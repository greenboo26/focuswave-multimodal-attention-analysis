# mmWave distance-error and physical-gate audit — 2026-08-30

Status: **PASS / descriptive distance-error complete; physical gate UNRESOLVED**
RUN_ID: `MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_20260829T220501Z`

## Decision

The existing corrected estimator outputs were aggregated on the pre-existing `ECG_VALID` and `RSP_VALID` reference rows. The analysis does not select a new distance threshold. Historical `0.30–1.50 m` is reported only as `HISTORICAL_GATE_SENSITIVITY`.

The formal front-end evidence remains: a near-side bright structure is observed in the locked B2 audit, but its cause is unresolved. It is not established as human chest, near-field/direct leakage, or fixed-environment reflection; a near-field exclusion gate is not authorized.

`REUSE_REJECTION_REASON`: the existing B2 structural audit and separate corrected HR/BR paired tables did not provide one aggregate with continuous distance-versus-absolute-error, predeclared bands, source-valid coverage, and target-stability distributions. This package therefore adds only a downstream aggregation layer.

## Denominators and reuse

| layer | windows/sessions | participants | role |
|---|---:|---:|---|
| formal corrected distance | 71 sessions | 71 session keys | distance/QC distribution only; no formal ECG/RSP truth |
| ECG_VALID HR | 99 windows | 5 | existing 99-window corrected HR-course output |
| RSP_VALID BR | 99 windows | 5 | existing 99-row valid RSP comparison output |

The five-participant reference layer must not be generalized to the formal 71-session cohort.

The separate #24 targeted ECG-QC layer is intentionally not merged into this package; this deliverable preserves the formal 71-session descriptive layer and the early 5-participant/99-window reference layer.

## Continuous distance versus absolute error

Correlations and slopes are descriptive because windows repeat within participant; no inferential p-value is used for gate selection.

| metric | N | MAE | median AE | bias | Pearson r(distance, AE) | Spearman rho(distance, AE) | slope AE/m |
|---|---:|---:|---:|---:|---:|---:|---:|
| HR / ECG_VALID | 99 | 3.777215 | 2.718214 | -0.283855 | 0.180362 | 0.251401 | 2.773851 |
| BR / RSP_VALID | 99 | 3.327631 | 2.33881 | -2.701301 | 0.165609 | 0.133291 | 2.003887 |

These values quantify association in the existing outputs; they do not prove a causal distance effect or justify a gate.

## Predefined distance bands

`MMWAVE_DISTANCE_ERROR_BY_BAND.csv` reports N, session/participant counts, error summaries, and the same descriptive association fields for `<0.20`, `0.20–0.30`, `0.30–0.60`, `0.60–1.00`, and `>1.00 m`. Empty bands remain explicit rather than being dropped.

## Coverage and target stability

`MMWAVE_TARGET_STABILITY_COVERAGE_SUMMARY.csv` reports source-valid window coverage, session/participant counts, target-bin switch rate, channel switch rate, and session-level stability distributions. Stability means repeated existing target/channel values across ordered reference windows; it is not independent chest-lock evidence. `MMWAVE_FORMAL_TARGET_STABILITY_EVIDENCE.csv` separately retains the existing B2 formal diagnostic proxies (range-peak mode fraction/dispersion and channel-amplitude CV) for near, far, and reference groups; these are not new thresholds.

Formal corrected-distance session distribution is in `MMWAVE_FORMAL_DISTANCE_DISTRIBUTION.csv`. The corrected QC and old→corrected transition counts are retained as existing QC metadata, not physiology validity.

## Physical evidence classification

`MMWAVE_PHYSICAL_EVIDENCE.csv` reuses the B2 locked front-end audit and the existing early representative range-profile figure. Formal structure is **OBSERVED / SUPPORTING**; mechanism is **UNRESOLVED**; early visual context is **ENGINEERING_REFERENCE**. No target label is upgraded and no exclusion gate is introduced.

## Provenance and limits

- Distance semantics: selected bin × `0.037 m`; selected bins and estimator outputs are reused, not reselected.
- ECG/RSP validity: existing paired tables define the available valid rows; this audit adds no new ECG/RSP artifact rule.
- No raw, NPZ, participant-level, or row-level output is written by this script.
- Full input hashes and aggregate output list are in `MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_MANIFEST.json`.
