# C2a 心理状态标签与样本单元审计

审计日期：2026-08-26  
状态：`C2A_DATASET_AUDIT_COMPLETE`

本阶段只读取 J 盘正式实验相关行为/时间对齐产物和已有字段盘点，不训练模型、不提取大规模 RGB/NIR 特征、不重新计算 HRV，也未修改正式原始数据。行级 manifest 和被试映射仅保存在本地 derived 目录。

## 1. 正式数据中的心理状态标签

主状态字段是 `probe_response`，原始取值为 1–4；本轮没有提前二值化。依据已有一次性 BB probe mapping 记录，四个代码对应：

| 原始代码 | 实际文案 | 构念定位 |
|---:|---|---|
| 1 | 完全专注于分拣任务 | 完全任务聚焦 |
| 2 | 关注实验本身，但没有聚焦于分拣任务 | 实验相关但未聚焦任务 |
| 3 | 在想与实验无关的事情 | 任务无关思维 |
| 4 | 大脑空白，没有明确想法 | 思维空白 |

当前审计队列共 1,440 个 probe：1 = 1,064（73.89%），2 = 240（16.67%），3 = 51（3.54%），4 = 85（5.90%），缺失 0。每个被试 20 个 probe。

另有 `probe_vigilance` 字段，但它是并行自报字段，不能在未核定其量表方向和构念前替代 `probe_response`。事后问卷中的“平时专注能力”等属于个体层 trait/外部效度变量，不应混入 probe 状态标签。

## 2. 建议的比赛主预测目标

当前最适合作为主目标的是保留原始四分类作为标签层，并将“1 vs 2/3/4”作为预先声明的二元主分析终点：

> 完全任务聚焦 vs 其他非完全任务聚焦状态。

理由是代码 1 代表最明确、最贴近任务操作的状态，且二元终点类别数量较稳定；但 2、3、4 构念并不等价，正文不能把它们统称为“走神”。

因此 C2b 建议先做：

1. 主分析：四分类标签保留，二元终点为 1 vs 2/3/4；
2. 次级分析：1 vs 3（任务无关思维）、1 vs 4（思维空白）；
3. 四分类/序数模型只有在 C2b 先确认样本量、每组分布和模型假设后再冻结。

本报告不自动冻结 C2b 的窗口长度、模型或评价指标。

## 3. 样本量与重复被试

- 被试 session 记录：72；
- 确定性映射的重复被试 group：46 个；
- 当前审计的 session 数：72；
- 有效 probe：1,440 个；
- 行级候选窗口 manifest：4,320 行，即每个 probe 分别记录 10 s、30 s、60 s 三种候选窗口；
- 每个被试 probe 数：20 个。

同一重复被试的所有 session 必须共享同一个 `group_subject_id`，后续 LOSO/GroupKFold 必须以该字段分组，禁止按窗口随机拆分。

## 4. Probe 前窗口覆盖

窗口统一定义为 `[probe_onset - duration, probe_onset)`，不使用 probe 之后的数据预测当前 probe：

| 候选窗口 | Probe 总数 | 时间戳完整覆盖 | 覆盖比例 |
|---:|---:|---:|---:|
| 10 s | 1,440 | 1,420 | 98.61% |
| 30 s | 1,440 | 1,420 | 98.61% |
| 60 s | 1,440 | 1,420 | 98.61% |

这只是时间范围覆盖，不等于传感器信号质量合格，也不等于 HR/BR 可用。窗口长度留待 C2b 依据行为前置效应、模态覆盖和验证结果冻结。

## 5. 模态覆盖

| 模态 | 当前审计证据 | 数量 | 限制 |
|---|---|---:|---|
| 行为 | probe-centered behavior manifest | 1,440 probes / 72 subjects | 字段覆盖不等于预测质量 |
| 毫米波 raw/timestamp | C2a manifest | 1,278 probes / 71 subjects | raw/timestamp presence，不是生理质量 |
| 毫米波 HR/BR | 既有正式窗口 JSON 字段盘点 | 71/72 subjects 有字段证据 | 本轮未重新计算 |
| RGB | subject master 的原始视频存在标记 | 72/72 sessions | 尚未做 probe-level 帧覆盖和运动质量 |
| NIR | 既有 C3 北京 aligned 产物 | 320 probes / 16 subjects / 16 sessions | 不属于本轮新计算，需按共同 probe 再 join |
| IBI/RMSSD/SDNN | C1d 已停止当前周期投入 | 不进入 C2 核心 | 只能标记 exploratory/unsupported |

毫米波显式 per-window phase 和 raw 字段本轮没有在既有窗口表中出现；J 盘仍有 raw cube 和时间戳，但这不等于已经生成可直接进入 C2 的 phase 特征。

## 6. 休息阶段

baseline 和 inter-block rest 的时间边界证据为 71/72。休息阶段目前没有独立的 probe 心理标签，主要是传感器/时间段信息，不能当作任务状态样本直接加入分类模型。

当前可保留为“静息生理基线/任务间恢复候选”，但是否进入最终模型、使用哪些模态以及如何定义质量门控，留到 C2b 决策。当前不能称为已经完成的静息信号质量验证。

## 7. 后续建模与防泄漏规则

- 样本单位优先使用 probe-centered window；窗口终点为 probe onset，禁止使用未来数据；
- 同一 `group_subject_id` 的所有 session 必须同时进入训练集或测试集；
- 采用 subject-grouped LOSO 或 GroupKFold，不得按窗口随机切分；
- 主终点先保留 1 vs 2/3/4，四分类和 1 vs 3、1 vs 4 作为次级候选；
- 不能仅凭类别顺序把四分类自动当作序数变量，需先确认 2、3、4 的心理距离和模型假设；
- 回归不适合直接预测 `probe_response` 四代码；只有在使用连续量表/比例型事后问卷作为另一个明确终点时才考虑回归；
- C2b 再冻结窗口长度、模型复杂度、评价指标和缺失规则。

## 本地产物

- `c2a_sample_manifest.csv`：行级 probe × window manifest，仅本地；
- `c2a_subject_group_map.csv`：匿名 session 到重复被试 group 映射，仅本地；
- `c2a_label_summary.csv`：脱敏标签汇总；
- `c2a_modality_coverage.csv`：模态覆盖汇总；
- `c2a_manifest.json`：审计元数据和 blocker；
- `scripts/audit_c2a_dataset.py`：生成紧凑汇总的审计脚本。

本地目录：

`D:\Project\厚粲杯\08_算法\output\40_正式实验\04_C2a_标签与样本单元审计\derived_20260826\`

本阶段完成审计，不自动进入 C2b 训练。下一步应把本报告和脱敏汇总交给 GPT，冻结 C2b 的预测任务、窗口长度和评价指标。
