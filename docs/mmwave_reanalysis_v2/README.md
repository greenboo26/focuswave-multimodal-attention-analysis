# MMWAVE_FORMAL_REANALYSIS_V2

Status: `PASS / PHASE_2A_BENCHMARK_CONTRACT_FROZEN`

This is an additive, Git-safe reanalysis surface. It does not replace or rewrite the historical C1, M1, C2B, C2C, v1-v9, C1b or formal-cohort results. Raw participant data, videos, NPZ/MAT/BIN/AVI, caches and machine-local path files remain outside Git.

## Scope

The scientific chain is staged as:

`BR benchmark -> HR benchmark with explicit respiratory-harmonic handling -> HRV gate -> formal cohort audit -> physiology x attention -> separate product modeling`

No formal cohort HR/BR output is authorized before external ECG/RSP benchmark gates are frozen. HRV remains `BLOCKED` until beat/IBI validation passes the predeclared coverage and error gates.

## Phase 2A decision

- Phase 1 remains preserved and was not repeated.
- AgeBalanced 110-participant / 440-session provenance and the historical 220 Rest-session scope are reconciled with immutable hashes.
- Participant split, windows, reference QC, synchronization, quality strata, metrics, harmonic-lock definitions, numeric gates and algorithm selection are frozen before held-out scores.
- A strict per-window schema and tests now bind every later method to one output contract.
- No historical baseline or candidate benchmark was run. Phase 2B is not authorized by this commit; HRV and formal cohort execution remain blocked.

## Index

- [ROADMAP.md](ROADMAP.md)
- [EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md)
- [DATASET_MATRIX.md](DATASET_MATRIX.md)
- [METHOD_MATRIX.md](METHOD_MATRIX.md)
- [PARAMETER_REGISTRY.md](PARAMETER_REGISTRY.md)
- [FAILURE_MODE_REGISTRY.md](FAILURE_MODE_REGISTRY.md)
- [BENCHMARK_PLAN.md](BENCHMARK_PLAN.md)
- [BENCHMARK_DECISION_V1.md](BENCHMARK_DECISION_V1.md)
- [VALIDATION_THRESHOLD_JUSTIFICATION.md](VALIDATION_THRESHOLD_JUSTIFICATION.md)
- [REFERENCE_AUDIT_V1.md](REFERENCE_AUDIT_V1.md)
- [REUSE_IMPLEMENTATION_AUDIT_V1.md](REUSE_IMPLEMENTATION_AUDIT_V1.md)
- [VALIDATION_GATES.md](VALIDATION_GATES.md)
- [FORMAL_COHORT_PLAN.md](FORMAL_COHORT_PLAN.md)
- [OPEN_GAPS.md](OPEN_GAPS.md)
- [HANDOFF.md](HANDOFF.md)
- [configs/mmwave_reanalysis_v2/manifest.json](../../configs/mmwave_reanalysis_v2/manifest.json)
- [per_window_benchmark_v1.schema.json](../../schemas/mmwave/per_window_benchmark_v1.schema.json)

## Evidence vocabulary

`CANONICAL` = accepted current evidence with traceable provenance; `SUPPORTING` = boundary/robustness evidence; `EXPLORATORY` = trial or development evidence; `SUPERSEDED` = retained historical evidence replaced by a later decision; `BLOCKED` = cannot be used for the stated claim; `MISSING_EVIDENCE` = the reported action/result cannot currently be reconstructed.
