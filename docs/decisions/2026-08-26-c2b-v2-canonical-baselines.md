# C2b-v2 canonical feature reconstruction and window completion

## Local evidence and re-entry points

- Runner: `D:\Project\厚粲杯\08_算法\scripts\run_c2b_v2_canonical_reconstruction.py`
- C2a source: `D:\Project\厚粲杯\08_算法\output\40_正式实验\04_C2a_标签与样本单元审计\derived_20260826\c2a_sample_manifest.csv`
- Raw mmWave source: `J:\Data`
- Local derived output: `D:\Project\厚粲杯\11_数据\derived\c2b_v2_canonical_baselines_20260826`
- Legacy matrix audited but not row-joined: `D:\Project\厚粲杯\11_数据\derived\j_m1_q0_71_rerun_v1\m1_q0_probe_matrix.csv`
- Local row-level matrices and OOF predictions remain outside GitHub.

状态：`C2B_V2_CANONICAL_BASELINES_COMPLETE`

本轮只使用正式行为时间轴和 J:\Data 毫米波数据；未读取 RGB/NIR，未计算 IBI/RMSSD/SDNN，未修改原始数据。30 s 为预先冻结的主窗口，10 s/60 s 为敏感性分析。

## 样本与 provenance 对账

- C2a 母表：1440 probes，72 sessions，46 group_subject_id。标签 1/2/3/4 = {1: 1064, 2: 240, 4: 85, 3: 51}。
- 1,420：C2a 中可由当前时间戳字段支持的完整时间覆盖；20 个缺失集中在 sub-067。
- 1,317：旧 M1/Q0 矩阵的独立行数，来源为旧 1,297 行 + sub099 20 行。旧矩阵没有当前 C2a 的绝对 probe onset，且 probe_id 命名空间不同，因此本轮没有伪造逐行 join。
- 1,278：只出现在旧 C2a 报告正文，当前 manifest、coverage CSV 和脚本无法复现；本轮标记为 `unreproducible_legacy_claim`，不作为毫米波有效样本数。

## 窗口级真实毫米波提取

| 窗口 | canonical 母表 | raw extractor 输出行 | q_extraction_ok | 说明 |
|---:|---:|---:|---:|---|
| 10 | 1440 | 1420 | 980 | sub-067 无毫米波文件；10 s 另有实际时间长度不足的窗口 |
| 30 | 1440 | 1420 | 1420 | sub-067 无毫米波文件 |
| 60 | 1440 | 1420 | 1420 | sub-067 无毫米波文件 |

## 特征与模型命名

- `C` = context only；`B` = behavior signal only；`W_basic/W_extended` = 不含 context 的毫米波特征；`C+B`、`C+W`、`C+B+W` 按字面组合。
- 行级 feature matrix 使用 probe 前窗口 `[probe_onset-duration, probe_onset)`；行为特征没有使用 probe 之后数据。
- 中位数填补仅发生在每个训练 fold 内；整行没有有效毫米波提取的 probe 没有进入 W 模型，不能被填补成毫米波样本。

## 30 s 主窗口 logistic 结果

| feature set | n | groups | ROC-AUC | PR-AUC | balanced accuracy |
|---|---:|---:|---:|---:|---:|
| C | 1440 | 46 | 0.596 | 0.341 | 0.575 |
| B | 1440 | 46 | 0.654 | 0.372 | 0.628 |
| W_basic | 1420 | 46 | 0.482 | 0.267 | 0.483 |
| W_extended | 1420 | 46 | 0.534 | 0.289 | 0.528 |
| C+B | 1440 | 46 | 0.687 | 0.396 | 0.640 |
| C+W_basic | 1420 | 46 | 0.544 | 0.305 | 0.533 |
| C+W_extended | 1420 | 46 | 0.553 | 0.306 | 0.538 |
| C+B+W | 1420 | 46 | 0.646 | 0.375 | 0.619 |

## 30 s strict matched cohort

以下才是行为与毫米波在同一批 probe 上的直接比较；full-cohort 的 C+B 数值不与 1,420 行 fusion 数值直接横比。

| feature set | n | groups | ROC-AUC | PR-AUC | balanced accuracy |
|---|---:|---:|---:|---:|---:|
| C+B | 1420 | 46 | 0.686 | 0.399 | 0.639 |
| C+B+W | 1420 | 46 | 0.646 | 0.375 | 0.619 |

## 预设窗口敏感性（logistic）

| window | C+B AUC | C+B+W AUC | W_extended AUC | W 有效 probe |
|---:|---:|---:|---:|---:|
| 10 | 0.638 | 0.603 | 0.553 | 980 |
| 30 | 0.687 | 0.646 | 0.534 | 1420 |
| 60 | 0.696 | 0.657 | 0.554 | 1420 |

## 预设 matched 增量比较

30 s 的 `C+B` vs `C+B+W` paired group bootstrap：ΔAUC 约 −.040，95% CI 约 [−.074, −.003]；融合预测的组均值分数高于行为基线的 group 数为 22/46。该结果表示在本轮 canonical 特征和当前低复杂度模型下，没有观察到毫米波在行为之外的增量。它不等同于宣称毫米波在所有表示或所有任务中无效。

## 限制

1. 旧 1,317 矩阵与当前 1,440 C2a 母表没有可审计的绝对 onset 逐行键，本轮不把两者强行拼接。
2. 10 s 的许多原始时间段实际时长不足预设门槛，因此只有 980 个窗口进入 W 模型；这不是缺失值填补造成的。
3. 这轮沿用现有无标签 phase/motion/QC 特征，没有重新开发毫米波生理算法；HRV/IBI 不在 C2 核心。
4. 本报告不自动触发 RGB/NIR 或复杂模型阶段。
