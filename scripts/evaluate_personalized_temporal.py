"""Temporal personalized calibration audit: early probes train, later probes test."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def run(rows, mask_fn):
    by = defaultdict(list)
    for r in rows: by[r["subject"]].append(r)
    y_all, s_all = [], []
    p_all, test_subjects = [], []
    pred_rows = []
    for s, rr in by.items():
        n = len(rr); cut = n // 2
        train, test = rr[:cut], rr[cut:]
        keep_train = [r for r in train if mask_fn(int(r["attention"]))]
        keep_test = [r for r in test if mask_fn(int(r["attention"]))]
        if len(keep_train) < 4 or len(set(int(r["attention"] == "1") for r in keep_train)) < 2 or not keep_test:
            continue
        names = [k for k in rr[0] if k not in ("subject", "attention")]
        Xtr = np.asarray([[float(r[k]) for k in names] for r in keep_train])
        ytr = np.asarray([int(r["attention"] == "1") for r in keep_train])
        Xte = np.asarray([[float(r[k]) for k in names] for r in keep_test])
        yte = np.asarray([int(r["attention"] == "1") for r in keep_test])
        med = np.nanmedian(Xtr, axis=0); Xtr = np.where(np.isfinite(Xtr), Xtr, med); Xte = np.where(np.isfinite(Xte), Xte, med)
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(Xtr, ytr)
        pp = model.predict_proba(Xte)[:, 1]
        p_all.extend(pp); y_all.extend(yte); s_all.extend([s] * len(yte)); test_subjects.append(s)
        pred_rows.extend({"subject": s, "y": int(a), "score": float(b)} for a, b in zip(yte, pp))
    y = np.asarray(y_all); p = np.asarray(p_all)
    return {"n_test_windows": len(y), "n_test_subjects": len(test_subjects), "subjects": test_subjects, "predictions": pred_rows,
            "auc": float(roc_auc_score(y, p)) if len(y) and len(set(y)) == 2 else None,
            "balanced_accuracy": float(balanced_accuracy_score(y, p >= .5)) if len(y) else None}


def subject_bootstrap(result, reps=1000, seed=19):
    pred = result.get("predictions", [])
    by = defaultdict(list)
    for r in pred: by[r["subject"]].append(r)
    subs = sorted(by)
    if len(subs) < 2: return None
    rng = np.random.default_rng(seed); aucs=[]; baccs=[]
    for _ in range(reps):
        chosen = rng.choice(subs, size=len(subs), replace=True)
        pp = [r for s in chosen for r in by[s]]
        y = np.asarray([r["y"] for r in pp]); score = np.asarray([r["score"] for r in pp])
        if len(set(y)) < 2: continue
        aucs.append(roc_auc_score(y, score)); baccs.append(balanced_accuracy_score(y, score >= .5))
    q = lambda a: [float(np.quantile(a, .025)), float(np.quantile(a, .5)), float(np.quantile(a, .975))] if a else None
    return {"n_bootstrap": len(aucs), "auc_2.5_50_97.5": q(aucs), "balanced_accuracy_2.5_50_97.5": q(baccs)}


def main():
    rows = list(csv.DictReader((OUT / "rich_focus_features.csv").open(encoding="utf-8-sig")))
    analyses = {
        "focus_vs_all_nonfocus": run(rows, lambda a: True),
        "focus_vs_mind_wandering": run(rows, lambda a: a in (1, 3)),
    }
    for value in analyses.values(): value["subject_bootstrap"] = subject_bootstrap(value); value.pop("predictions", None)
    out = {"n_windows": len(rows), "n_subjects": len(set(r["subject"] for r in rows)),
           "calibration_order": "first half of each subject by probe onset; test is second half",
           "analyses": analyses, "note": "Exploratory temporal personalized audit; subjects without both classes in calibration are excluded."}
    (OUT / "personalized_temporal_lopo.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
