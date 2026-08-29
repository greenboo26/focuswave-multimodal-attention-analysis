# FocusWave 毫米波前半段透明化审计

审计日期：2026-08-29；状态：**PARTIAL（代码与一段真实会话已核验；SDK/固件内部处理和物理距离标定仍 BLOCKED）**。

## 先给结论

1. 当前分析读取的不是 raw ADC，也不是分析端刚做完 Range FFT 的数据；它读取的是 RS6240 DLL `DatacubeConversion` 后、按 8 个 Tx/Rx 通道存入 NPZ 的复数 range cube。
2. 在可见的 producer Python 和当前分析的“NPZ → target 选择”路径中，**没有** DC offset、IQ imbalance、静态杂波/MTI、背景建模或 temporal-mean subtraction 作为实际预处理。诊断图中有均值相减对照，但明确只是审计显示，未参与结果。
3. 当前 target 选择不是人体定位：先按相位频段/稳定性在每个通道独立挑 bin，再从通道间选最高分；没有角度、波束形成、胸部约束或空间校准。
4. 现行 0.30–1.50 m gate 已避免代码记录过的远距离假峰，但“bin × 0.08 m”的分析坐标与 producer PSIC 的 37 mm metadata 不一致；所以这不是已验证的物理距离，近距离支架、桌面、键盘或泄漏是否被选中仍无法从本次证据排除。

## 真实数据核验

只读使用 `D:\acq_mmwave_data\sub-2_\mmwave\sub-2_mmwave_datacube_part001.npz`，其配套 meta 记录为 CAL、99,146 帧、98.7 fps、256 range FFT、2T4R。该文件实际含 8 个 `tx*_rx*` 复数数组，每个形状为 `1000 × 256`；本审计只读取该 10 秒 chunk，不运行分类、不写回原数据。

![CAL 前端审计图](frontend_diagnostic_figures/cal_sub2_part001_frontend_audit.png)

图的左上是当前存储数据的 raw range-time magnitude；右上是**仅作对照**的逐 bin 时间均值相减，证明该操作可以显示静态成分，但并非当前 pipeline。左下叠加当前代码的 0.30–1.50 m gate 和按同一公式重算出的候选；右下显示全距离平均功率最高的通道与最终按 BR/HR 评分选中的通道可以不同。

本 chunk 的直接结果（仅说明选择行为）：auto max-power 为 ch2；BR 候选为 ch3/bin13（当前分析坐标 1.04 m），HR 候选为 ch1/bin9（0.72 m）。它们不是 HR/BR/HRV 准确度结论，也不能证明对应人体胸部。

## 实际链路

`RS6240 callback dataType=3` → 原始 payload 同时写 PSIC bin → DLL `DatacubeConversion` → `tx0_rx0...tx1_rx3` 的复数 NPZ arrays → central script stack 为 `frames × bins × 8` → 全记录均值功率/相位候选评分 → 距离门 → 各通道独立选择 BR/HR bin。

| 问题 | 已核验事实 | 证据边界 |
|---|---|---|
| 输入是什么？ | SDK-derived complex range-domain NPZ（8 通道），不是本链路可见的 raw ADC。 | SDK 内部到底做了什么，未获得可审计源码。 |
| Range FFT 在哪？ | producer 写入 PSIC header 时标为 FFT / 1DFFT；central script 对 NPZ 是 identity。 | 固件/SDK的 FFT 参数和窗函数不可复现验证。 |
| DC/static clutter？ | 可见路径没有实际去除；只见后续 phase detrend（用于评分）和绘图诊断。 | 不排除 SDK 内部未文档化处理。 |
| bin 如何选？ | 1%功率阈值 + unwrapped phase 的 BR/HR SNR 与稳定性评分；当前主路径先加 0.30–1.50 gate。 | 无人体/胸部定位真值。 |
| channel 如何选？ | 8 通道逐一评分，BR 与 HR 可选不同通道；无平均、相干合成或 AoA。 | Tx/Rx物理布局与校准缺失。 |

完整逐项代码证据见 `FRONTEND_CODE_PROVENANCE.csv`。

## 高风险缺口（不修复，只列出）

- **距离坐标未闭环：** producer 的 PSIC metadata 写 37 mm resolution，analysis 默认却采用 0.08 m/bin。当前 gate 的“米”是代码坐标，尚不能当作物理测距或人体距离。
- **静态/近距离污染未被前置抑制：** 静止大反射体和泄漏进入功率与相位候选池；gate 只能排除坐标范围外反射，不能识别范围内桌面、支架或键盘。
- **没有空间 target identity：** 2T4R 目前是八路独立竞争，并未用来确认来自人体胸部的方向。
- **SDK opaque：** NPZ 前的 DC、IQ 或 firmware clutter 处理没有证据，不能写成“已处理”或“未处理”。

## 代码追溯

- 采集 producer：`D:\Project\厚粲杯\05_实验\FocusWave\01-MainProgram\core\mmwave_capture.py`，重点 92–177、378–459、482–484。
- 本地采集镜像：`D:\Project\厚粲杯\11_数据\radar_collector\scripts\mmwave_capture_v4.py`，与上述 datacube/NPZ 模式一致。
- 中央分析：`D:\Project\厚粲杯\08_算法\work\focuswave_repository_final_clean_clone_3cd3433\scripts\process_vital_signs_v3_1_1.py`，重点 1099–1233、1374–1412、2500–2517、2803–2880。
- git 证据：`7a482f01`（2026-08-16）注释记录了远距离 bin 252/247 的杂波选择缺陷及其距离门修正；当前文件最近提交 `7f98121d`（2026-08-23）。

下一步应先把行业图谱与本审计合并，明确哪些缺口是必须证伪/标定的；**本批不进入算法修复、调参或重跑专注分类。**


