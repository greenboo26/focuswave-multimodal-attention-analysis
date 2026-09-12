# AI project pointer

- project_identity: FocusWave multimodal attention analysis
- canonical_repository: https://github.com/greenboo26/focuswave-multimodal-attention-analysis.git
- canonical_branch: main
- repository_role: canonical analysis integration, contracts, documentation, reproducible audits, and cross-modal inference
- central_governance: https://github.com/greenboo26/ai-governance; read `adapters/RUNTIME_BOOTSTRAP.md`, `rules/repository-sync.yaml`, and `rules/durable-project-record.yaml`
- workspace_registry: `greenboo26/project@august/PROJECT_INDEX.md`
- local_startup_files: `AGENTS.md` if present, then `ANALYSIS_HISTORY_LEDGER.md`, `docs/canonical/ANALYSIS_PROGRESS_MAP_2026-08-28.md`, `docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md` when mmWave is in scope, then `docs/canonical/MMWAVE_CURRENT_STATE_2026-08-29.md`, `README.md`, `docs/00_治理/`, and current status/handoff
- mmwave_hr_active_mainline: `docs/canonical/2026-09-12_MMWAVE_HR_RECOVERY_AND_BASELINE_INTEGRATION_DECISION.md`
- mmwave_hr_current_handoff: `docs/canonical/2026-09-12_MMWAVE_HR_P2_FAILURE_ATTRIBUTION_HANDOFF.md`
- mmwave_hr_execution_issue: `https://github.com/greenboo26/focuswave-multimodal-attention-analysis/issues/35`
- related_repository_roles: `FocusWave` owns experiment production; `Attention-Analysis` owns NIR/RGB producer engineering; local `11_数据` owns data payloads

This file is navigation only. Current scientific and engineering truth remains in this repository's rules, status, handoff, tests, and evidence. For long-running work, prefer the canonical history/progress/current-state chain over reconstructing project state from chat memory.

For mmWave work, `docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md` is the first project-specific state/branch/interface authority after the general history ledger. Legacy `codex/mmwave-*` branches and their pull requests are provenance sources only unless that canonical file explicitly promotes a change into `main`.

For the current HR/BR/beat/HRV recovery mainline, read both `docs/canonical/2026-09-12_MMWAVE_HR_RECOVERY_AND_BASELINE_INTEGRATION_DECISION.md` and the current handoff `docs/canonical/2026-09-12_MMWAVE_HR_P2_FAILURE_ATTRIBUTION_HANDOFF.md` before proposing or executing additional failure attribution, window comparisons, selector changes, baseline calibration, or formal promotion. The frozen order is P0 full-chain audit → P1 restore compatible proven modules → P2 current DLL-time 30 s failure attribution → P3 180 s baseline-personalized HR target calibration → P4 freeze candidate pipeline → P5 30 s vs 60 s → P6 independent ECG validation → P7 formal promotion/downstream.

Every material result/problem/decision must comply with central `rules/durable-project-record.yaml`: future readers must be able to reconstruct the question, exact data/window/time semantics, code/commit, inputs, outputs, key numeric results, controlled comparison, decision logic, unresolved failures, and next dependency without relying on chat history. A one-line PASS/PARTIAL/BLOCKED or an orphan result directory is not sufficient completion evidence.
