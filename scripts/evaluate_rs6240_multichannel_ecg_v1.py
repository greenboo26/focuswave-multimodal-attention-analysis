"""Re-evaluate RS6240 S1/T0/T1/A4/C8-PH on ten windows with ECG evaluator v1.

The signal construction is intentionally copied from the first-pass ablation
logic, while the outcome metrics are replaced by the shared-offset,
beat-event evaluator in ``rs6240_ecg_evaluator_v1.py``. The script writes
only derived audit output under ``work/`` and never modifies raw data or the
existing baseline implementation.
"""

from __future__ import annotations

import csv
import json
import sys
from functools import lru_cache
from pathlib import Path

import bioread
import numpy as np
from scipy import signal


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from process_vital_signs_v3_1_1 import (  # noqa: E402
    FS,
    HR_HI_HZ,
    HR_LO_HZ,
    _analyze_displacement_v23,
    _sos_bandpass,
    select_bins_from_profile,
)
from rs6240_ecg_evaluator_v1 import evaluate_matched_beats, estimate_shared_offset  # noqa: E402


RAW = Path(r"D:\acq_mmwave_data")
REFERENCE = Path(r"D:\Project\厚粲杯\11_数据\derived\ecg_rsp_goldclean_reaudit_v1\goldclean_reference_windows.csv")
OUT = ROOT / "work" / "rs6240_ecg_evaluator_v1"
MODELS = {
    "S1": [0],
    "T0": [0, 1, 2, 3],
    "T1": [4, 5, 6, 7],
    "A4": [0, 1, 4, 5],
    "C8-PH": list(range(8)),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def ordered_files(mmwave: Path) -> list[Path]:
    return sorted(mmwave.glob("*_mmwave_datacube.npz")) + sorted(mmwave.glob("*_mmwave_datacube_part*.npz"))


@lru_cache(maxsize=16)
def timestamps(session: str) -> np.ndarray:
    path = RAW / session / "mmwave" / f"{session.rstrip('_')}_mmwave_timestamps.csv"
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) >= 3:
                try:
                    rows.append((int(row[0]), int(row[2])))
                except ValueError:
                    pass
    return np.asarray(rows, dtype=np.int64)


@lru_cache(maxsize=16)
def npz_index(session: str) -> tuple[tuple[Path, int, int], ...]:
    records = []
    offset = 0
    for path in ordered_files(RAW / session / "mmwave"):
        with np.load(path, allow_pickle=False) as data:
            keys = sorted(k for k in data.files if k.startswith("tx"))
            if len(keys) != 8 or len({data[k].shape for k in keys}) != 1:
                continue
            n = int(data[keys[0]].shape[0])
        records.append((path, offset, offset + n))
        offset += n
    return tuple(records)


def load_window(session: str, start_ms: int, end_ms: int) -> tuple[np.ndarray, int, int]:
    ts = timestamps(session)
    i0 = int(np.searchsorted(ts[:, 1], start_ms, side="left"))
    i1 = int(np.searchsorted(ts[:, 1], end_ms, side="right"))
    chunks = []
    for path, a, b in npz_index(session):
        left, right = max(i0, a), min(i1, b)
        if left >= right:
            continue
        with np.load(path, allow_pickle=False) as data:
            keys = sorted(k for k in data.files if k.startswith("tx"))
            chunks.append(np.stack([data[k][left - a : right - a] for k in keys], axis=-1).astype(np.complex64))
    if not chunks:
        raise RuntimeError(f"No NPZ data for {session} [{start_ms}, {end_ms}]")
    return np.concatenate(chunks, axis=0), i0, i1


@lru_cache(maxsize=16)
def load_ecg(session: str):
    raw_dir = RAW / session
    acq = sorted(raw_dir.glob("*.acq"))
    if not acq:
        raise FileNotFoundError(f"No BIOPAC acq for {session}")
    data = bioread.read_file(str(acq[0]))
    channel = next((c for c in data.channels if "ECG" in str(c.name).upper()), None)
    if channel is None:
        raise RuntimeError(f"No ECG channel in {acq[0]}")
    return np.asarray(channel.data, dtype=float), float(channel.samples_per_second), str(acq[0])


def ecg_clean_peaks(session: str, onset_acq_s: float, window_s: float = 30.0):
    """Keep the first-pass ECG cleaning rule unchanged for evaluator v1."""

    ecg, sr, acq_path = load_ecg(session)
    i0 = max(0, int(round((onset_acq_s - window_s) * sr)))
    i1 = min(len(ecg), int(round(onset_acq_s * sr)))
    seg = ecg[i0:i1] - np.median(ecg[i0:i1])
    sos = signal.butter(3, [0.5, 40.0], btype="band", fs=sr, output="sos")
    filtered = signal.sosfiltfilt(sos, seg)
    raw_peaks, _ = signal.find_peaks(filtered, distance=int(0.3 * sr), prominence=0.25)
    ibi_ms = np.diff(raw_peaks) / sr * 1000.0
    valid = (ibi_ms >= 300.0) & (ibi_ms <= 2000.0)
    if len(ibi_ms) >= 3:
        rel = np.abs(np.diff(ibi_ms)) / np.maximum(ibi_ms[:-1], 1.0)
        bad = np.zeros(len(ibi_ms), dtype=bool)
        for idx in np.where(rel > 0.20)[0]:
            bad[idx] = True
            bad[idx + 1] = True
        valid &= ~bad
    keep_peaks = raw_peaks[:-1][valid]
    if len(raw_peaks) and valid.size:
        keep_peaks = np.unique(np.concatenate([keep_peaks, raw_peaks[1:][valid]]))
    clean_ibi = np.diff(raw_peaks) / sr * 1000.0
    clean_ibi = clean_ibi[valid]
    rmssd = float(np.sqrt(np.mean(np.diff(clean_ibi) ** 2))) if len(clean_ibi) >= 3 else None
    return {
        "peaks_s": keep_peaks / sr,
        "ibi_ms": clean_ibi,
        "hr_bpm": 60000.0 / np.median(clean_ibi) if len(clean_ibi) else None,
        "rmssd_ms": rmssd,
        "acq_path": acq_path,
        "sr": sr,
    }


def model_bin(cube: np.ndarray, channels: list[int]) -> int:
    power = np.mean(np.abs(cube) ** 2, axis=0)
    candidates: dict[int, list[float]] = {}
    for ch in channels:
        _, _, rows = select_bins_from_profile(power, ch, cube, len(cube))
        for bin_idx, _hr_snr, _br_snr, _br_score, _stability, heart_score in rows:
            candidates.setdefault(int(bin_idx), []).append(float(heart_score))
    if candidates:
        return max(candidates, key=lambda idx: float(np.mean(candidates[idx])))
    return int(np.argmax(np.mean(power[:, channels], axis=1)))


def phase_signal(cube: np.ndarray, bin_idx: int, ch: int) -> np.ndarray:
    return np.unwrap(np.angle(cube[:, bin_idx, ch])).astype(float)


def fuse_phase(cube: np.ndarray, bin_idx: int, channels: list[int]) -> tuple[np.ndarray, dict]:
    signals = []
    scores = []
    for ch in channels:
        phi = phase_signal(cube, bin_idx, ch)
        band = _sos_bandpass(phi, HR_LO_HZ, HR_HI_HZ)
        residual = phi - signal.sosfiltfilt(signal.butter(3, [0.5, 3.0], btype="band", fs=FS, output="sos"), phi)
        score = float(np.std(band) / max(np.std(residual), 1e-9))
        signals.append(band - np.mean(band))
        scores.append(max(score, 1e-6))
    weights = np.asarray(scores, dtype=float)
    weights /= np.sum(weights)
    return np.sum(np.asarray(signals) * weights[:, None], axis=0), {"weights": weights.tolist(), "channels": channels, "bin": bin_idx}


def analyze_signal(x: np.ndarray, session: str):
    result, (_t, _breath, _heartbeat, peaks, _bp) = _analyze_displacement_v23(x, x, len(x), method="bp_heart", session=session)
    ibi = np.diff(peaks) / FS * 1000.0 if len(peaks) >= 2 else np.asarray([], dtype=float)
    ibi = ibi[(ibi >= 300.0) & (ibi <= 2000.0)]
    raw_phase = signal.detrend(x, type="linear")
    freqs, pxx = signal.periodogram(raw_phase, fs=FS, window="hann")
    mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    raw_bpm = float(freqs[mask][np.argmax(pxx[mask])] * 60.0) if np.any(mask) else None
    return {"result": result, "peaks_s": peaks / FS, "ibi_ms": ibi, "raw_hr_bpm": raw_bpm}


def rmssd(values: np.ndarray) -> float | None:
    return float(np.sqrt(np.mean(np.diff(values) ** 2))) if len(values) >= 3 else None


def build_model(cube: np.ndarray, session: str, model: str, channels: list[int]) -> dict:
    if model == "S1":
        all_channels = list(range(8))
        bin_idx = model_bin(cube, all_channels)
        scores = []
        for ch in all_channels:
            phi = phase_signal(cube, bin_idx, ch)
            band = _sos_bandpass(phi, HR_LO_HZ, HR_HI_HZ)
            scores.append(float(np.std(band)))
        ch = int(np.argmax(scores))
        x = _sos_bandpass(phase_signal(cube, bin_idx, ch), HR_LO_HZ, HR_HI_HZ)
        meta = {"channels": [ch], "bin": bin_idx, "weights": [1.0]}
    else:
        bin_idx = model_bin(cube, channels)
        x, meta = fuse_phase(cube, bin_idx, channels)
    return {"analysis": analyze_signal(x, session), "meta": meta}


def value_mean(rows: list[dict], key: str):
    values = [row[key] for row in rows if row.get(key) is not None]
    return float(np.mean(values)) if values else None


def main() -> None:
    references = [row for row in read_csv(REFERENCE) if row["session_id"] == "sub-97793_"][:10]
    if len(references) != 10:
        raise RuntimeError(f"Expected 10 sub-97793_ reference windows, got {len(references)}")

    windows = []
    for ref in references:
        session = ref["session_id"]
        onset_ms = int(ref["onset_ms"])
        cube, frame_start, frame_end = load_window(session, onset_ms - 30000, onset_ms)
        ecg = ecg_clean_peaks(session, float(ref["onset_acq_s"]))
        models = {name: build_model(cube, session, name, channels) for name, channels in MODELS.items()}
        windows.append({"ref": ref, "session": session, "onset_ms": onset_ms, "frame_start": frame_start, "frame_end": frame_end, "ecg": ecg, "models": models})
        print(f"built {session} onset={onset_ms} frames={frame_end - frame_start}")

    # One physical stream alignment: fit once from pooled S1 windows and use
    # exactly the same scalar for S1, T0, T1, A4 and C8-PH.
    offset_report = estimate_shared_offset(
        [(window["ecg"]["peaks_s"], window["models"]["S1"]["analysis"]["peaks_s"]) for window in windows],
        tolerance_s=0.15,
    )
    offset_s = float(offset_report["offset_s"])
    rows = []
    for window in windows:
        ref = window["ref"]
        ecg = window["ecg"]
        for model in MODELS:
            payload = window["models"][model]
            analysis = payload["analysis"]
            result = analysis["result"]
            heart_rate = result.get("heart_rate", {})
            matched = evaluate_matched_beats(ecg["peaks_s"], analysis["peaks_s"], offset_s, tolerance_s=0.15)
            pred_ibi = analysis["ibi_ms"]
            pred_full_rmssd = rmssd(pred_ibi)
            pred_hr = heart_rate.get("time_bpm")
            ecg_hr = ecg["hr_bpm"]
            row = {
                "evaluator_version": "ECG evaluator v1",
                "session": window["session"],
                "onset_ms": window["onset_ms"],
                "attention": ref["attention"],
                "frame_start": window["frame_start"],
                "frame_end": window["frame_end"],
                "model": model,
                "channels": "|".join(map(str, payload["meta"]["channels"])),
                "range_bin": payload["meta"]["bin"],
                "weights": json.dumps(payload["meta"]["weights"]),
                "global_offset_s": offset_s,
                "ecg_hr_bpm": ecg_hr,
                "pred_hr_bpm": pred_hr,
                "pred_raw_spectral_hr_bpm": analysis["raw_hr_bpm"],
                "hr_abs_error_bpm": abs(float(pred_hr) - ecg_hr) if pred_hr is not None and ecg_hr is not None else None,
                "ecg_rmssd_full_ms": ecg["rmssd_ms"],
                "radar_rmssd_full_ms": pred_full_rmssd,
                **matched,
                "resp_harmonic_mislock": int(any(abs(float(analysis["raw_hr_bpm"]) - harmonic * float(ref["rsp_br_bpm_goldclean"])) <= 5.0 for harmonic in (2.0, 3.0))) if analysis["raw_hr_bpm"] is not None and ref.get("rsp_br_bpm_goldclean") else None,
            }
            rows.append(row)

    OUT.mkdir(parents=True, exist_ok=True)
    window_path = OUT / "fusion_ecg_window_metrics.csv"
    with window_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    model_summary = {}
    summary_keys = [
        "hr_abs_error_bpm",
        "ibi_mae_ms_matched",
        "ibi_rmse_ms_matched",
        "rmssd_abs_error_ms_matched",
        "beat_precision",
        "beat_recall",
        "false_beat_rate",
        "timing_error_mae_ms",
        "resp_harmonic_mislock",
    ]
    for model in MODELS:
        model_rows = [row for row in rows if row["model"] == model]
        model_summary[model] = {
            "n_windows": len(model_rows),
            "matched_ibi_usable_windows": sum(row["matched_interval_count"] > 0 for row in model_rows),
            "matched_rmssd_usable_windows": sum(bool(row["rmssd_usable"]) for row in model_rows),
            **{key: value_mean(model_rows, key) for key in summary_keys},
        }

    summary = {
        "evaluator_version": "ECG evaluator v1",
        "reference_windows": len(references),
        "sessions": sorted({row["session"] for row in rows}),
        "matching": {
            "offset_estimation": offset_report,
            "offset_application": "one shared scalar fitted from pooled S1 windows, applied unchanged to every model/window",
            "algorithm": "monotonic one-to-one dynamic-programming beat-event matching",
            "tolerance_ms": 150.0,
            "ibi_rule": "only adjacent ECG beats and adjacent radar beats that are both matched one-to-one",
            "rmssd_rule": "computed only on the longest contiguous run of matched valid IBI intervals; coverage is reported",
        },
        "models": model_summary,
        "notes": [
            "ECG peak cleaning is unchanged from the first-pass evaluator.",
            "Ordinal truncation metrics are intentionally absent from this output.",
            "This remains a single-session, ten-window experimental comparison; no mainline algorithm was changed.",
            "No complex coherent fusion was run.",
        ],
    }
    with (OUT / "fusion_ecg_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

