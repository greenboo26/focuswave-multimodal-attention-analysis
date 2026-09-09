# 专注构念、Probe 语义与分析顺序补充裁决（2026-09-09）

状态：`METHOD_AMENDMENT / EXECUTION_NOT_YET_RUN`

本文件是对 `docs/decisions/2026-09-09-momentary-attention-feature-discovery-and-construct-validation.md` 的补充，不另起平行分析体系。原文件中关于宽候选特征库、participant-disjoint 验证、training-only 特征筛选、二分类后回到四分类、10/20/30 s、多模态资格门和竞争解释控制等内容继续有效；本补充把**更前置的构念定义、Probe 语义和事后问卷角色**补齐。

## 当前主路线（一张图）

```text
                  目标：专注状态
                        │
                        ▼
            1. 先定义构念和 Probe 语义
                        │
      ┌─────────────────┴──────────────────┐
      ▼                                    ▼
Thought Probe 四类                     事后问卷
1 Focused                          任务理解 / Probe 语义
2 Task-related                    困倦 / 疲劳 / trait
3 Mind-wandering
4 Blank
      │
      ▼
2. 不预设唯一二分，而是预定义多个有不同心理含义的对比
   - 1 vs 234：完全当前任务聚焦 vs 其他状态
   - 12 vs 34：广义任务相关投入 vs 非任务相关/空白
   - 1 vs 3：最纯 Focus–mind-wandering 对照
   - 1/2/3/4：完整状态分化
      │
      ▼
3. Probe × SART behavior 构念效度
   RT/RT variability/error/omission/commission/dynamics
   10/20/30 s 均报告
      │
      ▼
4. 宽候选特征发现
   Behavior + NIR + mmWave + RGB
   仅限科学上合理、producer/QC/生理资格允许的特征
      │
      ▼
5. participant-disjoint 简单模型
   所有 impute/scale/select/tune/fit 仅在 training participants 内
      │
      ▼
6. 找稳定特征 → 回到四分类
   二分类稳定特征可重点检查，但不能垄断四分类 feature space
      │
      ▼
7. 排除竞争解释
   time-on-task / sleepiness / fatigue / arousal / movement / QC
      │
      ▼
8. 证据链成立后再训练、校准产品“专注状态”输出
```

## 1. 不再把 `1 vs 234` 当作唯一的“专注定义”

当前四类 Probe 应继续保留为原始主观状态数据：

1. `Focused`：完全聚焦当前任务操作；
2. `Task-related thought`：仍围绕实验/任务内容，但未完全聚焦当前操作；
3. `Mind-wandering`：明确任务无关思维；
4. `Blank mind`：没有明确可报告思维内容。

关键修正：四类不能先验地当作一条“专注程度 1→2→3→4”的单轴。尤其 label 2 是边界状态，label 4 也不应自动当作更严重的 mind-wandering。

因此不寻找一个由模型性能决定的“唯一正确二分”。预定义以下不同构念对比：

- `1 vs 234`：回答“是否完全聚焦当前任务操作”；
- `12 vs 34`：回答“心理活动是否仍属于广义任务相关投入”；
- `1 vs 3`：回答“明确任务聚焦与明确任务无关思维之间有什么差异”；
- `1/2/3/4`：回答四种主观状态是否具有不同的行为和多模态模式。

禁止根据哪个划分 AUC 最高，反过来宣称哪个才是“真正的专注”。标签定义属于构念问题，模型性能只能回答可预测性。

## 2. 事后问卷必须前置进入效度框架

事后问卷不是新的 ground truth，也不与 Probe/行为/生理按人工比例组成“专注分数”。它承担三种角色。

### 2.1 硬门控：任务是否真正理解和执行

只有明确的任务理解/执行失败适合作为正式纳入门控，例如：

- 事后任务规则理解明确错误；
- 实际按键行为同时支持其没有按正确规则执行；
- session/ID 无法对应、关键数据无效；
- Probe 基本没有有效作答。

不应仅因“问卷与 Probe 不一致”就删除参与者。

### 2.2 Probe 语义效度与理解不确定性

应先做问卷 × Probe 审查，帮助判断各 Probe 类别是否按预期被使用：

- 事后“想与任务无关的事情/走神比例”优先与 **Probe 3** 比较，而不是默认与 2/3/4 总和比较；
- 事后“想实验表现、做得好不好、还要多久”等 task-related 内容优先与 **Probe 2** 使用比例比较；
- 如果自由回答明确表示“选项模糊、不知道怎么选”，记录 `probe_interpretation_uncertainty`，作为软标记和敏感性分析依据，不事后随意删人。

应比较：

`全样本结果` vs `排除高 Probe 理解不确定性参与者后的结果`。

### 2.3 竞争解释与外部效标

事后问卷中的疲劳、困倦变化、睡眠、咖啡因等用于判断所谓“低专注”是否主要被 sleepiness/fatigue/arousal 解释。

平时专注能力、通常可持续专注时长等 trait 问题用于 participant-level 外部效标，不作为 Probe 正误门控。

因此当前限制应表述为：**缺少的是 probe-level 瞬时困倦评分，而不是完全没有 sleepiness 测量。** 现有事后问卷可以支持 participant/session 层面的困倦与疲劳分层、协变量和敏感性分析，但不能替代每个 Probe 时刻的 KSS 类即时评分。

## 3. Behavior 的角色必须先于机器学习特征发现

Behavior 同时有两种角色，但顺序不能反：

1. **构念效度证据**：先检验 Probe-defined states 是否伴随理论上合理的任务行为变化；
2. **预测特征**：验证完成后，Behavior 也可以进入模型。

当前 canonical Behavior 已包含 mean/median/SD/MAD/CV/slope/accuracy/error/omission 等，不重新造一套“行为动态管线”。必要时只补经审计确实缺失的 IQR、P90-P10、trial-to-trial change、extreme slow/fast、commission 等。

Probe × Behavior 正式分析须保留 10/20/30 s 全部窗口，不以最高 AUC 或最小 p 值选“正确窗口”。

## 4. 老师提出的宽特征二分类路线继续采用，但位置后移

在构念/Probe/问卷/Behavior 这一层厘清后，再执行数据驱动特征发现：

- 建立各模态“科学上合理且质量合格”的宽候选特征库；
- 第一轮保持简单模型；
- participant-disjoint split；
- imputation、scaling、feature selection、hyperparameter tuning、model fitting 全部只发生在 training participants；
- 10/20/30 s 分别跑；
- 优秀特征定义为跨 fold/participant/window/QC/困倦敏感性下稳定，而不是一次性 Top 10。

当前生理资格门不因“全特征”而解除：未通过 beat/IBI validity 的 mmWave HRV 继续 `BLOCKED`；PERCLOS/blink duration 更偏 sleepiness/drowsiness 解释；pupil/HR/respiration/head-motion 不得单独称 attention-specific biomarker。

## 5. 二分类之后必须回到四分类

二分类的稳定特征只作为四分类重点候选，不能成为四分类唯一 feature space。

四分类至少保留两条路线：

- A：二分类稳定特征 → 四分类；
- B：完整合格候选特征库 → 四分类内部重新做 training-only 特征筛选。

这样才能区分：

- 哪些是一般性的“当前任务聚焦”信号；
- 哪些只负责区分 task-related thought / mind-wandering / blank mind。

## 6. 最终产品与研究阶段分开

研究阶段不人工规定：

`专注 = 40% Probe + 30% Behavior + 20% pupil + 10% HR`

主观、行为、生理首先是不同证据源。模型参数可以学习预测贡献，但不能解释成心理构念“组成比例”。

只有在构念效度、竞争解释、participant-level 泛化和校准都得到支持以后，才把经过验证的模型输出转换为产品层的“专注状态/概率/指数”。状态分数与信号质量/置信度必须分开。

## 7. 当前执行优先级

当前不是直接跑“所有模态二分类”。优先级冻结为：

1. **P0-A：构念与 Probe 对比定义表**：写清 `1 vs 234`、`12 vs 34`、`1 vs 3`、四分类各回答什么；
2. **P0-B：事后问卷 × Probe 语义/任务理解审查**：硬门控、软理解标记、困倦/疲劳/trait 角色分开；
3. **P0-C：Probe × Behavior × 10/20/30 s 构念效度**；
4. **P0-D（可并行）：各模态可用候选特征/QC/资格盘点**；
5. **P1：宽候选特征的 participant-disjoint 粗粒度模型**；
6. **P1：稳定特征审计 + 四分类双路线**；
7. **P2：竞争解释、跨模态增量、产品模型与校准。**

## 8. 当前结论

老师的“先简单二分、宽候选特征、再四分”方向继续保留，但不再作为分析的第 0 步。

真正的当前主线是：

> **定义专注构念与 Probe 语义 → 利用事后问卷做任务理解/Probe 语义/困倦疲劳效度审查 → 用 SART behavior 建立构念效度 → 再执行宽特征二分类发现 → 回到四分类 → 排除竞争解释 → 最后训练和校准产品专注状态模型。**

本补充只改变方法顺序和解释边界；没有重跑任何数据、没有改变已有 cohort/fold/window/producer/QC 生理资格，也没有把旧模型结果重新解释为最终结论。
