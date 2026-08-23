"""Evaluate mmWave features against aligned objective SART behavior outcomes."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu, spearmanr

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def corr(rows, xkey, ykey, subject_level=False):
    if subject_level:
        by = defaultdict(lambda: defaultdict(list))
        for r in rows:
            by[r["subject"]][xkey].append(num(r[xkey]))
            by[r["subject"]][ykey].append(num(r[ykey]))
        xx, yy = [], []
        for d in by.values():
            x = np.asarray(d[xkey], float); y = np.asarray(d[ykey], float)
            x = x[np.isfinite(x)]; y = y[np.isfinite(y)]
            if x.size and y.size:
                xx.append(float(np.median(x))); yy.append(float(np.median(y)))
    else:
        xx = [num(r[xkey]) for r in rows]; yy = [num(r[ykey]) for r in rows]
        keep = np.isfinite(xx) & np.isfinite(yy)
        xx, yy = np.asarray(xx)[keep], np.asarray(yy)[keep]
    if len(xx) < 4 or len(set(xx)) < 2 or len(set(yy)) < 2:
        return {"rho": None, "p": None, "n": int(len(xx))}
    rho, p = spearmanr(xx, yy)
    return {"rho": float(rho), "p": float(p), "n": int(len(xx))}


def main():
    mm = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
    beh = list(csv.DictReader((OUT / "behavior_probe_windows.csv").open(encoding="utf-8-sig")))
    by = defaultdict(list)
    for r in beh:
        by[r["subject"]].append(r)
    merged = []
    for r in mm:
        candidates = by.get(r["subject"], [])
        if not candidates:
            continue
        onset = num(r["onset_rel_s"])
        best = min(candidates, key=lambda x: abs(num(x["onset_rel_s"]) - onset))
        if abs(num(best["onset_rel_s"]) - onset) > 2.0:
            continue
        merged.append({**r, **{f"beh_{k}": v for k, v in best.items() if k not in ("subject", "onset_rel_s", "attention", "vigilance")}})
    with (OUT / "mmwave_behavior_criterion_windows.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = list(merged[0]) if merged else ["subject"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(merged)

    features = ["hr_med_bpm", "rmssd_ms", "z_rmssd", "n_peaks"]
    outcomes = ["beh_accuracy", "beh_commission_rate", "beh_omission_rate", "beh_rt_median_ms"]
    result = {"n_matched_windows": len(merged), "n_subjects": len(set(r["subject"] for r in merged)), "correlations": {}}
    for fkey in features:
        for okey in outcomes:
            result["correlations"][f"{fkey}__{okey}"] = {
                "window_level": corr(merged, fkey, okey, False),
                "subject_level": corr(merged, fkey, okey, True),
            }

    groups = {label: [num(r["beh_accuracy"]) for r in merged if r["attention"] == label and np.isfinite(num(r["beh_accuracy"]))] for label in ("1", "3")}
    if all(groups[k] for k in groups):
        u, p = mannwhitneyu(groups["1"], groups["3"], alternative="two-sided")
        pooled = np.sqrt((np.var(groups["1"], ddof=1) + np.var(groups["3"], ddof=1)) / 2)
        result["behavior_accuracy_focus_vs_mw"] = {"n_focus": len(groups["1"]), "n_mw": len(groups["3"]), "u": float(u), "p": float(p), "cohens_d": float((np.mean(groups["1"]) - np.mean(groups["3"])) / pooled) if pooled else None}
    result["note"] = "Criterion analysis only; behavior outcomes are not model inputs, and window-level p-values are exploratory because windows repeat within subjects."
    (OUT / "mmwave_behavior_criterion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
