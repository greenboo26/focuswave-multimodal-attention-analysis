# FocusWave Multimodal Attention Analysis 状态

## 2026-08-30 selector-path reconciliation and next-step gate — PARTIAL / #25 WAIT_ON_SELECTOR_VALIDITY

- 实际复用 canonical `process_vital_signs_v3_1_1.py` 的 `_select_spectral_bpm()`、previous-BPM anchor、time/frequency fusion、harmonic folding，在冻结 #24 的 335 个 DLL-time windows 做 downstream replay；未修改 producer/raw/target/QC/gate，ECG 仅作 retrospective oracle。
- #27 分母保持 `ECG_VALID=325`、`ECG_INVALID=10`、`UNRESOLVED=0`；可评估 ECG_VALID=`323`，coverage-limited=`2`。在 102 个 wrong-selection 中，sequential selector 恢复 exact=`37`、nearby=`10`；在 182 个 nearby 中恢复 exact=`17`、nearby=`45`。这是 selector/path 影响的可重复 supporting 证据，不是 HR 改善或真实 target 恢复证明。
- A2 已用既有 335 行 target-ablation、truth 与 selector replay 做窄 join：182 个 nearby 的路径级子类为 neighbor-bin=`6`、neighbor-channel=`11`、target/channel switch=`164`、无替代 target 改变=`1`；同一 fixed target 上 selector candidate 改变=`182`。这不是独立 physical target truth；candidate persistence/instability 仍因仅有 15 条未对齐 continuity rows 而 `NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS`。
- #25 的既有 283-pair diagnostic 20 s/60 s MAE=`14.703129/5.608574` bpm（差=`-9.094555`）与固定 targeted path 不同于 canonical selector replay，故窗口效应仍不可分离；保持 `WAIT_ON_SELECTOR_VALIDITY`，不按 MAE 推广 60 s。
- #26 已完成本轮独立物理证据回收检查：仅找到 protocol 的 0.4m 摆位说明和 0.8m 工程验证目标，未找到 session-level 距离/朝向/照片/geometry receipt；保持 `PHYSICAL_GATE_UNRESOLVED / HARD_EXTERNAL_BLOCKER`。
- #28 在 FocusWave `formaltest` 上完成最小 future-prevention patch：stop/disconnect 在 flush/close 前等待 worker 退出；不改历史 raw、采集参数或分析 producer 语义。该 patch 需以 FocusWave 外部仓库 commit 单独报告。
- 结果包：`docs/results/2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION/`，本次实际重跑基线=`17320ea553f63e49dce641135962c5601e5ccff9`；新增 path-level A2 aggregate，逐窗 replay/localization 表仍 local-only。HR/BR 继续 `HOLD`，HRV 继续 `BLOCKED`，未运行 C2B/C2C、未改 NIR/RGB。

## 2026-08-30 Issue #29 execution-evidence supervisor — REUSE_GATE=PASS / SCIENTIFIC_GATE=PARTIAL

- Supervisor 已核验 #24–#28 的实际脚本、结果、manifest、复用理由、分母边界和本地提交；不以会话文字替代证据。统一结果为 #24 ECG eligibility 层完成，#25 bounded diagnostic，#26 physical gate unresolved，#27 supporting-only，#28 历史 tail 不可恢复。
- HR/BR 继续 `HOLD`，HRV 继续 `BLOCKED`；未修改 producer/raw/firmware/portable V2/NIR/RGB，未运行 C2B/C2C，无新 HR 算法族或 MAE 调参。
- 证据包为 `docs/results/2026-08-30_MMWAVE_ISSUE29_SUPERVISOR/`；审查使用的 `805db1d3f2d701d46f678b7cd911990f779a4966` 明确是 `PRE_INTEGRATION_BASELINE`，集成后的 canonical commit 是 `c2150c9bb5bb4509b09b9b7be0ada956c3e222cc`。
- #24–#29 的唯一 local-execution→canonical 映射见 `docs/canonical/RESULT_INDEX_V1.md` 的 provenance map；本机仅验证了 #27 的稳定 local-only 结果目录存在；#24 仅有 manifest 记录的 ephemeral row-level 路径，#29 目录当前未存在，其他路径不在本轮机器验证范围。

## 2026-08-30 Issue #28 97795/block4 acquisition tail — PARTIAL / HISTORICAL_TAIL_IRRECOVERABLE

- 复用既有 DLL coverage audit、DLL contract、原始 coverage manifest 与 FocusWave `ecg` source；RUN_ID=`issue28-tail-20260830-r1`。11 个 session/block 目录中 6 个可审计、5 个为 `MISSING_REQUIRED_LOG`。
- `97795/block4` marker→last DLL frame gap=`24,809 ms`；w027/w028 的 end gap=`9,536/19,536 ms`。长尾候选为 `97795/97796/97994`；frame continuity 分别为 `true/false/false`，后两者含 `82/314` 个 gap，机制保持 unresolved，不能泛化为同一原因。
- 结论为历史尾部不可恢复；不做 padding、backfill 或 synthetic frame，不改变 #24–#27 的 335-window primary 分母，也不阻塞主线。未来修复位置仅指向 producer 的 stop/drain/order 与 queue/drop/timeout instrumentation，本轮未改 producer、raw、firmware 或 portable V2。
- 证据包为 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_ACQUISITION_TAIL_AUDIT_*`，入口为 `scripts/maintenance/run_mmwave_acquisition_tail_audit_20260830.py`；HR/BR 仍 `HOLD`，HRV `BLOCKED`。

## 2026-08-30 Issue #24 ECG reference eligibility — PARTIAL / ECG_REFERENCE_ELIGIBILITY_COMPLETE

- 在 `PRE_INTEGRATION_BASELINE` `805db1d3f2d701d46f678b7cd911990f779a4966` 上执行、后由 canonical `main` `c2150c9bb5bb4509b09b9b7be0ada956c3e222cc` 集成；复用 `scripts/gold_standard_qa.py` 的 ECG 清洗规则（0.5–40 Hz 三阶 SOS、R-peak 最小间距 0.30 s、固定 prominence 0.25、IBI 300–2000 ms、相邻 IBI >20% 异常波动剔除、有效 beat coverage ≥80%）和既有 `run_mmwave_targeted_validation_20260830.py` 的 block marker affine mapping。
- 针对冻结的 335 个 DLL-time windows，实际结果为 `ECG_VALID=325`、`ECG_INVALID=10`、`UNRESOLVED=0`。10 个 invalid 的主 reason 全部是 `abnormal_adjacent_ibi_fluctuation_gt20pct`；marker mismatch 单独存于 `ecg_qc_warning`，不作为 invalid reason。`97793/block1` 的 57 个窗口保留 marker warning，但 affine mapping 可用。
- 固定既有 ARM0/ARM1/ARM2 estimator rows，仅在 `ECG_VALID=325` 分母重算：ARM0 MAE=`25.005` bpm（325/325），ARM1=`21.906332` bpm（304/325），ARM2=`18.904008` bpm（325/325）。全 335 窗口的 `24.847938/21.774620/19.040268` 仅作 diagnostic，不作 validity denominator。
- RUN_ID=`ecg_eligibility_dll_20260829T220533Z`。逐窗 eligibility 与每个 reject reason 保存在 local-only `work/ecg_eligibility_dll_windows_20260830/ECG_DLL_WINDOW_ELIGIBILITY_LOCAL_ONLY.csv`；Git-safe aggregate、manifest 和报告位于 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`。
- 本轮只闭合 ECG reference eligibility 层；不把 20 s 窗口升级为 canonical HR window，不改 estimator/target/gate/producer/raw/firmware/portable V2，不运行 #16、C2B/C2C 或 HRV。HR 仍 `HOLD`，HRV 仍 `BLOCKED`。

## 2026-08-30 Issue #26 distance-error / physical gate — PASS / PHYSICAL_GATE_UNRESOLVED

- 复用 `selected_bin × 0.037 m` 校正语义、既有 B2 极端距离前端审计、早期 5 participant/99-window ECG-valid HR 与 99-row RSP-valid BR paired evidence；未重选 target、重跑 estimator、改变 QC 或运行 C2B/C2C。
- RUN_ID=`MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_20260829T220501Z`；连续 distance–absolute-error 与预定义 `<0.20`、`0.20–0.30`、`0.30–0.60`、`0.60–1.00`、`>1.00 m` 分层已完成，HR MAE=`3.777215` bpm、BR MAE=`3.327631` breaths/min，仅作早期参考描述；历史 `0.30–1.50 m` 仅为 `HISTORICAL_GATE_SENSITIVITY`。
- formal 71-session distance 分布复现为 `4/12/32/5/18`；near-side bright structure=`OBSERVED`，B2 labels 为 `LIKELY_HUMAN=4`、`AMBIGUOUS=82`、direct leakage=`0`、fixed reflection=`0`。这些 0 不证明机制不存在；near-field cause 与 current physical gate 仍 `UNRESOLVED`，未授权 exclusion gate。
- 结果包位于 `docs/results/2026-08-30_MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE/`；formal 71 场只作 distance/structure/QC 描述，早期 99 窗不外推为正式 71 场真值。未改 raw、firmware、producer、portable V2 或 HRV。

## 2026-08-30 Issue #27 ECG_VALID retrospective spectral truth audit — PARTIAL / SUPPORTING_ONLY

- 在既有 335-window fixed target/peak/ARM0/1/2 结果之后追加下游 spectral truth audit；ECG/RSP 仅作 oracle，未参与 target、channel、candidate、peak、ARM 选择，未改 producer 或参数。
- 分母冻结为全窗口 diagnostic/supporting=`335`、#24 ECG_VALID primary=`325`、ECG_INVALID=`10`、UNRESOLVED=`0`；97795/block4 w027/w028 为 `SUPPORTING_COVERAGE_LIMIT`，不与 10 个 ECG_INVALID 重复计数。
- ECG_VALID primary ARM0/ARM1/ARM2 MAE=`25.005/21.906332/18.904008` bpm，selected n=`325/325/325`，estimator-valid n=`325/304/325`；truth class 为 nearby=`182`、wrong-selection=`102`、selected-ECG-bin=`22`、absent/weak=`17`、coverage/reference=`2`。
- Internal harmonic guard 在 fixed targeted path 未调用；external RSP guard 仅 diagnostic。结果包为 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_VALID_SPECTRAL_*`，逐窗表 local-only；HR=`HOLD`、HRV=`BLOCKED`。

## 2026-08-30 mmWave timestamp-semantics repair — PARTIAL / DLL_CONTRACT_FROZEN__WINDOWS_MATERIALLY_CHANGED

- 以 canonical `main` baseline `ab39ad272462c54208b56e0b302b5d9ff1e95b4c`、FocusWave `ecg` commit `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317` 完成 `97793`、`9779`、`97795` 的 Python timestamp row ↔ NPZ frame ↔ DLL timestamp mapping；三场均 row/frame 数一致、frame index 连续、8 通道长度一致、DLL timestamp 单调，mapping status=`OK`。
- 冻结 `MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md`：以 `receive_data.timeStamp` 经 `_dotnet_ts_to_unix_ms()` 转换的绝对 Unix ms 作为 authoritative frame clock；Python `time.time()` 仅 provenance。底层 DateTime 由 device、firmware、SDK 还是 host-side DLL 生成，源代码未说明，保留为 unresolved provenance limitation。
- 按 block start/end markers（block1 `12/22`、block2 `13/23`、block3 `14/24`、block4 `16/26`）及既有 BIOPAC/101–110 tick audit 重建 335 个 complete-block、20 s/10 s/5 s-guard windows；block 内 continuity 规则和 block-start reset 不变，跨 rest/坐姿调整/block 边界 transition 未纳入。
- Window equivalence 为 exact `25`、partial `156`、obvious `154`，changed `310/335`，mean/median/min Jaccard=`0.736410/0.923114/0.000000`。因此不是 cosmetic change，旧 Python-time windows 与 DLL-time windows 不可互换。
- 在不改 estimator、target、gate、ECG reference 的前提下重放 ARM0/ARM1/ARM2：new DLL-time MAE 分别 `25.791632/22.189492/19.189060` bpm（334/334、323/335、334/335）；old Python-time provenance 分别 `24.884913/21.804185/19.068931` bpm。mean absolute HR value delta 为 `6.126641/6.845548/6.444105` bpm。
- 关键 blocker：`97795/block4` 程序结束 marker 比最后 DLL frame 晚 `24,809 ms`，最后一个 guarded window 只有 `46` 个 DLL frames；不做 Python-time backfill、padding 或 synthetic timestamp。分类为 A=`不支持`、B=`支持（materially changed windows）`、C=`保留 unresolved`。
- 旧 20 s 结果保留为 Python-time historical provenance，但 supersede 为当前 DLL authoritative contract 的结果；HR/BR 继续 `HOLD`，HRV `BLOCKED`，Issue #16 `PAUSED`。未修改 `Attention-Analysis@codex/formal-analysis-v2-portable`，未运行 C2B/C2C、HRV 新算法或全量 formal batch。
- 证据包：`docs/research/MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md`、`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv`、`MMWAVE_TIME_SEMANTICS_HR_COMPARISON.csv`、`MMWAVE_TIME_SEMANTICS_HR_METRICS.csv`、对应 reports/manifests；row-level mapping 仅保存在 `D:\Project\厚粲杯\11_数据\derived\mmwave_timestamp_semantics_repair_20260830\`。

## 2026-08-30 mmWave DLL-time coverage audit and fixed-denominator sensitivity — PARTIAL / COVERAGE_NOT_PRIMARY_HR_EXPLANATION

- 在已冻结的 DLL-time 335-window primary result 上，先于 sensitivity 固定了完全独立于 ECG/HR/abs error/arm performance 的 coverage contract：`COMPLETE`=`coverage_fraction≥0.95` 且边界 gap≤max(3×local median interval, 50 ms)、internal gap≤1,000 ms；`SEVERELY_INCOMPLETE`=`coverage_fraction<0.50` 或边界 gap>max(1,000 ms, 5×median) 或 internal gap>1,000 ms；其余为 `PARTIAL`。
- 从每个 subject/block 的 DLL timestamp 估计 local rate：median interval=10 ms、p5=9 ms、p95=12 ms、effective local rate=100 Hz；expected count 使用 `20,000/median_interval+1`，不是固定 2,000 帧真值。
- 335 个窗口 coverage class：`COMPLETE=333`、`PARTIAL=0`、`SEVERELY_INCOMPLETE=2`。两窗均为 `97795/block4` 尾部：`w027` 1,035 frames、coverage `0.517241`、end gap `9,536 ms`；`w028` 46 frames、coverage `0.022989`、end gap `19,536 ms`。
- 预注册 sensitivity：S0 all=`335`，S1 exclude severe=`333`，S2 complete-only=`333`。S0/S1/S2 ARM0 MAE=`25.791632/25.812760/25.812760`；ARM1=`22.189492/22.128143/22.128143`；ARM2=`19.189060/19.225180/19.225180` bpm；S0→S2 ΔMAE=`+0.021128/-0.061349/+0.036120` bpm。
- Coverage 结论为 `SEVERE_COVERAGE_FAILURE_LOCALIZED_ONLY` + `COVERAGE_NOT_PRIMARY_HR_EXPLANATION`：去除两条严重缺尾窗没有实质改变整体高误差模式；这只是完整采集窗口上的 validity sensitivity，不是 HR 算法提升。335-window primary 结果完整保留，未删除或覆盖 ARM0/ARM1/ARM2。
- 新增证据：`MMWAVE_DLL_WINDOW_COVERAGE_AUDIT.csv`、`MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_REPORT_2026-08-30.md`、`MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_MANIFEST.json`、`MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY.csv`、`MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_BY_BLOCK.csv`、`MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_REPORT_2026-08-30.md`、`MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_MANIFEST.json` 及对应 maintenance scripts。
- HR/BR 继续 `HOLD`，HRV `BLOCKED`，Issue #16 `PAUSED`；未修改 estimator、target、gate、filter、ECG、producer/raw/firmware、portable V2，未运行 C2B/C2C 或 full batch。

## 2026-08-30 formal multimodal model-ready v1 — PASS_MODEL_READY

- Frozen the observation-defined primary matched cohort at 1,295 probes / 65 sessions / 46 repeat participants from the 1,440-probe canonical timeline; all 46 matched repeat participants have one participant-disjoint LOSO fold.
- Audited modality states explicitly: NIR `OBSERVED=1,294`, `STRUCTURAL_MISSING=140`, `OBSERVATION_MISSING=5`, `QC_FAIL=1`; RGB `OBSERVED=1,420`, `STRUCTURAL_MISSING=20`. The NIR QC-fail row remains in the observation-defined denominator with NaN geometry.
- Froze Behavior 5, NIR 4, and RGB 6 primary predictors. Blink remains provisional and excluded; PERCLOS is absent/not validated; mmWave HOLD/EXCLUDE fields remain outside the primary predictor contract.
- Participant-disjoint LOSO leakage audit, pre-onset Behavior temporal audit, source-hash traceability, and readiness gate all pass. No model was trained and no NIR/RGB producer was rerun.
- Git-safe evidence package: `docs/results/2026-08-30_FORMAL_MODEL_READY_V1/`. Full probe-level missingness audits, expanded folds, and model-ready candidate remain local-only.

## 2026-08-30 formal multimodal mother-table attach — PARTIAL / structural V2 merge-ready PASS

- Reused the current local mother table (179 sessions / 112 repeat participants) and explicit `j_source_folder` evidence to map 72 current sessions / 46 repeat participants. `single_experiment_id` and `session_id` remain separate fields.
- Recovered 1,440 current formal behavior probes from J events and froze `pre_30s` on real `unix_ms` with the five-column probe key `repeat_participant_id, session_id, block_id, probe_id, window_name`.
- Built local-only behavior/NIR/RGB probe tables and coverage audit. Observed rows: Behavior 1,440; NIR 1,295; RGB 1,420; fully matched candidate 1,295. Missing rows remain explicit and are not filled.
- Ran the portable V2 validator at pinned commit `21c7da4fe2e03d853f0b6391d580334526f86ce3`: all three modality keys passed non-null/unique validation; outer and inner merge each returned 1,440 rows. This is structural readiness only, not feature completeness or model readiness.
- Evidence package: `docs/results/2026-08-30_FORMAL_MULTIMODAL_ATTACH/`. Row-level tables, raw videos/Parquet, and producer outputs remain local-only. No producer rerun or model training occurred.
- Remaining boundary: NIR has 145 probe rows without current window observations; RGB has 20 rows missing from `sub-099`; RGB blink candidate is provisional and PERCLOS is absent; mmWave remains reserve-only with HR/BR/RR HOLD and HRV/IBI EXCLUDE.

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

## 2026-08-30 targeted mmWave validation — SUPERSEDED / historical pre-contract run

- Completed the ordered targeted validation on `97793`, `9779`, and `97795`, using only the first 6000 frames and five overlapping windows per session; no full formal batch was run.
- Firmware identity is `CONFIRMED_WITH_PROVENANCE_LIMITATION`: the operator confirms `mrs6240_p2512.img` was used throughout formal acquisition; the machine burn/boot/version receipt remains missing. Remaining upstream engineering items retain explicit `UNRESOLVED` or `SDK/MANUAL_ONLY` status.
- Current target-selection continuity is not stable in the targeted sample: HR bin hops 8/12, BR bin hops 9/12, HR channel switches 11/12, BR channel switches 9/12. No same-target phase transition was available for comparison and independent motion evidence is absent; no movement attribution is made.
- A/B/C harmonic validation completed. B used radar-derived BR only and was identical to A (MAE 9.392 bpm; no trigger/rejection); C identified three external-RSP 3x windows with A/B harmonic-window MAE 27.336 bpm. B is not proposed for producer promotion; external RSP remains validation-only.
- Frozen portable-V2 contract: HR and BR/RR `HOLD`; HRV/IBI `EXCLUDE`; continuity/phase/motion fields `HOLD` as diagnostic QC only; missing/loadability `ALLOW` as structural metadata. HRV remains blocked at radar beat–ECG R-peak synchronization and paired IBI agreement.
- Evidence package: `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`. Issue #16 remains `PAUSED`; portable V2 was read-only and unchanged.

## 2026-08-30 targeted mmWave validation rerun — PROVISIONAL / REFERENCE_PIPELINE_AUDIT_PENDING

- 按 `docs/research/MMWAVE_BLOCK_RESET_AND_ECG_ALIGNMENT_CONTRACT_2026-08-30.md`，并核对 `kyandi233-dev/FocusWave@ecg` commit `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317` 后重做 `97793`、`9779`、`97795`；8 个完整 block、335 个窗口、327 个同 block 相邻 transition。每个 block 起始均重置 target/bin/channel state；跨 rest、坐姿调整和 block 边界的 transition 未计入。
- 旧版 12 个 transition 已逐项重分类：12/12 属于每场起始前 6000 frames 的 baseline/pre-block，0 个属于完整 formal block，0 个跨 rest/block；旧 12/12 不再作为 continuity failure 证据。
- `BLOCK_LOCAL_CONTINUITY` 诊断 candidate 将 HR bin hop 243/327 降至 164/327、HR channel switch 246/327 降至 158/327；但 HR MAE 仅由 25.958 降至 24.885 bpm，BR MAE 由 3.723 升至 4.237 breaths/min。仅凭轨迹变平滑不能升级生理有效性，HR/BR/RR 继续 `HOLD`，HRV 继续 `BLOCKED`。
- ECG/BIOPAC 使用每个 block 的 start/end marker 与 101–110 tick；ECG affine fit residual p95 中位数为 2.296 ms。8 个完整 block 中 7 个 marker sequence exact；`97793/block1` 在序列 index 73 出现 event `103` vs physical `102` 的单点 mismatch。
- mmWave tick 审计发现 730 个 `|nearest delta| > 100 ms` 的 timestamp gap；排除这些 gap 后 affine-fit residual p95 中位数为 6.133 ms，但本轮不将其表述为双机同步已通过。该 gap/marker 限制是本轮 PARTIAL 的主要 blocker。
- 本轮 HR/BR 仅使用现有 producer 的 bandpass + periodogram/peak 定义作 bounded diagnostic estimator；未运行 VMD、HRV 新算法、Issue #16、C2B/C2C 或全量 formal batch，未修改 producer、portable V2、实验程序或原始数据。
- 新版证据包：`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/`，包括 block-local continuity table、mmWave↔ECG same-window comparison、alignment audit、legacy 12-transition audit、manifest 和报告。旧版同目录结果保留为历史文件，不再作为当前结论。

## 2026-08-30 historical ECG reference-chain audit — PARTIAL / CURRENT_MMWAVE_COMPARISON_QUALIFIED

- 已完成历史 ECG/BIOPAC 链审计：盘点 canonical `master`、当前 `main`、mmWave reanalysis、`kyandi233-dev/FocusWave@ecg`，并确认 `Attention-Analysis@nvidia-cuda` 未发现相关 ECG/BIOPAC/mmWave reference script；`Attention-Analysis@codex/formal-analysis-v2-portable` 未修改。
- 历史最佳 HR 数值 `3.7772146 bpm` 已绑定到 5-session、100-row/99-valid、60 s probe 的 corrected-distance calibration；其 ECG 参考链是 `scripts/analyze_acq_reference.py` 的 metadata-zero 规则，毫米波端同时改变了 `0.08 m/bin` 到 `0.037 m/bin` 的 gate。因此该数字保留为历史 corrected calibration，不迁移为当前 3-session/20 s block 结果。
- 固定当前毫米波 `local_hr_freq_bpm` 后重放 335 个同窗：historical ECG `24.912767 bpm`、current block-marker-affine ECG `24.880549 bpm`、minimal-difference `24.912767 bpm`。255/335 个 ECG HR 数值发生变化，但中位绝对变化 `0.15 bpm`、最大 `3.30 bpm`；alignment 不能解释约 24.9 bpm 的当前毫米波误差。
- 因而当前 targeted HR MAE 仅取得 `CURRENT_MMWAVE_COMPARISON_QUALIFIED`：它是同一固定毫米波输出下的 20 s block-local diagnostic comparison，不是 formal HR validity；HR/BR 继续 `HOLD`，HRV 继续 `BLOCKED`。
- `97795` 的目录与通道/采样长度/marker 结构一致，但实际 `.acq` 文件名为 `97995.acq`；未重命名、复制或替换原始文件，故保留为 provenance limitation。mmWave timestamp gaps 与历史/当前毫米波估计器差异仍阻止统一 cross-era MAE 或 `PASS`。
- 新增证据：`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_SCRIPT_LINEAGE.csv`、`ECG_HISTORICAL_RESULT_PROVENANCE.csv`、`ECG_REFERENCE_PIPELINE_COMPARISON.csv`、`ECG_REFERENCE_PIPELINE_SUMMARY.csv`、`ECG_REFERENCE_AUDIT_REPORT_2026-08-30.md`、`ECG_REFERENCE_AUDIT_MANIFEST.json` 及审计脚本 `scripts/maintenance/audit_historical_ecg_reference_chain_20260830.py`。

## 2026-08-30 mmWave estimator lineage + same-window replay — PARTIAL / TIMESTAMP_SEMANTICS_CLASSIFIED

- 在 canonical `main` `64634159d226ee1ed892d53e56fcf3697fbff9b8` 上完成历史 mmWave HR estimator lineage：确认 `3.7772146 bpm` 来自 `run_hr_course_99_corrected.py → process_vital_signs_v3_1_1.py`，先用 6000-frame selection 固定 heart target，再对全记录运行 `bp_heart`；参数为 `0.037 m/bin`、`0.30–1.50 m`（bins 9–40）、phase unwrap + 5 mm/(4π)、4th-order SOS 0.8–2.0 Hz、periodogram/peak/time-course/segment correction/consensus，历史 comparison 为 60 s / 5 sessions / 99 valid windows。master legacy、calibration 和 reanalysis utilities 均登记为 inventory，未误认作 3.777 producer。
- 在冻结的 335 个 complete formal-block、20 s 窗口和既有 block-affine ECG HR 上重放：strict historical 60 s arm 为 `NOT_APPLICABLE_TO_20S`；仅改变 window length 的 `HISTORICAL_PIPELINE_20S_ADAPTATION` 为 MAE `14.748328`、median AE `14.348`、RMSE `18.551216`、bias `-12.794734`、Pearson `0.255126`、Spearman `0.243843`（335/335）。current independent 为 `25.958119` MAE，current block-local 为 `24.884913` MAE；两者均 335/335，且与上一版冻结 current rows 逐行一致（335/335 exact，最大差 0）。
- 同分母 pairwise：历史 20 s adaptation 相对 current independent 在 242/335 窗口更好、相对 block-local 在 231/335 更好；current block-local 相对 independent 的绝对误差平均改善 `1.073206 bpm`，但 163/335 为 tie。因此不报告 current regression 或历史原始 pipeline 已在当前窗口成立；HR 继续 `HOLD`，本轮结论为 `CASE B + CASE D`，整体 `PARTIAL`。
- target 差异已量化：历史 gate 对应 bin 9–40，当前 selector independent 未施加物理 gate；当前 independent 与历史 target 完全相同的 bin+channel 仅 4/335，block-local 也是 4/335；落在历史 9–40 gate 外的分别为 186/335 和 154/335。`0.037 m/bin` 在历史链中是物理 gate/距离换算参数，在当前 continuity 表中只是 reporting label，不能声称当前 selection 已使用该 gate。
- 时间语义已闭合但仍有真实采集间隔限制：A 类 event tick Unix ms 到最近 mmWave timestamp 共 3491 条，`|delta|>100 ms` 为 730；它不是相邻帧 gap。B 类相邻 mmWave timestamp 共 459126 条，median 7 ms、p95 20 ms、p99 31 ms、max 6495 ms，>20/50/100/500 ms 分别为 20682/840/457/457；真实 >100 ms 帧间隔因此存在，需与 A 类 730 分开解释。
- 证据包新增 `MMWAVE_HR_ESTIMATOR_LINEAGE.csv`、`MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv`、`MMWAVE_HR_ESTIMATOR_SUMMARY.csv`、`MMWAVE_HR_ESTIMATOR_PAIRWISE_COMPARISON.csv`、`MMWAVE_HR_ESTIMATOR_COMPARISON_REPORT_2026-08-30.md`、`MMWAVE_TIMESTAMP_SEMANTICS_AUDIT_2026-08-30.md`、`MMWAVE_HR_ESTIMATOR_AUDIT_MANIFEST.json` 及脚本 `scripts/maintenance/run_mmwave_estimator_same_window_audit_20260830.py`。完整时间 CSV 保存在 `D:\Project\厚粲杯\11_数据\derived\mmwave_timestamp_semantics_audit_20260830\`，manifest 记录行数和 SHA-256；未修改 producer、firmware、raw、FocusWave acquisition、portable V2、#16、C2B/C2C、HRV 或全量 formal batch。

## 2026-08-30 Issue #25 20 s vs historical 60 s controlled comparison — PARTIAL / DIAGNOSTIC_ONLY

- 追溯确认：20 s 首次进入当前链路来自 `472735b6b6af5f98e92ab7815718e81863cb6098` 的 `scripts/maintenance/run_mmwave_targeted_validation_20260830.py`，用途是 block-local continuity / ECG-aligned bounded diagnostic；历史 60 s 来自 `64634159d226ee1ed892d53e56fcf3697fbff9b8` 的 `run_hr_course_99_corrected.py` 与 `build_hr_course_99_audit.py`，真实语义为 v3.1.1 HR course 的 25 s internal window、5 s step，在 60 s probe 内按 `(t > onset-60) & (t <= onset)` 取 median。
- 依赖 #24 `d2d09f8ac502600d3a1241e33c429bd53756fa45` 的 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_ELIGIBILITY_MANIFEST.json`（commit 内容 SHA-256 `0806cb4f0e477788ee7cd604e3d04c811654fb692f2840767249982ebc5ba258`），口径为 ECG_VALID=325、ECG_INVALID=10、UNRESOLVED=0；marker mismatch 仅 warning，10 个 invalid 为相邻 IBI 异常波动。当前 20 s 与 trailing 60 s 均重新执行同一 0.5–40 Hz / R-peak / IBI / artifact / coverage adapter，不再使用简单 `ecg_status==valid`。
- RUN_ID `issue25_window_length_20260830` 在 `PRE_INTEGRATION_BASELINE` `805db1d3f2d701d46f678b7cd911990f779a4966` 上完成 303 endpoints / 8 blocks，结果随后由 canonical commits `4986ca32716fe415c01b518587b031da55d481c1` + `65b8e6547394be9c5bddba823ca7c72ce8e7ab38` 集成；两时长共同 ECG_VALID pair=283。20 s：coverage mean/median `0.655511/0.691708`、n=`283`、MAE/median AE/bias/Pearson/Spearman=`14.703129/14.514286/-12.598120/0.278024/0.268721`；60 s：`0.656046/0.691986`、n=`283`、`5.608574/4.083467/-3.630629/0.379439/0.399861`。名义频率分辨率为 20 s=`0.05 Hz/3 bpm`、60 s=`0.016666667 Hz/1 bpm`。这是 diagnostic comparison；selector validity 未闭合，formal window validity 仍 `UNRESOLVED`，HR 继续 `HOLD`。
- `REUSE_REJECTION_REASON`：既有 same-window audit 只有冻结的 335-row 20 s 分母，并明确将 strict historical 60 s 标为 `NOT_APPLICABLE_TO_20S`，不构造 trailing 60 s DLL-time window 或 paired ECG_VALID reference，故只增加最小 execution wrapper；未改 estimator、target、producer、raw、firmware、portable V2、C2B/C2C、HRV 或全量 formal batch。
- 证据：`docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_WINDOW_LENGTH_COMPARISON.csv`、`MMWAVE_WINDOW_LENGTH_METRICS.csv`、`MMWAVE_WINDOW_LENGTH_BLOCK_AUDIT.csv`、`MMWAVE_WINDOW_LENGTH_COMPARISON_REPORT_2026-08-30.md`、`MMWAVE_WINDOW_LENGTH_COMPARISON_MANIFEST.json`；入口 `scripts/maintenance/run_mmwave_window_length_comparison_20260830.py`。raw/row-level 与大型输出留在本地。

## 2026-08-30 mmWave gate/target ablation — PARTIAL / GATE_AND_TARGET_BOTH_MATTER

- 在同一 335 个窗口、同一 block-affine ECG 和同一当前 HR estimator 上完成四 arm：ARM0 current block-local；ARM1 current block-local + historical bins 9–40 gate；ARM2 historical 6000-frame fixed target + 当前 20 s estimator；ARM3 gate + current block-local。按用户给出的定义，ARM1 与 ARM3 实际逐窗完全相同，未虚构额外 block-local effect。
- ARM0 MAE `24.884913`（335/335）；ARM1/ARM3 MAE `21.804185`（314/335，21 个窗口 gate 内无候选）；ARM2 MAE `19.068931`（335/335）。ARM1 vs ARM0 common n=314，mean ΔAE `-2.638525`；ARM2 vs ARM0 common n=335，mean ΔAE `-5.815982`。三个被试和四个 block 的 participant/block MAE 均同方向改善，但 gate arm 有 coverage 损失。
- ARM0 gate 内 181 窗口 MAE `21.902392`，gate 外 154 窗口 MAE `28.390344`；支持 `PHYSICAL_GATE_MISMATCH` 是贡献因素，但 ARM2 的固定 target 改善更大。因此本轮最终标签为 `GATE_AND_TARGET_BOTH_MATTER`，不是单一距离 gate 结论；trajectory stability 与 HR accuracy 分开记录。
- 457 个真实 >100 ms adjacent frame intervals 的 overlap audit 中，335/335 个 HR 窗口均至少包含一个长间隔，无法形成无 gap 对照子集；`TIMESTAMP_LONG_INTERVAL_EFFECT=UNRESOLVED`。未删除任何窗口。
- 未满足 producer change candidate 的证据门槛；current HR producer 继续 `HOLD`。新增 ablation 表、participant/block/stability、gate split、gap split、report、manifest 和脚本均位于 `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/` 与 `scripts/maintenance/run_mmwave_gate_target_ablation_20260830.py`。

## 2026-08-30 mmWave long-interval source/impact audit — PARTIAL / TIMESTAMP_RECORDING_ARTIFACT

- 在 canonical `main` `42167d3a112215701fad09ec21999a78a977baad` 的固定输入上，审计 `97793`、`9779`、`97795` 的 457 个 Python timestamp column-3 相邻间隔 >100 ms 事件；335 个既有 complete formal-block、20 s 窗口、同一 block-affine ECG HR 和同一 HR estimator 均保留，未删除行。
- 457/457 个事件同时 >500 ms，0 个落在 100–500 ms；每个事件均是 NPZ 文件切换，且 frame index modulo 1000 在每名被试内恒定。DLL timestamp column-2 的相邻间隔 >100 ms 为 0、>500 ms 为 0；DLL inter-event 和 frame spacing 均约 10 s / 1000 frames。Python 长间隔因此定位为 consumer/write timestamp artifact candidate，与 `mmwave_capture.py` 中 consumer 侧 `time.time()`、每 1000 帧 `np.savez_compressed` 同线程写入相吻合，而不是已证实的 sensor frame loss。
- Python 列另有 6,203 个同毫秒重复、0 个负间隔；没有 timestamp reset。window burden 仍逐窗输出：每窗 n_gap_gt100 为 1–2，平均 1.755；Python gap sum 平均 4,143.660 ms；DLL 规则下 expected frame count 为约 2,000，实际窗口索引密度指标仍保留但不解释为真实丢帧率。
- 同窗 burden 对 HR absolute error 的 Spearman 仅作描述性报告：overall 的 n_gap ρ 为 ARM0 `-0.058547`、ARM1 `0.004575`、ARM2 `-0.065296`；sum-gap ρ 为 `0.040775`、`0.027823`、`-0.046619`。由于所有窗口都有长间隔且 burden 与分块写入位置混杂，不作因果或质量改善结论。
- 当前 estimator 继续使用固定 `FS=100.0` 的 bandpass/periodogram/peak 参数，不读取 timestamp 列；DLL 时间戳支持 dense frame sequence 的固定采样率假设，但 Python timestamp-axis window semantics 仍为 `QUESTIONABLE`。未运行 timestamp-aware resampling，因为对 writer artifact 列重采样会制造伪传感器缺口。
- 最终分类：`GAP_SOURCE_CLASSIFICATION=TIMESTAMP_RECORDING_ARTIFACT`；`GAP_EFFECT_ON_HR=UNRESOLVED`（无 clean no-gap comparator）；`FIXED_FS_WITH_GAPS=QUESTIONABLE`。HR/BR 继续 `HOLD`，HRV `BLOCKED`，Issue #16 `PAUSED`；未修改 FocusWave producer/raw/firmware、portable V2、C2B/C2C 或全量 batch。
- 证据包新增 `MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv`、`MMWAVE_WINDOW_GAP_BURDEN.csv`、`MMWAVE_GAP_BURDEN_CORRELATION.csv`、`MMWAVE_ACQUISITION_TIMESTAMP_SOURCE_AUDIT.md`、`MMWAVE_LONG_INTERVAL_AUDIT_REPORT_2026-08-30.md`、`MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json` 和 `scripts/maintenance/run_mmwave_long_interval_source_audit_20260830.py`。

