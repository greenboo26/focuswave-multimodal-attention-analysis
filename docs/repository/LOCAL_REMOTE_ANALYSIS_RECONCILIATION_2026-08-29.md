# Local ↔ GitHub canonical scientific analysis reconciliation（2026-08-29）

状态：**PARTIAL — hard gate not passed**

Canonical repository：`greenboo26/focuswave-multimodal-attention-analysis@main`

Verified canonical commit：`3ee7ecdf6959ab59f674c48567eaf013a2cfe827`

本对账不运行新分析、不修改科学结果、不清理或删除本地文件。逐条依据
canonical registry/result index、`01_管理` 管理记录、脚本索引、local large
output manifest、Codex migration CSV、报告/manifest 内容和路径存在性核对。
机器可读明细见同目录 CSV。

## 对账计数

| reconciliation_status | count |
|---|---:|
| MATCHED | 28 |
| LOCAL_ONLY | 0 |
| REMOTE_ONLY | 0 |
| PATH_STALE | 2 |
| RESULT_MISMATCH | 0 |
| SUPERSEDED | 1 |
| PRODUCER_OWNED | 6 |
| MISSING | 6 |
| 总分析条目 | 43 |

注：本 CSV 同时覆盖 canonical registry 的 29 项和当前管理记录中单独
登记的 HR/BR、C1c/C1d、#15/#16/#17、target-lock、B1/B2、Context、C+B、
frontend transparency、RS6240 capability 等 14 个分析视角；同一底层结果
在不同 analysis_id 下保持可追溯，不重复计算科学结果。

## 非 MATCHED 项

| analysis_id | 状态 | 证据 | 结论/处理 |
|---|---|---|---|
| P0_PROTOCOL | PATH_STALE | registry 指向的 `scripts/probe_program_version_audit.py` 在本地不存在；协议审计结果目录仍存在 | 保留路径陈旧证据；不得据此宣称当前协议脚本可复现 |
| C2C | PATH_STALE | canonical CSV 仍写旧的 `run_c2c_within_subject_normalization.py`，实际 canonical 入口为 `pipelines/mmwave/run_c2c_personalized_mmwave_calibration.py` | 不把旧结果提升为当前结果；允许修正 registry 路径后再考虑 canonical rerun |
| EARLY_INCREMENT | SUPERSEDED | registry 明确 superseded；本地为历史增量报告 | 保留历史 provenance，不进入当前结论 |
| C3A_V1/C3A_V2 | PRODUCER_OWNED | NIR producer manifest 与 `11_数据` 本地输出存在；central 无 final increment | producer 继续维护，central 只保留边界和索引 |
| NIR_FULLCLASS_69_ENGINEERING | PRODUCER_OWNED | NIR 69-session engineering manifest/report | 不解释为 final NIR scientific increment |
| RGB_MOTION/RGB_POSE/RGB_FACE | PRODUCER_OWNED | RGB producer path/report，central 仅有状态与 availability | 不跨仓库合并 producer code |
| CONTEXT | MISSING | 管理记录引用的 `audit_current_j_rgb_timebase_v1.py` 未在本地找到；已有 audit result 目录和 canonical 报告 | 保留已有报告，但补齐可复现脚本证据前不宣称 MATCHED |
| D1_HARMONIZATION | MISSING | registry 明确 `DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE` | 缺少外部 storage/evidence，不猜、不运行 |
| NIR_INCREMENT | MISSING | registry 为 `PLANNED_GLOBAL_ONLY`，无 final report/result | 等 producer 完成并提供 manifest |
| RGB_INCREMENT | MISSING | derived-window features 与 final report 不存在 | 等 producer 完成 |
| MULTIMODAL_FUSION | MISSING | canonical fusion card 明确无 final result | 不运行 final multimodal LOSO |
| CROSS_SITE | MISSING | registry 为 planned，暂无 cross-site final result | 等 global harmonization gate |

## 关键核验结论

- 当前 central 有效分析的本地脚本、输入、输出、报告和结论总体一致；
  `C2C` 有一处 registry 脚本路径陈旧，不能报告全局 MATCHED。
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

**未通过 PASS 条件。** `LOCAL_ONLY`、`REMOTE_ONLY`、`RESULT_MISMATCH` 为 0，
但仍有 2 个 `PATH_STALE` 和 6 个 `MISSING`。`PRODUCER_OWNED` 与
`SUPERSEDED` 均已明确标记。

在修正 C2C registry 路径、补齐外部 harmonization/NIR/RGB/final multimodal
证据前，不允许把当前状态报告为“全部本地与 GitHub 完全一致”，也不启动
#15/#16/#17 或 final multimodal 新分析。本轮对账到此停止，未执行目录清理。
