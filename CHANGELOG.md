# 修改说明

## 2026-08-30 — audit(mmwave): close reusable beat-level validation gate without HRV promotion

- Reused existing full-record v3.1.1 `heart_peaks` and `heartbeat` NPZ outputs; no new radar beat detector, selector, gate, producer, raw-data, or BR algorithm change.
- Added the narrow beat-level validation adapter, aggregate summary, tolerance sensitivity, manifest, and project code map. Eight complete blocks were evaluated with deterministic 60 s windows and existing ECG block-affine alignment.
- At ±75 ms, pooled radar-to-ECG beat sensitivity/precision were `0.170243/0.210619` (`119/699` ECG R-peaks, `565` radar peaks); at ±150 ms they remained `0.359084/0.444248`. No formal RMSSD/SDNN/LF-HF was calculated.
- HRV remains `BLOCKED`; HR/BR remain `HOLD`; #25 remains `WAIT_ON_SELECTOR_VALIDITY`.

## 2026-08-30 — audit(mmwave): complete historical producer lineage and fixed-contract stage audit

- Reused the existing timestamp-only coverage contract (`COMPLETE=333`, `SEVERELY_INCOMPLETE=2`) and existing selector, target-ablation, estimator-lineage and ECG oracle outputs; excluded w027/w028 from the controlled `COMPLETE ∩ ECG_VALID` n=`323` set without padding/backfill/reconstruction.
- Added the step-by-step pipeline map, 13-stage evidence table, controlled MAE/median AE/bias/RMSE/correlation metrics, paired deltas, failure-locus summary, and explicit KEEP / RESTORE_EXISTING / UNPROVEN / DROP decisions.
- Confirmed the historical `3.7772146 bpm` lineage and that audited historical/current/targeted paths have no proven pre-selection DC/static/clutter suppression; no producer, raw, target, ECG, or estimator algorithm was changed. #25 remains `WAIT_ON_SELECTOR_VALIDITY`.

## 2026-08-30 — audit(mmwave): classify Issue #28 acquisition tail coverage

- Added the bounded Issue #28 acquisition-tail audit, reusing the existing DLL-time coverage contract, historical manifest, and FocusWave `ecg` lifecycle source.
- Classified `97795/block4` as a historical irrecoverable tail (`24,809 ms` marker-to-last-DLL gap; w027/w028 end gaps `9,536/19,536 ms`); continuity findings for `97796/97994` remain unresolved and are not generalized.
- No padding, backfill, synthetic frame, producer, raw, firmware, portable-V2, or #24–#27 denominator change was made. Evidence is under `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_ACQUISITION_TAIL_AUDIT_*`.

## 2026-08-30 — audit(mmwave): complete ECG reference eligibility for DLL-time windows

### 改动

- Added `scripts/maintenance/run_ecg_eligibility_dll_windows_20260830.py`, reusing the historical ECG gold-standard cleaner, block-marker affine mapping, and fixed ARM0/ARM1/ARM2 rows.
- Added aggregate ECG eligibility reasons, per-block eligibility counts, ECG_VALID denominator ARM metrics, a manifest, and a report under `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`. Per-window reject reasons remain local-only under `work/`.

### 验证与边界

- 335 DLL-time windows: `ECG_VALID=325`, `ECG_INVALID=10`, `UNRESOLVED=0`; all 10 primary invalid reasons are abnormal adjacent IBI fluctuation >20%. Marker mismatch is a separate warning field.
- ECG_VALID ARM0/ARM1/ARM2 MAE: `25.005/21.906332/18.904008` bpm with valid n `325/304/325`; all-window values remain diagnostic only.
- HR remains `HOLD`, HRV remains `BLOCKED`; no estimator, target, gate, producer, raw, firmware, portable V2, #16, C2B/C2C, or HRV change occurred.

## 2026-08-30 — audit(mmwave): controlled 20 s versus historical 60 s window comparison

### 改动

- Added `scripts/maintenance/run_mmwave_window_length_comparison_20260830.py` with the fixed historical target, DLL-time endpoint grid, 20 s/trailing 60 s windows, and unchanged v3.1.1 estimator chain.
- Reused #24 ECG eligibility from commit `d2d09f8ac502600d3a1241e33c429bd53756fa45` and `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_ELIGIBILITY_MANIFEST.json`; both durations apply the same independent ECG adapter and only the 283 paired-valid endpoints enter MAE/correlation metrics.
- Added five Git-safe aggregate/report artifacts under `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`; no raw, row-level, producer, firmware, portable-V2, C2B/C2C, HRV or full-batch changes.

### 结果与边界

- RUN_ID=`issue25_window_length_20260830`; 303 endpoints / 8 blocks; 20 s MAE=`14.703129` bpm and 60 s MAE=`5.608574` bpm; nominal resolution=`3 bpm` versus `1 bpm`.
- Status is `PARTIAL / DIAGNOSTIC_ONLY`; formal window validity remains `UNRESOLVED`. `REUSE_REJECTION_REASON` is recorded in the report and manifest because the prior same-window audit could not construct a paired 60 s DLL-time/ECG_VALID comparison.

## 2026-08-30 — audit(mmwave): complete Issue #26 distance-error evidence package

- Reused `selected_bin × 0.037 m`, B2 extreme-range evidence, and early 5-participant/99-window ECG/RSP paired outputs; added only a downstream aggregate audit and did not change target, estimator, QC, producer, raw or firmware.
- RUN_ID=`MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_20260829T220501Z`; formal distance bands=`4/12/32/5/18`; early HR N=99 MAE=`3.777215` bpm and BR N=99 MAE=`3.327631` breaths/min remain descriptive reference evidence. Historical `0.30–1.50 m` remains `HISTORICAL_GATE_SENSITIVITY`.
- B2 near-side bright structure is `OBSERVED`; direct-leakage and fixed-reflection labels remain zero without being interpreted as proof of absence. Current physical gate and near-field cause remain `UNRESOLVED`; no exclusion gate is authorized. Evidence is under `docs/results/2026-08-30_MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE/`.

## 2026-08-30 — audit(mmwave): add ECG_VALID retrospective spectral truth audit

- Added the downstream Issue #27 audit script and Git-safe aggregate evidence under `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`, reusing frozen 335-window target/peak/ARM outputs and #24 ECG eligibility as an oracle.
- Separate layers remain explicit: all-window diagnostic/supporting=`335`; #24 ECG_VALID primary=`325`; ECG_INVALID=`10`; UNRESOLVED=`0`; primary truth classes are nearby=`182`, wrong-selection=`102`, selected-ECG-bin=`22`, absent/weak=`17`, coverage/reference=`2`.
- Internal harmonic guard was not applied in the fixed targeted path; external RSP A/B remains diagnostic only. Status is `PARTIAL / SUPPORTING_ONLY`; HR remains `HOLD` and HRV `BLOCKED`; no producer/raw/firmware/portable-V2 or C2B/C2C change.

## 2026-08-30 — audit(mmwave): repair authoritative DLL frame-time semantics and rerun bounded HR sensitivity

### 改动

- Added the frozen `MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md`, mapping audit generator, DLL-time window reconstruction, and unchanged-estimator HR sensitivity generator.
- Added Git-safe DLL-time windows, reconstruction report/manifest, HR old-vs-new comparison/metrics, and reports under `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`. The row-level frame mapping remains local-only.
- Recorded the acquisition-source limitation: FocusWave writes `receive_data.timeStamp` as the DLL DateTime converted to Unix ms; its underlying device/firmware/SDK/host origin is not documented by the source.

### 验证与边界

- Mapping passed for `97793`, `9779`, and `97795`: timestamp rows equal NPZ frames, frame indices are contiguous, channel lengths are consistent, and DLL timestamps are monotonic.
- Window equivalence: 25 exact / 156 partial / 154 obvious; 310/335 memberships changed. `97795/block4` has a 24,809 ms program-end-to-last-DLL coverage tail and one 46-frame guarded window; no backfill or padding was applied.
- Unchanged ARM0/ARM1/ARM2 HR sensitivity completed. HR/BR remain `HOLD`, HRV remains `BLOCKED`, Issue #16 remains `PAUSED`; no producer, target, gate, ECG, portable V2, raw, firmware, C2B/C2C, HRV-new-algorithm, or full-batch change occurred.

## 2026-08-30 — audit(mmwave): freeze DLL-time coverage contract and denominator sensitivity

### 改动

- Added `MMWAVE_DLL_WINDOW_COVERAGE_AUDIT.csv` and its report/manifest with subject-block local DLL rate, expected frame count, boundary/internal gaps, and frozen `COMPLETE`/`PARTIAL`/`SEVERELY_INCOMPLETE` classes.
- Added pre-registered S0 all-window, S1 exclude-severe, and S2 complete-only sensitivity outputs, per-block remaining-n table, report, manifest, and reproducible maintenance scripts.

### 验证与边界

- Coverage classes are timestamp-only and were frozen before reading HR sensitivity: 333 complete, 0 partial, 2 severe out of 335 windows. Severe windows are localized to `97795/block4/w027` and `w028`.
- S0→S2 MAE changes were ARM0 `+0.021128`, ARM1 `-0.061349`, and ARM2 `+0.036120` bpm; complete-window HR remains high-error. This is a validity sensitivity, not an algorithm improvement.
- The all-window DLL-time primary result remains intact. HR/BR stay `HOLD`, HRV `BLOCKED`, Issue #16 `PAUSED`; no estimator, target, gate, filter, ECG, producer, raw, firmware, portable V2, C2B/C2C, or full-batch change occurred.

## 2026-08-30 — audit(multimodal): freeze formal model-ready cohort and LOSO contract

### 改动

- Added the Git-safe formal model-ready v1 package under `docs/results/2026-08-30_FORMAL_MODEL_READY_V1/`.
- Froze the observation-defined 1,295-probe / 65-session / 46-repeat-participant cohort and 46-fold participant-disjoint LOSO registry from the 1,440-probe canonical timeline.
- Added explicit NIR/RGB missingness and QC semantics, Behavior temporal leakage audit, modality feature contracts, model-ready schema, readiness gate, and a parameterized generation script.

### 验证与边界

- Readiness gate: `PASS_MODEL_READY`; all participant/session/probe leakage checks passed and source hashes are recorded.
- Primary predictor counts are Behavior=5, NIR=4, RGB=6. Blink remains provisional and excluded; PERCLOS and mmWave HOLD/EXCLUDE fields are excluded.
- No NIR/RGB producer rerun and no model training occurred. Probe-level audits, expanded folds, and candidate table remain local-only.

## 2026-08-30 — audit(multimodal): attach current mother table and freeze probe merge contract

### 改动

- Reused the current 179-session / 112-repeat mother table and explicit 72-session J mapping evidence; generated a current 1,440-probe formal timeline with frozen `pre_30s` semantics.
- Recorded local-only behavior/NIR/RGB merge-ready tables, coverage/missingness, source-output schema/QC index, and a 1,295-row fully matched candidate. Existing NIR/RGB producers were not rerun and no model was trained.
- Added the Git-safe aggregate evidence package under `docs/results/2026-08-30_FORMAL_MULTIMODAL_ATTACH/`.

### 验证与边界

- Portable V2 validator at pinned commit `21c7da4fe2e03d853f0b6391d580334526f86ce3` passed the five-column probe key for Behavior/NIR/RGB; both outer and inner merges returned 1,440 rows.
- Overall status remains `PARTIAL`: NIR observed 1,295/1,440 probe rows, RGB observed 1,420/1,440; missing rows remain explicit. No raw/large producer artifact or row-level table was uploaded.

## 2026-08-30 — audit(mmwave): execute ordered next gate; keep #16 paused

### 改动

- 按最新 canonical prompt 顺序补齐 RS6240 设备/固件工程残余证据，并新增逐项状态矩阵 `docs/research/MMWAVE_DEVICE_FIRMWARE_ENGINEERING_EVIDENCE_2026-08-30.csv`。
- 审计既有 formal JSON/NPZ 的 target/bin/channel 持久化边界；确认缺少跨 window continuity history，写入最小 instrumentation/rerun contract，未启动 formal batch。
- 复核 formal runner 到 `respiration_harmonic_reject()` 的调用链；确认标准 formal runner 未传 `acq_path/ext_br_bpm`，external RSP harmonic rejection 未 active。
- 定位 HRV 最早 blocker 为同步 radar beat 与 ECG R peak 的逐搏匹配及 paired IBI agreement 缺失。

### 边界

- Overall `PARTIAL`；无模型、#16、C2B/C2C、target-lock rerun、设备烧录、原始数据、NIR/RGB 变更；#16 继续 `PAUSED`。
- 已闭合的 Range FFT / 37 mm / 8-channel discovery 保持原结论，不在本轮重复重开。

## 2026-08-29 — audit(mmwave): complete formal pipeline scientific audit

### 改动

- 恢复此前 RS6240 formal firmware/manual/SDK 审计，并绑定精确 firmware image、SHA-256、运行模式与 `ReportDataCube1D` 输出语义；确认正式距离语义为 0.037 m/bin、八通道复数 range-domain、1D 路径无新增 Doppler FFT。
- 完成 `ReportDataCube1D → target/bin/channel → phase → filter → harmonic → HR/BR/HRV/QC` 的逐文件逐逻辑块审计、文献对照矩阵、缺口/决策报告和 Mermaid 流程图。
- 明确 target selection、harmonic suppression、HRV ECG 对齐和 `33/37/2` 的科学边界；未将 generic SDK 默认值升级为 formal 行为。

### 边界

- 未运行新模型、#16、C2B/C2C、target-lock rerun，未修改原始数据、NIR/RGB 或科学代码；#16 保持 `PAUSED`。
- 本次 `PASS` 仅表示证据恢复与管线审计完成，不表示 HR/BR/HRV、participant compliance 或 acquisition quality 已验证。

## 2026-08-29 — analysis(mmwave): close Issue #15 physiology and QC qualification

### 改动

- 复用既有 formal QC、corrected 37 mm、BIOPAC ECG/RSP、B1/B2 和 067/099 provenance，
  关闭 #15 qualification；未重跑科学分析。
- HR 定为 `PASS_QUALITY_GATED`（corrected MAE=3.777 bpm），BR 定为
  `PASS_SUPPORTING`（corrected spectral MAE=3.328 breaths/min），HRV 保持 `BLOCKED`。
- 冻结 corrected QC tiers：Tier1=33、Tier2=37、Tier3=2；Tier1 仅为 QC-eligible candidate。
- 建立 #16 单次 quality-stratified sensitivity 输入契约，明确 70-session/1,400-probe
  分母、Tier1/Tier2 strata 和 067/099 exclusion。

### 边界

- 不启动新算法海选、C2B/C2C、AoA/beamforming、VMD grid、HRV 或 NIR/RGB 任务；不修改原始数据。
- 脚本、输入、输出、manifest、GitHub report 和结论变化记录见
  `docs/results/mmwave_formal_vital_qc_v1/MMWAVE_FORMAL_VITAL_QC_V1_CLOSURE_2026-08-29.md`。

## 2026-08-29 — audit(analysis): close local↔canonical reconciliation gate

### 改动

- 定向收口 P0 protocol、C2C、Context、D1、NIR/RGB increment、multimodal fusion 和 cross-site；
- 将已有 Context baseline 恢复为 MATCHED，将 C2C 历史结果标记 SUPERSEDED；
- 将未来任务分为 `PLANNED_NOT_EXECUTED` 与 `PRODUCER_NOT_READY`，不把未执行计划计为对账缺失；
- 对账结果：43 条视图中 30 条 MATCHED、TRUE_MISSING=0、PATH_STALE=0、RESULT_MISMATCH=0。

### 边界

- 未运行新科学分析、未启动 #15/#16/#17 或 final multimodal LOSO；未修改 NIR/RGB producer 或旧 dirty 工作树。

## 2026-08-29 — chore(analysis): close unresolved ownership classifications

### 改动

- 关闭 22 个 unresolved 处理单元：central 入口、历史归档、生成结果、
  NIR/RGB producer 资产和 superseded 结果均已明确归类；
- 确认 Issue12/NIR ladder 为 producer-side provenance，旧 Issue13/Q1
  label 冲突矩阵不进入 canonical scientific results；
- 结果索引和项目状态补充 closure 计数；没有新的科学运行或 central 结论。

### 边界

- 旧 dirty 分支、dirty clone/worktree 和 producer 代码均未删除、移动或覆盖；
- 大型矩阵、PNG、逐帧结果保持本地；后续工作回到正式科学分析主线。

## 2026-08-29 — merge(analysis): assimilate local unique evidence into canonical main

### 背景

旧 questionnaire 分支包含现行 mmWave pilot/QC/readiness 证据、研究文档、维护入口和历史
脚本，但不能把 62 个 ahead commit 直接 cherry-pick，也不能把 NIR/RGB producer worktree
跨仓库合并。需要把真实有价值的中央资产逐项收编并保留 provenance。

### 改动

- 收编 C1c/C1d、C2a/C2b supporting entrypoints，formal QC、HR course、B1/B2、range-gate
  和 merge-readiness 维护入口；
- 收编 questionnaire evidence generator，并修正旧结果中 label 3/label 4 的语义冲突；
- 收编 66 个历史脚本到既有 `scripts/legacy/`，57/57 个 tracked deletion 有内容级迁移证明；
- 收编 C1 pilot、formal QC、merge readiness、RGB raw/context 和 frontend transparency 的
  小型报告/CSV/manifest；大型矩阵、波形、逐帧输出和 PNG 保留本地；
- 更新 result index、registry 说明、canonical script README、PROJECT_STATUS 和本文件。

### 验证与边界

- 新增 Python 入口已通过轻量编译检查；PowerShell 入口已通过解析检查；未重新运行科学分析；
- NIR/RGB producer worktree、Issue12 NIR ladder 和旧 Q1/Issue13 错误标签结果未跨仓库合入；
- 旧 dirty 工作树仍保留，旧分支暂不能退休；完整逐项映射见
  `docs/repository/LOCAL_ANALYSIS_ASSIMILATION_2026-08-29.md`。

## 2026-08-29 — chore: enforce existing workspace traceability entry

### 背景

跨仓库工作曾把临时 worktree、结果位置和本机项目管理文件留在聊天或未登记目录中，下一次任务难以区分 canonical 入口、临时副本和历史快照。

### 改动

- 在根级 `AGENTS.md` 明确先读既有项目/目录规范，不新造平行状态、平行 `output/` 或临时 Git 仓库；
- 强制实质进展同步到既有历史账本、当前进度、脚本/结果索引、manifest/provenance、CHANGELOG 和 handoff；
- 强制提交说明包含修改、脚本/入口、结果位置、tracked/local-only 边界、验证、决策/阶段变化和下一步；
- 明确 Git worktree、临时 clone、运行态、原始数据和大型输出的清理边界。

### 验证与边界

- 本次只改入口纪律文档，未运行科学分析，未改变 label/window/fold/seed/model/QC 或科学结果；
- 脚本/生成结果：N/A；验证为 `git diff --check`、入口文本读取和 staged-path 检查；
- 本地 `D:\Project\厚粲杯\08_算法` 的未提交用户内容不在本次提交范围内。

> 格式参照 FocusWave（F:/FocusWave_1.3.6/04-docs/CHANGELOG.md）：每条 = 日期 + v版本 主题，结构 = 背景 / 改动 / 验证 / 涉及文件。
> 2026-08-10 起本文件同时承担原 `docs/版本说明.md` 的版本演进记录（已合并，版本说明.md 删除）。
> 版本号对应 `git tag v{版本}`（提交规范见 `docs/规范备忘.md`）。

---

## 2026-08-25 — audit(mmwave): J 盘目标锁定与 RGB 门控状态同步

### 背景

J 盘全场距离候选不足以证明毫米波持续锁定人体，需要把时间稳定性、8 通道空间一致性和 RGB 运动门控纳入跨会话可恢复状态。

### 改动

- 新增 `PROJECT_STATUS.md` 和 `.harness/analysis-state.json`，记录正式/验证管线边界、当前候选分片、负例和下一步。
- 新增 `docs/methodology/target_lock_audit.md`、`docs/methodology/rgb_motion_gate.md` 和对应决策记录。
- 新增参数化 RGB 运动门控与双门控合并脚本，输入通过命令行提供，不写死本地数据目录。
- 实际被试数据、视频、逐帧结果和大体量派生结果继续保留在本地 `11_数据\\derived`，不进入仓库。

### 验证

- 本地已完成 sub-078/sub-091 的首、中、末分片空间一致性和 RGB 探索性门控审计。
- 本次提交只包含方法、状态、决策和通用脚本，不包含原始数据或被试级派生数据。

---

## 2026-08-24 — v1.8 算法库结构整理、金标准资产归档与模型共享

### 背景

算法库根目录混合了项目说明、审计数据、NIR 工程、模型权重和运行环境，导致主线入口与可共享资产难以区分。此次整理以不移动原始数据、保留 NIR 独立 Git 历史、让同事可从 GitHub 获取模型为约束。

### 改动

- 根目录只保留仓库入口文件；项目管理说明、系统说明、运维日志、审计数据和审计脚本分别归档到 `docs/`、`data/` 和 `scripts/审计/`。
- 从 `11_数据` 移入算法库的小型派生质量表归档到 `data/质量/`；原始采集数据保持原位置不动。
- 新增 `docs/项目管理/算法库整理索引.md` 和 `外部工程版本.md`，登记主线入口、NIR 工程版本、路径边界和共享规则。
- 新增 `models/` 统一共享 NIR、RITnet、人脸检测和 DeepVOG 权重；通过 Git LFS 管理 `.h5`、`.onnx` 和 `.pt` 文件。
- 修正根目录文件移动后的脚本路径和系统说明链接。

### 验证

- 当前主线 `scripts/` 在排除 `archive_历史版本` 后 Python 编译通过。
- `scripts/审计/build_mmwave_audit.mjs` Node 语法检查通过。
- Git 工作区差异检查通过；历史归档中的 `process_vital_signs_v2_0.py` 仍有既存语法错误，未纳入当前主线。

### 版本边界

两个 NIR 工程保留独立仓库和本地未提交改动，不在本次主库提交中覆盖；主库通过版本登记和 `models/` 共享权重提供统一入口。

---

## 2026-08-14 — v1.7 问卷×行为×主程序三方对照 + 外部金标准数据集验证

### 背景

预实验答卷（7 人）需与 J 盘行为数据（11 人）及 FocusWave 主程序实现三方对照，找出
主观报告与客观数据的偏差来源；同时引入两个外部公开数据集（phish-tech TI 原始 ADC、
Zenodo 60GHz AgeBalanced 110 人 ECG 金标准）验证处理链路的跨设备可用性与金标准精度，
补上"HRV 验证必须 ECG"的缺口。

### 改动

- **问卷合并与三方对照报告**：`scripts/merge_preexp_surveys_0813.py`（v3 版 3 人补编号
  001-003 与 v4 版 004-007 合并）、`docs/报告/预实验问卷深入分析_结合主程序_0813.md`
- **序列规律双重实锤**：formal_A/B/C 均为 18 试次 cycle 机械重复 ×12，no-go 间隔
  完全固定（A=4/5、B=9、C=18），B 条件柠檬后 100% 接苹果；7/7 被试自报发现规律
- **判定逻辑审计**：commission/omission 响应窗口含掩蔽期（1150ms），74% 的
  commission 是掩蔽期节奏性按键（掩蔽后段 32 次预按的下一试次 100% 是 GO）；
  修正口径（仅刺激期 rt≤250ms）后条件效应 A 9.8% > C 4.2% > B 2.4%，个体模式
  与问卷自述吻合（002 紧张/疲倦、005 干扰窗、007 最后一轮）
- **时间戳规范澄清**：CSV 第 2 列（DLL 固件时戳，间隔中位 10.0ms）用于帧内时间轴，
  第 3 列（Python 回调，抖动大）仅用于跨模态对齐；写入 `docs/决策/规范备忘.md`
- **生命体征逐步图**：`scripts/plot_vitalsign_pipeline_0813.py`（静态杂波去除 + 3D mesh +
  带内功率选门 + SOS 窄带滤波，支持 --mesh-only / --all）；修复 IIR 低频窄带
  滤波数值爆炸（b/a → SOS）与噪声门误选（幅度阈值排除）
- **外部金标准验证管线**：`scripts/validate_external_gold_0814.py`（25s 窗 5s 步长时频
  融合 + quality 门控 + 谐波判别 + 金标准对比）；`scripts/analyze_external_heartbeat_0814.py`
  （TI 原始 ADC 解析，10 文件全跑通）
- **三项 A/B（见优化决策记录实验 35）**：T 波剔除（金标准 R 峰 26% 误检修复）、
  HPS 谐波乘积谱（2 倍锁定 32→4，保留）、时间轨迹连续性（保留）、呼吸谐波
  固定陷波（净负收益回退，v9 模拟验证的边界条件补全）

### 验证

- 外部金标准（220 会话）：总体 MAE 中位 9.5 BPM，quality 分层有效（high 1.6 /
  med 3.4 / low 10.1 BPM），2 倍锁定 4/1188 窗、半频锁定 0
- 跨设备：phish-tech TI 原始 ADC（4MHz/20Hz 快慢时间，与 POSSUMIC 完全不同格式）
  直接跑通，10 文件输出生理合理范围
- 行为数据：11 人时间轴与问卷提交时间交叉验证全部吻合（含双设备并行实验发现）

### 涉及文件

- `scripts/merge_preexp_surveys_0813.py`、`scripts/analyze_preexp_behavior_0813.py`（J 盘 11 人）
- `scripts/plot_vitalsign_pipeline_0813.py`、`scripts/validate_external_gold_0814.py`、
  `scripts/analyze_external_heartbeat_0814.py`
- `docs/报告/预实验问卷深入分析_结合主程序_0813.md`
- `docs/决策/规范备忘.md`（时间戳规范）、`docs/决策/优化决策记录.md`（实验 35）
- 数据：`11_数据/外部数据集_AgeBalanced_60GHz/`（110 人）、
  `11_数据/外部数据集_mmWave_Heartbeat/`（TI gby 批次）
- 一敏 v3.1 结果归档（心率时序改进，25s 窗 5s 步长时频融合 + 2:1 谐波修正 +
  quality 门控；raw/replay 双跑可复现）：
  - `output/旧实验/08_旧批次-DEEP-BREATH/v3_1/`（raw + replay）
  - `output/旧实验/08_旧批次-REST-3min/v3_1/`（raw + replay）
  - `output/旧实验/08_旧批次-SXQ-47min/v3_1/`（raw + replay）
  - 报告：`docs/报告/v3.1心率时序改进与验证报告.md`
  - 验证：rest_3min 100% 高质量窗（HR 91.7±1.7）；sxq/deep-breath 约 52% 高质量窗，
    使用需按 `quality != low` 筛选；HRV 需另行建立带质量门控的 NN 间期序列

---

## 2026-08-11 — v1.6 自主优化夜（31 项实验 + 摄像头-毫米波融合门控）

### 背景

用户要求睡眠期间自主尝试文献/仓库中的优化方法（NeuroKit 分析思路 +
mmHRV/倪杰2024/Radar_monitor 等来源），并利用摄像头数据融合。

### 改动

- **外部方法 A/B（7 项, 全无实质改进）**: SPC 定位（+1.8%, 保留 --use-spc 开关）、
  Hampel IBI 清洗（误伤 RSA 撤销）、相位差分/CFAR/SSA/包络归一化/CEEMDAN（不采用）
- **摄像头-毫米波融合（核心发现）**: NIR/RGB 1Hz 运动量 × 毫米波质量门
  **6/6 被试全显著**（000/003/004/005/006/007, d 中位 -0.90）; AUC 0.69,
  P90 阈值标记伪影精确率 76%; 工具 `motion_gate.py`; 方案
  `docs/摄像头毫米波融合门控方案.md`; 边界: 极弱信号（001 型）不适用
- **融合应用**: 006 错误窗 BR 升高通过运动量控制（非伪影）; 运动窗 HRV 虚高
  （RMSSD +55%）防护; 运动量门后事件相关更保守可信
- **行为机制**: 探针前后行为无一致变化（Wiemers2019 一致）; 错误后 RT 个体差异
  （005 冲动型 vs 007 警觉型）; RT 规律学习加速（007 313→177ms）
- **答卷分析**: 自报（睡眠/不适/专注力）与客观指标全面脱节
- **文献库**: Zotero 334 条中精读 7 篇（Corcoran2025/Martínez-Pérez2023/mmHRV/
  Cui2025/Gao2025/Joshi2025/Paterniani2023）——确认现有管线覆盖主流方法
- **正式实验设计建议**: docs/正式实验设计建议.md（刺激序列/探针/采集/管线/样本量）

### 验证

- 融合门控: 6/6 被试 p<0.05（000 p<0.001 d=-1.12; 005 p<0.001 d=-1.19 最强）,
  时间级趋势耦合（003 运动量↑质量↓同步）, 001 反向为时间混淆
- 外部方法: 预实验质量门口径下无改进——现有管线（门控+相位判别+谐波陷波+
  VMD+窄带逐拍+质量门）环节已覆盖

### 涉及文件

- `scripts/experiment_{spc,hampel,phasediff,cfar,ssa,envelope,ceemdan}.py`（7 项 A/B）
- `scripts/experiment_video_motion.py`、`scripts/experiment_video_roi.py`、`scripts/motion_gate.py`
- `scripts/analyze_survey_physio.py`、`scripts/analyze_probe_effect.py`
- `docs/优化决策记录.md`（31 项实验）、`docs/摄像头毫米波融合门控方案.md`、
  `docs/正式实验设计建议.md`、`docs/毫米波数据Q&A.md`（+5 篇文献笔记）

---

## 2026-08-11 — v1.5 分析框架扩展（NeuroKit 思路：事件相关 + 非线性 HRV + 标准化报告 + 特征矩阵）

### 背景

预实验探针标签偏斜（003/006 全"专注"）且被试对"刚才"的理解与探针前 30s 窗定义有出入，
仅靠探针窗分析信息量不足。参考 NeuroKit 的分析框架（预处理管线 → 事件相关 →
区间特征 → 统计建模），补上事件锚点、非线性特征、标准化预处理报告与统一特征矩阵。

### 改动

- **`analyze_erp_errors.py`（新增）**：行为错误事件相关分析。以 commission/omission
  为事件锚点（不依赖探针标签），事件映射到 30s 生理窗，对比错误窗 vs 非错误窗 +
  错误前/错误/错误后窗响应曲线。预实验事件池 183 commission + 252 omission，
  为探针的数十倍
- **`hrv_nonlinear.py`（新增）+ 窗特征扩展**：SampEn（样本熵）与 DFA（去趋势波动
  分析）α1/α2 写入全程窗与探针窗特征；`analyze_mmwave_hrv.py` 将 IBI 序列挂出
- **`gen_preexp_reports.py`（新增）**：标准化预处理报告（质量门 SNR/IBI + 全程窗
  可用率 + 生理/行为/探针汇总），对齐 NeuroKit pipeline 报告理念
- **`export_window_matrix.py`（新增）**：全被试可信窗特征矩阵
  （277 窗 × 18 特征 CSV），统一分析入口

### 验证（预实验 000-007）

- **错误窗呼吸率一致升高**：聚合 Cohen's d=+0.70（4/4 被试同向），
  003 d=0.77 p=0.011、006 d=1.32 p=0.0004 显著；错误后窗 RMSSD 回升
  （005: 18.0→24.3、007: 22.7→28.2）——"错误→唤醒→恢复"的事件相关模式
- SampEn 自测方向正确（正弦 0.105 vs 白噪声 1.892）；窗特征覆盖 275/277 窗
- 所有预实验被试（000-007）完成标准化预处理报告（004-007 质量可信，
  007 全程窗可用率 76.5% 最高）

### 注意

- 错误窗呼吸升高可能部分来自错误按键的动作伪影，细粒度分析需加正确按键窗对照
- SampEn 在部分高度规则窗返回 nan（缺失值处理）
- 探针标签偏斜问题未解决（003/006 仍全专注），探针分析仍受限于标签分布

### 涉及文件

- `scripts/analyze_erp_errors.py`、`scripts/hrv_nonlinear.py`（新增）
- `scripts/gen_preexp_reports.py`、`scripts/export_window_matrix.py`（新增）
- `scripts/analyze_mmwave_hrv.py`（IBI 挂出）、`scripts/analyze_mmwave_full.py`（非线性特征接入）
- `output/预实验/03_跨被试/09_预实验-事件相关/`、`09_预实验-预处理报告/`、`09_预实验-窗特征矩阵/`



| 版本 | 作者 | 日期 | 心跳方法 | 呼吸方法 | 结论 |
|:--:|------|------|------|------|------|
| v1 | 黄小轩 | 07-18 | 带通滤波 | 带通滤波 | 打通 pipeline |
| v2 | 黄小轩 | 07-23 | VMD (K=4) | 带通滤波 | HR 差距 30→5 BPM |
| v3 | 一敏 | 07-23 | VMD heart only | bp | ✅ 心跳三组全优于 bp |
| v4 | 一敏 | 07-23 | bp | VMD breath only | ❌ 两组退化 |
| v5 | 一敏 | 07-25 | vmd_heart | bp + 增强峰值 | ✅ 当前主线 |
| v6 | 一敏 | 07-25 | vmd_heart | 包络法 | ❌ 无稳定收益 |
| v7 | 一敏 | 07-25 | vmd_heart | 小波/时频 | ❌ 无稳定收益 |
| v8 | 一敏 | 07-25 | vmd_heart | EMD 变体 | ❌ 无稳定收益 |

脚本：`scripts/process_vital_signs_v1.py ~ v8.py`

> **分支关系说明**：v6/v7/v8 是 v5 主线（vmd_heart + bp + 稳健呼吸峰值）的**失败分支尝试**
> （分别实验包络法、小波/时频、EMD），效果均无稳定收益，未成为主线。
> 主线演进为 v1 → v2 → v3 → v5；分析架构（选 bin/门控/纠错）另立 `analyze_mmwave_hrv.py` v1.1→v1.4（见下方条目）。

### v5 实测结果（当前主线）

| 数据 | HR baseline→vmd_heart | BR | 判断 |
|------|------|------|------|
| v2_sart 29.8s | 76.9→65.3 BPM（频域 64.4） | 正常 | 最有代表性 |
| v3_tztest 9.8s | 84.4→76.5 BPM（频域 79.9） | 正常 | 较优样例 |
| v3_test 10.0s | 97.3→54.1 BPM（频域 48.0） | 失败 | 心跳改善，呼吸未收敛 |

HRV（仅供参考）：SDNN 49~173ms，RMSSD 40~223ms。

### SART-30s 全版本对比（最佳数据）

| 版本 | HR freq→time | 差距 | BR | 结论 |
|------|------|:--:|------|------|
| v1 bp | 64.4→76.9 | 12.5 | 14.1/18.0 | baseline |
| v3 vmd_heart | 64.4→**65.3** | 0.9 | 14.1/18.0 | 心跳大改善 |
| v5 vmd_heart | 64.4→**65.3** | 0.9 | 14.1/**15.0** | 心跳呼吸均最佳 |
| v7 vmd_heart | 66.8→69.8 | 3.0 | 17.8/15.0 | 反而不如 v5 |
| v8 vmd_heart | 64.4→65.3 | 0.9 | 14.1/15.0 | 与 v5 一致 |

结论：v5 仍是唯一一致优于 baseline 的版本，v7（小波）在最佳数据上表现更差。

## 数据对应（历史, 已归档可复现）

`output/` 按原始数据分组（v1~v8 历史输出已于 2026-08-10 整理时归档删除，对应脚本在 `scripts/archive_历史版本/`）：

| 输出目录（历史） | 原始数据 | 时长 | v1 | v2 | v3 | v4 | v5 | v6 |
|---------|---------|------|:--:|:--:|:--:|:--:|:--:|:--:|
| `01_DebugTool/` | DebugTool 导出 | 73.6s | ✓ | ✓ | | | | |
| `02_SART-30s/` | radar_collector data_v2 | 29.8s | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `03_TZTEST/` | radar_collector data_v3 fix | 9.8s | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `04_TEST-30s/` | radar_collector data_v3 test | 30s | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `05_SART-50min/` | radar_collector data_v3 SART | 50min | ✓ | ✓ | | | | |

> 当前 output/ 保留 07-10 系列（analyze_rest_3min / analyze_mmwave_hrv / analyze_mmwave_full / analyze_preexp_* / analyze_deep_breath / compare_4subjects 输出），命名见 `09_预实验-*` / `08_旧批次-*`。原始数据不随仓库分发。

## 后续改进方向

心跳 vmd_heart 已确认有效。当前瓶颈在呼吸——困难数据仍不稳定，HRV 未标准化。

---

## 2026-08-10 — v1.4 预实验全被试分析链（质量评估 + 稳健性检验 + 数据工具 + 目录规范）

### 背景

预实验新增 004-007 四被试。采集出现两类数据问题：005 被试编号被误输为 004；004 被试在实验结束后（Block6 停止后）离开座位但忘记停止采集，尾部约 5.5 分钟为无效数据。同时，000/003 的窗级相关此前出现"003 hr~RT 显著但 Spearman 不显著"的伪相关，需要统一的质量门与稳健性检验流程覆盖全被试。

### 改动

- **质量评估独立管线**：`assess_preexp_quality.py`（文献标准流程：距离功率谱定位 → 相位方差人体判别 → 呼吸谐波 iirnotch 陷波 → 心跳带 SNR/IBI 窗级门控；多候选 bin 应对近距杂波定位竞争），作为全程 HR/HRV 与探针窗分析的前置质量门
- **数据工具（新增）**：`truncate_preexp_data.py`（按行为实验结束或自定义时刻截断 mmwave 数据，npz/timestamps/bin/meta 全量同步，被截片入备份目录）；`rename_preexp_subject.py`（修正采集时编号输入错误，文件名/meta/CSV 全量）
- **004 数据修正**：按 Block6 停止时刻截断至 254837 帧（2574.4s），与行为实验完全对齐
- **005 数据修正**：全量重命名 + meta/CSV 内部字段修正
- **全被试分析**：004-007 质量评估、全程窗+探针特征（analyze_mmwave_full）、全 8 被试相关稳健性检验（analyze_preexp_robustness 扩展 SUBJECTS 全量）、跨被试 HR/HRV 分布对比（compare_preexp_hrv）、8 被试距离-时间热图（gen_range_time_maps 2×4）
- **目录规范**：output 重命名为 `09_预实验-*`（预实验批次）/ `08_旧批次-*`（8/1 旧批次 + 早期探索），消除 08/09 批次混淆；scripts 新增 README 索引（主线/工具/旧批次/基础模块/历史归档），归档过时脚本；01_管理 三文档同步新命名

### 验证

- 004-007 心跳质量全部"可信"（93%/99%/100%/100%，质量评估口径）；007 全程窗可用率最高（76%）
- 全 8 被试无跨被试一致、稳健显著的行为×生理相关；006 sdnn/rmssd~rt_mean Pearson 显著（p=0.018-0.025）但 Spearman 不显著（p=0.09-0.12），按判伪标准（Spearman 必须显著）判为边缘候选
- 个体差异（被试间 n=7）无显著，rmssd~RT 边缘相关由 001 杠杆点驱动（RMSSD 53 异常）
- 截断后重跑质量评估：末尾窗正常、static_target 窗消失、HR 伪影窗从 11 个降至 3 个（任务期内，保留）
- 脚本语法检查与 import 依赖验证通过（v2/v3/v5/v9 基础模块未被归档破坏）

### 实测结论（预实验 000-007）

| 被试 | 质量评估可信窗 | 全程窗可用率（v1.3 口径） | 备注 |
|------|--------------|--------------------------|------|
| 000 | 43% | 43% | 有信号 |
| 001 | — | 16% | 太弱 |
| 002 | — | 0% | 无信号 |
| 003 | 46% | 46% | hr~rt Pearson 显著但 Spearman 不显著（伪相关） |
| 004 | 93%（截断后 91%） | 31% | 已按行为结束截断 |
| 005 | 99% | 38% | 编号已修正 |
| 006 | 100% | 61% | sdnn/rmssd~rt Pearson 显著, Spearman 不显著（边缘候选） |
| 007 | 100% | 76% | 质量最好 |

**结论**: 全 8 被试无跨被试一致、稳健显著的行为×生理相关; 个体差异（n=7）
无显著（rmssd~RT 边缘相关由 001 杠杆点驱动）; 探针标签偏斜（003/006 几乎全"专注"）,
探针分组对比功效不足。预实验数据对"毫米波区分注意力状态"的验证能力有限, 待正式实验。

### 涉及文件

- `scripts/assess_preexp_quality.py`（新增）
- `scripts/truncate_preexp_data.py`、`scripts/rename_preexp_subject.py`（新增）
- `scripts/analyze_mmwave_full.py`、`scripts/analyze_mmwave_hrv.py`、`scripts/analyze_preexp_robustness.py`、`scripts/analyze_rest_3min.py`、`scripts/analyze_deep_breath.py`、`scripts/compare_4subjects.py`、`scripts/gen_range_time_maps.py`（目录路径同步）
- `scripts/README.md`（新增索引）、`scripts/archive_历史版本/`（+2 归档脚本）
- `output/`（目录规范重命名）、`01_管理/分析记录.md`、`01_管理/图表索引.md`、`01_管理/资源索引.md`
- `docs/版本说明.md`（并入本文件后删除）

---

## 2026-08-07 — v1.3 分析管线（analyze_mmwave_hrv.py, 综合管线）

### 背景

段级固定 bin 在部分窗信号差 → HR 假跳变；VMD 后主频漂移到倍频；单强反射场景（001）倍频锁错无冗余；环境反射误判心跳（008 曾选到 bin253=9.4m）；呼吸谐波污染心跳带。四被试（001/007/008/SXQ）统一管线需要综合修复。

### 改动（管线演进）

| 版本 | 改进 | 解决的问题 |
|------|------|-----------|
| v1.1 | 窗级自适应选 bin（每窗独立, 替代段级固定） | 段级固定 bin 在部分窗信号差 → HR 51→104→51 假跳变 |
| v1.1 | 频率锚定 bp 主频（窄带检测中心） | VMD 后主频漂移到倍频（HR 51→135 假跳变） |
| v1.1 | MIN_PEAKS 窗长自适应（30s→15 拍起） | 固定 30 拍对 30s 窗过严, 探针窗可用率 29%→71% |
| v1.2 | 多 bin 交叉验证（同段多 bin 心率一致性） | 单 bin 主频锁错无冗余（007 的 59 次伪影靠此修复） |
| 附加 | 距离门控 bin 8-45（≈30-166cm） | 环境反射误判心跳（008 曾选到 bin253=9.4m） |
| 附加 | 呼吸谐波陷波（v9 模块: 呼吸主频+2/3 次谐波 iirnotch） | 呼吸谐波污染心跳带（模拟验证: 谐波功率降 97% 心跳无损） |
| 附加 | 动作帧检测（帧间幅度差分 + MAD 阈值） | 大幅度动作破坏相位解调 |
| v1.3 | 段参考修正（med_hr_hint: 心率不瞬间翻倍） | 单强反射场景（001）倍频锁错无冗余可纠正, 探针窗 75%→100% |

### 验证（四被试, 统一管线 v1.3）

| 被试 | 全程窗可用率 | 探针窗可用率 |
|------|-------------|-------------|
| 001 | 88/91 (97%) | 24/24 (100%) |
| 007 | 96/96 (100%) | 48/48 (100%) |
| 008（排除休息） | 65/65 (100%) | 48/48 (100%) |
| SXQ（排除休息） | 46/57 (81%) | 38/48 (79%) |

### 关键教训（08-07）

1. **001 信号弱系误诊**: PTP 对比用了错误 bin（近场杂波）; 人体 bin 对比显示
   001 心跳 SNR 10.8（007/008 的 4 倍）, 001 是"好但孤"（单强反射无冗余）
2. **跨被试合并必须个体标准化**: 原始合并 SDNN p=0.007 的"显著"在
   被试内 z-score 后消失（p=0.34）——个体基线差异伪装成组间效应
3. **全程固定 bin 不可行**: 46 分钟任务 bin 漂移, 窗级自适应（97%）优于
   固定 bin（55/91）; 3 分钟静止才适合固定 bin（REST-3min 案例）

### 涉及文件

- `scripts/analyze_mmwave_hrv.py`
- `scripts/process_vital_signs_v9.py`（谐波陷波模块）
## 2026-08-29 — audit(mmwave): primary-relink RS6240 firmware mode and pipeline stages

- 恢复并重新绑定此前 RS6240 firmware/manual/SDK 审计：正式镜像 `mrs6240_p2512.img` 的 `fft_mode=2`、37 mm、256 点和 2T×4R 1D DataCube 路径已形成 primary-linked evidence。
- 新增逐逻辑块审计、文献—项目 stage matrix、gap/decision ledger 和 source-controlled Mermaid flowchart；明确 lower-layer window/calibration、Tx/Rx timing、target continuity、active harmonic gate 和 HRV beat evidence 的缺口。
- 不运行新科学分析、不运行 #16、不修改原始数据或 NIR/RGB producer。

## 2026-08-30 — audit(mmwave): freeze targeted validation merge contract

- 完成三场、首 6000 帧、五重叠窗口的 target/bin/channel continuity diagnostic；记录 HR/BR bin hopping、channel switching、phase comparability 和 provenance/QC 边界，不改 producer 数值路径。
- 完成 current A、radar-only BR guard B、external-RSP diagnostic C；B 相对 A 无触发、无改善，不进入 producer；external RSP 仅作验证参考。
- 冻结 portable V2 的 ALLOW/HOLD/EXCLUDE：结构性 missing/loadability `ALLOW`，HR/BR/RR 与 continuity/phase/motion QC `HOLD`，HRV/IBI 与外部 ECG/RSP 值 `EXCLUDE`；HRV 仍 `BLOCKED`，Issue #16 仍 `PAUSED`。

## 2026-08-30 — audit(mmwave): Issue #29 Supervisor execution-evidence review

- 审查 #24–#28 的实际脚本、结果、manifest、治理同步和本地提交；#24/#26/#27/#28 的边界证据可供父调度按提交整合，均不提升 HR/BR formal validity。
- #25 已由本地提交 `c4b5397d65e26ab3d8951005be83ed1d8c5f25d4` 闭合同源 ECG eligibility 下 283 个共同有效配对的 diagnostic 比较；formal window validity 仍 unresolved，不把旧 0 分母结果解释为无差异。
- 新增 Supervisor 矩阵与 manifest：`docs/results/2026-08-30_MMWAVE_ISSUE29_SUPERVISOR/`；整体 `REUSE_GATE=PASS`、`SCIENTIFIC_GATE=PARTIAL`；HR `HOLD`、HRV `BLOCKED`。
## 2026-08-30 — audit(mmwave): refresh #27→#25 stage replay provenance at f01

- Replayed the existing downstream stage adapter on canonical `main=f01c582e623025e091252d38ff52d276b323b830`; retained `COMPLETE=333` and `COMPLETE ∩ ECG_VALID=323` with unchanged metrics.
- Recorded direct paired effects only for the existing previous-anchor and time/frequency fusion switches; historical gate/target remains bounded contract replay.
- Added explicit reuse-rejection reasons for harmonic folding, VMD, segment correction/consensus, and final QC-only attribution; no producer, raw, ECG, gate parameter, or new algorithm was added.
- Refreshed the stage manifest with repository-relative tracked paths and updated `PROJECT_STATUS.md`, `ANALYSIS_HISTORY_LEDGER.md`, and `docs/canonical/RESULT_INDEX_V1.md`; #25 remains `WAIT_ON_SELECTOR_VALIDITY` and #29 remains scientific-gate `PARTIAL`.
