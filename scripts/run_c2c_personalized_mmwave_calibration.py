"""C2C: frozen within-person resting normalization of C2b-v2 mmWave features.

The 30-s analysis is primary.  It reuses the C2a canonical probes, C2b-v2
feature family, and repeat-participant-disjoint folds.  Each session's
pre-task 180-s ``baseline_start``--``baseline_stop`` interval is divided into
same-duration windows; feature-wise median/MAD defines a robust within-person
z score for every probe feature.  No HRV, IBI, RGB, NIR, label-guided target
selection, or signal-processing redevelopment is used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯")
ALGO = ROOT / "08_算法"
DATA = Path(r"J:\Data")
C2B = ROOT / "11_数据/derived/c2b_v2_canonical_baselines_20260826"
OUT = ROOT / "11_数据/derived/c2c_within_subject_normalization_v1"
SEED = 20260826
BOOTSTRAP = 5000
CONTEXT = ["block_num", "block_probe_fraction", "onset_rel_s"]
BEHAVIOR = ["b_trial_count", "b_rt_mean", "b_rt_median", "b_rt_sd", "b_rt_mad", "b_rt_cv", "b_rt_slope", "b_accuracy", "b_error_count", "b_error_rate", "b_omission_count", "b_omission_rate"]
W = ["m1_phase_std_rad", "m1_phase_velocity_mad", "m1_phase_accel_mad", "m1_log_power_low", "m1_log_power_transition", "m1_log_power_micro", "m1_log_power_high", "m1_micro_power_fraction", "m1_phase_peak_micro_hz", "m1_micro_peak_share", "m1_micro_spectral_entropy", "m1_harmonic_overlap", "m1_harmonic_power_fraction", "m1_phase_trend_rad_s", "q_target_power_snr_db", "q_target_amplitude_cv", "q_phase_jump_fraction", "q_frame_gap_fraction", "q_frame_gap_duration_fraction", "q_frame_rate_hz", "q_selection_margin"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def frozen_extractor():
    path = Path(__file__).with_name("build_evaluate_j_mmwave_m1_loso.py")
    spec = importlib.util.spec_from_file_location("c2c_frozen_extractor", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def timeline(subject: str) -> dict[str, float]:
    path = DATA / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    values = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                values[r["event"]] = float(r["unix_ms"])
            except (KeyError, TypeError, ValueError):
                pass
    return values


def baseline_features(subject: str, window_s: int, ext) -> tuple[list[dict], str | None]:
    """Return same-family unlabeled feature rows from actual pre-task rest."""
    try:
        t = timeline(subject)
        start, stop = t["baseline_start"], t["baseline_stop"]
        if stop - start < 180000 - 1000:
            return [], "baseline_interval_shorter_than_180s"
        d = DATA / f"sub-{subject}_" / "mmwave"
        ts = ext.load_timestamps(next(d.glob("*_timestamps.csv")))
        chunks = ext.ChunkIndex.create(d)
        if int(chunks.ends[-1]) != len(ts):
            return [], "npz_timestamp_frame_count_mismatch"
        rows = []
        for k in range(180 // window_s):
            lo, hi = start + k * window_s * 1000, start + (k + 1) * window_s * 1000
            i, j = int(np.searchsorted(ts, lo, side="left")), int(np.searchsorted(ts, hi, side="left"))
            dur = (ts[j - 1] - ts[i]) / 1000 if j > i else 0.0
            if dur < max(.8 * window_s, window_s - 5):
                continue
            row, _ = ext.extract_features(chunks.read(i, j), ts[i:j])
            if row.get("q_extraction_ok") == 1:
                rows.append(row)
        if len(rows) < 3:
            return rows, f"insufficient_usable_baseline_windows:{len(rows)}"
        return rows, None
    except Exception as exc:  # recorded per subject, never converted to values
        return [], f"baseline_extraction_error:{type(exc).__name__}:{exc}"


def robust_stats(rows: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {"baseline_n_windows": len(rows)}
    for feature in W:
        x = np.asarray([r.get(feature, np.nan) for r in rows], float)
        x = x[np.isfinite(x)]
        med = float(np.median(x)) if len(x) else np.nan
        mad = float(np.median(np.abs(x - med))) if len(x) else np.nan
        out[f"baseline_median__{feature}"] = med
        out[f"baseline_mad__{feature}"] = mad
    return out


def metric(y: np.ndarray, score: np.ndarray) -> dict[str, float]:
    return {"roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score), "balanced_accuracy": balanced_accuracy_score(y, score >= .5)}


def bootstrap_ci(pred: pd.DataFrame, reps: int, seed: int) -> dict[str, float]:
    groups = pred.group_subject_id.astype(str).unique()
    by = {g: np.flatnonzero(pred.group_subject_id.astype(str).to_numpy() == g) for g in groups}
    rng = np.random.default_rng(seed)
    values = {k: [] for k in ["roc_auc", "pr_auc", "balanced_accuracy"]}
    y_all, s_all = pred.y_true.to_numpy(int), pred.score.to_numpy(float)
    for _ in range(reps):
        ix = np.concatenate([by[g] for g in rng.choice(groups, len(groups), replace=True)])
        if len(np.unique(y_all[ix])) == 2:
            m = metric(y_all[ix], s_all[ix])
            for k, v in m.items(): values[k].append(v)
    result = {"bootstrap_valid": len(values["roc_auc"])}
    for k, vals in values.items():
        result[f"{k}_ci95_low"], result[f"{k}_ci95_high"] = np.quantile(vals, [.025, .975]) if vals else (np.nan, np.nan)
    return result


def evaluate(frame: pd.DataFrame, window_s: int, reps: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Identical repeat-participant-disjoint folds for all prespecified sets."""
    frame = frame.copy()
    frame["group_subject_id"] = frame.group_subject_id.astype(str)
    # A common complete calibration cohort makes C+B, absolute, and within
    # comparisons directly interpretable; no modality is imputed into existence.
    required = ["behavior_available", "mmwave_available", "within_available", *W]
    frame = frame[frame[required].notna().all(axis=1) & frame.behavior_available.eq(1) & frame.mmwave_available.eq(1) & frame.within_available.eq(1)].copy()
    y, groups = frame.target.to_numpy(int), frame.group_subject_id.to_numpy()
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    frame["fold"] = -1
    for fold, (_, te) in enumerate(sgkf.split(frame, y, groups)): frame.loc[frame.index[te], "fold"] = fold
    sets = {"C+B": CONTEXT + BEHAVIOR, "C+B+W_absolute": CONTEXT + BEHAVIOR + W, "C+B+W_within": CONTEXT + BEHAVIOR + [f"within_z__{x}" for x in W], "W_absolute": W, "W_within": [f"within_z__{x}" for x in W]}
    metrics, predictions = [], []
    for name, features in sets.items():
        parts = []
        for fold in range(5):
            tr, te = frame[frame.fold.ne(fold)], frame[frame.fold.eq(fold)]
            model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), LogisticRegression(C=1.0, max_iter=3000, class_weight="balanced", random_state=SEED + fold))
            weights = tr.groupby("group_subject_id")["group_subject_id"].transform(lambda x: 1 / len(x)).to_numpy()
            model.fit(tr[features].to_numpy(float), tr.target.to_numpy(int), logisticregression__sample_weight=weights)
            parts.append(pd.DataFrame({"subject": te.subject, "probe_seq": te.probe_seq, "group_subject_id": te.group_subject_id, "fold": fold, "y_true": te.target, "score": model.predict_proba(te[features].to_numpy(float))[:, 1], "feature_set": name, "window_s": window_s}))
        p = pd.concat(parts, ignore_index=True)
        m = metric(p.y_true.to_numpy(int), p.score.to_numpy(float))
        m.update(bootstrap_ci(p, reps, SEED + window_s + len(metrics)))
        m.update({"window_s": window_s, "feature_set": name, "n_probe": len(p), "n_participant": p.group_subject_id.nunique(), "positive_n": int(p.y_true.sum()), "coverage": len(p) / len(frame)})
        metrics.append(m); predictions.append(p)
    preds = pd.concat(predictions, ignore_index=True)
    a, b = preds.query("feature_set == 'C+B'"), preds.query("feature_set == 'C+B+W_within'")
    j = a.merge(b, on=["subject", "probe_seq", "group_subject_id", "fold", "y_true", "window_s"], suffixes=("_base", "_within"))
    groups = j.group_subject_id.astype(str).unique(); by = {g: np.flatnonzero(j.group_subject_id.astype(str).to_numpy() == g) for g in groups}; rng = np.random.default_rng(SEED + window_s)
    delta = []
    for _ in range(reps):
        ix = np.concatenate([by[g] for g in rng.choice(groups, len(groups), replace=True)])
        yy = j.y_true.to_numpy(int)[ix]
        if len(np.unique(yy)) == 2: delta.append(roc_auc_score(yy, j.score_within.to_numpy(float)[ix]) - roc_auc_score(yy, j.score_base.to_numpy(float)[ix]))
    d = {"window_s": window_s, "comparison": "C+B+W_within_minus_C+B", "delta_roc_auc": roc_auc_score(j.y_true, j.score_within) - roc_auc_score(j.y_true, j.score_base), "delta_roc_auc_ci95_low": np.quantile(delta, .025), "delta_roc_auc_ci95_high": np.quantile(delta, .975), "bootstrap_valid": len(delta), "n_common_probe": len(j), "n_participant": len(groups)}
    return pd.DataFrame(metrics), preds, pd.DataFrame([d])


def report(out: Path, metrics: pd.DataFrame, deltas: pd.DataFrame, coverage: pd.DataFrame) -> None:
    m = metrics[metrics.window_s.eq(30)].set_index("feature_set")
    d = deltas[deltas.window_s.eq(30)].iloc[0]
    supported = bool(d.delta_roc_auc_ci95_low > 0)
    lines = ["# C2C personal resting calibration of canonical mmWave features", "", f"状态：`{'WITHIN_SUBJECT_RADAR_INCREMENT_SUPPORTED' if supported else 'WITHIN_SUBJECT_RADAR_INCREMENT_NOT_SUPPORTED'}`", "", "30 s 是预冻结主分析；10/60 s 仅为冻结敏感性。C2a canonical probes、C2b-v2 行级 absolute 特征和 5-fold repeat-participant-disjoint StratifiedGroupKFold 被原样复用。每个 session 使用 experiment 前 `baseline_start` 至 `baseline_stop` 的 180 s 静息段，按分析窗切分，以 feature-wise median/MAD 构造 robust-z。", "", f"主队列：{int(m.iloc[0].n_probe)} probes，{int(m.iloc[0].n_participant)} repeat participants。静息校准 session 覆盖：{int(coverage.calibration_covered.sum())}/{len(coverage)}。", "", "| 30 s feature set | ROC-AUC [95% CI] | PR-AUC [95% CI] | Balanced accuracy [95% CI] | coverage |", "|---|---|---|---|---:|"]
    for name, r in m.iterrows(): lines.append(f"| {name} | {r.roc_auc:.3f} [{r.roc_auc_ci95_low:.3f}, {r.roc_auc_ci95_high:.3f}] | {r.pr_auc:.3f} [{r.pr_auc_ci95_low:.3f}, {r.pr_auc_ci95_high:.3f}] | {r.balanced_accuracy:.3f} [{r.balanced_accuracy_ci95_low:.3f}, {r.balanced_accuracy_ci95_high:.3f}] | {r.coverage:.3f} |")
    lines += ["", f"主要裁决量 ΔAUC = C+B+W_within − C+B = {d.delta_roc_auc:.3f}, participant-cluster bootstrap 95% CI [{d.delta_roc_auc_ci95_low:.3f}, {d.delta_roc_auc_ci95_high:.3f}]。", "", "只有在主要 30 s ΔAUC 的 95% CI 完全高于 0 时才标记 supported；10/60 s 不用于选择窗口、标签或模型。行级 features、baseline statistics 和 OOF predictions 仅保留本地 derived 输出。"]
    (out / "C2C_PERSONALIZED_MMWAVE_CALIBRATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", type=Path, default=OUT); ap.add_argument("--bootstrap", type=int, default=BOOTSTRAP); ap.add_argument("--windows", nargs="+", type=int, default=[10, 30, 60]); args = ap.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    ext = frozen_extractor(); all_metrics=[]; all_delta=[]; cov_rows=[]
    for w in args.windows:
        source = C2B / f"window_{w}s/canonical_feature_matrix_local.csv"
        frame = pd.read_csv(source, dtype={"subject": str}); frame.subject = frame.subject.str.zfill(3)
        bases=[]
        for subject in sorted(frame.subject.unique()):
            rows, reason = baseline_features(subject, w, ext); s = robust_stats(rows); s.update({"subject": subject, "calibration_covered": reason is None, "calibration_reason": reason or "ok"}); bases.append(s)
        base = pd.DataFrame(bases); base.to_csv(args.output / f"baseline_calibration_local_{w}s.csv", index=False, encoding="utf-8-sig")
        for f in W:
            frame = frame.merge(base[["subject", f"baseline_median__{f}", f"baseline_mad__{f}"]], on="subject", how="left")
            mad, med = frame[f"baseline_mad__{f}"], frame[f"baseline_median__{f}"]
            frame[f"within_z__{f}"] = (frame[f] - med) / (1.4826 * mad)
        frame["within_available"] = frame[[f"within_z__{f}" for f in W]].replace([np.inf, -np.inf], np.nan).notna().all(axis=1).astype(int)
        frame.to_csv(args.output / f"c2c_feature_matrix_local_{w}s.csv", index=False, encoding="utf-8-sig")
        metrics, preds, delta = evaluate(frame, w, args.bootstrap); metrics.to_csv(args.output / f"c2c_metrics_{w}s.csv", index=False, encoding="utf-8-sig"); preds.to_csv(args.output / f"c2c_oof_predictions_local_{w}s.csv", index=False, encoding="utf-8-sig"); delta.to_csv(args.output / f"c2c_delta_{w}s.csv", index=False, encoding="utf-8-sig")
        all_metrics.append(metrics); all_delta.append(delta); cov_rows.append(base[["subject", "calibration_covered", "calibration_reason", "baseline_n_windows"]].assign(window_s=w))
    metrics=pd.concat(all_metrics); deltas=pd.concat(all_delta); coverage=pd.concat(cov_rows); metrics.to_csv(args.output / "c2c_model_metrics_aggregate.csv", index=False, encoding="utf-8-sig"); deltas.to_csv(args.output / "c2c_primary_increment_aggregate.csv", index=False, encoding="utf-8-sig"); coverage.to_csv(args.output / "c2c_calibration_coverage_aggregate.csv", index=False, encoding="utf-8-sig")
    report(args.output, metrics, deltas, coverage.query("window_s == 30"));
    plot = metrics.pivot(index="feature_set", columns="window_s", values="roc_auc"); ax=plot.plot(kind="bar", figsize=(9,4), ylim=(0,1), title="C2C frozen window sensitivity: ROC-AUC"); ax.set_ylabel("ROC-AUC"); ax.figure.tight_layout(); ax.figure.savefig(args.output / "c2c_window_sensitivity_roc_auc.png", dpi=180); plt.close(ax.figure)
    public = args.output / "github_aggregate"; public.mkdir(exist_ok=True); metrics.to_csv(public / "c2c_model_metrics_aggregate.csv", index=False, encoding="utf-8-sig"); deltas.to_csv(public / "c2c_primary_increment_aggregate.csv", index=False, encoding="utf-8-sig"); coverage.groupby("window_s").agg(n_sessions=("subject", "size"), calibration_covered=("calibration_covered", "sum")).reset_index().to_csv(public / "c2c_calibration_coverage_summary.csv", index=False, encoding="utf-8-sig"); (public / "C2C_PERSONALIZED_MMWAVE_CALIBRATION_REPORT.md").write_text((args.output / "C2C_PERSONALIZED_MMWAVE_CALIBRATION_REPORT.md").read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__": main()
