# mmWave DLL-time window coverage audit — 2026-08-30

状态：`COVERAGE_CONTRACT_FROZEN / HR-INDEPENDENT`

- Input: frozen DLL-time windows `335`; the primary ARM0/ARM1/ARM2 full-window outputs are not deleted or overwritten.
- Coverage uses only DLL timestamps and the frozen block/window boundaries; ECG HR, radar HR, abs error, and arm performance are not used to define thresholds.
- Local frame rate per subject/block: median interval, p5, p95, and effective Hz=`1000/median_interval_ms`; expected count=`20,000/median_interval_ms + 1`.
- Frozen classes: `COMPLETE` if coverage ≥0.95, both boundary gaps ≤max(3×median interval, 50 ms), and largest internal gap ≤1,000 ms; `SEVERELY_INCOMPLETE` if coverage <0.50, a boundary gap >max(1,000 ms, 5×median interval), or an internal gap >1,000 ms; otherwise `PARTIAL`.
- Counts: `{'COMPLETE': 333, 'PARTIAL': 0, 'SEVERELY_INCOMPLETE': 2}`; exclusion candidates are flags only and do not delete primary windows.

## Subject/block local rates

| subject/block | median interval ms | p5 ms | p95 ms | effective Hz |
|---|---:|---:|---:|---:|
| 9779/block1 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 9779/block2 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 97793/block1 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 97793/block2 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 97795/block1 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 97795/block2 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 97795/block3 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |
| 97795/block4 | 10.000000 | 9.000000 | 12.000000 | 100.000000 |

## Non-complete windows

| subject | block | window | frames | coverage | start gap ms | end gap ms | largest internal gap ms | class |
|---|---|---|---:|---:|---:|---:|---:|---|
| 97795 | block4 | block4_w027 | 1035 | 0.517241 | 7.0 | 9536.0 | 13.0 | SEVERELY_INCOMPLETE |
| 97795 | block4 | block4_w028 | 46 | 0.022989 | 9.0 | 19536.0 | 12.0 | SEVERELY_INCOMPLETE |

## 97795/block4

The final 97795/block4 window is independently marked `SEVERELY_INCOMPLETE`: it has 46 DLL frames and an approximately 19.8 s end gap inside the guarded 20 s window. The preceding affected tail window is also classified by the same frozen boundary rule. No Python-time backfill, synthetic timestamp, padding, or HR-based exclusion is applied.

## Decision

This is a denominator sensitivity contract, not an algorithm improvement claim. The primary all-window DLL-time results remain the full 335-window results; S0/S1/S2 are reported separately after this contract is frozen.
