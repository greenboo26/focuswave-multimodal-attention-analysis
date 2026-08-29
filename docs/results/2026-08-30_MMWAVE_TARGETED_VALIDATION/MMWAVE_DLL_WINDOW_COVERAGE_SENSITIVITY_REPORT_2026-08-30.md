# mmWave DLL-time window coverage denominator sensitivity — 2026-08-30

状态：`PARTIAL / COVERAGE_SENSITIVITY_COMPLETE`

本轮只过滤已经完成的 DLL-time HR comparison rows；没有重跑或修改 HR estimator、target selector、gate、filter、ECG reference 或 primary all-window outputs。

## Frozen selections

- `S0_all_windows`: all 335 DLL-time windows, including severe coverage rows.
- `S1_exclude_severely_incomplete`: exclude only rows marked `SEVERELY_INCOMPLETE` by the pre-frozen timestamp-only contract.
- `S2_complete_only`: retain only rows marked `COMPLETE` by that same contract.
- The coverage contract was frozen before this sensitivity and does not use ECG HR, radar HR, abs error, or arm performance.
- Selection sizes: S0=`335`, S1=`333`, S2=`333`; S1 and S2 are identical here because no window is classified `PARTIAL`.

## Metrics

| selection | arm | selected n | valid n | coverage % | MAE | median AE | RMSE | bias | Pearson | Spearman |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S0_all_windows | arm0 | 335 | 334 | 99.701 | 25.791632 | 28.701 | 28.37093 | -25.47462 | 0.0119 | -0.071222 |
| S0_all_windows | arm1 | 335 | 323 | 96.418 | 22.189492 | 25.667 | 25.660192 | -21.688718 | 0.134016 | 0.113713 |
| S0_all_windows | arm2 | 335 | 334 | 99.701 | 19.18906 | 21.039 | 22.708948 | -17.800629 | 0.138025 | 0.126511 |
| S1_exclude_severely_incomplete | arm0 | 333 | 333 | 100.0 | 25.81276 | 28.727 | 28.394901 | -25.494796 | 0.004933 | -0.078109 |
| S1_exclude_severely_incomplete | arm1 | 333 | 322 | 96.697 | 22.128143 | 25.611 | 25.593489 | -21.625814 | 0.140343 | 0.119902 |
| S1_exclude_severely_incomplete | arm2 | 333 | 333 | 100.0 | 19.22518 | 21.157 | 22.739634 | -17.83258 | 0.131601 | 0.120003 |
| S2_complete_only | arm0 | 333 | 333 | 100.0 | 25.81276 | 28.727 | 28.394901 | -25.494796 | 0.004933 | -0.078109 |
| S2_complete_only | arm1 | 333 | 322 | 96.697 | 22.128143 | 25.611 | 25.593489 | -21.625814 | 0.140343 | 0.119902 |
| S2_complete_only | arm2 | 333 | 333 | 100.0 | 19.22518 | 21.157 | 22.739634 | -17.83258 | 0.131601 | 0.120003 |

## Subject/block remaining n

The complete table is in `MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_BY_BLOCK.csv`; only `97795/block4` changes from 28 to 26 selected windows under S1/S2. Per-arm valid n is retained because ARM1 has estimator-level missing rows independent of coverage class.

## Interpretation

- S0→S2 MAE deltas (bpm): `{'arm0': {'mae_delta_s2_minus_s0_bpm': 0.021128, 'valid_n_s0': 334, 'valid_n_s2': 333}, 'arm1': {'mae_delta_s2_minus_s0_bpm': -0.061349, 'valid_n_s0': 323, 'valid_n_s2': 322}, 'arm2': {'mae_delta_s2_minus_s0_bpm': 0.03612, 'valid_n_s0': 334, 'valid_n_s2': 333}}`.
- Coverage finding: `SEVERE_COVERAGE_FAILURE_LOCALIZED_ONLY` and `COVERAGE_NOT_PRIMARY_HR_EXPLANATION`. Severe incompleteness is localized to two tail windows in 97795/block4; the 333 complete windows retain the high-error diagnostic pattern.
- Any S1/S2 change is a validity sensitivity on complete acquisition windows, not an HR algorithm improvement and not a reason to delete or replace the S0 primary result.
- HR/BR remain `HOLD`; HRV remains `BLOCKED`; Issue #16 remains `PAUSED`.
