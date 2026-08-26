# Local workspace inventory v1

审计日期：2026-08-26；审计方式：本机文件系统、Git worktree、脚本、配置、manifest、CSV 表头和环境路径的只读扫描。未复制原始数据，未运行新的科学分析。

## Root-level facts

| local_path | artifact_type | repository/worktree | branch/commit | files / bytes | status | sensitivity |
|---|---|---|---|---:|---|---|
| `D:\Project\厚粲杯\08_算法_local_analysis_library_canonicalization_20260826` | canonical review worktree | `mmwave-hrv-analysis` | `codex/local-analysis-library-canonicalization-20260826` / `6f18c34` | 315 tracked checkout files at creation | current | Git-safe docs/scripts only |
| `D:\Project\厚粲杯\11_数据\derived` | derived results and manifests | external local data | n/a | 1,081 files / 448,429,073 bytes | mixed current/history | local-only; includes row-level and binary assets |
| `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR` | NIR formal outputs | external local data | independent checkout | 12,314 / 10,984,327,018 bytes | engineering/candidate; not full canonical feature result | local-only |
| `D:\Project\厚粲杯\11_数据\04_Attention-Analysis_nvidia-cuda_RGB` | RGB outputs | external local data | n/a | 3,626 / 500,775,161 bytes | engineering/audit | local-only |
| `J:\Data` | mounted mmWave discovery root | external data | n/a | 12,857 / 943,294,621,304 bytes | raw discovery only | raw/local-only |
| `D:\Project\厚粲杯\08_算法\01_Attention-Analysis_nvidia-cuda` | independent NIR code checkout | separate repository | `nvidia-cuda` / `1d3587f` observed in local scan | 6,192 / 504,939,512 bytes | dirty; do not merge | local checkout |
| `I:\预实验` | pre-experiment raw/derived root | external data | n/a | 2,684 / approximately 209.58 GB | not decoded/rerun in this audit | raw/local-only |

## Result-root inventory

The derived root contains 67 top-level result roots. Important observed manifests include `c2_radar_only_attention_baseline_v1`, `c2b_v2_canonical_baselines_20260826`, `final_behavior_context_baseline_v1`, `final_report_cohort_baseline_v2`, `questionnaire_criterion_validity_v1`, `m1_mmwave_person_effect_variance_audit_v1`, `beijing_zhuhai_canonical_harmonization_v1`, and `vitalsense_c1b_benchmark_v1`. Blocked or superseded evidence includes `beijing_longitudinal_event_v1`, `beijing_semantic_session_gate_event_v1`, `external_vitalsense_benchmark_preflight_v1`, and NIR smoke retries.

Each result root must be interpreted through the registry and its manifest. A directory name alone is not evidence of completion. All `.npz`, `.mat`, `.bin`, raw CSV and large image/video trees under external roots remain local-only.

## Worktrees and provenance

The local Git scan found this canonical review worktree plus concurrent C1/C2/C3, report, NIR and handoff worktrees. The pre-existing main checkout is dirty and was not modified. No AMD branch was created. For each registered asset, `input_root`, `output_root`, producing script, upstream RUN_ID, status and sensitivity are recorded in `ANALYSIS_REGISTRY_V1.csv`; historical checkout paths are retained as unresolved provenance where applicable.
