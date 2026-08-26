# Legacy producer audit V1

Five local retained producer assets are intentionally not physically moved in this candidate because import/path and local-root dependencies were not proven safe: `run_report_cohort_label_vigilance_v1.py`, `run_final_report_cohort_baseline_v2.py`, `run_q1_questionnaire_criterion_validity.py`, `run_report_repeat_session_effects_v1.py`, and the historical longitudinal/pre-Probe behavior producer family. They are mapped to canonical entrypoints and source refs; the producer files remain on their source branches.

Therefore `unmoved_legacy_producer_count = 5`. This is a deliberate migration boundary, not a missing audit. Any future move requires import graph, path-parameter, output-schema and clean-run verification.
