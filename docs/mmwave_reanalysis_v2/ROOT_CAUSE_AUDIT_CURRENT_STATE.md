# Root-cause audit current state

Status: `PARALLEL_TASKS_DISPATCHED`
Date: 2026-08-27

Three parallel workstreams are authorized under `PARALLEL_WORKSTREAMS_2026-08-27.md`.

Primary hypothesis ordering before new runs:

1. aggregation / cohort mismatch;
2. historical vs current ECG reference mismatch;
3. input/adapter semantics mismatch;
4. window-sensitive project-route logic;
5. range-bin / spatial selection differences;
6. only after the above: true unresolved signal-processing limitation.

Reason for this ordering: the observed historical-vs-current discontinuity is too large to attribute to algorithm quality alone without first making the compared populations, reference and metric definitions identical.

Heldout 80 remains untouched.
