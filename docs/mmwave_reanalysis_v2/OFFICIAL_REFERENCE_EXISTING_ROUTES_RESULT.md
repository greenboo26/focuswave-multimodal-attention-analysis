# AgeBalanced 官方 ECG reference：既有毫米波路线公平重测

Status: `PASS_DEVELOPMENT_ONLY`

执行范围：仅使用 AgeBalanced development 30 participants / 60 Rest sessions；未读取 held-out 80、`J:\Data`，未做 HRV、参数调优或新算法搜索。

## 官方 reference

本轮所有 AgeBalanced HR 分数均改用官方 Rest ECG FFT 定义：256 Hz 原始 ECG，四阶 Butterworth 0.8–2.0 Hz、`filtfilt`，逐窗口 FFT，去 DC，取正频率半谱最大幅值并转换为 BPM；不使用峰检测、IBI、窗函数、插值或 `ecg_reference_v1`。来源为 Zenodo 16760684 `ExampleCode.ipynb`，MD5 `204768fa033176b12baae016ccef19b1`。

## 核心比较

| route | dataset/input semantics | window | sessions | scored windows | ECG reference | pooled MAE | median(session MAE) | coverage | comparable? | notes |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| historical AgeBalanced route / `f4a8c74` | AgeBalanced derived complex range-FFT, 10 Hz | 25 s / 5 s | 60 | 328 | Official FFT | 10.493 | 9.296 | 100% | Yes, historical diagnostic | Issue #9 official rerun；历史约9–10 BPM成立 |
| current project route | 同上 | 30 s / 5 s | 60 | 268 | Official FFT | 10.361 | 8.575 | 100% | Yes | 当前30 s product-window route；与25 s不是同一窗口 |
| project route | 同上 | 50 s / 5 s | 60 | 88 | Official FFT | 9.292 | 7.813 | 100% | Yes, method-native | Task2R project route；不是30 s产品claim |
| SSA+VMD adapted | 同上 | 50 s / 5 s | 60 | 88 | Official FFT | 9.012 | 5.253 | 100% | Yes, same-condition | 已有Task2R路线；paper reimplementation/adapted，不是官方复现 |
| project route | 同上 | 60 s / 5 s | 14 complete sessions | 14 | Official FFT | 8.273 | 6.517 | 100% of attempted | Limited | 60/60 session中仅14个有完整60 s，不能与30/50 s等权解释 |
| Lei SSA adapted | 同上 | 60 s / 5 s | 14 complete sessions | 14 | Official FFT | 8.670 | 7.450 | 100% of attempted | Limited | Task2S；同一小样本上MAE劣于项目路线 |

`coverage` 的分母是该路线实际产生且通过 radar input gate 的窗口；官方 FFT reference 对这些窗口均返回值。60 s 行的 session 数下降来自输入时长，不是静默插值或 ECG reference 排除。

## 旧数字纠正

下列数字不再用于 AgeBalanced HR 性能判断：

- 30 s project route：`26.983 BPM` → 官方 FFT **10.361 BPM**。
- 50 s project route：`29.02 BPM` → 官方 FFT **9.292 BPM**。
- 50 s SSA+VMD adapted：`28.12 BPM` → 官方 FFT **9.012 BPM**。
- Task2S 60 s project route：`37.1163 BPM` → 官方 FFT **8.273 BPM**。
- Task2S 60 s Lei SSA route：`38.0582 BPM` → 官方 FFT **8.670 BPM**。

这些旧数字不是毫米波信号突然恶化的证据，而是把 `ecg_reference_v1` 的内部 ECG/QC 处理误当成 AgeBalanced 官方 benchmark ground truth。它们仍可作为历史 reference-sensitivity 记录，但应标记为 `SUPERSEDED_FOR_AGEBALANCED_HR_PERFORMANCE`。RS6240 原始 IQ、正式 `J:\Data` 或本地 BIOPAC 结果不在本表内，不能套用 AgeBalanced 官方 ECG。

## 方法盘点与结论

本轮真正重测的既有路线是：`f4a8c74` 历史/项目路线的 30、50、60 s 输入；Task2R 已运行的 SSA+VMD adapted；Task2S 已运行的 Lei SSA adapted。v1–v8、CEEMDAN、CFAR、SPC/Hampel、VitalSense 和 RS6240 正式路线没有被重新纳入：它们要么没有同一 AgeBalanced derived-input、同一冻结窗口和可恢复输出，要么属于不同设备/输入语义或不是当前 HR 公平比较路线。

在正确官方标准下，历史约 9–10 BPM 确实成立，且当前项目路线在30 s为10.361 BPM。50 s SSA+VMD 的 pooled MAE 比项目路线低0.280 BPM，但 RMSE 为14.157 vs 11.410、极端误差为7 vs 0，并出现1个 two-times lock；median session MAE 虽更低，不能称为稳定、全面改善。60 s Lei SSA 在14个完整 session上也未优于同条件项目路线。现有证据不支持继续进行新的生理算法优化或进入80人。

当前最值得保留的是 **现有 project route + 官方 AgeBalanced ECG reference**：它在30 s产品时间尺度上已有可解释的约10.36 BPM development结果，规则和历史 lineage清楚，避免把 reference错误带入后续结论。毫米波仍可保留为 signal/quality/motion supporting modality；本轮没有发现一个已有算法在公平官方 reference下表现出明确、稳定且足以授权新开发的改进点。

## 可追溯产物

- runner：`scripts/mmwave_reanalysis_v2/run_official_reference_existing_routes_v1.py`
- machine result：`D:\Project\厚粲杯\11_数据\derived\mmwave_reanalysis_v2_issue10_official_ecg_existing_routes_20260827\issue10_result.json`
- row-level local audit：`D:\Project\厚粲杯\11_数据\derived\mmwave_reanalysis_v2_issue10_official_ecg_existing_routes_20260827_rows.jsonl`
- official reference implementation：`scripts/mmwave_reanalysis_v2/run_benchmark_decomposition_issue9.py::official_agebalanced_ecg_hr_bpm`
- radar implementations：历史 baseline、Task2R、Task2S 原有 runner；本轮没有改动其算法参数。
- config hash：`68ba7c83b027799552c6211bc6dc028a7bf96c4c5594e5f23f99b0a5ef3d6290`
- `issue10_result.json` SHA-256：`376806e2a4c4d04359faa2dafb040fcdd0c1daa915b128fa084e369640910a2d`
- local rows JSONL SHA-256：`ad4da6c2d28af8488240e5875902bc44914b1453bb93696f4c1ca1afa43911a3`

本轮完成后停止；任何进一步毫米波任务必须重新明确授权。
