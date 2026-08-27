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

## 2026-08-27 MMWAVE_FORMAL_REANALYSIS_V2

- 独立分支 `codex/mmwave-formal-reanalysis-v2` 建立第一阶段资产审计与执行体系；不覆盖旧 C1/M1/C2B/C2C/v1-v9/C1b 结果。
- 新增 `docs/mmwave_reanalysis_v2/`：evidence ledger、dataset/method/parameter/failure matrices、benchmark plan、validation gates、formal cohort plan、open gaps 和 handoff。
- Phase 2A 状态 `PASS`：`BENCHMARK_DECISION_V1` 已在 held-out 评分前冻结；AgeBalanced 110/440 与历史 220 Rest sessions 已完成逐文件 provenance 对账；统一 per-window schema 和测试已落地。
- Phase 2B-1 为 `PARTIAL`：仅在冻结 development split 完成历史 25 s 等价性诊断（60 Rest sessions；session-MAE median 9.14 BPM）和 schema-valid 30 s baseline（256/268 scored；median AE 13.79 BPM）。25 s 与 V1 schema 窗口枚举不兼容；完整 220-session 历史复现仍需明确 held-out 授权。详见 `docs/mmwave_reanalysis_v2/PHASE2B1_HISTORICAL_BASELINE_REPRODUCTION.md`。
- 毫米波任务2已完成但状态为 `BLOCKED`：唯一允许的 SSA+VMD 外部路线的公开 `L=400` 参数不适配冻结 30 s 输入，未生成外部 development score；建议 `DOWNGRADE_PHYSIOLOGY`，保留信号级 supporting route。
- Task 2R 50 s development 同条件比较已完成：项目方案 MAE 29.02，SSA+VMD adapted MAE 28.12，均 coverage 92.05%，未达到 HR gate；锁频总数未下降。状态 `PARTIAL`，建议 `DOWNGRADE_PHYSIOLOGY`，不自动进入 80 人。
- Task 2S Lei 2025 SSA 核心 60 s development 比较已完成：实际 14 个 session 有完整 60 s 输入，项目路线 12/14 scored、MAE 37.12；Lei SSA 12/14 scored、MAE 38.06，coverage 不变但 RMSE/相关性/P90 恶化，未达到约 20% 一致改善门槛。状态 `PARTIAL`，建议 `STOP_PHYSIOLOGY_RND`，不自动进入 80 人。
- BR→HR→HRV 分层冻结；HRV 仍为 `BLOCKED`，正式 cohort 只能在外部 ECG/RSP benchmark 门通过后进入。

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

