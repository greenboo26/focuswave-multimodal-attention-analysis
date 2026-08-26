# AMD handoff requirements draft v1

这不是执行 runbook，也不授权建立 AMD 分支或开始批量分析。Sol 审查通过后，未来 AMD handoff 至少必须接收：

- 经过审查的 identity/session/cohort contract；
- `site + phase + program_family + block + probe_id` schema 和 Unix-ms 时间单位；
- participant-disjoint split、matched cohort、窗口、QC、seed、FDR/bootstrap 规则；
- 参数化 data/output roots、dry-run、input audit、run manifest 和 code/config digest；
- NVIDIA/AMD backend 对齐测试及明确的数值容差；
- local-only row-level/raw-data policy。

在 Sol approval 之前，AMD 只能保持未建立、未执行状态。
