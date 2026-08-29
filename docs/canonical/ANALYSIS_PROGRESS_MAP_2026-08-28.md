# FocusWave 当前分析进度与关系图

日期：2026-08-28（Asia/Shanghai）  
状态：`CURRENT_ANALYSIS_MAP`

> 这份文件回答三个问题：**现在分析做到哪一步、哪些已经做完、各分析之间是什么关系。**
> 新智能体在继续任何统计/算法任务前，应先读根目录 `ANALYSIS_HISTORY_LEDGER.md`，再读本文件。

## 1. 证据来源

本图不是从聊天记忆生成，当前主要依据：

1. `ANALYSIS_HISTORY_LEDGER.md`：跨仓库历史演变、采用/回退/替代记录；
2. `docs/canonical/SCIENTIFIC_METHOD_REVIEW_V1.md`：当前科学角色边界；
3. Issues #12/#13/#14/#15/#16/#17/#18 的当前执行状态；
4. `codex/mmwave-formal-reanalysis-v2/docs/results/RESULTS_DIRECTORY_HANDOFF_2026-08-28.md`：另一个 Codex 对本地 `D:\Project\厚粲杯` 真实结果目录的逐文件审查交接；该文档是“本地已经实际生成了哪些结果”的重要证据层，但不能自行覆盖中央 canonical 解释；
5. `kyandi233-dev/Attention-Analysis@nvidia-cuda` 的 NIR/RGB producer 当前 README/result；
6. `kyandi233-dev/FocusWave@stable-msmf` / `@ecg` 的采集、时间戳、marker、ECG/RSP 工程事实。

## 2. 总体关系：从实验数据到最终产品结论

```text
实验程序 / 采集
    │
    ├── Behavior + Probe ───────────────┐
    │                                   │
    ├── mmWave raw ──> HR / BR / HRV ──┼──> 状态效度 / 生理解释
    │             └─> signal/features ──┼──> AI 增量检验
    │                                   │
    ├── NIR video ──> pupil / eyelid ───┤
    │                                   │
    ├── RGB video ──> Face/Pose/Motion ─┤
    │                                   │
    └── Questionnaire ──────────────────┘
                                        │
                              participant-disjoint AI
                                        │
                              个体级/状态级测评解释
                                        │
                                  最终产品报告
```

这里有两条必须分开的证据链：

- **预测链**：某模态加入 Behavior 后，能不能提高 probe-level 注意状态预测？
- **测量解释链**：某个 HR/BR/NIR/RGB 指标到底能不能被可靠地解释成真实生理/行为测量？

例如 `Behavior+mmWave` 已经做过，并不等于 mmWave HR/BR/HRV 的生理资格已经完成。

## 3. 当前总进度

| 分析模块 | 当前状态 | 已经完成 | 当前还差什么 | 与其他分析关系 |
|---|---|---|---|---|
| Behavior / Probe 主分析 | `PASS / CORE READY` | 北京 70 sessions / 1,400 probes 主队列；probe 四类语义；30 s C+B 锚点；participant-disjoint CV | 主要是最终报告整合，不是重新跑主分析 | 所有传感器增量的基线；也是状态效度主骨架 |
| Behavior + mmWave AI 增量 C2B/C2C | `PASS AS ABLATION` | C2B-v2、C2C 已完成；没有稳定超越 C+B | 不重跑 | 回答“mmWave 是否增加 probe prediction”，不回答 HR 是否准确 |
| mmWave 外部 HR benchmark | `PASS DEVELOPMENT-ONLY` | AgeBalanced 官方 ECG reference 已纠正；30 s project pooled MAE 10.361 BPM；旧 27–38 BPM 已标 superseded | held-out 80 未开；不继续算法海选 | 只用于算法/reference 边界，不直接替代 J_Data 正式生理分析 |
| mmWave HR/BR/HRV 正式资格 #15 | `CLOSED_WITH_EXPLICIT_BOUNDARIES` | HR=`PASS_QUALITY_GATED`、BR=`PASS_SUPPORTING`、HRV=`BLOCKED`；corrected QC=33/37/2；067/099 状态明确 | 不再扩大算法或重算；#16 仅按 closure contract 做一次预定义 quality sensitivity | closure report 与 #16 input contract |
| mmWave task dynamics / alertness #16 | `PARTIAL` | 主 LMM/GEE 已存在；70-session 主分母固定；fixed-bin sensitivity 已有 | 接 #15 quality strata + 统一 matrix 后补分层 sensitivity；统一 questionnaire 68/67 分母 | 是 mmWave 生理变量与任务过程/警觉事件的正式统计解释 |
| mmWave report-ready matrix #17 | `PARTIAL / NEAR READY` | 唯一 72-row session matrix；067 无 raw；099 supplemental | 099 timeline/meta/provenance；68/67 questionnaire denominator mapping | 给 #15/#16 提供统一样本口径，防止各模型自己换分母 |
| Psychometric / validity #13 | `PARTIAL` | probe 状态效度、行为 criterion 路线可用；问卷可作外部效标 | 重复被试跨-session 稳定性、person-level reliability、与长期自评专注/持续时长关系需要正式闭合 | 把“瞬时状态预测”升级为“个体测评”的关键层 |
| NIR producer | `PAUSED FOR RECOMPUTE` | timestamp mapping 修复；71/72；1,420 probes；旧 PIR/QC/result 都有历史记录 | 按正式重算方案重新生产/验证后再做最终科学 inference | 旧正/负 incremental 都是历史/pre-recompute，不能进入最终结论 |
| RGB producer | `PAUSED / ENGINEERING NOT COMPLETE` | Face+Pose+Motion 科学路线和 schema 已定义；部分工程实现已存在 | CPU↔CUDA parity、gap stress、primary-face/blink/PERCLOS、正式 full-video runner、probe-level QC | 未完成前不能粗暴拿几个动作特征做 multimodal ladder |
| 最终 multimodal ladder | `WAITING ON VALID PRODUCERS` | Behavior 基线、mmWave ablation 已有 | 等 NIR 重算、RGB formal producer；再做 matched participant-disjoint incremental | 最终回答“多模态 AI 到底增加了什么” |
| 产品级报告 | `PARTIAL` | 动态状态、行为、部分 mmWave、问卷结构已有 | 等 #15/#16/#17、psychometric person-level、NIR/RGB 最终角色 | 最终形成状态层 + 个体层 + 置信度/质量说明 |

## 4. 当前真正的依赖关系

```text
                    ┌──────────────┐
                    │ Behavior/Probe│  已完成主骨架
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   Psychometric #13   mmWave AI C2B/C2C   Sensor producers
     PARTIAL             DONE             NIR / RGB
          │                │                │
          │                │                ├─ NIR：重算后再进最终模型
          │                │                └─ RGB：正式 producer 完成后再进
          │                │
          │        ┌───────┴────────┐
          │        │ mmWave physiology│
          │        │      #15         │
          │        └───────┬────────┘
          │                │ quality strata
          │                ▼
          │        ┌─────────────────┐
          │        │ task/alertness #16│
          │        └────────┬────────┘
          │                 │
          │        ┌────────┴────────┐
          │        │ unified matrix #17│
          │        └────────┬────────┘
          │                 │
          └──────────┬──────┘
                     ▼
            Final interpretation layer
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   动态注意状态报告          个体级稳定性/能力指标
                                   │
                          依赖 repeat-session + questionnaire
```

## 5. 现在最接近“收口”的部分

### A. mmWave 主线

当前不是再做算法开发，而是：

`#15 确定 HR/BR 质量资格 → #16 只补一次 quality-stratified sensitivity → #17 统一最终分母/099 provenance → 写正式结果`

HRV 如果 beat/IBI + ECG evidence 仍不足，直接保持 `exploratory-blocked`，不再扩大研发。

### B. 个体级心理测量

当前不能简单写成“稳定特质没有证据”。现有数据已经提供两条可以正式验证的路线：

1. 重复被试的跨-session 稳定性 / ICC / ranking stability；
2. 客观 person-level 指标与问卷中的自评专注水平、平时可持续专注时长的外部效标关系。

这条线决定产品是否只能报告“你刚才什么时候走神”，还是可以进一步报告“你的持续专注表现是否稳定、与你自己的长期感受是否一致”。

### C. NIR / RGB

两者现在都不应该阻塞 mmWave 收口：

- NIR：已有大量历史结果，但已决定重算，所以当前旧 AUC 只作历史证据；
- RGB：科学设计不等于 producer 已完成，正式 probe-level QC 之前不进入最终 ladder。

## 6. 已明确禁止重复的分析

- C2B/C2C Behavior+mmWave 不重跑；
- 旧 7 类 mmWave A/B（SPC/Hampel/phase diff/CFAR/SSA/envelope/CEEMDAN）不无理由重跑；
- generic multi-bin / AoA / beamforming / VMD grid 不重新包装成“新想法”；
- NIR 旧 68/69-session ladder 不作为最终结果重复解释；
- RGB pilot / proxy 不得冒充正式 RGB multimodal analysis。

详细历史和日期见 `ANALYSIS_HISTORY_LEDGER.md`。

## 7. 当前执行优先级

```text
第一优先：#15 → #16 → #17（mmWave 收口）
并行：#13 重复被试 + 问卷个体效标闭合
暂停等待：NIR 正式重算
暂停等待：RGB 正式 producer/QC
最后：完整 multimodal ladder + 产品报告
```

## 8. 维护规则

任何一个模块从 `PARTIAL` 变为 `PASS/BLOCKED`，或者主样本数、正式结果、科学角色发生改变时，都要同步更新本文件。

任何新的计算提案都要先检查：

`ANALYSIS_HISTORY_LEDGER.md` → `ANALYSIS_PROGRESS_MAP_2026-08-28.md` → 当前 issue/analysis card → 对应 producer/result。
