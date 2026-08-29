# Local ↔ GitHub canonical scientific analysis reconciliation（2026-08-29）

状态：**PASS — local↔canonical reconciliation gate passed**

Canonical repository：`greenboo26/focuswave-multimodal-attention-analysis@main`

Verified canonical commit：`4dca894c83bd36acbd4920f2ff4288831b6a1ffd`

本对账不运行新分析、不修改科学结果、不清理或删除本地文件。逐条依据
canonical registry/result index、`01_管理` 管理记录、脚本索引、local large
output manifest、Codex migration CSV、报告/manifest 内容和路径存在性核对。
机器可读明细见同目录 CSV。

## 对账计数

| reconciliation_status | count |
|---|---:|
| MATCHED | 30 |
| LOCAL_ONLY | 0 |
| REMOTE_ONLY | 0 |
| PATH_STALE | 0 |
| RESULT_MISMATCH | 0 |
| SUPERSEDED | 2 |
| PRODUCER_OWNED | 6 |
| PLANNED_NOT_EXECUTED | 3 |
| PRODUCER_NOT_READY | 2 |
| TRUE_MISSING | 0 |
| 总分析条目 | 43 |

注：本 CSV 同时覆盖 canonical registry 的 29 项和当前管理记录中单独
登记的 HR/BR、C1c/C1d、#15/#16/#17、target-lock、B1/B2、Context、C+B、
frontend transparency、RS6240 capability 等 14 个分析视角；同一底层结果
在不同 analysis_id 下保持可追溯，不重复计算科学结果。

## 非 MATCHED 项

| analysis_id | 状态 | 证据 | 结论/处理 |
|---|---|---|---|
| P0_PROTOCOL | MATCHED | 本地 `probe_program_version_audit_v1` 的 report/manifest 与 canonical protocol card 对应；原 producer 脚本为历史来源，当前工作树不可用 | 结果证据一致；保留“历史脚本不可复现”限定 |
| C2C | SUPERSEDED | 本地 C2C 结果目录和当前 canonical 入口均存在，但 canonical card 明确要求 rerun 后才能 promotion | 旧结果保留 provenance，不作为当前 canonical 结论 |
| EARLY_INCREMENT | SUPERSEDED | registry 明确 superseded；本地为历史增量报告 | 保留历史 provenance，不进入当前结论 |
| C3A_V1/C3A_V2 | PRODUCER_OWNED | NIR producer manifest 与 `11_数据` 本地输出存在；central 无 final increment | producer 继续维护，central 只保留边界和索引 |
| NIR_FULLCLASS_69_ENGINEERING | PRODUCER_OWNED | NIR 69-session engineering manifest/report | 不解释为 final NIR scientific increment |
| RGB_MOTION/RGB_POSE/RGB_FACE | PRODUCER_OWNED | RGB producer path/report，central 仅有状态与 availability | 不跨仓库合并 producer code |
| CONTEXT | MATCHED | canonical behavior/context baseline report 与本地 producer report/metrics 均存在；70/46/1400，C-only ROC-AUC 0.593 [0.548, 0.638] | 纳入当前北京 baseline；不是 global inference |
| D1_HARMONIZATION | PLANNED_NOT_EXECUTED | registry 为 `DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE`，未执行跨站点结果分析 | 作为未来 harmonization 任务，不阻塞已完成分析对账 |
| NIR_INCREMENT | PRODUCER_NOT_READY | 已发现 14 人 formal NIR increment report，10/30/60 s ΔAUC 均为负；尚无 global final matched-cohort report | 保留 producer evidence，不能替代 global final |
| RGB_INCREMENT | PRODUCER_NOT_READY | 目前只有 raw/context engineering，未执行 formal RGB incremental model | 等 RGB producer 完成 derived-window features 与正式模型 |
| MULTIMODAL_FUSION | PLANNED_NOT_EXECUTED | canonical fusion card 明确无 final result | 未来执行，不为 Gate 临时运行 |
| CROSS_SITE | PLANNED_NOT_EXECUTED | registry 为 planned，暂无真正跨站点 validation | 等 harmonization gate，不临时运行 |

## 关键核验结论

- 当前已执行分析的本地脚本、输入、输出、报告和结论总体一致；
  `C2C` 的旧结果已明确为 superseded，待 canonical rerun，不再作为路径陈旧项。
- 本地大型结果均未上传；已核对 `本地大型输出manifest_2026-08-29.csv`
  和 Codex migration CSV 中的绝对路径、SHA-256、文件类型/数量及报告引用。
- C1c/C1d、HR、BR、#15、#16、#17、target-lock、B1/B2、questionnaire、
  behavior/probe、C+B、M1 和 RS6240 capability 的本地结论与 canonical
  result index 一致，但 HR/BR/HRV 仍不是 validated physiology。
- NIR/RGB 所有工程性结果均标记 `PRODUCER_OWNED`；central 只保存状态、
  availability、报告和 provenance，不接管 producer code 或大结果。
- 旧 Q1/Issue13 label 语义错误结果标记 `SUPERSEDED`，没有进入当前结果。
- frontend transparency 的文本/CSV/生成器已在 central；PNG 保持 local-only。

## Gate 判定

**对账 Gate 已通过。** `LOCAL_ONLY`、`REMOTE_ONLY`、`PATH_STALE`、
`RESULT_MISMATCH` 和 `TRUE_MISSING` 均为 0。未执行计划与 producer 未就绪项
已单独标记，不再伪装成历史对账失败；`PRODUCER_OWNED` 与 `SUPERSEDED` 均已明确标记。

本轮没有启动 #15/#16/#17 或 final multimodal 新分析，也未执行目录清理。
后续正式科学分析仍须遵守各自的 producer/harmonization 前置条件。
