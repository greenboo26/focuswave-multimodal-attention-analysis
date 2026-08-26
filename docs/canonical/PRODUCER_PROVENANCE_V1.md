# Verified producer provenance v1

Producer mapping was checked against local worktree history and result manifests during the Sol correction pass.

| module(s) | producer | branch | commit | verification |
|---|---|---|---|---|
| REPORT_COHORT, FOUR_CLASS_PROBE, VIGILANCE, PROBE_VIGILANCE | `scripts/run_report_cohort_label_vigilance_v1.py` | `codex/report-cohort-label-vigilance-20260826` | `67851bff212fc1e73b9611ac5de670581e316cc7` | local Git history and output family |
| REPEAT_EFFECTS | `scripts/run_report_repeat_session_effects_v1.py` | `codex/report-repeat-session-effects-20260826` | `c2de2af3ba6fd46d351c4da4fcf05e281f982cff` | local Git history |
| Q1_QUESTIONNAIRE | `scripts/run_q1_questionnaire_criterion_validity.py` | `codex/q1-questionnaire-criterion-validity-20260826` | `ba7a2c6` | local Git history |
| BEHAVIOR_BASELINE / REPORT_COHORT baseline | `scripts/run_final_report_cohort_baseline_v2.py` | `codex/final-report-cohort-baseline-v2` | `414a4f46c8d058961a87750345d06a7129afc9f2` | manifest, 70/46/1400 and aggregate metrics |
| BEIJING_BEHAVIOR / PREPROBE_BEHAVIOR | `scripts/run_beijing_longitudinal_event_analysis_v1.py` / `scripts/run_beijing_preprobe_state_comparison_v1.py` | `codex/gpt-codex-handoff-20260825` | `97b236a` | local worktree and derived run manifests |

Other historical rows retain their local manifest/source provenance and are not silently upgraded to canonical producers. Missing producers remain explicitly unresolved where Sol allowed supporting-only retention.
