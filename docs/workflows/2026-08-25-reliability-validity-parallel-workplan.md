# 信效度与系统验证并行任务计划

日期：2026-08-25
依据：`docs/research/2026-08-25-reliability-validity-validation-strategy.md`

## 总原则

不把“信效度”扩展成新的庞大支线。所有任务只服务于比赛报告的三条主证据链：

1. 标签/构念有效性；
2. 毫米波测量与算法可靠性/有效性；
3. 最终系统的泛化与增量有效性。

Codex 负责数据审计、脚本、运行、质量控制（quality control [QC]）、可复现产物和 GitHub handoff；GPT 负责研究问题、方法冻结、证据边界、文献依据和最终科学解释。

## 可立即拆开并行的任务

### P0-A：Probe 构念有效性证据包

**Owner：Codex 执行；GPT 裁决。**

目的：证明当前 thought probe 与实验行为/任务进程存在可解释关系，而不是再训练一个复杂分类器。

可立即做，不依赖 NIR、HRV 或外部数据集。

固定任务：

1. 完成历史 session 的程序版本、probe 文案和 response mapping 一致性核验；
2. 建立 participant/session/stage/probe/time-on-task 的标签审计表；
3. 计算 probe 前行为的最小事件相关指标：错误、反应时、反应时变异、必要的遗漏/极端反应；
4. 比较 `label 1` 与 `label 2/3/4` 主终点，同时只做预先定义的描述性四类分布，不根据结果改标签；
5. 建立 time-on-task / block / stage 与 probe 状态的混合效应或等价描述性证据；
6. 输出报告级图表候选，但暂不把探索性关联升级成因果结论。

**禁止：**为了更高显著性/AUC 改窗口、改标签或只选择最强行为指标。

建议 RUN_ID：`PROBE_CONSTRUCT_VALIDITY_V1_20260825`

### P0-B：Common-subset 泛化与增量有效性

**Owner：Codex 执行；GPT 已批准框架。**

目的：直接服务最终系统信效度正文。

沿用已批准的 `COMMON_SUBSET_BASELINE_V1`：

- time/block structural baseline；
- behavior-only；
- radar-only；
- near-infrared（NIR）-only；
- behavior + radar；
- radar + NIR；
- behavior + radar + NIR。

所有模型必须在相同 strict common probe、相同参与者分折上比较。主 NIR 集合采用预先冻结的 `QC >=80%`，敏感性集合采用 `QC >=50%`。

重点输出：

- 受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）；
- balanced accuracy；
- participant bootstrap 95% confidence interval（置信区间 [CI]）；
- 相对 time/block baseline 和 behavior-only 的配对性能差值；
- coverage。

该任务不升级复杂模型；目的是估计“毫米波是否增加已有时间/行为信息之外的价值”。

建议 RUN_ID：沿用已规划的 `COMMON_SUBSET_BASELINE_V1`。

### P0-C：RS6240 现有技术可靠性/QC 汇总

**Owner：Codex。**

目的：不重新调算法，只把已经存在的证据整理成一张报告可用表。

从既有产物汇总：

- 数据/时间覆盖；
- target-lock candidate / 距离稳定性；
- 8 通道空间一致性；
- RGB motion gate / 运动伪影状态；
- extraction success / failure reason；
- 当前不能声称的内容。

只做已有结果的 provenance-aware summary，不新增阈值，不重新扫描全量原始数据，除非现有产物无法回答某字段并先向 GPT/用户说明。

建议 RUN_ID：`RS6240_REPORT_QC_SUMMARY_V1_20260825`

## 可以先审计、但不急于正式建模的任务

### P1-D：问卷可用性与计分审计

**Owner：Codex。**

先只建立问卷 inventory：

- 哪些是正式多题量表；
- 哪些是单题自评；
- 是否有反向计分；
- 缺失率；
- 哪些变量与“持续注意/任务聚焦”构念直接相关。

只有多题且理论上属于同一量表的项目，才准备内部一致性分析；单题不计算 Cronbach’s α。

此任务先交 `questionnaire_measurement_manifest`，不急于一次性把所有问卷和所有 probe 做相关。

建议 RUN_ID：`QUESTIONNAIRE_MEASUREMENT_AUDIT_V1_20260825`

### P1-E：静息/休息段可用性清单

**Owner：Codex。**

目的不是立刻做大量 physiology，而是确定后续“个人 baseline / recovery”分析是否有足够且时间语义一致的数据。

只需先列：

- 每个 participant/session 是否有静息段；
- 休息段起止时间；
- radar/NIR/RGB 在这些段的覆盖；
- 是否允许闭眼/是否禁止移动的实验规则是否对所有 session 一致；
- 哪些段满足后续 within-person baseline 分析的基本条件。

先做 manifest，不直接定义新的 HRV 或 attention 指标。

建议 RUN_ID：`REST_BREAK_COVERAGE_MANIFEST_V1_20260825`

## 当前阻塞、不能假装完成的任务

### BLOCKED-F：独立 Radar–ECG 外部 benchmark

**Owner：Codex 执行；GPT 负责协议和解释。**

C1b 继续保持 `protocol-ready / data-access blocked`。

正式 VS_DATASET healthy cohort 与同步心电图（electrocardiography [ECG]）参考数据到位后再运行：

1. 本项目逐搏算法；
2. VitalSense matched-filter baseline；
3. 同一 ECG R-peak、同一 session/device alignment、同一 electromechanical-delay policy、同一 beat matching 和 subject-disjoint 规则。

外部数据集结果在报告中只能称为“独立公开 Radar–ECG 数据集算法外部基准验证”。不得升级为“RS6240 HRV 已被 ECG 验证”。

当前不再调 VitalSense 12 个示例。

## 暂缓任务

以下任务当前不投入主资源：

- teacher–student；
- Transformer/Mamba 等复杂时序模型；
- 每个雷达特征逐一做生理解释；
- 完整可用性验证；
- 全套组内相关系数/重测信度；
- 大规模亚组公平性；
- 医疗/临床效度。

只有在 P0/P1 证据显示明确需要时再升级。

## 推荐并行顺序

可同时启动三条互不冲突的工程线：

**线 1：P0-A Probe 构念有效性**

**线 2：P0-B common-subset 泛化/增量有效性**

**线 3：P0-C RS6240 现有 QC 汇总**

若资源允许，再启动 P1-D 问卷审计和 P1-E 静息/休息 coverage manifest。BLOCKED-F 保持等待正式外部数据。

## 下一次 handoff 格式

每条线完成后分别提交：

- RUN_ID；
- branch / commit；
- objective；
- input data；
- entrypoint；
- frozen parameters/windows；
- participant/session grouping；
- outputs；
- key results；
- QC/coverage；
- exclusions/failures；
- deviations；
- open question for GPT/user。

不要把多条线混成一个“已完成信效度”的总判断。最终证据整合由 GPT/用户裁决。
