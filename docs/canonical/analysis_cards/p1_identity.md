# Identity/session master — method card

## Purpose

Define the scientific question and report role for Identity/session master. This card records existing work only; it does not authorize a new exploratory run.

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

- **Question:** 能否在跨盘合并前保留 participant-disjoint 所需身份证据
- **Producer:** scripts/audit_source_inventory.py plus central reconciliation adapter
- **Inputs / required columns:** analysis_tables_v2/subject_session_master_v2.csv; single_experiment_id, site, session_date_time, repeat_participant_id evidence
- **Cohort and unit:** session; local linkage evidence only
- **Model / validation:** no local global folds
- **Execution role and boundary:** colleague emits linkage evidence; central process freezes global repeat_participant_id and folds
- **Current evidence:** numbers and output files are limited to the referenced aggregate package or local manifest; no new result was generated in this correction pass.
