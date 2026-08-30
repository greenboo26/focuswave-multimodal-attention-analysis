# mmWave pre-selection clutter A/B — 2026-08-30

Status: **PARTIAL / diagnostic-only**

## Frozen contract

- Subset: the existing 335 DLL-time, formal-block diagnostic windows from 97793/9779/97795.
- A: existing raw mean-power profile and unchanged v3.1.1 candidate scoring/channel selector/block-local continuity.
- B: the identical cube after slow-time complex-mean subtraction, then the same existing selector. This is post-Range-FFT research only; it does not imply any pre-FFT or firmware operation.
- No ECG/RSP values, HR/BR estimates, gates, thresholds, or estimator outputs were read or used.

## Result

See the three CSV aggregates for selected-bin near-side rates, switching/residence, and channel-grid near-peak stability. The comparison is descriptive and cannot identify the reflector or validate a physical distance gate.

## Decision rule

A preprocessing change is not adopted by this diagnostic alone. It is eligible only if it reduces near-side selection and trajectory instability without coverage loss and is later separately authorized for a fixed-contract validation. Otherwise retain the current selector.
