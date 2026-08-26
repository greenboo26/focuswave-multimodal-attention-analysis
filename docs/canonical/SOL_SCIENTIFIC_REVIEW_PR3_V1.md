# SOL_SCIENTIFIC_REVIEW_PR3_V1

Status: `CHANGES_REQUIRED_BEFORE_TEAMMATE_HANDOFF`

Review target: PR #3 `Canonicalize completed local analyses for competition pipeline`.

Review purpose: decide whether the analyses already completed on the primary workstation are scientifically reasonable, sufficiently specified, and safe to hand to a teammate for the same analysis on corresponding data. This review does not require every registered stage to be rerun before the scientific review can be completed.

## Executive decision

The repository architecture and the behavior mainline are usable. PR #3 is **not yet a teammate-ready frozen analysis release** because several analysis/contract defects would allow two machines to produce semantically inconsistent or biased results while still appearing schema-compatible.

Teammate handoff must therefore wait until the blocking items below are fixed and the reviewed branch is merged to `main`. The teammate should then clone/pull the reviewed `main` (preferably an exact release tag/commit), not `master` and not a permanent per-person branch.

## Stage-by-stage adjudication

| analysis_id | Sol verdict | teammate handoff | scientific role / required action |
|---|---|---|---|
| `report_cohort_v1` | `ACCEPT` | yes after PR merge | Canonical cohort/label/vigilance surface is internally consistent with `LABEL_SEMANTICS_V1`; participant-clustered models are suitable for report/supporting inference. |
| `behavior_longitudinal_v1` | `ACCEPT` | yes after PR merge | Repeated observations are clustered by `repeat_participant_id`; probe windows are pre-probe only; BH correction is explicit. Treat recovery aggregates as supporting analyses rather than a standalone primary endpoint. |
| `behavior_preprobe_v1` | `ACCEPT_SUPPORTING` | yes after PR merge | 10/20/30 s windows and 18-test BH family are explicit. Gaussian GEE on error-rate summaries is acceptable as a supporting contrast, not the main predictive baseline. |
| `behavior_baseline_v2` | `ACCEPT_PRIMARY_WITH_DOCUMENTATION_FIX` | yes after semantics note | 5-fold `StratifiedGroupKFold` is participant-disjoint; imputation/scaling/model fit are train-fold only; 30 s primary and 10/20 s sensitivity are prespecified. However the `b_rt_*` extraction rule is not identical to the longitudinal script's `valid_go_rt` rule. The handoff documentation must state that these are analysis-specific behavior features (or the feature definition must be unified and rerun); do not imply same-named RT fields are universally identical across stages. |
| `repeat_session_v1` | `ACCEPT_SUPPORTING_WITH_INFERENCE_CAVEAT` | yes, supporting only | Random-intercept handling is appropriate. VB logistic mixed-model normal-tail p-values and BH-adjusted versions are approximate; effect sizes/CIs should be primary in reporting, not confirmatory p-value claims. |
| `questionnaire_q1_v1` | `BLOCK` | no | Canonical label semantics are `3=task-unrelated thought` and `4=mind blank`, but the Q1 association plan labels 3 as mind blank and 4 as mind wandering. Fix the mapping and verify the upstream bridge columns before rerun/handoff. |
| `mmwave_c1_alignment_v1` | `DIAGNOSTIC_ONLY` | not as a final teammate analysis | The lag sweep optimizes lag against ECG-derived matching performance. It is valid as a diagnostic sensitivity analysis, but provenance must not state `ecg_used_for_tuning=false` without qualification. Record ECG use for diagnostic lag optimization and keep this out of final performance claims. |
| `mmwave_m1_v1` | `ACCEPT_SUPPORTING_ENGINEERING` | optional, if teammate has corresponding mmWave inputs | LOSO and train-fold preprocessing are sound. M1/Q0 may be reproduced as raw-signal/quality evidence. M2/M3/F1 contain explicitly experimental HR/BR/HRV-derived fields and must not be described as ECG-validated physiology or a final HRV result. |
| `mmwave_c2b_v2` | `BLOCK` | no | (1) `C+B+W` currently filters on mmWave availability but does not explicitly require behavior availability, so the fusion model can be trained on a different availability cohort than intended; use the intersection for a true matched fusion definition. (2) the report contains hard-coded Beijing result/count text (including fixed delta-AUC/group counts and legacy counts), which would produce false report text on another machine/dataset. Runtime call-signature bug was fixed separately, but that does not resolve these scientific/reproducibility defects. |
| `mmwave_c2c_v1` | `CONDITIONAL_ACCEPT_BLOCKED_BY_C2B` | no until C2B is fixed/rerun | The pre-task 180 s unlabeled baseline normalization is scientifically coherent for a personalized-calibration scenario, and participant-disjoint folds are preserved. It inherits C2B feature matrices, so it cannot be frozen for teammate use until the corrected C2B is rerun and accepted. |
| `beijing_sensor_increment_v1` | `BLOCK_SUPPORTING` | no | LOSO currently skips a held-out participant when that participant has only one target class. A single-class held-out fold can still receive predictions and should contribute to pooled OOF AUC; skipping it creates outcome-dependent evaluation selection and the reported `n_probe` no longer equals evaluated OOF rows. Fix before reuse. |

## Cross-stage semantic issue: behavior RT features

`behavior_longitudinal_v1` defines `valid_go_rt` using Go trials with a response and RT >= 150 ms. `behavior_baseline_v2` and C2B construct their `b_rt_*` summaries from non-null RT values without the same Go/threshold rule. This does not automatically invalidate either historical analysis, but it means the same-looking RT names do not currently form one universal feature contract.

Competition-first resolution: do not silently change accepted historical results. Before teammate handoff, either:

1. explicitly version/document the two RT feature definitions as analysis-specific, keeping historical outputs intact; or
2. choose one canonical RT definition, change the affected producer(s), and rerun the affected analyses under a new pipeline version.

For V1 speed, option 1 is preferred unless the competition report requires direct coefficient/feature-name equivalence across those stages.

## Dual-machine package / collector review

`MACHINE_PACKAGE_CONTRACT_V1` correctly requires matching analysis IDs, schema, merge keys and frozen parameters, and correctly forbids averaging AUCs/p-values across machines.

However, `collect_machine_packages.py` currently enforces only CSV column-sequence equality before concatenation. It does **not** reject packages whose stage manifests differ in `pipeline_version`, `producer`, `source_ref`, `frozen` parameters, `result_unit` or `merge_key`. Therefore two semantically different runs can currently be concatenated if their columns happen to match.

Before teammate handoff, collector compatibility must require the same scientific signature for each `analysis_id + relative_path` group. At minimum compare:

- `pipeline_version`
- `producer`
- `source_ref`
- canonicalized `frozen` parameter object
- `result_unit`
- `merge_key`

The collector should fail closed on any mismatch and record the verified signature in `combined_manifest.json`.

## Branch / teammate rule

- `main` is the only formal development/release base after this review is resolved.
- `master` is legacy rollback only and must not be used by the teammate.
- PR #3 remains a review branch until the blocking items above are corrected.
- After approval/merge, create a stable reviewed tag or record the exact `main` commit for competition replication.
- The teammate clones/pulls that reviewed `main`/tag and supplies only local path configuration and local data roots.
- If the teammate needs code changes, create a short-lived task branch from the reviewed `main`; do not maintain a permanent teammate-specific scientific branch.

## Minimum gate before PR #3 can become teammate-ready

1. Fix Q1 label-3/label-4 semantics and rerun Q1 aggregate outputs.
2. Fix C2B matched availability logic and remove hard-coded result/count reporting; rerun C2B before treating C2C as frozen.
3. Correct C1 provenance wording so ECG-guided lag optimization is explicit and diagnostic-only.
4. Fix sensor-increment held-out single-class participant handling before that supporting stage is reused.
5. Strengthen the collector to reject scientific-signature mismatch, not only schema mismatch.
6. Add/clarify the analysis-specific RT feature-definition note for V1.
7. Only then mark PR #3 ready, merge to `main`, and freeze the teammate handoff commit/tag.

## Current handoff subset if competition work must proceed immediately

Without waiting for the blocked sensor stages, the following can be prepared as the first teammate-reproducible bundle after the Q1 semantic correction/documentation update:

`report_cohort_v1 -> behavior_longitudinal_v1 -> behavior_preprobe_v1 -> behavior_baseline_v2 -> repeat_session_v1`

Q1 joins this set after its label mapping is corrected. mmWave C2B/C2C and the legacy sensor increment are not prerequisites for handing off the validated behavior pipeline.
