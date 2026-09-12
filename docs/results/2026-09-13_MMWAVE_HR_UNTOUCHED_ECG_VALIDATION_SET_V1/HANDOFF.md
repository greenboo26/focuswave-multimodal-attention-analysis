# mmWave untouched ECG validation set v1 - handoff

RUN_ID: `mmwave_hr_untouched_ecg_validation_set_v1_20260913_r1`

STATUS: `BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE`

TASK_BRANCH: `codex/mmwave-hr-untouched-ecg-validation-v1-20260913`

BASE_MAIN_SHA: `40240750f740898709feb257f5188ec954b1d08b`

objective: 建 `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1`（OPT_A）：冻结 primary validation denominator、生成独立 per-window gold-clean ECG 参考、跑 `VS_1`-`VS_10`。不实现 C1/C2、不跑候选。

## key result

**判定 `BLOCKED`：正式 cohort 从未采集 ECG，验证集按原设计无法形成。**

全机 `.acq` 穷尽扫描：

| 根 | 角色 | `.acq` | sessions |
|---|---|---|---|
| `D:\acq_mmwave_data` | 校准根 | **11** | 11 |
| `I:\预实验` | 预实验根 E-batch | **0** | 10 |
| `J:\Data` | 正式数据根 J-batch | **0** | 72 |
| `D:\Project\厚粲杯\11_数据` | 派生/正式分析根 | **0** | — |

11 个有 ECG 的 session 分三类：

- 5 个校准 session（`sub-2_`-`sub-6_`）：有 ECG，**无 probe 窗口**；
- 5 个开发 session（`9779/97793/97994/97795/97796`）：有 ECG 且有 probe 窗口，但**已被反复消费**；
- `sub-97792_`：有 ECG，但 `events.csv` 无 block1-4 probe 段，仓库已判 `not_estimable`。

权威本地证据 `11_数据/derived/ECG_RSP独立验证资产审计_20260824.md` 明确：`D:\acq_mmwave_data` **不是正式实验的多被试队列，而是同一人反复测量的双机校准**，并标注 `calibration_reference_only_not_formal_subject_effect`。

因此 `VS_4`/`VS_5`/`VS_6`/`VS_7` 无法满足（6/10 满足），**验证集无法形成，C1/C2 不得运行**。

## correction

本轮**更正**了前两轮的建议：`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1` 与 `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` 都把 OPT_A 描述为"只差一个可工程补齐的 ECG 参考"。这个描述是错的 —— 缺口是**输入根本不存在**，不是工程问题。错误根因：此前只核对"正式 session 是否与开发集重叠"，**从未核对"正式 cohort 是否有 ECG"**。

## routing

```
VALIDATION_SET_BUILT       = false
CONTRACT_PRECONDITIONS_MET = 6 / 10
BLOCKING_ITEMS             = VS_4, VS_5, VS_6, VS_7
C1_RUN_PERMITTED           = false
C2_RUN_PERMITTED           = false
NEXT_DEPENDENCY            = REM_1（确认正式 cohort 是否有 ECG）→ 否则 REM_2 新采集 或 REM_4 接受缺失
```

修复选项（需裁决）：`REM_1` 确认/取回正式 cohort ECG（推荐先做）；`REM_2` 新采集；`REM_3` 用校准 session（**不推荐**，参与者不重叠不成立且需改窗口契约）；`REM_4` 接受缺失并保持 HR/BR HOLD、HRV BLOCKED。

`VS_DATASET_healthy_v1` 角色维持已冻结裁决：`SECONDARY_EXTERNAL_CORROBORATION_ONLY`，`UNTOUCHED=FALSE`，`PRIMARY_GATE_ELIGIBLE=FALSE`，`C1_EVIDENCE=NOT_PERMITTED`，`C2_EVIDENCE=PERMITTED_SECONDARY_ONLY`，`CAN_AUTHORIZE_V2=FALSE`。

## code entrypoint

`scripts/maintenance/run_mmwave_untouched_ecg_validation_feasibility_20260913.py`（deterministic；只读扫描四个候选源根、判定 contract 前置条件）

## LOCAL_OUTPUTS

- `D:\Project\厚粲杯\11_数据\derived\ECG_RSP独立验证资产审计_20260824.md` —— 权威 ECG 资产性质记录；local-only
- `D:\Project\厚粲杯\11_数据\derived\ecg_rsp_goldclean_reaudit_v1\` —— 唯一 per-window gold-clean ECG 参考（仅覆盖 5 个开发 session）；local-only
- 本任务未修改任何原始数据

## CLOUD_HANDOFF

本任务为 `BLOCKED` 前提核查，产出为 Git-safe 报告/清单/前置条件表/error log/handoff，未产生需要交接的 local-only 科学产物，因此未建立 Drive bundle。若 `REM_1`/`REM_2` 获准执行并产生真实验证集，届时按标准规则上传到 canonical shared `_AI_HANDOFF`（显式 `--drive-root-folder-id 1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL` + `rclone check --checksum` + 回读哈希）。

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`