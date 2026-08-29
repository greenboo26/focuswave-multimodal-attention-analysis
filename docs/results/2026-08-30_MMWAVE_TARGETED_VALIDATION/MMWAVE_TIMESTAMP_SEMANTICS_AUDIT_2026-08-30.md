# mmWave timestamp semantics audit — 2026-08-30

状态：`PARTIAL / SEMANTICS_CLASSIFIED`

## A. Event tick to nearest mmWave timestamp

Rows: 3491; `|nearest delta| > 100 ms`: 730. This is an event Unix-ms versus nearest mmWave timestamp residual. It is not an adjacent frame interval and must not be called a dropout/frame gap.

## B. Adjacent mmWave frame timestamp interval

Rows: 459126; median 7.000 ms; p95 20.000 ms; p99 31.000 ms; max 6495 ms.

Threshold counts: >20 ms 20682; >50 ms 840; >100 ms 457; >500 ms 457.

## Interpretation

The historical 730-like count is A: 730 event-to-nearest residuals. Only B can establish a true adjacent-frame gap; the complete B table and per-session summaries are recorded in `mmwave_frame_interval_audit.csv`.

## Source semantics

The mmWave timestamp Unix-ms column is read from the existing session `*_mmwave_timestamps.csv`; the acquisition program writes the mmWave frame timestamp alongside captured frames. No timestamp producer or raw file was changed in this audit.
