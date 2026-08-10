# 算法引用与开源代码清单

> 用途: 本管线各算法步骤对应的参考文献与公开代码。
> 文献分为两档: **核心算法依据与标准(8 篇)** 为本管线真实使用的文献; **调研对照(9 篇)** 为领域调研资料, 代码未直接使用。
> 说明: 毫米波生命体征/HRV 领域多数算法论文（尤其 IEEE/IOP 期刊）不强制公开代码，本清单标注了「无公开代码」的条目，其中部分有预印本或算法伪代码可自实现。

## 一、管线算法 → 参考文献映射

| 管线步骤                             | 本管线实现                                                  | 参考文献                                                                             | 公开代码                       |
| -------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------- | -------------------------- |
| ① 距离 FFT + 距离门                   | numpy rfft（256 点距离域）                                   | Alizadeh 2019; Paterniani 2023                                                   | TI mmWave Labs 开源 demo（见下） |
| ② 相位提取 + 解缠 → 位移                 | `np.unwrap(np.angle())`，λ/4π                           | Alizadeh 2019; Paterniani 2023 §V                                                | 同上                         |
| ③ 选 bin（v2：相位频谱 SNR）             | 心跳带 0.8-2.5Hz / 呼吸带 0.1-0.5Hz 带内 SNR 取最大               | 原创；对比 mmHRV 免校准目标检测                                                              | mmHRV 无公开代码                |
| ③ 定位（v9：最高能量距离门 + 相位方差人体判别）      | 全局最高能量 bin + 相位方差 0.1-50 判定人体/墙                        | Chen 2024（最高能量门）; Wang 2021 mmHRV（相位方差）                                          | 均无公开代码                     |
| ③ 窗级自适应选 bin + IBI CV 门控         | 多候选 (ch,bin) 评分：HR 生理范围 + IBI CV<0.12 + 峰数             | 原创                                                                               | 无                          |
| ④ 静态杂波消除                         | 相位均值对消 Y(n)=X(n)−X̄                                    | Chen 2024（第 2 步）; Alizadeh 2019                                                  | 无                          |
| ④ 带通分离（baseline）                 | scipy butter SOS + filtfilt（呼吸 0.1-0.5Hz，心跳 0.8-2.5Hz） | Wang 2021（BPFB baseline）; Paterniani 2023                                        | 无                          |
| ④ VMD 心跳分离（升级方案）                 | vmdpy / sktime.libs.vmdpy                              | Dragomiretskiy & Zosso 2014（算法原始文献）; Wang 2021（毫米波应用）; Carvalho 2020（vmdpy 实现文献） | ✅ vmdpy（见下）                |
| ④ 呼吸谐波抑制                         | 呼吸主频 + 2/3 次谐波 iirnotch 陷波                             | Dai 2025（notch 抑制呼吸谐波）                                                           | 均无公开代码                     |
| ⑤ 心跳峰值检测（窄带逐拍）                   | 频域主峰 ±0.05Hz 窄带带通 → 逐拍局部最大                             | Wang 2021; Paterniani 2023                                                       | 无                          |
| ⑤ 心跳峰值检测（prominence + IBI 自相关校正） | scipy find_peaks，多 prominence 阈值取 IBI CV 最优            | 通用信号处理方法                                                                         | scipy 官方实现                 |
| ⑤ 呼吸周期估计                         | 自相关函数滞后估计                                              | 通用信号处理方法                                                                         | scipy 官方实现                 |
| ⑥ IBI → HRV 时域（SDNN/RMSSD）       | 逐拍 IBI 序列直接计算                                          | Task Force 1996（定义标准）                                                            | —                          |
| ⑥ HRV 频域（LF/HF/LF-HF）            | IBI 插值 + periodogram                                   | Task Force 1996; Shaffer & Ginsberg 2017                                         | —                          |
| 质量评估（SNR / IBI 有效率 / 频谱锐度）       | 窗级 SNR≥3dB 且 IBI 有效率≥0.8                               | 原创（领域内 QDA-SSM 质量门控为同方向参照）                                                       | 无                          |

## 二、GitHub 开源仓库（已验证存在）

### 直接依赖（本管线实际使用的库）

| 仓库                                                                          | 说明                                                                                                                                              |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| [Fishsevens/vmdpy](https://github.com/Fishsevens/vmdpy)                     | VMD（变分模态分解）Python 官方实现，`pip install vmdpy`；现由 sktime 维护（`sktime.libs.vmdpy`）。原仓库 [vrcarva/vmdpy](https://github.com/vrcarva/vmdpy) 已归档（2024-06） |
| [vrcarva/carvalho-etal-2019](https://github.com/vrcarva/carvalho-etal-2019) | vmdpy 引用文献（Carvalho 2020）的官方代码仓库：EEG 五方法对比实验全部脚本（`main_feats.py` / `main_classify.py` / `main_figs.py`），README 含方法完整描述                          |

### 毫米波生命体征参考实现（端到端管线）

| 仓库                                                                                                  | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Ubiweb-lab/mmVital](https://github.com/Ubiweb-lab/mmVital)                                         | TI mmWave 雷达生命体征全流程：雷达配置、信号处理、HR/BR 提取、深度学习模型、App 可视化                                                                                                                                                                                                                                                                                                                                                                                      |
| [code-rookie-wr/mmWave-radar-vital-sign](https://github.com/code-rookie-wr/mmWave-radar-vital-sign) | TI IWR6843 60GHz 生命体征实现                                                                                                                                                                                                                                                                                                                                                                                                                    |
| [HsiehChin/mmWave-VitalSign](https://github.com/HsiehChin/mmWave-VitalSign)                         | 自由体动条件下的生命体征预测                                                                                                                                                                                                                                                                                                                                                                                                                             |
| [shakhal350/VitalSign-Capstone-2023](https://github.com/shakhal350/VitalSign-Capstone-2023)         | FMCW 雷达 + 深度学习，室内心跳/呼吸率检测                                                                                                                                                                                                                                                                                                                                                                                                                  |
| [m6c7l/pymmw](https://github.com/m6c7l/pymmw)                                                       | TI IWR 系列雷达 Python 工具箱（采集 + 处理通用库）                                                                                                                                                                                                                                                                                                                                                                                                         |
| [bitsforbrains/mmwave](https://github.com/bitsforbrains/mmwave)                                     | TI DCA1000EVM 采集卡数据读取/处理                                                                                                                                                                                                                                                                                                                                                                                                                   |
| [TI Resource Explorer mmWave Labs](https://dev.ti.com/tirex/explore/)                               | TI 官方 vital signs demo（IWR6843/AWR1642），mmWave Labs 全部开源。入口：dev.ti.com → Resource Explorer → mmWave Sensors → Industrial/Automotive Toolbox（需注册 TI 账号）。参考视频：[TI Vital Signs Lab 演示](https://www.ti.com/video/5428037798001)；Driver Vital Signs 实验文档：[Getting Started Guide](https://dev.ti.com/tirex/explore/content/mmwave_automotive_toolbox_3_6_0/labs/incabinsensing/driver_vital_signs/docs/DriverVitalSigns_GettingStartedGuide.pdf) |

## 三、参考文献（APA 7th）

### A. 核心算法依据与标准（8 篇，本管线真实使用）

1. Dragomiretskiy, K., & Zosso, D. (2014). Variational mode decomposition. *IEEE Transactions on Signal Processing, 62*(3), 531–544. https://doi.org/10.1109/TSP.2013.2288675

2. Wang, F., Zeng, X., Wu, C., Wang, B., & Liu, K. J. R. (2021). mmHRV: Contactless heart rate variability monitoring using millimeter-wave radio. *IEEE Internet of Things Journal, 8*(22), 16623–16636. https://doi.org/10.1109/JIOT.2021.3075167

3. Chen, Y., Yuan, J., & Tang, J. (2024). A high precision vital signs detection method based on millimeter wave radar. *Scientific Reports, 14*, 25535. https://doi.org/10.1038/s41598-024-77683-1

4. Dai, X., Zhang, Y., Luo, J., Liu, K., & Fu, D. (2025). Vital signs detection of moving targets using FMCW radar. *Measurement Science and Technology, 36*, 017002. https://doi.org/10.1088/1361-6501/ad8470

5. Alizadeh, M., Shaker, G., Almeida, J. C. M., Morita, P. P., & Safavi-Naeini, S. (2019). Remote monitoring of human vital signs using mm-wave FMCW radar. *IEEE Access, 7*, 54958–54968. https://doi.org/10.1109/ACCESS.2019.2912956

6. Paterniani, G., Sgreccia, D., Davoli, A., Guerzoni, G., Di Viesti, P., Valenti, A. C., Vitolo, M., Vitetta, G. M., & Boriani, G. (2023). Radar-based monitoring of vital signs: A tutorial overview. *Proceedings of the IEEE, 111*(3), 277–317. https://doi.org/10.1109/JPROC.2023.3244362

7. Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. *Circulation, 93*(5), 1043–1065.

8. Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. https://doi.org/10.3389/fpubh.2017.00258

### B. 调研对照（9 篇，代码未直接使用，可选背景）

9. Carvalho, V. R., Moraes, M. F. D., Braga, A. P., & Mendes, E. M. A. M. (2020). Evaluating five different adaptive decomposition methods for EEG signal seizure detection and classification. *Biomedical Signal Processing and Control, 62*, 102073. https://doi.org/10.1016/j.bspc.2020.102073（vmdpy 的来源论文，库作者要求引用）

10. Li, J., Li, X., Cai, Y., & Shi, K. (2026). HEBR: An HRV noncontact health monitoring method based on millimeter-wave enhanced time-frequency analysis. *IEEE Internet of Things Journal*. https://doi.org/10.1109/JIOT.2026.3661997

11. Li, M., & Zhou, J. (2026). A quality-gating and delay-alignment state-space framework for mmWave radar HRV estimation. *IEEE Access*. https://doi.org/10.1109/ACCESS.2026.3691396

12. Iwata, I., Sumi, K., Tanaka, Y., & Sakamoto, T. (2025). Accurate radar-based heartbeat measurement using higher harmonic components amplification. *IEEE Access*. https://doi.org/10.1109/ACCESS.2025.3575932（arXiv 有预印本 + Algorithm 1 伪代码，可自实现）

13. Zhao, L., Lyu, R., Zhou, A., Guo, Q., & Ma, H. (2025). mmCG: Noncontact millimeter-wave cardiography for heart rate variability monitoring. *IEEE Internet of Things Journal*. https://doi.org/10.1109/JIOT.2025.3573511

14. Cui, G., Wang, Y., Zhang, X., Li, J., Liu, X., Li, B., Wang, J., & Zhang, Q. (2025). Non-contact heart rate variability monitoring with FMCW radar. *Sensors, 25*(17), 5607. https://doi.org/10.3390/s25175607

15. Li, T., Wu, T., Qin, L., & Li, W. (2026). Interference resistant contactless heart rate variability monitoring. *Scientific Reports*. Advance online publication. https://doi.org/10.1038/s41598-026-59339-4

16. Xu, Z., Ye, T., Chen, L., Gao, Y., & Chen, Z. (2025). Health-Radar: Noncontact multitarget heart rate variability detection using FMCW radar. *IEEE Sensors Journal, 25*(1), 405–418. https://doi.org/10.1109/JSEN.2024.3494755

17. Li, Z., Wu, X., Álvarez Casado, C., Lindholm, V., Mikkonen, K., Xia, Z., Feng, X., & Bordallo López, M. (2026). A comprehensive survey on contactless vital sign monitoring using vision-based, radio-based, and fusion approaches. *Neurocomputing*. https://doi.org/10.1016/j.neucom.2026.132877

## 四、无公开代码情况说明

* **核心 8 篇中 6 篇无公开代码**（mmHRV、Chen 2024、Dai 2025、Alizadeh 2019、Paterniani 2023、Task Force 1996）：均为期刊论文，作者未公开代码，仅有算法描述，需自实现。

* **vmdpy（VMD 实现）有完整公开代码**：见上文 GitHub 仓库，`pip install vmdpy` 即可使用，这是本管线唯一直接依赖的第三方算法库。

* **Carvalho 2020**：正式版（Elsevier）付费，但作者在 GitHub 公开了论文全部代码（vrcarva/carvalho-etal-2019），另有 bioRxiv 预印本（免费，三方法早期版，DOI: 10.1101/691055）。

* **Iwata 2025**：IEEE Access 开放获取，arXiv 有预印本，正文含 Algorithm 1 伪代码，可自行复现（这是无代码文献中复现成本最低的一篇）。

* **HEBR、QDA-SSM、mmCG、Cui、SciRep 2025-2026**：新论文，暂无公开代码。

* 本管线在无公开代码的情况下自行实现了：SNR 选 bin、窗级自适应选 bin + IBI CV 门控、呼吸谐波 iirnotch 陷波（v9 模块）等，实现细节见 `process_vital_signs_v9.py` 与 `analyze_mmwave_hrv.py` 注释。

