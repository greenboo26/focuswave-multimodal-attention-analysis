# GPT ↔ Codex Collaboration Protocol

Status: canonical collaboration protocol for this repository; intended to be reused for future GPT + Codex projects.

## 1. Purpose

Use GPT and Codex as complementary roles rather than duplicate workers.

- GPT should spend its effort on research reasoning that benefits from literature synthesis, theory, methodological judgment, external-code audit, experimental design, and interpretation.
- Codex should spend its effort on reproducible engineering: code, adapters, tests, batch runs, data products, QC, manifests, and commits.
- GitHub is the persistent shared state between them.

The default pattern is **parallel work with explicit handoffs**, not sequential chat-copying and not two agents independently inventing competing plans.

## 2. Role ownership

### GPT owns

1. Literature and source review, including original papers and public repositories.
2. Theory/evidence chain: what physiological or psychological construct an analysis can support.
3. Method standards and acceptance criteria before results are seen.
4. Audit of external code before migration.
5. Experimental matrix and ablation logic.
6. Data-leakage, label-leakage, identity/grouping, and validation design decisions.
7. Interpretation of Codex outputs.
8. Research go/no-go / continue / downgrade / re-route decisions.
9. Report wording and evidence boundaries.
10. Deciding whether an adjacent construct (e.g. workload, fatigue, arousal, engagement) is actually supported by labels/task/theory.

GPT should NOT casually take over long-running batch execution or duplicate Codex implementation unless a small local check is necessary for adjudication.

### Codex owns

1. Repository inspection and implementation.
2. Data-format adapters and reproducible preprocessing.
3. Experiment harnesses and command-line entrypoints.
4. Tests, assertions, schema/QC checks, manifests, and failure semantics.
5. Batch execution and deterministic result export.
6. Generation of plots/tables/artifacts requested in the handoff.
7. Commit hygiene and file organization.
8. Recording exact inputs, parameters, versions, exclusions, and failures.
9. Implementing methods only within the research constraints defined by GPT/user.
10. Surfacing blockers instead of silently changing research assumptions.

Codex should NOT independently declare that an algorithm is physiologically valid, that a psychological construct has been detected, or that a research route is proven/disproven.

## 3. GitHub is the shared fact layer

Important state must be persisted in GitHub, not left only in either chat.

Persist at minimum:

- current branch and commit;
- active task and owner;
- source/evidence files used;
- parameters/configs;
- input and output paths;
- run IDs;
- QC/failure records;
- methodological decisions;
- next decision requested from the other side.

Recommended paths:

- `docs/workflows/` — collaboration rules and current handoff
- `docs/research/` — literature/code audits
- `docs/decisions/` — research adjudications
- `docs/runs/` — compact run summaries when appropriate
- `experiments/<name>/` — code, configs, manifests, local README for a concrete experiment

## 4. Standard work cycle

### Step A — GPT defines the question

Before Codex launches a major experiment, GPT/user should define:

- scientific/engineering question;
- success/failure criteria;
- allowed inputs;
- forbidden leakage paths;
- required outputs;
- whether the task is exploratory or confirmatory;
- what Codex must NOT reinterpret or change.

### Step B — Codex implements and runs

Codex:

- creates or reuses a clearly named experiment entrypoint;
- keeps configuration explicit;
- adds QC/assertions before expensive execution;
- runs only the requested scope unless an obvious implementation prerequisite is necessary;
- records partial failure rather than hiding it.

### Step C — Codex commits a completion record

Minimum format:

```text
RUN_ID:
branch / commit:
objective:
input data:
code entrypoint:
parameters/config:
grouping/split rule:
outputs:
QC summary:
failures/exclusions:
known limitations:
question for GPT/user:
```

A table/CSV alone is not a sufficient handoff if the interpretation depends on hidden runtime assumptions.

### Step D — GPT adjudicates

GPT reads the committed evidence and decides:

- what the result actually supports;
- whether thresholds or methods should remain frozen;
- whether a follow-up run is informative or merely post-hoc tuning;
- whether the result can enter the report and with what wording;
- the next experiment, if any.

### Step E — decision is persisted

If the result changes project direction, GPT/user decision should be written to `docs/decisions/` so Codex sees it at the next startup.

## 5. Parallelism rules

Parallel work is preferred when the tasks do not mutate the same files or depend on each other's unfinished output.

Good parallel pair:

- Codex: implement external ECG benchmark.
- GPT: read radar-HRV original papers and audit relevant public algorithms.

Good parallel pair:

- Codex: build radar-only prediction baseline.
- GPT: define label hierarchy, split policy, model comparison and reporting standard.

Bad parallel pair:

- GPT and Codex both independently rewrite the same experiment pipeline.
- Both agents independently choose different HRV success thresholds.
- Codex changes labels while GPT analyzes old label semantics.

If a dependency exists, the upstream side should leave a precise handoff rather than asking the other side to infer state from chat history.

## 6. Scientific integrity constraints

These are mandatory across collaboration:

1. **Identity leakage:** split by the strongest available independent unit. Until true participant IDs are recovered, use explicit recording-session holdout terminology.
2. **Window leakage:** overlapping windows from the same continuous segment must not cross train/test boundaries.
3. **Preprocessing leakage:** scalers, imputers, feature selectors, teacher targets, thresholds learned from data must be fitted only on allowed training data unless explicitly defined as external/fixed.
4. **HRV validity:** average HR or spectral-peak agreement alone is insufficient; beat timing/IBI evidence is required.
5. **Psychological naming:** raw radar correlation cannot be renamed as attention/workload/fatigue/arousal without an independent label, manipulation, or theoretically justified proxy.
6. **External evidence:** published accuracy does not certify our device/data. Public code is audited before reuse.
7. **Failures remain visible:** do not silently discard subjects/windows until the exclusion rule is documented.
8. **No deadline-based relaxation of evidence standards:** competition constraints can determine fallback product scope, not turn weak validation into strong validation.

## 7. Product-oriented fallback ladder

For this class of sensing project, engineering success and scientific claims are separated.

Preferred deployment ladder:

1. radar-only system;
2. multimodal training / radar-only deployment via teacher-student or auxiliary supervision;
3. radar + NIR;
4. full multimodal system when required for a usable competition product.

A fallback in deployment modality does not retroactively validate a failed physiological pathway. Conversely, an imperfect HRV pathway does not prevent an independently validated radar-only predictor from being a useful system result.

## 8. Current mmWave project-specific application

### Track A — physiological validity

External radar + ECG benchmark first:

`radar -> cardiac waveform -> beat timestamps -> ECG matching -> IBI -> HRV`

Primary success measures include beat precision/recall/F1, timing error, IBI error/correlation, HR error, HRV error on defensible windows, and usable coverage.

Then migrate the validated back-end to RS6240 while retaining this project's target-lock, multi-channel, motion, Q0, and respiration-harmonic gates.

### Track B — attention system

Do not wait for Track A to finish.

Build radar-only baselines using separable feature groups such as respiration, cardiac candidates/validated HRV when available, raw phase/micromotion, quality descriptors, and all-radar.

Later compare against NIR, behavior, and multimodal upper bounds. Only if multimodal information materially improves performance should teacher -> radar-only distillation be prioritized.

## 9. Rule for future GPT + Codex collaboration

Unless the user explicitly requests another arrangement, use this protocol as the default pattern for future GPT + Codex joint work:

- one side owns research/method adjudication (GPT);
- one side owns reproducible engineering execution (Codex);
- GitHub carries persistent shared state;
- handoffs are explicit;
- neither side silently changes the other's assumptions;
- the user can override ownership at any time.
