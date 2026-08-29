# MMWAVE FORMAL VITAL QC V1

日期：2026-08-28；closure：2026-08-29；状态：**CLOSED_WITH_EXPLICIT_BOUNDARIES**

Issue #15 closure 见 `MMWAVE_FORMAL_VITAL_QC_V1_CLOSURE_2026-08-29.md`。最终资格为：
HR=`PASS_QUALITY_GATED`、BR=`PASS_SUPPORTING`、HRV=`BLOCKED`；corrected QC 为
Tier1=33、Tier2=37、Tier3=2。该状态不把 Tier1 写成 ground-truth validated，且不授权
新的 C2B/C2C、AoA/beamforming、VMD grid 或 HRV 运行。

## 范围与边界

本批仅复盘既有 ECG/RSP 小样本质量规则，并对现有 formal mmWave 产物实施 QC v1 归因。未启动专注建模，未继续修改算法，未读取 NIR/RGB 作为本批证据。session 使用已有匿名编号；本报告不把匿名 session 当作已确认真实被试身份。

## 既有小样本规则复盘

| 项目 | 已确认内容 |
|---|---|
| 对应脚本 | `gold_standard_qa.py` v2.0；毫米波 producer 为既有 `process_vital_signs_v3_1_1.py`；批次时间门控入口为 `run_timeline_gated_mmwave_quality.py` |
| 复盘 commit | 仓库复核 HEAD `ba7a2c652bea82c3fa58ad5858a7460ed933fb47`；输入脚本 SHA-256 见 manifest |
| 输入数据 | formal 主队列既有 70 场、099 supplemental、067 缺失/未链接；ECG/RSP 严格参考为 5 场×20 个 60 s 窗口 |
| 输出目录 | 本批输出到 `docs/results/mmwave_formal_vital_qc_v1/`；既有输入产物路径与哈希记录在 manifest |
| ECG 清洗 | 0.5–40 Hz；R 峰最小间距 0.3 s；IBI 300–2000 ms；相邻 IBI 相对变化 >20% 剔除；正常 RR ≥80% 可用；时域 HR 取中位 IBI |
| RSP 清洗 | 0.1–0.7 Hz；峰间距 ≥0.5 s；6–42 次/分；低幅度松脱标记；正常周期 ≥80% 可用；呼吸率取中位周期率 |
| mmWave 清洗 | 既有 v3.1.1 与行为时间门控；10 s 心跳带通位移信号存在性窗；每个 block 独立，不跨 block 拼接 IBI/HRV |
| window 长度 | ECG/RSP 参考：60 s；formal mmWave QC：10 s 信号存在性窗；既有 probe 产物另按原有 probe 窗口记录 |
| filter band | ECG 0.5–40 Hz；RSP 0.1–0.7 Hz；毫米波沿用既有 producer 的心跳带通，不在本批改动 |
| beat matching | ECG 侧按 R 峰→IBI；既有毫米波对照按同一行为/时间窗口比较 HR；本批不重建逐搏 beat-to-beat matching |
| artifact rejection | ECG IBI 百分比变化法；RSP 生理范围与松脱标记；毫米波沿用既有信号存在性/质量窗及 target-lock 审计标记 |
| usable-window 判定 | ECG/RSP 正常比例 ≥80%；formal v1 session 另要求 window_quality_pct ≥80、probe_quality_pct ≥80，且无既有几何/相位不稳定标记 |
| ECG 标签调参 | **未用 ECG/RSP 标签调 formal batch v1 参数**；ECG/RSP 仅作为独立参照与归因证据。历史 0816 校准结论保留为机制背景，不回写为本批调参 |

## QC v1 归因规则

- A：raw、时间轴、同步或主队列 linkage 缺失/不完整。
- B：已有 target-lock 审计显示距离不合理、相位不稳定或仅低信号存在性；归入雷达几何/运动层。
- C：输入/输出链存在，但既有 10 s 或 probe 覆盖未过 v1 门槛；仅称 vital algorithm/QC gate failure，不推断硬件故障。
- D：HRV/IBI 逐搏证据不足，不能支持 HRV；不是 session 传感器质量结论。
- E：ECG/RSP 对照揭示构念效度、谐波或参考不一致风险；不是“数据质量差”或笼统“算法问题”。
- U：证据不足以在上述层级中进一步定位。

每个 session 的主归因与适用 flag 见 `mmwave_session_qc_summary_redacted.csv`。

## Use-tier definitions and gates

### Historical pre-37 mm QC：`HISTORICAL_PRE_37MM_QC_V1`

旧 **17/53/2** 是 corrected distance audit 前的历史 QC v1 口径，不是当前结论。旧 17 场曾被列为 Tier 1 QC-eligible candidate，旧 53 场曾被列为 motion/quality-only；这些数字仅用于解释历史决策和结果迁移，统一标记为 `HISTORICAL_PRE_37MM_QC_V1`，不得作为当前 #16 输入。

### Current corrected 37 mm QC gate

当前正式口径只使用 corrected distance `0.037 m/bin`：Tier1=`33`、Tier2=`37`、Tier3=`2`。Tier1 是 QC-eligible candidate，不等于 HR/BR ground-truth validated；Tier2 仅作 motion/quality 或预定义 sensitivity 对照；Tier3（067/099）不进入 formal #16 生理输入。

### 三个 use-tier 的 gate

| use_tier | 必须满足 | 失败/降级条件 | ECG/RSP 是否参与 | 当前允许用途 |
|---|---|---|---|---|
| `Tier_1_QC_eligible_candidate` | formal linkage 存在；`window_quality_pct >=80`；`probe_quality_pct >=80`；无 B 类 target-lock 几何/相位/低信号标记 | 任一覆盖率 <80% 降为 Tier 2；出现 B 标记降为 Tier 2；A/同步或 linkage 缺失降为 Tier 3 | **不参与 gate**；5 场 ECG/RSP 仅提供独立校准/机制边界 | HR/RR 研究候选，不能写成已验证生命体征；HRV 和 attention model 不可用 |
| `Tier_2_motion_only` | 有可追溯毫米波输出或信号存在性证据 | B 类几何/相位/信号证据，或 C 类窗口/probe gate 失败 | 不参与 gate | 仅微动/体动描述；HR/RR/HRV/attention model 均不可用 |
| `Tier_3_unusable_for_formal_v1` | A 类 raw、同步、时间轴或主队列 linkage 阻断 | 在补齐输入和 linkage 前不得升级 | 不适用 | formal v1 不可用；067/099 保持边界 |

补充限制：D (`hrv_too_strict_not_supported`) 适用于有 HRV 数值但无充分逐搏 ECG 验证的 session；E (`construct_validity_not_sensor_quality`) 表示独立 ECG/RSP 揭示的构念效度/谐波风险。D/E 不是传感器质量 pass，也不是 Tier 1 的放行证明。上述 gate 适用于 formal 主队列；ECG/RSP 小样本只用于参照协议和归因，不把 5 场扩展为 70 场金标准覆盖。

### Historical pre-37 mm interpretation：旧“只能用于微动/体动：53 场”

旧 53 场 = B 类 44 场 + C 类 9 场，均不是因为“缺 ECG/RSP”这一单一原因。B 由 `target_lock_status` 中的 `distance_implausible`、`plausible_distance_phase_unstable` 或 `plausible_distance_low_signal_presence` 决定；C 由既有输出存在但 `window_quality_pct <80` 或 `probe_quality_pct <80` 决定。它们可以保留已有毫米波信号/相位变化作微动或体动层描述，但这一旧分类不得作为当前 #16 输入。

### 1,297/1,400 到底是什么 pass

`1,297/1,400` 是既有 70 场主队列的 **probe-level mmWave quality flag**（`probe_quality_pct` 的分子/分母）：表示探针对应窗口在既有毫米波质量产物中被标记为 `ok`。它不是文件完整性 pass、不是 timestamp/sync pass、不是 ECG/RSP 对照 pass，也不是 HR/RR/HRV 生理准确性 pass。当前 corrected 分层中，满足既有联合 gate 的 Tier 1 为 `33` 场；不能把 1,297/1,400 改写为“毫米波生命体征可用”。

### Current corrected 37 mm session crosswalk

当前 session crosswalk 必须使用：`D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\mmwave_session_use_tier_crosswalk_corrected37mm.csv`。
该表的 `new_tier` 计数为 Tier1=33、Tier2=37、Tier3=2；Tier3 为 `067`、`099`。该 corrected 表替代旧 crosswalk 作为当前 #16 输入依据。

### Historical pre-37 mm session crosswalk：`HISTORICAL_PRE_37MM_QC_V1`

以下旧表完整保留，仅用于历史追溯；它不是当前 #16 输入：

| session_id | probe_count | qc_probe_pass_count | failure_mode | use_tier | can_use_for_motion | can_use_for_rr | can_use_for_hr | can_use_for_hrv | can_use_for_attention_model | reason |
|---|---:|---:|---|---|---|---|---|---|---|---|
| 056 | 13 | 13 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 057 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 058 | 20 | 20 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 059 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 062 | 10 | 10 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 064 | 17 | 17 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 065 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 067 | 0 | 0 | A_acquisition_or_sync | Tier_3_unusable_for_formal_v1 | no | no | no | no | no | 067: 缺失/未链接毫米波 raw 输入 |
| 068 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 070 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 071 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 072 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 073 | 17 | 17 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 074 | 19 | 19 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 075 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 076 | 16 | 16 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 077 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 078 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 081 | 16 | 16 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 082 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 083 | 19 | 19 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 084 | 12 | 12 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 085 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 086 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 087 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 088 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 089 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 090 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 091 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 093 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 094 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 095 | 18 | 18 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 096 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 098 | 19 | 19 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 099 | 20 | 20 | A_acquisition_or_sync | Tier_3_unusable_for_formal_v1 | no | no | no | no | no | 099: 有 raw 与 supplemental 输出，但缺少进入主队列所需的 timeline/meta linkage |
| 100 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 104 | 17 | 17 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 106 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 107 | 18 | 18 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 108 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 109 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 110 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 114 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 116 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 117 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 118 | 10 | 10 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 119 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 122 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 123 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 124 | 18 | 18 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 125 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 126 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 127 | 13 | 13 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 128 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 129 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 130 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 131 | 17 | 17 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 133 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 134 | 20 | 20 | U_unresolved | Tier_1_QC_eligible_candidate | yes | candidate_only | candidate_only | no | no | 通过 v1 的窗口与 probe 覆盖门槛；target-lock 仍是 candidate-only 证据，不能写成已确认胸部锁定 |
| 139 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 143 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 145 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 147 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 148 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 154 | 18 | 18 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 158 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 160 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 162 | 20 | 20 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 166 | 18 | 18 | C_vital_algorithm_failure | Tier_2_motion_only | yes | no | no | no | no | 毫米波输入/输出链存在，但既有 10 s 信号存在性门控或 probe 覆盖未达到 v1 综合分析门槛；不推断为传感器硬件故障 |
| 170 | 20 | 20 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |
| 175 | 13 | 13 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 距离候选存在，但相位稳定性不足；保留为微动/体动层，不进入综合生命体征层 |
| 178 | 19 | 19 | B_radar_geometry_or_motion | Tier_2_motion_only | yes | no | no | no | no | 目标距离证据不合理；不能把该场次的相位变化直接解释为胸部生命体征 |

## Session 分层结果

### Current corrected Tier 1：QC-eligible candidate（不是生命体征已用）

共 **33** 场：`071,072,074,076,078,082,083,086,088,089,091,093,094,095,096,098,100,106,107,109,110,114,116,119,124,125,126,129,130,134,139,143,170`

判定：窗口质量和 probe 覆盖均 ≥80%，且未被已有 target-lock 几何/相位标记阻断。HR/RR 仅作为后续研究候选；BR 仍为 supporting sensitivity；HRV 统一标记 D，不进入确认性主结论。不得写成“生命体征可用”。

### Current corrected Tier 2：只能用于质量分层对照/微动体动

共 **37** 场。包括 corrected distance、几何/相位/低信号或既有 coverage 条件未达到 Tier1 的场次。它们可作为 #16 预定义 quality-stratified 对照，但不得直接解释为 validated HR/BR/HRV。

### Tier 3：不可用于 formal v1

共 **2** 场：`067, 099`。067 为毫米波 raw 缺失/未链接；099 有 supplemental raw/输出，但缺少主队列 timeline/meta linkage，不能进入本 formal 主分母。

## ECG/RSP 独立效标协议与结果

严格参照为 BIOPAC ECG（心电图）/RSP（呼吸带）5 个重复测量场次、100 个 60 s 窗口；99 个窗口有对应毫米波指标。已有比较结果：HR course MAE 3.777 bpm（约 3.78 bpm），HR peak MAE 7.82 bpm，BR peak MAE 11.77 次/分，RMSSD MAE 262.64 ms。4.59/4.61 仅作 historical old-gate calibration result；RSP 频谱候选的既有汇总为 MAE 3.51 次/分，但仍属于独立验证后的 supporting sensitivity，不能覆盖普通峰值 BR 的失败证据。

关键归因：ECG/RSP 金标准清洗本身在小样本中可用；97795/97796 已观察到呼吸二/三次谐波落入心跳带，形成“强而错”锁定，说明高 SNR、相位稳定和时频自洽不等于心率构念有效。因此 E 是构念效度边界，不应写成传感器质量差。

## 原因统计

主归因计数、适用 flag 计数及口径见 `mmwave_failure_mode_counts.csv`。其中 D/E 是适用范围 flag，不能与 A/B/C/U 的主归因相加后当作互斥 session 数。

## 报告书可直接粘贴的毫米波 QC 结论段

本研究对正式毫米波记录实施了预先冻结的分层质量控制：ECG/RSP 参考侧采用带通、逐搏/逐周期异常剔除及 ≥80% 正常比例判定；毫米波侧沿用既有 v3.1.1 producer 与行为时间门控，对 10 s 信号存在性窗和 probe 覆盖进行审计，并将缺失/同步、雷达几何或运动、生命体征输出门控失败、HRV 逐搏证据不足、构念效度风险和未解析状态分开记录。corrected 37 mm QC 将 **33 场**列为 Tier 1 质量候选（**不是生命体征已验证**），**37 场**列为 Tier 2 质量/运动对照，**2 场**因输入或时间轴 linkage 不足不可用于 formal 主分析。旧 17/53/2 仅为 `HISTORICAL_PRE_37MM_QC_V1`，不得作为当前 #16 输入。独立 BIOPAC 参照显示，毫米波 HR course 的窗口级误差低于逐峰 HR，但 BR 峰值与 HRV 仍存在明显不一致；尤其呼吸二/三次谐波可在信号稳定时产生“强而错”的心跳锁定。因此，本研究不以“数据质量差”或笼统“算法问题”概括结果，而按证据层级限制毫米波 HR/RR 的研究性使用，并不将 HRV 作为已验证生理指标或专注效标输入。

## 验证与限制

本批读取并核对了既有 matrix、formal output audit、subject summary、segment quality、ECG/RSP 参考比较与规则脚本；输出 CSV/JSON/Markdown 均可读。未提交、未推送；工作区原有大量用户修改保持不变。治理主 checkout 未能在本机解析，故治理基线的独立复核仍是限制。
