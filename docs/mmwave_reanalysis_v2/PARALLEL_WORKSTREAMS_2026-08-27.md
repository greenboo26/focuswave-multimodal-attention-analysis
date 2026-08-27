# Parallel mmWave HR workstreams — 2026-08-27

Status: `DISPATCH_READY`

## Workstream A — discontinuity diagnosis

Question: why does historical 25 s development-equivalent performance (~9 BPM session-median MAE) diverge from current 30/50/60 s results (~27–37 BPM)?

Deliverables:
- exact same-session intersection;
- same-window old-vs-new ECG reference comparison;
- both pooled-window MAE and session-MAE median for every condition;
- 25/30/50/60 s factorized comparison with only one factor changed at a time;
- input units/sample-rate/phase convention/frequency-axis audit;
- error taxonomy: near-correct, 0.5x HR, 2x HR, other spectral lock, unexplained.

No new algorithms.

## Workstream B — repository archaeology / reuse gate

Question: what did we already implement, test, reject, or partially solve?

Inspect:
- central `CHANGELOG.md`, `EVIDENCE_LEDGER.md`, `FAILURE_MODE_REGISTRY.md`, `METHOD_MATRIX.md`;
- historical commits cited by the evidence ledger (`164d51e`, `55b6c01`, `ac2e512`, `f4a8c74`, `7a482f0`);
- acquisition `kyandi233-dev/FocusWave@ecg` and `stable-msmf`, especially mmWave capture and calibration programs;
- legacy `mmwave-hrv-analysis` only if accessible.

Deliverable: reusable-asset matrix with file/commit, what it solves, what failed, whether current benchmark preserved it.

## Workstream C — improvement direction ranking

Question: after A/B root cause is known, what is the cheapest targeted repair with the highest chance of fixing the actual defect?

Use uploaded literature plus existing repo assets. Rank directions by:
- direct match to observed failure;
- compatibility with AgeBalanced 10 Hz derived input;
- existing project implementation available;
- implementation time;
- risk of introducing unverifiable adaptation.

Deliverable: maximum 3 directions, with one recommended next validation and explicit stop condition.

## Merge decision

After A/B/C return, the primary review must choose only one of:
- `FIX_BENCHMARK_AND_RETEST_EXISTING_ROUTE`
- `ONE_TARGETED_SIGNAL_REPAIR`
- `STOP_HR_RND`

Do not create a fourth open-ended workstream.
