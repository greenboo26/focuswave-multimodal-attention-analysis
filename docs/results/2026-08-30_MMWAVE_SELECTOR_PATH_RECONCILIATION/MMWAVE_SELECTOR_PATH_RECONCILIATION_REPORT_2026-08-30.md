# mmWave selector-path reconciliation — 2026-08-30

状态：`PARTIAL / SELECTOR_PATH_REPLAY_COMPLETE_LOCALIZATION_EVIDENCE_LIMITED`

## 执行结果

在冻结 #24 的 335 个窗口上，原样复用 canonical `process_vital_signs_v3_1_1.py` 的 `_select_spectral_bpm()`、`detect_peaks_heart_lo()`、previous-BPM anchor、time/frequency fusion 和 harmonic folding。每窗保留原有 `local_hr_bin/local_hr_channel`，没有重选 target，也没有将 ECG 传入选择器。

- ECG_VALID primary：`325`；其中可评估=`323`、coverage-limited=`2`；wrong-selection=`102`、nearby=`182`。
- 固定 targeted path 与 selector path 的 exact/nearby/not-recovered 计数见 `MMWAVE_SELECTOR_PATH_RECONCILIATION_SUMMARY.csv`。
- 逐窗 replay 表仅写入 `D:\Project\厚粲杯\11_数据\derived\mmwave_selector_path_reconciliation_20260830\MMWAVE_SELECTOR_PATH_REPLAY_335_WINDOWS_LOCAL_ONLY.csv`，不进入 Git。

## A1 结论

这次 replay 能回答“既有 spectral selector 在相同 target/bin/channel 上是否改变频率选择”，不能回答“selector 是否找到了真实胸腔 target”。在可评估的 323 个 ECG_VALID 窗中，sequential previous-anchor selector 对 102 个 wrong-selection 恢复 exact=`37`，对 182 个 nearby 恢复 exact=`17`；无 previous-anchor 对照见 summary，用于区分跨窗状态贡献。任何恢复都只是 supporting diagnostic，不是正式 HR 改善。

## A2 定位证据边界

当前持久化的 `target_continuity_diagnostic.csv` 只有 `15` 行，是每个 subject 前 6000 frame 的早期 sliding-window 诊断；它不是 335 个完整 block-local 窗口，且没有逐窗 candidate→bin/channel 对应关系。因此不能把 182 个 nearby cases 进一步声称为 same-target/different-candidate、neighbor-bin、neighbor-channel、target/channel switching 或 candidate-persistence 子类。现阶段这部分是 `BLOCKED_ON_PER_WINDOW_CANDIDATE_BIN_CHANNEL_PROVENANCE`，不是算法 blocker，也不授权新增 instrumentation 或新算法。

## 复用与边界

`REUSE_REJECTION_REASON`：既有 ECG_VALID spectral audit 没有持久化 canonical `_select_spectral_bpm()` 在 335 窗中的 replay 及 previous-anchor 输入；既有 continuity 诊断也没有与 335 窗逐窗对齐的 candidate-bin-channel provenance。因此只增加 downstream adapter 和 Git-safe aggregate，不修改 producer、raw、target、QC、gate、NIR/RGB、C2B/C2C 或 HR/HRV 状态。
