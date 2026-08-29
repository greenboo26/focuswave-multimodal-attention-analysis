# FocusWave formal matched cohort v1 audit

Status: `FROZEN_PRIMARY_MATCHED_COHORT`

Definition: Behavior observed AND NIR observed AND RGB observed. The inclusion mask uses only modality observation flags and the canonical five-column key; it does not use the probe label, response, response time, or any outcome-derived field.

- Full canonical timeline: **1440 rows / 72 sessions / 46 repeat participants**.
- Primary matched cohort: **1295 rows / 65 sessions / 46 repeat participants**.
- Excluded from primary matched: **145 probes across 8 sessions**.
- Primary window: `pre_30s = [probe_onset_unix_ms-30000, probe_onset_unix_ms)`.
- Full timeline remains preserved in `canonical_probe_timeline.csv`; it is not overwritten by the matched table.

## Excluded sessions

| session_id | excluded probes | reason |
|---|---:|---|
| sub-086 | 20 | OBSERVED, STRUCTURAL_MISSING |
| sub-087 | 20 | OBSERVED, STRUCTURAL_MISSING |
| sub-088 | 20 | OBSERVED, STRUCTURAL_MISSING |
| sub-089 | 20 | OBSERVED, STRUCTURAL_MISSING |
| sub-091 | 20 | OBSERVED, STRUCTURAL_MISSING |
| sub-090 | 20 | OBSERVED, STRUCTURAL_MISSING |
| sub-099 | 20 | STRUCTURAL_MISSING |
| sub-083 | 5 | OBSERVATION_MISSING, OBSERVED |

## Participant coverage after matching

- Participants with at least one matched session: **46**.
- Participants with zero matched probes: **none**.
- Participants with partial session coverage: **R030, R048, R049, R069, R070, R071, R072**.
- Participants with partial block coverage: **R030, R048, R049, R069, R070, R071, R072**.

## Validation

All canonical keys are non-null and unique; all matched keys are members of the 1,440-row timeline; the expected 1,295-row count is met; no label-dependent filtering was used.

The one NIR `QC_FAIL` observation (`sub-084`, `block-1`, `probe-06`) remains in the observation-defined matched denominator with NaN pupil geometry. Any later model fit must use an explicit missing-value policy and must not silently delete this row.
