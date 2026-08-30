# mmWave canonical state, branch consolidation, and multimodal interface — V1

Status: `CANONICAL / MAIN-BOUND / INTERFACE_CONTRACT_FROZEN / ADAPTER_IMPLEMENTATION_PENDING`

Effective date: 2026-08-30. This document is the first mmWave-specific state authority for any AI or human entering the canonical repository. It consolidates branch history, current scientific decisions, time semantics, and the reserved multimodal interface. It does not rerun science and does not promote HR/BR/HRV beyond their existing evidence boundaries.

## 1. Authority and time handling

The only current development/state branch is `main`. The last scientific commit before this consolidation was `9b1c6f156567002db05d23ecfa0919ffd2aed429` (`audit(mmwave): execute nearfield preselection ab`) committed at `2026-08-30T07:42:14Z`, equivalent to `2026-08-30 15:42:14 Asia/Shanghai` and `2026-08-30 16:42:14 Asia/Tokyo`.

Repository commit/audit timestamps must be recorded in UTC ISO-8601 (`...Z`) as the authoritative timestamp. Human-facing local times may be shown as derived values with an explicit timezone. Signal alignment must never use commit time or local wall-clock labels: probe/window alignment uses real Unix milliseconds from the formal behavior timeline and modality acquisition timestamps.

The canonical probe window remains `pre_30s = [probe_onset_unix_ms-30000, probe_onset_unix_ms)`, clipped at the current formal block start when necessary, with `window_effective_start_unix_ms` retaining the actual effective boundary.

## 2. Branch and PR consolidation

| Asset | Head / relation | Canonical role | Decision |
|---|---|---|---|
| `main` | current canonical line | current state and future changes | `KEEP / ONLY CURRENT LINE` |
| `codex/mmwave-formal-reanalysis-v2` | `d87229afe071f23450728a6d617ec82317e6c9df`; diverged historical research line | AgeBalanced benchmark/reference, SSA/VMD, root-cause and literature provenance | `HISTORICAL_EVIDENCE_ONLY` |
| `codex/mmwave-production-contract-hardening` | `fc682b491fcbeeb9bd1b030c8af9da33282d2846`; one commit after the historical line | source of several production-contract ideas | `REVIEWED_SOURCE_ONLY / DO_NOT_WHOLESALE_MERGE` |
| `codex/mmwave-production-contract-review-fix-v1` | identical to `fc682b...`; zero unique commits/files | no unique evidence | `REDUNDANT_POINTER / DO_NOT_DEVELOP` |
| PR #20 | head `fc682b...`, base is the historical reanalysis branch rather than current `main` | provenance for hardening proposal | `SUPERSEDED_BY_MAIN_REVIEW` |

No new long-lived mmWave branch is authorized by this consolidation. Existing historical branches are retained only to preserve provenance; they are not current-state authorities.

### Hardening change disposition

The old hardening proposal is reviewed item by item rather than merged wholesale:

- `breath_rate` summary naming: **already absorbed in current main**; the runner now preserves the producer's public `breath_rate` object.
- explicit candidate/failure status instead of silently choosing an arbitrary candidate: **accepted principle**, required for the future canonical adapter/producer contract.
- strict finite JSON and no NaN/Infinity in formal exchange artifacts: **accepted principle**, required for future canonical exchange artifacts.
- frozen external identity/session manifest, identity keys passed through rather than inferred in mmWave code: **accepted principle**, required before a formal batch becomes canonical.
- no silent method/backend substitution: **accepted principle** for any future formally authorized estimator run.
- exact dependency rule `vmdpy==0.2`: **not canonical**. Current `main` remains the authority. No scientific equivalence/provenance test has established that exact standalone package version as the required scientific implementation. If VMD is ever re-authorized, backend/version provenance and numerical equivalence must be audited first.
- the old segment JSON schema is **design provenance only**. The canonical multimodal-facing schema is now `schemas/mmwave/mmwave_probe_merge_ready_v1.schema.json`.

## 3. Current scientific state

The latest completed A/B kept the existing selector. Slow-time complex-mean subtraction reduced the frequency of HR selections below 0.30 m but worsened HR bin/channel switching and did not improve BR near-side selection. Decision: `KEEP_CURRENT_SELECTOR / DO_NOT_ADD_PRESELECTION_PREPROCESSING`.

The current allowed scientific roles are:

- HR: `HOLD / SUPPORTING_ONLY`; not a primary multimodal predictor.
- BR / respiratory rate: `HOLD / SUPPORTING_ONLY`; not a primary multimodal predictor.
- HRV / IBI: `BLOCKED / EXCLUDE` until radar beat timing versus ECG R-peaks and paired IBI agreement pass the existing beat-level gate.
- target/bin/channel, phase, continuity, and motion-like radar fields: `DIAGNOSTIC_HOLD`; they may enter a future formal feature block only after their field semantics and producer lineage are frozen.
- loadability, coverage, missingness, and source/provenance fields: `STRUCTURAL_ALLOW`; they may be used for audit/coverage/missingness and prespecified sensitivity, not as surrogate physiology labels.

Current task/evidence boundaries:

- #24 ECG reference eligibility is frozen at `ECG_VALID=325`, `ECG_INVALID=10`, `UNRESOLVED=0` for the targeted DLL-time denominator.
- #25 remains `WAIT_ON_SELECTOR_VALIDITY`; the lower 60 s diagnostic MAE does not authorize choosing 60 s as a formal window by performance.
- #26 is frozen as audit `PASS` but scientific `BLOCKED / PHYSICAL_GATE_UNRESOLVED / HARD_EXTERNAL_BLOCKER`; reopen only with genuinely independent session-level placement truth.
- #27 has produced selector/path replay and localization evidence but remains supporting/partial; it does not promote HR validity.
- #28 historical acquisition tail is irrecoverable; use the frozen timestamp-only coverage criterion, never padding/backfill. Future-prevention engineering is separate from scientific validity.
- #29 remains the supervisor/governance issue for one canonical mmWave state.

There is no authorization here for a new HR algorithm family, VMD/SSA grid, AoA/beamforming redesign, error-tuned distance gate, full formal batch, or final mmWave multimodal model.

## 4. Canonical multimodal interface

Before this V1 consolidation, mmWave had a reserved scientific role in the multimodal design but no probe-level feature contract equivalent to Behavior/NIR/RGB. This document freezes that interface so future code has a single target.

### Observation/key contract

Every `mmwave_probe_merge_ready` row must use the same canonical key as the other modalities:

`repeat_participant_id, session_id, block_id, probe_id, window_name`

Identity semantics:

- `repeat_participant_id` = participant/statistical identity and fold grouping key;
- `session_id` = acquisition/session identity;
- `block_id` = formal block identity;
- `probe_id` = probe identity within the canonical timeline;
- `window_name` = window contract name, currently `pre_30s`.

The adapter must not infer participant identity from folder names. It must consume the already-frozen central mapping/manifest and pass identity fields through unchanged.

### Required exchange artifacts

The future adapter must produce, under a parameterized local derived-output root rather than a hard-coded machine path:

- `mmwave_probe_merge_ready.csv` — one row per canonical probe key, including explicit missingness rows;
- `mmwave_probe_merge_ready_manifest.json` — source commits/run IDs, hashes, field/schema versions, row counts, coverage, and status counts;
- optional `mmwave_probe_merge_ready_audit.csv` — non-sensitive aggregate/diagnostic audit if needed;
- row-level/participant-level data remain local-only; Git stores schema, contract, aggregate audit, and provenance only.

Recommended relative layout under the central derived package is `formal_multimodal_v2/mmwave/`. Actual roots must be parameterized through the existing local-path configuration/runbook rather than encoded into scientific code.

The JSON/CSV schema authority is `schemas/mmwave/mmwave_probe_merge_ready_v1.schema.json`; the field dictionary is `docs/canonical/MMWAVE_FEATURE_CONTRACT_V1.csv`.

### Missingness and validity rules

- Preserve the full canonical timeline denominator; never drop a probe row merely because mmWave is missing or scientifically withheld.
- Never zero-fill unavailable physiology/features.
- Use explicit state/reason fields (`OBSERVED`, `STRUCTURAL_MISSING`, `OBSERVATION_MISSING`, `QC_FAIL`, `NOT_ELIGIBLE`, `UNRESOLVED`).
- QC/availability fields are not physiological ground truth.
- A selected-bin-derived distance is a **distance proxy**, not measured human placement distance.
- Avoid the ambiguous field name `RR`: respiratory rate must use an explicit `breath_rate` name; beat intervals must use `IBI` in milliseconds.

## 5. Integration gate and next implementation task

`MMWAVE_INTERFACE_CONTRACT=FROZEN`, but `MMWAVE_PROBE_ADAPTER=IMPLEMENTATION_PENDING`.

The next integration implementation is deliberately narrow: adapt existing canonical mmWave outputs to the frozen probe key/window, produce `mmwave_probe_merge_ready.csv` plus manifest, and validate non-null/unique keys and merge behavior against the 1,440-row canonical probe timeline. It must not rerun or redesign the producer, change HR/BR estimators, select a better window by MAE, change distance/quality gates, or promote currently held/blocked physiology.

Until that adapter passes schema/merge tests, final multimodal code must continue treating mmWave as a reserved interface rather than a primary predictor block. When it passes, the multimodal 8-subset contribution design may consume only fields whose `multimodal_use` is permitted by `MMWAVE_FEATURE_CONTRACT_V1.csv` at that time.

## 6. AI handoff rule

Any AI touching mmWave must read this file after the repository-wide history ledger and before interpreting old mmWave branches/PRs/issues. If a later material decision changes current state, branch disposition, field semantics, time/window semantics, or multimodal eligibility, update this file in the same canonical `main` work cycle together with the applicable history/status/changelog evidence. Do not reconstruct a newer state from chat memory alone.

## 7. VMD backend decision, frontend clutter evidence, and window semantics — 2026-08-30

### VMD software/backend decision

Upstream facts were re-audited on 2026-08-30 rather than inferred from the old hardening PR:

- standalone `vmdpy` is an archived/read-only project; its own repository states that the package has been officially distributed with and maintained in `sktime` since August 2023;
- PyPI standalone `vmdpy` has only 0.1 and 0.2, with 0.2 released on 2020-08-11;
- `sktime` documents its VMD implementation as the official continuation of `vmdpy`; current stable `sktime` is 1.1.0 (2026-07-28);
- `sktime` 1.0.0 included an explicit VMD bug fix for odd-length input returning an even-length decomposition;
- source review shows the old standalone implementation truncates an odd-length signal (`f = f[:-1]`), whereas the maintained implementation preserves the input length using corrected mirroring and also uses a safe weighted-average helper for zero spectral weights.

Therefore the formal software decision is:

`VMD_BACKEND = sktime.libs.vmdpy.VMD`

`VMD_PACKAGE = sktime`

`VMD_FORMAL_VERSION_TARGET = 1.1.0`

`STANDALONE_VMDPY = HISTORICAL_REFERENCE_ONLY`

`BACKEND_FALLBACK = FORBIDDEN_FOR_FORMAL_RUNS`

The formal environment must pin the tested stable version, not use an open-ended `>=` dependency. A later sktime release must not silently alter a frozen formal run; it requires an explicit dependency update and validation. The maintained implementation follows the same VMD algorithm lineage and core iterative equations, so a fundamental runtime-speed difference is not expected; however byte/numerical identity is not assumed. Before re-authorizing VMD-generated physiology, run a frozen-input parity/smoke check covering representative even-length signals, an odd-length case, and zero/near-zero pathological input, and record downstream selected mode/HR as well as direct decomposition output and runtime. The old standalone package may be used only in an isolated comparison environment for that audit, not as a production fallback.

Current-code mismatch recorded at this decision point: `requirements.txt` still contains `vmdpy>=0.2`, and `scripts/process_vital_signs_v3_1_1.py::_load_vmd()` still attempts `sktime.libs.vmdpy` and then standalone `vmdpy` on any exception. Those are legacy implementation details and are **not the formal contract after this decision**. The corrective code change must remove standalone `vmdpy` from the formal dependency set, pin the selected stable sktime version, import only the maintained backend for formal VMD execution, record package/backend version in outputs/manifests, and fail explicitly rather than changing backend. Do not claim this code correction complete until the two files and tests are actually changed and verified.

The existing explicitly-labelled band-pass alternatives inside the scientific algorithm (`bp_fallback_short_signal`, `bp_fallback_no_valid_mode`) are a separate algorithm-contract question; they are not software-backend fallback and must not be conflated with `_load_vmd()` dependency substitution.

### Near-side bright structure and preprocessing

External FMCW vital-sign literature consistently documents strong static/background components from stationary objects and body parts, multipath/reflections, finite range/angular resolution and DC offset; antenna coupling/direct leakage is another physically possible source. Common front-end controls include range-FFT windowing when raw fast-time data are available, DC/IQ calibration, slow-time static-clutter subtraction or MTI/recursive background estimation, and spatial/temporal target consistency. A fixed near-side bright component therefore must not be labelled direct leakage from amplitude alone.

FocusWave has already tested one directly relevant intervention on the frozen 335-window diagnostic set: post-Range-FFT slow-time complex-mean subtraction before the unchanged selector. It reduced HR selections below 0.30 m but worsened HR/BR bin/channel switching and did not improve BR near-side selection. The decision remains `KEEP_CURRENT_SELECTOR / DO_NOT_ADD_THIS_PRESELECTION_MEAN_SUBTRACTION`. This result rejects that specific implementation for the current selector; it does **not** prove that all physically motivated clutter/DC calibration is useless. The formal stored NPZ is already range-domain DataCube, so ADC/fast-time windowing and some hardware-level DC/IQ operations cannot be retrospectively reconstructed unless an earlier raw representation exists.

### Distance gate

No current numeric physical distance gate is scientifically frozen. Historical `0.30–1.50 m` remains `HISTORICAL_GATE_SENSITIVITY`; selected-bin distance is a radar-selection proxy, not measured participant placement. #26 remains `PHYSICAL_GATE_UNRESOLVED / HARD_EXTERNAL_BLOCKER` because the repository lacks independent session-level placement truth sufficient to establish a current exclusion interval. A distance interval must not be selected by whichever interval minimizes HR error. Reopen only with independent geometry/placement evidence or a protocol/hardware constraint that is external to the outcome being scored.

### What “selector/path validity” means

`selector` means the rules that choose range bin, channel and spectral candidate. `path` means the entire processing chain from range-domain data through target/channel selection, phase extraction, filtering/decomposition, spectral/beat candidates, previous-window continuity and time/frequency fusion to the final HR value. If a 20 s result and a 60 s result are produced through different selector/path states, an MAE difference cannot be attributed to window duration alone. Existing controlled replay showed that restoring the previous-anchor selector and time/frequency fusion can materially change error on the same windows, which is why #25 remains `WAIT_ON_SELECTOR_VALIDITY` rather than simply choosing the duration with lower MAE.

### 20 s, 25 s, 40 s and 60 s are different contracts, not HRV standards

The 20 s window first entered the current targeted-validation evidence chain at commit `472735b6b6af5f98e92ab7815718e81863cb6098` as a block-local target-continuity / ECG-aligned bounded diagnostic (`20 s window / 10 s step / 5 s boundary guard`). The preceding block-reset/ECG-alignment design contract froze block boundaries and marker alignment but did not establish a physiological reason that 20 s is an optimal formal HR window. The later 20 s versus 60 s comparison explicitly remained `PARTIAL / DIAGNOSTIC_ONLY / formal window validity UNRESOLVED`.

Other durations in v3.1.1 have different roles: HR time-course estimation defaults to 25 s internal windows with 5 s steps; VMD decomposition is windowed at 40 s with 20 s steps; the historical 60 s probe-level HR result aggregates existing course points over a trailing 60 s interval. These durations must not be collapsed into one generic “analysis window”.

None of the above authorizes 20 s HRV. Standard short-term HRV convention is approximately 5 min, while ultra-short HRV requires metric-specific validation and is not interchangeable with standard short-term HRV. For FocusWave the earlier blocker is even more fundamental: radar beat timing has not passed ECG R-peak/paired-IBI validation. Therefore `HRV = BLOCKED` remains independent of whether HR uses 20 s or 60 s. If HRV is reopened after beat-level validity passes, the formal HRV duration and metric set must be separately pre-specified; a standard 5 min segment should be the default comparator when available, while any shorter RMSSD/SDNN use requires its own validation and must not be generalized to frequency-domain HRV.
