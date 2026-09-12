# mmWave untouched ECG validation set v1 - precondition feasibility audit

Document ID: `MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1`

State: `BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE` / `VALIDATION_SET_NOT_FORMED` / `NO_CANDIDATE_RUN`

RUN_ID: `mmwave_hr_untouched_ecg_validation_set_v1_20260913_r1`

Date: 2026-09-13 (Asia/Shanghai)

Base commit: `40240750f740898709feb257f5188ec954b1d08b`

## 0. 本任务的结果不是"建好了验证集"，而是"证明了它按原设计建不出来"

任务是建 `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1`（OPT_A）：冻结分母、生成独立 per-window gold-clean ECG 参考、跑 `VS_1`-`VS_10`。

**执行前提核查后判定 `BLOCKED`：正式 cohort 没有任何 ECG 采集来源，因此 `VS_4`/`VS_5`/`VS_6`/`VS_7` 无法满足，验证集无法形成，C1/C2 不得运行。**

按规范，这里如实报告 blocker，而不是伪造分母或改用不等价的替代口径。

## 1. 全机 ECG 覆盖：唯一权威清单

对四个可能承载生理采集的根做了穷尽扫描（`.acq` 计数）：

| 根 | 角色 | `.acq` 数 | session 目录 |
|---|---|---|---|
| `D:\acq_mmwave_data` | 校准根（`calibration_root`） | **11** | 11 |
| `I:\预实验` | 预实验根（`preexperiment_root`，E-batch） | **0** | 10 个 `sub-0xx_` |
| `J:\Data` | 正式数据根（`formal_data_root`，J-batch） | **0** | 72 |
| `D:\Project\厚粲杯\11_数据` | 派生/正式分析根 | **0** | — |

**全机只有 11 个 session 有 ECG 采集，全部在 `D:\acq_mmwave_data`。**

## 2. 这 11 个 ECG session 逐个可用性

| session | `.acq` | `beh/events.csv`（probe 窗口来源） | mmWave NPZ | 状态 |
|---|---|---|---|---|
| `sub-2_` | 1 | 无 | 100 | 校准 session，无 probe 窗口；RSP 通道缺失 |
| `sub-3_` | 1 | 无 | 78 | 校准 session，无 probe 窗口 |
| `sub-4_` | 1 | 无 | 94 | 校准 session，无 probe 窗口 |
| `sub-5_` | 1 | 无 | 81 | 校准 session，无 probe 窗口 |
| `sub-6_` | 1 | 无 | 84 | 校准 session，无 probe 窗口；历史硬件故障待复核 |
| `sub-9779_` | 1 | 有 | 156 | **开发集（已消费）** |
| `sub-97793_` | 1 | 有 | 163 | **开发集（已消费）** |
| `sub-97994_`（别名 97794） | 1 | 有 | 134 | **开发集（已消费）** |
| `sub-97795_` | 1 | 有 | 141 | **开发集（已消费）** |
| `sub-97796_` | 1 | 有 | 142 | **开发集（已消费）** |
| `sub-97792_` | 1 | 有（但**无 block1-4 probe 段**） | 31 | `not_estimable`：仅 baseline+practice，无正式 probe 窗口 |

分三类：

- **5 个校准 session**（`sub-2_` 到 `sub-6_`）：有 ECG，但**没有 probe 窗口**；
- **5 个开发 session**：有 ECG 且有 probe 窗口，但**已被 estimator improvement v1、P1/P2、low-bias audit 反复消费**；
- **1 个 `sub-97792_`**：有 ECG，但仓库既有记录明确判定 `not_estimable + reason=仅采集 baseline+practice（events.csv 无 block1-4 段事件）`，因此**没有 probe 窗口**。

## 3. 决定性证据：这套 ECG 数据在设计上就不是多被试队列

`11_数据/derived/ECG_RSP独立验证资产审计_20260824.md` 是权威记录，原文明确：

- 「这批 `D:\acq_mmwave_data` 资产**不是正式实验的多被试队列**……它们是**同一人反复测量**的毫米波 x ECG/RSP 双机校准、静息与呼吸专注测试。」
- 采集架构：电脑 A 采毫米波并经并口发 marker；电脑 B 的 BIOPAC MP160 记录 ECG 与呼吸带。
- 「**不能作为正式 179 场被试的组间、站点或注意主效应样本**。」
- 所有 ECG/RSP 参考数据保持 `calibration_reference_only_not_formal_subject_effect`，**不与正式被试主索引按数字自动合并**。

同时 `J:\Data` 的正式 session 结构为 `beh / mmwave / nir / rgb` 四目录，**没有 ECG 目录、没有 `.acq`、没有任何生理采集痕迹**；`I:\预实验` 的 10 个 session 同样是四目录结构、`.acq` 为 0。

**结论：正式 cohort（J-batch 72 + E-batch 44 = 116 sessions）从未采集 ECG。** 因此 OPT_A 所需的"为正式 session 生成独立 per-window gold-clean ECG 参考"**不存在可用的输入**。

## 4. 这对验证集 contract 的逐条影响

| contract item | 前置条件 | 说明 |
|---|---|---|
| `VS_1_SESSION_DISJOINT` | 满足 | 正式 session 与开发 session 不重叠（已核验） |
| `VS_2_PARTICIPANT_DISJOINT` | 满足 | 正式 id 空间独立 |
| `VS_3_UNTOUCHED` | 满足 | 正式 session 未用于 HR 开发 |
| `VS_4_INDEPENDENT_ECG_REFERENCE` | **不满足** | 正式 cohort 无任何 ECG 采集来源 |
| `VS_5_WINDOW_CONTRACT` | **不满足** | 冻结窗口契约依赖由 ECG/BIOPAC 采集推导的 block marker 对齐；无该采集则 `window_effective_start` 无法为正式 session 复现 |
| `VS_6_ECG_ELIGIBILITY` | **不满足** | 无 per-probe ECG 参考即无法分类 valid/invalid/unresolved |
| `VS_7_DENOMINATOR_FROZEN` | **不满足** | 无 ECG 资格即无法冻结分母 |
| `VS_8_NO_REUSE` | 满足 | 程序性 |
| `VS_9_NO_DEVELOPMENT_LEAKAGE` | 满足 | 程序性 |
| `VS_10_NO_SNAPSHOT_V2` | 满足 | 程序性 |

**4 项不满足，其中 3 项（VS_4/VS_5/VS_6）是科学性的、无法用程序手段绕过。**

## 5. 我在此之前给出的 OPT_A 建议是错的，这里更正

`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md` 与 `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` 都把 OPT_A 描述为"唯一同时满足 session 不重叠、participant 不重叠、probe 窗口、规模足够的来源，唯一缺口是需要独立生成 per-window gold-clean ECG 参考"，并称该缺口是"数据工程任务，不是科学决策"。

**这个描述是错的**：该缺口不是工程问题，而是**输入根本不存在**。正式 cohort 没有 ECG 通道；而唯一有 ECG 的池子按设计就是**同一名参与者的校准测量**，并把 5 个 probe session 全部用在了开发上。

错误根因：前两轮只核对了"正式 cohort 的 session 是否与开发集重叠"，**没有核对"正式 cohort 是否有 ECG 采集"**。本次按用户指定的两个根（`D:\acq_mmwave_data`、`11_数据`）深查后才暴露。

## 6. 修复选项（需要用户裁决，本任务不自行选择）

| id | 选项 | 能否得到真正 untouched 验证集 | 代价 |
|---|---|---|---|
| `REM_1` | 确认正式 cohort 当年是否采集过 ECG（可能存放在采集机/归档盘/合作方），若有则取回并重跑 gold-clean | 能 | 先确认来源，代价未知 |
| `REM_2` | **新采集**一组参与者/场次不重叠、且同时有 mmWave 与 ECG、按冻结窗口契约的数据 | 能，且唯一可保证 | 高（需现场采集） |
| `REM_3` | 用 `sub-2_`-`sub-6_` 校准 session 建"校准窗口契约"下的验证集 | **不能**：它们与开发集同属"同一人反复测量"，参与者不重叠不成立；且需改窗口契约 | 中；方法论上有实质削弱 |
| `REM_4` | 正式承认本项目当前不存在满足冻结 contract 的 untouched 验证集，**保持 HR/BR 为 HOLD、HRV 为 BLOCKED**，把 C1/C2 与 snapshot v2 一并挂起，直到获得 REM_1/REM_2 的资源 | 不适用（是接受现状） | 无额外成本，但永久限制 mmWave 的生理结论 |

**推荐 `REM_1` 优先**：它是唯一可能低成本解决、且不改变验证设计的前提；只有确认正式 cohort 确实没有 ECG，才进入 `REM_2` 或 `REM_4` 的取舍。

**明确不推荐 `REM_3`**：用同一名参与者的校准测量充当"参与者不重叠"验证集在方法上不成立，且需要改冻结的窗口契约，等于把验证做成走过场。

## 7. 当前状态与边界

```
VALIDATION_SET_BUILT        = false
CONTRACT_PRECONDITIONS_MET  = 6 / 10
BLOCKING_ITEMS              = VS_4, VS_5, VS_6, VS_7
C1_RUN_PERMITTED            = false
C2_RUN_PERMITTED            = false
SNAPSHOT_V1_MODIFIED        = false
FORMAL_PRODUCER_MODIFIED    = false
SOURCE_DATA_MODIFIED        = false
MODELS_TRAINED              = false
HRV_STATUS                  = BLOCKED
HR_BR_STATUS                = HOLD / SUPPORTING_ONLY
```

`VS_DATASET_healthy_v1` 角色按已冻结裁决维持不变：

```
ROLE                  = SECONDARY_EXTERNAL_CORROBORATION_ONLY
UNTOUCHED             = FALSE
PRIMARY_GATE_ELIGIBLE = FALSE
C1_EVIDENCE           = NOT_PERMITTED
C2_EVIDENCE           = PERMITTED_SECONDARY_ONLY
CAN_AUTHORIZE_V2      = FALSE
```

## 8. 证据

- 本目录：report、`MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1_MANIFEST.json`、`ECG_SOURCE_FEASIBILITY_SCAN.csv`、`VALIDATION_SET_CONTRACT_PRECONDITIONS.csv`、`ERROR_LOG.json`、`HANDOFF.md`
- 脚本：`scripts/maintenance/run_mmwave_untouched_ecg_validation_feasibility_20260913.py`
- 权威本地证据（local-only）：`11_数据/derived/ECG_RSP独立验证资产审计_20260824.md`、`11_数据/derived/ecg_rsp_goldclean_reaudit_v1/goldclean_reference_summary.json`、`11_数据/derived/physiology_reference_v1/physiology_reference_session_audit.csv`
- 路径声明：`08_算法/configs/paths.local.json`（`calibration_root`、`preexperiment_root`、`formal_data_root`）
- Issue: #35