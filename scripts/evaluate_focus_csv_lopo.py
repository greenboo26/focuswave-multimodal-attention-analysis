"""Subject-held-out evaluation for a probe-level focus CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from scipy.stats import rankdata


def fit_logistic(x, y, steps=3000, lr=0.03, l2=0.05):
    z = np.c_[np.ones(len(x)), x]
    w = np.zeros(z.shape[1])
    pos, neg = max(1, int(y.sum())), max(1, len(y) - int(y.sum()))
    weights = np.where(y == 1, len(y) / (2 * pos), len(y) / (2 * neg))
    for _ in range(steps):
        p = expit(z @ w)
        g = z.T @ (weights * (p - y)) / len(y)
        g[1:] += l2 * w[1:]
        w -= lr * g
    return w


def auc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return None
    r = rankdata(s, method="average")
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def run(rows, label_name):
    subjects = sorted({r["subject"] for r in rows})
    features = ["hr_delta", "z_rmssd", "n_peaks"]
    predictions = []
    for test_sub in subjects:
        train = [r for r in rows if r["subject"] != test_sub]
        test = [r for r in rows if r["subject"] == test_sub]
        xt = np.asarray([[r[k] for k in features] for r in train], float)
        yt = np.asarray([r["y"] for r in train], float)
        xv = np.asarray([[r[k] for k in features] for r in test], float)
        mu, sd = xt.mean(0), xt.std(0)
        sd[sd < 1e-9] = 1
        w = fit_logistic((xt - mu) / sd, yt)
        score = expit(np.c_[np.ones(len(xv)), (xv - mu) / sd] @ w)
        predictions.extend({"subject": test_sub, "y": int(y), "score": float(s), "pred": int(s >= .5)}
                           for y, s in zip([r["y"] for r in test], score))
    y = np.asarray([p["y"] for p in predictions])
    s = np.asarray([p["score"] for p in predictions])
    yh = np.asarray([p["pred"] for p in predictions])
    cm = [[int(((y == a) & (yh == b)).sum()) for b in (0, 1)] for a in (0, 1)]
    sens = cm[1][1] / max(1, sum(cm[1]))
    spec = cm[0][0] / max(1, sum(cm[0]))
    return {"label": label_name, "n": len(rows), "n_subjects": len(subjects),
            "positive_rate": float(y.mean()), "auc": auc(y, s),
            "balanced_accuracy": float((sens + spec) / 2), "confusion_matrix": cm,
            "predictions": predictions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    raw = list(csv.DictReader(args.input.open(encoding="utf-8-sig")))
    base = []
    for r in raw:
        try:
            attention = int(r["attention"])
            hr = float(r["hr_med_bpm"])
            z = float(r["z_rmssd"])
            npeaks = float(r["n_peaks"])
        except (ValueError, KeyError):
            continue
        base.append({"subject": r["subject"], "attention": attention,
                     "hr": hr, "z_rmssd": z, "n_peaks": npeaks})
    med = {}
    for sub in {r["subject"] for r in base}:
        med[sub] = float(np.median([r["hr"] for r in base if r["subject"] == sub]))
    for r in base:
        r["hr_delta"] = r["hr"] - med[r["subject"]]
    analyses = {}
    all_rows = [{**r, "y": int(r["attention"] == 1)} for r in base]
    analyses["focus_vs_all_nonfocus"] = run(all_rows, "attention=1 vs attention=2/3/4")
    mw_rows = [{**r, "y": int(r["attention"] == 1)} for r in base if r["attention"] in (1, 3)]
    analyses["focus_vs_mind_wandering"] = run(mw_rows, "attention=1 vs attention=3") if any(r["attention"] == 3 for r in mw_rows) else None
    result = {"input": str(args.input), "analyses": analyses,
              "caveat": "probe-level features; leave-one-subject-out; exploratory only"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (v and {x: v[x] for x in ("n", "n_subjects", "auc", "balanced_accuracy")}) for k, v in analyses.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
