#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apply the mechanism-audit governance sync to canonical current-state files.

File: apply_governance_sync_20260913.py
Version: 1.0.0
Purpose:
    把 mmWave low-bias mechanism audit v1 的结果写入 canonical 状态文件，并修正
    已知 stale pointer（#36 已 CLOSED / COMPLETED；snapshot v1 无合格 movement
    feature、motion proxy 仅 diagnostic）。只新增本次状态，不重写历史结果。

Usage:
    python scripts/maintenance/apply_governance_sync_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

STATUS_LEDGER_ENTRY = """### 2026-09-13：mmWave 系统性低估机制审计 v1 — MULTIFACTOR_MECHANISM_SUPPORTED

**Reuse Gate**：完全复用 estimator improvement v1 冻结的同一批输入（5 sessions / 100 probes / ECG_VALID 100/100 / DLL host receive/enqueue 时间源 / `[window_effective_start, probe_onset)` nominal 30 s），三份输入 CSV 的 SHA-256 全部 exact match；没有新算法、没有新 threshold、没有新 gating rule。`REUSE_REJECTION_REASON`：既有 estimator improvement v1 只回答了"哪条 gating rule 能过门"（结论 NO_STABLE_IMPROVEMENT），没有回答"低估来自哪里"，因此需要一次只读的机制分解。

**复现**：`CONTROL_REPRODUCTION=PASS`。fused MAE=`10.457079173`、bias=`-9.033105842`、p90 AE=`24.054346218`；time MAE=`8.996965770`、bias=`-6.737621327`；spectral MAE=`15.123834193`、bias=`-13.351010046`。100/100 keys exact。

**核心机制发现**：`CORRECT_OR_NEAR_CORRECT` 的 fused bias 仅 `+0.215472 bpm`（MAE `1.538915`），也就是说链路判断正确时估计器几乎无偏；总体 −9 bpm 全部由三个失败类别承担，按加性归因分别为 wrong peak 贡献 `-3.297976`（36.510%）、harmonic 贡献 `-3.486216`（38.594%）、target miss 贡献 `-2.332948`（25.827%）。频域路是三者中偏得最重的 arm（`-13.351010`），融合在 57/100 个 probe 上把结果拉到 time 以下、worsen/improve=`47/31`、净叠加 `1.460113 bpm`，并制造 4 个"time AE≤5 → fused AE>10"的可接受到灾难转换；但 fused 从不比 time 与 spectral 两路都差，因此融合不是主要低估来源。

**次级机制与未解问题**：距离只有弱关联且被 session/类别混淆（连续 distance vs signed error 的 Spearman ρ=`0.020855`，DESCRIPTIVE_ONLY / CLUSTERED_NONINDEPENDENT；within-session far−near 在 4/5 个含远距离 probe 的 session 中为负但 97794 反号，GT1.5M 内 50% 为 wrong peak）；ECG 心率带无清晰特异性（75_TO_90 与 GT90 的 fused bias 接近）；既有 QC 字段无 session 一致关系（`hr_usable_ratio` 在 100 probes 中恒为 1.0、无方差，phase_stability 与 motion_proxy 的 pooled ρ 仅 0.32/0.27 且 97793 反号，`hr_confidence` 与 selection margin 为 NOT_AVAILABLE）。各 arm 相对 ECG 的比值没有落在 ≈0.5 或 ≈2.0 的谐波锁定位，但非谐波残留仍为 `-6.764500 bpm`，说明 −9 bpm 不是少数谐波灾难拉出来的。未解决的问题是"为什么失败模式一律偏向低端而不是对称错"。

**决策与边界**：`MULTIFACTOR_MECHANISM_SUPPORTED`。只读审计，未改正式 producer、未改 snapshot v1、未发布 snapshot v2、未训练模型、未解锁 HRV。`NEXT_HYPOTHESIS`（不得本轮实现，且必须先进入 untouched validation）：频域打分中 `-0.035*|c-time|` 与 `-0.025*|c-previous|` 两项是否把谱峰系统性拉向低端；anchor 更新规则是否让历史低估长期驻留。

**证据**：`docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`（report、manifest、`FUSION_PATH_AUDIT.md`、fusion/distance/failure-class/ECG-band/QC 分解表、机制证据矩阵、error log、handoff）；逐 probe 机制表 `PROBE_LEVEL_MECHANISM_100_PROBES.csv` 为 local-only，路径与 SHA-256 在 manifest。HR/BR=`HOLD / SUPPORTING_ONLY`，HRV=`BLOCKED`，`models_trained=false`。

---
"""

PROJECT_STATUS_ENTRY = """## 2026-09-13 mmWave 系统性低估机制审计 v1 — MULTIFACTOR_MECHANISM_SUPPORTED

- 完全复用 estimator improvement v1 的冻结 denominator（5 sessions / 100 probes / ECG_VALID 100/100 / DLL-time 30 s），三份输入 SHA-256 exact match；`CONTROL_REPRODUCTION=PASS`（fused MAE `10.457079173` / bias `-9.033105842` / p90 AE `24.054346218`；time `8.996965770` / `-6.737621327`；spectral `15.123834193` / `-13.351010046`）。
- 关键发现：`CORRECT_OR_NEAR_CORRECT` 的 fused bias 仅 `+0.215472 bpm`（MAE `1.538915`），即链路判断正确时估计器几乎无偏；总体 −9 bpm 全部由三个失败类别承担（wrong peak 贡献 `-3.297976`、harmonic `-3.486216`、target miss `-2.332948`）。
- 频域路偏低最重（`-13.351010`），融合在 57/100 个 probe 上把结果拉低于 time、worsen/improve=`47/31`、净叠加 `1.460113 bpm`，并产生 4 个"time AE≤5 → fused AE>10"转换；但 fused 从不比 time 与 spectral 都差，故融合不是主要来源。
- 距离为弱且被 session/类别混淆的关联（ρ=`0.020855`，DESCRIPTIVE_ONLY / CLUSTERED_NONINDEPENDENT；within-session far−near 在 4/5 个可评估 session 中为负、97794 反号）；ECG 心率带无清晰特异性；既有 QC 字段无 session 一致关系（`hr_usable_ratio` 恒为 1.0 无方差；phase_stability/motion_proxy 的 ρ 仅 0.32/0.27 且 97793 反号；`hr_confidence` 与 selection margin 为 NOT_AVAILABLE）；无 ≈0.5/≈2.0 谐波锁定，但非谐波残留仍为 `-6.764500 bpm`。
- 只读审计：未改正式 producer、未改 integration snapshot v1、未形成 snapshot v2、未训练模型、HRV=`BLOCKED`。`NEXT_HYPOTHESIS`（不在本轮实现，须先进入 untouched validation）：频域打分的 time/previous 邻近项是否把谱峰系统性拉低；anchor 更新规则是否让历史低估驻留。
- 证据：`docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`（report、manifest、`FUSION_PATH_AUDIT.md`、各分解表、机制证据矩阵、error log、handoff）；逐 probe 表 local-only，路径与 SHA-256 已登记。Issue #35 保持 OPEN 作为 improvement 主线；Issue #36 已 CLOSED / COMPLETED；Issue #41 保持 integration snapshot v1 身份。

"""

RESULT_INDEX_ROW = (
    "| MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_20260913 | MULTIFACTOR_MECHANISM_SUPPORTED | "
    "[mechanism report, fusion path audit, decompositions and evidence matrix]"
    "(../results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/) | "
    "`D:\\Project\\厚粲杯\\11_数据\\derived\\mmwave_low_bias_mechanism_audit_v1_20260913` — "
    "`VERIFIED_ON_EXECUTING_MACHINE`; probe-level mechanism table local-only with SHA-256 in manifest | "
    "Read-only mechanism audit on the frozen 5-session/100-probe development set: control reproduced exactly; "
    "CORRECT_OR_NEAR_CORRECT nearly unbiased (+0.215 bpm) so the pooled -9 bpm is carried by the three failure "
    "classes; spectral arm most low-biased and fusion adds ~1.46 bpm penalty; distance weak/confounded, "
    "ECG band non-specific, existing QC fields not session-consistent; no candidate, no producer or snapshot v1 "
    "change, no v2, HRV BLOCKED |\n"
)

SCRIPT_INVENTORY_ADDENDUM = """## 2026-09-13 active addendum

- `maintenance/run_mmwave_low_bias_mechanism_audit_20260913.py`：只读机制审计，复用 estimator improvement v1 的冻结 5-session/100-probe denominator，分解 −9 bpm 低估来源（fusion / distance / failure class / ECG band / QC / harmonic）；不建 gating rule、不改 producer 或 snapshot v1。deterministic，支持 `--verify-only`。
- `maintenance/render_mmwave_mechanism_audit_docs_20260913.py`：从 manifest 与同目录 CSV 渲染审计报告、fusion code-path audit、error log 与 handoff，避免手抄数字。

"""

CANONICAL_STATE_NOTE = """## Mechanism-audit pointer — 2026-09-13

The low-bias mechanism audit v1 (`MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1`) is a read-only diagnostic on the frozen 5-session / 100-probe development set. Its conclusion is `MULTIFACTOR_MECHANISM_SUPPORTED`: on probes whose failure class is `CORRECT_OR_NEAR_CORRECT` the fused estimator is nearly unbiased (`+0.215 bpm`), so the pooled `-9 bpm` is carried by the `SELECTED_TARGET_WRONG_PEAK`, `HARMONIC_OR_HALF_DOUBLE_LOCK` and `TARGET_BIN_CHANNEL_MISS` classes; the spectral arm is the most low-biased arm and the fusion step adds a further `~1.46 bpm` penalty without ever being worse than both arms. Distance is only a weak, session-confounded association, the ECG HR bands show no clean specificity, and the available QC fields are not session-consistent.

This does not change the integration snapshot, the formal producer, the feature registry, or any HR/BR/HRV boundary. HR/BR remain `HOLD / SUPPORTING_ONLY`, HRV remains `BLOCKED`, and no candidate or snapshot v2 exists. The mechanism-derived ideas are recorded only as `NEXT_HYPOTHESIS` and must pass an untouched participant/session-disjoint validation before implementation.

Evidence: `docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`.

"""


def insert_after(path: Path, anchor: str, payload: str, label: str) -> None:
    """Insert payload immediately after the first occurrence of anchor."""
    text = path.read_text(encoding="utf-8")
    if payload[:60] in text:
        print(f"skip (already present): {label}")
        return
    if text.count(anchor) != 1:
        raise SystemExit(f"anchor not unique for {label}: {anchor!r}")
    path.write_text(text.replace(anchor, anchor + payload, 1), encoding="utf-8", newline="\n")
    print(f"inserted: {label}")


def main() -> None:
    """Apply all governance sync edits."""
    ledger = REPO / "ANALYSIS_HISTORY_LEDGER.md"
    text = ledger.read_text(encoding="utf-8")
    anchor = "---\n\n### 2026-09-12：mmWave estimator improvement v1 — NO_STABLE_IMPROVEMENT"
    if "### 2026-09-13：mmWave 系统性低估机制审计 v1" not in text:
        if text.count(anchor) != 1:
            raise SystemExit("ledger anchor not unique")
        ledger.write_text(text.replace(anchor, "---\n\n" + STATUS_LEDGER_ENTRY + "\n### 2026-09-12：mmWave estimator improvement v1 — NO_STABLE_IMPROVEMENT", 1),
                          encoding="utf-8", newline="\n")
        print("inserted: ANALYSIS_HISTORY_LEDGER.md")
    else:
        print("skip (already present): ANALYSIS_HISTORY_LEDGER.md")

    insert_after(
        REPO / "PROJECT_STATUS.md",
        "# FocusWave Multimodal Attention Analysis 状态\n\n",
        PROJECT_STATUS_ENTRY,
        "PROJECT_STATUS.md",
    )

    insert_after(
        REPO / "docs" / "canonical" / "RESULT_INDEX_V1.md",
        "|---|---|---|---|---|\n",
        RESULT_INDEX_ROW,
        "docs/canonical/RESULT_INDEX_V1.md",
    )

    inv = REPO / "docs" / "00_治理" / "当前脚本清单_2026-08-29.md"
    insert_after(
        inv,
        "# 当前脚本清单（2026-08-29 受控清理后；2026-08-30 增补 Issue #26/#28 audit）\n\n",
        SCRIPT_INVENTORY_ADDENDUM,
        "docs/00_治理/当前脚本清单_2026-08-29.md",
    )

    canon = REPO / "docs" / "canonical" / "MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md"
    insert_after(
        canon,
        "## Current implementation pointer — 2026-09-12\n",
        "\n" + CANONICAL_STATE_NOTE + "## Current implementation pointer — 2026-09-12\n",
        "docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md",
    )


if __name__ == "__main__":
    main()
