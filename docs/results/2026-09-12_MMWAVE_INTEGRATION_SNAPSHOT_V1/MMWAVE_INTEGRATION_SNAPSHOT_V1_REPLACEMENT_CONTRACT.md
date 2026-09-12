# mmWave integration snapshot v1 替代合同

`mmwave_integration_snapshot_v1` 是接口基线，不是生理算法冻结。后续版本只有同时满足全部门槛，才可声明替代；否则只能作为诊断或候选证据并与 v1 并存。

1. 分母与身份：保持正式 116 sessions / 61 participant groups / 2,320 probes，或先取得明确的新 cohort 决策；不得用 raw-folder 数量扩张分母。五字段源键和 Task B 四字段键必须逐行守恒，重复、缺失和多余键均为 0。
2. 时间与窗口：科学对齐必须使用动态链接库（dynamic-link library [DLL]）主机接收/入队时间列（CSV 零基索引 1），窗口必须为右开 `[effective_start, probe_onset)`、名义 30 s 且不得跨 block。Python 处理时间列（零基索引 2）只能用于质量控制。
3. 变量冻结：须预先冻结 producer、target/bin/channel selector、估计器、心率（heart rate [HR]）表示、呼吸率（breathing rate [BR]）表示、质量控制定义和缺失策略。不得根据事后结果从 fused HR 切换到 time/frequency HR。
4. 缺失与错误：来源不存在、不可读、不可估计、质量控制失败和 malformed 必须保留为空并分层登记；禁止补帧、回填、静默删除或把错误行当作结构性缺失。
5. 受控比较：须提供同一冻结键上的 old-vs-new 逐探针输出、变化数量、变化幅度、不变量差异和失败清单。局部样本、更低平均绝对误差或单一代码提交不足以替代。
6. 生理准入：HR/BR 的算法替代须通过独立、预先规定的生理参考准入门。心率变异性（heart rate variability [HRV]）需另立 beat-level admission，不得由当前快照推导。
7. 下游合同：科学模态固定使用 `behavior`、`ocular`、`movement`、`cardiopulmonary`；设备 `rgb`、`nir`、`mmwave` 只进入 `required_devices`。新版本须通过 Task B、materialize、比较计划与报告层的 modality/device 分离测试。
8. 持久证据：须生成新版本号、schema、feature registry、field-role map、manifest、error log、Formal 方法更新、GitHub commit/Issue 回执及云端读回核验。不得覆盖 v1 本地或云端产物。

当前 v1 的 HR/BR 状态为 `PROVISIONAL / PHYSIOLOGY_LIMITED`，HRV 为 `BLOCKED`，`algorithm_frozen=false`。Issue #35 与 #36 保持开放。
