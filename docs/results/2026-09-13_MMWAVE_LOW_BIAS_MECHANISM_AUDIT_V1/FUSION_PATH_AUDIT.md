# FUSION_PATH_AUDIT.md — 冻结融合链的代码路径审计

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

1. **gap ≤ 10 bpm 时是加权平均**，权重是两路各自的 quality。本次 69/100 个 probe 走该分支。
2. **gap > 10 bpm 时不做平均，而是二选一**，选择依据是"谁更接近 anchor"。本次 31/100 个 probe 走该分支。
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

因为打分里同时含 `-0.035*|c - time|` 与 `-0.025*|c - previous|`，而 time 与 previous 在本数据上都已经偏低，**谱峰会系统性地被拉向低端**。这解释了为什么 spectral 是三者中偏差最大的（-13.351010 bpm）。

## 5. 本任务观测到的融合行为

| 指标 | 值 |
|---|---|
| spectral < time 的 probe | 78/100 |
| fused < time 的 probe | 57/100 |
| spectral < time 且 fused 被向下拉 | 57/100 |
| time AE≤5 但 fused AE>5 | 7/100 |
| time AE≤5 但 fused AE>10 | 4/100 |
| fused 相比 time improve/worsen/tie | 31/47/22 |
| 平均 fusion penalty vs time | 1.460113 bpm |
| 平均 fusion 相对 time 的带符号位移 | -2.295485 bpm |
| 平均 spectral 相对 time 的带符号位移 | -6.613389 bpm |
| fused 同时差于 time 与 spectral | 0/100 |

结论：融合**不是**主要低估来源（它相对 spectral 明显收敛，且从不比两路都差），但它确实在
worsen（47）多于 improve（31）的方向上再叠加约
1.460 bpm，并制造了 4 个
"原本可接受、融合后超过 10 bpm"的转换。

## 6. 未做的事

本审计没有修改 L1–L4 任何一行代码，没有新增融合规则、没有调阈值、没有用 ECG 选峰。
上述机制只作为 `NEXT_HYPOTHESIS` 的输入，不构成本轮的修复或候选。
