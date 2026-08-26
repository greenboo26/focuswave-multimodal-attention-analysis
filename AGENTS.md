# FocusWave Multimodal Analysis repository instructions

本仓库是正式分析总仓库 candidate，不是原始数据仓库，也不是单一毫米波 HRV 项目。修改前先读取根目录 `D:\Project\AGENTS.md`、`D:\Project\项目文件管理与AI执行规范.md`，再读取本 README、`docs/WORKSPACE_LEDGER.md` 和相关 contract。

## Scope

- 只提交 Git-safe 的脚本、配置、schema、聚合结果、方法、provenance 和索引。
- 原始波形、视频、participant-level/row-level 数据、缓存、认证、机器私有路径和大型输出不入 Git。
- NIR/RGB 外部代码仓库是生产源；本仓库保存 ref/commit、schema、contract、QC 和中央分析入口，不复制外部 raw data。
- global identity、global cohort、participant-disjoint global folds 和最终跨站点 inference 只能在中央阶段冻结。

## Status vocabulary

`CANONICAL` 只用于已核验、可追溯并允许进入当前报告的资产；`SUPPORTING` 是边界或稳健性证据；`ENGINEERING_REFERENCE` 不是正式科学结果；`SUPERSEDED` 只能经 provenance 引用；`PENDING/BLOCKED` 不得写成完成。

## Change and verification

不重跑探索性科学分析，不物理移动 import-sensitive legacy producer。新增路径必须更新 migration manifest 或 architecture index，并执行 CSV/Markdown/path smoke checks、`git diff --check` 与敏感文件扫描。提交前检查 staged paths，确认无 raw/row-level 数据。
