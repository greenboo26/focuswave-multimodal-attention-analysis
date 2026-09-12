#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apply the external-asset-audit governance sync to canonical current-state files.

File: apply_external_audit_governance_sync_20260913.py
Version: 1.0.0
Purpose:
    把 mmWave external validation asset audit v1 的状态写入 canonical 状态文件。
    只新增本次状态，不重写历史结果。

Usage:
    python scripts/maintenance/apply_external_audit_governance_sync_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LEDGER_ENTRY = """### 2026-09-13：mmWave external validation asset audit v1 — ASSET_AUDIT_COMPLETE

**Reuse Gate**：本任务不重跑任何 HR 算法、不实现 C1/C2、不改 producer。复用 `vitalsense_c1b_benchmark_v1`（本地已完成的 C1b 基准）、`ANALYSIS_HISTORY_LEDGER.md` 的 AgeBalanced 2026-08-14 条目、以及三个外部数据集的只读检查；没有新算法、没有新 threshold。`REUSE_REJECTION_REASON`：preregistration v1 的 validation inventory 只扫了内部来源，漏掉本机三个外部公开数据集，必须先查清才决定是否值得给正式 cohort 重建 ECG gold-clean。

**核心结论**：**没有任何外部资产对 C1 可用；C2 只有 `VS_DATASET_healthy_v1` 可用且只能是 secondary。**

- `VS_DATASET_healthy_v1`（24 人，Resting+Apnea 48 段）：有 Mindray ECG Lead II（500 Hz，120 s）与呼吸/脉搏/每分钟 HR/RR；但雷达侧只有**已提取的单通道位移 `VitalSig`**（40,000 @ 333.3 Hz），**无 range bin、无通道、无 DataCube**，因此 C1 的"选择链内频域候选打分"机制无法表达；且本机已有**已完成的 C1b 正式基准**（`RUN_ID=C1B_VS_DATASET_20260825_V1`，`status=BENCHMARK_COMPLETE`，24 subjects / 48 pairs / 384 rows，含 `raw_hr_abs_error_bpm`/IBI/RMSSD/SDNN/beat 匹配指标；方法 `project_bandpass_peak` 与 `vitalsense_amf`；仅用 VS01 Resting 估一个全局固定延迟 −18.0 ms；报告自述不构成 beat/IBI/HRV 验证）。判定 `PARTIAL_CANDIDATE_SECONDARY`。
- `AgeBalanced_60GHz`（110 人，ECG ~250 Hz，range-FFT 帧 10 Hz）：**已被用于 HR 路线评估与选型**（commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1`；已公布 project route session-MAE median ≈ 9.5 BPM、HPS 10.6→9.7 保留、固定呼吸谐波陷波 9.5→10.4 回退、top3 multi-bin 9.5→9.3、VMD adaptive 不采用；官方 ECG FFT 参考重算 30 s pooled MAE = 10.361 BPM）。路线级暴露使其不再是未触碰验证集，判定 `INELIGIBLE_FOR_PRIMARY_VALIDATION`。
- `mmWave_Heartbeat`（TI gby 批次）：只有 10 个原始 ADC `.bin`，**无 ECG、无时间戳、无采集配置、无被试映射**，既无 ground truth 也无时间基准。判定 `INELIGIBLE`。

**路由决定**：`OPT_A` 确认为 **primary untouched validation** 并将执行；`VS_DATASET_healthy_v1` 追加为 **secondary external evidence（仅 C2）**；`AgeBalanced` 与 TI gby 不使用。新增硬边界：**`VS_DATASET` 不构成 C1 的任何证据**。判据与阈值不变，不因外部数据可用而放松。

**证据**：`docs/results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/`（report、manifest、`EXTERNAL_ASSET_ASSESSMENT.csv`、`EXTERNAL_ASSET_HISTORY_TRACE.csv`、error log、handoff）；脚本 `scripts/maintenance/run_mmwave_external_validation_asset_audit_20260913.py`；测试 `tests/test_mmwave_external_validation_asset_audit.py`。本地证据 `11_数据/derived/vitalsense_c1b_benchmark_v1/` 为 local-only。未修改任何外部数据、producer 或 snapshot v1；HRV 仍 `BLOCKED`。

---
"""

STATUS_ENTRY = """## 2026-09-13 mmWave external validation asset audit v1 — ASSET_AUDIT_COMPLETE

- **没有任何外部资产对 C1 可用**；C2 只有 `VS_DATASET_healthy_v1` 可用且只能作 secondary。preregistration v1 的 inventory 漏掉本机三个外部数据集，本任务补齐并据此调整路由。
- `VS_DATASET_healthy_v1`（24 人 / 48 段）：有 Mindray ECG Lead II（500 Hz、120 s）金标准，但雷达侧只有**预提取单通道位移 `VitalSig`**（40,000 @ 333.3 Hz），无 range bin / 通道 / DataCube → C1 机制无法表达；且本机已有**已完成 C1b 基准**（`C1B_VS_DATASET_20260825_V1`，24 subjects / 48 pairs / 384 rows，含 HR/IBI/RMSSD/SDNN 指标，报告自述不构成 beat/IBI/HRV 验证）→ 仅 `PARTIAL_CANDIDATE_SECONDARY`。
- `AgeBalanced_60GHz`（110 人，ECG ~250 Hz，range-FFT 帧 10 Hz）：**已被用于 HR 路线评估与选型**（commit `f4a8c74d…`；已公布 9.5 BPM、10.361 BPM 等数字）→ `INELIGIBLE_FOR_PRIMARY_VALIDATION`。
- `mmWave_Heartbeat`（TI gby）：仅 10 个原始 ADC `.bin`，无 ECG、无时间戳、无采集配置 → `INELIGIBLE`。
- **路由**：`OPT_A`（正式 cohort 116 sessions / 61 participant groups）确认为 primary untouched validation 并将执行；`VS_DATASET_healthy_v1` 追加为 **secondary external evidence（仅 C2）**；`AgeBalanced` 与 TI gby 不使用。
- **新增硬边界**：`VS_DATASET` 不构成 C1 的任何证据；C2 的 primary 仍是 `OPT_A`，`VS_DATASET` 结果必须同时声明 secondary 与已被 C1b 消费的历史。判据与阈值不变。
- 本任务只做资产追溯：未运行 C1/C2、未训练模型、未修改任何外部数据 / producer / snapshot v1，未形成 snapshot v2，HRV=`BLOCKED`。
- 证据：`docs/results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/`；测试 `tests/test_mmwave_external_validation_asset_audit.py`。

"""

RESULT_INDEX_ROW = (
    "| MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_20260913 | ASSET_AUDIT_COMPLETE / NO_CANDIDATE_RUN | "
    "[external asset audit report, assessment and history trace](../results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/) | "
    "Git-safe package in `docs/results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/`; external datasets stay local-only and unmodified; "
    "C1b local evidence at `11_数据/derived/vitalsense_c1b_benchmark_v1` | "
    "Audited the three local external datasets before committing to OPT_A: VS_DATASET_healthy_v1 is C2-capable but already consumed by a completed C1b "
    "benchmark and cannot express C1 (pre-extracted displacement only, no DataCube); AgeBalanced_60GHz was already used for HR route selection; "
    "mmWave_Heartbeat (TI gby) has no ECG reference and no time base. No external asset is C1-eligible. Routing: OPT_A remains primary untouched "
    "validation, VS_DATASET added as secondary C2-only external evidence, the other two excluded; no candidate run, no producer or snapshot v1 change, "
    "no v2, HRV BLOCKED |\n"
)

AI_PROJECT_MARKER = "- mmwave_current_preregistration: `docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md` (FROZEN_PREREGISTRATION; C1/C2 not implemented and not run)\n"
AI_PROJECT_ADDITION = (
    "- mmwave_current_external_asset_audit: `docs/results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/` "
    "(no external asset is C1-eligible; VS_DATASET is C2-only secondary evidence)\n"
)


def insert_after_unique(path: Path, anchor: str, payload: str, label: str) -> None:
    """Insert payload after the single occurrence of anchor."""
    text = path.read_text(encoding="utf-8")
    if payload.strip()[:50] in text:
        print(f"skip (already present): {label}")
        return
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"anchor count {count} for {label}")
    path.write_text(text.replace(anchor, anchor + payload, 1), encoding="utf-8", newline="\n")
    print(f"inserted: {label}")


def main() -> None:
    """Apply all governance sync edits."""
    ledger = REPO / "ANALYSIS_HISTORY_LEDGER.md"
    text = ledger.read_text(encoding="utf-8")
    marker = "### 2026-09-13：mmWave HR candidate preregistration v1"
    if "mmWave external validation asset audit v1" in text:
        print("skip (already present): ANALYSIS_HISTORY_LEDGER.md")
    else:
        if text.count(marker) != 1:
            raise SystemExit("ledger anchor not unique")
        ledger.write_text(text.replace(marker, LEDGER_ENTRY + "\n" + marker, 1), encoding="utf-8", newline="\n")
        print("inserted: ANALYSIS_HISTORY_LEDGER.md")

    insert_after_unique(
        REPO / "PROJECT_STATUS.md",
        "# FocusWave Multimodal Attention Analysis 状态\n\n",
        STATUS_ENTRY,
        "PROJECT_STATUS.md",
    )

    index = REPO / "docs" / "canonical" / "RESULT_INDEX_V1.md"
    text = index.read_text(encoding="utf-8")
    if "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_20260913" in text:
        print("skip (already present): docs/canonical/RESULT_INDEX_V1.md")
    else:
        anchor = "| MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_20260913 |"
        if text.count(anchor) != 1:
            raise SystemExit("result index anchor not unique")
        line_start = text.index(anchor)
        line_end = text.index("\n", line_start) + 1
        index.write_text(text[:line_end] + RESULT_INDEX_ROW + text[line_end:], encoding="utf-8", newline="\n")
        print("inserted: docs/canonical/RESULT_INDEX_V1.md")

    insert_after_unique(REPO / "AI_PROJECT.md", AI_PROJECT_MARKER, AI_PROJECT_ADDITION, "AI_PROJECT.md")


if __name__ == "__main__":
    main()
