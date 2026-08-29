# Issue #15 mmWave physiology/QC closure

日期：2026-08-29  
状态：`CLOSED_WITH_EXPLICIT_BOUNDARIES`

本 closure 只复用既有 formal QC、corrected 37 mm audit、BIOPAC ECG/RSP
comparison、B1/B2 audit、067/099 provenance 和现有 manifest/result tables。
没有重跑 C2B/C2C、没有开发新算法、没有重新计算 71/72 session，也没有读取或修改
NIR/RGB/原始数据。

## Final qualification table

| metric | reference denominator | current best evidence | corrected metric | applicable cohort/windows | QC requirement | known limitation | allowed scientific use | prohibited claim | final status |
|---|---|---|---|---|---|---|---|---|---|
| HR | BIOPAC ECG：5 sessions / 99 valid 60 s windows；formal J_Data：70-session main cohort，HR value 1,297/1,400 probe-quality windows，1,056/1,400 paired pre/post HR events | corrected distance spacing `0.037 m/bin`；HR course comparison；Tier crosswalk | HR-course MAE `3.777 bpm`（corrected 37 mm calibration） | #16 可使用 70-session main cohort；Tier1 仅作 quality-gated candidate，Tier2 仅作质量对照/敏感性 | 现有 window/probe coverage、corrected distance QC、target-lock/phase、timestamp/behavior provenance 联合；不能只看 SNR | 5-session calibration 不能代表 70-session ECG ground truth；target-lock 是 candidate，不是 chest-lock confirmation | quality-gated HR course candidate；一次预定义 quality-stratified #16 sensitivity；supporting physiology context | 不得写成全队列 HR 已验证、临床准确或每场胸部锁定 | `PASS_QUALITY_GATED` |
| BR | BIOPAC RSP：5 sessions / 99 valid 60 s windows；formal J_Data：既有 breath-quality 分层，50/70 sessions 达历史 coverage 条件 | corrected distance audit；RSP spectral comparison；existing BR quality labels | corrected spectral BR MAE `3.328 breaths/min`；historical old-gate `3.511` 仅保留历史 | #16 仅在既有 `usable_for_br`/quality-stratified窗口中作 supporting sensitivity；不扩大到所有 Tier1 | 现有 breath quality、window/probe coverage、corrected distance/phase/provenance；2BR/3BR harmonic flags 必须保留 | BR peak path 当前 reference aggregate 仍显示较差误差；5-session calibration 小；谐波风险未被全队列 reference 闭环解决 | supporting BR sensitivity、任务动态的辅助协变量/描述性结果 | 不得写成 BR 已验证、全队列准确或可替代 RSP | `PASS_SUPPORTING` |
| HRV | ECG beat/IBI reference：5-session reference evidence存在，但 formal 主队列没有闭合逐搏 ECG↔mmWave matching | 现有 RMSSD/IBI 输出、ECG reference audit、C1D stop decision | RMSSD comparison MAE `262.6418 ms`，within ±5 ms 为 `0/99`；不能作为验证通过 | 不进入 #16 生理主变量；最多登记为 blocked evidence boundary | 必须有逐搏 beat/IBI 对齐、ECG reference、artifact policy、window-level paired denominator | 当前没有足够 beat/IBI + ECG 闭环；C1D 为 `NO_MATERIAL_IMPROVEMENT_STOP_HRV` | 仅历史/失败模式/方法边界说明 | 不得进入 validated physiology、HRV 主模型、质量通过结论或 multimodal 主结论 | `BLOCKED` |

## QC tier decision

Corrected formal QC 使用既有规则和 `0.037 m/bin` distance semantics：

- Tier 1：33 sessions，`QC-eligible candidate`。允许进入 #16 的预定义 quality
  sensitivity 作为高质量候选层，但不等于 HR/BR ground-truth validated。
- Tier 2：37 sessions，`motion/quality-only`。可作为质量分层对照或敏感性层；不得把
  HR/BR 值解释为已验证生理测量。
- Tier 3：2 sessions，`067`、`099`。排除 formal #16 生理输入；067 无 raw，099
  有 supplemental output 但 timeline/meta/linkage 未闭合。

Tier 1/2 的依据不是笼统“信号质量差”，而是已有 window/probe coverage、corrected
distance QC、target-lock/phase、timestamp、motion/keypress 和 provenance 字段的联合
状态。B2 总体结论仍为 `RISK_NOT_SUPPORTED`，不能把异常距离改写成 near-field 或
fixed-environment reflection 结论。

## #16 input contract

只允许运行一次预先定义的 quality-stratified sensitivity，且只复用 #16 已有模型、
固定分母和既有窗口；不得借此重跑 producer 或搜索新阈值。

### Cohort and strata

- 主分母：既有 70-session J_Data main cohort、1,400 probe events；沿用 #16 已有
  task-dynamics/alertness event definition。
- Tier 1 quality stratum：33 sessions：
  `071,072,074,076,078,082,083,086,088,089,091,093,094,095,096,098,100,106,107,109,110,114,116,119,124,125,126,129,130,134,139,143,170`。
- Tier 2 quality stratum：37 sessions：
  `056,057,058,059,062,064,065,068,070,073,075,077,081,084,085,087,090,104,108,117,118,122,123,127,128,131,133,145,147,148,154,158,160,162,166,175,178`。
- Tier 3 exclusion：`067`、`099`；不进入 #16 生理变量模型。
- 5-session/99-window BIOPAC calibration 只作为独立 reference evidence，不与
  70-session task denominator 合并。

### Allowed variables

1. 既有 HR course/window 或 event-level 数值及其原有 `heart_rate_quality`；只在
   Tier1 中作为 quality-gated candidate，Tier2 仅用于预定义质量对照。
2. 既有 BR 数值及其原有 `breath_quality`；仅作为 supporting sensitivity，保留
   `research_harmonic_corrected`、`review_required`、`usable_for_br` 标签。
3. 既有 behavior/task-dynamics outcome 与 event timing；不改变原 #16 主模型。
4. 质量分层字段：corrected tier、corrected distance QC、window/probe coverage、
   target-lock/phase status、timestamp/provenance、既有 motion/keypress proxy。

### Exclusions and interpretation

- 排除 067/099、缺失 linkage、非既有 probe/window 定义、HRV/IBI/RMSSD 变量和任何
  新 target-lock/AoA/beamforming/VMD/multi-bin 派生量。
- 不把 Tier1、HR MAE 3.777 bpm 或 BR MAE 3.328 breaths/min 外推为 formal 70-session
  生理准确性。
- 不把 Tier2 的保留用于“校正后 HR/BR 可用”结论；其角色是质量异质性/敏感性对照。
- 不生成新的质量阈值，不重新选择 bin/channel，不改变主模型 denominator。

## Provenance

| item | script/input | local output | GitHub report/manifest | evidence |
|---|---|---|---|---|
| formal QC | `D:\Project\厚粲杯\08_算法\scripts\maintenance\build_formal_vital_qc_v1.py`; existing formal outputs and ECG/RSP reference | `D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\` | `docs/results/mmwave_formal_vital_qc_v1/MMWAVE_FORMAL_VITAL_QC_V1_REDACTED_MANIFEST.json` | existing QC report/tables |
| corrected distance/B1 | `C:\Users\550ACW\Documents\Codex\2026-08-29\b1-formal-71-corrected-target-distance\work\build_b1_distance_quality.py` | `D:\Project\厚粲杯\08_算法\docs\results\mmwave_formal_vital_qc_v1\mmwave_session_use_tier_crosswalk_corrected37mm.csv` | `docs/results/2026-08-29_FORMAL_37mm距离校正审计_v1/2026-08-29_FORMAL_37MM_DISTANCE_BASIC_SUMMARY.md` | 33/37/2 corrected crosswalk |
| B2 | existing read-only audit entrypoint and locked corrected-distance table | `D:\Project\厚粲杯\08_算法\docs\results\2026-08-29_BR管线与极端距离审计_v1\` | `docs/results/2026-08-29_BR管线与极端距离审计_v1/2026-08-29_FORMAL_EXTREME_RANGE_TARGET_AUDIT.md` | `RISK_NOT_SUPPORTED` |
| closure | no new analysis script; documentation-only closure | this report | this report plus #16 contract | decision boundary frozen |

## Decision change

Issue #15 从 `PARTIAL` 收口为 `CLOSED_WITH_EXPLICIT_BOUNDARIES`：HR 进入
`PASS_QUALITY_GATED`，BR 进入 `PASS_SUPPORTING`，HRV 保持 `BLOCKED`；#16 只允许
一次预定义 quality-stratified sensitivity。没有任何新算法、C2B/C2C、NIR/RGB 或
原始数据变更。
