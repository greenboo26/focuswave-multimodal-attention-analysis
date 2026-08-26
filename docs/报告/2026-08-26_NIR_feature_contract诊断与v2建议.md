# 2026-08-26 NIR feature contract 诊断与 v2 建议

## 1. 结论先行

当前正式 `C+B+NIR` 的 NIR 输入不是 generic face embedding，也不是完整旧调研设想中的 NIR。它实际由 30 个低维、可解释的 probe-level 特征组成：

- 10 个 PIR（pupil-to-iris diameter ratio）窗口统计量
- 10 个 OAR（ocular aperture ratio）窗口统计量
- 10 个 NIR QC / coverage 变量

因此当前 30 s `C+B+NIR ROC-AUC = 0.598` 应解释为：

> 当前 PIR/OAR/QC 表征在 matched participant-disjoint 评估中没有给 C+B 提供增量预测价值。

不能解释为：

> 完整 NIR 模态不能提供注意力/走神信息。

旧调研最重视的 PERCLOS、blink duration、blink re-dilation latency 等尚未进入当前正式 feature contract。

---

## 2. 当前实际进入模型的 NIR 特征

### PIR：10 个

- `nir_pir_median`
- `nir_pir_mean`
- `nir_pir_mad`
- `nir_pir_iqr`
- `nir_pir_sd`
- `nir_pir_p10`
- `nir_pir_p90`
- `nir_pir_slope_per_sec`
- `nir_pir_diff_mad`
- `nir_pir_diff_rate_mad_per_sec`

这些描述窗口内 pupil/iris ratio 的水平、离散、分位数、趋势和逐帧动态。它们不是毫米单位的绝对瞳孔直径。

### OAR：10 个

- `nir_oar_median`
- `nir_oar_mean`
- `nir_oar_mad`
- `nir_oar_iqr`
- `nir_oar_sd`
- `nir_oar_p10`
- `nir_oar_p90`
- `nir_oar_slope_per_sec`
- `nir_oar_diff_mad`
- `nir_oar_diff_rate_mad_per_sec`

OAR 是眼睛开合/眼球可见区域的几何候选量。当前 contract 不允许直接把它解释为 EAR、blink 或 PERCLOS。

### QC / coverage：10 个

- `nir_pir_valid_fraction`
- `nir_oar_available_fraction`
- `nir_roi_clipped_fraction`
- `nir_ritnet_found_fraction`
- `nir_ocular_fragmented_candidate_fraction`
- `nir_available_duration_fraction`
- `nir_internal_coverage_fraction`
- `nir_max_temporal_gap_sec`
- `nir_n_nir_rows`
- `nir_n_nir_rows_available`

QC = Quality Control。它们主要回答“这一段 NIR 数据有没有看清楚、有没有丢、能不能信”，不是注意力/走神本身的科学指标。

---

## 3. `fullclass` 的真实含义

当前 `fullclass` 是 RITnet 四分类眼部结构分割：

- class 0 = background
- class 1 = sclera
- class 2 = iris
- class 3 = pupil

它包含眼部语义分割、瞳孔/虹膜几何、pupil/iris ratio、ocular aperture、ROI/QC/provenance 等字段。

它不包含：

- generic face embedding
- facial AU embedding
- gaze embedding
- head pose embedding
- rPPG waveform
- HR/HRV
- respiration
- blink event labels
- PERCLOS labels

因此当前 NIR 下降不能简单归因于“高维 generic face embedding 过拟合”。

---

## 4. 当前质量情况

30 s matched 1360 probes 中，审计得到：

| 变量 | 平均值 | 达到 0.80 的窗口比例 | 解释 |
|---|---:|---:|---|
| `nir_pir_valid_fraction` | 0.752 | 55.1% | PIR 有效帧比例存在明显异质性 |
| `nir_oar_available_fraction` | 0.986 | 97.8% | OAR 大多可算，但不等于已验证闭眼指标 |
| `nir_ritnet_found_fraction` | 0.913 | 90.4% | RITnet 总体检出率尚可 |
| `nir_internal_coverage_fraction` | 0.931 | 97.4% | 大多数窗口时间覆盖较完整 |
| `nir_available_duration_fraction` | 1.000 | 100% | 总体窗口时长完整 |

需要特别注意：

> 数值缺失率低，不等于真实眼部信号质量稳定。

PIR 的有效帧比例平均只有约 0.752，只有约 55.1% 的窗口达到 0.80。

---

## 5. 旧调研预期 vs 当前 contract

团队旧调研对 NIR 的核心定位主要是：

- pupil diameter / pupil dynamics
- PERCLOS P80
- precise blink duration
- blink re-dilation latency
- gaze/PCCR（高精度候选）

当前覆盖情况：

| 旧调研指标 | 当前状态 |
|---|---|
| pupil diameter / dynamics | 部分实现：PIR + dynamics 已进入 |
| PERCLOS | 未直接提取 |
| blink count/rate | 未提取 |
| blink duration | 未提取 |
| inter-blink interval | 未提取 |
| blink re-dilation latency | 未提取 |
| gaze/PCCR | 未建立可靠标定链 |
| NIR rPPG/HR | 未提取，且非当前 NIR 主责 |
| HRV/respiration | 未提取，应优先留给 mmWave |
| head pose/AU | 未提取，应优先留给 RGB |

所以当前 NIR v1 实际更接近：

> PIR dynamics + OAR candidate + QC

而不是：

> pupil + PERCLOS + precise blink + re-dilation + gaze

---

## 6. 为什么 OAR 不等于 blink/PERCLOS

当前 OAR 可以理解为“这一帧眼睛开得有多大”。

例如：

- frame 1：开得较大
- frame 2：开始变小
- frame 3：很小
- frame 4：很小
- frame 5：恢复

当前管线有这条连续几何轨迹，但还没有正式把它转成：

- 一次 blink 的 onset
- 一次 blink 的 offset
- blink duration
- blink count/rate
- 一段窗口中的 PERCLOS

所以原材料在，但事件层还没有建立。

---

## 7. QC 应该扮演什么角色

QC 变量应主要用于：

1. 判断某个窗口是否可用；
2. 质量门控；
3. 低质量窗口敏感性分析；
4. 必要时作为 nuisance / quality covariate。

不应把“有多少帧找到眼睛”“ROI 是否裁边”等变量直接解释为 NIR 的核心注意力生理信号。

当前 v1 把 10 个 QC/coverage 变量与 PIR/OAR 一起作为预测输入，因此 v2 应明确区分：

- scientific features
- quality-control features

---

## 8. NIR v2 不需要推翻现有管线

不建议重跑 RITnet 全量推理。

现有逐帧 PIR/OAR 已经提供关键原材料。真正需要补的是上层事件和个体标准化。

### 8.1 瞳孔

优先保留：

- PIR median
- PIR IQR
- PIR slope
- PIR diff-rate MAD

新增：

- participant-relative / baseline-normalized PIR change

理由：跨 participant 直接比较 pupil level 容易混入个体差异。更有意义的是“这个人现在相对于自己的基线变化多少”。

### 8.2 眼睑 / blink

从逐帧 OAR 建立经过人工验证的：

- eye closure state
- blink onset/offset
- blink count/rate
- blink duration
- PERCLOS

其中优先级最高的是：

- PERCLOS
- blink duration

### 8.3 不加入本次 NIR v2 的内容

不建议为了让 NIR 看起来更“多”而加入：

- NIR rPPG / HR
- HRV
- respiration
- head pose
- facial AU/expression
- generic visual embedding

这些要么属于 mmWave/RGB 更合理的职责，要么当前 NIR 数据/contract 缺少可靠验证条件。

---

## 9. 在正式 NIR v2 之前必须先做的验证

不要直接批量计算 PERCLOS 后跑模型。

第一步应做：

> `NIR blink/PERCLOS feasibility + manual validation audit`

建议抽取少量代表性 session / probe-window：

- NIR 质量好
- NIR 质量中等
- NIR 质量差

人工查看短视频，并与逐帧 OAR 对齐，验证：

1. OAR 下降是否真的对应眼睛闭合；
2. RITnet 检测失败是否会被误判成闭眼；
3. ROI clipped / fragmented 是否会制造假 blink；
4. 阈值是否需要 participant-specific calibration；
5. blink onset / offset 如何定义；
6. 连续丢帧如何处理；
7. PERCLOS denominator 如何定义，只统计 valid frames 还是总时长。

只有该验证通过，才值得正式批量提取 PERCLOS/blink。

---

## 10. NIR v2 建议特征规模

控制在约 8–12 个理论驱动科学特征，不继续扩大维度。

候选：

1. PIR median
2. PIR IQR
3. PIR slope
4. PIR diff-rate MAD
5. baseline-normalized PIR change
6. OAR median
7. OAR lower-tail / p10
8. PERCLOS
9. blink count/rate
10. blink median duration
11. 可选：blink duration upper quantile

QC 保留在单独 quality block，不与科学特征混为一谈。

---

## 11. 当前 NIR v1 的最终冻结解释

建议统一使用：

> 当前正式 NIR v1 是“瞳孔/虹膜比例动态 + 眼睛开合候选几何 + 数据质量”的增量测试。它在 matched 68-session / 44-participant cohort 中没有提高 C+B，30 s ROC-AUC 从 0.672 降至 0.598，ΔAUC=-0.074，participant-bootstrap 95% CI [-0.114, -0.036]。该结果不能扩展解释为旧调研完整 NIR hypothesis 的失败，因为 PERCLOS、blink duration、blink re-dilation 等关键指标尚未进入正式 contract。

---

## 12. 当前决策

- NIR v1：作为正式阴性增量结果保留。
- 不重跑 RITnet 全量推理。
- 不继续堆 generic 特征。
- 先做小规模 OAR → blink/PERCLOS 人工验证。
- 验证通过后，仅做一次低维、理论驱动的 NIR v2。
- 如果 OAR 无法可靠恢复真实 blink / closure，则停止 NIR v2，不再为比赛阶段继续投入大规模工程成本。