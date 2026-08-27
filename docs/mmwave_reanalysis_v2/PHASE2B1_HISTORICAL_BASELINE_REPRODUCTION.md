# Phase 2B-1: Historical baseline reproduction

Status: `PARTIAL_DEVELOPMENT_ONLY`

Run date: 2026-08-27

Frozen baseline configuration: [`agebalanced_historical_baseline_v1.json`](../../configs/mmwave_reanalysis_v2/agebalanced_historical_baseline_v1.json)
Configuration SHA-256: `1acce55b24016387fcee77d6c01379a6b512d93a3d70b8ba6aab583c9f541299`

## Scope and stop boundary

This execution used only the frozen development split: 30 AgeBalanced participants and their two Rest sessions (60 sessions). It did not run the 80 held-out participants, any candidate method, `J:\Data`, BR scoring, or HRV. `BENCHMARK_DECISION_V1` was not changed.

The historical `25 s / 5 s` route is an equivalence diagnostic only. The frozen `per_window_benchmark_v1` contract permits 10, 30, or 60 s windows, so no 25 s row is presented as schema-valid. The `30 s / 5 s` development run is the only schema-valid output of this phase.

## Implemented and verified

- `pipelines/mmwave/ecg_reference_v1.py` implements the Decision V1 ECG-first reference procedure: timestamp/finite checks, robust normalization, 0.5--40 Hz third-order zero-phase filter, polarity selection, IBI plausibility, and window validity checks. It is radar-blind and does not compute HRV.
- `tests/test_ecg_reference_v1.py` passes four cases: positive and negative polarity, flatline rejection, and timestamp rejection.
- The 30 s JSON Lines artifact validates each record against `per_window_benchmark_v1.schema.json`.
- An exact field-level smoke comparison against historical source commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1` was completed for `P003_lying_rest`: selected bins and all five 25 s windows matched for frequency HR, time HR, fused HR, time/frequency gap, regularity, peak count, harmonic flag, and trajectory HR.

## 25 s / 5 s historical-equivalence diagnostic

| Scope | Sessions | Window pairs | Session-MAE median | High AE median | Medium AE median | Low AE median |
|---|---:|---:|---:|---:|---:|---:|
| Frozen development subset | 60 | 328 | 9.14 BPM | 1.10 BPM (n=15) | 5.45 BPM (n=6) | 9.30 BPM (n=307) |
| Historical changelog record | 220 | not recoverable | about 9.5 BPM | about 1.6 BPM | about 3.4 BPM | about 10.1 BPM |

The 9.14 BPM development-subset session median is descriptively close to 9.5 BPM, but it is **not** a full 220-session reproduction. The observed numerical differences cannot be assigned to an algorithm change: the legacy computation and legacy ECG scorer are retained for the 25 s route, and the source-equivalence smoke test passed. The material remaining difference is cohort scope (60 development sessions versus historical 220 sessions). Historical evidence does not recover the exact aggregation definition for the quality-stratified 1.6/3.4/10.1 numbers, so those entries remain `MISSING_EVIDENCE` rather than a failed/pass comparison. The historical 2x/half lock classifier is also `MISSING_EVIDENCE`; its reported 4/1188 and 0/1188 counts were not re-scored.

## 30 s / 5 s schema-valid development baseline

| Item | Result |
|---|---:|
| ECG reference sessions passing full-session QC | 60 / 60 |
| Attempted windows | 268 |
| Scored windows | 256 |
| Coverage | 95.5% |
| MAE / median AE / RMSE | 26.98 / 13.79 / 41.13 BPM |
| High radar-QC windows | 208; median AE 9.52 BPM |
| Medium radar-QC windows | 48; median AE 22.04 BPM |
| Rejected windows | 12, all `ECG_QC_FAIL` |

This is a newly measured development-only baseline under 30 s windowing and `ecg_reference_v1`; it is not comparable to the historical 25 s all-session summary and does not satisfy the Decision V1 validation threshold. It establishes a reproducible starting point only; it makes no HR-validity, BR-validity, or product claim.

## Git-safe result provenance

Local derived artifacts are deliberately untracked. Their source data remain local and their file hashes are:

| Artifact | SHA-256 |
|---|---|
| `legacy_equivalence_25s_development_rows.jsonl` | `6c77308bf3c129f6f8102fffc4880638370d9ec0542705585d80d837edebac0d` |
| `per_window_benchmark_v1_development_30s.jsonl` | `34da3b1c2af87158fa19aaa15b4e5f748aecdb44ffa7ebb093b74d25b5a3cb1d` |
| `phase2b1_summary.json` | `af132c79dc127572c12171e1ffee56559b186510af9e72b637fbceb286743a7d` |

## Remaining blockers and Phase 2B-2 prerequisite

- `BLOCKED`: a genuine historical 220-session reproduction would include the frozen 80-participant held-out set, which this phase expressly prohibited.
- `BLOCKED`: 25 s outputs cannot enter the frozen per-window schema without a future, separately approved contract version.
- `MISSING_EVIDENCE`: exact historical quality aggregation and harmonic-lock classification code/output.
- `BLOCKED`: BR on AgeBalanced, because it has no RSP reference; HRV remains blocked by the existing beat-level gate.

The next phase may reproduce the historical baseline on all 220 sessions only if an explicit authorization permits the held-out data for **historical-equivalence-only** use. It must then keep the held-out participants sealed from all candidate-method selection and threshold decisions. No candidate benchmark is authorized by this document.
