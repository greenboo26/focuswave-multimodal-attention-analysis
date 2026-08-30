# pre_30s 协议窗口 + 完整 selector 链 HR/BR 重跑结果（2026-08-31）

Status: `PARTIAL / SUPPORTING`（3 个 targeted subject 试跑；不晋升 HR/BR 冻结边界）

## 背景与动机

- #24 冻结的 335-window diagnostic（20s targeted path）HR MAE 19–26 bpm；
- #27 已证明该 path 漏接了 producer 的完整 selector 链（time + harmonic fold + spectral + fusion）；
- 本重跑使用**协议定的 pre_30s 对齐窗口**（不是按误差选的窗口）+ **完整 selector 链**，重算 HR/BR，拿不受劣化配置污染的真实误差。

## 方法

- 数据：`sub-97793 / 9779 / 97795`（targeted validation 三 subject，含 ECG/RSP 金标准）
- 窗口：`pre_30s = [probe_onset-30000ms, probe_onset)`，裁剪到 block start；probe onset 取行为 CSV 的 `probe_onset_time`（unix_ms）
- HR：完整 selector 链 = 自动选 bin/channel（`select_separate_channels_bins`）+ time-domain peaks + `_fold_harmonic` + `_select_spectral_bpm` + time/frequency fusion；block-local previous 状态
- 两个估计器时长：30s 全程 / 25s 末尾段
- BR：自动选 `br_bin/br_ch` + `_select_breath_candidate`（bandpass + matlab-style 双分支取优）
- 金标准：ECG（`gold_standard_qa`，#24 冻结参数：0.5–40Hz / prominence 0.25 / IBI 300–2000ms / 20% 伪迹剔除）；RSP（呼吸带）
- 对齐：block-local event-unix-ms → Biopac sample affine mapping（复用 #24 既有实现）

## 结果（60 probe 窗口；ECG 有效 60/60）

### HR

| subject | 30s fused MAE | 25s fused MAE | 25s medianAE | 锁半频 |
|---|---:|---:|---:|---:|
| 97793 | 7.80 | 7.56 | 5.47 | 0/20 (0%) |
| 9779 | 6.56 | 6.47 | 1.13 | 0/20 (0%) |
| 97795 | 19.83 | 17.92 | 14.27 | 1/20 (5%) |
| 汇总 | 11.40 | 9.02 | 5.15 | 1/60 (2%) |

### BR

| subject | MAE (breaths/min) | medianAE | 锁半频 |
|---|---:|---:|---:|
| 97793 | 2.21 | 0.83 | 2/20 (10%) |
| 9779 | 1.56 | 0.59 | 2/20 (10%) |
| 97795 | 3.55 | 2.13 | 1/20 (5%) |
| 汇总 | 2.44 | 0.87 | 5/60 (8%) |

## 关键发现

1. **fusion 是完整链里起纠错作用的核心**：spectral 单独 MAE 12.7–16.1，fused 9.0–11.4；spectral 会在部分窗口锁到错误低值（51–59 bpm，ECG 80–88），fusion 用时域峰值 HR 拉回。
2. **`_fold_harmonic` 本次 0 次触发**（60 窗口全 False）：真正解决 08-16 所述「呼吸谐波半频锁定」的是 fusion，不是谐波折叠。
3. **9779 是 08-16 锁半频最严重的 subject**（任务段 -27~-29 bpm），本次 25s fused medianAE 1.13 bpm、锁半频 0%——完整链确实解决了锁半频。
4. **97795 劣化有明确原因**：frame 空洞（30s 窗口实际 2352–2699 帧，#28 已知 continuity 问题）+ mechanical block（1/3）锁频残留；focus block（2/4）HR 正常（89–103 vs ECG 92–95）。BR 在 97795 依然稳（MAE 3.55），呼吸信号对空洞更鲁棒。
5. **系统性负 bias**：HR fused bias 约 -4 至 -6 bpm（低估）。需在更大样本确认是否系统性。

## 边界（不构成晋升）

- 仅 3 个 targeted subject / 60 窗口，非全正式队列；
- pre_30s 是对齐窗口；内部估计器时长（25s/30s）未冻结，仍需 T4 窗口合同；
- selector 自动选 bin 偶发远距离错选（hr_bin=246~248 ≈ 9m），是剩余误差来源之一，对应 #27 target selection 未解决部分；
- HR/BR 冻结边界（`HOLD / SUPPORTING_ONLY`）不变；本结果只更新 supporting 证据层。

## 资产

- 脚本（Git-safe）：`scripts/maintenance/run_mmwave_pre30s_selector_hr_20260831.py`
- 逐窗结果（local-only）：`D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831\`
- 运行环境：`08_算法/.venv_t0`（sktime 1.1.0 + vmdpy 0.2 + bioread 2025.5.2）
