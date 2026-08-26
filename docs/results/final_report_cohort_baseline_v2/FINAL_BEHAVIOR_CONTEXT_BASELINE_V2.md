# FINAL_BEHAVIOR_CONTEXT_BASELINE_V2

状态：`CANONICAL_BEIJING_REPORT_BASELINE`

Producer：`scripts/run_final_report_cohort_baseline_v2.py`，branch `codex/final-report-cohort-baseline-v2`，commit `414a4f46c8d058961a87750345d06a7129afc9f2`。

## Contract

- cohort：70 sessions / 46 natural participants / 1,400 probes；旧 72/1,440 fallback 未使用；
- endpoint：label 1（fully task-focused）vs labels 2/3/4（other non-fully-task-focused）；label 3=task-unrelated thought，label 4=mind blank；
- primary window：30 s；sensitivity：10 s、20 s；
- model：L2 logistic；5-fold StratifiedGroupKFold，group=`repeat_participant_id`；imputation/scaling/model fit only in training fold；
- uncertainty：participant-cluster bootstrap, 1,000 replicates；seed=`20260826`。

## Aggregate results

30 s primary: `C_context_only` ROC-AUC 0.593 [0.548, 0.638]，`B_behavior_only` 0.639 [0.575, 0.708]，`C_plus_B` 0.675 [0.621, 0.726]。PR-AUC 分别为 0.338 [0.247, 0.439]、0.367 [0.288, 0.480]、0.393 [0.309, 0.504]。完整 10/20/30 s 指标见同目录 aggregate CSV。

这些结果是北京 canonical baseline 和 sensor increment 的比较锚点，不是 global Beijing+Zhuhai inference，也不证明传感器具有跨站点泛化能力。
