# 毫米波雷达生命体征提取算法

基于 8 通道复包络数据（npz）提取心率（HR）、呼吸率（BR）、心率变异性（HRV）。
厚粲杯项目「毫米波多模态注意力测量」的信号处理与分析模块。

## 目录结构

```
08_算法/
├── README.md
├── scripts/                     ← 全部代码（详见 scripts/README.md 索引）
│   ├── process_vital_signs_v2/v3/v5/v9.py   ← 管线基础模块（被 import, 勿删）
│   ├── assess_preexp_quality.py ← 心跳质量评估（文献标准流程, 分析前置质量门）
│   ├── analyze_mmwave_full.py   ← 全程 × 行为联合分析（探针特征+时间线）
│   ├── analyze_mmwave_hrv.py    ← 休息段 HRV 分段分析（窗级自适应选 bin）
│   ├── analyze_preexp_robustness.py ← 行为×毫米波相关稳健性检验（全被试）
│   ├── compare_preexp_hrv.py    ← 跨被试 HR/HRV/行为分布对比
│   ├── gen_range_time_maps.py   ← 全程距离-时间热图（8 被试 2×4 对比）
│   ├── truncate_preexp_data.py  ← 数据截断（按行为实验结束, 尾部无效数据清理）
│   ├── rename_preexp_subject.py ← 被试编号修正（采集时输入错误）
│   ├── analyze_rest_3min.py / analyze_deep_breath.py / compare_4subjects.py ← 旧批次分析
│   ├── tools/                   ← 独立工具（check_preexp_data / compare_all_datasets）
│   └── archive_历史版本/         ← v1~v8 旧版本+过时脚本（只读归档）
├── docs/
│   ├── CHANGELOG.md             ← 修改说明 + 版本演进（参照 FocusWave：日期 — v版本 主题）
│   ├── requirements.txt         ← 依赖清单
│   ├── 规范备忘.md              ← Git 提交规范 / 目录命名 / 文档规范
│   ├── 信号处理算法文献.md       ← 文献库
│   ├── 毫米波数据Q&A.md
│   └── 交付/                    ← 给外部专家的交付包（仅清单 md/ris 入仓库）
├── output/                      ← 分析产物（git 忽略，可再生成）
│   ├── 09_预实验-*              ← 预实验批次 000-007（FULL/QUALITY/ROBUST/COMPARE）
│   └── 08_旧批次-*              ← 旧批次 001/007/008/SXQ + 早期探索
└── .gitignore
```

## Pipeline（分析架构 v1.4，2026-08-10 起）

```
原始 npz 分片（每片 1000 帧, 256 距离门 × 8 通道）
    ↓ [v1.4] 前置质量门: assess_preexp_quality（SNR≥3dB 且 IBI 有效率≥0.8 → 可信窗）
    ↓ 窗级自适应选 bin（每窗独立, 跟踪 bin 漂移）+ 多候选 bin（定位竞争）
    │    + 距离门控 bin 8-45（≈30-166cm, 排除环境反射）
    ↓ 呼吸谐波陷波（呼吸主频 + 2/3 次谐波 iirnotch, v9 模块）
    ↓ 多 bin 交叉验证（同段多 bin 心率一致性）
    ↓ 段参考修正（心率不瞬间翻倍, 纠正倍频锁定, v1.3）
    ↓ 相位解卷绕 → 胸壁位移
    ↓ 分离: 呼吸 bp（0.1-0.5 Hz）/ 心跳 VMD heart-only（0.8-2.5 Hz）
    ↓ 窄带逐拍检测 + IBI → HR / BR / HRV（时域+频域）
```

信号分离方法演进 v1-v8 与分析架构演进 v1.1→v1.4 见 `docs/CHANGELOG.md`（v6/v7/v8 为 v5 失败分支，已归档）。

## 用法

数据根目录：预实验 `F:/预实验`（sub-000_~sub-007_），输出统一到 `output/`（`09_预实验-*`）。

```bash
cd scripts

# 预实验分析主线（000-007，按顺序）
python assess_preexp_quality.py --subject 004 --data-root F:/预实验        # ① 质量门
python analyze_mmwave_full.py --subject 004 --data-root F:/预实验 \
    --output-dir 09_预实验-SUB004-FULL                                    # ② 全程窗+探针特征
python analyze_preexp_robustness.py --data-root F:/预实验                  # ③ 相关稳健性（全被试）
python compare_preexp_hrv.py                                               # ④ 跨被试分布对比
python gen_range_time_maps.py --data-root F:/预实验                        # ⑤ 距离-时间热图

# 数据工具
python truncate_preexp_data.py --subject 004 --data-root F:/预实验         # 尾部无效数据截断（默认按行为结束）
python rename_preexp_subject.py --subject 005 --wrong-id 004               # 编号输入错误修正

# 旧批次分析（8/1 采集, 可复现）
python analyze_mmwave_hrv.py --subject 001
python analyze_mmwave_full.py --subject 008 --exclude-rest
python compare_4subjects.py
python analyze_deep_breath.py
```

## 依赖

```bash
pip install -r docs/requirements.txt
```

| 库 | 状态 | 用途 |
|----|:--:|------|
| numpy / scipy | 已用 | 信号处理基础 |
| vmdpy | 已用 | VMD 分离心跳（K=4, alpha=1000） |
| matplotlib | 已用 | 出图 |
| PyWavelets | 待定 | 小波变换（v7 失败分支曾用） |

## 数据

原始采集数据（npz 分片 / bin）**不随仓库分发**（体积 GB 级 + 被试隐私）。
- 预实验数据：`F:\预实验\sub-XXX_\`（mmwave/ + beh/，000-007）
- 旧批次数据：`F:\sub-XXX_\`（mmwave/ + beh/，001/007/008/SXQ）
- 历史数据：`11_数据/radar_collector/`

## 可追溯

- 图 → 脚本 → 版本对应：`01_管理/图表索引.md`（仓库外，项目根目录）
- 算法版本演进与修改记录：`docs/CHANGELOG.md`
