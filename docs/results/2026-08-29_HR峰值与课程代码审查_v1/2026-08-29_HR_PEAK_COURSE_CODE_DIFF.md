# HR peak 与 HR course 代码调用链差异（只读代码追踪）

状态：PASS（代码位置与参数已按当前文件内容核对；未修改源码，未运行新算法，未重跑 formal，未做 BR/HRV 分析）。

## 1. 追踪范围与术语映射

目标代码仓库：`D:\Project\厚粲杯\08_算法`。

当前正式时间门控入口：

```text
scripts/run_timeline_gated_mmwave_quality.py::main()
  -> gate.discover_records()
  -> behavior_time_gate.build_record()
  -> behavior_time_gate.build_segments()
  -> run_timeline_gated_mmwave_quality.py::run_analysis()
  -> process_vital_signs_v3_1_1.analyze_long_record()
  -> _analyze_long_record_v23()
  -> _analyze_displacement_v23()
  -> heart-rate branches
  -> save_result()
```

正式 runner 的实际调用位于 `run_timeline_gated_mmwave_quality.py:70-109`；默认 `method` 为 `vmd_heart`，调用时传入每个 baseline/block 的 `frame_start` 与 `frame_end`（`run_timeline_gated_mmwave_quality.py:112-129`）。该入口没有传入 `forced_heart_ch`、`forced_heart_bin`、`heart_reference_candidates`、`ext_br_bpm` 或 `acq_path`。

本文件中的“HR peak”按代码输出链记录为：

- 全段峰检测 `detect_peaks_heart_lo()` 产生的 `heart_peaks`；
- 全段峰间期得到的 `hr_time_bpm`，经窗口参考校正/共识后写入 `heart_rate.time_bpm`。

“HR course”按代码输出链记录为：

- `estimate_hr_time_course()` 产生的 `heart_rate.time_course.points[*]`；
- 每个点的 `time_bpm`、`freq_bpm`、`fused_raw_bpm`、平滑后的 `fused_bpm`；
- 顶层 `heart_rate.fused_bpm` 为 `time_course.fused_median_bpm`。

以下只列代码事实；不评价哪条链为何有效，也不重复 corrected-gate robustness 分析。

## 2. 共同输入与共同前处理

### 2.1 输入数据与帧范围

- `collect_npz_parts()` 按 `sub-{subject}_mmwave_datacube_part*.npz` 收集分片；正式 runner 在 `run_timeline_gated_mmwave_quality.py:80-87` 传入 segment 帧范围。
- `behavior_time_gate.py:146-164` 从 `master_timeline.csv` 的 `baseline_start/stop` 与 `block_start/stop` 建立独立 segment；`_make_segment()` 在 `behavior_time_gate.py:127-143` 用毫米波时间戳映射为 `[frame_start, frame_end)`。
- `process_vital_signs_v3_1_1.py:_load_chunk()`（`1103-1108`）读取 NPZ 中按字典序排序的 `tx*` 数组，`np.stack(..., axis=-1).astype(np.complex64)`；`_as_range_cube()`（`1111-1112`）只转换为 `complex64` 数组。
- 当前 producer 代码没有 raw ADC 到 Range FFT 的步骤；其输入接口直接接收 range-bin/channel complex 数据。
- 代码常量：`FS=100.0` Hz、`N_CH=8`（`process_vital_signs_v3_1_1.py:13-15`）。
- 距离轴默认参数为 `bin_spacing_m=0.08` m、`range_bias_m=0.0` m（`process_vital_signs_v3_1_1.py:17-18, 2970-2973`）；代码没有定义 37 mm/bin 常量。该参数只在距离门控/距离轴记录中使用，信号抽取按 bin 索引读取。

### 2.2 target bin/channel 来源

HR peak 与 HR course 使用同一个选定的心跳 `channel/bin`，不是各自重新选择：

1. `accumulate_range_profile()`（`1146-1172`）在当前 segment 的所有选定帧上累计 bin/channel power。
2. `_analyze_long_record_v23()`（`2828-2845`）先计算 `0.3–1.5 m` 默认距离门，并将门外 bin 的累计 power 置零（`2835-2842`）。
3. `_select_refined_heart_candidate()`（`2316-2376`）对每个 channel 从 `select_bins_from_profile()` 返回的候选中取 `top_k_per_channel=1`（调用位于 `2847-2860`），并评估候选的完整 segment。
4. `select_bins_from_profile()`（`1194-1233`）的候选条件为 bin power 至少为该 channel 最大 bin power 的 `1%`；第一次要求 `0.1 < phase variance < 50`，为空时取消该相位方差条件；仍为空时退回最大 power bin。HR bin 按 `heart_score = log1p(hr_snr) * phase_stability**2` 取最大；channel 再按 `best_hr_selection_score` 取最大（`1374-1411`）。
5. `_select_refined_heart_candidate()` 对通过 10 s 信号门的候选按 `_score_heart_candidate_result()` 排序，返回一个 `(channel, heart_bin)`（`2368-2376`）。默认正式 runner 没有传 `heart_reference_candidates`，因此活动候选来源为 `phase_stable_auto`（`2339-2362`）。
6. `extract_displacement_separate()`（`1415-1435`）对该 `(heart_bin, heart_ch)` 调用 `extract_displacement()`；`extract_displacement()`（`268-270`）执行 `unwrap(angle)`，并按 `5.0 * phase / (4*pi)` 转为位移。

因此，HR peak 与 HR course 的输入信号、target channel、target bin、segment 范围和 VMD 心跳波形相同；差异从同一 `heart_pd` 进入两个 HR 估计支路后出现。

## 3. 共同心跳分离链

- `_analyze_displacement_v23()`（`2379-2416`）先对 `disp_hr` 做四阶 Butterworth 零相位带通 `0.8–2.0 Hz`（`2391-2392`）。
- 正式默认 `method="vmd_heart"` 时，调用 `separate_vmd_heart_windowed()`（`2393-2400`）。该函数使用 `window_s=40.0` s、`step_s=20.0` s（`1296-1304`）；每个片段调用 `separate_vmd_heart_only()`（`1316-1323`）。
- `separate_vmd_heart_only()` 调用 VMD：`alpha=1000, tau=0, K=3, DC=False, init=1, tol=1e-6`（`305-318`）。三个 mode 的角色代码记录为呼吸、心跳、噪声残差（`383-389`）。
- VMD mode 选择使用 HR band energy，并可使用 `hr_freq_hint`；呼吸 mode 选择使用 `br_freq_hint` 或 BR band energy（`289-302, 320-359`）。选中 mode 后，如有 `best_freq`，再做 `[best_freq-0.35, best_freq+0.35]` 与 `[0.8,2.0]` 的交集带通（`377-381`）。
- 若 `len(disp_hr)<200`，走 `bp_fallback_short_signal`；若没有有效 VMD 心跳 mode，走 `bp_fallback_no_valid_mode`（`305-314, 361-367`）。
- 若 `method` 不是 `vmd_heart`，则使用先前的 `0.8–2.0 Hz` 带通结果作为 `heart_pd`（`2393-2405`）。正式时间门控 runner 默认传入 `vmd_heart`（`run_timeline_gated_mmwave_quality.py:112-119`）。

## 4. HR peak 与 HR course 差异表

| 项目 | HR peak | HR course | 真实代码位置 |
|---|---|---|---|
| 输出对象 | `heart_rate.time_bpm`；峰数组为 `heart_peaks`/`n_peaks` | `heart_rate.time_course.points[*]`；顶层 `heart_rate.fused_bpm` 是 course fused median | `process_vital_signs_v3_1_1.py:2459-2482`, `1442-1480` |
| 主窗口长度 | 全部当前 segment 的 `heart_pd` 做一次峰检测；另有内部 segment correction 的 `20.0 s` 窗口 | 每点 `window_s=25.0 s`，`step_s=5.0 s`；每点另有 `10.0 s` signal-QC window | `1244-1293`; `1947-2015`; `857-918` |
| HR frequency range | `48–120 bpm`，来自 `HR_LO_HZ=0.8`、`HR_HI_HZ=2.0` | 同为 `48–120 bpm`；函数默认 `lo_bpm=HR_LO_BPM`、`hi_bpm=HR_HI_BPM` | `13-26, 857-865, 1244-1249` |
| 时间域方法 | `find_peaks` 得到一条全段 peak train；全局 `60*FS/mean(diff(hp))` | 每个 25 s 窗口取局部 peaks，经 robust IBI 估计 `60/median(clean IBI)` | `1244-1293`; `2407-2410`; `686-710`; `930-932` |
| 频域/PSD 方法 | 不是 peak 主估计；内部 20 s correction 对每窗调用 `signal.periodogram(..., window="hann")`，取 HR band 最大 PSD bin | 每个 25 s 窗口线性 detrend 后 `periodogram(..., window="hann", nfft=next_pow2(max(8*N,256)), scaling="spectrum")` | `1886-1894`; `727-742` |
| peak 的参数 | `distance=max(100*60/120, 100*0.3)=50` frames；prominence 依次为 `[0.1,0.08,0.05,0.04,0.03,0.02,0.01]*std`；保留最高 `len(IBI)*(1-min(CV,1))` 的一组 | 局部时间域要求至少 4 peaks、至少 3 个合法 IBI；MAD tolerance=`max(0.10, 3.5*1.4826*MAD, 0.20*median_IBI)` | `1244-1265`; `686-710` |
| candidate 数量 | peak detector 尝试 7 个 prominence 配置，最终只保留 1 个 `best_peaks` 数组；每个内部 20 s PSD window 只取 1 个最大 band bin | 每个 25 s PSD window 最多保留 8 个谱峰 candidate；若 `find_peaks` 找不到，退回 1 个 `argmax(band_power)` candidate | `1253-1265`; `1886-1894`; `727-742` |
| 是否使用上一窗口 | 主 `detect_peaks_heart_lo()` 不使用上一窗口；但最终共享的 20 s correction 有 `current_ref`，每窗按 `0.7*current_ref+0.3*corrected` 更新 | 使用。`previous_bpm` 初始为 `reference_bpm`；每点在 confidence≥`0.12` 时更新为 `0.8*previous+0.2*fused` | `686-710`; `1984-2002`; `896-897, 931, 972-973` |
| temporal continuity | peak detector 没有跨 25 s course window 的递归状态；内部 correction 的 `current_ref` 仅用于后续 20 s correction window | 使用 `previous_bpm` 参与谱 candidate 打分，权重惩罚为 `0.025*abs(candidate-previous_bpm)`；并作为 harmonic anchor/fusion anchor | `745-775`; `1984-2002`; `931-940` |
| 是否平滑 | peak 时间戳、全局 mean-IBI HR 不平滑 | 对 `fused_raw`：低置信点插值、3 点 median filter、前向递推、反向递推；输出使用 `fused_smooth` | `778-801`; `980-1006` |
| 是否限制跳变 | 对 peak train 的局部 IBI 做 `0.3*ref_ibi ≤ local_ibi ≤ 3.0*ref_ibi` 保留；没有 7 bpm course clamp | 每次前向/反向递推均限制相对相邻值的最大步长 `max_step_bpm=7.0`；time/frequency gap 超过 `10.0 bpm` 标记 warning | `1279-1293`; `792-800`; `942-958, 1010-1014` |
| fallback | `x_std<1e-8` 或最终 peak 数不足时返回空 peak；VMD 分离另有 BP fallback；内部 correction 无足够窗时返回 base frequency | 无谱 candidate 时先用 band argmax；只存在 time 或 freq 时单支路输出；两者都无时 fused 为 NaN；signal-QC 不通过的点最终保持 NaN | `1244-1248,1267-1268`; `305-314,361-367`; `736-742`; `959-970`; `985-987` |
| BR/harmonic 信息 | peak 检测本身不读取 BR；共享 VMD 接收 `br_freq_hint`。内部 20 s correction 可调用外部 RSP harmonic reject，但 formal runner 未传 `acq_path`/`ext_br_bpm`，该外部 BR 分支在该入口为 disabled。内部 half/double harmonic correction 仍可基于 `reference_bpm` | course 函数本身不直接读取 BR；其频率选择使用 `time_bpm/previous_bpm/reference_bpm` 做 half/double fold。course 前的共享 VMD 使用 `br_freq_hint`；外部 RSP harmonic reject 同样仅在 `ext_br_bpm` 非空时进入 | `2394-2398`; `1800-1826,1836-1846`; `1903-1909`; `713-724,767-774`; `2988-3021` |
| 质量分数 | `_robust_time_bpm()` 产生 `count_quality*regularity_quality`；候选 bin 的最终选择分数还加入 peak bonus、time/freq gap、window std、course metrics、signal usable ratio；signal hard gate 要求 usable ratio≥`0.50` | 每点 `confidence`：time/freq 同时存在且 gap≤10 时为 `exp(-gap/12)*sqrt(time_quality*freq_quality)`；单支路分别为 `0.45*time_quality` 或 `0.35*freq_quality`；输出 quality=`rejected/low/medium/high` | `686-710`; `2018-2089`; `942-999` |
| 最终写出 | JSON `heart_rate.time_bpm`, `heart_rate.time_bpm_global`, `heart_rate.n_peaks`；NPZ `heart_peaks` | JSON `heart_rate.time_course` 与顶层 `heart_rate.fused_bpm`；NPZ `hr_course_time_s`, `hr_course_time_bpm`, `hr_course_freq_bpm`, `hr_course_fused_raw_bpm`, `hr_course_fused_bpm`, `hr_course_confidence` 等 | `2407-2482`; `1442-1480` |

## 5. 代码差异的最小事实摘要

1. HR peak 是一条全段 peak train 的峰间期 HR；HR course 是 25 s/5 s 滑窗内的局部 IBI 与 PSD candidate 融合轨迹。
2. HR peak 的 peak detector 采用 7 个 prominence 试探并只保留一组 peak；HR course 的每个频谱窗最多保留 8 个 PSD 局部峰 candidate。
3. HR peak 的主 detector 不使用上一窗口、不做 course smoothing，也没有 7 bpm 跳变限幅；HR course 明确使用 `previous_bpm`、前后向平滑和 `7.0 bpm` 单步限制。
4. 两条链共享 NPZ 输入、segment 帧范围、target heart channel/bin、位移抽取、VMD/带通心跳波形、HR band 与候选 bin 评分；差异发生在 `detect_peaks_heart_lo()`、`_heart_segment_reference_correction()`、`_heart_window_consensus_bpm()` 与 `estimate_hr_time_course()` 的组合方式。

## 6. 证据文件与当前状态

- Producer：`D:\Project\厚粲杯\08_算法\scripts\process_vital_signs_v3_1_1.py`；当前 SHA256：`DA3E9692463508B234B744532097D0C6FF3DCA056FA5E748B6C25967E3A5C639`。
- Formal runner：`D:\Project\厚粲杯\08_算法\scripts\run_timeline_gated_mmwave_quality.py`；当前工作区存在未提交修改，本任务未修改该文件。
- Segment builder：`D:\Project\厚粲杯\08_算法\scripts\behavior_time_gate.py`。
- 已读取既有代码审计文件：`D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\MMWAVE_ALGORITHM_AND_RANGE_GATE_AUDIT_V1.md`；本任务仅使用其入口定位，参数均回到当前代码逐项核对。
