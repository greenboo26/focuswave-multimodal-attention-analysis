"""Lei 2025 SSA respiratory-harmonic-removal core, paper reimplementation.

The paper's author code is unavailable.  Uniquely unrecovered choices are
explicitly returned in ``missing_evidence`` and are never ECG-driven.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import periodogram


FS_HZ = 10.0
RESP_BAND_HZ = (0.1, 0.7)
SSA_FIRST_RANK = 2
HARMONIC_COMPONENTS_PER_TARGET = 2


def _diagonal_average(matrix: np.ndarray) -> np.ndarray:
    rows, cols = matrix.shape
    output = np.zeros(rows + cols - 1, dtype=float)
    counts = np.zeros_like(output)
    for row in range(rows):
        output[row : row + cols] += matrix[row]
        counts[row : row + cols] += 1.0
    return output / counts


def ssa_components(signal: np.ndarray, L: int) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(signal, dtype=float)
    if x.ndim != 1 or x.size < L:
        raise ValueError(f"SSA requires N >= L; got N={x.size}, L={L}")
    trajectory = np.column_stack([x[index : index + L] for index in range(x.size - L + 1)])
    left, singular_values, right = np.linalg.svd(trajectory, full_matrices=False)
    components = []
    for index, singular_value in enumerate(singular_values):
        elementary = singular_value * np.outer(left[:, index], right[index])
        components.append(_diagonal_average(elementary)[: x.size])
    return np.asarray(components), np.asarray(singular_values)


def _dominant_frequency(component: np.ndarray, fs_hz: float) -> tuple[float | None, float]:
    frequency, power = periodogram(component - np.mean(component), fs=fs_hz, detrend=False)
    band = (frequency >= 0.05) & (frequency <= 3.0)
    if not np.any(band):
        return None, 0.0
    indices = np.flatnonzero(band)
    index = int(indices[np.argmax(power[band])])
    return float(frequency[index]), float(power[index])


def estimate_respiratory_frequency(signal: np.ndarray, fs_hz: float = FS_HZ) -> float | None:
    frequency, power = periodogram(signal - np.mean(signal), fs=fs_hz, detrend=False)
    band = (frequency >= RESP_BAND_HZ[0]) & (frequency <= RESP_BAND_HZ[1])
    if not np.any(band):
        return None
    indices = np.flatnonzero(band)
    return float(frequency[indices[np.argmax(power[band])]])


def remove_harmonics(signal: np.ndarray, fs_hz: float = FS_HZ) -> tuple[np.ndarray, dict[str, object]]:
    """Apply the disclosed Lei-2025 SSA core to one window."""
    x = np.asarray(signal, dtype=float)
    L = int(np.floor(x.size / 2))
    first_components, first_singular_values = ssa_components(x, L)
    respiratory = np.sum(first_components[:SSA_FIRST_RANK], axis=0)
    fr = estimate_respiratory_frequency(respiratory, fs_hz)
    if fr is None:
        return x.copy(), {
            "ssa_L": L,
            "first_rank": SSA_FIRST_RANK,
            "respiratory_frequency_hz": None,
            "harmonic_components_removed": [],
            "singular_value_mean": None,
            "missing_evidence": ["RESPIRATORY_FREQUENCY_NOT_FOUND"],
        }

    # Paper does not expose amplitude or phase selection.  Fixed minimal rule:
    # one standard deviation of the first SSA respiratory reconstruction and
    # zero phase.  This is deliberately not tuned against ECG.
    amplitude = float(np.std(respiratory))
    time = np.arange(x.size, dtype=float) / fs_hz
    enhanced = x + amplitude * np.sin(2.0 * np.pi * 2.0 * fr * time)
    enhanced += amplitude * np.sin(2.0 * np.pi * 3.0 * fr * time)

    second_components, second_singular_values = ssa_components(enhanced, L)
    component_frequencies = []
    component_powers = []
    for component in second_components:
        frequency, power = _dominant_frequency(component, fs_hz)
        component_frequencies.append(frequency)
        component_powers.append(power)

    frequency_resolution = fs_hz / x.size
    tolerance = max(0.05, 2.0 * frequency_resolution)
    removed: list[int] = []
    target_details = {}
    for harmonic_number in (2, 3):
        target = harmonic_number * fr
        candidates = [
            index for index, frequency in enumerate(component_frequencies)
            if frequency is not None and abs(frequency - target) <= tolerance
        ]
        candidates.sort(key=lambda index: (-component_powers[index], index))
        selected = candidates[:HARMONIC_COMPONENTS_PER_TARGET]
        removed.extend(selected)
        target_details[str(harmonic_number)] = {"target_hz": target, "candidate_indices": selected}

    singular_mean = float(np.mean(second_singular_values))
    keep = [index for index, value in enumerate(second_singular_values) if value >= singular_mean and index not in removed]
    if not keep:
        keep = [index for index, value in enumerate(second_singular_values) if index not in removed]
    cleaned = np.sum(second_components[keep], axis=0) if keep else x.copy()
    return cleaned, {
        "ssa_L": L,
        "first_rank": SSA_FIRST_RANK,
        "first_singular_values": first_singular_values[:SSA_FIRST_RANK].tolist(),
        "respiratory_frequency_hz": fr,
        "harmonic_amplitude_rule": "std(first_two_SSA_respiratory_components)",
        "harmonic_phase_rule": "zero_phase",
        "harmonic_component_tolerance_hz": tolerance,
        "harmonic_target_details": target_details,
        "harmonic_components_removed": sorted(set(removed)),
        "component_frequencies_hz": component_frequencies,
        "singular_value_mean": singular_mean,
        "denoise_rule": "retain_second_SSA_components_with_singular_value_ge_mean_excluding_harmonics",
        "kept_components": keep,
        "missing_evidence": ["AUTHOR_CODE_UNAVAILABLE", "HARMONIC_AMPLITUDE_PHASE_NOT_UNIQUELY_REPORTED", "EXACT_COMPONENT_INDEX_RULE_NOT_MACHINE_READABLE"],
    }
