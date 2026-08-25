# C2b task-focus baselines

状态：`C2B_TASK_FOCUS_BASELINES_COMPLETE_WITH_WINDOW_BLOCKERS`

本轮执行了冻结的 30 s 主分析。正类为 `probe_response ∈ {2,3,4}`，即 non-fully-task-focused；负类为 `probe_response=1`，即 fully task-focused。未使用 RGB、NIR、IBI、RMSSD、SDNN 或深度模型。

## 数据与验证

实际可复用的 M1/Q0 特征矩阵包含 1,317 个 probe、71 个 session 和 46 个 `group_subject_id`。因此本轮不是 C2a 全部 1,440 probe 的完整复现。使用 5-fold `StratifiedGroupKFold`，同一重复被试的 session 不跨 fold。填补、标准化和模型拟合均在训练 fold 内完成。

## 30 s 主结果

| 特征组 | 模型 | PR-AUC | ROC-AUC | Balanced accuracy | F1 | Recall | Specificity | MCC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| M0 context-only | L2 logistic | .421 | .642 | .614 | .448 | .563 | .665 | .205 |
| M1 behavior-only | L2 logistic | .440 | .680 | .641 | .480 | .603 | .679 | .253 |
| M2 mmWave-basic | L2 logistic | .388 | .629 | .602 | .436 | .566 | .639 | .182 |
| M3 mmWave-extended | L2 logistic | .357 | .607 | .588 | .420 | .545 | .630 | .156 |
| M4 behavior + mmWave | L2 logistic | .392 | .643 | .613 | .449 | .586 | .640 | .201 |

在当前可复用矩阵和固定分组下，M2/M3 没有超过 M0 或 M1；M4 的 ROC-AUC 比 M1 低约 .037，尚未显示毫米波在行为之外的稳定增量价值。该结果是基线结果，不是“毫米波无效”的普遍结论。

树模型和 prevalence dummy 的完整结果见 `c2b_model_metrics.csv`。Accuracy 不作为主成功指标，因为正类比例约为 26.0%，多数类预测会产生误导性的高 accuracy。

## 窗口敏感性限制

30 s 是主窗口。现有本地资产没有与其同一 schema 的 10 s 和 60 s 特征矩阵，因此 `c2b_window_sensitivity.csv` 将 10 s/60 s 标为 `not_available`；本轮没有根据测试结果选择窗口，也没有假装完成敏感性分析。下一步如果要补齐，必须从同一冻结 pipeline 生成等价的 10 s/60 s 特征后再跑。

## 产物与隐私边界

本地输出目录：

`D:\Project\厚粲杯\11_数据\derived\c2b_task_focus_baselines_v1\`

包含模型指标、OOF predictions、fold assignments、feature schema、matched subset、window sensitivity、feature importance 和 manifest。OOF predictions、fold assignments 和任何行级数据只保留本地，不上传 GitHub。

本阶段完成 30 s 基线后停止，不自动进入 RGB/NIR 或全模态，也不自动冻结 C2b 的最终窗口和复杂模型方案。
