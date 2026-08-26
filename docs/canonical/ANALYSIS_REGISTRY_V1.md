# Analysis registry v1

状态枚举严格使用：`CANONICAL_FINAL`、`VALID_SUPPORTING`、`PENDING_CANONICAL_RERUN`、`SUPERSEDED_INTERMEDIATE`、`ENGINEERING_ONLY`、`PLANNED_GLOBAL_ONLY`、`BLOCKED_EXTERNAL_STORAGE`。完整机器可读表见同目录 CSV。

本轮没有新的探索性科学分析。CSV 的每一行对应一个保留的实际分析或正式计划阶段，包含输入、输出、入口、RUN_ID、样本单位、cohort、身份键、site/protocol 和跨机器复现要求。`exact_executable_script` 若标为历史 worktree 或 `not yet stable`，即为复现审计发现，不是可执行承诺。

## Status counts

| status | count |
|---|---:|
| `VALID_SUPPORTING` | 14 |
| `PENDING_CANONICAL_RERUN` | 3 |
| `BLOCKED_EXTERNAL_STORAGE` | 1 |
| `ENGINEERING_ONLY` | 6 |
| `PLANNED_GLOBAL_ONLY` | 5 |
| `CANONICAL_FINAL` | 0 |
| `SUPERSEDED_INTERMEDIATE` | 0 |
| total | 29 |

没有任何条目被提升为 `CANONICAL_FINAL`，因为 Sol 尚未审查，且最终多模态/跨站点分析尚未形成共同冻结入口。

## Interpretation rules

- `subject + probe_id` 是当前 Probe 级连接键；NIR 时间对齐使用绝对 Unix milliseconds，时间戳不是身份键。
- `repeat_participant_id` 只用于 participant-disjoint grouping 和重复测量，不能从目录名推断。
- Beijing B1+B2 是 shared primary；Zhuhai B3 仅 extension，直到全局 cohort gate 通过。
- labels 2/3/4 保留四分类层，不统称为 mind-wandering。
- C1/HRV、最终 NIR/RGB 增量、多模态融合与跨站点验证不得从工程状态推断科学完成。
