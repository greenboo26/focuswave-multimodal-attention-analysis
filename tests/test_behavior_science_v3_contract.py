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
    assert contract["status"] == "web-repair-base"
    assert contract["publication_policy"]["v2_results_publishable"] is False
    assert contract["publication_policy"]["formal_report_is_separate_from_process_report"] is True
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


def test_contract_requires_hierarchy_cluster_and_unit_specific_n():
    contract = load_json(CONTRACT)
    hierarchy = contract["hierarchy"]
    assert hierarchy["required_nesting"] == [
        "cycle within block",
        "block within session",
        "session within participant_cluster",
    ]
    assert hierarchy["required_interaction"] == "block_by_cycle"
    assert hierarchy["error_centering"] == "within_participant_centering_required"
    assert contract["questions"]["q2"]["ordered_model_without_cluster"] == "forbidden"
    assert contract["reporting"]["n_labels"] == ["probe_n", "session_n", "participant_group_n"]


def test_fixture_has_no_real_identity_or_machine_path_material():
    text = FIXTURE.read_text(encoding="utf-8")
    lowered = text.lower()
    forbidden_paths = ["d:\\", "e:\\", "d:/", "e:/"]
    assert not any(token in lowered for token in forbidden_paths)
    assert re.search(r"\d{11,}", text) is None
    assert "synthetic" in lowered
