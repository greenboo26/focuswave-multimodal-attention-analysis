# Derived data contract v1

## Frozen common key

The canonical Probe row key is `(site, single_experiment_id or session_id, probe_id)`. Participant grouping is `repeat_participant_id`; `subject` is a recording/session identifier and must not be silently treated as a person identifier. Absolute onset timestamps use Unix milliseconds. Window boundaries are explicit, usually `[probe_onset - window_s, probe_onset)`.

## Required shared fields

`site`, `phase`, `program_family`, `block`, `probe_id`, `probe_onset_unix_ms`, `label`, `vigilance_label`, `repeat_participant_id`, `identity_status`, `qc_flag`, `backend`, `schema_version`, `source_run_id`.

Existing tables may retain legacy names. Export adapters must map, for example, `probe_onset_ms_mmw`, `probe_onset_ms_nir`, and `probe_onset_unix_ms` into the contract after unit and timezone checks. `identity_status=unresolved` cannot enter participant-level LOSO or repeated-measures claims. `qc_flag` records pass/uncertain/reject provenance; it is not permission to delete rows silently.
