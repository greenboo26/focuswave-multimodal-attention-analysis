# FocusWave Multimodal Analysis repository instructions

跨客户端项目发现入口：先读根目录 `AI_PROJECT.md`。它只负责项目身份、canonical repository、中央治理/workspace 指针和 related-repository role boundary；本仓库科学/分析真相仍以本文件、`README.md`、`PROJECT_STATUS.md`、canonical method/runbook/contract 和当前 Git 证据为准。

中央跨 AI 治理唯一来源是 `greenboo26/ai-governance@main`；workspace 注册表是 `greenboo26/project@august/PROJECT_INDEX.md`。本文件是项目级规则，可在中央 hard-rule 边界内做项目 specialization，但不是全局治理源。

本仓库是 FocusWave 正式中央分析仓库，不是原始数据仓库，也不是单一毫米波 HRV 项目。任何机器 clone 后，先读取 `AI_PROJECT.md`、本文件、根目录 `ANALYSIS_HISTORY_LEDGER.md`、`README.md`、`PROJECT_STATUS.md`、相关 analysis card/contract；执行已完成本地分析的规范化复现时，再读取 `docs/repository/LOCAL_ANALYSIS_REPRODUCTION_RUNBOOK_V1.md`。

## 既有项目结构与实质进展追溯门

进入项目后先服从本仓库已有的 `ANALYSIS_HISTORY_LEDGER.md`、`docs/canonical/`、`PROJECT_STATUS.md`、`docs/`、`scripts/`、`results/`、contract 和 manifest 结构。不得新造平行状态文档、平行 `output/` 结构或临时 Git 仓库；组织文件不能替代项目已有的历史账本、当前状态地图和结果 provenance。

任何新脚本、重跑、结果变化、方法决定、否决路线或输入语义修正，只要产生实质进展，必须在同一次工作中更新适用的历史账本/当前进度、脚本索引或 runbook、结果/图表/表格索引、manifest/provenance、`CHANGELOG.md` 和 handoff。每次材料性提交还必须明确：修改路径、脚本/入口路径、结果路径、tracked 与 local-only 输出边界、验证方式、决策/阶段变化和下一步。没有某类资产时明确写 `N/A`，不得把路径只留在聊天或临时 agent 输出中。

若本仓库通过 `D:\Project\厚粲杯\08_算法` 的本机工作副本协作，外层工作区规则可作为补充：使用已经存在的 `D:\Project\厚粲杯\01_管理` 管理文件和 `08_算法/docs/00_治理/` 规范，不复制出第二套状态或结果体系；该路径不是远程 clone 的必需依赖。

Git worktree、临时 clone、运行态、原始数据和大型结果在归档证据、唯一提交、旧路径引用和活动任务核验完成前不得移动或删除；不得用 `reset`、`clean` 或普通文件操作制造同步假象。

`ANALYSIS_HISTORY_LEDGER.md` 是任何新算法、新特征、新 producer 改动或高成本重跑前的强制 Reuse Gate。必须先检查同类路线是否已经运行、采用、回退、被后续证据替代或存在 `MISSING_EVIDENCE`。若要重复已有路线，任务开头必须写明旧证据为什么不能回答当前问题；写不出来时默认不重复计算。

机器外层的个人工作区规范（例如父目录 AGENTS/项目管理规范）如果存在可以补充读取，但不得作为本仓库可执行性的必需依赖。本仓库不得要求另一台机器存在某个固定 `D:\...` 工作区文件。

## User-facing communication

面向用户汇报时，默认使用中文、短句和直接结论。内部 agent/仓库仍可保留完整英文技术记录、审计表、状态词和证据链，但不要把这些内部材料原样当作用户说明。

除非用户明确要求详细技术版，否则每次阶段性汇报优先按下面四个问题组织：

1. 现在在做什么？
2. 为什么做这一步？
3. 已经发现了什么？
4. 下一步是什么？

专业术语第一次出现时，用一句人话解释。`canonical`、`gate`、`producer`、`ledger`、`PARTIAL/BLOCKED` 等内部治理或工程词不能只给词不解释；需要使用时，应同时说明它对当前研究结论意味着什么。

不要用大段英文文件名、路径、commit、表格或 agent 间交接文本替代解释。证据路径和版本信息可以保留在回答末尾或用户要求时展开。优先先告诉用户“结果代表什么、能不能信、为什么、现在卡在哪里”。

如果一个结果仍有多种解释，要明确区分“数据事实”“当前判断”“尚未解决的问题”，不要用抽象状态词掩盖不确定性。进度汇报应让用户能在不打开仓库文件的情况下理解当前项目位置。

## Scope

- 只提交 Git-safe 的脚本、配置、schema、聚合结果、方法、provenance 和索引。
- 原始波形、视频、participant-level/row-level 数据、缓存、认证、机器私有路径和大型输出不入 Git。
- 已经完成的北京行为、问卷、mmWave 等本地分析，应通过 `scripts/canonical/run_local_analysis.py` + 未跟踪的 `configs/paths.local.json` 绑定本机路径；禁止再靠聊天记忆或硬编码盘符作为正式入口。
- NIR/RGB 外部代码仓库是生产源；本仓库保存 ref/commit、schema、contract、QC 和中央分析入口，不复制外部 raw data。
- global identity、global cohort、participant-disjoint global folds 和最终跨站点 inference 只能在中央阶段冻结。

## Status vocabulary

`CANONICAL` 只用于已核验、可追溯并允许进入当前报告的资产；`CANONICAL_EXECUTABLE` 还必须通过规范化复跑及 aggregate equivalence gate；`RESTORED_CANONICALIZATION_CANDIDATE` 表示 producer 已恢复和参数化但尚未完成本机等价复跑；`SUPPORTING` 是边界或稳健性证据；`ENGINEERING_REFERENCE` 不是正式科学结果；`SUPERSEDED` 只能经 provenance 引用；`PENDING/BLOCKED` 不得写成完成。

## Change and verification

- 不重跑探索性科学分析，不改变既有 label/window/fold/seed/model/QC 定义来追求更好结果。
- 历史 producer 可以从 immutable archive ref 恢复到 canonical pipeline surface，但必须保留 source ref/provenance，并只做执行层参数化。
- 新增路径必须更新 architecture/runbook/registry，并执行 Python syntax/tests、JSON/CSV/path smoke checks、`git diff --check` 与敏感文件扫描。
- 规范化复跑成功后必须写 `canonical_run_manifest.json`；随后用 `scripts/canonical/compare_reproduction.py` 对照已接受 aggregate package。equivalence 未通过前不得提升为 `CANONICAL_EXECUTABLE`。
- 提交前检查 staged paths，确认无 raw/row-level 数据和机器私有 paths config。
- 任何实际运行若产生“采用 / 放弃 / 结果无效 / reference 被替代 / 输入语义修复”等新历史决策，同一次交付必须更新 `ANALYSIS_HISTORY_LEDGER.md`，避免后续智能体重复运行。
