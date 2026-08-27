# V2 roadmap

## Phase 1 — asset audit and method network (current)

1. Register all local scripts, reports, datasets, benchmark outputs, literature and external implementations.
2. Separate executed evidence from narrative claims and unresolved provenance.
3. Freeze schemas, parameter provenance, benchmark metrics and stop rules.
4. Record open gaps; do not infer missing parameters or results.

## Phase 2 — benchmark implementation

1. Audit AgeBalanced/VS_DATASET access and exact schema.
2. Reproduce the existing baseline and at least two mature candidates on identical windows and QC.
3. Use ECG for HR/beat validation and RSP for BR validation; do not claim BR where RSP is absent.
4. Freeze an aggregate benchmark manifest and method selection decision.

## Phase 3 — own calibration data

Validate BR and HR symmetrically on the self-collected ECG/RSP calibration assets, including synchronization, ECG/RSP quality and device-specific sampling/timestamp rules.

## Phase 4 — formal cohort audit and application

Only after Phase 2/3 gates pass: target-lock, motion, timestamp, range-bin stability and usable-window coverage; then apply frozen methods with explicit per-window status and no silent interpolation.

## Phase 5 — science and product lines

Keep physiology x attention inference separate from mmWave-only deployment modeling. Signal-only radar features remain supporting evidence and must not be renamed HR/BR/HRV.
