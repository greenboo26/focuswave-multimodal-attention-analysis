# HR course corrected report sync

日期：2026-08-29

## 结论

现位文档中，`4.59/4.61 bpm` 不能再作为当前有效 HR-course 精度。当前 corrected 口径统一写作 `MAE=3.777 bpm（约 3.78 bpm）`；旧值仅保留为 historical old-gate calibration result。

## 已更新文件

- `D:\Project\厚粲杯\08_算法\docs\毫米波专注系统_运行手册.md`
- `D:\Project\厚粲杯\08_算法\docs\最终交付审计报告_100人目标.md`
- `D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\MMWAVE_FORMAL_VITAL_QC_V1.md`
- `D:\Project\厚粲杯\08_算法\work\issue15_formal_physiology_run_2026-08-27\issue15_Mainline_D_provenance_gate_freeze_2026-08-27.md`
- `D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\mmwave_reference_agreement_aggregate.csv`
- `D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\MMWAVE_ALGORITHM_AND_RANGE_GATE_AUDIT_V1.md`

## 处理方式

- 入口与审计正文：把现位 HR-course 数值改为 `3.777 bpm`，并保留旧门历史边界。
- 参考汇总 CSV：把 `HR_course` 的 MAE 更新为 `3.7770`.
- 算法/范围门控审计：保留历史表行，同时追加更正说明，避免继续把旧 `0.702` 解释为当前现值。

## 验证

- 已搜索并处理现位路径中的 `4.59 bpm` 与 `4.61 bpm` 表述。
- 已保留历史结果，不删除，只追加 caveat 或替换当前口径。

## 未更新风险

- `MMWAVE_ALGORITHM_AND_RANGE_GATE_AUDIT_V1.md` 仍保留历史表快照，适合追溯，不适合直接当作当前口径引用。
- 若后续要在更多 head-to-head 报告中显式写入 `target/channel 79/99` 与 `Pearson r=.605`，需要继续同步那些独立报告。


