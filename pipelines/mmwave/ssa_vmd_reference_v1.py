"""Single, frozen SSA+VMD paper-reimplementation adapter for Task 2R.

The adapter intentionally exposes the paper-to-device assumptions.  It is not
an author implementation.  ECG is never used to select an SSA rank, VMD mode,
or frequency estimate.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import periodogram


SSA_L = 400
SSA_R = 40
VMD_K = 5
VMD_ALPHA = 1000
VMD_TAU = 0
VMD_DC = 1
VMD_INIT = 0
VMD_TOL = 1e-6
FS_HZ = 10.0
HR_BAND_HZ = (0.8, 2.5)


def _diagonal_average(matrix: np.ndarray) -> np.ndarray:
    rows, cols = matrix.shape
    output = np.zeros(rows + cols - 1, dtype=float)
    counts = np.zeros_like(output)
    for row in range(rows):
        output[row : row + cols] += matrix[row]
        counts[row : row + cols] += 1.0
    return output / counts


def ssa_reconstruct(signal: np.ndarray, L: int = SSA_L, rank: int = SSA_R) -> np.ndarray:
    """Reconstruct a 1-D series with the paper's fixed SSA rank rule."""
    x = np.asarray(signal, dtype=float)
    if x.ndim != 1 or x.size < L:
        raise ValueError(f"SSA requires a one-dimensional signal with at least L={L} samples")
    trajectory = np.column_stack([x[index : index + L] for index in range(x.size - L + 1)])
    u, singular_values, vh = np.linalg.svd(trajectory, full_matrices=False)
    keep = min(rank, singular_values.size)
    reconstructed = (u[:, :keep] * singular_values[:keep]) @ vh[:keep]
    series = _diagonal_average(reconstructed)
    return series[: x.size]


def _load_vmd():
    try:
        from vmdpy import VMD
    except ImportError as error:  # pragma: no cover - environment-specific
        raise RuntimeError("vmdpy is required for the frozen SSA+VMD adapter") from error
    return VMD


def vmd_heart_mode(signal: np.ndarray, fs_hz: float = FS_HZ) -> tuple[np.ndarray, dict[str, object]]:
    """Run fixed VMD and select the mode with maximal HR-band power.

    Mode selection is a deterministic adapter rule because the paper describes
    the physiological role of its IMFs but does not provide author code or a
    machine-readable mode-index rule for this device representation.
    """
    VMD = _load_vmd()
    x = np.asarray(signal, dtype=float)
    centered = x - np.mean(x)
    modes, _, center_frequencies = VMD(
        centered,
        alpha=VMD_ALPHA,
        tau=VMD_TAU,
        K=VMD_K,
        DC=VMD_DC,
        init=VMD_INIT,
        tol=VMD_TOL,
    )
    frequencies = np.fft.rfftfreq(x.size, d=1.0 / fs_hz)
    band = (frequencies >= HR_BAND_HZ[0]) & (frequencies <= HR_BAND_HZ[1])
    powers = []
    for mode in np.asarray(modes):
        spectrum = np.abs(np.fft.rfft(mode - np.mean(mode))) ** 2
        powers.append(float(np.sum(spectrum[band])))
    candidate_indices = [index for index in range(len(powers)) if np.any(band) and index != 0]
    if not candidate_indices:
        candidate_indices = list(range(len(powers)))
    selected = max(candidate_indices, key=lambda index: (powers[index], -index))
    return np.asarray(modes[selected], dtype=float), {
        "vmd_mode_index": int(selected),
        "vmd_center_frequencies": np.asarray(center_frequencies).tolist(),
        "vmd_hr_band_powers": powers,
        "selection_rule": "maximal_non_dc_HR_band_power; no_ECG_selection",
    }


def estimate_window(signal: np.ndarray, fs_hz: float = FS_HZ) -> tuple[float | None, dict[str, object]]:
    """Estimate HR from the fixed SSA+VMD heart mode."""
    reconstructed = ssa_reconstruct(signal)
    heart_mode, info = vmd_heart_mode(reconstructed, fs_hz)
    frequency, power = periodogram(heart_mode - np.mean(heart_mode), fs=fs_hz, window="hann", detrend=False)
    band = (frequency >= HR_BAND_HZ[0]) & (frequency <= HR_BAND_HZ[1])
    if not np.any(band):
        return None, info
    band_indices = np.flatnonzero(band)
    peak_index = int(band_indices[np.argmax(power[band])])
    info.update({"estimate_hz": float(frequency[peak_index]), "estimate_bpm": float(60.0 * frequency[peak_index])})
    return float(60.0 * frequency[peak_index]), info
