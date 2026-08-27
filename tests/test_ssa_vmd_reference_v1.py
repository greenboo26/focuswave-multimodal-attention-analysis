import numpy as np

from pipelines.mmwave.ssa_vmd_reference_v1 import estimate_window, ssa_reconstruct


def test_ssa_reconstruct_preserves_50_second_length():
    time = np.arange(500, dtype=float) / 10.0
    signal = np.sin(2 * np.pi * 1.2 * time) + 0.8 * np.sin(2 * np.pi * 0.25 * time)
    reconstructed = ssa_reconstruct(signal)
    assert reconstructed.shape == signal.shape
    assert np.all(np.isfinite(reconstructed))


def test_ssa_vmd_synthetic_heart_estimate():
    time = np.arange(500, dtype=float) / 10.0
    signal = np.sin(2 * np.pi * 1.2 * time) + 0.8 * np.sin(2 * np.pi * 0.25 * time)
    estimate, info = estimate_window(signal)
    assert estimate == 72.0
    assert info["selection_rule"] == "maximal_non_dc_HR_band_power; no_ECG_selection"
