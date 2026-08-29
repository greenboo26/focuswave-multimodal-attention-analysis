# mmWave acquisition/DLL coverage tail audit — 2026-08-30

状态：`PARTIAL / HISTORICAL_TAIL_IRRECOVERABLE / FUTURE_STOP_ORDER_FIX_IDENTIFIED`

## Scope and reuse gate

本审计只读取既有 `events.csv`、`*_mmwave_timestamps.csv` 的事件、首尾、计数与 frame-index 连续性，并检查 FocusWave `ecg` immutable source ref。没有重做 Python-vs-DLL timestamp discovery，没有读取或修改 NPZ/raw payload，没有 synthetic padding/backfill，没有改 primary 335-window provenance，也没有运行 C2B/C2C 或 HR analysis。

- RUN_ID: `issue28-tail-20260830-r1`
- canonical algorithm HEAD: `805db1d3f2d701d46f678b7cd911990f779a4966`
- FocusWave source: `ecg@8e6fe5c5d08f386661bc05aaf9d5c5715a43b317`
- REUSE_REJECTION_REASON: existing c0f1717 coverage audit only covered the three targeted subjects and did not inspect acquisition lifecycle ordering or the other available session tails; a bounded new audit was required to answer Issue #28 items 1–3.
- Existing coverage manifest reused without modification: `MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_MANIFEST.json`; its recorded algorithm head remains `426576e0809252656b79729ac077e91a6bfca80d` and its historical input/reconstruction provenance remains the prior worktree (`D:\Project\厚粲杯\08_算法\work\mmwave_targeted_validation_20260830_rerun\docs\results\2026-08-30_MMWAVE_TARGETED_VALIDATION\MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv`).

## Source-level causal path

在 `mmwave_capture.py` 中，DLL callback 只把对象放入有界队列；worker 随后同步执行 `DatacubeConversion` 和文件写出。现有 `stop()` 的顺序是 `StopCollectingData()` → 将 `_recording_flag` 设为 false → 等待队列 → 停 worker → flush/close。这样，停止前已经进入队列但尚未被 worker 消费的帧，会在队列等待期间被取出但因 recording flag 已关闭而不再写出；当前 meta 也没有保存 queue backlog、callback drop 或 stop latency，无法从历史文件单独区分“队列残留被丢弃”和更底层 SDK/DLL 时间戳漂移。

源码顺序检查：

- callback enqueue line `340`; synchronous conversion line `410`.
- `stop()` line `558`; `recording_flag=False` line `565` precedes queue wait line `569`.
- main program logs block marker end before the final UI/cleanup; `_stop_all_modalities()` line `1264` precedes `experiment_end` logging line `1271`.
- EventLogger flushes each event at line `85`, so marker-file buffering is not the primary explanation for the observed event timestamps.

## Observed tail

| subject | audit | block4 | frame indices consecutive | reference end − last DLL ms | experiment end − last Python ms | final Python − DLL ms | queue-lag signature |
|---|---|---:|---|---:|---:|---:|---|
| 2 | MISSING_REQUIRED_LOG | None | N/A | None | None | None | False |
| 3 | MISSING_REQUIRED_LOG | None | N/A | None | None | None | False |
| 4 | MISSING_REQUIRED_LOG | None | N/A | None | None | None | False |
| 5 | MISSING_REQUIRED_LOG | None | N/A | None | None | None | False |
| 6 | MISSING_REQUIRED_LOG | None | N/A | None | None | None | False |
| 97792 | OK | False | True | 1472 | 1470 | 2 | False |
| 97793 | OK | False | True | 1709 | 1708 | 1 | False |
| 97795 | OK | True | True | 24809 | -71 | 24887 | True |
| 97796 | OK | True | False | 26119 | -74 | 26201 | True |
| 9779 | OK | False | True | 1171 | 1170 | 1 | False |
| 97994 | OK | True | False | 52560 | -49 | 52616 | True |

## Session-count and frame-index limits

`session_count=11` means all `D:\acq_mmwave_data` `sub-*` directories enumerated by this audit. `audited_session_count=6` means only sessions with both `beh/events.csv` and a timestamp CSV. The remaining `5` sessions are `MISSING_REQUIRED_LOG`; they were not excluded as negative evidence and cannot be used to rule out the same tail pattern.

Frame-index continuity is session-specific, not a global property:
- `97792`: `frame_index_consecutive=true` (`gap_count=0`).
- `97793`: `frame_index_consecutive=true` (`gap_count=0`).
- `97795`: `frame_index_consecutive=true` (`gap_count=0`).
- `97796`: `frame_index_consecutive=false` (`gap_count=82`, first gap=[1262810, 1262982, 171]).
- `9779`: `frame_index_consecutive=true` (`gap_count=0`).
- `97994`: `frame_index_consecutive=false` (`gap_count=314`, first gap=[103051, 103066, 14]).
- The nonconsecutive retained indices for `97796` and `97994` remain unresolved limitations. They do not invalidate the observed timestamps, but they prevent treating those sessions as proof of exactly the same frame-loss mechanism as `97795`.

## Root-cause conclusion

- Long-tail candidates under the engineering rule `reference end − last DLL >= 5000 ms`: `3` sessions: `97795, 97796, 97994`.
- `97795/block4`: the existing primary-window evidence remains unchanged: `w027` has 1,035 frames and `w028` has 46 frames; their DLL end gaps are 9,536 ms and 19,536 ms. The block4 marker is 24,809 ms after the last DLL frame.
- `97795`, `97796`, and `97994` all show the same long-tail signature in the available four-block recordings, so the evidence does not support calling this a 97795-only marker-write anomaly. However, `97796` and `97994` have `frame_index_consecutive=false`; that nonconsecutiveness is unresolved, and the five `MISSING_REQUIRED_LOG` sessions cannot be used to exclude the same pattern. Sessions without block4 are recorded as not comparable at block4.
- The best supported mechanism is a slow/saturated consumer plus shutdown ordering: the final Python processing times are near the experiment end while the stored DLL times lag by about 24.8 s, 26.1 s, and 52.6 s. This is not sufficient to prove a physical sensor dropout. `97795` has consecutive retained frame indices in this scan; `97796` and `97994` do not, so any stronger common-loss claim remains unsupported. Any unretained queue tail is not recoverable from the files.
- Historical status: `IRRECOVERABLE`. No timestamp, frame payload, queue counter, or callback receipt exists that can safely reconstruct the missing/ambiguous tail. Do not backfill, pad, or replace the primary 335-window result.

## Future prevention (source-owner patch location; not applied here)

最小修复位置是 FocusWave `ecg` 的 `01-MainProgram/core/mmwave_capture.py::MMWaveCapture.stop()`：停止 DLL 后先断开 callback 输入，并在 `_recording_flag` 仍为 true 时按 `unfinished_tasks`/明确 drain-and-join 语义消费已入队对象；只有队列真正排空或明确记录超时后，才关闭 recording/worker、flush 文件和写 meta。meta 应追加 queue residual/drop count、stop begin/end 和 drain timeout，便于下一次判定 acquisition tail。需要在采集机做一次短时真实硬件 dry-run 验证；本审计不修改 producer worktree，也不宣称该未来修复已经验证。

## Boundary to other issues

本结果只补足 acquisition/DLL tail 的工程证据；它不改变现有 335-window primary provenance，不阻塞 #24–#27 的 validity 分析，也不把 coverage tail 解释为总体 HR 大误差主因。

## Outputs

- `MMWAVE_ACQUISITION_TAIL_AUDIT_2026-08-30.csv`
- `MMWAVE_ACQUISITION_TAIL_AUDIT_REPORT_2026-08-30.md`
- `MMWAVE_ACQUISITION_TAIL_AUDIT_MANIFEST.json`
