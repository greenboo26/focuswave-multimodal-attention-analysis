# AMD execution modules v1

这是 Sol re-review 前的最小模块草案，不是 AMD 分支或执行授权。

| module | colleague action | central-only boundary |
|---|---|---|
| local discovery/provenance | discover local sessions and emit stable session keys, source evidence, schema and QC manifest | do not freeze global participant identity or folds |
| behavior/Probe derived | produce standardized local Probe/behavior tables if present | central cohort reconciliation and inference |
| questionnaire bridge | produce local questionnaire linkage evidence if present | central deterministic identity reconciliation |
| NIR AMD production/QC | run only Sol-approved AMD backend with runtime/backend provenance and parity checks | no final AUC/p-values independently |
| RGB AMD production/QC | same schema, timestamp/gap/QC and parity contract | no independent modality selection or threshold tuning |
| mmWave derived | only if external disk and final Sol-approved plan require it | no new feature-family exploration |
| global inference | do not run | central merge, global `repeat_participant_id`, participant-disjoint folds, pooled/site-held-out inference |

Required every module: Python/package snapshot, code commit, config digest, model hash, seed, schema version, input filter, output root, overwrite/resume policy and redacted run manifest.
