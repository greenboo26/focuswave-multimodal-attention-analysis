# mmWave handoff — root-cause audit route

Status: `ROOT_CAUSE_AUDIT_IN_PROGRESS_PARALLEL`

Branch target: `codex/mmwave-formal-reanalysis-v2`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。毫米波是多模态测量来源之一，不是整个项目的中心。

## Why the route changed

Task 2S completed, but its result does not yet justify treating the HR algorithm line as fully explained. The central unresolved fact is the large discontinuity between historical and current benchmark results:

- historical 25 s development-equivalent session-MAE median ≈ **9.14 BPM**;
- current 30 s product-window MAE ≈ **26.98 BPM**;
- current 50 s project route MAE ≈ **29.02 BPM**;
- current 60 s Task 2S project route MAE ≈ **37.12 BPM**.

These values are not directly comparable because they differ in window construction, ECG scorer/reference, aggregation and session inclusion. Therefore the next authorized work is root-cause analysis, not another external algorithm trial.

## Parallel tasks now active

Source-of-truth task documents:

- `ROOT_CAUSE_AUDIT_MASTER_PLAN.md`
- `PARALLEL_WORKSTREAMS_2026-08-27.md`
- `KNOWLEDGE_NOTES_MM_WAVE_HR_2026-08-27.md`

GitHub issues:

- #6 Root cause A — explain 9→27–37 BPM discontinuity;
- #7 Root cause B — audit existing mmWave assets and failures;
- #8 Root cause C — rank targeted HR improvements after diagnosis.

## Task A — benchmark discontinuity

Must isolate on common sessions/windows wherever possible:

1. input semantics / units / sample rate;
2. historical vs current adapter;
3. 25/30/50/60 s window construction;
4. historical ECG scorer vs `ecg_reference_v1`;
5. pooled-window MAE vs session-MAE-median aggregation;
6. exact session inclusion/intersection;
7. range-bin, phase, multi-bin and frequency-axis logic;
8. quality/trajectory/harmonic corrections;
9. error type: correct / 0.5x / 2x / other lock / unexplained.

No new algorithm family.

## Task B — reuse / repository archaeology

Inspect current central evidence and historical commits first. Existing evidence already records:

- v1–v8 historical comparisons;
- v3.1/v3.1.1 HR/IBI development;
- seven prior A/B trials (SPC/Hampel/phase-difference/CFAR/SSA/envelope/CEEMDAN);
- historical AgeBalanced v1.7 external validation;
- multi-bin/spatial/harmonic/quality failure modes;
- acquisition facts in `kyandi233-dev/FocusWave@ecg`.

Stable workspace registry marks `mmwave-hrv-analysis` as legacy, not canonical. Use it only if a specific historical artifact is actually accessible.

## Acquisition truth worth preserving

`kyandi233-dev/FocusWave@ecg/01-MainProgram/core/mmwave_capture.py` documents formal RS6240 capture as raw complex IQ + timestamps, 2T4R, 256 range FFT, nominal 10 ms frame period (~100 fps), 57 GHz start frequency and 37 mm range resolution. This input is materially different from AgeBalanced's 10 Hz derived radar representation. Algorithm portability must not silently conflate them.

The local BIOPAC special programs remain mechanism/stress-test evidence rather than independent-subject product validation.

## Task C — improvement ranking

Do not implement algorithms. Rank at most three targeted directions after A/B evidence:

1. fix benchmark/reference/adapter defect if present;
2. restore/reuse project logic that current benchmark may have dropped;
3. authorize one targeted signal-processing repair only if a localized true failure remains.

No algorithm fishing.

## Decision after A/B/C

Primary review must choose exactly one:

- `FIX_BENCHMARK_AND_RETEST_EXISTING_ROUTE`
- `ONE_TARGETED_SIGNAL_REPAIR`
- `STOP_HR_RND`

80-person heldout stays untouched during the audit. No formal `J:\Data` physiology run and no HRV work are authorized.

## Previous completed evidence remains valid with boundaries

### Phase 2B-1

- `ecg_reference_v1` implemented and tested.
- 25 s historical-equivalence development result: session-MAE median 9.14 BPM.
- P003 field-level smoke test matched historical source commit `f4a8c74`.
- 30 s current result: coverage 95.5%, MAE 26.98, median AE 13.79, RMSE 41.13 BPM.

### Task 2R

- 50 s project route: MAE 29.02 BPM.
- adapted SSA+VMD route: MAE 28.12 BPM; small improvement only, no gate-relevant rescue.
- This was not an official reproduction of Lei 2025.

### Task 2S

- 60 s project route: MAE 37.1163 BPM on 12 ECG-QC-scored complete-session windows.
- Lei 2025 SSA core adapted route: MAE 38.0582 BPM.
- No multi-metric rescue; AgeBalanced has no RSP, so respiratory-harmonic removal itself was not directly reference-assessable.

These results motivate the root-cause audit; they do not by themselves identify the cause of the historical-to-current discontinuity.

Completion vocabulary: `PASS / PARTIAL / BLOCKED`.
