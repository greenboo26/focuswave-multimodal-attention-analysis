# mmWave open questions → evidence sources → execution instruction — 2026-08-29

Status: `ASSIGNED / #16 PAUSED`

Purpose: persist the current discussion about **where each remaining mmWave pipeline question can actually be answered**, so the next agent does not repeat generic discovery or confuse manual/SDK evidence with project evidence.

## Current project state

The upstream is no longer wholly unknown. The following are already bound in the canonical audit:

- formal image uses `fft_mode=2`;
- `range_fft_len_log2=8` → 256-point range axis;
- distance semantics = `0.037 m/bin`;
- formal output is 2T×4R = 8-channel complex 1D Range-FFT DataCube;
- `ReportDataCube1D` is not raw ADC.

The remaining questions are narrower and must be answered from the appropriate evidence layer rather than by generic literature alone.

## Evidence-source map

| Open question | Most direct evidence | What this evidence can prove | What it cannot prove by itself |
|---|---|---|---|
| Range FFT exact implementation | RS6240 official SDK source, formal config, firmware-linked code path | FFT length, transform path, range packing, range conversion | that the exact experiment device ran the same build unless bound to formal image/device record |
| Pre-FFT window type | lower-layer DSP source, official manual/API, firmware-linked implementation | whether Hann/Hamming/etc. is applied, axis and parameters | actual experiment-device execution without formal-image binding |
| Zero padding / FFT scaling | FFT config and lower-layer implementation | transform length, padding/scaling behavior | acquisition-day deployment identity |
| DC / clutter removal | `prj_config.h`, DSP calls, firmware config | whether producer enables DC/static clutter processing | whether a different hidden lower layer modifies the signal unless source/runtime evidence exists |
| IQ calibration | calibration routines, init path, EEPROM/flash calibration loading, official calibration docs | whether IQ correction is supported/called and with which parameters | that formal device loaded valid calibration unless startup/runtime evidence exists |
| Channel amplitude/phase calibration | SDK calibration functions/tables + startup config | channel calibration behavior | formal-device application without device/build evidence |
| 8-channel physical identity | antenna/chirp config, official antenna/Tx-Rx mapping docs, producer key mapping | which Tx/Rx pair corresponds to each channel | coherent phase comparability unless timing/calibration is also proven |
| TDM Tx/Rx timing | chirp/frame config and official timing diagram | Tx switching order and inter-Tx timing | phase compensation unless a compensation path is separately found |
| TDM phase compensation | DSP/source call chain | whether timing/phase compensation is actually performed | exact formal-device execution unless bound to formal image |
| Which firmware was actually running during formal acquisition | flashing log, boot/serial output, device info/version metadata, acquisition log | exact deployment identity/build | DSP internals unless linked to source/manual |
| Target/bin/channel continuity across windows | project-produced selected-bin/channel outputs, target-lock audit tables, producer summaries | whether target selection hops across windows and channels | physical chest truth by itself |
| Whether phase jumps are participant motion or target-selection failure | selected bin/channel timeline + phase timeline + independent motion evidence (RGB/key press/Doppler where already available) | causal consistency between target switching and phase discontinuity; whether independent motion evidence co-occurs | universal motion causality without independent evidence |
| Whether 2×BR/3×BR suppression is active in formal HR path | formal runner → producer call chain → harmonic-rejection branch and arguments | whether the formal invocation actually reaches the suppression logic | whether the suppression is physiologically valid without reference testing |
| HRV validity | radar beat timestamps/IBI + ECG R-peak timestamps + synchronization + beat matching | whether beat-to-beat timing and HRV are valid against ECG | anything if only window-level HR or summary RMSSD exists |

## Required interpretation rules

1. `SDK supports X` is not equivalent to `formal firmware executed X`.
2. `formal firmware contains X` is not equivalent to `formal device used that firmware during acquisition` without burn/boot/version evidence.
3. `stable phase`, `high SNR`, `plausible distance`, or `good coverage` are not chest/physiology ground truth.
4. `phase unstable` must not be translated into participant motion unless independent motion evidence supports it.
5. target/bin/channel switching can itself create phase discontinuities even when the participant remains still.
6. 33/37 is not interpreted until the remaining target-continuity and failure-attribution questions are closed.
7. HRV remains blocked unless a true radar beat/IBI ↔ ECG R-peak chain is demonstrated.

## Execution order

### Task A — close device/firmware engineering unknowns first

Recover existing local/manual/SDK evidence and answer, in order:

1. pre-FFT window;
2. zero padding / FFT scaling;
3. DC/static clutter behavior;
4. IQ correction;
5. channel amplitude/phase calibration;
6. 8-channel Tx/Rx physical mapping;
7. TDM timing;
8. TDM phase compensation;
9. formal-device flashing/boot/version receipt.

For each item record:

- exact source path or official URL;
- manual version/page/section or source file/function/line;
- formal firmware binding status;
- formal device deployment binding status;
- conclusion;
- confidence;
- remaining gap.

Allowed status:

- `CONFIRMED_IN_FORMAL_FIRMWARE`
- `CONFIRMED_ON_FORMAL_DEVICE`
- `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY`
- `CONFIRMED_BY_OUTPUT_SEMANTICS`
- `UNRESOLVED`
- `NOT_APPLICABLE`

### Task B — audit target/bin/channel continuity

Use existing outputs first. Do not rerun science if the selected target/bin/channel is already persisted.

For each formal session/window where existing records allow it, derive or read:

- selected HR bin/channel;
- selected BR bin/channel;
- previous-window bin/channel;
- bin displacement;
- channel switch flag;
- phase discontinuity indicator;
- existing phase-stability/QC outcome;
- independent motion evidence if already available;
- keypress/motion proxy if already available.

Answer:

- how often bin hopping occurs;
- how often channel switching occurs;
- whether phase instability concentrates around switching;
- whether switching occurs without independent motion evidence;
- whether current QC is partly measuring target-selection continuity rather than acquisition quality.

If selected-bin/channel history is not persisted, stop and report the minimum instrumentation needed before any rerun. Do not silently start a new formal analysis.

### Task C — prove whether respiratory harmonic suppression is active

Trace the exact formal call path:

`formal runner → process_vital_signs_v3_1_1.py → harmonic rejection logic`

Record:

- function definition;
- call sites;
- required arguments;
- branch conditions;
- whether `acq_path`/RSP is actually supplied by the formal runner;
- whether 2×BR / 3×BR rejection is active, inactive, or only post-hoc flagging.

No new HR analysis is authorized in this task.

### Task D — HRV blocker definition only

Do not try to rescue HRV yet. Establish whether the existing formal assets contain:

- radar beat timestamps;
- radar IBI sequence;
- ECG R-peak timestamps;
- synchronization mapping;
- beat matching output.

If any required layer is absent, record the earliest missing layer and keep HRV=`BLOCKED`.

## Required durable outputs

Update/create in canonical GitHub:

1. `docs/research/MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`
2. `docs/research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`
3. `docs/research/MMWAVE_LITERATURE_VS_PROJECT_STAGE_MATRIX_2026-08-29.csv`
4. `docs/research/MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`
5. `docs/research/MMWAVE_PIPELINE_FLOWCHART_2026-08-29.md`
6. `PROJECT_STATUS.md` and `docs/canonical/RESULT_INDEX_V1.md` if interpretation/status changes
7. `CHANGELOG.md` for material conclusions

If large evidence stays local, store absolute local path + hash/manifest/provenance in a Git-safe record.

## Prohibited

- no #16 run;
- no C2B/C2C rerun;
- no new target-lock algorithm;
- no AoA/beamforming/VMD search;
- no raw-data modification;
- no NIR/RGB producer modification;
- no generic literature search as substitute for the already-known engineering evidence path;
- no translating phase/QC failure into participant movement without independent evidence.

## Completion condition

This task is `PASS` only when the device/firmware questions above have explicit evidence status, target/bin/channel continuity has been audited from existing outputs or its exact missing instrumentation is documented, formal harmonic suppression activation is proven, and HRV's earliest unresolved beat/ECG layer is identified.

Until then: `PARTIAL`, `#16 PAUSED`.
