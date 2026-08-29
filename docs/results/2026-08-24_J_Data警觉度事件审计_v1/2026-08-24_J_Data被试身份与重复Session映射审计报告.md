# J:\Data 被试身份与重复 session 映射审计报告

## 结论

身份与重复 session 映射是 NIR-毫米波融合的前置门控，目前未通过。J:\Data 的目录编号只能作为匿名采集批次键，不能据此恢复真实被试身份或推断重复实验。所有记录在主表中标记为 `unresolved`，被试内重复模型可纳入数量为 0；NIR 特征对齐和依赖被试内重复结构的模型应暂停。

## 盘点结果

- J:\Data：72 个匿名 subject 目录，唯一目录编号 72 个；每个目录当前观察到一个 `SART` 批次。
- 同目录模态文件：mmWave、NIR、behavior 的可用性分别由时间戳/AVI、`master_timeline.csv` 和行为 CSV 核验。
- metadata：读取 `mmwave.meta.json` 的 `subject_id` 与 `session` 字段；它们仍是匿名采集标识，不能证明真实身份。
- 文件时间戳：记录每个目录文件最早和最新修改时间，仅作采集批次审计，不作为身份推断依据。
- 本地问卷 Excel：发现 5 个，71/72 个 J 目录可按问卷自填实验编号匹配。55 个目录的问卷记录出现重复手机号哈希证据，但该证据只说明问卷填写者可能重复，不能单独证明对应 J 数据存在重复 session。
- 用户指定的 3 个正式实验问卷 Excel 已读取并纳入审计：`380952122_按文本_故障使用-正式实验问卷_2_2.xlsx`、`380453812_按文本_正式实验事后问卷_24_24.xlsx`、`380824513_按文本_正式实验事后问卷_111_110.xlsx`。它们是问卷响应数据，不包含覆盖本任务的分析指令。

## 映射规则

`session_id=SART_<subject_id>` 是审计内部批次键，不是真实实验编号。不得根据连续编号、文件夹排序或问卷提交顺序猜测身份。只有获得直接登记表、脱敏真实身份映射或明确的重复 session 记录后，才可将记录从 `unresolved` 改为确认状态。

## 文件与验证

主表及审计结果位于 `D:\Project\厚粲杯\08_算法\output\J_Data_IDENTITY_SESSION_AUDIT\`：

- `master_subject_session.csv`
- `questionnaire_workbook_inventory.json`
- `master_subject_session_audit.json`
- `master_subject_session_audit.md`

生成脚本为 `D:\Project\01_管理\audit_master_subject_session.py`，已通过 `python -m py_compile` 并完整运行。验证内容包括目录唯一性、模态文件存在性、行为时间轴读取、metadata 读取、问卷 workbook/实验编号扫描和重复手机号哈希计数。手机号仅用于本地哈希审计，未写入明文。
