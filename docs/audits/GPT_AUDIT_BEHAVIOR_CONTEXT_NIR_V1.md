# GPT_AUDIT_BEHAVIOR_CONTEXT_NIR_V1

Status: `AUDIT_DECISION_MEMO_V1`

Date: 2026-08-26

Scope: joint audit of the frozen behavior/context baseline and the reported NIR matched-cohort analysis. This memo records interpretation and decision rules only; it does not modify model outputs, cohorts, folds, or raw/derived data.

## 1. Evidence provenance

### Behavior + context baseline

Remote GitHub evidence verified from commit `414a4f46c8d058961a87750345d06a7129afc9f2` (`feat: freeze report cohort baseline v2`).

Frozen baseline:

- 46 repeat participants
- 70 formal sessions
- 1400 valid probes
- label: `1` vs `2/3/4`
- primary window: 30 s
- sensitivity windows: 10 s, 20 s
- model: L2 logistic regression
- validation: fixed 5-fold `StratifiedGroupKFold`
- grouping: `repeat_participant_id`, participant-disjoint
- imputation, scaling, and fitting performed within training folds only
- 30 s ROC-AUC:
  - C context only: 0.593
  - B behavior only: 0.639
  - C+B: 0.675

The frozen baseline also states that downstream NIR, RGB, and multimodal analyses should reuse the participant-level fold assignment rather than regenerate folds.

### NIR analysis

The following NIR results were reported by Codex from local analysis branch `codex/nir-69session-final-probe-analysis-v1`, local commit `6c0fae8afd3032bf110d466af3dea1d1c02227f7`.

Important provenance note: at audit time this NIR commit was **not available on remote GitHub**, so the NIR figures below are recorded from the Codex completion report and should be re-verified after that branch/artifacts are pushed or otherwise made remotely accessible.

Reported matched cohort:

- 68 sessions
- 44 repeat participants
- 1360 probes
- same probes, participants, and folds for C+B and C+B+NIR
- canonical alignment based on `unix_ms`

Reported ROC-AUC:

| Window | C+B | C+B+NIR | Delta |
|---:|---:|---:|---:|
| 10 s | 0.634 | 0.574 | -0.060 |
| 30 s | 0.672 | 0.598 | -0.074 |
| 60 s | 0.680 | 0.617 | -0.063 |

For the 30 s primary comparison, reported paired participant-bootstrap 95% CI for Delta AUC was `[-0.114, -0.036]` with 1000 bootstrap repetitions.

## 2. Baseline interpretation

The behavior/context baseline is sufficiently coherent to serve as the current formal anchor model.

At 30 s:

- behavior alone outperforms context alone;
- combining context and behavior further improves ROC-AUC and balanced accuracy;
- therefore behavior contains generalizable information about the probe-level target, and context adds complementary information beyond behavior alone.

Current decision:

> Treat `C+B` as the formal reference baseline for downstream modality-increment analyses.

This is a scientific comparison anchor, not a claim that C+B is the final competition model.

## 3. NIR interpretation

The correct comparison is the matched-cohort comparison inside the NIR analysis, not a raw comparison of 0.598 against the 46-participant baseline value of 0.675.

On the reported matched cohort:

- 30 s C+B = 0.672
- 30 s C+B+NIR = 0.598
- Delta AUC = -0.074
- paired participant-bootstrap 95% CI = [-0.114, -0.036]

The direction is also consistent at 10 s and 60 s.

Current interpretation:

> Under the currently frozen NIR representation, alignment, fusion method, L2-logistic model, matched probes, and participant-disjoint validation, adding NIR does not provide incremental predictive value over C+B and instead reduces discrimination performance.

This conclusion is deliberately narrower than saying that NIR contains no attention-related information.

The present result does **not** establish that:

- NIR cannot reflect attention or mind-wandering;
- NIR-only signal is necessarily at chance;
- all NIR feature representations are unhelpful;
- all multimodal fusion strategies involving NIR will fail.

It establishes that the **current NIR feature/fusion pipeline** has not passed the incremental-value test.

## 4. Why the result should not be over-interpreted

With approximately 44 independent participants in the matched NIR analysis, adding a relatively large or noisy feature block can worsen out-of-participant generalization even if some individual NIR variables contain signal.

Plausible mechanisms to examine include:

- high-dimensional weak features relative to participant count;
- redundant information already represented by behavior/context;
- participant-specific facial or physiological variation;
- correlated features under L2 shrinkage without true feature elimination;
- temporal mismatch between extracted NIR dynamics and probe labels;
- noisy or unstable modality-specific features;
- fusion-induced overfitting.

These are diagnostic hypotheses, not established causes.

## 5. Frozen decision for the current mainline

Until a diagnostic analysis demonstrates otherwise:

1. `C+B` remains the current formal anchor.
2. The current NIR v1 feature block should **not** be forced into the main competition model merely to preserve a multimodal label.
3. NIR v1 should be reported as a negative incremental-value result under the current pipeline.
4. Cohort definition, label definition, and participant-level fold assignment should remain frozen across modality comparisons whenever technically possible.
5. Comparisons between modalities should preferentially use matched probes/participants and identical fold assignment.

## 6. Minimum NIR diagnostic analysis before any expensive rerun

Before starting new full-session NIR inference or broad model searches, run a small diagnostic matrix on the existing matched cohort and frozen folds:

- NIR only
- C+NIR
- B+NIR
- C+B+NIR

Primary question:

> Does NIR have any participant-generalizable OOF signal on its own, and if so, is that signal lost when fused with C+B?

Interpretation guide:

- If NIR-only is approximately chance, the main issue is likely the current NIR representation itself.
- If NIR-only is meaningfully above chance but C+B+NIR remains below C+B, investigate fusion, dimensionality, redundancy, and regularization rather than immediately rerunning full inference.

Feature selection or dimensionality reduction, if tested, must be performed strictly inside training folds (preferably nested when tuning hyperparameters) to avoid leakage.

## 7. Multimodal comparison framework

Future multimodal analysis should be organized around incremental value relative to the same anchor, rather than reporting disconnected single-modality AUCs.

Candidate ablation structure:

- C
- B
- C+B
- C+B+mmWave
- C+B+NIR
- C+B+RGB
- C+B+mmWave+NIR
- C+B+mmWave+RGB
- C+B+NIR+RGB
- C+B+mmWave+NIR+RGB

Not every combination must appear in the final report. The core scientific question is:

> Does each additional sensor provide generalizable information beyond the already-available behavior/context baseline on the same evaluation population?

Use paired participant-level uncertainty estimates for direct incremental comparisons where possible.

## 8. Current priority order

Recommended order before changing the scientific contract:

1. Re-verify/push the NIR analysis artifacts so the reported local commit and metrics are remotely auditable.
2. Run the small NIR-only / C+NIR / B+NIR diagnostic matrix on the existing matched cohort and frozen folds.
3. Compare mmWave and RGB against C+B using the same matched-cohort / same-fold principle.
4. Use the team's prior multimodal literature survey to decide whether alternative low-dimensional or late-fusion strategies are justified for this sample size.
5. Avoid broad deep-learning or high-dimensional model searches until the above diagnostics show a defensible signal worth modeling.

## 9. Audit boundary

This memo records a decision checkpoint, not a final scientific conclusion about the intrinsic value of NIR, RGB, or mmWave sensing.

The central frozen rule is:

> A new modality counts as providing incremental value only when it improves participant-generalizable performance over the existing anchor under a matched and leakage-controlled comparison.
