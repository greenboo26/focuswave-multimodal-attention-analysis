"""汇总行为裁剪质量、文件审计与 ECG/RSP 独立参照，生成省赛报告素材。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(r"D:\Project\厚粲杯")
OUTPUT = PROJECT_ROOT / "08_算法" / "output" / "10_质量控制" / "01_行为时间门控" / "J_Data_行为时间裁剪_v1"
ACQ = PROJECT_ROOT / "08_算法" / "output" / "20_生理金标准验证" / "01_历史严格参照_v20260821"
REPORT_OUTPUT = PROJECT_ROOT / "08_算法" / "work" / "issue15_formal_physiology_run_2026-08-27" / "output" / "mmwave_quality"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    crop = load_json(OUTPUT / "crop_summary.json")
    rows = []
    for tag in ("E_Data", "Formal_mmwave"):
        rows.extend(load_json(OUTPUT / tag / "segment_quality.json"))
    task = [row for row in rows if row["status"] == "ok" and row["layer"] == "task"]
    baseline = [row for row in rows if row["status"] == "ok" and row["layer"] == "baseline"]
    if len(task) != 281 or len(baseline) != 130:
        raise RuntimeError(f"分段扫描未完整：task={len(task)}/281, baseline={len(baseline)}/130")
    counts = {level: sum(row["signal_existence_level"] == level for row in task) for level in ("pass", "partial", "fail")}
    acq = load_json(ACQ / "acq_reference_validation_summary.json")
    report = f"""# 省赛报告素材：毫米波数据质量与独立生理验证

生成日期：2026-08-23。该材料仅汇总当前可追溯证据，数值准确性与信号存在性分别报告。

## 数据完整性与分析口径

正式实验共核查 {crop['n_records']} 个被试目录，其中 {crop['n_included']} 条记录纳入主队列，{crop['n_excluded_invalid']} 条因毫米波文件缺失或空录制排除，sub-099 保持待复核。每名被试的毫米波记录均依照行为时间轴裁剪：静息基线限定为 baseline_start 至 baseline_stop；正式任务限定为各 block_start 至 block_stop。练习、说明页、block 间休息与结束后尾段均未进入分析。130 名被试中，109 名完成 2 个正式 block，21 名完成 3 个正式 block，共形成 281 个正式任务片段和 130 个独立基线片段。

## 正式任务的毫米波信号存在性

在 281 个正式任务片段中，{counts['pass']} 个片段的心跳带通位移 10 秒窗有至少 80% 高于既有 0.0005 mm 噪声阈值，{counts['partial']} 个片段为部分通过，{counts['fail']} 个片段未通过。任务片段的可用窗比例中位数为 {np.median([row['usable_ratio'] for row in task]):.3f}；基线片段的对应中位数为 {np.median([row['usable_ratio'] for row in baseline]):.3f}。该指标只证明雷达中存在可供心跳频段分析的相位位移信号，不能替代心电图对心率数值的验证，也不能证明心率变异性有效。

## ECG/RSP 独立参照

采用 BIOPAC ECG（心电图，记录心脏电活动）和 RSP（呼吸带，记录胸腹呼吸活动）作为独立参照。在 5 名具有严格 SART 行为门控窗口的被试中，共配对 {acq['paired_windows']} 个窗口。毫米波滑动心率与 ECG 的平均绝对误差为 {acq['heart_rate_course']['mae_bpm']:.2f} bpm（{acq['heart_rate_course']['within_5_bpm']}/{acq['heart_rate_course']['n']} 个窗口误差不超过 5 bpm）；逐峰心率误差为 {acq['heart_rate_peak']['mae_bpm']:.2f} bpm，仍可见谐波相关偏差。经低频半频候选修正后的频谱呼吸率误差为 {acq['respiration_spectral']['mae_bpm']:.2f} 次/分。RMSSD 与 SDNN 的误差分别为 {acq['hrv_rmssd']['mae_ms']:.2f} ms 和 {acq['hrv_sdnn']['mae_ms']:.2f} ms，说明原始毫米波逐搏间期尚未达到可直接解释的精度。HRV 保留为本项目的核心待验证特征：将以 ECG 标注的校准数据训练和冻结校正规则，并在留出被试上验证 IBI、RMSSD 与 SDNN 误差后，再进入正式注意模型。

## 可写入报告书的结论

本系统已完成 130 条正式实验毫米波记录的文件完整性核查与行为时间对齐，并可在正式任务片段中实施可追溯的信号存在性质量控制。独立 ECG 对照支持将质量门控后的毫米波滑动心率用于研究性趋势观察；呼吸率仅保留经质量标记的频谱候选结果。HRV 不应因当前原始误差而从项目中移除，而应作为需要 ECG 校正、被试外验证后才启用的核心特征。系统的专注效标仍以 SART 行为与探针报告为主，ECG 仅用于方法校正与验证，不参与正式实验的标签或实时输入。

## 追溯文件

- `crop_manifest.json/csv`：130 名被试的裁剪范围、保留帧数和排除原因。
- `E_Data/segment_quality.*`、`Formal_mmwave/segment_quality.*`：281 个任务片段与 130 个基线片段的质量扫描。
- `ACQ_reference_20260821/acq_reference_validation_summary.json`：ECG/RSP 独立参照结果。
"""
    REPORT_OUTPUT.mkdir(parents=True, exist_ok=True)
    (REPORT_OUTPUT / "省赛报告_毫米波质量与独立验证_20260827.md").write_text(report, encoding="utf-8")
    summary = {"crop": crop, "task_segment_counts": counts, "task_segments": len(task), "baseline_segments": len(baseline), "acq_reference": acq}
    (REPORT_OUTPUT / "省赛报告_毫米波质量与独立验证_20260827.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(REPORT_OUTPUT / "省赛报告_毫米波质量与独立验证_20260827.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


