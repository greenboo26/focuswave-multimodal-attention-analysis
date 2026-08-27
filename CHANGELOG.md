# 修改说明

> 格式参照 FocusWave（F:/FocusWave_1.3.6/04-docs/CHANGELOG.md）：每条 = 日期 + v版本 主题，结构 = 背景 / 改动 / 验证 / 涉及文件。
> 2026-08-10 起本文件同时承担原 `docs/版本说明.md` 的版本演进记录（已合并，版本说明.md 删除）。
> 版本号对应 `git tag v{版本}`（提交规范见 `docs/规范备忘.md`）。

---

## 2026-08-27 — result(mmwave): complete bounded Task 2S Lei-2025 SSA comparison

### 背景

Task 2R 的 adapted SSA+VMD 不能代表 Lei 2025 的 SSA 呼吸谐波去除核心，因此按单一外部参考任务补做 60 s method-native development comparison。

### 改动

- 新增 Lei 2025 SSA 核心的 `paper_reimplementation/adapted` 实现、测试、runner、配置和结果报告。
- 仅使用 AgeBalanced development 30 人/60 Rest session，60 s/5 s；不改变 Phase 2A contract，不访问 held-out、`J:\\Data`、BR 或 HRV。
- 作者代码及论文未唯一规定的幅相/分量选择保留为 `MISSING_EVIDENCE`，结果只作为限定开发证据。

### 验证

- 14 个 session 有完整 60 s 输入，12 个窗口通过统一 ECG QC；项目 MAE 37.1163，Lei SSA MAE 38.0582 BPM，coverage 均 85.71%。
- Lei 路线未达到约 20% 一致改善门槛，且 RMSE、相关性、P90 恶化；状态 `PARTIAL_DEVELOPMENT_ONLY_STOP_PHYSIOLOGY_RND`，完成后停止，不自动进入80人。

---

## 2026-08-27 — result(mmwave): complete bounded Task 2R 50 s comparison

### 背景

Task 2 的 30 s 长度冲突通过独立的 50 s method-native external track 处理；该轨道不代表 FocusWave 30 s 产品输出。

### 改动

- 在 AgeBalanced development 30 人、60 个 Rest session 上，以 50 s/5 s 同条件运行项目历史方案和 SSA+VMD `paper_reimplementation/adapted`。
- 修复 500 帧数据经过相位差分后被错误缩成 499 点的长度对齐问题；两种方法共用相同窗口与 ECG reference。
- 固定配置 hash `29977811e91aea54eb94b69a4ba0587db0a80049cca89aab87df183b1695e57c`，输出保留本地 hash，不提交原始/逐窗口数据。

### 验证

- 两种方法均 81/88 scored，coverage 92.05%；项目 MAE 29.02，SSA+VMD MAE 28.12 BPM，改善 0.90 BPM。
- Median AE 略差，相关接近零，2x/0.5x 总锁频未下降；两者均未达到 HR gate。
- Task 2R 状态 `PARTIAL_DEVELOPMENT_ONLY`，建议 `DOWNGRADE_PHYSIOLOGY`，不自动进入 80 人。

---

## 2026-08-27 — decision(mmwave): bound Task 2 to one external SSA+VMD reference

### 背景

比赛主线要求在约 2.5 小时内判断一个成熟外部方案是否值得继续，而不是扩展开放式算法搜索。

### 改动

- 对唯一允许的 SSA+VMD / EE-PCC-VMD 路线完成论文、参数、实现类别和输入兼容性审计。
- 记录 `SSA L=400`、VMD `K=5/alpha=1000/DC=1/init=0/tol=1e-6` 及与 AgeBalanced 30 s/10 Hz 输入的冲突；不自行修改参数、不补零、不切换候选。
- 生成 Task 2 机器可读决策与结果报告，保留项目 baseline 作为唯一已测 development 结果。

### 验证

- 外部路线在 adapter compatibility gate 被标记 `BLOCKED`，没有生成候选 benchmark 分数。
- 项目 baseline 仍为 coverage 95.5%、MAE 26.98、median AE 13.79、RMSE 41.13 BPM，未达到冻结 HR gate。
- Task 2 停止；建议 `DOWNGRADE_PHYSIOLOGY`，不自动进入 held-out、RS6240 或 `J:\\Data`。

---

## 2026-08-27 — feat(mmwave): execute bounded Phase 2B-1 historical-baseline reproduction

### 背景

在不改写 Phase 2A Decision V1、且不访问 held-out、`J:\\Data`、HRV 或新候选算法的限制下，需要验证统一 benchmark 基础设施能否承载历史 AgeBalanced baseline。

### 改动

- 实现并测试 `ecg_reference_v1`，新增历史 baseline adapter、冻结配置哈希和 30 s `per_window_benchmark_v1` 输出。
- 开发集（30 participants/60 Rest sessions）完成 25 s/5 s 历史等价性诊断及 30 s/5 s schema-valid baseline；原始逐窗口输出只保留本地 Git-safe provenance/hash。
- 新增 Phase 2B-1 差异审计，明确 25 s window 与 V1 schema 不兼容，以及历史 quality/harmonic aggregation 的 `MISSING_EVIDENCE`。

### 验证

- `ecg_reference_v1` 测试通过；开发集 60/60 session 的 full-session ECG QC 通过；30 s 输出逐行通过 schema 验证。
- 本阶段状态 `PARTIAL_DEVELOPMENT_ONLY`：没有将 60-session 结果虚报为全体 220-session 复现，也没有更改任何 frozen threshold/split/QC。

---

## 2026-08-27 — docs(mmwave): freeze Phase 2A benchmark contract before held-out scoring

### 背景

Phase 1 资产审计已经完成；在复现历史 baseline 或查看任何新算法 held-out 成绩前，需要先冻结数据、reference、窗口、质量门、指标、数值阈值和选择规则。

### 改动

- 新增 `BENCHMARK_DECISION_V1.md` 和机器可读 Decision V1；冻结 AgeBalanced 30/80 被试切分、30 s/5 s 主窗口、ECG/RSP reference-first QC、同步、质量分层、指标、谐波误锁与算法选择规则。
- 新增阈值依据、reference audit 和实现级 Reuse Gate；无原作者代码的方法统一标为 `paper_reimplementation`，缺许可证/不兼容实现保留为 blocked。
- AgeBalanced 逐文件对账得到 110 participants、440 total sessions、220 historical Rest sessions；记录 2,424 文件哈希。RS6240 reference inventory 确认 ECG 11/11、RSP 10/11，并保留两个 ID mismatch。
- 新增 `per_window_benchmark_v1` JSON Schema、测试及 Git-safe provenance manifests。

### 验证

- Phase 2A 只执行 provenance/reference 审计、合同冻结和 schema 测试；未运行历史 baseline、候选算法 benchmark、held-out 评分或 `J:\Data` 正式 cohort。
- HRV 与 Phase 2B 均未授权；旧 canonical 结果没有被覆盖。

---

## 2026-08-27 — docs(mmwave): establish MMWAVE_FORMAL_REANALYSIS_V2 evidence surface

### 背景

现有毫米波工作分散在历史 v1-v9、外部金标准、C1/M1/C2B/C2C 和正式数据审计中；历史“做过”记录不能直接等同于生理验证通过。

### 改动

- 在独立分支 `codex/mmwave-formal-reanalysis-v2` 新增 Git-safe V2 证据账本、数据集/方法/参数/失败模式矩阵、benchmark 计划、验证门、正式 cohort 计划、缺口清单和交接文件。
- 新增 `configs/mmwave_reanalysis_v2/manifest.json`，冻结当前阶段的执行边界：不启动正式 cohort、不恢复 HRV、不提交原始或逐行数据。
- 仅做指针式状态更新；旧分析和旧结果保持不变。

### 验证

- 已核验治理、workspace registry、中央仓库身份、当前 main 基线、现有毫米波注册项、历史提交/脚本、VitalSense benchmark 预检/复现和本地数据根存在性。
- Phase 1 没有运行新的科学 benchmark；状态为 `PARTIAL`。

## 2026-08-25 — audit(mmwave): J 盘目标锁定与 RGB 门控状态同步

### 背景

J 盘全场距离候选不足以证明毫米波持续锁定人体，需要把时间稳定性、8 通道空间一致性和 RGB 运动门控纳入跨会话可恢复状态。

### 改动

- 新增 `PROJECT_STATUS.md` 和 `.harness/analysis-state.json`，记录正式/验证管线边界、当前候选分片、负例和下一步。
- 新增 `docs/methodology/target_lock_audit.md`、`docs/methodology/rgb_motion_gate.md` 和对应决策记录。
- 新增参数化 RGB 运动门控与双门控合并脚本，输入通过命令行提供，不写死本地数据目录。
- 实际被试数据、视频、逐帧结果和大体量派生结果继续保留在本地 `11_数据\\derived`，不进入仓库。

### 验证

- 本地已完成 sub-078/sub-091 的首、中、末分片空间一致性和 RGB 探索性门控审计。
- 本次提交只包含方法、状态、决策和通用脚本，不包含原始数据或被试级派生数据。

---

## 2026-08-24 — v1.8 算法库结构整理、金标准资产归档与模型共享

### 背景

算法库根目录混合了项目说明、审计数据、NIR 工程、模型权重和运行环境，导致主线入口与可共享资产难以区分。此次整理以不移动原始数据、保留 NIR 独立 Git 历史、让同事可从 GitHub 获取模型为约束。

### 改动

- 根目录只保留仓库入口文件；项目管理说明、系统说明、运维日志、审计数据和审计脚本分别归档到 `docs/`、`data/` 和 `scripts/审计/`。
- 从 `11_数据` 移入算法库的小型派生质量表归档到 `data/质量/`；原始采集数据保持原位置不动。
- 新增 `docs/项目管理/算法库整理索引.md` 和 `外部工程版本.md`，登记主线入口、NIR 工程版本、路径边界和共享规则。
- 新增 `models/` 统一共享 NIR、RITnet、人脸检测和 DeepVOG 权重；通过 Git LFS 管理 `.h5`、`.onnx` 和 `.pt` 文件。
- 修正根目录文件移动后的脚本路径和系统说明链接。

### 验证

- 当前主线 `scripts/` 在排除 `archive_历史版本` 后 Python 编译通过。
- `scripts/审计/build_mmwave_audit.mjs` Node 语法检查通过。
- Git 工作区差异检查通过；历史归档中的 `process_vital_signs_v2_0.py` 仍有既存语法错误，未纳入当前主线。

### 版本边界

两个 NIR 工程保留独立仓库和本地未提交改动，不在本次主库提交中覆盖；主库通过版本登记和 `models/` 共享权重提供统一入口。

---

## 2026-08-14 — v1.7 问卷×行为×主程序三方对照 + 外部金标准数据集验证

### 背景

预实验答卷（7 人）需与 J 盘行为数据（11 人）及 FocusWave 主程序实现三方对照，找出
主观报告与客观数据的偏差来源；同时引入两个外部公开数据集（phish-tech TI 原始 ADC、
Zenodo 60GHz AgeBalanced 110 人 ECG 金标准）验证处理链路的跨设备可用性与金标准精度，
补上"HRV 验证必须 ECG"的缺口。

### 改动

- **问卷合并与三方对照报告**：`scripts/merge_preexp_surveys_0813.py`（v3 版 3 人补编号
  001-003 与 v4 版 004-007 合并）、`docs/报告/预实验问卷深入分析_结合主程序_0813.md`
- **序列规律双重实锤**：formal_A/B/C 均为 18 试次 cycle 机械重复 ×12，no-go 间隔
  完全固定（A=4/5、B=9、C=18），B 条件柠檬后 100% 接苹果；7/7 被试自报发现规律
- **判定逻辑审计**：commission/omission 响应窗口含掩蔽期（1150ms），74% 的
  commission 是掩蔽期节奏性按键（掩蔽后段 32 次预按的下一试次 100% 是 GO）；
  修正口径（仅刺激期 rt≤250ms）后条件效应 A 9.8% > C 4.2% > B 2.4%，个体模式
  与问卷自述吻合（002 紧张/疲倦、005 干扰窗、007 最后一轮）
- **时间戳规范澄清**：CSV 第 2 列（DLL 固件时戳，间隔中位 10.0ms）用于帧内时间轴，
  第 3 列（Python 回调，抖动大）仅用于跨模态对齐；写入 `docs/决策/规范备忘.md`
- **生命体征逐步图**：`scripts/plot_vitalsign_pipeline_0813.py`（静态杂波去除 + 3D mesh +
  带内功率选门 + SOS 窄带滤波，支持 --mesh-only / --all）；修复 IIR 低频窄带
  滤波数值爆炸（b/a → SOS）与噪声门误选（幅度阈值排除）
- **外部金标准验证管线**：`scripts/validate_external_gold_0814.py`（25s 窗 5s 步长时频
  融合 + quality 门控 + 谐波判别 + 金标准对比）；`scripts/analyze_external_heartbeat_0814.py`
  （TI 原始 ADC 解析，10 文件全跑通）
- **三项 A/B（见优化决策记录实验 35）**：T 波剔除（金标准 R 峰 26% 误检修复）、
  HPS 谐波乘积谱（2 倍锁定 32→4，保留）、时间轨迹连续性（保留）、呼吸谐波
  固定陷波（净负收益回退，v9 模拟验证的边界条件补全）

### 验证

- 外部金标准（220 会话）：总体 MAE 中位 9.5 BPM，quality 分层有效（high 1.6 /
  med 3.4 / low 10.1 BPM），2 倍锁定 4/1188 窗、半频锁定 0
- 跨设备：phish-tech TI 原始 ADC（4MHz/20Hz 快慢时间，与 POSSUMIC 完全不同格式）
  直接跑通，10 文件输出生理合理范围
- 行为数据：11 人时间轴与问卷提交时间交叉验证全部吻合（含双设备并行实验发现）

### 涉及文件

- `scripts/merge_preexp_surveys_0813.py`、`scripts/analyze_preexp_behavior_0813.py`（J 盘 11 人）
- `scripts/plot_vitalsign_pipeline_0813.py`、`scripts/validate_external_gold_0814.py`、
  `scripts/analyze_external_heartbeat_0814.py`
- `docs/报告/预实验问卷深入分析_结合主程序_0813.md`
- `docs/决策/规范备忘.md`（时间戳规范）、`docs/决策/优化决策记录.md`（实验 35）
- 数据：`11_数据/外部数据集_AgeBalanced_60GHz/`（110 人）、
  `11_数据/外部数据集_mmWave_Heartbeat/`（TI gby 批次）
- 一敏 v3.1 结果归档（心率时序改进，25s 窗 5s 步长时频融合 + 2:1 谐波修正 +
  quality 门控；raw/replay 双跑可复现）：
  - `output/旧实验/08_旧批次-DEEP-BREATH/v3_1/`（raw + replay）
  - `output/旧实验/08_旧批次-REST-3min/v3_1/`（raw + replay）
  - `output/旧实验/08_旧批次-SXQ-47min/v3_1/`（raw + replay）
  - 报告：`docs/报告/v3.1心率时序改进与验证报告.md`
  - 验证：rest_3min 100% 高质量窗（HR 91.7±1.7）；sxq/deep-breath 约 52% 高质量窗，
    使用需按 `quality != low` 筛选；HRV 需另行建立带质量门控的 NN 间期序列

---

## 2026-08-11 — v1.6 自主优化夜（31 项实验 + 摄像头-毫米波融合门控）

### 背景

用户要求睡眠期间自主尝试文献/仓库中的优化方法（NeuroKit 分析思路 +
mmHRV/倪杰2024/Radar_monitor 等来源），并利用摄像头数据融合。

### 改动

- **外部方法 A/B（7 项, 全无实质改进）**: SPC 定位（+1.8%, 保留 --use-spc 开关）、
  Hampel IBI 清洗（误伤 RSA 撤销）、相位差分/CFAR/SSA/包络归一化/CEEMDAN（不采用）
- **摄像头-毫米波融合（核心发现）**: NIR/RGB 1Hz 运动量 × 毫米波质量门
  **6/6 被试全显著**（000/003/004/005/006/007, d 中位 -0.90）; AUC 0.69,
  P90 阈值标记伪影精确率 76%; 工具 `motion_gate.py`; 方案
  `docs/摄像头毫米波融合门控方案.md`; 边界: 极弱信号（001 型）不适用
- **融合应用**: 006 错误窗 BR 升高通过运动量控制（非伪影）; 运动窗 HRV 虚高
  （RMSSD +55%）防护; 运动量门后事件相关更保守可信
- **行为机制**: 探针前后行为无一致变化（Wiemers2019 一致）; 错误后 RT 个体差异
  （005 冲动型 vs 007 警觉型）; RT 规律学习加速（007 313→177ms）
- **答卷分析**: 自报（睡眠/不适/专注力）与客观指标全面脱节
- **文献库**: Zotero 334 条中精读 7 篇（Corcoran2025/Martínez-Pérez2023/mmHRV/
  Cui2025/Gao2025/Joshi2025/Paterniani2023）——确认现有管线覆盖主流方法
- **正式实验设计建议**: docs/正式实验设计建议.md（刺激序列/探针/采集/管线/样本量）

### 验证

- 融合门控: 6/6 被试 p<0.05（000 p<0.001 d=-1.12; 005 p<0.001 d=-1.19 最强）,
  时间级趋势耦合（003 运动量↑质量↓同步）, 001 反向为时间混淆
- 外部方法: 预实验质量门口径下无改进——现有管线（门控+相位判别+谐波陷波+
  VMD+窄带逐拍+质量门）环节已覆盖

### 涉及文件

- `scripts/experiment_{spc,hampel,phasediff,cfar,ssa,envelope,ceemdan}.py`（7 项 A/B）
- `scripts/experiment_video_motion.py`、`scripts/experiment_video_roi.py`、`scripts/motion_gate.py`
- `scripts/analyze_survey_physio.py`、`scripts/analyze_probe_effect.py`
- `docs/优化决策记录.md`（31 项实验）、`docs/摄像头毫米波融合门控方案.md`、
  `docs/正式实验设计建议.md`、`docs/毫米波数据Q&A.md`（+5 篇文献笔记）

---

## 2026-08-11 — v1.5 分析框架扩展（NeuroKit 思路：事件相关 + 非线性 HRV + 标准化报告 + 特征矩阵）

### 背景

预实验探针标签偏斜（003/006 全"专注"）且被试对"刚才"的理解与探针前 30s 窗定义有出入，
仅靠探针窗分析信息量不足。参考 NeuroKit 的分析框架（预处理管线 → 事件相关 →
区间特征 → 统计建模），补上事件锚点、非线性特征、标准化预处理报告与统一特征矩阵。

### 改动

- **`analyze_erp_errors.py`（新增）**：行为错误事件相关分析。以 commission/omission
  为事件锚点（不依赖探针标签），事件映射到 30s 生理窗，对比错误窗 vs 非错误窗 +
  错误前/错误/错误后窗响应曲线。预实验事件池 183 commission + 252 omission，
  为探针的数十倍
- **`hrv_nonlinear.py`（新增）+ 窗特征扩展**：SampEn（样本熵）与 DFA（去趋势波动
  分析）α1/α2 写入全程窗与探针窗特征；`analyze_mmwave_hrv.py` 将 IBI 序列挂出
- **`gen_preexp_reports.py`（新增）**：标准化预处理报告（质量门 SNR/IBI + 全程窗
  可用率 + 生理/行为/探针汇总），对齐 NeuroKit pipeline 报告理念
- **`export_window_matrix.py`（新增）**：全被试可信窗特征矩阵
  （277 窗 × 18 特征 CSV），统一分析入口

### 验证（预实验 000-007）

- **错误窗呼吸率一致升高**：聚合 Cohen's d=+0.70（4/4 被试同向），
  003 d=0.77 p=0.011、006 d=1.32 p=0.0004 显著；错误后窗 RMSSD 回升
  （005: 18.0→24.3、007: 22.7→28.2）——"错误→唤醒→恢复"的事件相关模式
- SampEn 自测方向正确（正弦 0.105 vs 白噪声 1.892）；窗特征覆盖 275/277 窗
- 所有预实验被试（000-007）完成标准化预处理报告（004-007 质量可信，
  007 全程窗可用率 76.5% 最高）

### 注意

- 错误窗呼吸升高可能部分来自错误按键的动作伪影，细粒度分析需加正确按键窗对照
- SampEn 在部分高度规则窗返回 nan（缺失值处理）
- 探针标签偏斜问题未解决（003/006 仍全专注），探针分析仍受限于标签分布

### 涉及文件

- `scripts/analyze_erp_errors.py`、`scripts/hrv_nonlinear.py`（新增）
- `scripts/gen_preexp_reports.py`、`scripts/export_window_matrix.py`（新增）
- `scripts/analyze_mmwave_hrv.py`（IBI 挂出）、`scripts/analyze_mmwave_full.py`（非线性特征接入）
- `output/预实验/03_跨被试/09_预实验-事件相关/`、`09_预实验-预处理报告/`、`09_预实验-窗特征矩阵/`



| 版本 | 作者 | 日期 | 心跳方法 | 呼吸方法 | 结论 |
|:--:|------|------|------|------|------|
| v1 | 黄小轩 | 07-18 | 带通滤波 | 带通滤波 | 打通 pipeline |
| v2 | 黄小轩 | 07-23 | VMD (K=4) | 带通滤波 | HR 差距 30→5 BPM |
| v3 | 一敏 | 07-23 | VMD heart only | bp | ✅ 心跳三组全优于 bp |
| v4 | 一敏 | 07-23 | bp | VMD breath only | ❌ 两组退化 |
| v5 | 一敏 | 07-25 | vmd_heart | bp + 增强峰值 | ✅ 当前主线 |
| v6 | 一敏 | 07-25 | vmd_heart | 包络法 | ❌ 无稳定收益 |
| v7 | 一敏 | 07-25 | vmd_heart | 小波/时频 | ❌ 无稳定收益 |
| v8 | 一敏 | 07-25 | vmd_heart | EMD 变体 | ❌ 无稳定收益 |

脚本：`scripts/process_vital_signs_v1.py ~ v8.py`

> **分支关系说明**：v6/v7/v8 是 v5 主线（vmd_heart + bp + 稳健呼吸峰值）的**失败分支尝试**
> （分别实验包络法、小波/时频、EMD），效果均无稳定收益，未成为主线。
> 主线演进为 v1 → v2 → v3 → v5；分析架构（选 bin/门控/纠错）另立 `analyze_mmwave_hrv.py` v1.1→v1.4（见下方条目）。

### v5 实测结果（当前主线）

| 数据 | HR baseline→vmd_heart | BR | 判断 |
|------|------|------|------|
| v2_sart 29.8s | 76.9→65.3 BPM（频域 64.4） | 正常 | 最有代表性 |
| v3_tztest 9.8s | 84.4→76.5 BPM（频域 79.9） | 正常 | 较优样例 |
| v3_test 10.0s | 97.3→54.1 BPM（频域 48.0） | 失败 | 心跳改善，呼吸未收敛 |

HRV（仅供参考）：SDNN 49~173ms，RMSSD 40~223ms。

### SART-30s 全版本对比（最佳数据）

| 版本 | HR freq→time | 差距 | BR | 结论 |
|------|------|:--:|------|------|
| v1 bp | 64.4→76.9 | 12.5 | 14.1/18.0 | baseline |
| v3 vmd_heart | 64.4→**65.3** | 0.9 | 14.1/18.0 | 心跳大改善 |
| v5 vmd_heart | 64.4→**65.3** | 0.9 | 14.1/**15.0** | 心跳呼吸均最佳 |
| v7 vmd_heart | 66.8→69.8 | 3.0 | 17.8/15.0 | 反而不如 v5 |
| v8 vmd_heart | 64.4→65.3 | 0.9 | 14.1/15.0 | 与 v5 一致 |

结论：v5 仍是唯一一致优于 baseline 的版本，v7（小波）在最佳数据上表现更差。

## 数据对应（历史, 已归档可复现）

`output/` 按原始数据分组（v1~v8 历史输出已于 2026-08-10 整理时归档删除，对应脚本在 `scripts/archive_历史版本/`）：

| 输出目录（历史） | 原始数据 | 时长 | v1 | v2 | v3 | v4 | v5 | v6 |
|---------|---------|------|:--:|:--:|:--:|:--:|:--:|:--:|
| `01_DebugTool/` | DebugTool 导出 | 73.6s | ✓ | ✓ | | | | |
| `02_SART-30s/` | radar_collector data_v2 | 29.8s | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `03_TZTEST/` | radar_collector data_v3 fix | 9.8s | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `04_TEST-30s/` | radar_collector data_v3 test | 30s | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `05_SART-50min/` | radar_collector data_v3 SART | 50min | ✓ | ✓ | | | | |

> 当前 output/ 保留 07-10 系列（analyze_rest_3min / analyze_mmwave_hrv / analyze_mmwave_full / analyze_preexp_* / analyze_deep_breath / compare_4subjects 输出），命名见 `09_预实验-*` / `08_旧批次-*`。原始数据不随仓库分发。

## 后续改进方向

心跳 vmd_heart 已确认有效。当前瓶颈在呼吸——困难数据仍不稳定，HRV 未标准化。

---

## 2026-08-10 — v1.4 预实验全被试分析链（质量评估 + 稳健性检验 + 数据工具 + 目录规范）

### 背景

预实验新增 004-007 四被试。采集出现两类数据问题：005 被试编号被误输为 004；004 被试在实验结束后（Block6 停止后）离开座位但忘记停止采集，尾部约 5.5 分钟为无效数据。同时，000/003 的窗级相关此前出现"003 hr~RT 显著但 Spearman 不显著"的伪相关，需要统一的质量门与稳健性检验流程覆盖全被试。

### 改动

- **质量评估独立管线**：`assess_preexp_quality.py`（文献标准流程：距离功率谱定位 → 相位方差人体判别 → 呼吸谐波 iirnotch 陷波 → 心跳带 SNR/IBI 窗级门控；多候选 bin 应对近距杂波定位竞争），作为全程 HR/HRV 与探针窗分析的前置质量门
- **数据工具（新增）**：`truncate_preexp_data.py`（按行为实验结束或自定义时刻截断 mmwave 数据，npz/timestamps/bin/meta 全量同步，被截片入备份目录）；`rename_preexp_subject.py`（修正采集时编号输入错误，文件名/meta/CSV 全量）
- **004 数据修正**：按 Block6 停止时刻截断至 254837 帧（2574.4s），与行为实验完全对齐
- **005 数据修正**：全量重命名 + meta/CSV 内部字段修正
- **全被试分析**：004-007 质量评估、全程窗+探针特征（analyze_mmwave_full）、全 8 被试相关稳健性检验（analyze_preexp_robustness 扩展 SUBJECTS 全量）、跨被试 HR/HRV 分布对比（compare_preexp_hrv）、8 被试距离-时间热图（gen_range_time_maps 2×4）
- **目录规范**：output 重命名为 `09_预实验-*`（预实验批次）/ `08_旧批次-*`（8/1 旧批次 + 早期探索），消除 08/09 批次混淆；scripts 新增 README 索引（主线/工具/旧批次/基础模块/历史归档），归档过时脚本；01_管理 三文档同步新命名

### 验证

- 004-007 心跳质量全部"可信"（93%/99%/100%/100%，质量评估口径）；007 全程窗可用率最高（76%）
- 全 8 被试无跨被试一致、稳健显著的行为×生理相关；006 sdnn/rmssd~rt_mean Pearson 显著（p=0.018-0.025）但 Spearman 不显著（p=0.09-0.12），按判伪标准（Spearman 必须显著）判为边缘候选
- 个体差异（被试间 n=7）无显著，rmssd~RT 边缘相关由 001 杠杆点驱动（RMSSD 53 异常）
- 截断后重跑质量评估：末尾窗正常、static_target 窗消失、HR 伪影窗从 11 个降至 3 个（任务期内，保留）
- 脚本语法检查与 import 依赖验证通过（v2/v3/v5/v9 基础模块未被归档破坏）

### 实测结论（预实验 000-007）

| 被试 | 质量评估可信窗 | 全程窗可用率（v1.3 口径） | 备注 |
|------|--------------|--------------------------|------|
| 000 | 43% | 43% | 有信号 |
| 001 | — | 16% | 太弱 |
| 002 | — | 0% | 无信号 |
| 003 | 46% | 46% | hr~rt Pearson 显著但 Spearman 不显著（伪相关） |
| 004 | 93%（截断后 91%） | 31% | 已按行为结束截断 |
| 005 | 99% | 38% | 编号已修正 |
| 006 | 100% | 61% | sdnn/rmssd~rt Pearson 显著, Spearman 不显著（边缘候选） |
| 007 | 100% | 76% | 质量最好 |

**结论**: 全 8 被试无跨被试一致、稳健显著的行为×生理相关; 个体差异（n=7）
无显著（rmssd~RT 边缘相关由 001 杠杆点驱动）; 探针标签偏斜（003/006 几乎全"专注"）,
探针分组对比功效不足。预实验数据对"毫米波区分注意力状态"的验证能力有限, 待正式实验。

### 涉及文件

- `scripts/assess_preexp_quality.py`（新增）
- `scripts/truncate_preexp_data.py`、`scripts/rename_preexp_subject.py`（新增）
- `scripts/analyze_mmwave_full.py`、`scripts/analyze_mmwave_hrv.py`、`scripts/analyze_preexp_robustness.py`、`scripts/analyze_rest_3min.py`、`scripts/analyze_deep_breath.py`、`scripts/compare_4subjects.py`、`scripts/gen_range_time_maps.py`（目录路径同步）
- `scripts/README.md`（新增索引）、`scripts/archive_历史版本/`（+2 归档脚本）
- `output/`（目录规范重命名）、`01_管理/分析记录.md`、`01_管理/图表索引.md`、`01_管理/资源索引.md`
- `docs/版本说明.md`（并入本文件后删除）

---

## 2026-08-07 — v1.3 分析管线（analyze_mmwave_hrv.py, 综合管线）

### 背景

段级固定 bin 在部分窗信号差 → HR 假跳变；VMD 后主频漂移到倍频；单强反射场景（001）倍频锁错无冗余；环境反射误判心跳（008 曾选到 bin253=9.4m）；呼吸谐波污染心跳带。四被试（001/007/008/SXQ）统一管线需要综合修复。

### 改动（管线演进）

| 版本 | 改进 | 解决的问题 |
|------|------|-----------|
| v1.1 | 窗级自适应选 bin（每窗独立, 替代段级固定） | 段级固定 bin 在部分窗信号差 → HR 51→104→51 假跳变 |
| v1.1 | 频率锚定 bp 主频（窄带检测中心） | VMD 后主频漂移到倍频（HR 51→135 假跳变） |
| v1.1 | MIN_PEAKS 窗长自适应（30s→15 拍起） | 固定 30 拍对 30s 窗过严, 探针窗可用率 29%→71% |
| v1.2 | 多 bin 交叉验证（同段多 bin 心率一致性） | 单 bin 主频锁错无冗余（007 的 59 次伪影靠此修复） |
| 附加 | 距离门控 bin 8-45（≈30-166cm） | 环境反射误判心跳（008 曾选到 bin253=9.4m） |
| 附加 | 呼吸谐波陷波（v9 模块: 呼吸主频+2/3 次谐波 iirnotch） | 呼吸谐波污染心跳带（模拟验证: 谐波功率降 97% 心跳无损） |
| 附加 | 动作帧检测（帧间幅度差分 + MAD 阈值） | 大幅度动作破坏相位解调 |
| v1.3 | 段参考修正（med_hr_hint: 心率不瞬间翻倍） | 单强反射场景（001）倍频锁错无冗余可纠正, 探针窗 75%→100% |

### 验证（四被试, 统一管线 v1.3）

| 被试 | 全程窗可用率 | 探针窗可用率 |
|------|-------------|-------------|
| 001 | 88/91 (97%) | 24/24 (100%) |
| 007 | 96/96 (100%) | 48/48 (100%) |
| 008（排除休息） | 65/65 (100%) | 48/48 (100%) |
| SXQ（排除休息） | 46/57 (81%) | 38/48 (79%) |

### 关键教训（08-07）

1. **001 信号弱系误诊**: PTP 对比用了错误 bin（近场杂波）; 人体 bin 对比显示
   001 心跳 SNR 10.8（007/008 的 4 倍）, 001 是"好但孤"（单强反射无冗余）
2. **跨被试合并必须个体标准化**: 原始合并 SDNN p=0.007 的"显著"在
   被试内 z-score 后消失（p=0.34）——个体基线差异伪装成组间效应
3. **全程固定 bin 不可行**: 46 分钟任务 bin 漂移, 窗级自适应（97%）优于
   固定 bin（55/91）; 3 分钟静止才适合固定 bin（REST-3min 案例）

### 涉及文件

- `scripts/analyze_mmwave_hrv.py`
- `scripts/process_vital_signs_v9.py`（谐波陷波模块）
## 2026-08-27 — docs(mmwave): complete Issue #7 existing-asset and failure audit

- 新增 `docs/mmwave_reanalysis_v2/ISSUE_7_ROOT_CAUSE_B_AUDIT.md`，将历史 v1–v9/v3.1.1、七项 A/B、AgeBalanced、VitalSense、RS6240 采集实现和当前 benchmark contract 串成可追溯复用矩阵。
- 将 F-001–F-010 失败模式映射到具体代码/报告/提交，并冻结复用、排除、阻塞和停止边界。
- 本任务未运行新生理 benchmark，未访问 held-out/J:\\Data/HRV，未引入原始或逐行数据。
