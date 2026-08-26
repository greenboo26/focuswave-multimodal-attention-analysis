"""Build the local-only REPORT_ANALYSIS_COHORT and analyze probe labels/vigilance.

Input is restricted to the already-derived Beijing canonical identity, timeline,
probe, and behavioural-event assets.  This entry point does not open mmWave,
RGB, NIR, ECG, or RSP raw data and does not recover identities.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.genmod.cov_struct import Exchangeable
from statsmodels.genmod.families import Binomial, Gaussian
from statsmodels.genmod.generalized_estimating_equations import GEE, OrdinalGEE
from statsmodels.stats.multitest import multipletests


ROOT = Path(r"D:\Project\厚粲杯")
DERIVED = ROOT / "11_数据" / "derived"
SOURCE = DERIVED / "beijing_c2_identity_reuse_event_analysis_v2"
HARMONIZED = DERIVED / "beijing_zhuhai_canonical_harmonization_v1"
OUT = DERIVED / "report_cohort_label_vigilance_v1"
REPO = Path(__file__).resolve().parents[1]
PUBLIC = REPO / "docs" / "results" / "report_cohort_label_vigilance_v1"

LABELS = {1: "fully_task_focused", 2: "experiment_related_not_task_focused",
          3: "task_unrelated_thought", 4: "no_specific_thought"}
VIGILANCE = {1: "very_sleepy", 2: "rather_sleepy", 3: "rather_alert", 4: "very_alert"}


def bh(rows: list[dict]) -> None:
    valid = [i for i, r in enumerate(rows) if pd.notna(r.get("p_value"))]
    if valid:
        _, q, _, _ = multipletests([rows[i]["p_value"] for i in valid], method="fdr_bh")
        for i, value in zip(valid, q):
            rows[i]["q_value_bh"] = float(value)
    for r in rows:
        r.setdefault("q_value_bh", np.nan)


def ci(result, term: str) -> tuple[float, float, float, float]:
    est, se = float(result.params[term]), float(result.bse[term])
    return est, se, est - 1.96 * se, est + 1.96 * se


def add_model(rows: list[dict], *, family: str, outcome: str, term: str, result, n: int,
              n_people: int, effect: str, scale: str = "log_odds") -> None:
    est, se, low, high = ci(result, term)
    row = {"model_family": family, "outcome": outcome, "term": term, "estimate": est,
           "se": se, "ci95_low": low, "ci95_high": high, "p_value": float(result.pvalues[term]),
           "n_probe": n, "n_participants": n_people, "effect_scale": scale, "status": "fit"}
    if effect == "or":
        row.update(effect_size=math.exp(est), effect_ci95_low=math.exp(low), effect_ci95_high=math.exp(high))
    elif effect == "percent":
        row.update(effect_size=(math.exp(est) - 1) * 100, effect_ci95_low=(math.exp(low) - 1) * 100,
                   effect_ci95_high=(math.exp(high) - 1) * 100)
    else:
        row.update(effect_size=est, effect_ci95_low=low, effect_ci95_high=high)
    rows.append(row)


def fit_binomial(frame: pd.DataFrame, formula: str, outcome: str, terms: list[str], family: str,
                 rows: list[dict], weight_col: str | None = None) -> None:
    try:
        weights = frame[weight_col].to_numpy(float) if weight_col else None
        model = GEE.from_formula(formula, groups="repeat_participant_id", data=frame,
                                 family=Binomial(), cov_struct=Exchangeable(), weights=weights)
        result = model.fit()
        for term in terms:
            add_model(rows, family=family, outcome=outcome, term=term, result=result, n=len(frame),
                      n_people=frame.repeat_participant_id.nunique(), effect="or")
    except Exception as exc:
        for term in terms:
            rows.append({"model_family": family, "outcome": outcome, "term": term, "status": f"failed: {exc}"})


def fit_gaussian(frame: pd.DataFrame, formula: str, outcome: str, terms: list[str], rows: list[dict]) -> None:
    try:
        result = GEE.from_formula(formula, groups="repeat_participant_id", data=frame,
                                  family=Gaussian(), cov_struct=Exchangeable()).fit()
        for term in terms:
            add_model(rows, family="participant_clustered_GEE", outcome=outcome, term=term, result=result,
                      n=len(frame), n_people=frame.repeat_participant_id.nunique(), effect="percent", scale="log_ratio")
    except Exception as exc:
        for term in terms:
            rows.append({"model_family": "participant_clustered_GEE", "outcome": outcome, "term": term,
                         "status": f"failed: {exc}"})


def fit_ordinal(frame: pd.DataFrame, formula: str, outcome: str, terms: list[str], rows: list[dict]) -> None:
    try:
        result = OrdinalGEE.from_formula(formula, groups="repeat_participant_id", data=frame,
                                         cov_struct=Exchangeable()).fit()
        for term in terms:
            add_model(rows, family="participant_clustered_ordinal_GEE", outcome=outcome, term=term, result=result,
                      n=len(frame), n_people=frame.repeat_participant_id.nunique(), effect="or")
    except Exception as exc:
        for term in terms:
            rows.append({"model_family": "participant_clustered_ordinal_GEE", "outcome": outcome, "term": term,
                         "status": f"failed: {exc}"})


def load_cohort() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event = pd.read_csv(SOURCE / "formal_behavior_longitudinal_v1" / "probe_event_level_behavior.csv")
    crosswalk = pd.read_csv(HARMONIZED / "beijing_zhuhai_person_session_crosswalk.csv", dtype={"session_id": str})
    crosswalk = crosswalk[(crosswalk.site == "Beijing") & (crosswalk.include_in_shared_primary == 1)].copy()
    event["session_id"] = "sub-" + event.subject_id.astype(int).astype(str).str.zfill(3)
    cohort = event.merge(crosswalk[["session_id", "formal_session_index", "collection_reason"]], on="session_id",
                         how="left", validate="many_to_one")
    if len(cohort) != 1400 or cohort.repeat_participant_id.isna().any() or cohort.formal_session_index.isna().any():
        raise RuntimeError("canonical event/crosswalk merge is not the expected 1,400 fully linked probes")
    cohort["probe_state"] = cohort.probe_response.astype(int).map(LABELS)
    cohort["vigilance_level"] = cohort.probe_vigilance.astype(int).map(VIGILANCE)
    cohort["session_probe_index"] = cohort.groupby("session_id").cumcount() + 1
    cohort["block_probe_index"] = cohort.groupby(["session_id", "block_num"]).cumcount() + 1
    cohort["time_on_task"] = cohort.probe_progress.astype(float)
    cohort["label_1_fully_task_focused"] = (cohort.probe_response == 1).astype(int)
    cohort["log_pre10_rt_median"] = np.log(cohort.pre10_rt_median_ms.where(cohort.pre10_rt_median_ms > 0))

    raw = pd.read_csv(ROOT / "08_算法" / "output" / "40_正式实验" / "04_C2a_标签与样本单元审计" /
                      "derived_20260826" / "c2a_sample_manifest.csv")
    raw = raw.drop_duplicates(["subject_id", "probe_onset_time"])
    return cohort, raw, crosswalk


def make_summary(cohort: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    def add(domain, level, count, denominator=None, note=""):
        rows.append({"domain": domain, "level": str(level), "count": int(count),
                     "denominator": int(denominator) if denominator is not None else np.nan,
                     "percent": (100 * count / denominator) if denominator else np.nan, "note": note})
    add("cohort", "natural_persons", cohort.repeat_participant_id.nunique())
    add("cohort", "sessions", cohort.session_id.nunique())
    add("cohort", "valid_probes", len(cohort))
    for value, name in LABELS.items(): add("probe_state", name, (cohort.probe_response == value).sum(), len(cohort))
    for value, name in VIGILANCE.items(): add("vigilance", name, (cohort.probe_vigilance == value).sum(), len(cohort))
    add("source_scope", "C2a_canonical_sessions", raw.subject_id.nunique())
    add("source_scope", "C2a_canonical_probes", len(raw))
    add("exclusion", "C2_session_without_valid_timeline", 20, 1440, "sub-099; not in REPORT_ANALYSIS_COHORT")
    add("exclusion", "valid_timeline_outside_C2_universe", 20, None, "sub-067; not counted in C2a 1,440 source probes")
    add("coverage", "fourth_or_later_session_probes_retained", (cohort.formal_session_index >= 4).sum(), len(cohort),
        "retained in primary cohort")
    return pd.DataFrame(rows)


def models(cohort: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    # OrdinalGEE has threshold intercepts, so its design must omit the ordinary
    # intercept. Explicit binary contrasts avoid a nonidentified threshold /
    # intercept combination in statsmodels 0.14.
    cohort = cohort.copy()
    cohort["block2"] = (cohort.block_num == 2).astype(int)
    cohort["label2"] = (cohort.probe_response == 2).astype(int)
    cohort["label3"] = (cohort.probe_response == 3).astype(int)
    cohort["label4"] = (cohort.probe_response == 4).astype(int)
    base_terms = ["C(block_num)[T.2]", "time_on_task", "C(block_num)[T.2]:time_on_task"]
    for value, name in LABELS.items():
        d = cohort.copy(); d["state"] = (d.probe_response == value).astype(int)
        fit_binomial(d, "state ~ C(block_num) * time_on_task", f"probe_state:{name}", base_terms,
                     "participant_clustered_GEE_one_vs_rest", rows)
    fit_ordinal(cohort, "probe_vigilance ~ 0 + block2 + time_on_task + block2:time_on_task", "vigilance_ordinal",
                ["block2", "time_on_task", "block2:time_on_task"], rows)
    relation_terms = ["label2", "label3", "label4"]
    fit_ordinal(cohort, "probe_vigilance ~ 0 + label2 + label3 + label4 + block2 + time_on_task", "vigilance_by_probe_state",
                relation_terms, rows)
    err = cohort.dropna(subset=["pre10_error_rate", "pre10_n_trials"]).copy()
    fit_binomial(err, "pre10_error_rate ~ probe_vigilance + C(block_num) + time_on_task", "pre10_error_rate_by_vigilance",
                 ["probe_vigilance"], "participant_clustered_GEE_binomial_rate", rows, weight_col="pre10_n_trials")
    rt = cohort.dropna(subset=["log_pre10_rt_median"]).copy()
    fit_gaussian(rt, "log_pre10_rt_median ~ probe_vigilance + C(block_num) + time_on_task",
                 "pre10_rt_median_by_vigilance", ["probe_vigilance"], rows)
    bh(rows)
    return pd.DataFrame(rows)


def figures(cohort: pd.DataFrame) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True); PUBLIC.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "Arial", "font.size": 10})
    colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
    paths = []
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    for value, color in zip(range(1, 5), colors):
        g = cohort.groupby(["block_num", "block_probe_index"])["probe_response"].apply(lambda x: (x == value).mean()).reset_index(name="proportion")
        for block, part in g.groupby("block_num"):
            axes[0].plot(part.block_probe_index, part.proportion, color=color, alpha=.35 if block == 1 else 1,
                         linestyle="--" if block == 1 else "-", label=f"{LABELS[value]} (B{block})")
    axes[0].set(xlabel="Probe position within block", ylabel="Observed proportion", title="Four probe states over time-on-task")
    axes[0].legend(fontsize=6, ncol=2, frameon=False)
    v = cohort.groupby(["block_num", "block_probe_index"])["probe_vigilance"].agg(["mean", "count", "std"]).reset_index()
    v["se"] = v["std"] / np.sqrt(v["count"])
    for block, part in v.groupby("block_num"):
        axes[1].errorbar(part.block_probe_index, part["mean"], yerr=1.96 * part.se, marker="o", ms=3,
                         linestyle="-", capsize=2, label=f"Block {block}")
    axes[1].set(xlabel="Probe position within block", ylabel="Mean vigilance (1–4)", ylim=(1, 4),
                title="Vigilance over time-on-task")
    axes[1].legend(frameon=False)
    path = OUT / "report_cohort_label_vigilance_trajectory_v1.png"; fig.savefig(path, dpi=300, bbox_inches="tight"); plt.close(fig)
    shutil.copy2(path, PUBLIC / path.name); paths.append(path)

    fig, ax = plt.subplots(figsize=(6.5, 4), constrained_layout=True)
    table = pd.crosstab(cohort.probe_response, cohort.probe_vigilance, normalize="index")
    bottom = np.zeros(4)
    for value, color in zip(range(1, 5), colors):
        vals = table.reindex(index=range(1, 5), columns=range(1, 5), fill_value=0)[value].to_numpy()
        ax.bar(range(1, 5), vals, bottom=bottom, color=color, label=VIGILANCE[value]); bottom += vals
    ax.set(xlabel="Probe state code (1–4; see schema)", ylabel="Within-state proportion", ylim=(0, 1),
           title="Vigilance distribution by four probe states")
    ax.legend(title="Vigilance", frameon=False, fontsize=8)
    path = OUT / "report_cohort_label_vigilance_cross_v1.png"; fig.savefig(path, dpi=300, bbox_inches="tight"); plt.close(fig)
    shutil.copy2(path, PUBLIC / path.name); paths.append(path)
    return paths


def report(cohort: pd.DataFrame, summary: pd.DataFrame, model: pd.DataFrame) -> None:
    def display(outcome, term):
        x = model[(model.outcome == outcome) & (model.term == term)].iloc[0]
        if x.effect_scale == "log_ratio":
            return f"change={x.effect_size:.2f}%, 95% CI [{x.effect_ci95_low:.2f}%, {x.effect_ci95_high:.2f}%], p={x.p_value:.3g}, q={x.q_value_bh:.3g}"
        return f"OR={x.effect_size:.2f}, 95% CI [{x.effect_ci95_low:.2f}, {x.effect_ci95_high:.2f}], p={x.p_value:.3g}, q={x.q_value_bh:.3g}"
    lines = ["# REPORT_COHORT_LABEL_VIGILANCE_V1", "", "状态：`COMPLETE_BEHAVIOR_ONLY`", "",
             "## 唯一母表口径", "", "`REPORT_ANALYSIS_COHORT` 是本报告主线唯一行级母表，仅存于本地 derived 目录。它复用既有北京 deterministic identity/session/timeline/probe/behavior 资产，包含 46 名自然人、70 个正式 session 和 1,400 个有效 probe。每个 session 有 20 probe，B1/B2 各 10 probe。", "",
             "C2a canonical manifest 的 72 sessions、1,440 probe 是输入宇宙；其中 sub-099 的 20 probes 因 C2 session 没有有效 timeline 被排除。另有 sub-067 具有有效 timeline 但不在 C2 universe，故不计入 1,440，也不作为 missing。这样主表为 70/1,400。第 4 次 session 的 20 probes 完整保留。其他硬盘数据均为“暂未纳入本报告主线”，不是 missing。", "",
             "## 模型与样本", "", "四分类状态使用以参与者聚类的 one-vs-rest logistic GEE；vigilance 使用以参与者聚类的 cumulative-logit ordinal GEE；probe 前 10 s 错误率使用按可用试次数加权的 binomial GEE，RT 中位数使用 log-RT Gaussian GEE。模型均调整 block、block 内 probe progress，状态–vigilance 关系模型也调整这两个时间变量。效应为每 1.0 block-progress 或每 1 点 vigilance 的 OR/百分比变化；每个拟合使用 1,400 probes、46 人，RT/错误率的实际覆盖见模型表。全部计划项在本轮 BH-FDR 校正。", "",
             "## 主要结果", "",
             f"- label 1（fully task-focused）随 block 内 progress 下降：{display('probe_state:fully_task_focused', 'time_on_task')}。其余三类状态的完整结果见模型表，不能将 labels 2/3/4 统称为 mind-wandering。",
             f"- vigilance 随 progress 的 ordinal 变化：{display('vigilance_ordinal', 'time_on_task')}。",
             f"- 相比 label 1，label 2 对应的更高 vigilance 优势：{display('vigilance_by_probe_state', 'label2')}；label 3：{display('vigilance_by_probe_state', 'label3')}；label 4：{display('vigilance_by_probe_state', 'label4')}。",
             f"- 每增加 1 点 vigilance，probe 前 10 s 错误率的方向：{display('pre10_error_rate_by_vigilance', 'probe_vigilance')}；RT 中位数的比例变化：{display('pre10_rt_median_by_vigilance', 'probe_vigilance')}。", "",
             "## 限制", "", "这是北京已链接正式行为 cohort 的关联分析，不推断因果或生理机制，不外推珠海。GEE 处理 participant 内相关但不是 subject-specific random-intercept effect；状态轨迹为四个二元边际模型，故不是单一多项式模型。probe 前 10 s 行为窗是既有派生指标。", "",
             "## 产物", "", "- `report_analysis_cohort.csv`：本地行级母表，含 pseudonymous participant/session key，禁止上传。", "- `label_vigilance_summary.csv`：本地脱敏汇总。", "- `label_vigilance_models.csv`：本地脱敏模型结果。", "- Git version includes this runnable script, field schema, this methods/result report, and two aggregate figures only."]
    (OUT / "REPORT_COHORT_LABEL_VIGILANCE_RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (PUBLIC / "REPORT_COHORT_LABEL_VIGILANCE_RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cohort, raw, crosswalk = load_cohort()
    keep = ["repeat_participant_id", "session_id", "formal_session_index", "collection_reason", "subject_id", "block_num",
            "session_probe_index", "block_probe_index", "time_on_task", "probe_response", "probe_state", "probe_vigilance", "vigilance_level",
            "probe_onset_time", "pre10_error_rate", "pre10_rt_median_ms", "pre10_rt_sd_ms", "pre10_n_trials"]
    cohort[keep].to_csv(OUT / "report_analysis_cohort.csv", index=False, encoding="utf-8-sig")
    summary = make_summary(cohort, raw); summary.to_csv(OUT / "label_vigilance_summary.csv", index=False, encoding="utf-8-sig")
    model = models(cohort); model.to_csv(OUT / "label_vigilance_models.csv", index=False, encoding="utf-8-sig")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    # These two tables contain counts/model aggregates only, never participant
    # or session keys, and are the public reproducibility companions.
    summary.to_csv(PUBLIC / "label_vigilance_summary.csv", index=False, encoding="utf-8-sig")
    model.to_csv(PUBLIC / "label_vigilance_models.csv", index=False, encoding="utf-8-sig")
    figures(cohort); report(cohort, summary, model)
    manifest = {"run_id": "REPORT_COHORT_LABEL_VIGILANCE_V1", "n_source_c2a_sessions": int(raw.subject_id.nunique()),
                "n_source_c2a_probes": len(raw), "n_report_people": int(cohort.repeat_participant_id.nunique()),
                "n_report_sessions": int(cohort.session_id.nunique()), "n_report_probes": len(cohort),
                "fourth_or_later_session_probes_retained": int((cohort.formal_session_index >= 4).sum()),
                "raw_modalities_opened": False, "other_drives_status": "not_included_not_missing"}
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
