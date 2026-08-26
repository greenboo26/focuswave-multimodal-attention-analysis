# SOL Re-review V1

Reviewed branch: `codex/local-analysis-library-canonicalization-20260826`  
Reviewed commit: `ce4da877743132d6a8b4f21a298c58b1b06f3f5e`  
Reviewer: GPT-5.6 Sol  
Status: `REVIEW_COMPLETE_FINAL_SMALL_FIXES_REQUIRED`

## Decision

The first correction pass solved the major scientific-governance problems. The Beijing behavior/context anchor is now valid on the 70-session / 46-participant / 1,400-probe report cohort; producer provenance for the principal completed analyses is materially improved; local-vs-global identity/inference separation is conceptually correct; superseded NIR results are no longer treated as final; and the AMD/NVIDIA branches are correctly treated as divergent implementations rather than assumed equivalents.

However, the branch still does not satisfy the previous review's strict handoff gate. The remaining issues are small and bounded, but several directly affect what another workstation would execute or how final ordinal evidence would be reported.

`AMD_HANDOFF_APPROVAL = APPROVED_AFTER_FINAL_SMALL_FIXES`

Do not create the AMD execution branch yet. A short final gate re-review after the fixes below is sufficient; no broad re-audit or new exploratory analysis is required.

## Items that now pass

### A. Final Beijing C+B baseline — PASS

Verified against producer commit `414a4f46c8d058961a87750345d06a7129afc9f2` and the Git-safe V2 package:

- 70 sessions / 46 natural participants / 1,400 probes;
- label 1 versus labels 2/3/4;
- 30 s primary, 10/20 s sensitivity;
- L2 logistic;
- fixed participant-disjoint 5-fold StratifiedGroupKFold;
- imputation/scaling/model fit inside training fold only;
- participant-cluster bootstrap, 1,000 replicates, seed 20260826;
- old 1,440-probe fallback is not used.

30 s `C+B` ROC-AUC is approximately 0.675 with participant-cluster bootstrap 95% CI [0.621, 0.726]. This is accepted as the Beijing report baseline and the Beijing matched-cohort sensor anchor.

The Beijing `REPORT_FOLDS_V1` assignment may be reused for Beijing-only matched sensor comparisons. It must not be called the future global Beijing+Zhuhai fold assignment.

### B. Producer mapping — PASS WITH MINOR PROVENANCE CLEANUP

The principal completed producers are now correctly identified:

- report cohort / four-class / vigilance / Probe-vigilance: `run_report_cohort_label_vigilance_v1.py`, commit `67851bff212fc1e73b9611ac5de670581e316cc7`;
- repeat-session: `run_report_repeat_session_effects_v1.py`, commit `c2de2af3ba6fd46d351c4da4fcf05e281f982cff`;
- Q1: `run_q1_questionnaire_criterion_validity.py`, commit `ba7a2c652bea82c3fa58ad5858a7460ed933fb47`;
- Beijing baseline V2: `run_final_report_cohort_baseline_v2.py`, commit `414a4f46c8d058961a87750345d06a7129afc9f2`.

Supporting-only historical analyses do not need their missing entrypoints reconstructed merely for completeness. Retained/current provenance should use full 40-character SHAs instead of shortened forms such as `ba7a2c6` or `97b236a`.

### C. Label semantics — PASS

The normative mapping is now correct:

1 = fully task-focused;  
2 = experiment-related but not sorting-task-focused;  
3 = task-unrelated thought;  
4 = mind blank / no specific thought.

The primary binary endpoint remains label 1 versus labels 2/3/4 and must be described as fully task-focused versus other non-fully-task-focused states.

### D. Local production versus central/global inference — PASS IN PRINCIPLE

The intended architecture is correct:

`local raw -> standardized local derived/QC package -> central identity reconciliation -> global repeat_participant_id -> global cohort -> global participant-disjoint folds -> final pooled/site-held-out inference`.

Global merged cohort and global folds are intentionally not frozen yet. Their absence is not a failure at this stage because cross-disk identity evidence is not yet centrally merged.

## Final blocking fixes

### Blocker 1 — Make the actual execution surface standalone, not all 29 historical cards

The first review requested real independent method cards. The correction pass added a useful `Correction-pass verified contract` section, but many cards still retain the old generic template and defer execution-critical fields to the registry/local manifest. Examples include `nir_increment.md`, `nir_fullclass_69_engineering.md`, and `rgb_face.md`.

Do **not** spend time fully rewriting every historical/supporting card. Instead freeze a small `AMD_EXECUTION_RUNBOOK_V1` plus standalone cards/contracts for modules that the colleague may actually execute or that define future main inference:

- local discovery / identity-linkage export;
- NIR AMD production + QC;
- RGB Face AMD production + QC;
- RGB Pose/Motion production + QC if run on that workstation;
- standardized Probe-window export/adapters;
- future NIR increment, RGB increment and multimodal fusion input/output contracts;
- central identity/global-fold boundary.

For each executable module state explicitly: exact repository/ref, exact script, exact config/model assets and hashes where applicable, parameterized input/output roots, required input fields, output schema, timestamp/gap rules, QC, resume/overwrite semantics, manifest requirements, and stop/pass criteria. Historical cards can remain supporting references if clearly marked non-executable.

### Blocker 2 — Resolve modality-specific window-contract conflict

`AMD_NVIDIA_SCIENTIFIC_CONTRACT_V1.md` currently states a generic sensor rule of 30 s primary with 10/20 s sensitivities, while `nir_increment.md` records 30 s primary with 10/60 s sensitivities. These cannot both be normative.

Freeze modality-specific rules rather than a single generic rule:

- behavior/context baseline: 30 s primary; 10/20 s sensitivity;
- NIR increment: 30 s primary; 10/60 s sensitivity, preserving the previously frozen sensor plan;
- current mmWave frozen analyses: retain their already executed 10/30/60 definitions; do not rerun for cosmetic harmonization;
- RGB increment: explicitly freeze its primary/sensitivity windows before prediction modeling; do not inherit 10/20 or 10/60 silently and do not choose by observed AUC;
- multimodal fusion: use the predeclared common window required for an exact matched cohort, normally the 30 s primary comparison.

### Blocker 3 — Clarify local versus global participant identity fields

`DERIVED_DATA_CONTRACT_V1.md` correctly says global `repeat_participant_id` is not frozen independently on each disk, but its required shared fields still list `repeat_participant_id` without qualification.

Separate the concepts explicitly. The local package should contain a stable local linkage key/evidence and may contain a provisional/local repeated-person key when known. The central merge creates the authoritative `global_repeat_participant_id`. The AMD workstation must not manufacture a global key merely to satisfy a required column.

### Blocker 4 — Complete the two pre-specified ordinal-assumption sensitivities

Documentation alone is not enough because the actual completed producers fit common-slope ordinal models without a diagnostic.

For vigilance (4 observed levels), fit cumulative binary participant-clustered logistic GEE sensitivities using the same predictors for thresholds such as `vigilance >= 2`, `>= 3`, `>= 4`. Compare the key progress/state coefficient directions and magnitudes with the common-odds OrdinalGEE result. This is a diagnostic/sensitivity analysis, not a model search.

For Q1, the top >50% category is empty, so the observed outcome has three populated categories. Fit two cumulative thresholds (`Q4 >= 2`, `Q4 >= 3`) using the same standardized predictor definitions and participant-cluster robust inference. Compare directions/magnitudes with the OrderedModel common-odds results.

If threshold effects are reasonably coherent, retain the ordinal common OR as the compact report effect and publish the threshold-specific table as sensitivity. If they materially disagree, keep the ordinal result only with an explicit common-odds limitation and report the threshold-specific pattern; do not search alternate cutpoints to rescue significance.

### Blocker 5 — Freeze backend parity as executable Gate 0

The shared contract is conceptually correct but still says `CONTRACT_FROZEN_FOR_REVIEW_NOT_EXECUTION`. Convert it into an executable gate.

RGB AMD evidence is already strong enough to accept the DirectML scientific backend against its common CPU reference: the real-300 test shows 300/300 coverage, zero face-count mismatch, near-identical bbox and very high agreement for AU/emotion/pose/gaze/mesh/blendshape outputs. NVIDIA still requires its own CPU-reference-to-CUDA representative gate before NVIDIA full formal Face production; comparing different subjects across machines is not a parity test.

NIR AMD v0.2.0 has useful internal benchmark evidence, but the current release note is not direct CUDA-vs-DirectML scientific parity evidence. Before bulk AMD NIR production, Gate 0 must run a small frozen representative input through the AMD implementation and a common accepted reference, then compare detection/ROI/timestamps/fullclass-derived quantities under predefined tolerances. Bulk execution stops if the gate fails.

A full-data cross-machine duplication is unnecessary; a small representative copied sample is sufficient.

## Final-report corrections that do not need to block AMD branch creation after the above fixes

### 1. Pre-Probe error-rate model sensitivity

The newly published pre-Probe package is useful and its direction is plausible, but its current script fits Gaussian GEE directly to `error_rate`. Because pre-Probe windows can contain different numbers of trials, a binomial count/rate model using the available error numerator/`n_trials` denominator is statistically preferable. The already completed vigilance runner demonstrates this approach for the 10 s error rate.

Before final report lock, add a predefined binomial-GEE sensitivity for 10/20/30 s using the same label contrast, progress/block adjustment and participant clustering. Do not change windows based on results. This is not required to prepare the AMD sensor-production branch, but it is required before final manuscript/result-table freeze.

### 2. Q1 corrected semantic publication

Keep the historical producer commit untouched as provenance, but publish a current canonical Q1 result note/table whose code labels obey the normative code 3/4 semantics. Do not silently rewrite history. The numerical association by code can be retained if the source columns are verified to correspond to those codes.

### 3. Calibration wording

The Beijing C+B baseline has useful discrimination but should not be advertised as well calibrated merely because calibration bins were exported. Report Brier/calibration descriptively and reserve stronger calibration claims for a dedicated calibration assessment.

## Gate outcome

This correction pass is close to approval. No new broad analysis family is authorized, and global cohort/folds remain intentionally deferred until central cross-disk identity reconciliation.

Next expected status after the bounded fixes: `READY_FOR_SOL_FINAL_GATE`.
