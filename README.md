# FocusWave Multimodal Analysis

这是 FocusWave 多模态注意力分析的正式中央仓库：`FocusWave Multimodal Attention Analysis`。仓库主体不定义为 HR、BR 或 HRV 算法项目。毫米波是当前已审计的一个传感器验证边界，NIR 与 RGB 的生产代码位于外部 `kyandi233-dev/Attention-Analysis` 的受控 ref，最终结果和跨站点推断在本仓库中央收口。

> **任何新算法、新特征、新 producer 改动或高成本重跑之前，先读根目录 [`ANALYSIS_HISTORY_LEDGER.md`](ANALYSIS_HISTORY_LEDGER.md)。** 该账本汇总中央分析、FocusWave 采集、Attention-Analysis producer 与历史 workspace 中已经做过、采用、回退、被后续证据替代和仍缺证据的路线，用于避免重复花费计算/API预算。

## 当前科学状态

### 行为科学 v3 网页修复基线

本分支 `codex/behavior-science-v3-baseline` 是网页普通聊天修复行为科学脚本的公开审阅 base。`v2` 结果已被监督判退，不得发布、上传、复制到本仓库或据此创建结果 PR。

- 判退缺陷规范：[`docs/methods/行为科学v3判退缺陷规范.md`](docs/methods/行为科学v3判退缺陷规范.md)
- v3 机器可读契约：[`contracts/behavior/行为科学v3分析契约.json`](contracts/behavior/行为科学v3分析契约.json)
- 合成测试骨架：[`tests/test_behavior_science_v3_contract.py`](tests/test_behavior_science_v3_contract.py)
- 判退脚本副本：[`scripts/rejected_baselines/behavior/generate_behavior_science_analysis_v2_rejected_baseline.py`](scripts/rejected_baselines/behavior/generate_behavior_science_analysis_v2_rejected_baseline.py)

该分支只接受网页代码修复审阅和合成测试，不接受真实数据、具体匿名组键、PII、v2 结果表/图/报告。网页修复完成后必须使用独立分支和 PR；本地真实数据执行由监督放行后在独立环境中进行。

- 北京报告 cohort：70 sessions、46 natural participants、1,400 probes；label 1 对 labels 2/3/4；C+B 主窗口 30 s，10/20 s 为行为敏感性；participant-disjoint 5-fold；这是当前北京 C+B 锚点，不是未来 Beijing+Zhuhai global folds。
- Probe 四类语义固定为：1 完全任务聚焦，2 关注实验但未聚焦分拣，3 任务无关思维，4 思维空白。2/3/4 不得统称 mind-wandering。
- NIR producer 已完成 2026-08-26 timestamp mapping 修复：`sub-100`、`sub-178` 经 sequential AVI-frame mapping 恢复，当前 source/formal fullclass 成功数为 **71/72**；matched cohort 为 **71 sessions / 1,420 unique probes**，其中 primary coverage `>=0.80` 为 1,174 probes。`sub-099` 仍因缺失有效 `master_timeline.csv` 阻塞。旧 68-session/1,360-probe NIR v1 科学分析在 cohort 扩大后没有自动重跑，因此旧增量结果只能作为 historical/pre-recompute evidence，不能冒充最终 NIR increment。
- RGB 当前主线为 **Face + Pose + Motion** 连续行为测量，不直接输出 Attention Score，rPPG/HR/HRV 不在正式 RGB 主链。NVIDIA 侧共享科学层已进入 `nvidia-cuda`，但 `sub-130` native CPU ↔ CUDA parity、gap stress、primary-face/blink/PERCLOS gate、direct full-video runner 与统一正式 schema 尚未全部完成；在这些 Gate 完成前不进行 NVIDIA RGB 正式全量，局部 parquet/pilot 不得当作正式统计结果。
- mmWave C1 HRV 线已停止扩展，不能解释为硬件失败；C2B/C2C 没有稳定超越 C+B 的正增量，M1 作为 supporting person-effect audit，主线定位为 validation boundary/ablation。AgeBalanced reanalysis 已确认旧约 27–38 BPM 断层主要来自把内部 `ecg_reference_v1` 错当官方 benchmark ground truth；按官方 AgeBalanced ECG FFT 重算，现有 project route 30 s development pooled MAE 为 **10.361 BPM**。该结果只修正外部 HR benchmark 口径，不等于 HRV 已验证，也没有打开 held-out 80。
- 北京 B1+B2 与珠海 B1+B2 是 shared primary，珠海 B3 是 extension。`DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE` 表示外部存储暂不可用，不表示数据不存在。

## 科学方法终审

现有比赛分析已经完成交付前方法终审，正式结论见：

`docs/canonical/SCIENTIFIC_METHOD_REVIEW_V1.md`

终审状态：`PASS WITH ROLE BOUNDARIES`。当前行为主分析、问卷单题效标支持和毫米波增量检验的总体统计设计可以继续使用，不需要推翻重做；但 C1、M1、repeat-session、C2C 和 legacy sensor increment 等必须保持其 supporting/diagnostic 角色，不能被升级成主证据。任何同事或 AI agent 在运行前都必须遵守该文件的标签命名、重复被试、grouped-CV、窗口、FDR、bootstrap 和解释边界。

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

原始数据、participant-level rows、NPZ/MAT/BIN/AVI、缓存、模型私有路径和大型输出均禁止进入 Git。

## 从哪里开始

### 同事、新机器或新 AI agent

第一份读：`ANALYSIS_HISTORY_LEDGER.md`。

第二份读：`docs/canonical/TEAMMATE_ONBOARDING_V1.md`。

第三份读：`docs/canonical/SCIENTIFIC_METHOD_REVIEW_V1.md`。

然后再进入 `docs/canonical/COMPETITION_DUAL_MACHINE_RUNBOOK_V1.md` 和具体 contract。这个顺序用于同时避免“环境装对了但科学协议跑错了”和“历史上已经做过却再次重跑”。

`TEAMMATE_ONBOARDING_V1.md` 明确说明：

- 中央仓库与 `kyandi233-dev/Attention-Analysis` 各自负责什么；
- Windows / Git / Conda / Python 环境怎么准备；
- AMD NIR 为什么使用外部 `runtime/nir-formal` 的 DirectML 安装/运行文档；
- `configs/paths.local.json` 怎么配置且为什么不能提交；
- site/protocol 为什么必须先核验，而不是直接套北京 cohort；
- 标准机器包怎么输出、怎么交回、哪些科学规则不得修改。

中央仓库推荐 Python 3.11 作为新机器共同基线，运行依赖在 `requirements.txt`，测试依赖在 `requirements-dev.txt`。

### 已完成 onboarding 后

1. 读 `docs/canonical/COMPETITION_DUAL_MACHINE_RUNBOOK_V1.md` 和相关 analysis/contract；不要在其他 site 数据上盲目运行北京专用 stage。
2. 读 `docs/repository/REPOSITORY_ARCHITECTURE_V1.md`、`docs/provenance/CROSS_REPO_PROVENANCE_V1.md` 和双机 contract。
3. 只使用 `results/canonical/README.md` 作为当前正式结果入口；`results/supporting/` 与 `results/engineering_reference/` 不得升级为最终科学结论。
4. 本地派生前执行 runbook/contract 的 preflight；中央身份、cohort、fold 和最终 inference 需要中央整合权限。
5. 旧 `master`、legacy tag 与 archive tags 只作为 rollback/provenance surface 保留，不作为同事分析入口。

## 复现和数据边界

所有可运行模块必须记录 `machine_role`、`runtime_backend`、`pipeline_version`、`git_commit`、`model_hash`、`config_hash`、`schema_version`、`source_manifest_hash`。缺少这些字段的历史结果只可作为 supporting/reference，并在报告中显式写出不可复现限制。

正式治理入口：`docs/repository/CANONICAL_ENTRYPOINTS_V1.md`、`docs/repository/FINAL_REPOSITORY_TREE_V1.md` 和 `docs/repository/REPOSITORY_CUTOVER_PLAN_V1.md`。本仓库不上传原始数据、participant-level rows、NPZ/MAT/BIN/AVI、缓存或机器私有路径。
