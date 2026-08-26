from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/canonical/local_analysis_registry_v1.json"
EXAMPLE = ROOT / "configs/canonical/paths.local.example.json"
RUNNER = ROOT / "scripts/canonical/run_local_analysis.py"


def test_registry_is_machine_independent_and_producers_exist():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert data["schema_version"] == "focuswave-local-analysis-registry-v1"
    assert data["scope"] == "completed_local_analyses_only"
    assert data["science_change_allowed"] is False
    assert len(data["analyses"]) >= 8
    for analysis_id, spec in data["analyses"].items():
        assert (ROOT / spec["producer"]).is_file(), analysis_id
        assert spec["source_ref"].startswith("archive/20260826/"), analysis_id
        serialized = json.dumps(spec, ensure_ascii=False)
        assert "D:\\" not in serialized
        assert "J:\\" not in serialized


def test_local_path_example_has_aliases_only():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert set(data["paths"]) == {"raw_data_root", "derived_root", "legacy_output_root"}
    text = EXAMPLE.read_text(encoding="utf-8")
    assert "D:\\" not in text
    assert "J:\\" not in text


def test_runner_lists_same_analysis_ids_as_registry():
    expected = set(json.loads(REGISTRY.read_text(encoding="utf-8"))["analyses"])
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--list"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    actual = {line.split("\t", 1)[0] for line in proc.stdout.splitlines() if line.strip()}
    assert actual == expected


def test_c1_frozen_evaluator_basic_identity_case():
    import importlib.util
    import numpy as np

    path = ROOT / "pipelines/mmwave/frozen_c1_metrics.py"
    spec = importlib.util.spec_from_file_location("frozen_c1_metrics_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    ref = np.array([0.0, 1.0, 2.0, 3.0])
    out = module.metrics(ref, ref.copy(), 50.0, 0.0)
    assert out["matched_beats"] == 4
    assert out["precision"] == 1.0
    assert out["recall"] == 1.0
    assert out["f1"] == 1.0
    assert out["timing_mae_ms"] == 0.0
