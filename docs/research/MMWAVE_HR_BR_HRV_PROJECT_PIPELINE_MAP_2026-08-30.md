# FocusWave mmWave HR / BR / HRV 项目代码映射（2026-08-30）

状态：`PARTIAL`。这是代码与证据边界图，不是 HR、BR 或 HRV 生理有效性通过声明。

## 一句话结论

当前项目已经具备“同一上游、分 BR 与 cardiac 两支”的代码结构：

`complex range-domain cube → target/bin/channel → phase/displacement → BR branch + cardiac branch`

其中 cardiac branch 已经同时产生 `heart_peaks`、time-domain HR 和 frequency-domain HR。理论上，可靠的 `heart_peaks → IBI` 就能同时给出 beat-derived HR 和后续 HRV；但本轮固定 75 ms 一对一 ECG 对齐的 pooled sensitivity=`0.170243`、precision=`0.210619`，因此 HRV 仍为 `BLOCKED`，没有计算正式 RMSSD/SDNN。

## 实际代码映射

| 共享/分支步骤 | 实际项目代码 | 已有输出/证据 | 当前状态 |
|---|---|---|---|
| 共享输入 | `scripts/process_vital_signs_v3_1_1.py:1103-1128` 的 `_load_chunk()` / `_iter_selected_chunks()` | 读取 NPZ 中 `tx*` 组成的 8-channel complex range-domain DataCube；不再做第二次 Range FFT | `KEEP`；输入语义已审计 |
| target/bin/channel | `scripts/process_vital_signs_v3_1_1.py:1146-1233`、`:2803-2900` | 平均功率、phase stability、HR/BR band score 生成候选并选 channel/bin；历史 gate/target 与 previous-anchor 的恢复证据在 `docs/results/2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION/` | `RESTORE_EXISTING`；323 控制集 residual 仍不能完全拆成 target/bin/channel/selector/continuity |
| phase/displacement | `scripts/process_vital_signs_v3_1_1.py:268-273` 的 `extract_displacement()` / `_sos_bandpass()` | 由复数 range-domain 点取 phase/unwrapped displacement，再进入呼吸和心脏带通 | `KEEP`；不主张独立因果收益 |
| BR respiration branch | `scripts/process_vital_signs_v3_1_1.py:528-679` 的 `estimate_breath_rate_consensus()`、`_select_breath_candidate()` | 低频 `0.10-0.50 Hz` 呼吸波形、time/frequency consensus、`breath_peaks`；JSON 的 `breath_rate` 是现有 supporting 输出 | `SUPPORTING/HOLD`；本轮未重算 BR |
| cardiac separation | `scripts/process_vital_signs_v3_1_1.py:1296-1371` 的 `separate_vmd_heart_windowed()`，以及 `:2261-2275` 的 heart bandpass/VMD 分支 | 生成 `heartbeat`；现有 historical/full-record 输出包含该波形 | `RESTORE_EXISTING` / bundled evidence；不新增 VMD/静态抑制路线 |
| heartbeat peak timestamps | `scripts/process_vital_signs_v3_1_1.py:1244-1293` 的 `detect_peaks_heart_lo()`；`save_result()` 在 `:1442-1459` 将 frame-index 数组写入 NPZ `heart_peaks` | 三场 full-record existing NPZ 均可复用：`97793/9779/97795` 的 peak 数分别为 `1991/1967/1811`；本轮没有触发 `REUSE_REJECTION_REASON` | `REUSED`；这是本轮 beat-level lane 的关键可用中间结果 |
| HR from same beat sequence | `scripts/process_vital_signs_v3_1_1.py:686-710` 的 `_robust_time_bpm()`、`:2277-2294` 与 `:2407-2416` | 现有 producer 从 peak intervals 产生 time HR；本轮另用 paired matched peaks 计算 beat-derived mean HR | `DIAGNOSTIC_ONLY`；与 existing same-window spectral HR 的一致性未通过 |
| independent spectral HR QC | `scripts/process_vital_signs_v3_1_1.py:727-775` 的 `_spectral_candidates()` / `_select_spectral_bpm()`；`:1236-1242` 的 periodogram | 现有 `heartbeat` 同一 60 s 子窗重新调用 producer 的 periodogram 入口，只作 consistency check，不作第二套正式 cardiac pipeline | `QC/FALLBACK`；不能替代 beat validation |
| historical correction/consensus | `scripts/process_vital_signs_v3_1_1.py:1886-2015` 的 `_window_hr_candidates()` / `_heart_segment_reference_correction()`；`:2092-...` 的 window consensus | 已在同一 323 控制集上有 previous-anchor、time/frequency fusion 和 historical chain replay | `RESTORE_EXISTING`；独立阶段贡献仍 `UNPROVEN/BUNDLED_ONLY` |
| IBI for future HRV | 现有 peak-to-IBI 逻辑位于 `:689-710`、`:1896-1901`、`:2430-2443`；新验证 adapter 为 `scripts/maintenance/run_mmwave_beat_level_validation_20260830.py` | existing outputs 有 IBI-shaped/HRV fields，但过去没有 radar peak ↔ ECG R-peak 一对一 evidence；新 adapter 仅计算 matched beat/IBI validity，不计算 HRV 指标 | `BLOCKED` until beat-level agreement is adequate |
| formal HRV outputs | `scripts/process_vital_signs_v3_1_1.py:2430-2443` 可写出历史 `hrv` 字段 | 历史 JSON 的 `hrv` 字段不等于验证；本轮明确 `formal_hrv_metrics_calculated=false`，不读取/重算 RMSSD、SDNN、LF/HF | `EXCLUDE/BLOCKED` |

## 本轮实际验证链

```text
existing full-record NPZ heart_peaks (frame index)
  → authoritative DLL timestamp row
  → complete formal block + 30 s guard
  → one deterministic 60 s window
  → existing block-local ECG affine clock mapping
  → raw ECG R-peaks (gold-standard fixed parameters)
  → one-to-one matching (primary ±75 ms; sensitivity ±50/100/150 ms)
  → matched beat counts / timing / paired IBI / beat-derived HR
  → same-window existing periodogram HR consistency check
```

窗口选择不是历史 `_selection_60s` 文件的 raw frame 0。那些文件从各场 raw frame 0 开始，而 97793/9779/97795 的 formal block 1 分别从 frame 23596/26012/19000 附近开始；因此直接拿 `_selection_60s` 与 ECG 对齐会混入 block 之前的记录。本轮只使用 existing full-record output 中的 complete block 内 60 s 子窗。

## 证据和决策

- A lane 已冻结既有 `COMPLETE ∩ ECG_VALID=323` 与 `24.902438 → 13.276285 → 8.319342` 的恢复链；residual `55 wrong + 120 nearby` 的剩余 locus 仅按已有 provenance 记录，不能强行归因。#25 仍 `WAIT_ON_SELECTOR_VALIDITY`。
- B lane 复用了 existing `heart_peaks`，8 个 complete blocks 各取 1 个 60 s 子窗。主容差 pooled `119/699` ECG R-peaks 匹配、雷达峰总数 `565`，sensitivity=`0.170243`、precision=`0.210619`；±150 ms 也只有 sensitivity=`0.359084`、precision=`0.444248`。
- 由于 matched subset 很小，paired IBI 的相关系数不能单独作为通过证据；本轮不以条件性 timing/IBI 数字反向放宽 gate。
- BR 只保留现有 full-record `breath_rate` supporting metadata；没有把 BR 作为每窗 harmonic diagnostic 输入，也没有新增 BR 算法。
- HRV 继续 `BLOCKED`；只有在另行预定义并通过 beat-level gate 后，才允许测试 60 s RMSSD 或 300 s reference。`20 s` 不被继承为 HRV 主窗。

## 输出边界

- committed aggregate：`docs/results/2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE/`
- local-only per-window rows：`D:\Project\厚粲杯\11_数据\derived\mmwave_beat_level_validation_20260830\`
- 原始 `.acq`、NPZ、ECG 波形和 participant-level rows 不进入 Git。
