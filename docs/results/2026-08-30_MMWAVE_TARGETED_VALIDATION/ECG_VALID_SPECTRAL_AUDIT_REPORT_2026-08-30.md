# ECG_VALID retrospective spectral truth audit — 2026-08-30

状态：`PARTIAL / ECG_VALID_SPECTRAL_TRUTH_AUDIT_COMPLETE`

本轮对冻结的 335 个 complete formal-block、20 s mmWave windows 做 retrospective spectral audit。335 行是全窗口 diagnostic/supporting 分母，不是全量 ECG-valid。正式 ECG-valid 主分析严格沿用 #24：ECG_VALID=325、ECG_INVALID=10、UNRESOLVED=0；10 个 ECG_INVALID 只进入 supporting/diagnostic，不进入主分析。毫米波 target/bin/channel、selected HR peak 和 ARM0/1/2 均先由既有结果或既有 producer 路径确定；ECG/RSP 只在之后作为 oracle 做 truth label、nearest-candidate 和误差比较。逐窗 truth table 是 local-only，Git 只保留聚合证据。

## 1. Reuse gate and scope

复用：`mmwave_ecg_block_window_comparison.csv`、`MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv`、既有 `run_mmwave_targeted_validation_20260830.py` 的 `PartReader`/window contract、`process_vital_signs_v3_1_1.py` 的 bandpass/periodogram/peak/harmonic functions，以及既有 coverage audit。

`REUSE_REJECTION_REASON`：旧 ECG reference audit 只给出 ECG HR 与固定 mmWave HR 的逐窗比较；旧 harmonic A/B 只给出 15 个诊断样本，均没有为 335 窗统一持久化 top candidates、prominence、ECG-nearest rank 和选择错误分类。因此本轮只新增下游审计层，不改 producer、不改 target/peak selection、不重跑 C2B/C2C。

## 2. Truth classification

### 2.1 全窗口 diagnostic/supporting（n=335）

| class | n (%) |
|---|---:|
| absent_or_weak | 17 (5.07%) |
| insufficient_coverage_or_reference | 12 (3.58%) |
| nearby_target_bin_channel | 182 (54.33%) |
| true_peak_available_selected_target_but_wrong_selection | 102 (30.45%) |
| true_peak_selected_ecg_bin | 22 (6.57%) |

### 2.2 ECG_VALID primary（n=325）

| class | n (%) |
|---|---:|
| absent_or_weak | 17 (5.23%) |
| insufficient_coverage_or_reference | 2 (0.62%) |
| nearby_target_bin_channel | 182 (56.00%) |
| true_peak_available_selected_target_but_wrong_selection | 102 (31.38%) |
| true_peak_selected_ecg_bin | 22 (6.77%) |

其中 325 个 ECG_VALID 中有 `2` 个窗口标为 `SUPPORTING_COVERAGE_LIMIT`（coverage/reference 不足）；它们保留在 #24 的 ECG_VALID=325 分母中，但其 truth 结论只作 supporting/diagnostic caveat。它们不是 ECG_INVALID，不能再加到 10 个 ECG_INVALID 中。

- `true_peak_available_selected_target_but_wrong_selection`：同窗候选中存在落在 ECG 频率分辨率半 bin 内的 candidate，但既有 selected HR peak 不在该容差内。
- `true_peak_selected_ecg_bin`：selected peak 与 ECG 最近 candidate 均在半 bin容差内。
- `nearby_target_bin_channel`：candidate 或 selected 在预定义较宽邻近容差内，但未达到半 bin 级别。
- `absent_or_weak`：没有可用 candidate，或没有达到上述邻近分类；prominence 仍仅作诊断，不作 rejection。
- `insufficient_coverage_or_reference`：coverage audit 为 severe/missing，或 #24 ECG reference 非 ECG_VALID。

## 3. ARM0/1/2 same-window descriptive comparison

### 3.1 ECG_VALID primary (n=325; ARM1 estimator-valid=304)

| arm | selected n | estimator-valid n | coverage | MAE (bpm) | median AE (bpm) |
|---|---:|---:|---:|---:|---:|
| arm0 | 325 | 325 | 100.0% | 25.005 | 27.917331 |
| arm1 | 325 | 304 | 93.538462% | 21.906332 | 25.598185 |
| arm2 | 325 | 325 | 100.0% | 18.904008 | 20.607575 |

### 3.2 All-window diagnostic (selected n=335; ARM1 estimator-valid=314)

| arm | selected n | estimator-valid n | coverage | MAE (bpm) | median AE (bpm) |
|---|---:|---:|---:|---:|---:|
| arm0 | 335 | 335 | 100.0% | 24.847938 | 27.844895 |
| arm1 | 335 | 314 | 93.731343% | 21.77462 | 25.51482 |
| arm2 | 335 | 335 | 100.0% | 19.040268 | 20.807932 |

| subject | diagnostic n | ECG_VALID primary n | primary truth-class counts |
|---|---:|---:|---|
| 97793 | 111 | 106 | {'nearby_target_bin_channel': 62, 'true_peak_available_selected_target_but_wrong_selection': 34, 'true_peak_selected_ecg_bin': 5, 'absent_or_weak': 5} |
| 9779 | 112 | 107 | {'nearby_target_bin_channel': 59, 'true_peak_selected_ecg_bin': 15, 'true_peak_available_selected_target_but_wrong_selection': 24, 'absent_or_weak': 9} |
| 97795 | 112 | 112 | {'true_peak_available_selected_target_but_wrong_selection': 44, 'nearby_target_bin_channel': 61, 'absent_or_weak': 3, 'true_peak_selected_ecg_bin': 2, 'insufficient_coverage_or_reference': 2} |

| subject | block | diagnostic n | ECG_VALID primary n | primary truth-class counts |
|---|---|---:|---:|---|
| 97793 | block1 | 57 | 55 | {'nearby_target_bin_channel': 27, 'true_peak_available_selected_target_but_wrong_selection': 24, 'true_peak_selected_ecg_bin': 3, 'absent_or_weak': 1} |
| 97793 | block2 | 54 | 51 | {'true_peak_selected_ecg_bin': 2, 'true_peak_available_selected_target_but_wrong_selection': 10, 'nearby_target_bin_channel': 35, 'absent_or_weak': 4} |
| 9779 | block1 | 56 | 52 | {'nearby_target_bin_channel': 34, 'true_peak_selected_ecg_bin': 3, 'true_peak_available_selected_target_but_wrong_selection': 10, 'absent_or_weak': 5} |
| 9779 | block2 | 56 | 55 | {'true_peak_selected_ecg_bin': 12, 'nearby_target_bin_channel': 25, 'absent_or_weak': 4, 'true_peak_available_selected_target_but_wrong_selection': 14} |
| 97795 | block1 | 28 | 28 | {'true_peak_available_selected_target_but_wrong_selection': 8, 'nearby_target_bin_channel': 18, 'absent_or_weak': 2} |
| 97795 | block2 | 28 | 28 | {'nearby_target_bin_channel': 14, 'true_peak_available_selected_target_but_wrong_selection': 13, 'absent_or_weak': 1} |
| 97795 | block3 | 28 | 28 | {'nearby_target_bin_channel': 16, 'true_peak_available_selected_target_but_wrong_selection': 12} |
| 97795 | block4 | 28 | 28 | {'nearby_target_bin_channel': 13, 'true_peak_selected_ecg_bin': 2, 'true_peak_available_selected_target_but_wrong_selection': 11, 'insufficient_coverage_or_reference': 2} |

以上均为描述性 same-window 对照，不进行显著性检验或按 ECG 调峰。分层完整结果见 `ECG_VALID_SPECTRAL_ARM_SUMMARY.csv`。

验证：本脚本 `py_compile` 和实际运行通过；全仓 `pytest -q` 在既有 legacy `_cal_segment_test.py` 收集时因缺少 `process_vital_signs_v3_1_1` 导入而失败，未影响本定向审计运行。该残留记录在 manifest，不将其误报为本任务数据失败。

## 4. Harmonic guard audit

- Radar BR 的 2x/3x labels 和 external RSP 2x/3x labels 均写入 local-only truth table；它们不改变 selected peak。
- External RSP A 保留 raw selected peak，仅加 diagnostic label；B 调用现有 `respiration_harmonic_reject()` 计算“若启用”的 chosen/fallback/action，仍不回写 ARM0/1/2。
- 本轮 radar BR label 分布：`{'not_near_2x_3x_br': 256, 'near_3x_br': 73, 'near_2x_br': 6}`；external RSP A 分布：`{'not_near_2x_3x_br': 221, 'near_3x_br': 105, 'not_evaluable': 6, 'near_2x_br': 3}`；external RSP B would-reject=108/335。B 只是 A/B diagnostic，未实施 hard rejection。
- Internal producer harmonic guard 的真实代码行为是 `_select_spectral_bpm()` 对 `time_bpm`、`previous_bpm`、`reference_bpm` 做 half/double fold；它不读取 BR。当前固定 targeted validation 路径直接使用 `estimate_freq_periodogram()` + `detect_peaks_heart_lo()`，没有调用 `_select_spectral_bpm()`，因此本表的 internal guard 状态为 `not_applied_in_fixed_target_validation_path`。

## 5. ECG reference accounting

- #24 eligibility：ECG_VALID=325、ECG_INVALID=10、UNRESOLVED=0；invalid reason 分布：`{'abnormal_adjacent_ibi_fluctuation_gt20pct': 10}`。
- marker warning 分布：`{'marker_sequence_not_exact_but_block_affine_fit_available': 57, 'none': 278}`。marker warning 只表示 affine marker mapping 非 exact 但可用，不是额外 invalid reason。
- 10 个 ECG_INVALID 的 IBI/artifact 原因与 marker warning 不重复计数；本报告不把 warning 数与 invalid 数相加成新的失败总数。

## 6. Boundary

本轮结果是 `SUPPORTING` retrospective truth audit，不是 HR/BR validated physiology，也不是 producer change proposal。ECG 仍是 oracle；没有将 ECG 频率传入 target selection、candidate scoring、selected peak 或 ARM 计算。HR 保持 `HOLD`，HRV 保持 `BLOCKED`。

逐窗文件：`D:\Project\厚粲杯\11_数据\derived\ecg_valid_retrospective_spectral_truth_audit_20260830\ECG_VALID_RETROSPECTIVE_SPECTRAL_TRUTH_TABLE.csv`（local-only；335 行全窗口 diagnostic/supporting，ECG_VALID primary=325）
聚合文件：`ECG_VALID_SPECTRAL_AUDIT_MANIFEST.json`、`ECG_VALID_SPECTRAL_AUDIT_SUMMARY.csv`、`ECG_VALID_SPECTRAL_ARM_SUMMARY.csv`
