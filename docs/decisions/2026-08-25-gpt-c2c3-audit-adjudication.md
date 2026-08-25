# 生成式预训练变换器（generative pretrained transformer [GPT]）裁决：C2 evaluation/label audit 与 C3 identity/coverage crosswalk

日期：2026-08-25
依据：`docs/decisions/2026-08-25-gpt-c2-c3-audit-handoff.md`

## 总裁决

本轮 audit/crosswalk 通过。当前不进入复杂模型、teacher–student 或基于结果反向改标签/阈值。

下一步批准两件事：

1. 建立严格共同样本上的近红外（near-infrared [NIR]）、毫米波、行为及融合最小基线；
2. 同时由 GPT 侧冻结“完整实验结构分析 v2”的方法设计，后续用于事件相关、阶段/时间、静息/休息、问卷和重复测量分析，而不是直接把 C2 升级为更复杂分类器。

## 1. 标签终点裁决

暂时保留现有二元主终点：`label 1` 对 `label 2/3/4`，直到历史 session 的程序版本与 probe 文案一致性核验完成。

但是，科学命名必须立即修正：

- `label 1`：完全专注于分拣任务；
- `label 2`：关注实验本身，但没有聚焦于分拣任务；
- `label 3`：在想与实验无关的事情；
- `label 4`：大脑空白，没有明确想法。

因此，`1 vs 2/3/4` 的主终点只能描述为“完全任务聚焦（fully task-focused）与其他非完全任务聚焦状态（other non-fully-task-focused states）”的区分，或同义的构念中性名称。

不得把该二元终点直接写成“专注 vs 走神（mind-wandering）”。`label 3` 才最接近典型任务无关思维；`label 4` 属于思维空白；`label 2` 属于实验相关但任务未聚焦状态。三者不应在理论解释中被视为同一心理构念。

历史程序版本核验完成后，可预先定义次级/敏感性分析，例如多类别模型或特定类别对比；但不得根据哪种编码产生更高性能而选择标签方案。

## 2. 时间/区组 baseline 裁决

接受将原 `N0_grouped_null` 正式改名为“时间/区组结构基线（time/block structural baseline）”，不再称为 generic null。

受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）为 .628 的 `N0` 不包含雷达传感器信息，因此不能作为雷达证据；但 session-preserving permutation 的结果表明，时间/区组结构与标签之间存在明显的非随机关系。

后续雷达、行为和 NIR 模型必须至少同时对照：

- 训练折先验常数基线；
- probe index / time-on-task 基线；
- time/block structural baseline；
- 行为 baseline。

不得仅与 .50 比较后宣称存在有效传感器预测。

此外，`N0` 的结果提示 time-on-task / block progression 本身值得作为正式解释性分析对象，而不仅是需要“消除”的 nuisance variable。

## 3. subject 070 裁决

确认：subject `070` 在缺少可追溯真人身份材料前，保持 `unresolved_blocker`。

不得通过 NIR 特征、时间模式、模型相似性或其他推断方式补身份；不得将其纳入 participant-disjoint NIR 分组、共同样本模态比较或融合模型。

若后续仅做不涉及参与者泛化声明的纯描述性数据质量汇总，可单独列出，但必须明确其身份未解析。

## 4. 严格共同样本模态比较：批准，但增加运行条件

批准在严格共同 probe 上建立 NIR-only、radar-only、behavior-only 和 fusion 的公平最小基线，但正式运行前必须生成一个新的 common-subset manifest，并满足以下条件。

### 4.1 样本键

当前严格共同 probe 定义为：`subject + probe_id + exact absolute onset`。

C2 缺少显式 `session_id`。在正式建模前，Codex 应优先尝试通过现有 metadata/crosswalk 对 289 条 strict overlap 进行确定性 session 映射，并新增 canonical `session_id`。只有一对一、可审计的元数据映射可以使用；不得用特征或模型猜测。

如果仍无法恢复 `session_id`，可继续做 participant-disjoint 的最小共同样本基线，但必须继续称为“strict common probe”，不得写成“same-session multimodal dataset”。

### 4.2 参与者分组

必须使用完全相同的 `repeat_participant_id` 分折，使所有模态在同一测试参与者上产生预测。

优先使用留一参与者交叉验证（leave-one-participant-out cross-validation [LOPO-CV]）或与当前 C2 完全等价的 participant-disjoint folds；subject `070` 排除。

需要先报告 289 条 strict common probe 中：

- 可解析参与者数量；
- session 数量（若可恢复）；
- 四类原始 probe 标签数量；
- 二元主终点类别比例；
- 每个参与者的 probe 数和类别覆盖。

若部分测试参与者只有单一类别，则该参与者的 AUC 不可计算；不得填成 .50。应报告 pooled 折外预测（out-of-fold [OOF]）AUC，并另报可定义 participant-level AUC 的宏平均结果。

### 4.3 NIR 质量集合

不得把所有 289 条直接当作同等质量 NIR 数据。

正式比较至少预先形成两个集合：

- Primary NIR-comparable set：strict common probe + identity resolved + NIR 质量控制（quality control [QC]）覆盖率 ≥ 80%；
- Sensitivity set：strict common probe + identity resolved + NIR QC 覆盖率 ≥ 50%。

所有模态在每个集合中必须使用完全相同的 probe 行。也就是说，当比较 NIR 与 radar 时，radar 也必须限制在同一 NIR-qualified probe 集合上。

NIR QC 覆盖率 < 50% 的 probe 不进入 NIR 性能主分析。

### 4.4 第一轮模型复杂度

共同样本只有约 289 条 probe，且实际可用参与者数明显小于完整 C2 数据。因此第一轮只批准固定、低复杂度模型，不批准先上大型时序模型。

建议保持固定 L2 正则逻辑回归或同等级简单模型，所有标准化/缺失处理只能在训练折拟合。

第一轮比较至少包括：

- time/block structural baseline；
- behavior-only；
- radar-only；
- NIR-only；
- behavior + radar；
- radar + NIR；
- behavior + radar + NIR。

该轮目的不是追求最高 AUC，而是估计在同一批 probe、同一 participant folds 下，各模态是否提供增量信息。

### 4.5 统计报告

除 AUC 外，至少报告：

- balanced accuracy；
- sensitivity / specificity（若阈值预先固定或在训练折内确定）；
- 参与者层级 bootstrap 的 95% 置信区间（confidence interval [CI]）；
- coverage；
- 每个模态相对 behavior-only 与 time/block baseline 的 AUC 差值；
- paired participant bootstrap 的模态差值 95% CI。

不根据同一测试结果选择“最佳”QC 阈值、特征组或模型。

## 5. C2 audit 的科学解释

当前最重要的新发现不是“雷达 AUC 低”，而是标签存在可重复的任务推进/时间结构。

因此，下一版完整实验分析必须把：

- time-on-task；
- block / stage；
- probe sequence；
- 行为错误和反应时变化；
- participant repeated measures

作为正式建模结构，而不是仅作为机器学习中的 nuisance covariates。

这也意味着当前 C2 第一版应被定位为“最低复杂度预测基线”，不是整个实验的最终分析。

## 6. 完整实验结构分析 v2：批准设计，暂不直接大规模运行

在 common-subset 最小基线之外，批准开始建立方法设计文档，围绕：

`participant → session → stage/block → trial/time → probe`

组织以下分析：

1. probe-locked event-related trajectories；
2. trial-level behavior dynamics；
3. stage × time-on-task；
4. resting baseline / task reactivity；
5. break/recovery；
6. questionnaire trait × state relationships；
7. radar/NIR/behavior multimodal triangulation；
8. 最后再进入 radar-only predictive model v2。

该方法设计必须先定义研究问题、变量时间窗口、主/次终点和多重比较控制，再运行结果；不得先看哪个窗口/指标显著再倒推研究问题。

## 7. C1b 与 HRV 状态

C1b 继续保持 `protocol-ready / data-access blocked`。心率变异性（heart rate variability [HRV]）路线不取消、不降级，也不因当前 C2 结果修改冻结的逐搏（beat）/心搏间期（inter-beat interval [IBI]）评价协议。

## 下一次 Codex handoff 要求

下一次只需交回两个证据包：

1. `COMMON_SUBSET_BASELINE_V1`：common-subset manifest、participant/session/key audit、Primary/Sensitivity 样本量、固定模型结果、paired comparisons；
2. `LONGITUDINAL_EVENT_ANALYSIS_V2_DESIGN`：只交方法设计和变量/时间窗映射，不先跑大量探索性结果。

在这两个证据包回来前，不进入 teacher–student、复杂深度模型或根据结果重新定义心理标签。
