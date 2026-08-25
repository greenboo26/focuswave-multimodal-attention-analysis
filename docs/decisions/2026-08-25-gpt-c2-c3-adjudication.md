# GPT 裁决：C2 radar-only baseline 与 C3 NIR readiness

日期：2026-08-25
依据：`docs/decisions/2026-08-25-c2-c3-handoff.md`

## 一、总裁决

1. **C2 v1 接受为有效的第一版 baseline 结果。**
   - 当前证据不支持“现有 radar engineered features 对行为 baseline 有增量预测”。
   - 该结果不能扩大为“毫米波不能预测专注”。
   - 当前 `cardiac candidate` 仍为探索性特征，不是已验证 HR/IBI/HRV。

2. **C3 接受为 session-aligned 数据整合结果，但尚未具备正式 NIR 建模/融合条件。**
   - 下一优先级不是直接训练 NIR 或融合模型，而是恢复真实 participant identity，并建立与 C2 同一 probe universe 的 coverage crosswalk。

3. **暂不进入 Tac-Mamba/SCKD 式 teacher-student 或大型深度模型。**
   - 先完成评估审计、标签结构审计和 common-subset multimodal upper-bound；只有多模态对 radar-only 确有稳定增益时，知识蒸馏才值得投入。

4. **C1b 保持 blocked。** 正式 VS_DATASET 到位后再唤醒，不因 C2 结果改变 HRV 路线。

---

## 二、C2 v1 的关键解释

C2 结果：

- B0 behavior baseline ROC-AUC = 0.656
- R respiration = 0.622
- C cardiac candidate = 0.626
- M raw micromotion/phase descriptors = 0.609
- Q quality descriptors = 0.611
- RADAR_ALL = 0.593
- B0 + RADAR_ALL = 0.619
- grouped null N0 = 0.628

因此当前最严谨的结论是：

> 在既有 71-session / 1,317-probe M1/Q0 engineered feature matrix、当前 binary thought-probe endpoint、leave-one-repeat-participant-out 分组和固定 L2 logistic regression 下，没有观察到 radar feature 对 behavior baseline 的增量优势。

不能写：

- “毫米波无效”；
- “毫米波不能预测专注”；
- “HRV 路线失败”；
- “必须改成多模态部署”。

### 重要评估异常：N0 AUC = 0.628

普通常数/总体先验 null 的 ROC-AUC 理论上应接近 0.5。当前 grouped null 达到 0.628，说明在解释任何 0.60 左右的模型前，必须先审计 pooled out-of-fold prediction 是否受到 fold-specific prevalence / group base-rate / probe-time structure 的影响。

这不自动等于泄漏，但它意味着当前 pooled ROC-AUC 不能单独作为“存在传感器信号”的证据。

---

## 三、下一步第一优先：C2 evaluation/label audit（不要先上复杂模型）

### A. Null baseline audit

Codex 先明确 N0 的精确定义和生成方式，并新增至少：

1. `N_const`：训练折标签先验/常数预测基线；
2. `N_perm`：保持 participant/session grouping 的标签置换 null distribution（建议 >=1000 次）；
3. 检查将不同 LOPO fold 的概率直接拼接后，fold-specific intercept 是否人为产生跨 fold 排序；
4. 同时报告 pooled metric 与 participant/session-level macro summary；
5. 报告模型预测与 held-out participant label prevalence 的关系。

如果 N0 > 0.5 主要来自 group prevalence / fold intercept，应修正比较框架，但不得通过选择性重算只保留较好结果。

### B. 标签结构 audit

primary endpoint 暂时 **继续保留** `label=1` vs `label=2/3/4`，以保证与 C2 v1 连续性；此时不改标签。

但在进入 v2 前必须输出：

- 1/2/3/4 的原始 probe 文案和心理语义；
- 各标签总量；
- participant/session 内分布；
- probe 序号 / time-on-task 与标签关系；
- label transition / serial dependence；
- 每位 participant 是否同时包含两类 binary endpoint。

只有在原始 probe 语义支持时，才允许把 1-4 做 ordinal、high-confidence sensitivity endpoint 或其他重编码；不能仅因模型效果差而改标签。

### C. 简单 confound baselines

新增并单独报告：

- probe index / time-on-task only；
- session/order only（若设计允许）；
- behavior components 分解（不要只看汇总 B0）。

目的是回答当前 0.65 左右的可预测性究竟来自 task performance、时间趋势、participant base rate 还是真正状态变化。

---

## 四、C2 v2：在评估审计通过后再做 radar 表征改进

v2 的目标不是盲目提高 AUC，而是测试“现有 M1/Q0 汇总特征是否过度压缩了 radar 中的状态信息”。

优先顺序：

1. **60 s 内多尺度动态特征**：例如 10/20/30 s 子窗的均值、方差、趋势、变化率，而不是只保留整窗单一统计量；
2. respiration dynamics / spectral stability；
3. cross-channel coherence / 8-channel consistency；
4. target-lock / spatial-stability descriptors；
5. harmonic ambiguity descriptors；
6. raw phase / micromotion 的低维时序表示；
7. 在严格 nested grouped CV 下增加有限的非线性 baseline（例如 XGBoost / Random Forest / small temporal model），但必须与固定 logistic baseline 同表比较。

禁止：

- 根据 held-out participant 结果选窗口、阈值或特征；
- 直接上大型 Transformer/Mamba 并把改善归因于心理机制；
- 把质量描述符或微动特征命名成生理/心理指标。

---

## 五、C3：下一步不是训练，而是 identity + coverage crosswalk

目前 340 条 NIR probe-aligned rows 中：

- primary >=80% coverage：265
- 50-<80% sensitivity：10
- <50% / exclude：65
- participant_id 全部为空

因此 C3 下一步必须完成：

1. 从现有 session/recording metadata、行为表和 repeat_participant_id 映射中恢复 participant identity；
2. 禁止通过 NIR 特征值、时间模式或模型推断身份；只能使用可靠 metadata/crosswalk；
3. 建立 NIR 340 rows 与 C2 1,317 probe universe 的 key-level overlap 表；
4. 逐 session 列出缺失原因：无 NIR run / 时间不覆盖 / QC <50 / key mismatch / 其他；
5. identity 恢复后，才允许做 participant-disjoint NIR-only baseline。

### 公平多模态比较规则

未来比较 `radar-only / NIR-only / behavior / radar+NIR` 时，必须至少提供一组 **完全相同 probe rows + 完全相同 participant folds** 的 common-subset comparison。

不能用：

- radar 的 1317 行结果
- 对比 NIR 的 265 行优质子集结果

然后直接把性能差异解释成“模态优劣”。样本构成不同会造成严重选择偏差。

---

## 六、什么时候进入多模态 teacher -> radar-only

先完成：

1. C2 evaluation/label audit；
2. radar v2；
3. participant-aligned NIR-only baseline；
4. common-subset multimodal upper-bound。

只有当 multimodal upper-bound 相比 radar-only 在相同 rows / folds 上表现出稳定、可重复的增益，才进入：

`mmWave + NIR/behavior/RGB teacher -> mmWave-only student`

Tac-Mamba/SCKD 继续作为工程范式参考，不作为本项目认知状态效度证据。

---

## 七、当前面向用户的项目状态（不用内部编号解释）

- **毫米波 HRV 验证线**：协议已准备；缺正式 ECG-radar 公共数据，暂时等待。
- **毫米波直接预测专注线**：第一版 baseline 已完成；当前 engineered radar features 没有超过 behavior baseline，下一步先审计 null/标签结构，再改进 radar 时序表征。
- **NIR 多模态线**：时间对齐已做到 probe-level，但真实 participant identity 尚未恢复；先做身份和 coverage crosswalk，再做 NIR-only / multimodal 比较。

这三条线继续并行，不因 C2 v1 的中性/负结果放弃 radar-only 产品目标。
