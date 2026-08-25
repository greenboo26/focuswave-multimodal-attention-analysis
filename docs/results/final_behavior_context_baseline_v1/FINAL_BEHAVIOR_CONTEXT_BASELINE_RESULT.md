# FINAL_BEHAVIOR_CONTEXT_BASELINE_V1

状态：`COMPLETE`

## 冻结定义

- Cohort source: `C2a_frozen_Beijing_canonical_fallback`。`REPORT_ANALYSIS_COHORT` 未找到时，按预注册回退使用 C2a 北京 canonical cohort，且已验证为 1,440 probes / 72 sessions / 46 repeat-participant groups。
- 标签：label 1 = 完全任务聚焦；label 2/3/4 = 其他非完全任务聚焦。阳性类是后者，不等同于全部走神。
- 主窗口为 probe 前 30 s `[onset-30 s, onset)`；10 s、20 s 为预先规定敏感性，绝不用于选择主窗口。
- 分割：固定 5-fold StratifiedGroupKFold，所有同一 repeat-participant 的 session 保持在同一 fold；填补、标准化、L2 logistic 均仅在训练 fold 拟合。

## 30 s 主结果

| Set | ROC-AUC (95% CI) | PR-AUC (95% CI) | Balanced accuracy | Sensitivity | Specificity | TN/FP/FN/TP |
|---|---:|---:|---:|---:|---:|---:|
| C_context_only | 0.596 [0.549, 0.645] | 0.341 [0.260, 0.442] | 0.575 | 0.577 | 0.573 | 610/454/159/217 |
| B_behavior_only | 0.654 [0.590, 0.715] | 0.372 [0.288, 0.479] | 0.628 | 0.612 | 0.645 | 686/378/146/230 |
| C_plus_B | 0.687 [0.638, 0.736] | 0.396 [0.311, 0.498] | 0.640 | 0.617 | 0.664 | 706/358/144/232 |

CI 为 participant-cluster bootstrap（1,000 次）。`calibration_table.csv` 与 PNG 图提供简单 10-bin OOF 校准检查。

## 预先规定敏感性

| Window | Set | ROC-AUC | PR-AUC | Balanced accuracy |
|---:|---|---:|---:|---:|
| 10 s | C_context_only | 0.596 | 0.341 | 0.575 |
| 10 s | B_behavior_only | 0.560 | 0.309 | 0.584 |
| 10 s | C_plus_B | 0.638 | 0.355 | 0.610 |
| 20 s | C_context_only | 0.596 | 0.341 | 0.575 |
| 20 s | B_behavior_only | 0.633 | 0.360 | 0.617 |
| 20 s | C_plus_B | 0.677 | 0.390 | 0.617 |

这些为预先规定敏感性，不改变 30 s 主结论。

## Probe 前错误率模型

30 s trial-level error 的随机截距 logistic mixed model：β = 0.634, OR = 1.885, 95% CI OR [1.738, 2.045], p < .001。
它只检验状态关联，不构成因果解释；RT 若无稳定证据不应被过度解释。

## 限制

- `REPORT_ANALYSIS_COHORT` 在本次运行时不存在，故记录为受验证的 C2a 北京 canonical fallback，未拼接任何 1,317/1,400/1,420 口径。
- 这是行为/context 基线，不是传感器或多模态模型，也不能推断 RGB/NIR 的增量。
- 二分类合并保留 label 2/3/4 的构念异质性，不能将其统称为走神。
