# NIR 低 AUC 的方法学审计与下一步分析框架

日期：2026-08-25
角色：GPT 研究/方法负责人
状态：METHOD REVIEW / 当前结果仅探索性

## 1. 当前事实

严格共同样本中，近红外（near-infrared [NIR]）单模态模型的受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）为：

- Primary：.3497；
- Sensitivity：.3177。

方向性审计已经确认：`raw label 1 → target 0`，`raw labels 2/3/4 → target 1`；`predict_proba[:, 1]` 对应 target 1；24 个 fold 的类别顺序检查通过。8 个可评估参与者中有 5 个呈反向排序。因此当前低 AUC 不是简单的标签翻转或概率列取错，也不能用 `1 - AUC` 改写成新的性能结果。

## 2. 文献对这类结果的启示

瞳孔与 mind-wandering / task disengagement 的关系在文献中并不是单一方向。Pelagatti、Blini 和 Vannucci（2025）综述指出，不同研究对 tonic pupil size 报告过增大、减小和零效应；慢变 tonic pupil 同时受到 arousal、drowsiness、time-of-day、任务情境和个体基线等因素影响，因此将一个固定窗口均值直接视为稳定的“走神指标”容易产生不一致结果。

Jubera-García、Gevers 和 Van Opstal（2020）在持续注意任务中发现，行为和 phasic pupil response 对注意状态更敏感，而 tonic pupil diameter 在两项实验中表现不一致。他们在分析前将瞳孔数据按参与者转换为 z 分数，并用混合效应模型处理参与者内重复测量。这说明跨参与者直接比较绝对/标准化水平，可能混入较大的个体基线差异；事件相关或参与者内变化通常更接近研究问题。

另有多模态 mind-wandering 研究将 pupil feature 在每名参与者内标准化后再进入跨参与者机器学习，这种做法进一步支持：在研究“状态变化”时，应区分 **between-person baseline** 与 **within-person deviation**，而不是只使用一个 pooled level feature。

## 3. 对当前 NIR 结果最合理的解释

当前结果应写为：

> 在严格共同样本、当前低复杂度模型和现有 NIR 特征表示下，NIR-only 对“完全任务聚焦 vs 其他非完全任务聚焦状态”的排序呈稳定低于机会方向；方向性审计未发现标签或概率列实现错误，因此该现象需要从参与者内基线、time-on-task、tonic/phasic 时间尺度和状态构念差异进一步解释。

不得写：

- “NIR 无效”；
- “瞳孔与专注负相关”；
- “反转 AUC 后性能为 .65/.68”；
- “NIR 可以作为 ground truth”。

## 4. 优先假设，不按结果挑选

下一步只检验四个预先声明的方法学解释，按以下顺序进行。

### H1. Between-person baseline 主导 pooled ranking

如果不同参与者的 pupil baseline 差异远大于同一参与者在不同 probe 状态间的变化，pooled classifier 可能学习到“谁的瞳孔通常大/小”，而不是“这个人此刻是否偏离自己的基线”。

优先检查：

- participant-level pupil baseline distribution；
- 同一参与者内中心化后的状态差异；
- raw/standardized level 与 within-person centered feature 的方向是否一致。

这不是为了寻找更高 AUC，而是为了判断数据层级是否错配。

### H2. Time-on-task / stage 共同趋势

Tonic pupil size 可随持续任务、警觉度和疲劳相关状态缓慢变化；当前标签本身也存在明显 time/block structure。因此 pupil 与标签可能因为共同时间趋势表现出相关或反向关系。

优先模型：

`NIR feature ~ stage + time-on-task + probe state + (1|participant)`

或等价的重复测量模型。

首先报告控制 time-on-task 前后 probe-state 效应是否改变，而不是只看单一分类 AUC。

### H3. Tonic 与 phasic 时间尺度混合

当前 `pupil_equiv_diameter` 是标准化感兴趣区域像素尺度，不是毫米级物理直径。若当前主要是较长窗口均值，它更接近 tonic measure；文献显示 tonic measure 对 mind-wandering 的方向并不稳定。

后续若事件字段允许，应把分析分为：

- tonic / slow level：较长 probe-preceding baseline 与慢变趋势；
- phasic / event-related dynamics：刺激或 probe 前短时变化、baseline-corrected response、斜率/波动。

在 NIR 视频没有可靠事件分辨率或 blink/ROI QC 之前，不强行构造 phasic 指标。

### H4. 当前四类心理状态不是单一 on/off 轴

当前二元终点将 label 2、3、4 合并，但它们分别代表“实验相关但未聚焦任务”“实验无关思维”“思维空白”。这三类状态可能具有不同 pupil/arousal 模式。低 AUC 可能部分来自把异质状态压成一个二元目标。

因此，在历史 probe 版本语义确认后，可以做 **预先定义的描述性四类 NIR 轨迹**，但不根据哪一类分法 AUC 更高来重编码主终点。

## 5. 下一步正式方法：先轨迹，后分类

NIR 下一轮不以提高 AUC 为目标，建议按以下顺序。

### Step 1. Participant-level QC 与基线图

每名参与者报告：有效 probe 数、NIR quality control（质量控制 [QC]）覆盖、pupil level 分布、缺失、单类/多类标签覆盖。

### Step 2. Within-person centered trajectory

对可用 NIR feature 计算参与者内中心化或等价随机效应模型，不用测试集信息做全局标准化。若要进入预测模型，任何标准化必须在训练折内拟合。

### Step 3. Probe-locked / time-on-task mixed analysis

优先回答：

1. NIR 是否随 stage/time-on-task 系统变化；
2. 在控制 time-on-task 后，probe state 是否仍有关联；
3. 参与者内效应方向是否一致；
4. NIR 与 behavior trajectory 是一致、互补还是无稳定关系。

### Step 4. 描述性四类状态

只在 probe 语义审计通过后进行。报告 label 1/2/3/4 的估计轨迹和 CI，不用结果驱动重新定义主 endpoint。

### Step 5. 预测模型回归

只有在上述分析明确了合理时间尺度和方向后，才考虑重新构造 NIR predictive features。此时仍使用 participant-disjoint folds，并与 time/block baseline 公平比较。

## 6. 对 Codex 的验收要求

`NIR_EVENT_READINESS_V1` 或后续 NIR longitudinal handoff 至少应包含：

- participant-level QC/coverage；
- within-person 与 between-person 分解；
- stage/time-on-task 轨迹；
- probe state 在控制 time 后的效应；
- 原始 level 与 centered feature 的方向比较；
- 如可行，tonic 与 phasic/event-related 指标明确分开；
- 不提交反转后的 AUC 作为性能结果。

## 7. 结论

当前 NIR 低 AUC 是一个需要解释的真实分析现象，不是已发现的实现错误。最合理的下一步不是继续调分类器，而是把 pupil measurement 放回正确的数据层级：**参与者内状态变化 + stage/time-on-task + tonic/phasic 时间尺度 + 四类状态异质性**。这一步完成后，才有资格判断 NIR 是否为 attention monitoring 提供稳定的增量信息。

## 参考文献

Jubera-García, E., Gevers, W., & Van Opstal, F. (2020). Influence of content and intensity of thought on behavioral and pupil changes during active mind-wandering, off-focus, and on-task states. *Attention, Perception, & Psychophysics, 82*(3), 1125–1135. https://doi.org/10.3758/s13414-019-01865-7

Pelagatti, C., Blini, E., & Vannucci, M. (2025). Catching mind wandering with pupillometry: Conceptual and methodological challenges. *WIREs Cognitive Science, 16*(1), e1695. https://doi.org/10.1002/wcs.1695
