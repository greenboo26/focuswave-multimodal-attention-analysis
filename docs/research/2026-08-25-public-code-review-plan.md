# 2026-08-25 公开论文/代码源与代码审计计划

## 目标

本轮不以“搜到多少仓库”为目标，而是建立可复现的外部技术基线，回答三个项目级问题：

1. RS6240 毫米波能否从现有原始数据中稳定恢复 cardiac component、beat/IBI、HR/HRV，并处理 respiration harmonic / motion contamination？
2. 若 HRV 链条暂时不稳定，毫米波本身能否直接预测 thought-probe 标注的 on-task / mind-wandering 或相邻 attention-related state？
3. NIR、RGB、行为和问卷能否在训练阶段作为 teacher / auxiliary supervision，最终尽可能保留 radar-only deployment；若不够，再逐级退到 mmWave+NIR 和完整多模态系统。

## 当前公开来源

### S 级：第一批代码审计

#### 1. CogPhys
- Repository: https://github.com/AnirudhBHarish/CogPhys
- Paper/project: NeurIPS Datasets & Benchmarks 2025/2026 release
- Modalities: Radar, NIR, RGB/RGBD, thermal, contact ECG/respiration/PPG
- Target: cognitive load
- Public assets: training/evaluation code, cognitive_load pipeline, pretrained checkpoints; dataset requires DUA
- Relevance: 与本项目“remote physiology + cognitive state + multimodal”结构最接近；重点检查 participant split、waveform extraction、cognitive-load labels、remote PPG/resp/blink ablation。

#### 2. Radar-APLANC
- Repository: https://github.com/RadarHRSensing/Radar-APLANC
- Focus: radar heartbeat sensing without relying on dense ECG ground truth for training
- Relevance: pseudo-label / noise-contrast / weakly supervised heartbeat extraction，可能适合本项目大量无 ECG 的现有毫米波数据。

#### 3. VitalSense2024
- Repository: https://github.com/Rc-W024/VitalSense2024
- Focus: FMCW radar cardiac/respiratory vital-sign extraction
- Relevance: respiratory separation、cardiac residual、adaptive matched filtering、pulse temporal alignment；重点用于 beat/IBI 链路审计。

#### 4. VS_DATASET
- Repository: https://github.com/Rc-W024/VS_DATASET
- Focus: synchronized radar + ECG + respiration/pulse reference dataset and processing code
- Relevance: 外部 ground-truth 验证。用于区分“算法本身失败”与“RS6240 当前数据/采集条件失败”。

#### 5. SpectroTransNet-HRV
- Repository: https://github.com/zhang123-1999/SpectroTransNet-HRV
- Focus: FMCW radar -> CWT -> instantaneous HR trajectory -> IPFM beat reconstruction -> RMSSD/SDNN/SD2
- Status caveat: repository is a research-project implementation / technical-report draft rather than a peer-reviewed publication
- Relevance: 直接覆盖 HRV reconstruction；可作为实验 baseline，不单独作为权威效度证据。

### A 级：第二批代码审计

#### 6. mmJEPA-ECG
- Repository: https://github.com/lanyangyang/mmJEPA-ECG
- Paper: AAAI 2026
- Focus: self-supervised mmWave representation + ECG reconstruction
- Caveat: preliminary code; associated dataset not yet publicly released
- Relevance: 大量无 ECG 的本项目雷达数据可考虑 self-supervised pretraining。

#### 7. HRKNet
- Repository: https://github.com/licongsheng/HRKNet
- Focus: Koopman-based deep sequence model for FMCW radar HR
- Relevance: learning-based HR baseline；代码仓库较薄，优先级低于 S 级。

#### 8. EquiPleth
- Repository: https://github.com/UCLA-VMG/EquiPleth
- Focus: synchronized RGB + 77 GHz radar + PPG and fusion
- Relevance: 多传感器同步、radar/RGB physiological fusion 工程结构。

#### 9. FusionPhys
- Repository: https://github.com/chh-ying/fusionphys
- Focus: Visible/NIR/Radar remote physiological fusion
- Relevance: 与本项目 RGB+NIR+mmWave 传感器组合接近，作为多模态保底路线参考。

## 代码审计顺序

### Phase 1 — 认知状态端：CogPhys
检查：
- participant-level train/val/test split 是否防身份泄漏；
- cognitive-load 标签如何构造；
- radar 最终进入 cognitive load classifier 的究竟是 raw、resp waveform、HR/HRV 还是 engineered features；
- remote PPG / remote respiration / blink 的消融实验；
- 窗口长度、采样率、标准化是否在 fold 内完成；
- 哪些模块能映射到 thought probe / 60 s pre-probe window。

### Phase 2 — 心搏端：VitalSense2024 + VS_DATASET
检查：
- target/range-bin selection；
- phase unwrap / clutter removal；
- respiration extraction / harmonic rejection；
- cardiac residual reconstruction；
- beat detector 与 pulse interval 计算；
- reference ECG/PPG alignment；
- 对 motion / poor-SNR 的质量门控；
- 可否先在公开同步数据上复现，再迁移到 RS6240。

### Phase 3 — 无 ECG/弱监督：Radar-APLANC
检查：
- pseudo-label 来源；
- 正负样本构造；
- noise contrast 的假设；
- 是否输出 beat waveform / HR / IBI；
- 是否能利用本项目“目标锁定 + RGB motion gate”生成更可靠伪标签；
- 如何避免 teacher 错误被 student 放大。

### Phase 4 — 学习型 HRV：SpectroTransNet-HRV
检查：
- 10 s CWT 输入生成；
- ECG-derived instantaneous-HR label；
- curriculum loss；
- IPFM beat reconstruction；
- subject-independent split；
- HRV 指标的计算窗口与评价方式；
- 是否可将公开 ECG-radar 数据预训练模型迁移到 RS6240，再用本项目无标签数据做 domain adaptation / self-supervised adaptation。

### Phase 5 — 系统实验矩阵
最终至少比较：

1. radar-only raw/micromotion baseline；
2. radar respiratory features；
3. radar cardiac/HR/HRV features；
4. all-radar feature/model；
5. NIR-only；
6. behavior-only；
7. radar + NIR；
8. radar + NIR + behavior/RGB；
9. multimodal teacher -> radar-only student（若数据和标签允许）。

所有结果必须同时报告：
- 人员级 split（身份恢复后）或明确标注 recording-session split；
- class balance；
- AUROC / balanced accuracy / F1（按任务选择）；
- subject/cluster bootstrap CI；
- quality-gated vs ungated；
- 消融结果。

## 当前原则

- HRV 继续作为毫米波核心生理路线，不因当前四分片失败而撤销。
- raw phase/micromotion、respiration 等作为并行预测与辅助解释路线，不冒充 HRV。
- “做出系统”优先，但不接受身份泄漏或标签泄漏换取虚高准确率。
- 理想部署为 radar-only；训练阶段可以使用 NIR/RGB/行为/probe 作为监督或 teacher；若 radar-only 泛化不足，再退到 mmWave+NIR，最后才是完整多模态。
- 相邻心理量（attentional engagement、cognitive workload、mental fatigue、arousal 等）只有在任务设计、标签或可靠代理变量支撑时才能作为成果，不允许仅由微动相关性反向命名心理构念。
