# FocusWave formal multimodal model-ready v1 — 2026-08-30

Status: **PASS_MODEL_READY**.

This package freezes the formal observation-defined matched cohort, participant-disjoint LOSO registry, primary feature contracts, temporal/QC leakage boundaries, and model-ready schema. It is a candidate contract, not a model result: no logistic/RF/LightGBM/MLP model, fusion, Shapley analysis, or producer rerun was executed.

## Frozen denominator

- Full canonical timeline: 1,440 probes, 72 current sessions, 46 repeat participants.
- Primary matched cohort: 1,295 probes, 65 sessions, 46 repeat participants.
- Matching rule: Behavior observed AND NIR observed AND RGB observed; no label-dependent filtering.
- Window: `pre_30s = [probe_onset_unix_ms-30000, probe_onset_unix_ms)` on real `unix_ms`; the canonical key is `repeat_participant_id, session_id, block_id, probe_id, window_name`.
- All 46 matched repeat participants receive one LOSO outer fold. Seven participants have partial session/block coverage after matching; none disappear from the matched participant registry.

## Missingness and QC boundary

- NIR: 1,294 `OBSERVED`, 140 `STRUCTURAL_MISSING`, 5 `OBSERVATION_MISSING` (`sub-083`, block 1, probes 6–10), and 1 `QC_FAIL` (`sub-084`, block 1, probe 6). The QC-fail row remains in the 1,295 observation-defined denominator and its four pupil-geometry values remain NaN.
- RGB: 1,420 `OBSERVED` and 20 `STRUCTURAL_MISSING`, all from `sub-099`. Existing evidence shows source video/timestamps but no `master_timeline.csv`; no processed RGB session, raw parquet, or subject manifest is present. Postprocessing failure, probe-overlap failure, and QC failure are not asserted.
- The full row-level missingness audits and model-ready candidate remain local-only. They are not uploaded to this canonical repository.

## Primary predictor contract

- Behavior: 5 pre-onset RT/error predictors.
- NIR: 4 fullclass pupil geometry predictors; no PIR primary feature.
- RGB: 6 currently formed face-coverage, eyelid geometry/opening, head-motion, and global-motion predictors.
- Blink remains `PROVISIONAL_CANDIDATE` and is excluded from primary predictors. PERCLOS is absent/not validated. mmWave HR/BR/RR, HRV/IBI, continuity/phase/motion, and loadability fields are not primary predictors.
- QC and availability fields are retained for audit, coverage, sensitivity, or stratification only.

## Evidence and reproducibility

`FORMAL_MATCHED_COHORT_SUMMARY.json`, `LOSO_LEAKAGE_AUDIT.json`, the three feature contracts, `BEHAVIOR_TEMPORAL_LEAKAGE_AUDIT.csv`, `formal_model_ready_schema_v1.json`, `MODEL_READY_READINESS_GATE.json`, and `MODEL_READY_READINESS_REPORT.md` contain the aggregate counts, source hashes, semantics, and readiness checks. The participant registry is the compact fold authority; the expanded fold table and all other probe-level tables stay local.

The local full package is retained at:

`C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave\outputs\FocusWave_formal_multimodal_v2_2026-08-30`

The parameterized generator `scripts/maintenance/build_formal_model_ready_v1.py` reads an existing local package plus explicit NIR/RGB roots. It does not launch either producer and has no machine-specific path hardcoded.

Formal baseline modeling is authorized by the readiness gate, but remains a separate next phase. The downstream modeling implementation must declare how it handles the retained NaN geometry row and must not silently alter the matched denominator.
