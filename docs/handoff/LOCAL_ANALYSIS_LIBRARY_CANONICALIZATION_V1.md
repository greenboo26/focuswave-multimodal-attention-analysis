# LOCAL_ANALYSIS_LIBRARY_CANONICALIZATION_V1

状态：`ASSIGNED`
日期：2026-08-26
执行角色：本机 Codex
科学审查角色：GPT-5.6 Sol（本任务完成并 push 后）

## 0. 目标与顺序

本任务不是继续做新分析，而是把当前本机已经完成、正在使用、历史遗留的整个厚粲杯分析库整理为一套可审查、可复现、可跨机器交接的正式分析库。

固定顺序：

1. 本机 Codex 实际扫描本地工作区、脚本、环境、输入、derived 结果、Git 分支与正式输出；
2. 把现有分析整理为一个 NVIDIA/本地权威分支，并上传所有可公开/可脱敏的配置、方法、脚本、步骤、结果说明和数据契约；
3. GPT-5.6 Sol 只从 GitHub 拉取该分支，做独立科研方法审查；
4. 只有 Sol 明确批准后，才建立并发布同事 AMD/另一块数据盘执行分支与 runbook；
5. 未通过审查前，不让另一台机器依据本分支开始行为/问卷/mmWave 的新批量分析。

## 1. 项目重新命名

旧名称/旧仓库定位：`mmwave-hrv-analysis` / “毫米波心率分析”。

该名称已经不符合当前项目实际范围。当前分析库覆盖：
- experiment protocol / identity / cohort；
- behavior；
- probe response / vigilance；
- questionnaire；
- mmWave；
- NIR；
- RGB；
- multimodal increment / fusion；
- Beijing–Zhuhai cross-site validation；
- report-level statistical evidence。

新的项目显示名称冻结为：

`FocusWave Multimodal Attention Analysis`

建议远端仓库 slug：

`focuswave-multimodal-attention-analysis`

本任务中先完成代码、README、文档标题、内部路径语义和迁移清单的更名准备。不要在未完成本地审计前粗暴重命名本地目录或破坏已有 worktree。远端 repository slug 的最终改名在 Sol 审查通过后统一执行，以避免当前大量历史 branch / handoff / connector 引用在整理阶段失效。

必须生成：`docs/migration/REPOSITORY_RENAME_PLAN_V1.md`，记录：
- old name / new name；
- 本地目录是否需要改名；
- git remote 需要如何更新；
- 哪些文档/脚本含旧 repo 名；
- 哪些外部链接/CI/connector 可能受影响；
- rename 后验证命令。

## 2. 唯一工作分支

当前整理分支：

`codex/local-analysis-library-canonicalization-20260826`

不得把整理结果散落到多个新分支。

完成后该分支应成为 GPT 审查的唯一入口。不得直接 merge master；不得建立 AMD 分支；不得让同事开始执行。

## 3. 必须实际扫描的本地范围

不要依据聊天记录猜路径。逐项实际验证文件存在、mtime/commit、字段和内容。

至少扫描：

- `D:\Project\厚粲杯\08_算法\`
- `D:\Project\厚粲杯\11_数据\derived\`
- `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR\`
- `D:\Project\厚粲杯\11_数据\04_Attention-Analysis_nvidia-cuda_RGB\`
- 当前 `mmwave-hrv-analysis` 所有本地 worktree
- `D:\Project\厚粲杯\08_算法\01_Attention-Analysis_nvidia-cuda\`（若实际路径不同，以本机事实记录）
- `J:\Data` 当前正式数据 discovery 范围（只做元数据/文件结构审计，不上传原始数据）
- behavior / questionnaire / identity / protocol / canonical probe / mmWave / NIR / RGB 相关所有实际 derived 入口

扫描所有 `scripts/`、`configs/`、`.harness/`、`docs/results/`、`docs/decisions/`、本地临时分析脚本，以及不在 Git 中但实际用于正式结果的代码。

## 4. 先整理工作区，不删除证据

本地可能存在历史脚本、重复输出、临时文件和多个 worktree。整理规则：

- 先 inventory，再移动/归档；
- 不删除原始数据；
- 不删除仍无法确认 provenance 的 derived 结果；
- 对重复/旧结果标记 superseded，不靠删除解决；
- 不把 pseudonymous row-level/raw data 上传 GitHub；
- 不把大体积模型权重、视频、原始 CSV/NPZ/AVI/ACQ 上传 GitHub；
- 可以上传脱敏 aggregate result、schema、manifest 模板、配置、脚本、runbook、统计结果表、报告候选图。

必须生成：

`docs/canonical/LOCAL_WORKSPACE_INVENTORY_V1.md`

字段至少：
- local_path
- artifact_type
- repository/worktree
- branch
- commit
- input_root
- output_root
- producing_script
- upstream_run_id
- status
- canonical/superseded/unknown
- local_only_sensitive
- notes

## 5. 建立完整分析注册表

必须生成：

- `docs/canonical/ANALYSIS_REGISTRY_V1.md`
- `docs/canonical/ANALYSIS_REGISTRY_V1.csv`

每一个实际做过或正式计划保留的分析独立一行，不允许只按“行为/mmWave/NIR”粗分。

至少覆盖并核实：

- protocol/version harmonization
- identity/session master
- C2A label/sample audit
- Beijing formal behavior longitudinal
- pre-probe behavior windows
- B1-late→B2-early recovery comparison
- REPORT_ANALYSIS_COHORT
- four-class probe trajectory
- vigilance analysis
- probe-vigilance-behavior association
- repeat-session/practice effects
- questionnaire criterion validity Q1
- behavior/context baseline V1 及其 1400-probe rerun 状态
- early sensor increment baseline
- C1 alignment / beat / IBI / HRV validation
- C2b-v2 canonical mmWave absolute features
- C2C resting calibration
- M1 person-effect audit
- NIR C3A v1
- NIR C3A v2
- NIR 69-session fullclass engineering completion
- RGB Motion
- RGB Pose
- RGB Face benchmark / CUDA Gate / formal runner 当前状态
- Beijing–Zhuhai D1 harmonization
- 尚未完成的 final NIR increment / final RGB increment / multimodal fusion / cross-site validation

每项必须记录：

1. `analysis_id`
2. 中文名称
3. scientific_question
4. report_role
5. exact local inputs
6. upstream asset / RUN_ID
7. exact executable script
8. config file(s)
9. software environment
10. package versions / model versions / hashes（实际可获取时）
11. sample unit: trial / probe / session / participant
12. cohort rule
13. identity/grouping key
14. site / protocol scope
15. label definition
16. time window definition
17. feature set
18. QC rule
19. statistical model
20. repeated-measures handling
21. CV / folds
22. imputation/scaling leakage control
23. bootstrap / CI
24. multiple comparison correction
25. random seed
26. exact output root
27. output file list
28. output schema/columns summary
29. headline results
30. result interpretation
31. forbidden over-interpretation
32. branch / commit
33. status
34. superseded_by
35. whether another data disk should reproduce this stage
36. whether stage must wait for global merged data

状态枚举统一：
- `CANONICAL_FINAL`
- `VALID_SUPPORTING`
- `PENDING_CANONICAL_RERUN`
- `SUPERSEDED_INTERMEDIATE`
- `ENGINEERING_ONLY`
- `PLANNED_GLOBAL_ONLY`
- `BLOCKED_EXTERNAL_STORAGE`

## 6. 对每项分析生成“方法卡”

在 `docs/canonical/analysis_cards/` 下，每个正式/支持性分析生成一个 Markdown 方法卡。

每张卡必须包含固定章节：

### Purpose
分析回答什么科学问题，为什么服务最终报告。

### Inputs
真实输入文件、路径、字段、上游 provenance。

### Software / Environment
Python/R/MATLAB/Conda 环境；关键包版本；模型版本；GPU backend（如适用）。

### Procedure
从输入到输出的逐步步骤，要求别人能复现，不只是概述。

### Statistical specification
公式/模型 family、协变量、grouping、window、fold、bootstrap、FDR 等。

### QC / exclusions
什么条件排除 row/window/session；什么只 flag 不删。

### Outputs
每个输出文件：
- 文件名
- 格式
- 行单位
- 关键字段
- 是否含敏感 ID
- 是否允许上传 Git
- 下游用途

### Result reporting template
规定报告结果如何写。例如必须写：
- n participant / session / probe
- effect / AUC / OR / beta
- 95% CI
- p/q（需要时）
- matched cohort / folds（模型比较时）

给出一个不含虚构数字的规范结果段落模板。

### Current result
记录本机真实结果数字和当前解释边界。

### Repro command
从干净工作区执行的真实命令；若当前不存在稳定入口，标记 `NEEDS_PARAMETERIZED_ENTRYPOINT`，并在本任务中整理出可复用入口后再验证。

## 7. 软件与环境规范

生成：

`docs/canonical/SOFTWARE_ENVIRONMENT_MATRIX_V1.md`

逐项记录：
- analysis family
- OS
- Python/R/MATLAB version
- Conda env/path
- pip/conda package versions
- model/version/hash
- hardware backend
- CPU/GPU requirement
- deterministic settings / seed
- install/check commands
- known platform-specific difference

特别区分：
- general statistics / behavior / questionnaire：应尽量硬件无关；
- mmWave feature extraction：记录实际依赖；
- NIR/RGB engineering：NVIDIA `nvidia-cuda` 与 AMD `amd-DirectML` 可用不同 backend，但 scientific contract / schema 必须对齐。

## 8. 输出目录与文件格式规范

不要凭空设计。先读取现有真实输出，再收敛统一规则。

生成：

- `docs/canonical/OUTPUT_LAYOUT_V1.md`
- `docs/canonical/DERIVED_DATA_CONTRACT_V1.md`
- `docs/canonical/RESULT_REPORTING_STANDARD_V1.md`

### OUTPUT_LAYOUT_V1
明确：
- 本机每类 derived 数据实际保存位置；
- canonical 新输出应保存位置；
- 什么留本地；
- 什么进 Git；
- result package 命名规则；
- RUN_ID / version / manifest 命名规则。

### DERIVED_DATA_CONTRACT_V1
从真实表中冻结跨机器合并所需公共 key 和字段语义。至少明确：
- participant/session/probe key 语义
- `site`
- `phase`
- `program_family`
- block
- probe timestamp unit/timezone
- window boundaries
- label/vigilance
- QC flag semantics
- backend provenance
- schema version

不要在本任务中凭空强迫所有历史表改成相同列名；明确 canonical export adapter / mapping 即可。

### RESULT_REPORTING_STANDARD_V1
规定不同类型结果如何汇报：
- descriptive
- GEE/mixed model
- classification/CV
- matched modality increment
- bootstrap delta
- QC/coverage
- cross-site validation

每种类型明确必报字段和禁止省略字段。

## 9. 决策逻辑必须可追溯

生成：

`docs/canonical/DECISION_TRACE_V1.md`

不是复制聊天历史，而是整理真正影响分析设计的科学决策：
- 为什么主 endpoint 是 1 vs 2/3/4，同时保留四分类层；
- 为什么不能把 2/3/4 都称为 mind-wandering；
- 为什么主窗口/敏感性窗口这样设置；
- 为什么 participant-disjoint；
- 为什么 matched cohort；
- 为什么 C1/HRV 当前周期停止；
- 为什么 C2C/M1 后停止继续 mmWave normalization；
- 为什么 NIR旧结果 superseded；
- 为什么 RGB 工程与最终统计分开；
- 为什么 Beijing B1+B2 + Zhuhai B1+B2 为 shared primary，Zhuhai B3 为 extension；
- 为什么第4次及以上有效 formal session 不自动删除；
- 哪些决定是 protocol-driven，哪些是 data-driven，哪些是 post-hoc diagnostic。

每项决策给出：evidence → decision → downstream consequence。

## 10. 结果索引

生成：

`docs/canonical/RESULT_INDEX_V1.md`

每个结果必须说明：
- analysis_id
- 当前状态
- Git result path
- local full result path
- 文件内容介绍
- headline numbers
- 能否用于最终报告
- 若不能，原因
- superseded_by

解决目前“多个分支里都有结果、master 看不到最新状态”的问题。

## 11. 脚本可复现性检查

对于标记为 `CANONICAL_FINAL` / `VALID_SUPPORTING` / `PENDING_CANONICAL_RERUN` 且未来另一块数据盘需要执行的分析：

逐个验证：
- script 是否存在；
- 是否依赖硬编码本机绝对路径；
- 是否可以通过 config/CLI 指定 data root / output root；
- 是否会覆盖已有正式结果；
- 是否有 dry-run / input audit；
- 是否输出 run_manifest；
- 是否记录 code commit/config digest/seed；
- 是否可只处理指定 site/subject/session；
- 是否保留 row-level local-only 原则。

如果发现正式结果由一次性临时脚本生成，不能只把临时脚本原样发给同事。应整理成最小参数化入口，并在本机做 regression check：新入口应复现已有 headline results / row counts / schema（允许明确说明的浮点误差）。

生成：

`docs/canonical/REPRODUCIBILITY_AUDIT_V1.md`

## 12. 这一步暂时不要生成 AMD 正式 runbook

本任务只允许生成一个草案：

`docs/canonical/AMD_HANDOFF_REQUIREMENTS_DRAFT_V1.md`

内容只说明未来 AMD 分支需要哪些已审查模块与输出，不给同事“现在就执行”的最终命令。

正式 AMD branch / runbook 必须等 GPT-5.6 Sol 审查通过后再建立。

## 13. GPT 审查入口

生成：

`docs/canonical/SOL_REVIEW_ENTRYPOINT_V1.md`

它必须是一页式索引，告诉 GPT 审查时依次读取：
1. ANALYSIS_REGISTRY
2. DECISION_TRACE
3. REPRODUCIBILITY_AUDIT
4. DERIVED_DATA_CONTRACT
5. RESULT_REPORTING_STANDARD
6. RESULT_INDEX
7. SOFTWARE_ENVIRONMENT_MATRIX
8. 所有 analysis cards
9. 需要重点复核的 actual result files

并列出已知 unresolved items。

## 14. README 与项目入口

更新当前整理分支的 README/PROJECT_STATUS（保持历史可追溯），明确：

项目名称：`FocusWave Multimodal Attention Analysis`

项目目标：心理学有效性 + 行为基线 + 非接触传感器增量 + 多模态 + 跨站点验证。

不要再把项目入口写成单纯 HR/HRV 算法优化仓库。

同时更新唯一 `docs/WORKSPACE_LEDGER.md`：
- 当前本地 worktree
- 整理分支
- canonical assets
- 最新分析状态
- superseded 关系
- 下一步为 Sol review，AMD handoff 尚未批准

## 15. 完成标准

只有全部满足才可报告完成：

- 本地分析资产已经实际扫描，不是凭聊天整理；
- 每个正式分析有 registry entry；
- 每个保留分析有 method card；
- 输入/脚本/config/environment/output/result path 可追溯；
- 所有 result 文件有内容说明与状态；
- 旧/中间结果不会被误当最终；
- 软件与环境矩阵完整；
- cross-machine derived contract 已根据真实字段制定；
- reproducibility audit 已验证未来可执行入口；
- README / PROJECT_STATUS / WORKSPACE_LEDGER 已更新；
- 未上传 raw/敏感 row-level 数据；
- 未建立 AMD 正式执行分支；
- 所有改动 push 到 `codex/local-analysis-library-canonicalization-20260826`。

## 16. 完成后的回复格式

Codex 完成后只向用户/GPT汇报：

- `STATUS`
- branch
- commit SHA
- local worktree path
- inventory 总资产数量
- registry 中分析数量及各状态计数
- 找到的不可复现/一次性脚本问题
- 发现的 cohort/schema/路径冲突
- 已整理的 canonical executable entrypoints
- 仍未解决的问题
- 是否达到 `READY_FOR_SOL_REVIEW`

不要在完成后自动开始 AMD 分支或新的科学分析。
