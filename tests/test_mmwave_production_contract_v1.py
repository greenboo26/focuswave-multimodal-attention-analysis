import json
import sys
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import behavior_time_gate as gate
import process_vital_signs_v3_1_1 as algo
import run_timeline_gated_mmwave_quality as runner


def test_strict_json_never_emits_nonstandard_nan():
    text = runner.strict_json_dumps({"nan": float("nan"), "inf": float("inf"), "finite": 1.5})
    assert "NaN" not in text and "Infinity" not in text
    assert json.loads(text) == {"nan": None, "inf": None, "finite": 1.5}
    assert "NaN" not in algo.strict_json_dumps({"value": np.float64(np.nan)})


def test_vmd_preflight_blocks_missing_dependency_without_fallback(monkeypatch):
    real = runner._package_state
    monkeypatch.setattr(runner, "_package_state", lambda name, required_version=None:
                        {"package": name, "installed": False, "version": None,
                         "required_version": required_version, "version_ok": False}
                        if name == "vmdpy" else real(name, required_version))
    result = runner.method_preflight("vmd_heart")
    assert result["status"] == "blocked"
    assert result["selected_method"] is None
    assert result["fallback_used"] is False
    assert result["failure_reason"] == "MISSING_VMDPY_DEPENDENCY"


def test_bp_heart_must_be_selected_explicitly():
    result = runner.method_preflight("bp_heart")
    assert result["requested_method"] == "bp_heart"
    assert result["selected_method"] == "bp_heart"
    assert result["fallback_used"] is False


def test_all_nan_candidates_are_rejected_without_ch0_bin10_fallback():
    power = np.ones((16, 8), dtype=float)
    iq = np.full((1000, 16, 8), complex(float("nan"), 0.0), dtype=np.complex128)
    with pytest.raises(algo.CandidateSelectionError) as caught:
        algo.select_separate_channels_bins(power, iq, 1000)
    assert caught.value.reason == "NO_VALID_CHANNEL_BIN_SELECTION"
    assert len(caught.value.summaries) == 8
    assert all(item["algorithm_returned"] is False for item in caught.value.summaries)
    assert all(item["quality_valid"] is False for item in caught.value.summaries)
    assert all(item["selection_status"] == "rejected" for item in caught.value.summaries)


def test_empty_noise_baseline_is_rejected():
    power = np.ones((16, 1), dtype=float)
    iq = np.ones((20, 16, 1), dtype=np.complex128)
    with pytest.raises(algo.CandidateSelectionError, match="EMPTY_SPECTRAL_BASELINE"):
        algo.select_bins_from_profile(power, 0, iq, 20)


def _subject(root: Path, subject: str) -> Path:
    subject_dir = root / subject
    (subject_dir / "mmwave").mkdir(parents=True)
    (subject_dir / "beh").mkdir()
    return subject_dir


def test_32_byte_bin_and_empty_timestamps_is_invalid(tmp_path):
    root = tmp_path / "正式实验"
    subject = _subject(root, "sub-036")
    (subject / "mmwave" / "sub-036_mmwave.bin").write_bytes(b"0" * 32)
    (subject / "mmwave" / "sub-036_mmwave_timestamps.csv").write_bytes(b"")
    record = gate.build_record(root, subject)
    assert record["status"] == "excluded_invalid"
    assert record["exclusion_note"] == "PLACEHOLDER_BIN_32_BYTES_AND_EMPTY_TIMESTAMPS"


def test_empty_mmwave_directory_is_invalid(tmp_path):
    root = tmp_path / "正式实验"
    subject = _subject(root, "sub-047")
    record = gate.build_record(root, subject)
    assert record["status"] == "excluded_invalid"
    assert record["exclusion_note"] == "EMPTY_MMWAVE_DIRECTORY"


def test_manifest_keys_pass_through_without_inference(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"sessions": [{"session_id": "031",
        "anonymous_participant_group_id": "anon-group-01",
        "repeat_participant_id": "repeat-frozen-01"}]}), encoding="utf-8")
    rows = runner.load_input_manifest(path)
    records = runner.apply_input_manifest([], rows)
    assert records[0]["session_id"] == "sub-031"
    assert records[0]["anonymous_participant_group_id"] == "anon-group-01"
    assert records[0]["repeat_participant_id"] == "repeat-frozen-01"


def test_field_contract_reads_breath_rate_and_nested_quality():
    record = {"source_tag": "fixture", "subject": "sub-001", "session_id": "sub-001",
              "anonymous_participant_group_id": "anon-1", "repeat_participant_id": None}
    segment = {"layer": "task", "label": "block_1", "frame_start": 0, "frame_end": 1000,
               "frame_count": 1000, "retained_duration_s": 10.0}
    result = {"algorithm_returned": True, "quality_valid": True, "selection_status": "selected",
              "heart_rate": {"fused_bpm": 72.0, "time_course": {
                  "signal_quality": {"hard_gate_passed": True}, "metrics": {"median_bpm": 72.0}}},
              "breath_rate": {"time_bpm": 15.0}, "hrv": {"mean_IBI_ms": 833.3}}
    item = runner._segment_result(record, segment, result, "bp_heart", "fixture")
    assert item["breath_rate"]["time_bpm"] == 15.0
    assert item["quality"]["signal_quality"]["hard_gate_passed"] is True
    assert item["quality"]["metrics"]["median_bpm"] == 72.0
    assert item["status_layers"]["ibi_hrv"]["formal_report_status"] == "blocked"

    schema = json.loads((ROOT / "schemas/mmwave/segment_analysis_summary_v1.schema.json").read_text(encoding="utf-8"))
    payload = {
        "schema_version": runner.SCHEMA_VERSION, "pipeline_version": runner.PIPELINE_VERSION,
        "analysis_id": "fixture", "status": "completed", "method": "bp_heart",
        "input_manifest": {}, "preflight": {}, "n_sessions": 1,
        "n_segments_succeeded": 1, "n_segments_failed": 0,
        "records": [{"session_id": "sub-001", "anonymous_participant_group_id": "anon-1",
                     "segments": [item]}], "scientific_status": {},
    }
    Draft202012Validator(schema).validate(payload)


def test_output_directory_must_be_empty(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "existing.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="OUTPUT_DIRECTORY_NOT_EMPTY"):
        runner.prepare_output_dir(output)


def test_empty_record_set_refuses_silent_output(tmp_path):
    with pytest.raises(ValueError, match="EMPTY_RECORD_SET_REFUSES_OUTPUT"):
        runner.write_manifest([], tmp_path)
