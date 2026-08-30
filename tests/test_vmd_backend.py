"""Regression tests for the formal VMD backend contract (T0).

Pin _load_vmd() to sktime.libs.vmdpy.VMD with exact version sktime==1.1.0 and
prove the standalone vmdpy package can never become a silent fallback.
"""

from __future__ import annotations

import importlib
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PRODUCER = "process_vital_signs_v3_1_1"


def _load_producer():
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(PRODUCER)


def test_load_vmd_returns_maintained_sktime_backend():
    producer = _load_producer()
    vmd, backend, version = producer._load_vmd()
    assert backend == "sktime.libs.vmdpy"
    assert version == "1.1.0"
    assert vmd.__module__.startswith("sktime.libs.vmdpy")


def test_load_vmd_version_mismatch_fails_explicitly():
    producer = _load_producer()
    with mock.patch("importlib.metadata.version", return_value="1.0.0"):
        with pytest.raises(ImportError, match="requires exactly sktime==1.1.0"):
            producer._load_vmd()


def test_load_vmd_missing_sktime_raises_without_fallback():
    producer = _load_producer()
    with mock.patch(
        "importlib.metadata.version",
        side_effect=PackageNotFoundError("sktime"),
    ):
        with pytest.raises(ImportError, match="sktime is not installed"):
            producer._load_vmd()


def test_source_never_imports_standalone_vmdpy():
    source_path = SCRIPTS / f"{PRODUCER}.py"
    text = source_path.read_text(encoding="utf-8")
    assert "from vmdpy import" not in text
    assert "import vmdpy" not in text
