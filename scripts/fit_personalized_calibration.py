"""Fit a subject-specific research calibration model from labeled probe windows."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("output", type=Path)
    ap.add_argument("--csv", type=Path, default=Path(r"D:\Project\厚粲杯\08_算法\output\E_Data_FAST\focus_discrimination.csv"))
    ap.add_argument("--aligned-json", type=Path, default=Path(r"D:\Project\厚粲杯\08_算法\output\E_Data_FAST\focus_discrimination.json"))
    args = ap.parse_args()
    rows = [r for r in csv.DictReader(args.csv.open(encoding="utf-8-sig")) if r["subject"] == args.subject]
    meta = json.loads(args.aligned_json.read_text(encoding="utf-8"))
    sm = next(s for s in meta["subjects"] if s["subject"] == args.subject)
    baseline = float(sm.get("baseline_rmssd_ms") or 300.0)
    hr_values = np.asarray([float(r["hr_med_bpm"]) for r in rows], float)
    session_hr = float(np.median(hr_values))
    X = np.asarray([[float(r["hr_med_bpm"]) - session_hr,
                     (float(r["rmssd_ms"]) - baseline) / max(1.0, baseline),
                     float(r["n_peaks"])] for r in rows], float)
    y = np.asarray([int(r["attention"] == "1") for r in rows], int)
    if len(rows) < 8 or len(set(y)) < 2:
        raise SystemExit(f"subject {args.subject}: need at least 8 windows and both classes")
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
    model.fit(X, y)
    scaler = model.named_steps["standardscaler"]; clf = model.named_steps["logisticregression"]
    w = clf.coef_[0]; intercept = float(clf.intercept_[0])
    out = {"subject": args.subject, "features": ["hr_delta", "rmssd_z", "n_peaks"],
           "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
           "weights_intercept_first": [intercept, *w.tolist()],
           "session_hr_median_bpm": session_hr, "baseline_rmssd_ms": baseline,
           "training_n_windows": len(rows), "training_positive_n": int(y.sum()),
           "warning": "Research calibration only; requires held-out labeled probes and is not deployment validation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
