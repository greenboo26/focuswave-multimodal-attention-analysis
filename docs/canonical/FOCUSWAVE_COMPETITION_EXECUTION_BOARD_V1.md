# FocusWave 厚粲杯执行看板 V1

Status: `ACTIVE_EXECUTION_BOARD`

本看板只回答三个问题：**现在在哪、下一步是什么、什么条件下算完成。**

| 轨道 | 当前状态 | 当前工作 | 下一步 | 完成条件 |
|---|---|---|---|---|
| A. NIR producer | RUNNING / REPAIRING | 修复后批量重跑 | 汇总 coverage / failure / quality | 有稳定派生特征 + 质量字段 + 可用率报告 |
| B. Behavior / probe | ACTIVE | 保持 canonical 主分析 | 整合 time-on-task、vigilance、RT/RTV、错误 | 形成不依赖生理模态也成立的测验骨架 |
| C. 事后问卷 | ACTIVE / NEEDS_INTEGRATION | 整理效标与条目语义 | 对接整体专注、疲劳、走神、持续时间等产品指标 | 形成外部效标/收敛效度表，不夸大为标准化量表 |
| D. mmWave | TASK2 COMPLETE / BLOCKED | SSA+VMD 因论文参数与 30s/10Hz 输入不兼容而停止；HR 当前不得作为已验证产品输出 | 跳过外部算法继续搜索与 80 人算法考试，进入一次 RS6240 + BIOPAC 设备匹配校准 | 在约10小时上限内确定 HR、BR 各自是 physiology 输出还是 supporting signal；HRV 非必需 |
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

### 节点 1 — mmWave 设备匹配校准

Task 2 已结束：外部 SSA+VMD 路线是 `BLOCKED`，原因是可恢复论文参数要求 SSA `L=400`，而当前 30 s / 10 Hz 输入只有约 300 点；在没有作者代码或参数依据的情况下，不为完成任务擅自改 `L`、补零或改变重构规则。

这不是“SSA+VMD 很差”，也不是“毫米波绝对测不了 HR”。比赛路线因此改为：

- 停止继续搜索新的外部算法家族；
- 暂不进行 80 held-out 算法考试，因为当前没有值得晋级的外部候选；
- 直接用本项目自己的 RS6240 与同步 BIOPAC ECG/RSP 做一次设备匹配校准；
- HR 与 BR 分开决定：谁通过可信度验证就保留谁，谁不过就降级；
- 若设备匹配校准仍不能支持可靠生理量，则正式停止 physiology 研发，把 mmWave 保留为 motion / phase / quality 等 supporting signal。

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

## mmWave 当前决定

Task 2 的 `DOWNGRADE_PHYSIOLOGY` 解释为**当前产品声明降级**，而不是永久科学结论：

- 当前不得宣称 mmWave HR 已验证；
- 当前不得将 HR/HRV 作为核心心理测量变量；
- 允许一次设备匹配的 ECG/RSP 校准作为最后高收益检查；
- 若仅 BR 通过，则产品只保留 BR 生理解释；若仅 HR 通过，则只保留 HR；
- 若二者都不过，则 mmWave 只进入信号级 supporting features；
- HRV 只有逐搏验证自然通过时才考虑，否则不输出。

## 比赛级止损规则

- 某模态长期不可用或增量价值不稳定：降级，不阻塞主线；
- 复杂 AI 不稳定优于简单模型：保留简单模型；
- 心理指标信度不足：只称动态状态，不称能力/特质；
- 只有单一证据来源支持的产品分数：标探索性；
- 毫米波超出约10小时完善预算：停止新增算法家族；
- Task 2 后不再为外部方法改 benchmark 规则或开放式搜索参数；
- HRV 未通过逐搏验证：不输出 HRV。

## 比赛最终最小可交付版本

即使部分模态失败，也必须保证最小产品仍成立：

> **Behavior + probe + 事后问卷 + 至少一个稳定视觉/生理模态 + participant-disjoint AI + 信效度证据 + 可解释报告。**

多模态越多越好不是目标；**证据可靠、AI增量明确、产品解释完整**才是目标。
