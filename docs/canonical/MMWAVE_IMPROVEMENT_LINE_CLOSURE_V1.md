# mmWave HR improvement line — closure v1

Document ID: `MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1`

Status: `LINE_PAUSED / OPT_A_INVALID / C1_C2_PAUSED_PENDING_NEW_COLLECTION`

Date: 2026-09-13 (Asia/Shanghai)

Base commit: `edb83e8be02dd637b16ea5bd2fb3a54d0e3f4752`

## 1. 裁决（权威）

正式 FocusWave cohort **从实验设计起就没有 ECG**。据此：

| 决定 | 值 |
|---|---|
| `OPT_A` | **无效**（其定义要求为正式 cohort 生成独立 per-window gold-clean ECG 参考，输入在设计上不存在） |
| `REM_1`（搜索"漏掉的正式 ECG"） | **不执行** |
| 错误性质 | **corrected planning error**，不是"未解的数据位置问题" |
| `C1_SPECTRAL_SCORING_NEUTRALITY` | `PAUSED_PENDING_NEW_COLLECTION` |
| `C2_ANCHOR_PERSISTENCE` | `PAUSED_PENDING_NEW_COLLECTION` |
| 替代验证集搜索 | 停止 |
| snapshot v2 | 不形成 |

## 2. 为什么这是规划错误

`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1` 与 `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1` 曾把 `OPT_A` 描述为"可用、只差一个可工程补齐的 ECG 参考"，并给出路由"`OPT_A` to be built next / `PROCEED_AS_PRIMARY`"。

**该路由已作废。** 错误链条：

1. 第一轮 preregistration 盘点只看了内部来源，**先把 `OPT_A` 当成可行基线**；
2. 第二轮外部资产审计只问"外部数据能不能替代"，**没有回头质疑 `OPT_A` 自身是否可行**；
3. 第三轮才去核对前提，于是发现"正式 cohort 有没有 ECG"这个**从未被验证的假设**是假的。

根本原因：**规划阶段没有把"参考信号是否存在"列为可行性前提**，而是默认了它存在。正确做法是在写任何验证计划之前先做输入可行性门（是否存在参考采集、是否可对齐、是否有时间基准）；本文件即为该门的补做与结论。

## 3. 保留的成果（不重跑）

| 资产 | 状态 | 角色 |
|---|---|---|
| `MMWAVE_INTEGRATION_SNAPSHOT_V1` | `PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED` | 继续作为多模态毫米波输入 |
| `MMWAVE_ESTIMATOR_IMPROVEMENT_V1` | `NO_STABLE_IMPROVEMENT` | negative development result |
| `MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1` | `MULTIFACTOR_MECHANISM_SUPPORTED` | 机制证据（正确类几乎无偏；低估集中在失败类别） |
| HR/BR | `HOLD / SUPPORTING_ONLY` | 不变 |
| HRV | `BLOCKED` | 不变 |

## 4. 外部资产角色

```
VS_DATASET_healthy_v1      ROLE = SECONDARY_EXTERNAL_CORROBORATION_ONLY
                           UNTOUCHED = FALSE
                           PRIMARY_GATE_ELIGIBLE = FALSE
                           C1_EVIDENCE = NOT_PERMITTED
                           C2_EVIDENCE = PERMITTED_SECONDARY_ONLY
                           CAN_AUTHORIZE_V2 = FALSE
AgeBalanced_60GHz          ROLE = HISTORICAL_EXTERNAL_BENCHMARK
mmWave_Heartbeat (TI gby)  ROLE = INELIGIBLE
```

## 5. 重新激活条件

C1/C2 仅在以下条件同时成立时可解除 `PAUSED`：

1. 存在**新采集**的数据集：participant/session 与现有开发集不重叠；
2. 该数据集**同时**具备同步 mmWave 与 ECG；
3. 可满足冻结窗口契约 `[window_effective_start, probe_onset)` nominal 30 s、block-truncated、无 cross-block、DLL 时间源；
4. 通过 `VS_1`–`VS_10` 全部 contract 检查；
5. 预注册的成功/失败判据保持不变。

在这些条件满足之前，不做任何 C1/C2 实现或运行。

## 6. 控制权交接

```
MMWAVE_IMPROVEMENT_LINE = PAUSED
MMWAVE_INTEGRATION      = READY
MAIN_ANALYSIS           = PROCEED
```

毫米波不再是主分析的阻塞项。主分析线顺序：Behavior feature freeze → NIR freeze → RGB freeze → 统一 feature registry → 单模态正式分析 → 多模态增量分析。

## 7. 证据

- 本文件：`docs/canonical/MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md`
- 前提核查：`docs/results/2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1/`
- 机制证据：`docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`
- 预注册：`docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md`
- Issue: #35
