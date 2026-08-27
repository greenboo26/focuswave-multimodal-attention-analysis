# Dataset and Reference Audit V1

Status: **PARTIAL — contract frozen; two source-access/linkage gaps remain**

## AgeBalanced 60 GHz reconciliation

The local package contains 110 participant directories (`P001`–`P110`) and four sessions per participant: Lying/Rest, Sitting/Rest, Lying/Post-exercise and Sitting/Post-exercise. There are 440 radar/ECG sessions in total.

Historical commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1` states “220 sessions”. Its executable discovery expression is equivalent to `P*/**/Rest`, so it selects exactly two Rest sessions per participant: `110 × 2 = 220`. The script comment claiming an all-session count of 440 conflicts with this implementation and is superseded by the file-level mapping.

The frozen provenance file records 2,424 files, 710,626,642 bytes and canonical file-manifest SHA-256 `c737e53e99a2ccebee684df447b7c7233120e96ae692a32c2aaf34afdd248834`. The source `db_records.zip` SHA-256 is `0c4ce2199a611e868d78ab5bf4a43832ad7760c1ae96a28ed56ab29e9f878b43`. All 440 sessions have radar rFFT, radar timestamps, chirp config, Movesense ECG and chest accelerometer; the 220 Rest sessions additionally have a non-breathing marker. Radar is configured at 10 Hz. ECG timestamps imply approximately 250.003 Hz across the package. The per-session mapping and every source-file hash are in `configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json`.

The reference boundary is strict:

- raw ECG: **yes** (`Timestamp`, `mV`);
- source-provided R peaks/beats: **no**;
- raw RSP belt waveform: **no**;
- chest accelerometer: **yes, but not RSP**;
- HR validation: eligible only after independent ECG QC;
- BR validation: `BLOCKED_NO_RSP`;
- HRV: `BLOCKED`.

The data paper states that Movesense raw ECG was recorded for cardiac validation, the chest accelerometer for respiratory motion, and the devices used a common PC clock with a slight systematic delay. That does not convert accelerometry into RSP or remove the need for explicit synchronization and reference QC. Dataset DOI: `10.5281/zenodo.16760683`; paper DOI: `10.1038/s41597-026-07172-9`. The record-specific dataset license remains `MISSING_EVIDENCE`: neither the extracted package nor `db_records.zip` contains a license file, and Phase 2A did not recover trustworthy record metadata. No default Zenodo license is inferred.

## Reference capability matrix

| Dataset | Raw ECG | Source beats/R-peaks | Raw RSP | Other reference | Allowed score after own QC | State |
|---|---:|---:|---:|---|---|---|
| AgeBalanced 60 GHz | yes, ~250 Hz | no; derive and label `derived_events` | no | chest ACC; breath-hold markers in Rest | HR and future beat only; never BR | HR eligible after QC; BR/HRV blocked |
| VS_DATASET healthy | yes, Mindray `ecg_lead2`, 500 Hz expected | no; derive | yes, Mindray `respiration` | pleth/SpO2 fields not used here | HR, beat and BR | `BLOCKED` until clean source inventory/hash access is restored (O-002) |
| VitalSense2024 examples | optional ECG | no | no | no benchmark subject/session metadata | adapter smoke only | SUPPORTING |
| TI/phish-tech ADC | not verified | no | not verified | device engineering streams | no physiological validation | ENGINEERING_ONLY |
| RS6240 ECG/RSP calibration | raw BIOPAC ECG in 11/11 directories, 2,000 Hz | no; derive | raw BIOPAC RSP in 10/11 | digital trigger channels and RS6240 radar | HR in eligible linked sessions; BR only in the 10 RSP sessions | `PARTIAL`; exact raw-to-derived mapping and two ID mismatches unresolved |
| Formal `J:\Data` | no validated ECG/RSP reference in formal sessions | no | no | RGB/NIR/behavior are cross-modal checks, not gold physiology | none in Phase 2A | NOT_ACCESSED / UNAUTHORIZED |

## 2026-08-16 reference workflow adjudication

The 0.5–40 Hz ECG filter, 0.30 s peak distance, 300–2000 ms IBI range, 0.1–0.7 Hz RSP filter, 6–42 rpm range and ≥80% valid-ratio boundary are retained. Two device-generalization changes are frozen before scoring:

1. fixed raw-amplitude prominence is applied after robust median/MAD normalization, because Movesense, Mindray and BIOPAC units/scales differ;
2. adjacent IBI >20% and adjacent respiratory-cycle >17% are flags, not automatic deletions. The project already observed that simple change gates can remove real respiratory sinus arrhythmia or natural breathing variability.

These revisions create `ecg_reference_v1` and `rsp_reference_v1`; old 8/16 outputs remain historical evidence and are not overwritten. Phase 2B must implement and development-test these frozen adapters before any radar score.

## Remaining reference blockers

- `O-002`: VS_DATASET source files and clean per-file hash inventory are not currently recoverable from this checkout.
- `O-006-RS6240`: source inventory is now frozen in `configs/mmwave_reanalysis_v2/rs6240_reference_inventory_v1.json`: 11 directories, 11 raw ECG streams, 10 raw RSP streams, all at 2,000 Hz, and 93.4–98.8 Hz recorded radar frame rates. `sub-2_` has no RSP and cannot score BR. `sub-97795_` contains `97995.acq`, while `sub-97994_` contains `97794.acq`; these two identity mismatches require adjudication. ACQ/meta/timestamp hashes are recorded, but large radar BIN hashes and exact raw-to-derived window linkage remain `MISSING_EVIDENCE`.
- AgeBalanced record-specific license metadata remains `MISSING_EVIDENCE`; this does not change the local hash reconciliation but blocks a complete redistribution/license claim.
