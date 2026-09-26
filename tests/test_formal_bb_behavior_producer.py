from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipelines.behavior.formal_bb.group_validation import (
    assert_group_disjoint,
    build_group_kfold_assignments,
    fit_transform_train_only,
)
from pipelines.behavior.formal_bb.producer import _sdt, produce
from tests.fixtures.formal_bb.build_fixture import build


def test_multiscale_producer_and_explicit_pilot_exclusion(tmp_path: Path):
    manifest, identity, config = build(tmp_path / "fixture")
    out = tmp_path / "out"
    run = produce(manifest, identity, config, out)
    assert run["selected_session_count"] == 4
    assert run["selected_participant_group_count"] == 3
    expected = {
        "trial_metrics.csv", "window_metrics.csv", "phase_cycle_metrics.csv",
        "block_metrics.csv", "session_metrics.csv", "error_trajectory_metrics.csv",
        "run_manifest.json",
    }
    assert expected == {p.name for p in out.iterdir()}
    trials = pd.read_csv(out / "trial_metrics.csv")
    windows = pd.read_csv(out / "window_metrics.csv")
    phase_cycle = pd.read_csv(out / "phase_cycle_metrics.csv")
    blocks = pd.read_csv(out / "block_metrics.csv")
    sessions = pd.read_csv(out / "session_metrics.csv")
    assert "sub-9504" not in set(trials.session_id)
    assert trials.trial_key.is_unique
    assert windows.window_key.is_unique
    assert phase_cycle.phase_cycle_key.is_unique
    assert blocks.block_key.is_unique
    assert sessions.session_key.is_unique
    assert set(trials.loc[trials.is_probe.eq(1), "q1_nominal_4class"]) == {1, 2, 3, 4}
    assert set(trials.loc[trials.is_probe.eq(1), "q2_ordinal_4level"]) == {1, 2, 3, 4}
    for column in [
        "trial_count", "rt_mean", "rt_median", "rt_sd", "rt_mad", "rt_cv",
        "rt_slope", "accuracy", "error_count", "error_rate", "omission_count",
        "omission_rate",
    ]:
        assert column in windows.columns
    assert np.isfinite(sessions.dprime_loglinear).all()
    assert set(sessions.sdt_status) == {"ok"}


def test_probe_window_is_left_closed_and_anchor_exclusive(tmp_path: Path):
    manifest, identity, config = build(tmp_path / "fixture")
    out = tmp_path / "out"
    produce(manifest, identity, config, out)
    windows = pd.read_csv(out / "window_metrics.csv")
    probe = windows[(windows.session_id == "syn-001") & (windows.window_type == "probe_preceding_seconds")].iloc[0]
    # Five one-second-spaced trials fall in [anchor-5 s, anchor); the probe trial is excluded.
    assert probe.total_trial_opportunities == 5
    assert probe.window_end_s_exclusive - probe.window_start_s == 5


def test_extreme_proportions_are_finite_and_low_opportunities_are_rejected():
    cfg = {"sdt_min_go_opportunities": 4, "sdt_min_nogo_opportunities": 2}
    perfect = _sdt(8, 8, 0, 4, cfg)
    reverse = _sdt(0, 8, 4, 4, cfg)
    assert perfect["sdt_status"] == reverse["sdt_status"] == "ok"
    assert np.isfinite([perfect["dprime_loglinear"], perfect["criterion_c"], perfect["beta"]]).all()
    assert np.isfinite([reverse["dprime_loglinear"], reverse["criterion_c"], reverse["beta"]]).all()
    low = _sdt(1, 2, 0, 1, cfg)
    assert low["sdt_status"] == "rejected_low_opportunity"
    assert np.isnan(low["dprime_loglinear"])


def test_legacy_bbb_contract_is_rejected(tmp_path: Path):
    manifest, identity, config = build(tmp_path / "fixture")
    frame = pd.read_csv(manifest, dtype=str)
    frame.loc[0, "source_contract"] = "legacy_bbb_v3"
    frame.to_csv(manifest, index=False)
    with pytest.raises(ValueError, match="source_contract"):
        produce(manifest, identity, config, tmp_path / "out")


def test_groupkfold_never_splits_repeat_sessions():
    frame = pd.DataFrame({
        "session_id": ["s1", "s1", "s2", "s2", "s3", "s4"],
        "anonymous_participant_group_id": ["a", "a", "a", "a", "b", "c"],
    })
    folds = build_group_kfold_assignments(frame, n_splits=3)
    assert folds.loc[folds.session_id.isin(["s1", "s2"]), "fold_id"].nunique() == 1
    with pytest.raises(ValueError, match="leakage"):
        assert_group_disjoint(
            pd.DataFrame({"anonymous_participant_group_id": ["a"]}),
            pd.DataFrame({"anonymous_participant_group_id": ["a"]}),
        )


def test_scaling_and_selection_are_fit_on_training_fold_only():
    train = pd.DataFrame({
        "anonymous_participant_group_id": ["a", "a", "b", "b"],
        "target": [0, 0, 1, 1],
        "signal": [0.0, 0.1, 1.0, 1.1],
        "noise": [1.0, 0.0, 1.0, 0.0],
    })
    test = pd.DataFrame({
        "anonymous_participant_group_id": ["c", "c"],
        "target": [0, 1],
        "signal": [1000.0, 2000.0],
        "noise": [1000.0, 2000.0],
    })
    result = fit_transform_train_only(
        train, test, feature_columns=["signal", "noise"], target_column="target", select_k=1
    )
    assert result.selected_features == ("signal",)
    assert result.scaler_mean == pytest.approx((0.55, 0.5))
    assert result.test.max() > 100


def test_output_directory_is_never_overwritten(tmp_path: Path):
    manifest, identity, config = build(tmp_path / "fixture")
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        produce(manifest, identity, config, out)
