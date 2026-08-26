# Repository architecture V1

## Identity

`FocusWave Multimodal Analysis` 是 FocusWave 注意力/Probe 结果的正式中央分析仓库。当前 slug 为 `focuswave-multimodal-attention-analysis`，旧 slug `mmwave-hrv-analysis` 仅作为历史 provenance 记录。职责是中央方法、cohort/identity contract、跨机器 derived package 合并、结果 provenance 和最终分析 surface。

## Ownership boundaries

| layer | owner | allowed output |
|---|---|---|
| local producer | NVIDIA/AMD external Attention-Analysis refs | standardized derived tables, QC, linkage evidence, manifests |
| central integration | this repository | identity reconciliation, global cohort/folds, paired inference, report aggregates |
| historical producer | current task/result branches | immutable provenance and migration mapping |
| final report | this repository `results/canonical/` | only approved aggregate result packages |

## Canonical flow

`protocol -> identity -> label validity -> behavior/questionnaire validity -> C+B -> sensor increment -> multimodal fusion -> cross-site validation`.

The final cutover preserves stable entrypoints and contracts. Legacy producer content is recoverable through immutable tags; only curated successors remain in the browsable main tree. No raw or participant-level data is part of the repository.

## Directory contract

`configs/` freezes parameters; `contracts/` freezes interfaces; `schemas/` freezes columns and units; `pipelines/` points to executable/adaptor surfaces; `results/` expresses scientific status; `docs/` records rationale/provenance/governance; `tests/` contains lightweight checks only.
