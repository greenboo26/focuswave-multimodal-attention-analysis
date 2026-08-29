from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "results" / "mmwave_formal_vital_qc_v1"
MATRIX = ROOT / "work" / "issue17_formal_path_2026-08-27" / "issue17_report_ready_session_matrix_v1.csv"
QC_SUMMARY = OUT / "mmwave_session_qc_summary_redacted.csv"
SUBJECT = ROOT / "output" / "40_正式实验" / "02_探针与质量汇总" / "J_Data_主队列汇总_v1" / "J_Data_GROUP_SUMMARY" / "subject_summary.csv"
REF = ROOT / "output" / "20_生理金标准验证" / "01_历史严格参照_v20260821" / "mmwave_vs_reference_probes.csv"
REF_METRICS = REF.parent / "reference_metrics.json"
PRODUCER = ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
SCAN_CORE = ROOT / "scripts" / "_scan_quality.py"
SEGMENT_SCANNER = ROOT / "scripts" / "scan_timeline_gated_quality.py"
BATCH_RUNNER = ROOT / "scripts" / "run_timeline_gated_mmwave_quality.py"
PATH_CONFIG = ROOT / "configs" / "paths.local.json"
TARGET_AUDIT = ROOT.parent / "11_数据" / "derived" / "audit_j_mmwave_target_lock_v1.py"
TARGET_OUTPUT = ROOT.parent / "11_数据" / "derived" / "j_mmwave_target_lock_audit_v1" / "j_session_target_lock_summary_with_file_audit.csv"

FIELDS = [
    "session_id", "use_tier", "selected_bin_method", "range_min_m", "range_max_m",
    "selected_range_m_median", "selected_range_m_iqr", "range_bin_jump_rate",
    "channel_selection_method", "selected_channel_mode", "br_band", "hr_band",
    "hr_peak_method", "rr_method", "b_trigger_fields", "c_trigger_fields",
    "likely_fix_category",
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


def n(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def fmt(value: float | None, digits: int = 4) -> str:
    return "NA_not_available" if value is None else f"{value:.{digits}f}"


def reference_metrics() -> dict[str, dict[str, float | int | str]]:
    rows = read_csv(REF)
    specs = {
        "hr_peak": ("hr_mm_bpm", "hr_ecg_bpm"),
        "hr_course": ("hr_course_mm_bpm", "hr_ecg_bpm"),
        "br_peak": ("br_mm_bpm", "br_rsp_bpm"),
    }
    result: dict[str, dict[str, float | int | str]] = {}
    import numpy as np

    for label, (pred_key, ref_key) in specs.items():
        values = [(n(row.get(pred_key)), n(row.get(ref_key))) for row in rows]
        values = [(pred, refv) for pred, refv in values if pred is not None and refv is not None]
        pred = np.asarray([item[0] for item in values], dtype=float)
        ref = np.asarray([item[1] for item in values], dtype=float)
        error = pred - ref
        result[label] = {
            "n": int(len(values)),
            "mae": float(np.mean(np.abs(error))),
            "bias": float(np.mean(error)),
            "correlation": float(np.corrcoef(pred, ref)[0, 1]),
            "within_5_bpm": int(np.sum(np.abs(error) <= 5)),
            "reference_window_denominator": 100,
        }
    return result


def build_rows() -> list[dict[str, str]]:
    matrix = {row["session"]: row for row in read_csv(MATRIX)}
    qc = {row["session"]: row for row in read_csv(QC_SUMMARY)}
    target = {row["subject"]: row for row in read_csv(TARGET_OUTPUT)}

    rows: list[dict[str, str]] = []
    for session in sorted(matrix, key=lambda value: int(value)):
        q = qc[session]
        t = target.get(session, {})
        attribution = q["primary_attribution"]
        b_trigger = ""
        c_trigger = ""
        if session == "067":
            bin_method = "not_run: no linked mmWave input"
            channel_mode = "not_available"
            selected_median = "NA_not_available"
            b_trigger = ""
            c_trigger = ""
            fix = "coding/data-interpretation risk"
        else:
            bin_method = (
                "_scan_quality.scan_subject: full-session aggregate power; candidates >=1% max power; "
                "phase_var filter/fallback; HR score=log1p(hr_snr)*phase_stability^2"
            )
            if t:
                channel_mode = (
                    f"hr_ch={t.get('hr_ch', 'NA')}; best_ch={t.get('best_ch', 'NA')}; "
                    "BR channel not retained in target-lock summary"
                )
                selected_median = t.get("hr_bin_dist_m", "NA_not_available")
            else:
                channel_mode = "not_available"
                selected_median = "NA_not_available"
            status = t.get("preliminary_target_candidate_status", "")
            if status == "distance_implausible":
                b_trigger = (
                    f"target_lock_status=distance_implausible; distance_gate_020_100m=False; "
                    f"hr_bin_dist_m={t.get('hr_bin_dist_m', 'NA')}"
                )
                fix = "range-gate/human-body localization risk"
            elif status == "plausible_distance_phase_unstable":
                b_trigger = (
                    "target_lock_status=plausible_distance_phase_unstable; "
                    f"phase_stability_ge_090=False; phase_stability={t.get('phase_stability', 'NA')}"
                )
                fix = "motion-artifact risk (phase-stability proxy only)"
            elif status == "plausible_distance_low_signal_presence":
                fix = "timeline/window risk (supplemental linkage plus signal-existence gate)"
            elif attribution == "C_vital_algorithm_failure":
                fix = "motion-artifact risk / signal-existence gate (local cause unresolved)"
            else:
                fix = "unresolved: no trigger field localizes the remaining risk"
            if attribution == "C_vital_algorithm_failure":
                c_trigger = (
                    f"window_quality_pct={q.get('window_quality_pct', 'NA')}<80 or "
                    f"probe_quality_pct={q.get('probe_quality_pct', 'NA')}<80"
                )
            if session == "099":
                fix = "timeline/window risk (missing main-cohort timeline/meta linkage)"

        use_tier = q["analysis_bucket"]
        rows.append({
            "session_id": session,
            "use_tier": use_tier,
            "selected_bin_method": bin_method,
            "range_min_m": "0.30 (producer default; not applied by _scan_quality scanner)",
            "range_max_m": "1.50 (producer default; not applied by _scan_quality scanner)",
            "selected_range_m_median": selected_median,
            "selected_range_m_iqr": "NA_not_computable: existing target audit retains one HR bin/session",
            "range_bin_jump_rate": "NA_not_calculated_in_current_QC",
            "channel_selection_method": (
                "all 8 channels: aggregate channel power; per-channel separate BR/HR bin scores; "
                "max BR and max HR score selected independently"
            ) if session != "067" else "not_run",
            "selected_channel_mode": channel_mode,
            "br_band": "0.10-0.50 Hz",
            "hr_band": "0.80-2.00 Hz",
            "hr_peak_method": (
                "v3.1.1 full producer: heart peak detector + periodogram + IBI/time-course fusion; "
                "_scan_quality itself is signal-existence only and emits no HR"
            ),
            "rr_method": (
                "v3.1.1 full producer: consensus breath peak/periodogram plus MATLAB-style candidate; "
                "formal runner does not pass acq_path/RSP"
            ),
            "b_trigger_fields": b_trigger,
            "c_trigger_fields": c_trigger,
            "likely_fix_category": fix,
        })
    return rows


def write_doc(rows: list[dict[str, str]], metrics: dict[str, dict[str, float | int | str]]) -> None:
    b_distance = sum("distance_implausible" in row["b_trigger_fields"] for row in rows)
    b_phase = sum("phase_unstable" in row["b_trigger_fields"] for row in rows)
    c_rows = [row for row in rows if row["c_trigger_fields"]]
    c_detail_md = "\n".join(
        f"| {row['session_id']} | `{row['c_trigger_fields']}` |" for row in c_rows
    )
    md = f"""# MMWAVE ALGORITHM AND RANGE GATE AUDIT V1

日期：2026-08-28 ；状态：**PARTIAL / evidence-bounded**

本审计只回读当前代码、当前配置和已经存在的 formal/target-lock/reference 产物；没有重新运行 formal 全量算法，没有继续修改算法，也没有启动专注建模。`mmwave_algorithm_failure_trigger_audit.csv` 是本报告的逐 session 附表。

## 1. 当前实际脚本、commit、入口

| 角色 | 实际路径 | 入口/关键函数 | 版本证据 |
|---|---|---|---|
| 生命体征 producer | `{PRODUCER}` | `analyze_long_record()` → `_analyze_long_record_v23()`；强制心跳候选另有 `_analyze_long_record_with_forced_heart_candidate_v23()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; SHA256 `{sha256(PRODUCER)}` |
| formal 时间门控 batch runner | `{BATCH_RUNNER}` | `main()` → `run_analysis()` → `algo.analyze_long_record()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; current SHA256 `{sha256(BATCH_RUNNER)}`; working tree modified |
| formal 信号存在性 scanner | `{SEGMENT_SCANNER}` | `main()` → `scan_segment()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; current SHA256 `{sha256(SEGMENT_SCANNER)}`; working tree modified |
| J 盘 target-lock audit | `{TARGET_AUDIT}` | `main()` → `quality_core.scan_subject()` | 不在算法仓库；无该仓库 commit；SHA256 `{sha256(TARGET_AUDIT)}` |
| scanner 核心 | `{SCAN_CORE}` | `scan_subject()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; SHA256 `{sha256(SCAN_CORE)}` |
| 本机路径配置 | `{PATH_CONFIG}` | `formal_data_root` → `J:/Data`；`project_data_root` → `D:/Project/厚粲杯/11_数据` | 非代码配置；SHA256 `{sha256(PATH_CONFIG)}` |

当前 QC v1 的 72 场分层读取了既有 session matrix、`subject_summary.csv`、formal output audit 和 J 盘 target-lock audit；因此“实际用于 QC v1”的证据链是 `_scan_quality`/target-lock 产物加上既有 summary，不是本轮新跑出的 HR/RR 对照结果。

配置边界：`configs/paths.local.json` 的 `formal_data_root` 是 `J:/Data`；但 `run_timeline_gated_mmwave_quality.py` 与 `scan_timeline_gated_quality.py` 内仍保留 `E:\\Data`、`F:\\正式实验` 默认 roots，且没有在入口处读取 `paths.local.json`。本次 target-lock audit 的输入根由其代码显式固定为 `J:\\Data`，不能把两个默认 roots 当作本批实际输入。

## 2. 输入数据解释：已经是 range-bin complex data

`process_vital_signs_v3_1_1.py::_load_chunk()` 读取 NPZ 中按 `tx` 排序的 8 个数组，`np.stack(..., axis=-1).astype(np.complex64)`；`_as_range_cube()` 只做数组类型/形状转换。因此当前 producer 把输入解释为 **frame × range-bin × 8-channel 的 complex range-bin data**。

当前 producer 没有 raw ADC → Range FFT 的步骤。代码中的 `np.fft.rfft()`/`rfftfreq()`用于已提取相位/位移的时间频谱；`save_range_fft_*` 名称对应的诊断图也只是对已进入 range-bin cube 的幅度做可视化。上游是否曾从 raw ADC 生成这些 NPZ，不在当前 QC producer 链可见范围内。

## 3. 当前 HR/RR 流程

### Range bin 和 channel

- `_scan_quality.scan_subject()`：先对全 session 累积 range-bin/channel power；用第一个最多 1,000 frame 的样本调用 `select_separate_channels_bins()`，在所有 8 channels 上分别计算候选 bin 的 phase variance、HR/BR band SNR 和 phase-stability score；BR 与 HR 分别取最高分 channel/bin。
- `scan_timeline_gated_quality.scan_segment()`：对每个 baseline 或正式 block 重新累积、重新选一次 bin/channel；不是每个 10 s QC window 重新选择。`_scan_quality` 的 J 盘 target audit 则是每个 session 全时段选一次。
- 普通 producer `analyze_long_record()`：对每个传入的行为 segment/block 固定一次选择；先使用 distance gate 后再做 BR/HR 选择和 HR candidate refinement。不是 session 内每个输出 window 重新选。
- BR 与 HR **不保证共用** bin/channel：结果字段分别保存 `channels.breath/channels.heart` 与 `bins.breath/bins.heart`。

### Phase、band 和 rate estimator

- phase：`np.unwrap(np.angle(complex_signal))`；普通 producer 的 selected signal 在 segment 范围内展开；`_scan_quality` 的 target scan 对每个 NPZ part 分别展开，然后带通。
- 呼吸 band：`0.10–0.50 Hz`（6–30 bpm）。这是当前 mmWave producer；不能与 ECG/RSP 小样本复盘中的 RSP `0.10–0.70 Hz`混写。
- cardiac band：`0.80–2.00 Hz`（48–120 bpm）。
- 完整 producer 的 HR 不是单一方法：包含 heart peak detector/IBI time estimate、periodogram frequency estimate、VMD heart-mode selection 和 time-course/fusion。`_scan_quality`/`scan_timeline_gated_quality` 只计算心跳带位移的 10 s std 信号存在性，不输出 HR/RR 数值。
- 完整 producer 的 BR 是 consensus peak/periodogram 候选并包含 MATLAB-style 分支；但当前 formal runner 没有传 `acq_path`，所以外部 RSP 呼吸率与 `respiration_harmonic_reject()` 这条参考辅助支路在当前 formal batch runner 中没有被激活。

## 4. 人体范围限制和 localization

| 项目 | 实际代码/产物结论 |
|---|---|
| producer 默认 `min_range_m/max_range_m` | `0.30 / 1.50 m`；普通 `_analyze_long_record_v23()` 将 mask 应用于 breath 和 heart。 |
| `bin_to_meter` | `distance_m = bin_idx * bin_spacing_m - range_bias_m`；默认 `bin_spacing_m=0.08 m`、`range_bias_m=0.0 m`。 |
| 当前 scanner 是否应用该 gate | **没有**。`_scan_quality.py` 和 `scan_timeline_gated_quality.py`调用 bin selector 时未传入 distance mask；target-lock audit 另用 `0.20–1.00 m` 对自动候选距离作 preliminary 分类。 |
| 是否显式建模胸腔 | 没有。距离 gate 只是工程范围限制，不等于胸腔真值。 |
| 是否排除键盘/桌面/近场反射 | 未见对应的对象/平面/近场分类规则；不能声称已排除。 |
| 是否用静息基线定胸腔 bin | 当前 formal runner 未传 `heart_reference_candidates`，未见静息 baseline 自动锁定胸腔 bin。 |
| range-bin jump gate | 未实现/未出现在当前产物；`range_bin_jump_rate` 没有被计算。 |

## 5. B=44 的实际触发机制

B 的 44 场不是由一个叫 `range_bin_jump_rate` 的字段触发。当前 evidence breakdown 是：

- **36 场**：target-lock `distance_implausible`，具体字段是 `distance_gate_020_100m=False` 和自动候选 `hr_bin_dist_m` 落在 `0.20–1.00 m` 之外。
- **8 场**：`plausible_distance_phase_unstable`，具体字段是 `phase_stability_ge_090=False`。

现有 B 证据中没有 `motion_artifact_ratio`、`valid_phase_coverage` 或 `range_bin_jump_rate`。`phase_stability` 是基于相位 roughness/jump ratio/oscillation 的综合 proxy，不能改写成 motion-artifact ratio。target-lock 是全 session 扫描，而 formal segment scanner 是按 baseline/block 切分；当前输出没有字段能证明某个 B 是由 window 切错导致。因此 window miscut 只能列为待查风险，不能作为已触发 B 的事实。

## 6. C=9 的实际触发机制与 ECG/RSP 指标边界

C 的 9 场是：`056, 058, 062, 081, 084, 104, 118, 162, 166`。它们都已有输入/输出链和 target candidate，但 `subject_summary.csv` 中 `window_quality_pct < 80` 或 `probe_quality_pct < 80`；这就是当前 C trigger。精确值已写入附表 `c_trigger_fields`。

| session_id | 实际 C trigger |
|---|---|
{c_detail_md}

这 9 场**不是**由 per-session HR/RR MAE、bias、correlation、`harmonic_suspect`、`low_corr` 或 `stable_bias` 触发，因为这些字段不在当前 formal 70 场输入/输出中；也不能从当前文件证明“RR pass 但 HR fail”。当前 C 只能说“既有 signal-existence/probe coverage gate 未过，局部原因未解析”，不能写成 HR/RR 生理准确性失败。

可计算的 ECG/RSP 参考指标只来自独立的历史小样本 reference CSV（5 场参考、100 个 60 s 窗口；当前指标行 99），不是 formal 70 场逐 session gate：

| 参考比较 | n / 参考窗口分母 | MAE | bias（mmWave−reference） | correlation |
|---|---:|---:|---:|---:|
| HR peak | {metrics['hr_peak']['n']} / {metrics['hr_peak']['reference_window_denominator']} | {metrics['hr_peak']['mae']:.3f} bpm | {metrics['hr_peak']['bias']:.3f} bpm | {metrics['hr_peak']['correlation']:.3f} |
| HR course | {metrics['hr_course']['n']} / {metrics['hr_course']['reference_window_denominator']} | {metrics['hr_course']['mae']:.3f} bpm | {metrics['hr_course']['bias']:.3f} bpm | {metrics['hr_course']['correlation']:.3f} |
| BR peak | {metrics['br_peak']['n']} / {metrics['br_peak']['reference_window_denominator']} | {metrics['br_peak']['mae']:.3f} bpm | {metrics['br_peak']['bias']:.3f} bpm | {metrics['br_peak']['correlation']:.3f} |

这些 aggregate 不能回填为 C=9 的 per-session 指标，也没有被当前 formal C gate 使用。当前 formal 70 场的 coverage 总和是 `2894/3525` 个 10 s signal-existence windows、`1297/1400` 个 probe-level quality flags；后者不是 HR/RR pass。

## 7. 审计表字段说明

完整文件：`mmwave_algorithm_failure_trigger_audit.csv`。

- `range_min_m/range_max_m` 填的是普通 v3.1.1 producer 默认值 `0.30/1.50`，并在字段中保留了“scanner not applied”限定；B 的实际 preliminary target 分类阈值 `0.20–1.00 m`写在 `b_trigger_fields`。
- `selected_range_m_median` 只是既有 target audit 保留的一个 HR candidate distance；`selected_range_m_iqr` 不可从现有 summary 计算，不能假装有 session 内 range 分布。
- `range_bin_jump_rate` 明确为 `NA_not_calculated_in_current_QC`。
- `selected_channel_mode` 只报告 target audit 实际保留的 HR/best channel；当前 target summary 没有保存 BR channel，因此不补造 BR channel。

## 8. 分层结论（按风险类别）

### coding/data-interpretation risk

当前 NPZ 被代码按 8-channel complex range-bin cube 读取；当前链没有 raw ADC→Range FFT。若上游文件实际不是该格式，风险发生在 producer 边界之外，必须先做输入 schema/metadata 验证。067 没有可追溯输入，不能进入 formal v1。

### timeline/window risk

正式 batch runner 以 baseline 或单个行为 block 的明确 frame range 调用 producer；segment scanner 也按 segment 计算，但 target audit 是全 session 扫描。现有结果没有能证明 window miscut 的字段；099 另有主队列 timeline/meta linkage 缺失，保留为不可用，不应与 B/C 混写。

### range-gate/human-body localization risk

普通 producer 的工程 gate 是 0.30–1.50 m；当前 signal scanner 未应用该 gate，target-lock preliminary 分类使用 0.20–1.00 m。B 的 36 场由该距离合理性分类触发。距离候选本身不能证明人体胸腔锁定，也没有键盘/桌面/近场目标排除证据。

### motion-artifact risk

B 的 8 场有 `phase_stability_ge_090=False`；这是相位稳定性 proxy，不是已测得的 motion-artifact ratio。C 的 9 场只显示窗口/probe signal-existence coverage 未达门槛，具体局部原因仍未解析。

### harmonic/peak-selection risk

完整 producer 同时使用 peak、periodogram、IBI/time-course 和 VMD/fusion；代码提供基于外部 RSP 的 2×/3×呼吸谐波拒绝，但当前 formal runner 未传 `acq_path`，所以该支路不是当前 formal batch 的 active gate。独立小样本中 HR peak 与 HR course 的指标不同，说明 peak-selection/fusion 需要保留为独立风险；不能将其写成 C=9 的逐场已证实原因。HRV 逐搏证据也不能由当前 QC scanner 推出。

## 9. 最终口径

当前证据支持的表达是：17 场是通过既有窗口/probe/target-lock preliminary gate 的 **QC-eligible candidates**；53 场只能保留微动/体动层（B=44、C=9）；2 场因输入或主队列 linkage 阻断不可用。17 场不是“生命体征已验证可用”，`1297/1400` 不是“毫米波生命体征可用”。

来源文件哈希与逐 session 数值以本目录已有 manifest、`mmwave_session_qc_summary_redacted.csv` 和本次附表为准。
"""
    (OUT / "MMWAVE_ALGORITHM_AND_RANGE_GATE_AUDIT_V1.md").write_text(md, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with (OUT / "mmwave_algorithm_failure_trigger_audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    write_doc(rows, reference_metrics())
    print(json.dumps({"rows": len(rows), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()


