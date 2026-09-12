# FocusWave mmWave HR recovery P2 failure-attribution report

日期：2026-09-12
状态：`PASS / FAILURE_ATTRIBUTION_COMPLETE`

## 1. 范围与控制身份

本轮解释 current 动态链接库主机接收/入队时间（dynamic-link library host receive/enqueue time）、30 s、逐 probe 动态 target 的融合心率（heart rate [HR]）平均绝对误差（mean absolute error [MAE]）`10.4601 bpm`。Primary denominator 固定为 session `9779/97793/97794/97795/97796` 的 100 个 probe；窗口为 `[probe_end - 30 s, probe_end)`。执行前 `origin/main=da6d8ac1a945e811be182723a92287b51ae5d5e0`，与 handoff 一致。

P2 为 `DIAGNOSTIC_ONLY / ORACLE_ASSISTED`（仅诊断/心电图辅助回顾判别）。心电图（electrocardiogram [ECG]）仅在毫米波 target 和候选生成完成后用于判断候选位置与错误类别，没有进入 target、bin/channel、peak、fusion、threshold、quality gate 或参数选择。未修改 formal producer，未训练模型。

## 2. Reuse Gate 与分类 lineage

直接复用 `run_ecg_valid_retrospective_spectral_truth_audit_20260830.py` 的 exact/nearby tolerance、弱峰突出度和谐波容差，复用 `run_mmwave_selector_path_reconciliation_20260830.py` 与 current producer 的 candidate、time、spectral、previous-anchor、harmonic folding 与 fusion 定义。Exact tolerance 为 `max(0.5 × spectral resolution, 1.5 bpm)`，nearby tolerance 为 `max(2 × spectral resolution, 6 bpm)`，weak relative prominence 为 `.05`，harmonic tolerance 为 `5 bpm`；均未按本 100-probe 结果调参。

`REUSE_REJECTION_REASON`：旧 `nearby_target_bin_channel` 实际是 selected target 内较宽的频率容差，不是物理 bin 邻域，且旧审计为 20 s spectral-only，不能直接表达 current 30 s fused pipeline 的 fusion、time/spectral 分歧和 alternate target topology。本轮保留 `old_truth_semantics_class`，只增加 current primary/secondary 字段；详细映射见 `MMWAVE_HR_RECOVERY_P2_CLASSIFICATION_LINEAGE.csv`。

## 3. Invariant gate

重建仅为生成缺失的 diagnostic intermediate。100/100 key 唯一且完整；逐 probe 的 window start/end、frame i0/i1/count、frame-ID SHA-256、heartbeat SHA-256、HR/BR bin/channel、spectral/time/fused HR 和 ECG HR 与冻结 control 的差异均为 0。Control fused/time/spectral HR MAE 分别为 `10.460107/8.969469/15.113444 bpm`。因此 `INVARIANT_GATE=PASS`。

## 4. Primary failure attribution

| Primary class | *n* | % |
|---|---:|---:|
| CORRECT_OR_NEAR_CORRECT | 37 | 37% |
| SELECTED_TARGET_WRONG_PEAK | 28 | 28% |
| HARMONIC_OR_HALF_DOUBLE_LOCK | 18 | 18% |
| TARGET_BIN_CHANNEL_MISS | 17 | 17% |
| WEAK_OR_ABSENT_HEART_EVIDENCE | 0 | 0% |
| MOTION_OR_SIGNAL_QUALITY | 0 | 0% |
| COVERAGE_OR_REFERENCE_LIMITATION | 0 | 0% |
| AMBIGUOUS | 0 | 0% |

在 63 个 fused AE > 5 bpm 的失败 probe 中，selected-target peak/candidate error 为 28/63（44.4%），harmonic/half-double/mechanical-lock label 为 18/63（28.6%），target/bin/channel miss 为 17/63（27.0%）。因此主要已定位机制是 selected target 内 estimator/peak selection，而不是 target path 单独占主导。

Selected target 上 exact ECG-consistent spectral candidate 存在于 61/100；旧 spectral-only lineage 分布为 exact-selected 21、exact-available-but-wrong-selection 40、nearby-only 37、absent/weak 2。Current primary 使用 fused error 与机制优先级后，28 个归入 selected-target wrong peak。

mmWave 自身规则生成的广义 alternate candidate 集中，100/100 都能在 retrospective oracle 下找到至少一个 exact ECG-consistent frequency；位置为 different-channel distant-bin 76、different-channel same/adjacent-bin 12、same-channel other-bin 11、same-channel adjacent-bin 1。该结果受候选多重性影响，只证明“候选池中存在”，不证明 production selector 应如何选择，也不能据此宣称 target path 已验证。Primary `TARGET_BIN_CHANNEL_MISS=17` 只用于失败定位；P3 不因 100/100 availability 自动获得执行授权。

## 5. Fusion 作用

相对 time HR，fusion 改善/恶化/不变为 `31/47/22`；相对 spectral HR 为 `72/19/9`。共有 7 个 probe 出现 time HR 已在 ECG ±5 bpm 内、但 fusion 后 AE > 5 bpm。56 个 probe 的 time 与 spectral 均超出 ±5 bpm。Fusion 总体明显优于 spectral，却弱于 time（MAE `10.4601` vs `8.9695 bpm`）；因此 current residual 不能只归因于 target，fusion/peak chain 仍是直接修复依赖。

## 6. Error severity

| Fused AE stratum | *n* | Primary classes | Fused MAE | Time MAE | Spectral MAE |
|---|---:|---|---:|---:|---:|
| AE ≤ 5 bpm | 37 | correct 37 | 1.3412 | 2.7829 | 3.9374 |
| 5 < AE ≤ 10 bpm | 21 | harmonic 4; wrong peak 10; target miss 7 | 7.3132 | 6.6788 | 16.9774 |
| 10 < AE ≤ 20 bpm | 24 | harmonic 7; wrong peak 12; target miss 5 | 14.9584 | 11.0992 | 20.5332 |
| AE > 20 bpm | 18 | harmonic 7; wrong peak 6; target miss 5 | 26.8782 | 21.5191 | 28.6855 |

## 7. Per-session 与 97795

| Session | *n* | Fused MAE | Primary distribution |
|---|---:|---:|---|
| 9779 | 20 | 7.0291 | correct 12; harmonic 3; wrong peak 5 |
| 97793 | 20 | 8.6141 | correct 9; harmonic 3; wrong peak 6; target miss 2 |
| 97794 | 20 | 7.7967 | correct 6; harmonic 5; wrong peak 4; target miss 5 |
| 97795 | 20 | 18.9463 | correct 4; harmonic 6; wrong peak 7; target miss 3 |
| 97796 | 20 | 9.9144 | correct 6; harmonic 1; wrong peak 6; target miss 7 |

`97795` 有 16/20 个 probe 的 AE > 5 bpm，且 7 个 AE > 20 bpm；其错误同时分布于 wrong peak（7）、harmonic（6）和 target miss（3），没有单一 target-only 模式。其 mean phase stability=`.9314`，低于总体其它场但仍连续；mean motion proxy=`.0206` 并不升高，mean confidence=`.2857`。现有 producer usable-ratio gate 为 100/100 pass，故不能把 97795 的高误差归因为已冻结 motion/signal gate failure。最大三个误差为 37.65、36.67、32.15 bpm，分别属于 harmonic、wrong peak、harmonic。

## 8. Signal quality、coverage 与 30 s 边界

按 primary class 的 mean phase stability / motion proxy / confidence：correct `.955/.037/.383`；harmonic `.931/.025/.209`；wrong peak `.944/.030/.269`；target miss `.948/.036/.176`。这些连续描述显示错误类 confidence 较低，但 motion proxy 没有一致升高；没有新建 outcome-derived cutoff。Existing usable-ratio `<.50` 命中 0/100，因此 `MOTION_OR_SIGNAL_QUALITY=0`。Coverage/reference limitation 为 0/100，所有窗口满足冻结 frame/reference contract；DLL cutover 不重开。

P2 没有比较 30 s 与 60 s，也没有发现 coverage/timing 主导当前错误。频谱/候选机制与 fusion 结果支持“current 30 s 链存在 estimator uncertainty”，但不足以证明 30 s 时长本身是主要限制；需要 P4 冻结完整 candidate pipeline 后再决定 P5 window comparison。

## 9. Decision

`MAIN_FAILURE_MECHANISM=SELECTED_TARGET_ESTIMATOR_PEAK_AND_FUSION_PATH`，root-cause confidence 为 `MODERATE`。Primary target/bin/channel miss 为 17%，低于 selected-target wrong peak 28%，且 broad alternate availability 非特异；本结果不支持直接优先进入 baseline-personalized target P3。最小 next route 为 `ESTIMATOR_PATH_NEXT`：另立受控任务冻结 selected-target candidate/peak/fusion repair 的诊断设计；不得在 P2 直接改权重或 producer。P3 evidence status 为 `NOT_PRIMARY_BOTTLENECK / NOT_AUTHORIZED_BY_P2`。

HR/BR 保持 `HOLD / SUPPORTING_ONLY`，心率变异性（heart-rate variability [HRV]）保持 `BLOCKED`；不得输出 `FORMAL_HR_READY`。

## 10. Outputs

- Git-safe：本报告、aggregate summary、per-session summary、severity summary、classification lineage、manifest、error log、runner 与窄测试。
- Local-only 100-probe table：`D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p2_failure_attribution_20260912_r1\MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv`；path 与 SHA-256 见 manifest。
