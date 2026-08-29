# Formal BB V1 migration notes

The old BBB output and the accepted 70-session canonical probe asset remain provenance/reference inputs only. They must not be supplied to the V1 producer and are not relabeled as current 44-session results.

For local migration, first freeze a session manifest from the current raw BB source files and attach the approved `anonymous_participant_group_id` map. Keep one manifest row per session/Block/file, record exclusions rather than deleting rows, and make `sub-9504` explicit either in the manifest or the frozen configuration. Then run one or two sessions into a new output directory, compare raw trial counts and half-open window boundaries, and only after the smoke gate passes run the frozen full manifest. Never change window, RT, opportunity, or feature-selection settings after inspecting the outcome direction.

Downstream code that expects the existing 12 probe features can initially read the compatibility aliases in `window_metrics.csv`. New code should migrate to the explicit canonical names and use opportunity/status fields. Block/session consumers should read those same canonical metric names rather than copying probe-window aliases. Q1 remains nominal four-class and Q2 remains ordered four-level; neither is a focus-total score.

For prediction, generate `GroupKFold` assignments from `anonymous_participant_group_id`. All sessions in one anonymous group must use one fold. Within each fold, fit missing-value handling, scaling, feature selection, and the estimator on training rows only; transform the held-out fold afterward. Save fold assignments and fitted configuration provenance locally with the run manifest.
