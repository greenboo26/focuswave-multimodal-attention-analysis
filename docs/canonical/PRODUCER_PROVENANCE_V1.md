# Verified producer provenance v1

Producer mapping was checked against local worktree history and result manifests during the Sol correction pass.

| module(s) | producer | branch | commit | verification |
|---|---|---|---|---|
| REPORT_COHORT, FOUR_CLASS_PROBE, VIGILANCE, PROBE_VIGILANCE | aggregate successor `results/canonical/REPORT_LABEL_VIGILANCE_VALIDITY.md` | `archive/20260826/report-cohort-label-vigilance` | `67851bff212fc1e73b9611ac5de670581e316cc7` | preserved producer tag and output family |
| REPEAT_EFFECTS | supporting successor | `archive/20260826/report-repeat-session-effects` | `c2de2af3ba6fd46d351c4da4fcf05e281f982cff` | preserved producer tag |
| Q1_QUESTIONNAIRE | supporting successor | `archive/20260826/q1-questionnaire-criterion-validity` | `ba7a2c652bea82c3fa58ad5858a7460ed933fb47` | preserved producer tag |
| BEHAVIOR_BASELINE / REPORT_COHORT baseline | aggregate successor `results/canonical/BEIJING_C_B_BASELINE_V2.md` | `archive/20260826/final-report-cohort-baseline-v2` | `414a4f46c8d058961a87750345d06a7129afc9f2` | manifest, 70/46/1400 and aggregate metrics |
| BEIJING_BEHAVIOR / PREPROBE_BEHAVIOR | historical supporting provenance | `archive/20260826/retired/codex-gpt-codex-handoff-20260825` | `4e0f1aaa195f8346df4794da03527f383bf05db0` | immutable archive only; no current executable |

Other historical rows retain their local manifest/source provenance and are not silently upgraded to canonical producers. Missing producers remain explicitly unresolved where Sol allowed supporting-only retention.
