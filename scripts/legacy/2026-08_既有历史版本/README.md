# archive_历史版本 — 历史脚本归档

> 归档日期: 2026-08-10
> 归档说明: 历史迭代版本与一次性调试脚本。`process_vital_signs_v9.py` 与 `analyze_mmwave_hrv.py` 都是 `HISTORICAL_REFERENCE`，不是 current formal producer 或 runner；当前角色和资格边界以 `docs/research/MMWAVE_HR_BR_HRV_PROJECT_PIPELINE_MAP_2026-08-30.md` 与根目录 `PROJECT_STATUS.md` 为准。
> 注意: 部分脚本相互 import 依赖根目录模块,归档后不可直接运行,如需复现历史结果请将所需模块复制回 scripts/ 根目录。

## 内容

| 文件 | 说明 |
|------|------|
| `process_vital_signs_v1.py` | 最初版本(baseline bp) |
| `process_vital_signs_v2_0.py` ~ `v2_4_lite.py` | v2 系列中间迭代(一敏分析用) |
| `process_vital_signs_v4.py` | v4(vmd breath) |
| `process_vital_signs_v6.py` | v6 |
| `process_vital_signs_v7.py` | v7(小波) |
| `process_vital_signs_v8.py` | v8(EMD) |
| `check_data_quality_v5.py` | v5 批量质量检查(依赖已移除的 run_v5_case.py) |
| `check_bin_sliding_quality_v5.py` | bin 滑动窗口质量检查(一敏 v2_3/v2_4 判伪相关) |
| `_bin_compare.py` / `debug_bin_vs_part001.py` | 临时调试脚本 |
| `analyze_sxq_47min.py` / `compute_hrv.py` | SXQ 47min 分析（原 legacy/，被 analyze_mmwave_hrv.py 取代） |
| `analyze_angle_a43.py` / `compare_v9.py` | 角度探索与 v9 对比（原 exploration/） |
| `archive_2026-08-08_v23_v24_cleanup/` | 2026-08-08 归档的 v2_3/v2_4 判伪清理包 |

> 2026-08-10: legacy/ 与 exploration/ 已并入本目录。

