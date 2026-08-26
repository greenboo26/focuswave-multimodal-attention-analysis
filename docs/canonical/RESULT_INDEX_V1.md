# Result index v1

This index points to local full results without uploading them. See `ANALYSIS_REGISTRY_V1.csv` for the complete 29-entry table.

| analysis_id | status | Git description | local full result path | report use |
|---|---|---|---|---|
| BEIJING_BEHAVIOR | VALID_SUPPORTING | manifest/report schema only | `D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1` | behavior results with diagnostics/FDR caveat |
| C2B_V2 | VALID_SUPPORTING | canonical candidate contract | `D:\Project\厚粲杯\11_数据\derived\c2b_v2_canonical_baselines_20260826` | mmWave baseline, not final multimodal |
| Q1_QUESTIONNAIRE | VALID_SUPPORTING | criterion report pointer | `D:\Project\厚粲杯\11_数据\derived\questionnaire_criterion_validity_v1` | questionnaire evidence with criterion limit |
| M1 | VALID_SUPPORTING | person-effect audit pointer | `D:\Project\厚粲杯\11_数据\derived\m1_mmwave_person_effect_variance_audit_v1` | limitation/diagnostic |
| D1_HARMONIZATION | VALID_SUPPORTING | cross-site contract pointer | `D:\Project\厚粲杯\11_数据\derived\beijing_zhuhai_canonical_harmonization_v1` | harmonization only |
| C1_ALIGNMENT | BLOCKED_EXTERNAL_STORAGE | blocker and protocol record | `D:\Project\厚粲杯\11_数据\derived\c1_alignment_protocol_repair_v1` | not usable for HRV claim |
| C3A_V1/C3A_V2/NIR_69 | ENGINEERING_ONLY | engineering manifests | `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR` | not final NIR increment |
| NIR_INCREMENT/RGB_INCREMENT/MULTIMODAL_FUSION/CROSS_SITE | PLANNED_GLOBAL_ONLY | no final result | readiness manifests only | cannot enter final report |

All local paths are external to Git and must be checked on the executing machine.
