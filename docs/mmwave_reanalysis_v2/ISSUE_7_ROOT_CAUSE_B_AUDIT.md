# Issue #7 — mmWave existing-asset and failure-evidence audit

Status: **PASS (bounded repository audit) / PARTIAL (historical execution coverage)**
Audit date: 2026-08-27
Central repository: `greenboo26/focuswave-multimodal-attention-analysis`
Audit branch/commit: `codex/mmwave-formal-reanalysis-v2` @ `689d5fc537378dabf7b914f71aaacb39a26c49ab`
## 1. Scope and stop boundary

This is the Issue #7 Root cause B audit: identify what has already been implemented, tested, rejected, or remains blocked, and map each known failure mode to recoverable evidence. It does not run a new physiological benchmark, access the held-out 80 participants, access `J:\Data`, restore HRV work, or introduce a new algorithm family.

The audit uses the central repository as the scientific source of truth and checks acquisition semantics against `kyandi233-dev/FocusWave@ecg` @ `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`. Temporary clones used for inspection are outside the repository and are not part of the deliverable.

## 2. Reusable-asset matrix

| Asset / source | Concrete evidence | What it solves or records | Current reuse decision | Gap / control |
|---|---|---|---|---|
| Historical v1–v8/v9 line | `164d51e`; `scripts/process_vital_signs_v2.py`, `v3.py`, `v5.py`, `v9.py`; `CHANGELOG.md` | Band-pass baseline, VMD heart-only, peak/quality logic and respiratory-harmonic notch history | Preserve as historical baseline and diagnostic lineage | Old outputs and exact aggregate parameters are incomplete; do not treat narrative results as a reproducible benchmark |
| v3.1/v3.1.1 ECG calibration line | `55b6c01`; `scripts/process_vital_signs_v3_1_1.py`, `calibrate_ecg_mmwave.py`, `calibrate_vmd_segments.py` | Development HR/IBI calibration and segment-level comparison | Reuse only through the frozen benchmark adapter | HRV/beat validity is not established; retain supporting role |
| Seven local A/B trials | `ac2e512`; `scripts/experiment_{spc,hampel,phasediff,cfar,ssa,envelope,ceemdan}.py` | Previously tried location, denoising, phase and decomposition alternatives | Do not silently repeat; cite as prior evidence | Exact method-level `n`, parameters and output tables are incomplete (`MISSING_EVIDENCE`) |
| Gold-standard cleaning | `7a482f0`; `scripts/gold_standard_qa.py`, `validate_gold_anchor.py`; `docs/金标准清洗标准.md` | ECG/RSP QC and the T-wave double-detection control | Reuse the QC contract, not old unqualified scores | Applicability across every source/device still requires explicit inventory evidence |
| Historical AgeBalanced route | `f4a8c74`; reconciled by `configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json` | External 60 GHz derived-radar historical comparison | Supporting historical anchor only | 10 Hz derived input is not equivalent to RS6240 raw IQ; record 220 Rest sessions and provenance limits |
| Current benchmark contract | `configs/mmwave_reanalysis_v2/benchmark_decision_v1.json`, `schemas/mmwave/per_window_benchmark_v1.schema.json`, `pipelines/mmwave/ecg_reference_v1.py` | Frozen split/window/reference/QC/metric rules and machine-readable rows | Canonical benchmark surface | 25 s historical output cannot be represented directly by V1 schema; use diagnostic-only comparison |
| Official VitalSense route | `docs/research/2026-08-25-vitalsense-official-reproduction-v1/`; `Rc-W024/VitalSense2024@d9f71f9` | Independent MATLAB route and 48-session reproduction evidence | Secondary engineering reference; no RS6240 claim | Clean full dataset access and RS6240 adapter remain unresolved |
| VMD component | `vrcarva/vmdpy@47ca3e8` recorded in `reuse_gate_v1.json` | Transparent decomposition component | Eligible MIT component; direct synthetic smoke passed | Does not establish the full SSA+VMD paper method or device transfer |
| SSA+VMD / EE-PCC-VMD | Task 2R/2S reports and `pipelines/mmwave/lei2025_ssa_harmonic_removal_v1.py` | Bounded paper-derived harmonic/noise separation comparison | `paper_reimplementation/adapted`, not official reproduction | Current 50/60 s comparisons did not rescue the route; no further algorithm fishing |
| RS6240 acquisition implementation | `FocusWave@ecg` `01-MainProgram/core/mmwave_capture.py` @ `8e6fe5c`; raw complex IQ, timestamps, 2T4R, 256 range FFT, 10 ms frame period, 57 GHz, 37 mm range resolution | Defines the actual formal capture semantics and cross-device timestamp contract | Acquisition truth for adapter audits | Raw/derived linkage, channel map and calibration evidence are incomplete; do not infer AgeBalanced compatibility |
| Multi-bin/spatial/beamforming ideas | `docs/mmwave_reanalysis_v2/REUSE_IMPLEMENTATION_AUDIT_V1.md`, `O-007`, `O-012` | Potential response to bin drift, clutter and multipath | Defer | Requires compatible raw/angle tensor, Tx/Rx map and calibration; no implementation authorized in Issue #7 |

## 3. Failure evidence and existing controls

| Failure ID | Traceable evidence | Interpretation | Existing control / disposition |
|---|---|---|---|
| F-001 | `CHANGELOG.md` v9 notes; `FAILURE_MODE_REGISTRY.md`; 2025/2024 literature references | Respiratory fundamental or 2nd/3rd harmonic can enter the HR band and create a plausible but false lock | Report harmonic-lock category and retain harmonic modelling as an ablation; do not silently correct a result |
| F-002 | `docs/methodology/target_lock_audit.md`; historical target-lock notes in `CHANGELOG.md` | Strongest range bin can be clutter/multipath rather than chest motion | Require target-lock and cross-bin/spatial consistency; multi-bin repair is blocked by O-007 |
| F-003 | Historical v2/v3/VMD scripts and comments; `METHOD_MATRIX.md` | VMD mode selection is parameter- and signal-dependent | Freeze mode-selection parameters for any authorized benchmark; historical variants remain diagnostic |
| F-004 | VitalSense reproduction report and `FAILURE_MODE_REGISTRY.md` | HR plausibility does not imply beat timing or IBI validity | Separate HR accuracy from beat recall/coverage; HRV remains stopped |
| F-005 | `7a482f0`; `docs/金标准清洗标准.md` | ECG T-wave double detection can inflate the reference HR and invalidate radar comparison | ECG reference-first QC; status `CONTROLLED` |
| F-006 | `7a482f0`; gold-standard cleaning record | Static RSP variability must not be rejected by a generic jump rule | Keep RSP-specific QC; status `CONTROLLED` |
| F-007 | `docs/methodology/rgb_motion_gate.md`; historical RGB-mmWave gate work | Movement and window edges change radar quality and can create spurious peaks | Per-window motion/reject status; no automatic recovery of rejected physiology |
| F-008 | Historical single-bin/subject-001 notes; `FAILURE_MODE_REGISTRY.md` | A single bin lacks spatial redundancy, so harmonic locks can survive | Treat temporal continuity as diagnostic only; spatial repair requires resolved acquisition contract |
| F-009 | VitalSense schema/reproduction package | Dataset without RSP cannot support a BR claim | Use external route for HR/ECG only; status `CONTROLLED` |
| F-010 | `EVIDENCE_LEDGER.md` E-001–E-005, E-014–E-016; O-003/O-005/O-014 | Several historical claims lack exact output, parameter or aggregation artifacts | Mark `MISSING_EVIDENCE`; do not reconstruct values from memory or narrative tables |

## 4. Reuse and stop decisions

1. The project baseline, v3.1.1 calibration path, ECG reference implementation and existing QC controls are reusable, subject to the frozen V1 contract.
2. The seven A/B methods, historical v1–v9 branches and external paper methods are evidence of prior work, not authorization for another sweep.
3. `vmdpy` is reusable as a separately licensed MIT component. SSA+VMD remains a declared paper reimplementation/adaptation.
4. Sparse DCT is excluded pending permission and transparent source; mmVital is excluded from Phase 2B because license/input/geometry evidence is insufficient; mmVital-Signs is engineering reference only.
5. Multi-bin/beamforming is not implementable from the currently proven RS6240 package. The required next artifact is a raw/angle schema plus Tx/Rx calibration and raw-to-derived linkage, not a guessed adapter.
6. Issue #7 therefore ends with `CONFIRMED_REUSE_AND_FAILURE_BOUNDARIES`, not a signal-processing improvement. The primary review may choose the next route only after combining this report with Workstream A's factorized discontinuity audit.

## 5. Open evidence needed by the primary review

- O-003/O-005/O-014: recover exact historical A/B outputs, parameters and quality/harmonic aggregation, or keep them explicitly `MISSING_EVIDENCE`.
- O-007/O-012: reconcile RS6240 channel/antenna geometry, two reference-ID mismatches and raw-to-derived linkage before any spatial method is considered.
- O-002: restore approved VS_DATASET access only through a separately authorized data-access task.
- Workstream A must determine whether the 9 BPM versus 27–37 BPM discontinuity is a benchmark/adapter defect before any targeted signal repair is authorized.

## 6. Verification record

Read-only checks completed:

- central repository identity, branch and commit verified;
- historical commits `164d51e`, `55b6c01`, `ac2e512`, `f4a8c74`, `7a482f0` inspected for source lineage;
- current ledger, failure registry, method matrix, reuse gate and benchmark contract cross-checked;
- acquisition branch cloned read-only and `mmwave_capture.py` inspected for format/timestamp/device assumptions;
- no raw participant data, row-level results, credentials or machine-local path configuration added.
