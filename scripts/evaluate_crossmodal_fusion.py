"""LOPO audit for timestamp-gated mmWave + RGB/NIR exploratory features."""

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


MMWAVE = ["rmssd_ms", "sdnn_ms", "hr_med_bpm", "z_rmssd", "n_peaks"]
VISION = ["rgb_motion", "rgb_luminance", "nir_pupil_dark_fraction", "nir_eye_contrast"]


def lopo(rows: list[dict], features: list[str], positive: int, negative: set[int]) -> dict:
    d = []
    for row in rows:
        attention = int(row["attention"])
        if attention not in {positive, *negative}:
            continue
        try:
            x = [float(row[f]) for f in features]
        except (KeyError, TypeError, ValueError):
            continue
        if not np.all(np.isfinite(x)):
            continue
        d.append({"subject": row["subject"], "x": x, "y": int(attention == positive)})
    y_true, y_score, y_pred, subjects = [], [], [], []
    for subject in sorted({r["subject"] for r in d}):
        train = [r for r in d if r["subject"] != subject]
        test = [r for r in d if r["subject"] == subject]
        if len({r["y"] for r in train}) < 2 or not test:
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(np.asarray([r["x"] for r in train]), np.asarray([r["y"] for r in train]))
        score = model.predict_proba(np.asarray([r["x"] for r in test]))[:, 1]
        y_true.extend([r["y"] for r in test])
        y_score.extend(score.tolist())
        y_pred.extend((score >= 0.5).astype(int).tolist())
        subjects.extend([subject] * len(test))
    result = {
        "n": len(y_true),
        "subjects": len(set(subjects)),
        "features": features,
        "auc": float(roc_auc_score(y_true, y_score)) if len(set(y_true)) == 2 else None,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)) if y_true else None,
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmwave", type=Path, required=True)
    ap.add_argument("--crossmodal", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    with args.mmwave.open("r", encoding="utf-8-sig", newline="") as f:
        mm = list(csv.DictReader(f))
    with args.crossmodal.open("r", encoding="utf-8-sig", newline="") as f:
        cm = list(csv.DictReader(f))
    cm_map = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in cm}
    df = []
    for r in mm:
        key = (str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1))
        if key in cm_map:
            merged = dict(r)
            merged.update({k: v for k, v in cm_map[key].items() if k not in {"subject", "onset_rel_s", "attention"}})
            df.append(merged)
    analyses = {}
    for name, pos, neg in (("focus_vs_all", 1, {2, 3, 4}), ("focus_vs_mw", 1, {3})):
        analyses[name] = {
            "mmwave_only": lopo(df, MMWAVE, pos, neg),
            "rgb_nir_only": lopo(df, VISION, pos, neg),
            "mmwave_rgb_nir": lopo(df, MMWAVE + VISION, pos, neg),
        }
    result = {
        "n_matched_windows": int(len(df)),
        "n_subjects": int(len({str(r["subject"]).zfill(3) for r in df})),
        "gate": "Only windows already present in behavior-gated focus_discrimination.csv; RGB/NIR samples are inside the same 60 s window.",
        "feature_warning": "NIR is a dark-core/contrast pupil proxy, not calibrated pupil diameter; RGB is luminance/motion proxy, not a face landmark model.",
        "analyses": analyses,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
