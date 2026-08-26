# FINAL_BEHAVIOR_CONTEXT_BASELINE_V2

状态：`FINAL_REPORT_COHORT_BASELINE_V2`

本报告严格复用 V1 方法，仅将 cohort 更换为已冻结的 REPORT_ANALYSIS_COHORT。
标签为 1 vs 2/3/4，阳性类为 2/3/4；主窗口 30 s，敏感性窗口 10 s/20 s；模型为 L2 logistic。
验证为一次固定的 5-fold StratifiedGroupKFold，分组单位为 repeat_participant_id；所有 imputation、scaling 和模型拟合仅在 training fold。

cohort：1400 probes / 70 sessions / 46 participants。

## 30 s 主结果

| Set | ROC-AUC | PR-AUC | balanced accuracy | sensitivity | specificity | confusion matrix |
|---|---:|---:|---:|---:|---:|---|
| C_context_only | 0.593 [0.548, 0.638] | 0.338 [0.247, 0.439] | 0.568 [0.532, 0.602] | 0.564 [0.510, 0.616] | 0.572 [0.553, 0.593] | 594/444/158/204 |
| B_behavior_only | 0.639 [0.575, 0.708] | 0.367 [0.288, 0.480] | 0.620 [0.571, 0.669] | 0.602 [0.500, 0.707] | 0.639 [0.570, 0.700] | 663/375/144/218 |
| C_plus_B | 0.675 [0.621, 0.726] | 0.393 [0.309, 0.504] | 0.640 [0.603, 0.678] | 0.613 [0.541, 0.694] | 0.667 [0.611, 0.720] | 692/346/140/222 |

CI 为 participant-cluster bootstrap 95% CI（1,000 次）。Calibration 表按 OOF prediction 的 10 个 probability bins 保存。

## 敏感性窗口

| Window | Set | ROC-AUC | PR-AUC | balanced accuracy |
|---:|---|---:|---:|---:|
| 10 s | C_context_only | 0.593 | 0.338 | 0.568 |
| 10 s | B_behavior_only | 0.568 | 0.310 | 0.584 |
| 10 s | C_plus_B | 0.637 | 0.351 | 0.615 |
| 20 s | C_context_only | 0.593 | 0.338 | 0.568 |
| 20 s | B_behavior_only | 0.624 | 0.355 | 0.615 |
| 20 s | C_plus_B | 0.672 | 0.390 | 0.623 |

## Frozen outputs

- `REPORT_FOLDS_V1.csv`：46 个 repeat_participant_id 的固定五折分配。
- 后续 NIR、RGB、multimodal 模型必须复用该 participant-level assignment；不得重新按模态抽样或重新生成 folds。
- 本版本废止旧 `FINAL_BEHAVIOR_CONTEXT_BASELINE_V1` 的 1,440-probe C2a fallback。

## 未重跑既有报告

`REPORT_COHORT_LABEL_VIGILANCE_V1` 与 `REPORT_REPEAT_SESSION_EFFECTS_V1` 已通过既有 manifest 核对为 1,400 probes / 70 sessions / 46 participants；本任务未重跑。
