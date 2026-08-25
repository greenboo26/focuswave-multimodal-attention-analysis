# C1 Alignment Protocol Repair

状态：`C1_ALIGNMENT_NOT_PRIMARY_CAUSE_STOP_HRV_CONFIRMED`

本轮只修复验证协议，不重新提取 raw ADC，不修改 C1c/C1d detector、VMD、range/bin、waveform 或 ECG R 峰检测。

## 关键结论

- 固定 `-18 ms` 与全段 oracle lag 分开报告；oracle 只是后验上界。
- 设备同步只通过 `.acq` 数字 marker、`events.csv` 和雷达帧 Unix ms 审计，不用心搏 F1 定义 device offset。
- IBI 使用固定单调序列对齐，允许 missed/extra beat，不做任意时间伸缩；因此不依赖常数 lag。
- 半段 held-out 评估把 lag 选择与评价分离。

汇总：mean fixed F1 = `0.223`，mean oracle F1 = `0.362`，mean held-out F1 = `0.314`；lag-invariant aligned IBI MAE mean = `93.3 ms`。这些结果不足以称为 HRV 已验证。

## 概念分离

`device_clock_offset` 仅指独立 marker 映射；`electromechanical_delay` 指 ECG 电活动到机械事件的生理延迟；`detector_landmark_offset` 指局部峰或 DP 选取的机械形态点差异；`beat_matching_residual` 指固定评价规则下剩余的逐搏时间误差。它们不再合并称为 ECG–radar delay。

## 证据文件

- `c1_device_sync_audit.json`
- `c1_alignment_fixed_vs_oracle.csv`
- `c1_alignment_holdout_metrics.csv`
- `c1_alignment_lag_invariant_ibi.csv`
- `c1_detector_landmark_residuals.csv`

正式结论边界：本轮没有证明 RS6240 无法测 HRV；仅表明当前比赛周期内，逐搏 IBI/HRV 仍未获得可靠验证依据。
