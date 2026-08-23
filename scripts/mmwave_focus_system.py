"""Conservative research prototype for mmWave attention-state inference.

Input is one processed vital-signs NPZ from the project pipeline. The system
returns heart rate, optional exploratory HRV, quality gates, and a research
attention score. It deliberately emits ``indeterminate`` when signal quality
is insufficient and never presents the score as a diagnosis.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from scipy import signal


MODEL_DEFAULT = Path(r"D:\Project\厚粲杯\08_算法\output\Formal_mmwave_FAST\formal_attention_model.json")


def _seconds_from_peaks(peaks, t):
    p = np.asarray(peaks, float).ravel()
    if p.size == 0:
        return p
    # Pipeline versions have stored either sample indices or seconds.
    if np.nanmax(p) > np.nanmax(t) + 1:
        p = t[np.clip(p.astype(int), 0, len(t) - 1)]
    return p


def _window_peaks(peaks, start, end):
    return peaks[(peaks > start) & (peaks <= end)]


def extract_window(npz_path: Path, end_s: float, window_s: float = 60.0,
                   baseline_rmssd_ms: float | None = None,
                   allow_experimental_hrv: bool = False):
    d = np.load(npz_path, allow_pickle=True)
    t = np.asarray(d["t"], float)
    hp = _seconds_from_peaks(d.get("heart_peaks", []), t)
    bp = _seconds_from_peaks(d.get("breath_peaks", []), t)
    start = end_s - window_s
    p = _window_peaks(hp, start, end_s)
    ibi = np.diff(p)
    valid = np.isfinite(ibi) & (ibi >= 0.30) & (ibi <= 2.00)
    valid_ibi = ibi[valid]
    n_intervals = int(len(ibi))
    valid_ratio = float(valid.sum() / n_intervals) if n_intervals else 0.0
    hr = float(60.0 / np.median(valid_ibi)) if len(valid_ibi) >= 3 else None
    rmssd = float(np.sqrt(np.mean(np.diff(valid_ibi) ** 2)) * 1000.0) if len(valid_ibi) >= 3 else None
    sdnn = float(np.std(valid_ibi, ddof=1) * 1000.0) if len(valid_ibi) >= 3 else None

    # Respiration: report both peak-interval and spectral estimates. The
    # synchronized reference audit showed the spectral estimate is less
    # sensitive to missed breath peaks, but it remains research-grade.
    bp_w = _window_peaks(bp, start, end_s)
    breath_intervals = np.diff(bp_w)
    valid_breath_intervals = breath_intervals[(breath_intervals >= 1.5) & (breath_intervals <= 10.0)]
    breath_peak_bpm = (float(60.0 / np.mean(valid_breath_intervals))
                       if len(valid_breath_intervals) else None)
    breath = np.asarray(d.get("breath", []), float)
    breath_mask = (t > start) & (t <= end_s)
    breath_w = breath[breath_mask] if len(breath) == len(t) else np.array([])
    breath_spectral_raw_bpm = None
    if len(breath_w) >= 300:
        fs = 1.0 / float(np.median(np.diff(t[breath_mask])))
        freqs, power = signal.periodogram(signal.detrend(breath_w), fs=fs, window="hann")
        mask = (freqs >= 0.1) & (freqs <= 0.5) & np.isfinite(power)
        if np.any(mask):
            breath_spectral_raw_bpm = float(freqs[mask][np.argmax(power[mask])] * 60.0)
    breath_spectral_bpm = breath_spectral_raw_bpm
    breath_harmonic_correction = False
    if breath_spectral_raw_bpm is not None and breath_spectral_raw_bpm < 12.0 and breath_spectral_raw_bpm * 2.0 <= 30.0:
        breath_spectral_bpm = breath_spectral_raw_bpm * 2.0
        breath_harmonic_correction = True
    breath_gap = abs(breath_peak_bpm - breath_spectral_bpm) if breath_peak_bpm is not None and breath_spectral_bpm is not None else None
    breath_quality = (
        ("research_harmonic_corrected" if breath_harmonic_correction else "usable_for_br")
        if breath_spectral_bpm is not None
        and 6 <= breath_spectral_bpm <= 30
        and (breath_gap is None or breath_gap <= 8)
        else "review_required"
    )

    ht = np.asarray(d.get("hr_course_time_s", []), float)
    hc = np.asarray(d.get("hr_course_fused_bpm", []), float)
    hm = hc[(ht > start) & (ht <= end_s) & np.isfinite(hc)] if len(ht) else np.array([])
    hr_course = float(np.median(hm)) if len(hm) else hr
    gap = np.asarray(d.get("hr_course_time_freq_gap_bpm", []), float)
    gm = gap[(ht > start) & (ht <= end_s) & np.isfinite(gap)] if len(ht) else np.array([])
    agreement_gap = float(np.median(gm)) if len(gm) else None
    usable = np.asarray(d.get("hr_course_signal_usable", []), float)
    um = usable[(ht > start) & (ht <= end_s) & np.isfinite(usable)] if len(ht) else np.array([])
    usable_ratio = float(np.mean(um > 0)) if len(um) else None

    flags = []
    if hr is None or not (40 <= hr <= 120):
        flags.append("heart_rate_out_of_range")
    if len(p) < 35 or len(p) > 150:
        flags.append("peak_count_unusual")
    if valid_ratio < 0.80:
        flags.append("ibi_valid_ratio_low")
    if hr_course is None:
        flags.append("no_hr_course")
    if agreement_gap is not None and agreement_gap > 10:
        flags.append("time_frequency_disagreement")
    if usable_ratio is not None and usable_ratio < 0.80:
        flags.append("signal_usable_ratio_low")
    quality = "usable_for_hr" if not flags else "review_required"
    raw_rmssd = rmssd
    hrv_status = "exploratory_unvalidated"
    if allow_experimental_hrv and rmssd is not None and not flags:
        hrv_status = "exploratory_window_hrv"
    else:
        rmssd = None
        sdnn = None

    return {
        "window_end_s": float(end_s), "window_s": float(window_s),
        "heart_rate_bpm": hr, "heart_rate_course_bpm": hr_course,
        "heart_rate_quality": "usable_for_hr" if not flags else "review_required",
        "breath_rate_bpm": breath_spectral_bpm,
        "breath_rate_peak_bpm": breath_peak_bpm,
        "breath_rate_spectral_raw_bpm": breath_spectral_raw_bpm,
        "breath_rate_spectral_bpm": breath_spectral_bpm,
        "breath_rate_harmonic_correction": breath_harmonic_correction,
        "breath_rate_time_frequency_gap_bpm": breath_gap,
        "breath_quality": breath_quality,
        "rmssd_ms": rmssd, "sdnn_ms": sdnn, "hrv_status": hrv_status,
        "hr_calculable": bool(hr is not None),
        "br_calculable": bool(breath_spectral_bpm is not None),
        "hrv_calculable": bool(raw_rmssd is not None),
        "rmssd_raw_ms": raw_rmssd,
        "n_peaks": int(len(p)), "n_intervals": n_intervals,
        "ibi_valid_ratio": valid_ratio, "hr_course_agreement_gap_bpm": agreement_gap,
        "signal_usable_ratio": usable_ratio, "quality": quality, "quality_flags": flags,
    }


def add_attention_score(feature_row, session_hr_median, baseline_rmssd_ms, model_path=MODEL_DEFAULT):
    model = json.loads(Path(model_path).read_text(encoding="utf-8"))
    x = np.asarray([
        feature_row["heart_rate_bpm"] - session_hr_median,
        (feature_row["rmssd_raw_ms"] - baseline_rmssd_ms) / max(1.0, baseline_rmssd_ms),
        feature_row["n_peaks"],
    ], float)
    mu = np.asarray(model["mean"], float)
    sd = np.asarray(model["scale"], float)
    w = np.asarray(model["weights_intercept_first"], float)
    score = float(expit(np.r_[1.0, (x - mu) / np.maximum(sd, 1e-9)] @ w))
    if feature_row["quality"] != "usable_for_hr":
        decision = "indeterminate"
    elif score >= 0.65:
        decision = "research_focused"
    elif score <= 0.35:
        decision = "research_nonfocused"
    else:
        decision = "indeterminate"
    return {"research_focus_probability": score, "research_decision": decision,
            "decision_warning": "not validated for deployment or diagnosis"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz", type=Path)
    ap.add_argument("--end-s", type=float, required=True)
    ap.add_argument("--baseline-rmssd-ms", type=float, default=300.0)
    ap.add_argument("--session-hr-median", type=float, default=80.0)
    ap.add_argument("--allow-experimental-hrv", action="store_true")
    ap.add_argument("--model", type=Path, default=MODEL_DEFAULT)
    args = ap.parse_args()
    row = extract_window(args.npz, args.end_s, baseline_rmssd_ms=args.baseline_rmssd_ms,
                         allow_experimental_hrv=args.allow_experimental_hrv)
    raw_rmssd = row["rmssd_raw_ms"]
    if args.allow_experimental_hrv and raw_rmssd is not None and row["heart_rate_bpm"] is not None:
        row.update(add_attention_score(row, args.session_hr_median, args.baseline_rmssd_ms, args.model))
    else:
        row.update({"research_focus_probability": None, "research_decision": "indeterminate",
                    "decision_warning": "experimental HRV scoring is disabled; use --allow-experimental-hrv for research-only scoring"})
    print(json.dumps(row, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
