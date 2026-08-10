# 08_算法/scripts — 分析脚本索引

数据在 `F:/预实验/sub-XXX_/`（预实验批次 000-007），输出统一到 `../output/`，按批次分目录：预实验 `预实验/09_预实验-*`、旧批次 `旧实验/08_旧批次-*`。

## 预实验分析主线（000-007，按执行顺序）

| 脚本 | 用途 | 用法 |
|------|------|------|
| `assess_preexp_quality.py` | 心跳质量独立评估（文献标准流程：SNR/IBI 窗级门控），输出 `预实验/09_预实验-SUB{XXX}-QUALITY/` | `python assess_preexp_quality.py --subject 004 --data-root F:/预实验` |
| `analyze_mmwave_full.py` | 全程窗特征 + 探针前 30s 特征 + 行为对应，输出 `预实验/09_预实验-SUB{XXX}-FULL/` | `python analyze_mmwave_full.py --subject 004 --data-root F:/预实验 --output-dir 预实验/09_预实验-SUB004-FULL` |
| `analyze_mmwave_hrv.py` | 休息段/全程 HRV 提取管线（analyze_mmwave_full 的底层依赖，也可独立跑 rest HRV） | 被 full 脚本 import；独立用见 docstring |
| `analyze_preexp_robustness.py` | 行为×毫米波相关稳健性检验（Pearson/Spearman/分 block/剔离群/Jackknife），输出 `预实验/09_预实验-ROBUST-ALL/` | `python analyze_preexp_robustness.py --data-root F:/预实验` |
| `compare_preexp_hrv.py` | 跨被试 HR/HRV/行为分布对比 + 可用率 + 探针标签，输出 `预实验/09_预实验-SUBJECTS-COMPARE/` | `python compare_preexp_hrv.py` |
| `gen_range_time_maps.py` | 全程距离-时间热图（8 被试 2×4 对比 + 单图），输出 `预实验/09_预实验-SUBJECTS-COMPARE/` | `python gen_range_time_maps.py --data-root F:/预实验` |

## 数据工具

| 脚本 | 用途 | 用法 |
|------|------|------|
| `truncate_preexp_data.py` | 截断 mmwave 数据（默认按行为实验结束 Block6，可自定义时刻），被截片移入 `mmwave_truncated_backup/` | `python truncate_preexp_data.py --subject 004 --data-root F:/预实验` |
| `rename_preexp_subject.py` | 修正采集时被试编号输入错误（文件名/meta/CSV 全量） | `python rename_preexp_subject.py --subject 005 --wrong-id 004 --data-root F:/预实验` |
| `tools/check_preexp_data.py` | 采集端到端完整性快检（分片/时间戳/行为文件） | `python tools/check_preexp_data.py --subject 004` |
| `tools/compare_all_datasets.py` | 跨数据集信号质量统一对比（诊断"信号差是算法还是环境"） | `python tools/compare_all_datasets.py` |

## 旧批次分析（8/1 采集 001/007/008/SXQ，可复现，不再主动更新）

| 脚本 | 用途 |
|------|------|
| `analyze_rest_3min.py` | 3 分钟静止 HR/BR/HRV 诊断（sub-rest_3min） |
| `analyze_deep_breath.py` | 深度呼吸 RSA 效应 + BR 标定 |
| `compare_4subjects.py` | 旧四被试（001/007/008/SXQ）探针特征对比 |

## 管线基础模块（被上述脚本 import，勿删除）

| 脚本 | 提供 |
|------|------|
| `process_vital_signs_v2.py` | 采样率/通道数常量、带通滤波（被 analyze_mmwave_hrv / analyze_rest_3min import） |
| `process_vital_signs_v3.py` | VMD 心跳分离 `separate_vmd_heart_only` |
| `process_vital_signs_v5.py` | 呼吸峰值检测 `detect_peaks_breath_robust` |
| `process_vital_signs_v9.py` | 谐波陷波 `suppress_harmonics` |

## 历史版本

已失效或迭代中废弃的脚本移入 `archive_历史版本/`（含旧管线 v1/v2_0-v2_4/v4/v6/v7/v8、v2_3/v2_4 清理存档、旧诊断图脚本等），可追溯不复用。
