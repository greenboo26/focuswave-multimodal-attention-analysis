# mmWave external validation asset audit v1 — handoff

RUN_ID: `mmwave_external_validation_asset_audit_v1_20260913_r1`

STATUS: `ASSET_AUDIT_COMPLETE`

TASK_BRANCH: `codex/mmwave-external-validation-asset-audit-v1-20260913`

BASE_MAIN_SHA: `ebcb9e6e7d4f1446ac1a51e17091188c2782d657`

objective: 在给正式 cohort 重建 per-window ECG gold-clean（`OPT_A`）之前，先追溯并评估本机三个外部毫米波数据资产对 preregistered 候选 C1/C2 的可用性，避免做重复工程。只做资产追溯与可行性判断。

scope: `ASSET_AUDIT` —— 未运行 C1/C2、未运行任何 HR 算法、未修改 producer 或 snapshot v1、未修改任何外部数据。

## key result

没有任何外部资产对 **C1** 可用；**C2** 只有 `VS_DATASET_healthy_v1` 可用且只能是 **secondary**。

| dataset | verdict | 关键理由 |
|---|---|---|
| `VS_DATASET_healthy_v1` | `PARTIAL_CANDIDATE_SECONDARY` | 有 Mindray ECG Lead II（500 Hz）金标准，但雷达侧只有预提取单通道位移 `VitalSig`，无 DataCube → 承载不了 C1；且本机已有**已完成的 C1b 正式基准**（`C1B_VS_DATASET_20260825_V1`，24 subjects / 48 pairs）→ 对 C2 只能作 secondary external evidence |
| `AgeBalanced_60GHz` | `INELIGIBLE_FOR_PRIMARY_VALIDATION` | 有 ECG（~250 Hz）与 range-FFT 帧，但**已被用于 HR 路线评估与选型**（2026-08-14 条目，commit `f4a8c74d…`，已公布 9.5 / 10.361 BPM 等数字） |
| `mmWave_Heartbeat_TI_gby` | `INELIGIBLE` | 只有 10 个原始 ADC `.bin`；**无 ECG、无时间戳、无采集配置、无被试映射** |

## routing

```
PREREGISTRATION            = DONE
EXTERNAL_ASSET_INVENTORY   = COMPLETE
OPT_A_BUILD                = PROCEED_AS_PRIMARY

primary untouched validation : OPT_A（正式 cohort 116 sessions / 61 participant groups）
secondary external evidence  : VS_DATASET_healthy_v1（仅 C2，明确标注 secondary）
not usable                   : AgeBalanced（路线暴露）、TI gby（无参考）
```

**C1 的新边界**：`VS_DATASET` 不构成 C1 的任何证据（无 DataCube，机制不可表达）。
**C2 的新结构**：primary 仍为 `OPT_A`；`VS_DATASET` 仅作 secondary 旁证，且必须同时声明其 C1b 暴露历史。判据与阈值**不变**，不得因外部数据可用而放松。

## code entrypoint

`scripts/maintenance/run_mmwave_external_validation_asset_audit_20260913.py`（deterministic；只做目录扫描、目录级哈希与 git 历史反查，不读取 `.mat`/`.zlib` 内容）

数据格式与可行性结论来自本任务已完成的只读检查，逐条记录在 manifest 的 `assessments[].evidence` 字段与报告中。

## LOCAL_OUTPUTS

- `D:\Project\厚粲杯\11_数据\derived\vitalsense_c1b_benchmark_v1\` —— C1b 基准的本地证据（`status.json`、`run_config.json`、`benchmark_report.md`、`benchmark_summary_primary.csv` 等）；local-only，未入 Git。
- 三个外部数据集本身位于 `D:\Project\厚粲杯\11_数据\` 下，**local-only 且本任务未修改**。

## CLOUD_HANDOFF

- target folder: canonical shared Drive `_AI_HANDOFF/2026-09-13_mmwave_external_validation_asset_audit_v1`
- parent folder id: `1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL`（该共享 `_AI_HANDOFF` 不在 rclone remote 默认根下，必须显式带 `--drive-root-folder-id`）
- transport: `D:\Project\.tools\rclone.exe` 1.75.1 + 既有已授权 Google Drive remote；凭据仅存本机配置，未打印、未入日志、未入库
- uploaded files: 7（6 个 Git-safe 交付物 + `CLOUD_HANDOFF_VERIFICATION.json`）
- verification: `rclone check --checksum` exit 0；随后整目录回读到本机 staging 并逐文件重算 SHA-256，7/7 与本地一致；未混入 snapshot v1 / estimator improvement / low-bias mechanism audit 文件
- `CLOUD_HANDOFF_VERIFICATION.json` SHA-256: `B94E8836405C55AF65D1B345AEF0E7B799840EED206FBA9DE603564833FE3D37`
- 三个外部数据集**未上传**：留在本机 local-only，本 bundle 只含 Git-safe 审计报告、manifest、assessment/history 表、error log 与 handoff

CLOUD_UPLOAD: `UPLOADED_AND_VERIFIED`

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`
