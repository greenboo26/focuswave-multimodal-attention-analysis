#!/usr/bin/env python
"""Build the D1 Beijing--Zhuhai canonical tables without identity inference.

This is deliberately a linkage-first entrypoint.  It reuses frozen Beijing
event rows and the registered Zhuhai master, but it never promotes a Zhuhai
registration to an actual task session unless a deterministic linkage asset is
available.  Consequently it emits explicit NOT_ESTIMABLE model rows rather
than silently fitting a Beijing-only model as a cross-site replication.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DERIVED = Path(r"D:\Project\厚粲杯\11_数据\derived")
DEFAULT_OUT = DERIVED / "beijing_zhuhai_canonical_harmonization_v1"
MASTER = DERIVED / "analysis_tables_v2" / "subject_session_master_v2.csv"
BEIJING_JOIN = DERIVED / "beijing_c2_identity_reuse_event_analysis_v2" / "deterministic_join.csv"
BEIJING_PROBES = (DERIVED / "beijing_c2_identity_reuse_event_analysis_v2" /
                  "formal_behavior_longitudinal_v1" / "probe_event_level_behavior.csv")
ZHUHAI_LINKAGE = (DERIVED / "zhuhai_session_linkage_nir_event_readiness_v1" /
                  "zhuhai_session_linkage.csv")

SITE_BEIJING = "Beijing"
SITE_ZHUHAI = "Zhuhai"
FORMAL_START = pd.Timestamp("2026-08-15")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_site(value: object) -> str:
    text = str(value)
    if "珠海" in text or text.lower() == "zhuhai":
        return SITE_ZHUHAI
    if "北京" in text or text.lower() == "beijing":
        return SITE_BEIJING
    return "unknown"


def parse_registration_datetime(value: object) -> pd.Timestamp:
    """Parse only an explicit month.day date; this is provenance, not linkage."""
    if pd.isna(value):
        return pd.NaT
    match = re.search(r"(?<!\d)(8)\.(\d{1,2})(?!\d)", str(value))
    if not match:
        return pd.NaT
    return pd.Timestamp(year=2026, month=int(match.group(1)), day=int(match.group(2)))


def bflag(series: pd.Series) -> pd.Series:
    return series.fillna(0).astype(str).str.strip().isin({"1", "1.0", "true", "True", "yes", "YES"}).astype(int)


def build_beijing(master: pd.DataFrame, join: pd.DataFrame) -> pd.DataFrame:
    m = master.copy()
    m["site_norm"] = m["site"].map(normalize_site)
    m["single_experiment_id"] = pd.to_numeric(m["single_experiment_id"], errors="coerce")
    j = join.copy()
    j["subject"] = pd.to_numeric(j["subject"], errors="coerce")
    x = j.merge(m, left_on="subject", right_on="single_experiment_id", how="left", validate="one_to_one")
    if x["single_experiment_id"].isna().any():
        raise ValueError("A deterministic Beijing join row did not resolve in subject_session_master_v2")
    if not (x["site_norm"] == SITE_BEIJING).all():
        raise ValueError("Deterministic Beijing join contains a non-Beijing master row")
    return pd.DataFrame({
        "repeat_participant_id": x["repeat_participant_id_x"],
        "session_id": x["timeline_session"].astype(str).str.rstrip("_"),
        "site": SITE_BEIJING,
        "phase": "formal",
        "session_datetime": pd.to_datetime(pd.to_numeric(x["session_date_time"], errors="coerce"), unit="D", origin="1899-12-30", errors="coerce"),
        "formal_session_index": pd.to_numeric(x["repeat_count"], errors="coerce").astype("Int64"),
        "collection_reason": "routine_or_unresolved_from_frozen_beijing_assets",
        "retake_of_session_id": pd.NA,
        "program_family": "BB_2x432_20probes",
        "behavior_usable": 1,
        "probe_usable": 1,
        "mmwave_usable": (x["current_analysis_eligibility"] == "current_mmwave_behavior_analysis").astype(int),
        # Raw-file presence is not modality usability. NIR requires completed
        # eyes.csv plus its audited coverage status; RGB has no QC gate here.
        "nir_usable": ((x["nir_formal_processing_status"] == "completed_with_eyes_csv") &
                       (x["nir_quality_evidence_status"] == "current_task_coverage_audited_threshold_unfrozen")).astype(int),
        "rgb_usable": pd.Series(pd.NA, index=x.index, dtype="Int64"),
        "questionnaire_usable": bflag(x["questionnaire_present_current"]),
        "include_in_shared_primary": 1,
        "include_in_zhuhai_extended": 0,
        "identity_evidence": "beijing_c2_identity_reuse_event_analysis_v2/deterministic_join.csv",
        "identity_confidence": "deterministic_pass_formal",
        "actual_session_link_status": "linked",
        "linkage_note": x["join_status"],
    })


def build_zhuhai(master: pd.DataFrame, linkage: pd.DataFrame) -> pd.DataFrame:
    m = master.copy()
    m["site_norm"] = m["site"].map(normalize_site)
    z = linkage.copy()
    z["single_experiment_id"] = pd.to_numeric(z["single_experiment_id"], errors="coerce")
    x = z.merge(m, on=["single_experiment_id", "repeat_participant_id"], how="left", validate="one_to_one", suffixes=("_link", "_master"))
    if x["site_norm"].ne(SITE_ZHUHAI).any():
        raise ValueError("Zhuhai linkage rows did not resolve exclusively to Zhuhai master rows")
    dt = x["session_date_time_register"].map(parse_registration_datetime)
    phase = pd.Series(pd.NA, index=x.index, dtype="object")
    phase.loc[dt.notna() & (dt < FORMAL_START)] = "pilot"
    phase.loc[dt.notna() & (dt >= FORMAL_START)] = "formal"
    # An actual-session link is a hard gate.  Registration date classifies
    # provenance only; it does not manufacture a task session or a probe row.
    formal_rank = (pd.DataFrame({"pid": x["repeat_participant_id"], "dt": dt, "phase": phase})
                   .query("phase == 'formal'").sort_values(["pid", "dt"]).groupby("pid").cumcount() + 1)
    formal_index = pd.Series(pd.NA, index=x.index, dtype="Int64")
    formal_index.loc[formal_rank.index] = formal_rank.astype("Int64")
    return pd.DataFrame({
        "repeat_participant_id": x["repeat_participant_id"],
        "session_id": x["actual_session_id"].replace("", pd.NA),
        "site": SITE_ZHUHAI,
        "phase": phase,
        "session_datetime": dt,
        "formal_session_index": formal_index,
        "collection_reason": "unknown_unlinked_registration",
        "retake_of_session_id": pd.NA,
        "program_family": "BBB_3x432_30probes_expected_registration_level",
        "behavior_usable": 0,
        "probe_usable": 0,
        "mmwave_usable": 0,
        "nir_usable": 0,
        "rgb_usable": 0,
        "questionnaire_usable": 0,
        "include_in_shared_primary": 0,
        "include_in_zhuhai_extended": 0,
        "identity_evidence": x["registration_identity_source"],
        "identity_confidence": x["linkage_confidence"].fillna("registration_only"),
        "actual_session_link_status": x["actual_session_link_status"],
        "linkage_note": x["minimum_missing_evidence"],
    })


def build_probe_master(beijing_probes: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    b = beijing_probes.loc[beijing_probes["is_probe"].eq(1)].copy()
    fields = ["repeat_participant_id", "session_id", "site", "formal_session_index", "collection_reason",
              "mmwave_usable", "nir_usable", "rgb_usable"]
    cw = crosswalk.loc[crosswalk["site"].eq(SITE_BEIJING), fields].copy()
    cw["subject_num"] = pd.to_numeric(cw["session_id"].str.extract(r"(\d+)")[0], errors="coerce")
    frozen_pid = b["repeat_participant_id"].copy()
    b = b.drop(columns=["repeat_participant_id"])
    b = b.merge(cw, left_on="subject_id", right_on="subject_num", how="inner", validate="many_to_one")
    if not frozen_pid.loc[b.index].equals(b["repeat_participant_id"]):
        # The event asset is frozen; any disagreement is a linkage error, not
        # a reason to silently replace its participant grouping.
        raise ValueError("Frozen Beijing probe identity disagrees with deterministic crosswalk")
    b["probe_index_within_block"] = b.groupby(["session_id", "block_num"]).cumcount() + 1
    b["within_block_progress"] = b["block_progress"]
    b["shared_protocol_progress"] = ((b["block_num"].astype(float) - 1 + b["block_progress"].astype(float)) / 2)
    b["behavior_window_usable"] = (pd.to_numeric(b["pre10_n_trials"], errors="coerce") > 0).astype(int)
    out = pd.DataFrame({
        "repeat_participant_id": b["repeat_participant_id"], "session_id": b["session_id"], "site": b["site"],
        "formal_session_index": b["formal_session_index"], "collection_reason": b["collection_reason"],
        "block": b["block_num"], "probe_index_within_block": b["probe_index_within_block"],
        "probe_response": b["probe_response"], "probe_vigilance": b["probe_vigilance"],
        "probe_onset_unix_ms": b["absolute_onset_time"], "within_block_progress": b["within_block_progress"],
        "shared_protocol_progress": b["shared_protocol_progress"], "behavior_window_usable": b["behavior_window_usable"],
        "mmwave_usable": b["mmwave_usable"], "nir_usable": b["nir_usable"], "rgb_usable": b["rgb_usable"],
        "pre10_error_rate": b["pre10_error_rate"], "pre10_rt_median_ms": b["pre10_rt_median_ms"],
        "pre10_rt_sd_ms": b["pre10_rt_sd_ms"], "pre10_n_trials": b["pre10_n_trials"],
    })
    return out.sort_values(["site", "repeat_participant_id", "session_id", "block", "probe_index_within_block"])


def write_report(out: Path, crosswalk: pd.DataFrame, probes: pd.DataFrame, coverage: pd.DataFrame) -> None:
    bj = crosswalk.query("site == 'Beijing' and phase == 'formal'")
    zh = crosswalk.query("site == 'Zhuhai'")
    lines = [
        "# 北京—珠海 Canonical Harmonization D1 运行结果",
        "",
        "状态：`IDENTITY_OR_SESSION_LINKAGE_BLOCKED`",
        "",
        "## 运行结论",
        "",
        "北京冻结的 deterministic join 与 probe 事件成功复用。珠海仅有登记层身份记录；当前输入中没有任何一场可确定连接到实际行为、时间线、probe 或传感器记录。因此不能拟合跨站点 progress、B1/B2、行为效标或 B3 延伸模型。模型表保留预定义问题并明确标为 `NOT_ESTIMABLE`，未将北京单站点结果伪装为跨站点复现。",
        "",
        "## 当前可复核计数",
        "",
        f"- 北京已链接正式 session：{len(bj)}，自然人：{bj.repeat_participant_id.nunique()}，B1/B2 probes：{len(probes)}。",
        f"- 珠海登记记录：{len(zh)}，登记自然人：{zh.repeat_participant_id.nunique()}；实际已链接正式 session：0，已链接 pilot session：0。",
        f"- 第 4 次及以上的已链接正式 session：{int((bj.formal_session_index >= 4).sum())} 场，涉及 {bj.loc[bj.formal_session_index >= 4, 'repeat_participant_id'].nunique()} 人。",
        "",
        "## 阻断边界",
        "",
        "珠海登记日期只能用于 pilot/formal provenance 分类，不能替代实际 session 链接。缺少每场正式行为 CSV、master_timeline、probe response/vigilance、绝对 Unix ms、B1/B2/B3 边界和模态目录映射。补齐这些 deterministic keys 后，使用本入口重跑；届时才可运行按 repeat_participant_id 聚类、报告 OR/beta、95% CI 的预注册主模型与每人最多三场敏感性分析。",
        "",
        "## 本地输出",
        "",
        "完整 pseudonymous crosswalk 与行级 probe master 仅写入本地 derived 目录，未纳入 Git。Git 提交仅含可重跑脚本、字段定义与脱敏 blocked 摘要。",
    ]
    (out / "BEIJING_ZHUHAI_CANONICAL_HARMONIZATION_RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    master, join, bprobes, zlink = map(read_csv, [MASTER, BEIJING_JOIN, BEIJING_PROBES, ZHUHAI_LINKAGE])
    crosswalk = pd.concat([build_beijing(master, join), build_zhuhai(master, zlink)], ignore_index=True)
    probe_master = build_probe_master(bprobes, crosswalk)
    extended = probe_master.iloc[0:0].copy()  # no linked Zhuhai B3 records in this run
    coverage = (crosswalk.groupby(["site", "phase"], dropna=False)
                .agg(session_records=("repeat_participant_id", "size"), participants=("repeat_participant_id", "nunique"),
                     behavior_usable_sessions=("behavior_usable", "sum"), probe_usable_sessions=("probe_usable", "sum"),
                     mmwave_usable_sessions=("mmwave_usable", "sum"), nir_usable_sessions=("nir_usable", "sum"),
                     rgb_usable_sessions=("rgb_usable", lambda s: s.eq(1).sum()),
                     rgb_qc_unknown_sessions=("rgb_usable", lambda s: s.isna().sum()),
                     questionnaire_usable_sessions=("questionnaire_usable", "sum"))
                .reset_index())
    questions = [
        "label1 probability declines with time-on-task in Zhuhai direction",
        "B1/B2 main effect consistency by site",
        "site x shared-protocol-progress heterogeneity",
        "lower pre-probe error for label1 replicated in Zhuhai",
        "Zhuhai B3 continuation trajectory",
    ]
    model_rows = pd.DataFrame({"analysis": questions, "status": "NOT_ESTIMABLE", "reason": "No deterministically linked Zhuhai actual behavior/probe sessions", "effect_size": pd.NA, "ci95_low": pd.NA, "ci95_high": pd.NA, "p_value": pd.NA, "participant_clustering": "required_repeat_participant_id"})
    sensitivity = pd.DataFrame({"analysis_set": ["all_core_valid_formal_sessions", "earliest_three_core_valid_sessions_per_person"], "status": "NOT_ESTIMABLE_CROSS_SITE", "reason": "No linked Zhuhai core-valid formal session", "progress_effect": pd.NA, "site_effect": pd.NA, "site_progress_interaction": pd.NA, "behavior_criterion": pd.NA})
    crosswalk.to_csv(out / "beijing_zhuhai_person_session_crosswalk.csv", index=False, encoding="utf-8-sig")
    probe_master.to_csv(out / "beijing_zhuhai_shared_probe_master.csv", index=False, encoding="utf-8-sig")
    extended.to_csv(out / "zhuhai_extended_b3_probe_master.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(out / "beijing_zhuhai_modality_coverage.csv", index=False, encoding="utf-8-sig")
    model_rows.to_csv(out / "beijing_zhuhai_behavior_probe_models.csv", index=False, encoding="utf-8-sig")
    sensitivity.to_csv(out / "beijing_zhuhai_repeat_sensitivity.csv", index=False, encoding="utf-8-sig")
    (out / "field_definitions.md").write_text("# D1 fields\n\n`phase` for unlinked Zhuhai rows is registration-date provenance only. `include_in_shared_primary=1` requires a deterministic actual task/probe linkage; missing modality never by itself excludes an otherwise linked core task session.\n", encoding="utf-8")
    manifest = {"run_id": "D1_BEIJING_ZHUHAI_CANONICAL_HARMONIZATION_V1_20260826", "created_at_utc": datetime.now(timezone.utc).isoformat(), "inputs": [str(p) for p in [MASTER, BEIJING_JOIN, BEIJING_PROBES, ZHUHAI_LINKAGE]], "counts": {"crosswalk_rows": len(crosswalk), "shared_probe_rows": len(probe_master), "linked_zhuhai_probe_rows": 0}, "status": "IDENTITY_OR_SESSION_LINKAGE_BLOCKED"}
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out, crosswalk, probe_master, coverage)
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
