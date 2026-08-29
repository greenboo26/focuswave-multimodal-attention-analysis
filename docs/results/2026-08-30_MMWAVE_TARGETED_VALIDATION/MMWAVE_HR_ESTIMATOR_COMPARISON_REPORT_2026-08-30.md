# mmWave HR estimator same-window audit — 2026-08-30

状态：`PARTIAL`

本轮固定既有 335 个 complete formal-block、20 s 窗口及其 block-affine ECG HR；毫米波端对同一 raw NPZ window 重新计算 current independent/current block-local，并恢复历史 corrected-gate 的固定 target 后做 20 s adaptation。历史原定义的 60 s arm 不被静默改成 20 s，标记为 `NOT_APPLICABLE_TO_20S`。

## 1. Direct answer

- 历史 `3.7772146 bpm` 的真实来源：`run_hr_course_99_corrected.py → process_vital_signs_v3_1_1.py`, 先用 6000-frame selection 选固定 heart channel/bin，再在全记录上运行 `bp_heart`；距离口径为 `0.037 m/bin`、物理 gate `0.30–1.50 m`。历史结果是 5 sessions / 99 valid 60 s HR-course windows。
- 严格历史 60 s estimator 在当前 20 s denominator 上为 `NOT_APPLICABLE_TO_20S`，没有伪造 HR。
- 当前 335-row comparison 的历史 20 s adaptation 与两种 current estimator 指标见下表；所有统计均为描述性，不对重叠窗口做推断性显著性结论。

| estimator | all-available n | common-window n (all four) | MAE | median AE | RMSE | bias | Pearson r | Spearman r |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| historical_original_hr_bpm | 0 | 0 | None | None | None | None | None | None |
| historical_20s_adapt_hr_bpm | 335 | 0 | 14.748328 | 14.348 | 18.551216 | -12.794734 | 0.255126 | 0.243843 |
| current_independent_hr_bpm | 335 | 0 | 25.958119 | 28.84 | 28.390694 | -25.664322 | 0.016323 | -0.013683 |
| current_block_local_hr_bpm | 335 | 0 | 24.884913 | 27.87 | 27.675448 | -24.454472 | 0.008856 | -0.063346 |

## 2. Interpretation case

当前结果属于 `CASE B + CASE D` 的组合，而不是单独 CASE E：严格历史 60 s 不能在当前 20 s window 中直接成立；20 s adaptation 若接近 current，说明短窗/当前 cohort/当前 raw target condition 是重要差异。历史 3.777 还依赖 corrected physical gate、固定 target 和历史 60 s/QC denominator，因此不能据此判定 current pipeline regression。只有在同一 20 s 语义下 historical adaptation 明显优于 current、且 coverage/QC 等价时，才可升级为 regression candidate。

## 3. Target/bin/channel

- 历史 corrected target 使用每个 session 的 selection artifact 固定目标：`97793 ch4/bin9 (0.333 m)`、`9779 ch5/bin19 (0.703 m)`、`97795 ch7/bin25 (0.925 m)`。
- 当前 independent 与 block-local 的每窗 bin/channel、score、validity、missing reason 已逐行保存；当前 selector 的 independent path 不施加物理 range gate，不能把 `0.037 m/bin` 当作已经改变当前 selection。
- `MMWAVE_HR_ESTIMATOR_LINEAGE.csv` 记录了 0.08/0.037、gate、target、phase、filter、periodogram、peak、harmonic、window、QC 与历史结果的具体代码入口。

## 4. Timestamp semantics

- A（event tick Unix ms ↔ nearest mmWave timestamp）共 3491 rows，其中 `|delta|>100 ms` 为 730；这就是旧统计中的 730 类近邻差异，属于 event-to-mmWave nearest residual。它不是 frame gap。
- B（相邻 mmWave timestamp interval）共 459126 rows：median=7.000 ms，p95=20.000 ms，p99=31.000 ms，max=6495 ms；>20 ms=20682，>50 ms=840，>100 ms=457，>500 ms=457。
- 因此只有 B 的 >100 ms 才能称为真实相邻帧间隔；A 的 730 不能称为 dropout/frame gap。详细 CSV 保存在本地 derived 目录，manifest 记录 row count 与 SHA-256。

## 5. Decision

- 当前没有足够证据报告 `HISTORICAL_PIPELINE_STILL_GOOD_ON_CURRENT_WINDOWS`，因为 strict 60 s arm 不适用，20 s adaptation 不是历史原始语义。
- 当前不报告 `CURRENT_PIPELINE_REGRESSION`；历史与当前在 target/gate/window/cohort/QC 上尚未完全等价。
- 是否需要修当前 HR pipeline：本轮证据支持继续把 HR 保持 `HOLD` 并进入针对 target selection / short-window estimator 的修复设计，但不授权直接改 producer。唯一推荐动作是：在保持 335-row contract 和 ECG alignment 不变的前提下，先完成一个预注册的 `0.037 m/bin + block-local target + 20 s` estimator sensitivity，明确 target/gate/coverage 后再决定是否修复。

## 6. Artifacts

- `MMWAVE_HR_ESTIMATOR_LINEAGE.csv`
- `MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv`
- `MMWAVE_HR_ESTIMATOR_SUMMARY.csv`
- `MMWAVE_HR_ESTIMATOR_COMPARISON_REPORT_2026-08-30.md`
- `MMWAVE_TIMESTAMP_SEMANTICS_AUDIT_2026-08-30.md`
- local `event_tick_to_mmwave_nearest_audit.csv` and `mmwave_frame_interval_audit.csv`

## 7. Pairwise same-denominator comparisons

Each row uses only windows where both estimators and ECG are available; `delta` is absolute-error(method_a) minus absolute-error(method_b).

| method_a | method_b | n | MAE a | MAE b | mean delta | median delta | a better | tie | b better |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| historical_original_hr_bpm | historical_20s_adapt_hr_bpm | 0 | None | None | None | None | 0 | 0 | 0 |
| historical_original_hr_bpm | current_independent_hr_bpm | 0 | None | None | None | None | 0 | 0 | 0 |
| historical_original_hr_bpm | current_block_local_hr_bpm | 0 | None | None | None | None | 0 | 0 | 0 |
| historical_20s_adapt_hr_bpm | current_independent_hr_bpm | 335 | 14.748328 | 25.958119 | -11.209791 | -11.898 | 242 | 0 | 93 |
| historical_20s_adapt_hr_bpm | current_block_local_hr_bpm | 335 | 14.748328 | 24.884913 | -10.136585 | -9.865 | 231 | 0 | 104 |
| current_independent_hr_bpm | current_block_local_hr_bpm | 335 | 25.958119 | 24.884913 | 1.073206 | 0.0 | 73 | 163 | 99 |

## 8. Target/reproduction diagnostics

- `97793_block_local`: `{'n': 111, 'exact_bin_channel_n': 4, 'bin_diff_median': 1.0, 'bin_diff_mean': 4.2792792792792795, 'channel_diff_median': 2.0, 'channel_diff_mean': 1.990990990990991, 'outside_historical_gate_n': 44}`
- `97793_independent`: `{'n': 111, 'exact_bin_channel_n': 3, 'bin_diff_median': 2.0, 'bin_diff_mean': 50.13513513513514, 'channel_diff_median': 2.0, 'channel_diff_mean': 2.009009009009009, 'outside_historical_gate_n': 51}`
- `97795_block_local`: `{'n': 112, 'exact_bin_channel_n': 0, 'bin_diff_median': 18.0, 'bin_diff_mean': 56.00892857142857, 'channel_diff_median': 3.0, 'channel_diff_mean': 3.2767857142857144, 'outside_historical_gate_n': 71}`
- `97795_independent`: `{'n': 112, 'exact_bin_channel_n': 0, 'bin_diff_median': 18.0, 'bin_diff_mean': 45.794642857142854, 'channel_diff_median': 4.0, 'channel_diff_mean': 4.0, 'outside_historical_gate_n': 85}`
- `9779_block_local`: `{'n': 112, 'exact_bin_channel_n': 0, 'bin_diff_median': 10.0, 'bin_diff_mean': 17.732142857142858, 'channel_diff_median': 2.0, 'channel_diff_mean': 2.625, 'outside_historical_gate_n': 39}`
- `9779_independent`: `{'n': 112, 'exact_bin_channel_n': 1, 'bin_diff_median': 10.0, 'bin_diff_mean': 61.392857142857146, 'channel_diff_median': 2.0, 'channel_diff_mean': 2.419642857142857, 'outside_historical_gate_n': 50}`
- Frozen prior current-row reproduction: `{"current_independent_hr_bpm": {"n_compared": 335, "n_exact_at_1e-9": 335, "max_abs_delta_bpm": 0.0}, "current_block_local_hr_bpm": {"n_compared": 335, "n_exact_at_1e-9": 335, "max_abs_delta_bpm": 0.0}}`
