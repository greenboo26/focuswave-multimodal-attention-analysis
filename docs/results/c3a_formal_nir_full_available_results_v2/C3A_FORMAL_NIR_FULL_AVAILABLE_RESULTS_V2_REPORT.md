# C3A_FORMAL_NIR_FULL_AVAILABLE_RESULTS_V2

## Outcome

The formal directory is the authoritative entry point. It contains 73 run directories for 72 unique formal subjects; 69 have completed yolo8 session-level eyes/frames/summary results, while only 20 currently include the pre-existing fullclass per-frame ROI/QC dynamic asset required by the frozen C3A QC rule.

## Coverage and linkage

65 unique formal sessions deterministically link to a retained real-person formal experiment session and canonical timeline. 72 unique formal sessions have a complete current 10/30/60 s canonical probe timeline. 7 fail the real-person identity/session gate. Among linked sessions, 47 lack an existing fullclass dynamic asset or cannot be aligned; this is an asset-availability limit, not a video review result.

|   window_s |   linked_canonical_probe |   dynamic_exact_onset_probe |   primary_qc_probe |   repeat_participant_n |   median_valid_frame_rate |
|-----------:|-------------------------:|----------------------------:|-------------------:|-----------------------:|--------------------------:|
|         10 |                     1300 |                         360 |                237 |                     14 |                  0.946844 |
|         30 |                     1300 |                         360 |                234 |                     14 |                  0.949445 |
|         60 |                     1300 |                         360 |                221 |                     14 |                  0.948333 |

## Fixed model results

|   window_s | model           | status   |   n_probe |   n_participant |   positive_n |   oof_auc |   balanced_accuracy_0_5 |
|-----------:|:----------------|:---------|----------:|----------------:|-------------:|----------:|------------------------:|
|         10 | C+B             | eligible |       237 |              14 |           71 |  0.625064 |                0.569871 |
|         10 | C+B+NIR_dynamic | eligible |       237 |              14 |           71 |  0.584507 |                0.576913 |
|         30 | C+B             | eligible |       234 |              14 |           69 |  0.696882 |                0.667194 |
|         30 | C+B+NIR_dynamic | eligible |       234 |              14 |           69 |  0.648661 |                0.603162 |
|         60 | C+B             | eligible |       221 |              14 |           68 |  0.694252 |                0.670752 |
|         60 | C+B+NIR_dynamic | eligible |       221 |              14 |           68 |  0.670896 |                0.602124 |

## Paired participant bootstrap

|   window_s | comparison                |   n_probe |   n_participant |   delta_auc |   ci95_low |   ci95_high |   valid_bootstraps |
|-----------:|:--------------------------|----------:|----------------:|------------:|-----------:|------------:|-------------------:|
|         10 | C+B+NIR_dynamic minus C+B |       237 |              14 |  -0.0405566 |  -0.113483 |   0.0148705 |               2000 |
|         30 | C+B+NIR_dynamic minus C+B |       234 |              14 |  -0.0482213 |  -0.133682 |   0.0118385 |               2000 |
|         60 | C+B+NIR_dynamic minus C+B |       221 |              14 |  -0.0233564 |  -0.101123 |   0.0214364 |               2000 |

## Why v1 was a subset

The v1 C3A script entered through `c3_identity_coverage_crosswalk_v1`, a 17-session legacy crosswalk, then required a pre-existing fullclass dynamic CSV and therefore analysed 15 sessions / 12 repeat participants after its additional eligibility gates. That crosswalk is retained as OLD_SUBSET/preliminary evidence and is not used as the v2 coverage authority. V2 inventories all formal result directories first, uses `subject_session_master_v2.csv` plus the current canonical probe timeline for deterministic linkage, and separately reports session-level availability versus fullclass-dynamic model eligibility.

## Limits

No raw NIR video was opened or rerun. `eyes.csv/frames.csv/summary.json` establish completed session-level processing but cannot satisfy the frozen fullclass normalization/pupil-fit QC rule by themselves; those sessions are counted in availability but excluded from the C3A dynamic model until an already-authorized upstream fullclass result exists. All identity keys, run directories, probe timestamps, row-level features and OOF predictions remain local only. NIR is a visual physiological reference signal, not attention ground truth.
