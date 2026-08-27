# Benchmark Decision V1

Status: **PASS — FROZEN BEFORE HELD-OUT SCORING**

Freeze date: 2026-08-27

Machine contract: `configs/mmwave_reanalysis_v2/benchmark_decision_v1.json`

This decision freezes Phase 2 benchmark rules before historical baseline reproduction or any new held-out candidate score is inspected. It does not authorize Phase 2B, formal `J:\Data` analysis, HRV, or a candidate-method benchmark.

## Frozen cohort and split

- AgeBalanced primary benchmark: all 110 participants, exactly the two `Rest` sessions per participant (`Lying/Rest`, `Sitting/Rest`), 220 sessions. The 220 Post-exercise sessions are a separately labelled stress sensitivity set and cannot be pooled into primary selection.
- The participant split is frozen in `configs/mmwave_reanalysis_v2/agebalanced_split_v1.json`: seed `20260827`; deterministic SHA-256 ranking; 30 development participants and 80 held-out participants. Every session/window from one participant stays in one split.
- VS_DATASET is a secondary external generalization source only when its 48 source pairs and hashes are available. It does not replace the AgeBalanced held-out comparison.
- RS6240 ECG/RSP calibration is a device-matched validation source only after its raw-to-derived session linkage is frozen.
- Sources without raw RSP cannot score BR. Sources without QC-passed ECG-derived beats cannot score beat endpoints. HRV remains unauthorized.

## Frozen windows and input

Primary windows are 30 s with a 5 s step and half-open boundaries. A 10 s / 5 s sensitivity is HR-only; a 60 s / 5 s sensitivity may score HR, BR and beats. Incomplete end windows are rejected, never padded. Historical 25 s / 5 s reproduction is explicitly labelled `historical_equivalence_only` and cannot select a candidate.

The common radar input is the source-hashed, decoded complex range-FFT tensor plus source timestamps, normalized to `time × channel × range_bin`, cropped to the documented 0.30–3.50 m physical region, and windowed without interpolation. Phase unwrap, filtering, target/channel selection, beamforming, SSA, VMD, MUSIC and harmonic cancellation are method operations, not hidden common preprocessing; every such operation must be config-hashed and reference-blind.

## Frozen reference rules

Reference processing runs on the reference stream before any radar score is computed.

- `ecg_reference_v1`: raw ECG; monotonic timestamps ≥99.5%; finite samples ≥99.9%; third-order zero-phase Butterworth 0.5–40 Hz; robust median/MAD normalization; both polarities evaluated; `find_peaks` minimum distance 0.30 s and normalized prominence 0.25; IBI 300–2000 ms; at least 10 reference beats and ≥80% valid intervals per scored window. HR is `60 / median(valid IBI)`.
- The historical “adjacent IBI change >20%” rule is retained as a flag, not an automatic deletion. It can otherwise discard real respiratory sinus arrhythmia. Physiologic-range or detector/morphology failure is required for automatic deletion.
- `rsp_reference_v1`: raw respiratory-belt waveform only; monotonic timestamps ≥99.5%; finite samples ≥99.9%; fourth-order zero-phase Butterworth 0.1–0.7 Hz; robust normalization; `find_peaks` minimum distance 0.50 s and normalized prominence 0.20; 6–42 rpm; at least three complete cycles and ≥80% valid cycles. The historical 17% adjacent-cycle rule is not an automatic rejection rule.
- A chest accelerometer, a breath-hold marker or a radar respiratory trace is not renamed RSP.

## Frozen synchronization and quality

Rate metrics use source timestamps and identical half-open windows with no lag search. Beat matching is chronological one-to-one with ±75 ms primary tolerance and ±50/100/150 ms sensitivities. A single delay per `dataset × method` may be estimated from development participants only, using at least 100 matches from at least five people inside ±250 ms, then frozen and hash-recorded. Per-window, per-session held-out or held-out-informed delay tuning is forbidden.

Radar quality strata are reference-blind. The common QC target is the maximum residual-power channel/bin in the physical ROI after per-window complex-mean removal. High quality requires timestamp coverage ≥0.99, finite ratio ≥0.999, max gap ≤0.2 s, target SNR ≥10 dB and phase-increment coherence ≥0.8. Medium requires ≥0.95, ≥0.995, ≤0.5 s, ≥3 dB and ≥0.5. Decode failure, no ROI target, timestamp coverage <0.80, finite ratio <0.95 or max gap >1.0 s is rejected. Low and rejected windows remain in the coverage denominator.

## Frozen metrics, gates and selection

Every endpoint reports coverage, MAE, median AE, RMSE, Pearson and Spearman correlation, Bland–Altman bias/limits, 90th-percentile AE and quality strata. Beat endpoints add precision, recall, F1, timing MAE and IBI agreement. Confidence intervals use 2,000 participant-cluster bootstrap resamples with seed `20260827`.

Hard thresholds are frozen in `VALIDATION_THRESHOLD_JUSTIFICATION.md` and the machine contract. HR and BR are selected separately. An algorithm must first have a usable license/permission, reproducible provenance, fixed config hash, schema-valid output, and pass every endpoint-specific hard gate. Among eligible methods, the primary rank is held-out participant-macro MAE. A difference below 0.5 bpm/rpm whose paired participant-bootstrap 95% CI includes zero is a tie; the tie-break order is existing validated implementation, clear permissive license, lower compute, then fewer device assumptions. Held-out results cannot trigger retuning.

## Harmonic-lock definition

The tolerance around a candidate harmonic is `max(3 bpm, 5% of that harmonic rate)`. Correct HR takes precedence when within 3 bpm; otherwise classify `two_x_hr`, `half_x_hr`, `resp_h2`, `resp_h3` or `resp_h4`. A respiratory-harmonic lock requires valid RSP and must not also be a correct-HR estimate. If RSP is absent, respiratory-harmonic status is `NOT_ASSESSABLE`, not zero.

## Required output

All algorithms emit JSON Lines conforming to `schemas/mmwave/per_window_benchmark_v1.schema.json`. A CSV is allowed only as a lossless projection of the canonical records. Rejected windows must carry a reason and cannot be silently interpolated or omitted.
