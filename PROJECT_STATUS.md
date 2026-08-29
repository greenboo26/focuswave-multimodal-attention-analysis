# FocusWave Multimodal Attention Analysis 状态

## 2026-08-30 formal firmware deployment correction — CONFIRMED_WITH_PROVENANCE_LIMITATION

- Formal acquisition operator confirmation: the identified `mrs6240_p2512.img` firmware (SHA-256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`) was the firmware used throughout the formal acquisition. This is no longer an uncertainty about which firmware was deployed.
- The remaining gap is narrower: machine-generated burn/readback/serial boot/version receipts tied to the sessions were not retained/recovered. That is a provenance/reproducibility limitation only and must not be restated as “unknown formal firmware identity.”

## 2026-08-30 ordered mmWave next-execution gate — PARTIAL / #16 PAUSED

- 按 `docs/research/MMWAVE_NEXT_EXECUTION_PROMPT_2026-08-29.md` 顺序完成本轮只读审计；未重复已闭合的 Range FFT、37 mm、8-channel discovery。
- A：新增 `docs/research/MMWAVE_DEVICE_FIRMWARE_ENGINEERING_EVIDENCE_2026-08-30.csv`，逐项给出 window、padding/scaling、DC/clutter、IQ、校准、Tx/Rx、TDM timing/compensation、烧录/启动/版本的状态。正式实验所用固件身份已由采集操作记录确认；formal-session machine burn/boot/version/config receipt 仍缺失，仅作为 provenance/reproducibility gap，不再作为“用了哪版固件”的 blocker。
- B：既有 JSON/NPZ 有 segment-level 最终 bin/channel 与 radar peak array，但没有跨 window previous/current target history、bin/channel switch 或 phase discontinuity；continuity rate 不可从现有产物推出，已记录最小 instrumentation/rerun contract，未启动 formal batch。
- C：精确链 `formal runner → analyze_long_record → _analyze_long_record_v23 → _heart_segment_reference_correction → _window_hr_candidates → respiration_harmonic_reject` 已复核。标准 runner 不传 `acq_path/ext_br_bpm`，故 external RSP 2x/3x harmonic rejection 为 `INACTIVE`；内部 folding 仅 heuristic。
- D：HRV 最早 blocker 为同步 radar beat ↔ ECG R-peak beat-level matching/paired IBI agreement 缺失；HRV 继续 `BLOCKED`。
- 无模型、#16、C2B/C2C、target-lock rerun、设备烧录、原始数据、NIR/RGB 操作；#16 保持 `PAUSED`。

## 2026-08-29 mmWave literature/pipeline audit decision — PASS / #16 PAUSED

- 已建立 canonical 文献证据与决策账本：`docs/research/MMWAVE_LITERATURE_EVIDENCE_AND_DECISION_LEDGER_2026-08-29.md`。
- 已建立机器可读文献登记：`docs/research/MMWAVE_LITERATURE_EVIDENCE_REGISTER_2026-08-29.csv`。
- 已补回此前 RS6240 固件/手册/DataCube 审计中已经确认的 upstream 事实，见 `docs/research/MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`：`ReportDataCube1D` 不是 raw ADC，而是 8 通道 complex range-domain DataCube；Range FFT 已发生在 upstream；formal distance spacing 固定为 `0.037 m/bin`。这些事实不得再次整体降级为 `UNVERIFIABLE_UPSTREAM`。
- 已登记此前 formal firmware 镜像审计身份：`mrs6240_p2512.img`，SHA-256=`7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`，记录 build time=`2026-07-24 21:33:39`；该镜像现已由采集操作记录确认就是正式实验全程使用的固件。generic SDK default 仍不能直接当成 exact formal firmware behavior。
- 当前决策：formal producer/downstream 逐行/逻辑块科学审计已完成；Issue #16 quality-stratified sensitivity 仍暂停，等待单独授权与科学输入确认。
- `33/37/2` 当前只能作为 current-pipeline QC/eligibility strata；不得直接解释为 33 场采集好、37 场被试运动/采集差，也不得等同 physiology validity。
- 下一硬 Gate 已正式分配为 `docs/research/MMWAVE_PIPELINE_SCIENTIFIC_AUDIT_TASK_2026-08-29.md`：先恢复并绑定既有 RS6240 firmware/manual/SDK 证据，再逐行审 producer/downstream；禁止从零重复 discovery。
- 当前 `PIPELINE_SCIENTIFIC_AUDIT=PASS` 仅表示证据恢复与源级审计完成；正式镜像模式、37 mm range 轴、0xC2 DataCube 传输和下游 HR/BR/HRV/QC 边界已完成静态闭合；lower-layer 校准/窗口、Tx/Rx 时序/补偿和 target continuity 仍未闭合。机器生成的部署回执仍缺失，但正式固件身份本身已确认。未授权新算法、C2B/C2C 重跑、NIR/RGB producer 修改或原始数据修改。
- 本轮审计文件：`docs/research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`、`docs/research/MMWAVE_LITERATURE_VS_PROJECT_STAGE_MATRIX_2026-08-29.csv`、`docs/research/MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`、`docs/research/MMWAVE_PIPELINE_FLOWCHART_2026-08-29.md`。

## 2026-08-29 local↔canonical reconciliation gate — PASS

- 已完成本地与 canonical 的 43 条分析视图对账：30 条 MATCHED、2 条 SUPERSEDED、
  6 条 PRODUCER_OWNED、3 条 PLANNED_NOT_EXECUTED、2 条 PRODUCER_NOT_READY；
  PATH_STALE、RESULT_MISMATCH、TRUE_MISSING、LOCAL_ONLY、REMOTE_ONLY 均为 0。
- C2C 历史结果不作为当前结论，待 canonical rerun；NIR/RGB increment 尚不是 global final。
- 该 PASS 仅表示本地与 canonical 的已完成证据对账通过，不代表未来计划分析已完成。

## 2026-08-29 Issue #15 mmWave physiology/QC closure — CLOSED_WITH_EXPLICIT_BOUNDARIES

- HR：`PASS_QUALITY_GATED`；corrected BIOPAC calibration MAE=3.777 bpm，仅支持质量门控候选和 #16 sensitivity。
- BR：`PASS_SUPPORTING`；corrected spectral calibration MAE=3.328 breaths/min，仅支持辅助/敏感性分析。
- HRV：`BLOCKED`；现有 beat/IBI 与 ECG 闭环不足，C1D 保持 `NO_MATERIAL_IMPROVEMENT_STOP_HRV`。
- corrected QC：Tier1=33、Tier2=37、Tier3=2（067/099）；Tier1 不等于 ground-truth validated。
- #16 仅允许一次预定义 quality-stratified sensitivity；不重跑 C2B/C2C，不启动新算法路线。

## 2026-08-29 local analysis assimilation status — PARTIAL

- 已把旧 dirty 工作树中可确认的中央本地独有分析入口、QC/merge-readiness/RGB
  状态报告和小型 provenance 文件收编到现有 canonical 路径；没有重新运行科学分析。
- 57 个旧路径删除均已与 `scripts/legacy/`、`scripts/maintenance/` 或既有维护路径完成
  内容级迁移证明；历史脚本不计 active analysis。
- C1c/C1d 仍为 `VALIDATION_STOPPED`；HR、BR、HRV 仍受 QC/reference/逐搏验证边界约束。
- RGB/NIR worktree 仍由 producer repo 所有；RGB 仅 raw/context merge-ready，NIR 仅工程审计边界。
- 大型矩阵、波形、逐帧输出和 PNG 保留在本地 `11_数据\derived` 或 producer worktree，Git
  仅收报告、摘要、manifest、schema 和生成脚本。
- 旧分支仍含 78 个 tracked modified、40 个 untracked 及 unresolved 项，尚未具备退休条件。

收编逐项链路见 `docs/repository/LOCAL_ANALYSIS_ASSIMILATION_2026-08-29.md`，结果索引见
`docs/canonical/RESULT_INDEX_V1.md`。

## 2026-08-29 unresolved closure

已关闭上一阶段 22 个 unresolved 处理单元：5 个 `KEEP_IN_MAIN`、5 个
`PRODUCER_REPO_OWNED`、1 个 `SUPERSEDED`、4 个 `HISTORICAL`、7 个
`GENERATED_ONLY`；`SAFE_TO_REMOVE` 和 `BLOCKED_BY_RUNNING_TASK` 均为 0，
剩余 `UNRESOLVED` 为 0。这里是归类关闭，不是删除授权；旧 dirty 分支和
producer worktree 仍然保留。

## 2026-08-26 Stage 2C governance status

- `main` 是正式默认分支，repository 已更名为 `greenboo26/focuswave-multimodal-attention-analysis`。
- Stage 2C 文件树收口仅整理 Git-safe 的入口、contract、方法、provenance 和聚合结果；未开始新的科学分析，未修改科学结果。
- NVIDIA ref 固定为 `36a2d596c55b93071a8b5c80459a56c876c06351`，AMD ref 固定为 `d8e721079461ef7f71fafcd3edf819858fabbb16`。
- NIR 69/72 fullclass 状态不变；68 sessions/44 participants/1,360 probes 仍是 pre-recovery 边界；sub-100/sub-178 等待 full recovery/QC/Probe alignment；sub-099 仍为 `master_timeline` blocker。
- RGB 保持 `PIPELINE_ENGINEERING_PENDING / FORMAL_ANALYSIS_NOT_AUTHORIZED`；mmWave HRV 保持 validation boundary/ablation，不重新成为近端主线。
- 旧 `master` 与 `legacy/mmwave-hrv-master-pre-focuswave-20260826` 保留为 rollback surface。

## 2026-08-26 canonicalization status

项目显示名称：`FocusWave Multimodal Attention Analysis`。已在本地完成代码、derived、formal NIR/RGB、J 盘 discovery、环境和 worktree 事实审计。Registry 共 29 项：14 `VALID_SUPPORTING`、3 `PENDING_CANONICAL_RERUN`、1 `BLOCKED_EXTERNAL_STORAGE`、6 `ENGINEERING_ONLY`、5 `PLANNED_GLOBAL_ONLY`，0 `CANONICAL_FINAL`。下一步仅为 GPT-5.6 Sol 独立科研方法审查；AMD 分支和新批量分析均未开始。

更新时间：2026-08-25

## 当前正式管线

- ECG 正式管线保持不变。
- `v3.1.1` 仅用于独立验证，暂不替代正式主链。
- 毫米波目标锁定验证先于 HR、BR、HRV；全场合理距离峰不是充分质量条件。
- 尚未宣称毫米波 HR、BR 或 HRV 已经准确。

## J 盘目标锁定审计

- 26 个全场距离初筛候选已完成首/中/末分片审计，共 78 条记录。
- 目前重点场次为 `sub-078` 和 `sub-091`。
- 两场首、中、末分片均观察到 8 通道围绕共同近距离功率峰聚集。
- 四个中/末分片通过当前探索性 RGB 运动门控，可作为 HR/BR 复核候选。
- `sub-078-first` 与 `sub-091-first` 被探索性运动门标记，需先复核视频边界效应，不能直接剔除。
- `sub-074`、`sub-107`、`sub-129`、`sub-134` 保留为目标漂移负例。

## 当前下一步

1. 保持本轮 `docs/research/` 审计证据、矩阵、缺口/决策与流程图为 canonical 入口。
2. 对真正仍未闭合的 upstream 项逐项确认：DC/clutter、window、FFT length/zero padding、chirp aggregation/Doppler、normalization、channel calibration、8 通道物理映射、upstream phase correction。
3. 若另行授权 #16，只能使用已冻结输入契约、corrected 0.037 m/bin 口径和本轮记录的 HR/BR/HRV/QC 边界。
4. 不得用 33/37 直接推断 participant compliance 或 acquisition quality；不得将本轮 PASS 解读为 physiology validity。

## 证据边界

允许使用：`human-target-lock candidate`、`strong spatial consistency evidence`、`ReportDataCube1D is complex range-domain 8-channel data`、`Range FFT already occurred upstream`、`formal range spacing = 0.037 m/bin`。

暂不使用：`chest lock confirmed`、`HR accurate`、`BR accurate`、`HRV accurate`、`generic SDK behavior == exact formal firmware behavior`。

## 本地结果位置

完整被试数据和派生结果不进入本仓库，保留在本地：

`D:\Project\厚粲杯\11_数据\derived\j_mmwave_target_lock_audit_v1\`

## 2026-08-29 formal mmWave pipeline scientific audit — PASS / #16 PAUSED

- Recovered and relinked the prior RS6240 firmware/manual/SDK audit to the exact formal image: SHA-256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`, 233,280 bytes, build string `2026-07-24 21:33:39`.
- Confirmed formal stored output as eight-channel complex range-domain data with 256 bins and 0.037 m/bin; runtime-mode evidence supports range FFT without an added Doppler FFT for the 1D formal path.
- Kept DC/static clutter, window, FFT padding/cropping, chirp aggregation, normalization, physical channel mapping/calibration, and upstream phase correction explicitly unresolved where exact formal binding is absent. Generic SDK defaults are not promoted to formal behavior.
- Completed the line-by-line producer/downstream audit, literature-vs-project stage matrix, gaps/decisions report, and source-controlled Mermaid flowchart under `docs/research/`.
- Interpretation remains bounded: target lock is a mixed heuristic, standard formal execution does not activate the optional scalar RSP harmonic check, HRV is not ECG R-peak aligned, and corrected `33/37/2` tiers are current-pipeline QC eligibility strata rather than acquisition-quality, participant-compliance, or physiology-validity labels.
- This was a read-only scientific audit. No model run, C2B/C2C rerun, target-lock rerun, raw-data change, NIR/RGB change, or Issue #16 execution occurred. Issue #16 remains paused.

