from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipelines.behavior.behavior_science_v3.pipeline import (
    AnalysisConfig,
    aggregate_behavior_metrics,
    build_b1_b2_pairs,
    build_correlation_evidence,
    build_participant_disjoint_folds,
    build_probe_analysis_tables,
    candidate_decision_table,
    prepare_error_trajectories,
    q2_gate,
    qc_denominator_table,
    run_formal_analysis,
)


def synthetic_tables() -> dict[str, pd.DataFrame]:
    trial_rows = []
    for session, cluster, order in [
        ("synthetic-session-a1", "synthetic-cluster-a", 1),
        ("synthetic-session-a2", "synthetic-cluster-a", 2),
        ("synthetic-session-b1", "synthetic-cluster-b", 1),
        ("synthetic-session-c1", "synthetic-cluster-c", 1),
    ]:
        for block_i, block in enumerate(["B1", "B2"]):
            base = 1000 * (1 + block_i)
            for i in range(8):
                is_no_go = int(i in {3, 7})
                omission = int(not is_no_go and i == 5)
                commission = int(is_no_go and i == 3)
                correct = int(not omission and not commission)
                trial_rows.append({
                    "session_id": session,
                    "participant_cluster_ref": cluster,
                    "session_order": order,
                    "block_id": block,
                    "trial_num": i + 1,
                    "trial_time_s": base + i,
                    "is_no_go": is_no_go,
                    "response": "space" if (not is_no_go and not omission) or commission else "",
                    "rt": 300 + i * 10 if not is_no_go and not omission else np.nan,
                    "correct": correct,
                    "omission": omission,
                    "commission": commission,
                })
    trial = pd.DataFrame(trial_rows)

    windows = []
    q_levels = [1, 2, 3, 4]
    q2_levels = [1, 2, 3, 4]
    probe_index = 0
    for session, cluster in [
        ("synthetic-session-a1", "synthetic-cluster-a"),
        ("synthetic-session-a2", "synthetic-cluster-a"),
        ("synthetic-session-b1", "synthetic-cluster-b"),
        ("synthetic-session-c1", "synthetic-cluster-c"),
    ]:
        event = f"synthetic-event-{probe_index}"
        for window_s in [10, 20, 30]:
            windows.append({
                "synthetic_or_authorized_event_id": event,
                "session_id": session,
                "participant_cluster_ref": cluster,
                "block_id": "B2",
                "window_type": "probe_preceding_seconds",
                "window_seconds_nominal": window_s,
                "q1_nominal_4class": q_levels[probe_index],
                "q2_ordinal_4level": q2_levels[probe_index],
                "go_correct_rt_mean_ms": 320 + probe_index * 5 + window_s / 10,
                "go_correct_rt_median_ms": 315 + probe_index * 5 + window_s / 10,
                "go_correct_rt_sd_ms": 25 + probe_index,
                "go_correct_rt_mad_ms": 18 + probe_index,
                "go_correct_rt_iqr_ms": 30 + probe_index,
                "go_correct_rt_cv": .08 + probe_index * .01,
                "go_correct_rt_theilsen_slope_ms_per_s": .5 + probe_index * .1,
                "omission_rate": .05 + probe_index * .01,
                "commission_rate": .10 + probe_index * .01,
                "dprime_loglinear": 1.5 - probe_index * .1,
                "criterion_c": .1 + probe_index * .02,
                "beta": 1.0 + probe_index * .05,
            })
        probe_index += 1
    window = pd.DataFrame(windows)

    block_rows = []
    session_rows = []
    for session, cluster, order in [
        ("synthetic-session-a1", "synthetic-cluster-a", 1),
        ("synthetic-session-a2", "synthetic-cluster-a", 2),
        ("synthetic-session-b1", "synthetic-cluster-b", 1),
        ("synthetic-session-c1", "synthetic-cluster-c", 1),
    ]:
        per_session = trial[trial.session_id.eq(session)]
        sm = aggregate_behavior_metrics(per_session)
        session_rows.append({"session_id": session, "participant_cluster_ref": cluster,
                             "session_order": order, **sm, "accuracy": 1 - (sm["omission_rate"] + sm["commission_rate"]) / 2,
                             "error_rate": (sm["omission_rate"] + sm["commission_rate"]) / 2})
        for block in ["B1", "B2"]:
            bm = aggregate_behavior_metrics(per_session[per_session.block_id.eq(block)])
            block_rows.append({"session_id": session, "participant_cluster_ref": cluster,
                               "session_order": order, "block_id": block, **bm})
    block = pd.DataFrame(block_rows)
    session = pd.DataFrame(session_rows)

    trajectory = pd.DataFrame([
        {"session_id": "synthetic-session-a1", "participant_cluster_ref": "synthetic-cluster-a",
         "error_event_key": "synthetic-error-1", "error_type": "commission", "trial_offset": -1,
         "target_trial_key": "synthetic-t1", "go_correct_rt_ms": 300.0},
        {"session_id": "synthetic-session-a1", "participant_cluster_ref": "synthetic-cluster-a",
         "error_event_key": "synthetic-error-1", "error_type": "commission", "trial_offset": 1,
         "target_trial_key": "synthetic-shared", "go_correct_rt_ms": 340.0},
        {"session_id": "synthetic-session-a1", "participant_cluster_ref": "synthetic-cluster-a",
         "error_event_key": "synthetic-error-2", "error_type": "omission", "trial_offset": -1,
         "target_trial_key": "synthetic-shared", "go_correct_rt_ms": 340.0},
        {"session_id": "synthetic-session-a1", "participant_cluster_ref": "synthetic-cluster-a",
         "error_event_key": "synthetic-error-2", "error_type": "omission", "trial_offset": 1,
         "target_trial_key": "synthetic-t2", "go_correct_rt_ms": 360.0},
        {"session_id": "synthetic-session-b1", "participant_cluster_ref": "synthetic-cluster-b",
         "error_event_key": "synthetic-error-3", "error_type": "commission", "trial_offset": -1,
         "target_trial_key": "synthetic-t3", "go_correct_rt_ms": 310.0},
        {"session_id": "synthetic-session-b1", "participant_cluster_ref": "synthetic-cluster-b",
         "error_event_key": "synthetic-error-3", "error_type": "commission", "trial_offset": 1,
         "target_trial_key": "synthetic-t4", "go_correct_rt_ms": 350.0},
    ])
    return {"trial": trial, "window": window, "block": block, "session": session, "trajectory": trajectory}


def test_metrics_keep_go_omission_and_nogo_commission_separate():
    d = synthetic_tables()["trial"].head(8)
    result = aggregate_behavior_metrics(d)
    assert result["omission_denominator"] == 6
    assert result["commission_denominator"] == 2
    assert result["omission_numerator"] == 1
    assert result["commission_numerator"] == 1
    assert "correct_rate" not in result
    for metric in ["go_correct_rt_mean_ms", "go_correct_rt_median_ms", "go_correct_rt_sd_ms",
                   "go_correct_rt_mad_ms", "go_correct_rt_iqr_ms", "go_correct_rt_cv",
                   "go_correct_rt_theilsen_slope_ms_per_s", "dprime_loglinear", "criterion_c", "beta"]:
        assert metric in result


def test_probe_primary_is_one_event_row_and_sensitivity_is_not_independent_sample():
    t = synthetic_tables()
    primary, sensitivity = build_probe_analysis_tables(t["window"])
    assert len(primary) == 4
    assert primary.synthetic_or_authorized_event_id.is_unique
    assert set(primary.window_seconds_nominal) == {30}
    assert len(sensitivity) == 12
    assert set(sensitivity.window_seconds_nominal) == {10, 20, 30}
    assert not sensitivity.formal_independent_sample.any()


def test_b1_b2_pairing_is_session_internal_and_repeat_order_is_explicit():
    t = synthetic_tables()
    pairs, failures = build_b1_b2_pairs(t["block"])
    assert not pairs.empty
    assert set(pairs.pair_status) == {"ok_session_internal"}
    assert pairs.groupby(["session_id", "metric"]).size().eq(1).all()
    assert not failures.status.astype(str).str.contains("missing_explicit_session_order").any() if not failures.empty else True

    without_order = t["block"].drop(columns="session_order")
    _, failures2 = build_b1_b2_pairs(without_order)
    assert failures2.status.astype(str).str.contains("missing_explicit_session_order").any()


def test_error_overlap_is_audited_deduplicated_and_centered():
    t = synthetic_tables()
    resolved, overlap = prepare_error_trajectories(t["trajectory"])
    assert not overlap.empty
    shared = resolved[resolved.target_trial_key.eq("synthetic-shared")]
    assert len(shared) == 1
    assert shared.overlap_resolved.all()
    assert "within_participant_centered_rt_ms" in resolved
    assert "relative_to_pre_error_baseline_rt_ms" in resolved
    assert set(resolved.baseline_status).issubset({"available", "missing_pre_error_baseline"})


def test_q2_is_fail_closed_and_prediction_is_participant_disjoint():
    t = synthetic_tables()
    primary, _ = build_probe_analysis_tables(t["window"])
    desc, failures = q2_gate(primary)
    assert not desc.empty
    assert set(desc.analysis_status) == {"descriptive_only"}
    assert failures.iloc[0].status == "blocked_formal_inference"
    assert failures.iloc[0].formal_inference is False or failures.iloc[0].formal_inference == False

    folds = build_participant_disjoint_folds(primary, 3)
    check = folds.groupby("participant_cluster_ref").fold_id.nunique()
    assert check.eq(1).all()


def test_correlation_types_and_candidate_decisions_have_scientific_boundaries():
    t = synthetic_tables()
    corr = build_correlation_evidence(t["session"])
    rt_pair = corr[(corr.metric_a.eq("go_correct_rt_mean_ms")) & (corr.metric_b.eq("go_correct_rt_median_ms"))]
    assert not rt_pair.empty
    assert rt_pair.iloc[0].relation_type == "same_measure_family"
    assert not corr.formal_inference.any()

    decisions = candidate_decision_table(["omission_rate", "commission_rate", "dprime_loglinear"])
    assert {"decision_class", "evidence_source", "rule_version", "review_status", "scientific_boundary"}.issubset(decisions.columns)
    assert (decisions.candidate.eq("Q2_formal_ordinal") & decisions.decision_class.eq("scientific_prohibited")).any()


def test_qc_denominators_separate_levels():
    t = synthetic_tables()
    primary, _ = build_probe_analysis_tables(t["window"])
    qc = qc_denominator_table(t["trial"], primary, t["block"], t["session"])
    assert set(qc.layer) == {"session", "participant_group", "block", "probe", "trial"}
    assert qc.groupby("layer").size().eq(1).all()
    assert qc.observation_unit_zh.notna().all()


def test_end_to_end_v3_writes_failures_figures_and_report_manifest(tmp_path: Path):
    t = synthetic_tables()
    tables = tmp_path / "tables"
    tables.mkdir()
    t["trial"].to_csv(tables / "trial_metrics.csv", index=False)
    t["window"].to_csv(tables / "window_metrics.csv", index=False)
    t["block"].to_csv(tables / "block_metrics.csv", index=False)
    t["session"].to_csv(tables / "session_metrics.csv", index=False)
    t["trajectory"].to_csv(tables / "error_trajectory_metrics.csv", index=False)

    out = tmp_path / "out"
    manifest = run_formal_analysis(tables, out, AnalysisConfig(minimum_model_rows=999))
    assert manifest["schema_version"] == "focuswave-behavior-science-v3"
    assert manifest["go_omission_and_nogo_commission_modeled_separately"] is True
    assert manifest["q2_formal_status"] == "blocked_without_clustered_ordinal_backend"
    assert manifest["cohort_counts_are_runtime_derived_not_hardcoded"] is True
    assert (out / "model_failures_v3.csv").is_file()
    failures = pd.read_csv(out / "model_failures_v3.csv")
    assert not failures.empty
    assert (out / "figure_manifest_v3.csv").is_file()
    assert (out / "行为科学v3结果与准入说明.md").is_file()
    report_manifest = json.loads((out / "report_manifest_v3.json").read_text(encoding="utf-8"))
    assert report_manifest["engineering_validation_is_not_behavioral_validity"] is True
    assert report_manifest["future_identity_remap_required"] is True
