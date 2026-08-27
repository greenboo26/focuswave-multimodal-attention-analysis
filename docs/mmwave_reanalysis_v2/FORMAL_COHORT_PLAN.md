# Formal cohort plan

This plan is intentionally downstream of benchmark freeze.

1. **Target-lock audit:** verify human-target candidate, range-bin stability, channel completeness, spatial consistency and target-vs-clutter status.
2. **Motion audit:** combine radar quality with existing RGB/NIR motion evidence where available; preserve modality-specific missingness.
3. **Time audit:** verify frame timestamps, unix-ms alignment, behavior probe windows and session boundaries. Reuse central alignment contracts rather than inventing a parallel join.
4. **Coverage audit:** report session, probe and window coverage separately for BR, HR and signal-only layers.
5. **Frozen application:** apply only the benchmark-frozen BR/HR method and configuration. Each output row carries `valid`, `uncertain`, or `reject` and a reason code.
6. **HRV gate:** do not calculate or report HRV as physiological evidence unless G5 passes. Historical HRV outputs remain `SUPERSEDED`/`BLOCKED` according to their ledger row.
7. **Physiology × attention:** model BR, HR and validated respiratory dynamics separately against Probe state, vigilance, complete behavior features, time-on-task, errors, omissions and RT variability; use participant-aware grouped inference and the existing frozen label semantics.
8. **Cross-modal check:** compare with RGB motion and NIR pupil features as corroboration, not ground truth substitution.
9. **Product line:** compare Behavior, mmWave-physio, mmWave-signal, RGB, NIR, teacher and deployment models only after science-layer provenance is complete.
