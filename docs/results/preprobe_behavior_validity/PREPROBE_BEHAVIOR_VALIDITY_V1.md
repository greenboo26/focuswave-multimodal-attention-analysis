# Probe-before behavior validity v1

状态：`CANONICAL_BEIJING_VALIDITY_SUPPORTING`

Producer：`scripts/run_beijing_preprobe_state_comparison_v1.py`，当前 canonical branch commit `da4b7b5` 中存在；upstream RUN_ID=`BEIJING_PREPROBE_STATE_COMPARISON_V1`。

## Frozen method

70 Beijing valid sessions、46 participants、1,400 probes。比较 label 1（fully task-focused）与 labels 2/3/4（other non-fully-task-focused）前 10/20/30 s 的 error rate、RT median 和 RT SD。模型为 participant-clustered Gaussian GEE、exchangeable working correlation，调整 `probe_progress + block_num`。18 个 planned contrasts（3 windows × 3 outcomes × 2 adjusted/unadjusted families）使用 Benjamini–Hochberg（BH）校正；主报告使用调整模型。

## Aggregate adjusted contrasts

效应为“fully task-focused − other non-fully-task-focused”。错误率：10 s β=-0.0342 [−0.0460, −0.0225]，q<.001；20 s β=-0.0359 [−0.0435, −0.0282]，q<.001；30 s β=-0.0325 [−0.0397, −0.0253]，q<.001。RT median 的 BH q 为 .934/.955/.878，RT SD 的 BH q 为 .221/.341/.462（10/20/30 s）。

## Boundary and outputs

这是 Probe 状态与其前方行为的事件前关联，不是因果效应，也不把 2/3/4 解释为同一种 mind-wandering。脱敏 aggregate CSV、完整本地 report 和 manifest 保留在对应 `derived` 目录；Git 不含 row-level data。
