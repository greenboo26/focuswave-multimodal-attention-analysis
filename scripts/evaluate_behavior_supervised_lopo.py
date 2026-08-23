"""Test whether mmWave/RGB/NIR features predict objective SART performance."""

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
BEHAVIOR = ["accuracy", "commission_rate", "omission_rate", "no_go_accuracy", "rt_median_ms", "rt_sd_ms"]


def read(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def merged(mm_path: Path, behavior_path: Path, cm_path: Path, accuracy_threshold: float) -> list[dict]:
    mm = read(mm_path); beh = read(behavior_path); cm = read(cm_path)
    bmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in beh}
    cmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in cm}
    rows = []
    for r in mm:
        key = (str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1))
        if key not in bmap or key not in cmap:
            continue
        x = dict(r); x.update({k: v for k, v in cmap[key].items() if k not in {"subject", "onset_rel_s", "attention"}}); x.update(bmap[key])
        try:
            x["subject"] = key[0]; x["y"] = int(float(x["accuracy"]) < accuracy_threshold)
            for f_name in MM + VIS:
                x[f_name] = float(x[f_name])
        except (KeyError, ValueError, TypeError):
            continue
        if all(np.isfinite(x[f_name]) for f_name in MM + VIS):
            rows.append(x)
    return rows


def lopo(rows: list[dict], features: list[str]) -> dict:
    y_true, scores, preds, subjects = [], [], [], []
    for subject in sorted({r["subject"] for r in rows}):
        train = [r for r in rows if r["subject"] != subject]
        test = [r for r in rows if r["subject"] == subject]
        if len({r["y"] for r in train}) < 2 or not test:
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(np.asarray([[r[f] for f in features] for r in train]), np.asarray([r["y"] for r in train]))
        score = model.predict_proba(np.asarray([[r[f] for f in features] for r in test]))[:, 1]
        y_true.extend([r["y"] for r in test]); scores.extend(score.tolist()); preds.extend((score >= .5).astype(int).tolist()); subjects.extend([subject] * len(test))
    return {"n": len(y_true), "subjects": len(set(subjects)), "positive_rate": float(np.mean(y_true)) if y_true else None, "auc": float(roc_auc_score(y_true, scores)) if len(set(y_true)) == 2 else None, "balanced_accuracy": float(balanced_accuracy_score(y_true, preds)) if y_true else None, "features": features}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmwave", type=Path, required=True)
    ap.add_argument("--behavior", type=Path, required=True)
    ap.add_argument("--crossmodal", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--accuracy-threshold", type=float, default=.95)
    args = ap.parse_args()
    rows = merged(args.mmwave, args.behavior, args.crossmodal, args.accuracy_threshold)
    result = {"n_windows": len(rows), "n_subjects": len({r["subject"] for r in rows}), "target": f"accuracy < {args.accuracy_threshold}", "target_is_behavior_only": True, "analyses": {"mmwave_only": lopo(rows, MM), "rgb_nir_only": lopo(rows, VIS), "mmwave_rgb_nir": lopo(rows, MM + VIS)}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
