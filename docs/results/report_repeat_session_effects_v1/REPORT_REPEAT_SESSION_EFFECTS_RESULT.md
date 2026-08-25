# REPORT_REPEAT_SESSION_EFFECTS_V1

## 结论与范围

本报告检验北京正式实验中的重复 session/练习效应。主分析保留所有可用 session，包括第 4 次及以上 session；输入为冻结的 `beijing_zhuhai_shared_probe_master.csv` 中 Beijing 行，不读取毫米波、RGB、NIR 或原始行为文件，也不重做身份恢复。样本为 1400 个 probe、70 场正式 session、46 名具有 `repeat_participant_id` 的 participant；第 4 次及以上有 1 场 session。

冻结主模型为 `outcome ~ progress + formal_session_index + progress × formal_session_index + (1|participant)`。`progress` 为 canonical `shared_protocol_progress`（0--1）；因此 `session_order` 主效应是 protocol progress=0 时每增加一次正式 session 的差异，交互项表示 session-order 斜率随进度变化。二元 probe state（response=1, fully task-focused）与 pre10 error 使用随机截距 logistic mixed model；RT median 和 RT variability（pre10 RT SD）采用 log(ms) 线性混合模型。对模型表中四个结局的八个预定义 `session_order`/交互焦点检验实施 BH-FDR；progress 项保留在表内以完整报告模型，但不扩展校正 family。

## 主要模型结果

详见 `repeat_session_models.csv`。二元结局的 effect size 为 OR，连续结局的 effect size 为 beta（log-ms）。`p_nominal` 为拟合分布近似双侧 p 值，`p_bh_focal_8` 是上述有限的预定义 8 项 FDR 校正。变分 Bayes logistic mixed model 的 CI/p 值是近似推断，需与小样本高阶 session 稀疏性一同解释。

## 预先定义敏感性

敏感性分析对每名 participant 只保留最早 3 场 (`formal_session_index <= 3`)，不删除主分析的任何行。完整结果见 `repeat_session_sensitivity.csv`。主分析与敏感性中 session-order 与 progress 交互的符号比较为：probe_state: response=1 fully task-focused/session_order: 同向；probe_state: response=1 fully task-focused/progress_x_session: 同向；pre10 error rate (binomial numerator/denominator)/session_order: 同向；pre10 error rate (binomial numerator/denominator)/progress_x_session: 同向；pre10 RT median/session_order: 同向；pre10 RT median/progress_x_session: 同向；pre10 RT variability (SD)/session_order: 同向；pre10 RT variability (SD)/progress_x_session: 同向。该比较只回答第 4 次单一 session 是否显著改变方向/估计，不能作为对高阶 session 的充分精确性证明。

敏感性改变了部分主要 session-order 结论：fully task-focused 的 session-order OR 从主分析 0.71（FDR p=3.31e-18）变为最早三场 0.95（FDR p=0.263），后者不再精确；RT median 的 session-order beta 则从主分析 FDR p=0.152 变为最早三场 FDR p=0.037。相反，fully task-focused 的 progress 交互（主/敏感性 OR=1.57/1.69）以及 error 的 session-order（OR=1.16/1.13）和 progress 交互（OR=0.83/0.80）方向一致且均保持 FDR 后显著。因此，不能把包含第 4 次 session 的 fully task-focused 起始主效应或 RT 主效应写成稳健的重复练习结论；较稳健的信号是 error 的 session-order/进度交互与 probe-state 的进度交互。

## 限制

- `formal_session_index=4` 只有一场、一个 participant；对高阶重复练习效应的区间会不稳定，不能据此主张一般化的第 4 次效应。
- 这是已有 canonical probe 层的关联模型，session order 可能与未测量的招募、日程或设备因素混杂，不构成随机化练习效应因果估计。
- pre10 行为窗口彼此可能重叠；error 的分子/分母被作为可复用的窗口汇总建模，不能替代对 trial-level serial dependence 的专门分析。
- 结果只适用于冻结北京正式协议及其已确认的 response=1 构念，不推广到珠海或其他程序版本。

## 可复现产物与脱敏边界

- `repeat_session_models.csv`、`repeat_session_sensitivity.csv`、`figure_repeat_session_effects.png` 和本报告为脱敏聚合交付物，可随 Git 提交。
- `local_input_audit.csv` 保留 pseudonymous participant/session 行级资格信息，只在本地 derived 目录保存，不复制至 GitHub。
