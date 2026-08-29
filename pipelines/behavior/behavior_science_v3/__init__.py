"""FocusWave behavior science v3 formal-analysis entrypoints.

This package consumes already-derived/de-identified behavior tables. It does not
contain cohort identities, raw-data discovery, or formal cohort constants.
"""

from .pipeline import (
    AnalysisConfig,
    aggregate_behavior_metrics,
    build_b1_b2_pairs,
    build_correlation_evidence,
    build_participant_disjoint_folds,
    build_probe_analysis_tables,
    prepare_error_trajectories,
    run_formal_analysis,
)

__all__ = [
    "AnalysisConfig",
    "aggregate_behavior_metrics",
    "build_b1_b2_pairs",
    "build_correlation_evidence",
    "build_participant_disjoint_folds",
    "build_probe_analysis_tables",
    "prepare_error_trajectories",
    "run_formal_analysis",
]
