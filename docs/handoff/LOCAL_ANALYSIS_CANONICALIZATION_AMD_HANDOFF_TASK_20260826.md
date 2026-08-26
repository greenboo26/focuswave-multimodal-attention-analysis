# LOCAL_ANALYSIS_CANONICALIZATION_AND_AMD_HANDOFF_V1

## 任务目的

把当前 NVIDIA/本地硬盘已经完成的正式分析整理为一套可复现、可交接、可在另一块正式数据盘上等价执行的分析规范。最终目标是让 AMD 工作站只需要拉取远端 GitHub、读取本规范和对应代码入口，就能对其本地的珠海 + 部分北京正式数据生成与 NVIDIA 侧同 schema 的派生结果；最后两侧仅合并标准派生数据，再做全局身份、统一 folds、跨站点与多模态最终统计。

本任务首先是本地事实审计与规范化，不新增探索性算法，不为了整理而重算已经完成且可复用的正式结果。

## 权威仓库

### 总体分析/毫米波/行为/问卷
`greenboo26/mmwave-hrv-analysis`

### NIR/RGB 模态工程
`kyandi233-dev/Attention-Analysis`

NVIDIA 工作站使用 `nvidia-cuda`；AMD 工作站使用 `amd-DirectML`。两者允许硬件后端不同，但科学定义、时间轴语义、feature schema、QC schema 和最终统计输入语义必须可对齐。

## 唯一总账

`docs/WORKSPACE_LEDGER.md` 已被定义为本项目唯一工作区总账。不要创建第二份 ledger。完成本任务后必须更新该总账，把当前本地事实、正式分析状态、权威入口、输出目录和 superseded 关系写清楚。

## 第一阶段：本地事实审计

请实际读取本机，不要根据聊天记录猜路径。

至少审计：

1. `D:\Project\厚粲杯\08_算法\`
2. `D:\Project\厚粲杯\11_数据\derived\`
3. 当前 `mmwave-hrv-analysis` 所有本地 worktree/branch
4. `Attention-Analysis_nvidia-cuda` 本地 worktree
5. 当前正式 NIR 输出目录
6. 当前正式 RGB 输出目录
7. 当前行为、问卷、身份 crosswalk、canonical probe master、mmWave feature matrix 的实际位置

输出 `LOCAL_WORKSPACE_INVENTORY.md`，每个 worktree/数据资产记录：

- local path
- repository
- branch
- commit
- purpose
- input root
- output root
- status
- whether row-level/raw data are local-only

## 第二阶段：建立“已做分析注册表”

生成 `ANALYSIS_REGISTRY_V1.csv` 和可读版 `ANALYSIS_REGISTRY_V1.md`。

每一项已经做过的正式分析必须至少记录：

- `analysis_id`
- 中文名称
- 科学问题
- 输入资产及精确本地路径
- 生成输入的上游 RUN_ID/脚本（可追溯时）
- 实际执行脚本精确路径
- Git branch / commit
- cohort 定义
- participant grouping key
- session/probe/trial 单位
- label 定义
- time window 定义
- feature set
- QC 规则
- model family
- CV / participant-disjoint 规则
- bootstrap / CI 方法
- multiple-comparison correction（如适用）
- 输出目录
- 核心输出文件
- 核心结果数字
- 科学结论边界
- 状态：`CANONICAL_FINAL` / `VALID_SUPPORTING` / `SUPERSEDED_INTERMEDIATE` / `ENGINEERING_ONLY` / `PENDING_FINAL_RERUN`
- superseded_by（如有）
- 是否需要 AMD/另一块盘复现
- AMD 侧需要生成什么派生输出

至少覆盖并核对：

### protocol / identity / cohort
- 北京—珠海 protocol identity harmonization
- canonical identity master
- C2A dataset audit
- REPORT_ANALYSIS_COHORT 70 sessions / 46 participants / 1400 probes

### behavior / labels
- Beijing formal behavior longitudinal
- pre-probe 10/20/30 s behavior trajectories
- B1-late → B2-early recovery comparison
- REPORT_COHORT_LABEL_VIGILANCE_V1
- REPORT_REPEAT_SESSION_EFFECTS_V1
- FINAL_BEHAVIOR_CONTEXT_BASELINE_V1（明确记录它当前使用 1440-probe fallback，状态应为 `PENDING_FINAL_RERUN`，等待 1400-probe V2）

### questionnaire
- Q1 questionnaire criterion validity
- 核对 canonical label 3/4 中文语义，修正文档描述不一致但不擅自改变数值结果

### mmWave
- C1 alignment / beat / IBI / HRV validation
- C2B-V2 canonical absolute mmWave increment
- C2C personalized resting calibration
- M1 person-effect variance audit
- 已有早期 sensor increment baseline，标明 superseded 关系

### NIR
- C3A v1 OLD_SUBSET
- C3A v2 14-participant intermediate
- 当前 69/69 eligible source sessions fullclass 工程完成状态
- 明确最终 69-session Probe-level increment 尚待完成，不把旧 14-person结果当最终结论

### RGB
- Motion/Pose scientific validation
- Face backend benchmark
- NVIDIA CUDA Gate / full-video runner 当前真实状态
- 不把工程 Gate 写成已经完成的 attention prediction result

### cross-site
- D1 Beijing-Zhuhai harmonization
- 将当前科学解释写为 `DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE`（若本地事实仍支持：另一块盘不在当前机器），而不是把“未在本机链接到珠海数据”写成数据不存在

## 第三阶段：冻结跨机器数据生产契约

生成 `CROSS_MACHINE_DERIVED_DATA_CONTRACT_V1.md` 和 machine-readable `schemas/`。

不要凭空规定字段。必须先从当前实际分析输入、当前 NIR/RGB schema、canonical master 中提取可复用字段，再冻结最终最小必要字段。

至少定义以下层级：

### A. session manifest
建议语义至少覆盖：
- local subject/session code
- site
- phase
- program family/version
- formal session index（如本地可确定）
- collection reason（如可确定）
- modality availability/QC
- source disk provenance
- runtime backend
- pipeline version
- git commit
- schema version

### B. probe master
至少能够确定：
- local session key
- block
- probe ordinal/id
- probe unix ms
- probe_response
- probe_vigilance
- protocol progress
- site/program family

### C. behavior Probe features
冻结你当前实际使用的 10/20/30 s 行为字段与计算公式；不只写文件名。

### D. questionnaire session features
定义问卷—session bridge、题目编码、缺失与 provenance；珠海“是否参加第一阶段”只作为 identity/provenance 辅助，不作为心理预测变量。

### E. mmWave Probe features
冻结当前 C2B/C2C 所用 feature family、10/30/60 s窗口、absolute 与 resting-calibrated 的计算方式、QC、输出 schema。
当前周期不重新开发 HRV detector。

### F. NIR Probe features
以当前正式 fullclass scientific contract 为准，定义 10/30/60 s aggregation、QC、feature names/version、unix-ms alignment。
AMD/NVIDIA 的 backend provenance保留，但 feature语义一致。

### G. RGB Probe features
以 Attention-Analysis 当前 Face/Pose/Motion scientific contract 为准，定义 raw→derived→probe-window 汇总关系和 QC。只有当前正式 runner 已经实际支持的字段进入“可立即生产”集合；仍待冻结的 blink/PERCLOS event threshold 等明确标为 pending，不假装已经正式冻结。

## 第四阶段：为 AMD 同事生成可直接执行的 runbook

生成：

`docs/handoff/AMD_EXTERNAL_DISK_ANALYSIS_RUNBOOK_V1.md`

目标读者是假设不了解当前本机历史的同事/Codex。它必须从 Git pull 开始，按实际仓库/分支/环境执行，并明确每一步输入、命令/脚本、输出、成功判据和遇到 blocker 时怎么记录。

Runbook 按依赖顺序组织：

1. 仓库/commit/environment preflight
2. data discovery + local session manifest
3. behavior / Probe canonicalization
4. questionnaire linkage
5. mmWave frozen feature production（若该盘存在 mmWave）
6. NIR AMD formal/fullclass + QC + Probe features
7. RGB AMD DirectML formal + QC + Probe features
8. local export validation
9. 生成 `SITE_LOCAL_DERIVED_PACKAGE_V1`
10. 只把允许同步的标准派生结果/脱敏汇总通过约定方式交回；原始/行级敏感数据继续遵守项目数据边界

### 每一步必须写清楚
- 运行哪个脚本，不允许只写“分析行为”
- 使用什么参数/配置
- 哪些字段是结果
- 哪些文件必须出现
- 行数/coverage 等基本一致性检查
- 如何识别 complete / partial / blocked
- 输出中必须记录的 version/hash/provenance

## 第五阶段：定义“本地可独立做”与“必须中央合并后做”

生成 `CENTRAL_INTEGRATION_BOUNDARY_V1.md`。

明确：

### 各机器可以独立完成
- raw/video/session → modality derived features
- local timeline/probe alignment（只要使用统一 contract）
- local session/probe QC
- local descriptive QC summary
- local questionnaire bridge
- frozen mmWave/NIR/RGB feature generation

### 最终中央统一完成
- 全局 natural-person / repeat_participant identity reconciliation
- Beijing + Zhuhai canonical report cohort
- 最终 site/program-family inclusion
- participant-disjoint fold assignment
- matched-cohort model comparisons
- final behavior/context baseline V2
- final NIR increment
- final RGB increment
- NIR+RGB multimodal fusion
- mmWave final ablation/recheck
- Beijing↔Zhuhai pooled/site/external validation
- participant-level bootstrap and final report statistics

不要在两台机器各自训练最终模型后对 AUC 做平均。

## 第六阶段：整理本地目录，但保持可追溯

当前本地可能较乱。整理原则：

1. 先盘点，再移动；
2. 原始数据路径不做大规模重排；
3. 已有正式 derived 结果不覆盖；
4. 对重复/过时目录先建立映射和 superseded 标记；
5. 只有在确认无下游引用后才调整目录；
6. 尽量通过 registry + manifest 解决“找不到/不知道哪个最新”，而不是为了整洁改动大量历史路径。

如果确实需要整理脚本或新建 wrapper，请保持原始入口可追溯，并记录旧→新映射。

## 第七阶段：验证 AMD runbook 真的可执行

在本机不能执行 AMD DirectML 时，不伪造 AMD 成功。

需要做静态验证：
- runbook 引用的 Git 文件/脚本真实存在
- AMD branch 的环境/入口与当前 README 对得上
- schema 与 NVIDIA 侧输出能够字段级映射
- 没有引用仅存在于本机、GitHub 未提交的脚本作为同事唯一入口

如果发现 AMD 侧缺少行为/问卷/mmWave 某个可复用执行入口：
- 记录为 blocker
- 优先把当前已验证本地脚本泛化成参数化入口并提交，而不是让同事手工复制命令片段
- 新入口必须先在当前本地数据上回归验证，确认与既有正式结果一致或差异可解释

## 必须形成的 Git 交付物

至少：

- 更新后的唯一 `docs/WORKSPACE_LEDGER.md`
- `docs/handoff/LOCAL_WORKSPACE_INVENTORY.md`
- `docs/handoff/ANALYSIS_REGISTRY_V1.md`
- `docs/handoff/ANALYSIS_REGISTRY_V1.csv`
- `docs/handoff/CROSS_MACHINE_DERIVED_DATA_CONTRACT_V1.md`
- `docs/handoff/AMD_EXTERNAL_DISK_ANALYSIS_RUNBOOK_V1.md`
- `docs/handoff/CENTRAL_INTEGRATION_BOUNDARY_V1.md`
- schema files / templates（如确有需要）
- 如新增参数化 wrapper：对应 script + 最小回归测试

## 最终回报格式

完成后不要只说“整理好了”。请逐项回报：

1. 本机实际发现了哪些权威输入/输出根目录
2. 一共登记多少项 analysis_id
3. 哪些是 CANONICAL_FINAL
4. 哪些是 SUPERSEDED_INTERMEDIATE
5. 哪些是 PENDING_FINAL_RERUN
6. 哪些分析 AMD 侧可以直接按 Git 复现
7. 哪些缺少可复用 Git 入口，已经如何修复/仍为何 blocker
8. AMD runbook 的精确路径
9. cross-machine data contract 的精确路径
10. 是否移动/重命名了任何本地文件；如有列出旧→新映射
11. branch
12. commit SHA

完成后先读取并自检所有交付文档中的路径、脚本名和状态，再 push。
