# 比赛报告草稿：信度、效度与系统验证

日期：2026-08-25
状态：REPORT DRAFT / 待 Codex 正式结果回填

> 本稿只保留三条主证据链，避免为了“信效度”堆叠大量零散指标。所有英文缩写首次出现均按第 7 版《美国心理学会出版手册》（Publication Manual of the American Psychological Association, 7th ed. [APA 7]）要求介绍。

## 建议章节标题

### X.X 测量信度、效度与系统验证

本研究的测量体系同时包含即时主观状态、任务行为和非接触式传感信号，因此未将传统心理量表的单一信度系数机械套用于全部数据，而是围绕“状态标签是否具有构念依据—传感测量是否可靠—识别结果能否泛化并提供增量信息”建立三层证据链。

### X.X.1 即时任务聚焦状态的构念有效性

本研究采用 thought probe 对实验过程中的即时注意状态进行采样。探针包含四类回答：完全专注于分拣任务、关注实验但未聚焦分拣任务、实验无关思维，以及思维空白。基于当前程序资产和标签审计，主分析将“完全任务聚焦”与“其他非完全任务聚焦状态”进行区分，而不将后三类统一解释为“走神”。

由于 thought probe 旨在捕捉随时间变化的瞬时状态，其前后不一致可能反映真实状态变化，因此本研究不以 Cronbach’s α 或普通重测相关作为核心信度指标。相反，构念有效性主要通过探针状态与理论相关行为和任务进程之间的关系建立。既有研究表明，走神或任务脱离报告前常伴随反应时变异增加和持续注意表现下降，并且 thought-probe 报告可通过与任务表现、跨任务稳定性和 trait 指标的关系获得构念效度证据（Kane et al., 2021; Seli et al., 2013）。

本项目将预先定义 probe 前 10、20 和 30 s 行为窗口，检验 error、reaction time 及 reaction-time variability 等指标是否在完全任务聚焦与其他状态之间出现一致差异，同时显式建模 stage 和 time-on-task。北京两阶段数据还将比较 B1 末端与强制休息后 B2 起始的状态和行为变化。正式结果需回填：`[BEIJING_LONGITUDINAL_EVENT_V1 结果]`。

若问卷审计确认存在与持续注意直接相关的正式多题量表，则报告其内部一致性；单题“平时专注力如何”或“通常可持续专注多久”等仅作为 participant-level trait 指标或外部校标，不计算 Cronbach’s α。正式问卷证据待 `QUESTIONNAIRE_MEASUREMENT_AUDIT_V1` 后回填。

### X.X.2 毫米波测量与算法可靠性

本研究首先从数据可用性和信号质量层面评价毫米波测量可靠性，包括时间戳/同步完整性、有效覆盖率、目标距离稳定性、多通道空间一致性和运动伪影控制。这些指标用于证明 RS6240 数据满足后续分析条件，不直接等同于心理构念效度。现有 target-lock 和多通道质量控制结果将由 `RS6240_REPORT_QC_SUMMARY_V1` 汇总后回填。

对于仅作为预测输入的原始相位、微动、呼吸候选和质量描述符，本研究不逐一赋予强生理含义。对于拟解释为心率变异性（heart rate variability [HRV]）的指标，则采用更严格的分析验证链：毫米波信号先定位逐搏事件，再形成心搏间期（inter-beat interval [IBI]），最后计算 HRV。仅通过频谱峰获得平均心率候选不足以支持 HRV 结论。

独立公开 Radar–ECG 数据集将用于算法外部基准验证，其中心电图（electrocardiography [ECG]）作为逐搏参考。正式报告将优先呈现 beat matching、IBI error、heart-rate error、HRV error 和有效 coverage 等少量核心指标。该外部数据集能够证明算法在独立 Radar–ECG 数据上的逐搏/IBI 恢复能力，但由于硬件和采集情境与本项目 RS6240 不完全相同，不能单独写成“RS6240 HRV 已完成 ECG 外部验证”。当前正式 benchmark 仍受数据访问阻塞，因此在完成前只报告验证协议已经建立，不报告 VitalSense 示例 smoke test 为正式性能结果。

正式结果需回填：`[C1b external Radar–ECG benchmark]`。

### X.X.3 系统泛化稳定性与增量有效性

最终识别系统采用参与者独立的数据划分，避免同一真实参与者的不同 session 或 probe 同时进入训练集和测试集。模型性能使用受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）、balanced accuracy、coverage 和 95% 置信区间（confidence interval [CI]）等指标报告；在参与者层面不能计算 AUC 的单一类别测试参与者不以 .50 填补。

严格共同样本的最小基线已经在相同 probe 行和相同 participant-disjoint folds 下完成。近红外（near-infrared [NIR]）质量控制（quality control [QC]）覆盖率 ≥80% 的主集合包含 213 条 probe、12 名参与者和 14 个 canonical sessions；NIR QC ≥50% 的敏感性集合包含 221 条 probe。当前低复杂度模型中，time/block structural baseline 的 AUC 分别为 .680 和 .663；radar-only 分别为 .582 和 .591；behavior + radar + NIR 分别为 .641 和 .621。由于样本量较小、4 名参与者仅包含单一二元类别，且当前融合模型并未构成多模态性能上限，因此这组结果仅作为严格共同样本的多模态最小基线，不用于宣称某一模态“无效”或多模态“失败”。

系统效度的重点不是毫米波单独是否高于 .50，而是它在显式考虑 time/block 与行为之后是否提供稳定的增量信息。正式报告将优先比较：

`time/block → behavior → behavior + radar → behavior + radar + NIR`

并报告相同测试参与者上的配对性能差值及 participant-level bootstrap 95% CI。后续 radar-only v2 仅在事件相关分析明确时间尺度和动态特征后启动，避免先以复杂模型寻找高分结果再倒推心理机制。

## 建议正文中的总结句

> 综上，本研究未将“信效度”简化为单一统计系数，而是针对不同测量层级建立与其科学声称相匹配的验证证据：thought probe 通过行为与任务进程关系建立构念有效性，毫米波通过数据质量控制及独立 Radar–ECG 逐搏基准建立测量与算法可靠性，最终识别系统则通过参与者独立验证和相对于时间/行为基线的增量比较评估泛化稳定性与应用价值。

## 正文必须保留 / 可移至附录

正文建议只保留：
1. probe 构念有效性的 1–2 个核心行为/时间结果；
2. RS6240 QC 汇总中的 3–5 个核心质量指标；
3. 外部 Radar–ECG benchmark 的 4–6 个核心指标（正式数据取得后）；
4. participant-independent AUC、balanced accuracy、95% CI 和增量比较。

附录可放：
- 完整 QC 字段；
- 多个窗口/指标的敏感性结果；
- 全部 paired bootstrap 表；
- 完整逐搏容差敏感性分析；
- 非主问卷相关；
- exploratory 模态比较。

不建议正文单独展开：完整可用性验证、每个雷达特征的生理效度、所有通道的重复性指标、所有问卷题与所有 probe 的两两相关。

## 当前待回填清单

- `[P0-1]` 北京 behavior/probe/stage/time 正式事件相关结果；
- `[P0-3]` 历史 probe 程序版本一致性；
- `[QUESTIONNAIRE_MEASUREMENT_AUDIT_V1]` 问卷类型、计分、内部一致性适用范围；
- `[RS6240_REPORT_QC_SUMMARY_V1]` RS6240 报告级 QC 表；
- `[C1b]` 正式独立 Radar–ECG benchmark；
- `[NIR directionality audit]` NIR AUC < .50 的实现方向/参与者方向核验。

## 参考文献

Corcoran, A. W., Le Coz, A., Hohwy, J., & Andrillon, T. (2025). When your heart isn’t in it anymore: Cardiac correlates of task disengagement. *Communications Biology, 8*, 1646. https://doi.org/10.1038/s42003-025-09026-3

Kane, M. J., Smeekens, B. A., Meier, M. E., Welhaf, M. S., & Phillips, N. E. (2021). Testing the construct validity of competing measurement approaches to probed mind-wandering reports. *Behavior Research Methods, 53*(6), 2372–2411. https://doi.org/10.3758/s13428-021-01557-x

Seli, P., Cheyne, J. A., & Smilek, D. (2013). Wandering minds and wavering rhythms: Linking mind wandering and behavioral variability. *Journal of Experimental Psychology: Human Perception and Performance, 39*(1), 1–5. https://doi.org/10.1037/a0030954
