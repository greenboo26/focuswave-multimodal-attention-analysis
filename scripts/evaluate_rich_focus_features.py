"""Subject-out audit of a richer mmWave feature set for attention labels."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.signal import periodogram
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def finite_median(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def window_stat(t, x, start, end, fn):
    x = np.asarray(x, float)
    m = (t > start) & (t <= end) & np.isfinite(x)
    return float(fn(x[m])) if np.sum(m) >= 3 else np.nan


def local_rate(t, x, start, end, lo=0.10, hi=0.50):
    x = np.asarray(x, float)
    m = (t > start) & (t <= end) & np.isfinite(x)
    if np.sum(m) < 100:
        return np.nan
    y = x[m][::10]
    fs = 1.0 / np.median(np.diff(t[m][::10]))
    y = y - np.median(y)
    f, p = periodogram(y, fs=fs, detrend="linear")
    q = (f >= lo) & (f <= hi)
    return float(f[q][np.argmax(p[q])] * 60.0) if np.any(q) else np.nan


def features_for_row(r, cache):
    sub = r["subject"]
    if sub not in cache:
        p = OUT / f"sub-{sub}_" / f"sub-{sub}_ses-SART_mmwave_vital_signs.npz"
        d = np.load(p, allow_pickle=True)
        cache[sub] = {k: d[k] for k in d.files}
    d = cache[sub]
    t = np.asarray(d["t"], float)
    end = float(r["onset_rel_s"]); start = end - 60.0
    ht = np.asarray(d["hr_course_time_s"], float)
    hp = np.asarray(d["hr_course_fused_bpm"], float)
    cp = np.asarray(d["hr_course_confidence"], float)
    gp = np.asarray(d["hr_course_time_freq_gap_bpm"], float)
    su = np.asarray(d["hr_course_signal_usable"], float)
    ss = np.asarray(d["hr_course_signal_std_10s_mm"], float)
    peaks = np.asarray(d["heart_peaks"], int)
    if len(peaks) and np.nanmax(peaks) > np.nanmax(t) + 1:
        peaks = t[np.clip(peaks, 0, len(t) - 1)]
    peaks = peaks[(peaks > start) & (peaks <= end)]
    ibi = np.diff(peaks)
    valid = ibi[(ibi >= .30) & (ibi <= 2.0)]
    rmssd = np.sqrt(np.mean(np.diff(valid) ** 2)) * 1000 if len(valid) >= 3 else np.nan
    sdnn = np.std(valid, ddof=1) * 1000 if len(valid) >= 3 else np.nan
    bf = local_rate(t, d["breath"], start, end)
    return [
        finite_median(r["hr_med_bpm"]),
        finite_median(r["z_rmssd"]),
        float(len(peaks)),
        rmssd, sdnn,
        window_stat(ht, hp, start, end, np.median),
        window_stat(ht, hp, start, end, np.std),
        window_stat(ht, cp, start, end, np.median),
        window_stat(ht, gp, start, end, np.median),
        window_stat(ht, su, start, end, np.mean),
        window_stat(ht, ss, start, end, np.median),
        window_stat(t, d["heartbeat"], start, end, np.std),
        window_stat(t, d["breath"], start, end, np.std),
        bf,
    ]


def evaluate(X, y, groups, model):
    scores = np.full(len(y), np.nan)
    for g in sorted(set(groups)):
        tr = np.asarray(groups) != g; te = ~tr
        if len(set(y[tr])) < 2 or not np.any(te):
            continue
        model.fit(X[tr], y[tr])
        scores[te] = model.predict_proba(X[te])[:, 1]
    keep = np.isfinite(scores)
    pred = (scores[keep] >= .5).astype(int)
    return {
        "n": int(np.sum(keep)), "n_subjects": int(len(set(np.asarray(groups)[keep]))),
        "auc": float(roc_auc_score(y[keep], scores[keep])) if len(set(y[keep])) == 2 else None,
        "balanced_accuracy": float(balanced_accuracy_score(y[keep], pred)),
    }


def main():
    rows = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
    cache = {}
    feats, labels, subjects = [], [], []
    for r in rows:
        feats.append(features_for_row(r, cache)); labels.append(int(r["attention"])); subjects.append(r["subject"])
    X = np.asarray(feats, float); y0 = np.asarray(labels); groups = np.asarray(subjects)
    med = np.nanmedian(X, axis=0); X = np.where(np.isfinite(X), X, med)
    feature_names = ["hr_csv", "z_rmssd_csv", "n_peaks", "rmssd", "sdnn", "hr_course_median", "hr_course_sd", "hr_confidence", "hr_gap", "hr_usable", "signal_std", "heartbeat_sd", "breath_sd", "breath_rate"]
    with (OUT / "rich_focus_features.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["subject", "attention", *feature_names])
        for s, y, x in zip(groups, y0, X): w.writerow([s, int(y), *[float(v) for v in x]])
    models = {
        "logistic_rich": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
        "random_forest_rich": RandomForestClassifier(n_estimators=300, min_samples_leaf=8, class_weight="balanced", random_state=7),
    }
    results = {}
    for name, model in models.items():
        results[name] = {}
        for contrast, mask in {
            "focus_vs_all_nonfocus": np.ones(len(y0), bool),
            "focus_vs_mind_wandering": np.isin(y0, [1, 3]),
        }.items():
            yy = (y0[mask] == 1).astype(int)
            results[name][contrast] = evaluate(X[mask], yy, groups[mask], model)
    out = {"feature_names": feature_names, "n_windows": len(rows), "n_subjects": len(set(groups)), "results": results,
           "note": "All scores are leave-one-subject-out; missing values are median-imputed within the full audit table for descriptive model comparison; exploratory only."}
    (OUT / "rich_focus_features_lopo.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
