# FORMAL 37 mm distance and existing-quality basic summary

状态：PASS（仅基础统计；不解释机制）。

## 范围与口径

- 分析集：71 个 formal mmWave session；sub-067 不在这 71 行中。
- selected bin 与 selected channel 沿用历史 target-lock 表；没有重新选 target。
- corrected distance = selected_bin × 0.037 m；old distance 保留原 selected_bin × 0.08 m。
- corrected distance QC 与四类 transition 直接复用既有 FORMAL_37MM_DISTANCE_QC.csv；没有改 QC 定义。
- 没有读取 NIR/RGB；没有重跑 HR/BR；没有训练模型。

## 来源

- 距离与 QC：C:\Users\550ACW\Documents\Codex\2026-08-29\rs6240-sdk-hr-br-hrv-1\outputs\FORMAL_37MM_DISTANCE_QC.csv。
- selected channel、target-lock 质量字段：D:\Project\厚粲杯\11_数据\derived\j_mmwave_target_lock_audit_v1\j_session_target_lock_summary.csv。
- HR/BR 质量类别：D:\Project\厚粲杯\08_算法\output\30_预实验与原型\03_EData_FAST_历史原型\behavior_gated_runtime_all.csv。
- gap/timestamp 与行为 QC：D:\Project\单独毫米波从0分析\10_结果\formal_qc\session_manifest_v1.csv。
- motion/keypress 与 bin/channel 工程代理：D:\Project\单独毫米波从0分析\09_中间数据\formal\subject_results 下 71 个 *_window_features_v1.csv。

## Corrected distance distribution

| corrected distance band (m) | N |
|---|---:|
| <0.20 | 4 |
| 0.20–0.30 | 12 |
| 0.30–0.60 | 32 |
| 0.60–1.00 | 5 |
| 1.00–1.50 | 0 |
| >1.50 | 18 |

## Corrected QC transition

| transition | N |
|---|---:|
| PASS→PASS | 33 |
| PASS→FAIL | 2 |
| FAIL→PASS | 16 |
| FAIL→FAIL | 20 |

Corrected QC：PASS=49，FAIL=22；四类 transition 合计 71。

## Existing numeric quality fields

N/mean/median 均按 session 统计；PASS/FAIL 为 corrected distance QC 分组。窗口字段先按每 session 对已有 window rows 取 median，再进入本表统计；没有新建 QC 门槛。

| field (exact source field or explicit aggregation) | source | overall N | mean | median | PASS N | PASS mean | PASS median | FAIL N | FAIL mean | FAIL median |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hr_ch_power_ratio | target-lock hr_ch_power_ratio | 71 | 0.138487 | 0.1383 | 49 | 0.136163 | 0.1377 | 22 | 0.143664 | 0.1403 |
| phase_stability | target-lock phase_stability | 71 | 0.919894 | 0.9301 | 49 | 0.91732 | 0.9282 | 22 | 0.925627 | 0.93365 |
| below_threshold_ratio | target-lock below_threshold_ratio | 71 | 0.0332437 | 0 | 49 | 0.000102041 | 0 | 22 | 0.107059 | 0 |
| usable_ratio | target-lock usable_ratio | 71 | 0.966756 | 1 | 49 | 0.999898 | 1 | 22 | 0.892941 | 1 |
| std_mm_min | target-lock std_mm_min | 71 | 0.0343095 | 0.033631 | 49 | 0.0366012 | 0.034631 | 22 | 0.0292054 | 0.024811 |
| std_mm_median | target-lock std_mm_median | 71 | 0.129548 | 0.130344 | 49 | 0.149808 | 0.141561 | 22 | 0.084422 | 0.100481 |
| std_mm_p25 | target-lock std_mm_p25 | 71 | 0.0951413 | 0.095456 | 49 | 0.108477 | 0.099021 | 22 | 0.0654396 | 0.076272 |
| std_mm_p75 | target-lock std_mm_p75 | 71 | 0.189904 | 0.188411 | 49 | 0.221518 | 0.21583 | 22 | 0.119492 | 0.143753 |
| std_mm_max | target-lock std_mm_max | 71 | 1.60715 | 1.62529 | 49 | 1.64928 | 1.65617 | 22 | 1.5133 | 1.51222 |
| timestamp_dt_ms_median | session timestamp_qc python_dt_ms_median | 71 | 7.16901 | 7 | 49 | 7.20408 | 7 | 22 | 7.09091 | 7 |
| timestamp_dt_ms_p99 | session timestamp_qc python_dt_ms_p99 | 71 | 19.7183 | 20 | 49 | 19.5306 | 20 | 22 | 20.1364 | 20 |
| timestamp_dt_ms_max | session timestamp_qc python_dt_ms_max | 71 | 3833.34 | 3563 | 49 | 3731.2 | 3341 | 22 | 4060.82 | 3787.5 |
| timestamp_gap_warn_count | session timestamp_qc python_gap_warn_count | 71 | 170.028 | 164 | 49 | 167.286 | 165 | 22 | 176.136 | 161 |
| timestamp_gap_stop_count | session timestamp_qc python_gap_stop_count | 71 | 166.958 | 162 | 49 | 165.388 | 163 | 22 | 170.455 | 159.5 |
| timestamp_python_nonpositive_step_count | session timestamp_qc python_nonpositive_step_count | 71 | 215.113 | 240 | 49 | 215.551 | 242 | 22 | 214.136 | 235 |
| timestamp_dll_nonpositive_step_count | session timestamp_qc dll_nonpositive_step_count | 71 | 0.028169 | 0 | 49 | 0.0204082 | 0 | 22 | 0.0454545 | 0 |
| motion_energy_proxy_hz_2_5_plus_median | window median motion_energy_proxy_hz_2_5_plus | 71 | 0.0425618 | 0.0330337 | 49 | 0.0440694 | 0.0325564 | 22 | 0.0392039 | 0.0346991 |
| channel_amplitude_cv_median | window median channel_amplitude_cv | 71 | 0.250505 | 0.247148 | 49 | 0.238541 | 0.241908 | 22 | 0.277154 | 0.263116 |
| phase_rms_proxy_median | window median phase_rms_proxy | 71 | 2.3166 | 2.12517 | 49 | 2.41926 | 2.12517 | 22 | 2.08794 | 2.02372 |
| range_peak_bin_mode_fraction_median | window median range_peak_bin_mode_fraction | 71 | 0.877722 | 0.90604 | 49 | 0.886961 | 0.946309 | 22 | 0.857145 | 0.875273 |
| range_peak_bin_std_median | window median range_peak_bin_std | 71 | 0.328531 | 0.324322 | 49 | 0.337264 | 0.225407 | 22 | 0.309081 | 0.347386 |
| objective_mean_rt_ms_median | window median objective_mean_rt_ms | 71 | 302.319 | 288.912 | 49 | 296.496 | 288.912 | 22 | 315.287 | 288.812 |
| objective_accuracy_rate_median | window median objective_accuracy_rate | 71 | 0.951127 | 0.96 | 49 | 0.958367 | 0.96 | 22 | 0.935 | 0.96 |
| objective_commission_rate_median | window median objective_commission_rate | 71 | 0.0323944 | 0.04 | 49 | 0.0297959 | 0.04 | 22 | 0.0381818 | 0.04 |
| objective_omission_rate_median | window median objective_omission_rate | 71 | 0.0121127 | 0 | 49 | 0.0077551 | 0 | 22 | 0.0218182 | 0 |

## Existing categorical quality fields

这些字段是已有类别标签；mean/median 不适用，因此仅列 N 与类别计数，并按 corrected distance QC 分组。N 是已有 behavior-gated probe rows，不扩展为新的 session QC。

| field | overall N / counts | corrected PASS N / counts | corrected FAIL N / counts |
|---|---|---|---|
| heart_rate_quality | 1271 / review_required=132; usable_for_hr=1139 | 876 / review_required=95; usable_for_hr=781 | 395 / review_required=37; usable_for_hr=358 |
| breath_quality | 1271 / research_harmonic_corrected=126; review_required=589; usable_for_br=556 | 876 / research_harmonic_corrected=88; review_required=410; usable_for_br=378 | 395 / research_harmonic_corrected=38; review_required=179; usable_for_br=178 |

## Field availability boundaries

- target_score：未在 71-session 距离/target-lock 质量源中持久化，因此未写入 CSV。
- signal strength：没有同名字段；保留真实字段 hr_ch_power_ratio，不改名、不解释为新的信号强度指标。
- phase stability：使用真实字段 phase_stability。
- gap/timestamp QC：使用 session manifest 中真实的 timestamp_qc 字段及其计数/时间间隔字段。
- motion/keypress：使用已有 window-level motion_energy_proxy_hz_2_5_plus 与 objective_* 字段的 session median；没有同名 keypress_quality 字段。
- HR quality / BR quality：保留已有 heart_rate_quality / breath_quality 类别及计数；不重跑 HR/BR。
- channel/bin continuity：没有同名 continuity 字段；保留真实 window-level range_peak_bin_mode_fraction、range_peak_bin_std 和 channel_amplitude_cv 的 session median，不定义新 QC。

## Status counts

- timestamp_qc_status：PARTIAL=71
- behavior_qc_status：PASS=71
- formal_qc_status：PARTIAL=71
- hr_quality_mode：usable_for_hr=71
- br_quality_mode：research_harmonic_corrected=3; review_required=40; usable_for_br=28

本交付到此停止；没有机制解释、因果分析或后续模型步骤。
