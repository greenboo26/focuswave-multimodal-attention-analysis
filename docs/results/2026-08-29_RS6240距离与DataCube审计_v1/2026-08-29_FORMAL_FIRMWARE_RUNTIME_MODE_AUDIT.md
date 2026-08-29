# 正式 RS6240 固件运行模式与 DataCube 语义闭环

状态：**PASS — 正式 `mrs6240_p2512.img` 输出为 Range-FFT 后的 1D DataCube，不是 ADC complex samples。**  
审计日期：2026-08-29；全程只读，未重编译、烧录、修改数据或重跑分析。

## 判定链

### 直接固件证据（决定性）

用户确认的正式镜像 `mrs6240_p2512.img` 与 2026-08-12 ADC 实验镜像 `mrs6240_p2512_adc.img` 都是 233,280 bytes；两者只有 74 bytes、9 个连续区段不同（相同字节比例 99.9682785%）。这说明 ADC 镜像是对正式 ReportDataCube1D 构建做的极小改动，而非另一个应用。

最关键差异在二进制偏移 `0x37918` 的已初始化 `RadarFrameConfig_t.fft_mode`：

| 固件 | `range_resolution_mm` @ `0x37900` | `range_fft_len_log2` @ `0x37904` | `fft_mode` @ `0x37918` | 解释 |
|---|---:|---:|---:|---|
| 正式 `mrs6240_p2512.img` | 37 | 8 | **2** | `RADAR_FRAMEWORK_2DFFT_MODE` |
| ADC 实验 `mrs6240_p2512_adc.img` | 37 | 8 | **0** | `RADAR_FRAMEWORK_ADC_MODE` |

这个字段顺序来自 `ReportDataCube1D/src/main.c:65-82` 的全局 `RadarConfig_t` 初始化；枚举在 `radar_framework.h:68-71` 明确规定 `ADC_MODE=0`、`RFFT_MODE=1`、`2DFFT_MODE=2`。该工程为 `frame_type=0` 的 1D frame；SDK 同一枚举注释明确说明 2DFFT mode 在 1D frame 中不会执行 Doppler FFT。因此正式镜像的 `fft_mode=2` 表示：**保留 Range FFT，输出 1D range-domain DataCube；不产生 Doppler 维。**

ADC 镜像创建时间为 2026-08-12，且当前可见的 `prj_config.h:103-108` 正好把 `fft_mode` 改为 `ADC_MODE`。正式镜像的 build 字符串为 `Jul 24 2026 21:33:39`，ADC 镜像为 `Aug 12 2026 20:58:06`。其余大块差异是构建签名/校验和日期字符串；不是另一条采集应用的证据。

正式镜像与 SDK 预编译 `ReportDataCube1D_mrs6240_p2512.img` 不完全相同（2,286 个字节不同），因此本审计**没有**把二者视为完全一致；闭环只依赖正式镜像自身与有明确 ADC 意图的紧邻构建之间的已初始化模式字段对照。

### 正式 payload 的独立结构核验（支持性）

抽查 3 个正式 session（sub-058、sub-064、sub-070）的 `tx0_rx0`，各取 1,000 帧：

| session | 原始 256 点轴中位幅值峰 | 原轴 peak/median | 原轴逐帧众数峰占比 | 再做一次 FFT 后 peak/median | FFT 后逐帧众数峰占比 |
|---|---:|---:|---:|---:|---:|
| sub-058 | 9 | 325.88 | 99.7% | 2.14 | 6.8% |
| sub-064 | 8 | 186.04 | 54.1% | 2.16 | 5.2% |
| sub-070 | 8 | 120.66 | 44.1% | 2.01 | 15.3% |

原轴已有长期稳定、尖锐的固定 bin 峰；再做一次 FFT 没有产生同样稳定/尖锐的空间峰。这一结果与 range-domain DataCube 一致，并与“正式 payload 是尚待 PC 做第一次 Range FFT 的 ADC fast-time sample”不一致。不过它只是支持性证据；本次 PASS 不依赖视觉形态。

## DataCube 的正式语义

```text
ADC/IF → RS6240 硬件 Range FFT（正式 image 的 fft_mode=2）
       → 1D DataCube [TX=2, RX=4, range=256] complex16
       → HIF 0xC2 分块上传 → SDK DatacubeConversion
       → NPZ: tx0/tx1 × rx0..rx3，各 frame×256 complex
```

`2TX × 4RX` 是 8 个 TD-MIMO virtual channels。正式的 1D frame 不增加 Doppler FFT 维；`DataCube1D` 中的 256 点是 range-bin axis。

## 37 mm/bin、0.08 m/bin 与风险判定

- 正式固件镜像直接包含 `range_resolution_mm=37` 和 `range_fft_len_log2=8`。因此**37 mm/bin 现在可以作为正式 Range-FFT 轴的固件口径**：`range_m(i)=i×0.037`（本审计未发现或验证额外 range bias）。满量程名义值为 `256×0.037=9.472 m`。
- `0.08 m/bin` 没有出现在正式镜像的该配置字段中；analysis 中仅为硬编码默认值。因此它对这批正式 DataCube 应判为**错误的历史/默认遗留距离口径**，不得再用作其 target gate 的物理轴。
- 这不会单独证明已选错 target。它证明旧 0.30–1.50 m gate 实际按 0.08 取 bin 4–18，而正式 37 mm 口径应为 bin 9–40；旧 gate 会允许真实约 0.148–0.296 m 的 bins，并漏掉约 0.703–1.480 m 的 bins。
- 因而近距离强反射仍是**高风险但未证实**，不升级为“已证实影响”：尚未把某个实际被选 target bin、真实实验摆位和反射来源一一对应。现在已证实的是距离 gate 的口径错误，而不是某一次 target selection 的错误归因。

## 历史构建检索

在 `ReportDataCube1D` 与 SDK 父目录以 `*.map`、`*.elf`、`*.lst`、`*.log`、`*.bak`、旧 `prj_config.h` 和 build 文件名只读检索，未发现可与正式 SHA-256 完整匹配的 July build output 或正式版本的旧 `prj_config.h`。发现的 `radar_framework_hif_handler.c.bak_20260812` 与 HIF 配置处理有关，不能提供旧 `fft_mode`。

这项缺口不改变 PASS，因为正式/ADC 镜像的同构构建对照已直接定位到 `fft_mode` 这个模式枚举字段。

## 产物与可复核标识

- 正式 SHA-256：`7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`
- ADC SHA-256：`bc3395113a8647f1ec16c779b6b3f153e43a979727d3f1853506ef5548d447d7`
- 完整逐镜像哈希、可打印字符串与 diff 统计：`FIRMWARE_BINARY_COMPARISON.csv`。
- 三个正式 session 的数值诊断：`FORMAL_DATACUBE_SEMANTICS_CHECK.csv`；图仅呈现原轴、一次 FFT 和多帧稳定性，未用于单独定论。
