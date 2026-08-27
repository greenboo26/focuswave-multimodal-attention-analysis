import copy
import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator, ValidationError

from scripts.mmwave_reanalysis_v2.run_benchmark_decomposition_issue9 import (
    OFFICIAL_ECG_BAND_HZ,
    OFFICIAL_ECG_FILTER_ORDER,
    OFFICIAL_ECG_FS_HZ,
    official_agebalanced_ecg_hr_bpm,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "mmwave" / "per_window_benchmark_v1.schema.json"
DECISION_PATH = ROOT / "configs" / "mmwave_reanalysis_v2" / "benchmark_decision_v1.json"
SPLIT_PATH = ROOT / "configs" / "mmwave_reanalysis_v2" / "agebalanced_split_v1.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def validator():
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def valid_row():
    return {
        "schema_version": "per_window_benchmark_v1",
        "run_id": "contract-test",
        "dataset_id": "agebalanced_60ghz_ecg",
        "dataset_version": "zenodo-16760683",
        "subject_id": "P001",
        "session_id": "P001_lying_rest",
        "split": "development",
        "window_id": "P001_lying_rest_000000",
        "window_start_s": 0,
        "window_end_s": 30,
        "window_length_s": 30,
        "method": {
            "id": "historical_dual_band",
            "version": "v1",
            "implementation_class": "project_existing",
            "source_commit": "f4a8c74000000000000000000000000000000000",
            "config_sha256": "0" * 64,
            "input_sha256": None,
        },
        "radar_qc": {
            "status": "pass",
            "quality_stratum": "high",
            "timestamp_coverage": 1.0,
            "finite_ratio": 1.0,
            "max_gap_s": 0.1,
            "target_snr_db": 12.0,
            "target_coherence": 0.85,
            "motion_status": "not_available",
            "rejection_reason": None,
        },
        "reference_qc": {
            "ecg": {"available": True, "status": "pass", "sampling_rate_hz": 250.0, "valid_ratio": 0.98, "source_kind": "raw_waveform", "rejection_reason": None},
            "rsp": {"available": False, "status": "not_available", "sampling_rate_hz": None, "valid_ratio": None, "source_kind": "none", "rejection_reason": "NO_RSP"},
            "r_peaks": {"available": True, "status": "pass", "sampling_rate_hz": 250.0, "valid_ratio": 0.96, "source_kind": "derived_events", "rejection_reason": None},
        },
        "sync": {"status": "pass", "timestamp_origin": "common_pc_clock", "offset_ms": 0, "offset_source": "source_timestamps", "per_window_search_used": False},
        "hr": {"scorable": True, "reference_value": 66.0, "estimate_value": 65.0, "absolute_error": 1.0},
        "br": {"scorable": False, "reference_value": None, "estimate_value": None, "absolute_error": None},
        "beat": {"scorable": True, "status": "matched", "match_tolerance_ms": 75, "reference_count": 33, "estimate_count": 32, "matched_count": 31, "precision": 0.96875, "recall": 0.93939, "f1": 0.95385, "timing_mae_ms": 31.0, "ibi_mae_ms": 42.0},
        "harmonic_lock": {"classification": "none", "reference_basis": "ecg_hr", "tolerance_bpm": 3.0},
        "outcome_status": "scored",
        "rejection_reason": None,
    }


def test_valid_row_passes(validator, valid_row):
    validator.validate(valid_row)


def test_missing_required_field_fails(validator, valid_row):
    row = copy.deepcopy(valid_row)
    del row["method"]["config_sha256"]
    with pytest.raises(ValidationError):
        validator.validate(row)


def test_br_cannot_be_scored_without_rsp(validator, valid_row):
    row = copy.deepcopy(valid_row)
    row["br"] = {"scorable": True, "reference_value": 14.0, "estimate_value": 14.0, "absolute_error": 0.0}
    with pytest.raises(ValidationError):
        validator.validate(row)


def test_hr_and_beats_cannot_be_scored_without_ecg(validator, valid_row):
    row = copy.deepcopy(valid_row)
    row["reference_qc"]["ecg"]["available"] = False
    with pytest.raises(ValidationError):
        validator.validate(row)


def test_split_is_disjoint_and_complete():
    split = load_json(SPLIT_PATH)
    development = set(split["development_participants"])
    held_out = set(split["held_out_participants"])
    assert len(development) == 30
    assert len(held_out) == 80
    assert not development & held_out
    assert development | held_out == {f"P{number:03d}" for number in range(1, 111)}


def test_decision_is_frozen_and_hrv_remains_blocked():
    decision = load_json(DECISION_PATH)
    assert decision["status"] == "FROZEN_BEFORE_HELDOUT_SCORING"
    assert decision["authorization"]["formal_cohort"] is False
    assert decision["authorization"]["hrv"] is False
    assert decision["windows"]["primary"]["length_s"] == 30
    assert decision["windows"]["primary"]["step_s"] == 5


def test_official_agebalanced_ecg_fft_reference_matches_notebook_contract():
    fs = OFFICIAL_ECG_FS_HZ
    time = np.arange(0.0, 25.0, 1.0 / fs)
    signal = 0.2 + 0.5 * np.sin(2 * np.pi * 0.2 * time) + np.sin(2 * np.pi * 1.2 * time)
    hr = official_agebalanced_ecg_hr_bpm(time, signal, 0.0, 25.0)
    assert OFFICIAL_ECG_BAND_HZ == (0.8, 2.0)
    assert OFFICIAL_ECG_FILTER_ORDER == 4
    assert hr == pytest.approx(72.0)
