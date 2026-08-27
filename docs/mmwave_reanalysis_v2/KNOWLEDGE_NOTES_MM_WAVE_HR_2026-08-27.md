# mmWave HR knowledge notes — 2026-08-27

Status: `CURRENT_WORKING_NOTES`

## Repository roles

- Canonical scientific/analysis truth: `greenboo26/focuswave-multimodal-attention-analysis`.
- Experiment/acquisition truth: `kyandi233-dev/FocusWave` (`stable-msmf`; `ecg` branch contains BIOPAC-related and calibration work).
- `mmwave-hrv-analysis` is legacy according to the stable registry; do not use it as current canonical truth unless a specific historical artifact is needed and actually accessible.

## Acquisition facts worth preserving

`kyandi233-dev/FocusWave@ecg/01-MainProgram/core/mmwave_capture.py` records the formal RS6240 acquisition path as complex IQ plus timestamps and PSIC-compatible output. The module documents:

- 2 TX × 4 RX;
- range FFT 256;
- default frame period 10 ms (~100 fps);
- 57 GHz start frequency;
- 37 mm range resolution;
- raw `.npz` complex IQ and dual timestamps for cross-device alignment.

This is materially different from AgeBalanced's 10 Hz derived radar representation. Any algorithm portability claim must explicitly distinguish these two input types.

## Existing historical evidence already in the central repo

From `EVIDENCE_LEDGER.md`:

- v1–v8 historical comparisons exist; v5 was historically best on some internal samples, not external validation.
- v3.1/v3.1.1 contains HR/IBI development on rest/deep-breath/SXQ/ECG calibration subsets.
- seven external-method A/B trials were already attempted historically: SPC, Hampel, phase difference, CFAR, SSA, envelope and CEEMDAN; they did not materially improve the then-current gate, but this is not a universal negative result.
- AgeBalanced v1.7 historical validation reported overall session-median HR MAE around 9.5 BPM, with high/medium/low quality around 1.6/3.4/10.1 BPM.
- current AgeBalanced provenance is 110 participants, 220 Rest sessions, no RSP.

## Existing failure modes already documented

From `FAILURE_MODE_REGISTRY.md`:

1. respiratory 2nd/3rd harmonics entering HR band;
2. strongest range bin can be clutter/multipath rather than chest;
3. VMD mode-selection instability;
4. good HR does not imply beat timing / HRV validity;
5. ECG T-wave double detection (controlled in current reference);
6. motion / edge exposure changes radar quality;
7. sparse/single-bin data may lack spatial redundancy;
8. some historical outputs/parameters remain missing.

These are hypotheses to test against the 9→27–37 BPM discontinuity, not reasons to start new algorithm families.

## Highest-priority root-cause hypotheses

### H1 — Metric/aggregation mismatch
Historical 9.14 BPM is session-level MAE followed by median across sessions; current 26.98/29.02/37.12 figures have been reported as pooled window-level MAE in later benchmark tasks. These are not numerically interchangeable. Recompute all major results under both aggregation conventions before interpreting the size of the performance collapse.

### H2 — Session/window cohort mismatch
Task 2S 60 s analysis had only 14 complete sessions and 12 ECG-QC-scored sessions, versus 60 development Rest sessions in the 25 s historical-equivalence analysis. The apparent 37 BPM result may therefore represent a much smaller and different subset. The exact common-session intersection is mandatory.

### H3 — ECG scorer / reference mismatch
Historical 25 s equivalence deliberately used historical ECG scoring semantics, while current benchmark uses `ecg_reference_v1`. A scorer change can move the reference HR, window eligibility and aggregation. Compare old and new ECG HR on the same windows before blaming radar.

### H4 — Window-sensitive radar pipeline behavior
The project route includes frequency-domain peak logic, time-domain peak logic, candidate correction, quality gates and temporal handling. Changing 25→30→50→60 s can alter spectral resolution, candidate counts and continuity rules. Window length should be isolated after H1–H3.

### H5 — Input/adapter semantics
AgeBalanced radar is 10 Hz derived data, while formal RS6240 acquisition is ~100 fps complex IQ. Verify what `validate_external_gold_0814.py` consumed historically and what current adapters feed into the project route. Units, phase convention, sample rate and whether data are already transformed are critical.

### H6 — Range-bin / spatial-selection mismatch
Existing failure registry states strongest-bin selection can lock onto clutter/multipath. Determine whether historical v1.7 and current benchmark use identical candidate-bin construction and voting.

## Improvement directions — only after diagnosis

Priority is not 'most advanced algorithm'. It is:

1. restore equivalent scoring/input semantics if the discontinuity is procedural;
2. recover and reuse historical multi-bin / harmonic / quality logic if current adapter dropped it;
3. if true harmonic-lock remains, use one targeted harmonic-control strategy;
4. if range-bin failure dominates, prioritize spatial/multi-bin consistency rather than another decomposition method;
5. if current 10 Hz derived AgeBalanced input lacks information required by modern HR/IBI methods, stop extrapolating from raw ~100 Hz RS6240 literature and treat the limitation as an input-representation boundary.

## Explicit non-goals during root-cause audit

- no 80-person heldout;
- no HRV;
- no formal `J:\Data` physiology run;
- no second/third external algorithm family;
- no ECG-guided per-window tuning.
