"""Evaluate a conservative formal-probe attention prototype.

The model uses only probe-window features and subject-independent training.
Subject-specific centering is treated as an allowed calibration step, not a
label-dependent operation. This is an exploratory validation, not a clinical
classifier.
"""
from pathlib import Path
import csv
import json

import numpy as np
from scipy.special import expit
from scipy.stats import rankdata


ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\Formal_mmwave_FAST")
OUT = ROOT / "formal_attention_lopo.json"
MODEL_OUT = ROOT / "formal_attention_model.json"

data = json.loads((ROOT / "focus_discrimination.json").read_text(encoding="utf-8"))


def fit_logistic(x, y, steps=3000, lr=0.03, l2=0.05):
    z = np.c_[np.ones(len(x)), x]
    w = np.zeros(z.shape[1])
    pos = max(1, int(y.sum()))
    neg = max(1, len(y) - pos)
    weights = np.where(y == 1, len(y) / (2 * pos), len(y) / (2 * neg))
    for _ in range(steps):
        p = expit(z @ w)
        grad = z.T @ (weights * (p - y)) / len(y)
        grad[1:] += l2 * w[1:]
        w -= lr * grad
    return w


def auc(y, score):
    y = np.asarray(y)
    score = np.asarray(score)
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return None
    ranks = rankdata(score, method="average")
    return float((ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))
rows = []
for subject in data["subjects"]:
    ws = subject["windows"]
    hr_center = float(np.median([w["hr_med_bpm"] for w in ws]))
    baseline_rmssd = float(subject["baseline_rmssd_ms"])
    for w in ws:
        # Baseline-normalized features are permitted for an online calibration system.
        rows.append({
            "subject": subject["subject"],
            "y": int(w["attention"] == 1),
            "hr_delta": float(w["hr_med_bpm"] - hr_center),
            "rmssd_z": float((w["rmssd_ms"] - baseline_rmssd) / max(1.0, baseline_rmssd)),
            "n_peaks": float(w["n_peaks"]),
        })

features = ["hr_delta", "rmssd_z", "n_peaks"]
pred = []
subjects = sorted({r["subject"] for r in rows})
for test_subject in subjects:
    train = [r for r in rows if r["subject"] != test_subject]
    test = [r for r in rows if r["subject"] == test_subject]
    x_train = np.asarray([[r[k] for k in features] for r in train])
    y_train = np.asarray([r["y"] for r in train])
    x_test = np.asarray([[r[k] for k in features] for r in test])
    y_test = np.asarray([r["y"] for r in test])
    mu, sd = x_train.mean(axis=0), x_train.std(axis=0)
    sd[sd < 1e-9] = 1.0
    w = fit_logistic((x_train - mu) / sd, y_train)
    score = expit(np.c_[np.ones(len(x_test)), (x_test - mu) / sd] @ w)
    for r, y, s in zip(test, y_test, score):
        pred.append({"subject": test_subject, "y": int(y), "score": float(s), "pred": int(s >= 0.5)})

y = np.asarray([r["y"] for r in pred])
score = np.asarray([r["score"] for r in pred])
yhat = np.asarray([r["pred"] for r in pred])
cm = [[int(((y == a) & (yhat == b)).sum()) for b in (0, 1)] for a in (0, 1)]
sens = cm[1][1] / max(1, cm[1][0] + cm[1][1])
spec = cm[0][0] / max(1, cm[0][0] + cm[0][1])
result = {
    "n_windows": len(pred),
    "n_subjects": len(subjects),
    "label": "fully focused (attention=1) vs all other probe states",
    "features": features,
    "cross_validation": "leave-one-subject-out",
    "auc": auc(y, score),
    "balanced_accuracy": float((sens + spec) / 2),
    "confusion_matrix_labels_0_1": cm,
    "positive_rate": float(y.mean()),
    "predictions": pred,
    "interpretation": "exploratory only; subject calibration and class imbalance remain; no deployment claim",
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

# Fit a research-only reference model on all formal probe windows for the
# runtime prototype. This fit is not used to claim held-out performance.
x_all = np.asarray([[r[k] for k in features] for r in rows])
y_all = np.asarray([r["y"] for r in rows])
mu_all, sd_all = x_all.mean(axis=0), x_all.std(axis=0)
sd_all[sd_all < 1e-9] = 1.0
w_all = fit_logistic((x_all - mu_all) / sd_all, y_all)
MODEL_OUT.write_text(json.dumps({
    "features": features,
    "mean": mu_all.tolist(),
    "scale": sd_all.tolist(),
    "weights_intercept_first": w_all.tolist(),
    "training_n_windows": len(rows),
    "training_n_subjects": len(subjects),
    "warning": "research prototype only; held-out AUC is reported separately and is not deployment validation",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("n_windows", "n_subjects", "auc", "balanced_accuracy", "positive_rate")}, ensure_ascii=False))
