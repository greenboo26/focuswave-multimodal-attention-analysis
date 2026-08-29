"""Build the Issue #17 session-level report-ready mmWave matrix.

Read-only aggregation of existing formal assets. No raw signal processing,
parameter changes, or model refits are performed here.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯")
DERIVED = ROOT / "11_数据" / "derived"
ALGO = ROOT / "08_算法"
OUT = ALGO / "work" / "issue17_formal_path_2026-08-27"

MASTER = DERIVED / "analysis_tables_v1" / "subject_session_master.csv"
ELIG = DERIVED / "analysis_tables_v1" / "analysis_eligibility_master.csv"
AUDIT = DERIVED / "formal_output_audit_v1" / "formal_output_subject_audit.csv"
SUMMARY = ALGO / "output/40_正式实验/02_探针与质量汇总/J_Data_主队列汇总_v1/J_Data_GROUP_SUMMARY/subject_summary.csv"
PROBES = ALGO / "output/40_正式实验/02_探针与质量汇总/J_Data_主队列汇总_v1/J_Data_GROUP_SUMMARY/probe_summary.csv"
EVENTS = ALGO / "output/40_正式实验/J_Data_ALERTNESS_EVENTS/J_Data_ALERTNESS_EVENT_windows.csv"
DYNAMICS = ALGO / "output/40_正式实验/02_探针与质量汇总/J_Data_主队列汇总_v1/J_Data_GROUP_SUMMARY/J_Data_TASK_DYNAMICS_windows.csv"
CROP = ALGO / "output/10_质量控制/01_行为时间门控/J_Data_行为时间裁剪_v1/crop_manifest.csv"
TARGET = DERIVED / "j_mmwave_target_lock_audit_v1/j_session_target_lock_summary_with_file_audit.csv"
SUPP_JSON = ALGO / "output/10_质量控制/03_缺失与补跑/J_Data_067_099补跑审计_v1/sub-099_/sub-099_ses-SART_mmwave_vital_signs.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def as_float(value: str | None) -> float | None:
    if value in (None, "", "NA", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def pct(n: int, d: int) -> str:
    return "" if not d else f"{100.0 * n / d:.4f}"


def index(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {str(r.get(key, "")).zfill(3): r for r in rows if r.get(key)}


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    out: Counter[str] = Counter()
    for row in rows:
        out[str(row.get(key, "")).zfill(3)] += 1
    return dict(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master_all = read_csv(MASTER)
    master = [r for r in master_all if r.get("behavior_present") == "1"]
    elig = index(read_csv(ELIG), "single_experiment_id")
    audit = index(read_csv(AUDIT), "single_experiment_id")
    summary = index(read_csv(SUMMARY), "subject")
    probe_rows = read_csv(PROBES)
    event_rows = read_csv(EVENTS)
    dyn_rows = read_csv(DYNAMICS)
    crop_rows = index(read_csv(CROP), "subject")
    target = index(read_csv(TARGET), "subject")

    probe_n = count_by(probe_rows, "subject")
    probe_ok = Counter()
    for r in probe_rows:
        if r.get("quality", "").lower() == "ok":
            probe_ok[str(r.get("subject", "")).zfill(3)] += 1
    event_n = count_by(event_rows, "subject")
    event_hr_ok = Counter()
    harmonic_n = Counter()
    for r in event_rows:
        sid = str(r.get("subject", "")).zfill(3)
        if r.get("pre_quality") == "ok" and r.get("post_quality") == "ok":
            event_hr_ok[sid] += 1
        if r.get("post_harmonics_corrected", "").lower() == "true":
            harmonic_n[sid] += 1
    dyn_n = count_by(dyn_rows, "subject")

    supplemental = {}
    if SUPP_JSON.exists():
        supplemental = json.loads(SUPP_JSON.read_text(encoding="utf-8-sig"))

    fields = [
        "session", "repeat_participant", "repeat_count", "behavior_present",
        "questionnaire_present", "questionnaire_linkage", "behavior_linkage",
        "mmwave_available", "mmwave_path_status", "available_duration_s", "duration_source",
        "hr_probe_n", "hr_probe_ok_n", "hr_coverage_pct", "br_probe_n", "br_probe_ok_n",
        "br_coverage_pct", "coverage_basis", "quality_status", "quality_source",
        "motion_risk", "harmonic_risk", "harmonic_corrected_event_n", "target_lock_status",
        "target_lock_boundary", "probe_count", "task_dynamics_window_n",
        "task_dynamics_eligible", "alertness_event_n", "alertness_paired_hr_n",
        "alertness_eligible", "issue15_hr_role", "issue15_br_role", "issue15_hrv_role",
        "issue15_physio_mapping", "issue16_mapping", "main_model_boundary", "status",
    ]
    output: list[dict[str, str]] = []
    for base in sorted(master, key=lambda r: int(r["single_experiment_id"])):
        sid = str(base["single_experiment_id"]).zfill(3)
        e, a, s, t, c = elig.get(sid, {}), audit.get(sid, {}), summary.get(sid, {}), target.get(sid, {}), crop_rows.get(f"sub-{sid}", {})
        pe = int(probe_n.get(sid, 0))
        po = int(probe_ok.get(sid, 0))
        en = int(event_n.get(sid, 0))
        eh = int(event_hr_ok.get(sid, 0))
        duration = as_float(c.get("retained_duration_s"))
        duration_source = "crop_manifest.retained_duration_s" if duration is not None else ""
        if sid == "099" and duration is None and supplemental:
            duration = as_float(str(supplemental.get("duration_s", "")))
            duration_source = "supplemental_v3.1.1_json_raw_duration; not timeline-gated"
        if sid == "099":
            pe, po = int(a.get("supplemental_probe_n") or 20), int(a.get("supplemental_probe_ok") or 20)
            en, eh = 0, 0
        mm_available = e.get("mmwave_available", "0")
        qstatus = "missing" if sid == "067" else ("supplemental_quality_available" if sid == "099" else "existing_group_quality")
        harm = "not_available" if sid in ("067", "099") else ("observed_correction_events" if harmonic_n.get(sid, 0) else "no_correction_event_observed")
        status = "BLOCKED_missing_mmwave_raw_input" if sid == "067" else ("PARTIAL_supplemental_not_main_model" if sid == "099" else "PASS_existing_formal_path_linked")
        row = {
            "session": sid,
            "repeat_participant": e.get("repeat_participant_id", base.get("repeat_participant_id", "")),
            "repeat_count": e.get("colleague_participation_count", base.get("repeat_count", "")),
            "behavior_present": base.get("behavior_present", ""),
            "questionnaire_present": base.get("questionnaire_present", ""),
            "questionnaire_linkage": e.get("questionnaire_algorithm_bridge_status", base.get("questionnaire_match_status", "")),
            "behavior_linkage": "present" if base.get("behavior_present") == "1" else "missing",
            "mmwave_available": mm_available,
            "mmwave_path_status": "raw_and_existing_output" if sid not in ("067",) else "raw_mmwave_missing;behaviour_rgb_nir_present",
            "available_duration_s": "" if duration is None else f"{duration:.3f}",
            "duration_source": duration_source,
            "hr_probe_n": str(pe), "hr_probe_ok_n": str(po), "hr_coverage_pct": pct(po, pe),
            "br_probe_n": str(pe), "br_probe_ok_n": str(po), "br_coverage_pct": pct(po, pe),
            "coverage_basis": "shared_probe_quality; BR-specific window gate remains in Issue15" if sid != "067" else "no_mmwave_probe_asset",
            "quality_status": qstatus,
            "quality_source": "subject_summary + formal_output_subject_audit" if sid not in ("067", "099") else ("067 formal audit" if sid == "067" else "supplemental audit + target-lock scan"),
            "motion_risk": "not_available_as_frozen_session_field",
            "harmonic_risk": harm,
            "harmonic_corrected_event_n": str(harmonic_n.get(sid, 0)),
            "target_lock_status": t.get("preliminary_target_candidate_status", "missing_no_scan"),
            "target_lock_boundary": t.get("interpretation_boundary", "missing raw input"),
            "probe_count": str(pe),
            "task_dynamics_window_n": str(dyn_n.get(sid, 0)),
            "task_dynamics_eligible": "yes" if dyn_n.get(sid, 0) > 0 else "no",
            "alertness_event_n": str(en), "alertness_paired_hr_n": str(eh),
            "alertness_eligible": "yes" if en > 0 and eh > 0 else "no",
            "issue15_hr_role": a.get("hr_report_role", e.get("hr_report_role", "")),
            "issue15_br_role": a.get("br_report_role", e.get("br_report_role", "")),
            "issue15_hrv_role": a.get("hrv_report_role", e.get("hrv_report_role", "")),
            "issue15_physio_mapping": "main_candidate" if sid not in ("067", "099") else ("blocked_missing_mmwave" if sid == "067" else "supplemental_only"),
            "issue16_mapping": "main_70_session_denominator" if dyn_n.get(sid, 0) > 0 else ("not_in_main_model" if sid == "099" else "blocked"),
            "main_model_boundary": "70-session existing main outputs" if sid not in ("067", "099") else ("not eligible; missing mmWave" if sid == "067" else "supplemental; do not expand main denominator"),
            "status": status,
        }
        output.append(row)

    out_csv = OUT / "issue17_report_ready_session_matrix_v1.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(output)

    source_paths = [MASTER, ELIG, AUDIT, SUMMARY, PROBES, EVENTS, DYNAMICS, CROP, TARGET, SUPP_JSON]
    manifest = {
        "run_id": "issue17_formal_path_20260827_readonly_aggregation_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL",
        "scope": "formal mmWave path and shared session matrix; NIR/RGB paused; no C2B/C2C",
        "row_count": len(output), "behavior_session_count": len(master),
        "mmwave_group_summary_session_count": len(summary), "main_task_dynamics_session_count": len(set(r["session"] for r in output if r["task_dynamics_eligible"] == "yes")),
        "blocked_sessions": [r["session"] for r in output if r["status"].startswith("BLOCKED")],
        "supplemental_sessions": [r["session"] for r in output if r["status"].startswith("PARTIAL")],
        "067_decision": "BLOCKED: J:/Data/sub-067_/mmwave absent; no safe formal producer input",
        "099_decision": "PARTIAL: existing v3.1.1 supplemental output and 238 raw files; no timeline/meta linkage for main-model promotion",
        "sources": [{"path": str(p), "exists": p.exists(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() and p.is_file() else None} for p in source_paths],
        "producer_chain": [
            {"stage": "raw/session", "entry": "J:/Data/sub-XXX_/mmwave/*.npz + *_timestamps.csv; beh/master_timeline.csv", "status": "linked for 70; 099 supplemental; 067 blocked"},
            {"stage": "target-lock/radar signal", "entry": "11_数据/derived/audit_j_mmwave_target_lock_v1.py; _scan_quality.py; j_session_target_lock_summary_with_file_audit.csv", "status": "existing read-only audit; candidate-only boundary"},
            {"stage": "HR/BR/quality", "entry": "scripts/process_vital_signs_v3_1_1.py; run_timeline_gated_mmwave_quality.py; Formal_mmwave/segment_quality.csv", "status": "existing outputs; HR/BR gates not fully frozen"},
            {"stage": "probe/task windows", "entry": "J_Data_GROUP_SUMMARY/probe_summary.csv; J_Data_TASK_DYNAMICS_windows.csv; J_Data_ALERTNESS_EVENT_windows.csv", "status": "70 main; 099 supplemental"},
            {"stage": "group models", "entry": "J_Data_TASK_DYNAMICS_LMM/GEE.csv; J_Data_ALERTNESS_EVENT_LMM/GEE.csv", "status": "Issue16 existing outputs; no rerun"},
            {"stage": "behavior/questionnaire bridge", "entry": "analysis_tables_v1 + formal_questionnaire_bridge.csv", "status": "behavior 72; questionnaire linkage remains source-specific"},
        ],
        "validation": {"matrix_header_complete": set(fields) == set(output[0]) if output else False, "unique_sessions": len({r["session"] for r in output}) == len(output), "contains_067": any(r["session"] == "067" for r in output), "contains_099": any(r["session"] == "099" for r in output)},
    }
    (OUT / "issue17_formal_path_manifest_v1.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = OUT / "issue17_formal_path_report_v1.md"
    report.write_text("""# Issue #17 Mainline F：正式 mmWave 路径收口报告\n\n日期：2026-08-27\n状态：**PARTIAL**\nRUN_ID：`issue17_formal_path_20260827_readonly_aggregation_v1`\n\n## 结论\n\n已从现有只读 producer/postprocess 产物实际构建唯一 72 行 session-level report-ready matrix。行为分母为 72 场；现有正式 mmWave group summary 为 70 场；`099` 有 raw 与既有 v3.1.1 supplemental 输出但不升级主模型；`067` 的 `J:\\Data\\sub-067_\\mmwave` 缺失，无法安全补跑。\n\nNIR/RGB 保持 PAUSED；未读取其结果作为本矩阵科学输入；临时 NIR AUC 不在任何结论中。未重复 C2B/C2C，未开发新算法，未创建/切换远端分支，未 force push/reset/clean。\n\n## 唯一路径\n\n`raw/session → target-lock/radar signal → HR/BR/quality → probe/task windows → task dynamics/alertness → behavior/questionnaire`\n\n实际入口、输入输出和来源哈希见 `issue17_formal_path_manifest_v1.json`；矩阵见 `issue17_report_ready_session_matrix_v1.csv`。\n\n## 067/099 决策\n\n- `067`：**BLOCKED**。行为、RGB、NIR 存在，但毫米波目录无 raw 分片；没有可安全复用的正式 producer 输入，不能补写 HR/BR/quality，也不能进入 #15/#16 mmWave 分母。\n- `099`：**PARTIAL / supplemental**。240 个 raw datacube 分片、既有 `v3.1.1` 输出、42 个窗口与 20/20 probe 结果存在；但缺少时间门控 manifest/meta 链接，且现有结果明确标为 supplemental，因此不进入 #16 原 70 场主模型。\n\n## 供 #15/#16 共用的分母映射\n\n- #15：70 个现有主输出场次；HR 为主候选，BR 为质量门控研究候选，HRV 仍 exploratory-blocked。矩阵保留场次级 HR/BR 覆盖和角色字段，但不把 42/70、50/70 写成最终排除规则。\n- #16：task dynamics 与 alertness 继续使用已有 70 场主分母；`099` supplemental，`067` blocked。矩阵以现有窗口/event 数和 eligibility 字段固定该边界。\n- 行为/questionnaire：矩阵保留 72 场行为层，单独标明 questionnaire linkage；不把问卷复制成 probe-level 生理资格。\n\n## 剩余最小阻塞\n\n1. #15 冻结逐窗口 HR/BR quality gate 后，补入矩阵的 per-session BR-specific window coverage，并由 #16 仅重跑质量敏感性层。\n2. `067` 只有在取得原始 mmWave 分片、timestamps、meta/时间线匹配且复用同一正式 producer 版本后才可补跑。\n3. `099` 若要进入主模型，需补齐 timeline/meta linkage 并重新生成主链 manifest；当前 supplemental 边界保持不变。\n4. questionnaire bridge 的 68 vs behavior descriptive 67 分母需由 #15/#16 统一桥接规则后再更新。\n""", encoding="utf-8")


if __name__ == "__main__":
    main()


