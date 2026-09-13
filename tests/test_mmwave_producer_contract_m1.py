from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
MAINT = ROOT / "scripts" / "maintenance"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load(MAINT / "mmwave_probe_contract.py", "m1_contract_test")
j = load(MAINT / "run_mmwave_probe_merge_ready_20260831.py", "m1_j_test")
e = load(MAINT / "run_mmwave_probe_merge_ready_E_20260831.py", "m1_e_test")


def row(**overrides):
    value = {
        "repeat_participant_id": "R001",
        "session_id": "sub-001",
        "block_id": "block-1",
        "probe_id": "probe-01",
        "probe_index_in_block": "1",
        "window_name": "pre_30s",
        "window_start_unix_ms": "900",
        "window_effective_start_unix_ms": "1000",
        "window_end_unix_ms": "1300",
        "probe_onset_unix_ms": "1300",
    }
    value.update(overrides)
    return value


def timestamps():
    return np.asarray(
        [[0, 900, 950], [1, 1000, 1050], [2, 1100, 1150], [3, 1200, 1250], [4, 1300, 1350]],
        dtype=np.int64,
    )


def test_dll_effective_start_and_right_open_endpoint():
    selected = contract.select_frame_window(row(), timestamps())
    assert contract.SCIENCE_TIMESTAMP_COL == 1
    assert contract.QC_TIMESTAMP_COL == 2
    assert (selected.i0, selected.i1_exclusive, selected.n_frames) == (1, 4, 3)
    assert selected.first_science_timestamp_ms == 1000
    assert selected.last_science_timestamp_ms == 1200
    assert selected.all_selected_before_probe is True


def test_legacy_audit_reconstructs_old_contract_without_driving_science():
    selected = contract.select_frame_window(row(), timestamps())
    legacy = contract.select_legacy_frame_window(row(), timestamps())
    audit = contract.frame_audit_row(row(), selected, legacy)
    assert legacy["legacy_n_frames"] == 4
    assert audit["membership_changed"] is True


def test_same_frame_indices_with_different_clock_values_are_same_membership():
    values = np.asarray(
        [[0, 900, 901], [1, 1000, 1001], [2, 1100, 1101], [3, 1200, 1201], [4, 1300, 1301]],
        dtype=np.int64,
    )
    same_bounds = row(window_start_unix_ms="1000", window_effective_start_unix_ms="1000")
    selected = contract.select_frame_window(same_bounds, values)
    legacy = contract.select_legacy_frame_window(same_bounds, values)
    audit = contract.frame_audit_row(same_bounds, selected, legacy)
    assert (selected.i0, selected.i1_exclusive) == (1, 4)
    assert (legacy["legacy_i0"], legacy["legacy_i1_exclusive"]) == (1, 4)
    assert selected.membership_digest_sha256 == legacy["legacy_membership_digest_sha256"]
    assert selected.timestamp_digest_sha256 != legacy["legacy_timestamp_digest_sha256"]
    assert audit["membership_changed"] is False


def test_exact_endpoint_identity_and_monotonic_clock_fail_closed():
    with pytest.raises(ValueError, match="must equal"):
        contract.select_frame_window(row(window_end_unix_ms="1301"), timestamps())
    bad = timestamps().copy()
    bad[3, 1] = 1005
    with pytest.raises(ValueError, match="not monotonic"):
        contract.select_frame_window(row(), bad)


def test_membership_digest_is_stable():
    a = contract.select_frame_window(row(), timestamps())
    b = contract.select_frame_window(row(), timestamps())
    c = contract.select_frame_window(row(window_effective_start_unix_ms="1100"), timestamps())
    assert a.membership_digest_sha256 == b.membership_digest_sha256
    assert a.membership_digest_sha256 != c.membership_digest_sha256


def test_producer_usable_ratio_is_not_binary_availability():
    class FakeAlgo:
        HR_LO_BPM = 48.0
        HR_HI_BPM = 120.0

        def detect_peaks_heart_lo(self, heartbeat, lo_bpm, hi_bpm):
            return np.asarray([1, 20, 40], dtype=int)

        def estimate_hr_time_course(self, **kwargs):
            return {"signal_quality": {"usable_ratio": 0.42}}

    assert j.producer_usable_ratio(FakeAlgo(), np.arange(100.0)) == pytest.approx(0.42)


def test_e_batch_preserves_effective_start_and_rejects_unknown_truncation():
    bg = {"sub-001": "1"}
    mp = {"1": {"repeat_participant_id": "R001", "site": "北京"}}
    source = {
        "session_id": "sub-001", "block_id": "B1", "probe_order_in_block": "1",
        "probe_time_ms": "1300", "window_start_unix_ms": "900",
        "window_effective_start_unix_ms": "1000", "window_end_unix_ms": "1300",
        "window_crosses_block": "True",
    }
    canonical = e.to_canonical(bg, mp, source)
    assert canonical["window_effective_start_unix_ms"] == "1000"
    source.pop("window_effective_start_unix_ms")
    with pytest.raises(ValueError, match="refusing nominal-start fallback"):
        e.to_canonical(bg, mp, source)


def test_j_and_e_share_process_probe_contract_and_legacy_indexing_is_gone():
    j_source = (MAINT / "run_mmwave_probe_merge_ready_20260831.py").read_text(encoding="utf-8")
    e_source = (MAINT / "run_mmwave_probe_merge_ready_E_20260831.py").read_text(encoding="utf-8")
    assert "contract.select_frame_window(row, timestamps)" in j_source
    assert "j.process_probe(" in e_source
    assert "timestamps[:, 2]" not in j_source
    assert 'side="right"' not in j_source
