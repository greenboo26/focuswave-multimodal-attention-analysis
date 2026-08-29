# mmWave next execution prompt — 2026-08-29

Status: `ASSIGNED / #16 PAUSED`

Use this prompt verbatim for the next Codex/agent execution.

---

继续 `greenboo26/focuswave-multimodal-attention-analysis@main` 当前毫米波主线。

先读取并以其为唯一当前任务契约：

1. `PROJECT_STATUS.md`
2. `docs/research/MMWAVE_OPEN_QUESTIONS_EVIDENCE_MAP_AND_EXECUTION_INSTRUCTION_2026-08-29.md`
3. `docs/research/MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`
4. `docs/research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`
5. `docs/research/MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`
6. `docs/research/MMWAVE_LITERATURE_EVIDENCE_AND_DECISION_LEDGER_2026-08-29.md`
7. `docs/canonical/MMWAVE_CURRENT_STATE_2026-08-29.md`

不要重新从 generic FMCW 文献或 RS6240 基础介绍开始。

当前已确认，不得重新降级为 UNKNOWN：

- 正式镜像 `mrs6240_p2512.img`
- `fft_mode=2`
- `range_fft_len_log2=8`
- 256 点 1D Range FFT DataCube
- `0.037 m/bin`
- 2T×4R = 8 complex channels
- `ReportDataCube1D` 不是 raw ADC

本轮目标不是运行新科学分析，而是关闭剩余的证据问题。

## A. 先关闭设备/固件工程问题

依次确认：

1. pre-FFT window 类型、应用轴和参数；
2. zero padding / FFT scaling；
3. DC/static clutter removal；
4. IQ correction；
5. channel amplitude/phase calibration；
6. 8 通道 Tx/Rx 物理映射；
7. TDM Tx switching / chirp timing；
8. TDM phase compensation；
9. 正式实验设备是否真的烧录并启动了该 formal firmware image。

证据优先级：

formal device burn/boot/version record
> exact formal firmware image/build binding
> matching source/config
> official SDK exact report path
> official manual/API
> output semantics
> historical note

每一项必须给：

- source path / official URL
- manual version + page/section，或 source file + function + lines
- firmware binding
- formal-device binding
- conclusion
- status
- remaining gap

状态只能用：

`CONFIRMED_ON_FORMAL_DEVICE`
`CONFIRMED_IN_FORMAL_FIRMWARE`
`SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY`
`CONFIRMED_BY_OUTPUT_SEMANTICS`
`UNRESOLVED`
`NOT_APPLICABLE`

禁止把“SDK支持”写成“正式设备已执行”。

## B. 再查 target/bin/channel continuity

优先复用已有结果，不重新跑科学分析。

从现有输出读取或派生：

- 每窗 HR selected bin/channel
- 每窗 BR selected bin/channel
- previous-window bin/channel
- bin displacement
- channel switch
- phase discontinuity
- phase-stability/QC outcome
- 已有 independent motion evidence
- 已有 RGB/key-press/motion proxy（只读）

必须回答：

1. bin hopping 多不多；
2. channel switching 多不多；
3. phase unstable 是否集中出现在 target switch 附近；
4. 是否存在“无独立运动证据，但 target/bin/channel 发生切换并伴随 phase jump”；
5. 当前 QC 是否在相当程度上衡量 current target-selection continuity，而不是 acquisition quality。

如果现有结果没有保存 selected bin/channel history：

停止，不要擅自跑 formal batch；只报告最小 instrumentation/rerun 需求。

## C. 证明 formal 2×BR/3×BR harmonic suppression 是否真正 active

严格追：

`formal runner -> process_vital_signs_v3_1_1.py -> harmonic rejection branch`

列出：

- function definition
- call site
- required arguments
- branch condition
- `acq_path` / RSP 是否传入
- formal runner 到底是 ACTIVE suppression / INACTIVE / POST_HOC_FLAG_ONLY

不运行新的 HR 分析。

## D. HRV 只定义 blocker，不救算法

检查现有资产是否具备：

- radar beat timestamps
- radar IBI sequence
- ECG R-peak timestamps
- radar↔ECG sync mapping
- beat matching output

找到最早缺失层。若任何一层缺失，保持 HRV=`BLOCKED`。

## E. 更新 canonical GitHub

所有新事实、证据、判断和决策同轮写回：

- `MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`
- `MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`
- `MMWAVE_LITERATURE_VS_PROJECT_STAGE_MATRIX_2026-08-29.csv`
- `MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`
- `MMWAVE_PIPELINE_FLOWCHART_2026-08-29.md`
- `PROJECT_STATUS.md`
- `RESULT_INDEX_V1.md`
- `CHANGELOG.md`（若有 material conclusion change）

所有本地大文件只记录绝对路径 + hash/manifest/provenance，不上传原始数据。

## 禁止

- 不运行 #16
- 不重跑 C2B/C2C
- 不开发新 target-lock 算法
- 不做 AoA/beamforming/VMD/multi-bin search
- 不修改原始数据
- 不修改 NIR/RGB producer
- 不把 phase/QC failure 自动解释成 participant movement
- 不重复已经闭合的 Range FFT / 37mm / 8-channel discovery

## 完成标准

只有以下全部完成才可报 PASS：

1. 设备/固件剩余工程项都有明确 evidence status；
2. target/bin/channel continuity 已从现有输出完成审计，或明确证明缺少哪项最小 instrumentation；
3. formal harmonic suppression activation 已被调用链证明；
4. HRV 最早缺失的 beat/ECG layer 已定位；
5. 所有 material findings 同轮写回 canonical GitHub。

否则报 `PARTIAL`，并保持 `#16 PAUSED`。
