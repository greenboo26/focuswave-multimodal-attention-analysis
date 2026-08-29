# mmWave targeted validation rerun — 2026-08-30

状态：`PARTIAL / BLOCK_LOCAL_CONTINUITY_RETEST_COMPLETE_ECG_ALIGNMENT_LIMITS_RETAINED`

本轮严格按 `MMWAVE_BLOCK_RESET_AND_ECG_ALIGNMENT_CONTRACT_2026-08-30.md` 重做。只分析三场目标场次的完整程序 block；未运行 Issue #16、C2B/C2C、HRV 新算法、全量 formal batch，未修改 `kyandi233-dev/Attention-Analysis@codex/formal-analysis-v2-portable`，也未修改实验程序或原始数据。

## 1. 先行结论

- 完整可分析 block：8；不完整/未记录 block：4。不完整 block 不进入 continuity 或 ECG 误差汇总。
- 每个 block 第一分析窗均重置 local target/bin/channel state；所有 transition 都要求前后窗口属于同一 block；跨 rest、坐姿调整和 block 边界没有计入。
- 完整 block 的程序 marker 与 Biopac 数字输入脉冲配对状态为 7/8 个 block exact；tick 使用 101–110，并按 block 审计双机时间关系。tick 原始近邻差异包含采集空洞，不能直接当作时钟漂移。
- 唯一非 exact 的完整 block 为：97793/block1 (index 73: event 103 vs physical 102)；其余 marker 序列 exact。
- 结论等级：`PARTIAL / BLOCK_LOCAL_CONTINUITY_RETEST_COMPLETE_ECG_ALIGNMENT_LIMITS_RETAINED`。本轮支持修正旧证据边界，但不支持把 HR/BR 升级成正式 validated physiology；HRV 仍 BLOCKED。

## 2. 旧版 12 transitions 的撤销审计

旧版 3×5 个窗口产生 12 个 transition，但它们都来自每场 mmWave 起始后的前 6000 frames，而不是正式 Block 1/2/3/4：12 个 transition 中，0 个属于完整 formal block，0 个跨 rest/block boundary，12 个处于 baseline 或正式 block 之外。因此旧版 12/12 不再作为 block-local continuity failure 的证据。详表见 `legacy_12_transition_audit.csv`。

## 3. Block-local continuity

每个完整 block 从 start marker 后 5s 开始，以 20s 窗、10s 步进，至 end marker 前 5s 结束；窗口严格不跨 block。共 335 个窗口，327 个同 block 相邻 transition。

| 方法 | HR bin hop | HR channel switch | BR bin hop | BR channel switch | HR MAE vs ECG (n) | BR MAE vs RSP (n) |
|---|---:|---:|---:|---:|---:|---:|
| CURRENT_INDEPENDENT | 243/327 | 246/327 | 267/327 | 245/327 | 25.958 (335) | 3.723 (329) |
| BLOCK_LOCAL_CONTINUITY | 164/327 | 158/327 | 177/327 | 196/327 | 24.885 (335) | 4.237 (329) |

`BLOCK_LOCAL_CONTINUITY` 是诊断性 candidate：block start 初始化；随后在上一 local target 的 ±3 bin 邻域内按既定 score penalty 选择，邻域无候选时回退 current selector。它没有写入 producer。判断不以少跳 bin 单独通过，而以 ECG/RSP agreement 是否改善为主。

本轮 HR/BR 数值使用现有 producer 的 bandpass、periodogram/peak 定义作 bounded diagnostic estimator；没有运行 VMD、HRV 新算法或修改 producer。因此这些数值只用于本轮 candidate 对照，不构成正式特征发布。

## 4. ECG/BIOPAC alignment audit

每个 block 单独使用 `events.csv` 的 start/end marker 和 101–110 tick；ECG sample index 由该 block 的 event-unix-ms → Biopac digital-pulse sample affine fit 得到。mmWave 窗口则由同一 event unix 时间直接定位到 mmWave timestamp rows。

| 指标 | 结果 |
|---|---:|
| complete blocks | 8 |
| marker sequence exact | 7/8 |
| ECG fit residual p95 (median across blocks, ms) | 2.295799 |
| ECG fit residual max (max across blocks, ms) | 25.668139 |
| mmWave tick raw nearest delta p95 abs (median across blocks, ms) | 943.0 |
| mmWave tick raw nearest delta max abs (max across blocks, ms) | 2016.0 |
| mmWave tick affine-fit residual p95 (median across blocks, ms) | 6.132642 |
| mmWave tick affine-fit residual max (max across blocks, ms) | 96.310059 |
| mmWave tick gaps with |delta| > 100 ms (complete blocks) | 730 |

完整逐 block 结果见 `ecg_alignment_audit.csv`；不完整 block 只保留 marker/数据缺口记录，不用于 physiology comparison。ECG affine fit 的残差可用于样本映射质量；mmWave tick 的原始大差异同时受 timestamp 采集空洞影响，本轮不把它解释成已通过的双机漂移校正。

## 5. Interpretation and remaining boundary

- 旧 12-transition 证据已撤销为 block-local failure 证据；新 block-local 表才是当前可引用的 continuity evidence。
- 若 local candidate 减少 switch 但没有改善 ECG/RSP error，不能因“轨迹更平滑”而升级；若两者均无稳定改善，则 target continuity remains unresolved。
- 本轮不把 ECG/RSP 值写入最终 mmWave producer feature table；HR、BR/RR 保持 HOLD，HRV 保持 BLOCKED。

## 6. Evidence files

- `target_continuity_block_local.csv` — block-local current/local selection and within-block transitions
- `mmwave_ecg_block_window_comparison.csv` — each block window's mmWave HR/BR and ECG/RSP same-window comparison
- `ecg_alignment_audit.csv` — program marker, Biopac digital pulse, tick and drift audit
- `legacy_12_transition_audit.csv` — old 12-transition eligibility reclassification
- `run_manifest.json` — input, source, parameters, exclusions and SHA-256 record
