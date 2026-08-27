"""Frozen ECG reference implementation for MMWAVE_FORMAL_REANALYSIS_V2.

This module implements ``ecg_reference_v1`` from Benchmark Decision V1.  It
does not use radar data and does not compute HRV metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt


ECG_LOW_HZ = 0.5
ECG_HIGH_HZ = 40.0
ECG_FILTER_ORDER = 3
MIN_TIMESTAMP_MONOTONIC_RATIO = 0.995
MIN_FINITE_RATIO = 0.999
MIN_PEAK_DISTANCE_S = 0.30
NORMALIZED_PROMINENCE = 0.25
IBI_MIN_S = 0.300
IBI_MAX_S = 2.000
WINDOW_MIN_BEATS = 10
WINDOW_VALID_RATIO_MIN = 0.80


@dataclass(frozen=True)
class ECGReference:
    """Reference-QC result over one full source session."""

    timestamps_s: np.ndarray
    r_peak_times_s: np.ndarray
    valid_interval_mask: np.ndarray
    sampling_rate_hz: float | None
    timestamp_monotonic_ratio: float
    finite_ratio: float
    polarity: int | None
    status: str
    rejection_reason: str | None

    @property
    def valid_ratio(self) -> float:
        if self.valid_interval_mask.size == 0:
            return 0.0
        return float(np.mean(self.valid_interval_mask))


@dataclass(frozen=True)
class ECGWindowReference:
    """A full-session ECG reference restricted to a half-open window."""

    status: str
    rejection_reason: str | None
    hr_bpm: float | None
    beat_count: int
    interval_count: int
    valid_ratio: float


def robust_scale(values: np.ndarray) -> float:
    """Return the decision-specified 1.4826*MAD scale."""
    median = float(np.median(values))
    return float(1.4826 * np.median(np.abs(values - median)))


def estimate_sampling_rate_hz(timestamps_s: np.ndarray) -> tuple[float | None, float]:
    """Estimate sampling rate and return the positive-delta proportion."""
    if timestamps_s.size < 2:
        return None, 0.0
    delta = np.diff(timestamps_s)
    positive = delta > 0
    monotonic_ratio = float(np.mean(positive))
    if not np.any(positive):
        return None, monotonic_ratio
    median_delta = float(np.median(delta[positive]))
    return (1.0 / median_delta if median_delta > 0 else None), monotonic_ratio


def _empty_reference(
    timestamps_s: np.ndarray,
    sampling_rate_hz: float | None,
    monotonic_ratio: float,
    finite_ratio: float,
    reason: str,
) -> ECGReference:
    return ECGReference(
        timestamps_s=timestamps_s,
        r_peak_times_s=np.array([], dtype=float),
        valid_interval_mask=np.array([], dtype=bool),
        sampling_rate_hz=sampling_rate_hz,
        timestamp_monotonic_ratio=monotonic_ratio,
        finite_ratio=finite_ratio,
        polarity=None,
        status="fail",
        rejection_reason=reason,
    )


def detect_ecg_reference_v1(timestamps_s: np.ndarray, values: np.ndarray) -> ECGReference:
    """Run the frozen, radar-blind full-session ECG quality procedure.

    The historical 20-percent RR-change rule is deliberately *not* applied as
    a deletion rule.  It is consumed as a later audit flag when needed.
    """
    timestamps_s = np.asarray(timestamps_s, dtype=float)
    values = np.asarray(values, dtype=float)
    if timestamps_s.ndim != 1 or values.ndim != 1 or timestamps_s.size != values.size:
        raise ValueError("timestamps_s and values must be same-length one-dimensional arrays")
    sampling_rate_hz, monotonic_ratio = estimate_sampling_rate_hz(timestamps_s)
    finite_ratio = float(np.mean(np.isfinite(values))) if values.size else 0.0
    if timestamps_s.size < 16:
        return _empty_reference(timestamps_s, sampling_rate_hz, monotonic_ratio, finite_ratio, "TOO_SHORT")
    if monotonic_ratio < MIN_TIMESTAMP_MONOTONIC_RATIO:
        return _empty_reference(timestamps_s, sampling_rate_hz, monotonic_ratio, finite_ratio, "TIMESTAMP_NONMONOTONIC")
    if finite_ratio < MIN_FINITE_RATIO:
        return _empty_reference(timestamps_s, sampling_rate_hz, monotonic_ratio, finite_ratio, "ECG_NONFINITE")
    if sampling_rate_hz is None or sampling_rate_hz <= 2 * ECG_HIGH_HZ:
        return _empty_reference(timestamps_s, sampling_rate_hz, monotonic_ratio, finite_ratio, "ECG_SAMPLING_RATE")

    centered = values - np.median(values)
    scale = robust_scale(centered)
    if not np.isfinite(scale) or scale <= 0:
        return _empty_reference(timestamps_s, sampling_rate_hz, monotonic_ratio, finite_ratio, "ECG_FLATLINE")
    normalized = centered / scale
    sos = butter(ECG_FILTER_ORDER, [ECG_LOW_HZ, ECG_HIGH_HZ], btype="band", fs=sampling_rate_hz, output="sos")
    filtered = sosfiltfilt(sos, normalized)
    distance = max(1, round(MIN_PEAK_DISTANCE_S * sampling_rate_hz))
    positive_peaks, positive_props = find_peaks(filtered, distance=distance, prominence=NORMALIZED_PROMINENCE)
    negative_peaks, negative_props = find_peaks(-filtered, distance=distance, prominence=NORMALIZED_PROMINENCE)
    positive_prominence = float(np.median(positive_props.get("prominences", [0.0])))
    negative_prominence = float(np.median(negative_props.get("prominences", [0.0])))
    if negative_prominence > positive_prominence:
        peaks, polarity = negative_peaks, -1
    else:
        peaks, polarity = positive_peaks, 1
    peak_times = timestamps_s[peaks]
    intervals = np.diff(peak_times)
    valid = (intervals >= IBI_MIN_S) & (intervals <= IBI_MAX_S)
    if peak_times.size < 3 or np.sum(valid) < 2:
        return ECGReference(
            timestamps_s=timestamps_s,
            r_peak_times_s=peak_times,
            valid_interval_mask=valid,
            sampling_rate_hz=sampling_rate_hz,
            timestamp_monotonic_ratio=monotonic_ratio,
            finite_ratio=finite_ratio,
            polarity=polarity,
            status="fail",
            rejection_reason="ECG_TOO_FEW_VALID_INTERVALS",
        )
    return ECGReference(
        timestamps_s=timestamps_s,
        r_peak_times_s=peak_times,
        valid_interval_mask=valid,
        sampling_rate_hz=sampling_rate_hz,
        timestamp_monotonic_ratio=monotonic_ratio,
        finite_ratio=finite_ratio,
        polarity=polarity,
        status="pass",
        rejection_reason=None,
    )


def window_hr_from_reference(reference: ECGReference, start_s: float, end_s: float) -> ECGWindowReference:
    """Compute the frozen median-IBI HR inside a half-open window."""
    if reference.status != "pass":
        return ECGWindowReference("fail", reference.rejection_reason, None, 0, 0, 0.0)
    peak_times = reference.r_peak_times_s
    in_window = (peak_times >= start_s) & (peak_times < end_s)
    selected = peak_times[in_window]
    if selected.size < WINDOW_MIN_BEATS:
        return ECGWindowReference("fail", "ECG_WINDOW_TOO_FEW_BEATS", None, int(selected.size), 0, 0.0)
    intervals = np.diff(selected)
    valid = (intervals >= IBI_MIN_S) & (intervals <= IBI_MAX_S)
    valid_ratio = float(np.mean(valid)) if valid.size else 0.0
    if valid_ratio < WINDOW_VALID_RATIO_MIN or np.sum(valid) < 2:
        return ECGWindowReference("fail", "ECG_WINDOW_INVALID_INTERVALS", None, int(selected.size), int(intervals.size), valid_ratio)
    return ECGWindowReference(
        "pass",
        None,
        60.0 / float(np.median(intervals[valid])),
        int(selected.size),
        int(intervals.size),
        valid_ratio,
    )
