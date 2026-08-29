# RGB 当前结果状态 v1

- 盘点时间：2026-08-28（Asia/Shanghai）
- 数据根：`D:\\Project\\厚粲杯\\11_数据\\04_Attention-Analysis_nvidia-cuda_RGB`
- 证据范围：正式 RGB raw/context 产物；不启动新算法，不承诺虹膜校正。
- 状态：**PARTIAL / RAW-CONTEXT MERGE READY**。

## 结论

RGB 审计发现 72 个 session；cohort 记录中 71 个 formal session 已完成 raw 提取并可进入合并准备。正式 71 个 session 均有 Face raw、Motion raw、Pose landmarks 和带 behavior/probe 上下文的 `face_frames`。`sub-099` 被审计列为非 formal usable；`sub-060` 在输出根下仅有空目录且没有 subject manifest。

当前可直接合并的粒度是：`subject/session/block/probe/window`，时间锚定字段为 `unix_ms`。本轮已核对到 frame/context 行；尚未生成 RGB derived window summary。

## 1–2. Session、窗口与 coverage

见 [rgb_session_availability.csv](./rgb_session_availability.csv)。每个 session 的 baseline、block1、block2 行数与 Unix 时间覆盖均已列出；baseline 的 block 为空是设计状态，不是缺失。

- formal usable：**71/72**。
- behavior 对齐行定义为 `block` 与 `trial_num` 均非空的 frame/context 行。
- probe 对齐行定义为 `is_probe == 1` 的 frame/context 行。

## 3. 已有特征字段

见 [rgb_feature_dictionary.csv](./rgb_feature_dictionary.csv)。Face raw 保留 bbox/confidence、68 点坐标、head pose、20 个 AU、7 类表情、valence/arousal、gaze、478 点 mesh 和 blendshape；Pose raw 保留 landmark/world landmark 与 visibility/presence；Motion raw 保留灰度、帧差和运动能量。这些是 raw measurement，不等同于最终论文窗口特征。

## 4. 质量指标字段

现有质量字段包括 FaceScore/detected、pose_valid/visibility/presence、sample_error_ms、dt/gap、irregular_dt、motion_valid、diff threshold 与 probe/context completeness。它们是 QC 输入/标记，不是已通过的 downstream QC 结论；subject manifest 中 `qc_pass` 不应解释为 PASS。

## 5. 合并主键

推荐主键：**`subject/session/block/probe/window`**。实现时保留 `unix_ms` 作为时间锚点，并保留 `video_frame_position` 与 `capture_frame_idx` 两套 frame identity；禁止仅用行号或视频帧序号替代时间主键。

## 6. Behavior/probe 对齐行数

见 [rgb_merge_ready_summary.csv](./rgb_merge_ready_summary.csv)。该表同时给出总 `face_frames`、behavior-aligned 行、probe-aligned 行和 baseline/block1/block2 行数。它表示 raw/context 合并就绪，不表示 RGB derived features 已完成。

## 7. 缺失原因统计

- `sub-099`：审计明确 `not_formal_usable`，不纳入 RGB formal 合并。
- `sub-060`：有目录但无 manifest/cohort completion 记录，按未完成处理。
- 全部 71 个 formal session：未发现 `rgb_features.parquet`、face tracking、eye/iris、pose features、blink/PERCLOS 派生文件。
- 全部 71 个 formal session：未作虹膜校正，也不作虹膜校正承诺。
- 机械核验限制：subject manifest 内含 Windows 路径反斜杠，当前文件不能通过严格 JSON 解析；本交付的行数以 `cohort_status.csv`、实际 `face_frames.csv` 和 raw 文件记录为准，不把 manifest 的可解析性宣称为 PASS。
- 非 task frame/context 行主要来自 baseline、instructions、practice、transition/interblock transition；它们没有 block/trial 行为键属于当前数据结构边界，不应静默当作 behavior trial 行。

## 8. 报告书可直接使用的 RGB 模块状态段

> **RGB 模块状态。** 本研究已完成 RGB 正式数据的 raw-level 提取与可用性盘点。共审计 72 个 session，其中 71 个 session 完成 Face、Pose 与 Motion 原始输出，并保留统一的 `subject`、`unix_ms`、`phase`、`block`、`trial` 与 probe 上下文，可按 `subject/session/block/probe/window` 与行为及其他模态进行后续合并。RGB raw 层已保留面部检测/坐标、面部动作单元与表情、头部姿态/注视、面部网格、身体姿态及运动能量等字段，同时保留时间间隔、掉帧、检测有效性和姿态可见性等质量标记。当前状态为 **raw/context merge ready，derived-window feature 与 downstream QC 尚未完成**；`sub-099` 不纳入 formal RGB，`sub-060` 因缺少 formal manifest 暂不纳入。本文不报告虹膜校正、眼睑/PERCLOS 或其他尚未生成的 RGB 派生结果。

## 证据与限制

- RGB audit：`rgb_formal_audit_v1_summary.json`（72 discovered / 71 formal usable / sub-099 excluded）。
- cohort completion：`cohort_status.csv`（71 records；66 complete + 5 skipped_complete）。
- per-subject manifest：各 `sub-XXX/sub-XXX_manifest.json`。
- 本交付未启动 Face/Pose/Motion 新推理；未修改算法定义。


