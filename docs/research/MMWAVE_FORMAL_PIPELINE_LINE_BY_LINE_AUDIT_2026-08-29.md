# Formal mmWave pipeline line-by-line / logic-block audit

审计日期：2026-08-29
范围：RS6240 正式 `ReportDataCube1D` → NPZ → HR/BR/HRV/QC。全程静态复核；未运行科学分析、未重算数据、未修改 producer/NIR/RGB/原始数据。

## 结论

正式镜像 `mrs6240_p2512.img`（SHA-256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`）的已初始化配置字段为 `range_resolution_mm=37`、`range_fft_len_log2=8`、`fft_mode=2`。与同构的 2026-08-12 ADC 实验镜像（SHA-256 `bc3395113a8647f1ec16c779b6b3f153e43a979727d3f1853506ef5548d447d7`，`fft_mode=0`）对照后，正式数据应按 **1D Range-FFT DataCube** 解释，而不是 ADC fast-time samples。

因此，正式下游的 256 点轴是 range-bin 轴，当前固定距离口径为 `distance_m = bin × 0.037`；但该结论不扩展为已验证胸部锁定，也不证明所有 amplitude、通道相位校准或 TDM timing 细节。

## 上游审计块

| 逻辑块 | 代码/证据 | 实际操作 | 状态 | 风险/边界 |
|---|---|---|---|---|
| 镜像身份 | `FIRMWARE_BINARY_COMPARISON.csv`；正式/ADC image | 比较同构镜像、SHA、build 字符串及 `0x37918` | `MATCHED` | 缺正式烧录记录与设备启动回执；模式判定依赖已保存二进制对照 |
| 配置初始化 | `ReportDataCube1D/src/main.c:65-83` | 将 frame/range/FFT/accumulation/fft mode 写入全局配置 | `MATCHED` | source tree 当前 `prj_config.h:103-108` 是后续 ADC 实验编辑，不能单独代表正式镜像 |
| range 配置 | `prj_config.h:76-79`；镜像字段 | 1D frame、256 range FFT、37 mm resolution | `MATCHED` | 未验证额外 range bias |
| 1D signal path | `radar_signal_process_1d.c:99-108,160-178` | ADC mode 才走 raw ADC 约束；非 ADC 1D 读取 range FFT | `MATCHED_WITH_BINARY_BINDING` | 代码树与正式镜像时间不同，必须以镜像字段绑定 |
| report packing | `radar_framework_report.c:131-167` | 按 tx/rx/doppler/range 读取 complex16 并分块发 `0xC2` | `MATCHED` | HIF 分块是传输，不是 host 端 FFT |
| channel count | formal NPZ `tx0_rx0`…`tx1_rx3`；已有结构诊断 | 2T×4R=8 complex channels | `CONFIRMED_BY_OUTPUT_SEMANTICS` | 物理天线映射、chirp/TDM 时序与相干合并补偿仍缺正式回执 |
| DC/clutter | `prj_config.h:100-101` | `MMW_CLUTTER_REMOVAL_NONE` | `MATCHED` | 未启用不能被后处理报告写成已做静态杂波抑制 |
| window/scaling/calibration | SDK path scan + producer | 未找到该 ReportDataCube1D 应用的显式 window、IQ、通道相位校准或 scaling 调用 | `UNRESOLVED` | 预编译 lower-layer 行为不能从 generic SDK 默认推断 |

## 下游逻辑块

| 文件/行 | 操作 | 输入/输出 | 状态 | 主要风险 |
|---|---|---|---|---|
| `scripts/process_vital_signs_v3_1_1.py:1099-1112` | 读取 NPZ 八键并 stack | frame×256×8 complex64 | `MATCHED` | 若输入 schema 改变，边界处无独立 metadata gate |
| `:1146-1172` | 全段累积 power 与 channel power | bin×channel power | `PROJECT_VARIANT` | 全段聚合会隐藏局部目标变化；不是胸腔验证 |
| `:1194-1233` | phase variance、HR/BR SNR、stability score 选 bin | BR 与 HR 可选不同 bin/channel | `HEURISTIC` | 强反射、呼吸谐波、bin hopping、通道相位断裂可能造成稳定但错误候选 |
| `:268-278;1415-1437` | `angle`→`unwrap` 提取位移 | selected complex trace→phase/displacement | `PROJECT_VARIANT` | 选点切换前后没有独立 phase continuity gate；unwrap 不修复错误选点 |
| `:584-680` | detrend、0.1–0.5 Hz 呼吸带、peak/periodogram consensus | BR candidates | `HEURISTIC` | 外部 RSP 谐波拒绝支路不是当前 formal runner 的 active gate |
| `:289-391;1296-1373` | VMD/heart mode、心跳带、融合 | heartbeat candidate | `HEURISTIC` | 呼吸 2×/3×可进入 HR band；高 confidence 不等于 ECG 正确 |
| `:727-775;857-1052` | periodogram、peak/time-course、融合 confidence | HR course/quality | `HEURISTIC` | 参考锚定/谐波折返是方法规则，不是独立验证 |
| `:826-855` | interval/peak metrics | IBI-like summaries | `MISSING` | 当前没有足够 radar beat↔ECG beat 配对证据，HRV 保持 blocked |
| `scripts/run_timeline_gated_mmwave_quality.py:70-105` | 以 baseline/block 调 producer，独立汇总 block 质量 | per-block HR/BR/QC summaries | `PROJECT_VARIANT` | 明确不跨 block 合并 IBI/HRV；runner 未传 `acq_path`，RSP 辅助 branch 未激活 |
| `scripts/maintenance/build_formal_vital_qc_v1.py:36-82,150-205` | 覆盖率、target-lock/provenance 分类 | Tier/QC reasons | `MATCHED` | QC 是 eligibility/attribution，不是 physiology validity |

## 必须回答的科学问题

1. **target selection**：当前是 power + phase stability + HR/BR band score 的 human-target candidate heuristic，不是“最强反射=人体/胸部”。已有 8-channel 一致性只能作为 candidate evidence。
2. **bin/channel switching**：BR 与 HR 可以选择不同 bin/channel；当前审计没有证明跨 window 的连续锁定或 TDM phase compensation。bin hopping/phase discontinuity 是潜在有害项，不能被统一写成运动伪影。
3. **独立运动证据**：当前 `phase_stability` 和 coverage 是 proxy/gate，不是独立 motion sensor；不能用它区分真实运动与 target/phase/coverage 失败。
4. **呼吸谐波**：代码存在依赖外部 RSP 的 2×/3×拒绝支路，但 formal runner 未传 `acq_path`，因此不能写成当前 formal active suppression。已有证据证明“稳定但错误”的谐波风险真实存在。
5. **HRV**：当前 peak/interval-like 数字不足以构成 beat/IBI + ECG alignment evidence；HRV 仍 `BLOCKED`。
6. **QC gates**：文件完整性、时间/linkage、target/phase、signal presence、probe coverage、physiology reference 是不同层级；不能用一个“signal quality”笼统替代。

## 33/37 的正式含义

当前 corrected QC 的 `Tier1=33`、`Tier2=37`、`Tier3=2` 是 pipeline eligibility/attribution strata：Tier1 是 QC-eligible candidate，不是 HR/BR ground-truth validation；Tier2 保留微动/体动或局部输出但不放行正式生理主结论；Tier3 是 linkage/acquisition 级阻断。它们不是“33 个好、37 个坏”，也不是 participant compliance 统计。

## 结论性动作边界

- `HR`: `PASS_QUALITY_GATED`，使用 corrected 37 mm 口径及既有 reference evidence；不得写成无条件准确。
- `BR`: `PASS_SUPPORTING`，仅 supporting/sensitivity；不得升级为 validated respiratory ground truth。
- `HRV`: `BLOCKED`，除非新增且已批准的 beat/IBI + ECG evidence；本轮不新增。
- `#16`: 继续暂停；只允许使用既定质量分层契约，不在本轮运行。
