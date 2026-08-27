# MMWAVE_FORMAL_REANALYSIS_V2

Status: `PARTIAL / PHASE_1_ASSET_AUDIT_COMPLETE`

This is an additive, Git-safe reanalysis surface. It does not replace or rewrite the historical C1, M1, C2B, C2C, v1-v9, C1b or formal-cohort results. Raw participant data, videos, NPZ/MAT/BIN/AVI, caches and machine-local path files remain outside Git.

## Scope

The scientific chain is staged as:

`BR benchmark -> HR benchmark with explicit respiratory-harmonic handling -> HRV gate -> formal cohort audit -> physiology x attention -> separate product modeling`

No formal cohort HR/BR output is authorized before external ECG/RSP benchmark gates are frozen. HRV remains `BLOCKED` until beat/IBI validation passes the predeclared coverage and error gates.

## Phase 1 decision

- Existing project assets are sufficient to define the audit and benchmark interfaces.
- Historical evidence is heterogeneous: some results have scripts and aggregate outputs; others have missing parameters, missing raw inputs or only narrative claims.
- Current implementation choices are adoption/adaptation candidates, not validated winners.
- Current completion state is `PARTIAL`; no new scientific result was generated in this phase.

## Index

- [ROADMAP.md](ROADMAP.md)
- [EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md)
- [DATASET_MATRIX.md](DATASET_MATRIX.md)
- [METHOD_MATRIX.md](METHOD_MATRIX.md)
- [PARAMETER_REGISTRY.md](PARAMETER_REGISTRY.md)
- [FAILURE_MODE_REGISTRY.md](FAILURE_MODE_REGISTRY.md)
- [BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)
- [VALIDATION_GATES.md](VALIDATION_GATES.md)
- [FORMAL_COHORT_PLAN.md](FORMAL_COHORT_PLAN.md)
- [OPEN_GAPS.md](OPEN_GAPS.md)
- [HANDOFF.md](HANDOFF.md)
- [configs/mmwave_reanalysis_v2/manifest.json](../../configs/mmwave_reanalysis_v2/manifest.json)

## Evidence vocabulary

`CANONICAL` = accepted current evidence with traceable provenance; `SUPPORTING` = boundary/robustness evidence; `EXPLORATORY` = trial or development evidence; `SUPERSEDED` = retained historical evidence replaced by a later decision; `BLOCKED` = cannot be used for the stated claim; `MISSING_EVIDENCE` = the reported action/result cannot currently be reconstructed.
