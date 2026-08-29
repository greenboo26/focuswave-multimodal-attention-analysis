# Recommended analysis plan for morning

按 `FINAL_MERGE_READINESS_20260829.md` 的 A-F 计划执行：A 固定 70/46/1,400 canonical behavior/probe baseline；B 为 behavior+RGB，先过 RGB identity/QC gate；mmWave 全部标记为 `preliminary_screening_only`，不再使用“生命体征可用/只能体动”的硬分层。明早 mmWave 只进入 exploratory mmWave feature increment、quality-flag sensitivity analysis，以及 motion/target-lock/window-quality covariates；不进入 validated HR/RR/HRV 主分析。E 只取 68 个 canonical-intersection NIR completion subjects；F 暂缓 NIR 全队列、HRV 确认性分析以及任何“RGB=虹膜校正”的表述。

明早第一步：读取本目录四个 CSV，锁定 denominator、participant grouping、fold 和 missingness；任何结果若改变上述边界，先停在 PARTIAL，不直接进入主结论。


