# Issue #9 — Benchmark decomposition result

Status: `PASS` for the authorized development-only decomposition and official-reference alignment; remote redundant branch deletion remains outside this task and is not represented as complete.

## Scope and contract

The comparison reuses the canonical task branch `codex/mmwave-formal-reanalysis-v2`, the frozen AgeBalanced development split (30 participants, 60 Rest sessions), the existing historical radar adapter, the same radar outputs, and the same 5 s window starts. No held-out 80 participants, `J:\Data` physiology, HRV, physiology tuning, or new algorithm family was used.

For every window, the common inclusion rule was `radar_pass` plus a passing ECG scorer; rejected ECG windows were not interpolated. The 25 s route is retained as historical-equivalence diagnostic evidence, not as a frozen `per_window_benchmark_v1` artifact. The official reference is transcribed from Zenodo record 16760684 `ExampleCode.ipynb` (MD5 `204768fa033176b12baae016ccef19b1`).

## Core three-reference results

Values are `pooled-window MAE / median(session-level MAE)` in BPM. The parenthetical value is scored windows / scored sessions.

## Official reference implementation

The Rest ECG implementation uses the notebook's 256 Hz sampling rate, fourth-order Butterworth `b,a` bandpass (0.8–2.0 Hz) via normalized Nyquist cutoffs and `scipy.signal.filtfilt`. For each window it applies `np.fft.fft`, sets the DC bin to zero, keeps the positive half-spectrum, selects the maximum magnitude bin, and converts its frequency to BPM. There is no window function, extra detrending, normalization, peak detector, RR/IBI rule, or interpolation.

### 25 s windows

| Aggregation | legacy ECG | `ecg_reference_v1` |
|---|---:|---:|
| pooled-window MAE | **10.315 / 9.147** (328 / 60) | **26.682 / 12.143** (314 / 59) |
| median(session MAE) | **9.147** | **12.143** |

Official AgeBalanced FFT ECG: **10.493 / 9.296 BPM** (328 / 60; window/session coverage 100% / 100%). Official minus legacy is **+0.178 / +0.149 BPM**; official minus `ecg_reference_v1` is **−16.189 / −2.848 BPM**.

### 30 s windows

| Aggregation | legacy ECG | `ecg_reference_v1` |
|---|---:|---:|
| pooled-window MAE | **10.036 / 8.784** (268 / 60) | **26.983 / 13.803** (256 / 59) |
| median(session MAE) | **8.784** | **13.803** |

Official AgeBalanced FFT ECG: **10.361 / 8.575 BPM** (268 / 60; window/session coverage 100% / 100%). Official minus legacy is **+0.325 / −0.209 BPM**; official minus `ecg_reference_v1` is **−16.622 / −5.228 BPM**.

Coverage was 328/328 radar-pass windows for 25 s and 268/268 for 30 s. Legacy ECG scored all 60 sessions; `ecg_reference_v1` scored 59 sessions because one session had no passing reference window under the frozen QC. The same scorer-specific inclusion rule was applied at both lengths.

## Decomposition

The official-versus-legacy agreement confirms that the scorer/reference change is the dominant explanation of the historical ~9 BPM to current ~27 BPM discontinuity:

- Holding the legacy ECG scorer fixed, changing 25 s to 30 s changes pooled MAE only **10.315 → 10.036 BPM** and session-median MAE **9.147 → 8.784 BPM**.
- Holding 30 s fixed, changing legacy ECG to `ecg_reference_v1` changes pooled MAE **10.036 → 26.983 BPM** and session-median MAE **8.784 → 13.803 BPM**.
- Changing pooled-window MAE to session-level median does not create the discontinuity; it moves the 30 s current result from **26.983** to **13.803 BPM**, while the legacy 25 s result remains **9.147 BPM**.
- The one-session scorer-specific coverage difference is material for reporting but cannot explain a 16.9 BPM pooled gap by itself.
- Official AgeBalanced FFT and legacy ECG are practically equivalent on both window lengths: pooled MAE differs by 0.178 BPM (25 s) and 0.325 BPM (30 s), while session-MAE medians differ by 0.149 and −0.209 BPM.
- Official FFT versus `ecg_reference_v1` differs by 16.189 BPM (25 s) and 16.622 BPM (30 s) on pooled MAE, reproducing the previously identified discontinuity.

Most likely root-cause ranking:

1. **ECG scorer/reference semantics and resulting window-level reference values** — primary; specifically, `ecg_reference_v1` is not the AgeBalanced official FFT benchmark definition.
2. **Aggregation definition** — secondary reporting effect; it changes the level but not the legacy-to-current separation.
3. **Window length (25 s vs 30 s)** — negligible under the legacy scorer on the same radar route.
4. **Session inclusion** — small coverage effect; requires explicit common-session sensitivity in any retest.

## Frozen AgeBalanced external HR benchmark contract

- **Primary HR reference:** Official AgeBalanced Rest ECG FFT only.
- **Official implementation:** 256 Hz; fourth-order Butterworth `b,a` 0.8–2.0 Hz bandpass; zero-phase `filtfilt`; per-window `np.fft.fft`; DC bin zeroed; positive half-spectrum; maximum-magnitude frequency × 60.
- **Historical reference:** legacy ECG scorer retained for historical reproduction and continuity checks only.
- **Internal QC/beat reference:** `ecg_reference_v1` may remain available for internal beat/QC analyses, but must not be used as AgeBalanced external HR benchmark ground truth.
- **Window/cohort contract:** unchanged from Issue #9: 30 development participants / 60 Rest sessions, identical radar output, 25 s and 30 s diagnostic windows, 5 s starts, half-open source-time windows, common `radar_pass`, scorer-specific availability, and no interpolation.

## Decision

`FIX_BENCHMARK_AND_RETEST_EXISTING_ROUTE`.

The current 30 s `ecg_reference_v1` result should not be compared directly with the historical 25 s legacy session-median result. The official FFT alignment supports `FIX_BENCHMARK_AND_RETEST_EXISTING_ROUTE`; freeze Official AgeBalanced FFT as the sole external HR benchmark reference, retain legacy only for historical reproduction, and exclude `ecg_reference_v1` from AgeBalanced HR performance judgments. This issue does not authorize adapter, range-bin, phase-logic, or new signal-processing implementation.

## Reproducibility evidence

- Runner: `scripts/mmwave_reanalysis_v2/run_benchmark_decomposition_issue9.py`
- Input data: local AgeBalanced package, outside Git; provenance manifest is `configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json`.
- Frozen split: `configs/mmwave_reanalysis_v2/agebalanced_split_v1.json`.
- Machine-readable result: local derived output `mmwave_reanalysis_v2_issue9_benchmark_decomposition_20260827/issue9_result.json`.
- Radar implementation reused from `scripts/mmwave_reanalysis_v2/run_agebalanced_historical_baseline_v1.py`; ECG implementations are the official transcription in `scripts/mmwave_reanalysis_v2/run_benchmark_decomposition_issue9.py`, legacy transcription in the historical baseline runner, and `pipelines/mmwave/ecg_reference_v1.py`.

The result is development-only and does not validate HR on held-out participants or authorize formal physiology use.
