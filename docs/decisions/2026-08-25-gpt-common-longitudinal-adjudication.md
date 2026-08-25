# GPT 裁决：严格共同样本基线与纵向事件相关分析启动顺序

日期：2026-08-25
依据：`docs/decisions/2026-08-25-common-subset-and-longitudinal-handoff.md`

## 总裁决

本轮 handoff 通过，但做两项方法学修正。

第一，`COMMON_SUBSET_BASELINE_V1` 可以作为当前严格共同样本上的**多模态最小基线（common-subset multimodal minimum benchmark）**，但暂不称为“multimodal upper-bound”。原因是当前融合模型并未形成性能上界：Primary 集合中 time/block structural baseline 的受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）为 .680，而 behavior + radar + 近红外（near-infrared [NIR]）融合为 .641；Sensitivity 集合分别为 .663 与 .621。该结果只说明当前低复杂度模型在严格共同样本上的起点，不代表多模态潜在上限。

第二，批准纵向事件相关分析进入执行准备，但不要求“珠海全部核验完以后北京才能开始”。北京与珠海应拆成两个可独立验收的时间线工作包；只要北京自身的 participant/session/stage/probe/behavior 时间语义和 probe 程序版本已经确定，就可以先运行北京行为与时间结构的事件相关主分析。珠海三阶段继续独立完成字段与时间线核验后再进入珠海正式分析。

## 1. 共同样本基线的解释边界

接受以下事实作为当前正式最小基线：

- Primary 集合：213 条 probe，12 名参与者，14 个 canonical sessions；
- Sensitivity 集合：221 条 probe，12 名参与者，14 个 canonical sessions；
- 所有模态使用相同 probe 行、相同 participant-disjoint folds；
- subject `070` 已排除；
- 4 名参与者只有单一二元类别，因此 participant-level AUC 只在 8 名可定义参与者中计算；
- 当前 time/block structural baseline 高于 radar-only、NIR-only 和当前融合模型。

因此本轮可写：

> 在严格共同样本和相同参与者独立分折下，当前低复杂度 radar、NIR 及融合模型尚未稳定超过任务时间/区组结构基线。

不得写：

- “NIR 无效”；
- “毫米波不能预测注意状态”；
- “多模态没有价值”；
- “当前融合模型代表多模态性能上限”。

当前共同样本过小，且标签分布、单类参与者和时间结构都限制了模态结论的外推。

### NIR-only AUC 低于 .50 的专项审计

Primary 与 Sensitivity 集合中的 NIR-only AUC 分别为 .350 和 .318。该现象在科学解释前必须先进行方向性审计，但不得直接把 AUC 人工反转为 `.650` 或 `.682` 后当作性能结果。

Codex 应核验：

- 二元正类在全部折中是否始终指向同一标签；
- `predict_proba` / decision score 是否始终取相同正类列；
- 每折类别顺序是否一致；
- 标签编码与 common-subset merge 后是否发生反向映射；
- 低于 .50 是否由少数参与者的方向反转或明显分布漂移驱动。

如果实现与标签方向完全正确，则保留原 AUC，并把“系统性反向排序”作为需要进一步解释的结果，而不是自动视为可反转的预测能力。

## 2. 标签终点

继续保持 `label 1 vs label 2/3/4` 作为当前主终点，直到历史 session 的程序版本、probe 文案和 response mapping 一致性核验完成。

科学名称继续使用“完全任务聚焦 vs 其他非完全任务聚焦状态”，不得简称为“专注 vs 走神”。历史版本核验应视为正式纵向分析开始前的必需门控，而不是附带检查。

## 3. 纵向分析拆分后的启动顺序

### Track A：北京可先启动的主分析

前提：北京 session 的 participant identity、canonical session、B1/休息/B2 边界、probe onset、trial time、behavior 字段和 probe 版本均可确定性恢复。

满足前提后，不必等待珠海或完整 NIR，即可先运行：

1. `probe-locked behavior trajectories`：probe 前 10/20/30 s 的 error、reaction time、reaction-time variability、omission/commission 等预定义行为指标；
2. `stage × time-on-task`：B1 与 B2、block progression、probe sequence 对任务聚焦状态的影响；
3. `break/recovery`：比较 B1 末端、休息后和 B2 起始的行为/状态变化，但休息本身不自动视为闭眼或静息基线；
4. participant/session 重复测量模型。

第一轮建议优先只做 behavior + probe + stage/time，因为这部分数据最完整、理论解释最清楚，也能直接建立 thought probe 的构念有效性证据。

### Track B：珠海三阶段核验

珠海必须独立核验：

- 三阶段真实程序结构与阶段边界；
- probe/response mapping；
- behavior 字段和绝对时间；
- radar/NIR/RGB 等模态覆盖；
- 缺失场次与异常时长；
- 与 participant/session master 的确定性映射。

不得用北京两阶段语义或文件总时长推算珠海阶段边界。

核验完成后，珠海可以独立运行同构的事件相关分析，再判断北京与珠海哪些参数可以合并、哪些必须保留 site/protocol interaction。

### Track C：雷达与 NIR 的事件相关扩展

不阻塞 Track A，但需等各自时间窗与质量控制（quality control [QC]）字段验收后加入。

顺序建议：

1. behavior-only event-related；
2. radar event-related；
3. NIR event-related；
4. common-probe multimodal triangulation。

不得为了模态一致性而改变已经冻结的 probe 窗口或行为窗口。

## 4. 当前最重要的科学问题

下一阶段不以“把 AUC 做高”为首要目标，而先回答：

1. 完全任务聚焦状态是否随 time-on-task 和阶段系统变化？
2. probe 前行为错误和反应时波动在多少秒前开始分化？
3. 强制休息是否伴随第二阶段起始时的状态/行为恢复？
4. 这些效应在控制 participant/session 重复测量后是否仍存在？
5. radar 与 NIR 后续加入后，是否与这些行为/时间轨迹形成一致或互补信息？

这些结果将决定 radar-only predictive model v2 应学习哪些时间尺度和动态特征，而不是先更换复杂分类器。

## 5. 下一轮 Codex 任务拆分

批准以下并行任务：

### P0-1 北京纵向事件相关分析 v1

先运行 behavior + probe + stage/time，不等待珠海、NIR 或 HRV。

建议 RUN_ID：`BEIJING_LONGITUDINAL_EVENT_V1_20260825`

### P0-2 珠海三阶段时间线与字段核验

只做 deterministic timeline/schema audit，不先跑正式结果。

建议 RUN_ID：`ZHUHAI_THREE_STAGE_TIMELINE_AUDIT_V1_20260825`

### P0-3 历史 probe 程序版本一致性核验

覆盖北京与珠海历史 sessions，确认文案、response mapping 和程序版本；若存在版本差异，先形成版本—session manifest，不自行重编码标签。

建议 RUN_ID：`PROBE_PROGRAM_VERSION_AUDIT_V1_20260825`

### P0-4 NIR 方向性审计

只核验标签方向、正类概率列、每折类别顺序、merge 后标签映射和 participant-level 方向，不调模型、不改特征、不反转 AUC 作为新成绩。

建议 RUN_ID：`NIR_DIRECTIONALITY_AUDIT_V1_20260825`

### P1-5 Radar/NIR 事件特征 readiness

只检查预定义 10/20/30 s 或设计文档指定窗口能否稳定生成，不先做大规模模型选择。

## 6. 暂不批准

- teacher–student；
- 大型深度模型；
- 根据共同样本结果调整 NIR QC 阈值；
- 根据结果修改标签定义；
- 将当前 common-subset 结果包装为多模态 upper-bound；
- 把北京与珠海直接合并成同一阶段模型而不检查 protocol/site 差异。

## 下一次 handoff

优先返回四个独立证据包：

1. 北京 behavior/probe/stage/time 正式事件相关结果；
2. 珠海三阶段 timeline/schema audit；
3. 历史 probe 程序版本一致性 manifest；
4. NIR AUC < .50 的方向性审计。

随后再由 GPT/用户裁决是否把 radar/NIR 正式加入 longitudinal event analysis，以及是否建立北京—珠海联合模型。
