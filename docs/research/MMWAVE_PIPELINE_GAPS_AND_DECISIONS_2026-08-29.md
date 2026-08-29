# Formal mmWave pipeline gaps and decisions

Date: 2026-08-29
Canonical base: `3d4c073f98ddb0ef86e0e3a5c3f99b048610a0d8`
Audit status: **PASS for the assigned evidence-recovery and pipeline-audit gate; physiology validity remains bounded.**

## Durable decisions

### D-AUDIT-20260829-01 — Recovered upstream facts remain bound

The formal stored `ReportDataCube1D` output is not raw ADC. It is an 8-channel complex range-domain DataCube, and a Range FFT has already occurred upstream. The formal distance spacing is `0.037 m/bin`. These are not reset to `UNKNOWN` or `UNVERIFIABLE_UPSTREAM` merely because the full firmware build manifest is incomplete.

Evidence: `docs/research/MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`, prior RS6240 audit reports, formal image SHA-256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`, and the 256-point/2T4R output audit.

### D-AUDIT-20260829-02 — Exact upstream details stay unresolved where not bound

The exact formal image does not currently have a complete source-tree commit/build manifest. Therefore the following remain unresolved or SDK/manual-only: pre-FFT window type, exact DC/static/IQ correction, zero-padding/cropping details, normalization/physical amplitude scale, chirp aggregation internals, physical antenna coordinates, calibration state, and upstream phase correction. Generic SDK defaults must not be promoted to exact formal-firmware behavior.

### D-AUDIT-20260829-03 — Current target selection is a mixed heuristic

The selector is not a strongest-reflector detector, human/chest locator, respiration-target validator, or heartbeat-target validator. It combines power eligibility, phase variance, band SNR, phase-stability scoring, and separate BR/HR channel competition. Existing 8-channel spatial consistency is candidate evidence only; it is not calibrated beamforming or chest-lock confirmation.

### D-AUDIT-20260829-04 — Distance semantics are a live scientific risk

Formal data use `0.037 m/bin`, but the v3.1.1 producer defaults to `0.08 m/bin` for `0.30-1.50 m` gating. This is a material axis/gate mismatch, not a display-only unit issue. The corrected-distance audit showed target/channel and calibration-layer changes. Historical results remain traceable; no unrequested algorithm rewrite or formal rerun is authorized by this audit.

### D-AUDIT-20260829-05 — HR/BR/HRV claims remain tiered

- HR: quality-gated research candidate only.
- BR: supporting research candidate only; the producer's low/medium/high consistency label is not a validity gate.
- HRV: blocked for validated use because radar peaks are not aligned beat-by-beat to ECG R peaks.
- `33/37/2`: current-pipeline eligibility/provenance strata, not participant compliance, acquisition quality, chest lock, or physiology validity.

### D-AUDIT-20260829-06 — Issue #16 stays paused

No Issue #16 quality-stratified sensitivity was run or authorized. No new scientific model, C2B/C2C rerun, target-lock algorithm, AoA/beamforming, VMD/multi-bin search, NIR/RGB modification, or raw-data modification was performed.

## Open gaps, ranked by interpretation risk

| Gap | Current evidence | Impact if unresolved | Correct status |
|---|---|---|---|
| Formal image to source/build manifest | Image hash and mode-field comparison recovered; one-to-one build commit absent. | Cannot promote all generic SDK settings to exact firmware. | `PRIOR_AUDIT_CONFIRMED_NEEDS_PRIMARY_RELINK` |
| Formal range-axis use in all downstream callers | Formal axis is 0.037 m/bin; v3.1.1 default remains 0.08; scanner and target-lock have distinct gates. | Target candidate set and distance-based labels can change. | `POTENTIALLY_HARMFUL` |
| Window/DC/clutter/IQ/normalization | No complete exact-image runtime receipt. | Amplitude/SNR and stationary-reflector interpretation are uncertain. | `UNRESOLVED` |
| Physical 8-channel geometry/calibration | Logical Tx/Rx ordering is known; physical calibration is not. | Channel competition cannot establish chest direction or phase coherence. | `UNRESOLVED` |
| Range-bin continuity | One pair is selected per segment; no tracking/stitching/jump gate. | Stillness does not guarantee phase continuity across blocks/segments. | `POTENTIALLY_HARMFUL` |
| Respiration-harmonic suppression | Optional scalar RSP prior exists but is not passed by standard formal runner. | Stable 2x/3x BR can survive as HR-like output. | `POTENTIALLY_HARMFUL` |
| BR quality gate | BR receives only full-segment time/frequency consistency label. | Low-quality BR can remain numerically populated. | `POTENTIALLY_HARMFUL` |

## 2026-08-30 ordered next execution decisions

### D-AUDIT-20260830-01 — device/source capability is not formal-device activation

The targeted SDK audit is recorded in `MMWAVE_DEVICE_FIRMWARE_ENGINEERING_EVIDENCE_2026-08-30.csv`. SDK/source capability is retained as evidence, but no lower-layer setting is promoted to formal runtime without an image-to-source match and a formal-session burn/boot/version/configuration receipt. The current source-tree ADC-mode edit is explicitly not the formal image behavior.

### D-AUDIT-20260830-02 — continuity audit stops at missing history

Existing outputs contain segment-level final bin/channel values and radar peak arrays, but not the previous/current target history required to calculate target/bin/channel continuity. No continuity rate is inferred from counterfactual 37 mm gate changes. A future rerun must persist the exact per-window instrumentation listed in the line-by-line audit; no formal batch begins before that gate is satisfied.

### D-AUDIT-20260830-03 — formal harmonic suppression is inactive

The external RSP 2×/3× rejection branch is present but requires `acq_path`/`ext_br_bpm`; the standard formal runner does not provide it. Internal harmonic folding/reference correction is classified as heuristic and reference-dependent, not active adaptive suppression.

### D-AUDIT-20260830-04 — HRV earliest blocker is beat-level radar-to-ECG matching

Radar-derived peak/IBI-shaped values and independent ECG R-peak values exist at separate layers, but no synchronized beat matching and paired IBI agreement output exists in the formal evidence package. HRV remains `BLOCKED`.

Current gate result: **PARTIAL / #16 PAUSED**. No model, target-lock, C2B/C2C, raw-data, device-burn, NIR, or RGB operation was performed.
| HRV beat-level validation | Radar IBI-shaped fields exist; no ECG R-peak matching. | RMSSD/SDNN could be mistaken for validated physiology. | `MISSING` |
| Caller/provenance consistency | Runner summary uses `breathing_rate`, producer writes `breath_rate`; runner defaults contain legacy roots. | Reports may omit BR or read the wrong local root if rerun carelessly. | `POTENTIALLY_HARMFUL` |
| Independent motion evidence | Current B flags use distance/phase proxies; C uses coverage. | Cannot translate Tier 2 into participant motion/compliance failure. | `MISSING` |

## Interpretation of `33/37/2`

The corrected split is the result of applying existing formal QC/provenance rules with the corrected formal range semantics and retaining existing 067/099 boundaries. It measures the current pipeline's eligibility strata. The split cannot be decomposed from current evidence into “acquisition quality,” “participant cooperated,” “human chest was selected,” and “physiology was valid.” Those are separate claims requiring separate evidence.

## 2026-08-30 literature-backed decision on the two remaining near-term engineering questions

### D-AUDIT-20260830-05 — instrument and audit target continuity; do not redesign target tracking first

Literature consistently treats range-bin choice and continuity as a first-order vital-sign problem. Choi et al. (IEEE Access 2021, DOI `10.1109/ACCESS.2020.3043013`) show that precise target range-bin selection materially changes respiration/heartbeat accuracy. Choi et al. (Applied Sciences 2021, DOI `10.3390/app11104514`) further use spatial phase coherency across neighboring bins and explicitly identify range-bin tracking as a future stability improvement. Xue et al. (Measurement 2023, DOI `10.1016/j.measurement.2023.113715`) use local search plus moving-average tracking to obtain the target chest range bin and discuss phase-discontinuity handling. A later multiple-range-bin study (PMCID `PMC12031119`) also reports that exploiting concurrent bins can improve robustness over a single-bin choice.

Decision for this project: the next step is **diagnostic instrumentation first**, not a new tracking algorithm. Persist, per analysis window, the selected HR and BR bin/channel, previous selected bin/channel, bin/channel switch indicators, distance jump in bins/meters, selected-bin score/quality, and a phase-discontinuity diagnostic on the selected signal. Run this on a small prespecified representative set. If continuity is already stable, close the gap without algorithm change. Only if discontinuity/switching is frequent and materially associated with HR/BR error should a local-search, neighboring-bin coherence, or multi-bin strategy be considered.

This decision is deliberately conservative because the current task is to establish whether the existing selector is stable enough for the psychology/multimodal use case, not to optimize the radar field generally.

### D-AUDIT-20260830-06 — respiratory-harmonic suppression is scientifically justified, but external RSP must be validation-only, not a production crutch

Respiratory harmonics overlapping the heartbeat band are a well-established radar HR failure mode. Published approaches include adaptive notch filtering (PMCID `PMC8070581`), adaptive harmonic cancellation (PMCID `PMC9693980`), explicit elimination of spectral peaks corresponding to respiratory harmonics (Frontiers in Physiology 2023, DOI `10.3389/fphys.2023.1206471`), improved VME/respiratory-harmonic suppression (IEEE Access 2024, DOI `10.1109/ACCESS.2024.3434952`), SSA-based harmonic removal (Digital Signal Processing 2025, DOI `10.1016/j.dsp.2024.104911`), and spatial/source-separation methods (Sensors 2025, DOI `10.3390/s25041198`). The literature therefore supports treating 2×/3× respiratory contamination as a real HR ambiguity that warrants an explicit mitigation/sensitivity analysis.

Decision for this project: **do not make external BIOPAC/RSP a required production input to the radar HR estimator.** That would make the supposedly standalone radar feature depend on a reference sensor unavailable in deployment and would contaminate the interpretation of mmWave incremental value in multimodal modeling. Instead:

1. keep the formal standalone radar HR path reference-independent;
2. implement/verify an internal radar-derived BR harmonic guard using the same-window radar BR estimate, with explicit uncertainty/tolerance and a fail-safe that does not automatically delete a candidate solely because HR happens to be near an integer multiple of BR;
3. use synchronized external RSP only as a **validation/sensitivity oracle** on the calibration subset: compare current standalone HR, internal radar-BR harmonic guard, and external-RSP-assisted rejection against ECG HR under identical windows;
4. promote the internal guard only if it improves held-out/reference agreement without systematically rejecting true HR values that legitimately lie near 2× or 3× respiration.

This is especially important because a 2024 two-wave-model study (Electronics 2024, DOI `10.3390/electronics13214308`) documents the opposite failure case: a true heartbeat can itself lie at approximately 3× the respiration rate. Therefore a hard rule of “near 2×/3× BR = reject” is not scientifically safe.

### Near-term execution order after this review

`CONTINUITY_INSTRUMENTATION = AUTHORIZED_FOR_DIAGNOSTIC_IMPLEMENTATION`

`HARMONIC_VALIDATION_DESIGN = READY`

`EXTERNAL_RSP_AS_PRODUCTION_DEPENDENCY = REJECTED`

`INTERNAL_RADAR_BR_HARMONIC_GUARD = CONDITIONAL / VALIDATE_BEFORE_PROMOTION`

`HRV = BLOCKED / NOT_NEAR_TERM`

No formal batch, #16, C2B/C2C, NIR/RGB producer change, raw-data modification, or new multimodal model run is authorized by this literature decision alone.

## Next authorized gate

The next action may only be chosen after preserving this audit record. If a future task seeks a scientific rerun, it must first name the exact changed input/semantic question, use the corrected formal distance contract, record the caller and producer commit, and preserve the same session denominator. No rerun follows from this document alone.
