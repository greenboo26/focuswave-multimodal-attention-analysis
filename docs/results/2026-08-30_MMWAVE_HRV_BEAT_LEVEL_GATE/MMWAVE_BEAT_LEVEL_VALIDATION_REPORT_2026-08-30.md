# mmWave beat-level validation gate (2026-08-30)

Status: `PARTIAL / HRV_BLOCKED`; this is a beat-timing validity audit, not a formal HRV result.

## Direct conclusion

- Existing producer outputs already contain `heart_peaks` (frame indices) and a `heartbeat` waveform; no new radar beat detector or export adapter was created.
- Eight complete formal blocks were evaluated using one deterministic 60 s interval per block, after a 30 s boundary guard. The older `_selection_60s` files start at raw frame 0 before formal blocks and were not used as ECG-aligned windows.
- At the pre-existing primary ±75 ms one-to-one matching tolerance: pooled matches `119/699` ECG R-peaks against `565` radar peaks; sensitivity=`0.170243`, precision=`0.210619`.
- Per-window median sensitivity=`0.156091`, median precision=`0.188922`, median paired-IBI MAE=`46.258 ms`.
- The paired-beat subset has median raw timing MAE=`35.615 ms`; this conditional timing value does not compensate for the low match rate.
- Beat-derived mean HR is not consistent with same-window existing spectral HR: median absolute difference=`49.114 bpm` (the beat-derived values are based only on matched-beat intervals and are therefore not promotable).
- No formal RMSSD, SDNN, LF/HF, or any other HRV metric was calculated in this run. HRV remains `BLOCKED` because the beat-level evidence is not sufficient for promotion.

## Fixed evaluation contract

- Radar: existing full-record v3.1.1 NPZ `heart_peaks`; timestamps are mapped through the authoritative DLL-time rows. No detector parameter was changed.
- ECG: existing block-local affine event-marker mapping and the fixed `gold_standard_qa.py` ECG band/peak parameters; raw R-peaks are retained for the match audit.
- Matching: one-to-one nearest match, no per-window lag search; primary tolerance ±75 ms, with ±50/100/150 ms sensitivity only.
- IBI: successive intervals among matched pairs; a constant absolute offset cancels and is not used to select radar peaks.
- BR: existing full-record `breath_rate` is retained as supporting metadata only; no new BR method or per-window harmonic diagnostic was run.

## Tolerance sensitivity

| tolerance | pooled matched | ECG R-peaks | radar peaks | sensitivity | precision |
|---:|---:|---:|---:|---:|---:|
| 50 ms | 83 | 699 | 565 | 0.118741 | 0.146903 |
| 75 ms | 119 | 699 | 565 | 0.170243 | 0.210619 |
| 100 ms | 161 | 699 | 565 | 0.230329 | 0.284956 |
| 150 ms | 251 | 699 | 565 | 0.359084 | 0.444248 |

## Human-readable project pipeline map

The code-level map is maintained in `docs/research/MMWAVE_HR_BR_HRV_PROJECT_PIPELINE_MAP_2026-08-30.md`. In brief: shared range-domain input and phase/displacement feed a low-frequency BR branch and a cardiac branch; the cardiac branch's existing peak array is the common source for beat-derived HR and any future HRV, while spectral HR remains an independent QC/fallback output.

## Decision

`BEAT_LEVEL_GATE = NOT_PASSED_FOR_PROMOTION`; `HRV = BLOCKED`. The result identifies a measurable blocker (low radar-to-ECG beat correspondence) and does not authorize a new detector, new selector, HRV window tuning, or formal RMSSD/SDNN calculation.

## Artifacts

- `MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY.csv` — committed aggregate per-window metrics.
- `MMWAVE_BEAT_LEVEL_TOLERANCE_SENSITIVITY.csv` — committed pooled tolerance sensitivity.
- `MMWAVE_BEAT_LEVEL_VALIDATION_MANIFEST.json` — source hashes, contract, and output boundary.
- `MMWAVE_BEAT_LEVEL_VALIDATION_PER_WINDOW_LOCAL_ONLY.csv` — local-only detailed rows; raw ECG/radar data remain outside Git.
