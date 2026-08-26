# Sol review entrypoint v1

请按以下顺序进行独立科研方法审查：

1. `ANALYSIS_REGISTRY_V1.md` / `.csv`
2. `DECISION_TRACE_V1.md`
3. `REPRODUCIBILITY_AUDIT_V1.md`
4. `DERIVED_DATA_CONTRACT_V1.md`
5. `RESULT_REPORTING_STANDARD_V1.md`
6. `RESULT_INDEX_V1.md`
7. `SOFTWARE_ENVIRONMENT_MATRIX_V1.md`
8. `analysis_cards/` 下所有方法卡
9. registry 指向的 actual result manifests/reports（仅通过本地路径由 Codex 核验，Git 不含 raw/row-level data）

重点复核：C2 binary endpoint 与四分类边界、participant-disjoint grouping、Beijing/Zhuhai cohort、C1 HRV blocker、C2C/M1 stopping logic、NIR/RGB engineering 与 scientific increment 的分离，以及所有 hard-coded path/历史 worktree 入口。

当前 unresolved：无 `CANONICAL_FINAL`；多个历史入口未参数化；Python/package/model digest 不完整；NIR/RGB formal increment 未冻结；Zhuhai B3 仍是 extension；C1 alignment/HRV 未通过；global merged cohort 和 cross-site validation 未开始。达到 `READY_FOR_SOL_REVIEW` 的条件只要求本地事实审计、文档和自检完成，不表示科学结论已通过。
