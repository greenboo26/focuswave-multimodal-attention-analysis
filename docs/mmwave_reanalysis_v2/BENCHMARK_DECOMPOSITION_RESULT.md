# Issue #9 — Benchmark decomposition result

Status: `PASS` for the authorized development-only decomposition; remote redundant branch deletion remains outside this task and is not represented as complete.

## Scope and contract

The comparison reuses the canonical task branch `codex/mmwave-formal-reanalysis-v2`, the frozen AgeBalanced development split (30 participants, 60 Rest sessions), the existing historical radar adapter, the same radar outputs, and the same 5 s window starts. No held-out 80 participants, `J:\Data` physiology, HRV, physiology tuning, or new algorithm family was used.

For every window, the common inclusion rule was `radar_pass` plus a passing ECG scorer; rejected ECG windows were not interpolated. The 25 s route is retained as historical-equivalence diagnostic evidence, not as a frozen `per_window_benchmark_v1` artifact.

## Core 2×2 results

Values are `pooled-window MAE / median(session-level MAE)` in BPM. The parenthetical value is scored windows / scored sessions.

### 25 s windows

| Aggregation | legacy ECG | `ecg_reference_v1` |
|---|---:|---:|
| pooled-window MAE | **10.315 / 9.147** (328 / 60) | **26.682 / 12.143** (314 / 59) |
| median(session MAE) | **9.147** | **12.143** |

### 30 s windows

| Aggregation | legacy ECG | `ecg_reference_v1` |
|---|---:|---:|
| pooled-window MAE | **10.036 / 8.784** (268 / 60) | **26.983 / 13.803** (256 / 59) |
| median(session MAE) | **8.784** | **13.803** |

Coverage was 328/328 radar-pass windows for 25 s and 268/268 for 30 s. Legacy ECG scored all 60 sessions; `ecg_reference_v1` scored 59 sessions because one session had no passing reference window under the frozen QC. The same scorer-specific inclusion rule was applied at both lengths.

## Decomposition

The scorer/reference change is the dominant explanation of the historical ~9 BPM to current ~27 BPM discontinuity:

- Holding the legacy ECG scorer fixed, changing 25 s to 30 s changes pooled MAE only **10.315 → 10.036 BPM** and session-median MAE **9.147 → 8.784 BPM**.
- Holding 30 s fixed, changing legacy ECG to `ecg_reference_v1` changes pooled MAE **10.036 → 26.983 BPM** and session-median MAE **8.784 → 13.803 BPM**.
- Changing pooled-window MAE to session-level median does not create the discontinuity; it moves the 30 s current result from **26.983** to **13.803 BPM**, while the legacy 25 s result remains **9.147 BPM**.
- The one-session scorer-specific coverage difference is material for reporting but cannot explain a 16.9 BPM pooled gap by itself.

Most likely root-cause ranking:

1. **ECG scorer/reference semantics and resulting window-level reference values** — primary.
2. **Aggregation definition** — secondary reporting effect; it changes the level but not the legacy-to-current separation.
3. **Window length (25 s vs 30 s)** — negligible under the legacy scorer on the same radar route.
4. **Session inclusion** — small coverage effect; requires explicit common-session sensitivity in any retest.

## Decision

`FIX_BENCHMARK_AND_RETEST_EXISTING_ROUTE`.

The current 30 s `ecg_reference_v1` result should not be compared directly with the historical 25 s legacy session-median result. The next authorized action is a benchmark/reference contract repair or explicitly labelled dual-report retest of the existing route. This issue does not authorize adapter, range-bin, phase-logic, or new signal-processing implementation.

## Reproducibility evidence

- Runner: `scripts/mmwave_reanalysis_v2/run_benchmark_decomposition_issue9.py`
- Input data: local AgeBalanced package, outside Git; provenance manifest is `configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json`.
- Frozen split: `configs/mmwave_reanalysis_v2/agebalanced_split_v1.json`.
- Machine-readable result: local derived output `mmwave_reanalysis_v2_issue9_benchmark_decomposition_20260827/issue9_result.json`.
- Radar implementation reused from `scripts/mmwave_reanalysis_v2/run_agebalanced_historical_baseline_v1.py`; ECG implementation reused from `pipelines/mmwave/ecg_reference_v1.py`.

The result is development-only and does not validate HR on held-out participants or authorize formal physiology use.
