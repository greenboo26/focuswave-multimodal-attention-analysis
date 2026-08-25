# 北京 Probe 前轨迹与恢复分析交接

**RUN_ID：** `BEIJING_FORMAL_BEHAVIOR_LONGITUDINAL_V1_20260825`
**依据：** GPT 裁决 `e08b169`
**状态：** `completed_behavior_only_formal_subset`

## 样本

- 70 个通过 C2 deterministic join 的北京 session；
- 46 个重复参与者；
- 59,080 个 task trial；
- 1,400 个 Probe；
- 未使用毫米波、NIR、ECG 或 RSP。

## Probe 前 10/20/30 秒轨迹

结果文件：

`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1\preprobe_window_trajectories.csv`

总体均值（10/20/30 s）：

| 窗口 | 错误率 | RT 中位数 | RT SD |
|---:|---:|---:|---:|
| 10 s | .049 | 318.5 ms | 69.1 ms |
| 20 s | .053 | 316.1 ms | 79.9 ms |
| 30 s | .051 | 312.6 ms | 84.1 ms |

三种窗口均已报告，没有挑选单一最好看的窗口。轨迹图：

`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1\fig_preprobe_window_trajectories.png`

## B1 后段→B2 前段恢复

定义：B1 block 内最后 20% 作为 `B1_late`，B2 block 内前 20% 作为 `B2_early`，先在 session 内汇总，再按 `repeat_participant_id` 聚类。

结果文件：

- `recovery_b1late_b2early.csv`
- `recovery_probe_b1late_b2early.csv`
- `fig_recovery_b1late_b2early.png`

session-level 均值：

| 指标 | B1 late | B2 early | recovery GEE 原始 p |
|---|---:|---:|---:|
| 错误率 | .055 | .052 | .384 |
| RT 中位数 | 313.1 ms | 315.2 ms | .399 |
| RT SD | 92.0 ms | 87.9 ms | .428 |
| Probe response=1 比例 | .721 | .786 | .140 |

当前没有足够证据把 B2 early 的变化写成明确恢复效应。该结果不等于“休息无效”，而是说明在当前定义的 B1 late/B2 early 对比和行为指标上，恢复差异尚未达到明确证据标准。

## 解释边界

Probe response=1 与 2/3/4 使用程序代码中性命名；不得将 2/3/4 统称为“走神”。错误率和 Probe response=1 的时间趋势仍需结合 BH-FDR、模型诊断和缺失模式进行最终正文措辞冻结。当前恢复比较为计划性首轮结果，不外推珠海，也不解释毫米波或 NIR。
