# BIOPAC corrected-gate robustness audit

## Scope and paired design

Eight 60-s BIOPAC/ECG-RSP windows were re-evaluated with the same v3.1.1 inputs and logic. The only changed argument was the target-search spacing/gate: historical 0.08 m/bin versus formal 0.037 m/bin (physical 0.30–1.50 m = bins 9–40). The selected windows provide two HR-good, two HR-poor, two BR-good and two BR-poor examples; windows are labeled by the historical reference error used for sampling.

The historical 5-session/99-window HR-course result (~4.61 bpm in the prior report; current strict reference table reports 4.59 bpm) was not recomputed here. The table below is an 8-window paired robustness sample, not a replacement denominator.

## Paired results

- Paired windows: **8**; all pairs have both variants.
- Category coverage: HR_GOOD=2, HR_POOR=2, BR_GOOD=2, BR_POOR=2.
- Heart target bin changed: **2/8 (25.0%)**; heart channel changed: **2/8 (25.0%)**.
- Breath target bin changed: **3/8 (37.5%)**; breath channel changed: **2/8 (25.0%)**.

| role | old/new heart bin | old/new heart ch | old/new HR course | old/new BR |
|---|---:|---:|---:|---:|
| hr_good | 14 / 14 | 4 / 4 | 76.2 / 76.2 | 20.8 / 20.8 |
| hr_poor | 11 / 11 | 7 / 7 | 81.3 / 81.3 | 18.2 / 18.2 |
| br_good | 15 / 15 | 4 / 4 | 75.6 / 75.6 | 22.3 / 11.7 |
| br_poor | 9 / 9 | 1 / 1 | 68.6 / 68.6 | 21.8 / 21.8 |
| hr_good_2 | 8 / 23 | 4 / 7 | 86.8 / 74.4 | 9.3 / 7.2 |
| hr_poor_2 | 10 / 10 | 6 / 6 | 64.6 / 64.6 | 7.1 / 11.1 |
| br_good_2 | 10 / 10 | 1 / 1 | 77.9 / 77.9 | 8.9 / 8.9 |
| br_poor_2 | 17 / 21 | 5 / 4 | 80.9 / 83.5 | 8.5 / 8.5 |

### HR course

Historical MAE=12.128 bpm; corrected MAE=13.353 bpm; median AE 11.902->14.756; bias -11.903->-13.128. Because corrected-gate output changes occur in the sample and the original 99-window denominator was not rerun, final status is **STILL_PARTIAL**. The sample does not support discarding the historical result, but it does not close a robustness proof for ~4.61 bpm.

### BR

Historical MAE=6.987 bpm; corrected MAE=5.424 bpm; median AE 5.782->4.134; bias -3.633->-4.721. The corrected gate changes some breath candidates/outputs and leaves others unchanged; with this non-full denominator the final status is **STILL_PARTIAL**.

## Formal-distance context (not rerun here)

The previously closed formal QC remains: 71 mmWave sessions, old PASS=35, corrected PASS=49, transitions PASS→PASS=33, PASS→FAIL=2, FAIL→PASS=16, FAIL→FAIL=20. The canonical mainline denominator remains 70 sessions. This audit does not change target-lock outputs or rerun formal physiology.

## Interpretation

- No window in this paired sample establishes a new `CONFIRMED_AFFECTED` formal result; the evidence is a calibration robustness issue only.
- The historical HR-course ~4.61 bpm result may be retained as a historical calibration result with a distance-gate caveat; it is not re-certified as distance-robust by this 8-window sample.
- BR remains provisional (`STILL_PARTIAL`) for the same reason.
- No formal 70/71-session HR/BR/task-dynamics rerun is indicated solely by this audit; a future decision to close calibration robustness would require the same paired procedure on the original common-window denominator.
