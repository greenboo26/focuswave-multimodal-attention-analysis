# ECG reference eligibility for DLL-time windows — 2026-08-30

状态：`PARTIAL / ECG_REFERENCE_ELIGIBILITY_COMPLETE`

本报告只冻结 ECG reference eligibility。ECG 规则复用 `scripts/gold_standard_qa.py`；窗口时间到 ECG sample 的映射复用既有 block marker affine mapping。毫米波 ARM0/ARM1/ARM2 估计值固定读取既有 ablation CSV，未重新选择 target/bin/channel，也未用毫米波误差筛选 ECG。

## 1. Eligibility result

- Input windows: `335`; expected: `335`.
- `ECG_VALID`: `325`; `ECG_INVALID`: `10`; `UNRESOLVED`: `0`.
- `ECG_VALID` requires a complete block with usable block-marker affine mapping, at least 3 valid IBI, no rejected interval/artifact reason, and effective valid-beat coverage ≥80%.
- A non-exact marker sequence is retained as a warning when the block affine fit is available; it is not silently converted into a valid/invalid physiology decision.

## 2. Reused ECG rules

- Bandpass: 0.5–40 Hz, third-order SOS.
- R-peak: fixed 0.30 s minimum distance and fixed prominence 0.25.
- IBI plausibility: 300–2000 ms; out-of-range intervals are rejected.
- Artifact rejection: adjacent IBI relative change >20% marks both neighboring intervals as artifact candidates.
- Effective beat coverage: kept valid IBI / raw detected R-peak count ≥80%; no interpolation is introduced.
- Window gate: any out-of-range IBI or >20% adjacent-IBI artifact rejection makes that window `ECG_INVALID`; the reason is kept separately from marker warnings.
- Rest, posture-adjustment, boundary and incomplete-block periods are excluded structurally by the frozen DLL-time block window input.

## 3. Reason distribution

| eligibility | reason | windows |
|---|---|---:|
| ECG_INVALID | abnormal_adjacent_ibi_fluctuation_gt20pct | 10 |
| ECG_VALID | none | 325 |

## 4. ARM0/ARM1/ARM2 on ECG_VALID denominator

这些是固定既有毫米波 estimator 输出在新 ECG_VALID 分母上的描述性重算；它们不改变 estimator、target、gate 或历史 ARM 定义。

| arm | n selected | estimator-valid n | MAE bpm | median AE | RMSE | bias |
|---|---:|---:|---:|---:|---:|---:|
| arm0 | 325 | 325 | 25.005 | 27.917331 | 27.738634 | -24.591623 |
| arm1 | 325 | 304 | 21.906332 | 25.598185 | 25.388652 | -21.17871 |
| arm2 | 325 | 325 | 18.904008 | 20.607575 | 22.406726 | -17.319487 |

## 5. All-window diagnostic

All-window metrics are retained only as diagnostic context. They are not a validity denominator because ECG_INVALID and UNRESOLVED windows remain present and are not converted into evidence of mmWave error.

| arm | n selected | estimator-valid n | MAE bpm | interpretation |
|---|---:|---:|---:|---|
| arm0 | 335 | 335 | 24.847938 | diagnostic_only_not_validity_denominator |
| arm1 | 335 | 314 | 21.77462 | diagnostic_only_not_validity_denominator |
| arm2 | 335 | 335 | 19.040268 | diagnostic_only_not_validity_denominator |

## 6. Block and failure audit

Per-window reject reasons are in the local-only CSV listed in the manifest. Aggregate block evidence is committed in `ECG_ELIGIBILITY_BLOCK_SUMMARY.csv`.

| subject | block | windows | ECG_VALID | ECG_INVALID | UNRESOLVED | marker warning |
|---|---|---:|---:|---:|---:|---:|
| 97793 | block1 | 57 | 55 | 2 | 0 | 57 |
| 97793 | block2 | 54 | 51 | 3 | 0 | 0 |
| 9779 | block1 | 56 | 52 | 4 | 0 | 0 |
| 9779 | block2 | 56 | 55 | 1 | 0 | 0 |
| 97795 | block1 | 28 | 28 | 0 | 0 | 0 |
| 97795 | block2 | 28 | 28 | 0 | 0 | 0 |
| 97795 | block3 | 28 | 28 | 0 | 0 | 0 |
| 97795 | block4 | 28 | 28 | 0 | 0 | 0 |

No execution-level unresolved rows occurred.

## 7. Boundary

This closes the requested ECG eligibility layer for the current 335-window diagnostic comparison. It does not make the 20 s window scientifically canonical, does not validate HR/BR for the formal cohort, and does not open HRV. HR remains `HOLD`; HRV remains `BLOCKED`; #16 remains `PAUSED`.

## 8. Evidence

- `ECG_ELIGIBILITY_REASON_DISTRIBUTION.csv` — committed aggregate reasons.
- `ECG_ELIGIBILITY_BLOCK_SUMMARY.csv` — committed per-block counts and marker warnings.
- `ECG_ARM_METRICS_VALID_DENOMINATOR.csv` — committed ECG_VALID and all-window diagnostic metrics.
- `ECG_ELIGIBILITY_MANIFEST.json` — inputs, hashes, parameters, run ID and local-only row-level output path.
- `work/ecg_eligibility_dll_windows_20260830/ECG_DLL_WINDOW_ELIGIBILITY_LOCAL_ONLY.csv` — local-only per-window evidence with every reject reason.
