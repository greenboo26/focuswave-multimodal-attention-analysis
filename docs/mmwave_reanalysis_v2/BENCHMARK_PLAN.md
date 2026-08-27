# Benchmark plan

Protocol status: **FROZEN** by `BENCHMARK_DECISION_V1.md` and `configs/mmwave_reanalysis_v2/benchmark_decision_v1.json`. This file remains the high-level execution order; machine values take precedence.

## Common protocol

1. Build a per-session manifest containing source file, subject/session, sampling rates, time origin, target fields, ECG/RSP availability and immutable source hash.
2. Run reference-only ECG/RSP QC first. Save accepted intervals, rejected intervals, effective coverage and reasons.
3. Apply the same radar input cleaning, windows, candidate methods and quality gates to every method. No method-specific window selection.
4. Tune only on development subjects. Hold out complete subjects; never split windows from one subject across train/test.
5. Emit per-window results, aggregate results and a machine-readable manifest. Never interpolate rejected windows silently.

## HR / ECG metrics

Coverage, MAE, median absolute error, RMSE, Pearson/Spearman correlation, Bland–Altman bias and 95% limits, beat precision/recall/F1, one-to-one match count, timing error, 2x/0.5x lock rate, and respiratory-harmonic false-lock rate. Report overall and quality strata.

## BR / RSP metrics

The same rate metrics and Bland–Altman outputs, plus coverage and quality strata, but only for sessions/windows with valid RSP. If RSP is absent, the result is `NOT_VALIDATED_FOR_BR`.

## Candidate order

Baseline dual-band -> existing v3.1.1/VitalSense matched-filter interfaces -> v9 harmonic notch -> SSA+VMD -> DR-MUSIC/Harmonic MUSIC or sparse candidate -> multi-bin/spatial fusion. Selection is based on predeclared metrics and compatibility, not on a single best sample.
