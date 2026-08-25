# C1a → C1b：VS_DATASET benchmark 状态转换

更新时间：2026-08-25

## 状态

`C1a preflight 已完成 → GitHub 固化 → C1b 正式 VS_DATASET beat/IBI benchmark`

本记录对应的完整预检材料位于同目录 `2026-08-25-external-vitalsense-benchmark-preflight-v1/`。本次同步只提交脚本、manifest、报告和 smoke-test 限定结论，不提交公开数据集 MAT、原始数据或大型派生文件。

## C1a 已完成内容

- 已固定审阅 `VS_DATASET` 与 `VitalSense2024` 的公开代码快照和来源链接。
- 已实际阅读数据布局、信号分离、同步、心搏模板匹配和逐搏时间戳相关代码。
- 已建立参数化单记录适配器并完成一个 VitalSense2024 示例的 smoke test。
- smoke test 只验证 MAT 读取、雷达帧转换、暂定峰时间戳和评价 I/O 可运行，不构成 HR、IBI 或 HRV 性能证据。
- `VS_DATASET` 正式 healthy cohort 当前不在本机，尚未完成正式跨被试 benchmark。
- `TechValidation.m` 中名为 `maxCorr` 的字段实际保存 `lag_max`（同步 lag 样点），不能直接当作相关系数或同步质量指标。

## 正式评价的时序方法补充

ECG R-peak 是电活动标记，毫米波心搏峰反映随后机械胸壁运动。正式评价必须区分：

1. **设备/会话时间同步**：由原始时间戳或独立同步通道确定，并在测试评价前冻结。
2. **ECG 到机械心搏的固定生理时延**：作为 beat timing 的独立延迟项记录，不能与设备时钟偏移混为一谈。

逐搏结果同时报告：

- raw radar–ECG timing offset；
- constant-delay-corrected residual timing error；
- beat precision、recall、F1；
- matched IBI MAE、bias 和相关；
- HR MAE、coverage、RMSSD/SDNN error、failure reason。

主报告暂时保留 `±75 ms` 一对一匹配容差，不根据 smoke test 修改。另设 `±50 / ±75 / ±100 / ±150 ms` 敏感性表，用于检查结论是否依赖单一容差，不用于挑选最优结果。

如果估计 constant delay，必须预先规定估计范围和来源，并明确它是在 calibration/train 部分估计，还是仅作为 reference-alignment evaluation；不得在每个 held-out 测试窗口上反向搜索最佳 lag。

恒定整体延迟不会改变相邻 beat interval，因此 IBI、RMSSD 和 SDNN 必须独立评价，不能仅因绝对峰位置偏移就判定 IBI 提取失败。

## C1b 执行边界

正式数据取得后，使用同一批数据、同一套 ECG R-peak、同一套 session alignment 和同一评价协议比较：

1. 本项目毫米波逐搏算法；
2. VitalSense matched-filter baseline。

必须按 subject-disjoint split，禁止随机切窗口。若正式 VS_DATASET 暂时无法取得，不用 VitalSense 的 12 个示例代替正式 24 被试 benchmark；应将数据获取作为 blocker 记录，并转向 C2/C3 已确认的工作。

## 当前禁止的表述

- 不得写“HRV 已验证”。
- 不得把单记录 smoke test 当作公开数据集性能结果。
- 不得把 `maxCorr` 直接解释为相关系数。
- 不得提交 VS_DATASET/VitalSense 原始 MAT 或大型派生数据。
