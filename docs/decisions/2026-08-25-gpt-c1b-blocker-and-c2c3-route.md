# GPT route decision: C1b blocker and C2/C3 continuation

Date: 2026-08-25
Branch: `codex/c1a-preflight-sync`

## Decision

C1a preflight is accepted as complete. C1b is accepted as `protocol-ready / data-access blocked`.

The current smoke test is not a performance result and must not be used to tune the frozen beat-matching protocol. The C1b blocker is legitimate because the formal VS_DATASET healthy cohort and synchronized Mindray reference files are not locally available.

## Immediate route

Do not spend more time tuning the 12 VitalSense2024 example MAT files.

Proceed immediately with:

1. **C2 radar-only attention baseline v1** as the primary active engineering task.
2. **C3 NIR QC/integration** as the second active task, continuing from the current parameters without opportunistic retuning.
3. Keep **C1b** parked in `blocked` state until the formal VS_DATASET healthy cohort is obtained and verified.

## C1b reactivation trigger

C1b may be resumed only when all of the following are available and recorded:

- complete healthy-cohort radar MAT files for the intended subjects;
- synchronized reference/Mindray files needed for ECG Lead II evaluation;
- subject/session metadata sufficient to form subject-disjoint evaluation groups;
- source URL/DOI, access/license status, and data file inventory;
- checksum or equivalent integrity record where available.

On reactivation, first generate a new `RUN_ID`, freeze the input manifest and configuration, then run the project beat algorithm and VitalSense matched-filter baseline under the same ECG R-peak, device/session alignment, electromechanical-delay policy, one-to-one beat-matching rule, and subject-disjoint split.

## Frozen methodological constraints

- `±75 ms` remains the primary matching tolerance until a future explicit GPT/user decision changes it.
- `±50 / ±75 / ±100 / ±150 ms` may be reported only as sensitivity analysis, not used to select the best result.
- Device/session clock offset and ECG-to-mechanical-heartbeat delay are separate quantities and must remain separately represented.
- No per-test-window lag search or held-out-test tuning.
- IBI/HRV evaluation must be retained independently of constant absolute timing offset.
- `TechValidation.m` field `maxCorr` must not be interpreted as correlation quality because the audited code stores the lag index in that field.

## C2 priority questions

C2 should answer, before any teacher-student architecture work:

1. Does RS6240 radar-only data predict the current thought-probe/attention target above grouped null/baseline performance?
2. Which radar information group contributes signal: respiration, current cardiac candidates, raw micromotion, quality descriptors, or their combination?
3. Does quality gating improve generalization or merely reduce coverage?
4. Are results robust under the strongest currently valid grouping rule, without adjacent-window or session leakage?

C2 must not relabel a radar association as workload, fatigue, arousal, or another psychological construct unless supported by the actual labels/task.

## C3 priority questions

C3 should produce a probe-aligned NIR table with stable identity/session/probe/window/time/QC semantics. Until true participant identity is restored, the limitation must be explicit and person-level LOSO must not be claimed.

## Handoff rule

Codex should report C2/C3 results using the repository collaboration template and stop for GPT/user adjudication before changing label definitions, split/grouping rules, success thresholds, exclusion policies, or scientific interpretation.
