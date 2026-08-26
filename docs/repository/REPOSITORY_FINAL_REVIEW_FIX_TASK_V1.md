# Repository Final Review Fix Task V1

状态：`FINAL_SMALL_REPOSITORY_FIX_REQUIRED`

执行分支：`codex/focuswave-mainline-restructure-v1`

目标：只修复 GPT/Sol 仓库级最终审查发现的 cutover/provenance 一致性问题。不要重新审计全库，不开始新科学分析，不删除远端分支，不改 repository name/default branch，不 merge master。

## 1. 刷新 NVIDIA NIR producer ref 与 recovery 状态

当前 `kyandi233-dev/Attention-Analysis` 的 `nvidia-cuda` 已更新为：

`36a2d596c55b93071a8b5c80459a56c876c06351`

该 commit 已包含 canonical sequential AVI timestamp mapping：timestamp CSV 第一列是 source `capture_frame_idx`，有效 timestamp 行按 sequential AVI `frame_idx` 映射，同时保留 capture counter provenance。

更新至少：
- `README.md`
- `docs/provenance/CROSS_REPO_PROVENANCE_V1.md`
- `docs/repository/CANONICAL_ENTRYPOINTS_V1.md`
- `docs/methods/FINAL_ANALYSIS_SURFACE_CANDIDATE_V1.md`
- 任何仍写 `nvidia-cuda@01af...` 或“sub-100/sub-178 仍受 capture-counter/AVI mapping blocker”的当前状态文档。

当前准确状态必须写成：
- 69/72 formal fullclass complete 仍未变化；
- sub-100/sub-178 已证明不是真实 AVI frame-gap blocker；
- 两场为 `RECOVERABLE_PENDING_FULL_RECOVERY_QC_PROBE_ALIGNMENT`；
- 不得写成 71/72 complete；
- sub-099 仍为 master_timeline blocker；
- 当前 68-session/44-participant/1360-probe NIR v1 为 recovery 前 current result，若完整 recovery 改变 matched cohort，则按原冻结规则 rerun。

本修复过程中若 sub-100/sub-178 完整 recovery 任务已有新远端结果，必须实际 fetch 后按最新事实更新；不得根据聊天猜测。

## 2. 修正 cutover 语义：approved candidate -> main

当前旧 `master@96525b...` 是历史毫米波仓库，不得简单执行“rename master to main”。

重写 `REPOSITORY_CUTOVER_PLAN_V1.md`，明确：

1. 最终审核通过的 `codex/focuswave-mainline-restructure-v1` head 才是新 `main` 的来源；
2. cutover 前为旧 `master@96525b...` 创建不可变 legacy tag，建议：
   `legacy/mmwave-hrv-master-pre-focuswave-20260826`
3. 可选再创建短期 rollback ref，但不能把旧 master 继续定义为长期正式主线；
4. 从 approved candidate exact SHA 创建 `main`；
5. clean-clone/contract/path/result-entry smoke 通过后再切 GitHub default branch 到 `main`；
6. 更新本地 remotes/worktrees/cross-repo docs；
7. rollback window 内保留旧 master/legacy ref；
8. 确认无依赖后才删除旧 `master` branch，历史由 immutable legacy tag 保存。

`BRANCH_RETIREMENT_MATRIX_V1.csv` 中 `master` 不得继续分类为 `KEEP_LONG_LIVED`。改为类似：
`LEGACY_PRESERVE_UNTIL_CUTOVER`
并写明 final action = tag legacy commit, switch default to candidate-derived main, delete old master only after rollback window.

长期 branch policy 应区分：
- permanent: `main`, `integration/nvidia`, `integration/amd`, `analysis/development`
- ephemeral pattern: `task/<short-name>`，任务 merge/close 后删除；它不是第五条永久 branch。

## 3. 修正 M01 producer/provenance

`FINAL_ANALYSIS_SURFACE_CANDIDATE_V1.md` 当前把 `protocol, identity, report cohort` 整体指向 baseline commit `414a4f46...`，这不准确。

至少拆清：
- protocol/site/repeat-session policy：以 `codex/protocol-identity-update-20260826` 中 `docs/decisions/2026-08-26-beijing-zhuhai-protocol-identity-harmonization.md` 的实际 branch/head/commit 为 provenance；
- Beijing report cohort / C+B baseline：`414a4f46c8d058961a87750345d06a7129afc9f2`；
- global identity reconciliation/global cohort/global folds：仍 `GLOBAL_PENDING`，不得冒充已有 producer。

可以保留 10 个科学模块，但 M01 必须允许多个明确 producer/ref，而不是一个错误的统一 commit。

## 4. 删除分支前必须保护 producer commit

当前 migration manifest 存在“producer remains on retained result branch”，同时 branch matrix 又计划后续删除该 branch 的情况。这是不安全的。

新增 `docs/repository/PRODUCER_REF_PRESERVATION_V1.csv`，逐个覆盖所有未来计划删除、但仍承载 unique producer/runner/result provenance 的 branch。

至少字段：
- branch_name
- producer_commit
- unique_producer_paths
- canonical_successor
- preservation_method
- archive_tag_name
- migrated_path_if_any
- verification_status
- delete_allowed

删除硬门槛：每条 branch 在删除前必须满足至少一种：
A. producer 已物理迁移到新 mainline，并通过 import/path/schema/clean-run regression；或
B. exact producer commit 已建立 immutable archive tag，并且 canonical docs 记录 exact SHA + tag。

建议 archive tag 命名：
`archive/20260826/<sanitized-branch-purpose>`

baseline、label/vigilance、Q1、repeat-session、C1/C2B/C2C/M1 等 retained/supporting producer 都必须进入 preservation table。只记录裸 SHA 不视为长期 ref 保护。

更新 `MIGRATION_MANIFEST_V1.csv`：凡是未来 branch 要删除且 producer 暂不搬移的，status 不得只写 `MAPPED_LEGACY_PRODUCER`，还要明确 archive-tag preservation requirement。

## 5. Branch retirement matrix 最终删除规则

重新审计 32 条远端 branch 的当前 head（包括本 candidate 最新 head），更新 stale head SHA/date。

对所有 `MIGRATE_THEN_DELETE` / `ARCHIVE_REFERENCE_THEN_DELETE`：
- 明确 exact migrated/archive artifact；
- 明确 exact preservation tag 或 migrated producer；
- open PR/head dependency 未解除时 `delete_allowed=false`；
- external-storage unresolved、active Sol/canonicalization、PR #2、当前执行任务均不能提前删除。

不要在本任务中实际删除任何 branch/tag。

## 6. PR #2 disposition

PR #2 `chatgpt/multimodal-results-nir-diagnostic-20260826` 仍是 recovery 前 scientific snapshot。

生成 `docs/repository/PR2_DISPOSITION_V1.md`：
- keep open / update / close-with-archive 三选一的推荐；
- 哪些内容仍有效；
- 哪些 NIR 数字属于 pre-recovery current result；
- RGB formal analysis priority 已过时（当前 pipeline engineering pending）；
- mmWave HRV 不应重新成为近期主线；
- merge 到未来 main 前需要哪些更新。

本任务不 merge/close PR #2。

## 7. Cutover readiness gate

新增 `docs/repository/CUTOVER_READINESS_GATE_V1.md`，必须逐项给 PASS/BLOCKED：
- Sol scientific final gate
- candidate repository final review fixes
- current NIR producer ref/status refreshed
- producer ref preservation complete
- PR #2 disposition resolved
- no active task branch scheduled for deletion
- legacy master tag prepared
- candidate-derived main creation command validated
- clean clone passes
- canonical result entrypoints resolve
- no raw/row-level/sensitive assets staged
- repo rename/default-branch steps and rollback commands documented

只有全部 PASS 才允许返回 `REPOSITORY_CUTOVER_READY`。

## 8. 本轮不做

- 不改 GitHub repo slug；
- 不创建/切换 default `main`；
- 不删除 master 或任何其他 branch；
- 不开始 AMD bulk analysis；
- 不开始 RGB formal stats；
- 不重跑 NIR/mmWave/behavior scientific models；
- 不把 recovery smoke 当正式 fullclass completion。

## 返回格式

完成并 push 后返回：

`FOCUSWAVE_REPOSITORY_FINAL_FIX_REVIEW_READY`

并报告：
- branch
- commit SHA
- refreshed Attention-Analysis NVIDIA/AMD refs
- NIR current completion/recovery status
- M01 corrected provenance
- producer preservation rows/status counts
- branch retirement status counts + delete_allowed counts
- PR #2 disposition recommendation
- cutover readiness PASS/BLOCKED table
- unresolved blockers
