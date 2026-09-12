# mmWave HR 恢复 P0：历史最佳链与 DLL-time 正式 probe 链逐阶段审计

日期：2026-09-12

任务：`mmwave_hr_recovery_p0`

状态：`PASS / P0_COMPLETE / P1_READY_WITH_SOURCE_PRECONDITION`
研究边界：心率（heart rate [HR]）恢复链审计；不执行 30 s/60 s 最终比较，不设计新算法，不用心电图（electrocardiography [ECG]）调参，不改变 target/gate/window，不训练模型，不改写历史结果。本文的主要工程缩写为质量控制（quality control [QC]）、平均绝对误差（mean absolute error [MAE]）、二阶节（second-order sections [SOS]）、呼吸率（breathing rate [BR]）、呼吸带信号（respiration [RSP]）和搏间期（interbeat interval [IBI]）。

## 1. 结论

历史最佳 `MAE = 3.7772146 bpm` 与当前正式 probe HR 不是同窗、同 target、同时间语义的两次运行，不能直接解释为动态链接库接收时间（DLL-time）使误差从 `3.777` 增至约 `10.46 bpm`。历史结果来自 5 个校准场次、99 个有效 60 s trailing windows、全记录固定 target；当前 B2 来自同一 5 个场次的 100 个 `[probe_end-30 s, probe_end)` DLL-time 窗、逐 probe 动态 target。因此 `3.777` 只能作为历史完整链 comparator，不能作为当前正式 30 s 基线。

当前 `16729b2ef245f9304dae8674f3bac433bc02e98c` probe adapter 已接入历史链的大部分估计核心：Range-FFT 后复数 DataCube、相位展开、0.8–2.0 Hz 心搏带通、低阈值峰检测、时域 HR、频域候选、半/倍频折叠、probe 内 previous-BPM 锚定、时频融合、平滑、confidence（置信度）与 usable ratio（可用比例）。它遗漏的是 v3.1.1 producer 中已经存在、且位于 target 之后的兼容模块束：`_heart_segment_reference_correction()`、`_heart_window_consensus_bpm()`、将共识 HR 作为 `estimate_hr_time_course(..., reference_bpm=...)` 的初始参考，以及 producer 的全局 signal-quality hard gate（信号质量硬门）。2026-08-30 固定合同阶段重放已直接支持 previous-anchor selector 与时频融合，但对上述遗漏模块只能给出 bundled evidence（整束证据），没有同一合同的独立消融，因此 P1 是受控恢复 A/B，不是已证明会恢复到 `3.777 bpm`。

P0 的 Reuse Gate（既有资产复用门）为 `PASS`。P1 可开始，但存在一个必须先锁定的源码前提：B1 的实际执行提交 `16729b2` 本机可解析且测试可复现，但截至本审计开始时不在 `origin/main=b33e277620d43ca0e0a9960b5702dea7cf2dac87` 的祖先链，也不在远端分支上。P1 必须从 exact `16729b2` 建立隔离工作树，或先用独立代码集成任务把同一补丁无语义漂移地接回 canonical main；不得从当前 main 猜测重建。

## 2. 权威源与可复现入口

### 2.1 治理与方法源

- `greenboo26/ai-governance@main`，读取提交 `996930a86dad54a12d23587ae2bce59b2cdc4998` 的 `adapters/RUNTIME_BOOTSTRAP.md`、`rules/durable-project-record.yaml`、`rules/execution.yaml`。
- 本仓库 `AI_PROJECT.md`、本文件、`docs/canonical/2026-09-12_MMWAVE_HR_RECOVERY_AND_BASELINE_INTEGRATION_DECISION.md`、`docs/decisions/2026-09-12_MMWAVE_ECG_HRV_MASTER_ANALYSIS_PLAN.md`、`PROJECT_STATUS.md`、`ANALYSIS_HISTORY_LEDGER.md`。
- GitHub Issue #34 提供时间语义与切换验收；Issue #35 冻结 P0→P1→P2→P3→P4→P5 的执行顺序。

### 2.2 两条待比较 producer lineage

历史链：

`scripts/maintenance/run_hr_course_99_corrected.py`

`→ scripts/process_vital_signs_v3_1_1.py`

`→ producer commit 64634159d226ee1ed892d53e56fcf3697fbff9b8`

当前正式链：

`scripts/maintenance/run_mmwave_probe_merge_ready_20260831.py`

`→ scripts/process_vital_signs_v3_1_1.py` 内复用函数

`→ DLL cutover commit 16729b2ef245f9304dae8674f3bac433bc02e98c`

`64634159..16729b2` 间 producer 的实质差异仅为 VMD（variational mode decomposition，变分模态分解）backend 收口至 `sktime==1.1.0`；历史 runner 明确使用 `method='bp_heart'`，故历史 `3.777` 并未使用 VMD。VMD 不是从历史最佳链遗漏到当前链的模块。

### 2.3 运行证据

| 证据 | 分母与用途 | 结果/位置 | 证据等级 |
|---|---|---|---|
| 历史 HR-course gate | 5 sessions；100 rows，99 valid；60 s trailing windows | `docs/results/mmwave_formal_vital_qc_v1/HR_COURSE_CORRECTED_REPORT_SYNC.md`；本地历史包 `D:\Project\厚粲杯\11_数据\output\20_生理金标准验证\07_HR_COURSE_99_CORRECTED_GATE_AUDIT` | 历史完整链 comparator；非正式 probe 结果 |
| 2026-08-30 controlled stage replay | 固定 `COMPLETE ∩ ECG_VALID = 323`、同 target、同窗 | `docs/results/2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION/`；`24.902438 → 13.276285 → 8.319342 bpm` | previous-anchor 与 fusion 的直接 supporting evidence |
| 2026-08-31 pre_30s selector | 初版 3 sessions/60 probes；Python-time | `docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/`；25 s fused `MAE = 9.02 bpm` | supporting；证明当前估计核心已接入 |
| B1 DLL formal replay | J72+E44=116 sessions；2320 rows | `D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_b1_formal_dll_replay_20260912_r2` | engineering replay PASS；未训练模型 |
| B2 DLL ECG/RSP | 5 sessions；100 probes | `D:\Project\厚粲杯\11_数据\derived\mmwave_b2_ecg_rsp_window_dll_20260912_v2\all_subjects_pre30s_selector_hr.csv` | HR/BR supporting only |
| B3 beat/IBI | 5 sessions；16 complete blocks | `docs/results/2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE/MMWAVE_B3_BEAT_IBI_DLL_TIME_*_20260912.*` 及本地逐 block CSV | beat gate FAIL；HRV BLOCKED |
| B4 simple window comparison | 5 sessions；100 probe denominator | 当前 durable 证据仅见 2026-09-12 canonical decision | method diagnostic；comparator lineage 未闭合 |

## 3. Pipeline 总图

```text
历史 3.777 链
8-channel post-Range-FFT complex DataCube
 → 前 6000 frames 在 0.30–1.50 m bins 9–40 内选择并固定 heart channel/bin
 → unwrap(angle) × wavelength/(4π)
 → Butterworth SOS 4th-order 0.8–2.0 Hz
 → detect_peaks_heart_lo
 → global periodogram/time estimate
 → 20 s/10 s segment reference correction
 → window consensus reference
 → HR course 25 s/5 s：time + spectral candidates + half/double fold
 → previous/reference anchors + time-frequency fusion + smoothing
 → global signal-quality hard gate
 → 60 s probe-course median

当前 16729b2 DLL-time 正式 probe 链
8-channel post-Range-FFT complex DataCube
 → DLL col1 按 [probe_end-30 s, probe_end) 切帧
 → 每 probe 在全 bin/channel 上用 simple separate selector 重新选 heart target
 → unwrap(angle) × wavelength/(4π)
 → Butterworth SOS 4th-order 0.8–2.0 Hz
 → detect_peaks_heart_lo
 → HR course 25 s/5 s：time + top-8 spectral candidates + half/double fold
 → probe 内 previous anchor（初值 None）+ time-frequency fusion + smoothing
 → course confidence/usable ratio
 → 30 s probe 内 course median

P1 唯一允许的恢复束
当前链在 target 之后
 → existing segment reference correction
 → existing window consensus reference
 → 以 consensus 播种同一个 existing HR course
 → existing global signal-quality hard gate
 → 保持 DLL 帧、target、bin、channel、window、band、五键和分母不变
```

## 4. 26 阶段逐项 lineage 审计

机器可读逐行表见 `2026-09-12_MMWAVE_HR_RECOVERY_P0_STAGE_EVIDENCE.csv`。下表的 `有效证据` 指同合同独立效果；`整束证据` 指模块存在于历史完整链，但没有安全 seam（接口切面）可单独归因。

| # | 阶段 | 历史链：输入→实现→输出/参数 | 当前 16729b2：输入→实现→输出/参数 | 同一性、证据与裁决 | P1 最小动作 |
|---:|---|---|---|---|---|
| 1 | raw input | 每帧 8-channel complex range-domain DataCube，形状为 frame×range-bin×channel；runner 读取 raw 后交 producer | NPZ 中相同语义的 complex64 DataCube，tx keys 排序后堆叠 | 数据族相同；均为 post-Range-FFT，不是 ADC。`KEEP` | 无 |
| 2 | DLL timestamp | producer 对整段帧处理；历史 probe 评价由旧事件/记录时轴取 trailing 60 s，非当前正式 DLL probe slicer | CSV 第 2 列（0-based col1）`DLL host receive/enqueue time`；第 3 列 Python worker time 仅 QC；两端 `searchsorted(..., side='left')` | 时间合同不同；Issue #34 已闭合当前语义。`KEEP` 当前 DLL-time | 不回退 Python time |
| 3 | block/probe boundary | 全记录输出后评价 60 s trailing probe windows | `[probe_end-30 s, probe_end)`，block start 只负责前界 clipping；最少 200 frames | 窗口不同且不能混比。`KEEP` 当前冻结 30 s | 不改 window；不做 30/60 比较 |
| 4 | target selection | 前 6000 frames 调 `analyze_long_record`，0.30–1.50 m gate 内 refined heart candidate，随后整记录 forced fixed target | 每个 probe 对本窗 raw mean power 调 `select_separate_channels_bins`，无 refined selector、无跨 probe fixed target | 历史 target 与完整链捆绑；无独立同窗效果，且 P1 禁止改 target。`BUNDLED_ONLY` | P3 才能做 ECG-independent baseline target A/B |
| 5 | range bin | 历史 selection 选定后全记录固定 heart bin | 每 probe 动态重选 bin | 不同；79/99 历史 corrected audit 中 target/channel 相对旧表发生变化，但未分离 bin 因果。`BUNDLED_ONLY` | 不改 |
| 6 | channel | 历史 selection 选定后全记录固定 channel | 每 probe 动态重选 channel | 不同；同上。`BUNDLED_ONLY` | 不改 |
| 7 | bin spacing/距离语义 | `0.037 m/bin` 用于历史 bins 9–40 gate 与 distance label | `0.037 m/bin` 仅生成 selected-distance proxy | 数值相同，物理真值含义未证明；不能由 bin 直接断言胸部距离。`KEEP` spacing | 不改、不升级物理解释 |
| 8 | physical range gate | `0.30–1.50 m`，bins 9–40，影响历史 target 候选 | 当前无 numerical gate | 无 session-level measured distance truth；near-field A/B 不能支持恢复。`REJECT` | 不恢复；保持 `PHYSICAL_GATE_UNRESOLVED` |
| 9 | static/DC/clutter | target 前没有已证实 DC/static/clutter suppression；绘图 mean subtraction 非 producer | 同样对 raw mean power 选 target，无 preselection suppression | 独立 A/B 减少近端选择但破坏稳定性。`REJECT` 新增/恢复均值相减 | 无 |
| 10 | phase unwrap | `unwrap(angle(iq)) × wavelength_mm/(4π)` | 同一 producer helper 与参数 | 相同、已接入。`KEEP` | 无 |
| 11 | cardiac bandpass | `bp_heart`；4th-order Butterworth SOS，0.8–2.0 Hz，`fs=100 Hz` | `_sos_bandpass`；同参数 | 相同、已接入。`KEEP` | 无 |
| 12 | VMD | 历史 runner 强制 `bp_heart`，没有走 VMD | 正式 adapter 也不调用 VMD；producer backend 已收口 `sktime==1.1.0` | 不是遗漏；旧 vmdpy 生理结果曾降级，sktime 仅软件 smoke。`UNPROVEN` | 不恢复 |
| 13 | heartbeat waveform | 带通后的 displacement，写入 full-record NPZ | 同一带通 displacement 在 probe 内存中 | 同一信号定义，当前未导出逐样本 waveform。`KEEP` | 只可在 audit local-only 输出 hash，不扩正式 schema |
| 14 | beat detector | `detect_peaks_heart_lo`：prominence 从 0.10 至 0.01×SD 逐级，最小间距兼容≤120 bpm，至少 10 peaks | 同一函数 | 已接入；B3 的 beat sensitivity/precision `0.2177/.2490` 说明不能晋升 beat/HRV，但不是本轮另造 detector 的授权。`KEEP` | 无；HRV 继续 BLOCKED |
| 15 | time-domain HR | global/segment `_robust_time_bpm`，course 中按有效 IBI 0.5–1.25 s、MAD outlier filter 估计 | course 中同一 `_robust_time_bpm`；输出 `hr_time_bpm` median | 核心相同；历史多 global/segment paths。`KEEP` 当前 core | segment path随 #21 恢复 |
| 16 | spectral HR | global periodogram + segment candidates + course spectral selector | course `_spectral_candidates` 与 `_select_spectral_bpm`；48–120 bpm | course core 相同；历史多 pre-course reference。`KEEP` | 只恢复 reference 生成，不改 band/ranking 参数 |
| 17 | candidate generation | periodogram，Hann，`nfft≥8×window length`，top candidates；global/segment/course 多层 | course top 8 spectral peaks | course 已接入，global/segment 候选未接。`RESTORE_EXISTING` | 调 existing reference functions，不发明候选 |
| 18 | harmonic handling | course half/double fold；segment correction 另含 half/double/triple；外部 RSP 入口存在但历史 runner未传 RSP | course `_fold_harmonic` 已接入；B2 100/100 probes 的 `time_harmonic_folded_30s=False`，旧 60-probe 也为 0 | segment harmonic 只能随历史整束评价；外部 RSP 不属于历史 3.777 实际链。`BUNDLED_ONLY` | 只允许随 existing segment function；禁用外部 RSP 注入 |
| 19 | previous/reference anchor | HR course 接收 window-consensus reference；course 内 previous 递推，confidence≥.12 时 `0.8 previous + 0.2 fused` | `reference_bpm=None`，但同一 probe 的 course points 内 previous 递推仍存在；不跨 probe | 323-window direct replay 支持 previous-anchor selector `24.902438→13.276285`，但当前并非完全缺失；缺的是 consensus seed。`RESTORE_EXISTING` seed | 传入 existing consensus；保持不跨 probe |
| 20 | time-frequency fusion | gap≤10 bpm 加权融合；否则按 anchor/quality 选支路，之后 median/forward-back smoothing，max step 7 bpm | 同一 `estimate_hr_time_course` 内 fusion/smoothing | 直接证据 `13.276285→8.319342 bpm`，且当前已接入。`KEEP` | 无 |
| 21 | segment correction | `_heart_segment_reference_correction`，20 s window/10 s step，以 global spectral 为 base；无外部 RSP 输入 | 未调用 | 历史完整链存在，独立效果未拆。`RESTORE_EXISTING`，证据等级 `BUNDLED_ONLY` | target后调用原函数；参数原样 |
| 22 | consensus/time-course | `_heart_window_consensus_bpm` 先聚类窗口候选（约 6 bpm cluster），再把共识播种 25 s/5 s course | 只调用 25 s/5 s course，初始 reference None；精确 30 s 会产生 7 points/3 unique windows 的 edge duplication | time-course 已接入；pre-course consensus 遗漏。`RESTORE_EXISTING` consensus；edge duplication 留给既定方法任务，不在 P1 改 | 只加 consensus→reference；不改 center generation |
| 23 | confidence/usable/QC | candidate quality、course confidence/usable ratio，并有全局 signal-quality hard gate（10 s，SD≥0.0005 mm，usable ratio≥.5） | course confidence/usable ratio 与弱窗 gate 已接入；adapter 未复刻 producer 末端全局 blanking/state 语义 | 部分同；全局 gate 仅整束证据。`RESTORE_EXISTING`，但必须单独记录 gate hit | 在不改变五键/行保留的前提下用 existing gate；不得删行 |
| 24 | persistence/reset | selected heart target 在全记录固定；course previous 在整段连续 | 每 probe 重新选 target；previous 仅 probe 内；`previous_by_block` 参数未被 HR 调用链使用 | 不同；跨 probe target/HR persistence 未被独立证明，且会改变 P1 target 合同。`UNPROVEN` | 不启用；P3 独立比较 |
| 25 | 180 s baseline | 历史前 6000 frames 是 selection prefix，不能自动等同正式 `baseline_start–baseline_stop` 的 180 s 设计段 | `run_c2c_personalized_mmwave_calibration.py` 已用于 feature median/MAD 与 robust within-person z；正式 HR adapter 不读取 baseline | feature normalization 已实现且应保留；对 HR target calibration 的状态为 `UNPROVEN` | P1 不接；P3 才做 target calibration |
| 26 | final aggregation | 每个历史 60 s evaluation window 汇总 full-record course median；99 valid/100 | 每 probe 汇总本窗 course 的 time/freq/fused median、mean confidence、usable ratio；2320 行全部保留 | 算法聚合族近似，但窗口/target/时间语义不同。`KEEP` 当前正式聚合 | 保持字段、五键、2320 denominator；新增审计字段只能兼容扩展 |

## 5. 已接入、应恢复、不恢复与未决清单

### 5.1 当前已经接入并保持

- DLL host receive/enqueue time 切窗与 `[start,end)` 边界；
- 8-channel post-Range-FFT complex DataCube 输入；
- `0.037 m/bin` 工程 spacing，但只作 proxy；
- 当前逐 probe bin/channel selector；
- phase unwrap、位移换算、4th-order 0.8–2.0 Hz SOS 心搏带通；
- `detect_peaks_heart_lo`、`_robust_time_bpm`、top-8 spectral candidates、`_fold_harmonic`；
- probe 内 previous anchor、time-frequency fusion、smoothing、course confidence/usable ratio；
- 116 sessions/2320 rows、五键、缺失行保留、`models_trained=false`。

### 5.2 P1 恢复清单

只恢复一个 existing compatible downstream bundle：

1. `_heart_segment_reference_correction(heartbeat, peaks, base_freq_bpm, ...)`；
2. `_heart_window_consensus_bpm(...)`；
3. `estimate_hr_time_course(..., reference_bpm=consensus_bpm)` 的现有 reference seed；
4. producer 现有全局 signal-quality hard gate，并显式输出 gate-hit 审计，不删 probe 行。

这些函数已存在于 `scripts/process_vital_signs_v3_1_1.py`，P1 不复制实现、不改参数、不引入 ECG。它们只在当前 target 和当前 DLL frame slice 之后工作，因此可以保持 target/bin/channel/window 不变。

### 5.3 不恢复清单

- 历史 `0.30–1.50 m` physical gate；
- slow-time complex-mean subtraction 或其他未证明的 preselection static/DC/clutter 处理；
- VMD；
- 外部 RSP-guided harmonic correction；
- 新 beat detector、ECG-informed candidate ranking 或阈值；
- 历史 first-6000 fixed target、跨 probe previous-BPM 延续、跨 probe target persistence；
- 180 s baseline target calibration（属于 P3）；
- 将 60 s aggregation 或历史 trailing window搬入当前 30 s producer；
- 任何 30 s/60 s 最终选择（属于 P5）。

### 5.4 未决

1. `16729b2` 不在远端 main 祖先链：P1 execution source 可锁定，但 canonical reachability 尚未闭合。
2. segment correction、window consensus、reference seed、global gate 没有同合同独立消融；其收益是 `BUNDLED_ONLY`，P1 必须 A/B 验证。
3. B2 adapter 与测试在 `16729b2` 工作树上为未提交修改；本审计记录其 SHA-256，但该 B2 运行不能冒充由 `16729b2` 原样产生。
4. B3 的 durable 本地产物记录 `canonical_repo_head=9cbaca0`，相关 adapter/result 仍在脏工作树；它足以维持 HRV block，不是 P1 HR 恢复证据。
5. B4 的 A–D 数字当前只在 canonical decision 中找到；未找到独立 runner/manifest/row-level artifact。`3.777 vs 5.184` 不是已闭合的同窗比较。
6. 180 s baseline 的 HR target/bin/channel calibration 无 current formal candidate；只确认 feature-level normalization 已存在。
7. 当前 formal output 将可读窗记为 `OBSERVED`，即使 HR course 可能全缺；P1 需预先冻结 gate hit 与 state/missing-reason 的兼容写法。

## 6. B1–B4 对本审计的约束

### B1：正式重放

- code SHA：`16729b2ef245f9304dae8674f3bac433bc02e98c`；parent：`b2fddca2542859f62d5f4b57f1b4fdecd54a5b4c`。
- J72+E44=116 sessions，2320 rows；新表状态为 `OBSERVED=2180`、`STRUCTURAL_MISSING=120`、`QC_FAIL=20`。
- 2180 个可比较 probe 中 1847 个 frame membership 变化，333 个不变；不变 membership 的 deterministic feature change=`0`，regression gate=`PASS`。
- `models_trained=false`；因此下游正式包含 mmWave 的模型仍不能从 B1 自动晋升。
- 7 个 timestamp-invalid sessions 按冻结分母保留，不用 raw 目录数量扩分母。

### B2：DLL-time 5-session ECG/RSP supporting result

- 100/100 probes；HR spectral `MAE=15.11 bpm`、time `8.97 bpm`、fused `10.46 bpm`，fused median absolute error=`7.86 bpm`、bias=`−9.02 bpm`。
- 历史 last-25 fused comparator `10.72 bpm`、coverage 98/100；BR `MAE=3.11 breaths/min`、median absolute error=`1.12`、bias=`−2.26`。
- old Python-time fused `10.83→10.46 bpm`：46 improve、41 worsen、13 unchanged。时间切换没有解释完主要 HR 误差。
- 角色：supporting-only；不授权正式 HR 路径晋升。

### B3：beat/IBI gate

- 5 sessions、16 blocks；ECG beats=1364，radar peaks=1193，±75 ms matched=297。
- sensitivity=`.2177`，precision=`.2490`；paired IBI n=281，median IBI MAE=`48.65 ms`，RMSE=`57.63 ms`。
- 结论：beat-level evidence FAIL，HRV（heart rate variability，心率变异性）继续 `BLOCKED`；P1 不修改 peak detector，也不计算 RMSSD/SDNN。

### B4：simple window candidates

- A `[0,30)`：100/100，MAE `5.184 bpm`；B last-25：99/100，`5.966`；C two-25 median：99/100，`5.138`；D three-20 median：99/100，`5.576`。
- A 只是在 A–D 内部候选中较稳；`FORMAL_PRODUCER_CHANGE_RECOMMENDED=NO`。
- 由于 runner/manifest 与 legacy comparator 同窗性未闭合，B4 不进入 P1，也不覆盖 B2/历史 `3.777`。

## 7. P1 精确实现与 A/B 合同

### 7.1 源码与唯一允许修改点

1. 从 exact `16729b2` 建立新隔离工作树；先验证 parent、五个 cutover 文件签名与既有 10 个 timestamp/Issue #33 tests。
2. 生产逻辑只改 `scripts/maintenance/run_mmwave_probe_merge_ready_20260831.py` 的 target 后 HR estimation 段；复用 `scripts/process_vital_signs_v3_1_1.py` 的既有 functions，不改 producer functions。
3. 增加窄回归测试，证明 control 与 restoration arm 的五键、frame indices/hash、frame count、selected heart bin/channel、phase/motion/BR feature、window bounds 完全一致。
4. 写入全新 exclusive output directory；保留 control 与 restoration 两臂逐 probe paired table、manifest、source hashes、运行环境、failure rows、`models_trained=false`。禁止覆盖 B1/B2/历史包。

### 7.2 冻结执行顺序

```text
existing target + existing DLL frame slice
 → existing phase/bandpass/peaks
 → estimate_freq_periodogram 生成 base reference
 → existing _heart_segment_reference_correction（RSP=None）
 → existing _heart_window_consensus_bpm
 → existing estimate_hr_time_course(reference_bpm=consensus)
 → existing global signal-quality hard gate
 → same current probe aggregation/schema
```

### 7.3 评估分母与 ECG 边界

- 首先用 B2 同一 5-session/100-probe DLL-time denominator 做 paired A/B；ECG 只在输出完成后计算 MAE、median absolute error、bias、coverage 与 per-session dispersion。
- 不以 ECG 选择 target/bin/channel、candidate、阈值、gate 或参数；不查看 Q1/Q2 注意结果。
- 随后若且仅若代码合同 gate 通过，可在冻结 116/2320 表上做 engineering replay；这仍不是正式下游模型授权。

### 7.4 P1 acceptance gate

P1 只有同时满足下列条件才可标记 `PASS / RESTORATION_CANDIDATE_ACCEPTED`：

1. source identity：exact `16729b2` 或经单独验证的语义等价 canonical integration commit；
2. control reproduction：100-probe control 与已记录 B2 在 key、window、target 与 HR 输出上完全复现；若不能复现则停止，不比较算法；
3. invariant gate：两臂 100/100 keys 一对一，frame membership、selected bin/channel、window bounds 与非 HR deterministic fields 完全一致；
4. implementation gate：只调用上述 existing bundle；无新参数、ECG input、VMD、distance gate、baseline、cross-probe state；
5. output gate：不删 missing/QC rows；manifest、per-probe paired diff、error log、source hashes、`models_trained=false` 完整；
6. measurement gate：预先报告 fused HR MAE、median absolute error、bias、coverage 和五场次分散；不得只挑改善指标。若 fused MAE 或 coverage 明显劣化，恢复束不进入 formal producer；若改善，也只升级为 P1 supporting candidate，等待 P2/P3/P5。
7. regression gate：Issue #33、DLL timestamp、probe contract tests 与 `py_compile`、`git diff --check` 全部通过。

### 7.5 Stop conditions

出现任一项立即停止 P1 并报告 `BLOCKED` 或 `FAIL`：

- 无法解析 exact source 或 control 不能复现；
- target/bin/channel、frame membership、30 s window、五键或 denominator 发生变化；
- 需要 ECG 才能决定任何上游选择/参数；
- existing function 参数/逻辑不足而需要发明新算法；
- 需要 VMD、physical gate、baseline target calibration 或跨 probe persistence 才能继续；
- 输出会覆盖历史目录或丢弃 missing/QC rows；
- 在 P1 同时启动 30/60 最终比较、HRV 或下游模型。

## 8. P1 影响范围

P1 若被接受，将使当前 30 s DLL-time HR 字段、HR confidence/usable ratio、HR missing/QC reason 以及依赖这些字段的未来 session/block summaries 发生变化。因 116/2320 正式表的 HR 列可能变化，任何尚未授权的 mmWave HR 描述、Q1/Q2 mmWave model、Behavior+mmWave、多模态组合及报告 HR 图表必须继续等待新的 producer replay 与 integrity gate。

P1 不应改变 BR、motion、phase stability、selected distance proxy、selected bin/channel、frame/QC timestamp audit、Behavior/NIR/RGB 单模态结果、B3 beat-level结论、HRV block 或 180 s feature normalization。若这些字段变化，说明补丁越界。

## 9. 数值有效性表

| 数值 | 当前角色 | 是否可直接作为正式 HR 结论 |
|---|---|---|
| `3.7772146 bpm`，99 valid/100，5 sessions，60 s fixed-target full chain | 历史完整链 comparator | 否 |
| `24.902438→13.276285→8.319342 bpm`，n=323 | 同合同 controlled stage supporting evidence | 否；只支持模块路径判断 |
| 2026-08-31 25 s fused `9.02 bpm`，3 sessions/60 probes | Python-time pre30 supporting | 否 |
| B1 116/2320、2180 computable、333 identical membership/0 feature changes | 当前 engineering replay/integrity evidence | 是，限数据工程事实；不是 HR 准确度 |
| B2 DLL 30 s fused `10.46 bpm`，100/100 | 当前同窗 supporting HR comparator | 否；P1 control 基线 |
| B3 sensitivity `.2177`、precision `.2490` | 当前 beat gate failure | 是，限“HRV 继续 BLOCKED” |
| B4 A/C `5.184/5.138 bpm` | method diagnostic，artifact/comparator lineage 待闭合 | 否 |

## 10. P0 verdict

- `REUSE_GATE=PASS`：已定位并逐项比较 existing producer、formal adapter、B1–B4、controlled replay、baseline pipeline；未提出新算法。
- `P0_VERDICT=COMPATIBLE_DOWNSTREAM_BUNDLE_MISSING_FROM_CURRENT_FORMAL_ADAPTER`。
- `RESTORE_LIST=segment_reference_correction; window_consensus_reference; HR-course reference seed; existing global signal-quality hard gate`。
- `DO_NOT_RESTORE_LIST=historical physical gate; preselection mean subtraction/DC/clutter; VMD; external-RSP harmonic path; historical fixed target/cross-probe persistence; 180s baseline target calibration; 60s aggregation`。
- `P1_READY=YES`，但 source precondition 必须首先解决或显式固定 exact `16729b2`；这不等于 P1 结果预判为改善。
- HR/BR 保持 `HOLD / SUPPORTING_ONLY`；HRV 保持 `BLOCKED`；formal downstream 保持未授权。
