# M1 mmWave person-effect variance audit

## Final decision: `C LIMITED_STABLE_PERSON_EFFECT_IN_CURRENT_FEATURES`

This is a diagnostic of the frozen 30-s C2b-v2/C2C W feature family, not a physiological identity claim or a predictive-model result.

## Inputs and identity

- C2b-v2 input: `D:\Project\厚粲杯\11_数据\derived\c2b_v2_canonical_baselines_20260826\window_30s\canonical_feature_matrix_local.csv` (1440 rows).
- C2C input: `D:\Project\厚粲杯\11_数据\derived\c2c_within_subject_normalization_v1\c2c_feature_matrix_local_30s.csv` (1440 rows total; 1180 existing within-calibrated rows from 59 sessions and 42 participants); C2C CURRENT primary window is 30 s.
- Identity convention fixed by C2b/C2C: `group_subject_id` = repeat participant; `subject` = formal session. The audit retains these only locally and exports no identifiers.
- Feature family: 21 pre-existing m1/q probe features; missing values are listwise excluded feature-by-feature, never re-extracted or imputed for variance components.

## Three-level variance decomposition

For each feature, REML linear mixed model: `feature ~ 1 + (1|repeat_participant_id) + (1|repeat_participant_id:session_id)`. Residual is within-session/probe variance. ICC_person is participant variance / total variance; session proportion is session-within-person variance / total variance.
- C2b-v2 all-session absolute ICC: median 0.076, IQR [0.039, 0.160] across 21/21 estimable features.
- Highest all-session absolute ICC: `m1_log_power_transition` = 0.381. Near-zero (ICC < .01): q_frame_gap_fraction, q_frame_rate_hz.

## Calibration comparison on the same C2C-covered probe cohort

- Median ICC_absolute = 0.062; median ICC_within = 0.068; median ΔICC (within - absolute) = -0.028.
- Strongest absolute feature in the common cohort: `m1_log_power_transition` (absolute 0.367, within 0.000, Δ -0.367).

## Context-adjusted sensitivity

The sensitivity model adds frozen block as a categorical fixed effect and `block_probe_fraction` as within-block/experiment progress. It intentionally removes predictable task context before allocating residual stable between-person variation.
- Median absolute ICC: raw 0.076, context-adjusted 0.076; change +0.000.

## Cross-session centroid geometry

Centroids are session means of the 21 absolute features after robust global (median/MAD) feature scaling. Distances and correlations are descriptive, not identity-classifier accuracy.
- Eligible repeat participants (>=2 formal sessions): 14.
- Within person: 20 pairs, median distance 3.248, median cosine 0.871, median profile correlation 0.850.
- Between person: 1691 pairs, median distance 4.635, median cosine 0.751, median profile correlation 0.759.

## Limits

- C2C baseline extraction covered 70/72 sessions, but the all-21-feature complete within-z comparison has 59 sessions because a zero/missing session MAD makes at least one within-z undefined. This deterministic availability restriction is reported rather than repaired or imputed.
- Variance components are feature-wise Gaussian mixed-model summaries. Features with non-convergence are retained with an explicit caution status; failed estimates are not silently replaced.
- Baseline robust-z calibrates against a session's own resting distribution. A lower ICC therefore indicates reduced stable scale/location differences in these features, not proof that all person-specific signal has disappeared.
