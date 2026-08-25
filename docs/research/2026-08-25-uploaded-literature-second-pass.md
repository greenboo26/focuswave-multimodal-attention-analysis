# 2026-08-25 上传文献第二轮审计

本轮纳入用户新增原文与核验记录：

- Frazao et al. (2024), *Radar-Based Heart Cardiac Activity Measurements: A Review*, Sensors 24, 7654.
- Xu et al. (2025), *SCKD: Semi-Supervised Cross-Modality Knowledge Distillation for 4D Radar Object Detection*, AAAI-25.
- Wu et al. (2026), *Tac-Mamba: A Pose-Guided Cross-Modal State Space Model with Trust-Aware Gating for mmWave Radar Human Activity Recognition*, Electronics 15, 1535.
- `毫米波质量门控证据-论点映射_v1.md`
- `文献下载与核验记录_2026-08-25.md`

## 1. Frazao 2024 对 HRV 路线的直接裁决价值

这篇综述专门比较 radar HR 与 radar HRV 系统。最重要的不是某个误差数字，而是它明确区分了 HR 与 HRV 对时序信息的要求：HR 可以只保留峰数量或用频谱方法得到平均频率；HRV 必须保留每个峰在时间轴上的位置，因为 BBI/IBI 是 SDNN、RMSSD、pNN50 等的基础。因此，纯 FFT/谱峰方法不适合作为正式 HRV 路线。

这直接支持本项目的路线升级：

`平均 HR/BR 候选峰审计` 只能作为前置诊断，不能作为 HRV 有效性验证；正式路线必须进入 `beat timestamps -> IBI/BBI -> HRV`。

综述还指出：

- FMCW 在其纳入研究中整体表现较好，但不能把载频本身解释成性能决定因素；
- 系统架构和信号处理方法对结果影响最大；
- 测量距离增大通常伴随更高误差，且 HRV 文献大量集中在 <1 m 的理想静坐条件；
- 更高载频提高对微小胸壁位移的相位敏感性，同时也提高对随机体动/噪声的敏感性；
- HRV 系统通常需要比 HR 更复杂的多级信号处理链；
- 文献间性能指标、测试协议和参数报告不统一，因此不能把别人的误差直接当作本项目性能阈值。

### 对 RS6240 的含义

当前四分片中出现 2×/3× respiration harmonic 与子窗不稳定，不构成“毫米波 HRV 不可做”的证据；它更准确地说明目前仍停留在平均频谱候选层，而 HRV 需要转入 beat-level pipeline，并保留 target lock / motion / harmonic / IBI QC。

## 2. SCKD 2025 对 radar-only deployment 的意义

SCKD 的任务是 4D radar object detection，不是生理或认知任务，因此不能迁移其 mAP 数字。但它提供了与本项目部署目标高度一致的训练范式：

- teacher 使用 Lidar + radar 融合；
- student 只有 radar；
- feature-level distillation + output-level semi-supervised distillation；
- inference 阶段只保留 radar student，不增加部署端额外模态成本；
- 无标签数据可以通过 teacher 输出继续扩充 student 训练。

其 ablation 显示，在该任务中，将融合 teacher 的知识蒸馏到 radar-only student 能显著提高 radar student；且利用更多 unlabeled data 的 SSOD 可以进一步提升结果。

### 映射到本项目

候选结构：

`teacher = mmWave + NIR + RGB/behavior (+ probe label)`

`student = mmWave only`

蒸馏目标不应直接照搬 detection feature，而应考虑：

- attention-state logits / probability；
- intermediate temporal representation；
- pupil/blink/behavior auxiliary targets；
- quality-aware physiological representation；
- 若 HRV beat chain 成熟，再加入 cardiac/IBI auxiliary supervision。

## 3. Tac-Mamba 2026 对“多模态保底但不放弃毫米波”的意义

Tac-Mamba同样是 HAR，不是认知负荷或 HRV，因此只作为系统架构证据。它比 SCKD 更接近本项目当前担心的问题：视觉模态在环境变化或遮挡时可能产生 negative transfer。

论文明确采用：

- visual skeleton teacher -> radar student 的结构先验蒸馏；
- modality dropout，训练阶段随机遮蔽视觉；
- Trust-Aware gate，根据视觉可靠性动态抑制视觉支路；
- 视觉完全不可用时，模型有显式 radar-only fallback；
- 同时报告 multimodal 和 radar-only inference。

这说明本项目若做 NIR/RGB 辅助训练，不应设计成“摄像头一坏毫米波也坏”的强耦合 fusion，而应从一开始就训练 modality missing / degraded 条件。

### 本项目可转化的设计

建议至少比较：

1. mmWave-only student baseline；
2. full multimodal teacher upper bound；
3. simple fusion（用于证明是否有 negative transfer）；
4. quality/trust-gated fusion；
5. teacher -> mmWave-only student；
6. modality-dropout teacher/student；
7. NIR/RGB 缺失或低质量 stress test。

注意：Tac-Mamba 的 95.37% multimodal / 87.54% radar-only 是 MM-Fi HAR 的任务结果，不能作为本项目准确率目标。

## 4. 对现有项目路线的更新

### HRV 线继续，而且更明确

Frazao 综述强化而不是削弱 HRV 路线：正式 HRV 必须以 beat timing 为核心，因此停止扩大旧式 FFT HR/BR 统计是正确的；停止的是旧验证方法，不是 HRV 目标。

下一步顺序：

`VS_DATASET + ECG external benchmark`
-> `radar cardiac residual`
-> `beat timestamps`
-> `ECG R-peak matching`
-> `IBI/BBI error`
-> `RMSSD/SDNN`
-> `RS6240 adapter`

### 专注系统线形成明确三级目标

Tier 1（理想）：multimodal teacher -> mmWave-only student，部署只用毫米波。

Tier 2：mmWave + NIR，视觉只作为辅助或质量信号。

Tier 3（比赛保底）：完整多模态模型，确保最终有可展示的预测系统。

三层都必须与真正的 subject-level split、probe label 和质量门控绑定，不能以泄漏换准确率。

## 5. 新增证据的使用边界

- Frazao 2024：可用于 radar HRV 方法学、beat/BBI 必要性、距离/体动/架构影响；不能替代本项目 ECG 验证。
- SCKD 2025：可用于“多模态训练、radar-only inference、半监督蒸馏”工程范式；不能证明 NIR/RGB 一定能提升专注识别。
- Tac-Mamba 2026：可用于 modality dropout、trust-aware gating、negative transfer、radar fallback 范式；不能把 HAR 准确率迁移到心理状态识别。

## 当前结论

新增文献使总体路线更清楚：

**不要把“停止继续扩大旧 FFT HR 峰验证”误解成“毫米波不做 HRV”。**

真正的升级是：

- 生理链从 `HR frequency candidate` 升级到 `beat -> IBI -> HRV`；
- 系统链从“单模态 vs 多模态二选一”升级到“多模态 teacher / quality-aware training -> 尽可能 radar-only inference”；
- NIR、RGB、行为与 probe 的价值不仅是最终 fusion，也可以作为训练期监督、质量信号和 teacher knowledge。
