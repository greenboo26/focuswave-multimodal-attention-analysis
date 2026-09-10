# Issue #33 probe adapter repair and supervised-input audit

State: PARTIAL overall; engineering replay and input-quality audit PASS;
formal physiological predictor admission NOT_PASSED; models_trained=false.

## Scope and provenance

The four-repository audit identified central main 9cbaca004aa1f6e4977b620e4efda247f343f932 as the producer base. Formal-Analysis 1.15.8 defines the repair requirements. Attention-Analysis quality audit ran at 4d8c40e3e8187652837b0ea664eac70182591c91 with no tracked modifications. Acquisition formaltest was inspected at a4f2a6ee4eda2b4de42be538abb1ecf550380ca1.

The bounded historical-output search inspected 15 CSV/manifest candidates. Only the existing E table matched 880 rows/44 sessions. This is not a claim about unsearched or inaccessible locations. Its exact historical run/commit remains UNKNOWN. The adapter introduction commit a97f8fa7e5b4b758bf67810fc76cf8f4ddb4940b is VERIFIED as code history, not as the execution receipt. J records c35c3b9d41c4ce28dfbc1038d06c6c99fc0c645b and mmwave_probe_merge_ready_20260831, but its adapter was committed after the output timestamp, so its exact dirty source tree is not proven.

Old J SHA256: bc827dc317982ae0e920f661e28cec023473eccfcb034bc806e1a3583ef7828c.
Old E SHA256: b7ea774ccebb6e35397a56e76f108a63d41803bf697260d01977effa5fad3e36.
Both old tables and old manifests were rehashed after execution and remained unchanged. Local evidence contains sizes, timestamps, row/session/key counts, path registration, repository states, and candidate inventory. No row-level data or machine-private configuration belongs in Git.

## Changes and executable entrypoints

- Existing J/E command names now share `scripts/maintenance/mmwave_frozen_cohort.py`; required arguments are `--baseline`, `--freeze`, `--raw-root`, `--output-dir`, `--run-id`. An optional explicit `--sessions` subset is for isolated smoke runs only.
- Consume frozen keys and timeline metadata; never enumerate raw directories into the cohort or reuse old feature values. Exclusive output directories prevent overwriting historical results.
- Slice effective start through exclusive probe onset. Read formal `block_start` and `block_stop` from the behavioral master timeline. Unknown boundaries do not yield an accepted observed row.
- Reuse the producer's 25-second internal heart-rate course with 5-second steps, per-probe internal continuity and producer median summaries. Mean confidence aggregates exported point confidences; usable fraction uses producer signal-quality counts. No previous probe is passed as an external physiological reference.
- Check channel shapes, timestamp/NPZ row-count agreement and frame ordering. Use indexed headers to avoid repeatedly decompressing unrelated chunks; hash actual input slices.
- Write row provenance before CSV serialization and record source HEAD, dirty state, source hashes, input hashes, parameters, output hash and software versions in manifests. A dirty HEAD plus source hashes is explicitly distinguished from a clean commit-only run.
- `finalize_mmwave_boundaries.py` creates a new metadata-only version from a hash-verified feature run. It refuses changed effective slices or timelines. V3 adds E block-stop metadata required by the downstream interface; all numerical features are byte-equivalent to V2 cells.
- `compare_mmwave_probe_versions.py` writes exact-five-key differences, missing transitions, field change counts and finite-pair absolute-difference summaries.

## Measured results

J72 + E44 = 116 sessions / 2320 rows, exact one-to-one five-key mapping. The extra 21 E directories were excluded. All 385 old endpoint-hit probes have at least one changed field after the combined repair; this does not attribute every change to endpoint exclusion alone. Actual block-start truncations: 0. Unverified block timeline: 20 rows.

Observed rows: 2200 -> 2180; structural missing: 120 -> 120; quality failure: 0 -> 20. The additional failure is a timestamp/NPZ count mismatch (238639 versus 238000) in one session. No probe is dropped. Frame-index gaps inside the verified new slices: 0; this does not establish absolute frame-time validity.

Every row has at least one changed non-provenance field, including missing-reason/loadability metadata. It does not mean every row's physiological value changed.

| Field | Changed rows (including missing transitions) | Finite-pair median absolute difference | P90 | Maximum |
|---|---:|---:|---:|---:|
| Fused heart rate (beats/min) | 2197 | 0.7345 | 14.0677 | 52.1360 |
| Breath rate (breaths/min) | 402 | 0.0000 | 0.0060 | 12.1280 |
| Mean heart-rate confidence | 2197 | 0.0544 | 0.2377 | 0.5848 |
| Timestamp coverage fraction | 402 | 0.0000 | 0.0002 | 0.0501 |
| Motion proxy | 385 | 0.000000 | 0.000003 | 0.042079 |

Each numeric difference distribution uses 2180 finite old/new pairs. The 20 finite-to-missing transitions are counted separately in the machine-readable comparison. True internal usable fraction remains 1.0 in all 2180 accepted observed rows and missing in 140 rows; it still fails the nonconstant-feature gate. No threshold was changed to manufacture variance.

## Downstream quality audit

Both old/new inputs ran through the same quality-only implementation and rules. Behavior denominator stayed 2320; other modality and identity-bridge hashes were identical; input problems were empty and no model was trained.

| Analysis set | Old probes | New probes |
|---|---:|---:|
| Behavior + mmWave | 2200 | 2180 |
| Behavior + near-infrared + mmWave | 1873 | 1873 |
| Behavior + mmWave + visible-light video | 2100 | 2100 |
| All modalities | 1793 | 1793 |

The quality audit's `main_candidate` label means computational readiness only. It does not supersede the central field-use contract, and quality/confidence fields do not automatically become scientific predictors. Default downstream paths were not switched to this candidate run.

## Verification and remaining gate

Six targeted regression tests pass: boundary exclusion/course aggregation, identity/duplicate rejection, clipped start, cube row mapping, block-stop export and raw marker parsing. Full real-input replay, exact old/new keys, old hashes, output hashes, complete new row provenance, unchanged V2/V3 numerical values, absence of nonfinite literals, withheld heart-rate-variability fields and quality-only manifests were verified. No full repository test-suite claim is made.

Formal physiological admission remains NOT_PASSED. This controlled repair preserves the historical Python write-time column, whereas the targeted calibration contract established a DLL-provided clock. Absolute frame-time transfer to the formal cohort and independent physiological validation of the corrected course remain unresolved. The current heart-rate/breath-rate SUPPORTING_HOLD and heart-rate-variability BLOCKED decisions remain binding. These are evidence gates, not flags to disable in order to report completion.

Local result families: `baseline_20260910`, `run_j_v2`, `run_e_v2`, `run_j_v3`, `run_e_v3`, `comparison_v3`, `quality_old_v2`, `quality_new_v3`, `verification_v3.json`, under the user-approved independent issue33 directory. V2 and initial smoke/quality failures are preserved as history. V3 is the engineering candidate; it is not a primary physiological release.

Next evidence owner: resolve the formal frame-time contract and corrected-estimator external validation before approving physiological predictors. No new algorithm, tuning experiment, identity change, extra cohort, model training or hardware rerun was performed.
