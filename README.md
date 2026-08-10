# 毫米波雷达生命体征提取算法

基于 8 通道复包络数据（npz）提取心率（HR）、呼吸率（BR）、心率变异性（HRV）。
厚粲杯项目「毫米波多模态注意力测量」的信号处理与分析模块。

## 目录结构

```
08_算法/
├── README.md
├── requirements.txt
├── scripts/                     ← 全部代码
│   ├── process_vital_signs_v2/v3/v5/v9.py   ← 核心管线（v9 = 定位+谐波抑制主线）
│   ├── analyze_rest_3min.py     ← 3 分钟静止分析（HR/BR/HRV 时域+频域）
│   ├── analyze_mmwave_hrv.py    ← 休息段 HRV 分段分析（窗级自适应选 bin）
│   ├── analyze_mmwave_full.py   ← 全程 × 行为联合分析（探针特征+时间线）
│   ├── analyze_deep_breath.py   ← 深慢呼吸验证（RSA 效应+BR 标定）
│   ├── analyze_preexp_robustness.py / assess_preexp_quality.py ← 预实验质量评估
│   ├── gen_range_time_maps.py   ← 全程距离-时间热图
│   ├── compare_4subjects.py     ← 四被试对比图+统计
│   ├── tools/                   ← 独立工具（compare_range_profiles 等）
│   ├── figures/                 ← 跨数据集对比图生成
│   └── archive_历史版本/         ← v1~v8 旧版本+历史调试脚本（只读归档）
├── docs/
│   ├── 版本说明.md              ← 算法版本演进（v1→v9）
│   ├── 信号处理算法文献.md       ← 文献库
│   ├── 毫米波数据Q&A.md
│   ├── 规范备忘.md
│   └── 交付/                    ← 给外部专家的交付包（仅清单 md/ris 入仓库）
├── output/                      ← 分析产物（git 忽略，可再生成）
└── .gitignore
```

## Pipeline（当前主线 v1.3，2026-08-07 起）

```
npz 距离域复数 (n_frames, 256, 8)   ← 0xC2 datacube = Interval0 RFFT, 不做二次 FFT
    ↓ 窗级自适应选 bin（每窗独立, 跟踪 bin 漂移）
    │    + 距离门控 bin 8-45（≈30-166cm, 排除环境反射）
    ↓ 呼吸谐波陷波（呼吸主频 + 2/3 次谐波 iirnotch, v9 模块）
    ↓ 多 bin 交叉验证（同段多 bin 心率一致性）
    ↓ 段参考修正（心率不瞬间翻倍, 纠正倍频锁定, v1.3）
    ↓ 相位解卷绕 → 胸壁位移
    ↓ 分离: 呼吸 bp（0.1-0.5 Hz）/ 心跳 VMD heart-only（0.8-2.5 Hz）
    ↓ 窄带逐拍检测 + IBI → HR / BR / HRV（时域+频域）
```

历史版本 v1-v8 演进见 `docs/版本说明.md`（v6/v7/v8 为 v5 失败分支，已归档）。

## 用法

```bash
cd scripts

# 休息段 HRV 分析（任意被试）
python analyze_mmwave_hrv.py --subject 001

# 全程 × 行为联合分析（探针特征 + 时间线）
python analyze_mmwave_full.py --subject 008 --exclude-rest

# 预实验全程分析 / 稳健性检验 / 质量评估
python analyze_mmwave_full.py --data-root E:/预实验 --subject 000
python analyze_preexp_robustness.py
python assess_preexp_quality.py --subject 004

# 四被试对比图 + 统计
python compare_4subjects.py

# 深慢呼吸验证
python analyze_deep_breath.py
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
| PyWavelets | 待定 | 小波变换（v7 失败分支曾用） |

## 数据

原始采集数据（npz 分片 / bin）**不随仓库分发**（体积 GB 级 + 被试隐私）。
- 正式实验数据：`F:\sub-XXX_\`（mmwave/ + beh/）
- 预实验数据：`E:\预实验\`
- 历史数据：`11_数据/radar_collector/`

## 可追溯

- 图 → 脚本 → 版本对应：`01_管理/图表索引.md`（仓库外，项目根目录）
- 算法版本演进：`docs/版本说明.md`
