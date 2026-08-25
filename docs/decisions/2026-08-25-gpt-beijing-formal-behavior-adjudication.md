# GPT 裁决：北京第一批正式行为纵向结果

日期：2026-08-25
依据：`docs/decisions/2026-08-25-beijing-formal-behavior-results-handoff.md`
状态：`ACCEPTED_AS_FIRST_FORMAL_BEHAVIOR_RESULT_SET / FINAL_REPORT_WORDING_PENDING_CORRECTION`

## 1. 总裁决

接受本轮作为北京 70 个可审计 session、46 个重复参与者的第一批正式行为纵向模型结果。此次不再属于审计或预检，而是已经产生实际科研结果。

本轮仅使用行为数据，未混入毫米波、近红外、ECG 或 RSP；重复参与者通过按 `repeat_participant_id` 聚类的广义估计方程（generalized estimating equations [GEE]）处理，没有把同一人的多次 session 当成独立被试。该处理方向可接受。

但当前 handoff 报告的是原始 *p* 值，因此“进入结果章节”与“最终显著性措辞”需分两步：先完成既定的 Benjamini–Hochberg 错误发现率（false discovery rate [FDR]）/计划比较校正、模型诊断和缺失模式检查，再冻结最终报告表述。

## 2. 当前可以写的结果

### 2.1 Probe response=1 随 block 内进度下降

当前估计：β = -0.893，95% CI [-1.501, -0.284]，原始 *p* = .004，优势比约 0.41。

该结果可以作为当前最明确的主发现进入结果候选。由于北京 BB mapping 已经作为本轮 `PASS_FORMAL` 的组成部分通过，最终报告在确认该映射文件确实对应同一固定 probe-response 语义后，可使用“完全任务聚焦（probe response 1）概率随 block 内进度下降”的表述；不得把 2/3/4 统称为“走神”。

### 2.2 Trial error 随 block 内进度上升

当前估计：β = 0.251，95% CI [0.027, 0.474]，原始 *p* = .028。

该结果目前写为“错误率随任务推进增加的初步证据/趋势”。是否升级为最终正式显著结果，取决于既定多重比较校正后的 *p* 值以及模型诊断。

### 2.3 log RT 未见明显时间趋势

β = -0.015，95% CI [-0.084, 0.054]，原始 *p* = .669。

这是有信息量的阴性结果：当前变化更明显地体现在错误和 probe response，而不是平均反应时水平。不得把“不显著”解释为“反应时完全不受时间影响”，后续仍需看反应时变异性和 probe 前短时轨迹。

### 2.4 B1/B2 × 进度交互未见明显证据

当前只能说：没有证据表明 B1 与 B2 的 block 内时间斜率不同。不能据此说“休息没有作用”，因为恢复问题应由 B1 末端 → 休息 → B2 起始的计划比较直接检验，而不是只依赖整体交互项。

## 3. 现在最应该做的下一步

不新增 gate，不重新恢复身份，不重跑 C2。

下一轮直接完成同一 70-session 数据上的两组已冻结分析：

1. **Probe 前 10/20/30 秒行为轨迹**：error、reaction time、reaction-time variability，必要时 commission/omission；三种窗口全部报告，不挑最好看的窗口。
2. **B1 末端 → 休息 → B2 起始恢复比较**：至少报告 probe response 1、error、RT/RT variability 的计划比较与 95% CI。

在上述两组完成后，才把毫米波和 NIR 挂到同一时间轴，避免再次用传感器模型替代实验设计分析。

## 4. 报告级必补项

Codex 下一次 handoff 只需补：

- 既定 BH-FDR / Holm 校正后的结果列；
- GEE 模型公式、工作相关结构、收敛/诊断状态；
- 70 session / 46 participant 的缺失与排除摘要；
- 10/20/30 秒 probe 前轨迹；
- B1 late → B2 early 恢复计划比较；
- 报告级图。

不要新增身份、版本、语义或时间线审计，除非现有正式结果暴露出新的具体矛盾。

## 5. 当前一句话结论

北京数据已经从“整理阶段”进入“正式结果阶段”：在 70 个可审计 session、46 个重复参与者中，任务推进伴随 probe response 1 概率下降，并出现错误率上升的初步证据，而平均 log RT 未见明显时间趋势；最终显著性措辞待预先规定的多重比较校正和模型诊断完成后冻结。
