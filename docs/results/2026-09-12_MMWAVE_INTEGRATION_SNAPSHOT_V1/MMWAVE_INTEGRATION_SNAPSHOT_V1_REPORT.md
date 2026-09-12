# mmWave integration snapshot v1 正式报告

状态：`PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED`

## 1. 范围与结论

本轮只完成毫米波（millimeter wave [mmWave]）正式回放结果的接口收口，不重跑或调整算法。快照复用 producer commit `16729b2ef245f9304dae8674f3bac433bc02e98c` 已生成的 J72 + E44 冻结回放，保持 116 场、61 个参与者组和 2,320 个探针；109 场、2,180 个探针具有可估计心率与呼吸率，7 场、140 个探针按真实来源状态保留为空。五字段源键与 Task B 四字段键均为 2,320/2,320，重复、缺失和多余键均为 0。

本轮不冻结毫米波生理算法。心率（heart rate [HR]）与呼吸率（breathing rate [BR]）仅达到临时可集成、且生理效度受限；心率变异性（heart rate variability [HRV]）继续阻塞。Issue #35 与 #36 保持开放。

## 2. 时间与窗口合同

科学对齐使用 CSV 零基索引第 1 列，即动态链接库（dynamic-link library [DLL]）主机接收/入队时间。零基索引第 2 列为 Python 工作线程处理时间，只能用于质量控制，不能作为科学对齐时钟。窗口为右开区间 `[window_effective_start_unix_ms, probe_onset_unix_ms)`，名义长度 30 s；窗口不得跨正式 block，靠近 block 起点时以 `window_effective_start_unix_ms` 截断。该明确索引合同取代历史文档中含糊的“第二列”自然语言表述。

## 3. 字段角色

科学预测变量仅包括心肺模态的 `mmwave_hr_fused_bpm_median` 与 `mmwave_breath_rate_breaths_per_min_median`。HR 表示保持现行 fused 字段，未因 P2 诊断中 time-path 指标较好而事后切换。质量控制字段包括时间戳覆盖率、HR 平均置信度、producer 可用窗口比例与相位稳定性。频域/时域 HR、bin、channel、距离代理、target switch、motion proxy 均为诊断字段，不得进入正式科学模型。

当前没有合格的毫米波运动模态科学特征：`mmwave_motion_proxy_median` 仍为 `DIAGNOSTIC_ONLY_NOT_MOVEMENT_QUALIFIED`。IBI、RMSSD、SDNN、低频/高频功率及其比值均未进入快照，禁止由本快照派生或填补。

## 4. 可用性与错误状态

| 状态 | 探针 | 场次 | HR 有限值 | BR 有限值 |
|---|---:|---:|---:|---:|
| `AVAILABLE` | 2,180 | 109 | 2,180 | 2,180 |
| `SOURCE_MALFORMED` | 100 | 5 | 0 | 0 |
| `SOURCE_UNAVAILABLE` | 40 | 2 | 0 | 0 |
| 总计 | 2,320 | 116 | 2,180 | 2,180 |

来源不存在、不可读、不可估计、测量质量控制失败和文件格式错误均保留为显式状态；无填补、补帧、回填或删除。逐探针表含参与者关联信息，只保存在本地并以 SHA-256 登记。

## 5. Task B 与 materialize schema smoke

在 Attention-Analysis commit `5c7c82c53fd06477b8eef3b3ffedb7c630ead1a5` 上，以 `sub-031`（可用）、`sub-047`（来源不可用）和 `sub-099`（NPZ/时间戳数量不匹配）共 60 个真实探针执行接口烟雾测试。Task B 质量审计、分析集和 materialize 均通过；完整案例正确保留 `sub-031` 的 20 个探针，重复键为 0，`models_trained=false`。

映射严格使用科学模态 `behavior` 与 `cardiopulmonary`，设备约束另记为 `required_devices=["mmwave"]`，未把 `mmwave`、`nir` 或 `rgb` 当作科学模态。当前下游 1.16.10 迁移仍待完成：`RegisteredFeature.modality`、`PlannedModel.modalities`、`FeatureScheme` 的 modality/device 分离，以及 comparison plan 与 reporting 均未在所检查 commit 实现。因此结论为 `PASS_INTERFACE_WITH_DOWNSTREAM_1_16_10_MIGRATION_PENDING`，不是下游正式模型就绪。

## 6. 替代与复用合同

以后任何毫米波重跑只有同时满足以下条件才可替代本快照：冻结同一正式分母与键；明确 DLL 第 1 列时间及右开、block 截断 30 s 窗口；保留缺失/错误行；提供旧新逐探针配对差异和不变量门；冻结 producer、selector、estimator、HR 表示及质量控制定义；独立通过生理准入门；更新版本化 schema、manifest、错误日志、Formal 方法文档和 GitHub durable record。单独的算法诊断、更低平均绝对误差、局部 subset 或代码存在均不能替代本快照。

## 7. 产物与边界

Git 跟踪包包含 schema、科学特征注册映射、字段角色、可用性汇总、真实数据 schema smoke、错误日志、manifest、替代合同、handoff 与云端核验回执。逐探针快照及烟雾测试明细为 local-only。Google Drive 的最终对象清单和读回结果见 `MMWAVE_INTEGRATION_SNAPSHOT_V1_CLOUD_VERIFICATION.json`。

`models_trained=false`；`algorithm_frozen=false`；未运行 HRV、注意状态监督学习、NIR/RGB 重跑或任何 estimator 调参。
