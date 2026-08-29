# Multimodal complementarity / incremental contribution analysis design — 2026-08-30

Status: `DESIGN_FROZEN_FOR_REVIEW / EXECUTION_NOT_AUTHORIZED`

Purpose: define how mmWave, NIR, and RGB should be evaluated for **unique contribution, complementarity, redundancy, and full multimodal gain** without confusing different cohorts, subject leakage, producer quality, or modality availability.

This document is a design/decision record. It does not authorize new producer runs or final multimodal modeling before producer readiness gates are satisfied.

## 1. Scientific question

Primary question:

> On the same participants/probes and under subject-independent evaluation, how much does each modality add beyond context/behavior and beyond the other modalities?

This is deliberately different from asking which modality has the highest standalone accuracy.

The analysis should distinguish:

- **standalone signal**: can one modality predict the target at all?
- **incremental value**: does adding a modality improve held-out prediction over an existing set?
- **conditional contribution**: does a modality still help after other modalities are already present?
- **redundancy**: a modality predicts the target alone but adds little once another modality is present.
- **complementarity / synergy**: two modalities together improve held-out performance more than either one contributes alone.
- **interference**: adding a modality reduces held-out generalization.

## 2. Current project constraints

Current canonical state requires the following boundaries:

- mmWave #16 remains paused pending its separate authorization; corrected `33/37/2` is a current-pipeline QC/eligibility stratification, not participant compliance or physiology validity.
- mmWave HRV remains `BLOCKED`; do not include HRV in the primary multimodal feature set.
- HR is quality-gated/supporting only and BR is supporting only; any use must preserve those qualifications.
- NIR formal increment is `PRODUCER_NOT_READY` for the global matched-cohort result.
- RGB formal incremental modeling is `PRODUCER_NOT_READY`; current RGB state is engineering/raw-context rather than a final formal modality model.
- Therefore the multimodal design can be frozen now, but the final ladder must wait until formal modality contracts and matched denominators are available.

## 3. Primary evaluation unit and leakage rule

### Unit

Primary observation unit: the already-defined aligned probe/window unit used by the canonical multimodal dataset.

### Grouping

All train/validation/test splits must be grouped by **participant identity**, not by session or probe row.

If a participant has repeated sessions, all sessions/probes for that participant must remain in the same outer fold.

Primary generalization scheme: `LOSO / grouped participant-out`.

Any feature scaling, feature selection, imputation, calibration, threshold tuning, or model hyperparameter selection must be fitted inside the training portion of each outer fold.

Rationale: physiological and behavioral signals contain strong subject-specific structure; sample-level random splitting can inflate performance through subject leakage. Recent multimodal physiological work continues to use subject-independent LOSO for this reason.

## 4. Cohort matching rule — mandatory

A comparison is valid only when the two models being compared are evaluated on the **same held-out participants and same probe rows**.

Do not compare:

- `C+mmWave` on 1,400 probes
- against `C+NIR` on a smaller different cohort

and call the AUC difference a modality contribution.

For every pairwise increment, first construct a matched comparison cohort for the modalities involved.

Every result table must report:

- participants
- sessions
- probes/windows
- class counts
- missingness/QC exclusions
- exact outer folds

## 5. Model ladder

Let:

- `C` = context / behavior baseline already defined by the project
- `M` = mmWave formal feature block
- `N` = NIR formal feature block
- `R` = RGB formal feature block

On the same complete matched cohort for all three modalities, fit the full 8-subset ladder:

1. `C`
2. `C + M`
3. `C + N`
4. `C + R`
5. `C + M + N`
6. `C + M + R`
7. `C + N + R`
8. `C + M + N + R`

This exact subset ladder is preferred over immediately training a large deep-fusion model because it directly answers contribution and complementarity questions and is feasible with the current participant scale.

## 6. Primary model family

Primary contribution model: a transparent, regularized model family with the same fitting procedure across all modality subsets.

Recommended primary baseline:

- regularized logistic regression for binary target(s), or the corresponding regularized ordinal/multinomial model if the frozen target is not binary;
- all preprocessing fitted within training folds;
- identical outer folds for every subset;
- hyperparameters selected in an inner grouped/participant-safe loop if tuning is needed.

A more complex model may be used only as a prespecified secondary robustness analysis after the contribution ladder is complete.

Do not use model-family shopping to maximize the apparent multimodal gain.

## 7. Metrics

Primary report metrics:

- ROC-AUC for continuity with the existing project baseline;
- balanced accuracy / macro-F1 where class imbalance matters;
- log loss or Brier score as a probability-quality metric.

For every modality increment, report paired outer-fold differences rather than only two independent summary scores.

Example:

`ΔAUC(M | C) = AUC(C+M) - AUC(C)`

computed on identical held-out predictions.

Use participant-level or fold-level paired bootstrap/permutation confidence intervals where appropriate.

## 8. Unique conditional contribution

For each modality, calculate multiple marginal gains.

For mmWave:

- `Δ(M | C)`
- `Δ(M | C+N)`
- `Δ(M | C+R)`
- `Δ(M | C+N+R)`

Equivalent sets are calculated for NIR and RGB.

Interpretation:

- positive across several baselines → robust unique contribution;
- positive only when alone → likely redundancy with another modality;
- negative after adding another modality → interference/overfitting/quality mismatch;
- near zero throughout → little evidence of incremental predictive value.

## 9. Exact modality-level Shapley contribution

Because there are only three sensor modalities (`M,N,R`), the project can calculate **exact modality-level Shapley values** from the complete 2^3 subset ladder rather than using an approximate feature-level explainer.

Utility can be defined from held-out performance relative to the context baseline. Prefer a proper scoring-rule utility (e.g. improvement in log loss/Brier) for the contribution decomposition, with AUROC-based Shapley reported as an intuitive secondary view.

This yields a fair average marginal contribution for each modality across all orders in which the modalities could be added.

Important: this is a modality contribution analysis, not a causal attribution claim.

Literature precedent: multimodal clinical prediction work has used modality-level Shapley values based on AUROC to quantify the relative contribution of physiological time series, images, and notes.

## 10. Pairwise complementarity / interaction

For each pair of modalities, calculate an operational held-out interaction contrast.

Example for mmWave and NIR conditional on context:

`I(M,N | C) = U(C+M+N) - U(C+M) - U(C+N) + U(C)`

where `U` is the prespecified held-out utility.

Interpretation:

- `I > 0`: evidence that the joint pair contains complementary information beyond separate increments;
- `I ≈ 0`: roughly additive;
- `I < 0`: redundancy, interference, or insufficient sample size/quality.

Repeat for `M×R`, `N×R`, and optionally interactions conditional on the third modality.

These interaction contrasts are operational predictive definitions, not claims about biological causality.

## 11. Reliability / QC stratification

Do not silently treat missing or low-quality modality data as ordinary numeric values.

Each modality must bring its own producer-side validity/QC fields into the merge contract.

Primary analysis:

- use the fully matched formal cohort that satisfies the predefined modality availability/QC contract.

Sensitivity analysis:

- prespecified reliability-aware or missing-modality analysis only after the primary complete matched-cohort result is frozen.

Recent multimodal physiological work shows that reliability-aware fusion can be useful when modality quality varies, but this should be a later robustness layer rather than the first contribution analysis.

## 12. Modality-specific scientific boundaries

### mmWave

Primary multimodal block should use only features allowed by the current mmWave evidence boundary.

- HRV excluded from primary multimodal inference while `BLOCKED`.
- HR/BR must preserve their current qualified status.
- signal-quality, task-dynamics, target/phase, timing, and motion-related features may be included only if their semantic meaning is frozen in the formal feature contract.

### NIR

Do not assume a final NIR feature set until the formal producer contract is ready.

The NIR block should be frozen from the producer schema actually delivered to central analysis, including feature definitions, time aggregation, missingness, QC, and alignment to probe windows.

### RGB

Do not start formal incremental inference from current raw/context engineering outputs.

The RGB block enters the ladder only after the producer defines a formal feature schema, QC semantics, alignment contract, and matched cohort.

## 13. What the final report should answer

The final multimodal report should be able to state, with held-out evidence:

1. How well does context/behavior alone predict the target?
2. What does mmWave add beyond context?
3. What does NIR add beyond context?
4. What does RGB add beyond context?
5. Does mmWave still add after NIR/RGB are already present?
6. Does NIR still add after mmWave/RGB are present?
7. Does RGB still add after mmWave/NIR are present?
8. Which pairs are complementary versus redundant?
9. What is each modality's exact average marginal contribution (Shapley)?
10. Does the full three-modality model improve subject-independent generalization over the strongest simpler model?
11. Are gains stable across participants, or driven by a few individuals/folds?
12. How much performance changes when low-quality/missing-modality cases are included in a prespecified sensitivity analysis?

## 14. Role split

### User / research-decision layer

The user should not have to maintain low-level code/configuration. The material decisions needed from the user are:

1. confirm the primary prediction target/label and which label formulation is report-primary;
2. decide whether rest periods belong to the primary multimodal scientific question or a separate secondary analysis;
3. authorize producer completion/reruns on the local NIR/RGB machines when their owners say the formal contract is ready;
4. approve any later high-impact change to the frozen contribution design.

### ChatGPT / research-design and evidence layer

ChatGPT can:

- perform and maintain the literature review;
- design the contribution/complementarity estimands;
- audit the modality contracts and leakage safeguards;
- write the analysis specification and statistical interpretation rules;
- maintain GitHub decision/evidence records;
- review Codex/local-run outputs and determine whether they satisfy the frozen contract;
- interpret results and prepare report-ready figures/tables/text.

### Codex / local execution layer

Codex on the local project machines should:

- inspect local producer outputs that are not available on GitHub;
- run formal NIR/RGB producer jobs when authorized;
- build the aligned matched-cohort feature matrices;
- execute the frozen LOSO contribution ladder;
- write reproducible scripts, manifests, outputs, and local-large-output indexes;
- sync Git-safe results and decisions back to canonical GitHub in the same work cycle.

## 15. Evidence basis

Key literature used to support this design:

- Multimodal emotion-recognition reviews distinguish unimodal feature extraction and multimodal fusion strategies and emphasize evaluation across modality combinations: Neurocomputing 2023, DOI `10.1016/j.neucom.2023.126866`; Information Fusion 2023, DOI `10.1016/j.inffus.2023.101847`.
- Subject-independent physiological prediction literature uses LOSO because random/sample-level splitting can leak subject identity and inflate apparent performance; see Journal of Engineering Research 2026, DOI `10.1016/j.jer.2026.04.016`, and recent WESAD LOSO work in PMC `PMC13076599`.
- Multimodal medical risk-prediction work reports modality-level Shapley values over AUROC to quantify relative modality contribution; see PMC `PMC10918115` / `PMC10246140`.
- Reliability-aware multimodal physiological fusion remains an active direction for variable-quality modalities; see CVPR Workshops 2026, *Trust What You Fuse: Reliability-Aware Cross-Attention for Multimodal Physiological Stress Assessment in the Wild*.

## 16. Execution gate

Current status: `DESIGN READY / EXECUTION BLOCKED BY PRODUCER READINESS`.

Do not run the final 8-subset multimodal ladder until:

- the target/label is frozen;
- mmWave allowed feature contract is frozen for this task;
- NIR formal producer is ready;
- RGB formal producer is ready;
- a single matched participant/probe denominator and participant-safe folds are frozen.

At that point the next task is implementation of this design, not redesign of the multimodal question.
