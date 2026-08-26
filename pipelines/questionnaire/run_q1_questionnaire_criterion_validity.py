#!/usr/bin/env python
"""Q1: session-level questionnaire criterion-validity audit.

This script deliberately reads only existing *derived* audit/bridge products.  It
does not open questionnaire workbooks, trial-level task files, raw radar data,
or C2C/C3 prediction scores.  All row-level outputs remain in the local derived
directory; Git-facing outputs are aggregate tables, figures, and this method.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.miscmodels.ordinal_model import OrderedModel


AUDIT_DIR = Path(r"D:\Project\厚粲杯\11_数据\derived\questionnaire_measurement_audit_v1")
BRIDGE = Path(r"D:\Project\厚粲杯\11_数据\derived\questionnaire_non_nir_session_bridge_v1\questionnaire_non_nir_session_bridge.csv")
DEFAULT_OUT = Path(r"D:\Project\厚粲杯\11_数据\derived\questionnaire_criterion_validity_v1")

QUESTION_KEY = "整个实验过程中，你走神"
QUESTION_FIELD = "mind_wandering_ordinal"
QUESTION_TITLE = "正式版第4题：整个实验过程中，你走神（想与任务无关的事情）的时间大概占多少"

# Frozen canonical probe-label semantics.  Keep the bridge column mapping
# explicit so a display-label correction cannot silently leave the upstream
# derived columns interpreted under the old 3/4 ordering.
LABEL_SEMANTICS = {
    1: "fully task-focused",
    2: "experiment-related but not task-focused",
    3: "task-unrelated thought / mind wandering",
    4: "mind blank",
}
LABEL_PROPORTION_COLUMNS = {
    1: "专注_proportion",
    2: "任务相关干扰_proportion",
    3: "走神_proportion",
    4: "大脑空白_proportion",
}


def bh(p: pd.Series) -> pd.Series:
    """Benjamini-Hochberg adjusted p values, with no hidden test expansion."""
    values = p.to_numpy(dtype=float)
    order = np.argsort(values)
    ranked = values[order] * len(values) / np.arange(1, len(values) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(values)
    out[order] = np.minimum(ranked, 1.0)
    return pd.Series(out, index=p.index)


def cluster_bootstrap_spearman(data: pd.DataFrame, x: str, y: str, cluster: str,
                               draws: int = 5000, seed: int = 20260826) -> tuple[float, float, float, float]:
    clean = data[[x, y, cluster]].dropna()
    rho, p = spearmanr(clean[x], clean[y])
    groups = list(clean.groupby(cluster, sort=False))
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    for _ in range(draws):
        sampled = rng.integers(0, len(groups), len(groups))
        boot = pd.concat([groups[i][1] for i in sampled], ignore_index=True)
        value = spearmanr(boot[x], boot[y]).statistic
        if np.isfinite(value):
            estimates.append(float(value))
    ci_low, ci_high = np.quantile(estimates, [0.025, 0.975])
    return float(rho), float(ci_low), float(ci_high), float(p)


def item_metadata() -> tuple[pd.DataFrame, float, int]:
    manifest = pd.read_csv(AUDIT_DIR / "questionnaire_measurement_manifest.csv")
    matches = manifest[(manifest["version"] == "formal_v1") & manifest["raw_field_or_item"].str.contains(QUESTION_KEY, na=False)].copy()
    if matches.empty:
        raise RuntimeError("The pre-audited formal_v1 mind-wandering item was not found.")
    missing = pd.read_csv(AUDIT_DIR / "missingness_summary.csv")
    m = missing[(missing["version"] == "formal_v1") & missing["raw_field_or_item"].str.contains(QUESTION_KEY, na=False)]
    # The audit has two formal exports; combine counts rather than averaging file rates.
    missing_rate = float(m["n_missing"].sum() / m["n_rows"].sum())
    return matches.drop_duplicates("raw_field_or_item"), missing_rate, int(m["n_rows"].sum())


def association_rows(data: pd.DataFrame) -> pd.DataFrame:
    planned = [
        ("probe", "label_1_complete_task_focus_proportion", "专注（label 1）比例", "专注_proportion"),
        ("probe", "label_2_task_related_interference_proportion", "任务相关干扰（label 2）比例", "任务相关干扰_proportion"),
        ("probe", "label_3_mind_wandering_proportion", "走神（label 3）比例", LABEL_PROPORTION_COLUMNS[3]),
        ("probe", "label_4_mind_blank_proportion", "大脑空白（label 4）比例", LABEL_PROPORTION_COLUMNS[4]),
        ("behavior", "commission_error_rate", "NoGo 漏按/commission error rate", "behavior_commission_rate"),
        ("behavior", "preempt_rate", "预按率（辅助行为指标）", "behavior_preempt_rate"),
        ("behavior", "go_rt_median_ms", "Go trial 中位 RT（RT variability 无既有场次字段）", "behavior_go_rt_median_ms"),
    ]
    rows = []
    for family, code, label, col in planned:
        rho, low, high, p = cluster_bootstrap_spearman(data, QUESTION_FIELD, col, "repeat_participant_id_questionnaire")
        rows.append({"analysis_family": family, "association_id": code, "criterion_label": label,
                     "questionnaire_field": QUESTION_FIELD, "test": "Spearman rho; participant-cluster bootstrap CI",
                     "n_sessions": int(data[[QUESTION_FIELD, col]].dropna().shape[0]),
                     "n_participants": int(data.loc[data[[QUESTION_FIELD, col]].notna().all(axis=1), "repeat_participant_id_questionnaire"].nunique()),
                     "effect_size": rho, "ci95_low": low, "ci95_high": high, "p_nominal": p})
    out = pd.DataFrame(rows)
    out["p_bh_planned_7"] = bh(out["p_nominal"])
    out["interpretation"] = np.select(
        [out["ci95_low"] > 0, out["ci95_high"] < 0],
        ["positive association; interpretation depends on criterion direction", "negative association; interpretation depends on criterion direction"],
        default="weak/no precise directional association (CI crosses zero)")
    return out


def clustered_ordinal_models(data: pd.DataFrame) -> pd.DataFrame:
    """Ordinal logit models with participant-cluster robust covariance.

    The current canonical bridge excludes the sub-099 restricted session.  The
    older 68-session random-intercept model is therefore not imported: reusing
    its result would silently change the analytic denominator.  This model uses
    the 67-session canonical bridge and preserves participant clustering.
    """
    specs = [
        ("probe_noncomplete_task_focus", ["noncomplete_task_focus_proportion"]),
        ("behavior_error_and_median_rt", ["behavior_commission_rate", "behavior_go_rt_median_ms"]),
    ]
    work = data.copy()
    work["noncomplete_task_focus_proportion"] = 1.0 - work["专注_proportion"]
    rows: list[dict] = []
    for model_name, predictors in specs:
        cols = [QUESTION_FIELD, "repeat_participant_id_questionnaire", *predictors]
        d = work[cols].dropna().copy()
        x = d[predictors].copy()
        for predictor in predictors:
            x[predictor] = (x[predictor] - x[predictor].mean()) / x[predictor].std(ddof=0)
        result = OrderedModel(d[QUESTION_FIELD].astype(int), x, distr="logit").fit(
            method="bfgs", disp=False, cov_type="cluster",
            cov_kwds={"groups": d["repeat_participant_id_questionnaire"]},
        )
        for predictor in predictors:
            beta, se, p = result.params[predictor], result.bse[predictor], result.pvalues[predictor]
            rows.append({"model": model_name, "term": predictor, "model_type": "ordinal logit; participant-cluster robust SE",
                         "n_sessions": len(d), "n_participants": d["repeat_participant_id_questionnaire"].nunique(),
                         "estimate_log_odds_per_1sd": beta, "se_cluster_robust": se, "odds_ratio_per_1sd": np.exp(beta),
                         "ci95_or_low": np.exp(beta - 1.96 * se), "ci95_or_high": np.exp(beta + 1.96 * se), "p_nominal": p})
    out = pd.DataFrame(rows)
    out["p_bh_planned_3"] = bh(out["p_nominal"])
    return out


def make_figures(data: pd.DataFrame, out: Path) -> list[str]:
    plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False})
    labels = ["<10%", "10–30%", "30–50%"]
    jitter = np.random.default_rng(20260826)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
    for ax, column, ylabel, color in [
        (axes[0], "专注_proportion", "Probe 完全任务聚焦（label 1）比例", "#2f6f8f"),
        (axes[1], "behavior_commission_rate", "正式行为 commission error rate", "#b85c38"),
    ]:
        for level in [1, 2, 3]:
            vals = data.loc[data[QUESTION_FIELD] == level, column].dropna()
            ax.scatter(level + jitter.uniform(-0.10, 0.10, len(vals)), vals, alpha=.68, color=color, s=26)
            if len(vals): ax.plot([level-.18, level+.18], [vals.median(), vals.median()], color="black", lw=2)
        ax.set_xticks([1, 2, 3], labels)
        ax.set_xlabel("事后自评走神比例（有序类别）")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=.25)
    fig.suptitle("Q1 问卷单题与既有外部效标：场次级候选图（重复被试未视为独立）", fontsize=12)
    path = out / "figure_candidate_questionnaire_probe_behavior.png"
    fig.savefig(path, dpi=240)
    plt.close(fig)
    return [path.name]


def write_summary(out: Path, metadata: pd.DataFrame, missing_rate: float, audit_n: int,
                  data: pd.DataFrame, associations: pd.DataFrame, mixed: pd.DataFrame, figs: list[str]) -> None:
    probe = associations[associations.analysis_family == "probe"]
    behavior = associations[associations.analysis_family == "behavior"]
    focus = probe[probe.association_id == "label_1_complete_task_focus_proportion"].iloc[0]
    err = behavior[behavior.association_id == "commission_error_rate"].iloc[0]
    mixed_probe = mixed[(mixed.model == "probe_noncomplete_task_focus") & (mixed.term == "noncomplete_task_focus_proportion")].iloc[0]
    mixed_error = mixed[(mixed.model == "behavior_error_and_median_rt") & (mixed.term == "behavior_commission_rate")].iloc[0]
    mixed_rt = mixed[(mixed.model == "behavior_error_and_median_rt") & (mixed.term == "behavior_go_rt_median_ms")].iloc[0]
    text = f"""# Q1 问卷单题的外部效标关联（criterion validity）

## 结论与范围

本次只检验一项已有、可确定性桥接的正式实验事后自评：{QUESTION_TITLE}。它是自编单题的场次级状态候选，并非已验证量表，也没有计算 Cronbach alpha 或 McDonald omega。审计原始问卷共 {audit_n} 行在该题上的加权缺失率为 {missing_rate:.1%}；最终桥接分析包括 {len(data)} 场次、{data['repeat_participant_id_questionnaire'].nunique()} 名 participant/group_subject_id（重复 participant 使用 cluster-robust covariance 与 cluster bootstrap 处理）。

问卷有序分布为 <10%: {(data[QUESTION_FIELD] == 1).sum()}，10–30%: {(data[QUESTION_FIELD] == 2).sum()}，30–50%: {(data[QUESTION_FIELD] == 3).sum()}，>50%: 0。因此不把 4 级空类别当作连续分数；主模型为 ordinal logit，并用 participant cluster-robust covariance 保留重复场次的聚类，补充关联使用 Spearman rho 与 participant-cluster bootstrap 95% CI。BH 仅在预定义的 7 个单变量 probe/behavior 关联及 3 个有序模型斜率内实施。

## 主要证据

- 会话级的“非完全任务聚焦”是 label 2/3/4 的合并，并不等同于“全部走神”。有序模型显示，自评更高的走神类别与更高的 label 2/3/4 比例相关，OR(每 1 SD) = {mixed_probe.odds_ratio_per_1sd:.2f}, 95% CI [{mixed_probe.ci95_or_low:.2f}, {mixed_probe.ci95_or_high:.2f}], p_BH = {mixed_probe.p_bh_planned_3:.4f}。其区间很宽，属于 convergent/criterion-supportive evidence，而不是对逐窗口状态的验证。
- 对 label 1 完全任务聚焦比例，Spearman rho = {focus.effect_size:.3f}, participant-cluster bootstrap 95% CI [{focus.ci95_low:.3f}, {focus.ci95_high:.3f}], p_BH = {focus.p_bh_planned_7:.4f}。方向应与“走神越高、任务聚焦越低”一致，但该相关不替代混合模型。
- 对正式行为的 commission error rate，Spearman rho = {err.effect_size:.3f}, 95% CI [{err.ci95_low:.3f}, {err.ci95_high:.3f}], p_BH = {err.p_bh_planned_7:.4f}。该结果只能说明与任务表现的效标关联强弱；不应把不精确或阴性结果写成“问卷无效”。
- 预定义的联合有序行为模型（error 与 median RT 同时进入）中，commission error 的 OR(每 1 SD) = {mixed_error.odds_ratio_per_1sd:.2f}, 95% CI [{mixed_error.ci95_or_low:.2f}, {mixed_error.ci95_or_high:.2f}], p_BH = {mixed_error.p_bh_planned_3:.4f}；median RT 的条件 OR = {mixed_rt.odds_ratio_per_1sd:.2f}, 95% CI [{mixed_rt.ci95_or_low:.2f}, {mixed_rt.ci95_or_high:.2f}], p_BH = {mixed_rt.p_bh_planned_3:.4f}。后者与其边际 Spearman 结果不一致，应视为协变量条件下、模型依赖的探索性支持，不能单独作强结论。

## 可解释性边界

- 只分析了已有桥接的一个单题。审计中其余 state-like、trait-like 题目没有可复用的确定性数值联接字段，本次不读取原始问卷来补建 inventory 或数据驱动扩展测试。
- trait-like 的“自评专注力”和“平时持续专注时长”在审计中为正式版 5 级自编单题，但当前桥接产物未提供它们的数值答案，故为不可解释/未分析，而非无关联。
- 当前既有正式行为输入无场次级 RT variability；仅报告 error、preempt 和 median RT。未重新提取 trial，未使用最终 C2C/C3 预测分数。
- 结果限于已桥接的北京正式实验场次；问卷是事后总体回顾，不能复制到 probe/window，也不能推广为规范化或诊断性量表。

## 产物与复现

- `questionnaire_criterion_manifest.csv`：本地行级资格与来源 manifest（不上传 GitHub）。
- `questionnaire_probe_association.csv`、`questionnaire_behavior_association.csv`：聚合关联结果。
- `questionnaire_ordinal_clustered_model.csv`：当前 67 场次 canonical bridge 上的有序模型。
- 图候选：{', '.join(figs)}。
"""
    (out / "questionnaire_criterion_validity_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--bootstrap-draws", type=int, default=5000)
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    metadata, missing_rate, audit_n = item_metadata()
    data = pd.read_csv(BRIDGE)
    required_label_columns = set(LABEL_PROPORTION_COLUMNS.values())
    missing_label_columns = sorted(required_label_columns.difference(data.columns))
    if missing_label_columns:
        raise RuntimeError(f"upstream bridge missing canonical label columns: {missing_label_columns}")
    # The bridge is the upstream source of the four probe proportions.  Verify
    # the intended 3/4 column mapping before any association is calculated.
    bridge_label_mapping = {str(label): column for label, column in LABEL_PROPORTION_COLUMNS.items()}
    eligible = data[(data["bridge_status"] == "linked_main_non_nir_session") & data[QUESTION_FIELD].notna()].copy()
    for column in [QUESTION_FIELD, "专注_proportion", "任务相关干扰_proportion", "大脑空白_proportion", "走神_proportion", "behavior_commission_rate", "behavior_preempt_rate", "behavior_go_rt_median_ms"]:
        eligible[column] = pd.to_numeric(eligible[column], errors="coerce")
    # Local only: pseudonymous session/participant IDs are retained solely for auditability.
    local_manifest = eligible[["subject", "repeat_participant_id_questionnaire", "site_questionnaire", "bridge_status", QUESTION_FIELD,
                              "probe_n_total", "专注_proportion", "任务相关干扰_proportion", "大脑空白_proportion", "走神_proportion",
                              "behavior_commission_rate", "behavior_preempt_rate", "behavior_go_rt_median_ms"]].copy()
    local_manifest.to_csv(out / "questionnaire_criterion_manifest.csv", index=False, encoding="utf-8-sig")
    associations = association_rows(eligible)
    associations.loc[associations.analysis_family == "probe"].to_csv(out / "questionnaire_probe_association.csv", index=False, encoding="utf-8-sig")
    associations.loc[associations.analysis_family == "behavior"].to_csv(out / "questionnaire_behavior_association.csv", index=False, encoding="utf-8-sig")
    mixed = clustered_ordinal_models(eligible)
    mixed.to_csv(out / "questionnaire_ordinal_clustered_model.csv", index=False, encoding="utf-8-sig")
    metadata.assign(audit_weighted_missing_rate=missing_rate, audit_rows=audit_n).to_csv(out / "questionnaire_item_metadata_reused.csv", index=False, encoding="utf-8-sig")
    figs = make_figures(eligible, out)
    write_summary(out, metadata, missing_rate, audit_n, eligible, associations, mixed, figs)
    (out / "run_manifest.json").write_text(json.dumps({"scope": "derived-products-only; no raw questionnaire/trial/C2C/C3 read",
        "n_sessions": len(eligible), "n_participants": int(eligible['repeat_participant_id_questionnaire'].nunique()),
        "inputs": [str(AUDIT_DIR), str(BRIDGE)], "bootstrap_draws": 5000, "seed": 20260826,
        "label_semantics": LABEL_SEMANTICS, "bridge_label_proportion_columns": bridge_label_mapping},
        ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
