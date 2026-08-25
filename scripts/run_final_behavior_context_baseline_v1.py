"""Freeze FINAL_BEHAVIOR_CONTEXT_BASELINE_V1 on the canonical Beijing cohort.

The primary target is fully task-focused (label 1) versus other non-fully
task-focused state (labels 2/3/4).  This deliberately contains no mmWave,
RGB, NIR, HRV, feature discovery, or high-complexity model.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯")
COHORT = ROOT / r"08_算法\output\40_正式实验\04_C2a_标签与样本单元审计\derived_20260826"
DATA = Path(r"J:\Data")
DEFAULT_OUT = ROOT / r"11_数据\derived\final_behavior_context_baseline_v1"
SEED = 20260826
WINDOWS = (10, 20, 30)  # 30 s primary; 10/20 s are prespecified sensitivities.
CONTEXT = ["block_num", "block_probe_fraction", "onset_rel_s"]
BEHAVIOR = ["b_trial_count", "b_rt_mean", "b_rt_median", "b_rt_sd", "b_rt_mad",
            "b_rt_cv", "b_rt_slope", "b_accuracy", "b_error_count", "b_error_rate",
            "b_omission_count", "b_omission_rate"]
FEATURE_SETS = {"C_context_only": CONTEXT, "B_behavior_only": BEHAVIOR,
                "C_plus_B": CONTEXT + BEHAVIOR}


def mad(x: pd.Series) -> float:
    x = np.asarray(x, dtype=float); x = x[np.isfinite(x)]
    return float(np.median(np.abs(x - np.median(x)))) if len(x) else np.nan


def cohort_table() -> tuple[pd.DataFrame, str]:
    report = ROOT / r"11_数据\derived\REPORT_ANALYSIS_COHORT\REPORT_ANALYSIS_COHORT.csv"
    # A future REPORT table must have the exact audited keys and mapping.  It is
    # preferred only when it can be validated, never silently merged by count.
    source = report if report.exists() else COHORT / "c2a_sample_manifest.csv"
    d = pd.read_csv(source, dtype={"subject_id": str})
    required = {"subject_id", "probe_id", "block_num", "probe_response", "probe_onset_time"}
    if not required.issubset(d.columns):
        raise ValueError(f"cohort source lacks required columns: {source}")
    if "window_s" in d:
        d = d.loc[pd.to_numeric(d.window_s, errors="coerce") == 30].copy()
    d["subject"] = d.subject_id.astype(str).str.zfill(3)
    d["label"] = pd.to_numeric(d.probe_response, errors="coerce")
    d = d[d.label.isin([1, 2, 3, 4])].copy()
    d["probe_onset_ms"] = pd.to_numeric(d.probe_onset_time, errors="coerce")
    d = d.dropna(subset=["probe_onset_ms"]).sort_values(["subject", "probe_onset_ms"])
    d = d.drop_duplicates(["subject", "probe_onset_ms"]).copy()
    groups = pd.read_csv(COHORT / "c2a_subject_group_map.csv", dtype=str)
    group_map = dict(zip(groups.subject_id.str.zfill(3), groups.group_subject_id))
    d["group_subject_id"] = d.subject.map(group_map)
    if d.group_subject_id.isna().any() or len(d) != 1440 or d.subject.nunique() != 72 or d.group_subject_id.nunique() != 46:
        raise ValueError("canonical cohort validation failed; do not substitute a different denominator")
    d["target_other_nonfully_focused"] = (d.label != 1).astype(int)
    d["block_num"] = pd.to_numeric(d.block_num, errors="coerce")
    d["block_probe_fraction"] = d.groupby(["subject", "block_num"]).cumcount()
    n = d.groupby(["subject", "block_num"])["probe_onset_ms"].transform("count")
    d["block_probe_fraction"] = np.where(n > 1, d.block_probe_fraction / (n - 1), 0.0)
    starts = d.groupby("subject").probe_onset_ms.transform("min")
    # This is overwritten by the first observed behavioral trial below where available.
    d["onset_rel_s"] = (d.probe_onset_ms - starts) / 1000.0
    return d.reset_index(drop=True), ("REPORT_ANALYSIS_COHORT" if report.exists() else "C2a_frozen_Beijing_canonical_fallback")


def behavior_for_window(base: pd.DataFrame, window_s: int) -> pd.DataFrame:
    rows, first_trial = [], {}
    for subject, probes in base.groupby("subject", sort=True):
        files = sorted((DATA / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv"))
        if not files:
            raise FileNotFoundError(f"missing behavior files for canonical subject {subject}")
        trials = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
        trials["_onset"] = pd.to_numeric(trials.get("absolute_onset_time"), errors="coerce")
        trials = trials[trials._onset.notna()].copy()
        trials = trials[trials.get("is_probe", 0).fillna(0).astype(str) != "1"].sort_values("_onset")
        if trials.empty:
            raise ValueError(f"no behavioral trials for canonical subject {subject}")
        first_trial[subject] = float(trials._onset.min())
        for ix, p in probes.iterrows():
            x = trials[(trials._onset >= p.probe_onset_ms - window_s * 1000) & (trials._onset < p.probe_onset_ms)].copy()
            rt = pd.to_numeric(x.get("rt"), errors="coerce")
            valid = rt[np.isfinite(rt)]
            correct = pd.to_numeric(x.get("correct"), errors="coerce")
            omission = pd.to_numeric(x.get("omission"), errors="coerce").fillna(0)
            n = len(x); err = (correct.fillna(0) != 1).astype(int)
            elapsed = (x._onset.to_numpy(float) - (p.probe_onset_ms - window_s * 1000)) / 1000.0
            valid_mask = np.isfinite(rt.to_numpy(float))
            slope = float(np.polyfit(elapsed[valid_mask], rt.to_numpy(float)[valid_mask], 1)[0]) if valid_mask.sum() >= 2 else np.nan
            rows.append({"row_id": ix, "b_trial_count": n, "b_rt_mean": valid.mean(),
                         "b_rt_median": valid.median(), "b_rt_sd": valid.std(ddof=1), "b_rt_mad": mad(valid),
                         "b_rt_cv": valid.std(ddof=1) / abs(valid.mean()) if len(valid) > 1 and valid.mean() else np.nan,
                         "b_rt_slope": slope, "b_accuracy": correct.mean() if n else np.nan,
                         "b_error_count": err.sum() if n else np.nan, "b_error_rate": err.mean() if n else np.nan,
                         "b_omission_count": omission.sum() if n else np.nan, "b_omission_rate": omission.mean() if n else np.nan})
    out = pd.DataFrame(rows).set_index("row_id").reindex(base.index)
    out["onset_rel_s"] = [(base.loc[i, "probe_onset_ms"] - first_trial[base.loc[i, "subject"]]) / 1000.0 for i in base.index]
    return out


def point_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pred = (p >= .5).astype(int); tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "balanced_accuracy": balanced_accuracy_score(y, pred), "sensitivity": tp / (tp + fn),
            "specificity": tn / (tn + fp), "brier": brier_score_loss(y, p),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def bootstrap(y: np.ndarray, p: np.ndarray, groups: np.ndarray, n_boot=1000) -> dict:
    rng = np.random.default_rng(SEED); unique = np.unique(groups); values = {k: [] for k in point_metrics(y, p)}
    for _ in range(n_boot):
        sampled = rng.choice(unique, len(unique), replace=True)
        idx = np.concatenate([np.flatnonzero(groups == g) for g in sampled])
        m = point_metrics(y[idx], p[idx])
        for k, v in m.items(): values[k].append(v)
    return {f"{k}_ci95_low": float(np.quantile(v, .025)) for k, v in values.items()} | {f"{k}_ci95_high": float(np.quantile(v, .975)) for k, v in values.items()}


def evaluate(d: pd.DataFrame, window_s: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    y, groups = d.target_other_nonfully_focused.to_numpy(), d.group_subject_id.to_numpy()
    folds = np.full(len(d), -1, dtype=int)
    split = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    for fold, (_, test) in enumerate(split.split(d, y, groups)): folds[test] = fold
    metrics, oof = [], []
    for name, features in FEATURE_SETS.items():
        x = d[features].apply(pd.to_numeric, errors="coerce")
        p = np.full(len(d), np.nan)
        for fold in range(5):
            train, test = folds != fold, folds == fold
            # Match the pre-existing frozen C2b low-complexity baseline: each
            # repeat participant receives equal total training weight, while
            # class weighting handles the 1 vs 2/3/4 imbalance.
            model = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler()),
                              ("logistic", LogisticRegression(C=1.0, class_weight="balanced", max_iter=3000, random_state=SEED + fold))])
            train_weight = pd.Series(groups[train]).groupby(pd.Series(groups[train])).transform(lambda s: 1.0 / len(s)).to_numpy()
            model.fit(x.loc[train], y[train], logistic__sample_weight=train_weight); p[test] = model.predict_proba(x.loc[test])[:, 1]
        row = {"window_s": window_s, "model": "logistic_l2_fixed", "feature_set": name,
               "n_probe": len(d), "n_session": d.subject.nunique(), "n_participant_groups": d.group_subject_id.nunique(),
               "positive_n": int(y.sum()), "positive_rate": y.mean(), "n_features": len(features)}
        row.update(point_metrics(y, p)); row.update(bootstrap(y, p, groups)); metrics.append(row)
        oof.append(pd.DataFrame({"subject": d.subject, "group_subject_id": groups, "fold": folds, "window_s": window_s,
                                 "feature_set": name, "target": y, "prediction": p}))
    return pd.DataFrame(metrics), pd.concat(oof, ignore_index=True)


def calibration(oof: pd.DataFrame) -> pd.DataFrame:
    d = oof.copy(); d["bin"] = pd.cut(d.prediction, bins=np.linspace(0, 1, 11), include_lowest=True)
    return d.groupby(["window_s", "feature_set", "bin"], observed=False).agg(n=("target", "size"),
        mean_prediction=("prediction", "mean"), observed_rate=("target", "mean")).reset_index()


def figures(oof: pd.DataFrame, cal: pd.DataFrame, out: Path) -> None:
    primary = oof[(oof.window_s == 30)].copy(); fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=160)
    for name, x in primary.groupby("feature_set"):
        fpr, tpr, _ = roc_curve(x.target, x.prediction); axes[0].plot(fpr, tpr, label=name)
    axes[0].plot([0, 1], [0, 1], "k--", lw=.8); axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="30 s OOF ROC", xlim=(0,1), ylim=(0,1)); axes[0].legend()
    for name, x in cal[cal.window_s == 30].groupby("feature_set"):
        axes[1].plot(x.mean_prediction, x.observed_rate, marker="o", label=name)
    axes[1].plot([0,1],[0,1],"k--",lw=.8); axes[1].set(xlabel="Mean predicted probability", ylabel="Observed rate", title="30 s calibration (10 bins)", xlim=(0,1), ylim=(0,1)); axes[1].legend()
    fig.tight_layout(); fig.savefig(out / "final_baseline_main_results.png", dpi=300); plt.close(fig)
    fig, ax = plt.subplots(figsize=(5,4), dpi=160)
    for name, x in cal[cal.window_s == 30].groupby("feature_set"): ax.plot(x.mean_prediction, x.observed_rate, marker="o", label=name)
    ax.plot([0,1],[0,1],"k--",lw=.8); ax.set(xlabel="Mean predicted probability", ylabel="Observed rate", title="Calibration, 30 s", xlim=(0,1), ylim=(0,1)); ax.legend(); fig.tight_layout(); fig.savefig(out / "calibration_30s.png", dpi=300); plt.close(fig)


def error_model(d: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Random-intercept Bayesian logistic mixed model; a robust fallback is explicit."""
    x = d.dropna(subset=["b_error_count", "b_trial_count"]).copy(); x = x[x.b_trial_count > 0]
    expanded = []
    for _, r in x.iterrows():
        n, e = int(r.b_trial_count), int(r.b_error_count)
        expanded.extend({"error": 1 if i < e else 0, "target": int(r.target_other_nonfully_focused), "group": r.group_subject_id} for i in range(n))
    z = pd.DataFrame(expanded)
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
        model = BinomialBayesMixedGLM.from_formula("error ~ target", {"group_re": "0 + C(group)"}, z)
        fit = model.fit_vb(); beta, sd = float(fit.fe_mean[1]), float(fit.fe_sd[1]); zval = beta / sd
        from math import erf, sqrt
        p = float(2 * (1 - .5 * (1 + erf(abs(zval) / sqrt(2)))))
        ans = pd.DataFrame([{"window_s": 30, "outcome": "trial_error", "predictor": "other_nonfully_task_focused",
            "model": "Bayesian_random_intercept_logistic_mixed_model", "n_probe_windows": len(x), "n_trials": len(z),
            "beta": beta, "or": float(np.exp(beta)), "ci95_beta_low": beta-1.96*sd, "ci95_beta_high": beta+1.96*sd,
            "ci95_or_low": float(np.exp(beta-1.96*sd)), "ci95_or_high": float(np.exp(beta+1.96*sd)), "p_approx": p,
            "note": "Variational-Bayes posterior normal approximation; no causal or RT inference."}])
    except Exception as exc:
        ans = pd.DataFrame([{"window_s": 30, "outcome": "trial_error", "model": "not_estimated", "note": str(exc)}])
    ans.to_csv(out / "preprobe_behavior_models.csv", index=False); return ans


def report(metrics: pd.DataFrame, err: pd.DataFrame, source: str, out: Path) -> None:
    m = metrics[metrics.window_s == 30].copy(); lines = ["# FINAL_BEHAVIOR_CONTEXT_BASELINE_V1", "", "状态：`COMPLETE`", "",
        "## 冻结定义", "", f"- Cohort source: `{source}`。`REPORT_ANALYSIS_COHORT` 未找到时，按预注册回退使用 C2a 北京 canonical cohort，且已验证为 1,440 probes / 72 sessions / 46 repeat-participant groups。",
        "- 标签：label 1 = 完全任务聚焦；label 2/3/4 = 其他非完全任务聚焦。阳性类是后者，不等同于全部走神。",
        "- 主窗口为 probe 前 30 s `[onset-30 s, onset)`；10 s、20 s 为预先规定敏感性，绝不用于选择主窗口。",
        "- 分割：固定 5-fold StratifiedGroupKFold，所有同一 repeat-participant 的 session 保持在同一 fold；填补、标准化、L2 logistic 均仅在训练 fold 拟合。", "",
        "## 30 s 主结果", "", "| Set | ROC-AUC (95% CI) | PR-AUC (95% CI) | Balanced accuracy | Sensitivity | Specificity | TN/FP/FN/TP |", "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in m.iterrows(): lines.append(f"| {r.feature_set} | {r.roc_auc:.3f} [{r.roc_auc_ci95_low:.3f}, {r.roc_auc_ci95_high:.3f}] | {r.pr_auc:.3f} [{r.pr_auc_ci95_low:.3f}, {r.pr_auc_ci95_high:.3f}] | {r.balanced_accuracy:.3f} | {r.sensitivity:.3f} | {r.specificity:.3f} | {r.tn}/{r.fp}/{r.fn}/{r.tp} |")
    lines += ["", "CI 为 participant-cluster bootstrap（1,000 次）。`calibration_table.csv` 与 PNG 图提供简单 10-bin OOF 校准检查。", "", "## 预先规定敏感性", "", "| Window | Set | ROC-AUC | PR-AUC | Balanced accuracy |", "|---:|---|---:|---:|---:|"]
    for _, r in metrics[metrics.window_s.isin([10, 20])].iterrows():
        lines.append(f"| {int(r.window_s)} s | {r.feature_set} | {r.roc_auc:.3f} | {r.pr_auc:.3f} | {r.balanced_accuracy:.3f} |")
    lines += ["", "这些为预先规定敏感性，不改变 30 s 主结论。", "", "## Probe 前错误率模型"]
    if not err.empty and err.iloc[0].get("model") != "not_estimated":
        e = err.iloc[0]; ptxt = "< .001" if float(e.p_approx) < .001 else f"= {float(e.p_approx):.3f}"
        lines += ["", f"30 s trial-level error 的随机截距 logistic mixed model：β = {float(e.beta):.3f}, OR = {float(e['or']):.3f}, 95% CI OR [{float(e.ci95_or_low):.3f}, {float(e.ci95_or_high):.3f}], p {ptxt}。"]
    lines += ["它只检验状态关联，不构成因果解释；RT 若无稳定证据不应被过度解释。", "", "## 限制", "", "- `REPORT_ANALYSIS_COHORT` 在本次运行时不存在，故记录为受验证的 C2a 北京 canonical fallback，未拼接任何 1,317/1,400/1,420 口径。", "- 这是行为/context 基线，不是传感器或多模态模型，也不能推断 RGB/NIR 的增量。", "- 二分类合并保留 label 2/3/4 的构念异质性，不能将其统称为走神。"]
    (out / "FINAL_BEHAVIOR_CONTEXT_BASELINE_RESULT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, default=DEFAULT_OUT); ap.add_argument("--publish-dir", type=Path); args = ap.parse_args()
    out = args.out; out.mkdir(parents=True, exist_ok=True)
    base, source = cohort_table(); all_m, all_oof = [], []
    for w in WINDOWS:
        behavioral = behavior_for_window(base, w)
        d = pd.concat([base, behavioral.drop(columns="onset_rel_s")], axis=1)
        # Behavioral trials, rather than the first probe, define task onset context.
        d["onset_rel_s"] = behavioral["onset_rel_s"]
        m, o = evaluate(d, w); all_m.append(m); all_oof.append(o)
        if w == 30: err = error_model(d, out)
    metrics, oof = pd.concat(all_m, ignore_index=True), pd.concat(all_oof, ignore_index=True)
    metrics.to_csv(out / "final_baseline_metrics.csv", index=False); oof.to_csv(out / "oof_predictions_LOCAL_ONLY.csv", index=False)
    schema = pd.DataFrame([{"feature_set": k, "feature": v, "family": "context" if v in CONTEXT else "behavior", "window_role": "fixed"} for k, vs in FEATURE_SETS.items() for v in vs])
    schema.to_csv(out / "final_baseline_feature_schema.csv", index=False)
    cal = calibration(oof); cal.to_csv(out / "calibration_table.csv", index=False); figures(oof, cal, out); report(metrics, err, source, out)
    (out / "run_manifest.json").write_text(json.dumps({"run_id":"FINAL_BEHAVIOR_CONTEXT_BASELINE_V1","cohort_source":source,"cohort":{"probes":1440,"sessions":72,"participant_groups":46},"primary_window_s":30,"sensitivity_windows_s":[10,20],"seed":SEED,"models":"L2 logistic only","excluded_modalities":["mmWave","RGB","NIR","HRV"],"row_level_local_only":["oof_predictions_LOCAL_ONLY.csv"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.publish_dir:
        args.publish_dir.mkdir(parents=True, exist_ok=True)
        for name in ["final_baseline_metrics.csv", "preprobe_behavior_models.csv", "FINAL_BEHAVIOR_CONTEXT_BASELINE_RESULT.md", "final_baseline_feature_schema.csv", "calibration_table.csv", "run_manifest.json", "calibration_30s.png", "final_baseline_main_results.png"]: shutil.copy2(out / name, args.publish_dir / name)


if __name__ == "__main__": main()
