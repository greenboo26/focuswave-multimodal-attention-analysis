# 结果目录与文件内容详细交接

日期：2026-08-28
目标分支：`codex/mmwave-formal-reanalysis-v2`
仓库：`greenboo26/focuswave-multimodal-attention-analysis`
状态：只登记和说明既有结果，不复制原始数据，不重新运行分析。

## 1. 交接范围与阅读状态

本交接说明覆盖本机 `D:\Project\厚粲杯` 中已经形成结果或结果审计意义的目录，并保留正式结果、阶段性结果、历史副本、训练输出和阻塞性审计的区别。结果文件已经按原路径逐项打开核验；重复 worktree 和版本目录不合并。

详细逐文件审计原件仍保留在本机，不随代码仓库上传：

- `D:\Project\厚粲杯\08_算法\work\output_content_audit_20260828\INDEX.md`
- `D:\Project\01_管理\06_数据盘点\工作树与handoff_结果逐文件记录_2026-08-28.md`

原因：原始输出审计约 98 MB，含大量可再生输出、逐窗结果、图片和二进制文件；本仓库只提交可追踪的目录交接说明。

## 2. `08_算法\output`：算法主输出

该目录约 2,134 个文件，包含文本结果、表格、JSON、日志、NPZ、图片、Excel 和压缩包。各一级目录含义如下。

### `00_索引与审计`

输出总索引、结果清单、审计 CSV/JSON/NDJSON、Excel 汇总和索引图。用于回答“结果由什么脚本生成、输入是什么、是否通过质量门控”，不是新的统计模型。

### `10_质量控制`

行为时间门控、时间覆盖、有效窗口、裁剪清单、质量汇总、QC 日志和质量图。这里的结果用于决定哪些窗口可以进入后续建模；被排除的窗口不能当作阴性结果。

### `20_生理金标准验证`

毫米波与 ECG/RSP 的对照、HR/BR/HRV 逐窗结果、VMD/呼吸谐波比较、校准表、质量曲线和诊断图。正式可用的边界是：HR 校准保留 99 个完整配对窗口，HR MAE 约 5.02 bpm；RSP 频谱 BR MAE 约 5.18 次/分；峰间隔 BR 结果不进入正式结论。

### `30_预实验与原型`

预实验、近场、REST、深呼吸、早期算法和逐窗试验产物。包括 NPZ、JSON、CSV、PNG 和中间日志。它们用于方法探索和故障定位，不能与正式 J_Data 队列结果混合。

### `40_正式实验`

J_Data 正式批次、M1/Q0、LOSO（Leave-One-Session-Out，留一场次验证）、窗口级结果、质量结果和诊断图。主要结论是毫米波特征没有显示超过行为基线的稳定增量；这不是“毫米波没有信息”的证明。

### `50_多模态与报告`

行为、毫米波、NIR/RGB 的 Logistic/Forest 比较、结果表、报告底稿和图表。必须同时查看 cohort、时间窗、标签和折叠策略，不能只看单一 AUC。

### `90_历史归档`

旧批次、旧算法、早期正式实验和已经被新版本替代的报告。保留用于追溯，不作为当前主结果。

### `J_Data_ALERTNESS_EVENTS`

警觉度探针事件前后窗口、HR/BR 变化、LMM/GEE 结果和报告。当前已知 1,400 个事件、1,056 个 HR 前后配对可信事件；FDR 后三个焦点项没有稳定警觉度特异效应。固定 bin 敏感性中一般事件后 HR 的 q=.011，但警觉度交互 q=.283，故结论受测量路径限制。

### `J_Data_NIR_SAMPLED_BATCH` 与 `J_Data_NIR_SAMPLED_PILOT`

NIR 抽样批处理、试跑 CSV/JSON 和日志。用于验证管线，不代表全量正式 NIR 结果。

### `J_Data_NIR_TEACHER_STAGE1`

NIR 教师信号第一阶段资产、时间对齐和质量说明。当前用于管线验收和特征定义，不能代替正式全量统计。

### `J_Data_NIR_V1`

早期 NIR 窗口、CSV/JSON、日志和约 185 张 overlay JPG。它是阶段性视觉结果，必须与后续 69-session 正式统计和 71-session 队列重建分开。

## 3. NVIDIA CUDA 主线 NIR 结果

路径：`08_算法\01_Attention-Analysis_nvidia-cuda\docs\020-nir\results`

### `nir_v1_formal_stats_v1`

69 sessions、1,174 probes、47 个 participant clusters 的第一版正式 NIR 统计。30 秒 GEE 主模型中：PIR 被试内偏差 OR=1.111，95% CI 0.968–1.275，p=.133；PIR MAD OR=.888，p=.184；robust slope OR=1.066，p=.256。response 计数为 1/2/3/4 = 885/190/40/59。

其中 `model_summary.csv`、`primary_model_summary.csv`、`response_descriptive.csv`、`sensitivity_summary.csv`、`vigilance_model_summary.csv` 和 `provenance.json` 是表格/模型/来源文件；4 张 figure 分别展示 response 内 PIR、预测 fully-focused 概率、警觉度 PIR 和 10/20/30 秒 OR 森林图。

结论：PIR 方向略正，但主结果没有统计决定性；PIR slope 受任务进程和警觉度影响，不能直接解释为注意特异效应。

### `nir_incremental_value_v1`

在同一 69-session/1,174-probe 队列上比较 Behavior、Behavior+NIR、Behavior+mmWave、Behavior+mmWave+NIR。ROC-AUC 依次为 .5659、.5989、.5714、.5803；Behavior+NIR 相对行为基线 ΔAUC=.0330，95% CI [-.0051,.0750]。AUC 和 balanced accuracy 区间跨 0，不能称为稳定独立提升；特异度上升但灵敏度和 F1 下降。

### `nir_matched_cohort_regeneration_v1`

队列重建审计，不是新模型：matched sessions 由 68 增至 71，probes 由 1,360 增至 1,420；primary coverage 1,174，sensitivity-inclusive 1,212，sensitivity-only 38，excluded 208。`sub-099` 仍因缺少 `master_timeline.csv` 和 `meta.json` 被排除。新计数不能直接当作重跑后的正式统计结果。

### `nir_timestamp_mapping_recovery_v1`

记录 frame index、capture counter、有效 timestamp 行、AVI gap 和时间间隔定义，并验证 sub-056/057/058/100/178。sub-100 和 sub-178 完成 recovery、full-class extension 和 probe alignment；均未发现 AVI decode/frame gap。该结果不改变 sub-099 的时间轴缺失。

### `nir_v1_scientific_fix`

最小 PIR 科学特征层 dry-run：primary 1,174、sensitivity-only 38、excluded 208，总队列 1,420 probes，输出 4,260 行（71×20×3）。30 秒 fused PIR median=.3227，mean=.3306，SD=.0670；至少一只眼有 PIR 为 1,413/1,420，双眼均有 PIR 为 1,384/1,420。尚未替换既有正式统计。

## 4. `11_数据\derived`：派生结果目录

该区共约 300 个子目录、1,500 个文件。主要目录逐个说明如下：

- `analysis_tables_v1/v2`：分析表格的不同版本，记录模型汇总和字段变化。
- `focuswave_canonical_v1`：第一版 canonical 数据、行为、问卷、重复 session 和 producer output。
- `focuswave_canonical_v1_rerun_20260826`：同一 canonical 合同的重跑版本，约 225 个文件；必须以 rerun 版本号区分旧结果。
- `c2b_v2_canonical_baselines_20260826`：C2B v2 行为/上下文/毫米波基线和严格匹配指标，约 41 个文件。
- `c2c_within_subject_normalization_v1`：被试内雷达校准/归一化和模型比较，约 24 个文件。
- `final_behavior_context_baseline_v1`：行为与上下文基线旧版本。
- `final_report_cohort_baseline_v2`：正式报告 cohort 基线，含 10/20/30 秒指标、校准表、固定折叠和运行来源。
- `report_cohort_label_vigilance_v1`：报告 cohort 的警觉度标签、覆盖和限制。
- `report_repeat_session_effects_v1`：重复 session、被试效应和敏感性分析。
- `ecg_mmwave_v311_rerun_v1`：v3.1.1 ECG-毫米波重跑、逐窗质量、HR/IBI/HRV 和诊断结果。
- `ecg_rsp_goldclean_pairing_v1`：ECG/RSP 金标准清洗与严格配对。
- `formal_nir_quality_audit_v1`：正式 NIR session、probe-window 和质量分层审计。
- `formal_nir_probe_windows_quality_tiered_v1/v2/v3`：NIR 探针窗口的不同质量分层版本。
- `nir_69session_final_probe_analysis_v1`：69-session 正式 NIR 探针分析，状态为 `COMPLETE_WITH_CANONICAL_ATTRITION`。
- `nir_v1_scientific_fix_v1`：PIR 科学特征修复版本，属于特征层，不等于新正式统计。
- `j_m1_q0_71_rerun_v1`：J_Data 71 批次 M1/Q0 重跑和严格 LOSO 结果。
- `j_mmwave_target_lock_audit_v1`：距离、时间稳定性、空间一致性和 RGB 门控的目标锁定审计。
- `questionnaire_session_analysis_v1`：问卷与 session 层结果。
- `questionnaire_criterion_validity_v1`：问卷效标效度结果。
- `questionnaire_measurement_audit_v1`：问卷测量完整性和字段审计。
- `beijing_c2_identity_reuse_event_analysis_v2`：北京 C2 身份复用、事件和被试内重复分析。
- `beijing_sensor_increment_v1`：北京传感器增量价值分析。
- `beijing_zhuhai_canonical_harmonization_v1`：北京/珠海 canonical harmonization，当前受实际 session 连接限制。
- `rs6240_data_chain_technical_gate_v1`：RS6240 数据链技术门控；device-only 通过，firmware/Tx timing 阻塞，不能推进 complex coherent fusion。
- `vitalsense_c1b_benchmark_v1`：VitalSense C1b 外部基准预检。
- `vitalsense_official_reproduction_v1`：官方路线复现及 48 sessions 结果，仍不足以宣称逐搏 IBI/HRV 已验证。
- `external_vitalsense_benchmark_preflight_v1`：外部基准访问、格式和预检，不是本项目正式 cohort。
- `stable_data_inventory_v1`：稳定数据资产清单。
- `subject_modalities_v1`：被试/场次/模态覆盖表。
- `mounted_nonformal_data_audit_v1`：挂载数据的非正式来源审计。
- `zhuhai_session_linkage_nir_event_readiness_v1`：珠海接入准备；30/30 登记记录存在，但 0/30 连接实际 behavior、timeline 或 radar/NIR/RGB session，状态为 `BLOCKED_ACTUAL_SESSION_LINKAGE`。

其余 `mmwave_reanalysis_v2_*`、`sub099_*`、`zhuhai_*` 目录均按版本独立保留：前者是毫米波重分析，后两者分别是 sub-099 缺失/恢复核查和珠海接入核查，不能因名称相近而合并。

## 5. 工作树和 handoff 结果

`worktrees\final-report-cohort-baseline-v2\docs\results` 包含 Q1 问卷效标、正式行为/上下文基线、校准表和固定 participant-disjoint folds。30 秒 C+B 的 ROC-AUC=.675，B-only=.639，C-only=.593；正式 cohort 为 1,400 probes、70 sessions、46 participants。

`handoff_c1c2a_20260826\docs\results` 包含 C1 对齐协议、C1c/C1d pilot、C2a 标签审计和 C2b 基线。C1 fixed/oracle/held-out F1 分别约 .223/.362/.314；C1d DP adapter 平均 F1=.1974，低于 local peak .2483；C2a 为 1,440 probes、72 sessions、46 个重复被试组；C2b 30 秒模型 AUC 约为 .642/.680/.629/.607/.643（M0–M4）。

## 6. 不纳入 Git 的内容

原始实验数据、视频、NPZ 大型集合、模型权重、缓存、虚拟环境、`.git`、认证/会话材料和大规模可再生图片不复制进本仓库。本说明只登记它们的结果用途、来源和限制。

## 7. 交接结论

1. 正式行为/上下文基线、69-session NIR 统计、NIR 增量比较和 J_Data 事件结果必须按各自 cohort 和版本分别引用。
2. 新队列重建、时间戳恢复和 PIR scientific fix 是审计/准备结果，不得冒充新正式模型。
3. 珠海实际 session linkage 仍阻塞；sub-099 时间轴仍缺失。
4. 所有结果都必须同时引用对应版本目录、输入 cohort、窗口、折叠方式和质量层。
