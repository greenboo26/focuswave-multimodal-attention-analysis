"""Compare mmWave-only, behavior-only and exploratory fusion models."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"

MM = ["hr_med_bpm", "rmssd_ms", "z_rmssd", "n_peaks"]
BEH = ["beh_accuracy", "beh_commission_rate", "beh_omission_rate", "beh_rt_median_ms", "beh_rt_sd_ms"]


def evaluate(rows, features, mode):
    use = [r for r in rows if r["attention"] in ("1", "2", "3", "4")]
    y = np.array([int(r["attention"] == "1") for r in use])
    groups = np.array([r["subject"] for r in use])
    X = np.array([[float(r.get(k, "nan")) for k in features] for r in use])
    scores = np.full(len(use), np.nan)
    for held in sorted(set(groups)):
        tr, te = groups != held, groups == held
        if tr.sum() == 0 or len(set(y[tr])) < 2 or not te.any():
            continue
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(X[tr], y[tr]); scores[te] = model.predict_proba(X[te])[:, 1]
    good = np.isfinite(scores)
    if good.sum() == 0 or len(set(y[good])) < 2:
        return {"mode": mode, "n": int(good.sum()), "n_subjects": int(len(set(groups[good]))), "auc": None, "balanced_accuracy": None}
    return {"mode": mode, "n": int(good.sum()), "n_subjects": int(len(set(groups[good]))), "auc": float(roc_auc_score(y[good], scores[good])), "balanced_accuracy": float(balanced_accuracy_score(y[good], scores[good] >= 0.5))}


def main():
    rows = list(csv.DictReader((OUT / "mmwave_behavior_criterion_windows.csv").open(encoding="utf-8-sig")))
    result = {"n_windows": len(rows), "n_subjects": len(set(r["subject"] for r in rows)), "features": {"mmwave": MM, "behavior": BEH}}
    for scope, subset in [("focus_vs_all_nonfocus", rows), ("focus_vs_mind_wandering", [r for r in rows if r["attention"] in ("1", "3")])]:
        result[scope] = [evaluate(subset, MM, "mmwave_only"), evaluate(subset, BEH, "behavior_only"), evaluate(subset, MM + BEH, "fusion_exploratory")]
    result["note"] = "Fusion is an exploratory multimodal upper-bound comparison. Behavior features are not used by the mmWave-only runtime system and the result is not a pure mmWave deployment claim."
    (OUT / "mmwave_behavior_fusion_lopo.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
