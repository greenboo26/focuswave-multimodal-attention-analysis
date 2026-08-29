# mmWave gate/target ablation — 2026-08-30

状态：`PARTIAL`

本轮固定同一 335 个 complete formal-block 20 s windows、同一 block boundaries、同一 frozen block-affine ECG HR 和同一当前 HR frequency estimator。没有删除窗口。

## Arm definitions

- ARM0: current block-local reference, unchanged.
- ARM1: literal requested definition — current block-local selector/score/continuity plus historical bins 9–40 gate.
- ARM2: historical 6000-frame fixed target, but current 20 s HR estimator; no historical phase/filter/HR-course logic mixed in.
- ARM3: bins 9–40 gate plus current block-local selector/score/continuity.

ARM1 and ARM3 are functionally identical under the literal definitions: `True`. Therefore this run cannot independently estimate an additional block-local effect between those two arms; no hidden reinterpretation was introduced.

## Overall metrics

| arm | n | coverage | MAE | median AE | RMSE | bias | Pearson | Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| arm0 | 335 | 100.0% | 24.884913 | 27.87 | 27.675448 | -24.454472 | 0.008856 | -0.063346 |
| arm1 | 314 | 93.731% | 21.804185 | 25.515 | 25.295205 | -21.082045 | 0.149547 | 0.11303 |
| arm2 | 335 | 100.0% | 19.068931 | 21.244 | 22.493054 | -17.54603 | 0.214216 | 0.188072 |
| arm3 | 314 | 93.731% | 21.804185 | 25.515 | 25.295205 | -21.082045 | 0.149547 | 0.11303 |

## Paired comparisons against ARM0

`delta AE = AE(arm) - AE(ARM0)`; all use the same available windows.

| comparison | common n | mean delta | median delta | better | tie | worse |
|---|---:|---:|---:|---:|---:|---:|
| arm1_vs_arm0 | 314 | -2.638525 | 0.0 | 98 | 152 | 64 |
| arm2_vs_arm0 | 335 | -5.815982 | -3.511 | 188 | 48 | 99 |
| arm3_vs_arm0 | 314 | -2.638525 | 0.0 | 98 | 152 | 64 |

## Gate-outside error split for ARM0

This is descriptive only; trajectory stability and HR accuracy are not interchangeable.

| split | n | MAE | median AE | RMSE | bias |
|---|---:|---:|---:|---:|---:|
| inside_historical_gate | 181 | 21.902392 | 24.789 | 25.359325 | -21.265309 |
| outside_historical_gate | 154 | 28.390344 | 30.743 | 30.171203 | -28.202773 |

## Long-frame-interval overlap

Each window has `n_gap_gt100ms`, `max_frame_interval_ms`, and `gap_total_duration_ms`. No window was removed.

| split | arm | n | MAE | median AE |
|---|---|---:|---:|---:|
| no_gt100ms_gap | arm0 | 0 | None | None |
| no_gt100ms_gap | arm1 | 0 | None | None |
| no_gt100ms_gap | arm2 | 0 | None | None |
| no_gt100ms_gap | arm3 | 0 | None | None |
| has_gt100ms_gap | arm0 | 335 | 24.884913 | 27.87 |
| has_gt100ms_gap | arm1 | 314 | 21.804185 | 25.515 |
| has_gt100ms_gap | arm2 | 335 | 19.068931 | 21.244 |
| has_gt100ms_gap | arm3 | 314 | 21.804185 | 25.515 |

## Stability

Per-block bin hops, channel switches, range path, and target residence are in `MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv`; they are reported separately from HR error.

## Decision

- ARM1/ARM3 are identical under the literal request, so no independent block-local ablation is claimed.
- The final contributor label is selected only from observed same-window metrics and participant/block tables; no producer change is justified automatically.
- Current HR producer remains `HOLD` unless a later preregistered arm shows participant-wise improvement without QC/BR side effects.

## Artifacts

- `MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_SUMMARY.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_PAIRED.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_GATE_ERROR_SPLIT.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_GAP_ERROR_SPLIT.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_REPORT_2026-08-30.md`

## Participant-wise and block-wise MAE

Full participant table: `MMWAVE_HR_GATE_TARGET_ABLATION_PARTICIPANT.csv`; full block table: `MMWAVE_HR_GATE_TARGET_ABLATION_BLOCK.csv`.

### Participant-wise

| subject | arm | n | coverage | MAE | median AE |
|---|---|---:|---:|---:|---:|
| 9779 | arm0 | 112 | 100.0% | 21.750768 | 25.1245 |
| 9779 | arm1 | 110 | 98.214% | 19.483327 | 20.3725 |
| 9779 | arm2 | 112 | 100.0% | 20.704098 | 22.583 |
| 9779 | arm3 | 110 | 98.214% | 19.483327 | 20.3725 |
| 97793 | arm0 | 111 | 100.0% | 21.040279 | 24.191 |
| 97793 | arm1 | 109 | 98.198% | 20.618156 | 23.915 |
| 97793 | arm2 | 111 | 100.0% | 16.589063 | 19.001 |
| 97793 | arm3 | 109 | 98.198% | 20.618156 | 23.915 |
| 97795 | arm0 | 112 | 100.0% | 31.829366 | 34.376 |
| 97795 | arm1 | 95 | 84.821% | 25.852305 | 30.492 |
| 97795 | arm2 | 112 | 100.0% | 19.891491 | 20.566 |
| 97795 | arm3 | 95 | 84.821% | 25.852305 | 30.492 |

### Block-wise

| block | arm | n | coverage | MAE | median AE |
|---|---|---:|---:|---:|---:|
| block1 | arm0 | 141 | 100.0% | 23.986979 | 26.304 |
| block1 | arm1 | 132 | 93.617% | 20.719212 | 23.232 |
| block1 | arm2 | 141 | 100.0% | 19.74244 | 21.448 |
| block1 | arm3 | 132 | 93.617% | 20.719212 | 23.232 |
| block2 | arm0 | 138 | 100.0% | 22.380717 | 25.689 |
| block2 | arm1 | 135 | 97.826% | 20.707985 | 25.004 |
| block2 | arm2 | 138 | 100.0% | 18.587993 | 21.7035 |
| block2 | arm3 | 135 | 97.826% | 20.707985 | 25.004 |
| block3 | arm0 | 28 | 100.0% | 32.373536 | 34.5495 |
| block3 | arm1 | 22 | 78.571% | 29.131136 | 30.167 |
| block3 | arm2 | 28 | 100.0% | 20.34575 | 20.792 |
| block3 | arm3 | 22 | 78.571% | 29.131136 | 30.167 |
| block4 | arm0 | 28 | 100.0% | 34.260143 | 39.7045 |
| block4 | arm1 | 25 | 89.286% | 27.0046 | 34.192 |
| block4 | arm2 | 28 | 100.0% | 16.770857 | 15.6765 |
| block4 | arm3 | 25 | 89.286% | 27.0046 | 34.192 |

## Stability

Per-block bin hops, channel switches, range path, and target residence are in `MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv`; they are reported separately from HR error.

## Decision

- ARM1/ARM3 are identical under the literal request, so no independent block-local ablation is claimed.
- The observed result supports `GATE_AND_TARGET_BOTH_MATTER`: gate-only improves the common-window ARM0 comparison but loses 21/335 candidate windows; fixed historical target improves more on the same 335 rows. This is not a producer promotion because target/gate validity and long-gap contamination remain unresolved.
- Current HR producer remains `HOLD`; no producer change is justified automatically.

## Additional artifacts

- `MMWAVE_HR_GATE_TARGET_ABLATION_PARTICIPANT.csv`
- `MMWAVE_HR_GATE_TARGET_ABLATION_BLOCK.csv`

## Long-interval overlap interpretation

- Overlap summary: `{"window_n": 335, "window_any_gt100ms_gap_n": 335, "window_any_gt100ms_gap_pct": 100.0, "window_no_gt100ms_gap_n": 0, "sum_window_gap_occurrences": 588, "median_n_gap_gt100ms": 2.0, "max_n_gap_gt100ms": 2, "median_max_frame_interval_ms": 2507.0, "max_frame_interval_ms_across_windows": 4436, "median_gap_total_duration_ms": 4468.0, "max_gap_total_duration_ms": 6835, "timestamp_long_interval_effect": "UNRESOLVED_NO_CLEAN_NO_GAP_COMPARATOR"}`.
- Every one of the 335 HR windows contains at least one >100 ms adjacent timestamp interval, so a clean no-gap comparison arm does not exist. `TIMESTAMP_LONG_INTERVAL_EFFECT` is therefore `UNRESOLVED`, not declared negligible/minor/material.
