# RS6240 SDK / DataCube1D 距离尺度审计

状态：PARTIAL（只读审计；未改动固件、采集、分析或数据）  
审计日期：2026-08-29

## 已核验的范围与来源

- 中央分析：`greenboo26/focuswave-multimodal-attention-analysis@main`，当前读取 commit `e81c2983f78c63045a38761129ad28e3d788d966`。
- 采集程序：`kyandi233-dev/FocusWave@stable-msmf`，当前读取 commit `9d918e631b0efc00f90712192669798dc6c83a06`。
- SDK 主线：`D:\Project\厚粲杯\04_硬件\05_硬件使用\RS6x_7x_mmWave_sdk_V2.1.0\Software_Kit\02_SDK\psdf_sdk\project\mmwave\mmwave\ReportDataCube1D\cdk_6240_cpuf`。
- CDK：`cdk-windows-V2.24.11-20250612-1933`；工程名为 `ReportDataCube1D_MRS6240_P2512`，编译定义为 `CONFIG_BOARD_MRS6240_P2512_CPUF=1`，CPU 为 `e906fp`。CDK 仅用于构建，不参与数据处理。
- 正式文件抽查：`J:\Data\sub-058_\mmwave`。其 `meta.json` 创建时间为 2026-08-19 21:42:59；首个 NPZ 具有 8 个键 `tx0_rx0` 至 `tx1_rx3`，每键形状为 `(1000, 256)`、类型 `complex128`。其 `.datacube.bin` 人工写入的 PSIC 头解出 `2TX/4RX`、256、37 mm。

## 直接结论

### 1. 现在的 NPZ 到底是什么

它是采集程序从 `dataType=3 (0xC2)` 收到 DataCube payload 后，调用 SDK .NET API `DatacubeConversion()`，再逐 `txAntId/rxAntId` 组合成复数数组并写入 NPZ 的结果：

`设备 ADC/IF → 芯片数据立方体存储 → ReportDataCube1D 0xC2 分块上传 → SDK DatacubeConversion → 8 个 NPZ 复数数组`

8 个数组是 `2 TX × 4 RX = 8` 个时分 MIMO 虚拟通道，不是 4 个 RX 的重复或主机融合。正式文件证实它们是 `tx0/tx1 × rx0..rx3` 的 8 条独立数组。

但“每个元素一定是 range bin”**未获部署级证实**。当前 SDK 源树中的 `prj_config.h:103-108` 明确写有 2026-08-12 的实验性改动，并把 `CONFIG_RADAR_FRAMEWORK_FFT_MODE` 设为 `RADAR_FRAMEWORK_ADC_MODE`；其注释说明该模式跳过 range FFT、上传 8×256 raw complex16 time-domain samples，且完成验证后应改回 `2DFFT_MODE`。本地正式文件创建于此后，但缺少烧录镜像 SHA-256、设备回读配置或串口启动日志，故不能把“当前源树的 ADC 模式”写成“正式 session 已证实的运行模式”。

因此，对正式 NPZ 的最严谨标签是：**8 通道、每通道 256 点的 SDK 解码 complex DataCube；其为 range-domain 还是 raw time-domain ADC，当前证据尚未闭环。** 分析端把它命名/处理为 range cube，并不构成固件端语义证据。

### 2. 处理链与各格含义

| 环节 | 实际做了什么 | 证据 | 参数 | 是否影响距离轴 |
|---|---|---|---|---|
| ADC/IF | RF/ADC 由 RS6240 的底层控制库取得；本工程没有把裸 ADC 直接交给 PC 的独立采集接口。 | `radar_framework.c:195-205` 调 `mmw_time_domain_switch_set()` | 由 `fft_mode` 控制 | ADC 模式下，256 点是 fast-time sample index，不能直接用 mm/bin。 |
| 1D 框架 | `frame_type=0`，调用 `mmw_mode_cfg(..., MMW_WORK_MODE_1DFFT)`，注册 `MMW_DATA_TYPE_1DFFT` 回调。 | `main.c:69-81`；`radar_framework.c:159-205, 437` | 1D frame、10 ms frame period | 不单独改轴。 |
| Range FFT | 正常 FFT 模式下由 RS6240 控制/硬件数据路径完成；框架仅用 `__mmw_fft_range()` 从 cube 读出数据，未在 C 中执行 FFT。当前源树 ADC 模式则显式切为 time-domain，注释称跳过 range FFT。 | `radar_framework_report.c:131-138`；`prj_config.h:103-108` | `range_fft_len_log2=8`，即 256 | 仅 FFT 输出才能把 index 解释成 range bin。 |
| DataCube1D | report callback 从运动 cube 顺序读出 `[TX][RX][doppler][range]` complex16，封装为 `0xC2`；1D 的单 interval 情形由上位机保存为 8×256。 | `radar_framework_report.c:131-167, 652-679`；`radar_signal_process_1d.c:160-177` | `tx=2, rx=4, range=256`；报告元素 4 bytes/complex16 | 只搬运/封装，不重新标定。 |
| SDK/producer | 接收 `0xC2`，用 `DatacubeConversion` 解成 `real + j·imag`，按 tx/rx 写 NPZ；没有 FFT、去均值或杂波处理代码。 | `mmwave_capture.py:378-459, 482-484` | NPZ 以 1000 帧分片 | 不改轴。 |
| Python analysis | 将 NPZ 当作 range cube，并以常数 `0.08 m/bin` 计算距离 gate。 | `process_vital_signs_v3_1_1.py:17-18, 2500-2517, 2728-2755` | gate 默认 0.30–1.50 m | 当前轴与 37 mm 配置不一致。 |

## 输出前的处理：存在、未启用与未证明

| 项目 | 代码事实 | 该工程正式配置 | 能否确认正式采集启用 |
|---|---|---|---|
| DC offset / DC suppression | 框架具有 `mmw_psic_dc_suppression_update()` 路径，但只在 `MMW_CLUTTER_REMOVAL_DC` 时调用。 | `CONFIG_MMW_POINT_CLOUD_BB_CLUTTER_RM = MMW_CLUTTER_REMOVAL_NONE`。 | 否；当前工程配置为未启用，正式 session 又无运行回执。 |
| static clutter suppression / background cancellation | 使用同一 clutter 配置；`NONE` 时框架打印 disabled。 | 未启用。 | 否。 |
| MTI | 未在 ReportDataCube1D 的调用链发现 MTI 配置或函数调用。 | 未证明。 | 否。 |
| IQ offset / IQ imbalance correction | 未在该工程→report→producer 的实际调用链发现调用点。底层模拟/芯片校准不能由此排除。 | 未证明。 | 否。 |
| mean subtraction / detrend | producer 只解码、堆叠、保存；未发现此操作。 | 未启用。 | 否。 |
| windowing | 该工程没有窗口参数或显式窗口调用。若为 FFT 模式，底层预编译控制库是否内置窗函数无法从本工程源码确认。 | 支持/启用均未证明。 | 否。 |
| coherent accumulation | `acc_num_log2=0`，框架调用 `mmw_chirp_num_cfg(1)`。 | 未配置多 chirp accumulation。 | 源码层否；部署级仍缺回执。 |
| zero padding / FFT scaling | 未在工程中设置。ADC 模式要求 range FFT length 等于 ADC sample number。 | 无配置证据。 | 否。 |

## 距离映射闭环

### 37 mm/bin 的来源和公式

`ReportDataCube1D/src/prj_config.h:77-79` 设定 `range_fft_len_log2=8` 和 `range_resolution_mm=37`；`main.c:69-78` 将其传给框架。框架实际计算：

```text
N_range = 2^8 = 256
B_MHz = 150000 / range_resolution_mm = 150000 / 37 = 4054.05 MHz
end_freq = 57000 + B_MHz = 61054.05 MHz
max_range = N_range × 37 mm = 9472 mm
若且仅若 payload 是 range-FFT cube：distance(i) = i × 0.037 m
```

这与 FMCW 名义距离分辨率 `c/(2B)` 约为 0.037 m 一致。`37 mm` 同时由采集程序硬编码写入 PSIC 文件头的 range-resolution 字段；该头由 PC 在写 `.datacube.bin` 前构建，不是从 `0xC2` payload 读取。因此它是“采集端宣称采用的配置”，不是本 session 的独立固件回执。

若 session 实际运行 ADC mode，上述最后一行不成立：`i` 是 ADC fast-time sample index；必须有实际 chirp slope、ADC sampling rate 和采样起点才能由 beat-frequency 再换算距离。它们不在正式 meta、NPZ 或此 report header 中。

### 0.08 m/bin 的来源和判定

分析代码 `process_vital_signs_v3_1_1.py:17-18` 直接赋值 `SDK_DEFAULT_BIN_SPACING_M=0.08` 和 bias 0；`_bin_to_distance_m()` 只是 `bin_idx × bin_spacing_m - bias`，没有读取 meta、PSIC 头或 SDK 配置。SDK 中另一个点云示例 `subsys/mmw/mmw_application/mmw_app_pointcloud.c:107` 的确使用 `mmw_range_cfg(80*256, 80)`（8 cm）；这证明 SDK 有一套 80 mm 的**不同示例配置**，但不能证明它是 FocusWave ReportDataCube1D 的正式配置。

结论：`0.08 m/bin` 是 analysis 的硬编码历史/默认常数，非正式 DataCube1D 配置的派生值；对“已经确认是 FFT cube”的 37 mm 配置不一致，不能继续作为有效距离口径。它也不是 37 mm bin 的下采样或裁剪结果：两端均为 256 点，代码没有重采样。

### gate 的实际差异（只在 FFT 语义成立时）

默认 0.30–1.50 m gate：

| 距离口径 | 允许的整数 bin |
|---|---|
| 0.037 m/bin | 9–40 |
| 0.08 m/bin | 4–18 |

所以 0.08 口径会纳入正式 37 mm 尺度的约 0.148–0.296 m bins，并排除约 0.703–1.480 m bins。它不是轻微单位误差，而是实质改变 target 搜索区域。

## 近距离强反射风险

结论：**高风险但未证实。**

条件化原因如下：如果正式 payload 是 37 mm range FFT，当前 analysis 的 0.08 m/bin gate 会包含 true 0.148–0.185 m 的 bin 4–5。SDK 点云应用中把 200 mm 内列为 direct-wave / first-bins 的特殊阈值区，但该保护位于点云处理代码；ReportDataCube1D 的 report 路径直接上传完整 cube，未见对自泄漏、近场耦合、桌面/支架或静态反射的专用排除。并且当前工程的 static clutter removal 明确设为 NONE。

这尚不是“已证实选错目标”：没有本次审计所需的已烧录镜像哈希/启动配置，也没有已定位 session target bin 与实测摆位的闭环。若实际运行 ADC mode，距离 gate 本身没有物理含义，风险判断同样不能升级为因果结论。

## 最小可补证据（本次不执行）

1. 读取设备当前固件镜像哈希或启动日志，并和采集日期对应的烧录记录匹配。
2. 对一个正式 session 保存/解析设备配置回执，至少包含 `fft_mode`、range resolution、range FFT length、ADC sample rate、chirp slope。
3. 在不改算法的前提下，以该回执重新标注 range axis，并记录实际雷达—胸部距离及 target bin。

