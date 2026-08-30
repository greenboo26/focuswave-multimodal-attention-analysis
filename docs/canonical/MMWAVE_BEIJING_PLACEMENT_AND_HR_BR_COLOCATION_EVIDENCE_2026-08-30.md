# mmWave Beijing placement lower bound and HR/BR range-bin co-location evidence — 2026-08-30

Status: `CANONICAL_EVIDENCE_NOTE / NO_FORMAL_PHYSIOLOGY_PROMOTION / NO_NEW_SELECTOR`

This note records a new project-authoritative experiment fact supplied on 2026-08-30 and reconciles it with the current mmWave range-selection evidence. It does not authorize a new HR/BR estimator, an ECG-tuned gate, a distance-error-tuned selector, or deletion of canonical multimodal rows.

## 1. Beijing formal-experiment placement lower bound

Project-authoritative setup fact supplied by the experiment team/user:

- site: Beijing formal experiment;
- all formal participants were positioned so that the participant/chest target was at least `0.30 m` from the mmWave radar;
- therefore a true participant thorax/chest target physically located at `<0.30 m` is incompatible with the intended Beijing formal setup.

Evidence class: `USER_CONFIRMED_FORMAL_SETUP_CONSTRAINT`.

This is stronger than having no lower-bound setup information, but it is not a per-session tape/laser/photo measurement receipt and must not be rewritten as measured session-level ground truth. The current selected-bin-derived distance remains a radar-selection proxy; exact session-level range bias / mounting geometry / calibration receipts remain unresolved. Consequently:

- `BEIJING_PHYSICAL_CHEST_LOWER_BOUND = 0.30 m` is accepted as a formal setup constraint;
- a selected target proxy `<0.30 m` is `PHYSICALLY_IMPLAUSIBLE_AS_TRUE_CHEST_TARGET` and should be flagged for target/QC review;
- this fact alone does **not** yet authorize automatic deletion of every row whose computed selected-bin proxy is `<0.30 m`, because selected-bin distance is not the same thing as independently measured chest distance and the exact range-axis bias/calibration provenance is not fully closed;
- the upper physical ROI remains unresolved;
- historical `0.30–1.50 m` therefore remains historical sensitivity for the upper bound; the newly supported part is specifically the Beijing physical lower-bound setup constraint, not validation of the entire historical interval.

Recommended state wording for Issue #26: `LOWER_BOUND_SETUP_CONSTRAINT_AVAILABLE / SESSION_GEOMETRY_AND_UPPER_BOUND_UNRESOLVED` rather than treating the entire physical gate as solved.

## 2. Adjacent-window continuity is block-local

Current canonical targeted-validation code resets range-bin/channel continuity state at the start of every block:

- `scripts/maintenance/run_mmwave_targeted_validation_20260830.py::analyze_subject()` enters each `for block in blocks` with `previous_hr = previous_br = None` and `previous_current_hr = previous_current_br = None`;
- the first window therefore uses `block_start_reset_independent_init`;
- output rows explicitly record `selection_scope = strictly_within_complete_block; block state reset before first window`.

The current selector-path replay also keys the previous-BPM anchor by `block_id`, so the previous-state anchor does not leak across block boundaries.

Decision: `BLOCK_LOCAL_CONTINUITY_RESET = VERIFIED_FOR_CURRENT_TARGETED/REPLAY_CHAIN`.

If a future formal HR/BR physiology runner reuses adjacent-window continuity, block-start reset must remain part of the frozen contract. This verification does not itself promote HR/BR physiology.

## 3. HR and BR range-bin co-location: what the literature supports

There is substantial methodological support for treating respiration and heartbeat as signals from the same broad cardiopulmonary/thoracic target region in frontal vital-sign radar setups. Several published pipelines first select a target/cardiopulmonary range bin and then separate respiration and heartbeat by their different frequency bands. Examples include:

- Zhou et al., “A novel target state detection method for accurate cardiopulmonary signal extraction based on FMCW radar signals,” *Frontiers in Physiology* (2023): selects the target cardiopulmonary range bin, then extracts respiration and HR separately from the cardiopulmonary signal. https://pmc.ncbi.nlm.nih.gov/articles/PMC10330764/
- “Detection of vital signs based on millimeter wave radar,” *Scientific Reports* (2025): identifies the target range bin and describes phase variation in that bin as chest micro-motion caused by breathing and heartbeat. https://www.nature.com/articles/s41598-025-09112-w

However, the literature does **not** justify a universal rule that HR and BR must come from exactly the same bin. High-resolution or non-frontal geometries can resolve different body regions, and respiration/heartbeat may be strongest at different spatial positions. For example:

- Choi et al., “Selecting Target Range with Accurate Vital Sign Using Spatial Phase Coherency of FMCW Radar,” *Applied Sciences* 11(10):4514 (2021), DOI 10.3390/app11104514, reports respiration-related bins near abdomen/thorax and heartbeat-related bins nearer the neck in its geometry, and explicitly treats vital displacement as spatially distributed across multiple bins. https://www.mdpi.com/2076-3417/11/10/4514
- recent multi-bin work also deliberately uses different body/range regions when radar geometry separates body segments; this is a different geometry from a simple frontal chest-target assumption and argues against a universal same-bin rule.

Therefore the defensible FocusWave interpretation is:

`HR_BR_COLOCATION = PHYSICAL_CONSISTENCY_PRIOR / QC_CANDIDATE`, not `HR_BIN_MUST_EQUAL_BR_BIN`.

## 4. Allowed next audit and prohibited threshold tuning

A narrow outcome-independent audit is authorized using existing frozen range-bin outputs only. It should compute, without using ECG/RSP error or attention labels:

- `abs_hr_br_bin_gap = abs(hr_bin - br_bin)`;
- the equivalent proxy separation using the frozen bin spacing applicable to the audited output;
- proportions at same bin and within 1 / 2 / 3 bins;
- median, P90/P95, maximum;
- block/session distributions;
- whether large HR–BR separation co-occurs with already-recorded target/channel discontinuity or other structural QC states.

The audit must compare the current independent selection and the block-local continuity path where both are already available. It must not rerun raw acquisition, invent a new selector, use ECG/RSP to choose the threshold, or optimize a cutoff by HR/BR MAE.

No hard numerical HR–BR separation cutoff is frozen by this note. A future cutoff requires an outcome-independent rationale combining radar range resolution/bin spacing, intended frontal thoracic geometry, and the observed structural distribution. Thresholds must not be selected because they improve ECG/RSP agreement.

## 5. Missingness / exclusion semantics

Even if a later frozen HR–BR co-location QC marks a physiology estimate as implausible, apply the existing multimodal minimum-unit rule:

- do not delete the canonical probe row;
- do not delete other modalities;
- do not zero-fill HR/BR;
- mark only the affected mmWave physiology field/unit with explicit `QC_FAIL`, `NOT_ELIGIBLE`, or other frozen state/reason;
- structural coverage/provenance remains available where valid.

Current global roles remain unchanged by this evidence note: HR/BR=`HOLD / SUPPORTING_ONLY`; HRV/IBI=`BLOCKED / EXCLUDE`.
