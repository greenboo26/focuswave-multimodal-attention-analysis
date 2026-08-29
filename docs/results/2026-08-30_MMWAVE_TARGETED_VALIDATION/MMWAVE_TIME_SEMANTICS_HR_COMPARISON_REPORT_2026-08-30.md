# mmWave time-semantics HR sensitivity — 2026-08-30

状态：`PARTIAL / PYTHON_TIMESTAMP_ARTIFACT_MATERIALLY_CHANGED_WINDOWS`

本轮唯一改变是 window frame membership：旧 Python-time 窗口改为冻结 contract 定义的 DLL absolute Unix-ms 窗口。ARM0/ARM1/ARM2 的 target、gate、filter、FS=100、ECG reference 和 block denominator 均未改变。

- old rows/new rows: `335/335`; changed membership: `310`; obvious Jaccard<0.9: `154`.
- HR coverage old/new: `{'arm0': 335, 'arm1': 314, 'arm2': 335}` / `{'arm0': 334, 'arm1': 323, 'arm2': 334}`.
- Mean absolute HR value delta old→new: `{'arm0': 6.126641, 'arm1': 6.845548, 'arm2': 6.444105}` bpm.

## Metrics

详见 `MMWAVE_TIME_SEMANTICS_HR_METRICS.csv`，包括 old/new 的 MAE、median AE、RMSE、bias、Pearson、Spearman。所有相关系数均为描述性，不作因果推断。

| version | arm | n | coverage % | MAE | median AE | RMSE | bias | Pearson | Spearman |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| new_dll_time | arm0 | 334 | 99.701 | 25.791632 | 28.701 | 28.37093 | -25.47462 | 0.0119 | -0.071222 |
| old_python_time | arm0 | 335 | 100.0 | 24.884913 | 27.87 | 27.675448 | -24.454472 | 0.008856 | -0.063346 |
| new_dll_time | arm1 | 323 | 96.418 | 22.189492 | 25.667 | 25.660192 | -21.688718 | 0.134016 | 0.113713 |
| old_python_time | arm1 | 314 | 93.731 | 21.804185 | 25.515 | 25.295205 | -21.082045 | 0.149547 | 0.11303 |
| new_dll_time | arm2 | 334 | 99.701 | 19.18906 | 21.039 | 22.708948 | -17.800629 | 0.138025 | 0.126511 |
| old_python_time | arm2 | 335 | 100.0 | 19.068931 | 21.244 | 22.493054 | -17.54603 | 0.214216 | 0.188072 |

## Coverage blocker

- DLL authoritative data coverage summary: `{"97793": {"last_dll_unix_ms": 1786871352163, "complete_block_end_unix_ms": 1786871223401, "complete_block_end_after_last_dll_ms": -128762}, "9779": {"last_dll_unix_ms": 1786866226251, "complete_block_end_unix_ms": 1786866219087, "complete_block_end_after_last_dll_ms": -7164}, "97795": {"last_dll_unix_ms": 1786887631266, "complete_block_end_unix_ms": 1786887656075, "complete_block_end_after_last_dll_ms": 24809}}`.
- New windows with fewer than 100 DLL frames: `[('97795', 'block4', 'block4_w028', '46')]`.
- `97795/block4` ends with only 46 recorded DLL frames because the program end marker is 24,809 ms after the last DLL frame. The missing tail is not imputed; the affected HR rows are invalid/missing rather than silently treated as physiological failures.

## Decision

- `WINDOW_DECISION = PYTHON_TIMESTAMP_ARTIFACT_MATERIALLY_CHANGED_WINDOWS`.
- Classification A (cosmetic only): not supported; the change is material (310/335 membership changes, 154 obvious equivalence changes, and 6.13–6.85 bpm mean absolute HR value deltas).
- Classification B (materially changed windows): supported; the old Python-time rows and new DLL-time rows are not interchangeable.
- Classification C (unresolved): retained for exact DLL timestamp generator origin and the 97795/block4 acquisition-coverage tail.
- 旧 24.9/21.8/19.1 bpm 结果保留为历史 Python-time window provenance，但不再作为 DLL authoritative window 的当前结果；当前 contract 下应由 new DLL-time metrics 引用。
- 不修改 producer，不调 estimator，不修改 target/gate，不运行 HRV/#16/C2B/C2C/full batch。
- HR/BR 继续 `HOLD`；HRV `BLOCKED`；Issue #16 `PAUSED`。

## Artifacts

- `MMWAVE_TIME_SEMANTICS_HR_COMPARISON.csv`
- `MMWAVE_TIME_SEMANTICS_HR_METRICS.csv`
- `MMWAVE_TIME_SEMANTICS_HR_COMPARISON_REPORT_2026-08-30.md`
