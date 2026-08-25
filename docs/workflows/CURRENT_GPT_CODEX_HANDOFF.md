# Current GPT ↔ Codex Handoff

Date: 2026-08-25
Branch: `codex/audit-j-target-lock-gate`
Status: active

## 1. Working model

This task follows `docs/workflows/GPT_CODEX_COLLABORATION_PROTOCOL.md`.

- GPT: research/method lead, external-paper/code audit, acceptance criteria, interpretation, final route decisions.
- Codex: engineering implementation, data processing, experiment execution, QC, artifacts, manifests, commits.
- GitHub: authoritative shared state.

Do not rely on chat history alone.

## 2. Codex — start now

### Task C1 — External VS_DATASET beat/IBI benchmark

Priority: P0

Create a reproducible experiment, recommended location:

`experiments/external_vitalsense_benchmark/`

Objective:

Determine whether the current/ported radar cardiac pipeline can recover beat timing and IBI on a public radar dataset with synchronized ECG reference before further tuning on RS6240.

Required flow:

```text
VS_DATASET radar
  -> target/range handling
  -> phase / vital displacement
  -> respiration-cardiac separation
  -> cardiac waveform
  -> heartbeat timestamps
  -> ECG R-peaks
  -> explicit beat matching
  -> IBI
  -> HR / HRV evaluation
```

Implement at least one VitalSense-style beat-level baseline using the public author code/paper as a reference. If the current project method can be adapted to output beat timestamps, include it as a second baseline; do not block C1 on this second baseline.

Required outputs, preferably machine-readable CSV/Parquet plus run manifest:

- subject
- scenario
- radar beat timestamps
- ECG R-peak timestamps
- matching rule / tolerance
- matched/unmatched counts
- beat precision
- beat recall
- beat F1
- beat timing error distribution / MAE
- true and predicted IBI
- IBI MAE
- IBI correlation
- HR MAE
- usable coverage
- failure/exclusion reason
- RMSSD/SDNN comparison only on windows that meet a predeclared duration/beat-quality rule

Important constraints:

- Do not call average-HR agreement a successful HRV validation.
- Do not tune thresholds on the held-out evaluation subjects/windows.
- Do not silently delete hard subjects or failed windows.
- Keep physiological band/filter choices in config/manifest.
- Preserve raw intermediate outputs needed for audit.
- Keep external-dataset adapter separate from the later RS6240 adapter.

Completion record must include a RUN_ID, commit, exact data version/path, code entrypoint, config, QC, failures, and the decision question for GPT.

### Task C2 — Radar-only attention baseline v1

Priority: P1, may run in parallel with C1 if resources permit.

Recommended location:

`experiments/radar_only_attention_baseline_v1/`

Objective:

Test whether existing probe-aligned RS6240 data already contain predictive information about the current thought-probe/attention labels without waiting for HRV to be fully validated.

Feature/input groups should remain separable for ablation:

- R1 respiration features
- R2 current cardiac/HR candidates (clearly marked exploratory until beat validation)
- R3 raw phase / micromotion descriptors
- R4 quality descriptors / Q0
- R5 all-radar
- later R6 validated HRV when Track C1/C3 supports it

Required evaluation constraints:

- use the strongest currently available grouping unit;
- until real participant identity is restored, label evaluation explicitly as recording-session holdout, not person-level LOSO;
- no overlapping/adjacent windows from the same continuous segment may cross train/test;
- preprocessing/scaling/feature selection must be fit inside training folds;
- report class balance and baseline/null performance;
- preserve quality-gated and ungated comparisons if both are run.

Suggested metrics for binary classification: AUROC, balanced accuracy, F1, sensitivity/specificity, with grouped/bootstrap uncertainty where practical. If the current target is ordinal/continuous, record the exact label definition and use the matching metrics rather than coercing it into binary without approval.

Do not rename a signal association as workload/fatigue/arousal unless the label/task supports that construct.

### Task C3 — continue existing NIR integration job without opportunistic retuning

Maintain the current NIR precheck/QC direction already in progress. Do not restart or alter parameters solely because C1/C2 begin.

The NIR output must eventually support stable keys for multimodal analysis:

`participant/recording identity + session + probe_id + window_id + absolute time coverage + QC/failure semantics`

If identity cannot yet be restored, record that explicitly.

## 3. GPT — parallel work now

GPT will continue, in parallel with Codex engineering:

### G1 — Radar HRV literature and code audit

Deep-read and extract implementable details from:

- Frazao et al. 2024 radar cardiac/HRV review
- VitalSense / VS_DATASET
- Radar-APLANC
- Radar-Beat / mmHRV / IBI-focused original work where accessible
- SpectroTransNet-HRV only as an algorithm prototype, not a trusted benchmark without split/window corrections

Deliverable: a module-level implementation map separating:

- KEEP from our pipeline
- BORROW / adapt from external work
- EXPERIMENTAL only
- DO NOT COPY / known code risks

### G2 — Beat/IBI acceptance standard

Define the research acceptance criteria for:

- beat matching tolerance
- beat precision/recall/F1
- timing error
- IBI quality/coverage
- which HRV metrics/windows are defensible
- respiratory-harmonic ambiguity handling

Criteria should be fixed before looking at final C1 test results whenever possible.

### G3 — Attention-system evaluation design

Define:

- primary thought-probe target hierarchy
- allowed adjacent constructs
- grouping/split policy
- radar feature ablations
- multimodal upper-bound comparison
- criteria for whether teacher -> radar-only distillation is worth implementing

### G4 — Teacher/student architecture review

Use Tac-Mamba and SCKD as design references, not direct evidence for attention sensing.

Potential project translation:

```text
Teacher inputs:
  mmWave + NIR pupil/blink + behavior + RGB motion/pose + probe-derived supervision

Student input:
  mmWave only
```

Only prioritize this after simple radar-only and multimodal upper-bound baselines show a meaningful gap.

## 4. Handoff points

Codex should stop and request GPT/user adjudication when any of the following occurs:

1. A required implementation change alters the scientific definition of a label/window/success threshold.
2. External VS_DATASET code and paper appear inconsistent in a way that affects results.
3. Beat detection works for HR but not IBI/HRV.
4. Test performance improves only after changing thresholds using held-out data.
5. Radar-only attention performance looks high but split/leakage risk cannot be ruled out.
6. NIR/RGB/behavior identity mapping conflicts with radar/probe identity.
7. A major new data exclusion rule would remove a substantial portion of subjects/windows.

## 5. What Codex should report back to GPT

Use this exact compact handoff form:

```text
RUN_ID:
branch / commit:
task: C1 / C2 / C3
objective:
input data:
entrypoint:
config/parameters:
grouping/split rule:
outputs:
key metrics:
QC / coverage:
failures / exclusions:
implementation deviations from plan:
open question for GPT/user:
```

Do not include a scientific conclusion such as "HRV validated" or "attention detected" unless it is explicitly quoting a previously committed GPT/user decision.

## 6. Immediate expected order

Codex should prioritize:

1. C1 external VS_DATASET beat/IBI benchmark harness
2. C2 radar-only attention baseline
3. C3 continued NIR QC/integration

C1 and C2 can proceed in parallel if they do not compete for the same compute/resource bottleneck.

GPT will review the first committed C1/C2 evidence rather than asking Codex to self-adjudicate the research route.
