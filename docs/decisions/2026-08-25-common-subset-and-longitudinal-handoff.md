# COMMON_SUBSET_BASELINE_V1 与 LONGITUDINAL_EVENT_ANALYSIS_V2_DESIGN handoff

日期：2026-08-25
决策依据：`1f6443c`

## 状态

- `COMMON_SUBSET_BASELINE_V1 = COMPLETE / awaiting adjudication`
- `LONGITUDINAL_EVENT_ANALYSIS_V2_DESIGN = COMPLETE / design only`
- 未进入 C2 v2 动态特征、复杂模型或 teacher–student。
- C1b HRV 外部 benchmark 继续保持 blocked。

## COMMON_SUBSET_BASELINE_V1

### 样本与映射

- `RUN_ID`: `COMMON_SUBSET_BASELINE_V1_20260825`
- strict common probe：通过 `subject + probe_id + exact absolute onset` 一对一映射到 NIR session_id。
- C2 本身没有原生 `session_id`；canonical session 是由可审计 C3 crosswalk 恢复的，不能表述为 C2 原生字段。
- subject `070` 的 20 条 strict 行保留在 manifest 作为排除记录，未进入模型集合。
- 两个集合均为相同 probe 行、相同 participant-disjoint 外层 LOPO folds。

| 集合 | 行数 | 参与者 | canonical sessions | label 1/2/3/4 | 单类参与者 |
|---|---:|---:|---:|---|---:|
| Primary，NIR QC ≥80% | 213 | 12 | 14 | 135 / 46 / 15 / 17 | 4 |
| Sensitivity，NIR QC ≥50% | 221 | 12 | 14 | 143 / 46 / 15 / 17 | 4 |

四名单类参与者不参与 participant-level AUC 宏平均；未用 `.50` 填补，participant-level AUC 的可定义分母为 8。

### OOF 模型结果

所有预处理在训练折内拟合，分类阈值在内层训练折中确定。

| 集合 | time/block | behavior | radar | NIR | behavior + radar | radar + NIR | behavior + radar + NIR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Primary | .680 | .572 | .582 | .350 | .624 | .605 | .641 |
| Sensitivity | .663 | .537 | .591 | .318 | .626 | .588 | .621 |

这些结果是小规模、严格共同样本的最小基线，不支持直接宣称 NIR 无效，也不支持把 radar/NIR 模态差异推广到各自完整数据集。它们只说明：在同一批 probe、同一 participant folds 和当前低复杂度模型下，time/block structural baseline 高于单一传感器模型；NIR-only 本轮没有表现出增量优势。

模型比较还报告 balanced accuracy、sensitivity、specificity、coverage、participant macro AUC 和 paired participant bootstrap CI。所有 112 个模型×参考×指标的 paired bootstrap 均完成 1,000 次有效重抽样。

### 本地证据包

`D:\Project\厚粲杯\11_数据\derived\common_subset_baseline_v1\`

包含 common subset manifest、participant/session key audit、primary/sensitivity summaries、model comparison、paired bootstrap、OOF predictions 和 run manifest。被试级明细不上传 GitHub。

## LONGITUDINAL_EVENT_ANALYSIS_V2_DESIGN

### 结构

分析层级固定为：

`participant → session → stage/block → trial/time → probe`

- 北京：两阶段，B1 → 强制休息 → B2；每个 block 432 trials、10 probes。
- 珠海：单独按三阶段协议建模，不用北京 B1/B2 语义补齐。
- 休息段：当前标记 `eye_state_unknown`，不作为闭眼基线。
- 跨模态时间统一使用绝对 Unix milliseconds。

### 预定义分析

- probe-locked event-related trajectories；
- trial-level error、commission/omission、RT、连续错误、RT 变异和极端慢反应；
- probe 前 10/20/30 秒行为窗口；
- stage × time-on-task；
- resting baseline/task reactivity；
- break/recovery 及第二阶段恢复；
- questionnaire trait × state；
- radar/NIR/behavior triangulation；
- 最后才定义 radar-only predictive model v2。

主分析使用 participant/session 重复测量模型，participant 随机截距，必要时加入 session 嵌套；trial-level error 使用 logistic mixed model，RT 使用预先定义的稳健变换。多重比较按 scientific family 预先划分，主分析使用 Benjamini–Hochberg FDR，有限计划比较使用 Holm；事后选择窗口或指标只能标记为 exploratory。

### 当前 blockers

- `repeat_participant_id` 与 `canonical_session_id` 尚未全部完成确定性映射；
- subject `070` 仍为 unresolved blocker；
- 珠海三阶段原始程序、时间线、行为和各模态字段仍需核验；
- NIR 事件后 30 秒和 blink rate 等完整 event features 尚未形成验收产物；
- 北京/珠海 ECG/RSP session 映射、同步 marker 和质量字段尚未全部确认；
- 时间线缺失或时长不一致场次必须逐场处理，不能用文件时长猜补边界。

## 下一步裁决请求

1. 是否接受严格共同样本最小基线作为当前 multimodal upper-bound 的起点，而不把本轮小样本 AUC 当成最终模态结论。
2. 是否批准按设计文档先完成珠海三阶段字段/时间线核验，再运行任何事件相关结果。
3. 是否继续保持 `label 1 vs 2/3/4` 为主终点，直到历史程序版本一致性核验完成。

## 禁止的当前表述

- 不得把 NIR-only 的低 AUC 写成 NIR 无效。
- 不得把 time/block baseline 当作传感器证据。
- 不得把 strict common probe 自动写成 C2 原生 same-session 数据。
- 不得把设计文档中的窗口和模型写成已经完成的正式分析结果。
- 不得进入 teacher–student 或大型深度模型，直到 common-subset 与纵向结构结果完成裁决。
