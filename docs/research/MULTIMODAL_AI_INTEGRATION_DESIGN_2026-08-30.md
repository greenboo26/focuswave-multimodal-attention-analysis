# Multimodal AI integration design — 2026-08-30

Status: `DESIGN READY / EXECUTION BLOCKED BY PRODUCER READINESS`

Purpose: define how AI should be integrated into the mmWave + NIR + RGB multimodal attention analysis without replacing the interpretable scientific contribution analysis or creating leakage/overfitting risk.

## 1. Core principle

AI should enter the project as a **secondary predictive/fusion layer**, not as a substitute for the primary scientific question.

Primary scientific question:

> On the same participant/session/probe denominator, what independent, redundant, and complementary information do mmWave, NIR, and RGB add beyond context/behavior?

Primary scientific analysis remains the interpretable modality ladder:

- C
- C+M
- C+N
- C+R
- C+M+N
- C+M+R
- C+N+R
- C+M+N+R

with matched cohort, participant-disjoint LOSO, incremental delta metrics, pairwise interaction and exact three-modality Shapley contribution.

AI is added **after this baseline contract is frozen**.

## 2. Three places AI can enter

### Layer A — AI feature extraction

Use mature/pretrained modality-specific models to turn raw/high-dimensional windows into compact representations.

- mmWave: temporal/spectral encoder on validated range/phase/HR/BR/task-dynamics representations; do not feed blocked HRV as validated physiology.
- NIR: pretrained eye/face/ocular encoders or task-specific embeddings from validated NIR producer outputs.
- RGB: pretrained face/posture/action/visual-temporal encoders or validated producer embeddings.

Prefer pretrained/frozen encoders or heavily regularized shallow adaptation. Do not train large modality encoders from scratch on the current cohort.

### Layer B — AI multimodal fusion

Recommended secondary AI architecture:

```text
mmWave window/features -> modality encoder -> z_M ---\
NIR window/features    -> modality encoder -> z_N ----> quality-aware gated fusion -> attention-state head
RGB window/features    -> modality encoder -> z_R ---/
Context/behavior       -> small tabular encoder -> z_C -/
```

The fusion block should receive both modality embeddings and modality-quality/missingness indicators.

Recommended order of complexity:

1. regularized concatenation MLP;
2. quality-aware gated late fusion;
3. small cross-modal attention model only if 1–2 show reproducible held-out benefit.

Do not start with a large Transformer/cross-attention architecture.

### Layer C — AI output interpretation/product layer

The predictive model can output:

- attention/mind-wandering probability;
- confidence/uncertainty;
- modality contribution for the current prediction;
- modality quality/missingness state.

A later product/report layer may use an LLM to turn these structured outputs into readable explanations, but the LLM must not invent physiological states from raw sensor signals and must not be part of the scientific ground-truth label generation.

## 3. The recommended AI model for this project

Use a **quality-aware mixture/gating model** as the main AI fusion candidate.

For each probe/window:

- `z_M`: mmWave representation
- `z_N`: NIR representation
- `z_R`: RGB representation
- `z_C`: context/behavior representation
- `q_M/q_N/q_R`: modality quality or availability indicators

A small gating network outputs weights:

`w_M, w_N, w_R, w_C`

Then:

`z_fused = w_M*z_M + w_N*z_N + w_R*z_R + w_C*z_C`

or a concatenated gated representation.

Scientific motivation:

- mmWave can fail because current target selection/phase eligibility fails;
- NIR can fail because eye/face signal is unavailable or low quality;
- RGB can fail because face/pose/motion visibility is poor;
- therefore equal weighting is not scientifically justified.

The gate is allowed to learn **which available modality to trust for prediction**, but it must not turn a QC proxy into a physiology-validity claim.

## 4. AI must be tested against the interpretable baseline

The AI model is only useful if it beats simpler models under the same participant-disjoint folds.

Required comparisons:

- regularized logistic baseline
- simple MLP concatenation
- quality-aware gated fusion
- optional small cross-modal attention model

All must use the same matched cohort and fold assignments.

Report:

- AUROC / balanced accuracy / macro-F1 as appropriate
- calibration/Brier score
- participant-level confidence intervals
- incremental delta over C baseline
- incremental delta over best non-AI fusion
- missing-modality robustness

If the AI model does not materially improve held-out generalization, keep the interpretable model as the primary result.

## 5. Missing-modality robustness

The deployed/research model should be tested under:

- all three modalities available
- M missing
- N missing
- R missing
- two modalities available

Training may use modality dropout, but evaluation must use fixed predefined ablations.

This directly answers whether the system is robust when one sensor fails and whether one modality is effectively unnecessary.

## 6. Explainability that is scientifically useful

Do not rely only on generic feature SHAP.

Use two levels:

### Global modality contribution

Use the exact 8-combination modality ladder and Shapley contribution for M/N/R.

### Per-prediction contribution

For the AI model, report gating weights / modality attribution only as model behavior, not causal evidence.

A useful per-probe output is:

```text
prediction: mind-wandering probability 0.72
mmWave quality: medium / contribution: low
NIR quality: high / contribution: high
RGB quality: high / contribution: medium
uncertainty: moderate
```

This is more interpretable for a product/report than a single black-box probability.

## 7. AI-native research questions

Secondary questions that can be answered once all producers are ready:

1. Does quality-aware AI fusion outperform equal/simple concatenation?
2. Does learned gating shift between modalities across participants or task states?
3. Can the AI model maintain performance when one modality is missing?
4. Does AI fusion add performance after the exact modality Shapley/interaction analysis shows what is redundant vs complementary?
5. Does a small cross-modal interaction model improve only when specific modality pairs are jointly available?

These are predictive questions, not causal physiology claims.

## 8. Leakage/overfitting rules

Mandatory:

- participant-disjoint LOSO or nested participant-level CV;
- all preprocessing, feature selection, scaling, hyperparameter tuning inside training folds;
- no probe/window random split across the same participant;
- no using test participant labels to tune modality quality gates;
- no training large deep encoders from scratch on the current cohort;
- no changing architecture after inspecting test-fold outcomes without a new predefined evaluation.

## 9. Current project boundary

AI multimodal execution is blocked until NIR and RGB producer contracts are formal-ready and the mmWave input boundary remains frozen.

The AI design can be implemented now as code skeleton/contracts, but final model training must wait for a matched, versioned feature matrix from all modalities.

## 10. Recommended execution order

```text
1. Freeze primary outcome and matched-cohort definition
2. Freeze C/M/N/R feature contracts and QC/missingness fields
3. Run interpretable 8-model modality ladder
4. Compute incremental deltas + Shapley + pairwise interaction
5. Train simple MLP fusion
6. Train quality-aware gated fusion
7. Only if justified, train small cross-modal attention model
8. Run same LOSO folds + calibration + missing-modality ablation
9. Compare AI vs simple fusion
10. Promote only reproducible held-out gain into final report
```

## 11. Decision

`AI_INTEGRATION_DESIGN = READY`

`AI_MODEL_EXECUTION = BLOCKED_BY_PRODUCER_READINESS`

The recommended scientific/product framing is:

> interpretable multimodal contribution analysis establishes what each sensor adds; AI then learns a quality-aware fusion rule across those validated modality representations, and must prove additional participant-held-out predictive value beyond the simpler fusion baseline.
