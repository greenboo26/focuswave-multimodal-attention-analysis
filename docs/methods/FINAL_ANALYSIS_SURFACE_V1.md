# Final analysis surface V1

| ID | module | producer/ref | status | report role | rerun/entrypoint | boundary |
|---|---|---|---|---|---|---|
| M01 | protocol/site/repeat-session policy | `codex/protocol-identity-update-20260826@6e2eda0af827c7a6bff8056ec7d1e79bef955336`, `docs/decisions/2026-08-26-beijing-zhuhai-protocol-identity-harmonization.md` | CANONICAL_METHOD / GLOBAL_PENDING | methods/cohort policy | central reconciliation only | global identity/folds have no frozen producer |
| M01b | Beijing report cohort / C+B baseline | `codex/final-report-cohort-baseline-v2@414a4f46c8d058961a87750345d06a7129afc9f2` | CANONICAL_BEIJING | report anchor | reuse aggregate package | Beijing folds are not global folds |
| M02 | Probe labels and four-class validity | `67851bff212fc1e73b9611ac5de670581e316cc7` | CANONICAL_VALIDITY | primary validity | report runner | 2/3/4 not all mind-wandering |
| M03 | vigilance validity | same report runner | CANONICAL plus threshold sensitivity pending | primary validity | threshold diagnostic | ordinal/common-slope limitation |
| M04 | pre-Probe behavior and longitudinal/recovery | historical GPT handoff refs | SUPPORTING / rerun canonical | validity supplement | central behavior runner | preserve 10/20/30; no post-probe leakage |
| M05 | questionnaire convergence | `ba7a2c652bea82c3fa58ad5858a7460ed933fb47` | SUPPORTING with corrected semantic note pending | validity supplement | Q1 threshold sensitivity | not window-level ground truth |
| M06 | C+B canonical baseline | `414a4f46c8d058961a87750345d06a7129afc9f2` | CANONICAL_BEIJING_REPORT_BASELINE | anchor | reuse aggregate package | 30 s AUC ~.675, descriptive calibration only |
| M07 | mmWave validation boundary/frozen ablation | C1/C2B/C2C/M1 refs | SUPPORTING / STOPPED | boundary/supplement | no cosmetic rerun | not proof of hardware failure |
| M08 | NIR increment v1/recovery/v2 | external `nvidia-cuda@36a2d596c55b93071a8b5c80459a56c876c06351`, `amd-DirectML@d8e721079461ef7f71fafcd3edf819858fabbb16` | PRE_TIMESTAMP_RECOVERY / RECOVERABLE_PENDING_FULL_RECOVERY_QC_PROBE_ALIGNMENT | final sensor increment | Gate 0 then local production | 69/72 fullclass unchanged; 68/44/1360 is pre-recovery; sub-099 remains timeline blocker |
| M09 | RGB increment | external rgb refs | PIPELINE_ENGINEERING_PENDING | final sensor increment candidate | parity then frozen windows | formal stats not authorized |
| M10 | multimodal fusion/cross-site | central only | GLOBAL_PENDING | final report | complete common cohort | no global ID/folds before merge |

All modules must point to an exact producer, input schema, cohort, fold rule, output schema and interpretation boundary before entering `results/canonical/`.
