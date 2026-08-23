"""Exploratory within-subject leave-one-window-out audit with RGB/NIR proxies."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


MM = ["rmssd_ms", "sdnn_ms", "hr_med_bpm", "z_rmssd", "n_peaks"]
VIS = ["rgb_motion", "rgb_luminance", "nir_pupil_dark_fraction", "nir_eye_contrast"]


def merge(mm_path: Path, cm_path: Path) -> list[dict]:
    with mm_path.open(encoding="utf-8-sig", newline="") as f: mm = list(csv.DictReader(f))
    with cm_path.open(encoding="utf-8-sig", newline="") as f: cm = list(csv.DictReader(f))
    cmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in cm}
    out = []
    for r in mm:
        key = (str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1))
        if key not in cmap: continue
        x = dict(r); x.update({k: v for k, v in cmap[key].items() if k not in {"subject", "onset_rel_s", "attention"}})
        try:
            if not all(np.isfinite(float(x[f])) for f in MM + VIS): continue
            x["subject"] = key[0]; x["attention"] = int(r["attention"])
            x["x"] = np.asarray([float(x[f]) for f in MM + VIS], float)
        except (KeyError, ValueError, TypeError): continue
        out.append(x)
    return out


def audit(rows: list[dict], negatives: set[int], feature_count: int) -> dict:
    keep = [r for r in rows if r["attention"] in {1, *negatives}]
    scores = []; labels = []; subjects = []
    for s in sorted({r["subject"] for r in keep}):
        rs = [r for r in keep if r["subject"] == s]
        y = np.asarray([int(r["attention"] == 1) for r in rs])
        if len(rs) < 4 or len(set(y)) < 2: continue
        X = np.asarray([r["x"][:feature_count] for r in rs])
        for j in range(len(rs)):
            tr = np.ones(len(rs), bool); tr[j] = False
            if len(set(y[tr])) < 2: continue
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
            model.fit(X[tr], y[tr]); scores.append(float(model.predict_proba(X[j:j + 1])[:, 1][0])); labels.append(int(y[j])); subjects.append(s)
    return {"n": len(labels), "subjects": len(set(subjects)), "auc": float(roc_auc_score(labels, scores)) if len(set(labels)) == 2 else None, "balanced_accuracy": float(balanced_accuracy_score(labels, np.asarray(scores) >= .5)) if labels else None}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--mmwave", type=Path, required=True); ap.add_argument("--crossmodal", type=Path, required=True); ap.add_argument("--output", type=Path, required=True); args = ap.parse_args()
    rows = merge(args.mmwave, args.crossmodal)
    result = {"n_windows": len(rows), "n_subjects": len({r["subject"] for r in rows}), "analyses": {}}
    for name, neg in (("focus_vs_all", {2, 3, 4}), ("focus_vs_mw", {3})):
        result["analyses"][name] = {"mmwave_only": audit(rows, neg, len(MM)), "mmwave_rgb_nir": audit(rows, neg, len(MM) + len(VIS))}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"); print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
