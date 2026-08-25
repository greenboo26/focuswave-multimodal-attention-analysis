# RS6240 数据链技术 Gate：资料审计与科研边界

日期：2026-08-25
角色：GPT 研究/方法与资料审计
状态：TECHNICAL GATE / 等待 Codex 本地代码与数据证据

## 1. 当前问题

现有质量控制（quality control [QC]）审计暴露了三个会直接影响后续生理解释的问题：

1. 自动选择的 range-bin 为约 244–248，而另一份 profile 的主峰为约 8–13；
2. device timestamp 与 host timestamp 的连续性和缺口表现不同；
3. firmware calibration、发射时序、内存/消息布局与当前 parser 的对应关系尚未形成可追溯证据。

在这三项解决前，不应继续把现有相位/频谱候选升级为正式心率、呼吸率或心率变异性结论。

## 2. 官方公开资料能确定什么

正和微芯（Possumic）官方资料确认 RS6240 是 60 GHz、2 发射通道 × 4 接收通道（2T4R）的调频连续波（frequency-modulated continuous-wave [FMCW]）AiP MIMO 雷达，工作覆盖 57–66 GHz，连续扫频带宽最高 8 GHz，并集成模数转换器、基带、1D/2D 快速傅里叶变换硬件加速、静态杂波去除和恒虚警率检测等处理单元。官方页面还明确芯片内部包含 chirp generator 与 TX-to-RX 状态机，并具有统一的 power/clock subsystem。

厂商将呼吸/心跳列为适用的微动感知场景，并宣称最高约 2 cm 距离分辨率，但这一公开产品页并没有定义我们本地数据文件中的 `range_bin`、profile index、FFT padding/cropping、消息内存布局或时间戳字段语义。因此不能仅凭产品页把 `244–248` 或 `8–13` 直接换算成真实距离。

截至 2026-08-25，厂商英文下载页列出的 RS6240 Datasheet 为 V1.4，SDK 页面已出现 RS6x/7x mmWave SDK V2.1.1（2026-08-14）、HostSample V1.0.0、数据采集库和 RadarAnalysisTool/RadarDebugTool 等工具。**当前数据应优先匹配实际采集时使用的 firmware/SDK/config，而不是直接升级到最新 SDK 后重新解释旧数据。**

## 3. Range-bin 244–248 vs 8–13：现在能说什么

### 3.1 不能直接判断为“算法选错目标”

两个索引相差很大，但它们可能根本不属于同一个坐标系。正式结论前至少需要排除：

- 原始 range fast-time FFT bin 与经过裁剪/ROI 后的局部 profile index；
- 不同 FFT 长度或 zero-padding 下的索引；
- 只保留正频率/指定距离门后的重新编号；
- profile 已经过下采样、聚合、CFAR 或静态杂波处理；
- 解析时的通道、Tx/Rx、chirp 或内存 stride 错位；
- 文件字段本身记录的是内部 buffer index，而不是物理 range bin。

以上是需要核验的技术假设，不是当前已经证明的 bug 原因。

### 3.2 必须恢复同一物理距离映射

对于标准 FMCW 距离处理，物理距离与 beat frequency、chirp slope、ADC sampling rate 和 FFT 长度相关。常见映射形式可写为：

`range(k) = c × f_s × k / (2 × S × N_FFT)`

其中 `c` 为光速，`f_s` 为 ADC sampling rate，`S` 为 chirp slope，`N_FFT` 为 range FFT 长度。若处理链裁剪或重编号，必须额外保存 `bin_offset / crop_start / decimation` 等转换关系。

因此 Codex 的技术 gate 不能只比较两个索引数字，而应对同一 frame 生成一张可审计表：

`raw index → processing-stage index → physical range (m) → channel/Tx/Rx → source config`

只要两个索引经过映射后指向同一物理距离，它们可以共存；若物理距离确实不同，再判断哪个 target selection 路径错误。

## 4. Device timestamp 与 host timestamp

公开产品资料确认 RS6240 内部有独立的 radar/clock subsystem，而数据可以通过 UART、SPI、I²C、CAN-FD 等接口传输到主机。公开资料没有给出当前 NPZ 字段里 `device timestamp` 和 `host timestamp` 的精确定义，因此以下是工程原则，而不是厂商字段声明：

- 如果 device timestamp 由雷达采集/帧生成时钟产生，它通常更适合作为 **帧间采样连续性** 的主时间轴；
- host timestamp 会额外包含串口/USB/操作系统调度、buffering 和接收时延，适合做跨设备绝对时间对齐时的锚点，但可能有 transport jitter；
- 最理想结构是保存 `device monotonic time + host/Unix absolute anchor`，用前者定义连续生理波形采样，用后者连接 thought probe、RGB/NIR 等外部事件。

当前不能因为 host timestamp 有 gap 就简单删除 device-continuous 数据，也不能因为 device timestamp 连续就默认它与 probe 的 Unix 时间已严格同步。

### 时间轴 Gate 必须回答

1. device timestamp 的单位、起点、是否单调、是否 wrap-around；
2. 每 frame 理论间隔与实际 jitter；
3. host timestamp 是采集前、接收时还是写盘时记录；
4. 两条时间轴之间是否可用线性映射/锚点连接；
5. 丢包/重连时两条时间轴分别发生什么；
6. probe/event 使用哪套绝对时钟。

正式 event-related radar analysis 只有在“连续采样时间”与“跨模态绝对时间”两种用途都被解决后才能通过。

## 5. 2T4R / Tx timing 为什么需要核验

RS6240 具有 2T4R 阵列，并由芯片内部 chirp generator 与 TX-to-RX 状态机控制发射/接收过程。若当前数据使用时分多输入多输出（time-division multiplexing multiple-input multiple-output [TDM-MIMO]）或其他交替 Tx 方案，不同虚拟通道并非严格同一时刻采样。

对于静态目标的距离检测，这个时间差可能影响有限；对于胸壁微动和逐搏相位，若直接把不同 Tx 时刻的相位当作同时观测进行相干合并，动态位移可能表现为额外相位差。因此必须从实际配置恢复：

- Tx sequence；
- chirp repetition interval；
- 每个 channel 对应哪个 Tx/Rx；
- 当前 8 通道是否在代码中被当作真正同步通道；
- 相位组合前是否需要 timing compensation。

在这些字段确认前，“8 通道空间一致”只能作为有限的探索性 QC，不能自动解释为 8 个同步生理观测。

## 6. Firmware calibration 与 memory/message mapping

需要区分两类校准：

1. **影响 RF/ADC/相位与距离的校准**：若 firmware 在采集前或运行中执行 DC、IQ、Rx gain/phase、PLL/ramp 等校准，它可能改变绝对相位、通道间相位或有效量程；
2. **只影响上层 detection/point-cloud 的算法参数**：可能改变 target selection，但未必改变原始 ADC/1D FFT 相位。

Codex 不需要先理解所有 SDK 源码，但必须建立 provenance：

`采集 session → firmware/build → radar config → message type/version → parser struct/version → ndarray shape/stride → analysis feature`

尤其要核对：字节序、signed/unsigned、float/fixed-point、channel ordering、chirp ordering、frame header 长度、payload stride 和字段版本。只要其中一项错位，就可能产生“看似稳定、但物理含义错误”的 range/phase 输出。

## 7. 正式 Gate：什么时候允许恢复 radar physiology/event analysis

### G-R1 Range mapping：必须通过

能从实际 config 和 parser 确定每个分析 range index 对应的物理距离；解释 244–248 与 8–13 的关系或确认其中一路错误。

### G-R2 Time base：必须通过

确定连续波形采用的设备时间轴，并建立到实验绝对时间/probe onset 的可审计映射；报告 jitter、gap 与排除规则。

### G-R3 Channel/Tx semantics：必须通过

确定 8 通道的真实 Tx/Rx/channel ordering 和采样时序；若用于相干合并，说明 timing treatment。

### G-R4 Parser/firmware provenance：必须通过

每个正式 session 可追溯到 firmware/config/message/parser 组合，不能用未知版本结构默认为当前 SDK 格式。

### G-R5 Sanity test：必须通过

至少使用若干已知静态距离/稳定人体片段验证：物理距离、帧率、channel ordering、phase continuity 与配置预期一致。此处是数据链 sanity check，不是 HR/BR/HRV 准确性验证。

只有 G-R1–G-R5 通过后，才批准重新进入：

`target/chest micromotion → respiration/cardiac separation → beat → inter-beat interval (IBI) → heart rate variability (HRV)`。

## 8. 当前报告允许的表述

允许：

> RS6240 为 60 GHz 2T4R FMCW 雷达，硬件带宽与微动感知能力满足呼吸/心跳应用的设备级前提；本项目已开展时间覆盖、目标距离候选、多通道和运动门控等质量审计，但当前仍在核验 range-bin 映射、时间基准及 firmware/parser 语义，因此这些 QC 结果不作为 HR、BR 或 HRV 准确性证据。

不允许：

- “8 通道一致证明锁定胸部”；
- “target-lock 证明测到心跳”；
- “官方支持生命体征，因此本项目 HRV 已验证”；
- “host timestamp gap 证明 radar 本身丢帧”；
- 在 range/time/parser gate 未通过时继续扩大生理结论。

## 9. Codex 下一次技术 handoff 要求

`RS6240_DATA_CHAIN_TECHNICAL_GATE_V1` 至少返回：

1. 实际采集 firmware / SDK / radar config inventory；
2. NPZ/message parser 字段和 ndarray layout；
3. 244–248 与 8–13 的处理阶段和物理距离映射；
4. device/host timestamp 定义、jitter、gap、anchor；
5. 2T4R Tx/Rx/channel/chirp ordering；
6. calibration 是否存在及其作用层级；
7. 静态/已知距离 sanity test；
8. G-R1–G-R5 的逐项 PASS/BLOCKED 状态。

## 资料来源

Possumic. (n.d.). *RS6240 60GHz mmWave radar SoC*. https://www.possumic.com/en/rs6240.html

Possumic. (2026). *RS6240 technical documentation/download portal*. https://www.possumic.com/en/download/products/chips/rs6240.html

> 注：公开产品页可以确认芯片架构、2T4R、FMCW、带宽、硬件加速和官方工具版本，但当前公开访问权限不足以读取锁定的完整 Datasheet/SDK 字段定义；本文件没有用公开网页替代实际采集版本的 SDK/config/parser 审计。
