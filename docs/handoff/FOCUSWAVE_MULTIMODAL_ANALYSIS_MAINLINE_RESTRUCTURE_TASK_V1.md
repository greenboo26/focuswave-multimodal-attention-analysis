# FocusWave Multimodal Analysis 主线重构任务 V1

日期：2026-08-26  
执行分支：`codex/focuswave-mainline-restructure-v1`  
基线：`codex/local-analysis-library-canonicalization-20260826@ce4da877743132d6a8b4f21a298c58b1b06f3f5e`

## 0. 任务定位

当前远端仓库名仍为 `greenboo26/mmwave-hrv-analysis`，默认 `master` 仍以“毫米波 HR/BR/HRV 算法库”为主体，但项目实际已经发展为 FocusWave 的总分析与多模态证据整合仓库。

本任务目标不是继续给旧结构打补丁，而是在独立分支上构建一个**可供 GPT/Sol 审查的新正式主线候选**，目标显示名称固定为：

`FocusWave Multimodal Analysis`

建议未来远端 slug：

`focuswave-multimodal-analysis`

但本任务**禁止直接修改远端仓库名、默认分支、删除远端分支或 merge master**。这些动作必须在 GPT/Sol 审查通过后执行。

本仓库未来职责必须冻结为：

> 接收双机/各模态标准派生结果与 provenance，完成中央 identity/cohort、统一行为与问卷基线、mmWave/NIR/RGB 单模态增量、multimodal fusion、北京—珠海跨站点验证、最终统计与报告证据链。

`kyandi233-dev/Attention-Analysis` 继续负责 NIR/RGB 的底层工程、GPU/DirectML/CUDA runtime、视频/NIR 原始数据到标准派生输出。不要把该仓库的完整模型/runtime 复制到本仓库。

---

## 1. 严格边界

本轮允许：

- 扫描和审计所有远端 branches / open PR / canonicalization / Sol review / retained result branches；
- 重写本分支 README / AGENTS / 项目入口；
- 建立新的目录骨架、contract、schema、result index、branch retirement matrix、migration manifest；
- 把已经确认的 Git-safe canonical/supporting result docs 映射到新主线结构；
- 对旧目录进行“逻辑归类”和迁移映射；
- 对不会破坏 import/历史复现的纯文档、小型 aggregate 结果做实际移动/复制；
- 为未来正式 cutover 准备精确命令和顺序。

本轮禁止：

- 删除任何远端 branch；
- force push；
- rename GitHub repo；
- 修改 GitHub default branch；
- merge 到 `master`；
- 把 31 条旧 branch 机械 merge 到一起；
- 因目录美化批量移动仍被历史 producer import 的脚本；
- 修改科学结论、重新跑探索性统计；
- 启动 RGB 正式分析；
- 上传 raw/row-level participant data、NPZ/MAT/BIN/AVI、大模型、缓存、凭据。

如果旧脚本移动会破坏 import 或 provenance，先保留原路径，在 migration manifest 中登记未来目标路径，不为了目录漂亮破坏可复现性。

---

## 2. 必读来源

### 2.1 本仓库 canonicalization / review

至少读取：

- `codex/local-analysis-library-canonicalization-20260826`
  - `docs/canonical/ANALYSIS_REGISTRY_V1.csv`
  - `docs/canonical/ANALYSIS_REGISTRY_V1.md`
  - `docs/canonical/LOCAL_WORKSPACE_INVENTORY.md`（若路径存在）
  - `docs/canonical/DERIVED_DATA_CONTRACT_V1.md`
  - `docs/canonical/AMD_EXECUTION_MODULES_V1.md`
  - `docs/canonical/AMD_NVIDIA_SCIENTIFIC_CONTRACT_V1.md`
  - `docs/canonical/PRODUCER_PROVENANCE_V1.md`
  - `docs/canonical/SOFTWARE_ENVIRONMENT_MATRIX_V1.md`
  - `docs/canonical/RESULT_INDEX_V1.md`
  - `docs/canonical/analysis_cards/`
- `sol/scientific-review-20260826`
  - `docs/review/SOL_SCIENTIFIC_REVIEW_V1.md`
  - `docs/review/SCIENTIFIC_REVIEW_MATRIX_V1.csv`
  - `docs/review/SOL_REREVIEW_V1.md`
  - `docs/review/CANONICALIZATION_FIX_TASK_V2.md`

若 Fix V2 已经在其他 commit 完成，读取最新 commit，不使用旧 snapshot 覆盖新状态。

### 2.2 当前结果状态分支

至少核验这些生产/结果来源，不靠聊天总结代替：

- `codex/report-cohort-label-vigilance-20260826`
- `codex/report-repeat-session-effects-20260826`
- `codex/q1-questionnaire-criterion-validity-20260826`
- `codex/final-report-cohort-baseline-v2`
- `codex/c1-alignment-protocol-repair-20260826`
- `codex/c2b-v2-canonical-20260826`
- `codex/c2c-within-subject-normalization-20260826`
- `codex/m1-mmwave-person-effect-audit-20260826`
- `codex/d1-beijing-zhuhai-canonical-20260826`
- `chatgpt/multimodal-results-nir-diagnostic-20260826` / PR #2

PR #2 当前 NIR 数值只能按其 provenance/status 登记。不要把“结果说明已 push”误写成“producer 已远端可复现”。NIR timestamp recovery 后若 cohort 变化，其当前 68-session/1360-probe NIR v1 数值必须标为 `PRE_TIMESTAMP_RECOVERY_CURRENT_RESULT` 或等价状态，直到 canonical rerun 完成。

### 2.3 外部工程仓库边界

只读取 `kyandi233-dev/Attention-Analysis` 的当前科学 contract / branch responsibility，不复制底层完整 runtime：

- `nvidia-cuda`：NVIDIA 综合 production；当前 NIR timestamp canonical fix 已进入主线；
- `amd-DirectML`：AMD 综合 production；
- `rgb-nvidia` / `rgb-amd`：RGB 工程工作线；
- `analysis/multimodal-integration`：当前实际主要是 44 人 NIR+Behavior cohort development/QC，不得误标为最终 multimodal inference 主线。

RGB 当前状态：`PIPELINE_ENGINEERING_PENDING / FORMAL_ANALYSIS_NOT_AUTHORIZED`。

---

## 3. 先做 branch inventory，不准先删

当前仓库已有约 31 个 branches。必须重新 fetch 后以实际远端为准，生成：

`docs/repository/BRANCH_RETIREMENT_MATRIX_V1.csv`
`docs/repository/BRANCH_RETIREMENT_MATRIX_V1.md`

每条 branch 至少记录：

- branch name
- head SHA
- last commit date
- scientific/engineering purpose
- retained unique assets
- canonical successor
- open PR dependency
- classification
- deletion prerequisite
- recommended final action

classification 固定为：

- `KEEP_LONG_LIVED`
- `ACTIVE_TASK_DO_NOT_TOUCH`
- `MIGRATE_THEN_DELETE`
- `ARCHIVE_REFERENCE_THEN_DELETE`
- `SUPERSEDED_SAFE_TO_DELETE_AFTER_AUDIT`
- `HOLD_UNRESOLVED`

不要仅凭 branch 名称判断。必须检查 branch diff / unique files / result provenance。

特别注意：历史分支是 provenance，不代表必须永久保持为活跃 branch。历史应主要由 commits/tags/archive index 保存。

---

## 4. 新正式主线的目标结构

在本 branch 建立以下**实际可浏览**的目标结构；已有文件可以先通过 index/README 映射，不要求第一轮物理移动所有旧代码：

```text
FocusWave-Multimodal-Analysis/
├── README.md
├── AGENTS.md
├── CHANGELOG.md
│
├── configs/
│   ├── cohorts/
│   ├── windows/
│   ├── models/
│   └── paths.example.*
│
├── contracts/
│   ├── identity/
│   ├── behavior/
│   ├── questionnaire/
│   ├── mmwave/
│   ├── nir/
│   ├── rgb/
│   └── multimodal/
│
├── schemas/
│
├── pipelines/
│   ├── cohort/
│   ├── behavior/
│   ├── questionnaire/
│   ├── mmwave/
│   ├── nir/
│   ├── rgb/
│   ├── fusion/
│   └── cross_site/
│
├── results/
│   ├── canonical/
│   ├── supporting/
│   ├── engineering_reference/
│   └── superseded_index/
│
├── docs/
│   ├── methods/
│   ├── decisions/
│   ├── provenance/
│   ├── reports/
│   ├── repository/
│   └── archive/
│
└── tests/
```

### 4.1 第一轮迁移原则

- 新建目录和 index/README 必须实际存在；
- canonical docs/results 优先迁入/复制到目标位置；
- active producer script 若安全可迁移，允许迁移并修 imports/tests；
- 若迁移风险高，保留旧 `scripts/` 作为 compatibility surface，并在 `MIGRATION_MANIFEST_V1.csv` 记录：`old_path → future_target_path → status → blocker`；
- 不允许同时维护两个“权威结果索引”。新 `results/README.md` 应成为候选唯一入口；旧索引要明确指向它或标为 legacy。

---

## 5. 重写根 README：必须真正改变仓库身份

新的 README 不能只在旧“毫米波生命体征算法”README 顶部加几行说明。

根 README 第一屏必须直接回答：

1. 这个仓库是什么？
2. 哪个仓库负责 NIR/RGB production？
3. 双机怎么进入中央分析？
4. 当前主科学问题是什么？
5. 哪些结果是 canonical / supporting / pending？
6. 如何开始一次新的分析？
7. 哪些数据绝不能进入 Git？

核心流程建议明确写为：

```text
NVIDIA / AMD local production
        ↓
standardized derived package + QC + provenance
        ↓
central identity reconciliation
        ↓
global repeat_participant_id + report cohort + folds
        ↓
C+B baseline
        ↓
C+B+mmWave / C+B+NIR / C+B+RGB
        ↓
matched incremental validity
        ↓
C+B+NIR+RGB (and frozen mmWave ablation if justified)
        ↓
Beijing shared-primary + Zhuhai extension/external validation
        ↓
final report evidence chain
```

README 不得再把 HR/BR/HRV v1.7 作为项目主体。旧毫米波 pipeline 应移动到 mmWave module / legacy history 的说明层。

---

## 6. 双机规范必须在总仓库成为正式 contract

建立：

`contracts/multimodal/DUAL_MACHINE_ANALYSIS_CONTRACT_V1.md`

必须冻结：

### Local machine 可以做

- raw/video/session → modality-specific standardized derived outputs；
- local timestamp/timeline alignment（遵守共享 contract）；
- local QC；
- local provenance/hash/version；
- local Behavior/NIR/RGB/mmWave derived package generation；
- backend-specific NVIDIA CUDA / AMD DirectML runtime。

### Local machine 不可以独立决定

- global natural-person identity；
- final `global_repeat_participant_id`；
- combined Beijing/Zhuhai report cohort；
- final participant-disjoint folds；
- cross-disk matched cohort；
- final AUC/ΔAUC/p-values 作为全项目结论；
- 多机结果 AUC 平均。

### Central only

```text
local derived packages
→ identity reconciliation
→ global participant grouping
→ frozen report cohort
→ frozen folds
→ matched model comparisons
→ participant bootstrap
→ final multimodal/cross-site statistics
```

定义 machine provenance：

- `machine_role`
- `runtime_backend`
- `pipeline_version`
- `git_commit`
- `model_hash`
- `config_hash`
- `schema_version`
- `source_manifest_hash`

不得把 AMD/NVIDIA backend 默认当作科学 predictor；它是 provenance / sensitivity variable。

---

## 7. 正式分析 surface 要压缩，不再暴露 29 项给报告主线

建立：

`docs/methods/FINAL_ANALYSIS_SURFACE_CANDIDATE_V1.md`

把 registry 29 项归并成最终报告约 10 个模块：

1. Protocol / identity / report cohort
2. Probe label structure / four-class state
3. Vigilance validity
4. Pre-probe behavior validity / longitudinal behavior
5. Questionnaire convergent/criterion validity
6. C+B canonical baseline
7. mmWave validation boundary / frozen ablation
8. NIR incremental validity（v1 + recovery/v2 status）
9. RGB incremental validity（当前 blocked by pipeline engineering）
10. Multimodal fusion + cross-site validation

每个模块必须列：

- canonical analysis IDs
- producer branch/commit
- current status
- report role
- required rerun before final
- prohibited/superseded result

禁止因为历史上做过很多分析就让最终报告变成 29 个平级结果。

---

## 8. 当前科学状态必须准确迁入

至少正确体现：

### Behavior/context baseline

- canonical Beijing report cohort：70 sessions / 46 natural participants / 1400 probes；
- 30 s primary；10/20 s sensitivity；
- participant-disjoint folds；
- C+B 是正式锚点。

### NIR

- current NIR v1 feature block = PIR + OAR + QC/coverage；
- 当前 matched 68-session / 44-participant / 1360-probe result 属于 timestamp recovery 前的当前结果，若 sub-100/sub-178 完整 recovery 后进入 cohort，必须按冻结规则原样 rerun；
- `sub-100/sub-178` 已证明旧 blocker 是 capture-counter/AVI mapping 解释问题，当前等待完整 recovery/fullclass + Probe/QC；
- `sub-099` blocker 与 timestamp mapping 无关；
- NIR v2 只能在 blink/PERCLOS manual feasibility validation 通过后进行；
- 不为了救效果堆高维 generic feature。

### RGB

- pipeline 未完成；
- formal statistical analysis not authorized；
- `rgb-amd/rgb-nvidia` 先完成工程；
- 临时 `codex/rgb-nvidia-formal-pipeline-v1` 仅为待吸收后删除 checkpoint；
- 不把 partial parquet 当正式结果。

### mmWave

- C1 当前 HRV validation line 已停止于本比赛周期；
- 这不等同于证明 RS6240 硬件无法测 HRV；
- C2b/C2C 当前低复杂度 mmWave feature 对 C+B 无稳定正增量；
- M1 作为 supporting person-effect audit；
- mmWave 当前进入 final story 的角色是 validation boundary / ablation，而不是继续无止境优化。

### Beijing / Zhuhai

- Beijing B1+B2 + Zhuhai B1+B2 = shared primary；
- Zhuhai B3 = extension；
- external storage 未在中央机器可用时标 `DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE`，不是“数据不存在”；
- global identity/folds 中央统一。

---

## 9. 未来 branch policy

建立：

`docs/repository/BRANCH_POLICY_V1.md`

目标长期只保留少量长期分支。候选：

- `main`：唯一审查通过的正式主线；
- `integration/nvidia`：仅用于接收 NVIDIA-derived contract/provenance 变化；
- `integration/amd`：仅用于接收 AMD-derived contract/provenance 变化；
- `analysis/development`：中央分析方法开发；
- `task/<short-name>`：短期任务，merge 后删除。

不要强行在本任务创建所有这些远端 branch。先形成 policy 和 cutover plan。

旧 `codex/*` / `sol/*` / `experimental/*` / `sample/*` 的处理由 retirement matrix 决定。

---

## 10. 迁移与 cutover 计划

生成：

`docs/repository/REPOSITORY_CUTOVER_PLAN_V1.md`

必须给出未来审查通过后的准确顺序：

1. freeze current task branches；
2. 完成 Sol final gate；
3. tag legacy state（例如 `legacy-mmwave-analysis-pre-focuswave-cutover-20260826`，仅作为建议，不在本轮创建除非明确无风险）；
4. 将 candidate mainline 更新为审查通过状态；
5. rename display/root docs；
6. GitHub repo slug `mmwave-hrv-analysis → focuswave-multimodal-analysis`；
7. default branch `master → main` 的安全迁移方案；
8. 更新本地 remotes/worktrees/Codex instructions；
9. 更新跨仓库引用；
10. 按 matrix 删除已经无唯一资产的旧远端 branches；
11. 验证 GitHub links / scripts / docs / registry provenance；
12. 生成 post-cutover audit。

每一步写 rollback 条件。

---

## 11. 必须生成的交付物

至少：

- `README.md`（全新项目身份）
- `AGENTS.md`（更新为新仓库职责与读取顺序）
- `docs/repository/REPOSITORY_ARCHITECTURE_V1.md`
- `docs/repository/BRANCH_RETIREMENT_MATRIX_V1.csv`
- `docs/repository/BRANCH_RETIREMENT_MATRIX_V1.md`
- `docs/repository/MIGRATION_MANIFEST_V1.csv`
- `docs/repository/REPOSITORY_CUTOVER_PLAN_V1.md`
- `docs/repository/BRANCH_POLICY_V1.md`
- `contracts/multimodal/DUAL_MACHINE_ANALYSIS_CONTRACT_V1.md`
- `docs/methods/FINAL_ANALYSIS_SURFACE_CANDIDATE_V1.md`
- `results/README.md`
- `results/canonical/README.md`
- `results/supporting/README.md`
- `results/engineering_reference/README.md`
- `results/superseded_index/README.md`
- `docs/provenance/CROSS_REPO_PROVENANCE_V1.md`

如果需要补充 schema/index 文件，可以增加，但不要创建第二套重复 ledger。

`docs/WORKSPACE_LEDGER.md` 仍然是唯一项目 ledger；本任务只更新它，不创建另一个“总状态文件”。

---

## 12. 自检

完成前至少检查：

- 所有 branch 分类都能追到实际 SHA；
- 所有 canonical analysis 迁移来源都能追到 producer branch/commit；
- README 不再以毫米波 HRV 为主体；
- 双机 local vs central 边界无矛盾；
- NIR 当前 69/72、sub100/sub178 recovery 状态没有被误写成 71/72 complete；
- RGB 未被误写为可正式分析；
- PR #2 的 NIR 当前数值没有被误写为 timestamp-recovery 后 final；
- 没有 raw/row-level data 进入 staged files；
- Python/CSV/Markdown 路径检查通过；
- `git diff --check` 通过；
- 工作区干净；
- push 后远端 SHA 与本地一致。

---

## 13. 完成返回格式

返回：

`FOCUSWAVE_MAINLINE_RESTRUCTURE_REVIEW_READY`

并报告：

- branch
- commit SHA
- local worktree path
- 当前实际 branch 数
- branch classification 统计
- 计划保留的长期 branch
- 计划删除但尚未删除的 branch 数
- 新 README / architecture / dual-machine contract 路径
- 已实际迁移的 canonical assets 数
- 暂未移动、仅登记 migration manifest 的 legacy producer 数
- 当前 unresolved blockers
- 是否建议进入 GPT/Sol repository final review

本轮不要执行远端 rename / branch deletion / default-branch cutover。