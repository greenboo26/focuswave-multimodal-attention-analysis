# FocusWave 程序、分析与结果历史账本

> **任何新算法、新特征、新 producer 改动、新数据重跑或新的“可以试试”建议之前，先读本文件。**
>
> 目的不是替代当前科学结论，而是回答四个问题：**以前做过什么、什么时候做的、结果怎样、为什么采用/放弃。** 只有能够说明“新证据、新输入语义、新参考标准或新研究问题与旧实验有什么实质差别”时，才允许重复已有路线。

更新时间：2026-08-30（Asia/Shanghai）

---

### 2026-08-30：Issue #29 execution-evidence supervisor — REUSE_GATE=PASS / SCIENTIFIC_GATE=PARTIAL

**审查范围**：Supervisor 读取并核验 #24–#28 的实际脚本、aggregate 结果、manifest、复用说明、分母边界和本地提交；不把会话文字当作科学证据。统一确认：#24 仅闭合 ECG reference eligibility；#25 为 283-pair bounded diagnostic；#26 的 distance/error 描述性证据通过但 physical gate unresolved；#27 仅 supporting retrospective truth；#28 为历史 acquisition tail 不可恢复。

**统一门控**：`REUSE_GATE=PASS`、`SCIENTIFIC_GATE=PARTIAL`；HR/BR 继续 `HOLD`，HRV 继续 `BLOCKED`。没有 producer/raw/firmware/portable V2/NIR/RGB 修改、C2B/C2C 重跑、新 HR 算法族或 MAE 调参。证据包为 `docs/results/2026-08-30_MMWAVE_ISSUE29_SUPERVISOR/`，含执行矩阵与 manifest；`7629952520b0f237b67b6db5d54c8d30ced8a6f8` 明确标为 `LOCAL_EXECUTION`，集成后的 canonical commit 为 `c2150c9bb5bb4509b09b9b7be0ada956c3e222cc`。

### 2026-08-30：Issue #28 97795/block4 acquisition tail audit — PARTIAL / HISTORICAL_TAIL_IRRECOVERABLE

**复用与执行**：复用既有 `c0f1717` coverage audit、`426576e` DLL contract、原始 coverage manifest 与 FocusWave `ecg` 生命周期源码；RUN_ID=`issue28-tail-20260830-r1`。11 个 session/block 目录中 6 个可审计、5 个缺少必需日志，未重建缺失记录。

**结果与边界**：`97795/block4` marker→last DLL frame gap=`24,809 ms`；w027/w028 end gap=`9,536/19,536 ms`。长尾候选为 `97795/97796/97994`，frame continuity=`true/false/false`，后两者分别含 `82/314` 个 gap，原因不能泛化。历史尾部不可恢复；不做 padding、backfill、synthetic frame，不改变 #24–#27 的 335-window primary 分母。未来修复位置仅为 producer stop/drain/order 与 queue/drop/timeout instrumentation，本轮不改 producer/raw/firmware/portable V2，且不阻塞 #24–#27。

**证据与决策**：证据包为 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_ACQUISITION_TAIL_AUDIT_*`，入口为 `scripts/maintenance/run_mmwave_acquisition_tail_audit_20260830.py`。HR/BR 继续 `HOLD`，HRV `BLOCKED`；本条为 acquisition coverage 层的 `PARTIAL`，不是生理有效性结论。

### 2026-08-30：Issue #24 ECG reference eligibility on 335 DLL-time windows — PARTIAL / ECG_REFERENCE_ELIGIBILITY_COMPLETE

**Reuse Gate 与适配原因**：已有 `scripts/gold_standard_qa.py` 已包含历史 gold-standard ECG 的滤波、R-peak、IBI plausibility、相邻 IBI artifact rejection 和 ≥80% 有效 beat coverage；已有 `scripts/maintenance/run_mmwave_targeted_validation_20260830.py` 已包含 block start/end marker 与 Biopac digital marker 的 block-local affine mapping；已有 `MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv` 已固定 ARM0/ARM1/ARM2 estimator rows。旧入口不能直接输出当前 DLL-time window 的 `ECG_VALID/ECG_INVALID/UNRESOLVED`、逐窗 reject reason 并按新分母重算，因此只新增窄 adapter `scripts/maintenance/run_ecg_eligibility_dll_windows_20260830.py`；没有否决已有算法。`REUSE_REJECTION_REASON=existing scripts expose cleaning/mapping components but no combined 335-window eligibility output or valid-denominator ARM metrics`。

**运行与输入**：RUN_ID=`ecg_eligibility_dll_20260829T220533Z`；执行时使用 `PRE_INTEGRATION_BASELINE` `805db1d3f2d701d46f678b7cd911990f779a4966`，证据随后集成到 canonical `main` `c2150c9bb5bb4509b09b9b7be0ada956c3e222cc`；输入为 `MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv`（335 rows）和既有 `MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv`（335 rows），读取三场 `.acq`/`events.csv` 及 block marker 证据。ECG 参数沿用 gold-standard 入口：0.5–40 Hz、prominence 0.25、最小峰距 0.30 s、IBI 300–2000 ms、相邻 IBI 变化 >20% 记 artifact、coverage ≥80%。Rest、坐姿调整、block 边界和非 complete block 由冻结 DLL-time block window contract 结构性排除。

**结果与 reason 边界**：335 个窗口为 `ECG_VALID=325`、`ECG_INVALID=10`、`UNRESOLVED=0`。10 个 invalid 的 primary reason 全部是 `abnormal_adjacent_ibi_fluctuation_gt20pct`；`marker_sequence_not_exact_but_block_affine_fit_available` 只写入 `ecg_qc_warning`，不混入 primary invalid reason。`97793/block1` 的 57 个窗口均有该 warning，但 marker affine mapping 可用，不能把 marker mismatch 误读成 57 个 invalid。

**ARM 重算与决策**：固定既有毫米波 ARM rows，只在 ECG_VALID 分母得到 ARM0/ARM1/ARM2 MAE=`25.005/21.906332/18.904008 bpm`，valid n=`325/304/325`；all-window `24.847938/21.774620/19.040268 bpm` 仅作 diagnostic。该结果闭合 ECG reference eligibility 层，但不闭合 20 s window justification、distance gate、spectral truth 或 formal HR validity；HR 继续 `HOLD`，HRV 继续 `BLOCKED`，#16 继续 `PAUSED`。

**证据**：`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_REFERENCE_ELIGIBILITY_REPORT_2026-08-30.md`、`ECG_ELIGIBILITY_REASON_DISTRIBUTION.csv`、`ECG_ELIGIBILITY_BLOCK_SUMMARY.csv`、`ECG_ARM_METRICS_VALID_DENOMINATOR.csv`、`ECG_ELIGIBILITY_MANIFEST.json`；逐窗含 reject reason 的 CSV 仅在 `work/ecg_eligibility_dll_windows_20260830/` local-only，不入 Git。全套 pytest 在仓库根目录收集到既有 legacy `_cal_segment_test.py` 的模块路径错误；相关 ECG 测试文件在当前 HEAD 不存在，已改以 Python compile、脚本实际运行、CSV/JSON/hash/diff 校验完成验证。

### 2026-08-30：Issue #26 distance-error 与 physical gate audit — PASS / PHYSICAL_GATE_UNRESOLVED

**复用与执行**：复用 `selected_bin × 0.037 m`、B2 极端距离前端审计、早期 5 participant/99-window ECG-valid HR 与 99-row RSP-valid BR paired evidence；RUN_ID=`MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_20260829T220501Z`。只新增下游聚合入口 `scripts/maintenance/run_mmwave_distance_error_physical_gate_audit_20260830.py`，未重选 target、重跑 estimator、修改 QC 或运行 C2B/C2C；`REUSE_REJECTION_REASON` 为既有结构审计与 paired 表没有同时覆盖连续 distance-error、预定义分层、coverage 和 target-stability 的聚合入口。

**结果与边界**：formal 71-session distance 分布为 `4/12/32/5/18`；早期 HR N=99、MAE=`3.777215` bpm，BR N=99、MAE=`3.327631` breaths/min，仅作参考描述。B2 near-side bright structure=`OBSERVED`，labels=`LIKELY_HUMAN=4`、`AMBIGUOUS=82`、direct leakage=`0`、fixed reflection=`0`；0 不是机制不存在证明。历史 `0.30–1.50 m` 仅 `HISTORICAL_GATE_SENSITIVITY`，near-field cause/current physical gate 保持 `UNRESOLVED`，未授权 exclusion gate；结果包为 `docs/results/2026-08-30_MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE/`。

### 2026-08-30：Issue #27 ECG_VALID retrospective spectral truth audit — PARTIAL / SUPPORTING_ONLY

**复用与结果**：复用既有 335-window fixed target/peak/ARM0/1/2 输出、targeted validation window contract、producer bandpass/periodogram/peak/harmonic 实现及 #24 ECG eligibility；ECG/RSP 仅作 oracle。新增下游 audit 的原因是既有表没有统一记录 top candidates、prominence、ECG-nearest rank 与 selection classification，`REUSE_REJECTION_REASON` 写入 manifest/report。

**分母与决策**：全窗口 diagnostic/supporting=`335`；#24 ECG_VALID primary=`325`、ECG_INVALID=`10`、UNRESOLVED=`0`；truth class 为 nearby=`182`、wrong-selection=`102`、selected-ECG-bin=`22`、absent/weak=`17`、coverage/reference=`2`。ARM0/1/2 primary MAE=`25.005/21.906332/18.904008` bpm；internal harmonic guard 未在 fixed targeted path 调用，external RSP guard 仅 diagnostic。结果为 `SUPPORTING_ONLY`，HR=`HOLD`、HRV=`BLOCKED`，逐窗 truth table local-only。

---

### 2026-08-30：mmWave timestamp semantics repair、DLL-time window reconstruction 与 unchanged HR sensitivity — PARTIAL

**为什么需要 repair**：此前 335 个窗口按同一 CSV 的 Python `time.time()` 列定义，旧结果无法证明它们对应 acquisition frame 的真实时间语义。FocusWave source `ecg` `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317` 已确认 DLL `receive_data.timeStamp` 在 consumer 侧写入 timestamps CSV，且与 `frameIndex` 同行；本轮只修复 frame-time/window membership 口径，不重写 producer。

**输入与合同**：canonical `main` baseline `ab39ad272462c54208b56e0b302b5d9ff1e95b4c`；subjects `97793/9779/97795`；既有 `ecg_alignment_audit.csv`、`beh/events.csv` block markers（12/22、13/23、14/24、16/26）和 101–110 tick；20 s window、10 s step、5 s guard、complete-block-only。每个 block 独立 reset target/bin/channel tracking，跨 rest、姿势调整和 block boundary transition 排除。新 contract 以 DLL DateTime 转换出的绝对 Unix ms 为 authoritative clock，Python 列只作 provenance；DateTime 的 device/firmware/SDK/host origin 未被源代码独立说明。

**Mapping 与窗口结果**：三场 timestamp rows 与 NPZ frames 均为 `162924/155557/140648`，frame index 均连续、通道长度一致、DLL timestamp 单调，mapping=`OK`。335 个窗口的 exact/partial/obvious=`25/156/154`，changed=`310`，mean/median/min Jaccard=`0.736410/0.923114/0.000000`。旧 Python-time 窗口与新 DLL-time 窗口因此不可互换。

**HR sensitivity 与决策**：只重放既有 ARM0 current block-local、ARM1 historical gate + current block-local、ARM2 historical fixed target + current 20 s estimator，未改变 target/gate/filter/ECG/FS。new DLL-time MAE=`25.791632/22.189492/19.189060` bpm，old Python-time historical provenance=`24.884913/21.804185/19.068931` bpm；mean absolute HR value delta=`6.126641/6.845548/6.444105` bpm。`97795/block4` 的程序 end marker 比最后 DLL frame 晚 `24,809 ms`，最终 guarded window 仅 46 帧，未填补。分类 A cosmetic=`不支持`，B material window change=`支持`，C unresolved=`DLL timestamp generator origin + acquisition tail coverage`；旧 20 s 结果 retain as historical provenance、supersede for current DLL contract。HR/BR=`HOLD`，HRV=`BLOCKED`，Issue #16=`PAUSED`。允许以后重复的唯一入口是两个 maintenance scripts 与本次冻结 contract；不修改 portable V2、producer、raw、firmware，不运行 C2B/C2C、HRV 新算法或全量 batch。

**证据路径**：`docs/research/MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md`；`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv`、`MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_REPORT_2026-08-30.md`、`MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_MANIFEST.json`、`MMWAVE_TIME_SEMANTICS_HR_COMPARISON.csv`、`MMWAVE_TIME_SEMANTICS_HR_METRICS.csv`、`MMWAVE_TIME_SEMANTICS_HR_COMPARISON_REPORT_2026-08-30.md`、对应 manifest；row-level mapping 保留在本地 derived 目录，不上传 Git。

### 2026-08-30：mmWave DLL-time coverage contract 与 fixed-denominator sensitivity — PARTIAL

**为什么需要这次审计**：DLL-time 修复已确认 335 个窗口的 frame membership 发生实质变化，但 `97795/block4` 末尾仍有 24,809 ms program-end-to-last-DLL tail。需要先用 acquisition completeness 定义窗口是否完整，再判断少数缺尾窗是否解释 HR 高误差；coverage threshold 不得由 HR 结果反推。

**冻结输入与阈值**：canonical `main` `426576e0809252656b79729ac077e91a6bfca80d`；输入为 `MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv` 与已完成的 DLL-time HR comparison；窗口仍为 20 s/10 s step/5 s guard/block-local。每个 subject/block 从 DLL timestamp 估计 median/p5/p95 interval 和 effective Hz；expected count=`20,000/median_interval+1`。`COMPLETE`：coverage≥0.95、边界 gap≤max(3×median,50 ms)、internal gap≤1,000 ms；`SEVERELY_INCOMPLETE`：coverage<0.50 或 boundary gap>max(1,000,5×median) 或 internal gap>1,000 ms；否则 `PARTIAL`。这些规则只使用 DLL timestamps 和窗口边界。

**Coverage 结果**：335 窗中 `COMPLETE=333`、`PARTIAL=0`、`SEVERELY_INCOMPLETE=2`。严重窗均在 `97795/block4`：`w027` 为 1,035 frames、coverage `0.517241`、end gap `9,536 ms`；`w028` 为 46 frames、coverage `0.022989`、end gap `19,536 ms`。primary 335-window outputs 不删除、不覆盖。

**预注册 sensitivity**：S0 all=`335`、S1 exclude severe=`333`、S2 complete-only=`333`。S0/S1/S2 的 ARM0 MAE=`25.791632/25.812760/25.812760`，ARM1=`22.189492/22.128143/22.128143`，ARM2=`19.189060/19.225180/19.225180` bpm；S0→S2 ΔMAE=`+0.021128/-0.061349/+0.036120` bpm。完整窗口中的 HR 仍明显偏高误差，因此 coverage 结论为 `SEVERE_COVERAGE_FAILURE_LOCALIZED_ONLY` 与 `COVERAGE_NOT_PRIMARY_HR_EXPLANATION`，不是算法提升、不是删除依据。

**决策与可重复性**：HR/BR=`HOLD`，HRV=`BLOCKED`，Issue #16=`PAUSED`。允许以后重复的入口为 `scripts/maintenance/run_mmwave_dll_window_coverage_audit_20260830.py` 与 `run_mmwave_dll_window_coverage_sensitivity_20260830.py`；未修改 estimator/target/gate/filter/ECG/producer/raw/firmware/portable V2，未运行 C2B/C2C 或 full batch。证据包位于 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`，包含 coverage table、by-block n、reports 和 manifests。

## 1. 本账本的证据规则

### 2026-08-30：正式多模态母表 attach 与 V2 merge-ready 结构审计

**来源**：`docs/results/2026-08-30_FORMAL_MULTIMODAL_ATTACH/`

- 复用当前身份母表，不重跑 NIR/RGB producer，不建模；以显式 `j_source_folder` 证据将 72 个当前 J 会话映射到母表，保留 `single_experiment_id` 与 `session_id` 两个字段。
- 从当前正式行为事件恢复 1,440 个 probe，冻结 `pre_30s` 真实 `unix_ms` 窗口和五列 probe key；行为/NIR/RGB 三表均通过 portable V2 非空/唯一键审计，结构性 outer/inner merge 均为 1,440 行。
- 这不是科学特征完整性或模型就绪 PASS：NIR 有 145 行缺失窗口观测，RGB 有 20 行缺失 raw 观测；RGB PERCLOS 未生成，mmWave 仍为 reserve interface。

本文件重建自 GitHub 上四个与采集、producer、行为/生理分析、正式结果直接相关的仓库：

1. **中央科学与最终解释**：`greenboo26/focuswave-multimodal-attention-analysis@main`
2. **实验/采集程序**：`kyandi233-dev/FocusWave@stable-msmf`；ECG/RSP 校准和 marker 历史同时读取 `@ecg`
3. **NIR/RGB/Behavior producer**：`kyandi233-dev/Attention-Analysis@nvidia-cuda`，并读取其历史说明、结果目录和提交演变
4. **workspace / 历史过程日志**：`greenboo26/project@august`

`greenboo26/project@august/PROJECT_INDEX.md` 只负责 workspace 注册和历史佐证，不覆盖中央科学仓的当前结论。`mmwave-hrv-analysis` 是中央仓旧身份/旧名，不作为第五个独立科学仓处理。

### 证据优先级

同一结论冲突时，按下面顺序处理：

1. 当前中央 canonical contract / result / issue execution evidence
2. 当前 producer/acquisition 的固定 ref、正式 runtime、manifest、测试
3. 带 commit、脚本、结果路径的历史报告/决策记录
4. `project@august` 的日期型 work-log，用于恢复过程、日期和当时判断
5. 只有聊天转述、但找不到原始 GitHub 产物的数字：标记 `MISSING_EVIDENCE`，不得当作事实继续传播

### 状态词

- `ADOPTED`：当时采用，且没有被后续证据推翻
- `SUPPORTING`：可用于工程、机制、敏感性或历史解释，不能自动升级成主结论
- `REVERTED / NOT ADOPTED`：已经试过并放弃；没有新证据不得重复
- `SUPERSEDED`：历史结果真实存在，但参考、方法或数据口径已被后续结果替代
- `BLOCKED`：缺关键证据/输入，不应强行补数
- `MISSING_EVIDENCE`：能找到转述但不能绑定原始脚本、日期、commit 或结果表

---

## 2. 四个仓库分别负责什么

| 仓库 | 角色 | 本次重点读取的历史入口 |
|---|---|---|
| `focuswave-multimodal-attention-analysis` | 当前科学真相、跨模态模型、正式解释、mmWave reanalysis | 根 `CHANGELOG.md`、`PROJECT_STATUS.md`、`docs/canonical/*`、`docs/mmwave_reanalysis_v2/*`、Issues #9/#12/#15/#16/#17/#18 |
| `FocusWave` | SART/实验程序、mmWave/NIR/RGB采集、时间戳、marker、硬件语义 | `01-MainProgram/core/mmwave_capture.py`、`04-docs/CHANGELOG.md`、`02-tools/11-calibrate-mmwave-ecg.py`、`ecg` branch commits |
| `Attention-Analysis` | NIR/RGB producer、Behavior 历史分析、QC、模型运行和输出 schema | `docs/010-overview/*`、`020-nir/*`、`030-behavior/*`、`040-rgb/*`、结果目录、`nvidia-cuda` commits |
| `project@august` | 2026-07 起的工作日志、旧算法库过程、J_Data 脚本/结果索引、迁移前历史 | `.claude/work-logs/*`、`01_管理/01_项目管理/分析记录.md`、`PROJECT_INDEX.md` |

设计系统、AI 配置、UI-only 版本不进入本科学历史账本，除非它们改变实验输入、标签、时间轴或正式数据语义。

---

## 3. 跨仓库主时间线

### 2026-07-20：mmWave 采集链建立

**来源**：`project@august/.claude/work-logs/2026-07-20_mmWave采集脚本.md`

- 从 RS6240 官方 HIF/DLL 示例建立 Python 采集，不再使用手写 HIF 解析。
- 输出逐步确定为 `.npz + .datacube.bin + timestamps + meta`。
- 实测约 99 fps、8 通道（2T4R）、256 range bins、帧号连续、无明显丢帧。
- 这一天确定了“保留 raw + timestamp，生理指标离线反复重算”的基本原则。

**当前意义**：`2T4R / raw IQ / 约100 fps` 从项目最早期就存在，不是 8 月末才发现的新资产。

### 2026-07-21：采集参数纠错

**来源**：`2026-07-21_毫米波数据采集与算法基线审查.md`

- 发现旧 v1 文档/代码硬编码 `tx_ant=1, rx_ant=3`，修正为 `2T4R`；默认 UART 修正为实际 SPI。
- 明确只采 raw 与时间戳，实验结束后批处理。

### 2026-07-23：v3 采集修复 + VMD 已经进入历史主线

**来源**：`2026-07-23_v3采集脚本修复_算法VMD集成.md`

- v3 采集：0.5 s flush、1000-frame chunk、stop 顺序修复、双时间戳、DLL 时区修正；30 s 2965 帧、97 fps、无跳帧。
- VMD 已经系统测试 `K=3~6, alpha=1000~5000`，当时选择 `K=4, alpha=1000`。
- 历史 v2 数据上“时域/频域 HR 差距”从约 30 BPM 降到约 5 BPM，但这是**内部自洽性改善，不是 ECG 准确率证明**。

**防重复**：以后不得把“试 VMD / 调 K 和 alpha”描述为新方向。

### 2026-07-24：37 mm 固件 + 50 分钟压力测试

**来源**：`2026-07-24_厚粲杯_固件编译_50分钟测试_数据分析_问卷设计.md`

- 固件 range resolution 从 80 mm 改到 37 mm，对应带宽约 4.05 GHz。
- 50 min：298,472 帧、99.5 fps、3000.27 s、零报错。
- 当时得到 BR 12.9 BPM、频域 HR 66.9 BPM，动作时域 HR 84.2 BPM；**没有 ECG，因此不能作为准确率证据**。
- 当时曾设想“最终产品只用 mmWave、其他模态只训练/验证”，这个产品定位后来已经被当前多模态 FocusWave 方案替代，属于 `SUPERSEDED` 的历史假设。

### 2026-08-07：multi-bin、谐波抑制、时间连续性、测角/Doppler 都已经实际探索

**来源**：`2026-08-07_毫米波算法迭代与四被试分析.md`

当时 v1.3 管线已经包含或测试：

- 窗级自适应选 bin
- `bin 8-45` 距离门，修复曾选到 `bin253 ≈ 9.4m` 的远端杂波
- 呼吸谐波陷波
- **multi-bin 交叉验证**；历史日志记载 007 的倍频伪影曾由此修正
- MIN_PEAKS 随窗长调整
- 段参考/邻窗连续性修正
- 角度 FFT / 官方 A43 复刻 / Doppler 活体特征探索

四被试 158 个 probe 窗最重要的统计教训是：原始跨人合并曾出现 `p=.007`，做被试内标准化后变为 `p=.34`，说明个体基线可以伪装成组效应。

角度/Doppler 当时不能可靠区分人和环境源；1D datacube 不具备完整角度链需要的信息。**因此 generic AoA / beamforming / multi-channel 融合不是“从来没做过”。**

### 2026-08-07 晚：深慢呼吸自对照

**来源**：`2026-08-07_深慢呼吸验证实验.md`

- 511 s、50,487 帧、98.7 fps。
- 深慢呼吸时 HR 下降、SDNN/RMSSD 上升的方向符合 RSA 生理预期。
- 但提示音失败，呼吸节拍和屏息段操作与协议错位；且无 ECG 金标准。

**当前定性**：可作为 `SUPPORTING mechanism/sensitivity`，不能再写成“mmWave HRV 已验证”。后续 ECG/IBI 证据已经把 HRV 正式资格重新设为未闭合。

### 2026-08-09~10：信号质量问题从“摆位”继续追到近场反射、range selection 和调制内容

**来源**：
- `2026-08-09_预实验诊断与人体验证工具.md`
- `2026-08-10_毫米波预实验信号质量排查_0810重测对比.md`

重要演变：

- 8/9 曾初判预实验弱信号来自波束覆盖/摆位。
- 8/10 进一步对照后修正：异常强近场反射可压制人体带；近场峰本身所有数据都有，关键是强度/几何和人体带是否消失。
- 发现“反射幅度强”与“生理调制内容清晰”是两个维度，不能用单个 SNR/幅度给生理有效性盖章。
- 弱信号 60 s 窗可以“算出数字”但 HR 跳变、HRV 异常，因此再次证明“有值 ≠ 有效”。

### 2026-08-11 凌晨：7 类外部方法 A/B 已经集中试过

**中央 commit**：`ac2e512be33b2538f9b50a014f388ff40df8bfec`  
Git 时间：2026-08-10 18:35 UTC = 2026-08-11 02:35 北京时间  
**决策记录**：历史 `docs/优化决策记录.md` / 后来的 `docs/决策/优化决策记录.md`

其中 SPC 实验明确记录 `2026-08-11 00:40`。

| 方法 | 历史结果 | 决策 |
|---|---|---|
| SPC 相邻 bin 相位相干定位 | sub-003 46%→48%，+1.8%；001/002无改善 | 边际；可选，不进主线 |
| Hampel IBI 清洗 | HR几乎不变；后来 SDNN 004 -37%、007 -28% | **回退**；不能用统计离群法压正常 RSA |
| phase difference | 003/006/007无变化 | 不采用 |
| 1D CA-CFAR | 003 46→37%、006 100→91%、007 100→99% | 不采用 |
| SSA | trusted windows 无变化 | 不采用为常规修复 |
| envelope normalization | 无变化，HR差异中位约0.1 bpm | 不采用 |
| CEEMDAN | 判定近似但 SNR 平均低4–5 dB，计算贵 | 不采用 |

**硬规则**：这些方法不允许因为新智能体“想到”就再跑一轮。若要重试，必须先写清新的数据语义/失败模式/参考标准与旧 A/B 有何不同。

### 2026-08-12~13：ADC/测角路线实际做过，并且多轮推翻过早判断

**来源**：
- `2026-08-12_ADC固件实测与测角方案排查.md`
- `2026-08-13_测角校准与正式实验设计.md`

- ADC 固件实测底噪比 1D 高约 7–12 倍，整体质量明显更差。
- 官方手册要求速度补偿 + 软件天线校准；项目实际开发过固件传校准数据、PC 端 `analyze_angle.py`。
- 8/13 又推翻“chirp 相位不连续”的过早结论：泄漏 bin 相位稳定，人体 bin 跳变来自微动。
- 校准链最终能取到 `dec_fcw + ant_calib[8]`，但 1D 数据缺完整 Doppler 维度，用户决定回到主线。

**防重复**：不能再用“你们是 2T4R，所以试测角/beamforming”作为无历史依据的新方案。只有输入链、固件或数据维度发生了明确变化，才值得重新讨论。

### 2026-08-14：AgeBalanced 外部 ECG 参考验证 + multi-bin 再次 A/B

**commit**：`f4a8c74d89ec28e005c537cbd5280a15dcb584e1`  
Git 时间：2026-08-13 18:41 UTC = 2026-08-14 02:41 北京时间

历史 220 Rest sessions 口径下：

- project route session-MAE median 约 9.5 BPM
- high / medium / low ≈ 1.6 / 3.4 / 10.1 BPM
- HPS：约 10.6→9.7，2× locks 32→4，保留
- 时间连续性：9.7→9.5，小幅改善，保留
- **固定呼吸谐波陷波：9.5→10.4，净负，回退**
- **top3 multi-bin consensus：9.5→9.3，改善仅约0.2 BPM；high窗口增加，但 2× locks 4→6**
- VMD 自适应网格：固定参数 median 22.5、adaptive 25.4、bandpass 32.1；adaptive 更差，不采用

这一天已经回答了“multi-bin 有没有用”：**有小的质量/覆盖收益，但不是解决 HR 错频的突破，而且会选错共识组。**

### 2026-08-15：ECG 双机校准首次暴露严重错频；当天根因判断后来被修正

**来源**：`2026-08-15_毫米波ECG双机校准.md`

- mmWave 与 Biopac marker 残差约 0.7–1.2 ms，时间同步链良好。
- ECG 数据质量可用，mmWave frame/range signal 也很强。
- 当天看到 mmWave ≈55 BPM、ECG ≈106 BPM，**最初判断成“VMD 丢失心跳基频/半频锁定”**。

这个“VMD 丢基频”解释第二天被推翻，因此只保留为历史诊断过程，不能引用成当前根因。

### 2026-08-16：金标准清洗 + “强而错”呼吸谐波根因形成

**来源**：
- `2026-08-16_毫米波ECG校准诊断与生理多导程序开发.md`
- `2026-08-16_毫米波金标准对称清洗与锁半频根因定位.md`
- `2026-08-16_正式实验第一批数据分析与毫米波方法学重构.md`

关键纠正：

1. D:\acq_mmwave_results 的校准记录是**同一个人多次测量**，不是多个独立被试。
2. 自创 MAD ECG 清洗被废弃，改用文献支持的 IBI/正常 RR 规则；RSP 也按自身生理范围处理。
3. 97795/97796 实证：呼吸 2/3 次谐波可落入 HR band；**SNR 10–11dB、相位稳定、时频一致都能全绿，但 HR 仍然锁错。**
4. 8/15 的“VMD 丢基频”解释被修正为呼吸谐波覆盖/误锁。
5. 扩大固定陷波又会伤到真实低 HR，因此简单“把所有谐波 notch 掉”不能作为通用修复。
6. 心跳选 bin 曾选到远端 `bin 247/252`，加入合理距离门后恢复近距候选，再次说明前处理/target selection 是实际风险。

这一天还发生方法学重构：连续 30 s HRV × probe 的粗暴框架被降级，改为 probe-centered、event-related、block-level 三层；正式批当时生理×行为没有稳定跨人效应。

### 2026-08-23~24：J:\Data 正式 70 场分析进入 report-level 模型

**来源**：`project@august/01_管理/01_项目管理/分析记录.md`

- 行为资产：72 sessions；mmWave 主输出：70 sessions。
- 70/70 最终有 mmWave group output；约 1,297 个可信 probe windows。
- task-dynamics：2,237 个可信窗口；LMM 为主、GEE 为敏感性。
- alertness event：1,400 events，1,056 个 HR 前后均可信。
- adaptive-bin 主分析 HR post effect 后续汇总约 `-0.542 bpm`，FDR 后不显著。
- fixed-bin sensitivity 的 post effect显著，但它改变测量路径并筛掉失败事件，因此只能 sensitivity，不可替代主模型。
- BR 保持次要/探索；SDNN/RMSSD 不作正式生理推断。

### 2026-08-25：J 盘 8 通道空间一致性是 target-lock 证据，不是 HR 正确性证明

**commit**：`98dc319e650cbe0702bb1d1907d3907a50b55a87`  
时间：2026-08-25 07:39 UTC = 15:39 北京时间

- 26 个全场候选 × 首/中/末 = 78 个分片记录。
- sub-078/sub-091 的 8 通道共同近距离功率峰较稳定。
- 与 RGB motion gate 组合后选出 HR/BR 复核候选。

**边界**：只能叫 `human-target-lock candidate / spatial consistency evidence`，不能叫 chest-lock confirmed，更不能据此声称 HR/BR/HRV accurate。

### 2026-08-27：正式 reanalysis 解释 9→27–38 BPM 巨大断层

**中央 branch 历史证据**：`codex/mmwave-formal-reanalysis-v2/docs/mmwave_reanalysis_v2/*`

- Phase 2A 建立 30-development / 80-heldout participant split；80 仍未打开。
- Task2R：adapted SSA+VMD，仅小幅变化，不能代表 Lei 2025 正式方法。
- Task2S：Lei SSA core adapted，没有稳定 rescue。
- Issue #9 后确认：27–38 BPM 的巨大恶化主要来自 AgeBalanced ECG benchmark/reference 定义改变，而不是 project route 突然崩坏。
- 用 AgeBalanced 官方 ECG FFT 参考重算已有路线：30 s project pooled MAE 约 **10.361 BPM**；50 s project 9.292 vs adapted SSA+VMD 9.012，优势很小且不跨指标稳定。

**当前边界**：旧 `ecg_reference_v1` 的 27–38 BPM 不再作为 AgeBalanced HR 性能结论；但这也不等于 HRV 已经获得验证。

---

## 4. mmWave 已经试过、不能无理由重复的路线

| 路线 | 最早/关键日期 | 已知结果 | 以后规则 |
|---|---|---|---|
| VMD / K-alpha 扫描 | 2026-07-23；2026-08-14 adaptive grid | 已集成；adaptive grid反而更差 | 不得泛泛“试VMD” |
| multi-bin | 2026-08-07 已用于主线；2026-08-14 AgeBalanced A/B | AgeBalanced 9.5→9.3，小收益；2× lock 4→6 | 不得重新包装成新方向 |
| adjacent-bin SPC | 2026-08-11 00:40 | +1.8%，弱信号无帮助 | 仅作为历史/可选排序 |
| phase difference | 2026-08-11 | 无增量 | 不采用 |
| CFAR | 2026-08-11 | 漏检增多 | 不采用，除非场景/输入完全不同 |
| SSA | 2026-08-11；2026-08-27 Lei adapted | 预实验无增量；后续无稳定 rescue | 不再盲试 |
| CEEMDAN | 2026-08-11 | SNR更低、计算贵 | 不采用 |
| envelope norm | 2026-08-11 | 无增量 | 不采用 |
| Hampel on IBI | 2026-08-11 | 压平正常RSA，SDNN显著下降 | **禁止照搬到IBI** |
| fixed respiratory notch | 2026-08-14 | 9.5→10.4 | 已回退 |
| temporal continuity | 2026-08-07/14 | 小幅帮助，不能证明生理正确 | 只能辅助，不是gold evidence |
| 8-channel spatial consistency | 2026-08-25 | target-lock候选有效 | 不等于HR有效 |
| AoA / A43 / ADC angle | 2026-08-07、08-12~13 | 实际开发/校准过；1D链不支持完整角度主线 | 只有输入/固件改变才重开 |
| adapted SSA+VMD / Lei SSA | 2026-08-27 | 无稳定大幅优势 | 不继续算法海选 |

---

## 5. FocusWave 采集程序的演变

### `kyandi233-dev/FocusWave@stable-msmf`

当前 `01-MainProgram/core/mmwave_capture.py` 自身保留了 v1→v4 语义：

- v1/v2：从官方 DLL 采 2T4R complex IQ；建立 BIDS-like 输出、bin/npz/timestamp/meta
- v3（2026-07-23）：dual timestamp、chunked NPZ、flush、stop 顺序、时区修复
- v4（2026-07-24）：与 37 mm 固件/PSIC header 对齐；57 GHz、2T4R、range FFT 256、Doppler header 32、约100 fps
- 2026-08-09/10：修复空 NPZ chunk 导致分析阶段 crash；采集端不再写空 chunk，分析端也防御空 chunk

### `@ecg` 分支的采集/marker历史

- 2026-08-15~16：`02-tools/11-calibrate-mmwave-ecg.py` 建立 mmWave × Biopac 双机校准，rest/deep-breath/breath-hold/rest，多级 marker + 每秒 tick。
- commit `e6dea96...`（2026-08-16）：正式实验接入生理多导 marker、`events.csv`、camera 开关。
- commit `550c30e...`：禁用中文输入法，修复字母/空格被 IME 截获；这会影响 SART 行为数据完整性，因此属于数据语义历史，不是普通 UI 修复。
- commit `8e6fe5c...`：呼吸专注测试程序。

**边界**：ECG/RSP calibration 是工程/机制/reference evidence。历史校准记录主要是同一人反复测量，绝不能写成“11个独立被试验证”。

---

## 6. NIR producer 的演变

### 2026-08-16：旧多算法环境被停止门拦住

`Attention-Analysis/docs/010-overview/014-2026-08-23项目总览与架构历史快照.md` 记录：

- 当时 PuRe/PuReST/RITnet/DeepVOG、MediaPipe/YuNet/YOLO-face 等路线均有历史环境。
- 正式双眼近景下 MediaPipe、YuNet、当时 YOLO-face 的 ROI 身份门不通过，生产停止。
- 后来由自训练 YOLO26n eye ROI + RITnet 路线突破。

因此以后不能说“换 MediaPipe/YuNet/YOLO-face 看看”而不先说明为什么历史身份失败条件已消失。

### 2026-08-23~26：正式 NIR runtime 与时间戳语义修复

正式链：

`video → sequential AVI frame/unix_ms → YOLO26n eye ROI → RITnet → pupil/fullclass + phase → QC/alignment`

2026-08-26 的关键 bug 修复：timestamp CSV 第一列是 **capture counter**，可能跳号；它不是 AVI frame index。正确做法是用有效 timestamp 行的顺序作为 AVI frame index，同时保留 capture counter provenance。

恢复结果：

- sub-100：capture gaps存在，但 AVI frames = valid timestamp rows，修复后 RECOVERED
- sub-178：同样 RECOVERED
- 两场完成 full video recovery、fullclass、probe alignment
- cohort 从 69/72 formal complete 进展到 **71/72**；matched cohort 71 sessions / 1,420 probes
- sub-099 仍因 `master_timeline.csv` 缺失阻塞，不是 NIR AVI gap 问题

### NIR V1 scientific-fix / incremental 的历史边界

已有 producer 报告曾得到：

- 71 sessions / 1,420 probes 的 quality-tiered matrix
- 1,174 probes primary coverage >=0.80；38 sensitivity-only；208 excluded
- 旧 incremental report：Behavior AUC约 .566、Behavior+NIR约 .599，Δ≈+.033，但 CI 跨0；属于历史结果

中央 Issue #12 后又在 pre-recovery 68-session/1,360-probe artifact 上读到 `C+B .672 → C+B+NIR .598`、Δ约 -.074。

**当前工作决定（2026-08-28）**：NIR 已明确需要重算，#12/#14 暂停。因此上述正/负增量都不能被拿来包装成最终 NIR 科学结论；它们必须保留为 `HISTORICAL / PRE-RECOMPUTE`。

---

## 7. RGB producer 的正式边界

`Attention-Analysis/docs/040-rgb/041-RGB分析目标与数据流.md` 与 `044-RGB输出Schema与信息保留原则.md` 已经把 RGB 定义得很清楚：

- RGB 的第一阶段不是“直接预测专注”，而是保存可审计的 **Face + Pose + Motion** 连续行为测量。
- 所有对齐依赖真实 Unix ms，不允许 nominal fps 推时间。
- 昂贵模型的 raw output 先完整保存，再加 QC flag，最后才派生/筛选；不能为了某次模型随便丢字段。
- rPPG / RGB HR/HRV / 单一 attention score 不属于当前正式 RGB 主链。
- Pose 要保留完整 landmarks；Face 要保留模型能够稳定给出的完整 AU/expression/gaze/head outputs；Motion 要保留 gap/time identity/QC。
- probe-level 统计必须建立在正式 producer/QC/alignment manifest 上。

**防重复/防粗暴使用**：不得再拿 3 个 session 的 motion pilot、legacy `dark_fraction`、Hough proxy 或随便几个动作特征直接塞进 multimodal ladder 当“RGB 已完成”。

---

## 8. Behavior 分析的历史演变

`Attention-Analysis/docs/030-behavior/history/BBB-v3.0/001-正式SART行为分析报告.md` 在 2026-08-16 的 19 人早期样本已经显示：

- vigilance 随 block 恶化（omission、RT-CV）
- pre-error RT 有加速模式
- 多个指标 B1↔B3 个体排序相关较高（commission .849、omission .896、d' .917、RT-CV .853 等）

这类结果说明“稳定个体差异”并非完全没有证据，但它是**同一 session 的跨 block 排名稳定**，不能自动等于跨天 retest reliability。

后续中央分析必须继续区分：

1. probe/window 的动态状态效度
2. session-level person indicators
3. repeat-session/participant 的跨 session 稳定性
4. 与“自评专注水平 / 平时可持续专注多久”等长期自评的外部效标关系

因此“稳定特质全部 BLOCKED”过于粗暴；正确说法是：**状态证据更成熟，person-level 稳定性有现成数据路线但尚需按重复被试/问卷正式闭合。**

---

## 9. 当前 J_Data / mmWave 主线状态（2026-08-27~28）

### Issue #15 — physiology

当前 `PARTIAL`：

- HR：70/70 sessions 有值；1,297/1,400 probe-quality windows；1,056/1,400 paired pre/post HR；42/70 sessions 达到历史 >=80% paired coverage。定位为 **quality-gated primary candidate + sensitivity**。
- BR：50/70 sessions 同时达到 window/probe >=80% historical coverage；定位为 **supporting sensitivity**。
- HRV：70/70 有字段，但 ECG/beat/IBI validation 未闭合，继续 `exploratory-blocked`。
- 067：无 mmWave raw，`BLOCKED`。
- 099：有 raw 和 supplemental output，42 full windows、20/20 probe windows，但 timeline/meta/provenance 未闭合，不能并进原 70 场主模型。

最终 HR/BR quality gate 还需要按覆盖、gap/motion/keypress、BR/2BR/3BR 冲突、邻窗连续性、channel/bin evidence、reference status 联合确定；SNR 单字段不能判 PASS。

### Issue #16 — task dynamics / alertness

- 原 70 sessions 主分母不变。
- task dynamics / alertness 主模型已经完成；fixed-bin 只做 sensitivity。
- 等 #15 的最终 HR/BR strata 后，只补一次 predefined quality sensitivity。
- questionnaire bridge 的 68/67 分母要明确缺失对象和原因，不能静默换样本。

### Issue #17 — report-ready matrix

- 已生成唯一 **72-row session matrix**。
- 067 明确无 raw，不再浪费时间补跑。
- 099 只追 timeline/meta/provenance，不重新调 producer。
- #15/#16 后续都应读取同一 session matrix，禁止自己长出不同分母。

### C2B/C2C

Behavior+mmWave 增量已经做过，不重跑：

- C2B-v2 30 s strict matched：C+B AUC约 .686，C+B+W约 .646，Δ约 -.040
- C2C within-subject：C+B约 .670，C+B+W约 .640，Δ约 -.030，CI跨0

这些是“mmWave 是否在 Behavior 基础上增加 probe prediction”的问题，与“HR/BR 是否是可信生理指标”是两条不同证据链。

---

## 10. 明确的 `MISSING_EVIDENCE` 项

以下数字曾在后续总结中出现，但本轮逐仓库追溯仍未找到能把它们与**原始脚本 + 结果表 + 执行日期/commit**同时绑定的 durable GitHub 证据：

- “8 个窗口 multi-channel/multi-range 原型 HR MAE ≈45 BPM”
- “phase-domain fusion 400/400”
- “同 Tx coherence ≈0.458、跨 Tx ≈0.476”
- “自动 range-bin 244–248 vs 主功率峰 8–13”

因此这些数字现在统一记为 `MISSING_EVIDENCE / UNLINKED HISTORICAL NOTE`。以后若在本地旧输出或历史 commit 中找到原始产物，再补日期和证据；找到前不得用它们支撑新科学判断。

另有中央 EVIDENCE_LEDGER 已明确：早期 v1-v9、七类 A/B 的部分 exact method-level n/parameter/output 仍不完整，也必须保留 `MISSING_EVIDENCE`，不能从叙述反推精确数值。

---

## 11. 任何新计算前的 Reuse Gate

新的 Codex / ChatGPT / 人工分析在花费 GPU/CPU/API 预算前，必须先回答：

1. 本问题在本账本里有没有已经做过的同类方法？
2. 原脚本、结果、commit、数据范围在哪里？
3. 这次输入语义是否真的不同（例如 RS6240 raw vs AgeBalanced derived；30s vs 50s；ECG official reference vs旧 scorer）？
4. 这次研究问题是否不同（例如 probe prediction vs HR physiology validation）？
5. 新实验如果失败/成功，能否改变当前决策？若不能，就不运行。
6. 是否会重复 C2B/C2C、旧 NIR ladder、七类 mmWave A/B、multi-bin、VMD、angle/A43、fixed notch 等已做路线？
7. 如果必须重复，必须在任务开头写出“**为什么旧证据不足以回答这次问题**”。

如果第 7 点写不出来，默认停止重复计算。

---

### 2026-08-30：mmWave block-reset + ECG marker-aligned targeted validation rerun — PARTIAL

**为什么旧证据不足**：旧版 12 个 transition 只来自每场起始后的前 6000 frames，没有按正式程序 block marker 切段，也没有按 block 重建 mmWave↔ECG 同窗映射；因此不能回答“block 内 target continuity 是否稳定”或“marker-aligned HR/BR 是否改善”。

**输入与来源**：`greenboo26/focuswave-multimodal-attention-analysis@main` at `6ca449020039b6eabe0f0665024bead6c706a1a0`；`kyandi233-dev/FocusWave@ecg` at `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`；sessions `97793`、`9779`、`97795`；contract `docs/research/MMWAVE_BLOCK_RESET_AND_ECG_ALIGNMENT_CONTRACT_2026-08-30.md`。

**执行与结果**：每个完整 block 重新初始化 target/bin/channel，20 s window / 10 s step / 5 s boundary guard；8 个完整 block、335 个窗口、327 个同 block transitions。Local candidate 将 HR bin hops `243/327 → 164/327`、HR channel switches `246/327 → 158/327`，但 HR MAE `25.958 → 24.885 bpm`，BR MAE `3.723 → 4.237 breaths/min`，不支持 producer promotion。ECG 使用 `events.csv` start/end marker 与 Biopac digital pulse 的 block-local affine fit；ECG residual p95 median `2.296 ms`。7/8 marker sequences exact；`97793/block1` index 73 为 event `103` vs physical `102`。mmWave tick 有 730 个超过 100 ms 的 timestamp gap；gap 排除后 affine residual p95 median `6.133 ms`，仍标为 alignment limitation。

**决策**：旧 12/12 不再作为 continuity failure 证据；当前 block-local continuity 只能作诊断性证据。HR、BR/RR 保持 `HOLD`，HRV 保持 `BLOCKED`；Issue #16、C2B/C2C、VMD/新 HRV 和全量 formal batch 不运行。以后若重做，必须先解决 tick gap 的来源/语义和单点 marker mismatch，并继续使用 block-local reset + marker-aligned contract。

**证据包**：`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/` 的 `MMWAVE_TARGETED_VALIDATION_REPORT_2026-08-30.md`、`target_continuity_block_local.csv`、`mmwave_ecg_block_window_comparison.csv`、`ecg_alignment_audit.csv`、`legacy_12_transition_audit.csv`、`target_continuity_summary.json`、`ecg_alignment_summary.json`、`run_manifest.json`；脚本 `scripts/maintenance/run_mmwave_targeted_validation_20260830.py`。

---

### 2026-08-30：历史 ECG 参考链审计与固定毫米波重放 — PARTIAL

**为什么需要补审计**：targeted rerun 得到的 `24.885 bpm` 与历史 `3.777/4.590 bpm` 使用了不同 cohort、window 和毫米波端口径；在没有把旧 ECG 脚本、marker/offset、R-peak 规则和结果 provenance 分开之前，不能判断差异来自 ECG 参考还是毫米波/窗口变化。因此在审计完成前，当前 targeted 数值暂标为 `PROVISIONAL / REFERENCE_PIPELINE_AUDIT_PENDING`。

**输入与来源**：canonical `main` 已核验为 `472735b6b6af5f98e92ab7815718e81863cb6098`；历史 `master` 为 `96525b19422b34291e4d87747fef214d1fec60d7`；FocusWave `ecg` 为 `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`；mmWave reanalysis reference 为 `d87229afe071f23450728a6d617ec82317e6c9df`。已盘点 `analyze_acq_reference.py`、`gold_standard_qa.py`、`validate_gold_anchor.py`、旧 calibration 脚本、`ecg_reference_v1.py` 和 FocusWave marker 源；`Attention-Analysis@nvidia-cuda` 未找到相关 ECG/BIOPAC/mmWave reference script。

**历史结果**：`4.5901918 bpm` 是 5 sessions / 100 rows / 99 valid HR-course windows 的旧 `0.08 m/bin` gate reproduction；`3.7772146 bpm` 是相同 99 valid windows、同一历史 ECG 参考链下，仅将毫米波距离口径改为 `0.037 m/bin` 的 corrected-gate estimate。另有 goldclean re-pair `5.023715 bpm`。这些结果均为 60 s calibration/probe 口径，不能直接替代当前 3-session、20 s block-local targeted comparison。

**固定重放**：对 `97793`、`9779`、`97795` 的 335 个当前 block windows 固定既有 `local_hr_freq_bpm` 毫米波值，分别使用 historical metadata-zero ECG、current per-block marker-affine ECG 和 minimal-difference arm。结果为 `24.912767`、`24.880549`、`24.912767 bpm`；255/335 个窗口 ECG HR 有数值变化，但中位绝对变化 `0.15 bpm`、最大 `3.30 bpm`。因此当前约 24.9 bpm 误差不能归因于 ECG alignment；主要差异仍在当前毫米波估计器、cohort/window 和历史距离门不等价。

**决策**：历史 ECG 链已达到脚本/commit/参数/结果层面的可追溯；当前 targeted comparison 从 provisional 提升为 `QUALIFIED_FOR_THIS_FIXED_COMPARISON`，但整体状态仍 `PARTIAL`。HR/BR/RR 继续 `HOLD`，HRV 继续 `BLOCKED`。`97795` 的 `97995.acq` 文件名差异保留为 provenance limitation；mmWave timestamp gaps 与历史/当前毫米波估计器差异仍阻止统一 cross-era MAE 和 PASS。

**证据包**：同一结果目录新增 `ECG_SCRIPT_LINEAGE.csv`、`ECG_HISTORICAL_RESULT_PROVENANCE.csv`、`ECG_REFERENCE_PIPELINE_COMPARISON.csv`、`ECG_REFERENCE_PIPELINE_SUMMARY.csv`、`ECG_REFERENCE_AUDIT_REPORT_2026-08-30.md`、`ECG_REFERENCE_AUDIT_MANIFEST.json`；执行入口为 `scripts/maintenance/audit_historical_ecg_reference_chain_20260830.py`。原始 `.acq`/NPZ、实验程序、producer、portable V2 和 Attention-Analysis portable V2 均未改动。

---

## 12. 新智能体最小阅读顺序

1. `ANALYSIS_HISTORY_LEDGER.md`（本文件）
2. `README.md`
3. `docs/canonical/SCIENTIFIC_METHOD_REVIEW_V1.md`
4. 当前具体 analysis card / contract / issue
5. 若涉及 mmWave：`docs/mmwave_reanalysis_v2/EVIDENCE_LEDGER.md` + `FAILURE_MODE_REGISTRY.md` + 当前 #15/#16/#17
6. 若涉及 NIR/RGB：到 `kyandi233-dev/Attention-Analysis` 读取对应 producer 当前 README / result / schema，不从中央旧 proxy 猜字段
7. 若要追历史过程：再查 `greenboo26/project@august/.claude/work-logs/`

禁止仅根据聊天记忆或单条 README 提议高成本重跑。

---

## 13. 关键证据索引

### 中央科学仓

- `README.md`
- `PROJECT_STATUS.md`
- `docs/provenance/CROSS_REPO_PROVENANCE_V1.md`
- `docs/canonical/SCIENTIFIC_METHOD_REVIEW_V1.md`
- `docs/canonical/analysis_cards/c2b_v2.md`
- `docs/canonical/analysis_cards/c2c.md`
- `docs/mmwave_reanalysis_v2/EVIDENCE_LEDGER.md`
- `docs/mmwave_reanalysis_v2/ISSUE_7_ROOT_CAUSE_B_AUDIT.md`
- `docs/mmwave_reanalysis_v2/OFFICIAL_REFERENCE_EXISTING_ROUTES_RESULT.md`
- Issues #9, #12, #15, #16, #17, #18

### Acquisition `FocusWave`

- `01-MainProgram/core/mmwave_capture.py`
- `02-tools/11-calibrate-mmwave-ecg.py` (`ecg` branch)
- `04-docs/CHANGELOG.md`
- commits `e6dea96...`, `550c30e...`, `8e6fe5c...`

### `Attention-Analysis`

- `docs/010-overview/014-2026-08-23项目总览与架构历史快照.md`
- `docs/020-nir/08-16-03-NIR历史多算法环境与迁移说明.md`
- `docs/020-nir/029-NIR时间戳映射修复与sub100_sub178恢复任务.md`
- `docs/020-nir/results/nir_timestamp_mapping_recovery_v1/NIR_TIMESTAMP_MAPPING_RECOVERY_RESULT.md`
- `docs/020-nir/results/nir_matched_cohort_regeneration_v1/NIR_MATCHED_COHORT_DIFF.md`
- `docs/020-nir/results/nir_v1_scientific_fix/NIR_V1_MINIMAL_SCIENTIFIC_FIX_REPORT.md`
- `docs/020-nir/results/nir_incremental_value_v1/NIR_INCREMENTAL_VALUE_REPORT.md`
- `docs/030-behavior/history/BBB-v3.0/001-正式SART行为分析报告.md`
- `docs/040-rgb/041-RGB分析目标与数据流.md`
- `docs/040-rgb/044-RGB输出Schema与信息保留原则.md`

### Workspace / 历史过程

- `greenboo26/project@august/PROJECT_INDEX.md`
- `.claude/work-logs/2026-07-20_mmWave采集脚本.md`
- `.claude/work-logs/2026-07-23_v3采集脚本修复_算法VMD集成.md`
- `.claude/work-logs/2026-07-24_厚粲杯_固件编译_50分钟测试_数据分析_问卷设计.md`
- `.claude/work-logs/2026-08-07_毫米波算法迭代与四被试分析.md`
- `.claude/work-logs/2026-08-07_深慢呼吸验证实验.md`
- `.claude/work-logs/2026-08-09_预实验诊断与人体验证工具.md`
- `.claude/work-logs/2026-08-10_毫米波预实验信号质量排查_0810重测对比.md`
- `.claude/work-logs/2026-08-12_ADC固件实测与测角方案排查.md`
- `.claude/work-logs/2026-08-13_测角校准与正式实验设计.md`
- `.claude/work-logs/2026-08-15_毫米波ECG双机校准.md`
- `.claude/work-logs/2026-08-16_毫米波ECG校准诊断与生理多导程序开发.md`
- `.claude/work-logs/2026-08-16_毫米波金标准对称清洗与锁半频根因定位.md`
- `.claude/work-logs/2026-08-16_正式实验第一批数据分析与毫米波方法学重构.md`
- `01_管理/01_项目管理/分析记录.md`

---

### 2026-08-30：mmWave estimator lineage、same-window replay 与 timestamp semantics audit — PARTIAL

**输入与历史链**：canonical `main` `64634159d226ee1ed892d53e56fcf3697fbff9b8`；固定输入为 335 个 complete formal-block、20 s 窗口及既有 block-affine ECG HR。历史 `3.7772146 bpm` 已绑定到 `run_hr_course_99_corrected.py → process_vital_signs_v3_1_1.py`：6000-frame fixed target selection、`0.037 m/bin`、`0.30–1.50 m` bins 9–40、`bp_heart`、0.8–2.0 Hz、60 s historical probe、5 sessions/99 valid windows。master legacy、calibration 和 reanalysis utilities 已加入 lineage inventory，并标注不是该数值的 producer。

**同窗结果**：strict 60 s historical arm 对当前 20 s rows 为 `NOT_APPLICABLE_TO_20S`；20 s minimal adaptation MAE `14.748328`，current independent `25.958119`，current block-local `24.884913`，均 335/335；current 两个重算 arm 与冻结旧行 335/335 exact、最大差 0。Pairwise 同分母中 adaptation 相对 independent 在 242/335 窗口更好、相对 block-local 在 231/335 更好；independent 与 block-local 的绝对误差平均差为 `1.073206 bpm`，163/335 tie。历史 adaptation 不能回溯等价成历史原始 60 s 结果，故不判定 current regression 或 historical pipeline 已在当前窗口成立。

**target 与时间结论**：历史 9–40 gate 与当前 selector 不等价；bin+channel exact 仅 4/335（independent）和 4/335（block-local），落在历史 gate 外分别 186/335、154/335。A 类 event tick→nearest mmWave residual 为 3491 条、>100 ms 为 730；B 类相邻 frame interval 共 459126 条，median/p95/p99/max 为 7/20/31/6495 ms，>20/>50/>100/>500 ms 为 20682/840/457/457。730 不得再称为 frame gap；B 的 457 条才是实际 >100 ms 相邻间隔证据。

**决策与证据**：整体状态 `PARTIAL / TIMESTAMP_SEMANTICS_CLASSIFIED`；HR 保持 `HOLD`，不运行 HRV 新算法、#16、C2B/C2C 或全量 formal batch，不修改 producer、firmware、raw、FocusWave acquisition 或 portable V2。证据文件为 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_HR_ESTIMATOR_LINEAGE.csv`、`MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv`、`MMWAVE_HR_ESTIMATOR_SUMMARY.csv`、`MMWAVE_HR_ESTIMATOR_PAIRWISE_COMPARISON.csv`、两个 markdown report、manifest 和 `scripts/maintenance/run_mmwave_estimator_same_window_audit_20260830.py`；完整 timestamp CSV 位于 `D:\Project\厚粲杯\11_数据\derived\mmwave_timestamp_semantics_audit_20260830\`，manifest 记录 hash。

---

### 2026-08-30：mmWave gate/target ablation — PARTIAL / GATE_AND_TARGET_BOTH_MATTER

**输入与 arm**：沿用 canonical `main` `21be8b22e4c6460b819f82cc97fe9fb0a4e25bed` 的 335 个 complete formal-block 20 s windows、同一 block-affine ECG 和同一当前 HR estimator。ARM0 为 current block-local；ARM1 为其加历史 bins 9–40 gate；ARM2 为历史 6000-frame fixed target；ARM3 为 gate + current block-local。按文字定义 ARM1/ARM3 逐窗完全相同，未把它们当作独立 block-local 对照。

**结果与决策**：ARM0 MAE `24.884913`（335/335）；ARM1/ARM3 `21.804185`（314/335）；ARM2 `19.068931`（335/335）。ARM1 vs ARM0 mean ΔAE `-2.638525`（common n=314），ARM2 vs ARM0 mean ΔAE `-5.815982`（common n=335）；三名被试及四个 block 的 participant/block MAE 均同方向改善。ARM0 gate 内 MAE `21.902392`，gate 外 `28.390344`。因此选择 `GATE_AND_TARGET_BOTH_MATTER`，但不升级为 producer change candidate，HR 继续 `HOLD`。

**长间隔限制**：457 个真实 >100 ms adjacent frame intervals 全部 overlap 到 335/335 HR windows，无法形成无 gap comparator；`TIMESTAMP_LONG_INTERVAL_EFFECT=UNRESOLVED`，不删除窗口。证据为 `MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv`、summary/paired/participant/block/stability/gate-split/gap-split、report、manifest 与 `scripts/maintenance/run_mmwave_gate_target_ablation_20260830.py`。

---

### 2026-08-30：mmWave long-frame interval source/impact audit — PARTIAL / TIMESTAMP_RECORDING_ARTIFACT

**为什么需要这次审计**：上一版只能确认 457 个 Python timestamp column-3 相邻间隔超过 100 ms，且 335/335 个 HR 窗口都被覆盖，无法区分真实采集帧丢失、consumer/write 暂停、NPZ 分块边界或时间戳语义问题。因此本次不继续调 HR estimator，而是只追溯采集源、时间戳阶段、分块周期与窗口 burden。

**输入与冻结口径**：canonical `main` `42167d3a112215701fad09ec21999a78a977baad`；`97793`、`9779`、`97795`；335 个既有 complete formal-block 20 s windows；同一 window start/end、同一 frozen block-affine ECG HR、同一现有 HR frequency estimator。FocusWave source 为 `ecg` commit `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`，历史 acquisition source 为 `817a7fccb969bcc6e1e0071b387f88e3b3494481`。ECG/BIOPAC mapping 继续使用 `beh/events.csv` 的 block markers（baseline 11/21、block1 12/22、block2 13/23、block3 14/24、rest 15/25、block4 16/26 if used）和 101–110 ticks；既有 alignment audit 为 8 complete blocks、7/8 exact marker sequences。

**来源证据与结果**：`mmwave_capture.py` 的 SDK/DLL callback 先进入 bounded queue；consumer 线程在 `_process_datacube` 中生成 DLL timestamp 与 Python `time.time()` timestamp 并写 CSV；每 1000 个 processed frames 同一 consumer 线程执行 `np.savez_compressed` chunk rotation。457/457 个 Python 长间隔同时 >500 ms，0 个在 100–500 ms；457/457 个跨 NPZ 文件边界，frame index modulo 1000 对每名被试恒定。DLL timestamp 没有任何 >100 ms 或 >500 ms interval，DLL event periodicity 和 frame spacing 均约 10 s / 1000 frames。Python 列另有 6,203 个同毫秒重复、0 个负间隔，故无 timestamp reset。

**Window burden 与关联**：335/335 个窗口保留 burden 行；每窗 n_gap_gt100 为 1–2，平均 `1.755`，sum gap 平均 `4143.660 ms`，max gap 平均 `2544.337 ms`。以 DLL 约 10 ms 估算 expected frame count，实际 frame count/estimated loss fraction 仅作为窗口索引密度诊断，不等同真实 sensor frame loss。Spearman 为描述性：overall n_gap 与 absolute error 的 ARM0/ARM1/ARM2 分别 `-0.058547/0.004575/-0.065296`；sum-gap 分别 `0.040775/0.027823/-0.046619`；完整 participant/block 分层结果在 correlation CSV 中。所有窗口均有 artifact burden、没有 clean no-gap comparator，因此不作因果结论。

**决策**：`GAP_SOURCE_CLASSIFICATION=TIMESTAMP_RECORDING_ARTIFACT`；`GAP_EFFECT_ON_HR=UNRESOLVED`；`FIXED_FS_WITH_GAPS=QUESTIONABLE`。当前 estimator 的固定 `FS=100.0`、bandpass、periodogram、peak 均未修改，也未运行 timestamp-aware resampling（对 writer-artifact 列重采样不安全）。HR/BR 继续 `HOLD`，HRV `BLOCKED`，Issue #16 `PAUSED`；没有修改 producer、firmware、raw、FocusWave、portable V2、C2B/C2C 或全量 batch。

**证据包**：`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv`、`MMWAVE_WINDOW_GAP_BURDEN.csv`、`MMWAVE_GAP_BURDEN_CORRELATION.csv`、`MMWAVE_ACQUISITION_TIMESTAMP_SOURCE_AUDIT.md`、`MMWAVE_LONG_INTERVAL_AUDIT_REPORT_2026-08-30.md`、`MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json`、`ecg_alignment_audit.csv`；脚本 `scripts/maintenance/run_mmwave_long_interval_source_audit_20260830.py`。允许的下一步仅是基于 DLL/帧序列重新定义 timestamp/window contract 后再做只读复核，不是继续调 HR estimator。

### 2026-08-30：formal multimodal model-ready v1 — PASS_MODEL_READY

**输入与分母**：沿用 current mother-table attach 的 1,440-probe canonical timeline、72 current sessions、46 repeat participants和 `pre_30s` 五列 probe key。以 Behavior observed AND NIR observed AND RGB observed 冻结 primary matched cohort：1,295 probes、65 sessions、46 repeat participants；未使用 label-dependent filtering。

**缺失与 QC**：NIR 明确分为 `OBSERVED=1,294`、`STRUCTURAL_MISSING=140`、`OBSERVATION_MISSING=5`、`QC_FAIL=1`；RGB 为 `OBSERVED=1,420`、`STRUCTURAL_MISSING=20`。sub-099 的 20 行归因为 processed session/raw parquet/subject manifest absent，现有证据另显示 `master_timeline.csv` 缺失；不把它升级为 postprocessing、probe-overlap 或 QC failure。NIR QC_FAIL row 保留在 observation-defined denominator，geometry 保持 NaN。

**合同与决策**：冻结 Behavior=5、NIR=4、RGB=6 primary predictors；NIR 只用 fullclass pupil geometry，不启用 PIR；blink 仍为 provisional，PERCLOS absent/not validated，mmWave HOLD/EXCLUDE 字段不进入 primary predictor。46 个 participant-disjoint LOSO folds、participant/session/probe leakage audit、Behavior pre-onset temporal audit、source-hash/readiness gate 均 PASS。最终允许进入下一阶段 formal baseline modeling，但本轮不训练模型；下游必须先声明 NaN handling，不得静默改变 1,295 分母。

**证据与边界**：Git-safe package 为 `docs/results/2026-08-30_FORMAL_MODEL_READY_V1/`；完整 probe-level missingness audits、expanded folds 和 model-ready candidate 保留本地，不上传 canonical。生成器为 `scripts/maintenance/build_formal_model_ready_v1.py`，通过显式参数读取既有本地 package 和 producer roots，不启动 producer。

---

### 2026-08-30：Issue #25 20 s 来源与历史 60 s 受控比较 — PARTIAL / DIAGNOSTIC_ONLY

**输入与来源**：执行时的 `PRE_INTEGRATION_BASELINE` 为 `805db1d3f2d701d46f678b7cd911990f779a4966`，结果已集成到 canonical `main` `4986ca32716fe415c01b518587b031da55d481c1` + `65b8e6547394be9c5bddba823ca7c72ce8e7ab38`；20 s 来源绑定 `472735b6b6af5f98e92ab7815718e81863cb6098` 的 `scripts/maintenance/run_mmwave_targeted_validation_20260830.py`，历史 60 s 语义绑定 `64634159d226ee1ed892d53e56fcf3697fbff9b8` 的 `run_hr_course_99_corrected.py` / `build_hr_course_99_audit.py`（25 s internal course、5 s step、60 s trailing probe median）。

**#24 依赖与口径**：复用 #24 commit `d2d09f8ac502600d3a1241e33c429bd53756fa45`，manifest repo-relative path 为 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_ELIGIBILITY_MANIFEST.json`，commit 内容 SHA-256=`0806cb4f0e477788ee7cd604e3d04c811654fb692f2840767249982ebc5ba258`；其 ECG_VALID/ECG_INVALID/UNRESOLVED=`325/10/0`。当前两种时长均调用同源 `gold_standard_qa.py::ecg_qa` eligibility adapter：0.5–40 Hz、固定 R-peak、300–2000 ms IBI、相邻 IBI >20% artifact、valid coverage ≥80%、至少 3 个 valid IBI；marker mismatch 仅 warning。

**实际运行与结果**：RUN_ID=`issue25_window_length_20260830`，固定 10 s endpoint grid、8 complete blocks、303 paired endpoints、283 ECG_VALID pair。20 s nominal resolution=`0.05 Hz/3 bpm`，coverage mean/median=`0.655511/0.691708`，n=`283`，MAE/median AE/bias/Pearson/Spearman=`14.703129/14.514286/-12.598120/0.278024/0.268721`；60 s nominal resolution=`0.016666667 Hz/1 bpm`，coverage=`0.656046/0.691986`，n=`283`，对应=`5.608574/4.083467/-3.630629/0.379439/0.399861`。同窗 AE 差（20 s−60 s）mean/median=`9.094555/7.4`，20 s better/tie/60 s better=`74/1/208`，仅作 diagnostic。

**复用门与决策**：`REUSE_REJECTION_REASON` 为既有 same-window audit 仅有 20 s denominator、strict 60 s=`NOT_APPLICABLE_TO_20S`，缺少 paired 60 s DLL-time window 与 paired ECG_VALID reference，故增加最小 wrapper；未按结果选长度，未新造 estimator。结论为 `PARTIAL / DIAGNOSTIC_ONLY`，formal window validity=`UNRESOLVED`，HR=`HOLD`；允许以后复用入口为 `scripts/maintenance/run_mmwave_window_length_comparison_20260830.py`，证据位于 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_WINDOW_LENGTH_*`，raw/row-level/large outputs 不入 Git。

## 14. 维护规则

以后任何实际运行的新分析，只要产生“采用 / 放弃 / 结果无效 / 参考被替代 / 数据语义修复”之一，就必须在同一次交付中更新本账本，至少写：

`日期 → repo/ref/commit → 输入范围 → 脚本/配置 → 核心结果 → 决策 → 是否允许以后重复 → 被什么证据替代（如有）`

**不允许再出现“其实两周前做过，但后来智能体因为没看到记录又花钱重跑”的情况。**
