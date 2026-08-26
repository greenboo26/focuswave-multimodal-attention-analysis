# Beijing-Zhuhai D1 harmonization — method card

## Purpose

Define the scientific question and report role for Beijing-Zhuhai D1 harmonization. This card records existing work only; it does not authorize a new exploratory run.

## Inputs

Exact local inputs, fields, upstream RUN_ID, input/output roots and status are in `ANALYSIS_REGISTRY_V1.csv` and the referenced local manifest. Canonical key: `site + session + probe_id`; participant grouping: `repeat_participant_id`.

## Software / Environment

Windows; repository scripts and `requirements.txt`. Missing package/model/config digests remain unresolved and are not inferred.

## Procedure

Audit path and schema; verify identity, time unit, cohort and QC; invoke only the registered script; emit a manifest and output list; never overwrite existing evidence.

## Statistical specification

Use the registry's sample unit, cohort, window, CV/fold, repeated-measures, preprocessing and CI rules. Engineering/planned entries have no executed statistical model.

## QC / exclusions

Record pass/uncertain/reject and missingness. Unresolved identity cannot enter participant-level LOSO. Exclusions must be traceable and do not delete evidence.

## Outputs

Exact output files and schemas are in the local manifest. Raw/row-level data, NPZ/MAT/BIN/AVI, large images and model caches are local-only.

## Result reporting template

Report n participant/session/probe, cohort, missingness, model/window/QC, estimate or metric, 95% CI, p/q where applicable, status, and the forbidden interpretation.

## Current result

Use only the actual local report/manifest for numbers. No number is invented here; status is the registry status.

## Repro command

Read-only preflight: `python scripts/canonical/audit_local_analysis_library.py --repo . --derived-root <derived-root> --output work/local_library_audit.json`. Formal rerun is `NEEDS_PARAMETERIZED_ENTRYPOINT` when the registry points to a historical or unstable entry.

## Correction-pass verified contract

- **Question:** Beijing/Zhuhai 是否能在共享 contract 下合并
- **Producer:** scripts/audit_crossmodal_time_gate.py plus D1 manifest
- **Inputs / required columns:** beijing_zhuhai_canonical_harmonization_v1; site, phase, program_family, session/probe keys
- **Cohort and unit:** Beijing B1+B2 primary; Zhuhai B1+B2 shared primary; B3 extension
- **Model / validation:** harmonization/coverage audit, global inference central
- **Execution role and boundary:** DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE
- **Current evidence:** numbers and output files are limited to the referenced aggregate package or local manifest; no new result was generated in this correction pass.
