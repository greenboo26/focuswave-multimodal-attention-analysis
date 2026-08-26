# Final repository tree V1

The FocusWave mainline is the canonical central analysis repository. The tree contains Git-safe contracts, schemas, executable/adaptor surfaces, aggregate results, provenance and governance. Raw data, participant-level rows, NPZ/MAT/BIN/AVI files, caches, credentials and machine-private absolute paths are excluded.

## Current surface

```text
README.md
PROJECT_STATUS.md
configs/                 frozen cohort/window/model configuration
contracts/               identity, sensor, multimodal and fusion contracts
schemas/                 derived/QC/central merge field conventions
pipelines/               modality and central adaptor indexes
scripts/                 current tools and canonical audit entrypoints
tests/                   lightweight schema/path/contract smoke checks
results/canonical/       approved aggregate result entrypoints
results/supporting/      supporting and boundary evidence
results/engineering_reference/  producer/QC readiness references
results/superseded_index/        non-current result index
docs/methods/            current analysis surface and methods
docs/provenance/         cross-repository refs and evidence boundaries
docs/repository/         architecture, contracts, cutover and retirement ledgers
docs/research/           retained technical evidence and research references
docs/archive/            curated historical hardware and superseded references
```

## Stage 2C cleanup accounting

- 57 scripts with 97 legacy absolute-path hits were removed from the browsable main tree because they were `LEGACY_PROVENANCE_ONLY`; their contents remain recoverable from `archive/20260826/pre-stage2c-main` and earlier immutable tags.
- The historical `scripts/archive_历史版本/` tree and superseded mmWave-only delivery, handoff, report, plan, handbook, system, project-management and decision trees were removed after curated successors were added.
- PR #1 hardware evidence is curated at `docs/archive/hardware/RS6240_FORMAL_FIRMWARE_MULTICHANNEL_PLAN_20250825.md`.
- PR #2 valuable evidence is curated at `results/supporting/LU_YIMIN_V3_4_1_ECG_RSP_REFERENCE.md`, `results/engineering_reference/nir/NIR_FEATURE_CONTRACT_DIAGNOSTIC_V2.md` and `docs/archive/superseded/PR2_MULTIMODAL_STATUS_REFERENCE_20260826.md`.
- The pre-cleanup tree is recoverable from `archive/20260826/pre-stage2c-main` at `579f6abcefc86363f62b8abccbac85e87d1a14e8`.

## Scientific boundary

The cleanup changes repository navigation and provenance only. It does not create global identity/folds, rerun NIR recovery, authorize RGB formal analysis, or promote mmWave cardiac candidates to HRV results.
