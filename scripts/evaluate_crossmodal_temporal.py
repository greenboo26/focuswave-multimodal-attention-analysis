"""Temporal personalized audit for timestamp-gated mmWave/RGB/NIR features."""

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


def load_merge(mm_path: Path, cm_path: Path) -> list[dict]:
    with mm_path.open("r", encoding="utf-8-sig", newline="") as f:
        mm = list(csv.DictReader(f))
    with cm_path.open("r", encoding="utf-8-sig", newline="") as f:
        cm = list(csv.DictReader(f))
    cmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in cm}
    rows = []
    for r in mm:
        key = (str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1))
        if key not in cmap:
            continue
        x = dict(r)
        x.update({k: v for k, v in cmap[key].items() if k not in {"subject", "onset_rel_s", "attention"}})
        try:
            x["attention"] = int(r["attention"])
            x["onset_rel_s"] = float(r["onset_rel_s"])
            for f_name in MM + VIS:
                x[f_name] = float(x[f_name])
        except (KeyError, ValueError, TypeError):
            continue
        if all(np.isfinite(x[f_name]) for f_name in MM + VIS):
            x["subject"] = key[0]
            rows.append(x)
    return rows


def run(rows: list[dict], features: list[str], negatives: set[int]) -> dict:
    groups = {}
    for r in rows:
        if r["attention"] in {1, *negatives}:
            groups.setdefault(r["subject"], []).append(r)
    train_rows, test_rows = [], []
    for subject, rs in groups.items():
        rs = sorted(rs, key=lambda x: x["onset_rel_s"])
        split = max(1, len(rs) // 2)
        cal = rs[:split]
        test = rs[split:]
        if not test:
            continue
        mu = np.mean(np.asarray([[r[f] for f in features] for r in cal]), axis=0)
        sd = np.std(np.asarray([[r[f] for f in features] for r in cal]), axis=0)
        sd[sd < 1e-8] = 1.0
        for r in cal:
            rr = dict(r); rr["x"] = ((np.asarray([r[f] for f in features]) - mu) / sd).tolist(); train_rows.append(rr)
        for r in test:
            rr = dict(r); rr["x"] = ((np.asarray([r[f] for f in features]) - mu) / sd).tolist(); test_rows.append(rr)
    y_true, y_score, y_pred, test_subjects = [], [], [], []
    for subject in sorted({r["subject"] for r in test_rows}):
        train = [r for r in train_rows if r["subject"] != subject]
        test = [r for r in test_rows if r["subject"] == subject]
        if len({r["attention"] == 1 for r in train}) < 2 or not test:
            continue
        y_train = np.asarray([int(r["attention"] == 1) for r in train])
        y_test = np.asarray([int(r["attention"] == 1) for r in test])
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(np.asarray([r["x"] for r in train]), y_train)
        score = model.predict_proba(np.asarray([r["x"] for r in test]))[:, 1]
        y_true.extend(y_test.tolist()); y_score.extend(score.tolist()); y_pred.extend((score >= .5).astype(int).tolist()); test_subjects.extend([subject] * len(test))
    return {
        "n_test": len(y_true),
        "subjects": len(set(test_subjects)),
        "auc": float(roc_auc_score(y_true, y_score)) if len(set(y_true)) == 2 else None,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)) if y_true else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmwave", type=Path, required=True)
    ap.add_argument("--crossmodal", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = load_merge(args.mmwave, args.crossmodal)
    results = {}
    for name, negatives in (("focus_vs_all", {2, 3, 4}), ("focus_vs_mw", {3})):
        results[name] = {
            "mmwave_only": run(rows, MM, negatives),
            "rgb_nir_only": run(rows, VIS, negatives),
            "mmwave_rgb_nir": run(rows, MM + VIS, negatives),
        }
    result = {"n_rows": len(rows), "n_subjects": len({r["subject"] for r in rows}), "split": "first half calibration, second half independent test", "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
