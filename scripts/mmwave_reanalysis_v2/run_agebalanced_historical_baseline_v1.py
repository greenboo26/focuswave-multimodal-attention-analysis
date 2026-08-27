"""Phase 2B-1 development-only AgeBalanced historical-baseline reproduction.

The legacy 25 s / 5 s route retains the immutable f4a8c74 algorithm and
legacy ECG scorer strictly for equivalence diagnosis.  It is intentionally not
schema-valid because the frozen per_window_benchmark_v1 schema only permits
10/30/60-second windows.  The 30 s / 5 s development route uses the frozen
ecg_reference_v1 and emits schema-valid JSON Lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import platform
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator
from scipy.signal import butter, find_peaks, sosfiltfilt

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from pipelines.mmwave.ecg_reference_v1 import detect_ecg_reference_v1, window_hr_from_reference


HISTORICAL_SOURCE_COMMIT = "f4a8c74d89ec28e005c537cbd5280a15dcb584e1"
FS_RADAR = 10.0
FS_ECG_LEGACY = 250.0
BREATH_BAND = (0.1, 0.5)
HEART_BAND = (0.8, 2.5)
FILT_ORDER = 4
RANGE_BIN_MIN, RANGE_BIN_MAX = 1, 10
AMP_TH_RATIO = 0.2
N_BINS = 3
BIN_AGREE_BPM = 6.0
GAP_HIGH, GAP_MED = 6.0, 12.0
MIN_PEAKS = 3
DATASET_ID = "agebalanced_60ghz_ecg"
DATASET_VERSION = "zenodo-16760683"


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_radar(session_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    with (session_dir / "radar_rFFTs.zlib").open("rb") as stream:
        rffts, _ = pickle.loads(zlib.decompress(stream.read()))
    timestamp_series = pd.read_csv(session_dir / "radar_timestamps.csv", header=None).iloc[:, 0]
    timestamps = pd.to_datetime(timestamp_series, errors="raise").astype("int64").to_numpy(dtype=float) / 1e9
    return np.asarray(rffts), timestamps


def load_ecg(session_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    frame = pd.read_csv(session_dir / "movesense_ecg.csv", parse_dates=["Timestamp"])
    absolute_s = frame["Timestamp"].astype("int64").to_numpy(dtype=float) / 1e9
    relative_s = absolute_s - absolute_s[0]
    return absolute_s, relative_s, frame["mV"].to_numpy(dtype=float)


def legacy_ecg_hr_bpm(relative_s: np.ndarray, mv: np.ndarray, start_s: float, end_s: float) -> float | None:
    """Direct transcription of f4a8c74's window-level ECG score."""
    mask = (relative_s >= start_s) & (relative_s < end_s)
    if int(np.sum(mask)) < FS_ECG_LEGACY * 5:
        return None
    segment = mv[mask] - np.median(mv[mask])
    sos = butter(2, [5, 15], btype="band", fs=FS_ECG_LEGACY, output="sos")
    filtered = sosfiltfilt(sos, segment)
    peaks, _ = find_peaks(filtered, distance=int(0.25 * FS_ECG_LEGACY), prominence=0.2 * np.std(filtered))
    if len(peaks) < 3:
        return None
    peak_times = relative_s[mask][peaks]
    peak_heights = filtered[peaks]
    keep = np.ones(len(peaks), dtype=bool)
    for index in range(1, len(peaks)):
        if peak_times[index] - peak_times[index - 1] < 0.4:
            if peak_heights[index] > peak_heights[index - 1]:
                keep[index - 1] = False
            else:
                keep[index] = False
    peaks = peaks[keep]
    if len(peaks) < 3:
        return None
    rr = np.diff(relative_s[mask][peaks])
    rr = rr[(rr > 0.25) & (rr < 2.0)]
    if len(rr) < 2:
        return None
    return 60.0 / float(np.median(rr))


def hps_fundamental(segment: np.ndarray, f_lo: float = 0.7, f_hi: float = 2.3) -> float | None:
    spectrum = np.abs(np.fft.rfft(segment))
    frequency = np.fft.rfftfreq(len(segment), d=1 / FS_RADAR)
    best_hz, best_power = None, -1.0
    for candidate in frequency[(frequency >= f_lo) & (frequency <= f_hi)]:
        power = spectrum[np.argmin(np.abs(frequency - candidate))]
        for multiplier in (2, 3):
            if multiplier * candidate > frequency.max():
                break
            power *= spectrum[np.argmin(np.abs(frequency - multiplier * candidate))]
        if power > best_power:
            best_power, best_hz = power, candidate
    return float(best_hz) if best_hz is not None else None


def refine_harmonic(segment: np.ndarray, f0_hz: float | None) -> tuple[float | None, bool]:
    if f0_hz is None or f0_hz / 2 < 0.45:
        return f0_hz, False
    best_hz, best_score = f0_hz, -1.0
    for candidate in (f0_hz, f0_hz / 2):
        sos = butter(FILT_ORDER, [2 * candidate * 0.85 / FS_RADAR, 2 * candidate * 1.15 / FS_RADAR], btype="bandpass", output="sos")
        filtered = sosfiltfilt(sos, segment)
        peaks, _ = find_peaks(filtered, distance=int(0.5 / candidate * FS_RADAR), prominence=0.2 * np.std(filtered))
        if len(peaks) < MIN_PEAKS:
            continue
        ibi = np.diff(peaks) / FS_RADAR
        ibi = ibi[(ibi > 0.25) & (ibi < 2.0)]
        if len(ibi) < 2:
            continue
        regularity = ibi.std() / ibi.mean()
        heights = filtered[peaks]
        height_cv = heights.std() / (heights.mean() + 1e-12)
        score = 1.0 / (regularity + height_cv + 1e-6)
        if score > best_score:
            best_score, best_hz = score, candidate
    return float(best_hz), abs(best_hz - f0_hz) > 1e-6


def window_vitals(signal: np.ndarray, window_s: float, step_s: float) -> list[dict[str, Any]]:
    window_frames, step_frames = int(window_s * FS_RADAR), int(step_s * FS_RADAR)
    rows: list[dict[str, Any]] = []
    for start_index in range(0, len(signal) - window_frames + 1, step_frames):
        segment = signal[start_index : start_index + window_frames]
        segment = segment - segment.mean()
        f0 = hps_fundamental(segment)
        f1, corrected = refine_harmonic(segment, f0)
        freq_bpm = f1 * 60 if f1 is not None else None
        sos = butter(FILT_ORDER, [2 * HEART_BAND[0] / FS_RADAR, 2 * HEART_BAND[1] / FS_RADAR], btype="bandpass", output="sos")
        heart = sosfiltfilt(sos, segment)
        peaks, _ = find_peaks(heart, distance=int(0.25 * FS_RADAR), prominence=0.3 * np.std(heart))
        if len(peaks) >= MIN_PEAKS:
            ibi = np.diff(peaks) / FS_RADAR
            ibi = ibi[(ibi > 0.25) & (ibi < 2.0)]
            time_bpm = 60.0 / float(np.median(ibi)) if len(ibi) >= 2 else None
            regularity = float(ibi.std() / ibi.mean()) if len(ibi) >= 2 else 1.0
        else:
            time_bpm, regularity = None, 1.0
        if freq_bpm is not None and time_bpm is not None:
            gap = abs(freq_bpm - time_bpm)
            fused = (freq_bpm + time_bpm) / 2
        else:
            gap, fused = None, freq_bpm if freq_bpm is not None else time_bpm
        if gap is None or time_bpm is None:
            legacy_quality = "low"
        elif gap <= GAP_HIGH and regularity < 0.25:
            legacy_quality = "high"
        elif gap <= GAP_MED:
            legacy_quality = "med"
        else:
            legacy_quality = "low"
        rows.append(
            {
                "win_start_s": start_index / FS_RADAR,
                "freq_bpm": round(freq_bpm, 1) if freq_bpm is not None else None,
                "time_bpm": round(time_bpm, 1) if time_bpm is not None else None,
                "fused_bpm": round(fused, 1) if fused is not None else None,
                "time_freq_gap_bpm": round(gap, 1) if gap is not None else None,
                "regularity": round(regularity, 3) if regularity < 1 else None,
                "n_peaks": int(len(peaks)),
                "harmonic_corrected": bool(corrected),
                "legacy_quality": legacy_quality,
            }
        )
    return rows


def select_top_bins(profile: np.ndarray) -> list[int]:
    amplitude = np.abs(profile).mean(axis=0)
    amplitude_threshold = AMP_TH_RATIO * amplitude[RANGE_BIN_MIN : RANGE_BIN_MAX + 1].max()
    phase_difference = np.diff(np.angle(profile), axis=0)
    frequency = np.fft.rfftfreq(phase_difference.shape[0], d=1 / FS_RADAR)
    band = (frequency >= 0.15) & (frequency <= 2.5)
    scored: list[tuple[float, int]] = []
    for bin_index in range(RANGE_BIN_MIN, RANGE_BIN_MAX + 1):
        if amplitude[bin_index] < amplitude_threshold:
            continue
        signal = phase_difference[:, bin_index] - phase_difference[:, bin_index].mean()
        power = np.abs(np.fft.rfft(signal))[band] ** 2
        scored.append((float(power.sum()), bin_index))
    scored.sort(reverse=True)
    return [bin_index for _, bin_index in scored[:N_BINS]]


def bin_phase_signal(profile: np.ndarray, bin_index: int) -> np.ndarray:
    phase = np.angle(profile[:, bin_index])
    phase_difference = np.diff(np.unwrap(phase))
    smoothing_frames = int(0.25 * FS_RADAR)
    return np.convolve(phase_difference, np.ones(smoothing_frames) / smoothing_frames, mode="same")


def vote_bins(per_bin_rows: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if not per_bin_rows:
        return []
    merged: list[dict[str, Any]] = []
    for window_index in range(len(per_bin_rows[0])):
        values = [row[window_index]["fused_bpm"] for row in per_bin_rows if row[window_index]["fused_bpm"] is not None]
        base = dict(per_bin_rows[0][window_index])
        if not values:
            base["vote_bins"] = 0
            merged.append(base)
            continue
        sorted_values = sorted(values)
        best_start, best_length = 0, 0
        for start in range(len(sorted_values)):
            end = start
            while end < len(sorted_values) and sorted_values[end] - sorted_values[start] <= BIN_AGREE_BPM:
                end += 1
            if end - start > best_length:
                best_length, best_start = end - start, start
        group = sorted_values[best_start : best_start + best_length]
        base["fused_bpm"] = round(float(np.median(group)), 1)
        base["vote_bins"] = len(group)
        base["n_bin_estimates"] = len(values)
        if len(group) >= 2 and base.get("time_freq_gap_bpm") is not None and base["time_freq_gap_bpm"] <= GAP_MED:
            base["legacy_quality"] = "high" if base["time_freq_gap_bpm"] <= GAP_HIGH else "med"
        elif len(group) < 2:
            base["legacy_quality"] = "low"
        merged.append(base)
    trajectory = [row["fused_bpm"] for row in merged]
    for index, row in enumerate(merged):
        if trajectory[index] is None:
            row["traj_bpm"] = None
            continue
        neighbours = [trajectory[other] for other in (index - 1, index + 1) if 0 <= other < len(trajectory) and trajectory[other] is not None]
        row["traj_bpm"] = round(float(np.median(neighbours)), 1) if neighbours and abs(trajectory[index] - np.median(neighbours)) > 12 else row["fused_bpm"]
    return merged


def estimate_baseline(rffts: np.ndarray, window_s: float, step_s: float) -> tuple[list[dict[str, Any]], list[int]]:
    profile = np.mean(rffts, axis=1)
    selected_bins = select_top_bins(profile)
    if not selected_bins:
        return [], []
    return vote_bins([window_vitals(bin_phase_signal(profile, bin_index), window_s, step_s) for bin_index in selected_bins]), selected_bins


def source_hash_lookup(provenance: dict[str, Any]) -> dict[str, str]:
    return {item["relative_path"]: item["sha256"] for item in provenance["source_package"]["files"]}


def common_radar_qc(rffts: np.ndarray, timestamps: np.ndarray, start_index: int, window_frames: int) -> dict[str, Any]:
    window = rffts[start_index : start_index + window_frames, :, RANGE_BIN_MIN : RANGE_BIN_MAX + 1]
    time_window = timestamps[start_index : start_index + window_frames]
    finite_ratio = float(np.mean(np.isfinite(window))) if window.size else 0.0
    expected = window_frames
    timestamp_coverage = len(time_window) / expected if expected else 0.0
    gaps = np.diff(time_window)
    max_gap_s = float(np.max(gaps)) if gaps.size else None
    residual = window - np.mean(window, axis=0, keepdims=True)
    power = np.mean(np.abs(residual) ** 2, axis=0)
    if not np.any(np.isfinite(power)) or float(np.nanmax(power)) <= 0:
        return {"status": "fail", "quality_stratum": "rejected", "timestamp_coverage": timestamp_coverage, "finite_ratio": finite_ratio, "max_gap_s": max_gap_s, "target_snr_db": None, "target_coherence": None, "motion_status": "not_available", "rejection_reason": "NO_TARGET"}
    channel_index, local_bin = np.unravel_index(np.nanargmax(power), power.shape)
    non_adjacent = [index for index in range(power.shape[1]) if abs(index - local_bin) > 1]
    denominator = float(np.nanmedian(power[:, non_adjacent])) if non_adjacent else float("nan")
    numerator = float(power[channel_index, local_bin])
    snr_db = 10.0 * np.log10(numerator / denominator) if denominator > 0 and np.isfinite(denominator) else None
    selected = window[:, channel_index, local_bin]
    increment = np.diff(np.angle(selected))
    unit = np.exp(1j * increment[np.isfinite(increment)])
    coherence = float(abs(np.mean(unit))) if unit.size else None
    rejected = timestamp_coverage < 0.8 or finite_ratio < 0.95 or (max_gap_s is not None and max_gap_s > 1.0)
    if rejected:
        status, stratum, reason = "fail", "rejected", "RADAR_QC"
    elif timestamp_coverage >= 0.99 and finite_ratio >= 0.999 and max_gap_s <= 0.2 and snr_db is not None and snr_db >= 10 and coherence is not None and coherence >= 0.8:
        status, stratum, reason = "pass", "high", None
    elif timestamp_coverage >= 0.95 and finite_ratio >= 0.995 and max_gap_s <= 0.5 and snr_db is not None and snr_db >= 3 and coherence is not None and coherence >= 0.5:
        status, stratum, reason = "pass", "medium", None
    else:
        status, stratum, reason = "pass", "low", None
    return {"status": status, "quality_stratum": stratum, "timestamp_coverage": timestamp_coverage, "finite_ratio": finite_ratio, "max_gap_s": max_gap_s, "target_snr_db": snr_db, "target_coherence": coherence, "motion_status": "not_available", "rejection_reason": reason}


def harmonic_classification(estimate: float | None, reference: float | None) -> str:
    if estimate is None or reference is None:
        return "not_assessable"
    if abs(estimate - reference) <= 3.0:
        return "none"
    if abs(estimate - 2 * reference) <= max(3.0, 0.05 * 2 * reference):
        return "two_x_hr"
    if abs(estimate - 0.5 * reference) <= max(3.0, 0.05 * 0.5 * reference):
        return "half_x_hr"
    return "none"


def make_schema_row(
    run_id: str,
    subject_id: str,
    session_id: str,
    start_s: float,
    estimate: float | None,
    radar_qc: dict[str, Any],
    ecg_full: Any,
    ecg_window: Any,
    config_hash: str,
    input_hash: str | None,
) -> dict[str, Any]:
    if ecg_window.status == "pass" and radar_qc["status"] == "pass" and estimate is not None:
        outcome, rejection_reason = "scored", None
    elif ecg_window.status != "pass":
        outcome, rejection_reason = "rejected", "ECG_QC_FAIL"
    elif radar_qc["status"] != "pass":
        outcome, rejection_reason = "rejected", "RADAR_QC_FAIL"
    else:
        outcome, rejection_reason = "rejected", "METHOD_REJECTED"
    reference_value = ecg_window.hr_bpm if ecg_window.status == "pass" else None
    absolute_error = abs(estimate - reference_value) if outcome == "scored" else None
    ecg_status = "pass" if ecg_window.status == "pass" else "fail"
    return {
        "schema_version": "per_window_benchmark_v1",
        "run_id": run_id,
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "subject_id": subject_id,
        "session_id": session_id,
        "split": "development",
        "window_id": f"{session_id}_{int(round(start_s * 1000)):08d}",
        "window_start_s": float(start_s),
        "window_end_s": float(start_s + 30.0),
        "window_length_s": 30,
        "method": {"id": "historical_agebalanced_baseline", "version": "f4a8c74_legacy_core_30s_adapter_v1", "implementation_class": "project_existing", "source_commit": HISTORICAL_SOURCE_COMMIT, "config_sha256": config_hash, "input_sha256": input_hash},
        "radar_qc": radar_qc,
        "reference_qc": {
            "ecg": {"available": True, "status": ecg_status, "sampling_rate_hz": ecg_full.sampling_rate_hz, "valid_ratio": ecg_window.valid_ratio, "source_kind": "raw_waveform", "rejection_reason": ecg_window.rejection_reason},
            "rsp": {"available": False, "status": "not_available", "sampling_rate_hz": None, "valid_ratio": None, "source_kind": "none", "rejection_reason": "NO_RSP"},
            "r_peaks": {"available": ecg_full.status == "pass", "status": ecg_status, "sampling_rate_hz": ecg_full.sampling_rate_hz, "valid_ratio": ecg_window.valid_ratio, "source_kind": "derived_events" if ecg_full.status == "pass" else "none", "rejection_reason": ecg_window.rejection_reason},
        },
        "sync": {"status": "pass", "timestamp_origin": "source_timestamps", "offset_ms": 0.0, "offset_source": "source_timestamps", "per_window_search_used": False},
        "hr": {"scorable": outcome == "scored", "reference_value": reference_value, "estimate_value": estimate, "absolute_error": absolute_error},
        "br": {"scorable": False, "reference_value": None, "estimate_value": None, "absolute_error": None},
        "beat": {"scorable": False, "status": "blocked_hrv", "match_tolerance_ms": 75, "reference_count": None, "estimate_count": None, "matched_count": None, "precision": None, "recall": None, "f1": None, "timing_mae_ms": None, "ibi_mae_ms": None},
        "harmonic_lock": {"classification": harmonic_classification(estimate, reference_value), "reference_basis": "ecg_hr" if reference_value is not None else "none", "tolerance_bpm": 3.0 if reference_value is not None else None},
        "outcome_status": outcome,
        "rejection_reason": rejection_reason,
    }


def summarize_legacy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    session_errors: dict[str, list[float]] = defaultdict(list)
    quality_errors: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["estimate_bpm"] is None or row["legacy_gold_bpm"] is None:
            continue
        error = abs(row["estimate_bpm"] - row["legacy_gold_bpm"])
        session_errors[row["session_id"]].append(error)
        quality_errors[row["legacy_quality"]].append(error)
    per_session_mae = [float(np.mean(values)) for values in session_errors.values() if values]
    return {
        "sessions_with_pairs": len(per_session_mae),
        "window_pairs": int(sum(len(values) for values in session_errors.values())),
        "session_mae_median_bpm": float(np.median(per_session_mae)) if per_session_mae else None,
        "quality": {quality: {"n": len(values), "mean_ae_bpm": float(np.mean(values)), "median_ae_bpm": float(np.median(values))} for quality, values in sorted(quality_errors.items())},
    }


def summarize_schema(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row["outcome_status"] == "scored"]
    errors = [row["hr"]["absolute_error"] for row in scored]
    by_stratum: dict[str, list[float]] = defaultdict(list)
    for row in scored:
        by_stratum[row["radar_qc"]["quality_stratum"]].append(row["hr"]["absolute_error"])
    return {
        "attempted_windows": len(rows),
        "scored_windows": len(scored),
        "coverage": len(scored) / len(rows) if rows else 0.0,
        "mae_bpm": float(np.mean(errors)) if errors else None,
        "median_ae_bpm": float(np.median(errors)) if errors else None,
        "rmse_bpm": float(np.sqrt(np.mean(np.square(errors)))) if errors else None,
        "quality": {quality: {"n": len(values), "mae_bpm": float(np.mean(values)), "median_ae_bpm": float(np.median(values))} for quality, values in sorted(by_stratum.items())},
        "rejection_reasons": dict(Counter(row["rejection_reason"] for row in rows if row["rejection_reason"])),
    }


def development_sessions(data_root: Path, split: dict[str, Any]) -> list[tuple[str, str, Path]]:
    sessions: list[tuple[str, str, Path]] = []
    for subject_id in split["development_participants"]:
        for posture in ("Lying", "Sitting"):
            path = data_root / subject_id / posture / "Rest"
            if (path / "radar_rFFTs.zlib").is_file() and (path / "movesense_ecg.csv").is_file():
                sessions.append((subject_id, f"{subject_id}_{posture.lower()}_rest", path))
            else:
                raise FileNotFoundError(f"missing expected development Rest session: {path}")
    return sessions


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    data_root = args.data_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    provenance = load_json(args.provenance)
    split = load_json(args.split)
    source_hashes = source_hash_lookup(provenance)
    sessions = development_sessions(data_root, split)
    frozen_config = load_json(args.baseline_config)
    declared_config_hash = frozen_config.pop("config_hash_sha256")
    config = frozen_config
    config_hash = sha256_canonical(config)
    if config_hash != declared_config_hash:
        raise RuntimeError(
            "baseline configuration hash does not match the frozen declaration: "
            f"expected {declared_config_hash}, got {config_hash}"
        )
    legacy_rows: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []
    reference_qc_sessions: list[dict[str, Any]] = []
    schema_validator = Draft202012Validator(load_json(args.schema))
    for index, (subject_id, session_id, session_dir) in enumerate(sessions, start=1):
        print(f"[{index}/{len(sessions)}] {session_id}", flush=True)
        rffts, radar_timestamps = load_radar(session_dir)
        ecg_absolute, ecg_relative, ecg_values = load_ecg(session_dir)
        ecg_reference = detect_ecg_reference_v1(ecg_absolute, ecg_values)
        reference_qc_sessions.append({"subject_id": subject_id, "session_id": session_id, "status": ecg_reference.status, "reason": ecg_reference.rejection_reason, "sampling_rate_hz": ecg_reference.sampling_rate_hz, "valid_ratio": ecg_reference.valid_ratio, "peak_count": int(ecg_reference.r_peak_times_s.size)})
        base_rows_25, selected_bins_25 = estimate_baseline(rffts, 25.0, 5.0)
        for row in base_rows_25:
            gold = legacy_ecg_hr_bpm(ecg_relative, ecg_values, row["win_start_s"], row["win_start_s"] + 25.0)
            legacy_rows.append({"subject_id": subject_id, "session_id": session_id, "window_start_s": row["win_start_s"], "window_end_s": row["win_start_s"] + 25.0, "window_length_s": 25.0, "selected_bins": selected_bins_25, "estimate_bpm": row["traj_bpm"], "legacy_gold_bpm": round(gold, 1) if gold is not None else None, "legacy_quality": row["legacy_quality"], "legacy_fields": row, "schema_status": "SCHEMA_INCOMPATIBLE_WINDOW_LENGTH_25"})
        base_rows_30, _ = estimate_baseline(rffts, 30.0, 5.0)
        relative_radar_path = (session_dir.relative_to(data_root) / "radar_rFFTs.zlib").as_posix()
        input_hash = source_hashes.get(relative_radar_path)
        for row in base_rows_30:
            start_s = row["win_start_s"]
            start_index = int(round(start_s * FS_RADAR))
            radar_qc = common_radar_qc(rffts, radar_timestamps, start_index, int(30 * FS_RADAR))
            ecg_window = window_hr_from_reference(ecg_reference, radar_timestamps[start_index], radar_timestamps[start_index] + 30.0)
            record = make_schema_row("phase2b1_agebalanced_development_30s_v1", subject_id, session_id, start_s, row["traj_bpm"], radar_qc, ecg_reference, ecg_window, config_hash, input_hash)
            schema_validator.validate(record)
            schema_rows.append(record)
    write_jsonl(output_dir / "legacy_equivalence_25s_development_rows.jsonl", legacy_rows)
    write_jsonl(output_dir / "per_window_benchmark_v1_development_30s.jsonl", schema_rows)
    legacy_summary = summarize_legacy(legacy_rows)
    schema_summary = summarize_schema(schema_rows)
    reference_summary = {"sessions": len(reference_qc_sessions), "pass_sessions": sum(row["status"] == "pass" for row in reference_qc_sessions), "failed_sessions": [row for row in reference_qc_sessions if row["status"] != "pass"]}
    report = {
        "status": "PARTIAL_DEVELOPMENT_ONLY",
        "phase": "2B-1 Historical Baseline Reproduction",
        "authorization_boundary": "No held_out participants, formal cohort, HRV or new candidate methods were run.",
        "config_hash_sha256": config_hash,
        "historical_equivalence": {"scope": "development_only 30 participants / 60 Rest sessions", "window_s": 25.0, "step_s": 5.0, "schema_status": "INCOMPATIBLE_WITH_FROZEN_PER_WINDOW_SCHEMA_WINDOW_ENUM", "summary": legacy_summary, "historical_full_220_reference": {"session_mae_median_bpm": 9.5, "quality_reported": {"high": 1.6, "med": 3.4, "low": 10.1}, "harmonic_locks": "4/1188 two_x; 0 half; exact historical lock-classification code MISSING_EVIDENCE"}},
        "ecg_reference_v1": reference_summary,
        "development_30s_schema": {"scope": "development_only 30 participants / 60 Rest sessions", "window_s": 30.0, "step_s": 5.0, "schema_valid": True, "summary": schema_summary},
        "outputs": {"legacy_rows": "legacy_equivalence_25s_development_rows.jsonl", "schema_rows": "per_window_benchmark_v1_development_30s.jsonl"},
        "environment": {"python": sys.version, "platform": platform.platform()},
        "created_utc": utc_now(),
    }
    (output_dir / "phase2b1_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "phase2b1_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provenance", default="configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json", type=Path)
    parser.add_argument("--split", default="configs/mmwave_reanalysis_v2/agebalanced_split_v1.json", type=Path)
    parser.add_argument("--schema", default="schemas/mmwave/per_window_benchmark_v1.schema.json", type=Path)
    parser.add_argument("--baseline-config", default="configs/mmwave_reanalysis_v2/agebalanced_historical_baseline_v1.json", type=Path)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({"status": report["status"], "config_hash_sha256": report["config_hash_sha256"], "legacy_session_mae_median_bpm": report["historical_equivalence"]["summary"]["session_mae_median_bpm"], "schema_coverage": report["development_30s_schema"]["summary"]["coverage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
