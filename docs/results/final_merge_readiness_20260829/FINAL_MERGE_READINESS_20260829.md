# FINAL MERGE READINESS 20260829

状态：`READY_FOR_MORNING_ENTRY_PACKAGE / PARTIAL_MULTIMODAL`

## Canonical anchor

- Beijing valid sessions: **70**；participants: **46**；probes: **1,400**。
- `behavior/probe` 是唯一 canonical anchor；传感器缺失不改变 70/46/1,400 主分母。
- 主行为 baseline：30 s primary，10/20 s sensitivity；L2 logistic、participant-disjoint 5-fold StratifiedGroupKFold、`repeat_participant_id` 分组。
- 已有 30 s baseline：`B_behavior_only` ROC-AUC 0.639；`C_plus_B` ROC-AUC 0.675。

## Current availability boundary

- mmWave：70 场入口存在；现有 formal QC v1 只提供 **preliminary screening flags**，其中 **1,297/1,400 probes** 被既有字段标记为通过初筛。该比例不是生命体征、HR/RR、HRV 或 ECG/RSP 对照通过率。099 仍是 supplemental，067 不在 canonical 70 场。
- mmWave use-tier 全部标记为 `preliminary_screening_only`。原先的“17 场生命体征可用 / 53 场只能体动 / 2 场不可用”已撤销；17/53/2 仅保留为 preliminary QC flag distribution，不构成生理可用性分层。
- 该分布仅可写成：17 场达到既有 QC candidate gate、53 场带有 B/C preliminary flag、2 场带有 A/linkage 阻断 flag；三者都不是 HR/RR/HRV use-tier。
- B=44 仅表示 distance/target-lock preliminary flag：36 场 `distance_implausible`，8 场 `phase_stability_ge_090=False`；不得扩写为完整 radar geometry/motion failure。C=9 仅表示 window/probe quality preliminary flag；不得扩写为 HR/RR algorithm failure。
- formal scanner 未统一应用 producer 默认的 **0.30–1.50 m** gate；target-lock audit 采用 **0.20–1.00 m** preliminary gate。因此 `distance_implausible` 必须二次复核，不能直接作为人体胸腔定位失败或生命体征失败。
- formal 70 场没有逐 session ECG/RSP 对照指标，不能判断 RR pass/HR fail，不能判断 HRV 可用，也不能把毫米波作为 validated vital-sign predictor。
- RGB：canonical 70 场均有当前工程 manifest；状态是 engineering-complete，不能写成已完成正式增量推断，也不能写成“虹膜校正”。
- NIR：fullclass completion 69 场，与 canonical 70 场交集为 **68 场**；仅用于 E 层已 completion subjects，不等待 NIR 全队列。

## 明早推荐分析计划

### A. 主分析：behavior/probe baseline

固定 70/46/1,400。复用 canonical baseline 与 probe-before behavior validity；保留 label 1 对 labels 2/3/4 的预定义，不把 2/3/4 解释为同一种心理状态。

### B. 增量分析：behavior + RGB

使用与 A 相同的 probe、participant grouping、fold 与窗口。先过 RGB identity、时间戳、probe coverage 与 QC manifest gate；结果只能称 RGB increment，禁止表述为虹膜校正。gate 未闭合时仅保留为 available input / pending formal inference。

### C. 增量分析：behavior + mmWave exploratory feature increment

mmWave 只作为 `preliminary_screening_only` 的 exploratory feature increment。可报告 1,297/1,400 的 preliminary screening flag missingness，但不得把 `mmwave_qc_class` 或任何 `usable` 字段解释为 HR/RR/HRV 可用性，不得把毫米波作为 validated vital-sign predictor。

### D. 辅助分析：quality-flag sensitivity and covariates

固定 A 的分组与 folds，将 mmWave 初筛 flag、distance/target-lock preliminary flag、window/probe quality flag 作为 sensitivity-analysis strata 或协变量。若与 RGB 联合，只能称 exploratory multimodal increment；不得提升为 validated physiological modality。

### E. NIR 子样本验证

只取与 canonical cohort 相交的 68 个已 completion sessions；先做 exact subject/block/probe/onset alignment 与 Probe-window coverage QC，再做 paired/subsample validation。不得为凑齐队列等待或补跑。

### F. 不做或暂缓

- 不等待 NIR 全队列，不启动新的 NIR 全量推理。
- 不把 mmWave preliminary flags 写成生命体征可用性；不把 1,400 作为 mmWave validated-vital denominator。
- 不做 validated HR/RR/HRV 主分析：formal 70 场没有逐 session ECG/RSP 对照，不能判断 RR pass/HR fail，也不能判断 HRV 可用。
- 明早 mmWave 只进入 exploratory mmWave feature increment、quality-flag sensitivity analysis，以及 motion/target-lock/window-quality covariates。
- 不把 RGB 写成虹膜校正；RGB formal analysis authorization 仍需 gate。
- 不扩展到 global Beijing+Zhuhai inference，也不改写 099 supplemental 或 067 blocked 边界。

## Source and verification notes

- Anchor：`docs/results/final_report_cohort_baseline_v2/`、`docs/results/preprobe_behavior_validity/`。
- mmWave：`issue15_Mainline_D_formal_physiology_report.md` 与 canonical `m1_q0_probe_matrix.csv`。
- NIR：`nir_69session_final_probe_analysis_v1/qc_attrition_chain.csv`、`nir_session_qc_summary.csv`。
- RGB：`cohort_manifest.json`、`cohort_status.csv`。
- Central governance checkout 在本次构建时未能于可见 `D:\Project` 树中解析；这是验证限制，不是替代 authority。

## Output files

- `merge_session_availability_matrix.csv`
- `merge_probe_level_availability_matrix.csv`
- `available_model_sets.csv`
- `missingness_by_modality.csv`
- `recommended_analysis_plan_for_morning.md`


