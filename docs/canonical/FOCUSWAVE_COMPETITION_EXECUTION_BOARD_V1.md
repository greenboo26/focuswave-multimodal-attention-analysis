# FocusWave 厚粲杯执行看板 V1

Status: `ACTIVE_EXECUTION_BOARD`

本看板只回答三个问题：**现在在哪、下一步是什么、什么条件下算完成。**

| 轨道 | 当前状态 | 当前工作 | 下一步 | 完成条件 |
|---|---|---|---|---|
| A. NIR producer | RUNNING / REPAIRING | 修复后批量重跑 | 汇总 coverage / failure / quality | 有稳定派生特征 + 质量字段 + 可用率报告 |
| B. Behavior / probe | ACTIVE | 保持 canonical 主分析 | 整合 time-on-task、vigilance、RT/RTV、错误 | 形成不依赖生理模态也成立的测验骨架 |
| C. 事后问卷 | ACTIVE / NEEDS_INTEGRATION | 整理效标与条目语义 | 对接整体专注、疲劳、走神、持续时间等产品指标 | 形成外部效标/收敛效度表，不夸大为标准化量表 |
| D. mmWave | TASK2R READY | Task 2 在30s条件下因 SSA `L=400` 与300点输入不兼容而停止；该结果不否定外部方法 | 在 AgeBalanced development 30 人上续跑 50s method-native comparison：项目历史方案 vs SSA+VMD | 若50s比较可复现且至少一个方案值得外部泛化，再进入80 held-out；否则停止 physiology 算法扩展 |
| E. 多模态 AI | WAITING_FOR_MODALITY_OUTPUTS | 保持 folds/cohort 规则 | Behavior-only → +NIR → +RGB → +mmWave → multimodal | 同 folds OOF 证明是否存在稳定增量价值 |
| F. 信度/效度 | ACTIVE DESIGN | 证据框架已确定 | 汇总重复被试、阶段稳定性、probe、行为、问卷、增量效度 | 至少一类可靠性证据 + 两类方向一致效度证据支撑核心产品输出 |
| G. 产品评分 | NOT_YET_NAMED | 暂不提前命名 | 等信效度结果后定义核心分数与探索性分数 | 每个核心分数可解释、可追溯、有质量提示 |
| H. 展示/答辩 | PENDING | 暂不提前包装结论 | 结果稳定后做案例曲线、系统架构和答辩叙事 | 清楚回答“测什么、AI带来什么、为什么可信、如何形成产品” |

## 当前主路径

```text
NIR/RGB可用产物 ───────┐
Behavior + probe ──────┼──> 多模态 AI ──> 增量效度 ──> 产品评分
mmWave可信变量 ────────┤
事后问卷 ──────────────┘                └──> 外部效标/收敛效度

重复被试、participant-disjoint folds、数据质量贯穿全部分析。
```

## 当前最近三个关键节点

### 节点 1 — mmWave 50 s 外部方法续跑

Task 2 的 `BLOCKED` 只发生在 **30 s 输入条件**：30 s × 10 Hz 约300点，而已恢复 SSA 参数要求 `L=400`。因此它不能解释为“SSA+VMD 无效”或“毫米波 HR 已经判死”。

现在采用双轨窗口：

- **30 s**：FocusWave 产品/主分析窗口，继续保留，不因外部论文改变；
- **50 s**：AgeBalanced 外部方法原生比较窗口，用于尽量按论文公开参数运行 SSA+VMD。

50 s 比较必须让项目历史方案和 SSA+VMD 都在相同 50 s / 5 s、相同 development 30 人、相同 ECG reference 下运行。不能拿项目30s结果直接和外部50s结果排名。

若 development 50s 显示至少一个可复现方案值得继续，才进入80 held-out，并用已经确定的50s配置一次性外部验证；否则不为形式完整强行跑80。

### 节点 2 — NIR 重跑结束

第一时间不要直接做模型，先得到：

- 被试/session 可用率；
- 帧/窗口质量；
- 正式可用特征；
- 与 probe/行为可对齐的共同 cohort。

### 节点 3 — 建立统一多模态分析表

同一 participant、session、probe/window 下组合：

- labels / probe；
- Behavior；
- NIR；
- RGB；
- mmWave；
- quality / missingness；
- 事后问卷 participant-level criterion。

问卷用于效度和解释，不直接泄漏到 probe 标签预测。

## mmWave 当前证据层级

### AgeBalanced

110 个不同参与者，具有 ECG，可承担 HR 的多被试外部泛化证据。当前 30/80 participant split 保留：30 development，80 held-out。

### 本地 RS6240 + BIOPAC

已核对 `kyandi233-dev/FocusWave@ecg`：

- `11-calibrate-mmwave-ecg.py`：静息5min → 深呼吸2min → 屏息45s → 静息5min；
- `12-test-breath-focus.py`：同一被试机械按键 vs 专注 SART 交替；
- 两者都是专门机制/校准程序，与正式实验不同。

因此本地 BIOPAC 数据定位为**设备/机制/压力测试证据**，可用于理解呼吸谐波、屏息、明显生理变化和动作条件，但不能替代 AgeBalanced 的跨被试外部有效性证据，也不能单独决定产品级 HR/BR 是否成立。

## 比赛级止损规则

- 某模态长期不可用或增量价值不稳定：降级，不阻塞主线；
- 复杂 AI 不稳定优于简单模型：保留简单模型；
- 心理指标信度不足：只称动态状态，不称能力/特质；
- 只有单一证据来源支持的产品分数：标探索性；
- 毫米波总研究/完善预算约10小时；
- 允许50s论文原生外部比较，但不开放无限算法家族搜索；
- 50s外部结果不能冒充30s产品性能；
- HRV 未通过逐搏验证：不输出 HRV。

## 比赛最终最小可交付版本

即使部分模态失败，也必须保证最小产品仍成立：

> **Behavior + probe + 事后问卷 + 至少一个稳定视觉/生理模态 + participant-disjoint AI + 信效度证据 + 可解释报告。**

多模态越多越好不是目标；**证据可靠、AI增量明确、产品解释完整**才是目标。
