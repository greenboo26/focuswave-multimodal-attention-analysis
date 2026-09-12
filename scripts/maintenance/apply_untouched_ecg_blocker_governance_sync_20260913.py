#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Governance sync for the mmWave untouched-ECG-validation-set blocker.

File: apply_untouched_ecg_blocker_governance_sync_20260913.py
Version: 1.0.0
Purpose:
    记录 mmwave_hr_untouched_ecg_validation_set_v1 的 BLOCKED 结论，并更正
    MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1 中原先把 OPT_A 描述为"只差一个
    可工程补齐的 ECG 参考"的错误表述。

Usage:
    python scripts/maintenance/apply_untouched_ecg_blocker_governance_sync_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LEDGER_ENTRY = """### 2026-09-13：mmWave untouched ECG validation set v1 — BLOCKED / ECG 参考来源不存在

**Reuse Gate**：本任务不重跑算法、不实现 C1/C2。复用 `ECG_RSP独立验证资产审计_20260824.md`（权威 ECG 资产性质记录）、`ecg_rsp_goldclean_reaudit_v1`、`physiology_reference_v1` 与 `configs/paths.local.json` 声明的四个候选根；没有新算法、没有新阈值。`REUSE_REJECTION_REASON`：preregistration 冻结的验证集 contract 要求"独立 per-window gold-clean ECG 参考"，而该输入是否存在从未被核对过，必须先做前提核查。

**核心结论 `BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE`**：全机 `.acq` 穷尽扫描结果为 —— `D:\\acq_mmwave_data` **11** 个、`I:\\预实验`（E-batch，10 sessions）**0** 个、`J:\\Data`（J-batch，72 sessions）**0** 个、`11_数据` **0** 个。**只有 11 个 session 有 ECG，全部在校准根**，且分三类：5 个校准 session（`sub-2_`-`sub-6_`）有 ECG 但**无 probe 窗口**；5 个开发 session（`9779/97793/97994/97795/97796`）有 ECG 且有 probe 窗口但**已被反复消费**；`sub-97792_` 有 ECG 但 `events.csv` 无 block1-4 probe 段，既有记录已判 `not_estimable`。

**决定性设计证据**：`11_数据/derived/ECG_RSP独立验证资产审计_20260824.md` 明确 `D:\\acq_mmwave_data` **不是正式实验的多被试队列，而是同一人反复测量的双机校准**（电脑 A 采毫米波并经并口发 marker，电脑 B 的 BIOPAC MP160 记录 ECG/RSP），并标注 `calibration_reference_only_not_formal_subject_effect`、不得与正式被试主索引合并。正式 `J:\\Data` session 结构为 `beh/mmwave/nir/rgb` 四目录，**无 ECG 通道**。

**因此 `VS_4`（独立 ECG 参考）、`VS_5`（窗口契约，依赖 ECG/BIOPAC marker 对齐）、`VS_6`（ECG 资格）、`VS_7`（分母冻结）无法满足，contract 满足 6/10，验证集无法形成，C1/C2 不得运行。**

**更正**：`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1` 与 `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` 此前把 OPT_A 描述为"唯一只差一个可工程补齐的 ECG 参考"，并把该缺口称为"数据工程任务而非科学决策"。**该表述错误**：缺口是**输入根本不存在**。错误根因是前两轮只核对"正式 session 是否与开发集重叠"，**没有核对"正式 cohort 是否有 ECG"**。本任务撤回该建议并记录更正。

**修复选项（需裁决）**：`REM_1` 确认正式 cohort 是否采集过 ECG 并取回（推荐先做）；`REM_2` 新采集一组 participant/session 不重叠且同时有 mmWave+ECG 的数据；`REM_3` 用校准 session 建新窗口契约（**不推荐**，与开发集同属同一名参与者，参与者不重叠不成立，且需改冻结契约）；`REM_4` 接受当前不存在合规验证集，保持 HR/BR `HOLD`、HRV `BLOCKED` 并挂起 C1/C2 与 snapshot v2。

**证据**：`docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/`（report、manifest、`ECG_SOURCE_FEASIBILITY_SCAN.csv`、`VALIDATION_SET_CONTRACT_PRECONDITIONS.csv`、error log、handoff）；脚本 `scripts/maintenance/run_mmwave_untouched_ecg_validation_feasibility_20260913.py`；测试 `tests/test_mmwave_hr_untouched_ecg_validation_set.py`。未改 producer、snapshot v1 或任何原始数据；HRV 仍 `BLOCKED`。

---
"""

STATUS_ENTRY = """## 2026-09-13 mmWave untouched ECG validation set v1 — BLOCKED / ECG 参考来源不存在

- **`BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE`**：全机 `.acq` 穷尽扫描 —— `D:\\acq_mmwave_data` **11**、`I:\\预实验` **0**、`J:\\Data`（72 sessions）**0**、`11_数据` **0**。只有 11 个 session 有 ECG，全部在校准根：5 个校准 session（`sub-2_`-`sub-6_`）有 ECG 但无 probe 窗口；5 个开发 session（`9779/97793/97994/97795/97796`）有 ECG 但已被消费；`sub-97792_` 无 block1-4 probe 段、已判 `not_estimable`。
- **设计证据**：`ECG_RSP独立验证资产审计_20260824.md` 明确该池是**同一人反复测量的双机校准**（`calibration_reference_only_not_formal_subject_effect`），不是多被试队列；正式 `J:\\Data` 只有 `beh/mmwave/nir/rgb`，**从未采集 ECG**。
- **后果**：`VS_4`/`VS_5`/`VS_6`/`VS_7` 无法满足（contract 6/10），`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` 无法形成，**C1/C2 不得运行**，snapshot v2 无从讨论。
- **更正**：此前把 OPT_A 描述为"只差一个可工程补齐的 ECG 参考"是**错误**的；缺口是输入不存在。根因是前两轮未核对正式 cohort 是否有 ECG。该建议已撤回。
- **修复选项**：`REM_1` 确认/取回正式 cohort ECG（推荐先做）→ 否则 `REM_2` 新采集 或 `REM_4` 接受缺失（HR/BR `HOLD`、HRV `BLOCKED`）。`REM_3`（用校准 session）**不推荐**。
- 本任务只做前提核查：未实现候选、未跑候选、未改 producer / snapshot v1 / 原始数据，未形成 snapshot v2，HRV=`BLOCKED`。
- 证据：`docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/`；测试 `tests/test_mmwave_hr_untouched_ecg_validation_set.py`。

"""

RESULT_INDEX_ROW = (
    "| MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1_20260913 | BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE / SET_NOT_FORMED | "
    "[precondition feasibility audit and ECG coverage inventory](../results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/) | "
    "Git-safe package in `docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/`; no validation set was produced; "
    "local-only ECG assets under `11_数据/derived` | "
    "Exhaustive .acq scan shows only 11 ECG-bearing sessions on this machine, all under the calibration root: 5 calibration sessions "
    "with no probe windows, 5 already-consumed development sessions, and sub-97792 recorded as not_estimable. The formal cohort "
    "(J:/Data 72 + pre-experiment 10) never acquired ECG, and the calibration pool is by design one participant measured repeatedly. "
    "VS_4/VS_5/VS_6/VS_7 therefore cannot be satisfied (contract 6/10), so the untouched validation set cannot be formed and C1/C2 "
    "must not run. This retracts the earlier OPT_A recommendation, which had called the missing ECG reference an engineering gap. "
    "No producer or snapshot v1 change, no v2, HRV BLOCKED |\n"
)

PLAN_ANCHOR = "**Routing update (after the external audit): `OPT_A` is confirmed as the primary untouched validation source, to be built next.**"
PLAN_CORRECTION = """**CORRECTION (2026-09-13, `MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1`): `OPT_A` CANNOT BE BUILT. This plan's `OPT_A` description is retracted.**

`OPT_A` was described here and in `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` as available apart from a missing independent per-window gold-clean ECG reference, and that gap was called a data-engineering task rather than a science decision. **That was wrong.** The gap is a **missing input**: the formal cohort never acquired ECG at all. An exhaustive `.acq` scan found only 11 ECG-bearing sessions on this machine, all under `D:\\acq_mmwave_data`: 5 calibration sessions with no probe windows, 5 already-consumed development sessions, and `sub-97792_` which has no block1-4 probe events and is recorded as `not_estimable`. The authoritative local record `11_数据/derived/ECG_RSP独立验证资产审计_20260824.md` states that this pool is **one participant measured repeatedly for two-machine calibration** (`calibration_reference_only_not_formal_subject_effect`), not a multi-subject cohort. Root cause of the error: earlier rounds verified that formal sessions do not overlap the development set, but never verified that the formal cohort has ECG.

Consequence: `VS_4_INDEPENDENT_ECG_REFERENCE`, `VS_5_WINDOW_CONTRACT`, `VS_6_ECG_ELIGIBILITY` and `VS_7_DENOMINATOR_FROZEN` cannot be satisfied (contract 6/10), so `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` cannot be formed and C1/C2 must not be run. Next dependency: `REM_1` (determine whether the formal cohort ever acquired ECG and retrieve it), otherwise `REM_2` (new acquisition) or `REM_4` (accept the absence and keep HR/BR `HOLD`, HRV `BLOCKED`). `REM_3` (calibration sessions under a new window contract) remains **not recommended**.

Evidence: `docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/`.

"""

AI_PROJECT_MARKER = "- mmwave_current_external_asset_audit: `docs/results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/` (no external asset is C1-eligible; VS_DATASET is C2-only secondary evidence)\n"
AI_PROJECT_ADDITION = (
    "- mmwave_untouched_validation_blocker: `docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/` "
    "(BLOCKED: no ECG source exists for the formal cohort, so no untouched validation set can be formed)\n"
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
    marker = "### 2026-09-13：mmWave external validation asset audit v1"
    if "mmWave untouched ECG validation set v1" in text:
        print("skip (already present): ANALYSIS_HISTORY_LEDGER.md")
    else:
        if text.count(marker) != 1:
            raise SystemExit("ledger anchor not unique")
        ledger.write_text(text.replace(marker, LEDGER_ENTRY + "\n" + marker, 1), encoding="utf-8", newline="\n")
        print("inserted: ANALYSIS_HISTORY_LEDGER.md")

    insert_after_unique(REPO / "PROJECT_STATUS.md",
                        "# FocusWave Multimodal Attention Analysis 状态\n\n",
                        STATUS_ENTRY, "PROJECT_STATUS.md")

    index = REPO / "docs" / "canonical" / "RESULT_INDEX_V1.md"
    text = index.read_text(encoding="utf-8")
    if "MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1_20260913" in text:
        print("skip (already present): docs/canonical/RESULT_INDEX_V1.md")
    else:
        anchor = "| MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_20260913 |"
        if text.count(anchor) != 1:
            raise SystemExit("result index anchor not unique")
        line_start = text.index(anchor)
        line_end = text.index("\n", line_start) + 1
        index.write_text(text[:line_end] + RESULT_INDEX_ROW + text[line_end:], encoding="utf-8", newline="\n")
        print("inserted: docs/canonical/RESULT_INDEX_V1.md")

    insert_after_unique(REPO / "AI_PROJECT.md", AI_PROJECT_MARKER, AI_PROJECT_ADDITION, "AI_PROJECT.md")

    plan = REPO / "docs" / "canonical" / "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md"
    text = plan.read_text(encoding="utf-8")
    if "CANNOT BE BUILT" in text:
        print("skip (already corrected): MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md")
    else:
        if text.count(PLAN_ANCHOR) != 1:
            raise SystemExit("plan anchor not unique")
        plan.write_text(text.replace(PLAN_ANCHOR, PLAN_CORRECTION + PLAN_ANCHOR, 1),
                        encoding="utf-8", newline="\n")
        print("inserted: docs/canonical/MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md")


if __name__ == "__main__":
    main()