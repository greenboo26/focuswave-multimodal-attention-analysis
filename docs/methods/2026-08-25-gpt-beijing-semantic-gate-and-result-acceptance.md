# 北京纵向事件分析：Semantic Gate 与结果验收标准

日期：2026-08-25
角色：GPT 研究/方法负责人
状态：METHOD FROZEN

## 1. 目的

本文件把北京纵向事件分析从“需要精确程序 patch 版本”改为“需要可审计的语义等价证据”。目标是避免为了追求无法恢复的精确版本号长期阻塞正式分析，同时保持 participant/session 身份、事件时间线和 probe 语义这三项不可放宽的科研边界。

## 2. Semantic Gate：正式分析的最小通过条件

一个北京 session 可以进入正式 longitudinal/event-related analysis，当且仅当以下五项均能通过确定性证据恢复。

### G1. Participant identity

必须能把 session 绑定到唯一、可追溯的 `repeat_participant_id` 或等价匿名参与者键。允许使用登记表、既有 crosswalk、文件元数据和项目 master 中的确定性映射；不允许使用行为相似性、传感器特征、模型相似性或时间模式猜身份。

若同一真实参与者存在多次 session，所有 session 必须保留同一 participant identity，用于重复测量建模和 participant-disjoint split。

### G2. Canonical session identity

必须建立唯一 `canonical_session_id`，并能说明它由哪些原始文件/目录组成。session 边界不能由模型推断，也不能因为文件名相近直接合并。

### G3. Stage 与事件时间线

必须确定性恢复：

- B1 起止；
- 强制休息起止；
- B2 起止；
- trial onset / response time；
- probe onset；
- probe response 时间或至少 probe window 的真实事件边界。

时间线优先使用程序事件日志或明确的绝对时间戳。缺少时间线的 session 不用文件总时长猜补，可排除并记录为 `timeline_unresolved`。

### G4. Probe 文案与 response mapping 语义等价

不要求每个 session 找到精确 patch 版本号，但必须有足够证据证明进入同一分析池的 session 在以下语义上等价：

1. probe 问题测量的是同一即时注意构念；
2. `1/2/3/4` 的回答含义一致；
3. `probe_response` 与其他同时存在的字段（如 vigilance）没有被错读或交换；
4. 北京两阶段结构一致，probe 数和字段语义没有发生会改变主终点解释的版本迁移。

当前主终点仍为 `label 1` 与 `label 2/3/4` 的区分，科学名称固定为“完全任务聚焦 vs 其他非完全任务聚焦状态”。不得简称为“专注 vs 走神”。

### G5. Behavior 字段语义一致

至少要确认正式分析使用的 trial-level 字段在纳入 session 中含义一致，包括：

- correctness / error；
- reaction time；
- omission / commission（若程序定义支持）；
- trial index / stage index；
- probe 关联键。

如果某个字段跨版本定义发生变化，只能对该字段建立版本特异性分析，不得用同名字段自动合并。

## 3. 通过、部分通过与阻塞

### `PASS_FORMAL`

G1–G5 全部通过。该 session 可进入北京正式行为事件分析、广义线性混合效应模型（generalized linear mixed-effects model [GLMM]）或等价重复测量分析。

### `PASS_LIMITED`

participant/session/time/probe 语义均确定，但某个次级行为字段不可统一。该 session 可进入不依赖该字段的主分析，缺失字段按预定义 missingness 规则处理。

### `BLOCKED`

出现以下任一情况：participant identity 未解析、session 边界不清、B1/休息/B2 无法确定、probe 1–4 语义无法确认、行为字段含义冲突且无法版本分层。

阻塞 session 不进入正式模型。允许做数据量与缺失描述，不得与正式样本混合后再解释效应。

## 4. 北京正式结果的验收顺序

通过 Semantic Gate 后，正式结果按以下顺序验收。

### A. 样本与时间线验收

必须先报告：纳入参与者数、session 数、probe 数、trial 数、各标签数量、缺失/排除原因、单个参与者的 probe 覆盖范围。随后才看显著性结果。

### B. 主问题 1：Stage × time-on-task

主结果变量：完全任务聚焦 vs 其他非完全任务聚焦状态。

主预测结构：`stage + stage 内 time-on-task + stage × time-on-task`。

允许解释：完全任务聚焦概率随任务推进变化；B1 与 B2 的时间轨迹不同。

不允许直接解释：疲劳导致下降。只有存在独立疲劳测量且时间顺序、模型与替代解释均支持时，才可以把疲劳作为解释之一。

### C. 主问题 2：Probe 前 10/20/30 s 行为

三个窗口是一个预定义 scientific family。必须全部交回，不能只保留效应最大或 *p* 值最低的窗口。

优先报告：效应方向、估计值、95% 置信区间（confidence interval [CI]）、经预定义校正的 *p* 值、样本覆盖。

若 10、20、30 s 的方向一致，可描述为跨窗口稳定；若只在一个窗口出现，先描述为时间尺度特异性结果，不把它升级成普遍规律。

### D. 主问题 3：休息后恢复

核心比较为 B1 末端与 B2 起始。若 B2 起始的完全任务聚焦概率、错误或反应时稳定性相对 B1 末端改善，可称为“强制休息后伴随的恢复样变化”。

不得称为“休息导致恢复”，因为当前设计没有无休息对照来单独识别休息的因果效应。

## 5. 统计红线

- 同一参与者的 probe/trial 不能作为独立个体；
- participant 必须进入随机效应或等价重复测量结构；
- 若同一 participant 有多个 session，应在数据可识别时处理 session 嵌套或 session 随机效应；
- 不根据结果临时修改窗口、标签或排除阈值；
- 多重比较按冻结的 scientific family 校正；
- 统计符号和数字按第 7 版《美国心理学会出版手册》（Publication Manual of the American Psychological Association, 7th ed. [APA 7]）报告，例如 *p* < .001，而不是 *p* = .000。

## 6. Codex 下一次 handoff 的最小证据

`BEIJING_SEMANTIC_SESSION_GATE_AND_EVENT_V1` 至少返回：

1. 每个 session 的 G1–G5 gate 状态汇总；
2. `PASS_FORMAL / PASS_LIMITED / BLOCKED` 的数量和原因；
3. participant/session/stage/probe 的聚合样本规模；
4. 正式主模型公式和随机效应结构；
5. 10/20/30 s 全部行为窗口；
6. B1 late → B2 early 恢复比较；
7. 收敛、缺失、多重比较和排除状态；
8. 报告级图，而不是只交系数表。

## 7. 当前裁决

精确 patch 版本号不再作为单独硬 blocker。真正的硬门槛是：**身份可追溯、session 可识别、事件时间线真实、probe/response 语义等价、正式行为字段语义一致。**
