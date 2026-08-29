# FocusWave 历史毫米波距离口径影响范围审计

状态：**PARTIAL / evidence-bounded**。本审计只读毫米波和 ECG/RSP 校准数据；未读取 NIR/RGB，未改算法、未重跑 formal 70 场、未训练分类器。

## 已核验的换算与 gate

- 正式尺度：`distance = bin × 0.037 m`；历史分析错误尺度：`bin × 0.08 m`。
- v3.1.1 的历史 `0.30–1.50 m` gate 实际只允许 **bins 4–18**，即真实 **0.148–0.666 m**；正确同名 gate 应为 **bins 9–40**，即约 **0.333–1.480 m**。
- 因此错误不是单纯数值标签：凡调用 v3.1.1 距离 mask 的校准/producer，target 候选集合可能变了；没有 mask 的 scanner/M1 则不能据此说 target 被改写。

## 最小反事实

sub2_breath_hold: bin/channel 10/ch1 unchanged; fused HR 103.5 bpm unchanged; only 0.80→0.37 m.

该 pair 是直接证据：错误尺度**不必然**改变 target 或 HR。它不是对所有校准/正式 session 的证明。原计划其余代表片段在 v3.1.1 VMD 候选分解耗时过长时停止；没有以替代算法补算，因此不制造 HR/BR/HRV 结论。

## 三套 cohort 的结论

### BIOPAC/ECG-RSP calibration

v3.1.1、gold-anchor 和历史分段校准在选 bin 前确实使用 0.08 mask，归类为 **POTENTIALLY_AFFECTED**。已有完整 pair 未改变 bin 或 HR，尚无 `CONFIRMED_AFFECTED`。报告中的 HR course 约 4.61 bpm 不能称为已被距离 bug 排除影响；在少量好/坏 HR 与 RSP 对照片段完成同一 gate-only 重算前，应保持“待复核”，而非宣告失效。

### prepilot

C1c/C1d 使用冻结的 channel/bin 重放，不含 0.08 metre conversion 或 distance gate，逐搏 HRV 的这些重放/后端比较为 **UNAFFECTED**。若历史图文把 bin×0.08 写成米，则该文字为 **LABEL_ERROR_ONLY**。

### formal experiment

J target-lock scanner 先全 bin 选目标、后用 `bin×0.08` 贴距离：选 bin 本身为 **UNAFFECTED**，但 36 场基于 `0.20–1.00 m` 的 target-plausibility 标签为 **LABEL_ERROR_ONLY**，应按 37 mm 重释。71 场中原口径有 35 场落入该 gate；校正后是 49 场（16 场新进入、2 场退出），因此不能沿用旧的距离 QC 人数。正式 timeline producer 若实际调用 v3.1.1，则为 **POTENTIALLY_AFFECTED**。M1 task-dynamics 是独立的整数 gate `8–180`，没有直接 0.08 或 v3.1.1 mask 依赖；因此 M1、C2B/C2C 和 alertness 的现有结果对**本次 0.08 bug 为 UNAFFECTED**（不等于已验证其 target 一定是人体）。

正式 71 场的距离 QC transition 已单独写入 `FORMAL_37MM_DISTANCE_QC.csv` 与 `FORMAL_DISTANCE_QC_CHANGE_SUMMARY.csv`；这一步保留 selected bin、不重选 target。71 场是有 mmWave 的审计全集，canonical mainline 仍保持 70-session denominator；`sub-067`、`sub-099` 的既有 provenance 不被本次修正改写。

Transition：`PASS→PASS=33`、`PASS→FAIL=2`、`FAIL→PASS=16`、`FAIL→FAIL=20`。校正距离分布为 `<0.20 m=4`、`0.20–0.30 m=12`、`0.30–0.60 m=32`、`0.60–1.00 m=5`、`1.00–1.50 m=0`、`>1.50 m=18`。

## 近距离强反射

本轮没有新增“已证实误选”证据。错误 gate 曾把真实 0.148–0.296 m 的 bins 4–8 纳入，而正确 0.30 m 下界会排除它们，故其风险仍是 **高风险但未证实**；首个完整 pair 在 bin 10 未变，反而排除了“必然误选”的说法。

## 下一步（需决策后才执行）

仅补做少量 ECG/RSP calibration 的 gate-only pair（至少一个 HR 差、一个 BR 差片段），若 target 或 ECG/RSP 误差显著改变才升级为 `CONFIRMED_AFFECTED` 并决定相关结果重算；不自动扩展到 formal 70。
