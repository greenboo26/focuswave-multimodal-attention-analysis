# mmWave HR candidate preregistration v1 (MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1)

Status: `FROZEN_PREREGISTRATION / NO_CANDIDATE_IMPLEMENTED / NO_RUN_PERFORMED`

RUN_ID: `mmwave_hr_candidate_preregistration_v1_20260913_r1`

Preregistered: 2026-09-13 (Asia/Shanghai)

Base commit: `97cfa4e9a539d4f5df63913b24f63a1288636b6c`

## 0. 这份文件是什么，不是什么

这是一份**候选方案预注册（preregistration）**：在任何实现、任何运行之前，先把"为什么怀疑、允许改什么、禁止改什么、什么算成功、什么算失败"写死并存进 canonical main。

它不是：

- 不是新算法、不是新 gating rule、不是新 threshold；
- 不是 candidate 实现（本文件冻结时**没有任何 C1/C2 代码被写出**）；
- 不是运行结果（**本任务没有跑任何 mmWave 数据**）；
- 不是 snapshot v2，也不授权 snapshot v2；
- 不是对 fusing/time/spectral estimator、target/bin/channel selector、harmonic correction、窗口的任何修改。

**冻结的意义**：本文件一旦进入 canonical main，C1/C2 的任何实现都必须与之逐条对齐。任何偏离（改判据、改阈值、换指标、换分母）都不再是本预注册的验证，必须新开一份预注册并说明理由。

## 1. 当前状态与为什么停止盲目试规则

| 工作线 | 状态 |
|---|---|
| `MMWAVE_INTEGRATION_SNAPSHOT_V1` | `PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED`（继续作为暂定多模态毫米波输入） |
| `MMWAVE_ESTIMATOR_IMPROVEMENT_V1` | `COMPLETE / NO_STABLE_IMPROVEMENT`（`BEST_CANDIDATE=NONE`，`V2_CANDIDATE_STATUS=NOT_FORMED`） |
| `MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1` | `MULTIFACTOR_MECHANISM_SUPPORTED` |
| HR/BR | `HOLD / SUPPORTING_ONLY` |
| HRV | `BLOCKED` |

low-bias 机制审计的关键事实（本预注册的机制依据，全部来自已有证据，未新增计算）：

- `CORRECT_OR_NEAR_CORRECT`（n=39）的 fused bias 仅 `+0.215472 bpm`、MAE `1.538915`；
- 总体 `-9.033106 bpm` 集中在三个失败类别：wrong peak 贡献 `-3.297976`、harmonic `-3.486216`、target miss `-2.332948`；
- `CONTROL_SPECTRAL` bias `-13.351010` 是三个 arm 中最偏低的；fusion 在 57/100 个 probe 上把结果拉低于 time arm，worsen/improve=`47/31`，净叠加 `1.460113 bpm`，
  并制造 4 个"time AE≤5 → fused AE>10"的转换；
- 距离只是弱且被 session/类别混淆的关联（Spearman ρ=`0.020855`），不是原因；
- 没有 probe 落在 ≈0.5×/≈2.0× 的谐波锁定位，但非谐波残留仍为 `-6.764500 bpm`。

**结论**：correct 类几乎无偏，说明这不是全局校准偏移。继续在原来 100 个 probe 上搜索规则（例如 `+9 bpm` 全局校正、distance gate、第四个 gating rule）**预期收益低且容易过拟合**，因此本预注册明确排除这些方向。

## 2. 冻结的开发集（development set）

以下集合已被反复用于 HR estimator/fusion 开发，**永久作为 development set，不得再作为验证集**：

- sessions: `9779`、`97793`、`97794`、`97795`、`97796`（即 raw 目录 `sub-9779_`、`sub-97793_`、`sub-97994_`（alias 97794）、`sub-97795_`、`sub-97796_`）；
- 设计：`single_person_repeated_measurement_ecg_rsp_calibration_reference`（同一名参与者的重复测量，**不是**参与者不重叠样本）；
- denominator: 5 sessions × 20 probes = 100 probe 窗口，`ECG_VALID=100/100`，窗口 `[window_effective_start, probe_onset)` nominal 30 s，DLL host receive/enqueue 时间源；
- 已被 ECG oracle 反复查看。

因此这 100 个 probe 上得到的任何新规则都**不构成验证**。

## 3. 被预注册的候选（只此两个）

只冻结两个机制来源明确的候选。两者都只允许改"如何选择/如何记住心率"，**不允许**改 target 选择、不允许改谐波校正、不允许改窗口。

### C1 — `C1_SPECTRAL_SCORING_NEUTRALITY`

**为什么怀疑它（机制依据）**

canonical producer 的频域候选打分是：

```
scores  = log(relative_power)                                  # 功率项
scores -= 0.035 * |candidate - time_bpm|                       # 向时域估计靠拢
scores -= 0.025 * |candidate - previous_bpm|                   # 向历史锚靠拢
scores -= 0.010 * |candidate - reference_bpm|                  # 向外部参考靠拢（正式运行中通常为 None）
best    = argmax(scores)
quality = sqrt(relative_power[best]) * exp(-|selected - time_bpm| / 20.0)
```

两个邻近项（`-0.035*|c-time|`、`-0.025*|c-previous|`）都以**已经偏低的** `time` 与 `previous` 为吸引子。机制审计显示 `spectral` 是三个 arm 中 bias 最负的（`-13.351010`），这与"谱峰被显著拉向低端"一致。因此怀疑：**邻近惩罚把谱峰选择系统性地拉低，且该拉低不由功率证据支持。**

**允许改什么**

只允许改这两个邻近项的形式或强度，且必须满足：

1. 只使用 mmWave 派生量（候选频率、功率、time_bpm、previous_bpm）与冻结常数（`HR_LO_BPM=48.0`、`HR_HI_BPM=120.0`、`HR_TIME_FREQ_WARNING_BPM=10.0`、`FS=100.0`）；
2. 冻结**至多一个**变体，且该变体在写入实现之前必须在本文件登记为 `C1_VARIANT`（见 §6 冻结规则）；
3. 只允许"削弱或移除邻近惩罚"这类**减少先验牵引**的方向，不允许新增任何以 ECG 为输入的项、不允许新增以距离为输入的项。

**禁止改什么**

- 禁止用 ECG 参与候选生成或选择（ECG 只能在候选生成**之后**用于评价）；
- 禁止改 `HR_LO_BPM` / `HR_HI_BPM` 频带；
- 禁止新增任何距离门、质量门或置信度门；
- 禁止改 `_fold_harmonic` 的容差（`0.20 * anchor`）；
- 禁止顺带修改 fusion 规则（那是 C2 的范围）；
- 禁止改 target/bin/channel 选择与窗口定义。

**什么算成功（C1 成功判据）**

在未触碰验证集上（见 `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`），以冻结 control（当前 producer 输出）为对照，同时满足：

- `C1_SUCCESS_1`：验证集 fused HR MAE 相对 control 改善 ≥ `1.0 bpm`；
- `C1_SUCCESS_2`：paired improve > paired worsen（probe 级配对，tie 不计）；
- `C1_SUCCESS_3`：没有单个 session 的 MAE 恶化 > `1.0 bpm`；
- `C1_SUCCESS_4`：`AE>10 bpm` 计数不高于 control；
- `C1_SUCCESS_5`：不新增 `control correct (AE≤5) → candidate AE>10` 的转换（0 个）。

**什么算失败（C1 失败判据）**

任一条成立即 `C1_FAILED`：

- `C1_FAIL_1`：上述五条任一不满足；
- `C1_FAIL_2`：候选在验证集上不可计算（例如返回 None 比例 > 0）；
- `C1_FAIL_3`：实现偏离本预注册（改判据/改阈值/换指标/换分母）；
- `C1_FAIL_4`：需要查看验证集结果后才能确定变体取值（即存在事后选择）。

### C2 — `C2_ANCHOR_PERSISTENCE`

**为什么怀疑它（机制依据）**

两处 anchor 逻辑会把历史值向前传播：

```
# 1) selector 内的滚动锚
if fused is not None and (previous_bpm is None or confidence >= 0.12):
    next_previous = fused if previous_bpm is None else 0.8*previous_bpm + 0.2*fused

# 2) course 级时间平滑
alpha      = 0.20 + 0.30 * clip(confidence, 0, 1)
target     = alpha * filled[i] + (1 - alpha) * smoothed[i-1]
smoothed[i]= clip(target, smoothed[i-1] ± 7.0)
```

`next_previous` 使用 `0.8` 的历史权重、`_smooth_track` 在低置信度时 `alpha` 仅 `0.20`，两者都让历史低估长期驻留。同时 anchor 是 fusion 在 `gap > 10 bpm`（本数据 31/100 个 probe）时"二选一"的判据，因此偏低的 anchor 会**偏向选中更低的那一路**。此外 `_fold_harmonic` 以 anchor 判定是否折半（`abs(half - anchor) <= 0.20*anchor`），偏低的 anchor 也会影响折半决策。

因此怀疑：**anchor 的持久化（高历史权重 + 低置信度低步长 + ±7 bpm 限速）把早期低估固化为后续估计的吸引子。**

**允许改什么**

只允许改 anchor 的**更新方式**，且必须满足：

1. 只使用 mmWave 派生量（`fused`、`time_bpm`、`confidence`、`previous_bpm`）与既有常数（`confidence>=0.12`、`±7.0 bpm/step`）；
2. 冻结**至多一个**变体，登记为 `C2_VARIANT`；
3. 允许的方向限于"让 anchor 更快脱离历史值 / 让低置信度时段不更新 anchor / 让限速更对称"，不允许引入 ECG、距离或新质量门。

**禁止改什么**

- 禁止用 ECG 决定 anchor 是否更新；
- 禁止改 `confidence>=0.12` 这个既有阈值的语义（若变体涉及它，必须在 `C2_VARIANT` 中逐字写明，且属于**预注册的一部分而非事后调参**）；
- 禁止改 `_fold_harmonic` 的容差；
- 禁止改 fusion 的加权平均公式（C1 范围之外的部分）；
- 禁止改 target 选择、窗口、频带。

**什么算成功 / 失败**

与 C1 使用**完全相同**的五条成功判据与四条失败判据（`C2_SUCCESS_1..5`、`C2_FAIL_1..4`）。两个候选必须使用同一套判据、同一分母、同一指标，不得各自挑选更有利的判据。

## 4. 冻结的对照与指标

**对照（control）**：canonical main 的当前正式 producer 输出，不做任何修改。

**指标（在验证集上计算）**：

| 指标 | 定义 |
|---|---|
| 主指标 | fused HR MAE（mean absolute error vs 金标准 ECG，单位 bpm） |
| 配对 | probe 级 paired improve / worsen / tie |
| 尾部 | `AE>10 bpm` 计数、`AE>20 bpm` 计数 |
| 灾难转换 | `control AE≤5 → candidate AE>10` 的 probe 计数 |
| 分层 | 每个 session 单独报告 MAE/bias；每个 failure class 单独报告 |
| 过程量 | bias、median AE、p90 AE |

**必须同时报告的边界**：session 数、participant group 数、probe 数、ECG 有效/无效/未解析、时间源、窗口定义、producer commit、候选 commit。

## 5. 验证门槛（运行前的硬前置）

C1/C2 **在以下条件全部满足之前不得运行**：

1. `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` 已建立并通过其自身 contract 检查；
2. 该验证集与 §2 开发集 **session 不重叠**且 **participant group 不重叠**（两者都要，不只是其中之一）；
3. 该验证集的 ECG 金标准是独立生成的 per-window gold-clean 参考，且其清洗规则与开发集**逐字一致**（同 `gold_standard_qa.py` 规则：0.5–40 Hz 带通、300–2000 ms IBI、相邻 IBI 相对变化 >20% 剔除、正常间期 ≥80%）；
4. 该验证集的 probe 窗口契约与开发集一致（`[window_effective_start, probe_onset)`、nominal 30 s、无 cross-block、DLL host receive/enqueue 时间源）；
5. 候选实现以**独立 commit** 冻结，且该 commit 只包含本预注册允许的改动；
6. 本预注册已进入 canonical main。

若验证集的 ECG 参考或 probe 窗口契约无法满足，则**不是**"换一个更宽松的验证"，而是 `PREREGISTRATION_BLOCKED`。

## 6. 冻结规则（防事后调参）

- **一次一候选**：C1、C2 分别独立评价，不得合并成一个"组合候选"后再报结果（组合会引入未预注册的交互）。
- **一个变体**：每个候选只允许一个 `C1_VARIANT` / `C2_VARIANT`。变体必须在**看到任何验证集结果之前**写入实现并记录 commit hash。
- **禁止事后选择**：若变体 A 失败，不得在同一预注册下改判据后再试变体 B。任何新变体需要新的预注册。
- **禁止看验证集调参**：验证集结果一旦被看过，该验证集即被消耗；不得在其上迭代。
- **失败即记录**：候选失败必须留下 negative result 记录（与 estimator improvement v1 同样的形式），不得删除。
- **禁止重定义**：不得重定义 failure class，不得改成功判据的数值，不得改主指标。

## 7. 结果处置

```
C1/C2 任一通过独立验证
    → 才有资格讨论 mmWave snapshot v2；v2 仍需单独的任务、单独的 contract 与单独的决定

C1/C2 全部失败
    → 保持 MMWAVE_INTEGRATION_SNAPSHOT_V1，不形成 v2

任一候选在开发集上"看起来更好"
    → 不作为证据；开发集已冻结，只能用于机制解释，不能用于放行

验证集被看过之后
    → 该验证集退出，需另建新的未触碰验证集
```

**明确不允许的结果表述**：`IMPROVED`、`FORMAL_HR_READY`、`SNAPSHOT_V2_READY`。

## 8. 与主分析线的关系

毫米波转为**受控验证并行线**，不再阻塞 Behavior / NIR / RGB 与正式多模态分析：

- `MMWAVE_INTEGRATION_SNAPSHOT_V1` 继续作为多模态的暂定毫米波输入；
- HR/BR 仍为 `PROVISIONAL / SUPPORTING / PHYSIOLOGY_LIMITED`，不得升级为已验证生理量；
- HRV 继续 `BLOCKED`；
- 任何含 mmWave 的监督学习结果继续保留 measurement-limited/supporting 解释。

## 9. 本任务未做的事（边界声明）

- 未运行任何 mmWave 数据；未训练模型；未产生 candidate 输出；
- 未修改 producer、target、window、fusion、harmonic、threshold；
- 未修改 snapshot v1；未形成 snapshot v2；未解锁 HRV；
- 未把 ECG 用于任何 production 选择；
- 未在本预注册中写入任何实现代码。

## 10. 证据与指针

- 机制依据：`docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`（report、`FUSION_PATH_AUDIT.md`、`MECHANISM_EVIDENCE_MATRIX.csv`、bias attribution）；
- 负结果：`docs/results/2026-09-12_MMWAVE_ESTIMATOR_IMPROVEMENT_V1/`；
- 冻结 cohort：`docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/`（116 sessions / 61 participant groups / 2,320 probes）；
- 验证集计划：`MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`；
- 判据登记：`CANDIDATE_SUCCESS_CRITERIA_V1.csv`；
- 代码路径常量：`scripts/process_vital_signs_v3_1_1.py`（`HR_LO_BPM=48.0`、`HR_HI_BPM=120.0`、`HR_TIME_FREQ_WARNING_BPM=10.0`；`_select_spectral_bpm`、`_fold_harmonic`、`_robust_time_bpm`、`_smooth_track`）。

Issue: #35（mmWave HR improvement mainline，保持 OPEN）。
