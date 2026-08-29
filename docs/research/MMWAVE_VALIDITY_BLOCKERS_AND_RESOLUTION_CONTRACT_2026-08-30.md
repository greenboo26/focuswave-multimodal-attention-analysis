# mmWave validity blockers and resolution contract — 2026-08-30

Status: `DECISION_FROZEN / ECG_QC_COMPLETED_FOR_335_DLL_WINDOWS__NEXT_GATE_WINDOW_LENGTH`

Purpose: record and correct the current mmWave HR validity workflow after review of the latest targeted-validation sequence. This document is canonical for the unresolved validity blockers below. It does not authorize changing raw data, producer outputs, firmware, protected portable V2, or promoting HR/BR/HRV.

## 1. Immediate correction to current interpretation

The pre-QC current DLL-time ARM0/ARM1/ARM2 results (`25.791632 / 22.189492 / 19.189060 bpm` on S0; essentially unchanged on the 333 COMPLETE windows) remain **diagnostic results, not final criterion-validity estimates**. Issue #24 has now completed the required ECG reference-quality layer for these 335 windows: `ECG_VALID=325`, `ECG_INVALID=10`, `UNRESOLVED=0`; ECG_VALID ARM0/ARM1/ARM2 MAE is `25.005 / 21.906332 / 18.904008 bpm`.

Reason: the current rerun removed cross-rest / posture-adjustment / block-boundary periods and excluded incomplete blocks, but it has **not yet demonstrated a frozen, independently defined ECG signal-quality gate that rejects within-block ECG artifact / abnormal R-peak / implausible IBI windows before mmWave-vs-ECG error is computed**.

Therefore:

- `CURRENT_HR_VALIDITY_ESTIMATE = NOT_FINAL`
- `ECG_REFERENCE_QC = COMPLETED_FOR_335_DLL_WINDOWS__325_VALID_10_INVALID_0_UNRESOLVED`
- existing 19–26 bpm MAE values remain provenance for the current diagnostic pipeline and must not be presented as the final scientific accuracy of the mmWave system.

## 2. User/operator protocol facts that must be preserved

1. Rest periods and between-block posture-adjustment periods are not valid continuous-position physiology segments. Continuity must reset at block boundaries; cross-rest transitions are invalid evidence.
2. ECG is not assumed usable for the full recording. Within otherwise valid blocks, visibly/algorithmically abnormal ECG segments, unstable R-peak detection, implausible IBI behavior, or other independently defined ECG-quality failures must be rejected before criterion-validity scoring.
3. No assumption may be made that all three currently targeted sessions are fully valid end-to-end.
4. Formal acquisition used controlled posture/distance instructions; participant movement cannot be inferred from radar phase/bin instability without independent motion evidence.

## 3. The 20 s window is not a validated HR window contract

Lineage:

- The first targeted continuity diagnostic used the first 6000 frames per session and five overlapping windows: `0–2000`, `1000–3000`, `2000–4000`, `3000–5000`, `4000–6000` frames, reported as 20 s windows with 10 s step at 100 Hz.
- The later block-reset rerun inherited `20 s window / 10 s step / 5 s boundary guard` from that continuity diagnostic.

This 20 s setting was selected for target/bin/channel continuity diagnostics. It was **not** established as the scientifically optimal or canonical HR estimation duration by the historical 3.777 bpm pipeline or by a frozen literature-derived contract.

Therefore:

- `20S_HR_WINDOW_JUSTIFICATION = UNRESOLVED`
- 20 s must not be treated as the default formal HR validity window without a controlled window-length comparison.
- Historical 60 s probe behavior and the historical fixed-target pipeline must be reused as a reference implementation rather than silently replaced by a new 20 s estimator semantics.

## 4. Distance gate is not frozen and must not use the historical gate as current physical truth

Known facts:

- Corrected distance uses `distance_m = bin × 0.037`.
- Historical 3.777 bpm lineage used a `0.30–1.50 m` gate.
- Current acquisition geometry/operator discussion has considered a much nearer admissible range (including approximately 0/0.20 m to 1.0 m); the exact current physical gate must be resolved from current protocol/evidence, not imported from the historical gate.
- The formal extreme-range audit found persistent near-side bright structure, but its conservative conclusion was `RISK_NOT_SUPPORTED`: it did not establish that <0.30 m targets are near-field/direct-leakage artifacts, nor that >1.50 m targets are fixed-environment reflections.

Therefore:

- historical `0.30–1.50 m` results are `HISTORICAL_GATE_SENSITIVITY`, not proof of current physical gate correctness;
- statements such as “outside 0.30–1.50 m means non-human/invalid target” are revoked;
- the current distance gate may only be frozen after an ECG/RSP-quality-controlled distance-vs-error analysis plus front-end physical evidence.

Required distance analysis must preserve the same estimator/reference/QC and report at minimum: distance bands (including <0.20, 0.20–0.30, 0.30–0.60, 0.60–1.00, >1.00 as data permit), continuous distance-vs-absolute-error behavior, participant/session/block composition, target stability, coverage, HR MAE/median AE/bias/correlation and BR error where valid. Thresholds must not be selected by looking for the best HR result.

## 5. Near-field strong structure: observed, cause unresolved

Formal front-end audit already established that all groups can show persistent near-distance bright structure. It did **not** establish that this structure is direct leakage, near-field artifact, the participant, or another fixed reflection because session-level radar-to-body ground-truth position was unavailable.

Thus:

- `NEAR_SIDE_STRONG_STRUCTURE = OBSERVED`
- `NEAR_FIELD_DIRECT_LEAKAGE_CAUSE = UNRESOLVED`
- `NEAR_FIELD_EXCLUSION_GATE = NOT_AUTHORIZED`

This question must be resolved with current acquisition geometry/protocol evidence and, where possible, independent physical/target evidence before using near-distance exclusion as a scientific QC gate.

## 6. Harmonic / peak-selection validity is still unresolved

The current formal code path contains internal heuristic handling, while the optional external-RSP 2×/3× harmonic check is inactive in standard formal execution because the runner does not pass the required external-RSP inputs. This does **not** mean no respiratory/harmonic logic exists; it means the current internal logic has not yet been proven sufficient on the formal validation windows.

Required spectral truth audit, after ECG/RSP QC is frozen:

- mark ECG HR true frequency for each valid window;
- mark radar BR and candidate 2×/3× respiratory harmonics;
- inspect the selected radar HR peak and the strongest competing peaks;
- determine separately whether failures are caused by target/bin/channel selection, absence/low SNR of the ECG-aligned heart peak, or downstream peak/harmonic mis-selection;
- external RSP may be used as a diagnostic oracle/sensitivity only, not silently promoted to a production dependency.

## 7. Coverage result remains valid but is not the HR explanation

DLL-time coverage audit is retained:

- COMPLETE=333, PARTIAL=0, SEVERELY_INCOMPLETE=2;
- the two severe windows are localized to `97795/block4` tail;
- S0/S1/S2 HR metrics are nearly unchanged.

Therefore `COVERAGE_NOT_PRIMARY_HR_EXPLANATION` remains supported. The `97795/block4` tail still requires acquisition-integrity closure but does not block the independent ECG-QC / window / distance / spectral-validity analyses.

## 8. Required resolution order (no tuning shortcuts)

The next mmWave validity work must execute in this order:

1. **ECG reference-quality audit and frozen QC contract — COMPLETED FOR CURRENT 335 DLL-TIME WINDOWS**
   - reuse historical validated ECG preprocessing/QC where available;
   - identify and exclude rest/posture/boundary periods (already structurally excluded) and within-block ECG artifact independently of radar error;
   - output explicit valid/rejected windows with reasons;
   - recompute ARM0/ARM1/ARM2 only on the ECG-valid denominator.
   - evidence: `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_REFERENCE_ELIGIBILITY_REPORT_2026-08-30.md` and `ECG_ELIGIBILITY_MANIFEST.json`.

2. **Window-length provenance and controlled comparison**
   - trace the historical 60 s implementation exactly;
   - compare 20 s against scientifically defensible longer windows on the same valid data using unchanged target/estimator conditions where possible;
   - do not call 20 s canonical unless justified.

3. **Near-field / distance-vs-accuracy audit**
   - resolve current acquisition geometry evidence;
   - quantify whether distance materially changes ECG/RSP-valid accuracy;
   - only then freeze or reject a physical distance gate.

4. **Spectral truth / harmonic / peak-selection audit**
   - compare ECG truth frequency, radar candidate peaks, BR harmonics and final selected peak;
   - classify failure mechanism without tuning thresholds to the answer.

5. **Final validity decision**
   - only after steps 1–4 may HR be classified as validated, limited/supporting, or failed for this formal dataset;
   - HRV remains `BLOCKED` until radar beat ↔ ECG R-peak synchronization and paired IBI agreement are demonstrated;
   - BR/RR remains `HOLD` until its own reference-quality validation is closed.

## 9. Reuse / no-rebuild rule

Do not create a replacement physiology pipeline from scratch when a historical validated/reference implementation already exists. Reuse and trace the historical 3.777 bpm lineage, existing ECG/RSP reference code, current producer code, and existing literature evidence. Any adaptation must be explicitly labeled and compared against the original semantics.

No estimator, target rule, harmonic threshold, distance gate, or QC threshold may be tuned using the same ECG error values that are later reported as validation.

## 10. Current status

- `ECG_REFERENCE_QC`: `COMPLETED_FOR_335_DLL_WINDOWS / 325_VALID / 10_INVALID / 0_UNRESOLVED`
- `20S_HR_WINDOW`: `DIAGNOSTIC_LINEAGE_CONFIRMED / SCIENTIFIC_JUSTIFICATION_UNRESOLVED`
- `DISTANCE_GATE`: `NOT_FROZEN`
- `NEAR_FIELD_CAUSE`: `UNRESOLVED`
- `HARMONIC_PEAK_SELECTION_VALIDITY`: `UNRESOLVED`
- `DLL_FRAME_TIME`: `FROZEN`
- `DLL_COVERAGE`: `COVERAGE_NOT_PRIMARY_HR_EXPLANATION`
- `HR`: `HOLD / CURRENT_MAE_NOT_FINAL_VALIDITY_ESTIMATE`
- `BR/RR`: `HOLD`
- `HRV/IBI`: `BLOCKED`
- Issue #16: `PAUSED`

Any newer result that addresses one of these items must update this contract and the canonical status/ledger in the same work cycle.
