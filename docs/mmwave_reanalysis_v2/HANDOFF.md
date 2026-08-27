# mmWave handoff — root-cause audit route

Status: `OFFICIAL_REFERENCE_EXISTING_ROUTES_RETEST_COMPLETE_PARTIAL_STOP`

Branch target: `codex/mmwave-formal-reanalysis-v2`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。毫米波是多模态测量来源之一，不是整个项目的中心。

## Current conclusion

The official AgeBalanced ECG FFT reference has now been applied to the previously tested development routes. The earlier 26.98–38.06 BPM values were produced with `ecg_reference_v1` and are superseded for AgeBalanced HR performance claims. Under the official reference, the comparable project route is 10.361 BPM pooled MAE at 30 s / 5 s; historical 25 s remains 10.493 BPM. Existing 50 s routes are near 9 BPM, but SSA+VMD's small MAE advantage is not stable across RMSE, extreme errors and lock counts.

This handoff is therefore a completed development-only fairness retest. No new physiology optimization or held-out decision is authorized by this update.

## Earlier audit task records

Source-of-truth task documents:

- `ROOT_CAUSE_AUDIT_MASTER_PLAN.md`
- `PARALLEL_WORKSTREAMS_2026-08-27.md`
- `KNOWLEDGE_NOTES_MM_WAVE_HR_2026-08-27.md`

GitHub issues:

- #6 Root cause A — explain 9→27–37 BPM discontinuity;
- #7 Root cause B — audit existing mmWave assets and failures;
- #8 Root cause C — rank targeted HR improvements after diagnosis.
- #9 Benchmark decomposition — unified ECG scorer and aggregation; completed below.

## Issue #9 completed decomposition

Status: `PASS` for the authorized development-only benchmark decomposition. See `BENCHMARK_DECOMPOSITION_RESULT.md` for the full 2×2 tables.

On the same 30-participant / 60-session development split and same radar route:

- 25 s legacy ECG: pooled MAE 10.315 BPM; session-MAE median 9.147 BPM.
- 25 s `ecg_reference_v1`: pooled MAE 26.682 BPM; session-MAE median 12.143 BPM.
- 30 s legacy ECG: pooled MAE 10.036 BPM; session-MAE median 8.784 BPM.
- 30 s `ecg_reference_v1`: pooled MAE 26.983 BPM; session-MAE median 13.803 BPM.

The scorer/reference change explains the large historical-to-current separation; aggregation is secondary and window length is negligible under the legacy scorer. The decision is `FIX_BENCHMARK_AND_RETEST_EXISTING_ROUTE`. No held-out 80, `J:\Data`, HRV, physiology tuning, or new algorithm family was used.

## Official AgeBalanced ECG reference alignment — completed

Issue #9's follow-up was completed on this same branch. The official Zenodo 16760684 `ExampleCode.ipynb` (MD5 `204768fa033176b12baae016ccef19b1`) was read directly. Rest ECG uses 256 Hz, a fourth-order Butterworth `b,a` bandpass at 0.8–2.0 Hz through the helper's normalized Nyquist cutoffs and `scipy.signal.filtfilt`; each window then uses `np.fft.fft`, DC removal, positive half-spectrum, maximum magnitude bin, and Hz×60. No window function, extra detrending, normalization, peak detector, RR/IBI rule, or interpolation is used.

The same 30 development participants / 60 Rest sessions, radar output, 5 s starts, 25 s / 30 s windows and aggregation were reused. Results are pooled MAE / median session-MAE (BPM):

- 25 s Official **10.493 / 9.296** (328 windows / 60 sessions; 100% / 100% coverage); legacy **10.315 / 9.147** (328 / 60); `ecg_reference_v1` **26.682 / 12.143** (314 / 59; 95.7% / 98.3%).
- 30 s Official **10.361 / 8.575** (268 / 60; 100% / 100%); legacy **10.036 / 8.784** (268 / 60); `ecg_reference_v1` **26.983 / 13.803** (256 / 59; 95.5% / 98.3%).

Official≈legacy is confirmed. Official versus `ecg_reference_v1` remains separated by 16.189 BPM (25 s) and 16.622 BPM (30 s) pooled MAE, confirming that the prior ~9→27 BPM discontinuity is primarily caused by the non-official `ecg_reference_v1` benchmark semantics, not window length. The AgeBalanced external HR contract is frozen to Official FFT as the unique primary reference; legacy is historical-only; `ecg_reference_v1` is internal QC/beat-only.

## Existing routes retest under Official ECG — completed

The already-tested AgeBalanced routes were rescored without changing radar algorithms or parameters. Official FFT results are: 30 s project **10.361 BPM pooled MAE / 8.575 median session-MAE** (268/268 windows, 60/60 sessions); 50 s project **9.292 / 7.813** (88/88, 60/60); 50 s SSA+VMD adapted **9.012 / 5.253** (88/88, 60/60); 60 s project **8.273 / 6.517** (14/14, 14 complete sessions); 60 s Lei SSA adapted **8.670 / 7.450** (14/14, 14 complete sessions). The 25 s official historical diagnostic remains **10.493 / 9.296** (328/328, 60/60).

The former `ecg_reference_v1` values 26.983 (30 s), 29.02/28.12 (50 s project/SSA+VMD), and 37.1163/38.0582 (60 s project/Lei SSA) are superseded for AgeBalanced HR performance claims. They reflect the wrong external benchmark reference, not a demonstrated radar degradation. The 50 s SSA+VMD pooled MAE difference is only 0.280 BPM and is offset by worse RMSE, more extreme errors and a two-times lock; it is not a stable improvement. The 60 s comparison is limited by only 14 complete sessions. See `OFFICIAL_REFERENCE_EXISTING_ROUTES_RESULT.md`.

Recommendation after this fairness retest: retain the existing project route with Official AgeBalanced ECG as the interpretable 30 s benchmark; do not start another mmWave physiology task or held-out run automatically. Signal/quality/motion features remain supporting modality evidence.

## Task A — benchmark discontinuity

Must isolate on common sessions/windows wherever possible:

1. input semantics / units / sample rate;
2. historical vs current adapter;
3. 25/30/50/60 s window construction;
4. official AgeBalanced FFT ECG vs historical ECG scorer vs `ecg_reference_v1`;
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
- The 26.98 BPM figure is superseded for AgeBalanced HR performance by the official-reference result above; it remains only as reference-sensitivity evidence.

### Task 2R

- 50 s project route: MAE 29.02 BPM.
- adapted SSA+VMD route: MAE 28.12 BPM; small improvement only, no gate-relevant rescue.
- This was not an official reproduction of Lei 2025.

### Task 2S

- 60 s project route: MAE 37.1163 BPM on 12 ECG-QC-scored complete-session windows.
- Lei 2025 SSA core adapted route: MAE 38.0582 BPM.
- No multi-metric rescue; AgeBalanced has no RSP, so respiratory-harmonic removal itself was not directly reference-assessable.

The 60 s values above are also superseded for AgeBalanced HR performance by the Official FFT rescore (8.273 / 8.670 BPM); the old values remain as `ecg_reference_v1` sensitivity diagnostics.

These results motivate the root-cause audit; they do not by themselves identify the cause of the historical-to-current discontinuity.

Completion vocabulary: `PASS / PARTIAL / BLOCKED`.
