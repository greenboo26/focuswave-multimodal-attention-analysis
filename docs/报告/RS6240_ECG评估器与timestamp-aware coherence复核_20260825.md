# RS6240 ECG 逐搏评估器与 timestamp-aware coherence 复核

日期：2026-08-25  
状态：experimental validation；未修改主线算法，未进入 C8 complex coherent fusion

## 1. 本轮目的

针对首轮 RS6240 多通道比较的两个方法学风险进行修正：

1. 原评估器的 IBI/RMSSD 仍按数组顺序截断配对，漏搏后可能造成整段错位；
2. 首轮通道 coherence 使用 frame-index 数组并假定 `fs=100 Hz`，需要确认实际 timestamp 不规则性是否改变 same-Tx 与 cross-Tx 的判断。

本轮只使用已有 `sub-97793_` 的 10 个 ECG/RSP 校准窗口，未扩大场次，不修改 `process_vital_signs_v3_1_1.py`，也未运行 complex coherent fusion。

## 2. ECG evaluator v1

脚本：

```text
scripts/rs6240_ecg_evaluator_v1.py
scripts/evaluate_rs6240_multichannel_ecg_v1.py
```

规则已固定为：

- ECG 清洗规则沿用首轮版本；
- 先用 pooled S1 的 10 个窗口估计一个共享时间偏移，本轮为 `+0.365 s`；
- 该偏移不随窗口或模型重新拟合，原样应用于 S1、T0、T1、A4 和 C8-PH；
- 使用单调一对一动态规划 beat-event matching，容差 `150 ms`；
- beat precision、recall、false beat rate 和 timing error 直接由匹配事件计算；
- 只有相邻两个 ECG beat 与相邻两个 radar beat 都成功匹配时，才形成一对 IBI；
- RMSSD 只在连续的匹配有效 IBI run 上计算，并报告可用窗口数；
- 输出中不再保留按序截断 IBI 指标。

输出：

```text
work/rs6240_ecg_evaluator_v1/fusion_ecg_window_metrics.csv
work/rs6240_ecg_evaluator_v1/fusion_ecg_summary.json
```

## 3. 十窗口结果

| 模型 | HR MAE (bpm) | matched IBI MAE (ms) | matched IBI RMSE (ms) | RMSSD 绝对误差 (ms) | beat precision | beat recall | 谐波误锁率 | RMSSD 可用窗口 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 8.67 | 80.61 | 97.70 | 130.55 | 0.524 | 0.461 | 30% | 8/10 |
| T0 | 7.42 | 83.35 | 102.98 | 139.21 | 0.463 | 0.418 | 30% | 8/10 |
| T1 | 10.64 | 84.57 | 100.19 | 127.42 | 0.453 | 0.392 | 30% | 6/10 |
| A4 | 9.75 | 93.83 | 110.23 | 143.39 | 0.480 | 0.427 | 50% | 6/10 |
| C8-PH | 10.53 | 76.48 | 91.90 | 118.92 | 0.503 | 0.441 | 20% | 7/10 |

解释边界：

- T0 的 HR MAE 仍是五个模型中较好，但逐搏 recall 低于 S1，matched IBI MAE、IBI RMSE 和 RMSSD 误差均变差。因此不能写成 T0 已改善 HRV，只能保留为 experimental candidate，且首轮 HR 优势在 beat-level evaluator 下没有转化为整体逐搏优势。
- C8-PH 的匹配 IBI 与 RMSSD 误差较低、谐波误锁率也较低，但 beat recall 低于 S1，RMSSD 仅 7/10 窗口可用，不能据此宣布逐搏 superiority。
- 当前仍只有一个校准场次，不能进行跨场次重复性判断。

## 4. timestamp-aware coherence

脚本：

```text
scripts/audit_rs6240_timestamp_coherence_v1.py
```

输出：

```text
work/rs6240_timestamp_coherence_v1/pairwise_coherence_timestamp_aware.csv
work/rs6240_timestamp_coherence_v1/timestamp_quality.csv
work/rs6240_timestamp_coherence_v1/audit_summary.json
```

处理方法：

- 以 device timestamp 为主时间轴，以 host timestamp 作敏感性检查；
- 按每场前 6000 帧的实际 timestamp 计算中位采样间隔；
- 在 median-dt 均匀时间轴上线性重采样；
- 大于 `1.5 × median_dt` 的 gap 切段，不跨 gap 插值；
- 对每个连续段分别计算 coherence，再按重采样帧数加权；
- 同时保留首轮 frame-index、`fs=100 Hz` 结果用于直接比较。

device timestamp 质量：

| 场次 | 帧数 | 有效速率 (Hz) | median dt (ms) | max dt (ms) | >15 ms gap |
|---|---:|---:|---:|---:|---:|
| sub-3_ | 6000 | 98.886 | 10 | 14 | 0 |
| sub-4_ | 6000 | 98.874 | 10 | 14 | 0 |
| sub-97793_ | 6000 | 98.897 | 10 | 14 | 0 |

三场次、全部选定距离 bin 和通道对的汇总：

| cardiac-band coherence | frame-index 旧算法 | device timestamp 重采样 |
|---|---:|---:|
| same-Tx | 0.4584 | 0.4572 |
| cross-Tx | 0.4763 | 0.4733 |

按场次看，timestamp-aware 结果仍未出现 same-Tx 高于 cross-Tx 的结构：`sub-3_` 约为 0.65 vs 0.66，`sub-4_` 约为 0.46 vs 0.49，`sub-97793_` 约为 0.26 vs 0.27。timestamp 修正没有改变方向，但仍然不支持“同 Tx 天然更相干”的假设。

host timestamp 的间隔不规则性明显更大，严格切段后 0 条 cardiac-band coherence 记录可用。因此 host timestamp 只作为质量风险记录，不作为本轮 coherence 主估计。device timestamp 是当前可用的主结果。

## 5. 决策

当前路线保持：

```text
S1  formal baseline
T0  experimental candidate，先进入多场次验证
C8-PH  experimental negative/mixed result，不进入主线
C8 complex coherent fusion 继续封锁
```

本轮没有满足主线升级条件。尤其是：

```text
Tx timing 未确认
ReportDataCube1D calibration state 未确认
T0 尚未显示跨指标 beat-level superiority
当前只有一个 ECG 校准场次
```

下一步应先用同一 evaluator 扩展到所有可用 ECG/RSP 校准场次，以场次/被试为分析单位，报告每场 `ΔHR_MAE`、`ΔIBI_MAE`、`Δbeat_recall`、`ΔRMSSD_error` 和 `Δharmonic_mislock`。在此之前不扩大融合结构，也不把 T0 或 C8-PH 写入正式主线结论。

