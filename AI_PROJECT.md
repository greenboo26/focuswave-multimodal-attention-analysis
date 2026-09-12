# AI project pointer

- project_identity: FocusWave multimodal attention analysis
- canonical_repository: https://github.com/greenboo26/focuswave-multimodal-attention-analysis.git
- canonical_branch: `main`
- repository_role: canonical analysis integration, contracts, documentation, reproducible audits, and cross-modal inference
- central_governance: https://github.com/greenboo26/ai-governance; read `adapters/RUNTIME_BOOTSTRAP.md`, `rules/repository-sync.yaml`, and `rules/durable-project-record.yaml`
- workspace_registry: `greenboo26/project@august/PROJECT_INDEX.md`
- local_startup_files: `AGENTS.md` if present, then `ANALYSIS_HISTORY_LEDGER.md`, `docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md` when mmWave is in scope, `PROJECT_STATUS.md`, `docs/canonical/RESULT_INDEX_V1.md`, then the current result/handoff package
- mmwave_current_integration: `docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/`
- mmwave_current_mechanism_audit: `docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/`
- mmwave_current_handoff: `docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/HANDOFF.md`
- mmwave_hr_execution_issue: `https://github.com/greenboo26/focuswave-multimodal-attention-analysis/issues/35`
- mmwave_current_preregistration: `docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md` (FROZEN_PREREGISTRATION; C1/C2 not implemented and not run)
- mmwave_next_dependency: untouched participant/session-disjoint ECG validation set (`docs/canonical/MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md`, recommended `OPT_A`)
- related_repository_roles: `FocusWave@formaltest` owns current formal experiment/acquisition implementation; `Attention-Analysis` owns Behavior/NIR/RGB producer engineering and single-modality analysis; `FocusWave-Formal-Analysis` owns analysis plans/report evidence; local `11_数据` owns data payloads

This file is navigation only. Current scientific and engineering truth remains in this repository's canonical state, status, tests, manifests, handoffs and evidence. Prefer those durable sources over reconstructing project state from chat memory.

## mmWave current state

For mmWave work, `docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md` is the first project-specific branch/interface authority after the general history ledger. Legacy `codex/mmwave-*` branches and their pull requests are provenance sources only unless a canonical record explicitly promotes a change into `main`.

The previously documented P0→P7 recovery sequence and `docs/canonical/2026-09-12_MMWAVE_HR_P2_FAILURE_ATTRIBUTION_HANDOFF.md` remain historical lineage, not the current execution queue. The current canonical sequence has already advanced through reference/QC reconciliation, estimator-improvement v1 (`NO_STABLE_IMPROVEMENT`) and the low-bias mechanism audit (`MULTIFACTOR_MECHANISM_SUPPORTED`).

Current boundaries:

- `MMWAVE_INTEGRATION_SNAPSHOT_V1` remains the downstream integration interface: `PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED`.
- `MMWAVE_ESTIMATOR_IMPROVEMENT_V1` remains a negative result: `NO_STABLE_IMPROVEMENT`; no snapshot v2 was formed.
- `MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1` is the current mechanism evidence: correct/near-correct probes are nearly unbiased, while wrong-peak / harmonic-or-half-double / target-bin-channel-miss failures carry the pooled negative bias; spectral-to-fusion pull is secondary.
- Do not apply a global +9 bpm correction or introduce a distance gate from the exposed 100-probe development set.
- Any mechanism-derived production candidate must be frozen separately and validated on an untouched participant/session-disjoint ECG set before promotion.
- HR/BR remain `HOLD / SUPPORTING_ONLY`; HRV remains `BLOCKED`; no formal snapshot v2 exists.

The historical recovery decision `docs/canonical/2026-09-12_MMWAVE_HR_RECOVERY_AND_BASELINE_INTEGRATION_DECISION.md` remains important provenance and should be read when reconstructing how the current state was reached, but it must not override the newer canonical mechanism-audit and current-state records.

Every material result/problem/decision must comply with central `rules/durable-project-record.yaml`: future readers must be able to reconstruct the question, exact data/window/time semantics, code/commit, inputs, outputs, key numeric results, controlled comparison, decision logic, unresolved failures, and next dependency without relying on chat history. A one-line PASS/PARTIAL/BLOCKED or an orphan result directory is not sufficient completion evidence.
