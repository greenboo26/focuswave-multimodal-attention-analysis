# 毫米波雷达生命体征提取算法

基于 8 通道复包络数据（npz）提取心率（HR）、呼吸率（BR）、心率变异性（HRV）。
厚粲杯项目「毫米波多模态注意力测量」的信号处理与分析模块。

## 目录结构（2026-08-14 更新）

```
08_算法/
├── README.md
├── CHANGELOG.md                 ← 修改说明 + 版本演进（git tag v1.7, 2026-08-14）
├── scripts/                     ← 全部代码（21 个活跃脚本 + tools/ + archive_历史版本/）
│   ├── process_vital_signs_v2/v3/v5/v9.py ← 管线基础模块（被 import, 勿删）
│   ├── assess_preexp_quality.py ← 心跳质量评估（SPC 候选判据, 分析前置质量门）
│   ├── diagnose_poor_windows.py ← poor 窗细分诊断
│   ├── analyze_mmwave_hrv.py    ← HRV 核心（30s 窗×15s 步进, 行为轴截断, SPC 选 bin）
│   ├── analyze_mmwave_full.py   ← 全程 × 行为联合分析（探针特征+时间线）
│   ├── analyze_preexp_robustness.py ← 行为×毫米波相关稳健性检验
│   ├── compare_preexp_hrv.py    ← 跨被试 HR/HRV/行为分布对比
│   ├── hrv_nonlinear.py         ← 非线性特征（SampEn/DFA）
│   ├── motion_gate.py           ← 摄像头运动量门（旁证, 非门卫）
│   ├── export_window_matrix.py  ← 窗特征矩阵导出
│   ├── gen_range_time_maps.py   ← 距离-时间热图
│   ├── plot_vitalsign_pipeline_0813.py ← 生命体征 8 步流程图
│   ├── gen_preexp_reports.py    ← 预实验报告批量生成
│   ├── truncate_preexp_data.py / rename_preexp_subject.py ← 数据工具
│   ├── validate_external_gold_0814.py / analyze_external_heartbeat_0814.py ← 外部金标准验证
│   ├── tools/                   ← check_preexp_data / compare_all_datasets
│   └── archive_历史版本/         ← 7 类归档（旧管线/31项A_B实验/旧批次/近场测试/一次性/预实验专项/更早）
├── docs/
│   ├── 报告/                    ← ADC固件实测/测角校准/问卷深入分析 等
│   ├── 方案/                    ← 正式实验设计建议.md（BBBB 定稿）/融合门控方案/近场测试方案
│   ├── 决策/                    ← 优化决策记录.md（36 项实验）/规范备忘.md
│   ├── 交付/                    ← 专家审查包/交付包/答疑清单
│   └── 手册/                    ← 毫米波数据Q&A.md/脚本索引.md/信号处理算法文献.md/生理指标判断手册
├── output/                      ← 分析产物（git 忽略，可再生成）
│   ├── 预实验/                  ← 01_质量评估 / 02_全程窗 / 03_跨被试 / 04_汇总产物
│   ├── 旧实验/                  ← 旧批次（08_旧批次-*）
│   └── 外部数据集/              ← AgeBalanced 金标准验证产物
└── .gitignore
```

## Pipeline（分析架构 v1.7，2026-08-14 起）

```
摄像头运动量（motion_gate.py, 旁证） → 毫米波质量门（SPC 空间相位相干候选判据, 距离门控 bin 0-45）
    → 可信窗（行为时间轴截断: sart_start→最后 block_stop, 默认强制）
    → 呼吸谐波排除（n_harm=6 + 周期图谐波频点剔除）
    → HR/BR/HRV（30s 窗 × 15s 步进; IBI 生理连续性过滤 250ms; 30s 窗不做频域 LF/HF）
    → 行为分型（RT<150 预判 / 真误按 / 预判率）
    → 统计（被试内 z 标准化, 跨被试比较）
```

信号分离方法演进 v1-v8 与分析架构演进 v1.1→v1.7 见 `CHANGELOG.md`。

## 用法

数据根目录：预实验 `J:/预实验`（sub-000_~010_，F 盘已迁），输出统一到 `output/`。

```bash
cd scripts

# 预实验分析主线（默认按行为时间轴截断）
python assess_preexp_quality.py --subject 010 --data-root J:/预实验        # ① 质量门
python analyze_mmwave_full.py --subject 010 --data-root J:/预实验 \
    --output-dir 预实验/09_预实验-SUB010-FULL                             # ② 全程窗+探针特征
python analyze_preexp_robustness.py --data-root J:/预实验                  # ③ 相关稳健性（全被试）
python compare_preexp_hrv.py --data-root J:/预实验                         # ④ 跨被试分布对比

# 数据工具
python truncate_preexp_data.py --subject 004 --data-root J:/预实验         # 尾部无效数据截断
python rename_preexp_subject.py --subject 005 --wrong-id 004               # 编号输入错误修正

# 外部金标准验证（AgeBalanced 60GHz, Zenodo 10.5281/zenodo.16760683）
python validate_external_gold_0814.py --data-root "J:/外部数据集_AgeBalanced_60GHz"
```

## 依赖

```bash
pip install -r requirements.txt
```

| 库 | 状态 | 用途 |
|----|:--:|------|
| numpy / scipy | 已用 | 信号处理基础 |
| vmdpy | 已用 | VMD 分离心跳（K=4, alpha=1000） |
| matplotlib | 已用 | 出图 |

## 数据

原始采集数据（npz 分片 / bin）**不随仓库分发**（体积 GB 级 + 被试隐私）。
- 预实验数据：`J:\预实验\sub-XXX_\`（mmwave/ + beh/，000-010；分析集 003-010 共 8 名）
- 旧批次数据：`E:\sub-XXX_\`（001/007/008/SXQ）
- 外部数据集：`11_数据/外部数据集_AgeBalanced_60GHz/`（110 人 ECG 金标准）、`11_数据/外部数据集_mmWave_Heartbeat/`（TI 原始 ADC）
- 历史数据：`11_数据/radar_collector/`

## 可追溯

- 图 → 脚本 → 版本对应：`01_管理/图表索引.md`（仓库外，项目根目录）
- 分析记录：`01_管理/分析记录.md`（各次分析结论, 即时登记）
- 资源索引：`01_管理/资源索引.md`（重点文件位置速查）
- 算法版本演进与修改记录：`CHANGELOG.md`
- 文献：`03_文献/`（毫米波 / 毫米波HRV / 生理指标 / 走神探针）
