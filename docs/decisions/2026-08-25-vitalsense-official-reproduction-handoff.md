# C1B official VitalSense reproduction handoff

状态：`OFFICIAL_REPRO_COMPLETE`

本轮已从 `OFFICIAL_REPRO_TECHNICAL_BLOCKER` 继续完成官方 MATLAB 复现，不重复 clone、下载数据、等价性审计、ECG R 峰设计或匹配协议设计。

## 固定来源与环境

- 官方仓库：`D:\Project\厚粲杯\08_算法_worktrees\gpt-codex-handoff-20260825\external\vendor\VitalSense2024`
- 官方 commit：`d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6`
- MATLAB：`D:\Program Files\MATLAB\R2024b\bin\matlab.exe`
- 版本：MATLAB R2024b Update 1，Signal Processing Toolbox R2024b
- 官方源代码未修改。

## 官方 sample

官方 sample `C_chest_normal_withECG.mat` 已通过独立 adapter 在 MATLAB 命令行完成。日志和摘要位于：

`D:\Project\厚粲杯\11_数据\derived\vitalsense_official_reproduction_v1\official_sample_matlab_console.log`

已确认 HRestim、官方 pulse-template/RWAMF 路线和 MATLAB `findpeaks` 均实际调用。sample 输出 36 个雷达 beat，HR 为 89.70 bpm（FFT）、90.00 bpm（峰计数）和 92.6576 bpm（IBI）。

## 24 人正式批处理

VS01–VS24 × Resting/Apnea 共 48 个 session 已完成，MATLAB 状态为 `OFFICIAL_BATCH_COMPLETE complete=48 errors=0`。adapter 只负责输入字段、路径、非交互运行和结果导出，未修改官方算法源码。官方 beat 时间点、session 摘要和 MATLAB console 位于：

`D:\Project\厚粲杯\11_数据\derived\vitalsense_official_reproduction_v1\`

## C1b 评价

官方 beat 时间点已送入既有 C1b ECG evaluator，与 `project_bandpass_peak` 和 `python_vitalsense_amf` 使用同一 ECG Lead II、500 Hz、单调一对一匹配、±50/75/100/150 ms 容差，±75 ms 为主容差。未按 subject/session 单独调 delay。

官方路线在 ±75 ms 的平均总体 recall 约为 .156，project bandpass peak 约为 .178，Python AMF 约为 .134；平均 HR 绝对误差约为 .60、.62 和 .54 bpm。官方路线没有在逐搏召回或 HR 误差上显示明确优势。±150 ms 时官方平均 recall 约为 .31，仍不足以宣称逐搏、IBI 或 HRV 已验证。

官方延迟诊断在 VS01 Resting 的主容差下没有可用匹配，因此不能把 0 ms 当作估计结果；正式比较保留冻结的 C1b 固定 delay，并把该事实记录为 `official_delay_not_estimable`。

## 解释边界

本轮状态是 `OFFICIAL_REPRO_COMPLETE`，表示官方 MATLAB 路线和 48 session benchmark 已完成，不表示毫米波 HRV 已被验证。结果最接近 CASE B：平均 HR 可以得到合理估计，但严格逐搏覆盖较低；放宽时间容差会改善 recall，但不足以消除 beat-level 失败。RMSSD/SDNN 仅作为诊断输出，不得写成 HRV 有效性结论。

原始 MAT、逐搏大表和完整派生结果仅保留在本地，不提交 GitHub。GitHub 仅提交 adapter、评估脚本、固定 overlay 脚本、manifest、报告和总账更新。
