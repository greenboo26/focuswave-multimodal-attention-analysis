# C3A NIR 既有正式结果复用任务

状态：`READY_TO_RUN`

本地正式 NIR 工程/结果入口：

`D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR`

## 目标

NIR 不从原始视频重新开始。先盘点并复用上述正式 NIR 工程已经产生的结果、模型输出、帧级/窗口级派生数据、QC、时间戳和运行状态，再决定为了注意状态预测还缺哪些派生特征。

## 已知可复用下游资产

- `D:\Project\厚粲杯\11_数据\derived\c3_nir_qc_integration_v1\nir_probe_aligned.csv`
- `D:\Project\厚粲杯\11_数据\derived\c3_identity_coverage_crosswalk_v1\identity_crosswalk.csv`
- `D:\Project\厚粲杯\11_数据\derived\beijing_sensor_increment_v1\`
- `D:\Project\厚粲杯\11_数据\derived\nir_directionality_audit_v1\`

既有第一版结果已经表明：NIR identity resolved 约 320 probes / 16 sessions / 14 repeat participants；NIR QC>=80% 约 246 probes / 15 sessions / 13 repeat participants；第一版低复杂度 NIR 增量未显示正向提升。AUC<0.5 已排除简单标签翻转/概率列取错，不再重复审计。

## 第一阶段：盘点正式 NIR 工程，不重跑

只读检查 `01_Attention-Analysis_nvidia-cuda_formal_NIR`，记录：

- 当前正式处理 pipeline 入口脚本；
- 已处理被试/session；
- 每个 session 的 completion/status；
- 已保存的帧级、时间序列级、窗口级、session 级结果；
- HbO/HbR 或等价 NIR 生理表征的实际字段；
- ROI/通道/左右侧信息；
- 原始时间戳、绝对时间锚点和采样率；
- QC/coverage/failure reason；
- 是否已存在 baseline correction、detrend、filter、tonic/phasic 或动态特征；
- 哪些结果已经被 `nir_probe_aligned.csv` 使用，哪些有信息但尚未接入 probe 分析。

先生成一个简洁的 NIR asset manifest。不得因为不理解目录结构而重新处理原始视频。

## 第二阶段：利用已有结果构造更贴合注意状态的特征

如果现有正式输出足够，直接从现有派生时间序列构造 probe 前特征。优先 30s 主窗口，10s/60s 为固定敏感性分析。

优先考虑：

- participant/session 内相对基线变化；
- probe 前 HbO/HbR 均值相对个人基线的 delta；
- robust-z；
- probe 前斜率；
- 短期波动/标准差；
- tonic level 与 phasic change；
- 左右/ROI 差异（仅当现有 ROI 定义可靠）；
- 相对于实验前静息或同 session 合理基线的变化。

不得根据显著性无限扩展特征。

如果现有正式输出缺少完成这些分析所需的时间分辨率，才回到更上游的既有派生文件；只有在确认上游也不存在所需信息时，才允许重跑缺失 session/缺失阶段，而不是全量重跑 NIR 原始数据。

## 第三阶段：增量评价

严格使用同 probe cohort、同 repeat-participant-disjoint folds，至少比较：

- `C+B`
- `C+B+NIR_existing`
- `C+B+NIR_within_dynamic`

可补：

- `NIR_existing`
- `NIR_within_dynamic`

主裁决：

`ΔAUC = C+B+NIR_within_dynamic - C+B`

报告 ROC-AUC、PR-AUC、balanced accuracy、coverage、participant/group bootstrap 95% CI。

## 与 D1 的关系

C3A 先在现有北京 canonical 上执行，不等待 D1。D1 完成后，如果珠海 NIR 有同构正式输出，再将已经冻结的 NIR 特征定义用于珠海跨站点验证，不重新根据珠海结果改特征。

## 输出

GitHub 只提交脚本、字段说明、聚合结果、图和结论；被试级/帧级数据保持本地。

至少输出：

- `nir_formal_asset_manifest.md/csv`
- `nir_dynamic_feature_definition.md`
- `nir_dynamic_model_comparison.csv`
- `C3A_NIR_WITHIN_PERSON_DYNAMIC_RESULT.md`
- 1–2 张报告级图

完成后报告：实际可用 session/participant/probe、现有输出具体包含什么、是否需要任何上游重跑、existing vs within-dynamic 的 AUC/ΔAUC/CI、branch 和 commit SHA。
