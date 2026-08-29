# Issue #25 — controlled 20 s versus historical 60 s HR comparison

状态：`PARTIAL / DIAGNOSTIC_ONLY`; formal window validity remains `UNRESOLVED`

本报告只解决窗口来源与 formal validity 证据，不把短窗或长窗结果升级为 validated physiology。窗口长度在读取结果前预先固定为 20 s 与 trailing 60 s；没有按 MAE、相关或 coverage 选择长度。

## 1. Direct conclusion

- 20 s 首次进入当前证据链的来源是 commit `472735b6b6af5f98e92ab7815718e81863cb6098` 的 `scripts/maintenance/run_mmwave_targeted_validation_20260830.py`；目的为 block-local target continuity / ECG-aligned bounded diagnostic，非 HR formal window validation。
- 历史 60 s 的真实 semantics 来自 `64634159d226ee1ed892d53e56fcf3697fbff9b8` 上的 `scripts/maintenance/run_hr_course_99_corrected.py` 与 `scripts/maintenance/build_hr_course_99_audit.py`：先以首 6000 frames 固定 target，再用 v3.1.1 的 HR course（25 s internal window、5 s step）对每个 60 s probe window 的 course points 做 `(t > onset-60) & (t <= onset)` median。
- 当前受控比较使用同一 historical fixed target、同一 v3.1.1 bandpass/periodogram/peak/course chain、同一 block marker affine ECG alignment 和 DLL timestamp column 3；只改变 trailing window length。
- 结论等级为 `UNRESOLVED`：本轮可提供 3 个 targeted sessions / complete blocks 的 diagnostic window-length evidence，但不足以把 20 s 或 60 s 宣称为 formal HR validity window。

## 2. Pre-registered comparison contract

- Pair endpoints start at `block_start + 5 s + 60 s`, then advance by 10 s until `block_end - 5 s`; each endpoint has `[end-20 s, end]` and `[end-60 s, end]`. Thus both windows remain inside the same complete block and the same 5 s boundary guard.
- Target is fixed before window comparison from the historical corrected-gate selection artifact; no per-window target selection, no parameter sweep and no result-based length choice.
- ECG_VALID is the #24 eligibility adapter, not the old targeted-validation status field: 0.5–40 Hz third-order SOS, fixed 0.30 s R-peak distance and prominence 0.25, 300–2000 ms IBI, adjacent-IBI change >20% rejection, valid-beat coverage ≥80%, and ≥3 valid IBI. The #24 aggregate is 325 valid / 10 invalid / 0 unresolved out of 335.
- A pair enters metric calculations only when both the 20 s and trailing 60 s references independently pass that same ECG_VALID rule. Marker mismatch is retained as a warning when block-local affine mapping is available; it is not an independent ECG_INVALID cause.
- `coverage_fraction` is timestamp-only frame coverage using the block-local DLL interval median; `signal_usable_ratio` is the existing v3.1.1 internal 10 s signal gate ratio. Neither was used to choose the preferred length.

## 3. Frequency resolution, coverage and metrics

| window | pair-grid n | ECG_VALID pair n | estimator valid n | metric n | mean coverage | median coverage | frequency resolution | MAE | median AE | bias (est−ECG) | Pearson r | Spearman r |
|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 20 s | 303 | 283 | 303 | 283 | 0.655511 | 0.691708 | 0.05 Hz / 3.0 bpm | 14.703129 | 14.514286 | -12.59812 | 0.278024 | 0.268721 |
| 60 s | 303 | 283 | 303 | 283 | 0.656046 | 0.691986 | 0.016666667 Hz / 1.0 bpm | 5.608574 | 4.083467 | -3.630629 | 0.379439 | 0.399861 |

Exact paired error contrast (20 s AE − 60 s AE): common n=283, mean=9.094555, median=7.4, 20 s better=74, ties=1, 60 s better=208. This is descriptive and not a formal superiority test.

The nominal periodogram bin spacing is `FS/N`: 20 s = 0.05 Hz = 3 bpm and 60 s = 0.016666667 Hz = 1 bpm. Per-window values are retained because DLL-time coverage can make observed N differ from nominal duration.

## 4. Historical dependency chain

- Filter: existing v3.1.1 4th-order SOS cardiac bandpass, 0.8–2.0 Hz (48–120 bpm).
- PSD/spectral estimate: existing Hann-window periodogram with no new zero-padding or interpolation contract.
- Peak estimate: existing adaptive-prominence `detect_peaks_heart_lo`, minimum distance and IBI validity rules; then existing segment correction, consensus and `estimate_hr_time_course` fusion.
- Producer constraint: stored input is the existing 8-channel complex range-domain NPZ; no raw ADC/range FFT, firmware, channel calibration, target algorithm or producer code was changed.
- Historical corrected target constraint: 0.037 m/bin, physical gate 0.30–1.50 m (bins 9–40), first-6000-frame selection then forced target for the full comparison. The current comparison reuses the target, but does not claim that current selection was independently rerun with that gate.

## 5. Validity boundary and reuse rejection

- Reused: `run_mmwave_estimator_same_window_audit_20260830.py`, its `historical_20s_adaptation` helper, `run_mmwave_targeted_validation_20260830.py` `PartReader`/DLL-time block mapping, `gold_standard_qa.py::ecg_qa` as the #24 adapter implementation, historical selection artifacts and #24 aggregate eligibility evidence.
- #24 dependency source: `issue24_isolated_worktree_aggregate`; lineage commit `d2d09f8ac502600d3a1241e33c429bd53756fa45`; manifest repo-relative path `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_ELIGIBILITY_MANIFEST.json`; committed manifest SHA-256 `0806cb4f0e477788ee7cd604e3d04c811654fb692f2840767249982ebc5ba258`; materialized read-only manifest `C:\Users\550ACW\.codex\worktrees\0ce8\08_算法\docs\results\2026-08-30_MMWAVE_TARGETED_VALIDATION\ECG_ELIGIBILITY_MANIFEST.json` SHA-256 `7a32f16b41ab78507fc16bd2ec5fa2307643b689f782d771433a151ddd2f7023`; issue24 run `ecg_eligibility_dll_20260829T220533Z`; issue24 HEAD `805db1d3f2d701d46f678b7cd911990f779a4966`. The current run independently reapplies the adapter to both durations; it does not substitute `ecg_status == valid`.
- `REUSE_REJECTION_REASON`: the existing same-window audit only has the frozen 335-row 20 s denominator and deliberately marks strict historical 60 s as `NOT_APPLICABLE_TO_20S`; it does not construct 60 s DLL-time windows or compute the paired 60 s ECG_VALID reference. A minimal new execution wrapper was therefore required.
- The result remains diagnostic/UNRESOLVED because the targeted set is not the full formal cohort, `97795` retains the documented `.acq` filename provenance limitation, and DLL-time frame coverage/timestamp provenance remains a validity limitation. No formal promotion is made.

## 6. Execution and artifacts

- RUN_ID: `issue25_window_length_20260830`
- Canonical HEAD at execution: `805db1d3f2d701d46f678b7cd911990f779a4966`; origin/main: `805db1d3f2d701d46f678b7cd911990f779a4966	refs/heads/main`
- Input raw roots: `D:\acq_mmwave_data`; selected subjects: `97793, 9779, 97795`; source rows: 303 paired endpoints.
- Script output: `MMWAVE_WINDOW_LENGTH_COMPARISON.csv`, `MMWAVE_WINDOW_LENGTH_METRICS.csv`, `MMWAVE_WINDOW_LENGTH_BLOCK_AUDIT.csv`, `MMWAVE_WINDOW_LENGTH_COMPARISON_REPORT_2026-08-30.md`, `MMWAVE_WINDOW_LENGTH_COMPARISON_MANIFEST.json`.
- Excluded: C2B/C2C, Issue #16, HRV, NIR/RGB, firmware, portable V2, raw mutation, producer modification and full formal batch.

## 7. Block audit

| subject | block | pair-grid n | marker sequence exact | ECG fit p95 ms | DLL median interval ms |
|---|---|---:|---|---:|---:|
| 97793 | block1 | 53 | False | 2.666327 | 8.0 |
| 97793 | block2 | 50 | True | 1.987523 | 7.0 |
| 9779 | block1 | 52 | True | 2.243542 | 7.0 |
| 9779 | block2 | 52 | True | 2.180602 | 7.0 |
| 97795 | block1 | 24 | True | 2.952014 | 5.0 |
| 97795 | block2 | 24 | True | 2.079016 | 6.0 |
| 97795 | block3 | 24 | True | 2.348056 | 6.0 |
| 97795 | block4 | 24 | True | 2.378192 | 6.0 |
