# C2 evaluation/label audit 与 C3 identity/coverage crosswalk handoff

日期：2026-08-25
决策依据：`e1aa14474c55ee630bb6eaf58fa139f45fe35190`

## 状态

- `C2 evaluation/label audit = COMPLETE / awaiting adjudication`
- `C3 identity + coverage crosswalk = COMPLETE / one identity blocker remains`
- 未进入 C2 v2 动态特征、复杂模型或 teacher-student。
- C1b 仍为 `BLOCKED`，未调 VitalSense 示例。

## C2 evaluation/label audit

### RUN_ID 与范围

- `RUN_ID`: `C2_EVALUATION_LABEL_AUDIT_V1_20260825`
- 输入：1,317 probe、71 session、46 个已恢复 participant identity。
- 分组：leave-one-`repeat_participant_id`-out。
- primary endpoint 保持 `label 1` 对 `label 2/3/4`，未改标签、split、阈值或排除规则。
- 只读取既有矩阵、预测表、participant/session master 和当前 FocusWave 程序资产，未扫描原始 NPZ。

### null 与混杂审计

原 `N0_grouped_null` 并不是常数 null，而是使用 `block_num`、`block_probe_fraction`、`onset_rel_s` 的 time/block covariate logistic model。因此它达到 AUC > 0.5 不代表使用了传感器信息。

| 基线 | pooled OOF AUC | participant/session macro AUC | 解释 |
|---|---:|---:|---|
| `N_const` 训练折先验常数 | 0.141 | 0.500 | pooled 值受 fold 间常数排序影响，不能单独解释为信号 |
| `N0` grouped time covariates | 0.628 | participant 0.627 / session 0.636 | 时间/区组结构，不含 radar |
| probe index / time-on-task | 0.610 | participant 0.614 / session 0.619 | 简单时间混杂基线 |
| session repeat-order | 0.433 | participant 0.508 / session 0.500 | 仅为 participant 内重复次数，不是全局日历时间 |
| prior RT component | 0.617 | participant 0.626 / session 0.634 | 行为分量 |
| prior error component | 0.665 | participant 0.666 / session 0.677 | 行为分量 |
| B0 behavior components | 0.656 | participant 0.665 / session 0.675 | 行为 baseline |

participant/session-preserving permutation 已完成 `1000/1000` 次：在每个原始 session 内置换 binary target，保留 session label prevalence、participant/session 归属和 LOPO 结构。`N0` observed AUC `0.6281`，置换均值 `0.5148`，中心 95% 范围 `[0.4978, 0.5294]`，双侧经验 `p=0.0010`。

这说明 N0 的时间/区组结构确实不是随机噪声，但它仍然不是 radar 证据。任何对 radar AUC 的解释都必须同时报告 time/task baseline 和 participant/session macro summary。

### 标签审计

当前程序资产中的原始 probe 文案为：

1. 完全专注于分拣任务；
2. 关注实验本身，但没有聚焦于分拣任务；
3. 在想与实验无关的事情；
4. 大脑空白，没有明确想法。

标签数量：`1=974 (73.96%)`，`2=219 (16.63%)`，`3=47 (3.57%)`，`4=77 (5.85%)`。

描述性结构：ordinal label 与 `probe_id` 的 Spearman `rho=0.127`，与 `block_probe_fraction` 为 `0.123`，与 `onset_rel_s` 为 `0.180`；部分标签存在序列依赖，例如 `1→1` 条件概率 `0.851`、`4→4` 为 `0.569`。

这些结果只描述标签结构，不支持在本轮把 1–4 重编码为 ordinal，也不改变当前 binary primary endpoint。另一个限制是：文案已由当前 FocusWave 资产确认，但所有历史 C2 session 是否使用完全相同的程序版本/素材仍未完全核验。

## C3 identity + coverage crosswalk

### RUN_ID 与规则

- `RUN_ID`: `C3-IDENTITY-COVERAGE-CROSSWALK-V1-20260825`
- NIR 输入：340 rows、17 NIR sessions。
- C2 probe universe：1,317 rows、71 subject/session keys。
- 身份只能来自现有 metadata/crosswalk；未使用 NIR 特征、NIR 时间模式或模型推断。
- strict overlap key：subject + probe_id + exact absolute onset。
- 本次不做模型、不做 LOSO。

### 结果

- 17 个 NIR session 中，16 个恢复到 `repeat_participant_id`。
- subject `070` 缺少真人证据，保持空值并标记 `unresolved_blocker`。
- 严格同一 probe：289 rows。
- 仅 subject 编号相同、probe 不一致：31 rows，不视为同一 probe。
- NIR-only key mismatch：20 rows，实际为 subject `067`。
- C2-only、无对应 NIR probe row：1,028 rows。
- overlap union：1,368 rows，无重复 probe key。
- NIR QC：`<50% = 65`，`50–<80% = 10`，`>=80% = 265`。
- session failure audit：`no_nir_run=55`，`key_mismatch=10`，`QC<50=8`，`identity_unresolved=1`。

C2 表没有 `session_id` 字段，因此即使 probe 和绝对 onset 完全一致，本次也只称为“同一 probe”，不声称“同一 session”。

## 当前裁决请求

1. 是否确认当前 binary endpoint 继续作为 C2 primary endpoint，直到完成历史程序版本核验。
2. 是否接受将 N0 作为 time/block structural baseline 单独报告，而不再称为 generic null。
3. subject `070` 的身份材料补齐前，不将其用于 participant-disjoint NIR 分组。
4. 在 `289` 条严格 common probe 上，是否批准下一步建立 NIR-only 与 radar/NIR/behavior common-subset baseline；不得使用各自不同样本量直接比较模态优劣。

## 禁止的当前表述

- 不得把 N0 的 AUC 解释为传感器信号。
- 不得把 C2 audit 结果写成“毫米波不能预测专注”。
- 不得把 1–4 标签在本轮改称 ordinal 或重新编码。
- 不得把 C3 session crosswalk 写成 participant identity 已全部恢复。
- 不得进入 C2 v2 或 teacher-student，直到上述评估和 common-subset 决策完成。
