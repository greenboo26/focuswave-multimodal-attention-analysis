#!/usr/bin/env python
"""Build the Git-safe Issue #13 psychometric evidence matrix.

The script only consumes aggregate CSVs from already executed canonical/supporting
producers. It does not read raw questionnaires, trial rows, or sensor outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


FIELDS = [
    "evidence_id", "domain", "construct_class", "evidence", "cohort",
    "n_sessions", "n_observations", "n_participants", "analysis_unit", "direction", "effect",
    "ci95", "p", "q", "status", "product_implication", "source",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise KeyError(criteria)


def fmt(value: str, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def row(**kwargs: str) -> dict[str, str]:
    return {field: kwargs.get(field, "") for field in FIELDS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q1-dir", type=Path, required=True)
    parser.add_argument("--label-models", type=Path, required=True)
    parser.add_argument("--repeat-models", type=Path, required=True)
    parser.add_argument("--repeat-sensitivity", type=Path, required=True)
    parser.add_argument("--repeat-loso", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    q_probe = read_csv(args.q1_dir / "questionnaire_probe_association.csv")
    q_beh = read_csv(args.q1_dir / "questionnaire_behavior_association.csv")
    q_ord = read_csv(args.q1_dir / "questionnaire_ordinal_clustered_model.csv")
    label = read_csv(args.label_models)
    repeat = read_csv(args.repeat_models)
    repeat_sens = read_csv(args.repeat_sensitivity)
    loso = read_csv(args.repeat_loso)

    matrix: list[dict[str, str]] = []
    for evidence_id, source_rows, criteria, domain, construct, evidence, unit, product in [
        ("Q1-PROBE-L1", q_probe, {"association_id": "label_1_complete_task_focus_proportion"}, "criterion", "state", "问卷走神比例 vs Probe label 1 完全任务聚焦比例", "session", "可作为场次级外部效标；不能作为实时状态验证"),
        ("Q1-PROBE-L2", q_probe, {"association_id": "label_2_task_related_interference_proportion"}, "criterion", "state", "问卷走神比例 vs Probe label 2 任务相关干扰比例", "session", "支持状态构念的收敛方向，但不升级为量表效度"),
        ("Q1-PROBE-L3", q_probe, {"association_id": "label_3_mind_wandering_proportion"}, "criterion", "state", "问卷走神比例 vs Probe label 3 走神比例", "session", "支持相关状态证据；保持四类语义，不并入 mind-wandering 总类"),
        ("Q1-PROBE-L4", q_probe, {"association_id": "label_4_mind_blank_proportion"}, "criterion", "state", "问卷走神比例 vs Probe label 4 大脑空白比例", "session", "支持状态构念的方向性关联；不替代 Probe 事件测量"),
        ("Q1-BEH-COMMISSION", q_beh, {"association_id": "commission_error_rate"}, "criterion", "state", "问卷走神比例 vs commission error rate", "session", "可进入产品报告的外部效标桥接；效应较小，不能单独作稳定能力结论"),
        ("Q1-BEH-PREEMPT", q_beh, {"association_id": "preempt_rate"}, "criterion", "state", "问卷走神比例 vs preempt rate", "session", "不作为主产品指标；仅保留为弱/不精确辅助证据"),
        ("Q1-BEH-RT", q_beh, {"association_id": "go_rt_median_ms"}, "criterion", "state", "问卷走神比例 vs Go-trial median RT", "session", "当前不支持方向性产品结论；场次级 RT variability 尚未有既有字段"),
    ]:
        r = find(source_rows, **criteria)
        matrix.append(row(evidence_id=evidence_id, domain=domain, construct_class=construct,
                          evidence=evidence, cohort="Beijing canonical questionnaire bridge",
                          n_sessions=r["n_sessions"], n_observations=r["n_sessions"], n_participants=r["n_participants"],
                          analysis_unit=unit, direction=r["interpretation"],
                          effect=f"Spearman rho={fmt(r['effect_size'])}",
                          ci95=f"[{fmt(r['ci95_low'])}, {fmt(r['ci95_high'])}]",
                          p=f"{float(r['p_nominal']):.4g}", q=f"{float(r['p_bh_planned_7']):.4g}",
                          status="PARTIAL", product_implication=product,
                          source="Q1 questionnaire criterion-validity producer"))

    for evidence_id, criteria, evidence, product in [
        ("Q1-ORD-PROBE", {"model": "probe_noncomplete_task_focus", "term": "noncomplete_task_focus_proportion"}, "有序模型：非完全任务聚焦比例 vs 问卷走神等级", "可作为收敛/效标支持；不能解释为逐 Probe 状态准确率"),
        ("Q1-ORD-ERROR", {"model": "behavior_error_and_median_rt", "term": "behavior_commission_rate"}, "联合有序模型：commission error vs 问卷走神等级", "保留为模型依赖的辅助效标证据"),
        ("Q1-ORD-RT", {"model": "behavior_error_and_median_rt", "term": "behavior_go_rt_median_ms"}, "联合有序模型：median RT vs 问卷走神等级", "仅作为探索性条件关联；不单独进入产品主结论"),
    ]:
        r = find(q_ord, **criteria)
        matrix.append(row(evidence_id=evidence_id, domain="criterion", construct_class="state",
                          evidence=evidence, cohort="Beijing canonical questionnaire bridge",
                          n_sessions=r["n_sessions"], n_observations=r["n_sessions"], n_participants=r["n_participants"],
                          analysis_unit="session; participant-cluster robust SE", direction="positive model association",
                          effect=f"OR per 1 SD={fmt(r['odds_ratio_per_1sd'], 2)}",
                          ci95=f"[{fmt(r['ci95_or_low'], 2)}, {fmt(r['ci95_or_high'], 2)}]",
                          p=f"{float(r['p_nominal']):.4g}", q=f"{float(r['p_bh_planned_3']):.4g}",
                          status="PARTIAL", product_implication=product,
                          source="Q1 questionnaire criterion-validity producer"))

    for evidence_id, criteria, evidence, product in [
        ("BEHAV-LABEL1-TIME", {"outcome": "probe_state:fully_task_focused", "term": "time_on_task"}, "Probe label 1 随 block 内 progress 的变化", "支持状态测量对任务进程敏感；产品应报告时间/阶段校正后的状态指标"),
        ("BEHAV-VIG-TIME", {"outcome": "vigilance_ordinal", "term": "time_on_task"}, "Probe vigilance 随 task progress 的变化", "支持警觉状态的时间敏感性；不是稳定个体能力信度"),
        ("BEHAV-VIG-ERROR", {"outcome": "pre10_error_rate_by_vigilance", "term": "probe_vigilance"}, "vigilance 与 Probe 前 10 s error rate", "是行为外部效标支持；适合状态层，不适合 trait 包装"),
    ]:
        r = find(label, **criteria)
        matrix.append(row(evidence_id=evidence_id, domain="validity", construct_class="state",
                          evidence=evidence, cohort="70 sessions / 46 participants / 1,400 probes",
                          n_sessions="70", n_observations=r["n_probe"], n_participants=r["n_participants"],
                          analysis_unit="probe; participant-clustered GEE", direction="model-defined",
                          effect=f"OR={fmt(r['effect_size'], 2)}", ci95=f"[{fmt(r['effect_ci95_low'], 2)}, {fmt(r['effect_ci95_high'], 2)}]",
                          p=f"{float(r['p_value']):.4g}", q=f"{float(r['q_value_bh']):.4g}", status="PARTIAL",
                          product_implication=product, source="canonical label/vigilance validity producer"))

    for evidence_id, term, evidence, product in [
        ("REPEAT-STATE-ORDER", "session_order", "重复 session：label 1 的 session-order 主效应", "不能作为稳定 trait 信度；至少需要 session-order/进度校正"),
        ("REPEAT-STATE-INTERACTION", "progress_x_session", "重复 session：label 1 的 progress × session-order", "状态指标对任务进程的变化在重复 session 中方向一致；仍不是 test-retest ICC"),
        ("REPEAT-ERROR-ORDER", "session_order", "重复 session：pre10 error 的 session-order", "行为表现存在练习/场次结构；产品报告应避免把跨场次绝对分数当个人能力"),
    ]:
        r = find(repeat, outcome=("probe_state: response=1 fully task-focused" if "STATE" in evidence_id else "pre10 error rate (binomial numerator/denominator)"), term=term)
        s = find(repeat_sens, outcome=r["outcome"], term=term)
        direction = "主/最早三场敏感性同向"
        matrix.append(row(evidence_id=evidence_id, domain="reliability_sensitivity", construct_class="state",
                          evidence=evidence, cohort="70 sessions / 46 participants / 1,400 probes (sensitivity: 69 sessions)",
                          n_sessions=r["n_sessions"], n_observations=r["n_probes"], n_participants=r["n_participants"],
                          analysis_unit="probe; participant random-intercept mixed model", direction=direction,
                          effect=f"primary {r['effect_size_label']}={fmt(r['effect_size'], 2)}; sensitivity={fmt(s['effect_size'], 2)}",
                          ci95=f"primary [{fmt(r['effect_ci95_low'], 2)}, {fmt(r['effect_ci95_high'], 2)}]; sensitivity [{fmt(s['effect_ci95_low'], 2)}, {fmt(s['effect_ci95_high'], 2)}]",
                          p=f"primary {float(r['p_nominal']):.4g}; sensitivity {float(s['p_nominal']):.4g}",
                          q=f"primary {float(r['p_bh_focal_8']):.4g}; sensitivity {float(s['p_bh_focal_8']):.4g}",
                          status="PARTIAL", product_implication=product, source="repeat-session supporting producer"))

    b0 = find(loso, target="nonfocus_vs_focus", feature_set="B0")
    m1 = find(loso, target="nonfocus_vs_focus", feature_set="M1")
    matrix.append(row(evidence_id="REPEAT-GROUPED-LOSO", domain="generalizability", construct_class="state",
                      evidence="participant-disjoint repeated-participant LOSO：behavior baseline vs mmWave M1", cohort="71 sessions / 46 repeated participants / 1,317 probes",
                      n_sessions=b0["sessions"], n_observations=b0["n"], n_participants=b0["repeat_participants"], analysis_unit="probe; held-out repeat_participant_id",
                      direction="B0 > M1 in AUC", effect=f"B0 AUC={fmt(b0['roc_auc'], 3)}; M1 AUC={fmt(m1['roc_auc'], 3)}",
                      ci95=f"B0 [{fmt(json.loads(b0['roc_auc_ci95'])[0], 3)}, {fmt(json.loads(b0['roc_auc_ci95'])[1], 3)}]; M1 [{fmt(json.loads(m1['roc_auc_ci95'])[0], 3)}, {fmt(json.loads(m1['roc_auc_ci95'])[1], 3)}]",
                      p="NA (bootstrap CI only)", q="NA", status="PARTIAL",
                      product_implication="重复被试外推仍应以 behavior/context 为锚；不把 mmWave 增量包装成心理测验信度证据",
                      source="repeat-participant grouped LOSO sensitivity"))

    matrix.extend([
        row(evidence_id="MEASURE-STRUCTURE", domain="reliability", construct_class="trait/state", evidence="正式问卷多题量表、反向计分、alpha/omega、因子结构", cohort="212 audited item/design records; formal questionnaire sources included",
                    n_sessions="134 formal questionnaire rows", n_observations="212 item/design records", n_participants="未确定", analysis_unit="item inventory / respondent source", direction="未建立可核验多题量表",
                    effect="NA", ci95="NA", p="NA", q="NA", status="BLOCKED",
                    product_implication="不得把单题组合成标准化量表；不得宣称内部一致性或结构效度",
                    source="questionnaire measurement audit"),
        row(evidence_id="TRAIT-SINGLE-ITEM", domain="reliability", construct_class="trait-like", evidence="自评专注力、平时持续专注时长单题", cohort="formal questionnaire inventory; numeric bridge unavailable",
                    n_sessions="未形成可分析桥接", n_observations="未形成可分析桥接", n_participants="未形成可分析桥接", analysis_unit="session-level retrospective single item", direction="未分析；不是无关联",
                    effect="NA", ci95="NA", p="NA", q="NA", status="BLOCKED",
                    product_implication="只能作为描述性背景/候选稳定个体指标；当前不得包装为能力/特质分数",
                    source="questionnaire measurement audit + Q1 bridge"),
        row(evidence_id="STATE-ITEM-BRIDGE", domain="validity", construct_class="state", evidence="正式版第4题总体走神比例单题", cohort="67 linked sessions / 46 participants",
                    n_sessions="67", n_observations="67", n_participants="46", analysis_unit="session-level retrospective single item", direction="与 Probe/commission error 形成方向性关联",
                    effect="见 Q1-PROBE/Q1-BEH 行", ci95="见 Q1-PROBE/Q1-BEH 行", p="见 Q1-PROBE/Q1-BEH 行", q="见 Q1-PROBE/Q1-BEH 行", status="PARTIAL",
                    product_implication="可作为场次级主观外部效标/报告字段；不能复制到实时 probe/window 状态",
                    source="Q1 questionnaire criterion-validity producer"),
    ])

    with (args.out / "psychometric_validity_reliability_evidence_matrix_v1.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(matrix)

    lines = [
        "# Issue #13 Mainline B：心理测量信效度 evidence matrix v1",
        "",
        "状态：`PARTIAL`。已有 behavior/Probe/questionnaire/repeated-participant 资产已实际复用；没有等待 NIR/RGB/mmWave，也未重复运行 Behavior + mmWave 增量分析。",
        "",
        "## 口径",
        "",
        "- 状态指标：Probe label/vigilance、场次级事后走神比例及其行为效标；结果单位是 probe 或 session，不能直接解释为稳定个体能力。",
        "- 稳定个体指标：当前没有足够的重复测量信度或成熟多题量表证据；trait-like 单题只保留为候选背景指标。",
        "- `PARTIAL` 表示方向/效标支持存在，但仍受回顾性单题、时间结构、重复 session 或未完成结构效度限制；`BLOCKED` 表示不具备正式包装所需证据，不表示“无效”。",
        "",
        "## 结论",
        "",
        "1. 最适合正式产品报告的状态层候选是：Probe label 1/2/3/4 的时间敏感轨迹、Probe vigilance、以及经过时间/阶段校正的行为关联；它们是状态/过程指标。",
        "2. 场次级事后走神比例与 label 1、label 2/3/4 和 commission error 具有方向性关联，属于外部效标/收敛支持，不是标准化量表效度。",
        "3. 没有足够证据支持“稳定专注能力/特质分数”：没有成熟多题量表、内部一致性、因子结构或正式 test–retest ICC。",
        "4. 重复参与者 grouped LOSO 只说明泛化边界；B0 behavior/context 不应被 mmWave M1 增量替代，不能把它当作心理测验信度。",
        "",
        "## 证据明细",
        "",
        "完整字段见同目录 CSV；每行保留 n、分析单位、方向、效应、95% CI、p/q、状态和产品含义。",
        "",
        "| ID | 构念 | n(session/obs/participant) | 单位 | 效应 | 95% CI | p/q | 状态 | 产品含义 |",
        "|---|---|---:|---|---|---|---|---|---|",
    ]
    for r in matrix:
        lines.append(f"| {r['evidence_id']} | {r['evidence']} | {r['n_sessions']}/{r['n_observations']}/{r['n_participants']} | {r['analysis_unit']} | {r['effect']} | {r['ci95']} | {r['p']}/{r['q']} | {r['status']} | {r['product_implication']} |")
    (args.out / "PSYCHOMETRIC_VALIDITY_RELIABILITY_EVIDENCE_MATRIX_V1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "analysis_id": "issue13_psychometric_matrix_v1",
        "status": "PARTIAL",
        "source_policy": "aggregate_only; no raw questionnaire/trial/sensor rows",
        "n_matrix_rows": len(matrix),
        "inputs": {str(path.name): sha256(path) for path in [
            args.q1_dir / "questionnaire_probe_association.csv", args.q1_dir / "questionnaire_behavior_association.csv",
            args.q1_dir / "questionnaire_ordinal_clustered_model.csv", args.label_models, args.repeat_models,
            args.repeat_sensitivity, args.repeat_loso,
        ]},
    }
    (args.out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PARTIAL", "matrix_rows": len(matrix), "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

