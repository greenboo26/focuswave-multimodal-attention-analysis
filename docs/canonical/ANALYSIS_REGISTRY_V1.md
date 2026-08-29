# Analysis registry v1

状态枚举使用 review matrix 的科学语义：`KEEP_MAIN`、`KEEP_SUPPORTING`、`REVISE_METHOD`、`RERUN_CANONICAL`、`CANONICAL_BEIJING_REPORT_BASELINE`、`VALIDATION_STOPPED`、`SUPERSEDED`、`SUPERSEDED_INTERMEDIATE`、`ENGINEERING_ONLY`、`PLANNED_GLOBAL_ONLY`、`DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE`。完整机器可读表见同目录 CSV。

本轮没有新的探索性科学分析。CSV 的每一行对应一个保留的实际分析或正式计划阶段，包含输入、输出、入口、RUN_ID、样本单位、cohort、身份键、site/protocol 和跨机器复现要求。`exact_executable_script` 若标为历史 worktree 或 `not yet stable`，即为复现审计发现，不是可执行承诺。

## Status counts

| status | count |
|---|---:|
| `REVISE_METHOD` | 6 |
| `ENGINEERING_ONLY` | 4 |
| `PLANNED_GLOBAL_ONLY` | 4 |
| `VALID_SUPPORTING` | 3 |
| `KEEP_MAIN` | 2 |
| `KEEP_SUPPORTING` | 2 |
| `SUPERSEDED_INTERMEDIATE` | 2 |
| `RERUN_CANONICAL` | 1 |
| `CANONICAL_BEIJING_REPORT_BASELINE` | 1 |
| `SUPERSEDED` | 1 |
| `VALIDATION_STOPPED` | 1 |
| `PENDING_CANONICAL_RERUN` | 1 |
| `DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE` | 1 |
| total | 29 |

`BEHAVIOR_BASELINE` 已提升为 `CANONICAL_BEIJING_REPORT_BASELINE`，但这不等于 global canonical inference；最终多模态/跨站点分析仍需中央 identity reconciliation 和全局 folds。

## Interpretation rules

- `subject + probe_id` 是当前 Probe 级连接键；NIR 时间对齐使用绝对 Unix milliseconds，时间戳不是身份键。
- `repeat_participant_id` 只用于 participant-disjoint grouping 和重复测量，不能从目录名推断。
- Beijing B1+B2 是 shared primary；Zhuhai B3 仅 extension，直到全局 cohort gate 通过。
- labels 2/3/4 保留四分类层，不统称为 mind-wandering。
- C1/HRV、最终 NIR/RGB 增量、多模态融合与跨站点验证不得从工程状态推断科学完成。

## 2026-08-29 assimilation note

The local-unique evidence identified from the old dirty worktree now has a
canonical traceability record in `docs/repository/LOCAL_ANALYSIS_ASSIMILATION_2026-08-29.md`
and the result-level pointers in `RESULT_INDEX_V1.md`. Current executable
locations are:

- C1c/C1d pilot: `pipelines/mmwave/run_c1c_mmhrv_pilot.py` and
  `pipelines/mmwave/run_c1d_radarbeat_backend_pilot.py`;
- C2a/C2b supporting audits: `pipelines/mmwave/audit_c2a_dataset.py` and
  `pipelines/mmwave/run_c2b_task_focus_baselines.py`;
- QC/readiness: `scripts/maintenance/` entries listed in the canonical script
  README;
- questionnaire evidence: `scripts/build_psychometric_evidence_matrix_v1.py`
  together with the canonical questionnaire pipeline.

The old Q1 and Issue #13 matrices with the reversed label-3/label-4 wording
are superseded and are not canonical results. NIR and RGB producer worktrees
remain separately owned; their local outputs are registered but not merged
into this repository.
