# GPT↔Codex 双边协作交接：P0 审计汇总

**日期：** 2026-08-25
**用途：** 供 GPT/Sol 读取并进行下一阶段科研裁决。
**数据边界：** 不包含原始数据、被试级 CSV、视频、NPZ 或个人身份信息。

## 1. 当前状态

| 线路 | 状态 | 结论边界 |
|---|---|---|
| 北京纵向事件分析 | `BLOCKED_PREFLIGHT` | 尚未运行正式行为事件模型 |
| 珠海三阶段时间线 | `AUDITED_BUT_UNLINKED` | 已核验协议证据，实际 session 尚未连接 |
| 历史 Probe 程序版本 | `PARTIAL` | 北京可确认程序家族，精确版本未知；珠海实际版本未知 |
| NIR 方向性审计 | `PASS` | AUC 低于 .50 不是标签或概率列方向错误 |
| 问卷测量审计 | `COMPLETE_DESCRIPTIVE` | 未确认正式多题量表，主要是单题 trait/state 候选 |
| 静息/休息与 RS6240 QC | `COMPLETE_DESCRIPTIVE` | 已整理质量证据，但不等于 HR/BR/HRV 准确性验证 |

## 2. 北京纵向事件分析

本地目录：`D:\Project\厚粲杯\11_数据\derived\beijing_longitudinal_event_v1\`

- 72 个北京行为候选 session，71 个有时间线事件，1 个缺少时间线。
- participant/session canonical identity 仍不能确定性恢复。
- 当前程序版本审计不足以确认每个 session 的精确版本。
- agent 正确停止在预检阶段，没有输出虚假的事件模型结果。

解除条件：补齐 session 身份、时间线和程序版本/response mapping 证据，再运行预定义行为事件分析。

## 3. 珠海三阶段审计

本地目录：`D:\Project\厚粲杯\11_数据\derived\zhuhai_three_stage_timeline_audit_v1\`

- 登记表中 30 个珠海 session。
- FocusWave 历史版本支持 BBB 三阶段协议；北京 BB 两阶段证据保持独立。
- 30 个登记 session 尚未与 raw behavior、master timeline 和模态目录建立确定连接。
- 未根据总时长或文件数量猜测阶段边界。

正式表述：珠海三阶段设计得到程序级支持，但实际 session 级时间线和字段仍待恢复。

## 4. 历史 Probe 程序版本

本地目录：`D:\Project\厚粲杯\11_数据\derived\probe_program_version_audit_v1\`

- 共整理 179 个登记 session：北京 149，珠海 30。
- 北京 72 个行为目录显示 BB 两阶段、每阶段 432 trials、20 probes，有 `probe_response` 与 `probe_vigilance`；只能绑定 v3.1.0+ BB 家族，不能绑定精确 patch 版本。
- 珠海 30 个 session 缺少可连接的 raw behavior CSV、master timeline 或 probe asset，实际版本与 response mapping 为 `UNKNOWN`。
- 历史版本存在结构冲突：v1.3.4 单一四分类，v2.0/v2.1 使用 1–9，v3.0+ 使用 attention 四分类与 vigilance 四点字段，v3.1.0+ BB 为两阶段、20 probes。

风险：北京和珠海不能仅凭登记表或文件名直接合并。

## 5. NIR 方向性审计

本地目录：`D:\Project\厚粲杯\11_数据\derived\nir_directionality_audit_v1\`

- 映射为 `raw label 1 → target 0`，`raw labels 2/3/4 → target 1`。
- `predict_proba[:, 1]` 始终对应 target 1，24 个 fold 检查通过。
- AUC 为 primary `.3497`、sensitivity `.3177`，不允许用 `1 - AUC` 改写。
- 8 个可评估 participant 中有 5 个呈反向排序，低 AUC 不是单一 participant 造成。

裁决问题：NIR 是否作为反向/探索性结果保留，并进入共同样本纵向结构分析；不能仅凭 AUC < .50 宣布 NIR 无效。

## 6. 问卷测量审计

本地目录：`D:\Project\厚粲杯\11_数据\derived\questionnaire_measurement_audit_v1\`

- 共整理 212 条题目/设计记录。
- 未得到可核验的正式多题量表、反向计分规则、内部一致性或因子结构证据。
- “自评专注”“平时持续专注能力”可作为 trait-like 单题候选；走神、疲劳、困倦、注意维持与恢复可作为 state-like 单题候选。
- 北京/珠海问卷站点映射仍未知。

禁止：不把单题问卷自动称为量表，不报告未经支持的 alpha/omega，不把事后问卷与瞬时 Probe 标签混为同一时间尺度。

## 7. 静息/休息与 RS6240 QC

本地目录：`D:\Project\厚粲杯\11_数据\derived\rest_break_coverage_qc_manifest_v1\`

- 北京 72 个 BB 行为 session 中 71 个有时间线事件，1 个缺失；canonical identity/session 未确定。
- 珠海静息/休息字段因 raw session 尚未连接，保持 unknown。
- RS6240 审计覆盖 3 个 session，最多约 6000 frames、约 60 秒。
- 设备时间戳是主要依据；host timestamp 严格缺口使其不能直接提供可用 cardiac-band 连续段。
- 8 通道空间一致性目前只能作为探索性慢相位证据。
- target-lock、RGB gate、extraction success 都不能证明 HR/BR/HRV 准确。
- 风险包括 host timestamp gap、自动 range-bin 244–248 与 profile 主峰 8–13 不一致，以及 firmware calibration、Tx timing、memory mapping 尚未完全核验。

## 8. 请 GPT/Sol 裁决的最小问题

1. 北京需补齐哪些最小身份、版本和时间线证据，才能解除 `BLOCKED_PREFLIGHT`？
2. 珠海应继续恢复 session 级映射，还是先作为协议/设计证据进入报告？
3. 程序版本不完全一致时，北京和珠海哪些分析可以合并，哪些必须分站点报告？
4. NIR 低 AUC 应如何作为探索性结果和共同样本分析的一部分呈现？
5. 问卷单题如何进入 trait × state、Probe 外部效标和恢复分析？
6. RS6240 QC 如何写入“测量可靠性”部分，同时明确不能声称 HR/BR/HRV 已验证？

## 9. 固定双边协作协议

以后凡是 GPT↔Codex 协作，统一采用：

1. Codex 将关键状态、RUN_ID、输入范围、结果摘要、限制和待裁决问题写入一份 GitHub Markdown 交接文件。
2. 不上传原始数据、被试级派生数据、视频、NPZ、个人身份信息或大型临时输出。
3. GPT 只依据交接文件及明确引用的仓库文件裁决。
4. GPT 裁决另写入同一仓库 `docs/decisions/`，保留 commit hash。
5. Codex 读取裁决后执行，不在 blocker 阶段自行改标签、阈值、split 或主要科学解释。
6. 每次交接必须区分 `formal / exploratory / blocked / unverified`。

## 10. 本地产物索引

participant-level 产物仍保留在本地，不作为本次 GitHub 提交内容：

    D:\Project\厚粲杯\11_数据\derived\beijing_longitudinal_event_v1\
    D:\Project\厚粲杯\11_数据\derived\zhuhai_three_stage_timeline_audit_v1\
    D:\Project\厚粲杯\11_数据\derived\probe_program_version_audit_v1\
    D:\Project\厚粲杯\11_数据\derived\nir_directionality_audit_v1\
    D:\Project\厚粲杯\11_数据\derived\questionnaire_measurement_audit_v1\
    D:\Project\厚粲杯\11_数据\derived\rest_break_coverage_qc_manifest_v1\
