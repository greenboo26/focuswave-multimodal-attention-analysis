# GPT 裁决：a3ec61e 三主线 follow-up

日期：2026-08-25
依据：`docs/decisions/2026-08-25-gpt-981d5c6-followup-handoff.md`
角色：GPT 研究/方法裁决

## 总裁决

本轮三条主线执行合格，且没有越过 blocker 强行产生正式结果。下一步继续保持“先恢复证据链、再运行正式模型”，但做三项重要收缩：

1. 北京身份恢复不再从零搜索，优先复用已经在 C2 中恢复的 71 recording sessions / 46 `repeat_participant_id` 身份链，与北京 71 个有时间线 session 做确定性交叉映射；
2. 珠海暂不进入任何正式/探索性 NIR 事件建模，先只恢复“登记记录 → 实际采集 session → 行为/时间线 → 模态目录”的一对一数据链；
3. RS6240 将 range-bin 镜像关系与连续设备时间轴分别升级为有限通过，但总体 physiology/event gate 仍未通过。可以继续工程审计和非生理 QC，不批准 HR、BR、beat、IBI、HRV 的正式解释或调参扩展。

## 1. 北京：身份链复用优先于重新恢复

### 1.1 新发现

前序 C2 handoff 已明确记录：

- 既有矩阵包含 71 recording sessions；
- 46 个已恢复重复参与者；
- 通过 `repeat_participant_id` 做 participant-disjoint 分组。

当前北京 preflight 又得到：

- 72 个候选 behavior sessions；
- 71 个具有有效时间线；
- `sub-099_` 因缺少 `master_timeline.csv` 排除。

这两个“71”高度提示存在同一 session universe 或大范围重叠，但**数量相同不是身份依据**。必须做 deterministic crosswalk。

### 1.2 北京下一步只做一个最小 identity crosswalk

建议 RUN_ID：`BEIJING_C2_IDENTITY_REUSE_CROSSWALK_V1_20260825`

优先读取本地、已经用于 C2 的 participant/session master、repeat-participant crosswalk、71-session matrix manifest 或等价 provenance 文件，不重新用行为模式、时间模式、雷达/NIR 特征猜身份。

允许的连接键按优先顺序：

1. 原始匿名 subject/session key 的精确一致；
2. C2 manifest 中的 recording/session path 与北京 behavior/timeline path 的确定性对应；
3. 已有 project master/crosswalk 中明确记录的一对一映射；
4. 绝对采集时间 + 唯一匿名 subject/session code 的确定性联合匹配。

不允许：仅凭相同 session 数、相似 probe 数、标签分布、行为表现或传感特征建立身份。

输出必须区分：

- `EXACT_REUSED_IDENTITY`：可直接复用 C2 `repeat_participant_id`；
- `AMBIGUOUS`：存在多个候选；
- `UNMATCHED`：无现成 C2 身份证据；
- `EXCLUDED_TIMELINE`：如 `sub-099_`。

### 1.3 Canonical session

如果北京 behavior directory 与 C2 recording session 可以一对一对应，则该 crosswalk 可以同时解决 canonical session identity；无需另造新的 session 编号体系。新的 canonical key 必须保留来源字段，以便追溯到 C2 和北京 timeline 两边。

### 1.4 Probe response mapping 仍是独立硬门槛

即使 71 个 session 身份全部恢复，也不能自动认为 session 级 probe 语义已通过。

可接受的“语义等价证据”包括：

- 采集时实际发布包/程序资产；
- session log 中写出的 probe 文案或 option mapping；
- 可证明所有这些 session 来自同一冻结发布包、且该包中 1/2/3/4 含义明确；
- 其他能够从 session provenance 确定 response mapping 的非推断证据。

若只能确认“BB 两阶段、20 probes、字段名一致”，但无法确认 1/2/3/4 的具体含义，正式心理构念分析仍阻塞。

### 1.5 experiment_abort 的处理

`sub-064_`、`sub-084_` 不应自动全排，也不应自动当完整 session。

先确定：

- abort 发生于 B1、休息、B2 的哪一位置；
- abort 前的 trial/probe 时间线是否完整；
- abort 是否改变既有 probe response 的有效性。

若 abort 前存在完整、语义可确认的 probe，可在预先定义的“partial session”规则下纳入不依赖后续阶段的分析；涉及 B1→B2 恢复或完整 time-on-task 的分析则排除。不能事后按结果决定。

## 2. 北京身份未完全恢复前，是否允许画事件图

### 裁决：允许，但仅限 `EXPLORATORY_QC`，不能作为正式构念效度结果

在 participant identity 和 probe mapping 未完全通过前，可以生成以下图用于检查事件对齐、窗口定义和数据质量：

- 每个 session 单独的 probe-aligned behavior trajectory；
- session-level error / reaction time 轨迹；
- B1/休息/B2 边界可视化；
- 不带 population-level inferential statistics 的 session spaghetti/heatmap。

禁止：

- 把 session 当独立参与者计算总体 *p* 值；
- 把多个可能属于同一人的 session 当独立样本；
- 把这类图写成“thought probe 构念效度已验证”；
- 在 response mapping 未确认前给 1/2/3/4 赋予“完全任务聚焦/走神”等心理标签。

如必须用颜色区分类别，只能用 `raw response 1/2/3/4` 中性命名。

这类图的价值是提前发现窗口/时间线 bug，不是抢跑正式结果。

## 3. 珠海：只恢复 session data chain，不再扩展模型

珠海当前 30/30 登记记录均未连接到实际采集 session。因此下一步唯一主任务是 deterministic linkage。

建议 RUN_ID：`ZHUHAI_REGISTRY_TO_ACQUISITION_CROSSWALK_V1_20260825`

按以下证据优先级恢复：

1. 项目 session manifest / master index /登记表中明确记录的匿名 subject-session key；
2. 行为 CSV 或 `master_timeline.csv` 内嵌的 session/subject 元数据；
3. 程序运行日志、目录名、文件头或 manifest 中记录的绝对采集开始时间；
4. 在同一匿名 subject code 下，用登记时间与行为绝对时间形成唯一一对一匹配；
5. 行为 session 确定后，再用绝对时间范围去链接 NIR、毫米波、RGB 等模态。

不得使用 pupil、radar、RGB 行为模式等内容特征做身份推断。

如果本地没有任何包含实际 session id/绝对时间的 manifest，应明确返回 `SOURCE_METADATA_MISSING`，不要继续穷举目录结构或根据文件总时长猜测。

珠海在一对一 linkage 恢复前只作为“程序级三阶段协议证据”进入报告，不作为数据结果。

## 4. RS6240：技术 Gate 分项升级，但总体仍未开放 physiology

### 4.1 Range mapping

当前 18/18 小分片支持：

`mirror_bin = 256 - profile_bin`

且 16/18 局部最大值精确镜像匹配。

裁决状态：`G-R1 = PASS_WITH_LIMITS`。

这已足以说明 244–248 与 8–13 很可能是 256 点 FFT 的镜像索引体系，而不是两套完全不同的物理目标。下一步不再把它作为“疑似 target selection bug”主线，但仍需在完整 parser/config mapping 中确认正/负频率、bin-to-range 公式和使用哪一侧作为 canonical range index。

### 4.2 连续时间轴

已有 3 场、每场前约 6000 帧显示 `device_ms` 中位帧间隔约 10 ms、最大约 14 ms，未见 >15 ms gap；`host_ms` 存在大量缺口与非正增量。

裁决拆分为：

- `G-R2a continuous sampling time = PASS_WITH_LIMITS`：正式波形连续时间优先使用 `device_ms`；
- `G-R2b absolute experiment alignment = BLOCKED/UNVERIFIED`：仍需证明 `device_ms` 如何锚定到 probe/NIR/RGB 的绝对 Unix 时间，或通过何种同步 marker/host anchor 映射。

因此不能仅凭 `device_ms` 连续就开始正式 probe-locked radar physiology。

### 4.3 仍为硬 blocker

- firmware/build 与采集 session 绑定；
- 2TX × 4RX 的真实 Tx slot/chirp timing；
- PSIC/ReportDataCube1D 或实际 message 的正式 memory/IQ/channel mapping；
- calibration 在 session 级的存在与作用范围。

当前总体状态：`TECHNICAL_CHAIN_PARTIALLY_OPEN / PHYSIOLOGY_BLOCKED`。

允许继续：

- range/time/parser 工程 sanity checks；
- 非生理的数据覆盖、frame timing、索引一致性 QC；
- 小样本静态距离 sanity test。

不批准：

- HR/BR/beat/IBI/HRV 正式分析；
- 为追求生理结果继续调滤波器、谐波规则或 beat detector；
- 将 device_ms 的连续性解释为 probe 级绝对同步已经完成。

## 5. RS6240 最小补证路径

建议 RUN_ID：`RS6240_FIRMWARE_TX_MEMORY_PROVENANCE_V1_20260825`

只补三类证据，不再扩任务：

1. **Firmware provenance**：采集程序日志、binary/build hash、配置文件、SDK/firmware version string 或烧录记录；若无法逐 session 获取，至少建立“哪些 session 可绑定到同一 build”的证据。
2. **Tx timing**：实际 radar config / chirp profile / firmware source 或 debug export 中的 Tx sequence、chirp repetition interval、Tx slot；若拿不到固件源码，可接受厂商调试工具导出的实际配置。
3. **Memory mapping**：与当前采集版本对应的 message/struct 定义、parser source、字段 offset/shape、IQ/通道顺序、端序和镜像处理。必须对应历史采集版本，不能直接拿 2026 最新 SDK 格式替代。

如果这些资料在本地工作区不存在，应返回具体缺失文件类别并标记 `EXTERNAL_VENDOR_DOC_REQUIRED`，不继续猜测。

## 6. 当前 formal / exploratory / blocked / unverified

### Formal / 可作为正式既有事实

- C2 既有 71 recording sessions、46 个已恢复 `repeat_participant_id` 的 participant-disjoint 身份链存在；
- 北京 71 个 session 的基本 B1/休息/B2、trial/probe 时间结构通过字段/值域检查；
- 珠海程序级三阶段设计存在；
- RS6240 小样本中 range-bin 镜像关系得到有限支持；
- `device_ms` 在已审计小样本中明显更适合作为连续帧时间轴。

### Exploratory

- 北京 identity/probe gate 未通过前的 session-level 事件 QC 图；
- RS6240 小样本 range/time sanity 结论向全量 session 的外推；
- 当前 NIR 反向排序现象。

### Blocked

- 北京正式 longitudinal/event-related inference；
- 珠海实际三阶段数据分析；
- RS6240 正式 physiology 与 probe-locked physiology；
- C1b 正式外部 Radar–ECG benchmark 数据访问。

### Unverified

- 北京各 session 1/2/3/4 response mapping；
- 珠海实际 session 文件链；
- RS6240 session-level firmware/Tx/memory/calibration provenance；
- `device_ms` 到实验绝对 Unix 时间的正式映射。

## 7. 下一轮只保留三条任务

1. `BEIJING_C2_IDENTITY_REUSE_CROSSWALK_V1`：复用 C2 身份链 + 恢复 probe response semantic evidence；一旦 G1–G5 有正式通过 subset，立即按冻结方案跑该 subset 的北京正式行为事件分析，不必等待全部 72 场。
2. `ZHUHAI_REGISTRY_TO_ACQUISITION_CROSSWALK_V1`：只恢复 30 条登记记录到实际行为/timeline/session 的确定映射；暂不跑 NIR 模型。
3. `RS6240_FIRMWARE_TX_MEMORY_PROVENANCE_V1`：只补 firmware、Tx timing、memory/parser/calibration provenance 和绝对时间 anchor；不调生理算法。

三个任务都必须允许“部分成功”：北京只要形成可审计 `PASS_FORMAL` subset，就可以开始该 subset 的正式分析；珠海只要形成确定性链接 subset，就先报告覆盖，不要求一次恢复 30/30；RS6240 任一技术项找不到资料时应明确 `EXTERNAL_VENDOR_DOC_REQUIRED`，不以猜测填空。
