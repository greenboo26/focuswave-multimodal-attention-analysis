# 北京纵向事件相关分析：GPT 方法冻结与解释标准

日期：2026-08-25
角色：GPT 研究/方法负责人
状态：METHOD FROZEN / 等待 Codex 数据执行

## 1. 目的

本文件冻结北京两阶段数据第一轮正式纵向事件相关分析的方法边界。目标不是先提高分类性能，而是回答：完全任务聚焦状态是否随任务推进发生系统变化、probe 前行为是否出现可重复的动态变化、强制休息后是否存在恢复，以及这些效应在控制重复测量结构后是否仍存在。

当前二元主终点继续定义为：`label 1`（完全专注于分拣任务）与 `label 2/3/4`（其他非完全任务聚焦状态）的区分。不得简称为“专注 vs 走神”。在历史程序版本、probe 文案和 response mapping 一致性核验完成前，不修改主终点。

## 2. 方法学依据

Thought probe 的效度不应主要依赖传统量表内部一致性，而应看其与理论相关行为、时间结构和其他构念之间是否形成一致关系。Kane 等（2021）在超过 1,000 名本科生中发现，probe-caught task-unrelated thought 与更高的反应时变异和更低的持续注意表现存在稳定的被试内关联，并同时检验了跨任务、回顾性自评和执行控制等构念关系。

行为变化可能在 probe 前较短时间尺度内出现。Seli、Cheyne 和 Smilek（2013）报告走神前 5 个 trial 的反应变异增加；Henríquez、Chica、Billeke 和 Bartolomeo（2016）发现，走神相关的反应时改变可集中出现在 probe 前约 2.5–10 s。因此，本项目预先保留 10、20、30 s 行为窗口是有理论依据的，但三种窗口必须作为同一预定义分析 family 报告，不能只保留结果最好看的窗口。

Corcoran 等（2025）在持续注意任务中将行为、瞳孔和心脏指标按 probe 前 10 s epoch 分析，并使用广义加性混合效应模型（generalized additive mixed-effects model [GAMM]）控制 time-on-task 与参与者内时间结构。这支持本项目把 time-on-task 作为正式科学变量，并在必要时使用非线性时间建模，而不是只把它当作需要消除的混杂。

## 3. 数据层级与单位

固定层级：

`participant → session → stage → trial/time → probe`

北京协议：`B1 → 强制休息 → B2`。

第一轮分析单位分为两类：

1. probe-level：每个 probe 对应一个预定义的 probe 前行为窗口；
2. trial-level：保留单个 trial，用于错误概率和反应时随时间变化的重复测量分析。

不能把同一参与者的多个 probe/trial 当作独立个体。

## 4. 预定义研究问题与主次顺序

### RQ1：任务聚焦状态是否随 time-on-task 改变？【主问题】

主结果变量：二元主终点 `label 1 vs 2/3/4`。

主预测变量：
- stage（B1 / B2）；
- stage 内标准化 time-on-task；
- `stage × time-on-task`。

首选模型：二项分布的广义线性混合效应模型（generalized linear mixed-effects model [GLMM]），participant 随机截距；若同一 participant 有多个 session，则 session 嵌套于 participant 或加入 session 随机截距，具体形式由数据可识别性决定。

如果可视化或残差诊断明确提示非线性，使用 GAMM 作为预先允许的扩展，不以“哪个模型显著”作为选择标准。

### RQ2：probe 前行为是否在状态之间分化？【主问题】

预定义行为指标：
- error / accuracy；
- commission error 与 omission error（任务定义允许时分别报告）；
- reaction time；
- reaction-time variability；
- 极端慢反应比例（阈值必须由设计文档或训练数据规则预先定义，不按结果调）；
- 连续错误/近期错误计数（字段可靠时）。

预定义窗口：probe 前 10、20、30 s。

统计原则：三个窗口属于同一 scientific family。优先报告效应方向、效应量、95% 置信区间（confidence interval [CI]）和经预先定义多重比较方法校正的显著性结果；不得只报告最低 *p* 值窗口。

### RQ3：强制休息是否伴随 B2 起始恢复？【主问题】

休息段不自动定义为“闭眼静息”或专注状态。恢复分析只比较可观察的任务/状态变化：

- B1 末端；
- B2 起始；
- 必要时 B2 后续早期窗口。

主问题是：B2 起始是否相对于 B1 末端出现任务聚焦比例或行为表现恢复。

不得把 B1→B2 差异直接解释为休息的因果效应，除非设计具有能够支持因果归因的对照结构。报告用语应为“休息后伴随的恢复/变化”。

### RQ4：个体差异是否影响上述动态？【次级问题】

第一轮只允许随机截距吸收稳定个体差异。随机斜率只有在样本量、收敛和方差估计支持时才加入。

问卷 trait moderator 等待问卷 measurement audit 后再进入，不在第一轮行为主分析中临时加入大量协变量。

## 5. 多重比较与显著性解释

同一理论问题下的多个行为指标/时间窗口按预定义 scientific family 控制多重比较。

默认：
- 较大指标 family：Benjamini–Hochberg false discovery rate（错误发现率 [FDR]）；
- 少量明确计划比较：Holm 校正。

统计显著性不是唯一判断标准。正式结果必须同时报告：
- 效应方向；
- 估计值；
- 标准误或 95% CI；
- 经校正的 *p* 值（适用时）；
- 原始样本量、参与者数、有效 probe/trial 数；
- 缺失和排除原因。

按第 7 版《美国心理学会出版手册》（Publication Manual of the American Psychological Association, 7th ed. [APA 7]）报告统计符号和数字，例如 *p* < .001，而不是 *p* = .000。

## 6. 图形必须优先于“显著/不显著”摘要

第一轮至少保留以下报告级图：

1. probe 序号/time-on-task × 完全任务聚焦比例轨迹，按 B1/B2 分面或分线；
2. probe 前 10/20/30 s 行为变化的估计边际均值/效应图；
3. B1 末端 → B2 起始的恢复图；
4. participant-level raw/summary overlay，用于显示结果是否由少数人驱动。

避免只展示总体柱状图，因为会丢失动态和重复测量结构。

## 7. 结果解释红线

允许：
- “完全任务聚焦概率随 time-on-task 下降/变化”；
- “某行为指标在非完全任务聚焦报告前出现更高/更低水平”；
- “B2 起始相对于 B1 末端出现恢复样变化”；
- “在控制参与者重复测量后关联仍存在”。

不允许：
- 把 `label 2/3/4` 合称为 mind-wandering；
- 把行为关联写成行为导致走神；
- 把时间效应简单称为疲劳，除非有独立疲劳测量支持；
- 把休息前后变化写成已证明的休息因果效应；
- 根据结果临时缩短/延长窗口；
- 先筛选显著行为指标，再把它们当作预注册式主结果。

## 8. 与 radar/NIR 的衔接

第一轮 behavior + probe + stage/time 结果用于建立构念有效性和时间尺度依据。之后 radar 和近红外（near-infrared [NIR]）必须挂接到相同 probe 时间轴；不得因为某模态更容易显著而重新定义行为窗口或 probe 终点。

如果后续 radar/NIR 与行为轨迹方向一致，可作为跨模态聚合证据；如果不一致，应报告为互补或不一致信息，不强行解释为“验证失败”。

## 9. 验收条件

Codex handoff 必须包含：
- deterministic timeline/session mapping；
- 纳入/排除人数与 probe/trial 数；
- 主模型公式与随机效应结构；
- 收敛与诊断状态；
- 10/20/30 s 全部预定义窗口结果；
- 多重比较 family 与校正方式；
- 报告级图表；
- exploratory 分析与 confirmatory/predefined 分析明确分开。

## 参考文献

Corcoran, A. W., Le Coz, A., Hohwy, J., & Andrillon, T. (2025). When your heart isn’t in it anymore: Cardiac correlates of task disengagement. *Communications Biology, 8*, 1646. https://doi.org/10.1038/s42003-025-09026-3

Henríquez, R. A., Chica, A. B., Billeke, P., & Bartolomeo, P. (2016). Fluctuating minds: Spontaneous psychophysical variability during mind-wandering. *PLOS ONE, 11*(2), e0147174. https://doi.org/10.1371/journal.pone.0147174

Kane, M. J., Smeekens, B. A., Meier, M. E., Welhaf, M. S., & Phillips, N. E. (2021). Testing the construct validity of competing measurement approaches to probed mind-wandering reports. *Behavior Research Methods, 53*(6), 2372–2411. https://doi.org/10.3758/s13428-021-01557-x

Seli, P., Cheyne, J. A., & Smilek, D. (2013). Wandering minds and wavering rhythms: Linking mind wandering and behavioral variability. *Journal of Experimental Psychology: Human Perception and Performance, 39*(1), 1–5. https://doi.org/10.1037/a0030954
