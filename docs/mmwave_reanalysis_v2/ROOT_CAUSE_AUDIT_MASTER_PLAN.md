# mmWave HR Root-Cause Audit — Master Plan

Status: `IN_PROGRESS_PARALLEL`
Date: 2026-08-27
Branch: `codex/mmwave-formal-reanalysis-v2`

## Why this audit exists

Current results show a large discontinuity that must be explained before any final decision on HR physiology:

- historical 25 s development-equivalent result: session-MAE median about 9.14 BPM;
- current 30 s unified benchmark: MAE about 26.98 BPM;
- 50 s project route: MAE about 29.02 BPM;
- 60 s project route in Task 2S: MAE about 37.12 BPM;
- external/adapted routes did not materially improve this.

This pattern is too large to treat as ordinary algorithm variance. The immediate goal is diagnosis, not another algorithm trial.

## Parallel workstreams

### A. Benchmark-discontinuity root-cause audit

Goal: explain how the same project lineage moves from ~9 BPM historical 25 s performance to ~27–37 BPM under current benchmark conditions.

Must isolate, one factor at a time:

1. radar input semantics and units;
2. historical vs current adapter logic;
3. 25/30/50/60 s window construction and edge/session inclusion;
4. historical ECG scorer vs `ecg_reference_v1`;
5. metric aggregation (window-level pooled MAE vs session-level MAE median);
6. range-bin selection / multi-bin voting / phase handling;
7. frequency axis, sample-rate, decimation and phase-difference alignment;
8. quality gate and trajectory/harmonic corrections;
9. exact development session overlap across reported results.

Required artifact: a factorized A/B matrix on the same sessions and same ECG reference wherever mathematically possible. No new HR algorithm family.

### B. Existing-asset and failure-evidence audit

Goal: prevent reimplementation of methods already tried or already known to fail under specific conditions.

Sources to inspect:

- current canonical central analysis repository;
- historical commits/scripts/results referenced by `EVIDENCE_LEDGER.md`;
- `CHANGELOG.md`, historical v1–v9/v3.1/v3.1.1/AgeBalanced routes;
- acquisition implementation in `kyandi233-dev/FocusWave`, especially `ecg` and `stable-msmf` branches;
- legacy `mmwave-hrv-analysis` only if actually accessible; registry marks it legacy and non-canonical.

Known failure modes that must be traced to code/results rather than rediscovered: respiratory 2x/3x harmonic lock, strongest-bin clutter/multipath, VMD mode instability, phase/time alignment, motion, single-bin lack of spatial redundancy, ECG T-wave double detection.

### C. Improvement-priority audit

Goal: identify only low-cost, root-cause-matched improvements after A/B diagnosis.

Candidate directions are not authorized by default. They are ranked only after the failure is localized. Priority logic:

1. fix benchmark/input/reference bug if present;
2. reuse an existing project implementation if the failure mode was already solved historically;
3. apply one targeted fix to the identified failure mode;
4. only then consider an external method family.

No algorithm fishing.

## Current evidence anchors

- Stable registry identifies `greenboo26/focuswave-multimodal-attention-analysis` as canonical central analysis and `kyandi233-dev/FocusWave` as acquisition truth. `mmwave-hrv-analysis` is legacy.
- Existing failure registry already records respiratory-harmonic lock, range-bin/clutter risk, VMD mode instability, beat-timing mismatch, movement effects and sparse/single-bin limitations.
- Evidence ledger records historical v1–v8 comparisons, v3.1/v3.1.1 calibration, seven prior A/B trials, AgeBalanced v1.7 historical validation and current benchmark contracts.
- Acquisition `ecg` branch records RS6240 raw complex IQ + timestamps, 2T4R, 256 range FFT, ~10 ms frame period (~100 fps), 57 GHz start frequency and 37 mm range resolution in the current capture module. This hardware/acquisition truth is distinct from the 10 Hz AgeBalanced derived radar representation.

## Stop condition

This audit must end with one of three decisions:

- `BENCHMARK_OR_ADAPTER_DEFECT`: fix the defect and re-evaluate the existing project route;
- `LOCALIZED_SIGNAL_PROCESSING_DEFECT`: authorize exactly one targeted repair using existing assets first;
- `CONFIRMED_METHOD_LIMITATION`: input/reference/aggregation are clean and the project route genuinely fails, then stop HR R&D for the competition.

80-person heldout remains untouched during this audit.

## Completion vocabulary

`PASS / PARTIAL / BLOCKED`.
