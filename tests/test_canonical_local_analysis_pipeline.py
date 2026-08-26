from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/canonical/local_analysis_registry_v1.json"
PIPELINE = ROOT / "configs/canonical/competition_pipeline_v1.json"
EXAMPLE = ROOT / "configs/canonical/paths.local.example.json"
RUNNER = ROOT / "scripts/canonical/run_local_analysis.py"
COMPETITION = ROOT / "scripts/canonical/run_competition_pipeline.py"


def test_registry_is_machine_independent_and_producers_exist():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert data["schema_version"] == "focuswave-local-analysis-registry-v1"
    assert data["scope"] == "completed_local_analyses_only"
    assert data["science_change_allowed"] is False
    assert len(data["analyses"]) >= 11
    for analysis_id, spec in data["analyses"].items():
        assert (ROOT / spec["producer"]).is_file(), analysis_id
        assert spec["source_ref"].startswith("archive/20260826/"), analysis_id
        serialized = json.dumps(spec, ensure_ascii=False)
        assert "D:\\" not in serialized
        assert "J:\\" not in serialized
        assert "aggregate_outputs" in spec
        assert "merge_ready_outputs" in spec
        assert "frozen" in spec


def test_local_path_example_exposes_dual_machine_ports():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    expected = {
        "project_root", "raw_data_root", "derived_root", "legacy_output_root",
        "final_output_root", "teammate_input_root", "combined_input_root",
    }
    assert set(data["paths"]) == expected
    assert set(data["machine"]) == {"machine_id", "site"}
    text = EXAMPLE.read_text(encoding="utf-8")
    assert "D:\\" not in text
    assert "J:\\" not in text


def test_runner_lists_same_analysis_ids_as_registry():
    expected = set(json.loads(REGISTRY.read_text(encoding="utf-8"))["analyses"])
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--list"],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    actual = {line.split("\t", 1)[0] for line in proc.stdout.splitlines() if line.strip()}
    assert actual == expected


def test_competition_pipeline_profiles_are_valid_and_orderable():
    cfg = json.loads(PIPELINE.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    analyses = set(registry["analyses"])
    assert cfg["pipeline_version"] == "focuswave_canonical_v1"
    for stage, spec in cfg["stages"].items():
        assert stage in analyses
        for dep in spec.get("depends_on", []):
            assert dep in cfg["stages"]
    for profile in cfg["profiles"].values():
        assert profile
        assert set(profile) <= analyses
    assert set(cfg["profiles"]["competition_core"]) >= {
        "report_cohort_v1", "behavior_baseline_v2", "questionnaire_q1_v1",
        "mmwave_c2b_v2", "mmwave_c2c_v1",
    }


def test_competition_launcher_lists_contract():
    proc = subprocess.run(
        [sys.executable, str(COMPETITION), "--paths", str(EXAMPLE), "--list"],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert "competition_core" in payload["profiles"]
    assert "mmwave_c2b_v2" in payload["stages"]


def test_c1_frozen_evaluator_basic_identity_case():
    import importlib.util
    import numpy as np

    path = ROOT / "pipelines/mmwave/frozen_c1_metrics.py"
    spec = importlib.util.spec_from_file_location("frozen_c1_metrics_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ref = np.array([0.0, 1.0, 2.0, 3.0])
    out = module.metrics(ref, ref.copy(), 50.0, 0.0)
    assert out["matched_beats"] == 4
    assert out["precision"] == 1.0
    assert out["recall"] == 1.0
    assert out["f1"] == 1.0
    assert out["timing_mae_ms"] == 0.0


def test_q1_canonical_label_3_4_mapping_is_explicit():
    import importlib.util

    path = ROOT / "pipelines/questionnaire/run_q1_questionnaire_criterion_validity.py"
    spec = importlib.util.spec_from_file_location("q1_mapping_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.LABEL_SEMANTICS[3] == "task-unrelated thought / mind wandering"
    assert module.LABEL_SEMANTICS[4] == "mind blank"
    assert module.LABEL_PROPORTION_COLUMNS[3] == "走神_proportion"
    assert module.LABEL_PROPORTION_COLUMNS[4] == "大脑空白_proportion"


def test_collector_rejects_scientific_signature_mismatch(tmp_path):
    import importlib.util

    path = ROOT / "scripts/canonical/collect_machine_packages.py"
    spec = importlib.util.spec_from_file_location("collector_signature_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = {
        "pipeline_version": "focuswave_canonical_v1", "producer": "p.py",
        "source_ref": "archive/20260826/x", "frozen": {"seed": 1},
        "result_unit": "probe", "merge_key": ["subject"],
    }
    one = {"analysis_id": "x", "relative_path": "x.csv", "machine_id": "a", "site": "Beijing", "merge_key": ["subject"], "scientific_signature": base, "path": tmp_path / "a.csv"}
    two_sig = dict(base); two_sig["frozen"] = {"seed": 2}
    two = dict(one); two["machine_id"] = "b"; two["scientific_signature"] = two_sig; two["path"] = tmp_path / "b.csv"
    one["path"].write_text("subject,value\n1,1\n", encoding="utf-8")
    two["path"].write_text("subject,value\n2,2\n", encoding="utf-8")
    import pytest
    with pytest.raises(RuntimeError, match="scientific signature mismatch"):
        module.merge_group([one, two], tmp_path / "out.csv")


def test_sensor_single_class_heldout_is_not_filtered_from_source():
    source = (ROOT / "pipelines/mmwave/run_beijing_sensor_increment_v1.py").read_text(encoding="utf-8")
    assert 'test["target_label1"].nunique() < 2' not in source
    assert "single-class" in source


def test_c2b_uses_behavior_and_mmwave_intersection_for_fusion():
    source = (ROOT / "pipelines/mmwave/run_c2b_v2_canonical_reconstruction.py").read_text(encoding="utf-8")
    assert 'use["behavior_available"].eq(1) & use["mmwave_available"].eq(1)' in source
    assert "ΔAUC 约" not in source
    assert "1,420" not in source
    assert "1,317" not in source
    assert "1,278" not in source
