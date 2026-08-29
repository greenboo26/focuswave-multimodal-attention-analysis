# Formal mmWave producer/downstream line-by-line scientific audit

Audit date: 2026-08-29
Canonical repository: `greenboo26/focuswave-multimodal-attention-analysis@main`
Audit base: `3d4c073f98ddb0ef86e0e3a5c3f99b048610a0d8`
Overall status: **PASS as an evidence audit; `PIPELINE_SCIENTIFIC_AUDIT=PASS`, while physiological validity remains bounded and Issue #16 remains PAUSED.**

This document audits the existing formal mmWave path without rerunning a scientific model, changing source code, changing raw data, reopening C2B/C2C, or running Issue #16. The audit uses the recovered RS6240 evidence rather than restarting generic firmware/manual discovery.

## 1. Scope, evidence hierarchy, and recovered upstream facts

The audited downstream entry is `scripts/process_vital_signs_v3_1_1.py`, called by `scripts/run_timeline_gated_mmwave_quality.py`; signal-existence QC is separately implemented by `scripts/scan_timeline_gated_quality.py`. Formal QC tiering is a read-only interpretation of existing manifests and target-lock outputs, not a new physiology run.

Evidence hierarchy used:

1. exact formal firmware image and its hash;
2. matching firmware/source/configuration evidence;
3. official RS6240 SDK/manual implementation evidence;
4. formal output semantics and numerical consistency;
5. historical project notes, used only as provenance.

The recovered primary local evidence is:

- formal image: `D:\Project\厚粲杯\04_硬件\05_硬件使用\RS6x_7x_mmWave_sdk_V2.1.0\Software_Kit\04_Image\mrs6240_p2512.img`;
- observed SHA-256: `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`;
- observed file size: 233,280 bytes; recorded build string: `2026-07-24 21:33:39`;
- prior audit package: `docs/results/2026-08-29_RS6240距离与DataCube审计_v1/2026-08-29_FORMAL_FIRMWARE_RUNTIME_MODE_AUDIT.md` and `2026-08-29_RS6240_SDK_RANGE_MAPPING_AUDIT.md`;
- official SDK/manual root: `D:\Project\厚粲杯\04_硬件\05_硬件使用\RS6x_7x_mmWave_sdk_V2.1.0`;
- SDK/manual items already inspected: `RS6x_7x_SDK_参考手册_V1.2.pdf`, `RS6x_7x_HIF_参考手册_V1.0.pdf`, `HifMsgDataCollectionLib_使用说明_V1.1.txt`, `ReportDataCube1D/src/main.c`, `radar_framework.h`, `radar_framework.c`, `radar_framework_report.c`, and `prj_config.h`;
- exact formal output evidence: formal NPZ keys `tx0_rx0` through `tx1_rx3`, arrays shaped `[frames, 256]`, and PSIC/DataCube records with 2T4R/256/37 mm metadata.

The formal image comparison with the adjacent ADC experiment image located `fft_mode` at binary offset `0x37918`: formal image `2` (`RADAR_FRAMEWORK_2DFFT_MODE`), ADC experiment image `0` (`RADAR_FRAMEWORK_ADC_MODE`). For the 1D frame type, the SDK enum/comment means range FFT is retained and Doppler FFT is not added. This binds the formal stored data to a 1D range-domain DataCube; it does not bind every generic SDK default to the exact image.

## 2. Upstream recovery matrix

The complete machine-readable version is `MMWAVE_LITERATURE_VS_PROJECT_STAGE_MATRIX_2026-08-29.csv`.

The field-complete companion for each audited executable block is `MMWAVE_FORMAL_PIPELINE_AUDIT_FIELDS_2026-08-29.csv`. It preserves the required file/line, shape/type, operation, purpose, literature, parameter/source, empirical validation, omission/duplication risk, respiration/heartbeat attenuation, harmonic, bin-hopping, phase-discontinuity, distance-dependency, and status fields without collapsing them into prose.

| Stage/fact | Recovered fact | Formal binding status | Remaining boundary |
|---|---|---|---|
| ADC/IF acquisition | Formal stored NPZ is not raw ADC; it is downstream of the device DataCube/report path. | `PRIOR_AUDIT_CONFIRMED_NEEDS_PRIMARY_RELINK` | Exact one-to-one source-build manifest for the image is absent. |
| Range transform | Formal image has `fft_mode=2`; output semantics are stable 256-point range bins. | `CONFIRMED_IN_FORMAL_FIRMWARE` | Exact window implementation and firmware source commit remain unbound. |
| Range spacing | Formal image/config and output records support `0.037 m/bin`. | `CONFIRMED_IN_FORMAL_FIRMWARE` | No independently verified range bias; use zero bias only as an explicit assumption. |
| Doppler | 1D frame plus `2DFFT_MODE` does not create a Doppler dimension in this report path. | `CONFIRMED_IN_FORMAL_FIRMWARE` | This does not establish any hidden internal chirp accumulation behavior. |
| DC/static clutter | The inspected ReportDataCube1D source config showed clutter removal `NONE`; no exact-image build manifest proves this field for every deployment. | `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY` | Exact deployed setting and undocumented library behavior remain open. |
| Windowing | No auditable ReportDataCube1D source call or exact-image parameter was recovered. | `UNRESOLVED` | Do not claim rectangular, Hann, or any other window. |
| Zero padding/cropping | `range_fft_len_log2=8` establishes 256 as the configured range length. | `CONFIRMED_IN_FORMAL_FIRMWARE` for length; `UNRESOLVED` for padding/cropping | A 256-point output does not alone prove zero-padding absence. |
| Chirp aggregation | Source/config history records one-chirp configuration (`acc_num_log2=0`), but exact image/source binding is incomplete. | `PRIOR_AUDIT_CONFIRMED_NEEDS_PRIMARY_RELINK` | Coherent/noncoherent implementation inside precompiled libraries is not independently proven. |
| Channel mapping | Eight logical arrays preserve `2 TX × 4 RX` ordering in output. | `CONFIRMED_BY_OUTPUT_SEMANTICS` | Physical antenna coordinates, phase convention, and calibration are not closed. |
| Normalization/scaling | SDK conversion yields complex arrays; `complex128`/`complex64` is a container type, not a physical amplitude unit. | `UNRESOLVED` | No formal amplitude calibration or scale contract was found. |
| Channel calibration/phase correction | Official material discusses calibration, but the exact formal output path does not prove it was applied. | `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY` | Do not interpret eight-channel phase as calibrated geometry. |
| Report packing | `0xC2` DataCube payload → `DatacubeConversion` → eight Tx/Rx arrays is directly supported by producer source and output schema. | `CONFIRMED_BY_OUTPUT_SEMANTICS` | Raw payload bit-level meaning and firmware-internal corrections remain outside the stored NPZ. |

## 3. Downstream logic-block audit

Status vocabulary here is restricted to the task contract: `MATCHED`, `PROJECT_VARIANT`, `HEURISTIC`, `MISSING`, `POTENTIALLY_HARMFUL`, `NOT_REQUIRED`, `UNRESOLVED`.

### 3.1 Ingestion, target selection, and phase

| Code block | Operation and shapes | Scientific role and literature relation | Parameters/source | Risks and status |
|---|---|---|---|---|
| `process_vital_signs_v3_1_1.py:1099-1112` | Load NPZ `tx*` arrays, sort keys, stack to `[frame, range-bin, channel]`, cast to `complex64`; `_as_range_cube()` is identity. | Correctly consumes the recovered range-domain output; there is no downstream raw-ADC FFT. This matches the recovered upstream semantics and avoids double range FFT. | 8 channels; array shape from output audit. | If an incompatible NPZ is supplied, failure occurs at the producer boundary. `MATCHED`. |
| `process_vital_signs_v3_1_1.py:1115-1143` | Sorted chunk discovery and global frame slicing across chunks. | Provides deterministic segment input and behavior-time frame selection. | Glob order; `frame_start/frame_end`. | Does not validate frame IDs against timestamp continuity; chunk/frame mismatch can shift analysis. `PROJECT_VARIANT`. |
| `process_vital_signs_v3_1_1.py:1146-1172` | Mean `|z|²` over selected frames, first as bin×channel profile and then channel totals. | Range-profile localization is a standard prerequisite, but energy is not human/chest identity. | Full selected segment; no clutter subtraction. | Stationary reflector dominance; no DC/static/IQ correction; can suppress weak heartbeat target. `PROJECT_VARIANT`. |
| `process_vital_signs_v3_1_1.py:2500-2517, 2813-2845` | Map `distance=bin×spacing-bias`; zero out bins outside gate before selection. | A range gate is a valid engineering constraint only when the axis is bound. | Default `0.30-1.50 m`, `0.08 m/bin`, bias `0`. Formal spacing is `0.037 m/bin`. | **Materially harmful semantic mismatch**: the same gate means bins 4-18 under 0.08 m/bin versus bins 9-40 under 0.037 m/bin. Can admit near reflectors and exclude human bins. `POTENTIALLY_HARMFUL`. |
| `process_vital_signs_v3_1_1.py:1194-1233` | Per channel: retain bins ≥1% of max power; phase variance gate/fallback; detrend unwrapped phase; raw FFT power; BR/HR SNR; stability-weighted scores. | A project-specific signal-quality heuristic. Literature supports target-range selection as a critical problem, but not this score as human/heart localization. | `phi_var 0.1-50`; noise 2.5-5 Hz; HR 0.8-2 Hz; BR 0.1-0.5 Hz; `BR=snr×stability`, `HR=log1p(snr)×stability²`. | Respiratory harmonic can score as HR; candidate pool can contain environment/static reflectors; no reference validation at selection. `HEURISTIC`. |
| `process_vital_signs_v3_1_1.py:1374-1412` | Independently choose BR bin/channel and HR bin/channel over all eight channels. | Channel-wise quality competition is a project variant, not calibrated beamforming or target identity. | Optional `channel_override`; otherwise all channels. | BR and HR may come from different physical paths; switching across independently processed segments can create phase discontinuity. No spatial calibration. `POTENTIALLY_HARMFUL`. |
| `process_vital_signs_v3_1_1.py:1415-1439` | BR phase is concatenated then unwrapped; HR uses `5 mm×phase/(4π)` from selected complex bin. | Phase-based displacement is a standard FMCW vital-sign representation; the formula assumes wavelength and phase convention are appropriate. | `WAVELENGTH_MM=5.0`; one selected bin/channel per segment. | No explicit upstream phase calibration; bin changes are not tracked; phase continuity is only guaranteed within each concatenated segment. `PROJECT_VARIANT`. |
| `scan_timeline_gated_quality.py:31-85` | For each baseline/block, reselect HR bin/channel, then per chunk unwrap, detrend, HR-bandpass, and compute 10-s standard deviation. | Useful signal-existence screening, not physiology validity. | `0.0005 mm`; pass/partial/fail at 0.80/0.50 usable ratio. | Per-part unwrap reset and no BR output; can label a stable but wrong harmonic as present. `PROJECT_VARIANT`. |

### 3.2 Respiration branch

| Code block | Operation and shapes | Scientific role and literature relation | Parameters/source | Risks and status |
|---|---|---|---|---|
| `process_vital_signs_v3_1_1.py:642-679` | Compare (A) detrend+4th-order zero-phase 0.10-0.50 Hz bandpass with (B) detrend+first difference+5-sample moving mean+same bandpass; retain higher heuristic score. | Respiration extraction and drift control are expected; the two-branch selection is a project variant. | SOS Butterworth order 4; linear detrend; moving mean 5. | First difference can attenuate very slow respiration and alter phase/amplitude; zero-phase filtering is offline-only. `PROJECT_VARIANT`. |
| `process_vital_signs_v3_1_1.py:397-525, 528-574` | Savitzky-Golay/autocorrelation time candidates; Hann periodogram candidates; close-to-time selection; half-harmonic rule; robust peak sweep/repair. | Multi-domain agreement is reasonable as a descriptor; it is not independent validation. | 6-30 bpm; SG window 0.35 s; spectral proximity 0.08 Hz; half rule top ≥0.22 Hz, ±0.04 Hz, ≥35% power; six prominence factors. | Peak repair can invent a beat/breath at an expected location; no BR hard gate; harmonic logic is heuristic. `HEURISTIC`. |
| `process_vital_signs_v3_1_1.py:2379-2497` | Emit one full-segment `breath_rate.freq_bpm`, `time_bpm`, peak count, and high/medium/low confidence. | A descriptive BR estimate; reference literature requires paired reference agreement for validity. | Confidence from frequency/time gap ≤2/≤5 bpm. | Low-confidence BR is not nulled; output schema is not a physiological pass. `POTENTIALLY_HARMFUL`. |
| `run_timeline_gated_mmwave_quality.py:70-108` | Copies producer summaries after optional segment analysis. | Integration layer only. | Current code reads `result.get("breathing_rate", {})`; producer writes `breath_rate`. | BR summary can be empty in the batch report despite producer output. This is an implementation traceability defect. `POTENTIALLY_HARMFUL`. |

### 3.3 Heart branch, harmonic handling, and time/frequency fusion

| Code block | Operation and shapes | Scientific role and literature relation | Parameters/source | Risks and status |
|---|---|---|---|---|
| `process_vital_signs_v3_1_1.py:273-275, 2379-2405` | Detrended selected displacement is 4th-order zero-phase HR bandpass 0.8-2.0 Hz; optional VMD branch follows. | HR-band isolation and phase processing are common; exact filter is a project variant. | 48-120 bpm; SOS Butterworth order 4. | Fixed band excludes atypical HR and does not distinguish cardiac from respiratory harmonics. `PROJECT_VARIANT`. |
| `process_vital_signs_v3_1_1.py:305-394, 1296-1371` | VMD with K=3, alpha=1000; mode selection by HR-band power and optional band-frequency hint; overlapping 40-s windows/20-s steps tapered and averaged. | Decomposition is a method choice, not a universal standard. Literature supports separation but requires validation. | `K=3`, `alpha=1000`, `tau=0`, `tol=1e-6`; 40/20 s. | A mode can be respiration-heart mixed; VMD can attenuate true heartbeat or retain harmonic; overlap averaging smooths but cannot restore lost events. `PROJECT_VARIANT`. |
| `process_vital_signs_v3_1_1.py:1244-1293` | Sweep peak prominence; constrain IBI to 0.5-1.25 s; retain regularity-scored peaks; remove intervals outside 0.3-3× reference. | Peak timing is needed for beat candidates, but candidate peaks need ECG-level validation before HRV. | Seven prominence factors; `FS=100 Hz`. | Regularity can reward a stable wrong harmonic; no morphology or ECG beat alignment. `HEURISTIC`. |
| `process_vital_signs_v3_1_1.py:1800-1944` | Optional external scalar RSP prior rejects HR candidates near 2×/3× BR; other reference/time harmonic folding changes spectral value. | Literature supports explicit respiratory-harmonic handling; this code is conditional and not equivalent to adaptive validated suppression. | External RSP tolerance ±5 bpm; harmonics 2/3; internal reference tolerances 3-8 bpm. | Formal runner does not pass `acq_path`, so the external RSP branch is not active in the standard formal batch. Without it, harmonic handling is mainly post-hoc/reference-dependent. `POTENTIALLY_HARMFUL`. |
| `process_vital_signs_v3_1_1.py:1947-2239` | 20-s/10-s segment spectral candidates, time candidates, reference-driven harmonic correction, cluster median/fusion. | Temporal consistency is a useful robustness descriptor; it is not independent truth. | 20/10 s; cluster tolerance 6 bpm; at least 5 records for cluster substitution. | Reference/previous estimates can propagate a wrong anchor; cluster selection may hide bin/phase failures. `HEURISTIC`. |
| `process_vital_signs_v3_1_1.py:857-1072` | 25-s/5-s time/frequency estimates; weighted fusion, warning at >10 bpm, interpolation/median/forward-backward smoothing. | Agreement and missingness should be reported; smoothing is a project reporting choice. | 25/5 s; warning 10 bpm; high/usable thresholds 5/12 bpm, confidence .50/.20; max step 7 bpm. | Interpolation/smoothing can make an unstable course look continuous; hard-rejected windows are restored to missing, but no target identity is added. `POTENTIALLY_HARMFUL`. |

### 3.4 QC, HRV, reference, and formal tier interpretation

| Code block | Operation and shapes | Scientific role and literature relation | Parameters/source | Risks and status |
|---|---|---|---|---|
| `process_vital_signs_v3_1_1.py:907-918, 1033-1062, 2416-2422` | 10-s HR waveform SD gate; reject HR if usable ratio <0.50; rejected HR becomes missing. | Acquisition/signal-existence QC is necessary but cannot establish physiology validity. | SD ≥0.0005 mm; usable ratio ≥0.50. | Correctly prevents weak HR output, but can be mistaken for HR accuracy; no analogous BR hard gate. `PROJECT_VARIANT`. |
| `process_vital_signs_v3_1_1.py:2430-2442` | Gate peaks to usable HR windows; IBI = adjacent retained peak intervals; 300-2000 ms filter; compute SDNN/RMSSD/mean IBI. | This is a mathematical HRV-shaped output, but literature requires true beat timing and ECG beat-level agreement. | At least 4 gated peaks/IBIs; 300-2000 ms. | No ECG R-peak matching, beat sensitivity/precision, ectopy protocol, or paired IBI agreement. Claiming validated HRV would be harmful. `POTENTIALLY_HARMFUL`. |
| `analyze_acq_reference.py:95-128, 200-230` and `validate_gold_anchor.py` reference path | Independently clean ECG/RSP and align by timestamps/markers for small calibration/reference sets. | Appropriate reference direction; correlation alone is insufficient, and the small calibration set cannot validate the 70-session cohort. | ECG/RSP window rules and Unix-time mapping are separately recorded. | Reference code does not turn producer HRV into ECG-aligned radar IBI; denominators differ. `MATCHED` for reference role, not producer validation. |
| `scripts/maintenance/build_formal_vital_qc_v1.py` and existing QC manifests | Tier 1/2/3 combine coverage, target-lock flags, linkage/provenance, and existing output. | A transparent eligibility stratification is appropriate if labeled as pipeline/QC status. | Corrected 37 mm semantics; current `33/37/2`; 067/099 boundaries retained. | B/C flags are not participant motion, acquisition quality, HR/RR accuracy, or HRV validity. `PROJECT_VARIANT`. |
| `docs/results/2026-08-29_BR管线与极端距离审计_v1/2026-08-29_BR_PIPELINE_CODE_TRACE.md` and current callers | Separate producer, scanner, stored-output comparison, and RSP-prior paths. | Preserves denominator and caller differences. | `J:\Data` formal root in paths config; runner defaults still contain legacy E/F roots. | A caller can report different semantics from the producer; path defaults and `breath_rate` key mismatch require operational correction before future reruns. `POTENTIALLY_HARMFUL`. |

## 4. Answers to the required scientific questions

### 4.1 What does target selection seek?

It is a **mixed signal-quality heuristic**, not a strongest-reflector detector and not a human/chest/respiration/heartbeat target detector. Mean return power establishes candidate eligibility; phase variance, HR/BR-band spectral ratios, and phase-stability scores then select BR and HR independently. `auto_best_channel` is a diagnostic power argmax and is not necessarily the selected physiology channel. No chest geometry, angle-of-arrival, calibrated beamforming, or ECG-backed target identity is used.

### 4.2 Can switching create phase discontinuities?

Yes. The producer selects one BR and one HR bin/channel for each caller-provided segment. Different baseline/block calls can select different pairs, and the scanner independently reselects per segment. No range-bin tracking, cross-bin phase stitching, or transition QC is implemented. Within one extracted segment, phase is unwrapped after concatenation; that does not protect continuity across separately selected segments. `_scan_quality`-style historical scanning can additionally reset unwrap at NPZ-part boundaries. Participant stillness therefore cannot by itself rule out algorithmic phase discontinuity.

### 4.3 Which failures have independent motion evidence?

The current `33/37/2` formal tiering does not contain independent motion evidence. The existing phase-stability field is a phase roughness/jump proxy; it is not a motion-artifact ratio. Distance-implausible flags are range-semantics/target-candidate flags, not proof of body motion. Window/probe coverage failures are pipeline success/availability flags, not proof of motion or physiology failure. Timestamp/frame continuity and missing-linkage fields are acquisition/data-integrity evidence, but do not identify the cause of a physiological estimate failure. Thus current formal failures are predominantly mixed pipeline-eligibility strata with unresolved local causes.

### 4.4 Does HR actively suppress respiratory harmonics?

Not in the standard formal batch as a fully active, time-varying suppression stage. The code contains a conditional external RSP scalar prior that can reject 2×/3× BR candidates, and reference/time-domain harmonic folding. However, the standard formal runner does not pass `acq_path`; it therefore does not activate the external RSP path. The ordinary HR band/VMD/peak route can still lock onto a stable respiratory harmonic. The system records warnings/corrections in some paths, but this is not equivalent to validated adaptive harmonic suppression.

### 4.5 Is HRV true beat timing with ECG alignment?

The producer constructs adjacent peak intervals and calculates SDNN/RMSSD-shaped fields, so a mathematical IBI sequence exists. It does not match radar beats to ECG R peaks, quantify beat-level sensitivity/precision, establish ectopic-beat handling against ECG, or report paired radar-versus-ECG IBI agreement. Therefore the current HRV output is **exploratory and validation-blocked**, not a validated HRV measure.

### 4.6 Which QC gates measure what?

| QC family | What it primarily measures | What it does not prove |
|---|---|---|
| File/timestamp/frame/linkage | Acquisition/data integrity and joinability | Correct target or physiology |
| Phase stability / jump proxy | Current selected-signal regularity | Independent motion, chest identity, HR/BR accuracy |
| 10-s SD and usable coverage | Current pipeline signal existence/eligibility | Correct HR, BR, or HRV |
| Time-frequency agreement | Internal estimator consistency | Agreement with ECG/RSP |
| Distance gate / target plausibility | Current axis/selection policy | Human chest localization unless physically validated |
| ECG/RSP comparison | Small-sample external reference evidence | Full formal cohort validity when denominators differ |

### 4.7 What does `33/37` scientifically mean?

After the corrected formal `0.037 m/bin` distance interpretation, `33/37/2` means **current-pipeline QC eligibility strata**: 33 sessions pass the retained formal candidate gates, 37 carry B/C eligibility flags, and 2 remain provenance/linkage boundaries. It does not mean 33 good acquisitions and 37 bad acquisitions; it does not measure participant compliance, independent acquisition quality, chest lock, HR/BR accuracy, or HRV validity. The corrected distance audit also showed that the distance-axis bug materially affected the BIOPAC calibration layer, so old and corrected eligibility labels must not be treated as interchangeable.

## 5. Final audit decisions and prohibited interpretations

1. Keep the recovered upstream facts bound: formal stored output is 8-channel complex range-domain DataCube; Range FFT has occurred upstream; formal spacing is 0.037 m/bin.
2. Keep exact upstream implementation gaps explicit: windowing, exact DC/static/IQ behavior, zero-padding/cropping details, normalization, calibration, and physical array convention are not fully bound to the exact image.
3. Treat the downstream target selector, BR/HR separation, VMD, harmonic folding, and temporal smoothing as project variants/heuristics, not universal literature standards.
4. Treat `0.08 m/bin` as a harmful historical/default analysis dependency for formal data; do not revive it.
5. Treat HR as a quality-gated research candidate, BR as supporting research evidence, and HRV as validation-blocked.
6. Keep `PIPELINE_SCIENTIFIC_AUDIT=PASS` only for completion of this evidence audit. Keep `#16 quality-stratified sensitivity=PAUSED` until the separately authorized next gate; this audit does not authorize #16.

## 6. Evidence register

Literature IDs `L1-L11` are defined in `MMWAVE_LITERATURE_EVIDENCE_REGISTER_2026-08-29.csv`. The evidence supports processing requirements and validation principles; it does not prove that FocusWave implements them or transfer published performance to this dataset.

- `L1-L3`: localization/range selection and motion/noise problem framing.
- `L4-L5`: DC/phase/unwrap and respiration-heart separation as explicit processing stages.
- `L6`: respiratory 2×/3× harmonics can produce a stable wrong HR-like peak.
- `L7`: motion cancellation requires independent motion/range-Doppler evidence, not a generic instability label.
- `L8-L10`: external reference, repeated-measures agreement, and Bland-Altman-style validation.
- `L11`: HRV requires beat/IBI-level radar-to-ECG comparison.

No new literature source was added in this audit; `L12` remains pending metadata verification and was not used as primary support.

## 7. Ordered next execution audit (2026-08-30)

This section follows `docs/research/MMWAVE_NEXT_EXECUTION_PROMPT_2026-08-29.md` in order. It does not reopen the closed Range FFT, 37 mm, or eight-channel discovery.

### 7.1 A — device/firmware engineering residuals

The full item-by-item record is `docs/research/MMWAVE_DEVICE_FIRMWARE_ENGINEERING_EVIDENCE_2026-08-30.csv`. The result is **PARTIAL**: no requested item is `CONFIRMED_ON_FORMAL_DEVICE` because a formal-session burn/boot/version receipt is absent. The source-level statuses are explicit rather than blanket unknowns:

| Item | Status | Bound conclusion | Formal-device binding |
|---|---|---|---|
| pre-FFT window | `UNRESOLVED` | no exact window type/axis/coefficients | `UNRESOLVED` |
| zero-padding / FFT scaling | `UNRESOLVED` | 256 reported range elements are known; padding/crop/scale are not | `UNRESOLVED` |
| DC/static clutter | `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY` | SDK branch exists; inspected ReportDataCube1D source selects `MMW_CLUTTER_REMOVAL_NONE` | `UNRESOLVED` |
| IQ correction | `UNRESOLVED` | no exact formal-path primary evidence | `UNRESOLVED` |
| amplitude/phase calibration | `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY` | 2T4R calibration load/save/alignment capability exists | `UNRESOLVED` |
| physical Tx/Rx map | `CONFIRMED_BY_OUTPUT_SEMANTICS` | logical 2Tx×4Rx order is supported; physical coordinates are not | `UNRESOLVED` |
| TDM chirp timing | `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY` | source identifies 2T4R TD-MIMO, one-chirp accumulation, 10 ms frame; chirp order/interval absent | `UNRESOLVED` |
| TDM phase compensation | `UNRESOLVED` | SDK alignment code is not proof of formal report-path compensation | `UNRESOLVED` |
| formal burn/boot/version receipt | `UNRESOLVED` | local image hash is known, deployment receipt is missing | `UNRESOLVED` |

### 7.2 B — existing-output target/bin/channel continuity

Read-only audit of existing formal JSON/NPZ and canonical summaries finds:

- A segment-level result persists one final `bins`/`channels` choice and NPZ `heart_peaks`; it does not persist a per-window selection history.
- No canonical formal output contains the required cross-window `previous/current bin`, `previous/current channel`, `bin_displacement`, `channel_switch`, `phase_discontinuity`, or independent motion evidence sequence. Existing audit fields explicitly mark `range_bin_jump_rate` as not calculated.
- The historical 8-window 37 mm robustness audit reports changes between counterfactual gate settings, not consecutive-window target hopping; it cannot answer continuity.

Therefore B is **PARTIAL / INSTRUMENTATION_REQUIRED**, and execution stops at this gate for any new formal batch. The minimum future instrumentation/rerun contract is one row per baseline/block/window containing: `session_id`, `window_id`, `start_frame`, `end_frame`, `hr_bin`, `hr_channel`, `br_bin`, `br_channel`, prior-window choices, bin displacement, channel switch, phase discontinuity, phase stability, independent motion evidence, input root, producer commit, and firmware hash. No such rerun was started.

### 7.3 C — formal harmonic suppression activation

The exact chain is `run_timeline_gated_mmwave_quality.py:70-108` → `process_vital_signs_v3_1_1.py:3000-3054` → `_analyze_long_record_v23()` → `_heart_segment_reference_correction()` → `_window_hr_candidates()` → `respiration_harmonic_reject()` at `1800-1944`.

`respiration_harmonic_reject()` is a conditional external-RSP branch. It requires `ext_br_bpm`; `analyze_long_record()` derives that only when `acq_path` is supplied. The standard formal runner calls `analyze_long_record()` without `acq_path` and without an external RSP value. Thus the external 2×/3× respiratory-harmonic suppression is **INACTIVE in the standard formal runner**. Internal reference/time harmonic folding remains a heuristic correction, not proof of active adaptive suppression. Classification: **not active suppression; conditional branch available, with post-hoc/reference-dependent handling only**.

### 7.4 D — earliest HRV blocker

The producer stores radar peak indices in NPZ and derives adjacent radar IBI-shaped intervals for SDNN/RMSSD. Independent ECG reference code stores ECG R peaks and ECG IBI summaries, with window/marker alignment at the reference layer. The first missing deliverable in the formal evidence chain is **radar-beat ↔ ECG-R-peak beat-level matching with synchronized timestamps** (including false-positive/false-negative and paired IBI agreement). Consequently HRV remains **BLOCKED**; the existing `SDNN_ms`/`RMSSD_ms` fields are exploratory radar-derived outputs, not ECG-validated HRV.

### 7.5 Ordered execution result

Overall status: **PARTIAL**. A has explicit source-level statuses but lacks formal-device deployment binding; B cannot provide a continuity rate without the specified instrumentation; C is inactive in the standard formal runner; D identifies the earliest missing HRV layer. No model run, #16, C2B/C2C, target-lock rerun, raw-data change, NIR/RGB change, or device burn was performed. Issue #16 remains **PAUSED**.

## 7.6 Targeted execution addendum — supersedes the pre-instrumentation stop above

The previous 7.2/7.5 text recorded the absence of continuity history before the authorized diagnostic. The targeted package `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/` now supplies that small-sample history without changing the producer call or numerical output path.

- Scope: sessions `97793`, `9779`, `97795`; first 6000 frames; five overlapping 20-second windows per session; 12 adjacent transitions; no full formal batch.
- Instrumented fields: current/previous HR and BR bin/channel, bin displacement and 0.037 m reporting conversion, switch flags, current selection scores/rationale, phase comparability status, and provenance/QC boundary.
- Result: HR bin hops 8/12; BR bin hops 9/12; HR channel switches 11/12; BR channel switches 9/12. There were zero same-target HR transitions for raw phase boundary comparison. Motion evidence was unavailable and no movement inference was made.
- Interpretation: continuity is measured but not stable; HR and BR/RR remain `HOLD` for portable physiological feature ingestion. The diagnostic table is not a new target tracker and does not authorize target-lock/AoA/beamforming/multi-bin expansion.

The A/B/C harmonic package is also complete. B uses radar BR only and is identical to A in this sample; C uses external RSP only to label validation windows. B is not promoted, external RSP is not a production dependency, and the standard runner remains free of `acq_path/ext_br_bpm` input. HRV remains `BLOCKED` at radar-beat to ECG-R-peak synchronization and paired IBI agreement. The overall ordered task is therefore `PASS / MMWAVE_MERGE_READY_CONTRACT_FROZEN`, with the conservative ALLOW/HOLD/EXCLUDE table in the targeted report.
