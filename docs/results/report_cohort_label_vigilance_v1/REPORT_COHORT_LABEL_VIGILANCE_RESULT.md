# REPORT_COHORT_LABEL_VIGILANCE_V1

状态：`COMPLETE_BEHAVIOR_ONLY`

## 唯一母表口径

`REPORT_ANALYSIS_COHORT` 是本报告主线唯一行级母表，仅存于本地 derived 目录。它复用既有北京 deterministic identity/session/timeline/probe/behavior 资产，包含 46 名自然人、70 个正式 session 和 1,400 个有效 probe。每个 session 有 20 probe，B1/B2 各 10 probe。

C2a canonical manifest 的 72 sessions、1,440 probe 是输入宇宙；其中 sub-099 的 20 probes 因 C2 session 没有有效 timeline 被排除。另有 sub-067 具有有效 timeline 但不在 C2 universe，故不计入 1,440，也不作为 missing。这样主表为 70/1,400。第 4 次 session 的 20 probes 完整保留。其他硬盘数据均为“暂未纳入本报告主线”，不是 missing。

## 模型与样本

四分类状态使用以参与者聚类的 one-vs-rest logistic GEE；vigilance 使用以参与者聚类的 cumulative-logit ordinal GEE；probe 前 10 s 错误率使用按可用试次数加权的 binomial GEE，RT 中位数使用 log-RT Gaussian GEE。模型均调整 block、block 内 probe progress，状态–vigilance 关系模型也调整这两个时间变量。效应为每 1.0 block-progress 或每 1 点 vigilance 的 OR/百分比变化；每个拟合使用 1,400 probes、46 人，RT/错误率的实际覆盖见模型表。全部计划项在本轮 BH-FDR 校正。

## 主要结果

- label 1（fully task-focused）随 block 内 progress 下降：OR=0.43, 95% CI [0.25, 0.74], p=0.00253, q=0.00722。其余三类状态的完整结果见模型表，不能将 labels 2/3/4 统称为 mind-wandering。
- vigilance 随 progress 的 ordinal 变化：OR=0.26, 95% CI [0.14, 0.47], p=9.62e-06, q=6.42e-05。
- 相比 label 1，label 2 对应的更高 vigilance 优势：OR=0.44, 95% CI [0.32, 0.61], p=5.61e-07, q=5.61e-06；label 3：OR=0.46, 95% CI [0.31, 0.68], p=0.000109, q=0.000365；label 4：OR=0.21, 95% CI [0.12, 0.35], p=2.73e-09, q=5.45e-08。
- 每增加 1 点 vigilance，probe 前 10 s 错误率的方向：OR=0.68, 95% CI [0.56, 0.83], p=9.88e-05, q=0.000365；RT 中位数的比例变化：change=-4.00%, 95% CI [-8.53%, 0.76%], p=0.0983, q=0.179。

## 限制

这是北京已链接正式行为 cohort 的关联分析，不推断因果或生理机制，不外推珠海。GEE 处理 participant 内相关但不是 subject-specific random-intercept effect；状态轨迹为四个二元边际模型，故不是单一多项式模型。probe 前 10 s 行为窗是既有派生指标。

## 产物

- `report_analysis_cohort.csv`：本地行级母表，含 pseudonymous participant/session key，禁止上传。
- `label_vigilance_summary.csv`：本地脱敏汇总。
- `label_vigilance_models.csv`：本地脱敏模型结果。
- Git version includes this runnable script, field schema, this methods/result report, and two aggregate figures only.
