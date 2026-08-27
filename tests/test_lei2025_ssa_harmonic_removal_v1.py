import numpy as np

from pipelines.mmwave.lei2025_ssa_harmonic_removal_v1 import (
    estimate_respiratory_frequency,
    remove_harmonics,
)


def test_lei_ssa_core_preserves_shape_and_reports_contract_choices():
    fs = 10.0
    n = 600
    time = np.arange(n) / fs
    signal = (
        0.8 * np.sin(2 * np.pi * 0.25 * time)
        + 0.35 * np.sin(2 * np.pi * 0.50 * time)
        + 0.25 * np.sin(2 * np.pi * 0.75 * time)
        + 0.15 * np.sin(2 * np.pi * 1.20 * time)
    )
    cleaned, info = remove_harmonics(signal, fs)

    assert cleaned.shape == signal.shape
    assert np.isfinite(cleaned).all()
    assert info["ssa_L"] == 300
    assert info["missing_evidence"]
    assert estimate_respiratory_frequency(signal, fs) == 0.25
