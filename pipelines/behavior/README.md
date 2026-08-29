# Behavior pipeline

Canonical producers: `run_report_cohort_label_vigilance_v1.py` at `67851bff212fc1e73b9611ac5de670581e316cc7` and `run_final_report_cohort_baseline_v2.py` at `414a4f46c8d058961a87750345d06a7129afc9f2`. Source branches remain retained; this is an entrypoint map.

行为科学 v3 的正式修复入口是 `pipelines/behavior/behavior_science_v3/pipeline.py`。它只读取已经派生、去标识的行为表，不扫描真实数据目录、不创建身份映射，也不写死 44/38/6。当前 44 sessions / 38 current anonymous participant groups / 6 two-session repeat groups 仅作为外部运行时审计事实；未来约 72 场接入后必须重新构建完整匿名身份映射和参与者互斥分折。

v3 运行方式：

`python -m pipelines.behavior.behavior_science_v3.pipeline --tables-dir <derived_tables> --output-dir <new_output_dir>`

输入至少包含 `trial_metrics.csv`、`window_metrics.csv`、`block_metrics.csv`、`session_metrics.csv`、`error_trajectory_metrics.csv`。输出包括一 probe 一行的 `probe_primary_metrics_v3.csv`、分离的 `probe_window_sensitivity_v3.csv`、block/session 指标、session 内 B1–B2 配对、错误重叠审计、人内中心化/预错误基线变化、相关关系分类、Q1 模型、Q2 描述性 fail-closed 输出、模型失败表、participant-disjoint folds、按量纲森林图 manifest、QC 分母、候选证据矩阵、中文图表与 `report_manifest_v3.json`。

科学边界：Go omission（遗漏）与 No-Go commission（误按）保留各自机会分母，不合成一个 `correct` 正式因变量；Q1 固定为无序四分类并要求 participant/session 重复测量结构；Q2 在没有经过审计的 participant/session 聚类有序模型后端前禁止正式推断；模型失败必须进入 `model_failures_v3.csv`，不能静默为空。工程测试通过不等于行为测量效度、真实 44 场统计结论或心理机制结论通过。

v3 契约与判退边界见 [`docs/methods/行为科学v3判退缺陷规范.md`](../../docs/methods/行为科学v3判退缺陷规范.md) 和 [`contracts/behavior/行为科学v3分析契约.json`](../../contracts/behavior/行为科学v3分析契约.json)。被判退的 v2 脚本副本位于 [`scripts/rejected_baselines/behavior/generate_behavior_science_analysis_v2_rejected_baseline.py`](../../scripts/rejected_baselines/behavior/generate_behavior_science_analysis_v2_rejected_baseline.py)，只读保留，不得作为正式生产入口，也不得在其上继续修统计逻辑。
