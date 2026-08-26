# FocusWave Multimodal Attention Analysis 状态

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

