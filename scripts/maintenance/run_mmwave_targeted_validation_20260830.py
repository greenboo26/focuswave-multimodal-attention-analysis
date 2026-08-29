"""Marker-driven, block-local mmWave targeted validation.

Diagnostic only: no producer, portable-V2 repository, acquisition program,
raw acquisition file, HRV algorithm, or full formal batch is modified/run.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt


ALGO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(r"D:\acq_mmwave_data")
FOCUSWAVE_ROOT = Path(r"D:\Project\厚粲杯\05_实验\FocusWave")
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
PRODUCER_FILE = ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
FOCUSWAVE_ECG_COMMIT = "8e6fe5c5d08f386661bc05aaf9d5c5715a43b317"
SUBJECTS = ("97793", "9779", "97795")
WINDOW_S = 20.0
STEP_S = 10.0
BOUNDARY_GUARD_S = 5.0
LOCAL_BIN_RADIUS = 3
FORMAL_BIN_SPACING_M = 0.037
BLOCK_MARKERS = {"block1": (12, 22), "block2": (13, 23), "block3": (14, 24), "block4": (16, 26)}
MARKER_VALUES = {1, 2, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26} | set(range(101, 111))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(repo: Path, *args: str, fallback: str = "unavailable") -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception:
        return fallback


def session_dir(subject: str) -> Path:
    return DATA_ROOT / f"sub-{subject}_"


def acq_path(subject: str) -> Path:
    candidates = sorted(session_dir(subject).glob("*.acq"))
    if not candidates:
        raise FileNotFoundError(f"No .acq file for {subject}")
    return candidates[0]


def load_events(subject: str) -> list[dict]:
    rows = read_csv(session_dir(subject) / "beh" / "events.csv")
    for row in rows:
        row["unix_ms_int"] = int(float(row.get("unix_ms", 0) or 0))
        row["marker_int"] = int(row["marker"]) if str(row.get("marker", "")).strip().isdigit() else None
    return rows


def load_mmwave_timestamps(subject: str) -> np.ndarray:
    path = session_dir(subject) / "mmwave" / f"sub-{subject}_mmwave_timestamps.csv"
    values = np.atleast_2d(np.loadtxt(path, delimiter=",", dtype=np.int64))
    if values.shape[1] < 3:
        raise ValueError(f"Timestamp file has fewer than 3 columns: {path}")
    return values[:, :3]


def decode_biopac_markers(subject: str) -> tuple[list[dict], dict]:
    """Decode eight Biopac digital input lines into marker pulse starts."""
    import bioread

    datafile = bioread.read_file(str(acq_path(subject)))
    digital = [channel for channel in datafile.channels if channel.name.startswith("Digital")]
    if len(digital) < 8:
        raise RuntimeError(f"{subject}: expected 8 digital channels, found {len(digital)}")
    matrix = np.column_stack([np.asarray(channel.data, dtype=float) for channel in digital[:8]])
    values = ((matrix > 2.5).astype(np.uint8).dot(1 << np.arange(8, dtype=np.uint8))).astype(np.int16)
    nonzero = values > 0
    starts = np.flatnonzero(nonzero & ~np.r_[False, nonzero[:-1]])
    pulses = []
    for pos in starts:
        value = int(values[pos])
        if value not in MARKER_VALUES:
            continue
        next_pos = int(starts[np.searchsorted(starts, pos, side="right")]) if np.searchsorted(starts, pos, side="right") < len(starts) else len(values)
        pulses.append({"sample_index": int(pos), "marker": value, "pulse_samples": next_pos - int(pos)})
    metadata = {
        "acq_path": str(acq_path(subject)),
        "acq_start_ms_metadata": int(datafile.earliest_marker_created_at.timestamp() * 1000),
        "acq_fs_hz": float(datafile.samples_per_second),
        "acq_samples": int(len(values)),
        "digital_channel_names": [channel.name for channel in digital[:8]],
        "digital_threshold_volts": 2.5,
        "physical_pulse_count": len(pulses),
    }
    return pulses, metadata


def _physical_segment(pulses: list[dict], start_marker: int, end_marker: int, after: int) -> list[dict]:
    start_idx = next((i for i in range(after, len(pulses)) if pulses[i]["marker"] == start_marker), None)
    if start_idx is None:
        return []
    end_idx = next((i for i in range(start_idx + 1, len(pulses)) if pulses[i]["marker"] == end_marker), None)
    return pulses[start_idx : end_idx + 1] if end_idx is not None else pulses[start_idx:]


def fit_linear(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    centered = x - np.mean(x)
    slope = float(np.dot(centered, y - np.mean(y)) / np.dot(centered, centered))
    return slope, float(np.mean(y) - slope * np.mean(x))


def block_intervals(subject: str, timestamps: np.ndarray, events: list[dict], physical: list[dict]) -> tuple[list[dict], list[dict]]:
    mm_unix = timestamps[:, 2].astype(np.int64)
    blocks, audits = [], []
    physical_cursor = 0
    for segment, (start_marker, end_marker) in BLOCK_MARKERS.items():
        start_rows = [row for row in events if row.get("event") == "segment_start" and row.get("segment") == segment and row.get("marker_int") == start_marker]
        start = start_rows[0] if start_rows else None
        end_rows = [row for row in events if row.get("event") == "segment_end" and row.get("segment") == segment and row.get("marker_int") == end_marker and start and row["unix_ms_int"] > start["unix_ms_int"]]
        end = end_rows[0] if end_rows else None
        event_segment = [row for row in events if row.get("segment") == segment and row.get("marker_int") is not None]
        physical_segment = _physical_segment(physical, start_marker, end_marker, physical_cursor) if start else []
        if physical_segment:
            physical_cursor += len(physical_segment)
        complete = bool(start and end and physical_segment and physical_segment[-1]["marker"] == end_marker)
        block = {
            "subject": subject, "block_id": segment, "condition": start.get("note", "") if start else "",
            "start_event_unix_ms": start["unix_ms_int"] if start else None, "end_event_unix_ms": end["unix_ms_int"] if end else None,
            "start_marker": start_marker, "end_marker": end_marker,
            "status": "complete" if complete else ("missing_event_or_physical_end" if start else "not_recorded"),
            "event_marker_rows": len(event_segment), "physical_marker_rows": len(physical_segment),
            "mmwave_start_row": None, "mmwave_end_row_exclusive": None, "mmwave_frames": None,
        }
        if start and end:
            i0 = int(np.searchsorted(mm_unix, start["unix_ms_int"], side="left"))
            i1 = int(np.searchsorted(mm_unix, end["unix_ms_int"], side="right"))
            block.update({"mmwave_start_row": i0, "mmwave_end_row_exclusive": i1, "mmwave_frames": i1 - i0})
        blocks.append(block)
        audit = {
            "subject": subject, "block_id": segment, "status": block["status"],
            "event_marker_rows": len(event_segment), "physical_marker_rows": len(physical_segment),
            "marker_sequence_exact": None, "event_start_marker": start_marker if start else None, "event_end_marker": end_marker if end else None,
            "physical_start_sample": physical_segment[0]["sample_index"] if physical_segment else None,
            "physical_end_sample": physical_segment[-1]["sample_index"] if complete else None,
            "ecg_fit_slope_samples_per_ms": None, "ecg_fit_intercept_sample": None,
            "ecg_clock_drift_ppm_vs_2000hz": None, "ecg_fit_residual_p95_ms": None, "ecg_fit_residual_max_ms": None,
            "marker_mismatch_count": None, "first_marker_mismatch_index": None, "event_marker_at_first_mismatch": None,
            "physical_marker_at_first_mismatch": None, "mmwave_tick_n": 0, "mmwave_tick_usable_n": 0,
            "mmwave_tick_gap_n_abs_over_100ms": 0, "mmwave_tick_delta_median_ms": None,
            "mmwave_tick_delta_p95_abs_ms": None, "mmwave_tick_delta_max_abs_ms": None,
            "mmwave_tick_fit_residual_p95_ms": None, "mmwave_tick_fit_residual_max_ms": None,
            "mmwave_tick_drift_ppm_vs_event_clock": None,
            "alignment_evidence": "events.csv + physical Biopac digital pulses + mmWave Unix timestamps",
        }
        if complete:
            event_markers = [row["marker_int"] for row in event_segment]
            physical_markers = [row["marker"] for row in physical_segment]
            audit["marker_sequence_exact"] = event_markers == physical_markers
            mismatches = [(i, event_markers[i], physical_markers[i]) for i in range(min(len(event_markers), len(physical_markers))) if event_markers[i] != physical_markers[i]]
            audit["marker_mismatch_count"] = len(mismatches) + abs(len(event_markers) - len(physical_markers))
            if mismatches:
                audit.update({"first_marker_mismatch_index": mismatches[0][0], "event_marker_at_first_mismatch": mismatches[0][1], "physical_marker_at_first_mismatch": mismatches[0][2]})
            pairs = [(row["unix_ms_int"], pulse["sample_index"]) for row, pulse in zip(event_segment, physical_segment) if row["marker_int"] == pulse["marker"]]
            if len(pairs) >= 3:
                x = np.asarray([pair[0] for pair in pairs], dtype=float)
                y = np.asarray([pair[1] for pair in pairs], dtype=float)
                slope, intercept = fit_linear(x, y)
                residual_ms = (y - (intercept + slope * x)) / slope
                audit.update({
                    "ecg_fit_slope_samples_per_ms": round(slope, 9), "ecg_fit_intercept_sample": round(intercept, 3),
                    "ecg_clock_drift_ppm_vs_2000hz": round((slope / 2.0 - 1.0) * 1_000_000, 3),
                    "ecg_fit_residual_p95_ms": round(float(np.percentile(np.abs(residual_ms), 95)), 6),
                    "ecg_fit_residual_max_ms": round(float(np.max(np.abs(residual_ms))), 6), "ecg_pair_count": len(pairs),
                })
                block["ecg_fit_slope"] = slope
                block["ecg_fit_intercept"] = intercept
            ticks = [row for row in event_segment if row["event"] == "tick" and 101 <= row["marker_int"] <= 110]
            tick_deltas, tick_mmwave_times, tick_event_times = [], [], []
            for row in ticks:
                idx = int(np.searchsorted(mm_unix, row["unix_ms_int"], side="left"))
                candidates = [candidate for candidate in (idx, idx - 1) if 0 <= candidate < len(mm_unix)]
                if not candidates:
                    continue
                idx = min(candidates, key=lambda candidate: abs(int(mm_unix[candidate]) - row["unix_ms_int"]))
                tick_deltas.append(float(mm_unix[idx] - row["unix_ms_int"]))
                tick_mmwave_times.append(float(mm_unix[idx])); tick_event_times.append(float(row["unix_ms_int"]))
            if tick_deltas:
                t = np.asarray(tick_event_times, dtype=float); matched = np.asarray(tick_mmwave_times, dtype=float)
                delta = np.asarray(tick_deltas, dtype=float)
                usable = np.abs(delta) <= 100.0
                audit.update({
                    "mmwave_tick_n": len(delta), "mmwave_tick_delta_median_ms": round(float(np.median(delta)), 6),
                    "mmwave_tick_delta_p95_abs_ms": round(float(np.percentile(np.abs(delta), 95)), 6),
                    "mmwave_tick_delta_max_abs_ms": round(float(np.max(np.abs(delta))), 6),
                    "mmwave_tick_usable_n": int(np.sum(usable)),
                    "mmwave_tick_gap_n_abs_over_100ms": int(np.sum(~usable)),
                })
                if int(np.sum(usable)) >= 3:
                    tick_slope, tick_intercept = fit_linear(t[usable], matched[usable])
                    residual_ms = matched[usable] - (tick_intercept + tick_slope * t[usable])
                    audit.update({
                        "mmwave_tick_fit_residual_p95_ms": round(float(np.percentile(np.abs(residual_ms), 95)), 6),
                        "mmwave_tick_fit_residual_max_ms": round(float(np.max(np.abs(residual_ms))), 6),
                        "mmwave_tick_drift_ppm_vs_event_clock": round((tick_slope - 1.0) * 1_000_000, 3),
                    })
        audits.append(audit)
    return blocks, audits


class PartReader:
    def __init__(self, subject: str):
        mmwave_dir = session_dir(subject) / "mmwave"
        base = mmwave_dir / f"sub-{subject}_mmwave_datacube.npz"
        parts = sorted(mmwave_dir.glob(f"sub-{subject}_mmwave_datacube_part*.npz"))
        self.files = ([base] if base.exists() else []) + parts
        if not self.files:
            raise FileNotFoundError(f"{subject}: no mmWave datacube NPZ files")
        self.lengths = []
        for path in self.files:
            with np.load(path) as data:
                keys = sorted(key for key in data.files if key.startswith("tx"))
                if not keys:
                    raise RuntimeError(f"{subject}: no tx arrays in {path.name}")
                self.lengths.append(int(data[keys[0]].shape[0]))
        self.starts = np.concatenate(([0], np.cumsum(np.asarray(self.lengths, dtype=np.int64))))
        self.total_frames = int(self.starts[-1])
        self.cache: OrderedDict[int, np.ndarray] = OrderedDict()

    def _part(self, index: int) -> np.ndarray:
        if index in self.cache:
            value = self.cache.pop(index)
            self.cache[index] = value
            return value
        with np.load(self.files[index]) as data:
            keys = sorted(key for key in data.files if key.startswith("tx"))
            value = np.stack([data[key] for key in keys], axis=-1).astype(np.complex64)
        self.cache[index] = value
        while len(self.cache) > 3:
            self.cache.popitem(last=False)
        return value

    def slice(self, start: int, end: int) -> np.ndarray:
        if end <= start:
            raise ValueError(f"Invalid frame slice {start}:{end}")
        if start < 0 or end > self.total_frames:
            raise RuntimeError(f"mmWave slice outside raw frame range {start}:{end} / {self.total_frames}")
        chunks, cursor = [], 0
        for index in range(len(self.files)):
            part_start, part_end = int(self.starts[index]), int(self.starts[index + 1])
            if part_end <= start:
                continue
            if part_start >= end:
                break
            data = self._part(index)
            lo, hi = max(0, start - part_start), min(data.shape[0], end - part_start)
            if lo < hi:
                chunks.append(data[lo:hi])
        if not chunks:
            raise RuntimeError(f"No mmWave frames for {start}:{end}")
        result = np.concatenate(chunks, axis=0)
        if len(result) != end - start:
            raise RuntimeError(f"Short mmWave slice: got {len(result)}, expected {end-start}")
        return result


def independent_selection(algo, iq: np.ndarray) -> tuple[dict, list[dict]]:
    # The stored IQ values can exceed complex64's safe range for squaring.
    # Promote before power calculation so selection is not affected by overflow.
    real = iq.real.astype(np.float64, copy=False)
    imag = iq.imag.astype(np.float64, copy=False)
    bin_power = np.mean(real * real + imag * imag, axis=0)
    br_ch, br_bin, hr_ch, hr_bin, summaries = algo.select_separate_channels_bins(bin_power, iq, iq.shape[0])
    return {"hr_channel": int(hr_ch), "hr_bin": int(hr_bin), "br_channel": int(br_ch), "br_bin": int(br_bin)}, summaries


def local_choice(summaries: list[dict], role: str, previous: tuple[int, int] | None) -> tuple[int, int, str]:
    bin_key = "heart_bin" if role == "hr" else "breath_bin"
    score_key = "best_hr_selection_score" if role == "hr" else "best_br_score"
    global_item = max(summaries, key=lambda item: item[score_key])
    if previous is None:
        return int(global_item["channel"]), int(global_item[bin_key]), "block_start_reset_independent_init"
    prev_ch, prev_bin = previous
    local = [item for item in summaries if abs(int(item[bin_key]) - prev_bin) <= LOCAL_BIN_RADIUS]
    if not local:
        return int(global_item["channel"]), int(global_item[bin_key]), "global_fallback_no_candidate_within_radius"
    def score(item: dict) -> float:
        return float(np.log1p(max(float(item[score_key]), 0.0)) - 0.20 * abs(int(item[bin_key]) - prev_bin) - 0.50 * (int(item["channel"]) != prev_ch))
    chosen = max(local, key=score)
    return int(chosen["channel"]), int(chosen[bin_key]), "within_block_local_neighborhood"


def estimate_vitals(algo, iq: np.ndarray, br_ch: int, br_bin: int, hr_ch: int, hr_bin: int) -> dict:
    out = {"hr_freq_bpm": None, "hr_time_bpm": None, "br_freq_bpm": None, "br_time_bpm": None, "analysis_status": "ok"}
    try:
        phase = np.unwrap(np.angle(iq[:, br_bin, br_ch]))
        disp_br = algo.WAVELENGTH_MM * phase / (4 * np.pi)
        _breath, br_freq, bp, _ = algo._select_breath_candidate(disp_br)
        if br_freq is not None:
            out["br_freq_bpm"] = round(float(br_freq * 60.0), 3)
        if len(bp) >= 2:
            out["br_time_bpm"] = round(float(60.0 * algo.FS / np.mean(np.diff(bp))), 3)
        disp_hr = algo.extract_displacement(iq, hr_bin, hr_ch)
        heart_bp = algo._sos_bandpass(disp_hr, algo.HR_LO_HZ, algo.HR_HI_HZ)
        # The target-validation contract is about target continuity and
        # marker-aligned same-window agreement.  Use the producer's existing
        # bandpass/spectral and peak-domain definitions here, but do not run
        # the unstable VMD branch on every diagnostic candidate.  This keeps
        # the rerun bounded and avoids silently turning it into a new HRV or
        # producer-method experiment.
        hr_freq = algo.estimate_freq_periodogram(heart_bp, algo.HR_LO_HZ, algo.HR_HI_HZ)
        peaks = algo.detect_peaks_heart_lo(heart_bp, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM)
        time_global = float(60.0 * algo.FS / np.mean(np.diff(peaks))) if len(peaks) >= 2 else None
        out["hr_freq_bpm"] = round(float(hr_freq * 60.0), 3) if hr_freq is not None else None
        out["hr_time_bpm"] = round(float(time_global), 3) if time_global is not None else None
        out["hr_n_peaks"] = int(len(peaks)); out["br_n_peaks"] = int(len(bp))
    except Exception as exc:
        out["analysis_status"] = f"error:{type(exc).__name__}"
    return out


def load_ecg_reference(subject: str) -> tuple[np.ndarray, np.ndarray, float]:
    import bioread
    datafile = bioread.read_file(str(acq_path(subject)))
    ecg = next((channel for channel in datafile.channels if "ecg" in channel.name.lower()), None)
    rsp = next((channel for channel in datafile.channels if any(token in channel.name.lower() for token in ("rsp", "resp", "respiration"))), None)
    if ecg is None or rsp is None:
        raise RuntimeError(f"{subject}: missing ECG/RSP channel")
    return np.asarray(ecg.data, dtype=float), np.asarray(rsp.data, dtype=float), float(datafile.samples_per_second)


def bandpass(x: np.ndarray, fs: float, lo: float, hi: float) -> np.ndarray:
    return sosfiltfilt(butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos"), x.astype(float))


def ecg_rsp_window(ecg: np.ndarray, rsp: np.ndarray, fs: float, start_sample: int, end_sample: int) -> dict:
    lo, hi = max(0, int(start_sample)), min(len(ecg), int(end_sample))
    if hi - lo < int(10 * fs):
        return {"ecg_hr_bpm": None, "rsp_br_bpm": None, "ecg_status": "short_window"}
    ecg_w = bandpass(ecg[lo:hi], fs, 5.0, min(35.0, fs / 2 - 1))
    robust = np.median(np.abs(ecg_w - np.median(ecg_w))) * 1.4826
    prominence = max(float(robust) * 1.2, float(np.std(ecg_w)) * 0.25, 1e-6)
    r_idx, _ = find_peaks(ecg_w, distance=int(0.45 * fs), prominence=prominence)
    ibi = np.diff(r_idx) / fs; ibi = ibi[(ibi >= 0.30) & (ibi <= 2.00)]
    hr = 60.0 / np.median(ibi) if len(ibi) >= 3 else None
    rsp_w = bandpass(rsp[lo:hi], fs, 0.08, min(0.7, fs / 2 - 1))
    p_idx, _ = find_peaks(rsp_w, distance=int(1.5 * fs), prominence=max(float(np.std(rsp_w)) * 0.15, 1e-9))
    p_ibi = np.diff(p_idx) / fs; p_ibi = p_ibi[(p_ibi >= 2.0) & (p_ibi <= 10.0)]
    br = 60.0 / np.median(p_ibi) if len(p_ibi) >= 2 else None
    return {"ecg_hr_bpm": round(float(hr), 3) if hr is not None else None, "rsp_br_bpm": round(float(br), 3) if br is not None else None, "ecg_n_rpeaks": int(len(r_idx)), "rsp_n_peaks": int(len(p_idx)), "ecg_status": "valid" if hr is not None else "insufficient_rpeaks"}


def generate_windows(block: dict, timestamps: np.ndarray) -> list[dict]:
    if block["status"] != "complete":
        return []
    start = float(block["start_event_unix_ms"]) + BOUNDARY_GUARD_S * 1000.0
    end = float(block["end_event_unix_ms"]) - BOUNDARY_GUARD_S * 1000.0
    rows, index = [], 1
    while start + WINDOW_S * 1000.0 <= end + 1e-6:
        stop = start + WINDOW_S * 1000.0
        i0 = int(np.searchsorted(timestamps[:, 2], int(round(start)), side="left")); i1 = int(np.searchsorted(timestamps[:, 2], int(round(stop)), side="right"))
        if i1 > i0:
            rows.append({"window_id": f"{block['block_id']}_w{index:03d}", "window_index_within_block": index, "window_start_unix_ms": int(round(start)), "window_end_unix_ms": int(round(stop)), "mmwave_start_row": i0, "mmwave_end_row_exclusive": i1, "mmwave_frames": i1-i0, "window_start_s_from_block": round((start-block["start_event_unix_ms"])/1000.0, 3), "window_end_s_from_block": round((stop-block["start_event_unix_ms"])/1000.0, 3)})
        start += STEP_S * 1000.0; index += 1
    return rows


def analyze_subject(subject: str, algo) -> tuple[list[dict], list[dict], dict]:
    timestamps = load_mmwave_timestamps(subject); events = load_events(subject); physical, digital_meta = decode_biopac_markers(subject)
    blocks, alignment = block_intervals(subject, timestamps, events, physical); reader = PartReader(subject); ecg, rsp, ecg_fs = load_ecg_reference(subject)
    windows, continuity = [], []
    for block in blocks:
        previous_hr = previous_br = None
        previous_current_hr = previous_current_br = None
        align = next(row for row in alignment if row["subject"] == subject and row["block_id"] == block["block_id"])
        for window in generate_windows(block, timestamps):
            iq = reader.slice(window["mmwave_start_row"], window["mmwave_end_row_exclusive"])
            independent, summaries = independent_selection(algo, iq)
            local_hr_ch, local_hr_bin, hr_reason = local_choice(summaries, "hr", previous_hr)
            local_br_ch, local_br_bin, br_reason = local_choice(summaries, "br", previous_br)
            current_vitals = estimate_vitals(algo, iq, independent["br_channel"], independent["br_bin"], independent["hr_channel"], independent["hr_bin"])
            local_vitals = estimate_vitals(algo, iq, local_br_ch, local_br_bin, local_hr_ch, local_hr_bin)
            slope, intercept = align.get("ecg_fit_slope_samples_per_ms"), align.get("ecg_fit_intercept_sample")
            if slope is None or intercept is None:
                reference = {"ecg_hr_bpm": None, "rsp_br_bpm": None, "ecg_status": "alignment_unavailable"}
            else:
                ecg_i0 = int(round(slope * window["window_start_unix_ms"] + intercept)); ecg_i1 = int(round(slope * window["window_end_unix_ms"] + intercept))
                reference = ecg_rsp_window(ecg, rsp, ecg_fs, ecg_i0, ecg_i1); reference.update({"ecg_start_sample": ecg_i0, "ecg_end_sample": ecg_i1})
            row = {**window, "subject": subject, "block_id": block["block_id"], "condition": block["condition"], "block_status": block["status"], "ecg_reference_source": "acq_ECG_RSP_block_affine_marker_alignment", **reference,
                   "current_hr_channel": independent["hr_channel"], "current_hr_bin": independent["hr_bin"], "current_br_channel": independent["br_channel"], "current_br_bin": independent["br_bin"],
                   "local_hr_channel": local_hr_ch, "local_hr_bin": local_hr_bin, "local_br_channel": local_br_ch, "local_br_bin": local_br_bin, "local_hr_reason": hr_reason, "local_br_reason": br_reason,
                   "current_hr_freq_bpm": current_vitals.get("hr_freq_bpm"), "current_hr_time_bpm": current_vitals.get("hr_time_bpm"), "current_br_freq_bpm": current_vitals.get("br_freq_bpm"), "current_br_time_bpm": current_vitals.get("br_time_bpm"),
                   "local_hr_freq_bpm": local_vitals.get("hr_freq_bpm"), "local_hr_time_bpm": local_vitals.get("hr_time_bpm"), "local_br_freq_bpm": local_vitals.get("br_freq_bpm"), "local_br_time_bpm": local_vitals.get("br_time_bpm"),
                   "current_analysis_status": current_vitals.get("analysis_status"), "local_analysis_status": local_vitals.get("analysis_status"), "hr_bin_displacement_current": None, "br_bin_displacement_current": None, "hr_channel_switch_current": None, "br_channel_switch_current": None, "hr_bin_displacement_local": None, "br_bin_displacement_local": None, "hr_channel_switch_local": None, "br_channel_switch_local": None, "hr_bin_displacement_m_formal_0p037_local": None, "br_bin_displacement_m_formal_0p037_local": None, "selection_scope": "strictly_within_complete_block; block state reset before first window"}
            if previous_current_hr is not None:
                row.update({"hr_bin_displacement_current": abs(independent["hr_bin"]-previous_current_hr[1]), "hr_channel_switch_current": independent["hr_channel"] != previous_current_hr[0]})
            if previous_current_br is not None:
                row.update({"br_bin_displacement_current": abs(independent["br_bin"]-previous_current_br[1]), "br_channel_switch_current": independent["br_channel"] != previous_current_br[0]})
            if previous_hr is not None:
                row.update({"hr_bin_displacement_local": abs(local_hr_bin-previous_hr[1]), "hr_channel_switch_local": local_hr_ch != previous_hr[0], "hr_bin_displacement_m_formal_0p037_local": round(abs(local_hr_bin-previous_hr[1])*FORMAL_BIN_SPACING_M, 6)})
            if previous_br is not None:
                row.update({"br_bin_displacement_local": abs(local_br_bin-previous_br[1]), "br_channel_switch_local": local_br_ch != previous_br[0], "br_bin_displacement_m_formal_0p037_local": round(abs(local_br_bin-previous_br[1])*FORMAL_BIN_SPACING_M, 6)})
            for method in ("current", "local"):
                row[f"{method}_hr_error_bpm"] = round(abs(float(row[f"{method}_hr_freq_bpm"])-float(reference["ecg_hr_bpm"])), 3) if row[f"{method}_hr_freq_bpm"] is not None and reference.get("ecg_hr_bpm") is not None else None
                row[f"{method}_br_error_bpm"] = round(abs(float(row[f"{method}_br_freq_bpm"])-float(reference["rsp_br_bpm"])), 3) if row[f"{method}_br_freq_bpm"] is not None and reference.get("rsp_br_bpm") is not None else None
            windows.append(row); continuity.append(row.copy()); previous_current_hr = (independent["hr_channel"], independent["hr_bin"]); previous_current_br = (independent["br_channel"], independent["br_bin"]); previous_hr = (local_hr_ch, local_hr_bin); previous_br = (local_br_ch, local_br_bin)
    meta = {"subject": subject, "timestamp_rows": int(len(timestamps)), "timestamp_start_unix_ms": int(timestamps[0, 2]), "timestamp_end_unix_ms": int(timestamps[-1, 2]), "raw_npz_files": [path.name for path in reader.files], "raw_npz_lengths": reader.lengths, "raw_npz_total_frames": reader.total_frames, "timestamp_rows_equal_raw_npz_frames": len(timestamps) == reader.total_frames, "digital": digital_meta, "blocks": blocks}
    return windows, continuity, {"metadata": meta, "alignment": alignment}


def audit_legacy_12(subject: str, timestamps: np.ndarray, events: list[dict]) -> list[dict]:
    intervals = []
    for segment in ("baseline", "rest", "block1", "block2", "block3", "block4"):
        start = next((row for row in events if row.get("event") == "segment_start" and row.get("segment") == segment), None)
        end = next((row for row in events if row.get("event") == "segment_end" and row.get("segment") == segment and start and row["unix_ms_int"] > start["unix_ms_int"]), None)
        if start and end: intervals.append((segment, start["unix_ms_int"], end["unix_ms_int"]))
    rows = []
    windows = ((0, 2000), (1000, 3000), (2000, 4000), (3000, 5000), (4000, 6000))
    for index, ((from_start, from_end), (to_start, to_end)) in enumerate(zip(windows, windows[1:]), 1):
        t0 = int(timestamps[from_start, 2]); t1 = int(timestamps[to_end-1, 2]); labels = [seg for seg, lo, hi in intervals if t0 < hi and t1 > lo]
        cross = len(labels) > 1 or "rest" in labels
        category = "cross_rest_or_block" if cross else ("baseline_or_preblock" if labels == ["baseline"] or not labels else "formal_segment_not_complete_block")
        rows.append({"subject": subject, "legacy_transition_id": f"w{index:02d}_to_w{index+1:02d}", "from_start_frame": from_start, "from_end_frame_exclusive": from_end, "to_start_frame": to_start, "to_end_frame_exclusive": to_end, "start_unix_ms": t0, "end_unix_ms": t1, "overlapping_program_segments": "|".join(labels) if labels else "none", "legacy_transition_category": category, "eligible_block_local_continuity": False, "exclusion_reason": "legacy_first_6000_frames_not_a_complete_formal_block"})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def build_report(summary: dict) -> str:
    mm = summary["method_metrics"]; aa = summary["alignment_summary"]; ll = summary["legacy_summary"]
    return f"""# mmWave targeted validation rerun — 2026-08-30

状态：`{summary['status']}`

本轮严格按 `MMWAVE_BLOCK_RESET_AND_ECG_ALIGNMENT_CONTRACT_2026-08-30.md` 重做。只分析三场目标场次的完整程序 block；未运行 Issue #16、C2B/C2C、HRV 新算法、全量 formal batch，未修改 `kyandi233-dev/Attention-Analysis@codex/formal-analysis-v2-portable`，也未修改实验程序或原始数据。

## 1. 先行结论

- 完整可分析 block：{summary['complete_blocks']}；不完整/未记录 block：{summary['incomplete_blocks']}。不完整 block 不进入 continuity 或 ECG 误差汇总。
- 每个 block 第一分析窗均重置 local target/bin/channel state；所有 transition 都要求前后窗口属于同一 block；跨 rest、坐姿调整和 block 边界没有计入。
- 完整 block 的程序 marker 与 Biopac 数字输入脉冲配对状态为 {aa['exact_complete_blocks']}/{aa['complete_blocks']} 个 block exact；tick 使用 101–110，并按 block 审计双机时间关系。tick 原始近邻差异包含采集空洞，不能直接当作时钟漂移。
- 唯一非 exact 的完整 block 为：{', '.join(aa['marker_mismatch_blocks']) if aa['marker_mismatch_blocks'] else '无'}；其余 marker 序列 exact。
- 结论等级：`{summary['status']}`。本轮支持修正旧证据边界，但不支持把 HR/BR 升级成正式 validated physiology；HRV 仍 BLOCKED。

## 2. 旧版 12 transitions 的撤销审计

旧版 3×5 个窗口产生 12 个 transition，但它们都来自每场 mmWave 起始后的前 6000 frames，而不是正式 Block 1/2/3/4：{ll['n_total']} 个 transition 中，{ll['inside_complete_block_transitions']} 个属于完整 formal block，{ll['cross_rest_or_block_transitions']} 个跨 rest/block boundary，{ll['baseline_or_preblock_transitions']} 个处于 baseline 或正式 block 之外。因此旧版 12/12 不再作为 block-local continuity failure 的证据。详表见 `legacy_12_transition_audit.csv`。

## 3. Block-local continuity

每个完整 block 从 start marker 后 {BOUNDARY_GUARD_S:.0f}s 开始，以 {WINDOW_S:.0f}s 窗、{STEP_S:.0f}s 步进，至 end marker 前 {BOUNDARY_GUARD_S:.0f}s 结束；窗口严格不跨 block。共 {summary['window_count']} 个窗口，{summary['transition_count']} 个同 block 相邻 transition。

| 方法 | HR bin hop | HR channel switch | BR bin hop | BR channel switch | HR MAE vs ECG (n) | BR MAE vs RSP (n) |
|---|---:|---:|---:|---:|---:|---:|
| CURRENT_INDEPENDENT | {summary['current_hr_bin_hops']}/{summary['transition_count']} | {summary['current_hr_channel_switches']}/{summary['transition_count']} | {summary['current_br_bin_hops']}/{summary['transition_count']} | {summary['current_br_channel_switches']}/{summary['transition_count']} | {mm['current']['hr_mae_bpm']} ({mm['current']['hr_n']}) | {mm['current']['br_mae_bpm']} ({mm['current']['br_n']}) |
| BLOCK_LOCAL_CONTINUITY | {summary['local_hr_bin_hops']}/{summary['transition_count']} | {summary['local_hr_channel_switches']}/{summary['transition_count']} | {summary['local_br_bin_hops']}/{summary['transition_count']} | {summary['local_br_channel_switches']}/{summary['transition_count']} | {mm['local']['hr_mae_bpm']} ({mm['local']['hr_n']}) | {mm['local']['br_mae_bpm']} ({mm['local']['br_n']}) |

`BLOCK_LOCAL_CONTINUITY` 是诊断性 candidate：block start 初始化；随后在上一 local target 的 ±3 bin 邻域内按既定 score penalty 选择，邻域无候选时回退 current selector。它没有写入 producer。判断不以少跳 bin 单独通过，而以 ECG/RSP agreement 是否改善为主。

本轮 HR/BR 数值使用现有 producer 的 bandpass、periodogram/peak 定义作 bounded diagnostic estimator；没有运行 VMD、HRV 新算法或修改 producer。因此这些数值只用于本轮 candidate 对照，不构成正式特征发布。

## 4. ECG/BIOPAC alignment audit

每个 block 单独使用 `events.csv` 的 start/end marker 和 101–110 tick；ECG sample index 由该 block 的 event-unix-ms → Biopac digital-pulse sample affine fit 得到。mmWave 窗口则由同一 event unix 时间直接定位到 mmWave timestamp rows。

| 指标 | 结果 |
|---|---:|
| complete blocks | {aa['complete_blocks']} |
| marker sequence exact | {aa['exact_complete_blocks']}/{aa['complete_blocks']} |
| ECG fit residual p95 (median across blocks, ms) | {aa['ecg_p95_median_ms']} |
| ECG fit residual max (max across blocks, ms) | {aa['ecg_max_max_ms']} |
| mmWave tick raw nearest delta p95 abs (median across blocks, ms) | {aa['mmwave_raw_p95_median_ms']} |
| mmWave tick raw nearest delta max abs (max across blocks, ms) | {aa['mmwave_raw_max_max_ms']} |
| mmWave tick affine-fit residual p95 (median across blocks, ms) | {aa['mmwave_fit_residual_p95_median_ms']} |
| mmWave tick affine-fit residual max (max across blocks, ms) | {aa['mmwave_fit_residual_max_max_ms']} |
| mmWave tick gaps with |delta| > 100 ms (complete blocks) | {aa['mmwave_tick_gap_n_abs_over_100ms']} |

完整逐 block 结果见 `ecg_alignment_audit.csv`；不完整 block 只保留 marker/数据缺口记录，不用于 physiology comparison。ECG affine fit 的残差可用于样本映射质量；mmWave tick 的原始大差异同时受 timestamp 采集空洞影响，本轮不把它解释成已通过的双机漂移校正。

## 5. Interpretation and remaining boundary

- 旧 12-transition 证据已撤销为 block-local failure 证据；新 block-local 表才是当前可引用的 continuity evidence。
- 若 local candidate 减少 switch 但没有改善 ECG/RSP error，不能因“轨迹更平滑”而升级；若两者均无稳定改善，则 target continuity remains unresolved。
- 本轮不把 ECG/RSP 值写入最终 mmWave producer feature table；HR、BR/RR 保持 HOLD，HRV 保持 BLOCKED。

## 6. Evidence files

- `target_continuity_block_local.csv` — block-local current/local selection and within-block transitions
- `mmwave_ecg_block_window_comparison.csv` — each block window's mmWave HR/BR and ECG/RSP same-window comparison
- `ecg_alignment_audit.csv` — program marker, Biopac digital pulse, tick and drift audit
- `legacy_12_transition_audit.csv` — old 12-transition eligibility reclassification
- `run_manifest.json` — input, source, parameters, exclusions and SHA-256 record
"""


def main() -> int:
    sys.path.insert(0, str(ALGO_ROOT / "scripts")); import process_vital_signs_v3_1_1 as algo
    all_windows, continuity, alignment_rows, metadata_rows, legacy_rows = [], [], [], [], []
    for subject in SUBJECTS:
        windows, cont, details = analyze_subject(subject, algo); all_windows.extend(windows); continuity.extend(cont); alignment_rows.extend(details["alignment"]); metadata_rows.append(details["metadata"]); legacy_rows.extend(audit_legacy_12(subject, load_mmwave_timestamps(subject), load_events(subject)))
    transitions = [row for row in continuity if row["window_index_within_block"] > 1]
    complete = [row for row in alignment_rows if row["status"] == "complete"]; exact = [row for row in complete if row.get("marker_sequence_exact") is True]
    def count(key: str) -> int: return sum(bool(row.get(key)) for row in transitions)
    def mae(method: str, metric: str) -> tuple[float | None, int]:
        vals = [float(row[f"{method}_{metric}_error_bpm"]) for row in all_windows if row.get(f"{method}_{metric}_error_bpm") is not None]
        return (round(float(np.mean(vals)), 3), len(vals)) if vals else (None, 0)
    chr_mae, chr_n = mae("current", "hr"); lhr_mae, lhr_n = mae("local", "hr"); cbr_mae, cbr_n = mae("current", "br"); lbr_mae, lbr_n = mae("local", "br")
    def agg(key: str, mode: str = "median"):
        vals = [float(row[key]) for row in complete if row.get(key) is not None]
        return round(float(np.median(vals) if mode == "median" else np.max(vals)), 6) if vals else None
    alignment_summary = {"complete_blocks": len(complete), "exact_complete_blocks": len(exact), "marker_mismatch_blocks": [f"{row['subject']}/{row['block_id']} (index {row['first_marker_mismatch_index']}: event {row['event_marker_at_first_mismatch']} vs physical {row['physical_marker_at_first_mismatch']})" for row in complete if row.get("marker_sequence_exact") is False], "ecg_p95_median_ms": agg("ecg_fit_residual_p95_ms"), "ecg_max_max_ms": agg("ecg_fit_residual_max_ms", "max"), "mmwave_raw_p95_median_ms": agg("mmwave_tick_delta_p95_abs_ms"), "mmwave_raw_max_max_ms": agg("mmwave_tick_delta_max_abs_ms", "max"), "mmwave_fit_residual_p95_median_ms": agg("mmwave_tick_fit_residual_p95_ms"), "mmwave_fit_residual_max_max_ms": agg("mmwave_tick_fit_residual_max_ms", "max"), "mmwave_tick_gap_n_abs_over_100ms": sum(int(row.get("mmwave_tick_gap_n_abs_over_100ms") or 0) for row in complete)}
    legacy_summary = {"n_total": len(legacy_rows), "inside_complete_block_transitions": sum(row.get("legacy_transition_category") == "formal_segment_not_complete_block" for row in legacy_rows), "cross_rest_or_block_transitions": sum(row.get("legacy_transition_category") == "cross_rest_or_block" for row in legacy_rows), "baseline_or_preblock_transitions": sum(row.get("legacy_transition_category") == "baseline_or_preblock" for row in legacy_rows)}
    summary = {"status": "PARTIAL / BLOCK_LOCAL_CONTINUITY_RETEST_COMPLETE_ECG_ALIGNMENT_LIMITS_RETAINED", "complete_blocks": len(complete), "incomplete_blocks": len(alignment_rows)-len(complete), "window_count": len(all_windows), "transition_count": len(transitions), "current_hr_bin_hops": sum(row.get("hr_bin_displacement_current") not in (None, 0) for row in transitions), "current_hr_channel_switches": count("hr_channel_switch_current"), "current_br_bin_hops": sum(row.get("br_bin_displacement_current") not in (None, 0) for row in transitions), "current_br_channel_switches": count("br_channel_switch_current"), "local_hr_bin_hops": sum(row.get("hr_bin_displacement_local") not in (None, 0) for row in transitions), "local_hr_channel_switches": count("hr_channel_switch_local"), "local_br_bin_hops": sum(row.get("br_bin_displacement_local") not in (None, 0) for row in transitions), "local_br_channel_switches": count("br_channel_switch_local"), "method_metrics": {"current": {"hr_mae_bpm": chr_mae, "hr_n": chr_n, "br_mae_bpm": cbr_mae, "br_n": cbr_n}, "local": {"hr_mae_bpm": lhr_mae, "hr_n": lhr_n, "br_mae_bpm": lbr_mae, "br_n": lbr_n}}, "alignment_summary": alignment_summary, "legacy_summary": legacy_summary, "hrv": "BLOCKED", "issue_16": "PAUSED", "external_rsp_role": "validation_reference_only", "producer_modified": False, "portable_repo_modified": False, "raw_data_modified": False}
    RESULT_ROOT.mkdir(parents=True, exist_ok=True); write_csv(RESULT_ROOT / "target_continuity_block_local.csv", continuity); write_csv(RESULT_ROOT / "mmwave_ecg_block_window_comparison.csv", all_windows); write_csv(RESULT_ROOT / "ecg_alignment_audit.csv", alignment_rows); write_csv(RESULT_ROOT / "legacy_12_transition_audit.csv", legacy_rows)
    (RESULT_ROOT / "target_continuity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"); (RESULT_ROOT / "ecg_alignment_summary.json").write_text(json.dumps({"alignment": alignment_summary, "blocks": alignment_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"status": summary["status"], "analysis_set": list(SUBJECTS), "complete_blocks": summary["complete_blocks"], "incomplete_blocks": summary["incomplete_blocks"], "canonical_algorithm_repo_head": git_value(ALGO_ROOT, "rev-parse", "HEAD"), "canonical_algorithm_remote_main_at_fetch": git_value(ALGO_ROOT, "rev-parse", "origin/main"), "producer_script": str(PRODUCER_FILE), "producer_script_sha256": sha256(PRODUCER_FILE), "diagnostic_script_sha256": sha256(Path(__file__)), "acquisition_repository": "kyandi233-dev/FocusWave", "acquisition_branch": "ecg", "acquisition_commit": FOCUSWAVE_ECG_COMMIT, "acquisition_source_files": ["01-MainProgram/core/event_logger.py", "01-MainProgram/core/parallel_marker.py", "01-MainProgram/main_experiment_msmf.py"], "contract": "docs/research/MMWAVE_BLOCK_RESET_AND_ECG_ALIGNMENT_CONTRACT_2026-08-30.md", "parameters": {"window_s": WINDOW_S, "step_s": STEP_S, "boundary_guard_s": BOUNDARY_GUARD_S, "local_bin_radius": LOCAL_BIN_RADIUS, "mmwave_fs_hz": 100.0, "ecg_fs_hz_expected": 2000.0, "formal_bin_spacing_m_reporting_only": FORMAL_BIN_SPACING_M, "mmwave_tick_usable_threshold_ms": 100.0, "vital_estimator": "existing producer bandpass plus periodogram/peak definitions; bounded diagnostic only; no VMD or HRV algorithm"}, "inputs": metadata_rows, "exclusions": ["Issue #16", "C2B", "C2C", "new HRV algorithm", "full formal batch", "portable V2 repository", "Attention-Analysis codex/formal-analysis-v2-portable", "NIR/RGB producer", "raw data modification"], "conclusion_boundary": "block-local diagnostic comparison only; HR/BR HOLD; HRV BLOCKED; no producer promotion"}
    names = ["target_continuity_block_local.csv", "mmwave_ecg_block_window_comparison.csv", "ecg_alignment_audit.csv", "legacy_12_transition_audit.csv", "target_continuity_summary.json", "ecg_alignment_summary.json"]
    manifest["output_files"] = [{"path": name, "sha256": sha256(RESULT_ROOT / name)} for name in names]
    manifest_path = RESULT_ROOT / "run_manifest.json"; manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULT_ROOT / "MMWAVE_TARGETED_VALIDATION_REPORT_2026-08-30.md").write_text(build_report(summary), encoding="utf-8")
    manifest["output_files"].append({"path": "MMWAVE_TARGETED_VALIDATION_REPORT_2026-08-30.md", "sha256": sha256(RESULT_ROOT / "MMWAVE_TARGETED_VALIDATION_REPORT_2026-08-30.md")}); manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
