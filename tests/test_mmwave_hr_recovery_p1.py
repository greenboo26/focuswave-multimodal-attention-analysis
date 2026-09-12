import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_hr_recovery_p1_20260912.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("mmwave_hr_recovery_p1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fake_algo(hard_gate_passed=True):
    calls = {}

    def segment(**kwargs):
        calls["segment"] = kwargs
        return {"corrected_freq_bpm": 72.0, "windows": []}

    def consensus(**kwargs):
        calls["consensus"] = kwargs
        return 73.0, 74.0, {"source": "test_consensus"}

    def course(**kwargs):
        calls["course"] = kwargs
        return {
            "freq_median_bpm": 73.0,
            "time_median_bpm": 74.0,
            "fused_median_bpm": 73.5,
            "points": [{"confidence": 0.4}, {"confidence": 0.6}],
            "signal_quality": {"usable_ratio": 1.0 if hard_gate_passed else 0.25, "hard_gate_passed": hard_gate_passed},
        }

    algo = SimpleNamespace(
        HR_LO_BPM=48.0,
        HR_HI_BPM=120.0,
        HR_LO_HZ=0.8,
        HR_HI_HZ=2.0,
        detect_peaks_heart_lo=lambda *args, **kwargs: np.array([0, 100, 200]),
        estimate_freq_periodogram=lambda *args, **kwargs: 1.2,
        _heart_segment_reference_correction=segment,
        _heart_window_consensus_bpm=consensus,
        estimate_hr_time_course=course,
    )
    return algo, calls


def test_restoration_calls_only_frozen_bundle_with_consensus_seed_and_no_rsp():
    adapter = load_adapter()
    algo, calls = fake_algo(hard_gate_passed=True)
    result = adapter.restoration_step(algo, np.ones(3000))

    assert calls["segment"]["ext_br_bpm"] is None
    assert calls["segment"]["base_freq_bpm"] == 72.0
    assert calls["consensus"]["hr_freq_bpm_periodogram"] == 72.0
    assert calls["course"]["reference_bpm"] == 73.0
    assert calls["course"]["window_s"] == 25.0
    assert calls["course"]["step_s"] == 5.0
    assert result["fused_bpm"] == 73.5
    assert result["gate_hit"] is False


def test_global_signal_gate_blanks_hr_but_keeps_auditable_pre_gate_values():
    adapter = load_adapter()
    algo, _ = fake_algo(hard_gate_passed=False)
    result = adapter.restoration_step(algo, np.ones(3000))

    assert result["spectral_bpm"] is None
    assert result["time_bpm"] is None
    assert result["fused_bpm"] is None
    assert result["pre_gate"] == {"spectral_bpm": 73.0, "time_bpm": 74.0, "fused_bpm": 73.5}
    assert result["gate_hit"] is True
    assert result["gate_reason"] == "usable_ratio_below_0.50"
    assert result["status"] == "QC_FAIL_SIGNAL_QUALITY"


def test_p1_uses_dll_host_receive_clock_and_right_open_window():
    adapter = load_adapter()
    values = np.array([[0, 100, 500], [1, 110, 9_000], [2, 120, 10_000]])
    assert adapter.alignment_timestamps(values).tolist() == [100, 110, 120]
    lo, hi = np.searchsorted(adapter.alignment_timestamps(values), [100, 120], side="left")
    assert (lo, hi) == (0, 2)


def test_p1_dll_clock_fails_closed_without_python_fallback():
    adapter = load_adapter()
    import pytest

    with pytest.raises(ValueError, match="DLL host receive"):
        adapter.alignment_timestamps(np.array([[0], [1]]))
    with pytest.raises(ValueError, match="invalid or nonmonotonic"):
        adapter.alignment_timestamps(np.array([[0, 110, 1], [1, 100, 2]]))
