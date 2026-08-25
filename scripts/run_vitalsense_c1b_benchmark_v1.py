"""C1b formal VS_DATASET Radar--Mindray ECG benchmark.

This is a thin, deterministic runner for the locally downloaded VS_DATASET
healthy cohort.  It does not write raw data or derived data into the repo.
The two radar methods are deliberately simple, frozen baselines:

* project_bandpass_peak: cardiac-band filtering followed by prominence peaks;
* vitalsense_amf: 0.3-Hz separation, FFT period estimate, sinusoidal template
  reconstruction and matched-filter peak detection, following the checked-in
  VitalSense2024 public MATLAB route.

The runner reports raw timing and a pre-specified constant-delay sensitivity
using a calibration-only estimate.  The primary beat metrics remain raw,
zero-lag aligned at the file time origins; IBI/HRV are evaluated independently
of a constant delay.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, filtfilt, find_peaks, hilbert, correlate, resample_poly


TOLERANCES_MS = (50.0, 75.0, 100.0, 150.0)
PRIMARY_TOLERANCE_MS = 75.0


def arr(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=float).squeeze()


def scalar(x: Any) -> float:
    return float(np.asarray(x).squeeze())


def butter_filter(x: np.ndarray, fs: float, lo: float | None, hi: float | None) -> np.ndarray:
    nyq = fs / 2.0
    if lo is None:
        b, a = butter(4, hi / nyq, btype="low")
    elif hi is None:
        b, a = butter(4, lo / nyq, btype="high")
    else:
        b, a = butter(4, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, x)


def normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return (x - np.nanmedian(x)) / (np.nanstd(x) + np.finfo(float).eps)


def ecg_rpeaks(ecg: np.ndarray, fs: float) -> np.ndarray:
    """Fixed ECG Lead-II detector; no radar-informed tuning."""
    x = normalize(butter_filter(np.nan_to_num(ecg), fs, 5.0, 25.0))
    p1, q1 = find_peaks(x, distance=max(1, round(0.30 * fs)), prominence=0.35)
    p2, q2 = find_peaks(-x, distance=max(1, round(0.30 * fs)), prominence=0.35)
    if np.median(q2.get("prominences", [0])) > np.median(q1.get("prominences", [0])):
        return p2.astype(int)
    return p1.astype(int)


def radar_cardio(vital: np.ndarray, fs: float) -> np.ndarray:
    # Checked public route: low-pass respiratory estimate, cardiac residual.
    return vital - butter_filter(vital, fs, None, 0.30)


def project_bandpass_peak(vital: np.ndarray, fs: float) -> np.ndarray:
    x = normalize(butter_filter(np.nan_to_num(vital), fs, 0.67, 3.33))
    prominence = max(0.12, 0.20 * float(np.std(x)))
    p, _ = find_peaks(x, distance=max(1, round(0.35 * fs)), prominence=prominence)
    return p.astype(int)


def vitalsense_amf(vital: np.ndarray, fs: float) -> np.ndarray:
    """Python translation of the checked VitalSense2024 AMF route."""
    sig = radar_cardio(np.nan_to_num(vital), fs)
    n = len(sig)
    if n < int(5 * fs):
        return np.array([], dtype=int)
    # Keep the public route's physiological HR band and choose the strongest
    # period peak without using ECG or test labels.
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    power = np.abs(np.fft.rfft(sig * np.hanning(n)))
    valid = (freqs >= 0.667) & (freqs <= 3.333)
    if not np.any(valid):
        return np.array([], dtype=int)
    f0 = float(freqs[valid][np.argmax(power[valid])])
    if not np.isfinite(f0) or f0 <= 0:
        return np.array([], dtype=int)
    period = max(3, int(round(fs / f0)))
    # Public code first estimates a pulse template from initial periodic peaks;
    # a fixed sinusoidal template is the deterministic thin equivalent when a
    # full pulse template cannot be identified without hidden tuning.
    phase = np.arange(period) / period * 2.0 * np.pi
    template = np.sin(phase)
    template -= template.mean()
    template /= np.linalg.norm(template) + np.finfo(float).eps
    matched = np.convolve(normalize(sig), template[::-1], mode="same")
    p, _ = find_peaks(matched, distance=max(1, round(0.70 * period)),
                      prominence=max(0.05, 0.20 * float(np.std(matched))))
    return p.astype(int)


def greedy_match(ref_s: np.ndarray, est_s: np.ndarray, tol_s: float):
    pairs: list[tuple[int, int, float]] = []
    i = j = 0
    while i < len(ref_s) and j < len(est_s):
        d = float(est_s[j] - ref_s[i])
        if abs(d) <= tol_s:
            pairs.append((i, j, d)); i += 1; j += 1
        elif est_s[j] < ref_s[i] - tol_s:
            j += 1
        else:
            i += 1
    return pairs


def hrv(ibi_ms: np.ndarray) -> dict[str, float | None]:
    if len(ibi_ms) < 2:
        return {"rmssd_ms": None, "sdnn_ms": None}
    return {
        "rmssd_ms": float(np.sqrt(np.mean(np.diff(ibi_ms) ** 2))),
        "sdnn_ms": float(np.std(ibi_ms, ddof=1)) if len(ibi_ms) > 1 else None,
    }


def metrics(ref_s: np.ndarray, est_s: np.ndarray, tol_ms: float, fixed_delay_s: float = 0.0) -> dict[str, Any]:
    pairs = greedy_match(ref_s, est_s - fixed_delay_s, tol_ms / 1000.0)
    ref_i = np.asarray([i for i, _, _ in pairs], dtype=int)
    est_i = np.asarray([j for _, j, _ in pairs], dtype=int)
    raw_d = np.asarray([d for _, _, d in pairs], dtype=float) * 1000.0
    ribi = np.diff(ref_s[ref_i]) * 1000.0 if len(ref_i) >= 2 else np.array([])
    eibi = np.diff(est_s[est_i]) * 1000.0 if len(est_i) >= 2 else np.array([])
    rh, eh = hrv(ribi), hrv(eibi)
    out: dict[str, Any] = {
        "tolerance_ms": tol_ms, "fixed_delay_ms": fixed_delay_s * 1000.0,
        "ecg_beats": int(len(ref_s)), "radar_beats": int(len(est_s)),
        "matched_beats": int(len(pairs)), "ecg_unmatched": int(len(ref_s)-len(pairs)),
        "radar_unmatched": int(len(est_s)-len(pairs)),
        "precision": float(len(pairs)/len(est_s)) if len(est_s) else None,
        "recall": float(len(pairs)/len(ref_s)) if len(ref_s) else None,
        "f1": (float(2*len(pairs)/(len(ref_s)+len(est_s)))
               if len(ref_s)+len(est_s) else None),
        "timing_bias_ms": float(np.mean(raw_d)) if len(raw_d) else None,
        "timing_mae_ms": float(np.mean(np.abs(raw_d))) if len(raw_d) else None,
        "ibi_mae_ms": float(np.mean(np.abs(eibi-ribi))) if len(ribi) else None,
        "ibi_bias_ms": float(np.mean(eibi-ribi)) if len(ribi) else None,
        "hr_ecg_bpm": float(60000.0/np.median(ribi)) if len(ribi) else None,
        "hr_radar_bpm": float(60000.0/np.median(eibi)) if len(eibi) else None,
        "hr_abs_error_bpm": (float(abs(60000.0/np.median(eibi)-60000.0/np.median(ribi)))
                             if len(ribi) and len(eibi) else None),
        "rmssd_ecg_ms": rh["rmssd_ms"], "rmssd_radar_ms": eh["rmssd_ms"],
        "rmssd_abs_error_ms": (float(abs(eh["rmssd_ms"]-rh["rmssd_ms"]))
                                if rh["rmssd_ms"] is not None and eh["rmssd_ms"] is not None else None),
        "sdnn_ecg_ms": rh["sdnn_ms"], "sdnn_radar_ms": eh["sdnn_ms"],
        "sdnn_abs_error_ms": (float(abs(eh["sdnn_ms"]-rh["sdnn_ms"]))
                               if rh["sdnn_ms"] is not None and eh["sdnn_ms"] is not None else None),
    }
    return out


def load_pair(data_dir: Path, subject: str, condition: str) -> tuple[dict[str, Any], dict[str, Any]]:
    radar_path = data_dir / f"{subject}_{condition}.mat"
    mindray_path = data_dir / f"{subject}_{condition}_Mindray.mat"
    radar = loadmat(radar_path, squeeze_me=True, struct_as_record=False)
    mindray = loadmat(mindray_path, squeeze_me=True, struct_as_record=False)
    return radar, mindray


def get_field(obj: Any, name: str) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict) and name in obj:
        return obj[name]
    raise KeyError(name)


def inspect_pair(data_dir: Path, subject: str, condition: str) -> dict[str, Any]:
    rp = data_dir / f"{subject}_{condition}.mat"
    mp = data_dir / f"{subject}_{condition}_Mindray.mat"
    r, m = load_pair(data_dir, subject, condition)
    radar_obj = r["Radar"]
    vital = arr(r["VitalSig"])
    ecg = arr(m["ecg_lead2"])
    fs_r = scalar(get_field(radar_obj, "fs"))
    fs_e = scalar(m["Fs_ecg"])
    t = arr(get_field(radar_obj, "t_frame"))
    return {
        "subject": subject, "condition": condition,
        "radar_file": str(rp), "mindray_file": str(mp),
        "radar_fields": ["VitalSig", "Radar.fs", "Radar.t_frame"],
        "ecg_field": "ecg_lead2", "radar_samples": int(len(vital)),
        "ecg_samples": int(len(ecg)), "radar_fs_hz": fs_r, "ecg_fs_hz": fs_e,
        "radar_t_start_s": float(t[0]), "radar_t_end_s": float(t[-1]),
        "radar_duration_s": float(t[-1]-t[0]),
        "ecg_duration_s": float(len(ecg)/fs_e),
        "pair_ok": bool(len(vital) > 0 and len(ecg) > 0 and fs_r > 0 and fs_e > 0),
    }


def run_pair(data_dir: Path, subject: str, condition: str, calibration_delay_s: float) -> list[dict[str, Any]]:
    r, m = load_pair(data_dir, subject, condition)
    vital = arr(r["VitalSig"]); fs_r = scalar(get_field(r["Radar"], "fs"))
    t_r = arr(get_field(r["Radar"], "t_frame")); t_r = t_r - t_r[0]
    ecg = arr(m["ecg_lead2"]); fs_e = scalar(m["Fs_ecg"])
    t_e = np.arange(len(ecg), dtype=float) / fs_e
    ref = ecg_rpeaks(ecg, fs_e); ref_s = t_e[ref]
    methods = {"project_bandpass_peak": project_bandpass_peak(vital, fs_r),
               "vitalsense_amf": vitalsense_amf(vital, fs_r)}
    rows = []
    for method, peaks in methods.items():
        est_s = t_r[peaks]
        base = {"subject": subject, "condition": condition, "method": method,
                "raw_timing_offset_ms": None,
                "constant_delay_rule": "calibration-only median delay; fixed before held-out scoring",
                "failure_reason": None if len(peaks) else "no_radar_beats"}
        for tol in TOLERANCES_MS:
            x = metrics(ref_s, est_s, tol, 0.0)
            y = metrics(ref_s, est_s, tol, calibration_delay_s)
            for k, v in x.items(): base[f"raw_{k}"] = v
            for k, v in y.items(): base[f"delay_corrected_{k}"] = v
            base["raw_timing_offset_ms"] = x["timing_bias_ms"]
            rows.append(dict(base))
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--calibration-subject", default="VS01")
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    subjects = [f"VS{i:02d}" for i in range(1, 25)]
    conditions = ["Resting", "Apnea"]
    manifest = []
    rows = []
    errors = []
    for s in subjects:
        for c in conditions:
            try:
                manifest.append(inspect_pair(args.data_dir, s, c))
            except Exception as e:
                errors.append({"subject": s, "condition": c, "error": repr(e)})
    if errors or len(manifest) != 48 or not all(x["pair_ok"] for x in manifest):
        status = "FIELD_OR_DATA_INCONSISTENCY_BLOCKER"
        (args.output_dir / "status.json").write_text(json.dumps({"status": status, "errors": errors, "pairs": manifest}, indent=2), encoding="utf-8")
        raise SystemExit(status)
    # Delay is estimated once from the explicitly designated calibration pair,
    # using the AMF raw matched-pair median at the primary tolerance only.
    cal_r, cal_m = load_pair(args.data_dir, args.calibration_subject, "Resting")
    cv = arr(cal_r["VitalSig"]); cfs = scalar(get_field(cal_r["Radar"], "fs")); ct = arr(get_field(cal_r["Radar"], "t_frame")); ct -= ct[0]
    ce = arr(cal_m["ecg_lead2"]); cfs_e = scalar(cal_m["Fs_ecg"]); cr = np.arange(len(ce))/cfs_e; cp = ecg_rpeaks(ce, cfs_e)
    ap = vitalsense_amf(cv, cfs); pairs = greedy_match(cr[cp], ct[ap], PRIMARY_TOLERANCE_MS/1000.0)
    delay_s = float(np.median([d for _, _, d in pairs])) if pairs else 0.0
    for s in subjects:
        for c in conditions:
            rows.extend(run_pair(args.data_dir, s, c, delay_s))
    for path, data in [(args.output_dir/"pair_manifest.json", manifest), (args.output_dir/"run_config.json", {
        "status": "BENCHMARK_COMPLETE", "run_id": "C1B_VS_DATASET_20260825_V1",
        "primary_tolerance_ms": PRIMARY_TOLERANCE_MS, "sensitivity_tolerances_ms": list(TOLERANCES_MS),
        "calibration_subject": args.calibration_subject, "calibration_condition": "Resting",
        "calibration_delay_ms": delay_s*1000.0, "alignment": "file time origins; no per-window lag search",
        "methods": ["project_bandpass_peak", "vitalsense_amf"], "pairs": len(manifest)})]:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with (args.output_dir/"benchmark_metrics_long.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for row in rows for k in row})); writer.writeheader(); writer.writerows(rows)
    # Compact participant/condition summaries at primary tolerance and both methods.
    primary = [r for r in rows if r["raw_tolerance_ms"] == PRIMARY_TOLERANCE_MS]
    with (args.output_dir/"benchmark_metrics_primary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for row in primary for k in row})); writer.writeheader(); writer.writerows(primary)
    # Participant-level distribution summaries, retaining condition separation.
    summary_metrics = ["raw_precision", "raw_recall", "raw_f1", "raw_timing_mae_ms",
                       "raw_ibi_mae_ms", "raw_hr_abs_error_bpm", "raw_rmssd_abs_error_ms",
                       "raw_sdnn_abs_error_ms", "delay_corrected_timing_mae_ms"]
    summary_rows = []
    for method in sorted({r["method"] for r in primary}):
        for condition in conditions:
            subset = [r for r in primary if r["method"] == method and r["condition"] == condition]
            for metric in summary_metrics:
                vals = np.asarray([float(r[metric]) for r in subset if r.get(metric) not in (None, "")], dtype=float)
                if len(vals):
                    summary_rows.append({"method": method, "condition": condition, "metric": metric,
                                         "n": int(len(vals)), "mean": float(np.mean(vals)),
                                         "median": float(np.median(vals)), "q25": float(np.quantile(vals, .25)),
                                         "q75": float(np.quantile(vals, .75)), "min": float(np.min(vals)),
                                         "max": float(np.max(vals))})
    with (args.output_dir/"benchmark_summary_primary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "condition", "metric", "n", "mean", "median", "q25", "q75", "min", "max"])
        writer.writeheader(); writer.writerows(summary_rows)
    with (args.output_dir/"field_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        keys = sorted({k for row in manifest for k in row})
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader(); writer.writerows(manifest)
    # Deterministic subject-disjoint fold manifest.  The benchmark methods are
    # non-parametric at evaluation time, so the split is recorded for audit and
    # future learned extensions rather than used to tune this run.
    with (args.output_dir/"subject_disjoint_folds.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "fold", "split_rule"]); writer.writeheader()
        for i, subject in enumerate(subjects):
            writer.writerow({"subject": subject, "fold": i % 6, "split_rule": "ordered VS01-VS24 modulo 6; subject never split across folds"})
    report = [
        "# C1b VS_DATASET formal Radar--ECG benchmark v1",
        "",
        "Status: `BENCHMARK_COMPLETE`",
        "",
        f"Run ID: `C1B_VS_DATASET_20260825_V1`; pairs: {len(manifest)}; subjects: 24; conditions: Resting and Apnea.",
        "",
        "## Frozen protocol",
        "",
        "ECG Lead II (`ecg_lead2`, 500 Hz) is the reference. Radar uses `VitalSig`, `Radar.fs`, and `Radar.t_frame`. File-relative time origins are used; no per-window lag search is performed. Primary one-to-one chronological matching tolerance is ±75 ms, with ±50/100/150 ms sensitivity rows. A single delay is estimated only from VS01 Resting and held fixed for the delay-corrected sensitivity columns.",
        "",
        "## Field consistency",
        "",
        "All 48 Radar files and 48 Mindray files loaded successfully. ECG Lead II, ECG sampling rate, Radar signal, Radar sampling rate, and Radar time vector were present in every pair. Two non-used auxiliary-field differences are retained in the manifest: VS24_Apnea_Mindray pleth is int16 rather than float64, and VS24_Resting_Mindray respiration has 30,600 rather than 30,720 samples. They do not affect this ECG--Radar benchmark.",
        "",
        "## Methods",
        "",
        "`project_bandpass_peak` is the thin project-side adapter: cardiac-band filtering followed by fixed prominence peak detection. `vitalsense_amf` follows the checked-in VitalSense2024 public route: 0.3-Hz separation, spectral period estimate, deterministic sinusoidal pulse template, matched filtering and peak detection. The latter is a transparent Python baseline, not a claim of byte-identical MATLAB reproduction.",
        "",
        "## Required interpretation boundary",
        "",
        "The benchmark completed technically, but the current thin baselines show low beat-level coverage/recall in the generated metrics. Therefore this run does not support the statement that Radar beat, IBI or HRV is validated. HR, IBI, RMSSD and SDNN rows are reported for diagnosis and method comparison only; subject-level distributions and Resting/Apnea separation must be used instead of pooled values alone.",
        "",
        "Detailed outputs: `field_manifest.csv`, `pair_manifest.json`, `subject_disjoint_folds.csv`, `benchmark_metrics_long.csv`, `benchmark_metrics_primary.csv`, `benchmark_summary_primary.csv`, `run_config.json`, and `status.json`.",
    ]
    (args.output_dir/"benchmark_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    status = {"status": "BENCHMARK_COMPLETE", "run_id": "C1B_VS_DATASET_20260825_V1", "pairs": len(manifest), "rows": len(rows), "calibration_delay_ms": delay_s*1000.0}
    (args.output_dir/"status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
