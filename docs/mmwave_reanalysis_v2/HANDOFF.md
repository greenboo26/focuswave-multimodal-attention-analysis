# Phase 2A handoff

Status: `PARTIAL_PHASE_2B_1` (Phase 2A remains frozen and `PASS`)

Branch target: `codex/mmwave-formal-reanalysis-v2`

Base: `greenboo26/focuswave-multimodal-attention-analysis@main`, local base commit `eeb9954358d8074d53ff6a17cf4ade620f17e604`.

## Completed in Phase 2A

- Preserved Phase 1 without repeating the historical asset audit.
- Reconciled AgeBalanced 110 participants, 440 total sessions and historical 220 Rest sessions; froze 2,424 file hashes and a deterministic 30/80 participant split.
- Audited ECG/RSP/R-peak availability and froze reference-first QC. AgeBalanced BR is blocked; RS6240 has ECG in 11/11 and RSP in 10/11, with two identifier mismatches retained.
- Froze Decision V1: data rules, windows, common radar input, synchronization, quality strata, metrics, harmonic locks, numerical thresholds and algorithm selection.
- Implemented `per_window_benchmark_v1` JSON Schema and tests.
- Completed implementation-level Reuse Gate with fixed commits/licenses and honest `paper_reimplementation` labels.

## Phase 2B-1 completed under explicit bounded authorization

- Implemented and unit-tested `ecg_reference_v1`; it passed full-session QC for 60/60 AgeBalanced development Rest sessions.
- Reproduced the historical baseline route on development data only: 25 s / 5 s result is 9.14 BPM session-MAE median across 60 sessions. The result is a diagnostic, not a schema artifact, because V1 only permits 10/30/60 s.
- Produced a schema-valid 30 s / 5 s development baseline: 256/268 scored windows (95.5% coverage), MAE 26.98 BPM, median AE 13.79 BPM, RMSE 41.13 BPM. It does not pass validation and is not comparable to historical 25 s aggregate numbers.
- Full detail and Git-safe output hashes: `PHASE2B1_HISTORICAL_BASELINE_REPRODUCTION.md`.

## Not done by design

- No formal cohort HR/BR rerun.
- No new HRV computation.
- No raw/row-level data or local path configuration committed.
- No claim that any candidate method is validated or selected.

## Stop boundary

Do not automatically enter Phase 2B-2. Candidate algorithms, held-out scoring, HRV and formal `J:\Data` remain unauthorized. A full 220-session historical-equivalence run requires separate authorization because it would touch the frozen held-out participants.
