# GPT 981d5c6 裁决执行结果交接

**日期：** 2026-08-25
**执行依据：** GPT 裁决 `981d5c6`，现已在同一远程分支中核验可读
**执行状态：** 三条主线已完成；北京和珠海仍阻塞，RS6240 通过有限技术门控但未解除正式生理分析条件。

## 总结

| 主线 | 状态 | 关键结果 |
|---|---|---|
| 北京语义门控与事件分析 | `BLOCKED` | 72 个候选中完整 gate 通过 0 个，未运行事件模型 |
| 珠海 session 链接与 NIR 事件准备 | `BLOCKED_ACTUAL_SESSION_LINKAGE` | 30/30 登记 session 均无法确定性连接实际采集 session |
| RS6240 数据链技术门控 | `PASS_WITH_LIMITS` + 多项 `BLOCKED` | range-bin 镜像关系得到小样本支持，但固件、Tx 和正式 memory mapping 仍未闭合 |

## 1. 北京：BEIJING_SEMANTIC_SESSION_GATE_AND_EVENT_V1

产物目录：

`D:\Project\厚粲杯\11_数据\derived\beijing_semantic_session_gate_event_v1\`

- 候选 session：72。
- 完整语义 gate：0/72 通过。
- 71 个 session 的 B1/休息/B2 结构、432×2 trials、10×2 probes、trial/probe 时间字段和值域检查通过。
- `sub-099_` 缺少 `master_timeline.csv`，无法无猜测恢复阶段边界，因此排除并记录。
- `sub-064_`、`sub-084_` 含 `experiment_abort`，未静默视为正常完成。
- 所有 session 的 participant identity 与 canonical session 仍未确定。
- session 级原始 probe 文案、素材和 response mapping 未直接核验；历史 FocusWave 代码只能支持结构相容，不能直接证明 1/2/3/4 的具体语义。
- 行为事件模型未运行。

**解阻最小证据：** participant identity→canonical session 一对一映射；session 级 probe 素材/发布包或等价语义证据；对两个 `experiment_abort` session 的完成状态判定。

## 2. 珠海：ZHUHAI_SESSION_LINKAGE_AND_NIR_EVENT_READINESS_V1

产物目录：

`D:\Project\厚粲杯\11_数据\derived\zhuhai_session_linkage_nir_event_readiness_v1\`

- 登记 session：30。
- 登记层真人 participant 证据：30/30。
- 确定性实际 session 链接：0/30。
- 已连接行为 CSV、`master_timeline`、NIR、毫米波或 RGB：均为 0/30。
- 可确认三阶段边界、`probe_id`、绝对 probe 时间、response/vigilance mapping：均为 0/30。
- NIR event readiness：30/30 被 identity/time/event gate 阻断。
- 未用特征猜 participant，未把北京 BB 语义填入珠海，未根据总时长推断阶段。

**解阻最小证据：** 登记记录到实际采集目录/session manifest 的映射；珠海行为 CSV 与 `master_timeline.csv`；BBB 三阶段边界和绝对时间；程序发布包/运行 commit/探针素材；各模态 session 文件清单与时间戳；必要时提供非特征式匿名 crosswalk。

## 3. RS6240：RS6240_DATA_CHAIN_TECHNICAL_GATE_V1

产物目录：

`D:\Project\厚粲杯\11_数据\derived\rs6240_data_chain_technical_gate_v1\`

本轮只审计和复核 18 个小规模 NPZ 分片，未调心脏算法、未跑大批处理、未修改正式算法主链。

### 已获得的有限证据

- `range-bin 244–248` 与 profile 主峰 `8–13` 在 256 点 FFT 下符合 `mirror_bin = 256 - profile_bin`。
- 18/18 分片满足镜像范围支持，16/18 局部最大值索引精确镜像匹配。
- 该项状态为 `PASS_WITH_LIMITS`，只能说明当前小样本的索引关系得到支持，不能直接推出全量生理分析有效。
- 正式连续时间轴应优先采用 `device_ms`；已有 3 场、每场前 6000 帧的帧间隔中位数约 10 ms、最大约 14 ms，未发现超过 15 ms 的缺口。
- `host_ms` 不应作为主时间轴；已有 3 场出现大量大间隔和非正增量，严格切段后没有可用 cardiac-band 连续行。

### 仍然阻塞的证据

- firmware 精确版本及每场镜像哈希绑定：`BLOCKED`。
- calibration：`PARTIAL`；`sub-97793_` 缺少对应 `cal/events.csv`，无法逐场绑定校准状态、系数和输出。
- Tx timing：`BLOCKED`；目前只有代码级 2TX×4RX 和约 10 ms 帧周期，缺少固件级 Tx slot 或实测触发时序。
- memory mapping：`PARTIAL_NOT_FORMAL`；8 个 `tx*_rx*` 数组和 256 range bins 可见，但 PSIC/ReportDataCube1D 字段定义、IQ 排列、stride、端序和镜像处理尚未独立核验。

## 4. GPT 裁决文件可追溯性

子任务启动时远程分支尚未同步 `981d5c6`，因此三个任务的早期 manifest 记录了暂时性的不可读状态。随后已从同一远程分支核验：

`docs/decisions/2026-08-25-gpt-p0-audit-adjudication.md`

对应 commit：`981d5c6`。

此前 Codex handoff 为 `89a6818`；本轮合并后的远程分支已同时包含 GPT 裁决、本次三条主线结果及相关方法文件。

## 5. 当前不应做的事情

- 不应因为北京 71 个结构字段检查通过就直接运行正式事件模型。
- 不应把珠海 30 个登记记录当作已连接的 30 个实际 session。
- 不应把 NIR AUC 低于 .50 改写为 `1 - AUC`。
- 不应把 RS6240 的 target-lock、RGB gate、range-bin 镜像支持或 coverage 直接称为 HR/BR/HRV 准确性验证。
- 不应在 firmware、Tx timing 和 memory mapping 未闭合前继续扩展心脏算法调参。

## 6. 请求 GPT 下一轮裁决

1. 在 `981d5c6` 无法定位的情况下，是否先以 `89a6818` handoff 作为版本基线，还是请 GPT 提供正确仓库/分支路径？
2. 北京 identity 尚未恢复时，是否允许在明确标记为 session-level、非 participant-level 的范围内运行描述性事件图，而暂不做推断统计？
3. 珠海应优先从哪个登记表、采集目录或 session manifest 开始恢复 30 条链接？
4. RS6240 的 firmware、Tx slot 和 memory mapping 证据应从哪个硬件/固件文档或原始采集元数据补齐？

## 本地详细产物

- 北京：`D:\Project\厚粲杯\11_数据\derived\beijing_semantic_session_gate_event_v1\report.md`
- 珠海：`D:\Project\厚粲杯\11_数据\derived\zhuhai_session_linkage_nir_event_readiness_v1\handoff_report.md`
- RS6240：`D:\Project\厚粲杯\11_数据\derived\rs6240_data_chain_technical_gate_v1\report.md`

上述详细产物仅保留在本地，未上传 GitHub。
