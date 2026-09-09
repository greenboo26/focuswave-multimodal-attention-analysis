# 瞬时专注状态：特征发现与构念验证分析路线（2026-09-09）

状态：`METHOD_DECISION / EXECUTION_NOT_YET_RUN`

日期：2026-09-09

## 0. 本次决策一句话

采纳“**先用粗粒度二分类建立完整、科学上合理的候选特征空间并做严格的训练内特征发现，再回到四分类分析状态差异**”的路线；同时保留独立的构念效度链，防止把“能分类 probe 的特征”直接解释成“专注指标”。

这不是重做既有 Behavior baseline，也不是推翻当前 `1 vs 2/3/4` 主终点。它是对现有窄跨模态 predictor contract 的方法扩展。

---

## 1. Reuse Gate：本次为什么不是重复造轮子

### 1.1 已经存在、应直接复用的资产

当前 canonical 行为基线已经完成：

- `REPORT_ANALYSIS_COHORT = 1400 probes / 70 sessions / 46 repeat participants`；
- 标签为 `1 vs 2/3/4`；
- 10/20/30 s 三个 probe 前窗口；
- 5-fold `StratifiedGroupKFold`，按 `repeat_participant_id` 分组；
- 缺失值填补、标准化、L2 logistic 拟合都在 training fold 内；
- Behavior 现有实现已经不是“只取中位数”，而是包含：
  - trial count；
  - RT mean；
  - RT median；
  - RT SD；
  - RT MAD；
  - RT CV；
  - RT slope；
  - accuracy；
  - error count/rate；
  - omission count/rate。

入口：`pipelines/behavior/run_final_report_cohort_baseline_v2.py`。

因此：**行为侧“30 s 只取中位数导致波动被压掉”不是当前 canonical Behavior baseline 的真实状态。** 这个担忧仍然对“只用单一中心趋势代表一个长窗口”的做法成立，但行为主线已经补过 SD/MAD/CV/slope 等动态摘要，后续应复用而不是重写。

### 1.2 当前真正需要扩展的地方

`docs/results/2026-08-30_FORMAL_MODEL_READY_V1/MODEL_READY_READINESS_REPORT.md` 当前正式候选合同较窄：

- Behavior：5 个 primary predictors；
- NIR：4 个 primary predictors；
- RGB：6 个 primary predictors；
- blink 仅 `PROVISIONAL_CANDIDATE`；
- PERCLOS 未进入正式候选；
- mmWave/HR/BR/RR/HRV/IBI 被排除。

本次新问题是：

> 在 producer/QC/生理资格允许的前提下，扩大各模态的**科学上合理候选特征库**，检验哪些动态信息能稳定地区分“完全任务聚焦 vs 其他状态”，然后再进入四分类构念分化。

这和既有“固定小特征集的 baseline / incremental AUC”不是同一问题，因此存在明确的 `REUSE_REJECTION_REASON`：**旧结果不能回答完整候选特征空间中的稳定特征发现，也不能回答四类状态内部差异。**

但旧代码、fold、cohort、probe alignment、已有 feature extractor 必须优先复用。

---

## 2. 科学问题重新定义

项目最大科学问题不是：

> 哪个模态分类效果最好？

而是：

> Thought probe 标签及其对应的行为、眼动、自主生理和运动变化，能否共同支持“瞬时任务聚焦状态”的解释，而不是仅反映主观报告、任务表现、疲劳、困倦、唤醒或 time-on-task？

因此分析必须同时有两条轨道。

### Track A：数据驱动的特征发现

回答：

> 我们已有的合理候选特征中，哪些对 `Focused vs Other` 有稳定、跨参与者的信息？

### Track B：构念验证

回答：

> 这些差异为什么能支持 attentional state，而不是 sleepiness / fatigue / arousal / time-on-task？

两条轨道最后汇合，但不能互相替代。

---

## 3. Thought probe 的角色

当前四类语义保持：

1. `focused`：完全专注于当前分拣/任务；
2. `task-related thought`：仍与实验/任务有关，但没有完全聚焦当前操作；
3. `mind-wandering`：任务无关思维；
4. `blank mind`：没有明确思维内容。

### 3.1 Probe 不是绝对 ground truth

Thought probe 是即时主观状态的操作性测量 / experience sampling，不是“无测量误差的客观真值”。

其有效性主要来自：

- 与 probe 前行为变化的收敛；
- 与 time-on-task / task manipulation 的理论一致关系；
- 与眼动/生理等独立通道的收敛或区分；
- 不同任务/测量方法间的构念关系。

### 3.2 为什么允许先二分类

第一阶段定义：

`Focused = label 1`

`Other = label 2/3/4`

科学名称只能写：

> 完全任务聚焦 vs 其他非完全任务聚焦状态

不能写成：

> 专注 vs mind-wandering

也不能声称：

> task-related thought = mind-wandering = blank mind

二分类只承担粗粒度 screening / feature discovery 的角色：先判断数据里是否存在“明确任务聚焦”与其他状态之间的稳定信号。

---

## 4. 老师建议的裁决

老师提出：

1. 先把四类压成二类跑一套简单模型；
2. 第一轮不要由研究者凭感觉只挑少数特征；
3. 把“可以合理计算”的特征先放入候选空间；
4. 根据二分类结果找稳定优秀特征；
5. 再回到四分类分析。

### 裁决：方向 `PASS`，必须附加以下边界

#### 边界 A：不是“数学上能算的数字全部塞进去”

只能进入：

> `all scientifically computable and quality-qualified candidate features`

即“科学上合理、当前 producer 与数据质量允许计算的候选特征”。

提前排除：

- 明显不可靠或未通过 producer/QC gate 的变量；
- 高缺失且无法给出有效 missingness 语义的变量；
- near-constant / 无有效变异变量；
- probe 之后的信息；
- 标签派生变量；
- 数据泄漏变量；
- 当前时间窗不支持的方法学指标；
- 错误地把 QC 状态码当生理特征的变量。

#### 边界 B：特征筛选只能发生在训练参与者内部

禁止：

`全部 probes → 看标签挑 top features → 再 cross-validation`

这会把测试集标签泄漏到特征选择阶段，性能会虚高。

必须：

`按 participant 划 outer fold → training participants 内 impute/scale/select/tune/fit → untouched test participants evaluation`

只要加入特征筛选或超参数选择，就必须保证这些操作不查看 outer test fold。

#### 边界 C：二分类筛出的特征不能垄断四分类

二分类 top/stable features 可以作为四分类重点候选，但四分类还必须允许在完整合格 feature bank 中重新筛选。

原因：某特征可能不擅长 `Focused vs Other`，却非常擅长区分 `MW vs Blank` 或 `TRI vs Blank`。

---

## 5. 第一阶段：宽候选特征库 + 二分类

### 5.1 先分别做 10 / 20 / 30 s

第一轮不建议把三个窗口的所有特征直接拼进同一个模型。

应该固定相同特征定义，分别建立：

- 10 s 模型；
- 20 s 模型；
- 30 s 模型。

这样可以回答：

- 哪个时间尺度最稳定；
- 哪些信息只在离 probe 很近时出现；
- 哪些特征需要更长积累才可靠；
- 30 s 是否因为混入状态变化而稀释瞬时效应。

不得只保留表现最好看的窗口。

### 5.2 Behavior：复用现有动态特征，必要时补少量遗漏

现有 canonical Behavior 已包含：mean / median / SD / MAD / CV / slope / accuracy / error / omission。

可审计后考虑补充：

- IQR；
- P90-P10 或其他稳健分位数跨度；
- trial-to-trial absolute change；
- 极慢反应比例；
- 极快/anticipatory 反应比例；
- commission error（如果当前任务字段能可靠区分）；
- recent error sequence / lapse burst（字段可靠时）。

重点：这些不是人工指定为“唯一专注特征”，而是候选库的一部分。

### 5.3 NIR 候选信息类型

在 producer/QC 通过后，候选层应从“单一水平”扩展到：

- pupil center level：mean / median；
- pupil variability：SD / MAD / IQR / CV（当尺度定义允许）；
- pupil local slope / trend；
- pupil short-timescale fluctuation；
- blink count / rate；
- blink duration summary；
- eyelid closure / PERCLOS（只有正式定义和 QC 通过后）；
- valid-frame coverage / detection quality 作为质量变量，不与生理特征混为一谈。

重要解释边界：pupil/blink 同时强受 arousal、drowsiness、视觉条件等影响，不是 attention-specific marker。

### 5.4 mmWave 候选信息类型

只能按当前生理资格分层。

当前仓库状态中 HRV beat-level promotion gate 未通过，HRV 继续 `BLOCKED`；因此“宽特征库”不能借机把未验证 HRV 指标重新包装成正式 attention feature。

可考虑的层级：

- HR level / short-window variability：仅在 HR producer validity 允许的范围；
- respiration rate / variability：在短窗可估计性允许的范围；
- body-motion magnitude / variability / event count；
- radar signal quality / coverage / motion contamination：作为 quality/control variables。

10–30 s 内不应把传统 LF/HF 等频域 HRV 当正式主特征；任何 ultra-short HRV 也必须先过 beat/IBI validity gate，当前不自动授权。

### 5.5 RGB 候选信息类型

在正式 producer/QC 通过后，可按：

- head-pose deviation；
- head-pose variability；
- head-motion magnitude / variability；
- blink / eyelid（若字段正式可靠）；
- facial/body motion amount；
- movement event count；
- face/body coverage、tracking confidence 等 quality variables。

RGB movement/head pose 更适合 supporting disengagement evidence 或 quality 信息，不是“头一偏就是不专注”。

---

## 6. 模型第一轮保持简单

第一轮目标不是榨最高 AUC，而是确认候选信息中有没有稳定信号。

建议保留：

### Baseline

- L2 logistic regression：继续作为可解释、稳定、与旧结果可比的 baseline。

### Feature-discovery model（可选）

若需要模型内筛选，可增加 regularized logistic，例如 Elastic Net；但其超参数必须在 training data 内选择。

第一轮不建议直接把复杂 tree/boosting 模型作为唯一筛选器，因为：

- 样本独立单位主要是 participant，不是 1400 个彼此独立的 probes；
- 高相关候选特征很多；
- 复杂模型更难区分“真正稳定信息”与有限样本下的偶然组合。

复杂模型可以后置作为敏感性分析。

---

## 7. 什么叫“优秀特征”

禁止只看一次训练的 `Top 10 importance`。

至少同时看：

1. **跨 fold 稳定性**：不同训练参与者子集中是否反复出现；
2. **方向稳定性**：系数/关联方向是否一致；
3. **跨窗口稳定性**：10/20/30 s 是否存在可解释的时间尺度模式；
4. **跨 participant 泛化**：只在少数人上强不算稳定；
5. **缺失/QC 稳定性**：不能由 missingness pattern 偷偷完成分类；
6. **理论可解释性**：feature importance 只能说“有预测信息”，不能直接说“是专注生物标志物”。

推荐输出：

- 每个特征的 fold-selection frequency；
- coefficient sign consistency；
- window stability；
- OOF performance change；
- participant-cluster confidence interval；
- missingness/QC sensitivity。

---

## 8. 第二阶段：回到四分类

四分类目标不是简单追求四分类 accuracy，而是回答四个状态是否具有不同模式。

分析至少包括两条：

### A. 二分类稳定特征子集 → 四分类

回答：

> 第一阶段找到的“Focused vs Other”稳定信号，在四类中到底是谁驱动的？

例如：

- Focus 与 TRI 是否接近；
- MW 是否主要表现为行为波动；
- Blank 是否主要伴随 sleepiness-like ocular pattern。

### B. 完整合格 feature bank → 四分类内部重新筛选

回答：

> 是否存在只对 MW / TRI / Blank 内部区分有价值、但在二分类中被平均掉的特征？

不得因为某特征二分类不强就永久删除。

四分类必须报告：

- 每类样本数 / participant coverage；
- confusion matrix；
- macro/weighted 指标；
- class-specific sensitivity；
- participant-disjoint evaluation；
- 类别不平衡影响；
- 必要时的 pairwise follow-up，但不能用大量事后比较制造显著结果。

---

## 9. Track B：构念验证链

模型发现和科学解释必须分开。

### 第一层：Probe

角色：

> self-reported momentary attentional state

它是核心主观状态测量，不是绝对 ground truth。

### 第二层：Behavior

检验 probe 前行为是否同步变化。

核心关注：

- RT variability / CV；
- error / commission / omission（任务字段允许时）；
- extreme RT / lapse-like responses；
- trial-to-trial fluctuation；
- mean/median RT 作为水平信息。

这里不要求任何单一行为指标完美分类 probe，而要求状态之间存在理论一致、可重复的被试内差异。

Behavior 是 probe 最重要的客观收敛效标之一，但也不能单独定义“专注”。

### 第三层：NIR / mmWave / RGB

问题改为：

> 在 probe + behavior 的基础上，眼动、自主生理和运动信息是否提供方向合理、跨参与者稳定、且不是纯质量伪影的附加证据？

不要求每个模态 AUC 都必须上升。

### 第四层：竞争解释

至少检查：

- time-on-task；
- sleepiness / drowsiness；
- fatigue；
- arousal；
- movement / signal quality；
- task/block condition（若不同）。

---

## 10. 各模态的科学角色

| 数据/指标 | 当前最合理角色 | 不能单独声称什么 |
|---|---|---|
| Thought probe | 核心主观瞬时状态测量 | 绝对客观 ground truth |
| RT variability / CV / error | 核心行为收敛效标 | 行为本身就是“真实专注标签” |
| mean/median RT | 行为辅助信息 | RT 越快/慢就一定越专注 |
| pupil level/dynamics | supporting attention/arousal evidence | 瞳孔大小就是专注度 |
| blink rate | supporting + drowsiness-related evidence | 眨眼多就是不专注 |
| blink duration | fatigue/sleepiness control 为主 | 直接 attention marker |
| PERCLOS | sleepiness/drowsiness control 为主 | 专注指标 |
| HR | autonomic/arousal supporting/control | 心率直接代表专注 |
| respiration | arousal/load supporting/control | 呼吸率直接代表专注 |
| HRV | 当前 beat-level validity 不足，保持 blocked/exploratory | 10–30 s HRV 是正式专注 biomarker |
| mmWave body movement | quality/control + exploratory disengagement | 动得多就一定不专注 |
| RGB head pose | supporting disengagement + quality | 头偏离就是 mind-wandering |
| RGB blink | supporting + 可用于跨传感器一致性 | 独立专注真值 |
| facial/body movement | exploratory / quality | 核心专注证据 |

---

## 11. 为什么必须控制 time-on-task

大规模个体参与者元分析显示，mind-wandering 随任务进行时间增加具有稳定总体趋势。

因此如果不控制时间，可能出现：

`实验越做越久 → 更困/更无聊 → probe Other 增多 → RT 更不稳 → blink/PERCLOS/HR 等一起变化`

然后被错误解释成：

> “这些生理指标是专注特异标志物。”

现有 context variables（例如 block、block probe fraction、onset relative time）必须保留，而且 time-on-task 不是纯 nuisance，也可以作为真实心理过程单独报告。

---

## 12. Sleepiness / fatigue：最小新增测量建议

如果未来还能补采或更新实验协议，不建议堆大量问卷。

### 第一优先：KSS

Karolinska Sleepiness Scale（KSS）用于瞬时困倦评分。

原因不是它“测专注”，而是它可以帮助判断：

> pupil / blink / PERCLOS / HR 等变化究竟是 attentional state，还是 drowsiness。

Stawarczyk et al. (2020) 在 sustained-attention + thought-probe + ocular + sleepiness 设计中发现，mind-wandering 期间的眼动变化可由升高的 sleepiness 解释，而 mind-wandering 与 sleepiness 对行为还存在额外影响。这是本项目必须重视的竞争解释。

### 第二优先（可选）：简短 state fatigue VAS

如果只能再加一个低负担指标，可在 block 后增加单项即时疲劳评分，而不是优先上大量 workload questionnaire。

如果任务难度没有系统操纵，workload 暂时不是最优先新增量表。

### 对现有数据的边界

如果当前历史数据没有 KSS/独立瞬时 sleepiness self-report，则现有 PERCLOS/blink/pupil 可以帮助描述 drowsiness-like pattern，但不能完全替代独立 sleepiness 测量。

这一点属于设计层面的剩余限制，不能靠后处理“彻底补回来”。

---

## 13. 最小充分测量方案

### Momentary attentional state

#### 核心证据

1. **Probe**：Focused / Task-related / Mind-wandering / Blank；主粗粒度 endpoint 可用 `Focused vs Other`，但不把 Other 统一称为 MW。
2. **Behaviour**：RT variability/CV、error、extreme RT、trial-to-trial fluctuation；mean/median RT 为辅助。

#### 支持性证据

3. **NIR**：pupil dynamics、blink rate；同时保留 blink duration / PERCLOS 的 drowsiness 解释。
4. **mmWave**：通过当前 validity gate 的 HR、respiration、movement/quality；HRV 维持当前 blocked 边界。
5. **RGB**：head pose/motion、blink、body/facial motion，以及 tracking quality。

#### 必须控制/检查的竞争解释

1. time-on-task；
2. sleepiness / drowsiness；
3. fatigue（有测量时）；
4. arousal；
5. movement / signal quality；
6. task/block condition。

最终合理表述目标：

> 以 thought probe 锚定即时主观任务聚焦状态，以 probe 前行为建立构念相关的客观收敛证据，并考察眼动、自主生理和运动信息在控制任务进程、困倦/疲劳与质量因素后的多模态一致性和增量信息。

避免表述：

> “系统客观测量了人的专注度”

除非后续区分效度与竞争解释控制达到更高水平。

---

## 14. 目前已有数据距离“我们测量的是专注状态”还缺什么

按优先级：

### P0：立即可做，不需要补采

1. **Probe ↔ Behavior 被试内收敛效度**
   - 四类状态及 `Focused vs Other` 的 10/20/30 s 行为差异；
   - 重点看 RT variability/CV、error、extreme RT；
   - 报告效应量、CI、participant-level consistency，不只报分类准确率。

2. **候选特征合同扩展审计**
   - Behavior 现有动态特征直接复用；
   - NIR/mmWave/RGB 检查 producer 已有哪些 level/variability/trend/event/quality 字段；
   - 缺的特征只在有明确科学语义、输入充分、QC 合格时补。

3. **Focused vs Other 宽特征二分类**
   - 10/20/30 s 分开；
   - participant-disjoint；
   - feature selection 全部 training-only；
   - 简单 logistic baseline + 必要的正则化特征发现。

4. **特征稳定性分析**
   - selection frequency；
   - sign consistency；
   - window consistency；
   - participant robustness；
   - missingness/QC sensitivity。

### P1：紧接着做

5. **四分类结构**
   - binary stable features 重点复核；
   - full qualified bank 在四分类内部重新筛；
   - 明确 TRI / MW / Blank 是否呈不同模式。

6. **time-on-task 控制和状态动态**
   - 复用 block / probe fraction / onset-relative time；
   - 检查控制时间后特征与 probe 的关系是否仍在。

### P2：等 producer/资格成熟后并行接入

7. **NIR / RGB 正式特征 bank**：不能用 provisional/pilot 字段冒充正式 feature。
8. **mmWave**：只使用当前生理资格允许的指标；HRV 不因本次“全特征”策略而绕过现有 blocker。

### 当前无法完全补救的证据缺口

9. **若历史采集没有独立 sleepiness 量表**，则 sleepiness 的区分效度只能部分建立；应在报告 limitation 中明确，并在未来协议优先加 KSS。

---

## 15. 推荐执行顺序和并行关系

```text
A. 复用现有 1400-probe Behavior/cohort/folds
│
├─ A1. Behavior 四类 + 二类构念效度（10/20/30s）
│
├─ A2. 各模态现有 producer/schema/QC 特征盘点
│      └─ 形成 qualified feature bank contract
│
└─ A3. Focused vs Other 二分类 feature discovery
       ├─ 10s
       ├─ 20s
       └─ 30s

A1 与 A2 可以并行；A3 等每个模态 qualified bank 就绪后逐模态接入。

A3 完成
   ↓
B. 稳定特征审计
   ↓
C. 四分类
   ├─ binary stable subset
   └─ full qualified bank reselection
   ↓
D. competing explanations
   ├─ time-on-task
   ├─ sleepiness/fatigue evidence
   ├─ arousal-related interpretation
   └─ movement/QC
   ↓
E. multimodal incremental / final interpretation
```

注意：不需要等所有 producer 全部完成后才做 A1。Behavior + Probe 是当前最完整、最应先闭合的科学骨架。

---

## 16. 与旧分析的关系：哪些保留、哪些改变

### 保留

- `1 vs 2/3/4` 作为粗粒度主 endpoint；
- 10/20/30 s family；
- participant-disjoint validation；
- 现有 Behavior 动态特征；
- L2 logistic baseline；
- time/block context；
- probe、behavior、生理模态的角色分离；
- mmWave 当前 validity boundary。

### 改变/扩展

- 不再把跨模态固定窄 predictor list 当最终 feature space；
- feature discovery 阶段不由研究者只挑“看起来最像 attention”的少数变量；
- 扩展 level + variability + trend + event + quality 的候选表示；
- 加入严格 training-only feature selection；
- 将“稳定性”而非一次性 importance 排名作为优秀特征标准；
- 二分类之后必须回到四分类做 construct differentiation；
- 将 fatigue/sleepiness/arousal/time-on-task 明确作为 competing explanations，而不是把所有生理变化都叫 attention。

---

## 17. 本次文献依据（优先高质量综述/方法/实证）

1. Kane, M. J., Smeekens, B. A., Meier, M. E., Welhaf, M. S., & Phillips, N. E. (2021). Testing the construct validity of competing measurement approaches to probed mind-wandering reports. *Behavior Research Methods, 53*(6), 2372–2411. DOI: `10.3758/s13428-021-01557-x`.
   - 用于：probe 不是绝对 ground truth；需通过行为/跨任务等构念关系验证。

2. Weinstein, Y. (2018). Mind-wandering, how do I measure thee with probes? Let me count the ways. *Behavior Research Methods, 50*(2), 642–661. DOI: `10.3758/s13428-017-0891-9`.
   - 用于：thought-probe 问法和分类高度异质，不能把某一 probe 方案当无误差真值。

3. Seli, P., Cheyne, J. A., & Smilek, D. (2013). Wandering minds and wavering rhythms: Linking mind wandering and behavioral variability. *Journal of Experimental Psychology: Human Perception and Performance, 39*(1), 1–5. DOI: `10.1037/a0030954`.
   - 用于：probe 前较短 trial 范围内 RT variability 与 mind-wandering 的关系。

4. Henríquez, R. A., Chica, A. B., Billeke, P., & Bartolomeo, P. (2016). Fluctuating minds: Spontaneous psychophysical variability during mind-wandering. *PLOS ONE, 11*(2), e0147174. DOI: `10.1371/journal.pone.0147174`.
   - 用于：probe 前短时间尺度行为变化，支持 10/20/30 s sensitivity family。

5. Randall, J. G., Oswald, F. L., & Beier, M. E. (2014). Mind-wandering, cognition, and performance: A theory-driven meta-analysis of attention regulation. *Psychological Bulletin, 140*(6), 1411–1431. DOI: `10.1037/a0037428`.
   - 用于：mind-wandering 总体与较差任务表现相关，但关系受任务条件调节，行为不是完美标签。

6. Zanesco, A. P., Denkova, E., & Jha, A. P. (2025). Mind-wandering increases in frequency over time during task performance: An individual-participant meta-analytic review. *Psychological Bulletin, 151*(2), 217–239. DOI: `10.1037/bul0000424`.
   - 用于：time-on-task 是必须显式建模的竞争/过程变量。

7. Stawarczyk, D., François, C., Wertz, J., & D'Argembeau, A. (2020). Drowsiness or mind-wandering? Fluctuations in ocular parameters during attentional lapses. *Biological Psychology, 156*, 107950. DOI: `10.1016/j.biopsycho.2020.107950`.
   - 用于：ocular changes 可能被 sleepiness 解释；mind-wandering 与 sleepiness 对行为还可能有额外作用；支持加入 KSS/独立困倦控制。

8. Pelagatti, C., Blini, E., & Vannucci, M. (2025). Catching Mind Wandering With Pupillometry: Conceptual and Methodological Challenges. *WIREs Cognitive Science, 16*(1), e1695. DOI: `10.1002/wcs.1695`.
   - 用于：pupil 与 MW 方向不统一；tonic pupil 同时受 arousal/drowsiness/context 影响；固定长窗口可能隐含“状态长期稳定”的不合理假设；支持动态特征和多时间窗分析。

9. Corcoran, A. W., Le Coz, A., Hohwy, J., & Andrillon, T. (2025). When your heart isn’t in it anymore: Cardiac correlates of task disengagement. *Communications Biology, 8*, 1646. DOI: `10.1038/s42003-025-09026-3`.
   - 用于：probe 前短 epoch 的 behavior/pupil/cardiac 联合分析与 time-on-task 建模示例。

---

## 18. 最终方法学立场

本项目下一阶段不采用两种极端路线：

### 不采用纯人工挑特征

错误方式：

> 文献说 RT-CV、pupil 有意义 → 只给模型这几个 → 再证明它们重要。

这样容易把理论预期变成模型输入限制。

### 也不采用无边界“特征大杂烩”

错误方式：

> 数学上能算的都算 → 全部塞进去 → importance 高就叫 attention marker。

这样会混入不可靠指标、时间窗不成立的指标、QC 伪影和竞争解释。

### 正式采用

> **宽但有资格门的候选特征空间 + participant-disjoint、training-only 的特征发现 + 二分类粗筛 + 四分类构念分化 + 独立的 probe/behavior/physiology 收敛与区分效度链。**

这是本次 2026-09-09 方法更新的 canonical 决策。
