# mmWave 逐搏级验证扩样报告：5 场次 16 blocks（2026-08-31）

Status: `PARTIAL / HRV_BLOCKED`（扩样复核后维持）；这是 beat-timing 有效性审计，不是正式 HRV 结果。

## 1. 直接结论

- 08-30 的 3 场次 8 blocks 逐搏验证按同一固定评估契约扩充到 5 场次 16 blocks（新增 97796/97794 各 4 blocks；97792 判 not_estimable 跳过，见第 2 节清点）。
- 主容差 ±75 ms 一对一最近邻匹配：pooled `198/1364` ECG R 峰 vs `1089` 雷达峰；灵敏度 `0.145161`，精确率 `0.181818`。
- 旧 3 场次 8 窗在新运行中的数值：结构/匹配字段（matched 数、sensitivity、precision、paired-IBI 等）8 窗全部逐位一致（tolerance 1e-9），扩样修改未扰动旧场次匹配行为；timing 绝对量字段存在整体平移级微差（最大 0.002930 ms），根因：08-30 运行时脚本版本早于其 git 提交（08-30 MANIFEST 中 beat30 hash 3b01b206 与仓库任何提交版本均不同），该微差不影响任何匹配指标与结论。
- 旧 3 场次 pooled 灵敏度/精确率（从旧 CSV 复算）= `0.170243` / `0.210619`；新增 2 场次 8 窗 pooled = `0.118797` / `0.150763`。
- 结论：`HRV_BLOCKED` 在扩样后**加强**（新增场次匹配率更低，pooled 灵敏度 0.170 → 0.145，精确率 0.211 → 0.182；数字依据见第 4/5 节）。
- 本运行不计算任何正式 RMSSD/SDNN/LF/HF，不授权新检测器、调参或 HRV 指标晋升。

## 2. 5 场次 NPZ / marker 只读清点

- v3.1.1 NPZ 根：`08_算法/output/20_生理金标准验证/06_HR_COURSE_99_CORRECTED_GATE`（旧 3 场次 NPZ sha256 与 08-30 MANIFEST 逐位一致，确认同源）。

| 场次 | NPZ/JSON | 帧数 | heart_peaks | timestamps 行数一致 | 命名坑 | complete blocks |
|---|---:|---:|---:|---:|---|---:|
| 97793 | 有 | 162924 | 1991 | 是 | 无 | block1/2 |
| 9779 | 有 | 155557 | 1967 | 是 | 无 | block1/2 |
| 97795 | 有 | 140648 | 1811 | 是 | acq 误写 97995.acq | block1-4 |
| 97796 | 有 | 141395 | 1793 | 是 | 无 | block1-4 |
| 97794 | 有（文件名前缀 97994） | 133139 | 1629 | 是 | 目录/beh/mmwave 前缀 97994 | block1-4 |
| 97792 | **无 NPZ** | — | — | — | 仅 baseline+practice | 4 block 全 not_recorded |

- 97792 判定：`not_estimable + reason=仅采集 baseline+practice（events.csv 无 block1-4 段事件、无 v3.1.1 NPZ 输出）`，如实跳过。
- marker 对齐：16 个 complete block 中 15 个 marker 序列 exact；唯一非 exact 为 97793/block1（index 73 event 103 vs physical 102，与 08-30 口径一致），其 ECG affine fit p95 2.67 ms 仍可用。新增 97796/97794 的 8 个 block 全部 exact（fit p95 2.07–3.40 ms）。

## 3. 固定评估契约（与 08-30 一致，未改）

- 雷达侧：现有全记录 v3.1.1 NPZ `heart_peaks`，经权威 DLL 时间行映射；不改任何检测器参数。
- ECG 侧：block-local affine event-marker 映射 + 固定 `gold_standard_qa.py` 参数（0.5–40 Hz / 0.30 s / prominence 0.25）；保留原始 R 峰做匹配审计。
- 匹配：一对一最近邻，无逐窗 lag 搜索；主容差 ±75 ms，敏感性 ±50/100/150 ms。
- 窗口：每 block 一个确定性 60 s 区间（block 开始 +30 s 起、结束 -30 s 前），与 08-30 相同。
- IBI：仅匹配对内相邻间隔；常数偏移抵消且不用于选峰。
- 复现方式：扩展脚本直接 import 08-30 模块并调用其 `evaluate_window`（同一段代码），契约常量同源。

## 4. 每 block 匹配表（16 blocks，±75 ms）

| subject | block | ECG R 峰 | 雷达峰 | matched | sensitivity | precision | paired-IBI MAE (ms) | timing MAE (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 97793 | block1 | 80 | 72 | 19 | 0.2375 | 0.2639 | 43.7 | 38.2 |
| 97793 | block2 | 82 | 72 | 10 | 0.1220 | 0.1389 | 43.9 | 37.3 |
| 9779 | block1 | 83 | 68 | 13 | 0.1566 | 0.1912 | 45.1 | 32.2 |
| 9779 | block2 | 90 | 75 | 14 | 0.1556 | 0.1867 | 55.2 | 33.9 |
| 97795 | block1 | 88 | 61 | 9 | 0.1023 | 0.1475 | 49.8 | 43.3 |
| 97795 | block2 | 90 | 70 | 24 | 0.2667 | 0.3429 | 41.4 | 28.4 |
| 97795 | block3 | 93 | 71 | 13 | 0.1398 | 0.1831 | 47.4 | 38.8 |
| 97795 | block4 | 93 | 76 | 17 | 0.1828 | 0.2237 | 52.5 | 33.4 |
| 97796 | block1 | 93 | 74 | 11 | 0.1183 | 0.1486 | 61.8 | 38.0 |
| 97796 | block2 | 89 | 74 | 13 | 0.1461 | 0.1757 | 56.2 | 36.6 |
| 97796 | block3 | 87 | 66 | 10 | 0.1149 | 0.1515 | 45.8 | 37.8 |
| 97796 | block4 | 84 | 65 | 9 | 0.1071 | 0.1385 | 33.6 | 18.1 |
| 97794 | block1 | 81 | 63 | 4 | 0.0494 | 0.0635 | 46.4 | 36.4 |
| 97794 | block2 | 77 | 54 | 7 | 0.0909 | 0.1296 | 53.2 | 50.8 |
| 97794 | block3 | 80 | 64 | 15 | 0.1875 | 0.2344 | 58.3 | 39.1 |
| 97794 | block4 | 74 | 64 | 10 | 0.1351 | 0.1562 | 42.5 | 40.8 |

## 5. 分场次 pooled 汇总

| subject | 窗数 | ECG R 峰 | 雷达峰 | matched | sensitivity | precision | paired-IBI MAE 中位 (ms) | timing MAE 中位 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 97793 | 2 | 162 | 144 | 29 | 0.1790 | 0.2014 | 43.8 | 37.8 |
| 9779 | 2 | 173 | 143 | 27 | 0.1561 | 0.1888 | 50.2 | 33.1 |
| 97795 | 4 | 364 | 278 | 63 | 0.1731 | 0.2266 | 48.6 | 36.1 |
| 97796 | 4 | 353 | 279 | 43 | 0.1218 | 0.1541 | 51.0 | 37.2 |
| 97794 | 4 | 312 | 245 | 36 | 0.1154 | 0.1469 | 49.8 | 39.9 |
| **5 场次 pooled** | **16** | **1364** | **1089** | **198** | **0.1452** | **0.1818** | **46.9** | **37.5** |

5 场次 vs 3 场次对比：

| 指标 | 旧 3 场次 8 窗（08-30） | 扩样 5 场次 16 窗 | 方向 |
|---|---:|---:|---|
| pooled matched | 119 | 198 | 窗数翻倍、matched 未同倍增长 |
| pooled sensitivity | 0.170243 | 0.145161 | 下降（-2.5 百分点） |
| pooled precision | 0.210619 | 0.181818 | 下降（-2.9 百分点） |
| per-window 中位 sensitivity | 0.156091 | 0.137460 | 下降 |
| per-window 中位 precision | 0.188922 | 0.165963 | 下降 |
| paired-IBI MAE 中位 (ms) | 46.258 | 46.880 | 稳定 |
| 配对子集 timing MAE 中位 (ms) | 35.615 | 37.521 | 稳定 |

## 6. 容差敏感性（5 场次 pooled）

| tolerance | pooled matched | ECG R-peaks | radar peaks | sensitivity | precision |
|---:|---:|---:|---:|---:|---:|
| 50 ms | 135 | 1364 | 1089 | 0.098974 | 0.123967 |
| 75 ms | 198 | 1364 | 1089 | 0.145161 | 0.181818 |
| 100 ms | 277 | 1364 | 1089 | 0.203079 | 0.254362 |
| 150 ms | 433 | 1364 | 1089 | 0.317449 | 0.397612 |

## 7. 结论

`HRV_BLOCKED` **维持且加强**。理由（数字）：

- 扩样后 ±75 ms pooled 灵敏度 0.170 → 0.145、精确率 0.211 → 0.182，新增 97796/97794 场次的匹配质量比旧 3 场次更低（新增 8 窗 pooled 灵敏度 0.119 / 精确率 0.151），说明低匹配率不是旧场次的个例，而是该 beat 证据链的系统性现象。
- 配对子集 timing MAE 中位 37.5 ms 与 paired-IBI MAE 中位 46.9 ms 与旧结果同量级，但这是"匹配成功子集"上的条件值，不能补偿 0.85 的漏检率。
- 逐搏级证据仍不足以支持任何 HRV 指标晋升；本报告不计算 RMSSD/SDNN/LF/HF，不授权新检测器、HRV 窗口调参或正式 HRV 指标计算。

## 8. 资产与溯源

- 脚本（Git-safe）：`scripts/maintenance/run_mmwave_beat_level_validation_20260831_expanded.py`
- 逐窗明细（local-only，不进 Git）：`11_数据/derived/mmwave_beat_level_validation_20260831_5subjects_expanded/MMWAVE_BEAT_LEVEL_VALIDATION_PER_WINDOW_LOCAL_ONLY.csv`
- 汇总/容差/manifest：`docs/results/2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE/` 下 EXPANDED 三件套（旧 08-30 四件套保留未覆盖）
- Manifest：`MMWAVE_BEAT_LEVEL_VALIDATION_MANIFEST_EXPANDED_5SUBJECTS_20260831.json`（含 NPZ sha256、源码 hash、契约与边界）
