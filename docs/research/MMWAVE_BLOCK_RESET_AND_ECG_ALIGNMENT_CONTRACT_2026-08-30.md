# mmWave block-reset and ECG alignment contract — 2026-08-30

Status: `DECISION_FROZEN / IMPLEMENTATION_NOT_RUN`

Purpose: define the correct continuity boundary for any future mmWave target-tracking comparison and the exact block/ECG alignment anchors to use. This contract is downstream of the targeted validation closure and does not authorize a new formal batch, Issue #16, C2B/C2C, NIR/RGB producer changes, or portable-V2 edits.

## 1. Operator/protocol evidence: posture can legitimately reset between blocks

Operator protocol evidence from the formal acquisition: during block breaks participants were allowed/asked to restore posture, and posture was checked again before resuming. Maintaining exactly one posture for a long experiment was not realistic; participants could gradually slide down, slouch, or otherwise drift and then return toward the intended position during the break.

Scientific consequence: **target continuity must not be required across a block-rest-posture-reset boundary.** A change in selected range bin/channel between Block 1 and Block 2, or Block 2 and Block 3, is not automatically an algorithm failure because the participant's physical geometry relative to the radar may have intentionally changed during the break.

## 2. Correct continuity unit

The tracking state is therefore `BLOCK_LOCAL`, not `SESSION_GLOBAL`.

For every formal block:

1. at block start, initialize target selection anew from that block's data;
2. once initialized, continuity-aware selection may prefer the previous within-block target neighborhood rather than performing an unconstrained global re-selection on every window;
3. the tracker must still be allowed to move when evidence indicates real gradual drift or a better nearby target;
4. do not hard-freeze one bin/channel for the whole block;
5. at the next block boundary, discard the previous block's target state and initialize again.

Plain-language rule: **“follow continuously within a block; reset after the break.”**

This supersedes any interpretation of the prior suggestion as “pick one bin at the beginning of the session and never move again.”

## 3. Why the reset must occur at block start, not at arbitrary wall-clock times

The formal program on `kyandi233-dev/FocusWave@ecg` shows this actual order between blocks:

`block end -> forced rest -> rest end -> posture/NIR alignment -> next block 3-2-1 countdown -> block_start / segment_start marker -> run_single_block`

Source: `01-MainProgram/main_experiment_msmf.py` on branch `ecg`.

Therefore a future mmWave continuity algorithm must not carry target state across the `rest + posture alignment` interval. The new target state should be initialized using the first valid analysis window belonging to the new block after the block-start anchor.

## 4. ECG/Biopac block anchors from the acquisition program

Canonical acquisition-program source for this contract: `kyandi233-dev/FocusWave@ecg`.

### `01-MainProgram/core/event_logger.py`

The formal event logger writes every event to `beh/events.csv` with columns:

`event, segment, unix_ms, note, marker`

`unix_ms = time.time()*1000` and is stated to share the same time basis as the mmWave `timestamps.csv` Unix-time column. The same event is also sent as an 8-bit parallel-port pulse into the Biopac digital input when marker hardware is active.

Formal marker values:

| segment | start marker | end marker |
|---|---:|---:|
| baseline | 11 | 21 |
| block1 | 12 | 22 |
| block2 | 13 | 23 |
| block3 | 14 | 24 |
| rest | 15 | 25 |
| block4, if used by the breath-focus variant | 16 | 26 |

Experiment start/end markers are `1 / 2`.

Within each segment a per-second cyclic time code is emitted:

`101 -> 102 -> ... -> 110 -> 101 ...`

This dense tick sequence is explicitly intended to align the Biopac/ECG digital channel with the experiment/mmWave clock and to detect clock drift.

Direct source: https://github.com/kyandi233-dev/FocusWave/blob/ecg/01-MainProgram/core/event_logger.py

### `01-MainProgram/core/parallel_marker.py`

A marker is physically sent as an 8-bit pulse: write marker value to the parallel-port data register, hold for 5 ms by default, then write zero. The Biopac digital input records the pulse and reconstructs the 0–255 event value.

Direct source: https://github.com/kyandi233-dev/FocusWave/blob/ecg/01-MainProgram/core/parallel_marker.py

### `01-MainProgram/main_experiment_msmf.py`

The main experiment calls `_marker_seg_start('block1'/'block2'/'block3')` immediately before `run_single_block`, and `_marker_seg_end(...)` immediately after the block. Between non-final blocks it records a `rest` segment and then calls posture/NIR alignment before the next block loop begins.

Direct source: https://github.com/kyandi233-dev/FocusWave/blob/ecg/01-MainProgram/main_experiment_msmf.py

## 5. Required ECG/mmWave window mapping for any next comparison

Do **not** compare mmWave windows to ECG by assuming that one continuous session offset is sufficient.

For each participant/session:

1. read the experiment-side `events.csv`;
2. identify block start/end rows using `segment=block1/block2/block3` and markers `12/22`, `13/23`, `14/24`;
3. use the Biopac digital marker channel to identify the corresponding physical pulses;
4. use the cyclic `101–110` per-second markers to verify local alignment and clock drift within the block rather than relying only on a single start pulse;
5. map mmWave Unix timestamps to the same block using `events.csv`/mmWave timestamps;
6. cut ECG reference windows only from the matching block interval;
7. never allow an HR error window to cross a rest/posture-reset boundary;
8. report `block_id` in every continuity and ECG-comparison row.

If actual exported Biopac files already contain separate block files/segments, retain those boundaries and verify them against the program markers rather than reconstructing a different segmentation from elapsed time alone.

## 6. Candidate next test — corrected design

A future targeted test may compare, on the same prespecified ECG-aligned windows:

- `CURRENT_INDEPENDENT`: current behavior, each window selects bin/channel independently;
- `BLOCK_LOCAL_CONTINUITY`: initialize at each block start, then prefer a plausible neighboring bin/channel trajectory within that block while allowing justified drift;
- `BLOCK_LOCAL_MULTI_BIN` (optional only if separately authorized): combine evidence from several nearby plausible bins rather than relying on one winner.

Primary question: does block-local continuity materially improve ECG agreement compared with the current independent selector?

Do not judge success by “fewer switches” alone. A method passes only if physiological reference agreement improves without creating obvious failure cases.

## 7. Current authorization boundary

`BLOCK_BOUNDARY_RESET = FROZEN`

`ECG_ALIGNMENT_ANCHOR = PROGRAM_MARKERS + EVENTS.CSV + PER_SECOND_TICKS`

`SESSION_GLOBAL_FIXED_BIN = REJECTED`

`WHOLE_BLOCK_HARD_FIXED_BIN = NOT_RECOMMENDED`

`BLOCK_LOCAL_CONTINUITY_COMPARISON = CANDIDATE_NEXT_TEST / NOT_YET_RUN`

`HRV = BLOCKED`

`ISSUE_16 = PAUSED`
