# pre_30s 协议窗口 + 完整 selector 链 HR/BR 重跑结果：6 场次扩样（2026-08-31）

Status: `PARTIAL / SUPPORTING`（6 场次扩样；97792 判 not_estimable 跳过，实际 5 场次 100 窗；不晋升 HR/BR 冻结边界）

## 背景与动机

- 08-31 的 3 场次试跑（97793/9779/97795，60 窗）证明完整 selector 链把 HR 25s fused MAE 压到 9.02、锁半频 1/60；
- 飞书工作日志（08-16）与本地数据盘点证实：带 ECG+RSP 金标准的正式场次共 6 个（9779/97792/97793/97794/97795/97796，同一被试反复测量），另外 3 个场次（97792/97796/97794）三件套（acq+beh+mmwave）本地完整、无任何排除记录，属遗漏；
- 本扩样把 SUBJECTS 扩为 6 个重跑，目标把验证从 60 窗扩到约 120 窗。

## 只读验证结果（先验后跑）

逐场次核验 beh CSV、acq 解码、marker 对齐，全部通过才进入重跑：

| 场次 | beh Block CSV | probe onsets | acq 解码 | block 状态 | marker exact | 判定 |
|---|---|---|---|---|---|---|
| 97792 | 无 Block CSV（仅 SART_97792_Practice_run1.csv 等） | 不可得 | 可解码（97792.acq，2000Hz，566978 样本，190 pulses） | 4 block 全 not_recorded | 无 | **跳过 not_estimable** |
| 97796 | Block1-4 各 5 probes（onset 全非空） | 20/20 | 可解码（1416 pulses） | 4 block 全 complete | 4/4 exact，fit p95 2.40–3.40 ms | 通过 |
| 97794 | Block1-4 各 5 probes（onset 全非空） | 20/20 | 可解码（1392 pulses） | 4 block 全 complete | 4/4 exact，fit p95 2.07–3.26 ms | 通过 |

- **97792 跳过原因**：beh 目录无任何 Block 行为 CSV；events.csv 230 行仅 baseline 段（226 tick + start/end 各 1），无 block1-4 的 segment_start/end 事件。该场次只采到 baseline+practice，未进入正式 block，probe 窗口不存在。acq 虽可解码（190 pulses），但无对应 block 事件可用。
- **97794 命名坑**：目录名 `sub-97994_`，且目录内 beh/mmwave 文件名前缀全为 `sub-97994_*`（acq 文件名 97794.acq 正确）。脚本用文件主体 97994 读文件，输出行的 subject 统一写回 97794。
- **97795 命名坑**：acq 文件名误写 `97995.acq`（目录 sub-97795_ 正确，目录内唯一 acq），脚本显式映射该文件名。
- 旧 3 场次的既有口径保持不变（97793 仅 block1/block2 complete，block1 非 exact：index 73 event 103 vs physical 102，但 fit p95 2.67 ms 仍可用；9779 仅 block1/block2 complete）。

## 方法

- 数据：`sub-97793 / 9779 / 97795 / 97792 / 97796 / 97794`（97792 验证后跳过）
- 窗口：`pre_30s = [probe_onset-30000ms, probe_onset)`，裁剪到 block start；probe onset 取行为 CSV 的 `probe_onset_time`（unix_ms）
- HR：完整 selector 链 = 自动选 bin/channel（`select_separate_channels_bins`）+ time-domain peaks + `_fold_harmonic` + `_select_spectral_bpm` + time/frequency fusion；block-local previous 状态
- 两个估计器时长：30s 全程 / 25s 末尾段
- BR：自动选 `br_bin/br_ch` + `_select_breath_candidate`
- 金标准：ECG（0.5–40Hz / prominence 0.25 / IBI 300–2000ms / 20% 伪迹剔除）；RSP（呼吸带）
- 对齐：block-local event-unix-ms → Biopac sample affine mapping（复用 #24 既有实现）
- 脚本改动仅三处：SUBJECTS 扩为 6；新增 `ACQ_FILE_OVERRIDES` / `FILE_KEY_OVERRIDES` 命名映射（含 `install_target_overrides`）；输出改新目录不覆盖旧结果

## 结果（100 probe 窗口；ECG 有效 100/100）

### HR

| subject | 30s fused MAE | 25s fused MAE | 25s medianAE | 锁半频 |
|---|---:|---:|---:|---:|
| 97793 | 7.80 | 7.56 | 5.47 | 0/20 (0%) |
| 9779 | 6.56 | 6.47 | 1.13 | 0/20 (0%) |
| 97795 | 19.83 | 17.92 (n=9) | 14.27 | 1/20 (5%) |
| 97796 | 11.64 | 8.96 (n=7) | 2.74 | 0/20 (0%) |
| 97794 | 8.31 | 9.83 (n=9) | 7.94 | 0/20 (0%) |
| 汇总 | 10.83 | 9.12 (n=65) | 5.79 | 1/100 (1%) |

注：25s 估计器要求窗口 ≥2500 帧；97795/97796/97794 有部分 probe 靠近 block start（win_start 被裁剪到 block start），窗口不足 25s 帧，故 25s 可评估 n 小于 20。97793/9779 全部 20/20。

### BR

| subject | MAE (breaths/min) | medianAE | 锁半频 |
|---|---:|---:|---:|
| 97793 | 2.21 | 0.83 | 2/20 (10%) |
| 9779 | 1.56 | 0.59 | 2/20 (10%) |
| 97795 | 3.55 | 2.13 | 1/20 (5%) |
| 97796 | 6.94 | 5.46 | 3/20 (15%) |
| 97794 | 6.58 | 6.92 | 4/20 (20%) |
| 汇总 | 4.17 | 1.70 | 12/100 (12%) |

### 与旧 3 场次汇总对比

| 指标 | 旧 3 场次（60 窗） | 6 场次扩样（100 窗） |
|---|---:|---:|
| 30s fused MAE | 11.40 | 10.83 |
| 25s fused MAE | 9.02 | 9.12 |
| 25s medianAE | 5.15 | 5.79 |
| HR 锁半频 | 1/60 (2%) | 1/100 (1%) |
| BR MAE | 2.44 | 4.17 |
| BR medianAE | 0.87 | 1.70 |
| BR 锁半频 | 5/60 (8%) | 12/100 (12%) |

旧 3 场次的分场次数值全部复现（97793 7.80/7.56/5.47、9779 6.56/6.47/1.13、97795 19.83/17.92/14.27 与旧文档逐位一致），说明扩样修改未扰动旧场次行为。

## 关键发现

1. **fusion 纠错在新场次复现**：97796 30s spectral MAE 15.12 → fused 11.64；97794 12.24 → 8.31。5 个可估场次 fused 全部优于 spectral（汇总 15.13 → 10.83），fusion 起纠错作用的结论在扩样后依然成立。
2. **`_fold_harmonic` 100 窗 0 次触发**：与 3 场次结论一致，锁半频的解决靠 fusion 而不是谐波折叠。
3. **97796 锁半频情况**：30s/25s 锁半频均 0/20，但存在大幅低估（bias -10.94）；最差 3 窗 fused 62–65 vs ECG 85–91，比率约 0.70，属低频低估而非半频锁定（不在 0.42–0.58 区间）。25s fused medianAE 2.74 远好于 30s 的 10.19，末尾段更贴近 probe 时刻。
4. **负 bias 系统性复现**：5 场次 30s fused bias 全部为负（-4.19 至 -17.05），汇总 -8.77（30s）/ -6.58（25s）。旧 3 场次的系统性低估在新场次上进一步确认，且 97795（-17.05）与 97796（-10.94）拉大总体幅度。
5. **BR 在新场次劣化**：97796 MAE 6.94（锁半频 3/20，BR 9–10 vs RSP 20–23）、97794 MAE 6.58（锁半频 4/20，比率 0.50–0.55）。BR 锁半频汇总 8% → 12%，MAE 2.44 → 4.17。呼吸信号的半频锁定在新场次上更频繁，BR 结论比 HR 弱。
6. **hr_bin 远距离错选在新场次复现**：97796/97794 均出现 hr_bin=244–247（≈9m）与 55/83（≈2–3m）错选；97794 block4 最差窗即 bin=245 错选（fused 58.2 vs ECG 76.7）。与旧文档"selector 自动选 bin 偶发远距离错选是剩余误差来源"一致，仍属 #27 未解决部分。

## 边界（不构成晋升）

- 97792 判 not_estimable 跳过，实际扩样 5 场次 100 窗，未达 120 窗目标；97792 场次本身只采到 baseline+practice；
- 其余边界与旧 3 场次一致：仅 targeted subject 反复测量，非全正式队列；pre_30s 是对齐窗口，内部估计器时长未冻结；HR/BR 冻结边界（`HOLD / SUPPORTING_ONLY`）不变，本结果只更新 supporting 证据层；
- BR 的锁半频上升提示：若后续正式队列包含更多场次，呼吸估计需要单独的 half-harmonic 门控，不能沿用 HR 的 fusion 结论。

## 资产

- 脚本（Git-safe）：`scripts/maintenance/run_mmwave_pre30s_selector_hr_20260831.py`
- 逐窗结果（local-only）：`D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831_6subjects_expanded\`（5 个分场次 CSV + all_subjects CSV + run_stdout.log；旧 3 场次目录 `mmwave_pre30s_selector_hr_20260831\` 未动）
- 运行环境：`08_算法/.venv_t0`（sktime 1.1.0 + vmdpy 0.2 + bioread 2025.5.2）
- 本扩样文档：`PRE30S_SELECTOR_HR_BR_RESULT_EXPANDED_6SUBJECTS.md`（旧文档 `PRE30S_SELECTOR_HR_BR_RESULT.md` 保留未覆盖）
