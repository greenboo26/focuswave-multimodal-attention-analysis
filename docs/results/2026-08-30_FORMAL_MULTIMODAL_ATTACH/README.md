# Formal multimodal mother-table attach audit — 2026-08-30

Status: **PARTIAL**.

This evidence package records the current mother-table attach and merge-readiness audit. It does not contain participant/probe-level CSVs, raw videos, raw Parquet, or model outputs. The row-level deliverables remain local-only at:

`C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave\outputs\FocusWave_formal_multimodal_v2_2026-08-30`

## Scope and frozen semantics

- Existing mother table reused: `D:\Project\厚粲杯\11_数据\derived\analysis_tables_v1\subject_session_master.csv` — 179 sessions, 112 repeat participants.
- Current explicit mapping evidence: `D:\Project\厚粲杯\11_数据\derived\analysis_tables_v2\subject_session_master_v2.csv` `j_source_folder` — 72 sessions, 46 repeat participants. `single_experiment_id` and `session_id` remain separate fields.
- Canonical probe key: `repeat_participant_id, session_id, block_id, probe_id, window_name`.
- Frozen primary window: `pre_30s = [probe_onset_unix_ms-30000, probe_onset_unix_ms)`; formal behavior `master_timeline.csv` supplies block boundaries and real Unix milliseconds.
- Current timeline: 1,440 probes from 72 current J sessions; every session has two formal blocks and 20 valid probe onsets.

## Coverage and V2 audit

| table | rows | sessions | groups | observed rows | status |
|---|---:|---:|---:|---:|---|
| behavior probe merge-ready | 1,440 | 72 | 46 | 1,440 | PASS |
| NIR probe merge-ready | 1,440 | 72 | 46 | 1,295 | PARTIAL |
| RGB probe merge-ready | 1,440 | 72 | 46 | 1,420 | PARTIAL |
| fully matched candidate | 1,295 | 72 | 46 | 1,295 | candidate only |

The portable V2 validator was run from `Attention-Analysis` commit `21c7da4fe2e03d853f0b6391d580334526f86ce3`. All three modality tables passed non-null/unique canonical-key validation. Both portable outer and inner merges returned 1,440 rows. This is a structural merge-ready PASS, not a claim that every modality feature is available or scientifically validated.

NIR used the existing fullclass formal producer root with 65/65 `completion.json` records complete; it aggregated real `unix_ms` and retained QC/missingness. NIR missingness is 145 probe rows: seven sessions without current producer output plus five `sub-083` block-1 windows without eye-metric rows. No PIR-primary feature was used.

RGB used existing raw Parquet only. The postprocessing produced primary-face-rank, eyelid geometry, native blink-probability transition candidates, pose, head-motion and global-motion fields. PERCLOS was intentionally not produced. RGB missingness is 20 probe rows from `sub-099`.

mmWave remains a reserve interface: HR/BR/RR HOLD, HRV/IBI EXCLUDE, continuity/phase/motion diagnostic HOLD, and missing/loadability structural ALLOW. It is not attached as a predictor in this package.

## Local evidence files

The local-only package contains `current_cohort_manifest.csv`, `repeat_registry.csv`, `session_id_mapping.csv`, `canonical_probe_timeline.csv`, the three modality merge-ready tables, `modality_coverage_missingness_audit.csv`, `fully_matched_candidate.csv`, `producer_output_index.csv`, `artifact_index.csv`, and the JSON/Markdown audit reports. Their hashes and row/column counts are in the local `artifact_index.csv`; aggregate schema and validator evidence are mirrored here without row-level data.

No NIR/RGB producer was rerun. No model was trained. No raw or large producer artifact was uploaded.
