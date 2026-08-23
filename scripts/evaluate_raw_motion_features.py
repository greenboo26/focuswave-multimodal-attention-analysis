"""Extract lightweight raw-mmWave phase/motion features and audit attention value.

This is exploratory: it uses the existing selected channel/range bin, keeps
subjects grouped in leave-one-subject-out evaluation, and never replaces the
quality-gated physiological pipeline.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.signal import detrend, welch
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DATA = Path(r"E:\Data")
OUT = ROOT / "output" / "E_Data_FAST"
FS = 100.0
WINDOW_S = 60.0
KEYS = [f"tx{tx}_rx{rx}" for tx in range(2) for rx in range(4)]


def raw_phase(subject: str, channel: int, bin_index: int) -> np.ndarray:
    files = sorted((DATA / f"sub-{subject}_" / "mmwave").glob("*.npz"))
    if not files:
        return np.empty(0)
    key = KEYS[int(channel) % len(KEYS)]
    chunks = []
    for path in files:
        with np.load(path, allow_pickle=False) as z:
            if key not in z:
                return np.empty(0)
            x = np.asarray(z[key])
            b = int(np.clip(bin_index, 0, x.shape[1] - 1))
            chunks.append(x[:, b])
    return np.unwrap(np.angle(np.concatenate(chunks)))


def features(signal: np.ndarray, start: int, end: int) -> dict[str, float]:
    x = signal[start:end]
    if x.size < int(FS * 30):
        return {}
    x = detrend(x)
    dx = np.diff(x)
    abs_dx = np.abs(dx)
    med = float(np.median(abs_dx)) + 1e-9
    f, p = welch(x, fs=FS, nperseg=min(4096, x.size))
    integrate = getattr(np, "trapezoid", np.trapz)
    total = float(integrate(p, f)) + 1e-12
    low = float(integrate(p[(f >= 0.03) & (f < 0.5)], f[(f >= 0.03) & (f < 0.5)]))
    high = float(integrate(p[(f >= 0.5) & (f < 5.0)], f[(f >= 0.5) & (f < 5.0)]))
    return {
        "phase_std": float(np.std(x)),
        "phase_ptp": float(np.percentile(x, 95) - np.percentile(x, 5)),
        "phase_velocity_rms": float(np.sqrt(np.mean(dx * dx))),
        "phase_burst_fraction": float(np.mean(abs_dx > 5.0 * med)),
        "phase_jump_fraction": float(np.mean(abs_dx > 0.5)),
        "motion_low_power_ratio": low / total,
        "motion_high_low_ratio": high / (low + 1e-12),
    }


def main():
    rows = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
    by_subject = defaultdict(list)
    for row in rows:
        by_subject[row["subject"]].append(row)
    output_rows = []
    subjects_processed = 0
    for subject, subject_rows in sorted(by_subject.items()):
        npz = next((OUT / f"sub-{subject}_").glob("*_vital_signs.npz"), None)
        if npz is None:
            continue
        with np.load(npz, allow_pickle=True) as z:
            channel = int(z["best_ch"])
            bin_index = int(z["chest_bin"])
            t = np.asarray(z["t"])
        phase = raw_phase(subject, channel, bin_index)
        if phase.size == 0:
            continue
        subjects_processed += 1
        for row in subject_rows:
            start = int(round(float(row["onset_rel_s"]) * FS))
            end = start + int(WINDOW_S * FS)
            feat = features(phase, start, end)
            if not feat:
                continue
            output_rows.append({"subject": subject, "attention": int(row["attention"]), **feat})

    fields = list(output_rows[0]) if output_rows else ["subject", "attention"]
    with (OUT / "raw_motion_features.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(output_rows)

    results = {"n_windows": len(output_rows), "n_subjects": subjects_processed, "features": fields[2:]}
    for name in ("focus_vs_all_nonfocus", "focus_vs_mind_wandering"):
        data = output_rows if name.endswith("all_nonfocus") else [r for r in output_rows if r["attention"] in (1, 3)]
        y = np.array([int(r["attention"] == 1) for r in data])
        X = np.array([[float(r[k]) for k in fields[2:]] for r in data])
        groups = np.array([r["subject"] for r in data])
        scores = np.full(len(data), np.nan)
        for held in sorted(set(groups)):
            tr, te = groups != held, groups == held
            if tr.sum() == 0 or len(set(y[tr])) < 2 or te.sum() == 0:
                continue
            model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
            model.fit(X[tr], y[tr]); scores[te] = model.predict_proba(X[te])[:, 1]
        good = np.isfinite(scores)
        if good.sum() and len(set(y[good])) == 2:
            pred = scores[good] >= 0.5
            results[name] = {"n": int(good.sum()), "n_subjects": int(len(set(groups[good]))), "auc": float(roc_auc_score(y[good], scores[good])), "balanced_accuracy": float(balanced_accuracy_score(y[good], pred))}
        else:
            results[name] = {"n": int(good.sum()), "n_subjects": int(len(set(groups[good]))), "auc": None, "balanced_accuracy": None}
    results["note"] = "Exploratory raw phase motion audit; no deployment claim and no replacement for the quality-gated physiological pipeline."
    (OUT / "raw_motion_features_lopo.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
