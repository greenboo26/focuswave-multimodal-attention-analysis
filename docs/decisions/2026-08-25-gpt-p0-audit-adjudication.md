# GPT 裁决：P0 审计后的三条下一步主线

日期：2026-08-25
依据：`docs/decisions/2026-08-25-p0-audit-gpt-handoff.md`
协作规则：`docs/protocols/GPT_CODEX_COLLABORATION_PROTOCOL.md`
状态：GPT METHOD / SCIENTIFIC ADJUDICATION

## 一、当前状态总览

### 可以作为正式审计事实使用

1. 近红外方向性实现审计通过：当前二元标签映射与 `predict_proba[:, 1]` 的概率列方向一致，低于 .50 的受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）不是单纯标签翻转或概率列取错造成。
2. 问卷测量审计可以作为正式的描述性 inventory：当前未确认可核验的正式多题量表，因此不能报告 Cronbach’s α、McDonald’s ω 或因子结构；单题只能作为 trait-like / state-like 单题候选。
3. 静息/休息与 RS6240 质量控制（quality control [QC]）汇总可以作为正式的“已审计范围内技术质量事实”，但其范围仅限已审计 session，且不等于心率、呼吸率或心率变异性测量准确性验证。

### 仅可作为探索性结果

1. 近红外成像（near-infrared [NIR]）-only AUC = .3497 / .3177：保留为真实的当前模型表现，但不得通过 `1 - AUC` 反转后当作新成绩；也不得据此称 NIR 无效。
2. RS6240 8 通道空间一致性、target-lock candidate、RGB motion gate：可作为探索性技术/QC 证据，不能升级为生理效度证据。

### 当前阻塞

1. 北京正式纵向行为事件分析：缺 participant/session 确定性身份和完整 session 级时间线语义。
2. 珠海正式三阶段结果分析：30 个登记 session 尚未与 raw behavior、master timeline 和模态目录建立确定连接。
3. 毫米波逐搏/心搏间期/心率变异性外部参考验证：正式 Radar–ECG 数据仍未取得。

### 尚未验证

1. 北京每个 session 的精确程序 patch 版本；
2. 珠海实际 probe 版本与 response mapping；
3. RS6240 host timestamp gap、range-bin 索引冲突、firmware calibration、Tx timing、memory mapping 对全量正式生理分析的影响；
4. 当前 3 个 RS6240 session 的 QC 是否能代表全部采集数据。

---

# 主线 1：解除北京纵向分析 blocker，并并行恢复珠海 session 级映射

这是当前最高优先级。

## 1.1 北京解除 `BLOCKED_PREFLIGHT` 的最小证据

正式行为事件分析不要求先恢复“精确 patch 版本号”，但要求每个纳入 session 通过以下**语义等价门槛（semantic equivalence gate）**：

1. `repeat_participant_id` 或等价真实 participant identity 可确定；
2. canonical `session_id` 可确定，且行为文件与 session 一对一映射可审计；
3. B1、强制休息、B2 的边界来自真实事件时间戳/程序事件，而不是由总时长猜测；
4. trial onset、probe onset、probe response 值可确定；
5. probe 文案与 response mapping 可以绑定到同一语义家族，至少证明当前纳入 session 的 response 数值含义相同；
6. 同一 session 内 behavior 与 timeline 的时钟关系可确定；
7. 缺失上述任一关键字段的 session 可以排除，但必须记录排除原因和剩余覆盖率。

### 关于程序版本的正式裁决

**精确 patch 号不是必要条件，语义一致性才是必要条件。**

若北京 session 均可证明属于 v3.1.0+ BB 家族，并且实际输出字段、probe 文案、response mapping、B1/休息/B2 结构一致，则可以进入北京第一轮纵向行为分析，即使无法恢复每个 session 的精确 patch 版本。

反之，如果只知道“文件名看起来像 BB”但不能证明 response 1/2/3/4 的实际语义，则不能进入正式标签分析。

当前 1 个缺失 timeline 的北京 session 若无法确定性恢复，可以在正式分析中排除，不需要为保留 100% session 而推测补齐。

## 1.2 北京解锁后立即运行

沿用已冻结方法：

- stage / time-on-task → 完全任务聚焦 vs 其他非完全任务聚焦状态；
- probe 前 10 / 20 / 30 s 的 error、reaction time、reaction-time variability 等行为轨迹；
- B1 末端 → 强制休息 → B2 起始的恢复样变化；
- participant/session 重复测量结构。

不得等待 NIR、雷达 HRV 或珠海全部完成后再启动北京行为主分析。

## 1.3 珠海如何处理

珠海三阶段程序目前只能作为**协议/方法证据**进入报告，不能作为正式数据结果。

Codex 应继续恢复：

`登记 session → raw behavior → master timeline → modality folders → participant/session identity`

只有 session 级映射完成后，珠海才能进入正式纵向结果分析。

### 北京与珠海能否合并

在程序版本不完全一致时，允许合并的只有经过语义核验后真正同构的变量，例如：

- 相同含义的 probe 标签；
- stage 内标准化 time-on-task；
- 同一定义的 reaction time / error 指标；
- 相同时间语义的 probe-preceding windows。

以下内容必须先分站点报告：

- 北京两阶段 B1/B2 与珠海三阶段的阶段主效应；
- 休息/恢复结构；
- 任何依赖具体程序版本或 probe 语义的结果。

若后续建立联合模型，必须至少显式加入 site/protocol，并检查 `site/protocol × time` 或 `site/protocol × state` 的差异；不得把北京和珠海直接堆叠成同一阶段序列。

---

# 主线 2：把 NIR 与问卷放回“构念/纵向解释”位置，不再追单模态分数

## 2.1 NIR 低 AUC 的裁决

NIR 方向性审计已经排除最明显的实现错误，因此 `.3497 / .3177` 应保留为当前正式运行得到的**探索性负向排序结果**。

允许的写法：

> 在当前严格共同样本、当前特征表示和低复杂度 participant-disjoint 模型下，NIR-only 对主二元终点呈低于机会排序方向的表现；方向性实现审计未发现标签或概率列翻转，因此该结果需要通过参与者内事件相关轨迹和时间结构进一步解释。

不允许：

- 写成“NIR 无效”；
- 把 `1 - AUC` 当作新的性能成绩；
- 因为结果低于 .50 就重新编码正负类；
- 根据该结果修改 NIR QC 阈值。

### 下一步 NIR 只做解释性事件分析

在 participant identity 和时间线可用后，优先检查：

1. participant 内中心化后的 pupil-related measure 在 probe 前的变化；
2. stage / time-on-task 是否驱动整体方向；
3. 8 名可计算 participant-level AUC 的参与者中，方向是否稳定或存在明显个体异质性；
4. 与 behavior trajectory 的同向、反向或互补关系。

在这些问题明确前，不把 NIR 当“多模态 upper bound”或 teacher signal。

## 2.2 问卷单题怎么进入正式分析

当前没有正式多题量表证据，因此不新增内部一致性分析。

建议只预先保留少量直接相关单题：

### Trait-like 单题

例如“自评专注能力”“平时可持续专注多久”。

用途：

- participant-level 外部校标：与个体平均完全任务聚焦比例关联；
- participant-level moderator：与 time-on-task 下降斜率或恢复幅度交互。

### State-like 单题

例如当次实验后的疲劳、困倦、走神、自觉注意维持/恢复。

用途：

- session-level context / external criterion；
- 与该 session 的平均状态、time-on-task slope、恢复幅度对应。

不能把事后单题直接当作某一个 probe 的即时 ground truth。

在北京/珠海问卷站点映射恢复前，只做 measurement manifest，不运行跨站点问卷模型。

---

# 主线 3：把 RS6240 技术可靠性写清楚，并先解决“数据链可信度门槛”再上正式生理解释

当前 RS6240 QC 可以进入报告，但只能写为**有限范围技术质量审计**。

## 3.1 当前可以写进报告的内容

在明确限定“已审计 session / 已审计时间段”的前提下，可以报告：

- 设备时间戳可用性；
- 数据覆盖范围；
- target-lock candidate；
- 多通道空间一致性候选；
- RGB motion gate；
- extraction success / failure reason。

这些回答的是：

> 当前输入数据是否具备继续分析的技术条件？

不回答：

> HR / BR / HRV 是否已经测准？

其中心率为心率（heart rate [HR]），呼吸率为呼吸率（breathing rate [BR]），心率变异性为心率变异性（heart rate variability [HRV]）。

## 3.2 在正式 radar physiology/event analysis 前必须优先解决的三个工程问题

1. **range-bin 索引冲突**：自动 range-bin 244–248 与 profile 主峰 8–13 的映射关系必须解释清楚，排除索引、memory layout、FFT/profile 定义不同导致的错误锁定；
2. **时间戳连续性**：host timestamp 严格缺口不能被当作连续 cardiac-band 时间轴，必须明确正式分析采用哪套 device clock / resampling / gap policy；
3. **firmware / calibration / Tx timing / memory mapping**：至少形成可复现配置清单，确认当前解析代码与实际固件输出语义匹配。

这三项没有解决前，不批准把当前 radar cardiac candidate 升级为正式生理事件轨迹。

## 3.3 外部 Radar–ECG 验证继续独立保持 blocked

正式外部 Radar–ECG 数据到位后，继续按已冻结链路验证：

`radar → beat timestamp → inter-beat interval (IBI) → HRV`

其中心搏间期为心搏间期（inter-beat interval [IBI]），心电图为心电图（electrocardiography [ECG]）。

外部数据验证的是算法在独立 Radar–ECG 数据上的逐搏/IBI 恢复能力，不能单独写成“本项目 RS6240 已完成 ECG 验证”。

---

# 下一轮最多三个 handoff 包

Codex 下一轮只需返回以下三个主包，不再扩展新支线：

1. `BEIJING_SEMANTIC_SESSION_GATE_AND_EVENT_V1`：先给 session semantic gate 覆盖结果；若通过，同一包继续给北京 behavior/probe/stage/time 正式纵向结果。
2. `ZHUHAI_SESSION_LINKAGE_AND_NIR_EVENT_READINESS_V1`：恢复珠海 session 级映射；同时只做 NIR event-ready / within-person trajectory readiness，不启动复杂模型。
3. `RS6240_DATA_CHAIN_TECHNICAL_GATE_V1`：专门解决 range-bin、device/host timing、firmware/calibration/Tx/memory mapping，并形成报告级 QC 边界。

问卷 measurement manifest 作为主线 1 或 2 的轻量附属产物更新，不单独占第四条主线。

## 暂不批准

- teacher–student；
- 大型深度模型；
- 根据当前 AUC 调标签或 QC 阈值；
- 珠海未完成 session 链接前进行正式结果模型；
- 将 NIR 低 AUC 反转后作为性能；
- 将当前 3-session RS6240 QC 外推为全数据集生理效度；
- 在 radar 数据链技术门槛未解决前宣称 HR / BR / HRV 准确。
