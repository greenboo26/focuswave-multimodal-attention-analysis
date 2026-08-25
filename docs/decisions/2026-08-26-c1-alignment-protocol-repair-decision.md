# C1 alignment protocol repair decision

Date: 2026-08-26

## Status

`C1_ALIGNMENT_NOT_PRIMARY_CAUSE_STOP_HRV_CONFIRMED`

This is a current-competition-cycle stop for further beat-level IBI/HRV algorithm development. It is not a claim that RS6240 can never measure HRV.

## Scope

The repair used the frozen C1c/C1d radar beat timestamp assets for sessions `97793`, `9779`, and `97795`. It did not re-run raw ADC, change range/bin selection, VMD, waveform normalization, peak detection, ECG peak detection, or develop a new heartbeat algorithm.

## Evidence

- Independent synchronization evidence was read from each session's radar frame timestamp CSV, `events.csv`, and Biopac `.acq` digital marker stream.
- Marker-based clock mapping was available for all three sessions. Marker-fit maximum absolute residuals were approximately 0.63 ms, 0.48 ms, and 0.80 ms.
- Therefore, the audit did not find evidence for a device-clock error of the magnitude suggested by the `-250 ms` oracle lag.
- The fixed `-18 ms` mean F1 was 0.223; full-session oracle lag F1 was 0.362, but this is a label-informed upper bound only.
- Half-split held-out mean F1 was 0.314. Only one of three sessions reached the predeclared 0.10 session-level recovery threshold; the improvement was not stable across sessions or detector landmarks.
- Lag-invariant monotone IBI sequence alignment gave mean IBI MAE about 93.3 ms, with substantial missed/extra interval rates and inconsistent correlation. This audit does not depend on a constant timestamp shift.

## Interpretation

The fixed `-18 ms` assumption was too strong and is no longer used as an unqualified synchronization claim. However, the independent marker mapping and the held-out/IBI results do not support treating the oracle lag improvement as a recoverable synchronization correction. C1 remains unvalidated for reliable beat-level IBI/HRV in the current competition cycle.

## Reproducibility boundary

Raw ADC, ECG, `.acq`, and full waveform assets remain local and are not committed. The repository contains only the protocol-repair script, compact metrics, audit metadata, and this decision.
