# FocusWave 比赛版统一分析管线 V1

状态：`RUNTIME_VERIFIED / TEAMMATE_HANDOFF_READY`

## 目标

本管线把已经完成并被当前项目采用的本地分析，收成可重复执行、可对照、可跨机器交付和可继续合并的统一比赛管线。当前不重新探索模型，不改标签，不重新选择窗口，也不因为另一台机器尚未执行行为/问卷/mmWave 而阻塞本机规范化。

优先级：先保证已经完成的分析有统一入口、统一依赖、统一输出目录和统一 manifest；再保证另一台机器未来可以使用同一入口和同一输出结构；双机交付后先做 schema/键检查，再合并 `merge_ready` 表。环境精确 lock 后续冻结，但每次正式运行都会自动记录实际 Python、包版本、producer SHA、Git commit 和输入证据。

## 比赛主分析顺序

`competition_core` 由 `configs/canonical/competition_pipeline_v1.json` 固定：

| 阶段 | 作用 | 冻结规则 |
|---|---|---|
| `report_cohort_v1` | 北京报告 cohort、四类 Probe、警觉性 | 已有 1400 probe / 70 session / 46 participant 边界 |
| `behavior_longitudinal_v1` | trial/probe 行为纵向 | 10/20/30 s，participant-clustered GEE |
| `behavior_preprobe_v1` | Probe 前行为补充 | 10/20/30 s，不改变状态定义 |
| `behavior_baseline_v2` | 正式行为/context 基线 | 30 s 主分析；10/20 s 敏感性；固定 5-fold participant-disjoint |
| `repeat_session_v1` | 重复实验/练习效应 | 既有重复测量模型和敏感性不变 |
| `questionnaire_q1_v1` | 事后走神单题效标 | 既有 Q1、cluster bootstrap/ordinal model，不扩展新题 |
| `mmwave_m1_v1` | 原始毫米波描述性/限制证据 | 30 s、LOSO、固定未调参 L2 logistic |
| `mmwave_c2b_v2` | 毫米波正式绝对特征增量 | 30 s 主分析；10/60 s 敏感性；不重新开发 HRV |
| `mmwave_c2c_v1` | 静息个体内归一化 | 30 s 主分析；10/60 s 敏感性；180 s baseline |

`competition_full_existing` 额外加入 C1 alignment validation 和既有北京 sensor increment。它们是支持/边界证据，不替代主分析。

## 本机配置

复制：

```powershell
Copy-Item configs/canonical/paths.local.example.json configs/paths.local.json
```

只修改 `configs/paths.local.json`，不要提交它。填写：`project_root`、`raw_data_root`、`derived_root`、`legacy_output_root`、`final_output_root`、`teammate_input_root`、`combined_input_root`，以及 `machine.machine_id` 和 `machine.site`。

`legacy_output_root` 指向现有 `08_算法/output` 根；`derived_root` 指向现有 `11_数据/derived` 根。推荐本机 `machine_id` 使用稳定名称，例如 `beijing-nvidia-main`；另一台机器例如 `zhuhai-amd-main`。

## 运行

全链 preflight：

```powershell
python scripts/canonical/run_competition_pipeline.py `
  --paths configs/paths.local.json `
  --profile competition_core `
  --dry-run
```

行为+问卷优先快速收口：

```powershell
python scripts/canonical/run_competition_pipeline.py `
  --paths configs/paths.local.json `
  --profile behavior_questionnaire
```

毫米波主链：

```powershell
python scripts/canonical/run_competition_pipeline.py `
  --paths configs/paths.local.json `
  --profile mmwave_core
```

完整比赛主链：

```powershell
python scripts/canonical/run_competition_pipeline.py `
  --paths configs/paths.local.json `
  --profile competition_core
```

只补一个阶段：

```powershell
python scripts/canonical/run_competition_pipeline.py `
  --paths configs/paths.local.json `
  --stage questionnaire_q1_v1
```

依赖阶段自动加入；存在完整 `stage_manifest.json` 的阶段默认跳过。确认要重跑时才使用 `--force`。

## 统一最终输出目录

```text
<final_output_root>/
└─ focuswave_canonical_v1/
   └─ <machine_id>/
      ├─ machine_package_manifest.json
      ├─ report_cohort_v1/
      │  ├─ producer_output/
      │  ├─ aggregate/
      │  ├─ merge_ready/
      │  └─ stage_manifest.json
      ├─ behavior_longitudinal_v1/
      ├─ behavior_preprobe_v1/
      ├─ behavior_baseline_v2/
      ├─ repeat_session_v1/
      ├─ questionnaire_q1_v1/
      ├─ mmwave_m1_v1/
      ├─ mmwave_c2b_v2/
      └─ mmwave_c2c_v1/
```

- `producer_output/`：原 producer 完整输出。
- `aggregate/`：结果核对、报告和 Git-safe 审核用聚合表。
- `merge_ready/`：未来双机合并需要的标准化行级派生表，只安全传输，不提交 Git。
- `stage_manifest.json`：机器、site、分析 ID、producer/ref、冻结参数、merge key、产物 hash。
- `canonical_run_manifest.json`：实际 Python/包版本、Git commit、producer SHA、路径配置 hash、输入证据。

## 对方机器输入/交付口

对方不需要现在执行行为、问卷或毫米波。未来完成任何一个阶段后，把整个机器包复制到：

```text
<teammate_input_root>/
└─ focuswave_canonical_v1/
   └─ <她的 machine_id>/
      └─ <analysis_id>/
         ├─ aggregate/
         ├─ merge_ready/
         └─ stage_manifest.json
```

不要只发散落 CSV，也不要重新命名列。缺少某阶段可以晚些补，已有阶段可先进入合并。

## 双机合并

```powershell
python scripts/canonical/collect_machine_packages.py `
  --paths configs/paths.local.json
```

固定输出：

```text
<combined_input_root>/
└─ focuswave_combined_v1/
   ├─ combined_manifest.json
   ├─ report_cohort_v1/
   ├─ behavior_longitudinal_v1/
   ├─ questionnaire_q1_v1/
   ├─ mmwave_m1_v1/
   ├─ mmwave_c2b_v2/
   └─ mmwave_c2c_v1/
```

收集器只合并同 `analysis_id + relative_path` 且列 schema 完全一致的 `merge_ready` CSV，并自动加入 `_source_machine_id` 与 `_source_site`。列不一致直接停止，不做猜测性映射。

聚合 AUC、p 值等不通过“两台机器平均”得到最终跨站点结果。真正跨机器/跨站点分析从合并后的 `merge_ready` 行级派生表按冻结方法重新拟合；`aggregate/` 主要用于复现核验和报告。

## 历史结果一致性

对已经接受的历史 aggregate 包：

```powershell
python scripts/canonical/compare_reproduction.py <analysis_id> `
  --expected <accepted_package> `
  --actual <new_stage>/producer_output `
  --report <new_stage>/reproduction_equivalence.json
```

离散/计数字段必须一致，浮点值使用预先声明容差。北京主机的正式 runtime verification 已完成；若某阶段是明确的 bug/语义 correction，则应核验修复后的科学口径和 runtime provenance，而不是强求与错误旧结果数值完全一致。

## 当前完成边界

代码层与北京本地 runtime 均已完成验收：历史 producer 恢复、统一 launcher、主链 stage graph、固定目录规范、运行 provenance、aggregate/merge-ready 分层、对方机器输入口、scientific-signature fail-closed collector，以及受修复影响阶段的最小正式重跑均已通过。

PR #3 已完成最终 Sol runtime acceptance 并合并至 `main`。当前 teammate-handoff 基线为 `main@4c106ba885d81c01ade881beb21b55e0618f5193`；同事应以该正式基线为起点，在其本机只配置私有路径和实际可用数据，不重新调参、改标签、改窗口、改 fold 或改模型。北京已验证结果不要求同事复现出相同数值，但可合并产物必须满足统一 schema、merge key 与 scientific signature。