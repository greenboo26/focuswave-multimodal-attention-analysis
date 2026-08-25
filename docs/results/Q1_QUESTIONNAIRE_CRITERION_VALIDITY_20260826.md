# Q1 问卷单题的外部效标关联

## 结果

本分析只使用既有派生审计、确定性问卷—场次桥接和 canonical probe/行为汇总，未读取原始问卷、trial 或 C2C/C3 预测分数。可实际建模的是正式版第 4 题：“整个实验过程中，你走神（想与任务无关的事情）的时间大概占多少”。该题为自编、4 级比例类别的场次级状态候选，方向为走神比例越高表示主观注意越差；审计的两个正式答卷导出合计 134 行，该题加权缺失率为 0.0%。

最终主分析纳入北京 canonical 主场次的 67 场次、46 个 participant/group_subject_id。问卷类别为 <10%（23）、10–30%（35）、30–50%（9）和 >50%（0），因此未把类别当连续分数。重复 participant 使用 participant-cluster robust covariance；补充关联采用 participant-cluster bootstrap（5,000 次，种子 20260826）95% CI。BH 校正只覆盖预定义的 7 个单变量 probe/行为关联和 3 个有序模型斜率。

- 自评走神越高，与更高的非完全任务聚焦比例（label 2/3/4 的合并，不称为“全部走神”）相关：ordinal logit OR/1 SD = 4.01，95% CI [2.10, 7.66]，p_BH = .00008。
- 与 label 1 完全任务聚焦比例的 Spearman rho = −.581，participant-cluster bootstrap 95% CI [−.735, −.409]，p_BH = .000002。
- label 2 任务相关干扰、label 3 大脑空白和 label 4 走神的单变量关联分别为 rho = .534、.362、.330；其 95% CI 均不跨 0，p_BH 分别为 .00001、.0060、.0111。
- commission error rate 与自评走神的单变量关联为 rho = .260，95% CI [.014, .494]，p_BH = .0475。联合 ordinal 行为模型中，commission error OR/1 SD = 1.79，95% CI [1.12, 2.85]，p_BH = .0140。
- 中位 RT 的边际关联不精确（rho = −.068，95% CI [−.351, .196]，p_BH = .582），但在 error 调整后的联合 ordinal 模型中条件 OR/1 SD = 1.74，95% CI [1.27, 2.39]，p_BH = .0008。由于该方向与边际关联不一致，作为协变量条件下、模型依赖的探索性结果，不单独作强结论。

## 解释边界

probe 一致性构成 convergent/criterion-supportive evidence，不能验证逐窗口状态标签。错误率结果提供较弱的行为效标支持；预按率与中位 RT 的边际结果为 weak/no precise association，不可写作问卷无效。既有 canonical 行为汇总没有 session 级 RT variability，因此没有重提取 trial 来补造该指标。审计中另外列出的 trait-like 两题（自评专注力、日常持续专注时长）没有可复用的确定性数值桥接字段，属于不可解释/未分析而不是阴性结果。

行级 manifest 和含 pseudonymous session/participant ID 的数据仅保留在本地 `D:\Project\厚粲杯\11_数据\derived\questionnaire_criterion_validity_v1`，不进入 Git。聚合 CSV 和图候选见本目录同级文件。
