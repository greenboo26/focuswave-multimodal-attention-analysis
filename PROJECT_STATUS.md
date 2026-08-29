# FocusWave Multimodal Attention Analysis 状态

## 2026-08-29 local↔canonical reconciliation gate — PASS

- 已完成本地与 canonical 的 43 条分析视图对账：30 条 MATCHED、2 条 SUPERSEDED、
  6 条 PRODUCER_OWNED、3 条 PLANNED_NOT_EXECUTED、2 条 PRODUCER_NOT_READY；
  PATH_STALE、RESULT_MISMATCH、TRUE_MISSING、LOCAL_ONLY、REMOTE_ONLY 均为 0。
- C2C 历史结果不作为当前结论，待 canonical rerun；NIR/RGB increment 尚不是 global final。
- 该 PASS 仅表示本地与 canonical 的已完成证据对账通过，不代表未来计划分析已完成。

## 2026-08-29 Issue #15 mmWave physiology/QC closure — CLOSED_WITH_EXPLICIT_BOUNDARIES

- HR：`PASS_QUALITY_GATED`；corrected BIOPAC calibration MAE=3.777 bpm，仅支持质量门控候选和 #16 sensitivity。
- BR：`PASS_SUPPORTING`；corrected spectral calibration MAE=3.328 breaths/min，仅支持辅助/敏感性分析。
- HRV：`BLOCKED`；现有 beat/IBI 与 ECG 闭环不足，C1D 保持 `NO_MATERIAL_IMPROVEMENT_STOP_HRV`。
- corrected QC：Tier1=33、Tier2=37、Tier3=2（067/099）；Tier1 不等于 ground-truth validated。
- #16 仅允许一次预定义 quality-stratified sensitivity；不重跑 C2B/C2C，不启动新算法路线。

## 2026-08-29 local analysis assimilation status — PARTIAL

- 已把旧 dirty 工作树中可确认的中央本地独有分析入口、QC/merge-readiness/RGB
  状态报告和小型 provenance 文件收编到现有 canonical 路径；没有重新运行科学分析。
- 57 个旧路径删除均已与 `scripts/legacy/`、`scripts/maintenance/` 或既有维护路径完成
  内容级迁移证明；历史脚本不计 active analysis。
- C1c/C1d 仍为 `VALIDATION_STOPPED`；HR、BR、HRV 仍受 QC/reference/逐搏验证边界约束。
- RGB/NIR worktree 仍由 producer repo 所有；RGB 仅 raw/context merge-ready，NIR 仅工程审计边界。
- 大型矩阵、波形、逐帧输出和 PNG 保留在本地 `11_数据\derived` 或 producer worktree，Git
  仅收报告、摘要、manifest、schema 和生成脚本。
- 旧分支仍含 78 个 tracked modified、40 个 untracked 及 unresolved 项，尚未具备退休条件。

收编逐项链路见 `docs/repository/LOCAL_ANALYSIS_ASSIMILATION_2026-08-29.md`，结果索引见
`docs/canonical/RESULT_INDEX_V1.md`。

## 2026-08-29 unresolved closure

已关闭上一阶段 22 个 unresolved 处理单元：5 个 `KEEP_IN_MAIN`、5 个
`PRODUCER_REPO_OWNED`、1 个 `SUPERSEDED`、4 个 `HISTORICAL`、7 个
`GENERATED_ONLY`；`SAFE_TO_REMOVE` 和 `BLOCKED_BY_RUNNING_TASK` 均为 0，
剩余 `UNRESOLVED` 为 0。这里是归类关闭，不是删除授权；旧 dirty 分支和
producer worktree 仍然保留。

## 2026-08-26 Stage 2C governance status

- `main` 是正式默认分支，repository 已更名为 `greenboo26/focuswave-multimodal-attention-analysis`。
- Stage 2C 文件树收口仅整理 Git-safe 的入口、contract、方法、provenance 和聚合结果；未开始新的科学分析，未修改科学结果。
- NVIDIA ref 固定为 `36a2d596c55b93071a8b5c80459a56c876c06351`，AMD ref 固定为 `d8e721079461ef7f71fafcd3edf819858fabbb16`。
- NIR 69/72 fullclass 状态不变；68 sessions/44 participants/1,360 probes 仍是 pre-recovery 边界；sub-100/sub-178 等待 full recovery/QC/Probe alignment；sub-099 仍为 `master_timeline` blocker。
- RGB 保持 `PIPELINE_ENGINEERING_PENDING / FORMAL_ANALYSIS_NOT_AUTHORIZED`；mmWave HRV 保持 validation boundary/ablation，不重新成为近端主线。
- 旧 `master` 与 `legacy/mmwave-hrv-master-pre-focuswave-20260826` 保留为 rollback surface。

## 2026-08-26 canonicalization status

项目显示名称：`FocusWave Multimodal Attention Analysis`。已在本地完成代码、derived、formal NIR/RGB、J 盘 discovery、环境和 worktree 事实审计。Registry 共 29 项：14 `VALID_SUPPORTING`、3 `PENDING_CANONICAL_RERUN`、1 `BLOCKED_EXTERNAL_STORAGE`、6 `ENGINEERING_ONLY`、5 `PLANNED_GLOBAL_ONLY`，0 `CANONICAL_FINAL`。下一步仅为 GPT-5.6 Sol 独立科研方法审查；AMD 分支和新批量分析均未开始。

更新时间：2026-08-25

## 当前正式管线

- ECG 正式管线保持不变。
- `v3.1.1` 仅用于独立验证，暂不替代正式主链。
- 毫米波目标锁定验证先于 HR、BR、HRV；全场合理距离峰不是充分质量条件。
- 尚未宣称毫米波 HR、BR 或 HRV 已经准确。

## J 盘目标锁定审计

- 26 个全场距离初筛候选已完成首/中/末分片审计，共 78 条记录。
- 目前重点场次为 `sub-078` 和 `sub-091`。
- 两场首、中、末分片均观察到 8 通道围绕共同近距离功率峰聚集。
- 四个中/末分片通过当前探索性 RGB 运动门控，可作为 HR/BR 复核候选。
- `sub-078-first` 与 `sub-091-first` 被探索性运动门标记，需先复核视频边界效应，不能直接剔除。
- `sub-074`、`sub-107`、`sub-129`、`sub-134` 保留为目标漂移负例。

## 当前下一步

1. 复核两个首分片的 RGB 边界、遮挡和曝光变化。
2. 对四个中/末分片执行最小 HR/BR 验证链。
3. 暂不直接进入 HRV；逐搏定位和 ECG 验证仍是前置条件。

## 证据边界

允许使用：`human-target-lock candidate`、`strong spatial consistency evidence`。

暂不使用：`chest lock confirmed`、`HR accurate`、`BR accurate`、`HRV accurate`。

## 本地结果位置

完整被试数据和派生结果不进入本仓库，保留在本地：

`D:\Project\厚粲杯\11_数据\derived\j_mmwave_target_lock_audit_v1\`

