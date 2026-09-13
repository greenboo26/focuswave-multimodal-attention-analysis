from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "maintenance" / "audit_mmwave_producer_contract_repair_20260913.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = load(AUDITOR, "m1_audit_state_test")


def row(probe: int, fused: float | None, confidence: float | None) -> dict[str, str]:
    def value(x):
        return "" if x is None else str(x)

    return {
        "repeat_participant_id": "R001",
        "session_id": "sub-001",
        "block_id": "block-1",
        "probe_id": f"probe-{probe:02d}",
        "probe_index_in_block": str(probe),
        "window_name": "pre_30s",
        "mmwave_hr_fused_bpm_median": value(fused),
        "mmwave_hr_mean_confidence": value(confidence),
    }


def key(probe: int) -> tuple[str, ...]:
    return ("R001", "sub-001", "block-1", f"probe-{probe:02d}", "pre_30s")


def test_reconstruct_incoming_anchor_tracks_previous_bpm_update():
    incoming = audit.reconstruct_incoming_anchor(
        [row(1, 70.0, 0.50), row(2, 80.0, 0.50), row(3, 90.0, 0.50)]
    )
    assert incoming[key(1)] is None
    assert incoming[key(2)] == pytest.approx(70.0)
    assert incoming[key(3)] == pytest.approx(72.0)


def test_low_confidence_probe_does_not_update_existing_anchor():
    incoming = audit.reconstruct_incoming_anchor(
        [row(1, 70.0, 0.50), row(2, 100.0, 0.10), row(3, 90.0, 0.50)]
    )
    assert incoming[key(2)] == pytest.approx(70.0)
    assert incoming[key(3)] == pytest.approx(70.0)


def test_prior_hr_difference_produces_different_incoming_anchor_for_later_probe():
    old = audit.reconstruct_incoming_anchor(
        [row(1, 70.0, 0.50), row(2, 75.0, 0.50)]
    )
    new = audit.reconstruct_incoming_anchor(
        [row(1, 80.0, 0.50), row(2, 75.0, 0.50)]
    )
    assert old[key(2)] == pytest.approx(70.0)
    assert new[key(2)] == pytest.approx(80.0)
    assert audit._anchor_close(old[key(2)], new[key(2)]) is False
