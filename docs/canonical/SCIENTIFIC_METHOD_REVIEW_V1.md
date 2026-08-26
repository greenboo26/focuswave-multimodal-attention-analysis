# FocusWave 现有分析科学方法终审 V1

状态：`SCIENTIFIC_METHOD_REVIEWED / TEAMMATE_HANDOFF_WITH_BOUNDARIES`

日期：2026-08-27

本文件是当前比赛版统一分析管线在交给第二台机器复现前的科学/统计终审。终审对象是 `configs/canonical/local_analysis_registry_v1.json` 登记的既有分析及其当前 producer。目的不是重新探索模型，而是确认：分析问题是否与代码一致、重复被试是否被正确处理、交叉验证是否存在明显泄漏、窗口/标签/统计检验是否合理，以及哪些结果可以作为正式主分析、哪些只能作为 supporting/diagnostic。

## 总结裁决

当前分析框架**可以继续用于比赛和同事复现，不需要推翻重做**。没有发现会使行为主分析、问卷效标分析或毫米波增量检验整体失效的结构性统计错误。

但“方法可用”不等于“所有登记分析都是同等强度的主结果”。必须遵守以下边界：

1. `label 1 vs labels 2/3/4` 的二分类只能称为“完全任务聚焦 vs 其他非完全任务聚焦”，不得称为“专注 vs 走神”。label 2 是关注实验但未聚焦分拣，label 4 是思维空白。
2. 行为 `behavior_baseline_v2` 是当前最适合做预测锚点的主分析：repeat-participant-disjoint 5-fold、训练 fold 内 imputation/scaling、固定 L2 logistic、participant-cluster bootstrap，方法合理。
3. 行为纵向和 Probe 前状态比较使用 participant-clustered GEE，重复 participant 没有被当成独立样本；10/20/30 s 为预先固定窗口，BH-FDR 已处理预定义检验族，方法合理。
4. Q1 是单题场次级 criterion/convergent validity 支持，不是已验证量表。重复 participant 通过 cluster bootstrap / cluster-robust covariance 处理；不能因为单题相关显著就称为完整量表效度，也不能把阴性结果写成“问卷无效”。
5. mmWave C2B/C2C 的价值是检验“在行为/context 基线之外是否有稳定增量”。它们目前应按 validation/ablation 解释；不能因为某一个窗口或某一个模型偶然较高就改成正向毫米波主结论。
6. C1 alignment、M1 raw mmWave audit、repeat-session effect 和旧 sensor increment 必须保持 supporting/diagnostic 身份，不得升级为比赛主预测证据。
7. 不允许在看到同事数据结果后重新选择标签、窗口、fold、特征、模型或阈值。跨机器数值不要求相同，但科学签名必须相同。

## 逐分析终审

| analysis_id | 裁决 | 可否交给同事按同一方法执行 | 解释边界 |
|---|---|---|---|
| `report_cohort_v1` | `A / canonical cohort` | 可以，在对应 site 已完成 canonical identity/timeline mapping 后 | cohort/标签语义为正式入口；其中 vigilance/label 关联模型是描述与支持，不是预测主终点 |
| `behavior_longitudinal_v1` | `A / handoff-ready` | 可以，但其他 site 不能硬套北京 1400/70/46 数量 | participant-clustered GEE；主要解释时间/Block/行为轨迹，不作传感器因果推断 |
| `behavior_preprobe_v1` | `A / handoff-ready supporting` | 可以 | Gaussian GEE 比较 Probe 前行为；18 个预定义 adjusted/unadjusted tests 用 BH-FDR；状态名必须是“完全任务聚焦 vs 其他非完全任务聚焦” |
| `behavior_baseline_v2` | `A / primary handoff-ready` | 可以，在输入映射和 participant identity 正确后 | 当前行为/context 预测锚点；30 s 主窗口，10/20 s 敏感性；不能从敏感性窗口反向选主窗口 |
| `repeat_session_v1` | `B / supporting only` | 可以作为支持分析 | 随机截距处理重复 participant 的思路正确；二元 mixed model 使用 variational Bayes，其 CI/normal-tail p 是近似推断，因此不能作为唯一决定性显著性证据 |
| `questionnaire_q1_v1` | `A / criterion-supporting handoff-ready` | 可以，在问卷字段和 participant bridge 对齐后 | 单题不是量表；ordinal logit + participant-cluster robust SE、Spearman + participant-cluster bootstrap 合理；重点关注效应量/CI与方向一致性 |
| `mmwave_c1_alignment_v1` | `C / diagnostic boundary` | 一般不需要同事复现，除非其机器有同类 ECG/radar timestamp validation 资产 | 仅诊断常数延迟假设；使用 ECG 作诊断 lag reference，不是正式 HRV 结果；不授权重开 HRV 开发 |
| `mmwave_m1_v1` | `B / supporting raw-mmWave audit` | 有对应原始毫米波与协议时可执行 | 30 s LOSO、训练 fold 内 preprocessing、固定未调参 L2 logistic 合理；raw phase/spectral peak 是信号描述，不是经验证 HR/BR/HRV |
| `mmwave_c2b_v2` | `A- / formal increment test with negative/ablation interpretation` | 有对应毫米波数据且 site/protocol adapter 审核通过后可以 | 5-fold repeat/group-subject-disjoint；30 s 主、10/60 s 敏感性；C+B 与 C+B+W 必须在可比 matched cohort 上比较；多个 classifier 不得用于事后 cherry-pick，复杂模型只能作为预定义 secondary/sensitivity |
| `mmwave_c2c_v1` | `B+ / supporting personalization test` | 有有效 180 s baseline 且协议兼容时可以 | 每 session 静息段 median/MAD normalization 不使用标签，思路合理；比较必须在 common calibration cohort 和相同 grouped folds 上进行；未覆盖 session 不可被插值为“有校准” |
| `beijing_sensor_increment_v1` | `B / existing supporting integration` | 不作为新 site 的首选主分析；有兼容派生输入时可作为历史支持复现 | LOSO/repeat-participant grouping 合理，但它依赖既有北京 NIR/mmWave派生表和旧 crosswalk；无 paired CI 的 delta AUC 不应被当作决定性增量证据 |

其中 A/A- 表示可以进入标准交付；B/B+ 表示方法可保留但只能做 supporting；C 表示诊断边界，不属于同事必须复现的比赛主链。

## 关键方法核验

### 1. 重复被试

当前主分析没有把同一 natural participant 的重复 session 当作完全独立的人：

- 行为纵向/Probe 前比较：GEE `groups=repeat_participant_id`；
- 行为预测：`StratifiedGroupKFold` 以 `repeat_participant_id` 分组；
- repeat-session：participant random intercept；
- Q1：participant-cluster bootstrap / cluster-robust covariance；
- mmWave C2B/C2C：`group_subject_id` 分组，保持同一重复 participant 不跨 train/test；
- M1：LOSO。

这是本项目最重要的防伪重复措施，方法正确。同事 site 的 identity map 若尚未中央确认，则先解决 identity/bridge，不允许用 session ID 假装 participant ID。

### 2. 预测泄漏

`behavior_baseline_v2` 的 imputation、scaling 和 logistic fitting 在每个 training fold 内完成；test participant 不参与这些拟合。C2B/C2C 同样在 grouped folds 内拟合 preprocessing/model。当前没有发现把同一个重复 participant 同时放进 train/test 的明显泄漏。

毫米波逐窗口 target/range selection 使用该窗口自身的无标签信号质量，不读取 Probe label；这属于 sample-wise signal feature extraction，不构成 label leakage。但不得未来根据 outcome 表现修改选择规则。

### 3. 标签问题

`target = label != 1` 本身可以用于“完全任务聚焦 vs 非完全任务聚焦”检测，且比赛上有可解释性；问题只在命名。必须永久保留：

- 1 = 完全任务聚焦；
- 2 = 关注实验本身，但没有聚焦分拣任务；
- 3 = 与实验/任务无关思维；
- 4 = 思维空白。

因此 2/3/4 的合并不是纯 `mind-wandering` outcome。若未来要回答“真正走神（label 3）能否检测”，那是新的分析问题，需要新版本，而不是偷偷改当前 target。

### 4. 窗口与多重比较

行为 30 s 主分析 + 10/20 s sensitivity、毫米波 30 s 主分析 + 10/60 s sensitivity 的冻结策略是合理的，可以避免看到结果后选最好窗口。GEE/问卷的预定义检验族使用 BH-FDR；该做法适合当前比赛规模的探索/验证性质。

不能把不同 family 的大量临时检验全部混成新的“显著性搜索”，也不能只报告 sensitivity 中最好看的一个窗口。

### 5. Bootstrap 与置信区间

行为 baseline、Q1、C2C 使用 participant-cluster resampling，而不是逐 Probe 独立抽样，这与重复测量结构匹配。paired model increment 比较也应继续在同一个 common OOF cohort 上、按 participant cluster 做 paired resampling。

对于只有点估计、没有 paired uncertainty 的历史 sensor increment，保留为 supporting，不升级结论即可，无需为了比赛重做整套历史管线。

### 6. 模型复杂度

比赛当前样本量不适合不断调复杂模型。固定 L2 logistic 作为主要锚点是合理选择：可解释、方差较低，并且已经在 grouped CV 中验证。C2B 中存在 dummy/logistic/HGB 等预定义比较时，不允许事后根据最高 AUC 宣布“最佳模型”；复杂模型仅用于 secondary/sensitivity，正式结论优先看冻结基线与 paired increment。

## 对同事交付的最终规则

同事最终使用的是当前中央仓库 `main` 的已审查科学定义，而不是创建一套“同事专用科学分支”。必要代码适配从 `main` 开临时 task branch，经过 review 后回到 `main`。

同事必须复现的是**方法和科学签名**，不是北京数值。其他 site 可以有不同 participant/session 数量；不能把北京 1400 probes、70 sessions、46 participants 当作另一 site 的硬性 expected count。

如果外部 `Attention-Analysis` 当前 NIR config 与实际 site/protocol 不兼容，必须先建立并审查 protocol adapter/config。运行成功但协议错误的结果视为无效。

## 最终可写进比赛报告的强度

可以作为主线：

- canonical cohort/Probe semantics；
- 行为纵向模式；
- behavior/context grouped-CV baseline；
- Q1 作为单题 criterion/convergent-supporting evidence；
- mmWave C2B 作为“是否提供行为之外增量”的正式检验，按实际结果如实报告。

只能作为支持/边界：

- repeat-session practice effect；
- C1 alignment；
- M1 person-effect/raw-mmWave audit；
- C2C within-person calibration；
- legacy Beijing sensor increment。

若毫米波没有稳定增量，正确结论是“在当前冻结方法和样本上，没有证据支持其稳定超越行为/context 基线”，而不是改算法直到得到正结果，也不是宣称毫米波硬件无效。

## 终审结论

`PASS WITH ROLE BOUNDARIES`。

当前现有分析思路和主要统计方法总体合理，足以继续比赛与第二台机器标准化复现。当前需要管理的是**角色和解释强度**，不是重新设计整套分析。任何后续科学改动必须新建 pipeline/version 并重新 review，不得静默修改本 V1。