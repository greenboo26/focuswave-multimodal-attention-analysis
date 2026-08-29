# FocusWave formal model-ready v1 readiness report

Final status: **PASS_MODEL_READY**

The candidate contains 1295 matched probes from 65 sessions and 46 repeat participants, with 46 participant-disjoint LOSO outer folds. No model was trained and no producer was rerun.

## Predictor contract

- Behavior: 5 primary predictors.
- NIR: 4 primary predictors, fullclass pupil geometry only; no PIR.
- RGB: 6 primary predictors: current face coverage, eyelid geometry/opening, head motion, and global motion.
- Blink is retained only as `PROVISIONAL_CANDIDATE`; it is excluded from primary predictors. PERCLOS is absent/not validated. mmWave/HR/BR/RR/HRV/IBI are excluded.

## Missingness and QC

- NIR states are separately represented as structural missing, observation missing, QC fail, or observed. The 1,295-row observation-defined matched denominator is retained; missing geometry remains NaN.
- RGB `sub-099` is diagnosed as structural: no processed producer session/raw parquet/subject manifest, while source video and timestamps exist; the existing audit says `master_timeline.csv` is missing. No postprocessing failure or QC failure is asserted.

## Leakage and denominator gate

- LOSO leakage audit: **PASS**; participant intersection and session/probe checks are recorded in `LOSO_LEAKAGE_AUDIT.json`.
- Behavior predictors are bounded to the pre-onset window; post-probe response/RT and target labels are excluded from predictors.
- The full 1,440-row timeline, 1,295-row matched candidate, and all source hashes are traceable.

## Authorization boundary

`baseline_modeling_authorized = true`. This authorizes the next modeling phase only; it is not a model result. The retained NIR QC_FAIL row requires an explicit downstream NaN policy before fitting.

Local output package: `C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave\outputs\FocusWave_formal_multimodal_v2_2026-08-30`
Generation script: `C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave\work\build_formal_model_ready_v1.py`
