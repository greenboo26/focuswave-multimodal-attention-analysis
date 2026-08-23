# 毫米波专注状态研究系统

当前版本是可复现的研究原型，不是临床设备，也不是已经通过部署验证的专注分类器。

## 系统输出

- 心率（HR）：优先输出，可进行范围、峰数和时频一致性检查。
- 呼吸率（BR）：输出但必须结合质量标记解释。
- 心率变异性（HRV）：短窗 RMSSD 仅作探索性指标。
- 专注状态：只输出研究性概率；质量不足或概率不明确时输出 `indeterminate`（不可判定）。

## 对单个处理后 NPZ 文件运行

```powershell
.venv\Scripts\python.exe scripts\run_focus_runtime_batch.py `
  output\E_Data_FAST\sub-124_\sub-124_ses-SART_mmwave_vital_signs.npz `
  output\demo_runtime `
  --windows-csv output\E_Data_FAST\focus_discrimination.csv
```

程序会生成同名 `.json` 和 `.csv`。输入也可以是包含多个处理后 NPZ 文件的目录。每个窗口分别输出 `heart_rate_quality`、`breath_quality`、`hr_calculable`、`br_calculable` 和 `hrv_calculable`，不能把心率可算误读为呼吸率或 HRV 已验证。

如果已有行为探针时间清单，必须把它作为窗口来源传入，程序只会计算清单中的行为对齐窗口，避免把实验开始、结束、练习或休息段混入：

```powershell
.venv\Scripts\python.exe scripts\run_focus_runtime_batch.py `
  output\E_Data_FAST\sub-056_\sub-056_ses-SART_mmwave_vital_signs.npz `
  output\demo_behavior_gated_runtime `
  --windows-csv output\E_Data_FAST\focus_discrimination.csv
```

`--windows-csv` 至少需要 `subject` 和 `onset_rel_s` 字段；输出中的 `onset_rel_s` 是行为定义的 60 秒窗口结束时间。

若只是检查整段 NPZ 的算法行为，必须显式加入 `--allow-ungated-timeline`；该模式不用于正式分析，因为可能包含实验前后、练习或休息记录。

单文件入口默认关闭 HRV 专注评分，只输出质量和生理指标；只有明确加入 `--allow-experimental-hrv` 才会输出研究性专注概率。该概率不用于诊断或部署。

## 个体化研究校准

如果某个被试已经有带行为标签的探针窗口，可以先拟合该被试的研究性校准模型，再把模型传给批量入口：

```powershell
.venv\Scripts\python.exe scripts\fit_personalized_calibration.py 056 output\personal_model_056.json
.venv\Scripts\python.exe scripts\run_focus_runtime_batch.py input.npz output\personal_runtime `
  --model output\personal_model_056.json
```

该校准必须使用独立的后续探针做验证，不能把训练探针上的准确率当作泛化性能。

## 行为辅助多模态模式

如果部署场景同时允许读取 SART 前 60 秒行为统计，可以显式运行行为辅助模式。它使用正确率、误答率、漏答率和反应时统计，不使用当前探针标签；输出只能解释为“毫米波 + 行为辅助多模态”，不能作为纯毫米波性能：

```powershell
.venv\Scripts\python.exe scripts\personalized_temporal_runtime.py `
  --mmwave output\E_Data_FAST\focus_discrimination_augmented.csv `
  --crossmodal output\E_Data_FAST\crossmodal_features_all.csv `
  --behavior output\E_Data_FAST\behavior_probe_windows.csv `
  --behavior-assisted --expanded-vitals `
  --output output\E_Data_FAST\personalized_temporal_runtime_behavior.json
```

该模式仍然采用前半段校准、后半段独立测试；缺少足够校准标签时输出 `indeterminate`（不可判定）。

## 复核与验证

新增被试后可用以下命令更新全流程；如果只想复用已有生命体征结果，可加 `--skip-extraction`：

```powershell
.venv\Scripts\python.exe scripts\update_focuswave_pipeline.py --skip-extraction
```

该流程还会重建 `11_数据` 中 AgeBalanced 外部生命体征审计（440 个会话、110 名参与者），并在最后执行发布一致性检查。若只想复用已有外部审计结果，可加 `--skip-external`；若只更新行为分析而不重跑外部层，可使用：

```powershell
.venv\Scripts\python.exe scripts\update_focuswave_pipeline.py --skip-extraction --skip-rich --skip-external
```

原始相位微动特征审计需要重新读取 `E:\Data` 的原始距离立方体，耗时较长，使用 `--raw-motion` 显式开启。当前审计结果见 `output/E_Data_FAST/raw_motion_features_lopo.json`，仅用于研究性比较。

跨模态代理特征提取使用带 OpenCV 的实验 Python，且只读取行为门控后的探针窗口：

```powershell
python scripts\batch_extract_crossmodal.py --probe-csv output\E_Data_FAST\behavior_probe_windows.csv --output output\E_Data_FAST\crossmodal_features_all.csv --stride 300
.venv\Scripts\python.exe scripts\evaluate_crossmodal_fusion.py --mmwave output\E_Data_FAST\focus_discrimination.csv --crossmodal output\E_Data_FAST\crossmodal_features_all.csv --output output\E_Data_FAST\crossmodal_fusion_lopo.json
```

- [E_Data_FAST/final_summary.json](output/E_Data_FAST/final_summary.json)：71 名有效被试的总体结果。
- [E_Data_FAST/focus_lopo.json](output/E_Data_FAST/focus_lopo.json)：行为标签的被试留一验证。
- [E_Data_FAST/runtime_focus_system_eval.json](output/E_Data_FAST/runtime_focus_system_eval.json)：运行时质量门控审计。
- [E_Data_FAST/rich_focus_features_lopo.json](output/E_Data_FAST/rich_focus_features_lopo.json)：丰富特征模型审计。
- [E_Data_FAST/personalized_temporal_lopo.json](output/E_Data_FAST/personalized_temporal_lopo.json)：按时间顺序的个体校准审计。
- [E_Data_FAST/label_coverage_audit.json](output/E_Data_FAST/label_coverage_audit.json)：校准段和测试段的标签覆盖审计。
- [系统验证报告](output/系统验证报告_20260821.md)：数据来源、ECG 对照、手册对应关系和限制。
- [100 人目标采集与验收清单](数据采集与验收清单_100人目标.md)：后续被试的探针配额、时间戳和质量门槛。
- [100 人目标自动验收审计](output/E_Data_FAST/target_100_audit.json)：逐被试检查前后时间段的专注/走神标签覆盖和有效窗口。
- [发布验收结果](output/E_Data_FAST/release_verification.json)：检查数据覆盖、关键产物和脚本可编译性。
- [三层数据源清单](output/E_Data_FAST/source_inventory_final.json)：区分主验证集、正式实验和 ECG/RSP 多源对照层。
- [需求—证据追踪矩阵](需求-证据追踪矩阵.md)：逐项对应申请书目标、程序数据、手册边界和当前证据。
- [项目级完成审计](output/E_Data_FAST/project_completion_audit.json)：逐项区分已实现、部分可用、探索性和未完成要求。
- [系统模式策略](output/E_Data_FAST/system_mode_policy.json)：区分生理质量模式、个体化毫米波模式、行为辅助多模态模式和视觉探索模式。
- [来源覆盖审计](output/E_Data_FAST/source_evidence_audit.json)：核对 E:\Data、正式实验、ECG/RSP 参照、FocusWave 程序包、11_数据、03_文献和申请书均已进入证据链，并保留协议边界。
- [SART 行为效标审计](output/E_Data_FAST/behavior_outcome_audit.json)：将 trial 级正确率、误答、漏答和反应时对齐到探针，作为外部效标，不作为当前毫米波模型输入。
- [行为监督毫米波审计](output/E_Data_FAST/behavior_supervised_lopo.json)：以行为正确率下降为目标，检验毫米波是否能复现客观任务表现。
- [毫米波—行为效标分析](output/E_Data_FAST/mmwave_behavior_criterion.json)：检验毫米波特征是否能复现客观 SART 表现。
- [毫米波—行为融合审计](output/E_Data_FAST/mmwave_behavior_fusion_lopo.json)：比较毫米波、行为效标及其融合的跨被试结果；行为变量仅用于研究性效标对照，不进入毫米波运行时模型。
- [RGB/NIR/毫米波时间门控审计](output/E_Data_FAST/crossmodal_time_gate.json)：严格按 SART 行为区间排除练习、休息、实验前后记录。
- [跨模态窗口特征](output/E_Data_FAST/crossmodal_features_all.csv)：已提取时间门控后的 RGB 运动/亮度与 NIR 暗核心/眼部对比度代理；这些不是校准瞳孔直径或人脸关键点。
- [跨模态融合审计](output/E_Data_FAST/crossmodal_fusion_lopo.json)：视觉代理、毫米波和融合模型的被试留一验证。
- [跨模态个体校准审计](output/E_Data_FAST/crossmodal_temporal_lopo.json)：前半段只用于被试基线校准，后半段按时间顺序独立测试。
- [跨模态个体内审计](output/E_Data_FAST/crossmodal_within_subject_lopo.json)：同一被试留一窗口验证，结果仅支持个体化研究提示，不支持跨被试泛化。
- [个体化时间运行原型](output/E_Data_FAST/personalized_temporal_runtime.json)：前半段按被试拟合，后半段独立评分；校准标签不足时严格输出不可判定。
- [增强生理窗口特征](output/E_Data_FAST/focus_discrimination_augmented.csv)：在原有 HRV 特征外加入呼吸率、心率时频差、信号置信度和 10 秒信号波动。
- [增强特征留一审计](output/E_Data_FAST/augmented_vitals_lopo.json)：验证呼吸率和信号质量特征对专注标签与行为效标的增益。
- [增强特征个体化运行结果](output/E_Data_FAST/personalized_temporal_runtime_expanded.json)：前半段校准、后半段评分的增强版原型。
- [可导出的个体化逐窗评分结果](output/E_Data_FAST/personalized_scores_validated_behavior.json)：使用被试校准模型逐窗输出研究性专注概率、质量原因和不可判定状态。
- [行为辅助个体化运行结果](output/E_Data_FAST/personalized_temporal_runtime_behavior.json)：在增强毫米波模式上加入探针前 60 秒 SART 行为指标；这是行为辅助多模态结果，不是纯毫米波性能。
- [增强视觉特征审计](output/E_Data_FAST/augmented_vitals_enhanced_visual_lopo.json)：加入 RGB 人脸框和 NIR 瞳孔几何代理的独立对照，当前不作为默认输入。
- [行为时间门控运行示例](output/E_Data_FAST/demo_behavior_gated_runtime.json)：验证运行入口只处理行为清单中的窗口。
- [全量行为时间门控运行结果](output/E_Data_FAST/behavior_gated_runtime_all.json)：71 名有效被试、1,271 个行为窗口的端到端运行结果。
- [ECG/RSP呼吸率方法比较](output/ACQ_reference_20260821/breath_method_comparison.json)：100 个同步窗口比较峰间隔与呼吸频谱主峰方法。
- [ACQ 独立生理参照验证报告](output/ACQ_reference_20260821/ACQ_reference_validation_20260822.md)：5 名被试、100 个严格行为门控窗口，包含 ECG/RSP 对照图表、HR/BR/HRV 可用性判定。
- [ACQ 独立验证汇总](output/ACQ_reference_20260821/acq_reference_validation_summary.json)：毫米波 HR 课程估计、呼吸率和短窗 HRV 的误差统计。
- [ACQ 独立验证图](output/ACQ_reference_20260821/acq_reference_validation_scatter.png)：ECG/RSP 与毫米波逐窗散点对照。
- `D:\acq_mmwave_results`：BIOPAC ECG/RSP + 毫米波同步采集层；`.acq` 通道由 `bioread` 解析，行为 block 时间戳用于严格门控。
- `D:\正式实验`：正式实验第一批 6 名被试的毫米波、RGB/NIR 与行为数据；当前没有同步 ECG/RSP，因此作为行为与跨模态验证层，不冒充生理金标准。
- `D:\Project\厚粲杯\11_数据\外部数据集_AgeBalanced_60GHz`：110 名参与者的 60 GHz 雷达 + ECG 外部生命体征验证层，不含专注标签。
- [外部 AgeBalanced 心率审计](output/External_AgeBalanced/summary.json)：440 个会话的独立基线结果。

## 当前边界

71 名有效被试的心率可提取，但呼吸率和毫米波 HRV 的可靠性不足；多种丰富特征的跨被试 AUC 仍接近随机。探索性个体内验证表现较好，但只覆盖同时具有两类行为标签的被试，尚不能作为泛化证据。因此系统目前最适合作为“生理状态质量监测 + 个体化研究性专注评分”工具，不能把输出解释为确定的个体专注诊断。
### 当前默认生理特征模式

个体化运行时默认使用经过 ECG/RSP 对照后保留的心率和信号质量特征。毫米波 RMSSD/SDNN 仅能通过 `--physiology-profile legacy_hrv` 显式启用为探索性特征，不进入默认专注判定。行为辅助模式使用探针前 60 秒行为指标，结果不代表纯毫米波性能。

运行时可以用 `--model-dir` 导出每名被试前半段校准模型，再用 `scripts/score_personalized_models.py` 对新的行为时间门控窗口逐窗评分。缺少校准模型、质量门控失败或特征缺失时，系统输出 `indeterminate`，不强行给出专注标签。
