# 比赛报告草稿：信度、效度与系统验证

日期：2026-08-25
状态：REPORT DRAFT / 已同步 P0 审计，待正式纵向与外部 benchmark 结果回填

> 本稿只保留三条主证据链，避免为了“信效度”堆叠大量零散指标。英文缩写首次出现按第 7 版《美国心理学会出版手册》（Publication Manual of the American Psychological Association, 7th ed. [APA 7]）规范介绍。

## 建议章节标题

### X.X 测量信度、效度与系统验证

本研究同时包含即时主观状态、任务行为和非接触式传感信号，因此未将传统心理量表的单一信度系数机械套用于全部数据，而是围绕三个核心问题建立证据：**即时任务聚焦状态是否具有构念依据、毫米波测量与算法是否具有足够技术可信度、识别结果能否在未见参与者上泛化并提供时间/行为之外的增量信息。**

### X.X.1 即时任务聚焦状态的构念有效性

本研究采用 thought probe 对实验过程中的即时注意状态进行采样。探针包含四类回答：完全专注于分拣任务、关注实验但未聚焦分拣任务、实验无关思维，以及思维空白。基于当前程序资产和标签审计，主分析将“完全任务聚焦”与“其他非完全任务聚焦状态”进行区分，而不将后三类统一解释为“走神”。

由于 thought probe 旨在捕捉随时间变化的瞬时状态，其前后不一致可能反映真实状态变化，因此本研究不以 Cronbach’s α 或普通重测相关作为核心信度指标，而通过探针状态与理论相关行为及任务时间进程之间的关系建立构念有效性证据。既有研究表明，task disengagement 或 mind-wandering 报告前可出现反应时变异和持续注意表现变化，因此本项目预先定义 probe 前 10、20 和 30 s 行为窗口，并显式建模 stage 与 time-on-task。

当前北京正式事件相关分析尚处于 `BLOCKED_PREFLIGHT`：72 个行为候选 session 中 71 个具有时间线事件，但 participant/session canonical identity 尚未全部确定性恢复。后续不再要求每个 session 找到精确程序 patch 号；正式分析的硬门槛改为 participant identity、canonical session、B1/休息/B2 事件边界、probe 1–4 response mapping 语义及行为字段语义均可审计。通过该 Semantic Gate 后，正式回填 stage × time-on-task、probe 前行为轨迹和休息后恢复样变化。

问卷审计目前未发现可核验的正式多题量表、反向计分规则或既定内部一致性结构。因此当前不报告未经支持的 Cronbach’s α 或 McDonald’s ω。“平时专注力如何”“通常可持续专注多久”等可作为 participant-level trait-like 单题指标；当次疲劳、困倦、走神或恢复等可作为 state-like 单题候选，但必须先解决北京/珠海问卷与 session 的确定性映射。单题只作为外部校标或 moderator，不称为量表。

### X.X.2 毫米波测量与算法可靠性

本研究首先从数据可用性和信号质量层面评价毫米波测量可靠性，包括时间覆盖、目标距离候选、多通道空间一致性和运动伪影控制。这些质量控制（quality control [QC]）证据用于判断 RS6240 数据是否具备后续分析条件，不直接等同于心率、呼吸率或心率变异性准确性。

RS6240 为 60 GHz、2 发射通道 × 4 接收通道（2T4R）的调频连续波（frequency-modulated continuous-wave [FMCW]）雷达。厂商资料支持微动、呼吸/心跳等应用场景，但当前项目 QC 仅覆盖有限 session，而且已发现需要优先解决的数据链问题：自动 range-bin 约 244–248 与另一 profile 主峰约 8–13 的坐标/处理阶段关系尚未解释，device timestamp 与 host timestamp 的用途和缺口语义尚未完全恢复，firmware calibration、Tx timing、message/memory mapping 与 parser provenance 也尚未全部核验。因此现有 target-lock、多通道一致性和 RGB motion gate 只能作为技术 QC，不作为心率（heart rate [HR]）、呼吸率（breathing rate [BR]）或心率变异性（heart rate variability [HRV]）准确性验证。

后续只有在 `RS6240_DATA_CHAIN_TECHNICAL_GATE_V1` 通过物理 range mapping、连续与绝对时间轴、2T4R Tx/Rx/channel 时序、firmware/parser provenance 和已知距离 sanity check 后，才恢复正式 radar physiology/event analysis。

对于拟解释为 HRV 的指标，仍保持更严格的分析验证链：

`radar → beat timestamps → 心搏间期（inter-beat interval [IBI]）→ HRV`

仅通过频谱峰获得平均心率候选不足以支持 HRV 结论。独立公开 Radar–ECG 数据集将用于算法外部基准验证，其中心电图（electrocardiography [ECG]）作为逐搏参考。该外部 benchmark 能证明算法在独立 Radar–ECG 数据上的逐搏/IBI 恢复能力，但因硬件和采集情境不同，不能单独写成“本项目 RS6240 HRV 已完成 ECG 外部验证”。当前正式 benchmark 仍受数据访问阻塞，VitalSense 示例 smoke test 不作为正式性能结果。

### X.X.3 系统泛化稳定性与增量有效性

最终识别系统采用参与者独立的数据划分，避免同一真实参与者的不同 session 或 probe 同时进入训练集和测试集。模型性能使用受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）、balanced accuracy、coverage 和 95% 置信区间（confidence interval [CI]）等指标报告；参与者测试集中只有单一类别时，其 participant-level AUC 记为不可定义，不以 .50 填补。

严格共同样本的多模态最小基线已经在相同 probe 行和相同 participant-disjoint folds 下完成。近红外（near-infrared [NIR]）QC 覆盖率 ≥80% 的主集合包含 213 条 probe、12 名参与者和 14 个 canonical sessions；NIR QC ≥50% 的敏感性集合包含 221 条 probe。当前低复杂度模型中，time/block structural baseline 的 AUC 分别为 .680 和 .663；radar-only 分别为 .582 和 .591；behavior + radar + NIR 分别为 .641 和 .621。由于样本量较小、4 名参与者仅包含单一二元类别，且当前融合模型并未构成多模态性能上限，因此这组结果仅作为严格共同样本的**多模态最小基线**。

NIR-only 的 AUC 为 .3497 和 .3177。方向性审计已经排除标签反转或 `predict_proba` 概率列选择错误；8 个可评估参与者中有 5 个呈反向排序。因此该结果当前仅作为探索性现象保留，不写成“NIR 无效”，也不通过 `1 - AUC` 改写为新的成绩。后续 NIR 分析优先转向 participant-within trajectory、stage/time-on-task、tonic 与 phasic 时间尺度以及四类 probe 状态的描述性异质性，再决定是否重新构造预测特征。

系统效度的重点不是某个单模态 AUC 是否高于 .50，而是它在显式考虑 time/block 和行为之后是否提供稳定的增量信息。正式报告优先比较：

`time/block → behavior → behavior + radar → behavior + radar + NIR`

并在完全相同的测试参与者上报告配对性能差值及 participant-level bootstrap 95% CI。后续 radar-only v2 仅在事件相关分析明确时间尺度和动态特征后启动，避免先通过复杂模型寻找高分结果再倒推心理机制。

## 建议正文总结句

> 综上，本研究针对不同测量层级建立与其科学声称相匹配的验证证据：thought probe 通过行为与任务进程关系建立构念有效性；毫米波通过数据链技术 Gate、质量控制及独立 Radar–ECG 逐搏基准建立测量与算法可信度；最终识别系统通过参与者独立验证和相对于时间/行为基线的增量比较评估泛化稳定性与应用价值。当前尚未通过的数据链或外部参考验证均明确标记为 blocked 或 unverified，不以探索性质量指标替代正式生理效度证据。

## 正文必须保留 / 可移至附录

正文只保留：

1. probe 构念有效性的 1–2 个核心行为/时间结果；
2. RS6240 数据链 Gate 与 QC 的 3–5 个核心状态；
3. 外部 Radar–ECG benchmark 的 4–6 个核心指标（正式数据取得后）；
4. participant-independent AUC、balanced accuracy、95% CI 和增量比较；
5. NIR 低 AUC 的一句方法边界，不在正文展开完整审计。

附录可放：完整 QC 字段、10/20/30 s 全窗口结果、paired bootstrap、逐搏容差敏感性、NIR within/between-person 审计、非主问卷关联和 exploratory 模态比较。

## 当前待回填清单

- `[BEIJING_SEMANTIC_SESSION_GATE_AND_EVENT_V1]` 北京正式 longitudinal/event-related 结果；
- `[ZHUHAI_SESSION_LINKAGE...]` 珠海实际 session 级三阶段映射；
- `[QUESTIONNAIRE_SESSION_LINKAGE]` 单题问卷与 participant/session 的确定性映射；
- `[RS6240_DATA_CHAIN_TECHNICAL_GATE_V1]` range/time/channel/parser gate；
- `[C1b]` 正式独立 Radar–ECG benchmark；
- `[NIR_EVENT_READINESS_V1]` NIR participant-within/time-on-task 轨迹。

## 参考文献

Jubera-García, E., Gevers, W., & Van Opstal, F. (2020). Influence of content and intensity of thought on behavioral and pupil changes during active mind-wandering, off-focus, and on-task states. *Attention, Perception, & Psychophysics, 82*(3), 1125–1135. https://doi.org/10.3758/s13414-019-01865-7

Kane, M. J., Smeekens, B. A., Meier, M. E., Welhaf, M. S., & Phillips, N. E. (2021). Testing the construct validity of competing measurement approaches to probed mind-wandering reports. *Behavior Research Methods, 53*(6), 2372–2411. https://doi.org/10.3758/s13428-021-01557-x

Pelagatti, C., Blini, E., & Vannucci, M. (2025). Catching mind wandering with pupillometry: Conceptual and methodological challenges. *WIREs Cognitive Science, 16*(1), e1695. https://doi.org/10.1002/wcs.1695

Seli, P., Cheyne, J. A., & Smilek, D. (2013). Wandering minds and wavering rhythms: Linking mind wandering and behavioral variability. *Journal of Experimental Psychology: Human Perception and Performance, 39*(1), 1–5. https://doi.org/10.1037/a0030954
