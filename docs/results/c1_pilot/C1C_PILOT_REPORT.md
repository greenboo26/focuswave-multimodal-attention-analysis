# C1c mmHRV single-target pilot

状态：`C1C_PILOT_COMPLETE`，但未达到继续扩展的“明显量级改善”门槛。

## 输入与范围

- 正式 RS6240 raw ADC NPZ：每帧 8 路 complex、256 个 fast-time 点。
- 前端：逐通道 256 点 range FFT → 单通道/单 bin 周期性与相位稳定性选择 → complex phase → unwrap。
- VMD：`vmdpy`，`K=3`、`alpha=1000`、`tau=0`、`DC=False`、`init=1`、`tol=1e-6`。
- 心跳范围：0.8–2.0 Hz；归一化包络窗口：2 s。
- 逐搏检测复用现有 `process_vital_signs_v3_1_1.detect_peaks_heart_lo`。
- 每场固定取前 60 s / 6000 frames；没有 beamforming，没有 ECG 驱动的前端调参。
- ECG 时间轴沿用既有 marker 线性对齐，固定 delay `-18.000 ms`，主容差 `±75 ms`，另输出 `±50/100/150 ms`。

## 代表场次

`sub-97793_`、`sub-9779_`、`sub-97795_`。前者为相对较好对照，中者为稳定/中等对照，后者为已有半频风险的较差对照。`sub-97794_` 当前没有 NPZ，未硬凑进 pilot；`sub-97795_` 使用其目录内唯一的 `97995.acq`，这是既有文件命名差异，不是新建或复制数据。

## 主容差结果（±75 ms）

| session | method | precision | recall | F1 | IBI MAE (ms) | HR abs error (bpm) | RMSSD abs error (ms) | SDNN abs error (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 97793 | project bandpass | .467 | .224 | .303 | 45.0 | 1.38 | 35.4 | 12.4 |
| 97793 | Python AMF | .357 | .160 | .221 | 49.9 | 1.54 | 25.5 | 13.5 |
| 97793 | v3.1.1 VMD proxy | .544 | .276 | .366 | 46.7 | 1.14 | 5.4 | 1.0 |
| 97793 | C1c mmHRV | .434 | .212 | .284 | 48.0 | 1.54 | 38.0 | 17.2 |
| 9779 | project bandpass | .333 | .231 | .273 | 38.6 | .32 | 27.6 | 14.3 |
| 9779 | Python AMF | .268 | .182 | .217 | 50.7 | .63 | 38.2 | 20.7 |
| 9779 | v3.1.1 VMD proxy | .302 | .215 | .251 | 40.1 | .68 | 51.4 | 25.0 |
| 9779 | C1c mmHRV | .316 | .207 | .250 | 30.9 | .49 | 25.0 | 12.4 |
| 97795 | project bandpass | .192 | .127 | .153 | 57.1 | .15 | 25.9 | 27.7 |
| 97795 | Python AMF | .281 | .145 | .192 | 31.2 | .03 | 30.1 | 8.2 |
| 97795 | v3.1.1 VMD proxy | .176 | .136 | .154 | 47.5 | .05 | 10.3 | 4.2 |
| 97795 | C1c mmHRV | .250 | .182 | .211 | 52.5 | 1.27 | 8.0 | 9.6 |

三场平均：C1c `F1=.248`、recall `.200`、IBI MAE `43.8 ms`；最佳对照为 v3.1.1 VMD proxy，`F1=.257`、recall `.209`、IBI MAE `44.8 ms`。C1c 没有稳定改善，且 HR 绝对误差平均更高（1.10 bpm vs 对照约 0.62–0.73 bpm）。

## 诊断结论

三场均成功完成 raw ADC→range FFT→phase→VMD。选中的 bin 分别为 97793: ch0/bin15，9779: ch4/bin12，97795: ch3/bin24；VMD 均未回退，均选出 0.8–1.43 Hz 范围内的心跳候选模态。算法链可以运行，但逐搏性能没有达到“从约 .15 级别跃升到 .5 以上”之类的量级改善。

因此裁决为：保留 C1c 作为可复现的 single-target adaptation 研究产物，暂不扩展到 48 session，不把它写成 mmHRV 已验证，也不继续在该 pilot 上调 K/alpha/峰值阈值。下一步如继续 HRV，应另行选择明确的后端逐搏分段方法或先解决 raw target/phase 信号层问题。

## 限制

本次正式 RS6240 raw ADC 没有可直接运行的官方 MATLAB VitalSense RWAMF 对应输入，因此三条“同输入对照”是本地 C1b-compatible project bandpass、Python AMF 和 v3.1.1 VMD proxy；官方 MATLAB VS_DATASET 结果不能与 RS6240 raw ADC 直接并列为同一输入基准。论文中 mmHRV 的 K/alpha、峰值阈值等参数在本地材料中不能唯一恢复，本轮采用冻结的保守 adapter 参数并已记录。


