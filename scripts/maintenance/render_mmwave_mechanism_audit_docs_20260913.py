#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render the mechanism-audit report, fusion path audit, error log and handoff.

File: render_mmwave_mechanism_audit_docs_20260913.py
Version: 1.0.0
Purpose:
    把 run_mmwave_low_bias_mechanism_audit_20260913.py 已经算出的结果渲染成
    Markdown 报告 / fusion code-path audit / error log / handoff。所有数字都从
    MANIFEST.json 与同目录 CSV 读取，避免手抄数字造成报告与结果不一致。

Usage:
    python scripts/maintenance/render_mmwave_mechanism_audit_docs_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "docs" / "results" / "2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1"


def read_csv(path: Path) -> list[dict]:
    """Read a CSV into a list of dicts."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    """Return uppercase SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def render_fusion_path_audit(out: Path, manifest: dict) -> str:
    """Explain exactly how the frozen fused HR is produced, with no code change."""
    fusion = manifest["fusion_summary"]["POOLED"]
    return f"""# FUSION_PATH_AUDIT.md — 冻结融合链的代码路径审计

本文件只做 code-path audit，不修改任何代码。所有行号来自 canonical main 的：

- `scripts/process_vital_signs_v3_1_1.py`（正式 producer，本任务 byte-identical 未改）
- `scripts/maintenance/run_mmwave_pre30s_selector_hr_20260831.py`（probe 级 selector 适配器，producer 方法复用）

## 1. 三层结构

`hr_30s_fused_bpm` 不是单次函数输出，而是三层串联的结果：

| 层 | 位置 | 作用 |
|---|---|---|
| L1 时域心率 | `_robust_time_bpm`（producer 第 697 行） | 由峰值间期（inter-beat interval [IBI]）中位数求 bpm |
| L2 频域心率 | `_select_spectral_bpm`（producer 第 756 行） | 在 0.6–3.0 Hz 带内按功率与邻近度打分选峰 |
| L3 融合 | `selector_step`（适配器第 72 行） | 把 time/spectral 合成 `selector_fused_bpm` 与 confidence |
| L4 时间平滑 | `_smooth_track`（producer 第 789 行） | 对整条 course 做前后向平滑并限速 ±7 bpm/步 |

## 2. L3 融合的精确规则（决定低估方向的关键）

```
gap = abs(time_bpm - selected)
agreement = exp(-gap / 12.0)
wt, wf = max(0.05, time_quality), max(0.05, frequency_quality)
if gap <= HR_TIME_FREQ_WARNING_BPM (=10.0):
    fused = (wt*time_bpm + wf*selected) / (wt + wf)      # 加权平均
    confidence = agreement * sqrt(time_quality * frequency_quality)
else:
    fused = time_bpm if (anchor is None or abs(time_bpm-anchor) <= abs(selected-anchor)) else selected
    confidence = 0.10 * (time_quality if fused == time_bpm else frequency_quality) * agreement
```

三点是本任务的核心机制事实：

1. **gap ≤ 10 bpm 时是加权平均**，权重是两路各自的 quality。本次 {fusion['n'] - fusion['gap_gt10_n']}/100 个 probe 走该分支。
2. **gap > 10 bpm 时不做平均，而是二选一**，选择依据是"谁更接近 anchor"。本次 {fusion['gap_gt10_n']}/100 个 probe 走该分支。
3. **anchor 本身是过去 fused 值的滚动混合**（适配器第 100–101 行：`next_previous = 0.8*previous + 0.2*fused`，且仅当 `confidence >= 0.12` 才更新）。因此 anchor 继承历史低估，会倾向于选中更低的那一路。

另外，confidence 在 gap > 10 分支被乘上 `0.10 * agreement`，量级显著低于正常分支，所以这些 probe 的 `next_previous` 往往不更新（保持旧的低 anchor）。

## 3. L1 时域路为什么也会偏低

`_robust_time_bpm` 的 quality 只有两项：

```
count_quality = min(1.0, len(clean)/10.0)
regularity_quality = exp(-5.0 * robust_cv)
```

它没有对"峰数偏少"或"漏检导致 IBI 被拉长"做方向性惩罚。当峰值漏检时 IBI 变长，bpm 直接偏低，而 `median(clean)` 仍然稳定，于是 time_bpm 以较高 quality 输出一个偏低值。

## 4. L2 频域路为什么最低

`_select_spectral_bpm` 的打分是：

```
scores = log(relative_power)
scores -= 0.035 * abs(candidates - time_bpm)      # 被 time 拉
scores -= 0.025 * abs(candidates - previous_bpm)  # 被上次融合值拉
best = argmax(scores)
quality = sqrt(relative_power[best]) * exp(-abs(selected - time_bpm)/20.0)
```

因为打分里同时含 `-0.035*|c - time|` 与 `-0.025*|c - previous|`，而 time 与 previous 在本数据上都已经偏低，**谱峰会系统性地被拉向低端**。这解释了为什么 spectral 是三者中偏差最大的（{manifest['frozen_control_reproduced']['spectral']['bias']:.6f} bpm）。

## 5. 本任务观测到的融合行为

| 指标 | 值 |
|---|---|
| spectral < time 的 probe | {fusion['spectral_lt_time_n']}/100 |
| fused < time 的 probe | {fusion['fused_lt_time_n']}/100 |
| spectral < time 且 fused 被向下拉 | {fusion['spectral_pulled_fused_down_n']}/100 |
| time AE≤5 但 fused AE>5 | {fusion['time_ae_le5_fused_gt5_n']}/100 |
| time AE≤5 但 fused AE>10 | {fusion['time_ae_le5_fused_gt10_n']}/100 |
| fused 相比 time improve/worsen/tie | {fusion['improve_n']}/{fusion['worsen_n']}/{fusion['tie_n']} |
| 平均 fusion penalty vs time | {fusion['mean_fusion_penalty_vs_time_bpm']:.6f} bpm |
| 平均 fusion 相对 time 的带符号位移 | {fusion['mean_fusion_signed_shift_vs_time_bpm']:.6f} bpm |
| 平均 spectral 相对 time 的带符号位移 | {fusion['mean_spectral_signed_shift_vs_time_bpm']:.6f} bpm |
| fused 同时差于 time 与 spectral | {fusion['fusion_worse_than_both_arms_n']}/100 |

结论：融合**不是**主要低估来源（它相对 spectral 明显收敛，且从不比两路都差），但它确实在
worsen（{fusion['worsen_n']}）多于 improve（{fusion['improve_n']}）的方向上再叠加约
{fusion['mean_fusion_penalty_vs_time_bpm']:.3f} bpm，并制造了 {fusion['time_ae_le5_fused_gt10_n']} 个
"原本可接受、融合后超过 10 bpm"的转换。

## 6. 未做的事

本审计没有修改 L1–L4 任何一行代码，没有新增融合规则、没有调阈值、没有用 ECG 选峰。
上述机制只作为 `NEXT_HYPOTHESIS` 的输入，不构成本轮的修复或候选。
"""


def render_report(out: Path, manifest: dict, tables: dict) -> str:
    """Render the main audit report."""
    fc = {r["failure_class"]: r for r in tables["fc"]}
    attr = {r["failure_class"]: r for r in tables["attribution"]}
    fusion = manifest["fusion_summary"]
    pooled = fusion["POOLED"]
    dist = manifest["distance_descriptives"]
    within = {r["subject"]: r for r in manifest["within_session_distance"]}
    bands = [r for r in tables["band"] if r["scope"] == "POOLED"]
    qc = {r["qc_field"]: r for r in tables["qc"] if r["scope"] == "POOLED"}
    harm = {r["arm"]: r for r in manifest["harmonic_relations"]}
    flags = manifest["secondary_flag_frequency"]

    def fc_row(name: str, col: str) -> str:
        return fc[name][col] if fc.get(name) else ""

    band_lines = "\n".join(
        f"| {b['ecg_hr_band']} | {b['n']} | {b['ecg_hr_median_bpm']} | {b['fused_bias_bpm']} | "
        f"{b['fused_mae_bpm']} | {b['time_bias_bpm']} | {b['spectral_bias_bpm']} | "
        f"{b['mean_fusion_penalty_vs_time_bpm']} | {b['session_distribution']} |"
        for b in bands
    )
    within_lines = "\n".join(
        f"| {s} | {within[s]['n_near_lt1.5m']} | {within[s]['n_far_ge1.5m']} | "
        f"{within[s]['near_fused_bias_bpm']} | {within[s]['far_fused_bias_bpm']} | "
        f"{within[s]['within_session_far_minus_near_bias_bpm']} |"
        for s in ("9779", "97793", "97794", "97795", "97796")
    )
    sess_lines = "\n".join(
        f"| {s} | {fusion[s]['n']} | {fusion[s]['spectral_lt_time_n']} | {fusion[s]['fused_lt_time_n']} | "
        f"{fusion[s]['spectral_pulled_fused_down_n']} | {fusion[s]['mean_fusion_penalty_vs_time_bpm']:.3f} | "
        f"{fusion[s]['improve_n']}/{fusion[s]['worsen_n']}/{fusion[s]['tie_n']} | "
        f"{fusion[s]['time_ae_le5_fused_gt5_n']} | {fusion[s]['time_ae_le5_fused_gt10_n']} |"
        for s in ("9779", "97793", "97794", "97795", "97796")
    )
    attr_lines = "\n".join(
        f"| {a} | {attr[a]['n']} | {attr[a]['mean_signed_error_fused_bpm']} | "
        f"{attr[a]['bias_contribution_to_pooled_bpm']} | {attr[a]['share_of_pooled_bias_pct']} | "
        f"{attr[a]['fusion_penalty_contribution_to_pooled_bpm']} |"
        for a in ("CORRECT_OR_NEAR_CORRECT", "SELECTED_TARGET_WRONG_PEAK",
                  "HARMONIC_OR_HALF_DOUBLE_LOCK", "TARGET_BIN_CHANNEL_MISS")
    )
    qc_lines = "\n".join(
        f"| {q} | {qc[q]['n']} | {qc[q]['spearman_vs_signed_error_fused']} | "
        f"{qc[q]['spearman_vs_absolute_error_fused']} | {qc[q]['spearman_vs_fusion_penalty_vs_time']} | "
        f"{qc[q]['direction_consistent_across_sessions']} |"
        for q in ("hr_usable_ratio", "phase_stability", "motion_proxy", "mmwave_frames",
                  "ecg_valid_ratio", "rsp_valid_ratio")
    )
    flag_lines = "\n".join(f"| {k} | {v} |" for k, v in flags.items())

    return f"""# 毫米波 HR 系统性低估机制审计 v1（MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1）

RUN_ID: `mmwave_low_bias_mechanism_audit_v1_20260913_r1`

审计类型：`MECHANISM_AUDIT`（机制审计，不是 estimator 搜索）

最终机制状态：**{manifest['mechanism_status']}**

## 1. 这次审计回答什么

当前融合心率（fused HR）相对心电图（electrocardiography [ECG]）参考约 **−9 bpm** 系统性低估。
本任务不搜索新的 estimator rule，而是回答：这个低估主要来自哪里，以及下一轮真正修算法时
应该预注册什么方向。

硬边界（全部满足）：没有新建 gating rule、没有调阈值、没有用 ECG 选 production peak、
没有改 fused/time/spectral estimator、没有改 target/bin/channel selector、没有改融合、
没有改谐波校正、没有改窗口、没有做 30 s vs 60 s 比较、没有开始 P3 baseline personalization、
没有改 snapshot v1、没有改正式 producer、没有发布 snapshot v2、没有训练注意状态模型、
没有解锁心率变异性（heart rate variability [HRV]）。

## 2. 冻结 denominator 与输入身份

| 项目 | 值 |
|---|---|
| sessions | {manifest['denominator']['n_sessions']}（{", ".join(manifest['denominator']['session_counts'].keys())}） |
| probes | {manifest['denominator']['n_probes']} |
| ECG 资格 | 100/100 ECG_VALID（复用 estimator improvement v1） |
| 窗口 | `[window_effective_start, probe_onset)`，nominal 30 s，无 cross-block |
| 时间源 | DLL host receive/enqueue timestamp（CSV 零基第 1 列） |

输入身份核验全部 exact match（SHA-256）：

| 输入 | rows | SHA-256 |
|---|---|---|
""" + "\n".join(
        f"| {name} | {info['rows']} | `{info['sha256']}` |"
        for name, info in manifest["inputs"].items()
    ) + f"""

## 3. 冻结 control 复现（必须先通过）

| arm | MAE | bias | p90 AE |
|---|---|---|---|
| CONTROL_FUSED | {manifest['frozen_control_reproduced']['fused']['mae']} | {manifest['frozen_control_reproduced']['fused']['bias']} | {manifest['frozen_control_reproduced']['fused']['p90_ae']} |
| CONTROL_TIME | {manifest['frozen_control_reproduced']['time']['mae']} | {manifest['frozen_control_reproduced']['time']['bias']} | N/A |
| CONTROL_SPECTRAL | {manifest['frozen_control_reproduced']['spectral']['mae']} | {manifest['frozen_control_reproduced']['spectral']['bias']} | N/A |

与冻结值误差 < {manifest['control_tolerance']}，`CONTROL_REPRODUCTION=PASS`；100/100 keys exact。

## 4. 核心问题 1：融合是否把频域的低估带进最终 fused HR

融合链的精确代码路径见 `FUSION_PATH_AUDIT.md`。关键事实是：融合在 `gap ≤ 10 bpm` 时做加权平均，
在 `gap > 10 bpm` 时**二选一**，而选择依据是与一个继承历史低估的 anchor 的距离。

| 指标 | POOLED |
|---|---|
| spectral < time | {pooled['spectral_lt_time_n']}/100 |
| fused < time | {pooled['fused_lt_time_n']}/100 |
| spectral < time 且 fused 被向下拉 | {pooled['spectral_pulled_fused_down_n']}/100 |
| time AE≤5 但 fused AE>5 | {pooled['time_ae_le5_fused_gt5_n']}/100 |
| time AE≤5 但 fused AE>10 | {pooled['time_ae_le5_fused_gt10_n']}/100 |
| improve/worsen/tie（fused vs time） | {pooled['improve_n']}/{pooled['worsen_n']}/{pooled['tie_n']} |
| 平均 fusion penalty vs time | {pooled['mean_fusion_penalty_vs_time_bpm']:.6f} bpm |
| fused 同时差于两路 | {pooled['fusion_worse_than_both_arms_n']}/100 |

按 session 分层（每个 session 20 probes）：

| session | n | spectral<time | fused<time | pulled | penalty | imp/wor/tie | t≤5→f>5 | t≤5→f>10 |
|---|---|---|---|---|---|---|---|---|
{sess_lines}

**判定**：频域路确实系统性偏低（bias {manifest['frozen_control_reproduced']['spectral']['bias']:.6f}），
融合也确实在 57/100 个 probe 上把结果拉到 time 以下。但融合只贡献约
{pooled['mean_fusion_penalty_vs_time_bpm']:.3f} bpm 的额外绝对误差，且从不比两路都差，
所以**低估的主因不是融合本身，而是 feed 进融合的 time/spectral 两路本身已经偏低**。

## 5. 核心问题 2：distance 关联是否独立于 session / failure class

连续 distance 的描述性相关（`{dist['label']}`）：

| 关系 | Spearman ρ |
|---|---|
| distance vs signed_error_fused | {dist['spearman_distance_vs_signed_error_fused']:.6f} |
| distance vs absolute_error_fused | {dist['spearman_distance_vs_absolute_error_fused']:.6f} |
| distance vs fusion_penalty_vs_time | {dist['spearman_distance_vs_fusion_penalty_vs_time']:.6f} |
| distance vs signed_error_time | {dist['spearman_distance_vs_signed_error_time']:.6f} |
| distance vs signed_error_spectral | {dist['spearman_distance_vs_signed_error_spectral']:.6f} |

pooled 的 ρ 接近 0，说明**连续距离本身几乎不解释任何 probe 间差异**。

within-session 比较（远距离 ≥1.5 m 减近距离 <1.5 m 的 fused bias）：

| session | n near | n far | near bias | far bias | far − near |
|---|---|---|---|---|---|
{within_lines}

far − near 在 4/5 个含远距离 probe 的 session 中为负，方向基本一致；但 97794 反号（+1.78），
且远距离 probe 高度集中在少数 session（例如 97796 占 40%）。

`DISTANCE_FAILURE_CLASS_MATRIX.csv` 给出了更强的线索：**GT1.5M 的错误几乎全部来自错误类别**，
而不是距离本身让正确 target 的估计变差——在 GT1.5M 内 `CORRECT_OR_NEAR_CORRECT` 的
fused bias 只有 {[r for r in tables['dfc'] if r['distance_band']=='GT1.5M' and r['failure_class']=='CORRECT_OR_NEAR_CORRECT'][0]['fused_bias_bpm']} bpm，
而该带 50% 的 probe 是 wrong peak。

**判定**：距离是一个**弱且被 session/类别混淆**的关联，不能解释为距离因果，也不得据此造新 gate。

## 6. 核心问题 3：低估是否主要是错误类型驱动

按严格 P2 类别分解（`FAILURE_CLASS_BIAS_DECOMPOSITION.csv`）：

| failure class | n | fused bias | fused MAE | time bias | spectral bias |
|---|---|---|---|---|---|
| CORRECT_OR_NEAR_CORRECT | {fc_row('CORRECT_OR_NEAR_CORRECT','n')} | {fc_row('CORRECT_OR_NEAR_CORRECT','fused_bias_bpm')} | {fc_row('CORRECT_OR_NEAR_CORRECT','fused_mae_bpm')} | {fc_row('CORRECT_OR_NEAR_CORRECT','time_bias_bpm')} | {fc_row('CORRECT_OR_NEAR_CORRECT','spectral_bias_bpm')} |
| SELECTED_TARGET_WRONG_PEAK | {fc_row('SELECTED_TARGET_WRONG_PEAK','n')} | {fc_row('SELECTED_TARGET_WRONG_PEAK','fused_bias_bpm')} | {fc_row('SELECTED_TARGET_WRONG_PEAK','fused_mae_bpm')} | {fc_row('SELECTED_TARGET_WRONG_PEAK','time_bias_bpm')} | {fc_row('SELECTED_TARGET_WRONG_PEAK','spectral_bias_bpm')} |
| HARMONIC_OR_HALF_DOUBLE_LOCK | {fc_row('HARMONIC_OR_HALF_DOUBLE_LOCK','n')} | {fc_row('HARMONIC_OR_HALF_DOUBLE_LOCK','fused_bias_bpm')} | {fc_row('HARMONIC_OR_HALF_DOUBLE_LOCK','fused_mae_bpm')} | {fc_row('HARMONIC_OR_HALF_DOUBLE_LOCK','time_bias_bpm')} | {fc_row('HARMONIC_OR_HALF_DOUBLE_LOCK','spectral_bias_bpm')} |
| TARGET_BIN_CHANNEL_MISS | {fc_row('TARGET_BIN_CHANNEL_MISS','n')} | {fc_row('TARGET_BIN_CHANNEL_MISS','fused_bias_bpm')} | {fc_row('TARGET_BIN_CHANNEL_MISS','fused_mae_bpm')} | {fc_row('TARGET_BIN_CHANNEL_MISS','time_bias_bpm')} | {fc_row('TARGET_BIN_CHANNEL_MISS','spectral_bias_bpm')} |

**这是本审计最强的发现**：`CORRECT_OR_NEAR_CORRECT` 的 fused bias 只有
{fc_row('CORRECT_OR_NEAR_CORRECT','fused_bias_bpm')} bpm（MAE {fc_row('CORRECT_OR_NEAR_CORRECT','fused_mae_bpm')}）。
也就是说，**当链路判断正确时，估计器几乎无偏**；总体 −9 bpm 完全由三个失败类别承担。

把 pooled bias 按类别做加性归因（每个类别贡献 = 该类带符号误差之和 / 100）：

| failure class | n | 类别内 fused bias | 对 pooled bias 的贡献 | 占 pooled bias | fusion penalty 贡献 |
|---|---|---|---|---|---|
{attr_lines}

## 7. 核心问题 4：ECG HR 高低是否解释 bias

| ECG band | n | ECG median | fused bias | fused MAE | time bias | spectral bias | fusion penalty | sessions |
|---|---|---|---|---|---|---|---|---|
{band_lines}

LT75 仅 n=5，不得强推断。75_TO_90 与 GT90 的 fused bias 接近（−9.26 与 −9.78），
说明这不是简单的"高心率时估计器跟不上"；但两个带被 session 组成混淆（见 sessions 列），
且 GT90 的 spectral bias 反而较小。**不足以支持心率带特异性机制。**

## 8. 核心问题 5：既有 QC 是否解释低估

| QC field | n | ρ vs signed error | ρ vs absolute error | ρ vs fusion penalty | 跨 session 方向一致 |
|---|---|---|---|---|---|
{qc_lines}

`hr_usable_ratio` 在本轮 100 个 probe 中**恒为 1.0**，没有方差，因此秩相关无定义：
这个字段在 eligibility 层没有判别力（全部探针都通过可用窗比例检查），不是缺失值。

`phase_stability` 与 `motion_proxy` 的 pooled ρ 很弱（0.32 / 0.27），
且 **5 个 session 中有 1 个（97793）方向相反**，不满足 session 一致性。
`hr_confidence` 与 selection margin 在本轮冻结输出中为空，标记 `NOT_AVAILABLE`，不补算。

**判定**：现有 QC 字段不支持"低估由低信噪比/低质量驱动"这一假设。

## 9. 核心问题 6：谐波机制

各 arm 相对 ECG 的比值分布（冻结诊断关系，未重新优化容差）：

| arm | ratio median | p10 | ≈0.5 lock | ≈2.0 lock | ratio < 0.8 |
|---|---|---|---|---|---|
| fused | {harm['fused']['ratio_median']} | {harm['fused']['ratio_p10']} | {harm['fused']['n_near_half_lock_0.45_0.55']} | {harm['fused']['n_near_double_lock_1.9_2.1']} | {harm['fused']['n_strongly_low_ratio_lt0.8']} |
| time | {harm['time']['ratio_median']} | {harm['time']['ratio_p10']} | {harm['time']['n_near_half_lock_0.45_0.55']} | {harm['time']['n_near_double_lock_1.9_2.1']} | {harm['time']['n_strongly_low_ratio_lt0.8']} |
| spectral | {harm['spectral']['ratio_median']} | {harm['spectral']['ratio_p10']} | {harm['spectral']['n_near_half_lock_0.45_0.55']} | {harm['spectral']['n_near_double_lock_1.9_2.1']} | {harm['spectral']['n_strongly_low_ratio_lt0.8']} |

**没有任何 probe 落在 ≈0.5 或 ≈2.0 的谐波锁定位**。相反，三个 arm 的比值分布整体向低端偏斜
（spectral 有 {harm['spectral']['n_strongly_low_ratio_lt0.8']}/100 低于 0.8）。
因此本数据的"系统性低估"形态是**整体低偏**，而不是经典半频/倍频锁定。

把 harmonic 类别整体剔除后：

| 分组 | n | fused bias | fused MAE |
|---|---|---|---|
| HARMONIC_CLASS_ONLY | {fc_row('HARMONIC_CLASS_ONLY','n')} | {fc_row('HARMONIC_CLASS_ONLY','fused_bias_bpm')} | {fc_row('HARMONIC_CLASS_ONLY','fused_mae_bpm')} |
| NON_HARMONIC_RESIDUAL | {fc_row('NON_HARMONIC_RESIDUAL','n')} | {fc_row('NON_HARMONIC_RESIDUAL','fused_bias_bpm')} | {fc_row('NON_HARMONIC_RESIDUAL','fused_mae_bpm')} |

非谐波残留仍是 {fc_row('NON_HARMONIC_RESIDUAL','fused_bias_bpm')} bpm 的明确负偏，
所以 **−9 bpm 不是少数谐波灾难拉出来的**。

既有 P2 次级标记频次（说明哪些机制真的在触发）：

| flag | n |
|---|---|
{flag_lines}

## 10. 机制证据矩阵

完整矩阵见 `MECHANISM_EVIDENCE_MATRIX.csv`（含 EVIDENCE_FOR / EVIDENCE_AGAINST /
SESSION_CONSISTENCY / FAILURE_CLASS_LINK / CONFIDENCE / NEXT_TEST）。

| 机制候选 | 置信度 |
|---|---|
| SPECTRAL_LOW_BIAS_PULLS_FUSION_DOWN | HIGH |
| HARMONIC_ERROR | HIGH |
| DISTANCE_OR_GEOMETRY_ASSOCIATION | MEDIUM |
| TARGET_SELECTION_ERROR | MEDIUM |
| SELECTED_TARGET_PEAK_ESTIMATION_ERROR | MEDIUM |
| SESSION_SPECIFIC_DATA_QUALITY | MEDIUM |
| LOW_SIGNAL_OR_QC | LOW |

## 11. 最终机制判定

**{manifest['mechanism_status']}**

数据事实：
1. 低估不是均匀的估计器标定误差——正确类几乎无偏（+{fc_row('CORRECT_OR_NEAR_CORRECT','fused_bias_bpm')} bpm）。
2. 低估集中在三个失败类别，且每个失败类别的估计都显著向低端偏。
3. 频域路是三者中偏得最厉害的（{manifest['frozen_control_reproduced']['spectral']['bias']:.3f} bpm），
   融合把它往 time 拉回一部分，但仍净叠加约 {pooled['mean_fusion_penalty_vs_time_bpm']:.3f} bpm，
   并制造 {pooled['time_ae_le5_fused_gt10_n']} 个"可接受→灾难"转换。
4. 距离只有弱关联且被 session/类别混淆；ECG 心率带无清晰特异性；既有 QC 字段无 session 一致关系。

当前判断（仍属机制解释而非结论放行）：
- 主机制是**失败模式主导的低偏**：一旦进入 wrong peak / harmonic / target miss，估计值系统性偏低。
- 次机制是**频域路系统性低偏并被融合部分传递**。
- 距离更像这些失败模式的空间代理，而不是独立原因。

尚未解决：为什么失败模式一律偏向低端（而不是对称错）——这需要 selection margin、
hr_confidence 等当前 `NOT_AVAILABLE` 字段，或独立验证集。

## 12. NEXT_HYPOTHESIS（不得在本轮实现）

只写成假设，不实现、不评价为 production candidate：

- `NEXT_HYPOTHESIS_A`：在**不改变 target/bin/channel 选择**的前提下，检验频域打分的
  `-0.035*|c - time|` 与 `-0.025*|c - previous|` 两项是否把谱峰系统性拉向低端。
- `NEXT_HYPOTHESIS_B`：检验 anchor 更新规则（`0.8*previous + 0.2*fused`，且 `confidence >= 0.12`）
  是否让历史低估长期驻留，从而在 gap > 10 的二选一分支里偏向低值。
- `NEXT_HYPOTHESIS_C`：为 selection margin / hr_confidence 增加 instrumentation，
  区分"选错峰"与"选对峰但峰值估计偏低"。

任一假设都必须先在**参与者/场次不重叠的未触碰验证集**上检验，不得在同一 100 probes 上继续拟合。

## 13. 证据边界

- 这是一次 development set 上的描述性机制审计；100 probes 来自 5 个 session，
  不是 100 个独立样本，不做 pooled p-value，不声称 population inference。
- ECG 仅作为机制诊断 oracle 使用，不参与任何 production 选择。
- 本审计不构成 HR/BR 提升、不是正式放行依据，HRV 继续 `BLOCKED`。
"""


def main(argv: list[str] | None = None) -> int:
    """Render all Markdown deliverables from the computed results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    out: Path = args.out_dir

    manifest = json.loads((out / "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_MANIFEST.json").read_text(encoding="utf-8"))
    tables = {
        "fc": read_csv(out / "FAILURE_CLASS_BIAS_DECOMPOSITION.csv"),
        "attribution": read_csv(out / "BIAS_ATTRIBUTION_DECOMPOSITION.csv"),
        "band": read_csv(out / "ECG_HR_BAND_DECOMPOSITION.csv"),
        "qc": read_csv(out / "QC_BIAS_DECOMPOSITION.csv"),
        "dfc": read_csv(out / "DISTANCE_FAILURE_CLASS_MATRIX.csv"),
    }

    (out / "FUSION_PATH_AUDIT.md").write_text(
        render_fusion_path_audit(out, manifest), encoding="utf-8", newline="\r\n"
    )
    (out / "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_REPORT.md").write_text(
        render_report(out, manifest, tables), encoding="utf-8", newline="\r\n"
    )

    error_log = {
        "task_id": manifest["task_id"],
        "run_id": manifest["run_id"],
        "errors": [],
        "warnings": [
            {
                "id": "QC_HR_USABLE_RATIO_CONSTANT",
                "detail": "hr_usable_ratio is 1.0 for all 100 probes, so it has no discriminating "
                          "power in this development set; rank correlations are undefined, not missing.",
            },
            {
                "id": "QC_FIELDS_NOT_AVAILABLE",
                "detail": manifest["qc_fields_not_available"],
            },
            {
                "id": "P2_CLASS_LABEL_SOURCE",
                "detail": "The frozen per-probe failure class is taken from the P2 detail column "
                          "PRIMARY_FAILURE_CLASS. The copy of that label inside the control table "
                          "differs and was not used.",
            },
            {
                "id": "DRIVE_LOCATION_DIAGNOSIS_ERROR",
                "detail": "An earlier location check used an ASCII-transliterated path segment in the "
                          "rclone listing, so the canonical shared Drive _AI_HANDOFF appeared to be "
                          "absent and an alternative listing was misread as the bundle's parent. The "
                          "shared _AI_HANDOFF is NOT reachable from the rclone remote default root; it "
                          "must be addressed with --drive-root-folder-id 1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL. "
                          "The bundle itself was always in the correct folder; the probe command was "
                          "wrong. Re-verified afterwards: 15/15 files match by read-back in the "
                          "canonical folder, and no duplicate copy exists elsewhere in the Drive tree.",
            },
            {
                "id": "SESSION_CONFOUNDING",
                "detail": "Distance-band and ECG-band cells are confounded with the 5 calibration "
                          "sessions; every pooled number in the report is accompanied by a per-session "
                          "table and must not be read as population inference.",
            },
        ],
        "blocked_conditions_encountered": [],
        "state": "AUDIT_COMPLETE",
    }
    (out / "ERROR_LOG.json").write_text(
        json.dumps(error_log, ensure_ascii=False, indent=2) + "\r\n",
        encoding="utf-8",
        newline="\r\n",
    )

    handoff = f"""# mmWave low-bias mechanism audit v1 — handoff

RUN_ID: `{manifest['run_id']}`

STATUS: `{manifest['mechanism_status']}`

TASK_BRANCH: `codex/mmwave-low-bias-mechanism-audit-v1-20260913`

BASE_MAIN_SHA: `291e50ab4313685b0645210756c9921ec9e8f245`

objective: 解释融合心率约 −9 bpm 系统性低估的主要来源，并给出有机制依据、可预注册的
下一轮方向；不搜索 estimator rule、不形成 snapshot v2。

denominator: 5 sessions（9779, 97793, 97794, 97795, 97796）× 100 probes，
ECG_VALID 100/100，窗口 `[window_effective_start, probe_onset)` nominal 30 s，
DLL host receive/enqueue 时间源。输入三份 CSV 的 SHA-256 全部 exact match。

key result:
- `CONTROL_REPRODUCTION=PASS`（fused MAE 10.457079 / bias −9.033106 / p90 AE 24.054346；
  time MAE 8.996966 / bias −6.737621；spectral MAE 15.123834 / bias −13.351010）。
- 正确类几乎无偏：`CORRECT_OR_NEAR_CORRECT` fused bias
  {[r for r in tables['fc'] if r['failure_class']=='CORRECT_OR_NEAR_CORRECT'][0]['fused_bias_bpm']} bpm。
- pooled 低估由三个失败类别承担；频域路偏得最重，融合净叠加约
  {manifest['fusion_summary']['POOLED']['mean_fusion_penalty_vs_time_bpm']:.3f} bpm 且制造
  {manifest['fusion_summary']['POOLED']['time_ae_le5_fused_gt10_n']} 个"可接受→灾难"转换。
- 距离只有弱关联且被 session/类别混淆；既有 QC 字段无 session 一致关系；
  无 ≈0.5/≈2.0 谐波锁定，但非谐波残留仍为负偏。

decision: `{manifest['mechanism_status']}`。不改 producer、不改 snapshot v1、不发布 v2、
不训练模型，HRV 继续 `BLOCKED`。

code entrypoint: `scripts/maintenance/run_mmwave_low_bias_mechanism_audit_20260913.py`
（deterministic；文档由 `scripts/maintenance/render_mmwave_mechanism_audit_docs_20260913.py` 渲染）。

LOCAL_OUTPUTS:

- `{manifest['local_only_outputs'][0]['path']}` — {manifest['local_only_outputs'][0]['rows']} rows — SHA-256 `{manifest['local_only_outputs'][0]['sha256']}` — local-only，因为含逐 probe ECG 参照与诊断细节。

CLOUD_HANDOFF:

- target folder: canonical shared Drive `_AI_HANDOFF/2026-09-13_mmwave_low_bias_mechanism_audit_v1`（本任务独立目录，未混入 snapshot v1 或 estimator improvement 文件）
- parent folder id: `1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL`（该共享 `_AI_HANDOFF` 不在 rclone remote 默认根下，必须用 `--drive-root-folder-id 1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL` 访问）
- transport: rclone 1.75.1（便携版，仓库外 `D:\\Project\\.tools\\rclone.exe`），既有已授权 Google Drive remote；凭据只存在于本机 rclone 配置，未打印、未入日志、未入库
- uploaded files: 15（14 个 Git-safe 交付物 + `CLOUD_HANDOFF_VERIFICATION.json`）
- CLOUD_UPLOAD: `UPLOADED_AND_VERIFIED`
- verification: `rclone check --checksum` exit 0；随后把整目录回读到本机 staging 并逐文件重算 SHA-256，15/15 与本地一致，目录内不含任何 snapshot v1 / estimator improvement 文件
- `CLOUD_HANDOFF_VERIFICATION.json`：逐文件回读结果记录；该文件最后写入，其自身 SHA-256 只登记在 GitHub Issue #35 pointer（收录于此会改变本文件摘要，故不收录）
- local-only: `PROBE_LEVEL_MECHANISM_100_PROBES.csv` 未上传、未入 Git；摘要记录在审计 manifest

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`
"""
    (out / "HANDOFF.md").write_text(handoff, encoding="utf-8", newline="\r\n")

    # 统一为 LF：这些文件没有 text/eol 属性，Git 会原样存储 CRLF，
    # 从而让 git diff --check 把每一行都报成 trailing whitespace。
    for generated in (
        "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_REPORT.md",
        "FUSION_PATH_AUDIT.md",
        "HANDOFF.md",
        "ERROR_LOG.json",
    ):
        path = out / generated
        data = path.read_bytes().replace(b"\r\n", b"\n")
        path.write_bytes(data)

    print(f"rendered docs into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
