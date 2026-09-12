# mmWave external validation asset audit v1

Document ID: `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1`

Status: `ASSET_AUDIT_COMPLETE / NO_CANDIDATE_RUN / NO_PRODUCER_CHANGE`

RUN_ID: `mmwave_external_validation_asset_audit_v1_20260913_r1`

Date: 2026-09-13 (Asia/Shanghai)

Base commit: `ebcb9e6e7d4f1446ac1a51e17091188c2782d657`

## 1. 为什么先做这一步

preregistration v1 的 validation inventory 只扫了内部来源（开发集、正式 cohort、校准 session），**漏掉了本机已有的三个外部公开数据集**。在给正式 cohort 重建 per-window ECG gold-clean（`OPT_A`）之前，必须先确认这些外部资产能不能直接当验证集——否则可能白做一轮重工程。

本任务只做资产追溯与可行性判断：**不跑 C1/C2、不改 producer、不改 snapshot v1、不修改任何外部数据**。

## 2. 三个外部资产是什么

| dataset | 来源 | subjects | 雷达 | 参考信号 | 本机体量 |
|---|---|---|---|---|---|
| `VS_DATASET_healthy_v1` | Wu et al. 公开集，DOI `10.34810/data2962` | 24（Resting + Apnea = 48 段） | 自研 120 GHz FMCW | **Mindray ECG Lead II 500 Hz**、呼吸 256 Hz、脉搏 60 Hz、每分钟 HR/RR、血压 | 102 文件 / 31 MB |
| `AgeBalanced_60GHz` | AgeBalanced 公开队列 | 110 | TI 60.25 GHz（B=480 MHz，R_BIN 0.312 m） | Movesense **ECG ~250 Hz** + 加速度 | 2,424 文件 / 678 MB |
| `mmWave_Heartbeat`（TI gby 批次） | TI 原始 ADC 批次 | 未记录（10 个文件） | TI mmWave 原始 ADC | **无** | 10 文件 / 125 MB |

## 3. 逐条回答四个问题

### 3.1 `VS_DATASET_healthy_v1`

**Q：有足够 HR/ECG ground truth 吗？** 有，而且质量最高。每个 120 s 记录同时给出 `ecg_lead2`（Lead II，500 Hz，60,000 样本）、`ecg_lead3`、`ecg_leadv1`，外加呼吸、脉搏、每分钟 HR/RR 与血压。

**Q：时间分辨率够吗？** 够。雷达帧间隔 3.0 ms（`Radar.fs = 333.3`，40,000 帧 = 120 s），ECG 2.0 ms。时间轴由 `Radar.t_frame` 显式给出。

**Q：有原始毫米波输入吗？** **没有。** 雷达侧只有 `VitalSig` —— 一个**已经提取好的单通道位移波形**，没有 range bin、没有通道、没有 DataCube。

**Q：能适配当前 30 s / producer 契约吗？** 部分能。120 s 可切 3–4 个 30 s 窗口，全库约 144 个不重叠窗口，分母充足。但它**无法承载 target/bin/channel 选择这一步**。

**暴露判定：`DEVELOPMENT_EXPOSED`。** 这一点很关键：本机存在一个**已完成的 C1b 正式基准**：

- `RUN_ID = C1B_VS_DATASET_20260825_V1`，`status = BENCHMARK_COMPLETE`；
- 24 subjects / 48 pairs / 384 rows；
- 产出 `benchmark_metrics_long.csv`、`benchmark_metrics_primary.csv`、`benchmark_summary_primary.csv`、`pair_manifest.json`、`subject_disjoint_folds.csv`；
- 指标包含 `raw_hr_abs_error_bpm`、`raw_ibi_mae_ms`、`raw_rmssd_abs_error_ms`、`raw_sdnn_abs_error_ms`、`raw_precision/recall/f1`；
- 方法：`project_bandpass_peak`、`vitalsense_amf`（透明 Python 基线，非字节级 MATLAB 复现）；
- 校准：仅从 `VS01 Resting` 估一个全局固定延迟（−18.0 ms）并固定；
- 冻结协议的裁决文档早于正式结果：`docs/decisions/2026-08-25-gpt-c1b-dataset-local-ready-run-decision.md`、`...-timing-lag-evaluation-amendment.md`；
- 该报告自身明确写：**这次运行不构成 Radar beat / IBI / HRV 已验证**，HR/IBI/RMSSD/SDNN 仅作诊断。

**结论 `PARTIAL_CANDIDATE_SECONDARY`**：它**永远不能用于 C1**（没有 DataCube，机制无法表达）；对 **C2 可用**（频域选峰 + anchor 持久化只依赖位移波形），但由于本队列已产出过公开基准数字，它**只能作为 secondary external evidence，不能作为 primary untouched validation**。

### 3.2 `AgeBalanced_60GHz`

**Q：有 HR/ECG ground truth 吗？** 有：`movesense_ecg.csv`（时间戳 + mV，约 250 Hz）与加速度。

**Q：时间分辨率够吗？** 够：雷达帧周期 100 ms（10 Hz，30 s = 300 帧）。

**Q：有原始毫米波输入吗？** 有 range-FFT 域帧（`radar_rFFTs.zlib` + `radar_timestamps.csv` + `radar_chirpConfig.json`），**不是原始 ADC**，但保留距离维，理论上可做 target 选择。

**Q：能适配 30 s 契约吗？** 格式上可以。

**暴露判定：`DEVELOPMENT_EXPOSED`。** 这是最关键的排除理由——该队列**已经被用于 HR 路线的评估与选型**（`ANALYSIS_HISTORY_LEDGER.md` 2026-08-14 条目，commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1`），并且已经公布过具体数字：historical 220 Rest sessions 下 project route session-MAE median ≈ 9.5 BPM、high/medium/low ≈ 1.6/3.4/10.1 BPM、HPS 10.6→9.7（保留）、时间连续性 9.7→9.5（保留）、**固定呼吸谐波陷波 9.5→10.4（净负，已回退）**、top3 multi-bin consensus 9.5→9.3（2× locks 4→6）、VMD adaptive 22.5/25.4/32.1（不采用）；后来按官方 ECG FFT 参考重算 30 s pooled MAE = **10.361 BPM**，50 s 为 project 9.292 vs adapted SSA+VMD 9.012。

**结论 `INELIGIBLE_FOR_PRIMARY_VALIDATION`**：路线级暴露使其不再可能是"未触碰"验证集，即便 C2 的 anchor 代码本身不是那次调参的对象。

### 3.3 `mmWave_Heartbeat`（TI gby 批次）

**Q：有 HR/ECG ground truth 吗？** **没有。** 目录里只有 10 个 `.bin` 原始 ADC 文件（每个 13,107,200 bytes），没有 ECG、没有呼吸参考、没有时间戳、没有采集配置、没有被试映射。

**Q：时间分辨率够吗？** 无法判定——没有 chirp 配置也没有时间戳。

**Q：能适配 30 s 契约吗？** 不能：既没有时间基准，也没有窗口锚点。

**暴露判定：`NOT_EXPOSED_BUT_UNUSABLE`** —— 从未跑过任何分析（仓库里仅在 `CHANGELOG.md` 出现一次清单行），但因为没有参考信号而不可用。

**结论 `INELIGIBLE`**。

## 4. 汇总判定

| dataset | HR/ECG GT | 雷达输入类型 | 30 s 可行 | C1 | C2 | 暴露 | verdict |
|---|---|---|---|---|---|---|---|
| `VS_DATASET_healthy_v1` | 有（Lead II 500 Hz） | 预提取位移（`VitalSig`） | 是 | **否** | 是 | `DEVELOPMENT_EXPOSED`（已完成 C1b 基准） | `PARTIAL_CANDIDATE_SECONDARY` |
| `AgeBalanced_60GHz` | 有（ECG ~250 Hz） | 压缩 range-FFT 帧 | 是 | 否 | 否 | `DEVELOPMENT_EXPOSED`（HR 路线选型） | `INELIGIBLE_FOR_PRIMARY_VALIDATION` |
| `mmWave_Heartbeat_TI_gby` | **无** | 原始 ADC | 否 | 否 | 否 | 未暴露 | `INELIGIBLE` |

**没有任何外部资产对 C1 可用；C2 只有 `VS_DATASET` 可用，且只能算 secondary。**

## 5. 路由决定

```
PREREGISTRATION            = DONE
EXTERNAL_ASSET_INVENTORY   = COMPLETE
OPT_A_BUILD                = PROCEED_AS_PRIMARY

primary untouched validation : OPT_A（正式 cohort 116 sessions / 61 participant groups）
secondary external evidence  : VS_DATASET_healthy_v1（仅 C2，明确标注 secondary）
not usable                   : AgeBalanced（路线暴露）、TI gby（无参考）
```

**为什么仍然走 `OPT_A` 作为 primary**：真正"未触碰 + 参与者/场次不重叠"的验证集，三个外部资产都无法提供——`VS_DATASET` 已被 C1b 基准消费且承载不了 C1；`AgeBalanced` 已被路线选型消费；TI gby 无参考。**但这次审计不是白做**：`VS_DATASET` 给 C2 提供了一个 24 人、含 ECG Lead II 金标准、可切约 144 个 30 s 窗口的**独立外部旁证**，这是原计划里没有的资源。

### 对 C1/C2 验证结构的影响

- **C1**：只能由 `OPT_A` 承担（需要 DataCube 与 target 选择）。**且 C1 必须标注一条新边界：`VS_DATASET` 不构成 C1 的任何证据。**
- **C2**：primary 仍为 `OPT_A`；`VS_DATASET` 作为 **secondary external evidence** 单独报告，且必须声明其已暴露历史（C1b 基准）。**不得**把 `VS_DATASET` 的 C2 结果当作唯一放行依据。
- 判据与成功阈值**不变**（仍是 preregistration 里冻结的五条），不得因为外部数据可用而放松。

## 6. 边界声明

本任务：

- 未运行任何 C1/C2 或任何 HR 算法；未训练模型；未产生 candidate 输出；
- 未修改三个外部数据集中的任何文件；
- 未修改 producer、snapshot v1、target/window/fusion/harmonic/threshold；
- 未形成 snapshot v2；未解锁 HRV；HR/BR 仍 `HOLD / SUPPORTING_ONLY`；
- 未把 ECG 用于任何 production 选择。

## 7. 证据

- 本目录：`MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_REPORT.md`、`..._MANIFEST.json`、`EXTERNAL_ASSET_ASSESSMENT.csv`、`EXTERNAL_ASSET_HISTORY_TRACE.csv`、`ERROR_LOG.json`、`HANDOFF.md`
- 脚本：`scripts/maintenance/run_mmwave_external_validation_asset_audit_20260913.py`（deterministic，只做扫描与哈希）
- C1b 基准本地证据（local-only）：`11_数据/derived/vitalsense_c1b_benchmark_v1/`（`status.json`、`run_config.json`、`benchmark_report.md`、`benchmark_summary_primary.csv`）
- AgeBalanced 使用证据：`ANALYSIS_HISTORY_LEDGER.md` 2026-08-14 条目
- 预注册与验证集计划：`docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md`、`docs/canonical/MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`
- Issue #35
