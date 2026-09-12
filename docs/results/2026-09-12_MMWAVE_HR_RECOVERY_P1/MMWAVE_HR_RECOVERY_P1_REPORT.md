# FocusWave mmWave HR recovery P1 paired A/B report

日期：2026-09-12  
任务：`mmwave_hr_recovery_p1`  
状态：`PASS / RESTORATION_NOT_SUPPORTED`  
研究边界：毫米波（millimeter wave [mmWave]）心率（heart rate [HR]）恢复链 P1；未执行 P2 failure attribution（失败归因）、P3 baseline personalization（基线个体化）、P5 30/60 s 比较、心率变异性（heart-rate variability [HRV]）或注意状态模型。

## 1. 结论

在冻结的 5-session / 100-probe / 30 s / DLL host receive-enqueue time（动态链接库主机接收/入队时间）/ pre-probe / ECG reference（心电图参考）分母上，P0 批准的 existing downstream bundle（既有下游模块束）没有改善 HR。Control 的 fused HR（融合心率）平均绝对误差（mean absolute error [MAE]）为 `10.4601 bpm`；restoration 为 `13.1737 bpm`，差值为 `+2.7136 bpm`。绝对误差逐 probe 比较为 improve/worsen/tie=`30/70/0`，五个 session 的 MAE 均劣化。因此 verdict 为 `PASS / RESTORATION_NOT_SUPPORTED`：P1 工程与配对审计完成，但该模块束不进入正式 producer。

此结论不是“producer 不具备这些函数”，也不是对历史 `3.7772146 bpm` 的否定。P0 已证明函数历史存在、当前遗漏且接口兼容；P1 进一步表明，在当前 DLL-time、30 s、逐 probe 动态 target 的同窗合同下，整束恢复不能复现历史收益。HR/BR（呼吸率）继续 `HOLD / SUPPORTING_ONLY`，HRV 继续 `BLOCKED`。

## 2. Reuse Gate 与源码身份

- canonical repository：`greenboo26/focuswave-multimodal-attention-analysis`；启动时 `origin/main=ac740c8ca449416562203d48c3ddc738c9d47bf7`；治理 `origin/main=add39f53560f5547db04bbfc0db2607c24ff45e5`。
- execution source：`16729b2ef245f9304dae8674f3bac433bc02e98c`；parent=`b2fddca2542859f62d5f4b57f1b4fdecd54a5b4c`；本地 exact git object、remote identity 和 DLL cutover 文件均重新核验。
- B2 frozen adapter SHA-256=`4854AAA20244FC35949E16F205072A2C45B0F7BAE939002CEB136C530DF3CB4D`；test SHA-256=`5D1195E3F86F7D6D1ADD4125E9C223314A236FAF9730D8DB374BFD0858D5865D`；历史 B2 output SHA-256=`967FCC304EF4DDAB3B9CA9F9C8F6BC2AC6C6D20C02C43D880DFD436ACCFF00D9`。
- P1 runner 与执行时内容字节相同，SHA-256=`D66BC4553042A9A6937DAD6843662C03AB5F03A3EA0E23D4BA77D795596FE148`；producer SHA-256=`BC65C2D2C99EBDFEDEA2500579CAEB45CB8918466CF788ADE718806BDD351FDA`。

Reuse Gate 为 `PASS`。Restoration 直接调用 `scripts/process_vital_signs_v3_1_1.py` 的 `_heart_segment_reference_correction()`、`_heart_window_consensus_bpm()`、`estimate_hr_time_course(..., reference_bpm=consensus_bpm)` 与既有 signal-quality hard gate（信号质量硬门）；没有复制实现、修改参数或引入 ECG 调参。

## 3. Control reproduction

在 restoration 修改前，冻结 B2 adapter/test 被放入 `16729b2` detached worktree 原样执行。新 control CSV 与历史 B2 CSV 均为 100 rows，逐单元格差异为 `0`，文件 SHA-256 完全相同。复现结果：fused HR MAE=`10.4601 bpm`、median absolute error（中位绝对误差）=`7.8590 bpm`、bias（偏差）=`−9.0160 bpm`、coverage（覆盖）=`100/100`；spectral HR（频域心率）MAE=`15.1134 bpm`，time HR（时域心率）MAE=`8.9695 bpm`。

`97792` 没有正式 probe 窗口，继续保持 frozen not-estimable（冻结不可估计），没有替换 session；P1 的 B2 分母仍为原 5 sessions / 100 probes。

## 4. 固定 A/B 与泄露控制

Control 保持冻结 B2 current chain。Restoration 只在完全相同的 target 后 heartbeat waveform（心搏波形）上增加：global periodogram base reference（全局周期图基础参考）→ 20 s/10 s segment correction（分段校正）→ window consensus（窗口共识）→ 以 consensus 作为 25 s/5 s course 初始 reference → existing global signal gate。

两臂首先独立完成 HR 估计；随后才读取已经冻结的 ECG 窗口结果计算误差。ECG 没有进入 target、bin/channel、candidate、threshold、gate 或参数选择。外部 RSP-guided harmonic correction（呼吸带引导谐波校正）明确传入 `None`。未改变 target、物理距离门、静态/直流/杂波处理、VMD（variational mode decomposition，变分模态分解）、beat detector（心搏检测器）、跨 probe persistence（持续性）、180 s baseline、窗口长度、标签、HRV 或下游模型。

## 5. 配对结果

| 指标 | Control | Restoration | 方向 |
|---|---:|---:|---|
| Spectral HR MAE, bpm | 15.1134 | 16.6626 | 劣化 1.5491 |
| Time HR MAE, bpm | 8.9695 | 10.6764 | 劣化 1.7069 |
| Fused HR MAE, bpm | 10.4601 | 13.1737 | 劣化 2.7136 |
| Fused median absolute error, bpm | 7.8590 | 11.7075 | 劣化 3.8485 |
| Fused bias, bpm | −9.0160 | −11.9765 | 负偏差扩大 2.9605 |
| Fused root mean square error（均方根误差 [RMSE]）, bpm | 14.2659 | 17.4762 | 劣化 3.2103 |
| Fused coverage | 100/100 | 100/100 | 不变 |

逐 probe absolute-error delta（绝对误差差，restoration − control）的平均值为 `+2.7136 bpm`，中位数为 `+0.2812 bpm`；improve/worsen/tie=`30/70/0`。大误差 probe 数从 `>10 bpm: 42`、`>20 bpm: 18`、`>30 bpm: 4` 增至 `56/28/9`。

| Session | Control MAE | Restoration MAE | ΔMAE | Control bias | Restoration bias | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| 9779 | 7.0291 | 8.7232 | +1.6941 | −5.8795 | −7.5772 | 20/20 → 20/20 |
| 97793 | 8.6141 | 9.5871 | +0.9730 | −7.1936 | −8.2524 | 20/20 → 20/20 |
| 97794 | 7.7967 | 9.7888 | +1.9922 | −4.9625 | −6.9163 | 20/20 → 20/20 |
| 97795 | 18.9463 | 23.9540 | +5.0076 | −17.4630 | −23.8254 | 20/20 → 20/20 |
| 97796 | 9.9144 | 13.8154 | +3.9010 | −9.5812 | −13.3114 | 20/20 → 20/20 |

同语义 course mean confidence（时间进程平均置信度）从 `.2856` 降至 `.2719`，中位数从 `.2339` 降至 `.2216`。两臂 producer internal usable ratio（内部可用比例）均值均为 `1.0000`。Restoration global gate hit=`0/100`，所以 gate 前后 HR、coverage 与 status 相同；missing/QC transition（缺失/质量状态转换）为 `ESTIMATED→ESTIMATED=100`。

## 6. Invariant 与 regression evidence

100/100 keys 一对一，无重复、无单臂缺失。逐 probe 核对 window start/end、frame i0/i1、frame-ID SHA-256、frame count、heartbeat SHA-256、DLL timestamp source/column、HR/BR bin/channel、distance proxy、BR、phase stability、motion、ECG/RSP reference 与状态，越界差异为 `0`，因此 `INVARIANT_GATE=PASS`。

Exact-source tests：Issue #33 probe contract、DLL timestamp、B2 content 与 P1 narrow tests 共 `14 passed`；`py_compile=PASS`；`git diff --check=PASS`。P1 runner 的 canonical copy 与实际执行文件 SHA-256 相同；producer 在 `16729b2` 与启动时 canonical main 的 git blob 和 SHA-256 均相同。正式 producer 未修改。

## 7. 输出、失败记录与 tracked boundary

Git-tracked：本报告、summary、per-session aggregate、source identity、manifest、error log、P1 runner、summarizer 和 narrow tests。含逐 probe 细节与 JSON diagnostics 的 100-row paired table 保持 local-only：

`D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p1_20260912_paired_r4\MMWAVE_HR_RECOVERY_P1_PAIRED_100_PROBES.csv`

最终 local manifest：

`D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p1_20260912_paired_r4\manifest.json`

第一次 control 启动因默认 Python 缺少 `bioread` 在科学计算前退出，随后复用既有 `.venv_t0` 并在新目录成功重跑。一次 paired 汇总的外层 stdout 重定向先于目录创建而失败，没有生成或覆盖结果；最终使用新 `paired_r4`。完整 stable IDs、影响与解决状态见 `MMWAVE_HR_RECOVERY_P1_ERROR_LOG.json`。

## 8. Verdict 与下一依赖

- `REUSE_GATE=PASS`
- `CONTROL_REPRODUCTION=PASS`
- `INVARIANT_GATE=PASS`
- `RESTORATION_RESULT=NOT_SUPPORTED`
- `P1_VERDICT=PASS / RESTORATION_NOT_SUPPORTED`
- `P2_READY=YES`，仅表示 P1 依赖已闭合；P2 未在本任务执行。

P1 不产生正式 producer upgrade。下一依赖是另行授权的 P2：在 current DLL-time 30 s control chain 上做 failure attribution；不得把本负结果当作开始 P3 baseline selector、P5 30/60 s 比较、HRV 或注意模型的授权。
