# 六篇毫米波文献方法地图（第一批）

**范围与证据边界。** 本文件只审读指定的六篇 PDF；未运行 FocusWave 代码、未处理 NIR/RGB、未开发或调参任何算法。页码均为 PDF 页序（与文内印刷页可能相差封面）。**FMCW**=调频连续波，**IF**=中频，**FFT**=快速傅里叶变换，**ECG**=心电图，**HR**=心率，**BR**=呼吸率，**HRV**=心率变异性，**IBI**=相邻心搏间期，**SCG**=心震图。

## 先给人话结论

文献共识不是“对原始雷达直接找 HR 峰”。较完整的链条是：先留住可追溯的原始复数 IF/ADC，再做范围定位和静态/电子偏置控制，在明确的目标范围门（必要时还有方向/通道）抽慢时间复数序列，取相位并处理跳变/漂移，才谈呼吸-心动分离及 HR；若要 HRV，还必须逐搏时间点与同步 ECG 的 IBI 一致性验证。不同论文最大的分歧在于：目标选择是“最大能量”还是“心动质量”，以及呼吸谐波和体动如何处理。它们不能证明 FocusWave 的任一实现已经做到了这些步骤。

## 逐篇“人话方法卡”

### 1. Bhingikar et al. (2026)：雷达非接触 HR 综述

- **要解决什么：** 汇总接触式与雷达式 HR 检测的原理、雷达种类与实际挑战；不是新的受试者实验或单一处理算法（PDF pp. 1-2, 16）。
- **输入到输出：** 综述覆盖 CW、FMCW、IR-UWB 雷达；指出 FMCW 可用距离 bin/到达角分离目标，后续方法涉及相位、谱/时频分析、分解与峰检测，但未给一条可复现实验 pipeline（pp. 2, 16）。
- **为什么这些步骤必要：** 心动胸壁位移约 0.2-0.5 mm、约 1-2 Hz；呼吸约 4-12 mm、约 0.1-0.3 Hz，且静态物体的强低频回波会淹没弱心动分量（pp. 3, 15）。
- **标准/创新：** 标准是范围/角度分离、抑制体动与呼吸谐波、以 ECG/PPG 等参考验证；本文贡献是横向综述，不提出一项待复用的新前端算法（pp. 2, 15-16）。
- **真值、样本、准确度：** 无新采样、无本文准确度；“ECG 是 HR/HRV 的金标准”是背景陈述，不能被误读成该综述的验证结果（p. 4）。
- **局限：** 综述汇集异质研究；不同距离、姿势、参考标准和指标不可直接横比。它明确提示体动、姿势、多人及静态杂波是关键风险（pp. 2, 15）。

### 2. Ostrysz et al. (2026)：动态条件微波生命体征综述

- **要解决什么：** 讨论人在移动或日常活动时，微波/雷达如何监测呼吸、HR 等；不是单一 FMCW 数据集研究（pp. 1, 5, 14）。
- **输入到输出：** 覆盖 UWB、Doppler、FMCW MIMO、反射计等路线；动态场景建议从“静态时的弱微振动低 SNR”转向“动态时强体动低 SIR”，需多阶段自适应滤波、盲源分离/卡尔曼跟踪，必要时结合 IMU/相机（pp. 6, 12）。
- **标准/创新：** 本文是场景与硬件/处理要求对照综述，强调动态条件的设计边界而非交付新分离算法（pp. 11-12）。
- **真值、样本、准确度：** 无新受试者队列或统一性能值，故不可把其引述的单篇结果当作本综述验证（pp. 14-15）。
- **局限：** 自己指出“robustness bottleneck”：大量研究仍是受控实验，临床转化与标准化不足；解剖差异、环境干扰和算法复杂度仍限制部署（pp. 5, 14）。

### 3. Marnach et al. (2026)：24 GHz FMCW 心搏检测

- **要解决什么：** 把 24 GHz FMCW 的呼吸/心搏处理链写成可解释的流程，并将较慢的 Hilbert/平滑步骤替换为适实时的 Moving-RMS/Moving-Average（pp. 1, 6-7）。
- **实际链条：** 2TX/4RX 采集 → 按通道/斜坡组成 radar cube → detrend 去电子偏置 → 每斜坡/通道做 1D FFT → 幅度谱最大峰定位目标 range bin → 取该复数 bin 相位并 unwrap。心搏支路再做相邻时刻复数相乘的相位差、以平滑相位去呼吸、包络/Moving-RMS、峰检测；最后可用 Gaussian 卷积和 12 s 滑窗 IQR plausibility check 减少离群峰（pp. 5-8; Figs. 7, 9-20）。
- **为什么：** FFT 先给距离；相位对胸壁微动敏感；平滑相位相减抑制慢呼吸；包络/峰检测把连续信号变成心搏候选（pp. 5-6）。
- **标准/创新：** 1D range FFT、unwrap、呼吸残差、峰检测属于常见环节；Moving-RMS/Moving-Average 的实时替换、Gaussian 样本卷积与 IQR 合理性检查是本文强调的扩展（pp. 6-8）。
- **真值、样本、准确度：** 使用同步 GE CARESCAPE B650 ECG（p. 1；Fig. 12）。论文展示 3 分钟、152 个心搏的示例：卷积后均值 70.18 bpm、SD 19.19 bpm；对应 ECG 65.70 bpm、SD 2.32 bpm。另一独立数据的 plausibility check 后为 67.39 ± 5.20 bpm（pp. 8-9）。这些是示例统计，**未报告可泛化的受试者数/总体 MAE**。
- **局限：** 体动仍是未解决难点，代码与测量数据未公开（p. 10）。最大幅度 range bin 也不等同于已验证的胸/心选择。

### 4. Yu et al. (2026)：77 GHz FMCW 的 SCG 与 HRV

- **要解决什么：** 为“逐搏 IBI/HRV”而非仅窗口平均 HR，定位心脏方向、重建高信噪比 SCG 并找主动脉瓣开放（AO）点（pp. 1, 3-4）。
- **实际链条：** 原始 ADC IF（TI AWR1642 2T4R，经 TDM 成 1T8R）→ fast-time FFT 得 8 天线 range bin → 每个 range bin 均值相减去静态背景 → 最大能量 index 选人体 range gate → 在该门以改进 Capon 波束形成按 SCG 质量扫描方位、加权合成慢时间复数序列 → MDACM 解相位 → 6 层 wavelet-packet（db45）取第 6-12 子带重建 SCG → Hilbert 包络辅助 AO 定位 → IBI → SDNN/RMSSD/pNN50（pp. 4, 6-10; Fig. 1）。
- **为什么：** 单纯空间谱峰可能是杂波/腹式呼吸，不一定是心动最高 SNR；作者以 20 s 模板的 DTW 质量指数选方位，显式承认目标“最大能量”不够（pp. 6-7）。WPT 用于处理呼吸三次谐波与心动频带重叠（pp. 7-8）。
- **标准/创新：** range FFT、静态均值相减、相位解调、时频分解、ECG 对照是常见模块；以 SCG DTW 质量代替常规 Capon 空间谱选方位、AO 检测是本文创新（pp. 3, 6-9）。
- **真值、样本、准确度：** 同步 Shimmer ECG，13 名受试者各 10 min，22-34 岁、平躺、雷达距胸 0.6 m（p. 10）。对 ECG：平均 SDNN 绝对误差 4.11 ms、RMSSD 8.08 ms、pNN50 2.15%；IBI MAE 5.0 ms、MRE 0.69%（pp. 1, 12, 16）。
- **局限：** 单人仰卧、中心轴有限角度扫描；模板必须高 SNR；未覆盖多人和多姿势（p. 13）。因此不能把这组 HRV 数字迁移到 FocusWave。

### 5. Hao et al. (2025)：FMCW + A-VMD HR

- **要解决什么：** 在 77-81 GHz IWR1843BOOST 中，针对随机小体动、呼吸及谐波，提出 adaptive variational mode decomposition（A-VMD）与谐波加权 HR 估计（PDF pp. 2-4）。
- **实际链条：** 原始 I/Q 合成复数数据，按 fast-time × slow-time × 4 Rx 整形 → 1D range FFT → QOR（quadrature offset removal）→ MTI 和滑动平均去静态杂波 → STFT/能量最大点选位置 → atan2 相位 → unwrap、相位差 → 滤波/分解，A-VMD 分离心动 → 在谱中以谐波关系加权估 HR（pp. 4-8; Fig. 1, 3-5）。
- **标准/创新：** 复数 I/Q、range FFT、QOR/MTI、phase unwrap/difference 是前端常规模块；A-VMD 通过优化 VMD 的 K 与 alpha、及谐波加权为作者主张的创新（pp. 2-3, 18-19）。
- **真值、样本、准确度：** 10 名受试者；文中称以 Cardiio 与血压计作接触式对照，给出 15 个样本的算法比较（pp. 3, 16）。结论称 HR 平均绝对误差 <4 bpm，A-VMD 的总体准确率 94.46%，但不同对照设备/状态的严格同步细节在已审页中不充分（pp. 16-19）。
- **局限：** 文中明说大幅旋转体动未纳入；VMD 参数选择与复杂度仍是泛化风险（pp. 16, 18）。最大能量点仅是反射强，非心动生理真值。

### 6. Hao et al. (2025)：MRVS（DWT + AKF）

- **要解决什么：** 把静态杂波、呼吸谐波和噪声压下，估计 HR/BR；MRVS 是“增强-分解-重建”三段式方法（PDF pp. 2-3, 5）。
- **实际链条：** 原始 ADC（IWR1843/DCA1000）→ 1D FFT 找 range bin → 取慢时间相位 → DC offset removal、coherent accumulation/mean-phase cancellation/MTI 对比 → unwrap + 一阶 phase difference → db5 四层 DWT → PSD 指认呼吸 A4、心动 D3 → inverse DWT + adaptive Kalman filter（AKF）+ square-root normalization 重建 → 谱最大峰及置信阈值判定 HR/BR（pp. 5-10; Figs. 2-8）。
- **为什么：** 相位较频率更敏感于微位移；phase difference 可减漂移、突出心动；DWT/PSD 把多尺度信号分到候选子带，AKF 用于平滑非平稳重建（pp. 5-9）。
- **标准/创新：** range FFT、DC/MTI、unwrap/difference、PSD/阈值都是可审计的常规图层；“叠加+差分增强”以及 AKF-DWT + square-root normalization 的组合为作者方案（pp. 5-9）。
- **真值、样本、准确度：** 以 HUAWEI WATCH GT2 为 HR 参考，初步比较 6 人；报告 AKF-DWT 的 MAPE 范围 1.85%-4.78%，0.4-1.2 m 的绝对误差在 4 bpm 内，角度至 45° MAPE 6.89%（pp. 10-12）。这不是 ECG/逐搏 HRV 验证。
- **局限：** 手表 HR 不是 ECG 逐搏真值；样本小、办公室场景；体动/后背姿势误差上升，文中只是 HR/BR 估计，不能外推 HRV（pp. 10-15）。

## 交接给三线合并时可直接使用的判断

1. **共同核心步骤：** 原始复数数据与采样布局可追溯 → range FFT/明确 range gate → 去电子偏置与静态背景 → 慢时间相位（含 unwrap/差分或漂移控制）→ 呼吸/心动分离 → HR；若声称 HRV，必须 AO/R 峰等逐搏点和 IBI 对 ECG 的一致性。
2. **最大分歧：** Marnach/A-VMD/MRVS 用幅度或能量最大点；Yu 直接显示“空间谱/能量峰可能不是心动最高质量”的反例，改用心动质量选择。两类选择不应混称为“已定位心脏”。
3. **最值得复用的图类：** (a) range-time 的去杂波前后；(b) 带目标门标记的 range 图；(c) raw/unwrapped/differenced phase；(d) 分离前后/子带能量与 PSD（标呼吸基频、谐波、HR）；(e) 与 ECG/RSP 同步的波形、IBI Bland-Altman/误差分布；(f) session 级 QC。见 `FIGURE_ATLAS.md`。
4. **仍然不能下的结论：** 这些文献没有证明 FocusWave 的 RS6240 数据格式、range/channel 选择、静态杂波处理或任何 HR/HRV 指标已合规；该答案只能由前端代码审计和实际 session 诊断图给出。


