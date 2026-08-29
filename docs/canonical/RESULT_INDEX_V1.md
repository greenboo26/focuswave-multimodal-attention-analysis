# Result index v1

This index points to local full results without uploading them. See `ANALYSIS_REGISTRY_V1.csv` for the complete 29-entry table.

| analysis_id | status | Git description | local full result path | report use |
|---|---|---|---|---|
| FORMAL_MULTIMODAL_ATTACH_20260830 | PARTIAL / structural V2 merge-ready PASS | [current mother-table attach evidence](../results/2026-08-30_FORMAL_MULTIMODAL_ATTACH/) | `C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave\outputs\FocusWave_formal_multimodal_v2_2026-08-30` | 72-session / 46-group / 1,440-probe current attach; NIR 1,295 observed, RGB 1,420 observed; no model or physiology promotion |
| FORMAL_MULTIMODAL_MODEL_READY_V1_20260830 | PASS_MODEL_READY | [formal matched cohort, LOSO, feature contracts, and readiness gate](../results/2026-08-30_FORMAL_MODEL_READY_V1/) | `C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave\outputs\FocusWave_formal_multimodal_v2_2026-08-30` | 1,295 probes / 65 sessions / 46 repeat participants; 46 participant-disjoint folds; Behavior=5, NIR=4, RGB=6; baseline modeling authorized, no model run |
| MMWAVE_NEXT_EXECUTION_20260830 | PARTIAL / #16 PAUSED | ordered device-firmware, continuity, harmonic-activation, and HRV-blocker audit; [evidence matrix](../research/MMWAVE_DEVICE_FIRMWARE_ENGINEERING_EVIDENCE_2026-08-30.csv) | `D:\Project\厚粲杯\11_数据\derived\j_mmwave_target_lock_audit_v1` plus existing formal JSON/NPZ outputs | engineering/evidence boundary only; no new formal batch and no validated HRV claim |
| P0_PROTOCOL | MATCHED_SUPPORTING | [protocol method card](analysis_cards/p0_protocol.md); historical producer script unavailable | `D:\Project\厚粲杯\11_数据\derived\probe_program_version_audit_v1` | protocol/version evidence only; no new number inferred |
| BEIJING_BEHAVIOR | VALID_SUPPORTING | manifest/report schema only | `D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1` | behavior results with diagnostics/FDR caveat |
| BEHAVIOR_BASELINE | CANONICAL_BEIJING_REPORT_BASELINE | [aggregate baseline package](../results/final_report_cohort_baseline_v2) | `D:\Project\厚粲杯\11_数据\derived\final_report_cohort_baseline_v2` | current Beijing C+B anchor, 70/46/1400 |
| CONTEXT | MATCHED_SUPPORTING | [behavior/context baseline report](../results/final_report_cohort_baseline_v2/FINAL_BEHAVIOR_CONTEXT_BASELINE_V2.md) | `D:\Project\厚粲杯\11_数据\derived\final_report_cohort_baseline_v2` | context-only ROC-AUC 0.593; Beijing baseline only |
| PREPROBE_BEHAVIOR | VALID_SUPPORTING | [Probe-before aggregate package](../results/preprobe_behavior_validity) | `D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1` | objective behavior validity |
| C2B_V2 | VALID_SUPPORTING | canonical candidate contract | `D:\Project\厚粲杯\11_数据\derived\c2b_v2_canonical_baselines_20260826` | mmWave baseline, not final multimodal |
| Q1_QUESTIONNAIRE | VALID_SUPPORTING | criterion report pointer | `D:\Project\厚粲杯\11_数据\derived\questionnaire_criterion_validity_v1` | questionnaire evidence with criterion limit |
| M1 | VALID_SUPPORTING | person-effect audit pointer | `D:\Project\厚粲杯\11_数据\derived\m1_mmwave_person_effect_variance_audit_v1` | limitation/diagnostic |
| D1_HARMONIZATION | PLANNED_NOT_EXECUTED | cross-site contract pointer; external storage unavailable | `D:\Project\厚粲杯\11_数据\derived\beijing_zhuhai_canonical_harmonization_v1` | no executed cross-site result; future harmonization task |
| C1_ALIGNMENT | BLOCKED_EXTERNAL_STORAGE | blocker and protocol record | `D:\Project\厚粲杯\11_数据\derived\c1_alignment_protocol_repair_v1` | not usable for HRV claim |
| C3A_V1/C3A_V2/NIR_69 | ENGINEERING_ONLY | engineering manifests | `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR` | not final NIR increment |
| NIR_INCREMENT | PRODUCER_NOT_READY | 14-participant formal producer report exists; no global final matched-cohort report | `D:\Project\厚粲杯\11_数据\derived\c3a_formal_nir_full_available_results_v2` | producer evidence is not the global final increment |
| RGB_INCREMENT | PRODUCER_NOT_READY | raw/context engineering only; no formal RGB incremental model | RGB producer status and availability manifests | wait for producer derived-window features/model |
| MULTIMODAL_FUSION/CROSS_SITE | PLANNED_GLOBAL_ONLY | no final result | readiness manifests only | future work; not a reconciliation failure |

All local paths are external to Git and must be checked on the executing machine.

## 2026-08-29 local-analysis assimilation evidence

The following small reports, summaries, and manifests were assimilated from the
old dirty worktree. Large matrices, waveform files, frame-level outputs, and
PNGs remain local-only.

| analysis | status | canonical report/index | local output or input boundary | conclusion / decision | provenance |
|---|---|---|---|---|---|
| C1c mmHRV pilot | VALIDATION_STOPPED | `../results/c1_pilot/C1C_PILOT_REPORT.md` | `D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1` | no clear improvement; do not claim HRV validation | `pipelines/mmwave/run_c1c_mmhrv_pilot.py` |
| C1d RadarBeat backend pilot | VALIDATION_STOPPED | `../results/c1_pilot/C1D_PILOT_REPORT.md` | same C1c fixed-waveform local boundary | F1 decreased on the pilot; stop this development cycle | `pipelines/mmwave/run_c1d_radarbeat_backend_pilot.py` |
| C2a dataset audit | SUPPORTING_AUDIT | `pipelines/mmwave/audit_c2a_dataset.py` | local C2a/mmWave derived tables | audit entrypoint only; no new scientific claim | `pipelines/mmwave/audit_c2a_dataset.py` |
| C2b task-focus baselines | SUPPORTING_AUDIT | `pipelines/mmwave/run_c2b_task_focus_baselines.py` | local C2b derived tables | exploratory baseline; not final multimodal inference | `pipelines/mmwave/run_c2b_task_focus_baselines.py` |
| Issue #13 psychometric evidence | REVISE_METHOD | `scripts/build_psychometric_evidence_matrix_v1.py` | local questionnaire/behavior aggregates | corrected label semantics; old label-3/4 matrix is superseded | generator plus `pipelines/questionnaire/run_q1_questionnaire_criterion_validity.py` |
| formal physiology / QC | PARTIAL | `../results/mmwave_formal_vital_qc_v1/` | local formal mmWave + BIOPAC reference outputs | QC strata only; not a validated vital-sign tier | `scripts/maintenance/build_formal_vital_qc_v1.py` |
| MMWAVE_PIPELINE_AUDIT | SUPPORTING_AUDIT_COMPLETE_BOUNDED | `../research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`; field-complete audit CSV and gaps/flowchart in the same directory | `D:\Project\厚粲杯\08_算法\docs\results\2026-08-29_RS6240距离与DataCube审计_v1\` and local SDK assets | evidence/source audit complete; formal image is 1D Range-FFT DataCube; calibration, timing, target continuity and HRV remain bounded | `../research/MMWAVE_LITERATURE_VS_PROJECT_STAGE_MATRIX_2026-08-29.csv` |
| B1 corrected-distance audit | CLOSED_WITH_EXPLICIT_BOUNDARIES | `../results/mmwave_formal_vital_qc_v1/MMWAVE_FORMAL_VITAL_QC_V1_CLOSURE_2026-08-29.md` | local corrected 37 mm tables | current QC tiers are 33/37/2; scientific use remains quality-bound | `scripts/maintenance/rebuild_readiness_matrices_20260829.py` |
| B2 extreme-range audit | PRELIMINARY | existing BR/range-gate report family | local extreme-range QC tables | no upgrade of physiology conclusions | `scripts/maintenance/B2_extreme_range_target_audit_20260829.py` |
| merge readiness / denominator | PARTIAL | `../results/final_merge_readiness_20260829/FINAL_MERGE_READINESS_20260829.md` | local availability/missingness matrices | 70/46/1400 anchor; 067/099 boundaries remain | `scripts/maintenance/build_merge_readiness_20260829.ps1` |
| RGB current status | ENGINEERING_ONLY | `../results/rgb_current_status_v1/RGB_CURRENT_STATUS_V1.md` | `D:\Project\厚粲杯\08_算法\01_Attention-Analysis_rgb-nvidia` | raw/context merge-ready; derived tracking/QC absent | producer worktree; not merged across repositories |
| target-lock | CANDIDATE_ONLY | existing target-lock cards and local manifest | `D:\Project\厚粲杯\11_数据\derived\j_mmwave_target_lock_audit_v1` | candidate only; not chest-lock confirmation | existing canonical scripts |
| behavior/probe | CANONICAL_BEIJING_REPORT_BASELINE | existing baseline package | `D:\Project\厚粲杯\11_数据\derived\final_report_cohort_baseline_v2` | 70 sessions / 46 participants / 1400 probes anchor | existing canonical pipeline |
| C2C | SUPERSEDED_PENDING_CANONICAL_RERUN | existing C2C card; historical local output retained | `D:\Project\厚粲杯\11_数据\derived\c2c_within_subject_normalization_v1` | old local result is provenance only; no promotion before rerun | `pipelines/mmwave/run_c2c_personalized_mmwave_calibration.py` |
| NIR completed audit | ENGINEERING_ONLY / PRODUCER_REPO_OWNED | existing NIR cards and manifests | `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR` | not a final NIR increment; no cross-repo merge | producer worktree |
| multimodal LOSO | PLANNED_GLOBAL_ONLY | `docs/canonical/analysis_cards/multimodal_fusion.md` | matched multimodal inputs | final result MISSING; not run in this assimilation | canonical fusion contract |

| MMWAVE_TARGETED_VALIDATION_20260830 | PASS / MMWAVE_MERGE_READY_CONTRACT_FROZEN | `../results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_TARGETED_VALIDATION_REPORT_2026-08-30.md` plus diagnostic CSV/JSON/manifest | `D:\acq_mmwave_data\sub-97793_`, `sub-9779_`, `sub-97795_`; first 6000 frames only | continuity measured but unstable; B not promoted; external RSP validation-only; HR/BR HOLD, HRV/IBI EXCLUDE, structural missing/loadability ALLOW | producer reference `640cacea31ee54a63de348ddf11ba87834cb0db6` |

Explicitly MISSING at this checkpoint: full-cohort ECG/RSP vital validation,
C1 full-cohort HRV validation, RGB derived-window features, and final
multimodal LOSO results.

## unresolved closure

The prior unresolved set is fully classified in
`../repository/LOCAL_ANALYSIS_ASSIMILATION_2026-08-29.md`: 5
`KEEP_IN_MAIN`, 5 `PRODUCER_REPO_OWNED`, 1 `SUPERSEDED`, 4 `HISTORICAL`,
7 `GENERATED_ONLY`, 0 `SAFE_TO_REMOVE`, and 0
`BLOCKED_BY_RUNNING_TASK`. No unresolved current result remains in this
index. Dirty old branches and producer worktrees remain protected from
deletion; their status is not a claim of canonical scientific validity.
