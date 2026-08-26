# Canonical entrypoints V1

| entrypoint | source ref/commit | role | status |
|---|---|---|---|
| report cohort, four-class, vigilance, Probe-vigilance | `codex/report-cohort-label-vigilance-20260826@67851bff212fc1e73b9611ac5de670581e316cc7` / `scripts/run_report_cohort_label_vigilance_v1.py` | Beijing validity family | canonical aggregate |
| C+B baseline | `codex/final-report-cohort-baseline-v2@414a4f46c8d058961a87750345d06a7129afc9f2` / `scripts/run_final_report_cohort_baseline_v2.py` | Beijing report anchor | canonical aggregate |
| questionnaire Q1 | `codex/q1-questionnaire-criterion-validity-20260826@ba7a2c652bea82c3fa58ad5858a7460ed933fb47` / `scripts/run_q1_questionnaire_criterion_validity.py` | convergent validity | supporting; corrected note pending |
| repeat-session robustness | `codex/report-repeat-session-effects-20260826@c2de2af3ba6fd46d351c4da4fcf05e281f982cff` / `scripts/run_report_repeat_session_effects_v1.py` | supporting control | supporting |
| pre-Probe/longitudinal behavior | historical GPT handoff refs | behavior validity supplement | supporting/rerun canonical |
| NIR local producer | external `Attention-Analysis@nvidia-cuda` / `@amd-DirectML` | standardized local derived/QC | Gate 0 required |
| RGB local producer | external rgb-nvidia/rgb-amd family | engineering derived/QC | formal analysis pending |
| fusion/cross-site | this repository central stage | global folds and final inference | global identity pending |

Historical scripts not listed above remain provenance references until a path/import audit authorizes physical migration.
