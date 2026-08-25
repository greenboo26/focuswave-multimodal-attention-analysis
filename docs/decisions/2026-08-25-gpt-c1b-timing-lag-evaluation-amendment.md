# GPT 裁决：C1b ECG–Radar 时间延迟评价协议修订（官方结果前冻结）

日期：2026-08-25  
分支：`codex/gpt-codex-handoff-20260825`  
状态：`FROZEN_PRE_RESULT_AMENDMENT`

## 1. 为什么现在修订

本修订发生在官方 VitalSense MATLAB 24 人正式结果产出之前，目的不是为了改善某个已经看到的结果，而是纠正原 C1b 中“用单一固定延迟代表全部 ECG–Radar 时间差”的解释风险。

原 C1b 使用 `VS01 Resting` 估计一次约 `−18 ms` 的固定延迟，并将其冻结用于其余场次。该做法可以防止逐被试、逐场次或逐窗口调参，但这个数不能被解释为 BIOPAC、Mindray 或雷达硬件本身的固有延迟。

ECG R 峰与雷达心搏峰之间的观测时间差至少可能同时包含：

1. 参考设备/前端滤波及采样链延迟；
2. 两设备时钟或时间轴残余偏差；
3. ECG 电活动到胸壁机械活动之间的生理机电延迟；
4. 雷达滤波、模板和峰值定位算法本身选择的机械事件位置及算法延迟。

因此，从一个被试一个场次得到的单一 `−18 ms` 不能代表上述四项的普遍常数。

## 2. BIOPAC 与 C1b 必须分开

当前 VS_DATASET C1b 的参考设备是 Mindray，不是 BIOPAC。因此 BIOPAC 官方硬件/模块延迟不能直接用于修正 VS_DATASET 的 ECG–Radar 时间轴。

BIOPAC 延迟问题只适用于后续“本项目 RS6240 + BIOPAC”验证。到那一步，应把以下项目分别记录：

- BIOPAC 主机触发/采样延迟；
- ECG 模块及其滤波设置产生的延迟；
- RS6240 设备时间与实验绝对时间的同步误差；
- ECG→机械心搏的生理延迟；
- 雷达算法的峰定位延迟。

禁止把这些量合并命名为一个笼统的 `device delay`。

## 3. 原 C1b 结果如何处理

原 C1b 结果不删除、不覆盖。

`VS01 Resting → −18 ms` 的固定延迟结果保留为：

`LEGACY_FIXED_OFFSET_SENSITIVITY`

其用途是与已经完成的第一版 benchmark 保持可追溯性，不再作为“真实设备延迟”或唯一主要评价依据。

原有 ±50 / ±75 / ±100 / ±150 ms 结果也全部保留。

## 4. 官方 VitalSense 复现后的时间评价分两层

### 4.1 第一层：绝对时间定位能力

每一种雷达逐搏算法都必须先报告“不做任何延迟校正”的原始时间关系：

- ECG R 峰数；
- radar beat 数；
- 一对一匹配数；
- Precision；
- Recall；
- F1；
- ±50 / ±75 / ±100 / ±150 ms 全部结果；
- 成功匹配对中的 `radar_time - ecg_R_time` 分布；
- 该分布的中位数、四分位距和参与者间分布；
- Resting 与 Apnea 分开报告。

这一层回答：

> 该算法检测到的雷达机械事件，实际位于 ECG R 峰前后什么位置，偏移是否稳定。

禁止先把所有雷达峰强行移到 R 峰附近再报告这一层结果。

### 4.2 第二层：训练集估计、测试集冻结的算法特异性固定延迟

允许每一种算法拥有自己的“全局固定延迟校正”，因为不同算法可能选择不同的机械波形位置。

但必须严格 subject-disjoint：

1. 对每一个测试被试折，只使用训练被试数据估计该算法的固定延迟；
2. 训练集内允许在预先冻结的 `−250 ms` 到 `+250 ms` 范围内，以 1 ms 步长搜索一个全局 offset；
3. 选择使训练集 ±75 ms 一对一匹配 F1 最大的 offset；
4. 若多个 offset 并列，选择绝对值最小者；若仍并列，选择数值较小者；
5. 得到 offset 后立即冻结；
6. 测试被试、测试 session、测试窗口不得再次调 offset；
7. 每折必须保存训练得到的 offset。

最终报告：

- raw/no-offset 结果；
- train-only fixed-offset 结果；
- legacy `−18 ms` 结果。

三者必须分开命名，不能混在一张“最佳结果”里。

## 5. 为什么不能逐被试调 delay

逐被试或逐 session 用 ECG 找最优 delay，会把测试答案用于校正雷达结果。

这会造成一种虚假的提升：只要把每个人的雷达峰整体平移到 ECG 附近，Precision/Recall 就可能明显增加，但这种算法在没有 ECG 的真实部署中无法获得该平移量。

因此正式结论禁止：

- participant-specific lag；
- session-specific lag；
- window-specific lag；
- 根据测试集结果选择 delay；
- 根据官方 VitalSense 测试结果再改变搜索范围。

## 6. HRV/IBI 评价与绝对峰位必须分开

心率变异性（heart rate variability [HRV]）主要依赖相邻心搏间期，而不是要求雷达机械峰与 ECG R 峰发生在完全相同的绝对时刻。

若雷达对每一拍都稳定晚一个常数，例如每拍均晚 100 ms，则该常数在相邻时间点相减时会抵消，理论上仍可能得到正确的心搏间期（inter-beat interval [IBI]）。

因此后续必须同时报告两个问题：

**问题 A：绝对事件定位是否准确？**  
使用 Precision / Recall / F1 / lag distribution 回答。

**问题 B：逐搏间隔是否准确？**  
在一对一匹配后，必须额外报告：

- 匹配 beat 覆盖率；
- 连续可评价 IBI 的数量与覆盖率；
- IBI MAE；
- IBI median absolute error；
- IBI 偏差及 95% 一致性范围（Bland–Altman）；
- participant-level IBI 结果分布。

禁止只在少量成功匹配 beat 上报告一个很小的 IBI MAE，却不同时报告覆盖率。

## 7. RMSSD / SDNN 的解释门槛

当前阶段不因为代码可以计算 RMSSD 或 SDNN 就宣称 HRV 已验证。

只有在逐搏检测和连续 IBI 覆盖已经达到可信水平后，才进入正式 HRV 一致性评价。正式 HRV 评价还必须确认分析时长是否适合对应指标。

因此官方 VitalSense 复现当前优先级仍是：

1. Precision / Recall / F1；
2. beat coverage；
3. consecutive IBI coverage；
4. IBI accuracy；
5. 之后才是 RMSSD / SDNN。

## 8. 对官方 VitalSense 三方法比较的冻结要求

官方 MATLAB 复现完成后，在完全相同 ECG evaluator 下比较：

1. `project_bandpass_peak`；
2. `Python VitalSense-inspired AMF`；
3. `official MATLAB VitalSense2024 RWAMF`。

每种方法都必须同时给出：

- raw/no-offset；
- train-only algorithm-specific fixed-offset；
- legacy `−18 ms` sensitivity；
- ±50 / ±75 / ±100 / ±150 ms；
- Resting；
- Apnea；
- overall。

不允许只展示对某一种算法最有利的 offset 或 tolerance。

## 9. 对结果的预先解释规则

- 若 raw Recall 低，但 train-only fixed-offset 后明显提高：主要问题包含稳定的算法/生理事件位置偏移，不能简单解释为大量漏搏。
- 若 ±75 ms 低、±150 ms 明显提高：提示时间定位偏移/抖动是重要因素。
- 若固定 offset 后、甚至 ±150 ms 下仍低：才更支持真实漏检、误检或心搏候选选择失败。
- 若 IBI 在较高连续覆盖下准确，但绝对 lag 较大：说明算法可能稳定检测到某个机械心搏事件，HRV 价值需要单独评估。
- 若 IBI MAE 小但连续覆盖很低：不得宣称 IBI/HRV 已验证。

## 10. 执行顺序

MATLAB 环境现已到位后，Codex 应：

1. 从官方复现 checkpoint 继续，不重复环境前的审计；
2. 先跑官方 sample；
3. 再跑 VS01–VS24 × Resting/Apnea；
4. 保存官方 radar beat；
5. 在看到正式比较结果之前实现本文件规定的 evaluator 修订；
6. 一次性输出 raw、train-only fixed-offset、legacy offset 三套结果；
7. 更新 `WORKSPACE_LEDGER.md`；
8. handoff 给 GPT/user，停止自动进入 V2 算法开发。

## 11. 当前科研边界

本修订不否定已经完成的 C1b benchmark。它重新定义了该 benchmark 中“延迟”的解释：

> 单一固定 offset 是评价校准参数，不是硬件固有延迟，也不是 ECG→雷达机械事件的普遍生理常数。

后续所有文档必须保持这一表述。
