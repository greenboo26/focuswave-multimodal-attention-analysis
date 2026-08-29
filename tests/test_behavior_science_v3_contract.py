"""行为科学 v3 契约的合成 smoke tests；不读取真实数据。"""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "behavior" / "行为科学v3分析契约.json"
FIXTURE = ROOT / "tests" / "fixtures" / "behavior_science_v3_synthetic.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_freezes_rejected_v2_and_separates_reports():
    contract = load_json(CONTRACT)
    assert contract["status"] == "formal-repair-implementation"
    assert contract["publication_policy"]["v2_results_publishable"] is False
    assert contract["publication_policy"]["formal_report_is_separate_from_process_report"] is True
    assert contract["publication_policy"]["engineering_validation_is_behavioral_validity"] is False
    assert contract["sensitivity_windows_seconds"] == [10, 20, 30]


def test_primary_rows_are_one_per_event_and_windows_are_separate():
    fixture = load_json(FIXTURE)
    rows = fixture["primary_probe_rows"]
    assert fixture["synthetic"] is True
    assert len({row["event_id"] for row in rows}) == len(rows)
    assert all("window_seconds_nominal" not in row for row in rows)

    windows = fixture["window_sensitivity_rows"]
    assert {row["window_seconds_nominal"] for row in windows} == {10, 20, 30}
    keys = {(row["event_id"], row["window_seconds_nominal"]) for row in windows}
    assert len(keys) == len(windows)


def test_contract_requires_hierarchy_cluster_outcome_separation_and_unit_specific_n():
    contract = load_json(CONTRACT)
    hierarchy = contract["hierarchy"]
    assert "block within session" in hierarchy["required_nesting"]
    assert "session within participant_cluster" in hierarchy["required_nesting"]
    assert hierarchy["error_centering"] == "within_participant_centering_and_pre_error_baseline_change"
    assert hierarchy["leakage_control"] == "participant_cluster_disjoint_split_before_prediction_fit"
    assert contract["questions"]["q2"]["ordered_model_without_cluster"] == "forbidden"
    assert contract["outcome_separation"]["combined_correct_dependent_variable"] == "forbidden_for_formal_error_inference"
    assert contract["reporting"]["n_labels"] == ["probe_n", "session_n", "participant_group_n"]
    assert contract["reporting"]["model_failure_table"] == "model_failures_v3.csv"


def test_candidate_matrix_requires_evidence_not_unsupported_binary_gate():
    contract = load_json(CONTRACT)
    decision = contract["candidate_decision"]
    assert "evidence_source" in decision["required_fields"]
    assert "scientific_prohibited" in decision["decision_classes"]
    assert decision["unsupported_binary_0_1_gate"] == "forbidden"


def test_fixture_has_no_real_identity_or_machine_path_material():
    text = FIXTURE.read_text(encoding="utf-8")
    lowered = text.lower()
    forbidden_paths = ["d:\\", "e:\\", "d:/", "e:/"]
    assert not any(token in lowered for token in forbidden_paths)
    assert re.search(r"\d{11,}", text) is None
    assert "synthetic" in lowered
