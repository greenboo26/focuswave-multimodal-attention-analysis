# MMWAVE ALGORITHM AND RANGE GATE AUDIT V1

日期：2026-08-28 ；状态：**PARTIAL / evidence-bounded**

本审计只回读当前代码、当前配置和已经存在的 formal/target-lock/reference 产物；没有重新运行 formal 全量算法，没有继续修改算法，也没有启动专注建模。`mmwave_algorithm_failure_trigger_audit.csv` 是本报告的逐 session 附表。

## 1. 当前实际脚本、commit、入口

| 角色 | 实际路径 | 入口/关键函数 | 版本证据 |
|---|---|---|---|
| 生命体征 producer | `D:\Project\厚粲杯\08_算法\scripts\process_vital_signs_v3_1_1.py` | `analyze_long_record()` → `_analyze_long_record_v23()`；强制心跳候选另有 `_analyze_long_record_with_forced_heart_candidate_v23()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; SHA256 `da3e9692463508b234b744532097d0c6ff3dca056fa5e748b6c25967e3a5c639` |
| formal 时间门控 batch runner | `D:\Project\厚粲杯\08_算法\scripts\run_timeline_gated_mmwave_quality.py` | `main()` → `run_analysis()` → `algo.analyze_long_record()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; current SHA256 `5c4d9f30df1d3c8ad8b80cd80579551cc01052c895821d693d1d9c1224cb1147`; working tree modified |
| formal 信号存在性 scanner | `D:\Project\厚粲杯\08_算法\scripts\scan_timeline_gated_quality.py` | `main()` → `scan_segment()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; current SHA256 `53ff7009943bdc17dc4a54b89011c763f6620de588fc6017138e2108c220cc48`; working tree modified |
| J 盘 target-lock audit | `D:\Project\厚粲杯\11_数据\derived\audit_j_mmwave_target_lock_v1.py` | `main()` → `quality_core.scan_subject()` | 不在算法仓库；无该仓库 commit；SHA256 `7b0c080a5198f84ff6c31d63012184bd4a4549d8de95a6be309259f2725b7335` |
| scanner 核心 | `D:\Project\厚粲杯\08_算法\scripts\_scan_quality.py` | `scan_subject()` | Git last commit `9b4dc1b6073f3533f0a37b4b4f4906c97beb39ce`; SHA256 `29ed5646c3facecb231f0fefabdaacf72846bf7d2ccaf48536e6c78ef192b0f5` |
| 本机路径配置 | `D:\Project\厚粲杯\08_算法\configs\paths.local.json` | `formal_data_root` → `J:/Data`；`project_data_root` → `D:/Project/厚粲杯/11_数据` | 非代码配置；SHA256 `b933d4d6ef179641136bee8b0e2f9c6222a08a7615ecfc8df8ef0c004696cbdb` |

当前 QC v1 的 72 场分层读取了既有 session matrix、`subject_summary.csv`、formal output audit 和 J 盘 target-lock audit；因此“实际用于 QC v1”的证据链是 `_scan_quality`/target-lock 产物加上既有 summary，不是本轮新跑出的 HR/RR 对照结果。

配置边界：`configs/paths.local.json` 的 `formal_data_root` 是 `J:/Data`；但 `run_timeline_gated_mmwave_quality.py` 与 `scan_timeline_gated_quality.py` 内仍保留 `E:\Data`、`F:\正式实验` 默认 roots，且没有在入口处读取 `paths.local.json`。本次 target-lock audit 的输入根由其代码显式固定为 `J:\Data`，不能把两个默认 roots 当作本批实际输入。

## 2. 输入数据解释：已经是 range-bin complex data

`process_vital_signs_v3_1_1.py::_load_chunk()` 读取 NPZ 中按 `tx` 排序的 8 个数组，`np.stack(..., axis=-1).astype(np.complex64)`；`_as_range_cube()` 只做数组类型/形状转换。因此当前 producer 把输入解释为 **frame × range-bin × 8-channel 的 complex range-bin data**。

当前 producer 没有 raw ADC → Range FFT 的步骤。代码中的 `np.fft.rfft()`/`rfftfreq()`用于已提取相位/位移的时间频谱；`save_range_fft_*` 名称对应的诊断图也只是对已进入 range-bin cube 的幅度做可视化。上游是否曾从 raw ADC 生成这些 NPZ，不在当前 QC producer 链可见范围内。

## 3. 当前 HR/RR 流程

### Range bin 和 channel

- `_scan_quality.scan_subject()`：先对全 session 累积 range-bin/channel power；用第一个最多 1,000 frame 的样本调用 `select_separate_channels_bins()`，在所有 8 channels 上分别计算候选 bin 的 phase variance、HR/BR band SNR 和 phase-stability score；BR 与 HR 分别取最高分 channel/bin。
- `scan_timeline_gated_quality.scan_segment()`：对每个 baseline 或正式 block 重新累积、重新选一次 bin/channel；不是每个 10 s QC window 重新选择。`_scan_quality` 的 J 盘 target audit 则是每个 session 全时段选一次。
- 普通 producer `analyze_long_record()`：对每个传入的行为 segment/block 固定一次选择；先使用 distance gate 后再做 BR/HR 选择和 HR candidate refinement。不是 session 内每个输出 window 重新选。
- BR 与 HR **不保证共用** bin/channel：结果字段分别保存 `channels.breath/channels.heart` 与 `bins.breath/bins.heart`。

### Phase、band 和 rate estimator

- phase：`np.unwrap(np.angle(complex_signal))`；普通 producer 的 selected signal 在 segment 范围内展开；`_scan_quality` 的 target scan 对每个 NPZ part 分别展开，然后带通。
- 呼吸 band：`0.10–0.50 Hz`（6–30 bpm）。这是当前 mmWave producer；不能与 ECG/RSP 小样本复盘中的 RSP `0.10–0.70 Hz`混写。
- cardiac band：`0.80–2.00 Hz`（48–120 bpm）。
- 完整 producer 的 HR 不是单一方法：包含 heart peak detector/IBI time estimate、periodogram frequency estimate、VMD heart-mode selection 和 time-course/fusion。`_scan_quality`/`scan_timeline_gated_quality` 只计算心跳带位移的 10 s std 信号存在性，不输出 HR/RR 数值。
- 完整 producer 的 BR 是 consensus peak/periodogram 候选并包含 MATLAB-style 分支；但当前 formal runner 没有传 `acq_path`，所以外部 RSP 呼吸率与 `respiration_harmonic_reject()` 这条参考辅助支路在当前 formal batch runner 中没有被激活。

## 4. 人体范围限制和 localization

| 项目 | 实际代码/产物结论 |
|---|---|
| producer 默认 `min_range_m/max_range_m` | `0.30 / 1.50 m`；普通 `_analyze_long_record_v23()` 将 mask 应用于 breath 和 heart。 |
| `bin_to_meter` | `distance_m = bin_idx * bin_spacing_m - range_bias_m`；默认 `bin_spacing_m=0.08 m`、`range_bias_m=0.0 m`。 |
| 当前 scanner 是否应用该 gate | **没有**。`_scan_quality.py` 和 `scan_timeline_gated_quality.py`调用 bin selector 时未传入 distance mask；target-lock audit 另用 `0.20–1.00 m` 对自动候选距离作 preliminary 分类。 |
| 是否显式建模胸腔 | 没有。距离 gate 只是工程范围限制，不等于胸腔真值。 |
| 是否排除键盘/桌面/近场反射 | 未见对应的对象/平面/近场分类规则；不能声称已排除。 |
| 是否用静息基线定胸腔 bin | 当前 formal runner 未传 `heart_reference_candidates`，未见静息 baseline 自动锁定胸腔 bin。 |
| range-bin jump gate | 未实现/未出现在当前产物；`range_bin_jump_rate` 没有被计算。 |

## 5. B=44 的实际触发机制

B 的 44 场不是由一个叫 `range_bin_jump_rate` 的字段触发。当前 evidence breakdown 是：

- **36 场**：target-lock `distance_implausible`，具体字段是 `distance_gate_020_100m=False` 和自动候选 `hr_bin_dist_m` 落在 `0.20–1.00 m` 之外。
- **8 场**：`plausible_distance_phase_unstable`，具体字段是 `phase_stability_ge_090=False`。

现有 B 证据中没有 `motion_artifact_ratio`、`valid_phase_coverage` 或 `range_bin_jump_rate`。`phase_stability` 是基于相位 roughness/jump ratio/oscillation 的综合 proxy，不能改写成 motion-artifact ratio。target-lock 是全 session 扫描，而 formal segment scanner 是按 baseline/block 切分；当前输出没有字段能证明某个 B 是由 window 切错导致。因此 window miscut 只能列为待查风险，不能作为已触发 B 的事实。

## 6. C=9 的实际触发机制与 ECG/RSP 指标边界

C 的 9 场是：`056, 058, 062, 081, 084, 104, 118, 162, 166`。它们都已有输入/输出链和 target candidate，但 `subject_summary.csv` 中 `window_quality_pct < 80` 或 `probe_quality_pct < 80`；这就是当前 C trigger。精确值已写入附表 `c_trigger_fields`。

| session_id | 实际 C trigger |
|---|---|
| 056 | `window_quality_pct=51.02<80 or probe_quality_pct=65.00<80` |
| 058 | `window_quality_pct=78.00<80 or probe_quality_pct=100.00<80` |
| 062 | `window_quality_pct=18.75<80 or probe_quality_pct=50.00<80` |
| 081 | `window_quality_pct=79.17<80 or probe_quality_pct=80.00<80` |
| 084 | `window_quality_pct=64.29<80 or probe_quality_pct=60.00<80` |
| 104 | `window_quality_pct=58.33<80 or probe_quality_pct=85.00<80` |
| 118 | `window_quality_pct=43.48<80 or probe_quality_pct=50.00<80` |
| 162 | `window_quality_pct=79.31<80 or probe_quality_pct=100.00<80` |
| 166 | `window_quality_pct=65.91<80 or probe_quality_pct=90.00<80` |

这 9 场**不是**由 per-session HR/RR MAE、bias、correlation、`harmonic_suspect`、`low_corr` 或 `stable_bias` 触发，因为这些字段不在当前 formal 70 场输入/输出中；也不能从当前文件证明“RR pass 但 HR fail”。当前 C 只能说“既有 signal-existence/probe coverage gate 未过，局部原因未解析”，不能写成 HR/RR 生理准确性失败。

可计算的 ECG/RSP 参考指标只来自独立的历史小样本 reference CSV（5 场参考、100 个 60 s 窗口；当前指标行 99），不是 formal 70 场逐 session gate：

| 参考比较 | n / 参考窗口分母 | MAE | bias（mmWave−reference） | correlation |
|---|---:|---:|---:|---:|
| HR peak | 99 / 100 | 7.822 bpm | -6.957 bpm | 0.324 |
| HR course | 99 / 100 | 4.590 bpm | -1.078 bpm | 0.702 |
| BR peak | 99 / 100 | 11.769 bpm | -11.769 bpm | -0.046 |

这些 aggregate 不能回填为 C=9 的 per-session 指标，也没有被当前 formal C gate 使用。当前 formal 70 场的 coverage 总和是 `2894/3525` 个 10 s signal-existence windows、`1297/1400` 个 probe-level quality flags；后者不是 HR/RR pass。

更正说明：上表 `HR course` 行保留为 historical old-gate calibration 快照。当前 corrected HR-course 口径应写作 `target/channel 79/99、course 99/99、MAE=3.777 bpm（约 3.78 bpm）、Pearson r=.605`；`4.590 bpm / r=.702` 仅作 historical old-gate calibration result，因此本节关于 HR course 的现位解释应视为 `MATERIALLY_AFFECTED`。

## 7. 审计表字段说明

完整文件：`mmwave_algorithm_failure_trigger_audit.csv`。

- `range_min_m/range_max_m` 填的是普通 v3.1.1 producer 默认值 `0.30/1.50`，并在字段中保留了“scanner not applied”限定；B 的实际 preliminary target 分类阈值 `0.20–1.00 m`写在 `b_trigger_fields`。
- `selected_range_m_median` 只是既有 target audit 保留的一个 HR candidate distance；`selected_range_m_iqr` 不可从现有 summary 计算，不能假装有 session 内 range 分布。
- `range_bin_jump_rate` 明确为 `NA_not_calculated_in_current_QC`。
- `selected_channel_mode` 只报告 target audit 实际保留的 HR/best channel；当前 target summary 没有保存 BR channel，因此不补造 BR channel。

## 8. 分层结论（按风险类别）

### coding/data-interpretation risk

当前 NPZ 被代码按 8-channel complex range-bin cube 读取；当前链没有 raw ADC→Range FFT。若上游文件实际不是该格式，风险发生在 producer 边界之外，必须先做输入 schema/metadata 验证。067 没有可追溯输入，不能进入 formal v1。

### timeline/window risk

正式 batch runner 以 baseline 或单个行为 block 的明确 frame range 调用 producer；segment scanner 也按 segment 计算，但 target audit 是全 session 扫描。现有结果没有能证明 window miscut 的字段；099 另有主队列 timeline/meta linkage 缺失，保留为不可用，不应与 B/C 混写。

### range-gate/human-body localization risk

普通 producer 的工程 gate 是 0.30–1.50 m；当前 signal scanner 未应用该 gate，target-lock preliminary 分类使用 0.20–1.00 m。B 的 36 场由该距离合理性分类触发。距离候选本身不能证明人体胸腔锁定，也没有键盘/桌面/近场目标排除证据。

### motion-artifact risk

B 的 8 场有 `phase_stability_ge_090=False`；这是相位稳定性 proxy，不是已测得的 motion-artifact ratio。C 的 9 场只显示窗口/probe signal-existence coverage 未达门槛，具体局部原因仍未解析。

### harmonic/peak-selection risk

完整 producer 同时使用 peak、periodogram、IBI/time-course 和 VMD/fusion；代码提供基于外部 RSP 的 2×/3×呼吸谐波拒绝，但当前 formal runner 未传 `acq_path`，所以该支路不是当前 formal batch 的 active gate。独立小样本中 HR peak 与 HR course 的指标不同，说明 peak-selection/fusion 需要保留为独立风险；不能将其写成 C=9 的逐场已证实原因。HRV 逐搏证据也不能由当前 QC scanner 推出。

## 9. 最终口径

当前证据支持的表达是：17 场是通过既有窗口/probe/target-lock preliminary gate 的 **QC-eligible candidates**；53 场只能保留微动/体动层（B=44、C=9）；2 场因输入或主队列 linkage 阻断不可用。17 场不是“生命体征已验证可用”，`1297/1400` 不是“毫米波生命体征可用”。

来源文件哈希与逐 session 数值以本目录已有 manifest、`mmwave_session_qc_summary_redacted.csv` 和本次附表为准。


