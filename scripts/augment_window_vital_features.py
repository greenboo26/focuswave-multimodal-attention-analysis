"""Add window-level breath and HR quality features from processed vital NPZs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import signal


def peak_seconds(peaks: np.ndarray, t: np.ndarray) -> np.ndarray:
    p = np.asarray(peaks, float).ravel()
    if p.size and np.nanmax(p) > np.nanmax(t) + 1:
        p = t[np.clip(p.astype(int), 0, len(t) - 1)]
    return p


def augment(row: dict, npz_path: Path) -> dict:
    d = np.load(npz_path, allow_pickle=True)
    t = np.asarray(d["t"], float)
    end = float(row["onset_rel_s"]); start = end - 60.0
    bp = peak_seconds(d.get("breath_peaks", []), t)
    in_breath = bp[(bp > start) & (bp <= end)]
    breath_intervals = np.diff(in_breath)
    valid_breath_intervals = breath_intervals[(breath_intervals >= 1.5) & (breath_intervals <= 10.0)]
    row["breath_rate_bpm"] = (float(60.0 / np.mean(valid_breath_intervals))
                               if len(valid_breath_intervals) else np.nan)
    bt = t[(t > start) & (t <= end)]
    bs = np.asarray(d.get("breath", []), float)
    bsv = bs[(t > start) & (t <= end)] if len(bs) == len(t) else np.asarray([])
    spectral_br_raw = np.nan
    if len(bsv) >= 300:
        fs = 1.0 / float(np.median(np.diff(bt)))
        freqs, power = signal.periodogram(signal.detrend(bsv), fs=fs, window="hann")
        mask = (freqs >= 0.1) & (freqs <= 0.5) & np.isfinite(power)
        if np.any(mask):
            spectral_br_raw = float(freqs[mask][np.argmax(power[mask])] * 60.0)
    spectral_br = spectral_br_raw
    harmonic_correction = False
    if np.isfinite(spectral_br_raw) and spectral_br_raw < 12.0 and spectral_br_raw * 2.0 <= 30.0:
        spectral_br = spectral_br_raw * 2.0
        harmonic_correction = True
    row["breath_rate_spectral_raw_bpm"] = spectral_br_raw
    row["breath_rate_spectral_bpm"] = spectral_br
    row["breath_rate_harmonic_correction"] = harmonic_correction
    row["breath_rate_time_freq_gap_bpm"] = abs(float(row["breath_rate_bpm"]) - spectral_br) if np.isfinite(row["breath_rate_bpm"]) and np.isfinite(spectral_br) else np.nan
    ht = np.asarray(d.get("hr_course_time_s", []), float)
    def window_value(key: str, finite: bool = True):
        v = np.asarray(d.get(key, []), float)
        mask = (ht > start) & (ht <= end) & (np.isfinite(v) if finite else True)
        return float(np.median(v[mask])) if np.any(mask) else np.nan
    row["hr_time_freq_gap_bpm"] = window_value("hr_course_time_freq_gap_bpm")
    row["hr_signal_usable_ratio"] = window_value("hr_course_signal_usable", finite=False)
    row["hr_confidence"] = window_value("hr_course_confidence")
    row["hr_signal_std_10s_mm"] = window_value("hr_course_signal_std_10s_mm")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--npz-root", type=Path, required=True)
    args = ap.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        subject = str(row["subject"]).zfill(3)
        npz = args.npz_root / f"sub-{subject}_" / f"sub-{subject}_ses-SART_mmwave_vital_signs.npz"
        if npz.exists():
            row = augment(row, npz)
        else:
            for key in ("breath_rate_bpm", "breath_rate_spectral_raw_bpm", "breath_rate_spectral_bpm", "breath_rate_harmonic_correction", "breath_rate_time_freq_gap_bpm", "hr_time_freq_gap_bpm", "hr_signal_usable_ratio", "hr_confidence", "hr_signal_std_10s_mm"):
                row[key] = np.nan
        out.append(row)
    fields = list(out[0]) if out else []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    print(json.dumps({"rows": len(out), "subjects": len({r["subject"] for r in out}), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__": main()
