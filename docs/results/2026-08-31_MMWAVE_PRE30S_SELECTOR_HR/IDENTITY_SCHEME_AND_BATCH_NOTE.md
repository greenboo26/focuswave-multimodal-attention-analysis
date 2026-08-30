# 身份编码体系与两盘批次说明（2026-08-31）

> 记录 mmWave merge-ready adapter 涉及的身份编码和 J/E 两盘批次划分，避免后续 agent 重复困惑。不是科学结论，是身份/数据组织说明。

## 1. 两套身份编码，用途不同

| 编码 | 格式样例 | 来源 | 覆盖 | 用途 |
|---|---|---|---|---|
| R 格式 | `R027` / `R047` | mother table（`analysis_tables_v1/subject_session_master.csv`，179 sessions / 112 组） | 179 场（含珠海） | **四个模态 merge-ready 表当前用的键**（`canonical_probe_timeline` 的 `repeat_participant_id`） |
| P 格式 | `P-001F33A876` | 问卷/重复登记核验（`participant_key`） | 116 场 | Behavior formal_v3 的 `participant_group_id`、`cohort_manifest.csv` 的 `repeat_participant_id` |

`formal_multimodal_v2.yaml` 声明的 canonical future key 是 `participant_group_id`（P 格式方向）；当前 merge-ready 表仍用 R 格式（历史 alias）。两套编码的统一迁移是"身份键审计"（Attention-Analysis `docs/060-formal-analysis/007`）中的待办，不是 mmWave 单独的事。

## 2. E 盘 session 的 R 格式映射链

`session_id_mapping.csv` 的 `session_id` 列只填了 72 个 J 盘 session（`resolved`），E 盘行 `session_id` 为空（`not_current_J_session`）——**但 R 格式仍在**，通过编号链可查：

```
sub-031 → background_subject_manifest.source_subject_raw = 031
       → single_experiment_id = 31（数值一致）
       → session_id_mapping.repeat_participant_id = R027 ✅
```

7 个抽检全部验证通过（sub-031→R027, sub-032→R026, sub-036→R031, sub-047→R042, sub-061→R053, sub-137→R102, sub-177→R118）。同一 R 对应多个 eid 是正常的重复访问，不是冲突。

## 3. 两盘批次划分（正式 cohort 116 场）

| 批次 | sessions | probe 窗口 | probe 时间来源 | mmWave 数据根 |
|---|---:|---:|---|---|
| J 盘（canonical 时间线） | 72（sub-056~sub-178） | 1440 | `canonical_probe_timeline.csv` | `J:\Data` |
| E 盘（44 场次迁移包） | 44（sub-031~sub-055, sub-061, sub-137~sub-177 等） | 880 | `probe_primary_30s.csv`（Behavior formal_v3，`probe_time_ms` 绝对 unix ms） | `E:\正式实验` |
| 合计 | 116 | 2320 | | |

E 盘版 adapter 的格式映射：`block_id` B1→block-1；`probe_id` 由 `probe_order_in_block` 生成 probe-01 格式；窗口时间 = `probe_time_ms - 30000 → probe_time_ms`；`window_effective_start` 不裁剪（probe 均位于 block 中段，跨 block 概率低，`window_crosses_block` 原值保留）。

## 4. 输出文件

| 文件 | 批次 | 位置 |
|---|---|---|
| `mmwave_probe_merge_ready.csv` | J 盘 72 sessions（1440 行） | `_FormalAnalysis/mmWave/` |
| `mmwave_probe_merge_ready_E.csv` | E 盘 44 sessions（880 行） | `_FormalAnalysis/mmWave/` |

两表列结构完全一致（timeline 33 列 + 22 mmwave 字段），R 格式一致，可直接按五键拼接为 116 场 2320 行。E 盘 5 个无效占位（sub-036/038/040/041 空 timestamps、sub-047 空目录）自动记 `STRUCTURAL_MISSING`。
