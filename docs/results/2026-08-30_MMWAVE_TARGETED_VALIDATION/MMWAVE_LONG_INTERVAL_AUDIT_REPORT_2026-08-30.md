# mmWave long-frame interval source and impact audit — 2026-08-30

状态：`PARTIAL / TIMESTAMP_RECORDING_ARTIFACT / GAP_EFFECT_UNRESOLVED`

## Direct answer

- 457 个 Python timestamp column-3 长间隔全部同时 >500 ms：457 / 457。
- 全部 457 个 Python 长间隔分布（min/p10/median/p90/p95/max ms）：{'n': 457, 'min_ms': 1748, 'p10_ms': 1953.2, 'median_ms': 2326.0, 'p90_ms': 2859.8, 'p95_ms': 3070.2, 'max_ms': 6495}；对应 DLL 间隔分布：{'n': 457, 'min_ms': 8, 'p10_ms': 9.0, 'median_ms': 10.0, 'p90_ms': 11.0, 'p95_ms': 12.0, 'max_ms': 13}。
- 457 个事件全部落在 NPZ file/chunk boundary；每个 subject 的边界数与长间隔数一一对应。
- 同一批数据的 DLL timestamp column-2 没有任何 >100 ms 或 >500 ms interval，说明当前 457 更符合 consumer/write timestamp artifact，而不是已被源码证明的 sensor frame loss。
- 事件周期不是独立生理周期，而是 1000-frame NPZ rotation/write pattern candidate；不能把 estimated_missing_frames 当作实际丢帧数。

## Acquisition source evidence

- `FocusWave@ecg` source commit: `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`; historical acquisition fix commit: `817a7fccb969bcc6e1e0071b387f88e3b3494481` (`v1.4.4`).
- `01-MainProgram/core/mmwave_capture.py:337-342`, `_on_data`: SDK/DLL callback only puts `receive_data` into a bounded queue (`maxsize=5000`); queue full increments `error_count` but does not write a timestamp row.
- `:466-489`, `_process_data_loop`: consumer thread dequeues data and calls `_process_datacube` for dataType 3.
- `:352-376`, `_dotnet_ts_to_unix_ms`: DLL callback `receive_data.timeStamp` is converted to Unix ms; this is the hardware/DLL-side timestamp field.
- `:378-397`, `_process_datacube`: after dequeue, it obtains DLL time and Python `time.time()`, then writes both to timestamp CSV. The audited column 3 is therefore generated at consumer/write processing time, not at callback receipt.
- `:428-431` and `:433-464`: every 1000 processed frames triggers `_flush_npz_chunk`; `np.savez_compressed` runs in the same consumer thread.
- `:558-585`, `stop`: stops DLL, waits up to 5 s for the queue, stops worker, and writes the final NPZ chunk. Historical `v1.4.4` only added conversion-error/empty-chunk protection; it did not remove this architecture.

## Long-event classification

Rows: 457; all >500 ms: `True`. See `MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv` for every row, phase, chunk, block and rest flags.

| subject | Python >100 | Python >500 | DLL >100 | DLL >500 | chunk-boundary events | Python long distribution |
|---|---:|---:|---:|---:|---:|---|
| 97793 | 162 | 162 | 0 | 0 | 162 | {'n': 162, 'min_ms': 1763, 'p10_ms': 1922.2, 'median_ms': 2278.5, 'p90_ms': 2761.9, 'p95_ms': 2832.7, 'max_ms': 4338} |
| 9779 | 155 | 155 | 0 | 0 | 155 | {'n': 155, 'min_ms': 1805, 'p10_ms': 2001.8, 'median_ms': 2360.0, 'p90_ms': 2882.4, 'p95_ms': 3724.4, 'max_ms': 6495} |
| 97795 | 140 | 140 | 0 | 0 | 140 | {'n': 140, 'min_ms': 1748, 'p10_ms': 1927.9, 'median_ms': 2312.0, 'p90_ms': 2925.0, 'p95_ms': 3040.25, 'max_ms': 3977} |

## ECG/BIOPAC alignment contract

Window HR/ECG comparisons are inherited from the fixed 335-row block-local replay and its per-block alignment audit: `events.csv` start/end markers (baseline 11/21, block1 12/22, block2 13/23, block3 14/24, rest 15/25; block4 16/26 when present) plus 101–110 per-second ticks. The existing audit records 8 complete blocks, 7/8 exact marker sequences, and block-wise ECG affine fits; no cross-rest or cross-posture mapping is used. The marker/tick audit remains evidence for alignment quality, not a license to interpret Python writer timestamps as sensor timing. The prior 12 transitions remain revoked as continuity-failure evidence: they were baseline/pre-block startup transitions, not valid within-block transitions.

## Periodicity and distribution

The periodicity audit reports quantiles, fixed 1/2/5/10/30/60-s matches within ±1 s, histograms, frame modulo 1000, and phase/boundary counts below. Frame-index spacing and DLL-time spacing are the acquisition-side checks; Python-time spacing is separately shown because it is generated in the consumer/write path.

| subject | Python inter-event s (median [p10,p90]) | DLL inter-event s (median [p10,p90]) | frame inter-event (median) | Python fixed-period matches | DLL fixed-period matches | frame modulo 1000 | phases |
|---|---|---|---:|---|---|---|---|
| 97793 | 10.113 [10.104, 10.124] | 10.114 [10.112, 10.116] | 1000.0 | {'1': 0, '2': 0, '5': 0, '10': 161, '30': 0, '60': 0} | {'1': 0, '2': 0, '5': 0, '10': 161, '30': 0, '60': 0} | {'501': 162} | {'baseline': 17, 'baseline->outside_formal_segments': 1, 'block1': 58, 'block1->rest': 1, 'block2': 55, 'block2->outside_formal_segments': 1, 'outside_formal_segments': 5, 'rest': 23, 'rest->outside_formal_segments': 1} |
| 9779 | 10.114 [10.104, 10.122] | 10.114 [10.112, 10.115] | 1000.0 | {'1': 0, '2': 0, '5': 0, '10': 153, '30': 0, '60': 0} | {'1': 0, '2': 0, '5': 0, '10': 154, '30': 0, '60': 0} | {'69': 155} | {'baseline': 18, 'block1': 57, 'block2': 57, 'outside_formal_segments': 9, 'outside_formal_segments->block2': 1, 'rest': 13} |
| 97795 | 10.982 [6.248, 12.653] | 10.113 [10.111, 10.115] | 1000.0 | {'1': 0, '2': 7, '5': 5, '10': 45, '30': 0, '60': 0} | {'1': 0, '2': 0, '5': 0, '10': 139, '30': 0, '60': 0} | {'816': 140} | {'baseline': 16, 'block1': 27, 'block2': 28, 'block3': 28, 'block4': 27, 'outside_formal_segments': 12, 'outside_formal_segments->block1': 1, 'outside_formal_segments->block2': 1} |

Python inter-event histograms and complete periodicity details are in `MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json`. The fixed-period and histogram counts are descriptive diagnostics; the exact repeated frame modulo and NPZ boundary coincidence are the stronger source-localization evidence.

## Timestamp and boundary sanity checks

- duplicate long-event frame keys: `0`
- nonpositive adjacent Python intervals: `6203`; DLL intervals: `0`; these are same-millisecond duplicates, not negative clock steps
- negative Python timestamp intervals: `0`; timestamp reset found: `False`
- Python events in the 100–500 ms band: `0` (none; all 457 events are >500 ms)
- all long events are NPZ chunk boundaries: `True`
- fixed stop/wait behavior is source-localized to shutdown (`stop` queue drain/final flush), not a repeated in-recording boundary mechanism

## Window gap burden

All 335 windows retain their burden fields. `expected_frame_count_local` uses the regular DLL timestamp nominal interval; the Python timestamp span can be inflated by writer pauses. No window was removed. The estimated frame-loss fraction is a window-index density diagnostic only and must not be read as confirmed sensor frame loss when the Python window axis is artifact-contaminated.

## Gap burden versus HR error

Spearman results are in `MMWAVE_GAP_BURDEN_CORRELATION.csv`; rows are reported overall, participant-stratified, and block-stratified. Because every window has a long interval and the intervals are a recording artifact, these correlations are descriptive and cannot identify causal gap damage.

## Fixed sampling-rate sanity check

The current estimator uses fixed `FS=100.0` in `scripts/process_vital_signs_v3_1_1.py:13`; `_sos_bandpass` uses `fs=FS` at `:273-275`; periodogram uses `fs=FS` at `:1236-1241`; peak minimum distance uses `FS` at `:1244-1249`. It does not consume the timestamp column. The DLL timestamp sequence is regular at about 10 ms, so fixed-FS processing of the dense IQ frame sequence is supported by source/data evidence. Using Python column 3 as a physical time axis remains questionable because its pauses are writer-side artifacts.

`TIMESTAMP_AWARE_RESAMPLED` was not run: resampling the writer-artifact column would manufacture a false sensor-gap correction. First resolve the timestamp-column contract; no HR algorithm or producer change is justified by this audit.

## Final classification

- `GAP_SOURCE_CLASSIFICATION = TIMESTAMP_RECORDING_ARTIFACT`
- `GAP_EFFECT_ON_HR = UNRESOLVED` (no clean no-gap comparator; burden is confounded with writer/chunk position)
- `FIXED_FS_WITH_GAPS = QUESTIONABLE` overall; fixed-FS signal processing is supported for the DLL-regular dense frame sequence, but Python timestamp-axis window semantics are not.
- HR remains `HOLD`; BR remains `HOLD`; HRV remains `BLOCKED`; #16 remains `PAUSED`.

## Artifacts

- `MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv`
- `MMWAVE_WINDOW_GAP_BURDEN.csv`
- `MMWAVE_GAP_BURDEN_CORRELATION.csv`
- `ecg_alignment_audit.csv`
- `MMWAVE_ACQUISITION_TIMESTAMP_SOURCE_AUDIT.md`
- `MMWAVE_LONG_INTERVAL_AUDIT_REPORT_2026-08-30.md`
- `MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json`
