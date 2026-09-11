# FocusWave 毫米波 × ECG/RSP × 外部数据集 × HRV 总体分析计划

日期：2026-09-12  
状态：`ACTIVE MASTER PLAN`  
适用范围：正式实验毫米波、ECG/RSP 生理金标准验证、外部 VS_DATASET、HR/BR/IBI/HRV、毫米波下游注意状态与多模态分析。

---

## 0. 本文解决什么问题

本文把目前分散在 Issue #33、Issue #34、ECG 验证、HRV gate、外部 benchmark 和正式注意状态分析中的任务统一为一条可执行主线，并明确：

1. 哪些已经完成；
2. 哪些只是历史结果，必须重算；
3. 哪些工作可以并行；
4. 哪些工作存在先后依赖，不能提前；
5. 哪些参数当前只能视为已有实现，不得误称为已经有文献依据或正式最优值；
6. 如何从“HR/BR supporting”逐步判断是否有资格进入 IBI/HRV；
7. 如何避免在修复时间轴时回退 Issue #33 已经修好的代码。

本文是执行总图，不替代已有详细报告和历史结果。

---

## 1. 研究问题分层：四条证据链不能混在一起

### 1.1 正式实验链：毫米波和注意状态有什么关系？

正式实验的目的不是先证明毫米波“医学级测量”，而是检验毫米波特征是否与任务中的注意/警觉状态及行为表现有关。

当前固定 cohort：

- J：72 sessions
- E：44 sessions
- 总计：116 sessions
- 每场 20 probes
- 总计：2320 probe keys

正式实验毫米波输出包括：

- HR frequency / time / fused；
- BR；
- HR confidence；
- HR usable ratio；
- motion proxy；
- phase stability；
- selected bin/channel；
- distance proxy；
- timestamp coverage；
- QC / missing / provenance。

其中 HR/BR 当前仍是 `SUPPORTING/HOLD`；IBI、RMSSD、SDNN 当前不属于正式可用特征。

正式下游包括：

- Q1 四类状态关联；
- Q2 有序/二元警觉关联；
- 行为效标；
- 参与者内/间分解；
- 高运动排除敏感性；
- RGB ↔ mmWave 对照；
- 所有包含 mmWave 的多模态模型、LOSO、增量和边际贡献。

### 1.2 ECG/RSP 验证链：毫米波生理量到底测得准不准？

ECG/RSP 的角色是生理金标准，而不是注意状态标签。

分两层：

- 窗口级：Radar HR/BR vs 同时间 ECG/RSP；
- 逐搏级：Radar heartbeat timestamps vs ECG R-peaks，进一步评价 IBI，再决定 HRV 是否有资格进入。

ECG/RSP 的 event-marker → BIOPAC sample affine mapping 是独立 reference 链；Issue #34 改的是毫米波时间轴，不应随意修改 ECG detector、RSP reference 或 marker 映射。

### 1.3 外部数据集链：算法离开 FocusWave 自有数据还能不能工作？

VS_DATASET 使用自己的：

- `Radar.t_frame`
- Mindray ECG sampling time

不依赖 FocusWave 正式 `timestamps.csv`，因此不受 Python→DLL 正式 probe 时间轴问题影响。

它用于：

- beat detection；
- IBI；
- HR；
- RMSSD / SDNN；
- 项目 baseline 与 VitalSense route 的独立比较。

它提供外部效度证据，但不能替代 FocusWave 自己的 ECG/RSP 验证。

### 1.4 时间尺度链：30 s 指标到底代表什么？

这和“Radar 测得准不准”是另一个问题。

需要分别回答：

- Radar 30 s vs ECG 同一个 30 s：测量准确性；
- ECG 30 s vs ECG 60/120/300 s：短窗口代表性；
- 短窗口指标 vs probe/behavior：心理学使用价值。

不能把这三个问题混为一个 HRV 结论。

---

## 2. 当前已经确定的时间轴合同

### 2.1 正式 CSV 三列语义

正式历史 CSV 已知为：

1. frame index；
2. DLL host receive/enqueue Unix time；
3. Python worker processing/write Unix time。

正式科学切窗应使用第 2 列，即 `timestamps[:,1]`。

第 3 列不再用于正式 frame membership，但保留用于：

- `processing_delay_ms`；
- worker backlog；
- NPZ compression / IO stall；
- queue latency；
- 采集 QC。

### 2.2 不能误称第 2 列为何物

第 2 列不是：

- radar hardware timestamp；
- device frame-start time；
- chip RTC frame-start。

其正确语义是：

`DLL host receive/enqueue time`

现有正式采集未持久化真正的 `mmw_frame_start_timestamp()` RTC，因此不能从历史数据倒推出硬件帧开始绝对时间。

### 2.3 probe window 合同

正式 probe 分析窗口继续保持：

`[window_effective_start, probe_onset)`

其中：

`window_effective_start = max(nominal pre-30s start, block_start)`

必须保留 block start / block stop 门控；probe onset 精确时刻的帧不进入 probe 前窗口。

---

## 3. Issue #33 已经修好的内容：本轮禁止回退

当前任何 DLL-time 修改必须建立在 Issue #33 正确基线上，不允许用旧 adapter 重写。

必须保持不变：

- frozen cohort / five-key identity；
- J72 + E44 = 116 sessions；
- 2320 probe keys；
- `beh/master_timeline.csv` 的 block_start / block_stop 来源；
- `[effective_start, probe_onset)`；
- NPZ / timestamp count 和 shape/order QC；
- HR producer course；
- 当前 `window_s=25 s`、`step_s=5 s` 实现；
- HR freq/time/fused median aggregation；
- mean confidence aggregation；
- `signal_quality.usable_ratio`；
- BR estimator；
- selector；
- VMD；
- distance/bin/channel 逻辑；
- label；
- HRV fields 仍为空；
- provenance 在写表前完整生成。

重要：这里“保持不变”仅表示 timestamp cutover 任务不能顺手改变这些内容，不表示 25/5 等参数已经被永久证明为最佳方法。

---

## 4. 当前 DLL-time cutover 状态

当前 isolated minimal patch 已完成以下内容：

- 严格基于 `b2fddca2542859f62d5f4b57f1b4fdecd54a5b4c`；
- 正式 slicing 改为 DLL host receive 时间；
- Python processing time 仅保留 processing-delay QC；
- Issue #33 regression tests 通过；
- DLL timestamp 专属 tests 通过；
- 未运行正式 116 场；
- 未提交/推送该本地 patch。

正式进入 full run 前只允许做 provenance/test 收尾，不允许改变科学算法。

需完成：

1. endpoint audit 名称/语义不能把 DLL endpoint hit 仍叫作旧 Python-time `old_endpoint_hit`；建议同时保留：
   - `legacy_python_endpoint_hit`
   - `formal_dll_endpoint_hit`
2. pipeline version 明确标记 DLL cutover；
3. regression test 显式锁定 HR course `window_s=25.0`、`step_s=5.0`，防止未来无意回退。

完成后才能给出：

`PRODUCTION_CUTOVER_READY = YES`

---

## 5. 工作流 A：真实 frame-rate / timing quality 审计

### 5.1 为什么必须做

当前 producer 以 `FS=100 Hz` 运行，但人工观察中部分记录似乎每秒只有 90+ frames。

“平均不到 100”本身不能直接判定 HRV 不可行，关键要区分：

- 稳定但实际约 95–99 Hz；
- 目标 100 Hz，但存在间歇性 frame drop / gap；
- Python processing/整数秒统计造成的表观帧率下降，而 DLL 帧间隔实际接近 10 ms。

对于 HR，轻微误差可能仍可接受；对于 beat timing / IBI / HRV，间歇性时间空洞更危险。

### 5.2 需要输出的审计量

基于 DLL host receive 时间，固定 116 场只读统计：

- frame interval median；
- P90 / P95 / P99；
- implied effective frame rate；
- 8–12 ms interval 比例；
- >15 ms / >20 ms / >30 ms / >50 ms 比例；
- frame index gap count / rate；
- longest consecutive gap；
- session-level distribution；
- J/E 是否系统不同；
- processing delay 分布作为软件 QC；
- 是否存在“真实 DLL 时间稳定、Python 时间卡顿”的典型段。

### 5.3 输出结论必须回答

1. `FS=100` 是否可视为近似充分；
2. 是否需要对 HRV 分支做 timestamp-aware / resampling 处理；
3. 是否存在必须排除或单独标记的 frame-gap 段；
4. 不能因为平均 FPS <100 就直接改 producer 的 `FS`。

本任务是只读审计，不改正式 producer。

---

## 6. 工作流 B：116/2320 DLL-time 正式重放

前置依赖：DLL cutover final review PASS。

### 6.1 目标

用完全相同的：

- cohort；
- raw data；
- block boundary；
- estimator；
- selector；
- VMD；
- feature schema；
- labels；

只把正式 frame membership 从 Python processing time 切换为 DLL host receive time。

### 6.2 必须验收

- 116 sessions；
- 2320 probe keys 1:1；
- five-key membership 不变；
- structural missing/QC 变化有原因；
- old/new selected frame slice 对比；
- frame membership change count；
- input slice hash；
- HR/BR/motion/phase/bin/channel/coverage 的 paired diff；
- 如果 frame membership 相同而 feature 改变，视为 regression，立即 STOP；
- old outputs 不覆盖；
- 新 output 独立目录与 manifest；
- 不训练模型。

### 6.3 该任务结束后才能进入

- 新正式 mmWave Q1/Q2；
- behavior association；
- within/between；
- high-motion sensitivity；
- RGB↔mmWave；
- 包含 mmWave 的 multimodal / LOSO / increment / marginal contribution。

---

## 7. 工作流 C：ECG/RSP 窗口级 HR/BR DLL-time 重验

前置依赖：DLL cutover code PASS；可与 116/2320 full run 并行，不需要等正式注意模型。

### 7.1 保持不变

- ECG detector；
- RSP reference；
- block-local event → BIOPAC sample affine mapping；
- subject/session inclusion；
- probe onset；
- gold-standard preprocessing；
- 现有评价指标定义。

### 7.2 唯一必须改变

毫米波窗口的 frame selection 使用 DLL host receive time，而不是 Python processing time。

### 7.3 输出

重算历史 5 可估场次 / 100 probe windows：

- 30 s HR：MAE / medianAE / bias / distribution；
- 25 s HR：同上；
- spectral / time / fused；
- BR vs RSP；
- session-level heterogeneity；
- selected bin/channel 与大误差的关系；
- old Python-time vs new DLL-time paired comparison。

历史数值只作为 comparator，不直接沿用为新结论。

---

## 8. 工作流 D：逐搏 ECG gate / IBI / HRV 可行性重验

前置依赖：DLL cutover code PASS；可与工作流 B/C 并行。

### 8.1 第一阶段必须先回答 beat timing，不先算正式 HRV

保持：

- 同一 radar beat detector；
- 同一 ECG detector；
- 同一 block windows；
- 同一 matching 规则；
- 同一预定义 gate；

只把 radar absolute timing 映射改为 DLL host receive time。

输出：

- ECG beat count；
- radar beat count；
- matched count；
- precision / recall / F1；
- tolerance sensitivity；
- timing bias / MAE；
- IBI MAE / RMSE / bias；
- session/block heterogeneity；
- 和 frame-gap、motion、target-bin error 的关系。

### 8.2 HRV 状态不能预判

DLL-time 重验后才允许三种结果：

- `PASS`：逐搏证据达到预定义标准，进入 HRV metric validation；
- `FAIL / HRV_BLOCKED`：继续 blocked；
- `INDETERMINATE`：数据不足或 timing/gap 不可判定。

不能因为旧结果 blocked 就预设新结果仍 blocked；也不能因为 DLL 时间更合理就预设一定通过。

### 8.3 如果 beat gate 通过

再进入：

`beat timestamps → IBI sequence → RMSSD / SDNN`

第一优先级：

- RMSSD；
- SDNN。

LF/HF 不作为主 HRV 指标，也不解释为简单“交感/副交感平衡”。

---

## 9. 工作流 E：HR course 25 s / 5 s 方法审计

这是独立的方法问题，不能混入 timestamp cutover。

### 9.1 当前事实

现有 producer `estimate_hr_time_course()` 默认：

- `window_s=25.0`
- `step_s=5.0`

该设置是已有工程实现；当前仓库证据不能证明“5 s 是由某篇论文确定的领域标准”。

### 9.2 当前 30 s probe 的实现风险

当前函数按中心点生成 course，再将边界窗口 clip 回有效范围。在恰好 30 s 的 probe 里，可能重复使用相同的 0–25 s / 5–30 s 数据段，因此多个 course points 并不等于多个独立局部窗口。

这可能影响：

- median 的权重；
- mean confidence；
- usable ratio。

### 9.3 正确审计方式

只使用 ECG reference 来比较预先定义的候选，不看 Q1/Q2，不看下游 AUC，不根据注意分类效果选参数。

候选可以包括：

- 整个 30 s 单次 HR；
- 末尾 25 s；
- 真正 unique 的 25 s / 5 s windows；
- 20 s / 5 s windows；
- 其他候选仅在有明确方法依据时增加。

输出：

- HR MAE / bias / coverage；
- session robustness；
- 是否存在 edge-duplication bias；
- 是否建议维持或修改正式 HR course。

此任务可以与正式 DLL full run 并行，但在审计完成前不得改变正在执行的 timestamp-only formal run。

---

## 10. 工作流 F：短时 HRV 时间尺度验证

前置依赖：不需要 radar beat gate 通过；可以先用 ECG reference 独立研究。

目标：回答“30 s HRV 代表什么”，不是回答“Radar 测得准不准”。

建议在同一 ECG 记录上比较：

- 30 s；
- 60 s；
- 120 s；
- 可用时 300 s。

优先指标：

- RMSSD；
- SDNN。

比较：

- absolute difference；
- relative difference；
- Bland–Altman；
- ICC / agreement；
- 随 time-in-block / fatigue / vigilance 是否系统变化。

解释边界：

- 短窗和长窗不一致，不等于传感器测不准；
- 可能只是被试生理状态在变化，30 s 反映的是更局部/瞬时状态；
- FocusWave 若目标是瞬时注意状态，短窗变化可能有意义，但不能自动称为标准 5-min HRV。

---

## 11. 工作流 G：外部 VS_DATASET

Issue #34 不要求重跑现有 C1b benchmark，因为其时间基准独立于 FocusWave 正式 probe 时间轴。

当前用途：

- 保留现有 benchmark 作为独立算法证据；
- 如果后续开发新的 radar beat / IBI / HRV 方法，则把 VS_DATASET 作为独立外部评价集；
- 不能为了提高 FocusWave HRV 结果去反复调外部 test set；
- 不用外部数据的好结果替代 FocusWave 自身 ECG gate。

---

## 12. 工作流 H：正式注意状态与多模态重算

前置依赖：工作流 B 的新 DLL-time mmWave formal table PASS。

必须重算：

1. mmWave 描述统计；
2. Q1；
3. Q2；
4. behavior association；
5. within / between participant decomposition；
6. high-motion sensitivity；
7. report 5.4 mmWave summaries / plots；
8. RGB ↔ mmWave comparisons；
9. 所有包含 mmWave 的 multimodal combinations；
10. LOSO / participant-disjoint performance；
11. mmWave increment；
12. marginal contribution 中所有涉及 mmWave 的组合。

不因 Issue #34 自动重算：

- pure Behavior；
- pure NIR；
- pure RGB；
- 完全不依赖 mmWave 的既有分析。

如果未来 HRV 通过 measurement gate，再作为“新增候选特征”单独进入该层；不得为了注意分类效果倒过来调整 HRV detector。

---

## 13. 可并行关系

### Wave 0：立即可并行

A0. DLL cutover provenance/test 最终收尾  
A1. DLL frame-rate / frame-gap 只读审计  
A2. 历史 `<1.2 ms` 双机同步来源只读 provenance 审计  
A3. HR 25/5 方法代码/设计只读审计与候选协议冻结  
A4. ECG-only 30/60/120/300 s HRV 时间尺度分析协议设计

其中 A1/A2/A3/A4 不能修改 formal producer。

### Wave 1：DLL cutover `READY=YES` 后可并行

B1. 116/2320 DLL-time formal replay  
B2. ECG/RSP 100-window HR/BR DLL-time rerun  
B3. 5-session / 16-block beat-level DLL-time rerun

B1/B2/B3 可以同时运行，因为目标和输出目录独立。

### Wave 2：依赖结果分支

如果 B3 beat gate 不通过：

- HRV 继续 blocked；
- 做 failure decomposition；
- 判断是 frame timing、target selection、heartbeat waveform 还是 detector 问题；
- 不进入正式 RMSSD/SDNN。

如果 B3 通过：

- 进入 IBI validation；
- 再验证 RMSSD/SDNN；
- 再结合 A4/F 的短窗时间尺度解释。

同时，B1 formal table PASS 后即可启动 H 的所有 mmWave-dependent downstream analyses，不需要等待 HRV 研究完成，因为当前 formal mmWave 本来就不包含 HRV。

### Wave 3：最后整合

- 更新正式报告 mmWave 章节；
- 更新 ECG/RSP validation；
- 更新 HRV 状态；
- 更新多模态结果；
- 区分 measurement validity、construct validity 和 predictive utility；
- 所有历史 Python-time 结果明确降级为 historical comparator。

---

## 14. 执行优先级

最高优先：

1. DLL cutover 最终 ready；
2. frame-rate / gap audit；
3. 116/2320 formal replay；
4. ECG HR/BR 和 beat-level rerun。

第二优先：

5. HR 25/5 方法审计；
6. ECG-only short-HRV timescale；
7. beat gate 通过后的 IBI/RMSSD/SDNN。

第三优先：

8. mmWave-dependent downstream attention analysis；
9. multimodal rerun；
10. final report integration。

外部 VS_DATASET 当前不因 Issue #34 重跑，只在新 HRV method 形成后作为独立外部验证。

---

## 15. 硬性禁止项

除非有新的单独授权，不允许：

- 为了修 timestamp 重写 J/E adapter；
- 修改 frozen cohort；
- 自动纳入额外 E sessions；
- 修改 labels；
- 修改 Behavior/NIR/RGB 结果；
- 修改 HR/BR estimator；
- 修改 VMD / selector / distance gate；
- 用 Q1/Q2 或 AUC 选择 HR/HRV 算法参数；
- 把 DLL host time 称为 hardware frame-start；
- 从 25/5 HR course 直接推导 HRV；
- 在 beat gate 通过前写入正式 RMSSD/SDNN；
- 把 LF/HF 简化解释为“交感/副交感平衡”；
- 覆盖旧 formal outputs；
- 把历史 Python-time 结果冒充新的 final result。

---

## 16. 最终目标状态

最终希望得到四个独立、可审计的结论：

### A. Timing validity

正式毫米波 probe/window 与行为时间轴使用最合理的现有 host-time source，并明确其边界和实际 frame-rate/gap 质量。

### B. Physiological validity

HR/BR 有独立 ECG/RSP 证据；IBI/HRV 是否通过由 beat-level gate 决定，而不是由注意预测结果决定。

### C. Construct / behavioral validity

通过 Q1/Q2、behavior、within/between、motion sensitivity 评估毫米波特征和注意/警觉构念之间的关系。

### D. Generalization

外部 VS_DATASET 用于独立验证 beat/IBI/HRV 算法是否具有跨数据集可迁移性。

四层证据不能互相替代，但可以共同构成 FocusWave 毫米波模块完整证据链。
