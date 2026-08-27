# FocusWave Multimodal Analysis repository instructions

跨客户端项目发现入口：先读根目录 `AI_PROJECT.md`。它只负责项目身份、canonical repository、中央治理/workspace 指针和 related-repository role boundary；本仓库科学/分析真相仍以本文件、`README.md`、`PROJECT_STATUS.md`、canonical method/runbook/contract 和当前 Git 证据为准。

中央跨 AI 治理唯一来源是 `greenboo26/ai-governance@main`；workspace 注册表是 `greenboo26/project@august/PROJECT_INDEX.md`。本文件是项目级规则，可在中央 hard-rule 边界内做项目 specialization，但不是全局治理源。

本仓库是 FocusWave 正式中央分析仓库，不是原始数据仓库，也不是单一毫米波 HRV 项目。任何机器 clone 后，先读取 `AI_PROJECT.md`、本文件、根目录 `ANALYSIS_HISTORY_LEDGER.md`、`README.md`、`PROJECT_STATUS.md`、相关 analysis card/contract；执行已完成本地分析的规范化复现时，再读取 `docs/repository/LOCAL_ANALYSIS_REPRODUCTION_RUNBOOK_V1.md`。

`ANALYSIS_HISTORY_LEDGER.md` 是任何新算法、新特征、新 producer 改动或高成本重跑前的强制 Reuse Gate。必须先检查同类路线是否已经运行、采用、回退、被后续证据替代或存在 `MISSING_EVIDENCE`。若要重复已有路线，任务开头必须写明旧证据为什么不能回答当前问题；写不出来时默认不重复计算。

机器外层的个人工作区规范（例如父目录 AGENTS/项目管理规范）如果存在可以补充读取，但不得作为本仓库可执行性的必需依赖。本仓库不得要求另一台机器存在某个固定 `D:\...` 工作区文件。

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