# mmWave producer M1 contract/provenance repair — implementation handoff

Date: 2026-09-13  
Status: `IMPLEMENTED_ON_CHILD_BRANCH / REAL_2320_RUN_PENDING`  
Issue: #43  
Frozen base: `main@3d3671f05b0c502e60824c9f7b9c2fa18efddbb6`

## Scope

This M1 change closes the code-side items required by FocusWave Formal
`1.15.9-毫米波生成链合同修复与time-legality处置_20260913.md`.
It does not change the HR/BR estimator family, physiology qualification,
HRV status, C1/C2 status, supervised learning, or form a snapshot v2.

The historical corrected replay commit `16729b2ef245f9304dae8674f3bac433bc02e98c`
remains supporting lineage evidence, but GitHub cannot currently resolve it as a
remote commit and the historical replay manifest source hashes are inconsistent
with the declared source commit. Therefore M1 does not treat that historical
identifier as provenance closure. A fresh run from this remotely retrievable
child branch must provide its own exact commit and source hashes.

## Frozen producer time contract

The shared implementation is
`scripts/maintenance/mmwave_probe_contract.py`.

1. Scientific alignment uses timestamp CSV zero-based column `1`,
   `DLL host receive/enqueue time`.
2. Zero-based column `2`, Python worker processing time, is QC-only.
3. Formal frame membership is strictly
   `[window_effective_start_unix_ms, probe_onset_unix_ms)`.
4. `window_end_unix_ms` must equal `probe_onset_unix_ms` exactly.
5. A frame timestamp exactly equal to probe onset is excluded.
6. `window_effective_start_unix_ms` is the actual lower slicing boundary.
7. J and E runners call the same `process_probe()` implementation and therefore
   share this contract.

The shared selector also reconstructs the pre-M1 current-main membership
(Python processing clock + nominal start + right-inclusive endpoint) for
**audit only**. That legacy selector cannot generate new scientific features.

## Usable-window fraction

The pre-M1 runner wrote a binary availability indicator into
`mmwave_hr_usable_window_fraction`. M1 replaces that semantic with the existing
producer's `estimate_hr_time_course(...).signal_quality.usable_ratio`, without
using that course output to replace the frozen HR estimate. The HR/BR estimator
outputs remain the existing selector path.

## Frame-membership evidence

Each J/E run emits a local-only per-probe frame audit:

- `mmwave_probe_frame_membership_audit.csv`
- `mmwave_probe_frame_membership_audit_E.csv`

For selected probes it contains the canonical identity, legacy/new frame range
and frame count, first/last timestamp, legacy/new membership SHA-256 digest,
whether membership changed, and strict new-contract predicates including
`new_all_selected_before_probe`.

Unavailable or unreadable sessions remain present as explicit audit stubs.
No missing row is zero-filled or deleted.

## Fresh-run provenance

Each J/E manifest records:

- exact Git `source_commit`;
- current `source_branch`;
- whether the source worktree is clean;
- SHA-256 of the adapter, shared contract module, and producer source;
- the frozen clock/window contract;
- the frame-audit path;
- explicit `models_trained=false`, `q1_q2_used_for_acceptance=false`,
  `snapshot_v2_formed=false`.

A fresh run is provenance-closed for this code layer only when the worktree is
clean and the recorded commit is the pushed PR head. This does not itself grant
physiology validity or downstream prediction eligibility.

## Old-vs-new audit

After the corrected J/E tables are generated, run:

```powershell
python scripts/maintenance/audit_mmwave_producer_contract_repair_20260913.py `
  --old-j <pre-M1 mmwave_probe_merge_ready.csv> `
  --old-e <pre-M1 mmwave_probe_merge_ready_E.csv> `
  --new-j <M1 mmwave_probe_merge_ready.csv> `
  --new-e <M1 mmwave_probe_merge_ready_E.csv> `
  --frame-j <M1 mmwave_probe_frame_membership_audit.csv> `
  --frame-e <M1 mmwave_probe_frame_membership_audit_E.csv> `
  --output-dir <M1 audit directory>
```

Acceptance is fail-closed on:

- 2320-probe key conservation;
- complete frame-audit key coverage;
- zero `new_all_selected_before_probe` violations;
- zero deterministic HR/BR/target/state differences on probes whose actual
  frame membership is unchanged.

`mmwave_timestamp_coverage_fraction` and
`mmwave_hr_usable_window_fraction` are excluded from that deterministic
same-membership invariant because M1 intentionally corrects their time/QC
semantics.

## Tests

`tests/test_mmwave_producer_contract_m1.py` covers DLL science clock selection,
effective-start truncation, exact right-open endpoint, exact endpoint identity,
non-monotonic DLL clock rejection, stable membership digests, producer usable
ratio semantics, E-batch effective-start propagation/fail-closed fallback, and
J/E shared `process_probe` use.

## Remaining gate

Code implementation alone does not change Formal
`blocked_upstream_contract_mismatch`.

The status can only be reconsidered after a fresh clean-worktree run on the
frozen governed cohort demonstrates 2320 probes / 116 sessions / 61 participant
groups, produces the old-vs-new audit, and the manifest commit/hash values are
verified against the pushed PR head.
