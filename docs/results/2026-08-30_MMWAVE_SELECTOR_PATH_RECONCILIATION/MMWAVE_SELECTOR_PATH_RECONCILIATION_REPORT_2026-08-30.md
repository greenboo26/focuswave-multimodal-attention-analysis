# mmWave selector-path reconciliation — 2026-08-30

状态：`PARTIAL / SELECTOR_PATH_REPLAY_AND_PATH_LOCALIZATION_COMPLETE_PHYSICAL_TARGET_UNRESOLVED`

## 执行结果

在冻结 #24 的 335 个窗口上，原样复用 canonical `process_vital_signs_v3_1_1.py` 的 `_select_spectral_bpm()`、`detect_peaks_heart_lo()`、previous-BPM anchor、time/frequency fusion 和 harmonic folding。每窗保留原有 `local_hr_bin/local_hr_channel`，没有重选 target，也没有将 ECG 传入选择器。

- ECG_VALID primary：`325`；其中可评估=`323`、coverage-limited=`2`；wrong-selection=`102`、nearby=`182`。
- 固定 targeted path 与 selector path 的 exact/nearby/not-recovered 计数见 `MMWAVE_SELECTOR_PATH_RECONCILIATION_SUMMARY.csv`。
- 逐窗 replay 表仅写入 `D:\Project\厚粲杯\11_数据\derived\mmwave_selector_path_reconciliation_20260830\MMWAVE_SELECTOR_PATH_REPLAY_335_WINDOWS_LOCAL_ONLY.csv`，不进入 Git。

## A1 结论

这次 replay 能回答“既有 spectral selector 在相同 target/bin/channel 上是否改变频率选择”，不能回答“selector 是否找到了真实胸腔 target”。在可评估的 323 个 ECG_VALID 窗中，sequential previous-anchor selector 对 102 个 wrong-selection 恢复 exact=`37`，对 182 个 nearby 恢复 exact=`17`；无 previous-anchor 对照见 summary，用于区分跨窗状态贡献。任何恢复都只是 supporting diagnostic，不是正式 HR 改善。

## A2 路径级定位

将现有 335 行 target-ablation 的 selected bin/channel 与本次 replay/truth 按 `(subject, window_id)` 对齐后，182 个 nearby 可得到路径级最小分类：neighbor-bin=`6`、neighbor-channel=`11`、target/channel switch=`164`、no alternative target change=`1`，合计 182；同一 fixed target 上 selector candidate 改变=`182`。逐窗分类表仅写入 `D:\Project\厚粲杯\11_数据\derived\mmwave_selector_path_reconciliation_20260830\MMWAVE_NEARBY_LOCALIZATION_SUBTYPES_182_WINDOWS_LOCAL_ONLY.csv`，聚合见 `MMWAVE_NEARBY_LOCALIZATION_SUBTYPES.csv`。

这解决的是“已有路径之间如何分流”的证据缺口，不是“真实 target 在哪里”。`target_continuity_diagnostic.csv` 仍只有 `15` 条早期 sliding-window 记录，未提供与 335 窗对齐的连续 candidate persistence/instability，因此该子类保持 `NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS`；独立 physical target truth 仍 `UNRESOLVED`。

## 复用与边界

`REUSE_REJECTION_REASON`：既有 ECG_VALID spectral audit 没有 canonical `_select_spectral_bpm()` 的 335 窗 previous-anchor replay；target ablation、truth 和 replay 也未合并为 182 nearby 的路径级 subtype aggregate。因此只扩展现有 downstream adapter 做窄 join，不修改 producer、raw、target、QC、gate、NIR/RGB、C2B/C2C 或 HR/HRV 状态。
