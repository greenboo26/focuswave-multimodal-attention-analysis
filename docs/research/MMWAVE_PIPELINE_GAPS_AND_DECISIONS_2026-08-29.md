# mmWave pipeline gaps and decisions

日期：2026-08-29。本文只记录既有证据恢复和静态审计后的决策，不启动新分析。

## 已闭合

- 正式镜像 `mrs6240_p2512.img` 的 `fft_mode=2` 与 ADC 实验镜像 `fft_mode=0` 已由二进制字段对照绑定；正式 `ReportDataCube1D` 不是 raw ADC fast-time 输出。
- 正式 256 点轴采用 37 mm/bin；旧 0.08 m/bin 只能作为历史错误口径，不能继续用于正式 target gate。
- `0xC2` 是 DataCube 报告/分块传输；host producer 负责解码、堆叠和下游分析，不再把它描述成 host 首次 Range FFT。
- 2T×4R 八路 complex 输出已由正式 NPZ 键和既有结构诊断确认。

## 保持未闭合

| gap_id | 缺口 | 影响 | 状态 | 不允许的替代推断 | 最小后续证据 |
|---|---|---|---|---|---|
| G-01 | 正式镜像与具体 session 的烧录/启动回执 | 部署级 provenance | `UNRESOLVED` | 不把 generic SDK 或当前源树默认为 exact session | 设备回读 hash/启动日志与 session 对齐 |
| G-02 | window、IQ、通道相位校准及 amplitude scaling | 相位/幅值可比性 | `UNRESOLVED` | 不把 SDK capability 写成已启用 | exact build/source 或运行配置回执 |
| G-03 | 物理 8 通道映射、TDM chirp 顺序、timing compensation | 相干合并和 phase interpretation | `UNRESOLVED` | 不把 8-channel consistency 写成 chest lock | exact config/parser/采样时序证据 |
| G-04 | target/bin/channel continuity gate | 错误目标和相位跳变 | `POTENTIALLY_HARMFUL` | 不用 phase unwrap 替代连续性验证 | 预定义的非重跑 audit/原始 provenance |
| G-05 | formal runner 的外部 RSP harmonic rejection 未激活 | BR/HR harmonic risk | `PROJECT_VARIANT` | 不称 2×/3× suppression 为当前 active gate | runner input contract 与已存在 RSP linkage |
| G-06 | radar beat↔ECG beat/IBI evidence | HRV | `BLOCKED` | 不把 HR peak/interval-like output 写成 HRV | 新批准的 paired beat/IBI evidence；本轮不运行 |

## 研究决策

- D-01：#15 的 HR/BR 资格不因 pipeline audit 自动升级；保持 HR quality-gated、BR supporting、HRV blocked。
- D-02：#16 在本审计完成前不运行；审计完成后仍只能按已冻结 input contract 执行一次 quality-stratified sensitivity。
- D-03：不重跑 C2B/C2C，不重开 AoA/beamforming/VMD grid/multi-bin/target-lock。
- D-04：后续任何 formal 结论必须同时引用 firmware identity、37 mm axis、producer script、QC tier、reference boundary；缺一项只能降为 exploratory/supporting。
