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
| HRV beat-level validation | Radar IBI-shaped fields exist; no ECG R-peak matching. | RMSSD/SDNN could be mistaken for validated physiology. | `MISSING` |
| Caller/provenance consistency | Runner summary uses `breathing_rate`, producer writes `breath_rate`; runner defaults contain legacy roots. | Reports may omit BR or read the wrong local root if rerun carelessly. | `POTENTIALLY_HARMFUL` |
| Independent motion evidence | Current B flags use distance/phase proxies; C uses coverage. | Cannot translate Tier 2 into participant motion/compliance failure. | `MISSING` |

## Interpretation of `33/37/2`

The corrected split is the result of applying existing formal QC/provenance rules with the corrected formal range semantics and retaining existing 067/099 boundaries. It measures the current pipeline's eligibility strata. The split cannot be decomposed from current evidence into “acquisition quality,” “participant cooperated,” “human chest was selected,” and “physiology was valid.” Those are separate claims requiring separate evidence.

## Next authorized gate

The next action may only be chosen after preserving this audit record. If a future task seeks a scientific rerun, it must first name the exact changed input/semantic question, use the corrected formal distance contract, record the caller and producer commit, and preserve the same session denominator. No rerun follows from this document alone.
