# Formal BB V1 migration notes

The old BBB output and the accepted 70-session canonical probe asset remain provenance/reference inputs only. They must not be supplied to the V1 producer and are not relabeled as current 44-session results.

For local migration, first freeze a session manifest from the current raw BB source files and attach the approved `anonymous_participant_group_id` map. Keep one manifest row per session/Block/file, record exclusions rather than deleting rows, and make `sub-9504` explicit either in the manifest or the frozen configuration. Then run one or two sessions into a new output directory, compare raw trial counts and half-open window boundaries, and only after the smoke gate passes run the frozen full manifest. Never change window, RT, opportunity, or feature-selection settings after inspecting the outcome direction.

Downstream code that expects the existing 12 probe features can initially read the compatibility aliases in `window_metrics.csv`. New code should migrate to the explicit canonical names and use opportunity/status fields. Block/session consumers should read those same canonical metric names rather than copying probe-window aliases. Q1 remains nominal four-class and Q2 remains ordered four-level; neither is a focus-total score.

For prediction, generate `GroupKFold` assignments from `anonymous_participant_group_id`. All sessions in one anonymous group must use one fold. Within each fold, fit missing-value handling, scaling, feature selection, and the estimator on training rows only; transform the held-out fold afterward. Save fold assignments and fitted configuration provenance locally with the run manifest.

## Required regeneration after the anchor-exclusion repair

Outputs produced from PR #19 baseline commit `0423beba1813bf81b16d4d7d7e9c7ac4763920e6` must not be reused when a probe row can fall inside its own pre-probe time interval. Regenerate all selected outputs from the same frozen manifest, identity map, and unchanged window configuration. The repaired membership rule is: same session, same Block, left-closed/right-open time interval, `is_probe=0`, and anchor `trial_key` excluded.

The current queue audit target is 44 sessions, 38 current-queue anonymous groups, and six two-session repeat groups, but the producer must derive and record those counts from external inputs. Before the future approximately 72-session run, rebuild the complete anonymous identity mapping and all participant-disjoint folds; the present 38 groups are not a permanent identity namespace.

Local Codex should first run the synthetic regression suite, then an isolated one- or two-session smoke run, verify every probe-window membership against raw trial keys, and only then rebuild the complete frozen manifest into a new output directory. Compare trial/window row counts, opportunity denominators, anchor exclusion, session/Block boundaries, hashes, and statuses. Do not alter 10/20/30-second windows, RT gates, SDT gates, labels, or grouping based on the repaired results.
