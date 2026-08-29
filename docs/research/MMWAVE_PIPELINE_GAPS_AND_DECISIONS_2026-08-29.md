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

### D-AUDIT-20260830-05 — instrument and audit target continuity; do not freeze one bin forever

Literature consistently treats range-bin choice as a first-order vital-sign problem. Choi et al. (IEEE Access 2021, DOI `10.1109/ACCESS.2020.3043013`; open metadata: https://doaj.org/article/94f8211fcdaa4edf8fe10924a8dbb1df) show that precise target range-bin selection materially changes respiration/heartbeat accuracy. Choi et al. (Applied Sciences 2021, DOI `10.3390/app11104514`; full text: https://www.mdpi.com/2076-3417/11/10/4514) use spatial phase coherency across neighboring bins and explicitly note range-bin tracking as a stability improvement. Xue et al. (Measurement 2023, DOI `10.1016/j.measurement.2023.113715`; abstract: https://www.sciencedirect.com/science/article/abs/pii/S0263224123012794) use local search plus moving-average filtering to obtain each target chest range bin. A 2025 multi-bin study (PMCID `PMC12031119`; full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC12031119/) reports better HR and BR accuracy when multiple concurrent bins are used rather than a single-bin choice.

Plain-language interpretation fixed for this project: **the proposal is not “pick one bin at the beginning and never move again.”** A `bin` is one distance slot. If the chest-related reflection is around bin 20, a continuity-aware method can use the previous window as a prior and preferentially search around bin 19–21/22 in the next window, while still allowing a larger move when evidence strongly supports it. The scientific goal is to avoid implausible window-to-window jumping, not to prohibit real target drift.

Conceptual example only:

`window 1: bin 20 -> window 2: first examine nearby bins 19–21 -> choose 20 or 21 if supported; do not automatically jump to bin 37 merely because its instantaneous score is slightly larger.`

This is a tracking prior, not a hard lock. A hard fixed-bin policy could itself become wrong if posture, breathing geometry, or the dominant body reflection shifts.

Decision for this project: the next scientific test, if separately authorized, is a **small controlled continuity strategy comparison**, not a full radar redesign. Compare the current independent-window selector against one or more conservative alternatives such as local-neighborhood continuity, neighboring-bin phase coherency, or multi-bin aggregation on exactly the same ECG-referenced windows. Do not promote any method unless it improves reference agreement. This is distinct from the completed diagnostic instrumentation; the targeted validation has already shown that current independent-window selection switches frequently.

### D-AUDIT-20260830-06 — respiratory-harmonic suppression is scientifically justified, but external RSP must be validation-only, not a production crutch

Respiratory harmonics overlapping the heartbeat band are a well-established radar HR failure mode. Published approaches include adaptive notch filtering (PMCID `PMC8070581`), adaptive harmonic cancellation (PMCID `PMC9693980`), explicit elimination of spectral peaks corresponding to respiratory harmonics (Frontiers in Physiology 2023, DOI `10.3389/fphys.2023.1206471`), improved VME/respiratory-harmonic suppression (IEEE Access 2024, DOI `10.1109/ACCESS.2024.3434952`), SSA-based harmonic removal (Digital Signal Processing 2025, DOI `10.1016/j.dsp.2024.104911`), and spatial/source-separation methods (Sensors 2025, DOI `10.3390/s25041198`). The literature therefore supports treating 2×/3× respiratory contamination as a real HR ambiguity that warrants an explicit mitigation/sensitivity analysis.

Decision for this project: **do not make external BIOPAC/RSP a required production input to the radar HR estimator.** That would make the supposedly standalone radar feature depend on a reference sensor unavailable in deployment and would contaminate the interpretation of mmWave incremental value in multimodal modeling. Instead:

1. keep the formal standalone radar HR path reference-independent;
2. only revisit harmonic suppression after target continuity is stabilized enough to make the input signal interpretable;
3. then compare candidate harmonic-handling approaches against ECG on identical windows;
4. use synchronized external RSP only as a validation label/oracle, never as a required deployed input;
5. promote a harmonic method only if it improves ECG agreement without systematically rejecting true HR values that legitimately lie near 2× or 3× respiration.

A 2024 two-wave-model study (Electronics 2024, DOI `10.3390/electronics13214308`) documents the opposite failure case: a true heartbeat can itself lie at approximately 3× the respiration rate. Therefore a hard rule of “near 2×/3× BR = reject” is not scientifically safe.

### Why continuity comes before harmonic tuning — plain-language fixed explanation

The processing order is important:

1. **Choose what body reflection to follow.** This is target/bin/channel selection. If this changes arbitrarily between windows, the algorithm may be listening to a different reflection each time.
2. **Check whether the signal from that followed target is temporally coherent.** `Phase` is the wave-cycle position; tiny chest motion changes phase. Here “phase continuity” means asking whether the signal evolves smoothly enough across adjacent windows after following approximately the same target.
3. **Only then tune heartbeat-versus-respiration separation.** `Respiratory harmonic` means a multiple of the breathing rhythm, e.g. breathing 18/min can create strong components around 36/min or 54/min. Some of these can overlap the heart-rate search band and be mistaken for heartbeat.
4. **Finally compare radar HR with ECG.** ECG is the external reference used to decide whether the changed radar method actually became more accurate.

If step 1 is unstable, changing step 3 can be misleading because the algorithm is trying to remove harmonics from a signal source that may itself change from window to window. Therefore the decision is not “all upstream preprocessing is wrong”; it is “the already-corrected data semantics remain valid, but target continuity now becomes the next testable algorithmic bottleneck.”

### Near-term status after targeted validation

`CURRENT_INDEPENDENT_WINDOW_SELECTOR = FAILED_CONTINUITY_ON_TARGETED_SAMPLE / HOLD`

`HARD_FIXED_BIN_FOR_WHOLE_SESSION = NOT_RECOMMENDED`

`CONTINUITY_AWARE_LOCAL_OR_MULTI_BIN_COMPARISON = CANDIDATE_NEXT_TEST / NOT_YET_AUTHORIZED`

`EXTERNAL_RSP_AS_PRODUCTION_DEPENDENCY = REJECTED`

`CURRENT_INTERNAL_RADAR_BR_GUARD = NOT_PROPOSED_FOR_PRODUCER`

`HRV = BLOCKED / NOT_NEAR_TERM`

## Next authorized gate

The next action may only be chosen after preserving this audit record. If a future task seeks a scientific rerun, it must first name the exact changed input/semantic question, use the corrected formal distance contract, record the caller and producer commit, and preserve the same session denominator. No rerun follows from this document alone.

## 2026-08-30 targeted validation closure

### D-AUDIT-20260830-07 — continuity diagnostic is complete but does not pass the physiological feature gate

The authorized diagnostic was run on `97793`, `9779`, and `97795`, using only frames 0–5999 and five overlapping 20-second windows per session. Across 12 adjacent transitions, HR bin hops were 8/12, BR bin hops 9/12, HR channel switches 11/12, and BR channel switches 9/12. No transition retained the same HR bin/channel pair for a directly comparable raw phase boundary diagnostic. Independent motion evidence was not present, so these switches cannot be attributed to participant movement.

Decision: the continuity question is now measured for the representative set, but it is not stable enough to promote HR or BR/RR as formal physiological merge features. Keep the continuity table as diagnostic QC, mark HR and BR/RR `HOLD`, and do not introduce a tracker, target-lock redesign, AoA, beamforming, multi-bin search, or full-batch rerun in this cycle.

### D-AUDIT-20260830-08 — targeted harmonic A/B/C does not justify a producer change

The same 15 elapsed-time windows were compared against `.acq` ECG/RSP references. A is the current standalone radar result. B uses radar-derived BR only with a ±5 bpm 2x/3x guard and a radar-time fallback only when non-harmonic. C uses external RSP only as a diagnostic oracle. B triggered zero times and was identical to A (MAE 9.392 bpm; p95 absolute error 27.664 bpm); C marked three external-RSP 3x windows where A/B harmonic-window MAE was 27.336 bpm versus 4.907 bpm in the 12 non-harmonic windows.

Decision: B is `NOT_PROPOSED_FOR_PRODUCER` from this targeted set. External RSP remains `VALIDATION_ONLY`; its observed harmonic relation cannot be used as a production input or as proof of physiology validity. HRV remains blocked and no new beat-level work is authorized by this result.

### D-AUDIT-20260830-09 — merge-ready contract frozen with conservative feature dispositions

The canonical integration contract is frozen for the read-only portable V2 target: structural missing/loadability metadata is `ALLOW`; HR, BR/RR, continuity QC, phase-stability QC, and motion/QC proxy are `HOLD` with explicit diagnostic-only semantics; HRV/IBI and external ECG/RSP values are `EXCLUDE`. `missing != 0 != success`, HR/RR remain separate, and no external reference value enters the final mmWave feature table. This closes the ordered task as `PASS / MMWAVE_MERGE_READY_CONTRACT_FROZEN` without upgrading any physiological claim.
