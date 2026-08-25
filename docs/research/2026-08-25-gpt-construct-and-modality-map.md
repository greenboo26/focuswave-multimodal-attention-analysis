# 构念—测量—模态关系图：GPT 理论框架

日期：2026-08-25
状态：RESEARCH FRAMEWORK / 用于纵向分析与报告解释

## 1. 核心原则

本项目不是让所有变量彼此相关，也不是把所有模态都当作“专注度传感器”。不同数据位于不同层级、承担不同角色。

固定层级：

`个体 trait → session/context → stage/time-on-task → trial-level behavior / physiology → thought probe state`

最终产品目标可以是 radar-only，但科研分析必须先区分：什么是心理状态标签、什么是行为表现、什么是生理候选、什么是质量控制、什么是个体背景变量。

## 2. 五类数据的科学角色

### 2.1 Thought probe：即时状态操作性测量

当前四类：

1. 完全专注于分拣任务；
2. 关注实验本身，但没有聚焦于分拣任务；
3. 在想与实验无关的事情；
4. 大脑空白，没有明确想法。

当前主终点：`1 vs 2/3/4`，科学名称为“完全任务聚焦 vs 其他非完全任务聚焦状态”。

Thought probe 是主观即时状态报告，不是绝对 ground truth，也不是稳定 trait。

### 2.2 Behavior：任务表现与注意稳定性的外显结果

行为是最接近任务表现的客观通道，主要包括：
- error / accuracy；
- reaction time；
- reaction-time variability；
- omission / commission；
- recent error sequence；
- time-on-task / trial index。

行为的主要作用有三层：
1. 为 thought probe 提供构念有效性证据；
2. 描述注意状态转变前的动态；
3. 作为强基线，检验 radar/NIR 是否提供增量信息。

行为不是需要被“控制掉”的杂音。当前审计已经显示 time/block 和 error-related behavior 本身具有明显预测结构，因此必须作为正式科学变量。

### 2.3 Questionnaire：个体 trait 与外部校标

问卷原则上位于 participant level，而不是 probe level。

正式多题量表可在量表理论允许时计算内部一致性；单题“平时专注力如何”“通常能持续专注多久”等不能计算 Cronbach’s α，只能作为单题 trait 指标或外部校标。

优先检验的关系不是“每个问卷题 × 每个 probe”，而是：
- trait attention ↔ 个体平均完全任务聚焦比例；
- trait attention ↔ time-on-task 下降速度；
- trait attention × momentary state/physiology interaction。

只有在问卷 measurement audit 明确构念和计分后才进入正式模型。

### 2.4 Radar：产品核心传感模态，但生理解释分层

Radar 数据分成两类。

第一类：可直接作为预测输入但不赋予强生理含义的特征，例如原始相位/微动、呼吸候选、质量描述符和跨通道稳定性。这类特征需要质量控制（quality control [QC]），但不要求每一个特征都单独建立“心理效度”。

第二类：准备赋予明确生理意义的指标，例如心率变异性（heart rate variability [HRV]）。这类指标必须经过独立参考验证：

`radar → beat timestamps → inter-beat interval [IBI] → HRV`

在逐搏/IBI 外部验证完成前，只能称 `cardiac candidate` 或探索性心脏相关特征，不得称为已验证 HRV。

Radar 的核心科研问题不是“单独 AUC 多高”，而是：
- 是否存在与 stage/time/probe 状态相关的动态；
- 在 time/block 和 behavior 之后是否仍提供增量信息；
- 后续经过验证的 HRV 是否形成与自主神经调节一致的解释链。

### 2.5 Near-infrared：辅助生理/行为模态与多模态参照

近红外（near-infrared [NIR]）当前主要承担：
- pupil-related state dynamics；
- blink/eye-state 信息（字段可靠后）；
- 对 radar-only 的多模态参照和上限探索。

`pupil_equiv_diameter` 当前为标准化感兴趣区域像素尺度，不是物理毫米直径；报告只能解释为相对/标准化 pupil measure。

NIR 不能被定义为 ground truth。它与 probe/behavior/radar 的一致或互补关系属于多模态三角验证（triangulation），不是“谁验证谁”的单向结构。

## 3. 最重要的理论关系

### 主链 A：任务进程 → 状态 → 行为

`stage / time-on-task → thought probe state ↔ behavior`

这是当前最先验证的链。目的：判断任务聚焦状态是否随实验推进变化，以及 probe 前行为是否存在理论一致的动态。

### 主链 B：任务进程/状态 ↔ 生理动态

`stage / time-on-task ↔ radar / NIR ↔ probe state`

必须先控制或显式建模 time-on-task，避免把“实验越做越晚”的共同趋势误写成传感器特异性注意标记。

### 主链 C：增量信息

`time/block → + behavior → + radar → + NIR`

这里检验的是增量有效性，不是简单比较不同样本上的单模态 AUC。

只有同一 probe、同一 participant folds 才能公平比较模态。

### 主链 D：trait × state

`questionnaire trait → mean state / time-on-task slope`

以及在理论允许时：

`trait × momentary physiology/behavior → probe state`

该链用于解释“谁更容易出现任务聚焦下降”，不用于把 trait 问卷当即时标签。

### 主链 E：休息/恢复

`B1 late → break → B2 early → B2 progression`

休息段本身没有专注/不专注标签，也不能自动定义为闭眼静息。它主要用于恢复/重置分析和后续个体 baseline 探索。

## 4. 不应建立的错误关系

- `HRV = attention`：错误。HRV 只是可能与自主神经调节和状态变化有关的生理指标。
- `NIR = ground truth`：错误。
- `behavior = ground truth`：错误。行为和 probe 分别捕捉任务表现和主观状态。
- `label 2/3/4 = mind-wandering`：错误。
- `time-on-task = nuisance only`：错误。当前数据和文献均提示其本身是重要心理过程。
- `所有问卷题 → 所有 probe`：不必要且容易造成多重比较泛滥。
- `单模态 AUC 高低 = 模态有效/无效`：错误，尤其在样本、fold 或覆盖不同的情况下。

## 5. 报告中的一句主逻辑

推荐最终报告把整个证据链表述为：

> 本研究以 thought probe 作为即时任务聚焦状态的操作性测量，以任务行为建立构念相关证据，并在显式建模阶段与 time-on-task 的基础上考察毫米波和近红外生理/行为信息的动态关联及增量预测价值；对于拟赋予明确生理含义的毫米波 HRV 指标，则另行通过逐搏与 IBI 的外部参考数据进行分析验证。

## 6. 与预测系统的关系

科学解释与工程预测分开但连续：

`先解释什么在 probe 前变化`
→ `确定有意义的时间尺度/动态特征`
→ `再建立 participant-disjoint radar-only v2`
→ `必要时评估多模态训练或融合`

不得倒过来先用复杂模型找最强特征，再把这些特征解释成预先存在的心理机制。

## 参考文献

Corcoran, A. W., Le Coz, A., Hohwy, J., & Andrillon, T. (2025). When your heart isn’t in it anymore: Cardiac correlates of task disengagement. *Communications Biology, 8*, 1646. https://doi.org/10.1038/s42003-025-09026-3

Kane, M. J., Smeekens, B. A., Meier, M. E., Welhaf, M. S., & Phillips, N. E. (2021). Testing the construct validity of competing measurement approaches to probed mind-wandering reports. *Behavior Research Methods, 53*(6), 2372–2411. https://doi.org/10.3758/s13428-021-01557-x

Seli, P., Cheyne, J. A., & Smilek, D. (2013). Wandering minds and wavering rhythms: Linking mind wandering and behavioral variability. *Journal of Experimental Psychology: Human Perception and Performance, 39*(1), 1–5. https://doi.org/10.1037/a0030954
