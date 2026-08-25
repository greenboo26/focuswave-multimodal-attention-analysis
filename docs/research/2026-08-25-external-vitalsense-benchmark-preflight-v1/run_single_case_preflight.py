"""Single-record, parameterized smoke test for the VitalSense2024 MAT layout.

This is an adapter preflight, not a reproduction of a published result.  It
uses one explicitly named MAT file, produces only a JSON audit, and never
searches a beat-wise lag against ECG.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, filtfilt, find_peaks, windows


def robust_hr(t: np.ndarray) -> float | None:
    return float(60.0 / np.median(np.diff(t))) if len(t) >= 2 else None


def hrv_ms(ibi_s: np.ndarray) -> dict[str, float | None]:
    if len(ibi_s) < 2:
        return {"rmssd_ms": None, "sdnn_ms": None}
    return {
        "rmssd_ms": float(1000 * np.sqrt(np.mean(np.diff(ibi_s) ** 2))),
        "sdnn_ms": float(1000 * np.std(ibi_s, ddof=1)),
    }


def greedy_match(reference_s: np.ndarray, estimate_s: np.ndarray, tolerance_s: float):
    """One-to-one chronological matching; pairs are never re-used."""
    pairs, i, j = [], 0, 0
    while i < len(reference_s) and j < len(estimate_s):
        delta = estimate_s[j] - reference_s[i]
        if abs(delta) <= tolerance_s:
            pairs.append((i, j, float(delta)))
            i += 1
            j += 1
        elif estimate_s[j] < reference_s[i] - tolerance_s:
            j += 1
        else:
            i += 1
    return pairs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-mat", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    p.add_argument("--frame-s", type=float, default=0.003)
    p.add_argument("--raw-chirp-samples", type=int, default=512)
    p.add_argument("--adc-fs-hz", type=float, default=683600.0)
    p.add_argument("--center-hz", type=float, default=122e9)
    p.add_argument("--tolerance-s", type=float, default=0.075)
    args = p.parse_args()

    mat = loadmat(args.input_mat, squeeze_me=True)
    required = {"beatingTone_time", "ECGSignal"}
    absent = sorted(required - set(mat))
    if absent:
        raise SystemExit(f"missing required variables: {absent}")
    raw = np.asarray(mat["beatingTone_time"], dtype=float)
    ecg_raw = np.asarray(mat["ECGSignal"], dtype=float).ravel()
    if raw.ndim != 2 or raw.shape[0] != args.raw_chirp_samples:
        raise SystemExit(f"unexpected radar shape {raw.shape}; expected ({args.raw_chirp_samples}, frames)")
    if len(ecg_raw) != raw.size:
        raise SystemExit("ECG length is not one sample per raw radar ADC sample")

    n_frame = raw.shape[1]
    fs_frame = 1 / args.frame_s
    time_s = np.arange(n_frame) * args.frame_s
    # VitalSense2024-compatible target selection: maximum positive FFT index
    # over every 100th chirp, then windowed single-bin DFT over all chirps.
    nfft = raw.shape[0] * 8
    selected = raw[:, ::100] * windows.hann(raw.shape[0])[:, None]
    target_bin = int(np.max(np.argmax(np.abs(np.fft.fft(selected, nfft, axis=0))[: nfft // 2], axis=0)))
    n = np.arange(raw.shape[0])
    basis = windows.hann(raw.shape[0]) * np.exp(-2j * np.pi * target_bin * n / nfft)
    phase = np.unwrap(np.angle(basis @ raw) - np.angle(basis @ raw[:, 0]))
    radar_mm = 1000 * (3e8 / args.center_hz) / (4 * np.pi) * phase
    # Separation is intentionally the same 0.3-Hz low-pass subtraction route.
    b, a = butter(4, 0.3 / (fs_frame / 2), btype="low")
    cardiac = radar_mm - filtfilt(b, a, radar_mm)
    # ECG is acquired on the same ADC stream; take the first sample per chirp.
    ecg = ecg_raw[::args.raw_chirp_samples]
    ecg = (ecg - np.median(ecg)) / (np.std(ecg) + np.finfo(float).eps)
    ecg_peaks, _ = find_peaks(ecg, distance=round(0.30 * fs_frame), prominence=0.5)
    radar_peaks, _ = find_peaks(cardiac, distance=round(0.35 * fs_frame), prominence=0.25 * np.std(cardiac))
    ref_t, est_t = time_s[ecg_peaks], time_s[radar_peaks]
    pairs = greedy_match(ref_t, est_t, args.tolerance_s)
    matched_ref = np.array([ref_t[i] for i, _, _ in pairs])
    matched_est = np.array([est_t[j] for _, j, _ in pairs])
    ibi_ref, ibi_est = np.diff(matched_ref), np.diff(matched_est)
    ibi_err_ms = 1000 * (ibi_est - ibi_ref) if len(ibi_ref) else np.array([])
    hr_ref, hr_est = robust_hr(ref_t), robust_hr(est_t)
    h_ref, h_est = hrv_ms(ibi_ref), hrv_ms(ibi_est)
    out = {
        "status": "completed_single_record_smoke_test",
        "input_mat": str(args.input_mat),
        "input_variables": sorted(k for k in mat if not k.startswith("__")),
        "input_shapes": {"beatingTone_time": list(raw.shape), "ECGSignal": int(len(ecg_raw))},
        "parameters": {"frame_s": args.frame_s, "radar_fs_hz": fs_frame, "adc_fs_hz": args.adc_fs_hz,
                       "alignment": "same-ADC index correspondence; fixed lag 0 s; no ECG-driven lag optimization",
                       "beat_tolerance_s": args.tolerance_s, "target_selection": "max positive FFT bin over every 100th chirp"},
        "counts": {"radar_frames": n_frame, "ecg_beats": int(len(ref_t)), "radar_beats": int(len(est_t)), "matched_beats": len(pairs)},
        "metrics": {
            "hr_reference_bpm": hr_ref, "hr_radar_bpm": hr_est,
            "hr_absolute_error_bpm": None if hr_ref is None or hr_est is None else abs(hr_est - hr_ref),
            "beat_recall": len(pairs) / len(ref_t) if len(ref_t) else None,
            "beat_precision": len(pairs) / len(est_t) if len(est_t) else None,
            "matched_ibi_mae_ms": float(np.mean(np.abs(ibi_err_ms))) if len(ibi_err_ms) else None,
            "matched_ibi_bias_ms": float(np.mean(ibi_err_ms)) if len(ibi_err_ms) else None,
            "rmssd_error_ms": None if h_ref["rmssd_ms"] is None else abs(h_est["rmssd_ms"] - h_ref["rmssd_ms"]),
            "sdnn_error_ms": None if h_ref["sdnn_ms"] is None else abs(h_est["sdnn_ms"] - h_ref["sdnn_ms"]),
        },
        "limitations": ["ECG peak detector is a provisional generic detector, not adjudicated R-peaks.",
                        "Mechanical radar pulse morphology need not be zero-lag with ECG R-peaks; this smoke test deliberately does not learn a lag.",
                        "One example recording only; no subject/session split, tuning, or publication comparison is claimed."],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
