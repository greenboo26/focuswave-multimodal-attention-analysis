# 北京正式行为纵向分析结果交接

**RUN_ID：** `BEIJING_FORMAL_BEHAVIOR_LONGITUDINAL_V1_20260825`
**状态：** `completed_behavior_only_formal_subset`
**执行 commit：** `cea8f36`
**入口：** `scripts/run_beijing_longitudinal_event_analysis_v1.py`

## 输入与复用资产

- 北京 deterministic join：`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\deterministic_join.csv`
- C2 身份主表：`D:\Project\厚粲杯\11_数据\derived\analysis_tables_v2\subject_session_master_v2.csv`
- BB Probe mapping：`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\bb_probe_mapping_once.csv`
- 冻结设计：`D:\Project\厚粲杯\11_数据\derived\longitudinal_event_analysis_v2_design\design_report.md`

没有重新恢复 participant identity，没有重新计算 C2 模型，没有使用毫米波、NIR、ECG 或 RSP。

## 样本与结果文件

- `PASS_FORMAL` sessions：70
- 重复参与者：46
- trial：59,080
- Probe：1,400
- Probe 前行为窗口：10 s、20 s、30 s

结果目录：

`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1\`

具体文件：`report.md`、`model_results.csv`、`descriptives.csv`、`fig_error_trajectory.png`、`fig_preprobe_error_trajectory.png`、`trial_level_behavior.csv`、`probe_event_level_behavior.csv`、`run_manifest.json`。

## 首轮统计结果

使用按 `repeat_participant_id` 聚类的广义估计方程（GEE），而不是把每条 trial 当作完全独立观测。

1. Trial error 随 block 内进度上升：beta = 0.251，95% CI [0.027, 0.474]，原始 *p* = .028。该结果提示任务推进过程中错误率有增加迹象。
2. log RT 的 block 内进度效应不明显：beta = -0.015，95% CI [-0.084, 0.054]，原始 *p* = .669。
3. `probe_response=1` 的概率随 block 内进度下降：beta = -0.893，95% CI [-1.501, -0.284]，原始 *p* = .004，优势比约为 0.41。
4. B1/B2 与进度的交互项均未见明显证据。

`probe_response=1` 与 `probe_response=2/3/4` 保持代码中性命名，不能直接写成“专注 vs 走神”。

## 解释边界

这是北京 70 个可审计 session 的首轮行为纵向结果，不是生理机制证明，也不能外推珠海。错误率随时间上升与 Probe response=1 下降是同一时间结构下的行为现象，尚不能声称因果疲劳或已经解释了注意状态变化。正式报告还应结合缺失模式、模型诊断、planned contrasts 和 BH-FDR 校正列进行最终呈现。

## 请求 GPT 裁决

1. 是否将这组结果作为报告中的第一批正式行为结果？
2. 是否批准下一步在同一 70-session 时间轴上加入已完成的 Probe 前 10/20/30 s 行为轨迹图和 B1→休息→B2 恢复对比？
3. 在不改标签和窗口的前提下，哪些结果进入正文，哪些放入探索性/补充材料？
