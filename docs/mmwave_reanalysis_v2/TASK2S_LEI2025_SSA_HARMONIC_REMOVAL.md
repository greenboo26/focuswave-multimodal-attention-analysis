# 毫米波 Task 2S：Lei 2025 SSA 呼吸谐波去除最后验证

Status: `READY_TO_DISPATCH`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测评产品。

## 1. 决策依据

Task 2R 的 `SSA+VMD adapted` 不能代表 Lei et al. (2025) 目标论文的完整方法。Task 2R 实际采用固定 SSA `L=400`、固定 rank、固定 VMD `K=5/alpha=1000` 与自定义 IMF 选择；而 Lei 2025 原文的核心步骤是：

1. SSA 窗口 `L = n/2`；
2. 第一次 SSA 取前两个最大奇异分量重构呼吸基频；
3. 根据呼吸基频生成并加入二次、三次呼吸谐波正弦信号以主动增强谐波；
4. 第二次 SSA 后删除对应四个显著谐波分量；
5. 按奇异值均值阈值去除低贡献噪声分量；
6. 之后才进入 VMD / EE-VMD / PCC-VMD。

本轮只验证最核心、最对症、公开信息最完整的 SSA 呼吸谐波去除与去噪部分。目的不是完整复现论文，也不是继续算法海选。

## 2. 唯一目标

在 AgeBalanced development 30 participants / 60 Rest sessions 上，使用 **60 s / 5 s** 条件比较：

- A：项目现有 HR 路线；
- B：完全相同 HR 路线 + Lei 2025 SSA 呼吸二/三次谐波去除与 SSA 去噪。

除了新增 Lei SSA 处理外，其余 HR estimator、ECG reference、session、窗口起点、QC 和评价指标必须相同，以便回答唯一问题：

> 正确按 Lei 2025 核心 SSA 逻辑处理呼吸谐波，是否能明显减少当前 HR 灾难性锁频和大误差？

## 3. 数据与窗口

只允许：

- AgeBalanced development 30 participants；
- Lying/Rest + Sitting/Rest，共 60 sessions；
- radar 10 Hz；
- **60 s window / 5 s step**；
- `ecg_reference_v1`；
- 已确定 participant split。

选择 60 s 的原因：Lei 2025 原实验为 1 min，且原文规定 `L = n/2`。AgeBalanced 60 s × 10 Hz ≈ 600 点，因此 SSA 使用 `L ≈ 300`，遵循论文规则，而不是沿用 Task 2R 的固定 `L=400`。

## 4. Lei 2025 SSA 核心实现

必须按原文方法结构执行并保存 provenance：

### 4.1 第一次 SSA

- 输入：与项目路线相同的预处理相位时间序列；
- `n = 当前窗口实际样本数`；
- `L = floor(n/2)` 或在奇偶处理上采用等价且明确记录的 `n/2` 规则；
- 构建 trajectory matrix；
- SVD；
- 取两个最大奇异分量；
- diagonal averaging 重构呼吸基频时间序列；
- 从该重构信号估计呼吸基频 `fr`，不得使用 ECG 真值。

### 4.2 主动增强二/三次呼吸谐波

- 根据 `fr` 构造 `2fr` 与 `3fr` 正弦信号；
- 加入原时间序列以增强对应呼吸谐波能量；
- 增强信号的幅度/相位若原文无法唯一恢复，必须标记 `MISSING_EVIDENCE` 并采用一个事先说明、非 ECG 驱动的最小工程规则；
- 不允许逐窗口利用 ECG 选择幅度、相位或最优解释。

### 4.3 第二次 SSA 与谐波删除

- 对增强后的信号再次执行 SSA；
- 按论文描述识别增强后对应二/三次呼吸谐波的四个显著分量；
- 删除这些分量并重构无呼吸谐波信号；
- 不得把“直接 notch 2fr/3fr”冒充 Lei SSA 方法。

### 4.4 SSA 去噪

- 依据原文：使用所有奇异值的均值作为阈值；
- 低于均值的低贡献分量作为噪声，不参与重构；
- 不使用 Task 2R 的固定 rank=40。

## 5. 暂时明确不做

本轮**不做完整 PCC-VMD / EE-VMD / GWO**。

原因：原文没有完整给出 GWO population、iterations、K/alpha 搜索边界等全部机器可复现参数；而论文自身结果显示最大收益已经出现在 SSA 呼吸谐波/噪声处理阶段。本轮先判断这个核心模块是否对我们的主要失败模式有价值。

同时禁止：

- 不看 80 held-out；
- 不访问正式 `J:\Data`；
- 不跑 HRV；
- 不跑 BR 外部验证；
- 不使用本地 BIOPAC 调参；
- 不开 DR-MUSIC、Iwata/VME、HEBR、Health-VMD、mmCG、稀疏分离或第二个外部算法家族；
- 不根据 ECG 反复调 SSA 工程细节直到结果变好。

## 6. 必须做的同条件比较

同一 development cohort、同一窗口和 reference，至少报告：

- attempted / scored windows；
- coverage；
- MAE；
- median AE；
- RMSE；
- Pearson / Spearman；
- Bland–Altman bias / LoA；
- P90 AE；
- 2x / 0.5x HR lock；
- 极端错误窗口数量；
- quality strata。

AgeBalanced 无 RSP，因此真实 `respiratory_harmonic` 标签仍为 `NOT_ASSESSABLE`；只能根据 HR/频率关系做代理诊断，不能写成已由 RSP 验证。

## 7. 继续投入门槛

本任务的门槛不是医学合格线，而是比赛时间预算下的继续研发门槛。

只有当 Lei SSA 相比同条件项目路线同时出现**明确、方向一致的实质改善**时才建议继续，例如：

- MAE 至少改善约 20%；
- median AE 至少改善约 20%；
- RMSE 同方向明显改善；
- correlation 明显上升，而非仍接近 0；
- coverage 不得通过大量拒绝窗口换取表面成绩；
- 极端错误 / 明显 2x、0.5x 锁频减少。

如果只改善约 1–2 BPM、约 5–10%，或主要指标互相冲突，则视为不值得继续。

## 8. 完成后的唯一决策

### `ADVANCE_LEI_PIPELINE`
核心 SSA 模块明显改变问题性质。此时停止本任务，下一轮再决定是否值得补完整 PCC-VMD/GWO，或直接确定简化 Lei-SSA + project estimator 方案进入 80 held-out。

### `STOP_PHYSIOLOGY_RND`
核心 SSA 模块没有实质改善。停止新的 HR/HRV 算法开发；不再继续 DR-MUSIC、VME、HEBR、Health-VMD 等方法海选。mmWave 转入 motion/phase/spectral/quality supporting-signal 与多模态 AI 主线。

### `BLOCKED`
Lei 核心 SSA 中仍存在影响结论的公开信息缺失，无法在不依赖 ECG 调参的情况下形成可信实现。明确缺口后停止，不自动换算法。

## 9. 80 held-out

本轮绝不运行 80 人。

只有 `ADVANCE_LEI_PIPELINE` 且最终执行配置已经确定、不再根据 held-out 调参时，才允许下一轮一次性进入 80-person held-out 外部验证。

## 10. HRV 边界

本轮不恢复 HRV。AgeBalanced radar 仅 10 Hz，HRV 要求 beat-level IBI 时间精度；当前先验证 HR/谐波问题。HRV 不属于本轮比赛必做 KPI。

## 11. 时间与模型

硬上限：**1.5–2 h**。

主线程：GPT-5.6 Terra / medium。

Luna/low 可做机械性参数核对、manifest、结果汇总。默认不使用 Sol/high。

若 2 h 内不能产生可信 development A/B 结果，停止并返回 `BLOCKED`，不得无限扩展。

## 12. 完成后只返回

- `PASS / PARTIAL / BLOCKED`；
- A/B 60s 同条件结果表；
- Lei SSA 实际实现细节与所有 `MISSING_EVIDENCE`；
- 极端错误/锁频变化；
- `ADVANCE_LEI_PIPELINE / STOP_PHYSIOLOGY_RND / BLOCKED`；
- 是否建议未来进入 80 held-out；
- commit SHA。

完成后停止。