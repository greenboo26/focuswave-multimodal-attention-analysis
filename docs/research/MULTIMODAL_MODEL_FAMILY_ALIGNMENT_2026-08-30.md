# Multimodal model-family alignment — 2026-08-30

Status: `DESIGN CLARIFICATION / NO MODEL RUN`

Purpose: align the competition/proposal model wording (`logistic regression`, `random forest`, `neural network`) with the canonical multimodal complementarity and AI-fusion strategy. This is an addendum to `MULTIMODAL_COMPLEMENTARITY_ANALYSIS_DESIGN_2026-08-30.md` and `MULTIMODAL_AI_INTEGRATION_DESIGN_2026-08-30.md`; it is not a parallel analysis system and does not authorize execution.

## 1. What each model is for

### Logistic regression

Role: interpretable primary baseline for the 8-subset modality ladder.

Use the same matched participant/session/probe denominator and the same participant-disjoint LOSO folds for:

- C
- C+M
- C+N
- C+R
- C+M+N
- C+M+R
- C+N+R
- C+M+N+R

This family is used to quantify modality incremental value, conditional contribution, pairwise interaction, and modality-level Shapley contribution without confounding the scientific question with model complexity.

### Random forest

Role: prespecified nonlinear robustness model.

It asks whether the same multimodal signal remains useful when nonlinear feature relations and interactions are allowed. It must use the same matched cohort and the same outer LOSO folds as logistic regression. Random forest does not replace the interpretable primary ladder and must not be selected only because it yields a larger test score.

LightGBM may be added later as an optional tree-boosting robustness model, but it is not required for the proposal wording and should not displace the planned random-forest comparison.

### Neural network

Role: AI fusion model family.

The neural-network progression is:

1. simple concatenation MLP — all validated modality features are concatenated and passed through a small network;
2. quality-aware gated fusion — the model also receives modality quality/availability fields and learns how much to rely on mmWave, NIR, RGB, and context for each probe/window;
3. optional small cross-modal attention model only if the simpler neural models show reproducible participant-held-out benefit.

Do not begin with a large Transformer or train large encoders from scratch on the current cohort.

## 2. LOSO is the common evaluation rule, not another model

`LOSO = Leave-One-Subject-Out`.

For each fold, all data from one participant are held out for testing and every session/probe belonging to that participant stays outside training. The same fold assignment must be reused across logistic regression, random forest, MLP, gated fusion, and any optional later model.

All scaling, imputation, feature selection, calibration, and hyperparameter tuning must occur inside the training data of each outer fold.

## 3. Canonical analysis order

The model families are not alternatives chosen by score shopping. They have different scientific roles and are evaluated in order:

1. Freeze primary outcome, feature/QC contracts, matched cohort, and participant-level folds.
2. Run the full 8-subset ladder with regularized logistic regression.
3. Compute paired incremental deltas, conditional contribution, pairwise interaction, and exact modality-level Shapley values.
4. Run random forest on the same subsets/folds as a nonlinear robustness analysis.
5. Run a simple MLP fusion model on the same matched cohort/folds.
6. Run quality-aware gated fusion to test whether dynamic trust in mmWave/NIR/RGB improves held-out prediction.
7. Test missing-modality robustness with predefined M/N/R ablations.
8. Only if steps 5–7 show reproducible improvement, consider a small cross-modal attention model.
9. Promote the simplest model that provides reproducible participant-held-out benefit; do not promote a more complex model merely because it is labeled AI.

## 4. How this maps to the proposal wording

A concise proposal-compatible description is:

> 本研究首先采用逻辑回归建立可解释基线，并使用随机森林评估非线性特征关系；在此基础上构建轻量神经网络进行多模态融合，并进一步探索基于模态质量的门控融合模型，使模型能够根据毫米波、NIR 与 RGB 在当前时间窗的可用性与质量自适应调整信息权重。所有模型均采用被试级独立交叉验证（LOSO）评估对未见被试的泛化能力。

This wording preserves the original planned methods while giving each method a non-redundant scientific role.

## 5. Multimodal scientific question remains primary

The project does not define success as `which algorithm has the highest AUC`.

Primary questions remain:

- what mmWave adds beyond context/behavior;
- what NIR adds beyond context/behavior;
- what RGB adds beyond context/behavior;
- whether a modality still adds value after the other modalities are present;
- which modality pairs are complementary vs redundant;
- whether full M+N+R improves subject-independent generalization over simpler subsets;
- whether quality-aware AI fusion improves over simple fusion under identical folds.

## 6. Current execution boundary

`MULTIMODAL_ANALYSIS_DESIGN = READY`

`MODEL_FAMILY_ALIGNMENT = READY`

`FINAL_MULTIMODAL_EXECUTION = BLOCKED_BY_PRODUCER_READINESS`

Do not run the final multimodal ladder or AI model until NIR/RGB formal producer contracts, the mmWave allowed feature block, target/label, matched denominator, and participant-safe fold contract are frozen.

No scientific model, #16, NIR/RGB producer, or raw-data operation is authorized by this document.

## 7. Time-budgeted execution priority

The project already collects behavior + mmWave + NIR + RGB within the same acquisition session, and every modality has timestamps for temporal alignment. A participant/session/probe mother table already exists. Therefore the project must **not** budget time as if cross-source identity reconstruction or de-novo multimodal alignment were required.

The remaining merge step is narrower:

- attach each producer's formal feature/QC outputs to the existing mother-table/probe timeline;
- verify timestamp/window mapping and probe labels;
- audit missing/QC cases;
- freeze the common matched denominator and participant-level LOSO folds.

If the producer outputs already expose the required timestamps/probe identifiers and formal features, this merge/audit step should normally be a short task (roughly tens of minutes to ~1–2 hours), not the dominant schedule bottleneck. Longer delays would indicate producer/schema/QC readiness problems rather than a fundamental multimodal alignment problem.

Implementation/runtime estimates after formal modality outputs are ready:

- Existing mother-table attach + timestamp/QC/missingness verification + matched cohort freeze: roughly 0.5–2 hours when schemas are clean.
- Regularized logistic 8-subset ladder + LOSO + incremental deltas: about 1–3 hours. Shapley and pairwise interaction are cheap after the 8 models exist and usually add well under 1 hour.
- Random forest on the same folds/subsets: about 1–3 hours including a restrained hyperparameter grid and reporting. It is optional if the deadline is severe.
- Simple MLP concatenation: about 2–4 hours including implementation, training, basic tuning, convergence checks, and report generation.
- Quality-aware gated fusion: about 3–6 hours after the MLP pipeline works, because it adds model code, QC/availability inputs, stability checks, and comparison against simple fusion.
- Missing-modality robustness/ablation: about 1–3 hours once the trained pipeline exists.
- Small cross-modal attention / Transformer-like model: roughly 0.5–1.5 additional working days including implementation, tuning, overfitting checks, and fair comparison. This is not deadline-critical and should be skipped unless simpler neural fusion has already produced a reproducible gain.

Time-priority decision under a tight deadline:

1. Must do: reuse existing mother table + timestamp-aligned formal outputs, freeze matched cohort and participant-safe LOSO, run logistic 8-subset ladder, and compute incremental contribution/complementarity.
2. Strongly preferred if time remains: random forest OR simple MLP. If only one can be added, prefer the simple MLP when the project needs an explicit AI model, and prefer random forest when the priority is methodological robustness with minimum implementation risk.
3. Optional: gated fusion only after the simple MLP baseline is stable and there is enough time for a fair held-out comparison.
4. Skip under deadline pressure: cross-modal attention / Transformer and LightGBM expansion.

Given the existing synchronized acquisition/timestamps and mother table, the likely schedule bottleneck is now **formal NIR/RGB producer readiness and feature/QC availability**, not multimodal temporal alignment itself.
