# C1d Radar-Beat backend-only pilot

更新日期：2026-08-26

## 最终状态

`C1D_NO_MATERIAL_IMPROVEMENT_STOP_HRV`

`C1D_BLOCKED_MISSING_WAVEFORM_ASSET` 已解除。C1c 前端确定性重放通过，缺失的中间波形资产已经补存；随后执行的 C1d 后端试验未达到预先冻结的成功门槛。因此，在当前比赛周期内停止继续投入毫米波逐搏 HRV 算法开发。该结论不等同于“毫米波 HRV 在一般意义上不可能”，而是针对当前数据、当前比赛周期和已冻结验证范围的停止决策。

## C1c 确定性重放

仅重读三个已冻结 session 的前 6000 帧 raw ADC，严格复用原 C1c 的 channel/bin、range FFT、phase unwrap、VMD、normalization 和 local-peak 规则；没有使用 ECG 调整前端参数，也没有重新搜索 channel/bin。

固定选择为：

| session | channel | range bin | sampling rate |
|---|---:|---:|---:|
| 97793 | 0 | 15 | 100 Hz |
| 9779 | 4 | 12 | 100 Hz |
| 97795 | 3 | 24 | 100 Hz |

三场重放结果与原 `c1c_metrics_primary.csv` 中 `c1c_mmhrv_adaptive_vmd`、±75 ms 行逐字段一致，检查字段包括 precision、recall、F1、IBI MAE、HR error 和 radar beat count，差异均为 0。这里的结论是“过程级可复现”；由于旧 manifest 未记录完整输入哈希和依赖版本，不能扩大表述为 bit-level reproducibility。

补存资产：

- `97793/c1c_waveforms_replayed.npz`
- `9779/c1c_waveforms_replayed.npz`
- `97795/c1c_waveforms_replayed.npz`

每个文件至少包含 `time_s`、`sampling_rate_hz`、`selected_channel`、`selected_bin`、`selected_complex_slow_time`、`unwrapped_phase`、`heartbeat_component`、`normalized_heartbeat`、`local_peak_times_s` 和 `ecg_peak_times_s`。

## C1d 后端比较

C1d 只读取上述固定 waveform，不重新读取 raw ADC，不做 beamforming，不调 VMD，也不使用 ECG 构建 template 或优化 DP 参数。由于本地没有 Radar-Beat/RF-Heartbeat 的完整可复现实现和全部数值参数，本轮实现应准确称为 **Radar-Beat-style backend adapter**：个体化 heartbeat template、滑动归一化互相关和带间期约束的全局动态规划分段。相关公开方法见 [Radar-Beat](https://doi.org/10.1016/j.bspc.2023.105360) 和 [RF-Heartbeat 方法材料](https://pdfs.semanticscholar.org/f8e4/9dca0ed298e7adc92b2f28d7f8b94f0b5558.pdf)。这些来源支持方法方向，不证明本地 adapter 等同于论文原始实现。

同场 baseline waveform 没有作为独立持久资产保存，因此按预先约定的降级方案，完成了同一 C1c waveform 上 `原 local peak detector` 与 `global DP adapter` 的配对比较。评价固定使用 delay = −18 ms、±75 ms 主容差，并保留 ±50/100/150 ms 敏感性结果。

### ±75 ms 主结果

| session | 原 local peak F1 | DP F1 | F1 差值 | 原 IBI MAE (ms) | DP IBI MAE (ms) | IBI 差值 (ms) | 结果 |
|---|---:|---:|---:|---:|---:|---:|---|
| 97793 | 0.2845 | 0.2250 | −0.0595 | 47.95 | 56.73 | +8.78 | 未改善 |
| 9779 | 0.2500 | 0.2037 | −0.0463 | 30.94 | 39.86 | +8.92 | 未改善 |
| 97795 | 0.2105 | 0.1635 | −0.0471 | 52.47 | 63.51 | +11.03 | 未改善 |
| 平均 | 0.2483 | 0.1974 | **−0.0509** | 43.79 | 53.37 | **+9.58** | **失败** |

冻结成功门槛为：平均 F1 至少提高 0.10、至少 2/3 session 同方向明显改善、IBI MAE 不明显恶化。本轮实际为 0/3 session 改善，平均 F1 下降 0.0509，且三场 IBI MAE 均恶化，未达到任何核心门槛。

## 产物

- 重放脚本：`D:/Project/厚粲杯/08_算法/scripts/replay_c1c_assets.py`
- C1d 脚本：`D:/Project/厚粲杯/08_算法/scripts/run_c1d_radarbeat_backend_pilot.py`
- 重放长表：`D:/Project/厚粲杯/11_数据/derived/c1c_mmhrv_pilot_v1/c1c_replay_metrics_long.csv`
- C1d 主结果：`D:/Project/厚粲杯/11_数据/derived/c1c_mmhrv_pilot_v1/c1d_metrics_primary.csv`
- C1d 全容差结果：`D:/Project/厚粲杯/11_数据/derived/c1c_mmhrv_pilot_v1/c1d_metrics_long.csv`
- 裁决 JSON：`D:/Project/厚粲杯/11_数据/derived/c1c_mmhrv_pilot_v1/c1d_decision.json`
- 每场诊断图：各 session 目录下的 `c1d_template_similarity_dp.png`

原始数据未修改、未移动、未重命名；本轮没有扩展到 48 session。


