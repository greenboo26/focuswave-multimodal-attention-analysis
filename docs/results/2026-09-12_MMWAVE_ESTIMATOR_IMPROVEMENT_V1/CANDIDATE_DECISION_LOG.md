# Candidate decision log

All hypotheses and thresholds were frozen before paired evaluation.

## H1_WARNING_TIME_GATE

- Hypothesis: Use time HR when abs(time HR - spectral HR) > 10 bpm; otherwise retain current fused HR.
- Frozen source: Existing producer HR_TIME_FREQ_WARNING_BPM=10.0.
- Result: REJECT.
- MAE: 9.618844 bpm; paired improve/worsen/tie: 8/1/91.
- Failed checks: no_control_correct_to_gt10_transition, no_probe_worsens_gt5_bpm.

## H2_HARMONIC_CONFLICT_TIME_GATE

- Hypothesis: Use time HR only when the >10 bpm disagreement co-occurs with fused/spectral HR within 5 bpm of 2x or 3x mmWave BR.
- Frozen source: Existing 10 bpm warning plus frozen P2 5 bpm harmonic diagnostic tolerance.
- Result: REJECT.
- MAE: 10.454474 bpm; paired improve/worsen/tie: 1/0/99.
- Failed checks: at_least_3_of_5_sessions_improve.

## H3_LOW_CONFIDENCE_TIME_GATE

- Hypothesis: Use time HR when disagreement >10 bpm and current confidence <0.12; otherwise retain fused HR.
- Frozen source: Existing producer confidence>=0.12 reliable-anchor threshold.
- Result: REJECT.
- MAE: 9.739718 bpm; paired improve/worsen/tie: 7/1/92.
- Failed checks: no_control_correct_to_gt10_transition, no_probe_worsens_gt5_bpm.

## Stop decision

No candidate passed the frozen stability gate; stop with `NO_STABLE_IMPROVEMENT`.
