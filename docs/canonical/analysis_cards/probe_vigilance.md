# Probe-vigilance-behavior association — method card

## Purpose

Define the scientific question and report role for Probe-vigilance-behavior association. This card records existing work only; it does not authorize a new exploratory run.

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
