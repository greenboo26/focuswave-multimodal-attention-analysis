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

本轮 correction 已解决/收口：北京 70/46/1400 baseline、Probe-before aggregate package、真实 producer provenance、local/global identity boundary、AMD/NVIDIA ref/blob audit 和最小 AMD module surface。剩余 review 重点：历史入口的完整可运行性、ordinal proportional-odds diagnostic、NIR/RGB parity execution evidence、global merged cohort。AMD 仍未建立，达到 `READY_FOR_SOL_REREVIEW` 不表示科学结论已自动批准。
