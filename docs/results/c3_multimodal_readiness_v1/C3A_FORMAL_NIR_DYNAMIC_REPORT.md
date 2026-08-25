# C3A formal NIR dynamic increment

## Formal-asset inventory

The formal NIR directory was read without opening raw video. Fullclass ROI/QC dynamic CSVs were available for 15 identity-eligible formal sessions; each supplies per-frame Unix ms, eye/ROI clipping state, pupil fit and normalization validity, pupil-to-iris ratio, ocular aperture ratio, and pupil confidence. The requested GitHub handoff commit was not in this local clone object database, so its user-provided hash is recorded but not represented as locally verified.

## Coverage and fixed QC

|   window_s |   canonical_identity_resolved_probe |   formal_fullclass_exact_onset_probe |   primary_qc_probe |   participant_n |   median_valid_frame_rate |
|-----------:|------------------------------------:|-------------------------------------:|-------------------:|----------------:|--------------------------:|
|         10 |                                 320 |                                  300 |                195 |              12 |                  0.943333 |
|         30 |                                 320 |                                  300 |                193 |              12 |                  0.946667 |
|         60 |                                 320 |                                  300 |                182 |              12 |                  0.945293 |

Primary QC was frozen before modelling: at least 80% valid (un-clipped, normalized, fitted) frames over the exact probe-before window. 10/30/60 s are fixed windows; 30 s is the primary window, while 10/60 s are sensitivity analyses.

## Incremental models

|   window_s | model           | status   |   n_probe |   n_participant |   positive_n |   oof_auc |   balanced_accuracy_0_5 |
|-----------:|:----------------|:---------|----------:|----------------:|-------------:|----------:|------------------------:|
|         10 | C+B             | eligible |       195 |              12 |           58 |  0.65039  |                0.592374 |
|         10 | C+B+NIR_dynamic | eligible |       195 |              12 |           58 |  0.655172 |                0.611628 |
|         30 | C+B             | eligible |       193 |              12 |           56 |  0.69695  |                0.648266 |
|         30 | C+B+NIR_dynamic | eligible |       193 |              12 |           56 |  0.707117 |                0.652307 |
|         60 | C+B             | eligible |       182 |              12 |           55 |  0.721832 |                0.656764 |
|         60 | C+B+NIR_dynamic | eligible |       182 |              12 |           55 |  0.716679 |                0.649177 |

## Paired repeat-participant bootstrap

|   window_s | comparison                |   n_probe |   n_participant |   delta_auc |   ci95_low |   ci95_high |   valid_bootstraps |
|-----------:|:--------------------------|----------:|----------------:|------------:|-----------:|------------:|-------------------:|
|         10 | C+B+NIR_dynamic minus C+B |       195 |              12 |  0.00478228 |  -0.127428 |   0.0566133 |               2000 |
|         30 | C+B+NIR_dynamic minus C+B |       193 |              12 |  0.0101668  |  -0.140856 |   0.0665976 |               2000 |
|         60 | C+B+NIR_dynamic minus C+B |       182 |              12 | -0.0051539  |  -0.157596 |   0.0523597 |               2000 |

## Scope boundary

No raw NIR video was read or rerun. HbO/HbR time series are not present in the formal asset schema, so no haemodynamic claim is made. Row-level values, identities, session keys and OOF predictions remain only in the local derived output. RGB/C3B is not started.
