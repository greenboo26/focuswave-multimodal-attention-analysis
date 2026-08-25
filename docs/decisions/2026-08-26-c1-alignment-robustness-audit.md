# C1 alignment robustness audit

Status: `C1_ALIGNMENT_ASSUMPTION_INVALID_REOPEN_HRV`

本审计只读取 C1c replay 与 C1d backend 已保存的 ECG/radar beat timestamps；没有读取 raw ADC，没有修改前端、VMD、峰检测或使用 ECG 调参。delay 符号与冻结 evaluator 一致：adjusted radar = radar - delay_ms/1000。

## Primary ±75 ms

| method | mean fixed F1 | mean optimal-lag F1 | mean gain | sessions gain >= .10 | mean fixed recall | mean optimal recall | mean optimal delay |
|---|---:|---:|---:|---:|---:|---:|---:|
| c1c_local_peak | 0.248 | 0.353 | 0.105 | 1/3 | 0.200 | 0.286 | -45.0 ms |
| c1d_radarbeat_global_dp | 0.197 | 0.370 | 0.173 | 3/3 | 0.170 | 0.322 | 70.0 ms |

## Interpretation boundary

- Lag sweep is diagnostic only, not a formal performance result.
- C1b baseline timestamp assets were not saved in the C1c replay package; they were not regenerated because this audit forbids raw/front-end recomputation.
- IBI fields are reported using the same evaluator and matched-beat rule; changing lag can change the matched subset, so they are not interpreted as an invariant full-sequence IBI test.
- The final status applies to the two available frozen timestamp methods only; the unavailable C1b methods are explicitly listed in `c1_alignment_unavailable_methods.csv`.