# MACHINE_PACKAGE_CONTRACT_V1

Status: `ACTIVE_FOR_COMPETITION_PIPELINE_V1`

This contract defines the file interface between FocusWave analysis machines. It does not require both machines to have processed every modality at the same time.

## Package root

Each machine exports:

```text
<root>/focuswave_canonical_v1/<machine_id>/<analysis_id>/
```

Required stage files:

- `stage_manifest.json`
- `producer_output/`
- `aggregate/`
- `merge_ready/` when the registry declares merge-ready artifacts.

The machine root also contains `machine_package_manifest.json`.

## Stage manifest required fields

`schema_version`, `pipeline_version`, `analysis_id`, `machine_id`, `site`, `status`, `science_change`, `producer`, `source_ref`, `role`, `frozen`, `result_unit`, `merge_key`, `aggregate_artifacts`, `merge_ready_artifacts`, `merge_ready_policy`, `completed_at_utc`.

`science_change` must be `false` for the V1 competition pipeline.

## Merge-ready rules

1. `analysis_id` must match the central registry.
2. The declared CSV column sequence must be identical across machine packages before concatenation.
3. Existing semantic keys are not rewritten on import. The collector adds `_source_machine_id` and `_source_site`.
4. Pseudonymous row-level derived tables are secure-transfer artifacts and must not be committed to Git.
5. Missing stages are allowed. A machine can deliver behavior later even if it currently only has NIR or another modality.
6. Final pooled/site-held-out modeling is rerun from combined merge-ready inputs. Final AUCs, p-values or coefficients from two machines are not averaged.

## Standard merge keys

The registry owns the merge key for each analysis. Current keys include the stable available subset of:

- `site`
- `session_id` / `subject`
- `repeat_participant_id`
- `probe_onset_time` / `probe_onset_ms`
- `probe_id` / `probe_seq`

A stage must not invent a new identity mapping to satisfy this contract.

## Versioning

V1 package paths use `focuswave_canonical_v1`. Any scientific change to labels, primary window, feature definition, cohort rule, fold rule, or model family requires a new pipeline version rather than silently changing V1.
