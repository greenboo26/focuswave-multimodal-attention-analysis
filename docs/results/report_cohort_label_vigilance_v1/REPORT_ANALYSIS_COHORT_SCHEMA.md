# REPORT_ANALYSIS_COHORT field schema

`REPORT_ANALYSIS_COHORT` is a local-only, probe-level report master table. It is derived from the frozen Beijing deterministic identity/session/timeline/probe/behavior assets. The CSV itself is never committed because it retains pseudonymous participant and session identifiers.

| Field | Meaning | Public status |
| --- | --- | --- |
| `repeat_participant_id` | Frozen pseudonymous natural-person key used only to cluster repeated observations | local only |
| `session_id` | Frozen pseudonymous formal-session key | local only |
| `formal_session_index` | Observed repeat session order; index 4 is retained | local only |
| `subject_id` | Operational session code | local only |
| `block_num` | BB task block, 1 or 2 | local only |
| `session_probe_index` | Probe ordinal within session, 1–20 | local only |
| `block_probe_index` | Probe ordinal within its block, 1–10 | local only |
| `time_on_task` | Existing within-block normalized probe progress | local only |
| `probe_response` | Four canonical response codes: 1 fully task-focused; 2 experiment-related but not task-focused; 3 task-unrelated thought; 4 no specific thought | local only |
| `probe_vigilance` | Four-point self-reported vigilance: 1 very sleepy to 4 very alert | local only |
| `pre10_*` | Existing behavior-only 10-second pre-probe aggregate | local only |

Primary scope is 70 linked Beijing formal sessions, 46 natural persons, and 1,400 probes. The upstream C2a input universe has 72 sessions and 1,440 probes; a 20-probe C2 session without a valid timeline is excluded. A separate valid-timeline session outside the C2 universe is not counted as missing.
