# FORMAL extreme-range target audit

状态：PARTIAL（只读前端诊断；classification 是保守的 session-level 可见证据标签，不是新的 QC gate）。

## Scope and prohibitions

本审查锁定 B1 已交付的 71-session corrected-distance 表：全部 16 个 corrected distance <0.30 m、全部 18 个 >1.50 m，并从 0.30–0.60 m 的 32 个 session 按 session ID 排序后等距固定抽取 9 个 reference。没有重新选择 target、没有改变 gate、没有重跑 HR/BR、没有运行 corrected-gate comparison、没有训练分类器、没有做 HRV，也没有读取 NIR/RGB。

距离统一按 `distance_m = bin × 0.037`。expected human range unavailable：当前核验到的 formal 文件中没有可作为 session-level 雷达—人体摆位 ground truth 的记录，因此未在图中补画人体预期位置。

## Locked sample

- near group: 16 sessions; far group: 18 sessions; reference: 9 sessions.
- reference IDs: 056, 076, 086, 094, 104, 109, 125, 139, 175.
- reference rule: sorted session ID, nine rounded equally spaced indices over the full 32-session 0.30–0.60 m list; see `FORMAL_EXTREME_RANGE_REFERENCE_SAMPLE.csv`.

## Historical target and existing QC fields

每个 sample session 的 `heart_bin/heart_ch` 与 `breath_bin/breath_ch` 从既有 v3.1.1 formal JSON 的 `bins`/`channels` 原样读取；本诊断不使用图形结果覆盖它们。B1 的 corrected distance 仍由其锁定表给出；其 `hr_quality_mode`、`br_quality_mode`、`usable_ratio`、`below_threshold_ratio` 与 `channel_amplitude_cv_median` 原样引用。

## Front-end diagnostic

每个图包含：(1) 全部通道幅值的多通道均值 range profile；(2) existing DataCube 的 range-time 诊断热图；(3) 0.20、0.30、0.60、1.50 m 参考线；(4) historical heart/breath target 标记。图中的时间块是为展示全场稳定性而对既有 NPZ 分块做的诊断性聚合，不是 BR pipeline 的 temporal tracking。

## Conservative target classification counts

- NEAR_LT_0.30 (n=16): heart — AMBIGUOUS=14; LIKELY_HUMAN=2; breath — AMBIGUOUS=15; LIKELY_HUMAN=1.
- FAR_GT_1.50 (n=18): heart — AMBIGUOUS=18; breath — AMBIGUOUS=17; LIKELY_HUMAN=1.
- REFERENCE_0.30_0.60 (n=9): heart — AMBIGUOUS=9; breath — AMBIGUOUS=9.

标签只允许 `LIKELY_HUMAN`、`LIKELY_NEAR_FIELD_OR_DIRECT_LEAKAGE`、`LIKELY_FIXED_ENVIRONMENT_REFLECTION`、`AMBIGUOUS`。near/fixed 标签要求异常距离位置与持续的 profile/heatmap 模式同时出现；没有达到保守条件就保留 `AMBIGUOUS`。`LIKELY_HUMAN` 仅表示可见的稳定且有峰位离散/微动的形态更接近人体候选，不能替代摆位 ground truth。每个 heart 与 breath 独立分类，不强行合并。

## Descriptive comparison

`FORMAL_EXTREME_RANGE_TARGET_DIAGNOSTIC_METRICS.csv` 保留本审查使用的现有 session-level 描述字段：target profile 的历史 bin 距离、DataCube 诊断 peak-bin mode fraction/std、B1 已有 channel amplitude CV、usable ratio、below-threshold ratio，以及已有 HR/BR quality label。没有创建新的 QC threshold。

以下为 43 个锁定 session 的组内中位数；`target/profile rel` 是历史 target bin 的多通道 profile 相对峰值，`target peak ±1 fraction` 是该历史 target 落在诊断块峰值 ±1 bin 的比例，二者均为描述性证据，不是重新选 target。

| group | n | heart target/profile rel | breath target/profile rel | heart target peak ±1 fraction | breath target peak ±1 fraction | range peak mode fraction | range peak bin std (bin) | channel amplitude CV | usable ratio | below-threshold ratio | existing HR quality | existing BR quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| NEAR_LT_0.30 | 16 | 0.368 | 0.280 | 0.183 | 0.227 | 0.699 | 0.719 | 0.248 | 1.000 | 0.000 | usable_for_hr=16 | review_required=9; usable_for_br=7 |
| FAR_GT_1.50 | 18 | 0.561 | 0.430 | 0.824 | 0.366 | 0.630 | 1.316 | 0.263 | 1.000 | 0.000 | usable_for_hr=18 | review_required=11; usable_for_br=7 |
| REFERENCE_0.30_0.60 | 9 | 0.436 | 0.204 | 0.065 | 0.152 | 0.748 | 1.342 | 0.242 | 1.000 | 0.000 | usable_for_hr=9 | research_harmonic_corrected=1; review_required=5; usable_for_br=3 |

形态描述：三组均可见近距离侧的持续亮带，历史 heart/breath marker 并不在所有 session 中都对应全局最大峰；因此图形显示了共同的前端 range-profile 结构，但不能仅凭它把该结构定性为人体、direct leakage 或固定环境反射。远端组的诊断 peak-bin std 中位数高于 reference，且 mode fraction 中位数不高于 reference，不支持‘远端更像固定环境反射’；近端组的 mode fraction/std 也未显示相对 reference 的一致固定峰模式。

### Interpretation answers

1. <0.30 m 组是否明显更像 near-field/direct leakage：没有出现一批同时满足‘历史 target 在极近端、target-dominant 且跨诊断块持续固定’的 target；近端组相对 reference 的描述性指标也不形成一致差异，不能支持升级。
2. >1.50 m 组是否明显更像固定环境反射：没有出现一批同时满足‘历史 target 在远端、target-dominant 且低 peak-bin dispersion’的 target；远端组 peak-bin dispersion 反而更高，不能支持固定环境反射结论。
3. reference 是否更像人体 target：reference 中少数 target 满足收紧后的可见形态标签，但没有 session-level 摆位 ground truth；作为组整体，没有足够证据宣称其比两端更接近人体。
4. heart 与 breath 异常模式是否一致：不一致或证据不足；两列 target 独立分类，shared bin/channel 只作为记录字段，不能替代 profile/heatmap 证据。
5. “近距离强反射高风险但未证实”能否升级：本轮不能升级；异常距离本身没有得到独立的 target-level 非人体反射证据支持。

## Conclusion rule

本次总体结论：`RISK_NOT_SUPPORTED`。在本次 16 个近端、18 个远端和 9 个 reference 的只读前端比较中，没有观察到能把两端异常组分别归为 near-field/direct leakage 或 fixed-environment reflection 的一批明确 session-level target 证据；现有共同近距离亮带属于可见结构，但缺少摆位/独立物理 ground truth，且组间描述性指标不支持两端具有独特异常模式。`LIKELY_HUMAN` 只用于少数满足收紧后可见形态条件的独立 target，不改变总体风险结论。

## Provenance

- B1 distance/quality source: `C:\Users\550ACW\Documents\Codex\2026-08-29\b1-formal-71-corrected-target-distance\outputs\FORMAL_37MM_DISTANCE_QUALITY_BASE.csv`.
- historical target/output source: `D:\Project\厚粲杯\08_算法\output\30_预实验与原型\03_EData_FAST_历史原型` (existing `*_mmwave_vital_signs.json`).
- DataCube source: `J:\Data` (existing `*_datacube*.npz`; read-only).
- code trace: `BR_PIPELINE_CODE_TRACE.md` and `BR_PIPELINE_CODE_PROVENANCE.csv` in the same output directory.
- diagnostic figure directory: `extreme_range_target_figures/`.

本审查到此停止；没有后续算法、参数或 formal 重跑步骤。
