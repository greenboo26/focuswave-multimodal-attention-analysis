# mmWave current state — 2026-08-29

Status: `CURRENT / MAINLINE-BOUND`

Purpose: keep the mmWave work anchored to what has already been done, what changed today, and what must not be reopened without material new evidence. This file is a current-state addendum to `ANALYSIS_HISTORY_LEDGER.md` and `docs/canonical/ANALYSIS_PROGRESS_MAP_2026-08-28.md`; it does not erase historical results.

## Current project phase

The mmWave mainline is **closure, evidence reconciliation, and report integration**, not open-ended algorithm reinvention.

Before proposing a rerun, new front-end algorithm, AoA/beamforming, multi-bin search, VMD grid, or other redesign, first check the historical ledger and the existing progress map. A local bug or corrected metric does not by itself justify restarting the mmWave pipeline.

## What changed on 2026-08-29

### Issue #15 closure

- HR：`PASS_QUALITY_GATED`；corrected BIOPAC calibration MAE=`3.777 bpm`，仅可作为
  quality-gated candidate 和 #16 sensitivity。
- BR：`PASS_SUPPORTING`；corrected spectral calibration MAE=`3.328 breaths/min`，仅作
  supporting/sensitivity，不宣称全队列准确。
- HRV：`BLOCKED`；现有 beat/IBI + ECG 闭环不足，C1D 保持
  `C1D_NO_MATERIAL_IMPROVEMENT_STOP_HRV`。
- corrected QC：Tier1=`33`、Tier2=`37`、Tier3=`2`（067/099）；Tier1 不是
  ground-truth validated。
- #16 只允许一次预定义 quality-stratified sensitivity；契约见
  `docs/canonical/ISSUE16_QUALITY_STRATIFIED_SENSITIVITY_CONTRACT_2026-08-29.md`。

### Formal distance semantics

- Formal RS6240 DataCube distance spacing is corrected to **0.037 m/bin**.
- Historical analyses that interpreted the same bins with `0.08 m/bin` require a caveat or corrected paired audit when distance gating affected target selection.

### BIOPAC HR calibration

On the same 5-session / 99-valid-window denominator, changing only the distance spacing used by the physical 0.30–1.50 m gate materially changed target/channel selection and HR-course output.

- historical old-gate HR-course MAE: **4.590 bpm**;
- corrected-distance HR-course MAE: **3.777 bpm**;
- status: `MATERIALLY_AFFECTED` at the BIOPAC calibration layer;
- the historical 4.59/4.61 value is retained only as a historical old-gate result.

This does **not** automatically invalidate the formal 70-session task/alertness conclusions; those are a separate evidence layer.

### BIOPAC BR calibration

On the recovered 5-session / 99-valid-window RSP comparison denominator:

- historical old-gate spectral BR MAE: **3.511 breaths/min**;
- corrected-distance spectral BR MAE: **3.328 breaths/min**;
- target bin changed in 59/99 paired windows;
- channel changed in 79/99;
- BR value changed in 70/99;
- status: `MATERIALLY_AFFECTED` at the BIOPAC calibration layer.

Again, this is a calibration-layer result, not an automatic formal-model invalidation.

### Corrected formal QC tier recomputation

Replacing only the old distance-based QC condition with corrected 37 mm distance QC, while preserving the existing phase-stability, window/probe coverage, and 067/099 provenance conditions, gives:

- Tier 1 QC-eligible candidate: **33 sessions**;
- Tier 2: **37 sessions**;
- Tier 3: **2 sessions** (`067`, `099`);
- 16 sessions moved from old Tier 2 to new Tier 1.

Tier 1 remains a **QC-eligible candidate tier**, not proof that HR/BR are ground-truth validated in those 33 sessions.

### B2 extreme-range target audit

B2 completed a read-only front-end diagnostic on 43 locked sessions:

- 16 corrected-distance sessions <0.30 m;
- 18 >1.50 m;
- 9 fixed reference sessions from 0.30–0.60 m;
- 43/43 DataCubes present and 43 diagnostic figures generated;
- heart and breath targets classified independently;
- no batch-level visible pattern supported labeling the near group as direct/near-field leakage or the far group as fixed-environment reflection;
- overall conclusion: **`RISK_NOT_SUPPORTED`**.

Boundary: session-level expected human placement distance was unavailable in that audit, so most individual target labels remained `AMBIGUOUS`. Abnormal selected distance must not be converted into a non-human-reflection claim without independent physical evidence.

## Frozen / do-not-repeat boundaries

The existing canonical progress map already freezes the following without material new evidence:

- Behavior+mmWave C2B/C2C reruns;
- old seven-class mmWave A/B method sweeps;
- generic multi-bin / AoA / beamforming / VMD-grid work repackaged as a new idea.

The 2026-08-29 corrections do not remove those freeze rules. In particular, **multi-antenna processing and AoA/beamforming must not be reopened as a generic next step merely because the formal DataCube has 8 channels**. Reopen only if a focused evidence audit demonstrates a concrete unresolved capability question and shows that the required channel identity/coherence/calibration information is available for the formal dataset.

Non-angle multi-channel operations already present in historical/current work (for example per-channel scoring or selecting a channel/bin) must be distinguished from true angle estimation or coherent beamforming.

## Current interpretation

1. The 37 mm correction fixed a real distance-axis bug and materially changed the calibration-layer target selections and HR/BR metrics.
2. Corrected HR and BR calibration are promising/supporting, but do not prove every formal session is locked to the chest.
3. B2 does **not** support the claim that extreme selected distances are systematically caused by near-field leakage or fixed environmental reflections.
4. Therefore the mainline should not pivot into a new clutter/localization program solely because some selected distances are extreme.
5. Any proposed front-end rework must first recover and compare prior project exploration, current implementation, and formal evidence; only a demonstrated unresolved gap may advance to implementation.

## Required next-decision discipline

For any new mmWave task, report in this order:

1. current phase;
2. relevant completed/frozen work;
3. what new evidence changed since the last state;
4. whether the new proposal was already explored or rejected;
5. the smallest action that advances the current mainline;
6. what remains blocked.

Do not replace project-state evidence with chat-memory reconstruction.
