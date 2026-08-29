# mmWave pipeline scientific audit task — 2026-08-29

Status: `ASSIGNED / #16 PAUSED`

Canonical repository: `greenboo26/focuswave-multimodal-attention-analysis@main`

## Goal

Recover already-completed RS6240 firmware/manual/SDK findings, bind them to the formal experiment output path, then perform the literature-backed line-by-line/logic-block audit of the formal mmWave producer/downstream chain.

This task exists specifically to prevent repeated rediscovery and to explain whether the current `33/37` split reflects acquisition quality or current pipeline eligibility.

## Must read first

1. `PROJECT_STATUS.md`
2. `docs/research/MMWAVE_LITERATURE_EVIDENCE_AND_DECISION_LEDGER_2026-08-29.md`
3. `docs/research/MMWAVE_LITERATURE_EVIDENCE_REGISTER_2026-08-29.csv`
4. `docs/research/MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`
5. `docs/canonical/MMWAVE_CURRENT_STATE_2026-08-29.md`
6. `ANALYSIS_HISTORY_LEDGER.md`
7. current formal mmWave producer/downstream scripts and provenance indexes

## Phase 1 — Recover prior RS6240 upstream evidence

Do **not** restart from generic web/manual discovery first.

Search existing local project records, Git history, prior audit outputs, firmware inspection notes, SDK/manual copies, and existing decision records for the work already performed on:

- `mrs6240_p2512.img`
- firmware SHA-256/build information
- `ReportDataCube1D`
- RS6240 official report format
- range FFT/output semantics
- 2T4R / 8-channel mapping
- distance-bin derivation
- SDK/firmware processing path
- antenna/channel calibration
- chirp/Tx timing and ordering

For every recovered fact provide:

- source path or stable URL
- document/manual/SDK version
- page/section/function/line reference
- exact statement or implementation meaning
- whether it binds to the exact formal firmware image or only to generic SDK/manual behavior
- current confidence/status

Use only these statuses:

- `CONFIRMED_IN_FORMAL_FIRMWARE`
- `CONFIRMED_BY_OUTPUT_SEMANTICS`
- `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY`
- `PRIOR_AUDIT_CONFIRMED_NEEDS_PRIMARY_RELINK`
- `UNRESOLVED`
- `NOT_APPLICABLE`

## Phase 2 — Build the upstream stage matrix

At minimum audit:

1. ADC/IF acquisition
2. ADC DC-offset correction
3. static-clutter/background suppression
4. pre-FFT windowing
5. FFT length / zero padding
6. Range FFT
7. range conversion / cropping
8. chirp aggregation
9. Doppler or zero-Doppler processing
10. normalization/scaling
11. channel calibration
12. 8-channel physical ordering
13. phase calibration/correction before output
14. final `ReportDataCube1D` packing

For each stage report:

- what the literature expects or commonly does
- what the official RS6240 source/manual says
- what the exact formal firmware can be proven to do
- what the output semantics independently prove
- what remains unresolved

## Phase 3 — Line-by-line downstream scientific audit

Audit the current formal processing from `ReportDataCube1D` through HR/BR/HRV/QC.

For every scientifically meaningful logic block record:

- file
- line start/end
- code/operation
- input/output shape and type
- mathematical operation
- scientific purpose
- literature evidence ID(s)
- parameter and source
- whether parameter is frozen/empirically validated/heuristic
- risk if omitted
- risk if duplicated
- respiration attenuation risk
- heartbeat attenuation risk
- harmonic-confusion risk
- bin-hopping risk
- phase-discontinuity risk
- distance-semantics dependency
- current status

Allowed downstream statuses:

- `MATCHED`
- `PROJECT_VARIANT`
- `HEURISTIC`
- `MISSING`
- `POTENTIALLY_HARMFUL`
- `NOT_REQUIRED`
- `UNRESOLVED`

## Phase 4 — Special questions that must be answered

1. Is target selection finding the strongest reflector, a human target, a respiration target, a heartbeat target, or a mixed heuristic?
2. Can range-bin/channel switching create phase discontinuities despite participant stillness?
3. Which “motion/geometry” failures have independent motion evidence and which are algorithmic target/phase/coverage failures?
4. Does the HR estimator actively suppress respiratory 2×/3× harmonics or only flag them afterward?
5. Is HRV based on true beat timing/IBI, and is there ECG beat-level alignment?
6. Which current QC gates primarily measure acquisition integrity, and which primarily measure current-pipeline success?
7. After this audit, what does `33/37` scientifically mean?

## Required durable outputs

Create/update in canonical GitHub:

1. `docs/research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`
2. `docs/research/MMWAVE_LITERATURE_VS_PROJECT_STAGE_MATRIX_2026-08-29.csv`
3. `docs/research/MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`
4. `docs/research/MMWAVE_PIPELINE_FLOWCHART_2026-08-29.md` with Mermaid/source-controlled visual
5. update `MMWAVE_UPSTREAM_FIRMWARE_AND_DATACUBE_EVIDENCE_2026-08-29.md`
6. update `PROJECT_STATUS.md`, `RESULT_INDEX_V1.md`, and `CHANGELOG.md` if material conclusions change

If large local evidence cannot enter Git, record absolute local path + manifest/hash/provenance in a Git-safe index.

## Prohibited

- no new scientific model run
- no #16 sensitivity
- no C2B/C2C rerun
- no new target-lock algorithm
- no AoA/beamforming/VMD/multi-bin search
- no NIR/RGB producer modification
- no raw-data modification
- no blanket `UNVERIFIABLE_UPSTREAM` for facts already established by prior firmware/manual/SDK work
- no claiming SDK defaults are exact formal-firmware behavior without binding evidence

## Completion condition

PASS only when:

- prior firmware/manual/SDK evidence has been recovered and linked;
- known upstream facts are no longer reset to unknown;
- every material producer/downstream stage has a source/evidence/status;
- literature evidence and project implementation are explicitly separated;
- missing/heuristic/potentially harmful processing is enumerated;
- a source-controlled visual flowchart exists;
- the project can state what `33/37` actually measures without conflating participant compliance, acquisition quality, signal quality, and physiology validity.

Otherwise report `PARTIAL` and stop.
