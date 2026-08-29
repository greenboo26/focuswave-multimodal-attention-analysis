# mmWave DLL frame-time reconstruction and window equivalence audit — 2026-08-30

状态：`WINDOW_CONTRACT_RECONSTRUCTED / HR_NOT_YET_RERUN`

- Canonical algorithm baseline at run: `ab39ad272462c54208b56e0b302b5d9ff1e95b4c`.
- FocusWave acquisition source: `ecg` `8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`.
- This run only freezes frame-time semantics, audits mapping, and compares old/new window membership. It does not run HR, change target/gate, change ECG, or modify producer/raw/firmware/portable V2.

## DLL timestamp meaning

`receive_data.timeStamp` is a DLL-provided .NET DateTime/string field converted by `_dotnet_ts_to_unix_ms()` into Unix ms. Its exact device-vs-SDK generation origin is not documented in the repository, so the contract records that limitation. In the data, it is monotonic and aligns to program marker Unix times within millisecond-scale deltas.

## Python/NPZ/DLL mapping

Mapping audit: `D:\Project\厚粲杯\11_数据\derived\mmwave_timestamp_semantics_repair_20260830\MMWAVE_FRAME_TIME_MAPPING_AUDIT.csv` (local-only row-level output), SHA-256 `31ee9ed82d302c481fcddd0eb74dd1ad8ee4ca0cc16716d2b3bceecfb9544959`.

| subject | timestamp rows | NPZ frames | frame diff | mapping | DLL monotonic | negative DLL steps | DLL interval median/max ms |
|---|---:|---:|---|---|---|---:|---|
| 97793 | 162924 | 162924 | [1] | OK | True | 0 | 10.0/16.0 |
| 9779 | 155557 | 155557 | [1] | OK | True | 0 | 10.0/15.0 |
| 97795 | 140648 | 140648 | [1] | OK | True | 0 | 10.0/15.0 |

## Marker and BIOPAC anchor audit

Existing `ecg_alignment_audit.csv` remains the BIOPAC/program marker audit: block-local mappings, 101–110 ticks, and complete-block status are reused. The reconstruction does not create a new ECG reference. Anchor details are in the manifest.

## Absolute coverage limitation

- Complete-block end minus last recorded DLL frame: `{"97793": {"last_dll_unix_ms": 1786871352163, "complete_block_end_unix_ms": 1786871223401, "complete_block_end_after_last_dll_ms": -128762}, "9779": {"last_dll_unix_ms": 1786866226251, "complete_block_end_unix_ms": 1786866219087, "complete_block_end_after_last_dll_ms": -7164}, "97795": {"last_dll_unix_ms": 1786887631266, "complete_block_end_unix_ms": 1786887656075, "complete_block_end_after_last_dll_ms": 24809}}`.
- Short reconstructed windows (`new_window_frame_count < 100`): `1`; the observed case is `[('97795', 'block4', 'block4_w028', 46)]`.
- The 97795/block4 program end marker is 24,809 ms after the last DLL frame; the final guarded window therefore contains only 46 recorded DLL frames. No synthetic timestamps, frame padding, or Python-time backfill is applied.

## Old versus new windows

- New DLL-time windows: `335`; exact `25`, partial (Jaccard ≥ 0.9) `156`, obvious (Jaccard < 0.9) `154`.
- Changed membership: `310/335`; Jaccard mean/median/min: `0.73641/0.923114/0.0`.
- New frame count range: `46–1979`; mean frame-count delta versus old: `40.776119`.
- The old Python-time windows are not automatically deleted or superseded by this audit; the HR decision is deferred until the unchanged estimator is rerun on the new membership if the equivalence gate is materially changed.

## Final decision gate

- `DLL_TIME_RECONSTRUCTION`: supported for this dataset as absolute DLL Unix ms, with the source-origin limitation recorded.
- `WINDOW_EQUIVALENCE`: see exact/partial/obvious counts above.
- `HR_RERUN`: not performed in this first stage.
- HR remains `HOLD`; BR remains `HOLD`; HRV remains `BLOCKED`; Issue #16 remains `PAUSED`.

## Artifacts

- `MMWAVE_FRAME_TIME_MAPPING_AUDIT.csv` — local-only row-level mapping audit
- `MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md`
- `MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv`
- `MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_MANIFEST.json`
- `MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_REPORT_2026-08-30.md`
