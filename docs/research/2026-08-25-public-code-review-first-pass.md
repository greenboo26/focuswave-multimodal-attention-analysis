# 2026-08-25 公开代码审计第一轮结果

## 状态

本轮已从 README 层进入代码级阅读，覆盖：

- `AnirudhBHarish/CogPhys`
- `Rc-W024/VitalSense2024`
- `Rc-W024/VS_DATASET`
- `RadarHRSensing/Radar-APLANC`
- `zhang123-1999/SpectroTransNet-HRV`

本文件记录“哪些结论可用于本项目”“哪些只能当算法原型”“哪些公开代码存在实现风险”。

---

## 1. CogPhys：最适合作为认知状态多模态系统参照，但不能误写成 radar-HRV 证据

### 已确认

CogPhys 的 cognitive-load pipeline 是实际可运行代码，不是示意：

- `cognitive_load/train/data_loader.py`
- `cognitive_load/train/train_ml_models.py`
- `cognitive_load/train/run_experiments.py`
- `cognitive_load/train/utils.py`

数据按 participant ID 使用预定义 train/valid/test fold；标准化器由 sklearn `Pipeline` 在训练集拟合，基础防泄漏结构可参考。

认知负荷分类输入是远程/接触式生理波形组合：remote PPG、remote respiration、blink，以及 contact PPG/respiration 对照。代码从 PPG 中提取 HR、IBI、RMSSD、SDNN、pNN50、SD1/SD2 等，也从 respiration 中提取主频、功率、谱熵，从 blink 中提取频率/持续时间/间隔等。

### 重要边界修正

CogPhys 中 **radar 主要用于 remote respiration waveform**；HRV 主要来自 remote/contact PPG，而不是 radar HRV。

因此 CogPhys 可以支持：

- 非接触多模态生理特征可以预测 cognitive load；
- radar respiration 是有效组成部分；
- remote PPG/respiration/blink 的组合与消融值得借鉴；
- participant-level split 和 multimodal pipeline 值得复用。

但它 **不能单独作为“radar HRV -> cognitive load”证据**。

### 代码风险/注意

当前公开 `utils.py` 的标签代码有“mental demand only for test”式实验痕迹，使用 participant 内中位数二分；因此不能默认 GitHub 当前分支与论文最终全部结果完全同构。正式复现应对照论文/补充材料。

---

## 2. VitalSense2024：当前最值得迁移的 beat/IBI 传统算法基线

### 已确认 pipeline

`main.m` 的核心链条：

1. FMCW range FFT；
2. 选目标 range bin；
3. unwrap phase -> 毫米级 vital displacement；
4. FIR low-pass（示例 cutoff 0.3 Hz）得到 respiration；
5. `cardiac = vital - respiration`；
6. cardiac spectrum + `HRestim.m` 的 autocorrelation/频谱候选得到初始心搏周期；
7. 用初始周期切出多个 cardiac pulse；
8. 平均得到个人化 pulse template；
9. 翻转模板构造 adaptive matched filter；
10. matched-filter output 上找 heartbeat peaks；
11. 用 peak interval 得到 HR，并可进一步得到 IBI。

这比本项目当前“频谱中找 HR 候选峰”更接近 HRV 所需的 beat-level 路线。

### 可以迁移

- respiration / cardiac 分离的基线框架；
- FFT + autocorrelation 联合估计初始周期；
- 个体自适应 pulse template；
- adaptive matched filter；
- heartbeat peak timing / interval 结构。

### 不能照抄

- 原实现从单个时刻/单个峰完成 range 选择；本项目已证明累计峰或单时刻峰不能当稳定人体锁定证据；必须保留我们自己的 target-lock gate。
- `0.3 Hz` 呼吸低通、`fir1(300)`、频率边界都与 122 GHz/3 ms frame 示例绑定，不能直接搬到 RS6240。
- 对 missed peak 的处理较粗糙（大间隔按 mean+2SD 删除），不能直接作为正式 IBI QC。
- 仅做低通减法不能保证去掉 2×/3× respiration harmonic；本项目必须额外加入 harmonic rejection/ambiguity flag。

---

## 3. VS_DATASET：优先级最高的外部 ground-truth benchmark

### 已确认

这是 `Rc-W024` 官方仓库，对应 2026 Scientific Data 数据论文，MIT 代码许可。Healthy cohort：24 subjects，每人 Resting + Apnea，总计约 4 min；Radar 与 Mindray reference 分文件同步提供。

公开代码至少包括：

- `VS_separation.m`
- `TechValidation.m`
- `VitalSig_HUGTiP.m`
- `PlotVS.m`
- technical-validation CSV/MAT

`VS_separation.m` 明确读取 radar `VitalSig` 和 ECG lead II，使用相同的 respiration/cardio separation，并可直接对照 radar cardiac residual 与 ECG。

### 对本项目的用途

建立“外部验证双分叉”：

- 若我们的 cardiac/beat 算法在 VS_DATASET + ECG 上可以复现，但在 RS6240 上失败 -> 优先怀疑 RS6240 当前采集、目标锁定、姿态/距离、SNR 或 domain shift；
- 若在 VS_DATASET 上也失败 -> 优先修算法实现，不能继续用本项目数据调参自证。

### 代码风险

`TechValidation.m` 中字段 `maxCorr` 实际被赋值为 `lag_max`（最大相关所在的 lag index），并非 `max(c)` 的相关系数；因此公开 technical-validation 脚本存在变量命名/统计实现问题，不能无审计照搬。

---

## 4. Radar-APLANC：弱监督思想很有价值，但当前公开代码需要修复后再用

### 核心方法已确认

公开实现构造：

- positive RF：目标 range 附近；
- negative RF：远离目标的 noise range；
- traditional radar phase / pseudo waveform；
- 模型输出转换到 HR 生理频段内的归一化 PSD；
- contrastive loss 让 positive output 接近伪/传统心搏 PSD，同时远离 noise-range output。

训练配置中使用约 10 s PSD 子窗，并限定 HR band。

### 对本项目特别有价值

本项目比原仓库拥有更多可用于弱监督筛选的信息：

- 已有 target-lock audit；
- 8-channel spatial consistency；
- RGB motion gate；
- 后续可加入 NIR/行为时间窗口；
- respiration-harmonic ambiguity flag。

因此可以构建质量更高的 pseudo-label acceptance gate，而不是简单把能量最大 range 当正样本。

### 公开实现中的关键疑点

`data/datasets.py` 会加载 `pseudo.npy`，并返回 `(Pseudo, p_rf, n_rf, traditional_data_f)`；但是当前 `rf/train.py` 虽然对 `pseudo` 做了 normalize，真正传入 `ContrastLoss` 的却是 `t_rf/traditional_data_f`，而非 `pseudo`。

即：README 强调的 augmented pseudo-label stage，在当前公开 `train.py` 中没有明显接入 loss。

此外，checkpoint 选择调用 validation evaluator，而公开数据包含真实 PPG，因此需要进一步检查“训练无 GT”与“模型选择是否用了 GT”的严格边界。

结论：**借方法，不直接复制仓库结果；若采用，需要修复并重新审计训练/验证独立性。**

---

## 5. SpectroTransNet-HRV：IHR -> IPFM -> HRV 思路值得做原型，但当前结果不能当正式基准

### 有价值的思路

代码完整实现：

- radar phase bandpass；
- 10 s CWT spectrogram；
- ECG R-peaks -> frame-wise instantaneous HR (IHR) curve；
- CNN/Transformer 预测 IHR；
- 把 IHR 积分成 phase，整数 crossing 重建 beat times；
- beat times -> RR；
- RR -> RMSSD/SDNN/pNN50/SD1/SD2。

这提供另一条不依赖“直接从 radar raw waveform 每个峰找 beat”的路线：

`radar -> continuous IHR trajectory -> IPFM beat reconstruction -> IBI/HRV`。

### 关键可靠性问题

1. README 自己注明是 research-project / technical-report draft，不是正式发表论文。
2. `RadarSpectrogramDataset` 当前代码按 `dataset_index.csv` 行号前 80%/后 20% 切分，没有按 subject ID group split；`test_subjects` 参数未使用。
3. 数据用 10 s window、1 s stride，若 CSV 顺序保持时间邻接，行级 split 可能造成高度重叠窗口泄漏。
4. HRV 在单个 10 s IHR curve 上通过少量重建 RR 直接计算；这不应作为本项目正式 60 s/长窗 HRV 有效性的依据。

结论：**保留 CWT/IHR/IPFM 架构作为 prototype，重新做 person/session split 和长窗口 HRV aggregation 后才可比较。**

---

# 第一轮对本项目的直接决策

## A. 不再只扩大旧 HR/BR FFT 峰分析

下一步毫米波心脏路线应升级到 beat-level benchmark，而不是继续增加“某个窗口 HR 峰是多少”的样本数量。

## B. 第一优先实现：外部 ECG benchmark harness

建议建立独立实验入口，例如：

`experiments/external_vitalsense_benchmark/`

流程：

`VS_DATASET radar + ECG`
-> `VitalSense-style separation`
-> `initial HR period`
-> `adaptive matched filter`
-> `radar beat timestamps`
-> 与 ECG R-peaks 对齐
-> 输出 beat timing / IBI / HR / HRV error。

至少报告：

- beat precision / recall / F1（预先固定时间容差）；
- beat timing MAE；
- IBI MAE / correlation；
- HR MAE；
- 在足够长窗口上的 RMSSD/SDNN error；
- respiration-harmonic failure rate。

## C. 第二优先：RS6240 adapter

仅替换传感器前端，不降低后端验证标准：

`RS6240 target-locked multi-channel phase`
-> adaptive respiration extraction
-> harmonic-aware cardiac residual
-> initial period
-> matched filter / learned heartbeat representation
-> 8-channel consensus beat candidates
-> IBI QC。

保留现有 target-lock、RGB motion gate、Q0 质量描述符，不能退回“全场能量最大 range”。

## D. 同时建立 radar-only attention baseline，但与 HRV 路线并行而非替代

输入组至少做：

1. respiration-only；
2. cardiac/HR candidate；
3. validated HRV（仅通过 beat QC 的窗口）；
4. raw/micromotion descriptors；
5. all-radar。

目标先用 thought probe / 行为标签；身份恢复前只能叫 recording-session split，恢复后必须 person-level evaluation。

## E. 多模态保底/教师路线

参考 CogPhys：

- NIR pupil/blink；
- radar respiration/cardiac；
- behavior；
- RGB motion/pose quality；
- thought probe。

先建立 multimodal upper-bound；若明显优于 radar-only，再尝试 teacher -> radar-only student，而不是直接接受部署必须依赖摄像头。

---

# 下一轮阅读顺序

1. VS_DATASET 的 `VitalSig_HUGTiP.m` 与公开数据字段；
2. VitalSense 主算法完整 peak reconstruction 与原论文方法；
3. Radar-APLANC `IQ_to_PhaseAngle.py`、`model.py`、`eval_RHB`，确认训练/验证 GT 边界；
4. CogPhys 论文/补充材料与 GitHub 分支逐项对齐，确认最终 cognitive-load feature set；
5. EquiPleth / FusionPhys，审计多模态同步和 fusion；
6. mmJEPA-ECG，评估 self-supervised radar pretraining 是否能接入现有 RS6240 数据。

## 当前结论

公开资源足以支撑一条“先在带 ECG 的公开 radar 数据上证明 beat/IBI 算法，再迁移 RS6240；与此同时用现有 multimodal 数据建立 radar-only 与 multimodal attention model”的双线研发路径。

这比继续只在本项目四个 HR/BR 候选分片上调峰更有信息增益，也不会削弱 HRV 在项目理论链中的核心位置。
