"""Within-subject leave-one-window-out audit for the rich mmWave features."""
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


def audit(X, y, subjects, mask):
    X, y, subjects = X[mask], y[mask], subjects[mask]
    scores = np.full(len(y), np.nan)
    for s in sorted(set(subjects)):
        ix = np.flatnonzero(subjects == s)
        if len(ix) < 4 or len(set(y[ix])) < 2:
            continue
        for j in ix:
            tr = ix[ix != j]
            if len(set(y[tr])) < 2:
                continue
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
            model.fit(X[tr], y[tr])
            scores[j] = model.predict_proba(X[j:j + 1])[:, 1][0]
    keep = np.isfinite(scores)
    if not np.any(keep): return {"n": 0, "n_subjects": 0, "auc": None, "balanced_accuracy": None}
    pred = (scores[keep] >= .5).astype(int)
    return {"n": int(np.sum(keep)), "n_subjects": int(len(set(subjects[keep]))),
            "auc": float(roc_auc_score(y[keep], scores[keep])) if len(set(y[keep])) == 2 else None,
            "balanced_accuracy": float(balanced_accuracy_score(y[keep], pred))}


def main():
    rows = list(csv.DictReader((OUT / "rich_focus_features.csv").open(encoding="utf-8-sig")))
    names = [k for k in rows[0] if k not in ("subject", "attention")]
    X = np.asarray([[float(r[k]) for k in names] for r in rows], float)
    y0 = np.asarray([int(r["attention"]) for r in rows]); subjects = np.asarray([r["subject"] for r in rows])
    out = {"n_windows": len(rows), "n_subjects": len(set(subjects)), "analyses": {
        "focus_vs_all_nonfocus": audit(X, (y0 == 1).astype(int), subjects, np.ones(len(y0), bool)),
        "focus_vs_mind_wandering": audit(X, (y0 == 1).astype(int), subjects, np.isin(y0, [1, 3])),
    }, "note": "Leave-one-window-out within each subject; exploratory and not a substitute for external validation."}
    (OUT / "within_subject_focus_lopo.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
