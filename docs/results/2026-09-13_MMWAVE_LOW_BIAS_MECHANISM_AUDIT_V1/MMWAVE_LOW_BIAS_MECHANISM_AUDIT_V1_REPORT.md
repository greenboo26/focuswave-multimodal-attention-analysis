# 毫米波 HR 系统性低估机制审计 v1（MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1）

RUN_ID: `mmwave_low_bias_mechanism_audit_v1_20260913_r1`

审计类型：`MECHANISM_AUDIT`（机制审计，不是 estimator 搜索）

最终机制状态：**MULTIFACTOR_MECHANISM_SUPPORTED**

## 1. 这次审计回答什么

当前融合心率（fused HR）相对心电图（electrocardiography [ECG]）参考约 **−9 bpm** 系统性低估。
本任务不搜索新的 estimator rule，而是回答：这个低估主要来自哪里，以及下一轮真正修算法时
应该预注册什么方向。

硬边界（全部满足）：没有新建 gating rule、没有调阈值、没有用 ECG 选 production peak、
没有改 fused/time/spectral estimator、没有改 target/bin/channel selector、没有改融合、
没有改谐波校正、没有改窗口、没有做 30 s vs 60 s 比较、没有开始 P3 baseline personalization、
没有改 snapshot v1、没有改正式 producer、没有发布 snapshot v2、没有训练注意状态模型、
没有解锁心率变异性（heart rate variability [HRV]）。

## 2. 冻结 denominator 与输入身份

| 项目 | 值 |
|---|---|
| sessions | 5（9779, 97793, 97794, 97795, 97796） |
| probes | 100 |
| ECG 资格 | 100/100 ECG_VALID（复用 estimator improvement v1） |
| 窗口 | `[window_effective_start, probe_onset)`，nominal 30 s，无 cross-block |
| 时间源 | DLL host receive/enqueue timestamp（CSV 零基第 1 列） |

输入身份核验全部 exact match（SHA-256）：

| 输入 | rows | SHA-256 |
|---|---|---|
| CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv | 100 | `B4251445B1938DF61F07EFECE9ECBA4DD29FEFFCEED699E0B5B5226D0571A76D` |
| REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv | 100 | `EA9DB07FB37A2027569714B3193FC49AAFECA7C59690750BFFAF523C7188F479` |
| MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv | 100 | `FFED63DDE2E30F5A7B216E5996CB136012286CE4832CA82E6541A66E556C81B1` |

## 3. 冻结 control 复现（必须先通过）

| arm | MAE | bias | p90 AE |
|---|---|---|---|
| CONTROL_FUSED | 10.457079173 | -9.033105842 | 24.054346218 |
| CONTROL_TIME | 8.99696577 | -6.737621327 | N/A |
| CONTROL_SPECTRAL | 15.123834193 | -13.351010046 | N/A |

与冻结值误差 < 1e-06，`CONTROL_REPRODUCTION=PASS`；100/100 keys exact。

## 4. 核心问题 1：融合是否把频域的低估带进最终 fused HR

融合链的精确代码路径见 `FUSION_PATH_AUDIT.md`。关键事实是：融合在 `gap ≤ 10 bpm` 时做加权平均，
在 `gap > 10 bpm` 时**二选一**，而选择依据是与一个继承历史低估的 anchor 的距离。

| 指标 | POOLED |
|---|---|
| spectral < time | 78/100 |
| fused < time | 57/100 |
| spectral < time 且 fused 被向下拉 | 57/100 |
| time AE≤5 但 fused AE>5 | 7/100 |
| time AE≤5 但 fused AE>10 | 4/100 |
| improve/worsen/tie（fused vs time） | 31/47/22 |
| 平均 fusion penalty vs time | 1.460113 bpm |
| fused 同时差于两路 | 0/100 |

按 session 分层（每个 session 20 probes）：

| session | n | spectral<time | fused<time | pulled | penalty | imp/wor/tie | t≤5→f>5 | t≤5→f>10 |
|---|---|---|---|---|---|---|---|---|
| 9779 | 20 | 15 | 12 | 12 | 0.922 | 10/7/3 | 1 | 1 |
| 97793 | 20 | 17 | 10 | 10 | 0.988 | 5/8/7 | 1 | 1 |
| 97794 | 20 | 16 | 12 | 12 | 1.826 | 7/9/4 | 3 | 1 |
| 97795 | 20 | 16 | 14 | 14 | 3.277 | 2/15/3 | 1 | 0 |
| 97796 | 20 | 14 | 9 | 9 | 0.287 | 7/8/5 | 1 | 1 |

**判定**：频域路确实系统性偏低（bias -13.351010），
融合也确实在 57/100 个 probe 上把结果拉到 time 以下。但融合只贡献约
1.460 bpm 的额外绝对误差，且从不比两路都差，
所以**低估的主因不是融合本身，而是 feed 进融合的 time/spectral 两路本身已经偏低**。

## 5. 核心问题 2：distance 关联是否独立于 session / failure class

连续 distance 的描述性相关（`DESCRIPTIVE_ONLY / CLUSTERED_NONINDEPENDENT`）：

| 关系 | Spearman ρ |
|---|---|
| distance vs signed_error_fused | 0.020855 |
| distance vs absolute_error_fused | 0.004382 |
| distance vs fusion_penalty_vs_time | 0.006611 |
| distance vs signed_error_time | 0.065473 |
| distance vs signed_error_spectral | 0.141575 |

pooled 的 ρ 接近 0，说明**连续距离本身几乎不解释任何 probe 间差异**。

within-session 比较（远距离 ≥1.5 m 减近距离 <1.5 m 的 fused bias）：

| session | n near | n far | near bias | far bias | far − near |
|---|---|---|---|---|---|
| 9779 | 15 | 5 | -5.272624 | -7.426486 | -2.153862 |
| 97793 | 16 | 4 | -6.042120 | -12.301104 | -6.258984 |
| 97794 | 18 | 2 | -5.176956 | -3.395781 | 1.781175 |
| 97795 | 15 | 5 | -16.241280 | -21.232975 | -4.991694 |
| 97796 | 12 | 8 | -5.945066 | -15.013604 | -9.068538 |

far − near 在 4/5 个含远距离 probe 的 session 中为负，方向基本一致；但 97794 反号（+1.78），
且远距离 probe 高度集中在少数 session（例如 97796 占 40%）。

`DISTANCE_FAILURE_CLASS_MATRIX.csv` 给出了更强的线索：**GT1.5M 的错误几乎全部来自错误类别**，
而不是距离本身让正确 target 的估计变差——在 GT1.5M 内 `CORRECT_OR_NEAR_CORRECT` 的
fused bias 只有 0.819053 bpm，
而该带 50% 的 probe 是 wrong peak。

**判定**：距离是一个**弱且被 session/类别混淆**的关联，不能解释为距离因果，也不得据此造新 gate。

## 6. 核心问题 3：低估是否主要是错误类型驱动

按严格 P2 类别分解（`FAILURE_CLASS_BIAS_DECOMPOSITION.csv`）：

| failure class | n | fused bias | fused MAE | time bias | spectral bias |
|---|---|---|---|---|---|
| CORRECT_OR_NEAR_CORRECT | 39 | 0.215472 | 1.538915 | 0.176566 | -2.112739 |
| SELECTED_TARGET_WRONG_PEAK | 27 | -12.214726 | 14.954587 | -9.652446 | -18.091227 |
| HARMONIC_OR_HALF_DOUBLE_LOCK | 18 | -19.367868 | 19.367868 | -16.252071 | -26.295081 |
| TARGET_BIN_CHANNEL_MISS | 16 | -14.580922 | 14.580922 | -7.968431 | -18.183100 |

**这是本审计最强的发现**：`CORRECT_OR_NEAR_CORRECT` 的 fused bias 只有
0.215472 bpm（MAE 1.538915）。
也就是说，**当链路判断正确时，估计器几乎无偏**；总体 −9 bpm 完全由三个失败类别承担。

把 pooled bias 按类别做加性归因（每个类别贡献 = 该类带符号误差之和 / 100）：

| failure class | n | 类别内 fused bias | 对 pooled bias 的贡献 | 占 pooled bias | fusion penalty 贡献 |
|---|---|---|---|---|---|
| CORRECT_OR_NEAR_CORRECT | 39 | 0.215472 | 0.084034 | -0.930 | -0.533680 |
| SELECTED_TARGET_WRONG_PEAK | 27 | -12.214726 | -3.297976 | 36.510 | 0.841600 |
| HARMONIC_OR_HALF_DOUBLE_LOCK | 18 | -19.367868 | -3.486216 | 38.594 | 0.382390 |
| TARGET_BIN_CHANNEL_MISS | 16 | -14.580922 | -2.332948 | 25.827 | 0.769803 |

## 7. 核心问题 4：ECG HR 高低是否解释 bias

| ECG band | n | ECG median | fused bias | fused MAE | time bias | spectral bias | fusion penalty | sessions |
|---|---|---|---|---|---|---|---|---|
| LT75 | 5 | 72.332731 | -2.638625 | 5.802445 | -1.523720 | -8.275430 | -0.423851 | 97794:5 |
| 75_TO_90 | 75 | 84.596405 | -9.261042 | 10.494039 | -6.673072 | -14.759561 | 1.484930 | 9779:18|97793:20|97794:15|97795:8|97796:14 |
| GT90 | 20 | 92.024540 | -9.776964 | 11.482138 | -8.283156 | -9.337839 | 1.838042 | 9779:2|97795:12|97796:6 |

LT75 仅 n=5，不得强推断。75_TO_90 与 GT90 的 fused bias 接近（−9.26 与 −9.78），
说明这不是简单的"高心率时估计器跟不上"；但两个带被 session 组成混淆（见 sessions 列），
且 GT90 的 spectral bias 反而较小。**不足以支持心率带特异性机制。**

## 8. 核心问题 5：既有 QC 是否解释低估

| QC field | n | ρ vs signed error | ρ vs absolute error | ρ vs fusion penalty | 跨 session 方向一致 |
|---|---|---|---|---|---|
| hr_usable_ratio | 100 | UNDEFINED | UNDEFINED | UNDEFINED | CONSTANT_NO_VARIANCE |
| phase_stability | 100 | 0.324236 | -0.339946 | -0.086763 | NO |
| motion_proxy | 100 | 0.265935 | -0.326049 | -0.203653 | NO |
| mmwave_frames | 100 | -0.007829 | -0.056296 | -0.070840 | NO |
| ecg_valid_ratio | 0 |  |  |  | NOT_AVAILABLE |
| rsp_valid_ratio | 0 |  |  |  | NOT_AVAILABLE |

`hr_usable_ratio` 在本轮 100 个 probe 中**恒为 1.0**，没有方差，因此秩相关无定义：
这个字段在 eligibility 层没有判别力（全部探针都通过可用窗比例检查），不是缺失值。

`phase_stability` 与 `motion_proxy` 的 pooled ρ 很弱（0.32 / 0.27），
且 **5 个 session 中有 1 个（97793）方向相反**，不满足 session 一致性。
`hr_confidence` 与 selection margin 在本轮冻结输出中为空，标记 `NOT_AVAILABLE`，不补算。

**判定**：现有 QC 字段不支持"低估由低信噪比/低质量驱动"这一假设。

## 9. 核心问题 6：谐波机制

各 arm 相对 ECG 的比值分布（冻结诊断关系，未重新优化容差）：

| arm | ratio median | p10 | ≈0.5 lock | ≈2.0 lock | ratio < 0.8 |
|---|---|---|---|---|---|
| fused | 0.909652 | 0.717184 | 0 | 0 | 27 |
| time | 0.935695 | 0.755060 | 0 | 0 | 16 |
| spectral | 0.840575 | 0.630688 | 0 | 0 | 46 |

**没有任何 probe 落在 ≈0.5 或 ≈2.0 的谐波锁定位**。相反，三个 arm 的比值分布整体向低端偏斜
（spectral 有 46/100 低于 0.8）。
因此本数据的"系统性低估"形态是**整体低偏**，而不是经典半频/倍频锁定。

把 harmonic 类别整体剔除后：

| 分组 | n | fused bias | fused MAE |
|---|---|---|---|
| HARMONIC_CLASS_ONLY | 18 | -19.367868 | 19.367868 |
| NON_HARMONIC_RESIDUAL | 82 | -6.764500 | 8.501052 |

非谐波残留仍是 -6.764500 bpm 的明确负偏，
所以 **−9 bpm 不是少数谐波灾难拉出来的**。

既有 P2 次级标记频次（说明哪些机制真的在触发）：

| flag | n |
|---|---|
| DIAGNOSTIC_ONLY | 100 |
| ORACLE_ASSISTED | 100 |
| FUSION_IMPROVED_VS_SPECTRAL | 70 |
| TIME_AND_SPECTRAL_WRONG | 53 |
| FUSION_WORSENED_VS_TIME | 47 |
| FUSION_IMPROVED_VS_TIME | 31 |
| FUSION_TIED_VS_TIME | 22 |
| FUSION_WORSENED_VS_SPECTRAL | 21 |
| SPECTRAL_NEAR_2X3X_BR | 13 |
| FUSED_NEAR_2X3X_BR | 12 |
| TIME_NEAR_2X3X_BR | 12 |
| FUSION_TIED_VS_SPECTRAL | 9 |
| TIME_CORRECT_FUSION_WRONG | 7 |
| SPECTRAL_CORRECT_FUSION_WRONG | 1 |

## 10. 机制证据矩阵

完整矩阵见 `MECHANISM_EVIDENCE_MATRIX.csv`（含 EVIDENCE_FOR / EVIDENCE_AGAINST /
SESSION_CONSISTENCY / FAILURE_CLASS_LINK / CONFIDENCE / NEXT_TEST）。

| 机制候选 | 置信度 |
|---|---|
| SPECTRAL_LOW_BIAS_PULLS_FUSION_DOWN | HIGH |
| HARMONIC_ERROR | HIGH |
| DISTANCE_OR_GEOMETRY_ASSOCIATION | MEDIUM |
| TARGET_SELECTION_ERROR | MEDIUM |
| SELECTED_TARGET_PEAK_ESTIMATION_ERROR | MEDIUM |
| SESSION_SPECIFIC_DATA_QUALITY | MEDIUM |
| LOW_SIGNAL_OR_QC | LOW |

## 11. 最终机制判定

**MULTIFACTOR_MECHANISM_SUPPORTED**

数据事实：
1. 低估不是均匀的估计器标定误差——正确类几乎无偏（+0.215472 bpm）。
2. 低估集中在三个失败类别，且每个失败类别的估计都显著向低端偏。
3. 频域路是三者中偏得最厉害的（-13.351 bpm），
   融合把它往 time 拉回一部分，但仍净叠加约 1.460 bpm，
   并制造 4 个"可接受→灾难"转换。
4. 距离只有弱关联且被 session/类别混淆；ECG 心率带无清晰特异性；既有 QC 字段无 session 一致关系。

当前判断（仍属机制解释而非结论放行）：
- 主机制是**失败模式主导的低偏**：一旦进入 wrong peak / harmonic / target miss，估计值系统性偏低。
- 次机制是**频域路系统性低偏并被融合部分传递**。
- 距离更像这些失败模式的空间代理，而不是独立原因。

尚未解决：为什么失败模式一律偏向低端（而不是对称错）——这需要 selection margin、
hr_confidence 等当前 `NOT_AVAILABLE` 字段，或独立验证集。

## 12. NEXT_HYPOTHESIS（不得在本轮实现）

只写成假设，不实现、不评价为 production candidate：

- `NEXT_HYPOTHESIS_A`：在**不改变 target/bin/channel 选择**的前提下，检验频域打分的
  `-0.035*|c - time|` 与 `-0.025*|c - previous|` 两项是否把谱峰系统性拉向低端。
- `NEXT_HYPOTHESIS_B`：检验 anchor 更新规则（`0.8*previous + 0.2*fused`，且 `confidence >= 0.12`）
  是否让历史低估长期驻留，从而在 gap > 10 的二选一分支里偏向低值。
- `NEXT_HYPOTHESIS_C`：为 selection margin / hr_confidence 增加 instrumentation，
  区分"选错峰"与"选对峰但峰值估计偏低"。

任一假设都必须先在**参与者/场次不重叠的未触碰验证集**上检验，不得在同一 100 probes 上继续拟合。

## 13. 证据边界

- 这是一次 development set 上的描述性机制审计；100 probes 来自 5 个 session，
  不是 100 个独立样本，不做 pooled p-value，不声称 population inference。
- ECG 仅作为机制诊断 oracle 使用，不参与任何 production 选择。
- 本审计不构成 HR/BR 提升、不是正式放行依据，HRV 继续 `BLOCKED`。
