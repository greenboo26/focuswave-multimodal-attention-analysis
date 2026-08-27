# 毫米波任务 2R：AgeBalanced 50 s 外部方法续跑

Status: `READY_TO_DISPATCH`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。

## 1. 为什么续跑

原 Task 2 在 30 s / 10 Hz 条件下停止，因为 SSA 的公开参数 `L=400` 需要至少 400 个连续样本，而 30 s 只有约 300 点。这个 `BLOCKED` 只说明“论文原参数不能直接用于 30 s 输入”，不说明 SSA+VMD 无效，也不说明项目历史方案已经被判定为最终失败。

AgeBalanced 是外部验证数据。外部方法比较不需要被 FocusWave 产品 30 s 更新时间强行限制。因此新增一个独立的 **50 s method-native external comparison**：

- 30 s：保留为 FocusWave 产品/主分析窗口；
- 50 s：只用于 AgeBalanced 上按论文更接近的输入长度比较外部方法；
- 两条轨道结论不得混写。

## 2. 本轮唯一目标

在 AgeBalanced development 30 participants / 60 Rest sessions 上，用 **50 s / 5 s** 窗口完成：

1. SSA+VMD / EE-PCC-VMD 的最小可复现实现；
2. 项目历史方案同步改为 50 s / 5 s；
3. 两者在相同 ECG reference、相同 session、相同窗口起点、相同评价指标下比较。

本轮不是重新开发毫米波算法，也不是证明 50 s 能直接用于最终 FocusWave 产品。

## 3. 数据与输入

只允许：

- AgeBalanced development 30 participants；
- 每人 Lying/Rest + Sitting/Rest，共 60 sessions；
- radar 10 Hz 表示；
- 50 s window / 5 s step；
- `ecg_reference_v1`；
- 已确定的 participant split；
- 已登记来源论文、参数和 `vmdpy` 组件。

禁止：

- 不看 80 held-out；
- 不访问正式 `J:\Data`；
- 不用本地单被试 BIOPAC 数据调 SSA/VMD 参数；
- 不恢复 HRV；
- 不扩展到第二个外部算法家族；
- 不根据结果反复搜索 `L/K/alpha` 直到变好。

## 4. SSA+VMD 参数处理

优先严格采用已恢复的公开参数：

- SSA `L=400`；
- VMD `K=5`；
- `alpha=1000`；
- 其余公开参数按 Task 2 provenance 记录执行。

50 s × 10 Hz ≈ 500 点，因此 `L=400` 在长度上可实现。

如果论文的重构秩、分量筛选、EE/PCC 选择规则仍有多个合理解释：

- 先按已有证据恢复；
- 无法唯一恢复的部分明确记录 `MISSING_EVIDENCE`；
- 不允许用 ECG 真值逐窗口选择最优解释；
- 若必须做一个工程选择，应在 development 内一次性说明依据，并标记为 `paper_reimplementation/adapted`，不能称作者官方复现。

## 5. 为什么项目历史方案也要跑 50 s

如果只让 SSA+VMD 看 50 s、项目方案仍只看 30 s，就无法判断差异来自“算法”还是“多看了 20 s 数据”。

因此本轮必须产生同条件比较：

| 方法 | Window | ECG reference | Development participants |
|---|---|---|---|
| 项目历史方案 | 50 s / 5 s | ecg_reference_v1 | 同 30 人 |
| SSA+VMD | 50 s / 5 s | ecg_reference_v1 | 同 30 人 |

历史 25 s 和产品 30 s 结果保留作为旁证，但不能与 50 s 直接做“谁更强”的主比较。

## 6. 输出格式

现有 `per_window_benchmark_v1` 只允许 10/30/60 s，因此 **不要为了本轮外部验证修改主 schema**。

50 s 结果单独输出为 `method_native_external_50s` development artifact，字段尽量复用现有 benchmark 字段与评价代码，并明确：

- `comparison_role = method_native_external`
- `window_s = 50`
- `product_window_claim = false`

这是一条外部方法比较轨道，不是 FocusWave 30 s 产品输出合同。

## 7. 必须报告

同一 development cohort 上至少报告：

- coverage；
- MAE；
- median AE；
- RMSE；
- Pearson / Spearman；
- Bland–Altman bias / LoA；
- P90 AE；
- 2x / 0.5x 明显锁频；
- quality strata；
- 失败窗口数量与主要失败模式。

AgeBalanced 没有 RSP，因此 `respiratory_harmonic` 仍为 `NOT_ASSESSABLE`，不能记为 0。

另增加一个很小的解释表：

- 项目方案 25 s historical-equivalence；
- 项目方案 30 s product-window development；
- 项目方案 50 s external-comparison；

只用于说明“窗口/评分条件会怎样改变项目方案表现”，不能把不同口径的 MAE 直接排名。

## 8. 进入 80 人的条件

50 s development 完成后停止并给出建议。

只有满足以下条件才建议进入 80 held-out：

1. SSA+VMD 可复现实现已经确定，关键参数/选择规则不再根据 80 人调整；
2. 项目历史方案与 SSA+VMD 均可在 50 s 同条件稳定运行；
3. development 结果显示至少一个方案具有继续外部泛化验证的现实价值；
4. 80 人将按已经确定的 50 s 条件一次性比较，不能看完结果再改参数重跑并继续称其为 untouched held-out。

如果 SSA+VMD 仍因方法细节无法可靠实现，则 `BLOCKED`；这次才是真正的“公开信息不足”，而不是 30 s 长度限制。

## 9. 本地 RS6240 + BIOPAC 的角色

本轮不执行本地校准。

已查 `kyandi233-dev/FocusWave@ecg`：

- `11-calibrate-mmwave-ecg.py` 是静息→深呼吸→屏息→静息的专门机制校准程序；
- `12-test-breath-focus.py` 是同一被试机械按键 vs 专注 SART 的机制对照程序；
- 它们与正式实验不同，不能作为跨被试产品有效性证据。

因此本地 BIOPAC 数据后续只作为设备/机制/压力测试证据，不替代 AgeBalanced 多被试 ECG 外部验证。

## 10. 时间与模型

本轮目标时间：约 **2–2.5 h**，计入毫米波约 10 h 总预算。

主线程：**GPT-5.6 Terra / medium**。

Luna/low 可做：参数对账、manifest、schema-like 输出检查、机械汇总。

只有在需要改变科学比较规则或解释重大矛盾时才升级 Sol / medium；默认不使用 Sol/high。

## 11. 完成后只返回

- `PASS / PARTIAL / BLOCKED`；
- 50 s 项目方案结果；
- 50 s SSA+VMD 结果；
- 同条件比较表；
- 关键 provenance / 参数解释；
- 是否建议进入 80 held-out；
- 若进入 80，明确待执行的唯一 50 s 配置；
- commit SHA。

完成后停止，不自动运行 80 人。
