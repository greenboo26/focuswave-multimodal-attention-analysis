# GPT 裁决：C1b 数据已就绪，直接进入 24 被试 Radar–ECG 正式验证

日期：2026-08-25
依据：`8f08d5470257bce2a000374c6d28b5c21cf438ed`
状态：`C1B_APPROVED_TO_RUN`

## 1. 当前状态

VS_DATASET 健康队列完整包已经下载到本地：

`D:\Project\厚粲杯\11_数据\external_benchmarks\VS_DATASET_healthy_v1\`

总账已确认：

- 24 名被试，`VS01`–`VS24`；
- 96 个 `.mat`，每人 `Resting.mat`、`Resting_Mindray.mat`、`Apnea.mat`、`Apnea_Mindray.mat`；
- `README.txt`、`Subject Information.tab`；
- 共 98 个官方数据文件；
- 已生成逐文件 SHA-256；
- 当前状态为 `DATASET_LOCAL_READY / benchmark_not_run`。

因此此前“正式数据不在本地”的 blocker 已解除。不要继续做数据入口或下载可得性审计。

## 2. `Subject Information.tab` 大小差异的处理

Dataverse API 元数据大小与实际下载大小不一致已经被记录。该差异本身不阻塞 benchmark。

本轮只需要：

1. 尝试正常解析 `Subject Information.tab`；
2. 记录实际字段、行数、编码和 SHA-256；
3. 若可正常解析且 24 名被试信息完整，则继续；
4. 只有文件无法解析、被试清单不完整或与 `.mat` 目录发生直接冲突时，才升级为 blocker。

不得为了匹配 API 声明字节数而截断或修改下载文件。

## 3. 第一阶段：字段与配对核验

先对完整 24 人目录建立一个字段清单，不重新设计算法。

最低输出：

- 48 个 Radar–Mindray session pair：24 × (`Resting`, `Apnea`)；
- 每个 `.mat` 的顶层变量名、数组尺寸、采样率或时间字段；
- Mindray 文件中 ECG Lead II 的实际字段名、单位、采样率和时间基准；
- Radar 文件中正式算法需要的信号字段、采样率和时间字段；
- 每对 Radar/Mindray 是否可确定性配对；
- 每个 session 的持续时间和明显缺失情况；
- subject/session manifest。

若字段在 24 人中一致，直接进入正式 benchmark，不停下来等待新的 GPT 方法裁决。

若只有少数 session 存在字段或质量异常，保留完整清单并按预先定义的技术可用性规则标记，不因结果好坏决定排除。

## 4. 第二阶段：恢复冻结的 C1b benchmark

沿用已经冻结的评价协议，不重新调 VitalSense 示例，不改变评价规则。

核心流程：

`ECG Lead II → R-peak → session/device 对齐 → 雷达心搏事件 → 一对一 beat matching → IBI → HR / RMSSD / SDNN`

固定规则：

- 主 beat matching tolerance：`±75 ms`；
- `±50 / ±75 / ±100 / ±150 ms` 全部报告为敏感性分析；
- 设备/记录时钟偏移与 ECG→机械心搏的生理时延分开表示；
- 禁止在测试窗口上逐窗搜索最佳 lag；
- 禁止根据 held-out 结果调阈值；
- IBI / HRV 评价必须独立于一个固定绝对时间偏移；
- `TechValidation.m` 的 `maxCorr` 不作为相关质量指标，因为既有代码审计已确认该字段实际保存 lag index。

## 5. 正式结果必须回答什么

至少按被试和 session 输出：

1. ECG R-peak 数；
2. 雷达检测 beat 数；
3. 一对一匹配数量与未匹配数量；
4. 主 `±75 ms` 下的 beat-level 性能；
5. `±50/75/100/150 ms` 敏感性；
6. 原始 timing offset；
7. 固定常数时延修正后的残余 timing error；
8. IBI 误差；
9. HR 误差；
10. RMSSD 与 SDNN 的雷达–ECG 一致性。

Resting 与 Apnea 分开报告，同时可以给完整健康队列汇总，但不得只报 pooled 数值掩盖条件差异。

所有总体结果应保留 participant-level 分布或 participant bootstrap / 置信区间，不能只给一个总平均。

## 6. 解释边界

该 benchmark 验证的是“雷达逐搏 / IBI / HRV 算法在公开 Radar–ECG 数据上的外部测量性能”。

它不能单独证明：

- RS6240 本机已经达到相同性能；
- 北京实验中的毫米波心脏指标已经有效；
- HRV 已经能预测专注状态。

只有外部算法验证通过后，才批准把经过验证的 beat/IBI/HRV 计算链移植回 RS6240，并做设备级和北京 Probe 时间轴验证。

## 7. 本轮停止条件

这次不再返回“protocol ready”。只有两种正常结束：

1. `BENCHMARK_COMPLETE`：24 人正式结果完成；
2. `FIELD_OR_DATA_INCONSISTENCY_BLOCKER`：存在明确、可定位的字段或数据冲突，并列出具体 subject/session/file/field。

不得因为没有现成同名 runner 而停止；若缺少入口脚本，按冻结协议新建最薄执行入口并直接运行。

完成后更新 `docs/WORKSPACE_LEDGER.md`，记录入口脚本、完整本地产物路径、字段 manifest、benchmark 结果文件和最终状态。
