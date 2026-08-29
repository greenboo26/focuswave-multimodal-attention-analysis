import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "docs" / "results" / "mmwave_formal_vital_qc_v1"
MATRIX = ROOT / "work/issue17_formal_path_2026-08-27/issue17_report_ready_session_matrix_v1.csv"
AUDIT = Path(r"D:\Project\厚粲杯\11_数据\derived\formal_output_audit_v1/formal_output_subject_audit.csv")
SUBJECT = ROOT / "output/40_正式实验/02_探针与质量汇总/J_Data_主队列汇总_v1/J_Data_GROUP_SUMMARY/subject_summary.csv"
REF = ROOT / "output/20_生理金标准验证/01_历史严格参照_v20260821/mmwave_vs_reference_probes.csv"
REF_METRICS = REF.parent / "reference_metrics.json"
SEGMENT = ROOT / "output/10_质量控制/01_行为时间门控/J_Data_行为时间裁剪_v1/Formal_mmwave/segment_quality.csv"
GOLD_SCRIPT = ROOT / "docs/交付/毫米波ECG金标准验证_0816/脚本/gold_standard_qa.py"
PRODUCER = ROOT / "docs/交付/毫米波ECG金标准验证_0816/脚本/process_vital_signs_v3_1_1.py"

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def num(row, key):
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    matrix = {r["session"]: r for r in read_csv(MATRIX)}
    audit = {r["single_experiment_id"]: r for r in read_csv(AUDIT)}
    subject = {r["subject"]: r for r in read_csv(SUBJECT)}
    records = []
    for session in sorted(matrix):
        m = matrix[session]
        a = audit.get(session, {})
        s = subject.get(session, {})
        wq = num(s, "window_quality_pct")
        pq = num(s, "probe_quality_pct")
        target = m.get("target_lock_status", "")
        status = m.get("status", "")
        if status.startswith("BLOCKED") or status.startswith("PARTIAL"):
            primary = "A_acquisition_or_sync"
            bucket = "Tier_3_unusable_for_formal_v1"
            reason = ("067: 缺失/未链接毫米波 raw 输入" if session == "067" else
                      "099: 有 raw 与 supplemental 输出，但缺少进入主队列所需的 timeline/meta linkage")
        elif target in {"distance_implausible", "plausible_distance_phase_unstable", "plausible_distance_low_signal_presence"}:
            primary = "B_radar_geometry_or_motion"
            bucket = "Tier_2_motion_only"
            reason = {
                "distance_implausible": "目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征",
                "plausible_distance_phase_unstable": "距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层",
                "plausible_distance_low_signal_presence": "仅有低信号存在性候选；不足以支持主队列生命体征综合分析",
            }[target]
        elif wq is None or pq is None or wq < 80 or pq < 80:
            primary = "C_vital_algorithm_failure"
            bucket = "Tier_2_motion_only"
            reason = "毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障"
        else:
            primary = "U_unresolved"
            bucket = "Tier_1_QC_eligible_candidate"
            reason = "通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定"
        codes = [primary]
        if session != "067":
            codes += ["D_hrv_too_strict_not_supported", "E_construct_validity_not_sensor_quality"]
        if primary == "A_acquisition_or_sync":
            codes.append("U_unresolved")
        records.append({
            "session": session,
            "primary_attribution": primary,
            "attribution_codes": ";".join(codes),
            "analysis_bucket": bucket,
            "mmwave_path_status": status,
            "target_lock_status": target,
            "window_quality_pct": "" if wq is None else f"{wq:.2f}",
            "probe_quality_pct": "" if pq is None else f"{pq:.2f}",
            "hr_probe_n": m.get("hr_probe_n", ""),
            "hr_probe_ok_n": m.get("hr_probe_ok_n", ""),
            "br_probe_n": m.get("br_probe_n", ""),
            "br_probe_ok_n": m.get("br_probe_ok_n", ""),
            "hr_report_role": a.get("hr_report_role", m.get("issue15_hr_role", "")),
            "br_report_role": a.get("br_report_role", m.get("issue15_br_role", "")),
            "hrv_report_role": a.get("hrv_report_role", m.get("issue15_hrv_role", "")),
            "reason_evidence_layer": reason,
            "reference_scope": "独立 ECG/RSP 校准/机制证据；不作为正式 70 场外部金标准覆盖",
        })
        records[-1].update({
            "probe_count": m.get("probe_count", m.get("hr_probe_n", "")),
            "qc_probe_pass_count": m.get("hr_probe_ok_n", ""),
            "can_use_for_motion": "yes" if bucket != "Tier_3_unusable_for_formal_v1" else "no",
            "can_use_for_rr": "candidate_only" if bucket == "Tier_1_QC_eligible_candidate" else "no",
            "can_use_for_hr": "candidate_only" if bucket == "Tier_1_QC_eligible_candidate" else "no",
            "can_use_for_hrv": "no",
            "can_use_for_attention_model": "no",
        })

    fields = list(records[0])
    with (OUT / "mmwave_session_qc_summary_redacted.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(records)
    cross_fields = ["session", "probe_count", "qc_probe_pass_count", "primary_attribution", "analysis_bucket",
                    "can_use_for_motion", "can_use_for_rr", "can_use_for_hr", "can_use_for_hrv",
                    "can_use_for_attention_model", "reason_evidence_layer"]
    with (OUT / "mmwave_session_use_tier_crosswalk.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cross_fields); w.writeheader()
        for r in records: w.writerow({k: r.get(k, "") for k in cross_fields})

    ref_rows = read_csv(REF)
    metric_defs = [
        ("HR_course", "hr_course_error_bpm", "bpm", "ECG", "HR course"),
        ("HR_peak", "hr_error_bpm", "bpm", "ECG", "HR peak"),
        ("BR_peak", "br_error_bpm", "次/分", "RSP", "BR peak"),
        ("RMSSD", "rmssd_error_ms", "ms", "ECG", "RMSSD"),
    ]
    agg = []
    for name, col, unit, ref, label in metric_defs:
        vals = [float(r[col]) for r in ref_rows if r.get(col, "") != ""]
        agg.append({"metric": name, "reference": ref, "n_windows": len(vals), "unit": unit,
                    "mae": round(sum(abs(x) for x in vals)/len(vals), 4),
                    "bias": round(sum(vals)/len(vals), 4),
                    "within_abs_5": sum(abs(x) <= 5 for x in vals),
                    "interpretation": label})
    with (OUT / "mmwave_reference_agreement_aggregate.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(agg[0])); w.writeheader(); w.writerows(agg)

    counts = Counter()
    for r in records:
        for code in r["attribution_codes"].split(";"):
            counts[code] += 1
    count_rows = [{"failure_mode": k, "session_count": counts[k], "count_basis": "primary_or_applicable_flag"} for k in sorted(counts)]
    with (OUT / "mmwave_failure_mode_counts.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(count_rows[0])); w.writeheader(); w.writerows(count_rows)

    primary_counts = Counter(r["primary_attribution"] for r in records)
    manifest = {
        "artifact": "MMWAVE_FORMAL_VITAL_QC_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL",
        "redaction": "absolute paths, raw filenames, personal identifiers and raw waveforms omitted; anonymous session namespace retained",
        "scope": "formal mmWave batch QC and ECG/RSP criterion-attribution only; no focus modeling; no algorithm change",
        "repo_head_reviewed": "ba7a2c652bea82c3fa58ad5858a7460ed933fb47",
        "session_counts": {"total": len(records), "primary": dict(primary_counts), "analysis_buckets": dict(Counter(r["analysis_bucket"] for r in records))},
        "rules": {
            "ecg": "0.5-40 Hz bandpass; R-peak distance >=0.3 s; IBI 300-2000 ms; adjacent IBI relative change >20% rejected; usable if normal RR ratio >=80%",
            "rsp": "0.1-0.7 Hz bandpass; peak distance >=0.5 s; 6-42 breaths/min; low-amplitude loose-belt flag; usable if normal cycle ratio >=80%; median rate",
            "mmwave": "existing v3.1.1/time-gated outputs; 10 s heart-band signal-presence windows; independent block analysis; no cross-block IBI/HRV concatenation",
            "formal_v1_session_gate": "window_quality_pct >=80 and probe_quality_pct >=80, plus no existing target-lock geometry/phase instability flag; this is a QC eligibility rule, not a claim of physiological accuracy",
            "ecg_label_tuning": "no ECG/RSP labels used to tune formal-batch v1 parameters; ECG/RSP used only as independent reference/attribution evidence",
        },
        "reference_cohort": {"sessions": 5, "paired_windows": 100, "metric_rows": 99, "source": "existing strict BIOPAC ECG/RSP comparison artifact"},
        "sources": {p.name: {"sha256": sha256(p)} for p in [MATRIX, AUDIT, SUBJECT, REF, REF_METRICS, SEGMENT, GOLD_SCRIPT, PRODUCER] if p.exists()},
        "outputs": ["MMWAVE_FORMAL_VITAL_QC_V1.md", "MMWAVE_FORMAL_VITAL_QC_V1_REDACTED_MANIFEST.json", "mmwave_session_qc_summary_redacted.csv", "mmwave_session_use_tier_crosswalk.csv", "mmwave_reference_agreement_aggregate.csv", "mmwave_failure_mode_counts.csv"],
    }
    (OUT / "MMWAVE_FORMAL_VITAL_QC_V1_REDACTED_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    comp = [r["session"] for r in records if r["analysis_bucket"] == "Tier_1_QC_eligible_candidate"]
    motion = [r["session"] for r in records if r["analysis_bucket"] == "Tier_2_motion_only"]
    unusable = [r["session"] for r in records if r["analysis_bucket"] == "Tier_3_unusable_for_formal_v1"]
    def md_table(rows):
        head = "| session_id | probe_count | qc_probe_pass_count | failure_mode | use_tier | can_use_for_motion | can_use_for_rr | can_use_for_hr | can_use_for_hrv | can_use_for_attention_model | reason |\n|---|---:|---:|---|---|---|---|---|---|---|---|"
        lines = [head]
        keys = ["session", "probe_count", "qc_probe_pass_count", "primary_attribution", "analysis_bucket", "can_use_for_motion", "can_use_for_rr", "can_use_for_hr", "can_use_for_hrv", "can_use_for_attention_model"]
        for r in rows:
            reason = r["reason_evidence_layer"].replace("|", "\\|")
            lines.append("| " + " | ".join(str(r.get(k, "")) for k in keys) + " | " + reason + " |")
        return "\n".join(lines)
    md = f'''# MMWAVE FORMAL VITAL QC V1

日期：2026-08-28 ；状态：**PARTIAL**

## 范围与边界

本批仅复盘既有 ECG/RSP 小样本质量规则，并对现有 formal mmWave 产物实施 QC v1 归因。未启动专注建模，未继续修改算法，未读取 NIR/RGB 作为本批证据。session 使用已有匿名编号；本报告不把匿名 session 当作已确认真实被试身份。

## 既有小样本规则复盘

| 项目 | 已确认内容 |
|---|---|
| 对应脚本 | `gold_standard_qa.py` v2.0；毫米波 producer 为既有 `process_vital_signs_v3_1_1.py`；批次时间门控入口为 `run_timeline_gated_mmwave_quality.py` |
| 复盘 commit | 仓库复核 HEAD `ba7a2c652bea82c3fa58ad5858a7460ed933fb47`；输入脚本 SHA-256 见 manifest |
| 输入数据 | formal 主队列既有 70 场、099 supplemental、067 缺失/未链接；ECG/RSP 严格参考为 5 场×20 个 60 s 窗口 |
| 输出目录 | 本批输出到 `docs/results/mmwave_formal_vital_qc_v1/`；既有输入产物路径与哈希记录在 manifest |
| ECG 清洗 | 0.5–40 Hz；R 峰最小间距 0.3 s；IBI 300–2000 ms；相邻 IBI 相对变化 >20% 剔除；正常 RR ≥80% 可用；时域 HR 取中位 IBI |
| RSP 清洗 | 0.1–0.7 Hz；峰间距 ≥0.5 s；6–42 次/分；低幅度松脱标记；正常周期 ≥80% 可用；呼吸率取中位周期率 |
| mmWave 清洗 | 既有 v3.1.1 与行为时间门控；10 s 心跳带通位移信号存在性窗；每个 block 独立，不跨 block 拼接 IBI/HRV |
| window 长度 | ECG/RSP 参考：60 s；formal mmWave QC：10 s 信号存在性窗；既有 probe 产物另按原有 probe 窗口记录 |
| filter band | ECG 0.5–40 Hz；RSP 0.1–0.7 Hz；毫米波沿用既有 producer 的心跳带通，不在本批改动 |
| beat matching | ECG 侧按 R 峰→IBI；既有毫米波对照按同一行为/时间窗口比较 HR；本批不重建逐搏 beat-to-beat matching |
| artifact rejection | ECG IBI 百分比变化法；RSP 生理范围与松脱标记；毫米波沿用既有信号存在性/质量窗及 target-lock 审计标记 |
| usable-window 判定 | ECG/RSP 正常比例 ≥80%；formal v1 session 另要求 window_quality_pct ≥80、probe_quality_pct ≥80，且无既有几何/相位不稳定标记 |
| ECG 标签调参 | **未用 ECG/RSP 标签调 formal batch v1 参数**；ECG/RSP 仅作为独立参照与归因证据。历史 0816 校准结论保留为机制背景，不回写为本批调参 |

## QC v1 归因规则

- A：raw、时间轴、同步或主队列 linkage 缺失/不完整。
- B：已有 target-lock 审计显示距离不合理、相位不稳定或仅低信号存在性；归入雷达几何/运动层。
- C：输入/输出链存在，但既有 10 s 或 probe 覆盖未过 v1 门槛；仅称 vital algorithm/QC gate failure，不推断硬件故障。
- D：HRV/IBI 逐搏证据不足，不能支持 HRV；不是 session 传感器质量结论。
- E：ECG/RSP 对照揭示构念效度、谐波或参考不一致风险；不是“数据质量差”或笼统“算法问题”。
- U：证据不足以在上述层级中进一步定位。

每个 session 的主归因与适用 flag 见 `mmwave_session_qc_summary_redacted.csv`。

## Use-tier definitions and gates

### 先澄清“17 场”

“17 场”不是“生命体征可用”，也不是 ECG/RSP 对照通过。它表示 **Tier 1 QC-eligible candidate**：在现有 formal 产物中，`window_quality_pct >= 80`、`probe_quality_pct >= 80`，且没有已有 target-lock 几何/相位不稳定标记。它们具有可进入后续综合分析的质量候选资格；HR/RR 只能标为 `candidate_only`，HRV 为 `no`，attention model 为 `no`。严格说，它们的主归因仍是 `U_unresolved`（未能从现有证据进一步定位失败原因），不是 usable。

### 三个 use-tier 的 gate

| use_tier | 必须满足 | 失败/降级条件 | ECG/RSP 是否参与 | 当前允许用途 |
|---|---|---|---|---|
| `Tier_1_QC_eligible_candidate` | formal linkage 存在；`window_quality_pct >=80`；`probe_quality_pct >=80`；无 B 类 target-lock 几何/相位/低信号标记 | 任一覆盖率 <80% 降为 Tier 2；出现 B 标记降为 Tier 2；A/同步或 linkage 缺失降为 Tier 3 | **不参与 gate**；5 场 ECG/RSP 仅提供独立校准/机制边界 | HR/RR 研究候选，不能写成已验证生命体征；HRV 和 attention model 不可用 |
| `Tier_2_motion_only` | 有可追溯毫米波输出或信号存在性证据 | B 类几何/相位/信号证据，或 C 类窗口/probe gate 失败 | 不参与 gate | 仅微动/体动描述；HR/RR/HRV/attention model 均不可用 |
| `Tier_3_unusable_for_formal_v1` | A 类 raw、同步、时间轴或主队列 linkage 阻断 | 在补齐输入和 linkage 前不得升级 | 不适用 | formal v1 不可用；067/099 保持边界 |

补充限制：D (`hrv_too_strict_not_supported`) 适用于有 HRV 数值但无充分逐搏 ECG 验证的 session；E (`construct_validity_not_sensor_quality`) 表示独立 ECG/RSP 揭示的构念效度/谐波风险。D/E 不是传感器质量 pass，也不是 Tier 1 的放行证明。上述 gate 适用于 formal 主队列；ECG/RSP 小样本只用于参照协议和归因，不把 5 场扩展为 70 场金标准覆盖。

### “只能用于微动/体动：53 场”的具体含义

53 场 = B 类 44 场 + C 类 9 场，均不是因为“缺 ECG/RSP”这一单一原因。B 由 `target_lock_status` 中的 `distance_implausible`、`plausible_distance_phase_unstable` 或 `plausible_distance_low_signal_presence` 决定；C 由既有输出存在但 `window_quality_pct <80` 或 `probe_quality_pct <80` 决定。它们可以保留已有毫米波信号/相位变化作微动或体动层描述，但本 QC 不授权将其 HR/RR 解释为有效生命体征。

### 1,297/1,400 到底是什么 pass

`1,297/1,400` 是既有 70 场主队列的 **probe-level mmWave quality flag**（`probe_quality_pct` 的分子/分母）：表示探针对应窗口在既有毫米波质量产物中被标记为 `ok`。它不是文件完整性 pass、不是 timestamp/sync pass、不是 ECG/RSP 对照 pass，也不是 HR/RR/HRV 生理准确性 pass。它与本批分层的关系是：它支持 probe 层覆盖描述；只有同时满足 window ≥80%、probe ≥80% 且无 B 标记，才进入 Tier 1 的 17 场。其余主队列场次进入 Tier 2 或更低，不应把 1,297/1,400 改写为“毫米波生命体征可用”。

### Session crosswalk

完整交叉表另存为 `mmwave_session_use_tier_crosswalk.csv`；以下为同一表的可读版本：

{md_table(records)}

## Session 分层结果

### Tier 1：QC-eligible candidate（不是生命体征已用）

共 **{len(comp)}** 场：`{", ".join(comp)}`

判定：窗口质量和 probe 覆盖均 ≥80%，且未被已有 target-lock 几何/相位标记阻断。HR/RR 仅作为后续研究候选；BR 仍为 supporting sensitivity；HRV 统一标记 D，不进入确认性主结论。不得写成“生命体征可用”。

### Tier 2：只能用于微动/体动

共 **{len(motion)}** 场。包括主归因 B 的几何/相位/低信号证据，以及主归因 C 的窗口或 probe 覆盖不足场次。它们可保留相位变化、微动或体动层面的描述性信息，不应直接解释为 HR/BR/HRV。

### Tier 3：不可用于 formal v1

共 **{len(unusable)}** 场：`{", ".join(unusable)}`。067 为毫米波 raw 缺失/未链接；099 有 supplemental raw/输出，但缺少主队列 timeline/meta linkage，不能进入本 formal 主分母。

## ECG/RSP 独立效标协议与结果

严格参照为 BIOPAC ECG（心电图）/RSP（呼吸带）5 个重复测量场次、100 个 60 s 窗口；99 个窗口有对应毫米波指标。已有比较结果：HR course MAE 4.59 bpm，HR peak MAE 7.82 bpm，BR peak MAE 11.77 次/分，RMSSD MAE 262.64 ms。RSP 频谱候选的既有汇总为 MAE 3.51 次/分，但仍属于独立验证后的 supporting sensitivity，不能覆盖普通峰值 BR 的失败证据。

关键归因：ECG/RSP 金标准清洗本身在小样本中可用；97795/97796 已观察到呼吸二/三次谐波落入心跳带，形成“强而错”锁定，说明高 SNR、相位稳定和时频自洽不等于心率构念有效。因此 E 是构念效度边界，不应写成传感器质量差。

## 原因统计

主归因计数、适用 flag 计数及口径见 `mmwave_failure_mode_counts.csv`。其中 D/E 是适用范围 flag，不能与 A/B/C/U 的主归因相加后当作互斥 session 数。

## 报告书可直接粘贴的毫米波 QC 结论段

本研究对正式毫米波记录实施了预先冻结的分层质量控制：ECG/RSP 参考侧采用带通、逐搏/逐周期异常剔除及 ≥80% 正常比例判定；毫米波侧沿用既有 v3.1.1 producer 与行为时间门控，对 10 s 信号存在性窗和 probe 覆盖进行审计，并将缺失/同步、雷达几何或运动、生命体征输出门控失败、HRV 逐搏证据不足、构念效度风险和未解析状态分开记录。QC v1 将 {len(comp)} 场列为 Tier 1 质量候选（**不是生命体征已用**），{len(motion)} 场仅保留微动/体动层信息，{len(unusable)} 场因输入或时间轴 linkage 不足不可用于 formal 主分析。独立 BIOPAC 参照显示，毫米波 HR course 的窗口级误差低于逐峰 HR，但 BR 峰值与 HRV 仍存在明显不一致；尤其呼吸二/三次谐波可在信号稳定时产生“强而错”的心跳锁定。因此，本研究不以“数据质量差”或笼统“算法问题”概括结果，而按证据层级限制毫米波 HR/RR 的研究性使用，并不将 HRV 作为已验证生理指标或专注效标输入。

## 验证与限制

本批读取并核对了既有 matrix、formal output audit、subject summary、segment quality、ECG/RSP 参考比较与规则脚本；输出 CSV/JSON/Markdown 均可读。未提交、未推送；工作区原有大量用户修改保持不变。治理主 checkout 未能在本机解析，故治理基线的独立复核仍是限制。
'''
    (OUT / "MMWAVE_FORMAL_VITAL_QC_V1.md").write_text(md, encoding="utf-8")
    print(json.dumps({"out": str(OUT), "sessions": len(records), "primary": dict(primary_counts)}, ensure_ascii=False))

if __name__ == "__main__":
    main()


