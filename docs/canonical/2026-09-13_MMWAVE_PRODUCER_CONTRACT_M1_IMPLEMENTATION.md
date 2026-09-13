# mmWave producer M1 contract/provenance repair — implementation handoff

Date: 2026-09-13  
Status: `PRODUCER_RUN_COMPLETE / AUDIT_GATE_REFINED_AFTER_STATEFUL-HR REVIEW`  
Issue: #43  
Frozen producer execution commit: `01da845e70e255b6537f8d03220aac2e6cc0bf31`  
Current PR branch: `codex/mmwave-producer-contract-provenance-m1-20260913`

## Scope

This M1 change closes the code-side items required by FocusWave Formal
`1.15.9-毫米波生成链合同修复与time-legality处置_20260913.md`.
It does not change the HR/BR estimator family, physiology qualification,
HRV status, C1/C2 status, supervised learning, or form a snapshot v2.

The historical corrected replay commit `16729b2ef245f9304dae8674f3bac433bc02e98c`
remains supporting lineage evidence, but GitHub cannot resolve it as a remote
commit and its historical replay manifest hashes are inconsistent with the
declared source commit. M1 therefore establishes a new remotely retrievable
producer execution lineage.

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

The shared selector reconstructs the pre-M1 current-main membership
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
and frame count, first/last timestamp, frame-index membership SHA-256, separate
clock-value SHA-256, whether membership changed, and strict new-contract
predicates including `new_all_selected_before_probe`.

Unavailable or unreadable sessions remain present as explicit audit stubs.
No missing row is zero-filled or deleted.

## Fresh-run provenance

The governed-cohort run completed from a clean worktree at exact producer
execution commit:

`01da845e70e255b6537f8d03220aac2e6cc0bf31`

Both J/E manifests record that exact commit, a clean worktree, source SHA-256
values, the frozen clock/window contract, and explicit no-model/no-Q1Q2/no-v2
flags. The four executed source hashes were independently rechecked against the
files used for the run.

The real run produced 2,320 probe rows across 116 sessions. The producer-level
legacy `repeat_participant_id` cardinality is 62 in both pre-M1 and M1 tables;
this field cardinality did not change in M1. The downstream Cardiopulmonary
ingest layer separately resolves the governed participant-group universe to 61.
Therefore producer M1 must not claim a native producer-table count of 61 groups.

## Post-run audit finding and corrected determinism contract

The first old-vs-new audit returned `FAIL` because 54 probes had unchanged local
frame membership but changed HR-derived fields. Review of the frozen producer
code established that this was not caused by DLL/Python timestamp values being
fed directly into HR estimation: after frame selection, HR consumes the selected
IQ frames at fixed `FS=100`.

The HR selector is stateful within each session/block. Each probe consumes an
incoming `previous_bpm` anchor, and the anchor is updated from prior probe fused
HR/confidence. Consequently, an earlier legitimate frame-membership change can
alter the anchor carried into a later probe whose own local frame membership is
unchanged.

Real audit evidence supports this mechanism: all 54/54 same-membership HR
differences occurred after at least one earlier membership change in the same
session/block, and all 54/54 also occurred after an earlier fused-HR change in
that block. No corresponding same-membership differences were observed in BR,
target bin/channel, distance proxy, phase, motion, state, observed/missingness,
or loadability fields.

Formal `1.15.9` requires same-membership deterministic quantities to remain
identical **or otherwise be separately explained**. The audit gate is therefore
refined as follows:

- stateless derived fields: same frame membership => identical output;
- stateful HR fields (`freq/time/fused/confidence`): same frame membership **and
  same incoming `previous_bpm` anchor** => identical output;
- same local membership with a diverged incoming anchor is reported as explained
  state propagation, not silently ignored and not counted as an unexplained
  determinism failure.

The audit reconstructs incoming anchor lineage from emitted fused HR and
confidence using the unchanged producer update rule: first finite fused HR seeds
the state; later finite fused HR updates when confidence is `>= 0.12` via
`0.8 * previous + 0.2 * fused`.

This audit refinement does not change producer outputs and does not require a
116-session signal rerun. It requires only re-running the old-vs-new auditor on
the already-generated pre-M1/M1 J/E tables and frame-audit CSVs.

## Tests and execution facts

At producer execution commit `01da845e...`,
`tests/test_mmwave_producer_contract_m1.py` contains **8** test functions; the
real machine collected and passed all 8 (`8 passed / 0 failed`). Any earlier PR
text stating `13 passed` for that exact commit was incorrect and is superseded.

The later audit-gate refinement adds dedicated stateful-anchor unit tests. Local
verification of those new tests passed (`3 passed / 0 failed`) together with
positive/negative synthetic audit controls: upstream anchor divergence is
classified as explained state propagation, while a same-membership + same-anchor
HR difference remains fail-closed.

## Remaining gate

Producer execution provenance is closed for the `01da845e...` run. Formal
`blocked_upstream_contract_mismatch` must remain unchanged until the revised
auditor is executed against the already-produced real old/new J/E tables and the
result confirms:

- key conservation and frame-audit coverage;
- zero strict new-frame membership violations;
- zero stateless same-membership violations;
- zero stateful HR violations when both local membership and incoming anchor are
  the same;
- all remaining same-membership HR differences, if any, are explicitly accounted
  for by incoming-anchor divergence.

This remains a producer contract/provenance decision only. It does not establish
HR/BR physiological validity or prediction eligibility by itself.
