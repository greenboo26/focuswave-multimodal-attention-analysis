# mmWave HR 恢复、基线个体化与正式分析顺序决策

日期：2026-09-12  
状态：`ACTIVE / DECISION_FROZEN / EXECUTION_PENDING`  
作用：统一毫米波 HR/BR/beat/HRV 的历史证据、当前已修问题、尚未收口问题、3 分钟基线的角色，以及后续正式执行顺序。  
本文件是后续任务的高优先级方法与执行依据；任何新 HR/BR/beat/HRV 任务必须先读本文和 `docs/decisions/2026-09-12_MMWAVE_ECG_HRV_MASTER_ANALYSIS_PLAN.md`。

---

## 0. 为什么需要这份文件

2026-08-29 至 2026-09-12 的毫米波工作已经积累了大量局部审计、修复、ECG/RSP 验证、selector/path replay、timestamp 修正和窗口比较，但这些结果分散在多个 issue、结果目录和历史状态文档中。此前存在以下治理风险：

1. 发现一个问题后只留下局部结论，未来重新阅读时无法快速判断问题是否已修、修到什么程度；
2. 历史最佳 HR≈3.777 bpm、正式 probe HR≈10–11 bpm、20 s diagnostic HR≈19–26 bpm 等不同证据层容易被混为同一指标；
3. 已经证明有效的旧模块（previous-BPM/selector、time-frequency fusion、完整 HR course 等）与当前正式 DLL-time probe 路径没有被系统性逐项核对；
4. 正式实验程序实际包含每名被试 180 s 静息基线，但这段基线主要用于质量/个体内标准化，尚未被完整整合为 HR target/selector 的个体化校准链；
5. 在上游算法链尚未确认完整时直接比较 30 s/60 s，会把“算法缺失”和“窗口长度效应”混在一起；
6. 过去若只看聊天或一两句状态，无法重建数字来自哪批数据、哪套时间语义、哪个脚本和哪个 commit。

因此，本文件冻结新的执行顺序：**先恢复和核清完整已知有效 HR 链，再做剩余失败归因，再把 3 分钟基线用于不依赖 ECG 的个体化校准，之后才允许正式比较 30 s/60 s 和决定正式 HR 路径。**

---

## 1. 实验流程事实：正式实验确实有 3 分钟静息基线

正式采集程序 `kyandi233-dev/FocusWave@formaltest/01-MainProgram/main_experiment_msmf.py` 的真实顺序为：

1. 启动 NIR / RGB / mmWave；
2. 坐姿调整；
3. 记录 `baseline_start`；
4. 运行约 180 s 静息基线，三模态持续同步采集；
5. 记录 `baseline_stop`；
6. cover / instructions / practice；
7. 正式 block；
8. block 间休息与重新坐姿调整；
9. 实验结束。

因此，180 s 基线是正式设计的一部分，不是后补概念。已有分析代码也明确把 `baseline_start`–`baseline_stop` 作为独立时间段，与正式 block 分开裁剪。

### 1.1 目前基线已经被怎样使用

已有 `pipelines/mmwave/run_c2c_personalized_mmwave_calibration.py` 实现过真正的个体内基线标准化：

- 每个 session 读取 180 s pre-task baseline；
- 按 10/30/60 s 与任务相同长度切窗；
- 对每个毫米波特征计算该人的 baseline median / MAD；
- 任务窗口转成相对于该人自己的 robust within-person z；
- 30 s 为预冻结主分析，10/60 s 作为敏感性；
- participant-disjoint folds；
- 不使用 ECG 标签来选 target。

这证明“使用静息基线做个体差异化”并非未实现，而是已经存在一条 feature-level 个体内标准化管线。

### 1.2 目前基线尚未完成的用途

**尚未闭合：把 180 s 基线用于 HR target/bin/channel 的个体化校准与连续性先验。**

当前正式 HR probe producer 并没有明确形成以下闭环：

`180 s baseline → 每人稳定胸部 target 候选/稳定 channel/bin 分布 → 正式任务以个人 baseline target 为锚点 → 允许有限动态更新 → 完整 HR estimator → ECG 独立验证`

这是当前明确的未完成项，不允许再用“已有基线标准化”替代或暗示该 HR calibration 已完成。

---

## 2. 历史最佳 HR≈3.777 bpm 的真实来源与边界

历史最佳 HR 数值：

- HR course MAE ≈ `3.7772146 bpm`；
- 5 calibration sessions；
- 99 valid 60 s HR-course windows；
- producer lineage：`scripts/maintenance/run_hr_course_99_corrected.py → scripts/process_vital_signs_v3_1_1.py`；
- producer commit：`64634159d226ee1ed892d53e56fcf3697fbff9b8`；
- 8-channel complex range-domain DataCube；
- 前约 6000 frames 先选择固定 heart channel/bin；
- corrected spacing=`0.037 m/bin`；
- historical physical gate=`0.30–1.50 m = bins 9–40`；
- `bp_heart` 0.8–2.0 Hz；
- phase unwrap；
- segment correction / consensus / time-course；
- ECG 作为独立 reference 评价。

### 2.1 该数值证明什么

它证明：

> 在这 5 个 calibration sessions、历史 fixed-target、60 s HR-course 和对应 QC 条件下，硬件 + 历史完整算法链可以达到约 3.78 bpm 的窗口级 HR MAE。

它不能直接证明：

- 116 场正式实验全部达到 3.78 bpm；
- probe 前 30 s 达到 3.78 bpm；
- 每个正式被试都有同样稳定的固定 chest target；
- historical 0.30–1.50 m gate 可以未经重新验证直接升级为 current formal physical gate；
- HRV 或逐搏已经有效。

### 2.2 为什么过去没有直接把 3.777 宣布为正式全队列精度

不是因为这条链“无效”，而是因为它与正式 probe 路径同时存在多处条件差异：

- fixed target vs probe/window 动态 selector；
- 60 s HR-course vs probe 前 30 s；
- historical range gate vs current formal selector 语义；
- calibration sessions/QC denominator vs formal 116-session population；
- historical完整 downstream chain vs 某些简化 diagnostic path。

正确处理不是丢弃 3.777，而是把这些差异拆开做受控实验。

---

## 3. 历史已确认的问题、改进和失败路线

### 3.1 已确认：旧距离换算/门控口径曾有错误或不一致

历史 `4.59/4.61 bpm` 已被 corrected-distance calibration 的 `3.777 bpm` 替代为当前历史最佳 reference；旧数值仅保留 historical old-gate provenance。

状态：`DONE / HISTORICAL_CORRECTION_CONFIRMED`

### 3.2 已确认：20 s targeted diagnostic 曾过度简化完整 HR 链

历史/current stage audit 在同一受控窗口上得到：

- raw fixed-target periodogram MAE = `24.902438 bpm`；
- 恢复 existing previous-anchor / `_select_spectral_bpm()` 后 = `13.276285 bpm`；
- 再恢复 existing time/frequency fusion 后 = `8.319342 bpm`；
- old targeted block-local ≈ `26.161212 bpm`；
- historical fixed-target + full existing chain 的 20 s adaptation ≈ `13.916131 bpm`。

解释：

- `previous-BPM/selector` 和 `time-frequency fusion` 是已有项目资产，恢复后能显著降低同窗 HR 误差；
- 因此 19–26 bpm 级别的旧 targeted diagnostic 不能代表完整 producer 的实际能力；
- 这不是证明某个单独阶段具有纯因果效应，因为部分阶段仍是 bundled effect。

状态：`DONE / SUPPORTING_CONTROLLED_EVIDENCE`

### 3.3 已确认：HR 失败不主要等于“雷达根本没有心跳信息”

ECG_VALID retrospective spectral truth audit（325 ECG-valid windows）曾得到：

- `true_peak_available_selected_target_but_wrong_selection` = `102 / 325 = 31.38%`；
- `nearby_target_bin_channel` = `182 / 325 = 56.00%`；
- `true_peak_selected_ecg_bin` = `22 / 325 = 6.77%`；
- `absent_or_weak` = `17 / 325 = 5.23%`；
- `insufficient_coverage_or_reference` = `2 / 325 = 0.62%`。

解释：

- 大量错误来自“当前 target 上有真 HR 候选但选错峰”，或“更好的 HR 信息在附近 bin/channel”；
- 只有少数窗口属于真正 absent/weak；
- ECG 在这里仅作为 retrospective oracle，不进入 production selection。

状态：`DONE / DIAGNOSTIC_FAILURE_ATTRIBUTION_ON_OLD_20S_CONTRACT`

注意：这些比例来自 2026-08-30 的旧 20 s diagnostic contract，**不能直接当成 2026-09-12 DLL-time 30 s 正式链的当前失败比例**。必须后续在新正式链上重新归因。

### 3.4 已确认：恢复已有 selector 可以救回部分 wrong/nearby cases，但没有全部解决

既有 selector replay：

- 102 wrong-selection：恢复 `37 exact + 10 nearby`，仍有 55 未恢复；
- 182 nearby：恢复 `17 exact + 45 nearby`，仍有 120 未恢复。

状态：`DONE / PARTIAL_RECOVERY`

### 3.5 已确认：让 target 轨迹更平滑不等于生理更准确

block-local continuity 诊断降低了 bin hop / channel switch，但 HR MAE 改善很小，BR 还可能变差。结论：不能把“更稳定”自动解释为“更正确”。

状态：`DONE / ROUTE_NOT_PROMOTED`

### 3.6 已确认：selector 前 slow-time mean subtraction 没有足够证据进入正式链

它降低部分近场选中率，却提高 bin/channel switch，未形成共同收益证据，因此 `KEEP_CURRENT_SELECTOR / DO_NOT_ADD_PRESELECTION_PREPROCESSING`。

状态：`DONE / ROUTE_REJECTED_FOR_FORMAL_PROMOTION`

### 3.7 已确认：Python processing timestamp 不是正式 frame membership 应使用的时间

2026-09-12 DLL cutover 已冻结到：

`16729b2ef245f9304dae8674f3bac433bc02e98c`

正式 slicing 使用 DLL host receive/enqueue time；Python processing time 只用于 backlog/processing-delay QC。

状态：`DONE / ENGINEERING_CUTOVER_FROZEN`

---

## 4. 2026-09-12 最新重验结果：时间修复后仍未解决 HR/beat 根因

### 4.1 B1：116-session / 2320-probe 正式 DLL-time replay

- cohort：J72 + E44 = 116 sessions；
- probe keys：2320，five-key 1:1；
- OBSERVED = 2180；
- STRUCTURAL_MISSING = 120；
- QC_FAIL = 20；
- 2180 可计算 probes 中 selected-frame membership 改变 `1847`；
- same-membership deterministic feature regression = `0`；
- 工程回归门：`PASS`；
- no model；HRV fields 保持 null。

解释：DLL cutover 对选帧影响很大，但当输入帧集合相同，特征没有静默漂移，因此变化主要来自正确时间语义改变，而不是算法偷偷变化。

状态：`DONE / ENGINEERING_REPLAY_PASS / PHYSIOLOGY_NOT_PASSED`

### 4.2 B2：5-session / 100-probe ECG/RSP DLL-time 窗口级验证

新 DLL-time：

- 30 s spectral HR MAE = `15.11 bpm`；
- 30 s time HR MAE = `8.97 bpm`；
- 30 s fused HR MAE = `10.46 bpm`；
- 30 s fused medianAE = `7.86 bpm`；
- 30 s fused bias = `-9.02 bpm`；
- 30 s coverage = `100%`；
- historical last-25 s fused MAE = `10.72 bpm`，coverage `98/100`；
- BR MAE = `3.11 breaths/min`；
- BR medianAE = `1.12`；
- BR bias = `-2.26 breaths/min`。

相对旧 Python-time：

- 30 s fused HR `10.83 → 10.46`，仅小幅改善；
- BR `4.17 → 3.11`，改善更明显；
- HR 逐窗 46 improve / 41 worsen / 13 unchanged。

结论：时间修复正确，但**不是 HR 剩余大误差的主要原因**。

状态：`DONE / HR_BR_SUPPORTING_ONLY`

### 4.3 B3：beat / IBI gate

DLL-time ±75 ms：

- ECG beats = `1364`；
- radar beats = `1193`；
- matched = `297`；
- sensitivity = `0.2177`；
- precision = `0.2490`；
- F1 = `0.2323`；
- paired IBI n = `281`；
- IBI MAE median = `48.65 ms`；
- IBI RMSE median = `57.63 ms`；
- missed ECG = `1067`；
- extra radar = `896`。

相对旧 Python-time，beat matching 有改善，但仍远低于 HRV promotion gate。

结论：

- 当前主要问题不是“matched beat 的时间误差稍大”，而是大量 beat 根本未正确匹配；
- 不允许进入正式 RMSSD/SDNN；
- HRV 继续 `BLOCKED`。

状态：`DONE / FAIL / HRV_BLOCKED`

### 4.4 B4：30/25/20 s 简单 HR 窗口候选比较

A–D 候选中：

- A `[0,30)`：coverage 100/100，MAE `5.184`；
- B last-25：coverage 99/100，MAE `5.966`；
- C two-25 median：coverage 99/100，MAE `5.138`；
- D three-20 median：coverage 99/100，MAE `5.576`。

A 因 coverage、session dispersion、解释性更稳，被推荐为 A–D 内部候选；但 `FORMAL_PRODUCER_CHANGE_RECOMMENDED=NO`。

重要审计问题：B4 曾列 `legacy comparator ≈ 3.777`，而严格历史 `3.777` 的原始定义是 5-session/99-valid **60 s** fixed-target HR-course。后续必须明确 B4 的 comparator 是否为真正同一 DLL-time 30 s denominator 上重算，还是历史 reference 数字被带入。未核清前禁止把 `3.777 vs 5.184` 写成严格同窗方法比较。

状态：`DONE / METHOD_COMPARE_COMPLETE / COMPARATOR_LINEAGE_RECHECK_REQUIRED`

---

## 5. 当前核心判断：不是先做 30 s vs 60 s，而是先补完整上游链

新的依赖顺序如下，后续不得颠倒：

### P0 — 当前完整链差异审计（最高优先级）

目标：把“历史最佳完整 HR chain”和“2026-09-12 DLL-time 正式 probe chain”逐阶段对齐，回答：

- 哪些模块已经在 current chain；
- 哪些 historical 有、current 缺；
- 哪些只是 diagnostic path 曾缺，但 current 已恢复；
- 哪些历史模块仅 bundled，不能声称独立有效；
- 哪些参数/门控已被后续证据降级，不能直接恢复。

必须覆盖：

- target/bin/channel selection；
- physical range semantics；
- phase extraction/unwrap；
- heart bandpass；
- VMD/cardiac separation；
- peak detection；
- time HR；
- spectral HR；
- half/double fold；
- previous/reference BPM continuity；
- time/frequency fusion；
- segment correction；
- consensus/time-course；
- final QC/coverage；
- baseline availability and role。

输出必须是逐阶段表：`historical / current / evidence / keep-restore-reject-unproven / exact code path / current test evidence`。

禁止：在 P0 完成前因为“历史看起来好”直接改 formal producer。

### P1 — 恢复/接回已证明有效且兼容的既有模块

仅允许：

- 直接复用现有实现；或
- 对 current DLL-time contract 做最小兼容 patch。

每个恢复项必须在固定 ECG denominator 上做 same-window A/B，且 ECG 不得参与 production target/peak selection。

若拒绝复用已有模块，必须记录 `REUSE_REJECTION_REASON`。

### P2 — 在当前 DLL-time 30 s 正式链上重新做失败归因

旧 20 s truth proportions 仅作为历史线索。必须在 current chain 上重新统计：

- selected target 上真 HR candidate 已存在但选错峰；
- 更好候选在附近 bin；
- 更好候选在附近 channel；
- target/channel 选择错误；
- heartbeat waveform poor/contaminated；
- motion contamination；
- respiratory harmonic / mechanical lock；
- signal absent/weak；
- coverage/timestamp QC；
- 其他 unresolved。

目标：解释当前 `30 s fused HR MAE=10.46` 的主要失败构成，而不是继续沿用旧 20 s failure proportions。

### P3 — 把正式 180 s baseline 用于 HR 个体化校准（新重点）

这是当前明确的未完成主线。

先做 calibration-only / ECG validation，不直接推入 116 场正式结论。

候选必须是 ECG-independent production rule，例如：

- 从 180 s baseline 估计稳定 target/bin/channel 分布；
- 建立每人稳定 target anchor；
- 任务期允许有限邻域更新，而不是每 probe 全空间从零搜索；
- baseline HR/BR plausible range 只能作为不依赖 ECG 的个人先验/质量参考，不能硬把任务 HR 拉向基线；
- baseline phase/motion/power/selection-margin 用于 quality context；
- 保留 current absolute 特征，并区分 within-person deviation。

必须比较：

- current dynamic selector；
- historical-like fixed target（仅合法复用，不依赖 ECG）；
- baseline-personalized anchored selector。

比较必须在相同 DLL-time、相同 30 s、相同 ECG reference、相同 HR estimator 下进行。

### P4 — 冻结完整 HR candidate pipeline

只有 P0–P3 完成后，才能冻结一个或多个完整候选 pipeline。

冻结内容必须包含：

- target policy；
- baseline policy；
- HR estimator；
- window semantics；
- QC；
- fallback；
- provenance；
- ECG-independent production contract。

### P5 — 之后才比较 30 s vs 60 s

窗口长度比较必须建立在同一个完整、冻结的 candidate pipeline 上。

必须回答两个不同问题：

1. measurement accuracy：同窗 radar HR vs ECG，30 s 和 60 s 谁更准；
2. psychological temporal specificity：30 s/60 s 与 probe/behavior 的时间对应差异。

不能把“HR 更准”自动解释成“更适合专注状态”；也不能因为 30 s 是既有主合同就拒绝测试 60 s。

已有旧 diagnostic 线索：

- old 20 s/60 s paired diagnostic 曾得到约 `14.703 vs 5.609 bpm`；
- 该比较受 selector validity / pipeline差异约束，不能当最终窗口结论；
- 它只说明窗口长度可能是重要因素，值得在完整 pipeline 上重新严格测试。

### P6 — ECG/RSP 独立验证与 holdout

开发与验证必须分开：

- ECG 可以用于开发集定位失败、比较候选；
- 一旦规则冻结，必须在独立 holdout session/window 上只做评价；
- 禁止逐窗用 ECG 真值选 peak/target 后再拿同一 ECG 报准确率。

若现有 5 sessions 不足以形成可信 development/holdout split，必须显式报告样本限制，不能伪造独立验证。

### P7 — 才进入 116-session 正式 HR/BR 生理解释和下游注意分析

只有通过相应 physiological admission gate 的变量才可升级；否则：

- HR/BR 继续 supporting；
- motion/phase等非生理绝对值特征按独立 formal spec 判断；
- HRV 保持 blocked 直到 beat-level gate 独立通过。

---

## 6. ECG 的正确角色：必须固定

ECG/RSP 的角色分为：

### 可做

- 给 HR/BR/beat 提供 reference truth；
- 事后判断当前算法错在哪里；
- 在 development subset 上比较已有候选方法；
- 冻结规则后，在独立 holdout 上评价 generalization；
- 形成 error distribution、Bland–Altman、beat matching、IBI evidence。

### 禁止

- 正式运行时读取 ECG；
- 每个窗口根据 ECG HR 选择最接近的 radar peak；
- 用 ECG 选择 target/bin/channel 后再在同一窗口报告“精度”；
- 按 ECG error 搜索 range gate/阈值并在同一 denominator 上宣布验证通过；
- 把 retrospective oracle result 冒充 production algorithm result。

### 正确的“从 ECG 学习”路径

`ECG development evidence → 找到失败模式 → 提出不依赖 ECG 的规则 → 冻结规则 → independent ECG holdout evaluation → formal promotion decision`

ECG 并非“不能学”，而是不能发生答案泄漏。

---

## 7. 结果与问题状态总表

| 项目 | 当前结论 | 状态 | 是否已解决 |
|---|---|---|---|
| Python-time → DLL-time | 正式 frame membership 已切到 DLL host receive time | DONE | 是 |
| Issue #33 probe contract | endpoint/block/QC/provenance 修复 | DONE | 是 |
| 116/2320 DLL replay | 工程回归 PASS；1847/2180 membership changed | DONE | 是 |
| HR窗口级准确性 | 30 s fused MAE 10.46，bias -9.02 | SUPPORTING_ONLY | 否，准确性仍不足 |
| BR窗口级准确性 | MAE 3.11 breaths/min | SUPPORTING_ONLY | 部分 |
| beat matching | sens 0.218 / precision 0.249 @75ms | FAIL | 否 |
| HRV | beat gate 未通过 | BLOCKED | 否 |
| historical 3.777 lineage | 来源与边界已查清 | DONE | 是 |
| historical完整链 vs current链差异 | 有历史 stage audit，但未对 2026-09-12 current chain 完整逐阶段重新闭合 | ACTIVE P0 | 否 |
| current 10.46 failure composition | 旧 20s 有 truth audit，新 DLL 30s 尚未完整重做 | ACTIVE P2 | 否 |
| 180s baseline feature normalization | 已有实现 | DONE | 是 |
| 180s baseline HR target calibration | 尚未形成 current formal candidate | ACTIVE P3 | 否 |
| 30s vs 60s最终比较 | 旧 diagnostic 有线索，完整链 final comparison 未做 | WAIT P5 | 否 |
| B4 legacy 3.777 comparator 同窗性 | 需重核 lineage | BLOCKED_BY_AUDIT | 否 |

---

## 8. 后续每个任务的强制交付格式

从本决策起，任何毫米波任务不允许只在聊天中报告一两句结论。

每个任务必须在同一工作周期至少交付：

1. `REPORT.md` 或 canonical decision record：
   - 问题；
   - 为什么要做；
   - 复用了哪些历史资产；
   - 数据 scope / session / window / denominator；
   - timestamp/window semantics；
   - 脚本与 commit；
   - 输入；
   - 输出；
   - 关键数值；
   - paired comparison；
   - 解释；
   - 决策；
   - 未证明内容；
   - remaining problems；
   - next dependency。
2. manifest：脚本、commit、输入、输出、hash、参数；
3. 必要的逐窗/逐 session 表；敏感数据或大型数据可 local-only，但 GitHub 必须记录路径、row count/hash/摘要；
4. 图表若产生，必须说明它在证明什么，不允许 orphan figure；
5. update high-visibility pointer：issue / PROJECT_STATUS / RESULT_INDEX / canonical current-state 至少一个；
6. 明确 `DONE / PARTIAL / BLOCKED / SUPERSEDED / DIAGNOSTIC_ONLY / FORMAL_READY`。

### 禁止

- “发现了问题”就算完成；
- 只放一个结果目录但没有总报告；
- 只写“PASS”而不写数据和验收依据；
- 只在聊天里写本地路径；
- 新结果覆盖旧结果而不留 lineage；
- 在已知 pipeline 不完整时直接做 final 参数/窗口比较；
- 后续智能体重新从聊天猜当前进度。

---

## 9. 立即执行顺序

当前主线顺序冻结为：

`P0 当前完整链差异审计`  
→ `P1 恢复已证明有效且兼容的既有模块`  
→ `P2 DLL-time 30 s 当前链失败归因`  
→ `P3 180 s baseline 个体化 HR target/calibration`  
→ `P4 冻结完整 HR candidate pipeline`  
→ `P5 同一完整 pipeline 上 30 s vs 60 s`  
→ `P6 ECG independent holdout validation`  
→ `P7 116-session formal promotion / downstream`

可以并行：

- P0 中的代码 lineage mapping 与历史结果/manifest 核验；
- P2 的诊断脚本准备可以在 P0 后半段进行，但 final failure attribution 必须使用 P1 后冻结的 candidate/current chain；
- baseline feature inventory 可以与 P0 并行，但 P3 的 HR target experiment 设计必须等 P0/P1 明确 target selector contract。

不得提前：

- P5 不能先于 P0–P4；
- P7 不能先于 physiological admission decision；
- HRV 不能绕过 B3 beat-level FAIL。

---

## 10. 当前决策

`DECISION = REOPEN_HR_OPTIMIZATION_AS_CONTROLLED_RECOVERY, NOT ALGORITHM_SEARCH`

含义：

- 不是重新发明一套毫米波算法；
- 不是无限算法海选；
- 是把历史已证明有价值的项目资产、正式 180 s baseline、当前 DLL-time contract 和 ECG/RSP reference 重新闭成一条可验证的正式候选链；
- 所有改进先在 calibration/reference 层验证，不得直接污染正式注意标签；
- 当前 10.46 bpm 不被接受为“已经做到最好”，也不被自动宣判为不可用；
- historical 3.777 不被直接外推为正式精度，但必须作为能力上界线索和 recovery baseline 被严肃复用；
- 30 s/60 s 不是当前第一步，窗口比较必须后置到完整 candidate pipeline 冻结之后。

当前项目状态：`PARTIAL / ACTIVE RECOVERY`。
