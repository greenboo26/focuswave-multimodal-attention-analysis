# Reuse Gate — Implementation Audit V1

Status: **PASS audit / PARTIAL executable coverage**

The audit distinguishes an original/official repository, a mature third-party component and a method reconstructed from a paper. Visible source without a usable license is not treated as reusable open source. A paper-derived implementation without author code is always `paper_reimplementation`.

| Candidate | Paper / repository | Fixed source | License | Input and device assumptions | RS6240 adapter smoke | Decision |
|---|---|---|---|---|---|---|
| SSA+VMD | DSP 2025, DOI `10.1016/j.dsp.2024.104911`; no author code found | VMD component `vrcarva/vmdpy@47ca3e8` | MIT for VMD component | 1-D phase/displacement; SSA/VMD parameters still need adapter | VMD direct-module synthetic smoke PASS; combined SSA+VMD not implemented | eligible only as `paper_reimplementation` |
| DR-MUSIC | Scientific Reports 2024, DOI `10.1038/s41598-024-77683-1`; no author code found | paper only | paper terms; no software license | radar phase, radar-derived respiration, RLS and MUSIC order assumptions | not run | eligible only as `paper_reimplementation` |
| Harmonic MUSIC | arXiv `2408.01951`; no author code found | paper only | no software license | phase/displacement and harmonic covariance/model-order assumptions | not run | eligible only as `paper_reimplementation` |
| Sparse DCT | `Z-H-XU/DCT-Vital-Signs@470b68d` | fixed commit | no OSI license; restrictive notice | raw I/Q 2560 Hz; external RSP in demo; opaque `SparseOptimization.p` | blocked | exclude unless permission and transparent implementation are recovered |
| mmVital | `Ubiweb-lab/mmVital@c559da1` | fixed commit | `MISSING_EVIDENCE` (no LICENSE file) | TI IWR1443/IWR1843 raw ADC, 4 antennas, 128 ADC samples, beam steering | blocked by license, raw-format/geometry mismatch and incomplete Python port | exclude from Phase 2B |
| mmVital-Signs | `KylinC/mmVital-Signs@ac2bf21` | fixed commit | Apache-2.0 | TI xWR hardware TLV/UART, SDK 3.5, 20 fps | no offline RS6240 adapter | engineering reference only |
| VitalSense official | `Rc-W024/VitalSense2024@d9f71f9` | fixed commit | MIT | dataset-specific `VitalSig`, MATLAB matched-filter route | official sample and historical 48-session reproduction PASS; RS6240 adapter not established | reproducible secondary baseline once data access returns |
| Multi-bin/spatial RS6240 | no single adopted implementation | none | n/a | needs Tx/Rx map, antenna calibration, compatible complex tensor and often raw angle data | blocked by O-007 | defer; do not invent in Phase 2B baseline |

The checked repositories are recorded machine-readably in `configs/mmwave_reanalysis_v2/reuse_gate_v1.json`. Clone locations are temporary audit evidence and are not committed. No external source tree was copied into the central repository.

## Reproducible now

- Existing project historical baseline code: reproducible source lineage, pending Phase 2B adapter/schema integration.
- VitalSense official MATLAB implementation: fixed MIT commit and prior official smoke/reproduction evidence; blocked only by current clean VS_DATASET access for a new run.
- VMD component: MIT fixed commit and direct implementation smoke PASS; this does not make the full SSA+VMD paper method an official implementation.

## Not reproducible enough for Phase 2B

- DR-MUSIC and Harmonic MUSIC: paper equations only; any implementation is a declared paper reimplementation.
- mmVital: no license evidence and incompatible TI raw-ADC/array assumptions.
- Sparse DCT: restrictive/no OSI license and opaque p-code.
- Multi-bin/beamforming: RS6240 antenna/channel calibration contract is unresolved.

Phase 2B should therefore begin with the existing baseline and existing v3.1.1/VitalSense-compatible adapters. Paper reimplementations may follow only after development-only unit/synthetic tests and config freeze; they cannot be described as official reproductions.
