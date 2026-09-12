#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Close the mmWave HR improvement line and correct the OPT_A planning error.

File: apply_mmwave_line_closure_20260913.py
Version: 1.0.0
Purpose:
    按用户裁决收口毫米波改进线：
      - OPT_A 无效（正式 FocusWave cohort 从设计起就没有 ECG）；
      - 不再执行 REM_1，也不再搜索"漏掉的正式 ECG"；
      - 把该错误记录为 corrected planning error，而不是待解的数据位置问题；
      - C1/C2 -> PAUSED_PENDING_NEW_COLLECTION；
      - 保留 snapshot v1、HR/BR HOLD、HRV BLOCKED、不形成 v2；
      - VS_DATASET 仅作 C2 secondary corroboration，AgeBalanced 作为历史 external benchmark；
      - 控制权交回主分析线。

Usage:
    python scripts/maintenance/apply_mmwave_line_closure_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CLOSURE_ID = "MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1"

LEDGER_ENTRY = """### 2026-09-13：mmWave improvement line CLOSURE v1 — OPT_A 无效，C1/C2 PAUSED_PENDING_NEW_COLLECTION

**Reuse Gate**：本任务不跑任何算法、不改任何结果。复用 `MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1` 的前提核查结论与用户裁决；没有新计算。`REUSE_REJECTION_REASON`：`REM_1`（继续搜索"漏掉的正式 ECG"）已被判定为**不需要**，因此不重复该取证劳动。

**用户裁决（本节为权威）**：正式 FocusWave cohort **从实验设计起就没有 ECG**。因此：

- `OPT_A` **无效**（其定义要求为正式 cohort 生成独立 per-window gold-clean ECG 参考，而该输入在设计上不存在）；
- **不再执行 `REM_1`**，也不再搜索所谓"漏掉的正式 ECG"；
- 这是**已更正的规划错误（corrected planning error）**，不是"未解的数据位置问题"；
- `C1_SPECTRAL_SCORING_NEUTRALITY` 与 `C2_ANCHOR_PERSISTENCE` 状态为 **`PAUSED_PENDING_NEW_COLLECTION`**；
- 不再寻找替代验证集；
- 不再形成 snapshot v2。

**保留的毫米波成果（不重跑）**：`MMWAVE_INTEGRATION_SNAPSHOT_V1` 继续作为多模态输入；`MMWAVE_ESTIMATOR_IMPROVEMENT_V1` = `NO_STABLE_IMPROVEMENT`；`MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1` = `MULTIFACTOR_MECHANISM_SUPPORTED`；HR/BR=`HOLD / SUPPORTING_ONLY`；HRV=`BLOCKED`。

**外部资产角色**：`VS_DATASET_healthy_v1` 仅保留 **C2 secondary corroboration**（`SECONDARY_EXTERNAL_CORROBORATION_ONLY`、`UNTOUCHED=FALSE`、`PRIMARY_GATE_ELIGIBLE=FALSE`、`C1_EVIDENCE=NOT_PERMITTED`、`C2_EVIDENCE=PERMITTED_SECONDARY_ONLY`、`CAN_AUTHORIZE_V2=FALSE`）；`AgeBalanced_60GHz` 作为**历史 external benchmark**保留；`mmWave_Heartbeat`（TI gby）`INELIGIBLE`。

**更正记录**：`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1` 与 `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` 曾把 `OPT_A` 描述为"可用、只差一个可工程补齐的 ECG 参考"，并给出"`OPT_A` to be built next"的路由。**该路由已作废**。错误性质是**规划错误**：前序轮次核对了 session 重叠，却从未核对正式 cohort 是否具备 ECG 采集；而正确答案是"设计上就没有"。规划阶段未先把"参考信号是否存在"作为可行性前提，是本次错误的根本原因。

**状态**：`MMWAVE_IMPROVEMENT_LINE = PAUSED`；`MMWAVE_INTEGRATION = READY`；`MAIN_ANALYSIS = PROCEED`。毫米波不再阻塞 Behavior / NIR / RGB 与正式多模态分析。

---
"""

STATUS_ENTRY = """## 2026-09-13 mmWave improvement line CLOSURE v1 — OPT_A 无效，C1/C2 PAUSED_PENDING_NEW_COLLECTION

- **用户裁决为权威**：正式 FocusWave cohort **从实验设计起就没有 ECG**。因此 `OPT_A` **无效**，`REM_1` **不再执行**，也不再搜索"漏掉的正式 ECG"。这是**已更正的规划错误（corrected planning error）**，不是未解的数据位置问题。
- **C1/C2 状态**：`C1_SPECTRAL_SCORING_NEUTRALITY` 与 `C2_ANCHOR_PERSISTENCE` = **`PAUSED_PENDING_NEW_COLLECTION`**；不再寻找替代验证集；不形成 snapshot v2。
- **保留的毫米波成果（不重跑）**：`MMWAVE_INTEGRATION_SNAPSHOT_V1` 继续作为多模态输入；`MMWAVE_ESTIMATOR_IMPROVEMENT_V1` = `NO_STABLE_IMPROVEMENT`；`MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1` = `MULTIFACTOR_MECHANISM_SUPPORTED`。
- **边界**：HR/BR=`HOLD / SUPPORTING_ONLY`；HRV=`BLOCKED`；snapshot v1 未改；producer 未改；`models_trained=false`；未形成 v2。
- **外部资产角色**：`VS_DATASET_healthy_v1` 仅作 **C2 secondary corroboration**（`UNTOUCHED=FALSE`、`PRIMARY_GATE_ELIGIBLE=FALSE`、`C1_EVIDENCE=NOT_PERMITTED`、`CAN_AUTHORIZE_V2=FALSE`）；`AgeBalanced_60GHz` 作为历史 external benchmark；TI gby `INELIGIBLE`。
- **状态收口**：`MMWAVE_IMPROVEMENT_LINE = PAUSED`；`MMWAVE_INTEGRATION = READY`；`MAIN_ANALYSIS = PROCEED`。控制权交回主分析线（Behavior freeze / NIR freeze / RGB freeze → 统一 feature registry → 单模态分析 → 多模态增量分析）。
- 证据：`docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md`。

"""

CLOSURE_DOC = """# mmWave HR improvement line — closure v1

Document ID: `MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1`

Status: `LINE_PAUSED / OPT_A_INVALID / C1_C2_PAUSED_PENDING_NEW_COLLECTION`

Date: 2026-09-13 (Asia/Shanghai)

Base commit: `edb83e8be02dd637b16ea5bd2fb3a54d0e3f4752`

## 1. 裁决（权威）

正式 FocusWave cohort **从实验设计起就没有 ECG**。据此：

| 决定 | 值 |
|---|---|
| `OPT_A` | **无效**（其定义要求为正式 cohort 生成独立 per-window gold-clean ECG 参考，输入在设计上不存在） |
| `REM_1`（搜索"漏掉的正式 ECG"） | **不执行** |
| 错误性质 | **corrected planning error**，不是"未解的数据位置问题" |
| `C1_SPECTRAL_SCORING_NEUTRALITY` | `PAUSED_PENDING_NEW_COLLECTION` |
| `C2_ANCHOR_PERSISTENCE` | `PAUSED_PENDING_NEW_COLLECTION` |
| 替代验证集搜索 | 停止 |
| snapshot v2 | 不形成 |

## 2. 为什么这是规划错误

`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1` 与 `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` 曾把 `OPT_A` 描述为"可用、只差一个可工程补齐的 ECG 参考"，并给出路由"`OPT_A` to be built next / `PROCEED_AS_PRIMARY`"。

**该路由已作废。** 错误链条：

1. 第一轮 preregistration 盘点只看了内部来源，**先把 `OPT_A` 当成可行基线**；
2. 第二轮外部资产审计只问"外部数据能不能替代"，**没有回头质疑 `OPT_A` 自身是否可行**；
3. 第三轮才去核对前提，于是发现"正式 cohort 有没有 ECG"这个**从未被验证的假设**是假的。

根本原因：**规划阶段没有把"参考信号是否存在"列为可行性前提**，而是默认了它存在。正确做法是在写任何验证计划之前先做输入可行性门（是否存在参考采集、是否可对齐、是否有时间基准）；本文件即为该门的补做与结论。

## 3. 保留的成果（不重跑）

| 资产 | 状态 | 角色 |
|---|---|---|
| `MMWAVE_INTEGRATION_SNAPSHOT_V1` | `PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED` | 继续作为多模态毫米波输入 |
| `MMWAVE_ESTIMATOR_IMPROVEMENT_V1` | `NO_STABLE_IMPROVEMENT` | negative development result |
| `MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1` | `MULTIFACTOR_MECHANISM_SUPPORTED` | 机制证据（正确类几乎无偏；低估集中在失败类别） |
| HR/BR | `HOLD / SUPPORTING_ONLY` | 不变 |
| HRV | `BLOCKED` | 不变 |

## 4. 外部资产角色

```
VS_DATASET_healthy_v1      ROLE = SECONDARY_EXTERNAL_CORROBORATION_ONLY
                           UNTOUCHED = FALSE
                           PRIMARY_GATE_ELIGIBLE = FALSE
                           C1_EVIDENCE = NOT_PERMITTED
                           C2_EVIDENCE = PERMITTED_SECONDARY_ONLY
                           CAN_AUTHORIZE_V2 = FALSE
AgeBalanced_60GHz          ROLE = HISTORICAL_EXTERNAL_BENCHMARK
mmWave_Heartbeat (TI gby)  ROLE = INELIGIBLE
```

## 5. 重新激活条件

C1/C2 仅在以下条件同时成立时可解除 `PAUSED`：

1. 存在**新采集**的数据集：participant/session 与现有开发集不重叠；
2. 该数据集**同时**具备同步 mmWave 与 ECG；
3. 可满足冻结窗口契约 `[window_effective_start, probe_onset)` nominal 30 s、block-truncated、无 cross-block、DLL 时间源；
4. 通过 `VS_1`–`VS_10` 全部 contract 检查；
5. 预注册的成功/失败判据保持不变。

在这些条件满足之前，不做任何 C1/C2 实现或运行。

## 6. 控制权交接

```
MMWAVE_IMPROVEMENT_LINE = PAUSED
MMWAVE_INTEGRATION      = READY
MAIN_ANALYSIS           = PROCEED
```

毫米波不再是主分析的阻塞项。主分析线顺序：Behavior feature freeze → NIR freeze → RGB freeze → 统一 feature registry → 单模态正式分析 → 多模态增量分析。

## 7. 证据

- 本文件：`docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md`
- 前提核查：`docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/`
- 机制证据：`docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`
- 预注册：`docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md`
- Issue: #35
"""

PLAN_ANCHOR = "**Routing update (after the external audit): `OPT_A` is confirmed as the primary untouched validation source, to be built next.**"
PLAN_VOID = """**ROUTING VOID (2026-09-13, `MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1`): the `OPT_A` routing below is VOID. `OPT_A` is invalid.**

The formal FocusWave cohort **never collected ECG by design**, so `OPT_A` cannot be built; `REM_1` will not be executed and no "missing formal ECG" search will be performed. This is recorded as a **corrected planning error**, not an unresolved data-location question. `C1_SPECTRAL_SCORING_NEUTRALITY` and `C2_ANCHOR_PERSISTENCE` are `PAUSED_PENDING_NEW_COLLECTION`, and no snapshot v2 will be formed. See `docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md`. The paragraphs below are retained only as provenance of the error.

"""

REC_ANCHOR = "**Recommendation: `OPT_A`.**"
REC_VOID = """**RETRACTED RECOMMENDATION (see routing void above).** `OPT_A` is invalid, and the claim that its blocker was "a data-engineering task, not a science decision" was wrong: the input does not exist by design. The original text is retained below only as provenance.

"""

EXTERNAL_ROUTING_OLD = "**Routing update (after the external audit): `OPT_A` is confirmed as the primary untouched validation source, to be built next.**"
EXTERNAL_PLAN_NOTE = """**Routing void (2026-09-13): the `OPT_A`/`PROCEED_AS_PRIMARY` routing written here is VOID** — the formal cohort never collected ECG by design, so `OPT_A` is invalid and `REM_1` will not run. This is a corrected planning error. `C1/C2 = PAUSED_PENDING_NEW_COLLECTION`; snapshot v1 unchanged; no v2. See `docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md`.

"""

AI_PROJECT_MARKER = "- mmwave_untouched_validation_blocker: `docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/` (BLOCKED: no ECG source exists for the formal cohort, so no untouched validation set can be formed)\n"
AI_PROJECT_ADDITION = (
    "- mmwave_line_closure: `docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md` "
    "(OPT_A invalid by design; C1/C2 = PAUSED_PENDING_NEW_COLLECTION; improvement line PAUSED, integration READY)\n"
)


def insert_after_unique(path: Path, anchor: str, payload: str, label: str) -> None:
    """Insert payload after the single occurrence of anchor."""
    text = path.read_text(encoding="utf-8")
    if payload.strip()[:60] in text:
        print(f"skip (already present): {label}")
        return
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"anchor count {count} for {label}")
    path.write_text(text.replace(anchor, anchor + payload, 1), encoding="utf-8", newline="\n")
    print(f"inserted: {label}")


def main() -> None:
    """Apply the closure and all corrections."""
    closure = REPO / "docs" / "canonical" / "MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md"
    if not closure.exists():
        closure.write_text(CLOSURE_DOC, encoding="utf-8", newline="\n")
        print("created: docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md")

    ledger = REPO / "ANALYSIS_HISTORY_LEDGER.md"
    text = ledger.read_text(encoding="utf-8")
    marker = "### 2026-09-13：mmWave untouched ECG validation set v1"
    if "mmWave improvement line CLOSURE v1" in text:
        print("skip (already present): ANALYSIS_HISTORY_LEDGER.md")
    else:
        if text.count(marker) != 1:
            raise SystemExit("ledger anchor not unique")
        ledger.write_text(text.replace(marker, LEDGER_ENTRY + "\n" + marker, 1), encoding="utf-8", newline="\n")
        print("inserted: ANALYSIS_HISTORY_LEDGER.md")

    insert_after_unique(REPO / "PROJECT_STATUS.md",
                        "# FocusWave Multimodal Attention Analysis 状态\n\n",
                        STATUS_ENTRY, "PROJECT_STATUS.md")
    insert_after_unique(REPO / "AI_PROJECT.md", AI_PROJECT_MARKER, AI_PROJECT_ADDITION, "AI_PROJECT.md")

    plan = REPO / "docs" / "canonical" / "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md"
    text = plan.read_text(encoding="utf-8")
    if "ROUTING VOID" in text:
        print("skip (already voided): MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md")
    else:
        for anchor, replacement, label in (
            (PLAN_ANCHOR, PLAN_VOID + PLAN_ANCHOR, "plan routing"),
            (REC_ANCHOR, REC_VOID + REC_ANCHOR, "plan recommendation"),
        ):
            if text.count(anchor) != 1:
                raise SystemExit(f"anchor count {text.count(anchor)} for {label}")
            text = text.replace(anchor, replacement, 1)
        plan.write_text(text, encoding="utf-8", newline="\n")
        print("voided: docs/canonical/MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md")

    ext = REPO / "docs" / "results" / "2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1" / "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_REPORT.md"
    if ext.exists():
        text = ext.read_text(encoding="utf-8")
        anchor = "## 5. 路由决定"
        if "路由作废" not in text:
            if text.count(anchor) != 1:
                raise SystemExit("external report anchor not unique")
            note = ("## 5. 路由决定\n\n**路由作废（2026-09-13）**：本节原写 `OPT_A_BUILD = PROCEED_AS_PRIMARY`，"
                    "该路由已作废 —— 正式 cohort 从设计起就没有 ECG，`OPT_A` 无效，`REM_1` 不再执行。"
                    "这是已更正的规划错误。`C1/C2 = PAUSED_PENDING_NEW_COLLECTION`；snapshot v1 不变；不形成 v2。"
                    "见 `docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md`。以下原文仅作 provenance 保留。\n\n")
            ext.write_text(text.replace(anchor, note, 1), encoding="utf-8", newline="\n")
            print("voided: external asset audit report")


if __name__ == "__main__":
    main()