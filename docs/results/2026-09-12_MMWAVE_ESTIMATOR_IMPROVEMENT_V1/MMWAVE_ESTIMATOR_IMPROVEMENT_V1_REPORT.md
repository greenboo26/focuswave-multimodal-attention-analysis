# 毫米波心率估计器改进 v1 报告

## 当前结果

- Phase A：`PASS / REFERENCE_QC_LINEAGE_RECONCILED`。
- Phase B：`NO_STABLE_IMPROVEMENT`。
- 独立验证：不可用；5 个校准场次均已被反复查看，本结果不能升级为正式放行。
- P2 结论变化：无。严格参考重归因后，错误仍主要位于选中目标内的估计器/峰值/谐波/融合路径；目标漏选既不是唯一类别，也不是最大类别。
- 最佳候选：`NONE`。
- v2 状态：`NOT_FORMED`；这不是已经发布的 snapshot v2。
- 正式 producer 修改：false。integration snapshot v1 修改：false。训练模型：false。心率变异性（heart rate variability [HRV]）：blocked。

## 冻结比较

全部估计器使用同一组 100 个严格 ECG 有效探针窗口。候选评价前已冻结当前融合心率、时域心率和频域心率三个对照。候选规则只读取毫米波派生的时域心率、频域心率、融合心率、置信度与毫米波呼吸率；ECG/RSP 仅在候选生成后用于开发期评价。

当前融合心率平均绝对误差（mean absolute error [MAE]）：10.457079 bpm；当前时域心率 MAE：8.996966 bpm；当前频域心率 MAE：15.123834 bpm。

没有候选通过预先声明的总体、尾部、场次稳定性与灾难性失败检查。观察上最优的 H1_WARNING_TIME_GATE 虽将 MAE 降至 9.618844 bpm，但造成一个 control-correct 窗口进入 >10 bpm 错误，故拒绝。

系统性偏差仍为低估。分场次、ECG 心率带和选中距离代理的聚合见 `SYSTEMATIC_BIAS_AUDIT.csv`；最大误差探针保留在 local-only 表中。

## 云盘交接

云端交接已完成：`CLOUD_UPLOAD=UPLOADED_AND_VERIFIED`。经用户授权后使用 rclone 1.75.1（便携版，`D:\Project\.tools\rclone.exe`）的 Google Drive remote，将 12 个文件上传到既有目录 `2026-09-12_mmwave_estimator_improvement_v1`（folder id `1gZC80XNklehALcuJ6U8NJe_aKy5iwzPd`，未新建目录），随后逐文件回读并重算 SHA-256：11/11 tracked 文件与 manifest 一致，未混入任何 `mmwave_integration_snapshot_v1` 文件。OAuth token 只保存在本机 rclone 配置中，未进入 Git、未进入任何报告。清单与哈希见 `MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json` 的 `cloud_handoff` 段。

## 证据边界

这是在已经查看过 ECG oracle 的校准集上进行的估计器开发。任何通过开发门的规则都必须经过参与者/场次不重叠、未触碰 ECG 验证后，才能进入 replacement review。不得覆盖 `mmwave_integration_snapshot_v1`，也不得改变 Task B/materialize 输入。
