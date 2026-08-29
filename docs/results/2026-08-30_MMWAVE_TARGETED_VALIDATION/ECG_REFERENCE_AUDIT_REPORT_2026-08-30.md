# Historical ECG reference-chain audit — 2026-08-30

状态：`PARTIAL / HISTORICAL_ECG_CHAIN_AUDITED_CURRENT_MMWAVE_COMPARISON_QUALIFIED`

本审计只替换 ECG/BIOPAC 参考链，毫米波端固定读取既有 block-local targeted rerun 的 `local_hr_freq_bpm`；没有重新选择 bin/channel，也没有运行正式全量批处理。原始 `.acq`、NPZ、实验程序、producer、portable V2 与 `Attention-Analysis@codex/formal-analysis-v2-portable` 均未修改。

## 1. 结论

- 已确认历史最佳 HR 数值是 5-session/99-valid-window 的 corrected-distance calibration：MAE `3.7772146 bpm`；其 ECG 参考链可追溯到 `scripts/analyze_acq_reference.py`，但毫米波端同时使用了旧/更正距离门，不能当作本轮 3-session、20-s block 结果。
- 历史 `4.5901918 bpm` 是同一 5-session/99-window 链的旧 `0.08 m/bin` gate；该历史表可重现。`3.7772146 bpm` 是只改变毫米波 `0.037 m/bin` gate 后的 corrected-gate estimate，不是 ECG detector 单独带来的改善。
- 三场固定窗口重放使用同一 `local_hr_freq_bpm` 毫米波值。历史 metadata-zero ECG、当前 per-block marker-affine ECG、以及 minimal-difference arm 的 HR reference 结果均已逐窗写入 `ECG_REFERENCE_PIPELINE_COMPARISON.csv`。
- 因历史与当前 detector 的核心 ECG 参数相同（4th-order 5–35 Hz、adaptive prominence、0.45-s minimum distance、0.30–2.00-s IBI），本次差异主要来自 alignment/window/cohort/mmWave-side，而不是已发现的 R-peak detector 改写。
- 最终状态保持 `PARTIAL`：历史链已解释到可复现的脚本和结果层，但当前 `.acq` 文件的 `97795` 目录内文件名为 `97995.acq`，只能确认目录/通道/marker/采样长度的一致性，不能从文件名本身证明被试 ID；同时 mmWave timestamp gaps 和历史/当前毫米波估计器不同，不能宣称一个统一的 cross-era MAE。

## 2. Fixed replay summary

| ECG arm | n | MAE vs fixed mmWave HR (bpm) | median absolute error | bias (mmWave−ECG) |
|---|---:|---:|---:|---:|
| historical | 335 | 24.912767 | 27.8 | -24.449681 |
| current | 335 | 24.880549 | 27.917 | -24.447158 |
| minimal_difference | 335 | 24.912767 | 27.8 | -24.449681 |

重放表中的 `historical` 与 `minimal_difference` 在本实现中使用同一 metadata-zero sample mapping；这是有意的 isolation arm，显示当前 ECG detector 相对历史 `analyze_acq_reference` detector 没有产生另一个独立结果。`current` 才使用本轮每个 block 的 physical-marker affine mapping。
逐窗比较显示 old→current ECG HR 在 255/335 窗发生数值变化，变化的中位绝对值为 0.15 bpm、最大绝对值为 3.3 bpm；current−old 的平均变化为 -0.002522 bpm。reference alignment 有可测但很小的逐窗影响，不能解释约 24.9 bpm 级别的毫米波误差。

## 3. Alignment audit

- OLD_ALIGNMENT：`(event_unix_ms − earliest_marker_created_at) × fs/1000`，对应历史 `analyze_acq_reference.py` 的 acquisition-zero 规则。
- CURRENT_ALIGNMENT：每个 block 单独用 `events.csv` 的 program marker 与 BIOPAC 8-bit digital pulse 做 affine fit；不跨 rest、坐姿调整或 block boundary 借用 mapping。
- 本次固定重放读取 335 个已有 mmWave comparison rows；每个 block 重新查找对应 `.acq` ECG 和 block mapping。
- 三场均为 2000 Hz，ECG 通道为 `ECG, X, RSPEC-R`，marker 通道为 `Digital (STP Input 0..7)`。
- `97795` 使用 `D:\acq_mmwave_data\sub-97795_\97995.acq`；没有重命名或复制它。审计分类为 `directory_subject_matches_basename_typo`，不是把文件名错误升级为生理数据错配。
- mmWave tick gap 统计和 ECG marker mismatch 仍保留在既有 `ecg_alignment_audit.csv`；它们限制双机时间轴的最终闭合，但不改变本次 ECG reference replay 的 block-local reset 规则。

## 4. Historical result lineage and decision

`ECG_SCRIPT_LINEAGE.csv` 区分了 canonical `master` 历史脚本、当前 `main` 同名副本、alternate `gold_standard_qa`/`validate_gold_anchor`、formal reanalysis reference、FocusWave acquisition marker source，以及 Attention-Analysis 的无相关脚本盘点。

历史 `3.777` 应保留为：`corrected-distance calibration result, ECG reference chain reproducible, not transferable to current block-local run`。历史 `4.590` 应保留为：`old-distance-gate historical reproduction`。当前 `24.885` 应保留为：`current 20-s block-local diagnostic MAE, qualified/provisional, not formal HR validity`。

## 5. Scope and next gate

HR/BR 继续 `HOLD`，HRV 继续 `BLOCKED`；没有运行 #16、C2B/C2C、HRV 新算法或全量 formal batch。下一步若要闭合，需要在同一冻结毫米波输出和同一 block/window contract 下，取得可证明等价的历史/当前 reference mapping，或明确重新定义一套只用于当前 block 的 reference benchmark；本审计不擅自选择其中之一。

## 6. Files

- `ECG_SCRIPT_LINEAGE.csv` — script/branch/commit and parameter lineage
- `ECG_HISTORICAL_RESULT_PROVENANCE.csv` — historical MAE denominator and comparability
- `ECG_REFERENCE_PIPELINE_COMPARISON.csv` — fixed mmWave, old/current/minimal ECG per-window replay
- `ECG_REFERENCE_PIPELINE_SUMMARY.csv` — descriptive replay metrics
- `ECG_REFERENCE_ALIGNMENT_AUDIT.csv` — OLD_ALIGNMENT vs CURRENT_ALIGNMENT and `.acq` mapping audit
- `ECG_REFERENCE_AUDIT_MANIFEST.json` — inputs, exclusions, hashes and status
