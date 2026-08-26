# Dual-machine analysis contract V1

This contract is the boundary between local NIR/RGB production and central FocusWave inference. It is the current repository contract; global identity, global folds and final inference remain centrally gated.

## Local machine may do

- discover only its authorized local raw roots and export stable session keys;
- produce standardized NIR/RGB derived features, timestamps, gaps, coverage and QC;
- export local linkage evidence, `identity_status`, source manifest and aggregate QC;
- run the executable Gate 0 parity check for its backend;
- package Git-safe derived outputs without row-level participant data unless separately authorized.

## Local machine must not do

- invent an authoritative `global_repeat_participant_id`;
- freeze the global cohort or global participant-disjoint folds;
- calculate final pooled/site-held-out p-values or AUCs independently;
- average final results from AMD and NVIDIA;
- tune windows, thresholds, feature definitions or model complexity after viewing outcome performance;
- start bulk production when Gate 0 fails or required provenance is missing.

## Central-only flow

`local raw -> local standardized derived/QC package -> central identity reconciliation -> global_repeat_participant_id -> global cohort -> global folds -> final inference/report`.

The local package uses a stable `site + session_id/single_experiment_id`, a `local_participant_linkage_key` when deterministically available, `identity_status`, and optional `local_repeat_participant_id` explicitly marked provisional. A field named `repeat_participant_id` is not authoritative unless `id_scope=global_central` is present.

## Required provenance fields

Every package, runner manifest and report aggregate must include:

`machine_role`, `runtime_backend`, `pipeline_version`, `git_commit`, `model_hash`, `config_hash`, `schema_version`, `source_manifest_hash`.

Additional required fields are `site`, `session_key`, `input_root_alias`, `output_root_alias`, `timestamp_policy`, `gap_policy`, `qc_policy`, `resume_policy`, `overwrite_policy`, and `identity_status`.

## Window rules

- C+B behavior baseline: 30 s primary, 10/20 s sensitivity.
- NIR increment: 30 s primary, 10/60 s sensitivity.
- Existing mmWave analyses retain executed 10/30/60 s definitions.
- RGB window rule must be frozen before prediction modeling; no AUC-driven selection.
- Multimodal primary comparison uses the exact matched common cohort at predeclared 30 s.
