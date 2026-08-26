"""Freeze the report cohort and rerun the V1 behavior/context baseline.

The input cohort is the already frozen REPORT_ANALYSIS_COHORT (1400 probes,
70 sessions, 46 repeat participants). The script fixes one participant-level
5-fold StratifiedGroupKFold assignment and reuses it for 10/20/30-second C,
B, and C+B L2-logistic models. Imputation, scaling, and model fitting happen
inside each training fold. Row-level predictions remain local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, roc_auc_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯")
COHORT = ROOT / "11_数据/derived/report_cohort_label_vigilance_v1/report_analysis_cohort.csv"
DEFAULT_OUT = ROOT / "11_数据/derived/final_report_cohort_baseline_v2"
DATA_ROOT = Path(r"J:\Data")
SEED = 20260826
WINDOWS = (10, 20, 30)
BOOTSTRAP = 1000
CONTEXT = ["block_num", "block_probe_fraction", "onset_rel_s"]
BEHAVIOR = [
    "b_trial_count", "b_rt_mean", "b_rt_median", "b_rt_sd", "b_rt_mad",
    "b_rt_cv", "b_rt_slope", "b_accuracy", "b_error_count", "b_error_rate",
    "b_omission_count", "b_omission_rate",
]
SETS = {"C_context_only": CONTEXT, "B_behavior_only": BEHAVIOR,
        "C_plus_B": CONTEXT + BEHAVIOR}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def robust_mad(x: pd.Series) -> float:
    a = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    return float(np.median(np.abs(a - np.median(a)))) if len(a) else np.nan


def load_cohort(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path, dtype={"subject_id": str, "repeat_participant_id": str})
    d["subject"] = d["subject_id"].str.extract(r"(\d+)")[0].str.zfill(3)
    d["probe_onset_ms"] = pd.to_numeric(d["probe_onset_time"], errors="coerce")
    d["label"] = pd.to_numeric(d["probe_response"], errors="coerce")
    d["target"] = (d["label"] != 1).astype(int)
    d["block_num"] = pd.to_numeric(d["block_num"], errors="coerce")
    d["block_probe_fraction"] = (pd.to_numeric(d["block_probe_index"], errors="coerce") - 1) / 9.0
    if len(d) != 1400 or d["subject"].nunique() != 70 or d["repeat_participant_id"].nunique() != 46:
        raise ValueError("REPORT_ANALYSIS_COHORT does not have the required 1400/70/46 shape")
    if set(d["label"].dropna().astype(int)) != {1, 2, 3, 4}:
        raise ValueError("Unexpected report cohort labels")
    return d.sort_values(["subject", "probe_onset_ms"]).reset_index(drop=True)


def session_trials(subject: str, data_root: Path) -> pd.DataFrame:
    files = sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv"))
    if not files:
        return pd.DataFrame()
    parts = [pd.read_csv(f) for f in files]
    t = pd.concat(parts, ignore_index=True)
    t["_onset"] = pd.to_numeric(t.get("absolute_onset_time"), errors="coerce")
    t = t[t["_onset"].notna()].sort_values("_onset").copy()
    probe = pd.to_numeric(t.get("is_probe", 0), errors="coerce").fillna(0)
    return t[probe.ne(1)].copy()


def add_context(d: pd.DataFrame, data_root: Path) -> pd.DataFrame:
    out = d.copy()
    first = {}
    for subject in out["subject"].unique():
        t = session_trials(subject, data_root)
        first[subject] = float(t["_onset"].min()) if not t.empty else np.nan
    out["onset_rel_s"] = (out["probe_onset_ms"] - out["subject"].map(first)) / 1000.0
    return out


def behavior_features(d: pd.DataFrame, data_root: Path, window_s: int) -> pd.DataFrame:
    rows = []
    for subject, group in d.groupby("subject", sort=True):
        trials = session_trials(subject, data_root)
        for _, probe in group.iterrows():
            if trials.empty:
                rows.append({"subject": subject, "probe_onset_ms": probe.probe_onset_ms,
                             **{k: np.nan for k in BEHAVIOR}})
                continue
            end = float(probe.probe_onset_ms)
            x = trials[(trials["_onset"] >= end - window_s * 1000.0) & (trials["_onset"] < end)].copy()
            rt = pd.to_numeric(x.get("rt"), errors="coerce")
            valid_rt = rt.dropna()
            correct = pd.to_numeric(x.get("correct"), errors="coerce")
            omission = pd.to_numeric(x.get("omission"), errors="coerce").fillna(0)
            n = len(x)
            err = (correct.fillna(0) != 1).astype(int)
            sd = float(valid_rt.std(ddof=1)) if len(valid_rt) > 1 else np.nan
            valid_mask = rt.notna().to_numpy()
            elapsed = (x["_onset"].to_numpy(float) - (end - window_s * 1000.0)) / 1000.0
            slope = (float(np.polyfit(elapsed[valid_mask], valid_rt.to_numpy(float), 1)[0])
                     if valid_mask.sum() >= 2 else np.nan)
            mean = float(valid_rt.mean()) if len(valid_rt) else np.nan
            rows.append({
                "subject": subject, "probe_onset_ms": probe.probe_onset_ms,
                "b_trial_count": n, "b_rt_mean": mean,
                "b_rt_median": float(valid_rt.median()) if len(valid_rt) else np.nan,
                "b_rt_sd": sd, "b_rt_mad": robust_mad(valid_rt),
                "b_rt_cv": float(sd / abs(mean)) if np.isfinite(sd) and mean else np.nan,
                "b_rt_slope": slope, "b_accuracy": float(correct.mean()) if n else np.nan,
                "b_error_count": int(err.sum()) if n else np.nan,
                "b_error_rate": float(err.mean()) if n else np.nan,
                "b_omission_count": int(omission.sum()) if n else np.nan,
                "b_omission_rate": float(omission.mean()) if n else np.nan,
            })
    return pd.DataFrame(rows)


def fixed_folds(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = np.full(len(d), -1, dtype=int)
    y = d["target"].to_numpy(int)
    groups = d["repeat_participant_id"].to_numpy()
    for fold, (_, test) in enumerate(splitter.split(d, y, groups)):
        folds[test] = fold
    if (folds < 0).any():
        raise ValueError("Some rows were not assigned to a fold")
    d = d.copy()
    d["fold"] = folds
    check = d.groupby("repeat_participant_id")["fold"].nunique()
    if not check.eq(1).all() or len(check) != 46:
        raise ValueError("Participant fold leakage or missing participant")
    f = (d.groupby(["repeat_participant_id", "fold"], as_index=False)
           .agg(n_probe=("target", "size"), n_session=("subject", "nunique")))
    return d, f


def metric_row(y: np.ndarray, score: np.ndarray, bootstrap_values: dict[str, tuple[float, float]] | None = None) -> dict:
    pred = (score >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    row = {"roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score),
           "balanced_accuracy": balanced_accuracy_score(y, pred),
           "sensitivity": tp / (tp + fn) if tp + fn else np.nan,
           "specificity": tn / (tn + fp) if tn + fp else np.nan,
           "brier": brier_score_loss(y, score), "tn": int(tn), "fp": int(fp),
           "fn": int(fn), "tp": int(tp)}
    if bootstrap_values:
        for name, (lo, hi) in bootstrap_values.items():
            row[f"{name}_ci95_low"], row[f"{name}_ci95_high"] = lo, hi
    return row


def bootstrap_ci(pred: pd.DataFrame, seed: int) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    groups = pred["repeat_participant_id"].unique()
    by_group = {g: np.flatnonzero(pred["repeat_participant_id"].to_numpy() == g) for g in groups}
    vals = {k: [] for k in ["roc_auc", "pr_auc", "balanced_accuracy", "sensitivity", "specificity", "brier"]}
    for _ in range(BOOTSTRAP):
        sampled = rng.choice(groups, len(groups), replace=True)
        idx = np.concatenate([by_group[g] for g in sampled])
        y, score = pred["target"].to_numpy(int)[idx], pred["score"].to_numpy(float)[idx]
        if len(np.unique(y)) < 2:
            continue
        m = metric_row(y, score)
        for k in vals:
            vals[k].append(m[k])
    return {k: (float(np.quantile(v, .025)), float(np.quantile(v, .975))) for k, v in vals.items() if v}


def calibrate(pred: pd.DataFrame) -> pd.DataFrame:
    bins = pd.cut(pred["score"], bins=np.linspace(0, 1, 11), include_lowest=True)
    out = pred.assign(bin=bins).groupby("bin", observed=False).agg(
        n=("target", "size"), mean_prediction=("score", "mean"), observed_rate=("target", "mean"))
    out.insert(0, "bin", out.index.astype(str))
    return out.reset_index(drop=True)


def evaluate(frame: pd.DataFrame, window_s: int, out: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = behavior_features(frame, DATA_ROOT, window_s)
    x = frame.merge(b, on=["subject", "probe_onset_ms"], how="left")
    all_metrics, predictions = [], []
    for name, features in SETS.items():
        scores = np.full(len(x), np.nan)
        for fold in range(5):
            train, test = x["fold"].ne(fold), x["fold"].eq(fold)
            model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                                   LogisticRegression(C=1.0, class_weight="balanced", max_iter=3000,
                                                      random_state=SEED + fold))
            weights = x.loc[train].groupby("repeat_participant_id")["repeat_participant_id"].transform(lambda s: 1.0 / len(s)).to_numpy()
            model.fit(x.loc[train, features], x.loc[train, "target"], logisticregression__sample_weight=weights)
            scores[test] = model.predict_proba(x.loc[test, features])[:, 1]
        pred = x[["subject", "repeat_participant_id", "probe_onset_ms", "target", "fold"]].copy()
        pred["score"] = scores
        pred["feature_set"], pred["window_s"] = name, window_s
        ci = bootstrap_ci(pred, SEED + window_s)
        base = metric_row(pred.target.to_numpy(int), scores, ci)
        all_metrics.append({"window_s": window_s, "model": "logistic_l2", "feature_set": name,
                            "n_probe": len(pred), "n_session": pred.subject.nunique(),
                            "n_participant": pred.repeat_participant_id.nunique(),
                            "positive_n": int(pred.target.sum()), "positive_rate": float(pred.target.mean()),
                            **base})
        predictions.append(pred)
        calibrate(pred).assign(window_s=window_s, feature_set=name).to_csv(out / f"calibration_{name}.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_csv(out / f"oof_predictions_{window_s}s_LOCAL_ONLY.csv", index=False)
    return pd.DataFrame(all_metrics), pd.concat(predictions, ignore_index=True)


def write_report(out: Path, metrics: pd.DataFrame, cohort: pd.DataFrame) -> None:
    m30 = metrics[metrics.window_s.eq(30)].set_index("feature_set")
    def fmt(r, key): return f"{r[key]:.3f} [{r[key + '_ci95_low']:.3f}, {r[key + '_ci95_high']:.3f}]"
    lines = ["# FINAL_BEHAVIOR_CONTEXT_BASELINE_V2", "", "状态：`FINAL_REPORT_COHORT_BASELINE_V2`", "",
             "本报告严格复用 V1 方法，仅将 cohort 更换为已冻结的 REPORT_ANALYSIS_COHORT。",
             "标签为 1 vs 2/3/4，阳性类为 2/3/4；主窗口 30 s，敏感性窗口 10 s/20 s；模型为 L2 logistic。",
             "验证为一次固定的 5-fold StratifiedGroupKFold，分组单位为 repeat_participant_id；所有 imputation、scaling 和模型拟合仅在 training fold。", "",
             f"cohort：{len(cohort)} probes / {cohort.subject.nunique()} sessions / {cohort.repeat_participant_id.nunique()} participants。", "",
             "## 30 s 主结果", "", "| Set | ROC-AUC | PR-AUC | balanced accuracy | sensitivity | specificity | confusion matrix |", "|---|---:|---:|---:|---:|---:|---|"]
    for name in ["C_context_only", "B_behavior_only", "C_plus_B"]:
        r = m30.loc[name]
        lines.append(f"| {name} | {fmt(r,'roc_auc')} | {fmt(r,'pr_auc')} | {fmt(r,'balanced_accuracy')} | {fmt(r,'sensitivity')} | {fmt(r,'specificity')} | {int(r.tn)}/{int(r.fp)}/{int(r.fn)}/{int(r.tp)} |")
    lines += ["", "CI 为 participant-cluster bootstrap 95% CI（1,000 次）。Calibration 表按 OOF prediction 的 10 个 probability bins 保存。", "", "## 敏感性窗口", "", "| Window | Set | ROC-AUC | PR-AUC | balanced accuracy |", "|---:|---|---:|---:|---:|"]
    for w in [10, 20]:
        for name in ["C_context_only", "B_behavior_only", "C_plus_B"]:
            r = metrics[(metrics.window_s.eq(w)) & metrics.feature_set.eq(name)].iloc[0]
            lines.append(f"| {w} s | {name} | {r.roc_auc:.3f} | {r.pr_auc:.3f} | {r.balanced_accuracy:.3f} |")
    lines += ["", "## Frozen outputs", "", "- `REPORT_FOLDS_V1.csv`：46 个 repeat_participant_id 的固定五折分配。", "- 后续 NIR、RGB、multimodal 模型必须复用该 participant-level assignment；不得重新按模态抽样或重新生成 folds。", "- 本版本废止旧 `FINAL_BEHAVIOR_CONTEXT_BASELINE_V1` 的 1,440-probe C2a fallback。", "", "## 未重跑既有报告", "", "`REPORT_COHORT_LABEL_VIGILANCE_V1` 与 `REPORT_REPEAT_SESSION_EFFECTS_V1` 已通过既有 manifest 核对为 1,400 probes / 70 sessions / 46 participants；本任务未重跑。"]
    (out / "FINAL_BEHAVIOR_CONTEXT_BASELINE_V2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global DATA_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", type=Path, default=COHORT)
    ap.add_argument("--data-root", type=Path, default=DATA_ROOT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    DATA_ROOT = args.data_root
    args.output.mkdir(parents=True, exist_ok=True)
    cohort = add_context(load_cohort(args.cohort), args.data_root)
    cohort, fold_summary = fixed_folds(cohort)
    fold_summary.to_csv(args.output / "REPORT_FOLDS_V1.csv", index=False)
    cohort.to_csv(args.output / "cohort_input_LOCAL_ONLY.csv", index=False)
    metrics = []
    for w in WINDOWS:
        m, _ = evaluate(cohort, w, args.output)
        metrics.append(m)
    metrics = pd.concat(metrics, ignore_index=True)
    metrics.to_csv(args.output / "final_baseline_metrics.csv", index=False)
    fold_manifest = {"run_id": "REPORT_FOLDS_V1", "seed": SEED, "method": "5-fold StratifiedGroupKFold", "group_key": "repeat_participant_id", "n_participant": 46, "folds": 5, "assignment_reused_for_windows": list(WINDOWS)}
    (args.output / "REPORT_FOLDS_V1.json").write_text(json.dumps(fold_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"run_id": "FINAL_REPORT_COHORT_BASELINE_V2", "cohort_source": str(args.cohort), "cohort_sha256": sha256(args.cohort), "n_probe": len(cohort), "n_session": cohort.subject.nunique(), "n_participant": cohort.repeat_participant_id.nunique(), "label": "1 vs 2/3/4", "primary_window_s": 30, "sensitivity_windows_s": [10, 20], "model": "L2 logistic", "validation": "5-fold StratifiedGroupKFold, participant-disjoint", "bootstrap": "participant cluster, 1000 replicates", "old_1440_fallback_used": False}
    (args.output / "FINAL_REPORT_COHORT_BASELINE_V2.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(args.output, metrics, cohort)


if __name__ == "__main__":
    main()
