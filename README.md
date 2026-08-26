# FocusWave Multimodal Analysis

这是 FocusWave 多模态注意力分析的正式分析总仓库入口候选，当前 GitHub repository 为 `greenboo26/focuswave-multimodal-attention-analysis`；仓库主体不再定义为 HR、BR 或 HRV 算法项目。毫米波是当前已审计的一个传感器验证边界，NIR 与 RGB 的生产代码分别位于外部 `kyandi233-dev/Attention-Analysis` 的受控 ref，最终结果和跨站点推断在本仓库中央收口。

## 当前科学状态

- 北京报告 cohort：70 sessions、46 natural participants、1,400 probes；label 1 对 labels 2/3/4；C+B 主窗口 30 s，10/20 s 为行为敏感性；participant-disjoint 5-fold；这是当前北京 C+B 锚点，不是未来 Beijing+Zhuhai global folds。
- Probe 四类语义固定为：1 完全任务聚焦，2 关注实验但未聚焦分拣，3 任务无关思维，4 思维空白。2/3/4 不得统称 mind-wandering。
- NIR 当前 69/72 formal fullclass complete 仍未变化；68 sessions/44 participants/1,360 probes 是 timestamp recovery 前的 `PRE_TIMESTAMP_RECOVERY_CURRENT_RESULT`，不是最终完整预测结果。sub-100/sub-178 已证明不是真实 AVI frame-gap blocker，当前为 `RECOVERABLE_PENDING_FULL_RECOVERY_QC_PROBE_ALIGNMENT`；sub-099 仍为 `master_timeline` blocker。若 recovery 改变 matched cohort，必须按冻结规则 rerun，NIR v2 仍需先完成 blink/PERCLOS 手工可行性检查。
- RGB 目前是 `PIPELINE_ENGINEERING_PENDING / FORMAL_ANALYSIS_NOT_AUTHORIZED`。`rgb-amd`、`rgb-nvidia` 先完成工程和 parity；局部 parquet 不得当作正式统计结果。
- mmWave C1 HRV 线已停止扩展，不能解释为硬件失败；C2B/C2C 没有稳定超越 C+B 的正增量，M1 作为 supporting person-effect audit，主线定位为 validation boundary/ablation。
- 北京 B1+B2 与珠海 B1+B2 是 shared primary，珠海 B3 是 extension。`DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE` 表示外部存储暂不可用，不表示数据不存在。

## 双机中央流程

```text
local raw data
  -> local standardized derived/QC package + linkage evidence
  -> central identity reconciliation
  -> authoritative global_repeat_participant_id
  -> global cohort and participant-disjoint folds
  -> final pooled / site-held-out inference
```

NIR/RGB 外部仓库只负责受控的本机派生生产。AMD 或 NVIDIA 均不得独立冻结 global participant ID、global folds、跨站点 p-values/AUCs，也不得将两台机器的最终推断结果平均。完整约束见 `contracts/multimodal/DUAL_MACHINE_ANALYSIS_CONTRACT_V1.md`。

## 目录入口

```text
configs/       cohort、window、model 配置
contracts/     identity、behavior、questionnaire、sensor、fusion contract
schemas/       local derived、QC、central merge 的字段约定
pipelines/     各 modality 的 canonical entrypoint/adaptor 索引
results/       canonical、supporting、engineering reference、superseded index
docs/          methods、decisions、provenance、reports、repository governance
tests/         schema/path/contract smoke checks
```

本次重构只迁移 Git-safe 的索引、contract 和聚合结果入口，不移动 import-sensitive legacy producer；迁移边界见 `docs/repository/MIGRATION_MANIFEST_V1.csv`。原始数据、participant-level rows、NPZ/MAT/BIN/AVI、缓存、模型私有路径和大型输出均禁止进入 Git。

## 从哪里开始

1. 先读 `docs/repository/REPOSITORY_ARCHITECTURE_V1.md`、`docs/provenance/CROSS_REPO_PROVENANCE_V1.md` 和双机 contract。
2. 只使用 `results/canonical/README.md` 作为当前正式结果入口；`results/supporting/` 与 `results/engineering_reference/` 不得升级为最终科学结论。
3. 本地派生前执行 runbook/contract 的 preflight；中央身份、cohort、fold 和最终 inference 需要中央整合权限。
4. 当前 repository 已完成 Stage 2A rename 和 default branch 切换；旧 `master`、legacy tag 与 archive tags 仍保留，branch retirement 尚未执行。

## 复现和数据边界

所有可运行模块必须记录 `machine_role`、`runtime_backend`、`pipeline_version`、`git_commit`、`model_hash`、`config_hash`、`schema_version`、`source_manifest_hash`。缺少这些字段的历史结果只可作为 supporting/reference，并在报告中显式写出不可复现限制。

正式审查入口：`docs/repository/REPOSITORY_CUTOVER_PLAN_V1.md`。本 candidate 只等待 GPT/Sol repository final review，不自行执行 branch retirement 或仓库切换。
