# SOL Scientific Review V1

Review branch: `sol/scientific-review-20260826`  
Reviewed canonicalization commit: `da4b7b536ec8540487435dd0eba1388d24164315`  
Reviewer: GPT-5.6 Sol  
Status: `REVIEW_COMPLETE_FIXES_REQUIRED`

## Executive decision

The project-level scientific direction is sound and should be retained:

`protocol/identity -> label validity -> behavioral validity -> questionnaire convergence -> behavior/context baseline -> single-modality incremental value -> multimodal fusion -> cross-site validation`.

The current canonicalization branch is **not yet safe to hand directly to the AMD workstation for whole-project execution**. The main blocker is not that the scientific questions are fundamentally wrong. The blocker is that the canonicalization deliverables remain an inventory rather than a fully specified, independently executable scientific contract: several registry rows point to the wrong historical scripts, many method cards are generic templates, some completed aggregate results are not present on the reviewable branch, and global identity/fold rules are not yet separated cleanly from local-machine derived production.

`AMD_HANDOFF_APPROVAL = APPROVED_AFTER_FIXES`

No AMD execution branch should be created yet. After the fixes listed below are completed and pushed, Sol should perform a short gate re-review. Only an explicit `APPROVED` on that re-review permits creation of the colleague execution branch.

## What is scientifically already strong

### 1. Primary psychological endpoint

The primary binary endpoint `probe_response = 1` versus `2/3/4` is defensible for the competition model because label 1 is the uniquely clear fully task-focused state, while the raw four-class layer is retained for psychological interpretation. The canonical mapping must remain:

- 1: fully task-focused;
- 2: experiment-related but not sorting-task-focused;
- 3: task-unrelated thought;
- 4: mind blank/no specific thought.

Labels 2/3/4 must not be collectively described as mind-wandering.

### 2. Participant dependence and leakage control

Using `repeat_participant_id` as the grouping unit is mandatory. All sessions from the same natural person must remain in the same train/test group. Probe windows end at probe onset, so no post-probe information enters prediction. These are appropriate protections against pseudoreplication and leakage.

### 3. Behavior/label validity chain

The Beijing evidence is coherent: task progress is associated with lower probability of full task focus, vigilance declines with progress, and higher vigilance is associated with fewer pre-probe errors. The questionnaire Q4 result further converges with the session-level proportion of Probe states. Together these are more persuasive than treating Probe self-report as an isolated ground truth.

### 4. Sensor incremental evaluation

The matched-cohort principle is correct. Each sensor model must be compared with `C+B` on exactly the same probes, participants and folds. The primary sensor window should remain fixed rather than chosen by the best AUC. This is the correct architecture for NIR/RGB/mmWave increment claims.

### 5. mmWave stopping decision

The current mmWave evidence is sufficient to stop expanding the present feature family during this competition cycle. C1 does not validate reliable beat-to-beat HRV; C2B/C2C do not show stable incremental value beyond behavior/context; M1 suggests only limited feature-specific person structure. These are useful boundaries, not proof that the RS6240 hardware is incapable of HRV measurement.

## Critical fixes required before AMD handoff

### Critical 1 — Replace generic analysis cards with real method cards

The 29 current cards largely repeat a template such as “see registry/local manifest” and do not independently state the actual scientific method. For every analysis that is retained as `KEEP_MAIN`, `KEEP_SUPPORTING`, `RERUN_CANONICAL`, `REVISE_METHOD`, or is required for colleague-side derived production, the card must contain:

- exact scientific question;
- exact producer script and producer branch/commit;
- exact input asset(s) and required columns;
- unit of analysis;
- inclusion/exclusion and QC rules;
- model formula, family and link;
- repeated-participant handling;
- window definition;
- preprocessing/imputation/scaling location relative to CV;
- CV/fold construction where applicable;
- bootstrap and multiplicity family;
- output files and exact output schema;
- completed aggregate results, if already run;
- interpretation boundary;
- whether the colleague must reproduce it, produce only local derived data, or not run it at all.

A card that only points to another manifest is insufficient for remote execution.

### Critical 2 — Correct registry producer/entrypoint mapping

The canonical registry currently maps several analyses to generic or older scripts rather than the scripts that actually produced the reviewed results. Examples verified during this review include:

- `REPORT_COHORT` / four-class / vigilance results were produced by `scripts/run_report_cohort_label_vigilance_v1.py`, not the generic audit entry registered in the canonical table;
- `REPEAT_EFFECTS` was produced by `scripts/run_report_repeat_session_effects_v1.py`, not `scripts/analyze_formal_cross_subject.py`;
- `Q1_QUESTIONNAIRE` was produced by `scripts/run_q1_questionnaire_criterion_validity.py`, not `scripts/evaluate_mmwave_behavior_criterion.py`.

The same producer audit must be completed for all 29 IDs. Historical scripts may remain listed as upstream/supporting code but must not be called the canonical producer unless verified.

### Critical 3 — Resolve the final behavior baseline cohort

`FINAL_BEHAVIOR_CONTEXT_BASELINE_V1` was run on the 72-session/1,440-probe C2A fallback because the 70-session report cohort did not yet exist on its branch. Therefore V1 cannot be the final report anchor.

The local inventory mentions `final_report_cohort_baseline_v2`. Before handoff, either:

1. if V2 genuinely exists, upload a Git-safe aggregate report, metrics table, calibration summary, redacted manifest and exact producer/config, then verify the cohort is exactly 70 sessions / 46 natural participants / 1,400 valid probes; or
2. rerun the baseline on that 70/1,400 Beijing report cohort without changing the model definition.

Do not preserve the contradictory registry phrase `72 sessions/1400 probes`.

The final global model folds are **not** the Beijing folds. After the external disk is linked and cross-disk identity reconciliation is completed, a new global participant fold assignment must be frozen centrally.

### Critical 4 — Separate local-machine production from global inference

The AMD workstation must not independently create the final global `repeat_participant_id` map or final ML folds. Its execution contract should produce local evidence and standardized derived tables, including source/session identity evidence, but the central integration stage must resolve any cross-disk duplicate/repeat participants before global folds are generated.

Correct flow:

`local raw data -> local standardized derived package -> central identity reconciliation -> global cohort -> global folds -> final inferential/statistical models`.

Local descriptive QC is allowed. Final cross-site p-values/AUCs should not be calculated independently on two machines and then averaged.

### Critical 5 — Correct superseded/status semantics

The current registry status taxonomy does not yet reflect scientific history correctly. At minimum:

- `EARLY_INCREMENT` -> `SUPERSEDED`;
- `C3A_V1` -> `SUPERSEDED_INTERMEDIATE`;
- `C3A_V2` -> `SUPERSEDED_INTERMEDIATE`;
- `NIR_69` should be renamed/split as `NIR_FULLCLASS_69_ENGINEERING` and must not be treated as the final NIR prediction result;
- C1 existing result should be represented as a valid stopped-validation boundary rather than merely “external storage blocked”;
- D1 old blocker status should be recoded as `DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE`, not evidence of missing/failed Zhuhai data.

### Critical 6 — Fix Q1 label text and ordinal-model documentation

The Q1 report contains a textual reversal of the canonical Chinese descriptions of labels 3 and 4. The code-value interpretation must be corrected throughout the repository before final reporting.

For Q1 and vigilance ordinal models, document the proportional-odds assumption. A full new model search is not required; an assumption diagnostic or predeclared threshold-specific sensitivity is sufficient if the assumption is questionable.

### Critical 7 — Make the Probe-before behavior validity result independently reviewable

The repository currently exposes descriptive 10/20/30-second trajectories and the B1-late/B2-early recovery comparison, but the canonical branch does not expose a complete, clearly identified final Probe-state contrast package. Because Probe-before error is an important objective validity link, its final aggregate result must be uploaded with:

- exact window definition;
- state comparison/contrast;
- model family;
- participant clustering/random effect;
- multiplicity family;
- aggregate effect sizes/CIs/q-values;
- actual runner and provenance.

Do not rely on a chat-memory statement for the final report.

### Critical 8 — Freeze a shared AMD/NVIDIA scientific contract before combining image-derived features

The current `Attention-Analysis` hardware branches are not merely identical code with different providers: they have diverged histories. Some shared scientific-layer files are identical, but branch identity alone does not prove numerical or semantic equivalence.

Before the AMD handoff, freeze:

- shared schema version;
- feature definitions and units;
- timestamp/gap rules;
- sampling schedules;
- QC definitions;
- model hashes;
- backend-specific runner commits;
- `runtime_backend` provenance;
- representative parity tests and tolerances.

The goal is scientific equivalence, not bitwise identity. Continuous features may differ slightly across CUDA and DirectML, but gross face counts, ROI decisions, missingness, timestamps and feature semantics must be consistent within predefined tolerances.

### Critical 9 — Recover only missing producers that are actually needed

Three production entrypoints were reported missing from the canonical branch: `probe_program_version_audit.py`, `run_c2b_v2_canonical_reconstruction.py`, and `run_c2c_within_subject_normalization.py`.

Do not spend time restoring every historical script merely for completeness. Recover/parameterize a missing producer only if:

- it is required to reproduce a retained final result; or
- the colleague must run that analysis on the external disk.

For example, current C2B/C2C mmWave results can remain supporting evidence without forcing an AMD-side rerun if the external disk is not needed for a final mmWave replication/ablation. The remote handoff should be minimal, not a museum of historical scripts.

### Critical 10 — Freeze software/provenance for retained runnable modules

For every runnable module sent to the colleague, record at minimum:

- Python version;
- package lock/snapshot;
- random seed;
- code commit;
- config digest;
- model file hash where applicable;
- output schema version;
- input discovery root and site/session filter;
- overwrite/resume policy.

Historical results that cannot recover all of these may remain supporting evidence with an explicit reproducibility limitation, but they should not be silently represented as fully reproducible canonical runs.

## Statistical-method review

### Probe four-class and vigilance analyses

Participant-clustered GEE is an appropriate marginal approach for repeated Probe observations. One-vs-rest models for the four classes are acceptable for descriptive state trajectories, especially because labels 3 and 4 are sparse, but they are not a coherent multinomial probability model; the report must retain that limitation. There is no need to add an elaborate multinomial model solely for methodological aesthetics.

Ordinal GEE for vigilance is reasonable provided the scale direction is fixed and the proportional-odds assumption is documented. State-vigilance and vigilance-error associations belong in one validity analysis family, not as several independent headline studies.

### Repeat-session effects

The question is worth retaining as a robustness analysis. The existing mixed-model specification addresses repeated participants, and the earliest-three-session sensitivity is important because the fourth session is represented by only one participant. Variational-Bayes logistic mixed-model intervals/p-values are approximate; therefore these results should remain supporting/sensitivity evidence and should not be used for a strong causal “practice effect” claim. Session order should not automatically become a prediction feature.

### Questionnaire validity

The Q4 analysis provides convergent/criterion-supportive evidence, not a gold standard for individual Probe windows. Clustered inference is appropriate given repeated sessions. Because the top ordinal category is empty, category distribution and proportional-odds assumptions should be stated explicitly. The conditional RT result whose direction differs from the marginal association should remain exploratory.

### Behavior/context prediction baseline

Five-fold participant-grouped cross-validation is reasonable with 46 independent Beijing participants. Imputation, scaling and fitting must occur inside each training fold. Report ROC-AUC, PR-AUC, balanced accuracy, sensitivity, specificity and calibration. State which class is positive and report its prevalence. A fixed 0.5 threshold is acceptable as a prespecified descriptive threshold, but should not be presented as an optimized operational threshold.

### Sensor increment

Each incremental comparison must use identical probes, participants and folds on both sides of the comparison. Do not compare raw AUCs across different modality-specific cohorts as evidence that one modality is superior.

For the final NIR/RGB multimodal comparison, the cleanest primary comparison is a complete multimodal common cohort containing all four models:

- `C+B`;
- `C+B+NIR`;
- `C+B+RGB`;
- `C+B+NIR+RGB`.

This allows direct modality comparison. Modality-specific larger-cohort increment analyses can be secondary coverage analyses.

Because sensor QC may depend on state/site/participant, also report the QC/coverage attrition chain by site and label; this is a missing-data/selection diagnostic, not a new predictive model.

### Cross-site validation

Two distinct questions must not be conflated:

1. pooled shared-primary performance: Beijing B1+B2 + Zhuhai B1+B2 with participant-grouped CV and `site` retained;
2. true external transportability: model and hyperparameters frozen on Beijing, evaluated once on Zhuhai B1+B2.

If Zhuhai is used for tuning, model selection or threshold selection, that analysis can no longer be described as an external validation. Zhuhai B3 remains a long time-on-task extension rather than part of the shared primary endpoint.

## Final minimum analysis set for the report

The 29 registry rows should remain as project history, but the final report should converge to a much smaller scientific set:

1. **Protocol, identity and cohort definition** — program family, site, repeated participants, shared-primary/B3 extension, sample flow.
2. **Psychological/behavioral validity** — Probe four-class structure, vigilance trajectory, Probe-vigilance link, Probe-before objective behavior.
3. **Questionnaire convergent validity** — Q4 and the clearly supported behavioral relation.
4. **Repeat-session robustness** — supporting/sensitivity only.
5. **Behavior/context baseline** — the canonical anchor model.
6. **mmWave boundary/ablation** — concise C1 + C2B/C2C summary; M1 in supplement unless needed to explain normalization.
7. **Final NIR increment** — canonical 30 s primary + fixed sensitivities.
8. **Final RGB increment** — same statistical contract.
9. **Final NIR+RGB fusion** — common-cohort simple fusion.
10. **Cross-site validation** — pooled shared-primary and/or genuinely held-out Zhuhai evaluation, clearly distinguished.

Everything else is engineering provenance, historical evidence or supplement.

## Final report evidence chain

The recommended narrative is:

`formal protocol and reliable participant/session identity`

-> `Probe labels have interpretable psychological structure`

-> `vigilance and objective behavior change consistently with those states`

-> `session-level questionnaire self-report converges with Probe behavior`

-> `behavior/context provides a reproducible baseline`

-> `test whether each non-contact sensor adds information beyond that baseline`

-> `test whether NIR+RGB fusion adds further information`

-> `verify transportability across Beijing/Zhuhai without participant leakage or site tuning`.

This is substantially stronger than centering the report on mmWave/HRV algorithm optimization.

## Superseded / do-not-cite-as-final list

Do not use the following as final headline results:

- early minimum sensor increment baseline (`EARLY_INCREMENT`);
- C3A NIR v1 12-participant result;
- C3A NIR v2 14-participant/234-probe result;
- the 1,440-probe behavior baseline V1 as the final canonical baseline;
- old 1,278-probe mmWave coverage claim;
- D1 external-storage blocker as if it were a negative Zhuhai data result.

They may remain in provenance/history with clear superseded labels.

## AMD handoff decision

`AMD_HANDOFF_APPROVAL = APPROVED_AFTER_FIXES`

The colleague branch should **not** yet be created. The next step is one focused Codex correction pass on the canonicalization branch. That pass should not launch new exploratory analyses. It should correct the registry, populate real method cards, expose the missing reviewable aggregate packages, freeze local-vs-global execution boundaries, and define the cross-backend contract.

After that correction pass is pushed, Sol should perform a short gate review. If the critical items above are resolved, the AMD branch can then be created with only the modules the colleague actually needs to execute on the external disk.
