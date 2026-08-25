# AGENTS.md

## Mandatory startup reading

When Codex enters this repository, read these files before making research or implementation decisions:

1. `AGENTS.md` (this file)
2. `docs/workflows/GPT_CODEX_COLLABORATION_PROTOCOL.md`
3. `docs/workflows/CURRENT_GPT_CODEX_HANDOFF.md`
4. `PROJECT_STATUS.md`
5. Relevant `docs/decisions/` and `docs/research/` evidence files for the active task

## GPT ↔ Codex collaboration rule

This repository uses a fixed division of responsibility whenever GPT and Codex work in parallel.

- **GPT = research/method lead and adjudicator.** GPT owns literature review, theory/evidence chains, methodological standards, algorithm/code audit, experimental design, interpretation, and final research go/no-go decisions.
- **Codex = engineering executor.** Codex owns code changes, data adapters, experiment harnesses, batch execution, QC artifacts, reproducible outputs, manifests, tests, and Git commits.
- **GitHub = shared fact layer.** Neither side should rely on chat history as the authoritative project state. Results, assumptions, parameters, failures, and decisions must be written into the repository.

Codex MUST NOT turn an engineering result directly into a scientific claim. Codex reports what was run and what happened; GPT adjudicates what the result supports.

Codex MUST NOT silently change research thresholds, labels, train/test grouping, window definitions, physiological interpretations, or success criteria. If an implementation requires such a change, stop and record the blocking issue for GPT/user review.

GPT should not duplicate Codex's heavy engineering work when Codex can run it reproducibly. GPT should instead review the evidence, inspect external literature/code, define acceptance criteria, and evaluate Codex outputs.

## Required Codex completion record

Every non-trivial experiment or implementation task must leave a concise handoff record containing at least:

```text
RUN_ID:
branch / commit:
objective:
input data:
code entrypoint:
parameters/config:
train/val/test or grouping rule:
outputs:
QC summary:
failures / exclusions:
known limitations:
next decision needed from GPT/user:
```

Store this in the relevant experiment directory, `docs/runs/`, or another path explicitly named in the current handoff.

## Research integrity constraints

- No subject/session/window leakage across evaluation splits.
- Until real participant identity is restored, do not call recording-session holdout "person-level LOSO".
- Do not infer HRV validity from average HR agreement alone. Beat timing / IBI evidence is required for HRV claims.
- Do not promote exploratory raw-radar associations into named psychological constructs without task/label/theory support.
- External papers/code define methods and comparison points; they do not certify this project's thresholds or performance.
- Preserve failures. Do not delete inconvenient outputs or overwrite prior runs without an auditable reason.

## Current project direction

The project is pursuing two parallel primary tracks:

1. **Radar physiological track:** external radar+ECG beat/IBI benchmark → validated heartbeat extraction → RS6240 adaptation → HRV where supported.
2. **Radar attention-system track:** radar-only attention baseline now; NIR/RGB/behavior/probe may be used as auxiliary/teacher information later, with radar-only deployment preferred when performance permits.

Multimodal deployment is a fallback / upper-bound route, not an automatic replacement for radar-only sensing.

For exact current assignments, read `docs/workflows/CURRENT_GPT_CODEX_HANDOFF.md`.
