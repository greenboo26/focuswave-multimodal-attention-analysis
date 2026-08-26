# SOL_SCIENTIFIC_REVIEW_GATE_V1

状态：`WAITING_FOR_LOCAL_CANONICALIZATION`

本审查只在 `LOCAL_ANALYSIS_LIBRARY_CANONICALIZATION_V1` 完成并标记 `READY_FOR_SOL_REVIEW` 后启动。

## 审查对象

唯一审查分支：
`codex/local-analysis-library-canonicalization-20260826`

GPT-5.6 Sol 必须从 GitHub 读取该分支，不依赖本地聊天记忆判断本机事实。

## 审查目标

确认整理后的整个分析体系：

1. 科学问题明确；
2. 每项保留分析都服务最终报告；
3. 样本单位、重复被试、site/protocol 处理正确；
4. 标签与 vigilance 构念解释正确；
5. 时间窗口无未来泄漏；
6. 模型 family 与 outcome 匹配；
7. CV participant-disjoint；
8. 模态增量使用 matched cohort 和统一 folds；
9. bootstrap / CI / FDR 适当；
10. 工程 QC 与心理学结论不混淆；
11. 不存在无意义重复分析、结果导向窗口/模型选择；
12. AMD/NVIDIA 跨机器 contract 足以支持最后合并；
13. 历史 superseded 结果不会进入最终报告；
14. 输出和 provenance 足以复现与审计。

## 每项分析裁决

Sol 必须对 registry 每个 analysis_id 给出一个：

- `KEEP_MAIN`
- `KEEP_SUPPORTING`
- `REVISE_METHOD`
- `RERUN_CANONICAL`
- `DROP_FROM_REPORT`
- `ENGINEERING_ONLY`
- `SUPERSEDED`

并写明原因与必要修改。

## 特别强制复核

- `REPORT_ANALYSIS_COHORT` 的 1400 / 1420 / 1440 等口径；
- response 1 vs 2/3/4 主终点与四分类层；
- label 3 / 4 中文 mapping 全仓一致性；
- vigilance 的量表方向、模型与报告措辞；
- behavior longitudinal / pre-probe / recovery 是否重复或合理分层；
- questionnaire criterion validity 的 bridge、重复测量、结果边界；
- repeat-session effect 模型与前三场敏感性；
- behavior/context baseline 是否已经统一到 canonical cohort/folds；
- C1 HRV 是否只作为 validation/negative boundary，而不是主比赛模型；
- C2b/C2C/M1 是否还有必要在外部盘重复提取，以及最终报告角色；
- NIR v1/v2 superseded 关系与 69-session final 的定义；
- RGB engineering output 到 Probe-level feature 的统计桥接；
- AMD DirectML vs NVIDIA CUDA parity/backend provenance；
- Beijing B1+B2 / Zhuhai B1+B2 shared-primary 与 Zhuhai B3 extension；
- 同一自然人跨硬盘/跨站点时 participant grouping；
- final multimodal models 的 matched cohort / common folds / site handling；
- 哪些分析只能在合并后运行，禁止双机各自算完再平均结论。

## 必须产出

Sol 审查结果应包含：

1. `SCIENTIFIC_REVIEW_MATRIX`：逐 analysis_id 裁决；
2. `CRITICAL_FIXES`：必须先改的问题，按严重性排序；
3. `FINAL_MINIMUM_ANALYSIS_SET`：最终报告真正需要的最小分析集合；
4. `FINAL_REPORT_EVIDENCE_CHAIN`：报告证据链；
5. `SUPERSEDED_DO_NOT_CITE`：禁止最终引用的旧结果；
6. `AMD_HANDOFF_APPROVAL`：`APPROVED` / `APPROVED_AFTER_FIXES` / `REJECTED`；
7. 如果批准，明确 AMD 分支应该包含哪些 analysis modules、哪些只做 local derived production、哪些必须等 global merge。

## 审查通过条件

只有以下条件同时满足才允许创建同事 AMD 正式执行分支：

- 无未解决的高风险数据泄漏；
- 无未解决的 cohort/identity 口径冲突；
- 无错误 label mapping；
- 保留分析的模型与重复测量结构合理；
- cross-machine derived schema 可确定性合并；
- 已明确哪些统计只能 global 运行；
- AMD/NVIDIA 后端差异有 provenance/parity 方案；
- 所有交给同事执行的入口已在 NVIDIA 本机经过复现或输入审计；
- 最终报告分析集合已经收敛，不再把工程诊断当主结果。

未经 `AMD_HANDOFF_APPROVAL=APPROVED`，不得建立正式 AMD execution branch。
