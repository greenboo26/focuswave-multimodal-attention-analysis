#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apply the preregistration governance sync to canonical current-state files.

File: apply_preregistration_governance_sync_20260913.py
Version: 1.0.0
Purpose:
    把 mmWave HR candidate preregistration v1 的状态写入 canonical 状态文件。
    只新增本次状态，不重写历史结果。

Usage:
    python scripts/maintenance/apply_preregistration_governance_sync_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LEDGER_ENTRY = """### 2026-09-13：mmWave HR candidate preregistration v1 — FROZEN_PREREGISTRATION（未实现、未运行）

**Reuse Gate**：本任务不重跑任何毫米波数据、不重算 ECG/RSP、不搜索阈值。复用 low-bias mechanism audit v1 的机制结论、`ecg_rsp_goldclean_reaudit_v1` 与 `physiology_reference_v1` 的既有 cohort 事实、以及 canonical producer 既有常量；没有新算法、没有新 gating rule、没有新 threshold。`REUSE_REJECTION_REASON`：既有 estimator improvement v1 只回答了"哪条规则能过门"（`NO_STABLE_IMPROVEMENT`），没有把机制假设固化成可验证的预注册，也没有建立独立验证集，因此需要一个只写规则与验证合同、不运行的步骤。

**核心内容**：冻结两个候选 —— `C1_SPECTRAL_SCORING_NEUTRALITY`（频域打分中的 `-0.035*|c-time|` 与 `-0.025*|c-previous|` 邻近惩罚把谱峰拉向已经偏低的吸引子；依据是 `CONTROL_SPECTRAL` 的 bias 为三路最负 `-13.351010`）与 `C2_ANCHOR_PERSISTENCE`（anchor 以 `0.8*previous+0.2*fused` 且仅在 `confidence>=0.12` 时更新，`_smooth_track` 用 `alpha=0.20+0.30*confidence` 与 `±7.0 bpm` 限速，且 anchor 是 `gap>10 bpm` 时二选一的判据，本数据 31/100 个 probe 走该分支）。两者都只允许改"如何选择/如何记住心率"，共用同一套五条成功判据（MAE 改善 ≥ `1.0 bpm`、paired improve>worsen、单 session 恶化 ≤ `1.0 bpm`、`AE>10` 不增加、0 个 `correct→catastrophic` 转换）与四条失败判据。

**关键调查结果**：当前唯一存在的 gold-clean per-window ECG 参考（`ecg_rsp_goldclean_reaudit_v1`，`sessions=5`、`ecg_usable_windows=100`）**只覆盖已被反复查看的 5 个开发 session**（`9779/97793/97794/97795/97796`），且该 cohort 设计为同一名参与者的重复测量，因此**参与者不重叠的验证集目前在该机器上不存在**。其余本地 ECG 来源（`sub-2_`–`sub-6_`、`sub-7_`、`sub-97792_`）是校准 session 或严重不足，不能直接当验证集。正式 cohort 有 `116 sessions / 61 participant groups / 2320 probes`，与开发集 session 重叠为 `0`，是现实可用的未触碰来源，唯一缺口是需要独立生成 per-window gold-clean ECG 参考。因此推荐 `OPT_A`（正式 cohort），并明确不推荐为了迁就现有数据而改窗口契约的 `OPT_B`。

**决策与边界**：本任务状态为 `FROZEN_PREREGISTRATION / NO_CANDIDATE_IMPLEMENTED / NO_RUN_PERFORMED`；C1/C2 在 `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` 通过 `VS_1`–`VS_10` contract 之前**不得运行**。未修改 producer、snapshot v1、target/window/fusion/harmonic/threshold；未形成 snapshot v2；未训练模型；HRV 仍 `BLOCKED`。毫米波转为不阻塞主分析的受控验证并行线。

**证据**：`docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md`、`docs/canonical/MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`、`docs/canonical/CANDIDATE_SUCCESS_CRITERIA_V1.csv`、`docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_MANIFEST.json`、回归测试 `tests/test_mmwave_hr_candidate_preregistration.py`。

---
"""

STATUS_ENTRY = """## 2026-09-13 mmWave HR candidate preregistration v1 — FROZEN_PREREGISTRATION（未实现、未运行）

- 冻结两个机制来源明确的候选：`C1_SPECTRAL_SCORING_NEUTRALITY`（频域打分的 time/previous 邻近惩罚把谱峰拉向已偏低的吸引子；`CONTROL_SPECTRAL` bias `-13.351010` 为三路最负）与 `C2_ANCHOR_PERSISTENCE`（anchor 以 `0.8*previous+0.2*fused` 且仅在 `confidence>=0.12` 时更新；`_smooth_track` 用 `alpha=0.20+0.30*confidence` 与 `±7.0 bpm` 限速；anchor 又是 `gap>10 bpm` 时二选一的判据，本数据 31/100 probe 走该分支）。两者都只允许改"如何选择/如何记住心率"，共用同一套五条成功判据与四条失败判据。
- 成功判据（两候选共用，实现前冻结）：MAE 相对 control 改善 ≥ `1.0 bpm`；paired improve>worsen；无单 session MAE 恶化 > `1.0 bpm`；`AE>10` 计数不增加；`control AE≤5 → candidate AE>10` 转换为 `0`。
- 关键调查：唯一存在的 gold-clean per-window ECG 参考（`sessions=5`、`ecg_usable_windows=100`）**只覆盖已被反复查看的 5 个开发 session**，且为同一名参与者的重复测量，因此**参与者不重叠的验证集当前不存在**；其余本地 ECG 来源为校准 session 或窗口不足。正式 cohort `116 sessions / 61 participant groups / 2320 probes` 与开发集 session 重叠 `0`，推荐 `OPT_A` 作为未触碰验证来源，唯一缺口是独立生成 per-window gold-clean ECG 参考。
- 硬门槛：C1/C2 在 `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` 通过 `VS_1`–`VS_10` contract 之前不得运行；通过独立验证才可讨论 snapshot v2；失败则保持 snapshot v1。
- 本任务未运行任何数据、未实现任何候选、未改 producer / snapshot v1 / target / window / threshold，未形成 snapshot v2，HRV=`BLOCKED`。毫米波为不阻塞主分析的受控验证并行线。
- 证据：`docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md`、`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`、`CANDIDATE_SUCCESS_CRITERIA_V1.csv`、`MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_MANIFEST.json`；测试 `tests/test_mmwave_hr_candidate_preregistration.py`。

"""

RESULT_INDEX_ROW = (
    "| MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_20260913 | FROZEN_PREREGISTRATION / NO_CANDIDATE_IMPLEMENTED / NO_RUN_PERFORMED | "
    "[preregistration, untouched-validation-set plan and criteria register](MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md) | "
    "docs/canonical/ + `MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_MANIFEST.json` in Git; no local output (no data run performed) | "
    "Freezes C1 spectral-scoring-neutrality and C2 anchor-persistence with one shared five-criterion success rule and four failure conditions; "
    "records that the only gold-clean per-window ECG reference covers just the 5 exposed development sessions, so a participant-disjoint validation "
    "set does not yet exist; recommends the 116-session formal cohort (`OPT_A`) pending an independent per-window gold-clean ECG reference; "
    "no candidate implemented, no run, no producer/snapshot v1 change, no v2, HRV BLOCKED |\n"
)

AI_PROJECT_MARKER = "- mmwave_hr_execution_issue: `https://github.com/greenboo26/focuswave-multimodal-attention-analysis/issues/35`\n"
AI_PROJECT_ADDITION = (
    "- mmwave_current_preregistration: `docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md` "
    "(FROZEN_PREREGISTRATION; C1/C2 not implemented and not run)\n"
    "- mmwave_next_dependency: untouched participant/session-disjoint ECG validation set "
    "(`docs/canonical/MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`, recommended `OPT_A`)\n"
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
    marker = "### 2026-09-13：mmWave 系统性低估机制审计 v1"
    if "MMWAVE HR candidate preregistration v1" in text:
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
    if "MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_20260913" in text:
        print("skip (already present): docs/canonical/RESULT_INDEX_V1.md")
    else:
        anchor = "| MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_20260913 |"
        if text.count(anchor) != 1:
            raise SystemExit("result index anchor not unique")
        line_start = text.index(anchor)
        line_end = text.index("\n", line_start) + 1
        index.write_text(text[:line_end] + RESULT_INDEX_ROW + text[line_end:], encoding="utf-8", newline="\n")
        print("inserted: docs/canonical/RESULT_INDEX_V1.md")

    insert_after_unique(REPO / "AI_PROJECT.md", AI_PROJECT_MARKER, AI_PROJECT_ADDITION, "AI_PROJECT.md")


if __name__ == "__main__":
    main()
