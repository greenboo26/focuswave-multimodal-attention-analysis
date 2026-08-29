# Issue #16 quality-stratified sensitivity input contract

状态：`READY_AFTER_ISSUE15_CLOSURE`  
前置：`MMWAVE_FORMAL_VITAL_QC_V1_CLOSURE_2026-08-29.md`

只允许一次预定义 quality-stratified sensitivity。主 task-dynamics/alertness 分析
不改模型、不改 70-session denominator、不重跑 C2B/C2C。

## Input

- Main cohort：70-session J_Data，1,400 probe events，沿用既有 #16 event/window
  definitions。
- Tier 1：33 corrected-QC sessions，HR 为 quality-gated candidate，BR 为 supporting。
- Tier 2：37 sessions，仅作为质量异质性对照，不解释为 validated physiology。
- Exclude：067、099；HRV/IBI/RMSSD；任何新 target-lock、AoA、beamforming、VMD
  grid、generic multi-bin 派生量。

## Variables

- Existing HR course/window/event values + existing `heart_rate_quality`.
- Existing BR values + existing `breath_quality`；保留 harmonic/review labels。
- Existing task-dynamics/alertness outcomes and event timing.
- Existing quality fields：corrected tier/distance QC、window/probe coverage、
  target-lock/phase、timestamp/provenance、motion/keypress proxies。

## Interpretation

Tier 1 与 Tier 2 只能作为预定义 quality strata；任何 strata 间差异都不能被写成
毫米波 HR/BR 生理准确性证据。5-session/99-window BIOPAC calibration denominator
单独保留，不能并入 70-session task denominator。不得把 HRV 进入模型。

## Acceptance

运行前只需确认输入 manifest、session crosswalk、现有 #16 输出和 commit identity；
若任一身份/分母/字段发生变化，停止并重新走 evidence gate，不自动扩展任务范围。
