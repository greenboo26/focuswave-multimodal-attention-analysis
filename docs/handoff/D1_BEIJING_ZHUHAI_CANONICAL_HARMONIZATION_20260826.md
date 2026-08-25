# D1 北京—珠海 Canonical Harmonization 与共同协议验证

状态：`READY_TO_RUN`

日期：2026-08-26

## 目标

建立北京与珠海统一的自然人—session—模态质量主表，并在已确认共享的正式 B1/B2 协议上产生第一版跨站点纵向行为/探针结果。

本任务直接复用已冻结的协议裁决：

`docs/decisions/2026-08-26-beijing-zhuhai-protocol-identity-harmonization.md`

不再重新审计 FocusWave Git 历史。

## 已冻结事实

- 珠海正式实验从 2026-08-15 开始，正式协议为 BBB；
- 北京正式实验为同一协议的 BB 缩短版；
- 两地正式 B1/B2 使用同一四分类注意状态探针、警觉度探针和 probe schedule family；
- 1–9 分即时专注评分过渡版本从未用于正式被试；
- 珠海正式实验前约有 10 名左右预实验被试，预实验程序分支与正式实验明显不同；
- 北京和珠海常规每人最多安排 3 次正式实验只是采集管理原则；第 4 次及以后因模态质量重采形成的正式 session 可以保留；
- 正式 session 的保留由核心任务/probe/timeline 是否有效决定；各传感器是否进入某项分析由模态级 QC 决定；
- 同一自然人的全部 session 始终共享同一个 participant group。

## 输入优先级

优先复用已有权威资产：

1. `D:\Project\厚粲杯\11_数据\derived\analysis_tables_v2\subject_session_master_v2.csv`
2. `D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\deterministic_join.csv`
3. `D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1\`
4. `D:\Project\厚粲杯\11_数据\derived\zhuhai_session_linkage_nir_event_readiness_v1\`
5. 预约表、正式问卷答卷时间、实验采集目录时间、已有 participant/session 对照资产。

珠海问卷中的“是否参加过第一阶段/预实验”只作为 pilot/formal 身份辅助字段。北京残留该题的少量答卷直接忽略该字段。

## 阶段 A：统一 person/session crosswalk

为所有可确定的北京、珠海 session 建立一行一个 session 的 canonical master。

至少包含：

- `repeat_participant_id`
- `session_id`
- `site`
- `session_datetime`
- `phase` = pilot/formal
- `program_family`
- `formal_session_index`
- `collection_reason`
- `retake_of_session_id`（若可确定）
- `behavior_usable`
- `probe_usable`
- `mmwave_usable`
- `nir_usable`
- `rgb_usable`
- `include_in_shared_primary`
- `include_in_zhuhai_extended`
- `identity_evidence`
- `identity_confidence`

### session 保留逻辑

核心任务、probe 与时间线有效的正式 session 保留在 canonical master 中，包括第 4 次及以后正式重采。

模态质量按模态记录。例如：

- NIR 出视野：`nir_usable=0`，其他有效模态继续保留；
- mmWave 质量不足：`mmwave_usable=0`，行为/probe/NIR/RGB 仍可进入相应分析；
- 仅在核心实验结构本身无法恢复时设置 `include_in_shared_primary=0`。

`formal_session_index` 按真实正式采集顺序编号，可大于 3。

`collection_reason` 优先使用：

- `routine`
- `mmwave_retake`
- `nir_retake`
- `rgb_retake`
- `multimodal_retake`
- `other_retake`
- `unknown_formal_reason`

不确定原因保留为 unknown，并保留证据字段，不根据结果猜测。

## 阶段 B：建立两个 canonical probe master

### 1. shared_primary

范围：

`Beijing B1+B2 + Zhuhai B1+B2`

纳入所有 `phase=formal` 且核心任务/probe/timeline 有效的正式 session。

每条 probe 至少包含：

- `repeat_participant_id`
- `session_id`
- `site`
- `formal_session_index`
- `collection_reason`
- `block_num`
- `probe_index_within_block`
- `probe_response`
- `probe_vigilance`
- `probe_onset_unix_ms`
- `block_progress`
- `shared_protocol_progress`
- 行为窗口可用性
- mmWave/NIR/RGB 可用性

### 2. zhuhai_extended

范围：

`Zhuhai B3`

字段结构尽量与 shared_primary 相同，用于更长 time-on-task 扩展分析。

## 阶段 C：共同协议的第一版纵向验证

先做行为/probe，不等待传感器模型。

### C1. 描述性结果

分别报告北京、珠海：

- participant 数；
- formal session 数；
- B1/B2 probe 数；
- label 1/2/3/4 分布；
- vigilance 分布；
- 每人 session 数量分布，包括第 4 次及以后 session；
- 各模态 usable 覆盖率。

### C2. 主模型

核心 endpoint 沿用：

`label 1 = 完全任务聚焦`

`label 2/3/4 = other non-fully-task-focused states`

主模型回答：完全任务聚焦概率是否随任务进度下降，以及这一轨迹是否因站点而明显不同。

建议固定模型：

`label1_binary ~ progress + block + site + progress:site`

重复结构至少正确处理 `repeat_participant_id`；若 session 层随机截距稳定可识别，可使用 participant/session 层级模型。机器学习式切分在本阶段不是必须，但任何预测评估继续 participant-disjoint。

报告：

- progress 主效应；
- site 主效应；
- site × progress；
- effect size / OR 或 beta；
- 95% CI；
- participant-cluster 或 participant bootstrap 稳健结果。

site interaction 的目的只是判断两地轨迹是否明显异质，不以显著性作为是否允许 pooled 的唯一标准。

### C3. 行为效标复现

复用北京已经冻结的 pre-probe 行为定义，在珠海以及 pooled shared-primary 上检查：

- probe 前错误率；
- RT median；
- RT variability（数据可用时）。

重点验证北京已有发现“完全任务聚焦 probe 前错误率较低”能否在珠海方向复现，并在 pooled 模型中保持。

### C4. 珠海 B3 扩展

使用 `zhuhai_extended` 描述 B1→B2→B3 的完整 time-on-task 轨迹。

核心问题：北京 B1/B2 范围之外继续延长任务后，完全任务聚焦、警觉度和行为表现是继续变化、平台化还是出现恢复。

## 重复次数敏感性分析

主分析使用全部核心结构有效的正式 session。

完成主模型后，追加一次预先定义好的敏感性分析：

- A：全部有效 formal sessions；
- B：每个自然人仅保留最早 3 次有效 formal sessions。

比较核心 progress、site、site×progress 和行为效标结论是否实质改变。

这项敏感性分析用于评估 session 数量不均衡，不用于事后选择更好看的结果。

## 输出

本地至少生成：

- `beijing_zhuhai_person_session_crosswalk.csv`
- `beijing_zhuhai_modality_qc_manifest.csv`
- `beijing_zhuhai_shared_primary_probe_master.csv`
- `zhuhai_extended_b3_probe_master.csv`
- `shared_primary_descriptives.csv`
- `shared_primary_longitudinal_models.csv`
- `shared_primary_behavior_criterion_models.csv`
- `repeat_count_sensitivity.csv`
- `D1_BEIJING_ZHUHAI_CANONICAL_HARMONIZATION.md`
- 至少 2 张报告级候选图：跨站点 label1 trajectory；珠海 B1→B2→B3 trajectory。

GitHub 只提交脚本、聚合统计、图和裁决/报告；含 pseudonymous participant/session 行级 master 保留本地。

## 完成后的裁决状态

根据实际结果使用清晰状态，例如：

- `SHARED_PROTOCOL_POOLED_ANALYSIS_SUPPORTED`
- `SHARED_PROTOCOL_WITH_SITE_HETEROGENEITY`
- `IDENTITY_OR_SESSION_LINKAGE_BLOCKED`

无论结果如何，都保留北京与珠海属于同一正式 B1/B2 measurement protocol 的既有协议事实；统计异质性描述的是样本/站点表现，不反推程序协议不同。
