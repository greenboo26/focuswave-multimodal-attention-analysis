from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/canonical/compare_reproduction.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("compare_reproduction_test", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_equivalence_exact_and_float_tolerance(tmp_path):
    m = load_checker()
    expected = tmp_path / "expected.csv"
    actual = tmp_path / "actual.csv"
    pd.DataFrame({"feature_set": ["A", "B"], "n_probe": [10, 20], "roc_auc": [0.7, 0.8]}).to_csv(expected, index=False)
    pd.DataFrame({"feature_set": ["B", "A"], "n_probe": [20, 10], "roc_auc": [0.8 + 1e-10, 0.7 - 1e-10]}).to_csv(actual, index=False)
    result = m.compare_csv(expected, actual, atol=1e-8, rtol=1e-7)
    assert result["status"] == "PASS"


def test_equivalence_rejects_count_change(tmp_path):
    m = load_checker()
    expected = tmp_path / "expected.csv"
    actual = tmp_path / "actual.csv"
    pd.DataFrame({"feature_set": ["A"], "n_probe": [10], "roc_auc": [0.7]}).to_csv(expected, index=False)
    pd.DataFrame({"feature_set": ["A"], "n_probe": [11], "roc_auc": [0.7]}).to_csv(actual, index=False)
    result = m.compare_csv(expected, actual, atol=1e-8, rtol=1e-7)
    assert result["status"] == "FAIL"
