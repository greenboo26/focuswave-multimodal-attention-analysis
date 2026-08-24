"""ECG beat-level evaluator for the RS6240 multichannel ablation.

The evaluator deliberately separates three operations:

1. Estimate one shared time offset from pooled S1 windows.
2. Match ECG and radar beat events monotonically and one-to-one.
3. Compute IBI/RMSSD only from adjacent matched beat events.

It does not perform per-window or per-model offset fitting, and it never
matches IBI arrays by ordinal position after a missed beat.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


Pair = tuple[int, int, float]
State = tuple[int, float, list[Pair]]


def _prefer(left: State | None, right: State | None) -> State | None:
    """Choose maximum cardinality, then minimum total absolute timing error."""

    if left is None:
        return right
    if right is None:
        return left
    if left[0] != right[0]:
        return left if left[0] > right[0] else right
    if not np.isclose(left[1], right[1]):
        return left if left[1] < right[1] else right
    # Deterministic tie break: preserve the left-hand path.
    return left


def match_monotonic_one_to_one(
    ecg_s: Sequence[float],
    radar_s: Sequence[float],
    offset_s: float,
    tolerance_s: float = 0.15,
) -> list[Pair]:
    """Return monotonic one-to-one matches under a fixed global offset.

    The dynamic program maximizes the number of matched events and then
    minimizes total absolute timing error. ``radar_s`` is shifted by
    ``offset_s`` before matching. Returned pairs are ``(radar_index,
    ecg_index, absolute_error_seconds)`` in chronological order.
    """

    ecg = np.asarray(ecg_s, dtype=float)
    radar = np.asarray(radar_s, dtype=float) + float(offset_s)
    if ecg.size == 0 or radar.size == 0:
        return []
    if np.any(np.diff(ecg) < 0) or np.any(np.diff(radar) < 0):
        raise ValueError("Beat event arrays must be sorted in ascending time")

    n, m = len(ecg), len(radar)
    dp: list[list[State | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = (0, 0.0, [])

    for i in range(n + 1):
        for j in range(m + 1):
            current = dp[i][j]
            if current is None:
                continue
            if i < n:
                dp[i + 1][j] = _prefer(dp[i + 1][j], current)
            if j < m:
                dp[i][j + 1] = _prefer(dp[i][j + 1], current)
            if i < n and j < m:
                error = abs(float(radar[j] - ecg[i]))
                if error <= tolerance_s:
                    matched: State = (
                        current[0] + 1,
                        current[1] + error,
                        current[2] + [(j, i, error)],
                    )
                    dp[i + 1][j + 1] = _prefer(dp[i + 1][j + 1], matched)

    result = dp[n][m]
    return result[2] if result is not None else []


def estimate_shared_offset(
    windows: Iterable[tuple[Sequence[float], Sequence[float]]],
    tolerance_s: float = 0.15,
    search_min_s: float = -1.0,
    search_max_s: float = 1.0,
    step_s: float = 0.005,
) -> dict:
    """Estimate one offset from pooled baseline windows.

    ``windows`` contains ``(ecg_peaks, radar_peaks)`` pairs. The caller is
    expected to pass S1 only; the resulting scalar is then applied unchanged
    to every ablation model and every window.
    """

    pairs = list(windows)
    if not pairs:
        return {
            "offset_s": 0.0,
            "tolerance_s": tolerance_s,
            "pooled_matched_count": 0,
            "pooled_timing_mae_ms": None,
            "search": [search_min_s, search_max_s, step_s],
        }

    best: tuple[tuple[int, float, float], float, int] | None = None
    grid = np.arange(search_min_s, search_max_s + step_s / 2.0, step_s)
    for offset in grid:
        count = 0
        error = 0.0
        for ecg_s, radar_s in pairs:
            matched = match_monotonic_one_to_one(ecg_s, radar_s, float(offset), tolerance_s)
            count += len(matched)
            error += sum(item[2] for item in matched)
        # Maximize cardinality, minimize error, then prefer the smallest
        # absolute correction so an unnecessary large offset is not selected.
        score = (count, -error, -abs(float(offset)))
        if best is None or score > best[0]:
            best = (score, float(offset), count)

    assert best is not None
    offset = best[1]
    all_errors: list[float] = []
    for ecg_s, radar_s in pairs:
        all_errors.extend(item[2] for item in match_monotonic_one_to_one(ecg_s, radar_s, offset, tolerance_s))
    return {
        "offset_s": offset,
        "tolerance_s": tolerance_s,
        "pooled_matched_count": best[2],
        "pooled_timing_mae_ms": float(np.mean(all_errors) * 1000.0) if all_errors else None,
        "search": [search_min_s, search_max_s, step_s],
        "source": "pooled S1 windows",
    }


def _rmssd(values_ms: Sequence[float]) -> float | None:
    values = np.asarray(values_ms, dtype=float)
    if len(values) < 3:
        return None
    return float(np.sqrt(np.mean(np.diff(values) ** 2)))


def evaluate_matched_beats(
    ecg_s: Sequence[float],
    radar_s: Sequence[float],
    offset_s: float,
    tolerance_s: float = 0.15,
    ibi_min_ms: float = 300.0,
    ibi_max_ms: float = 2000.0,
) -> dict:
    """Evaluate beat events and matched adjacent IBI intervals."""

    ecg = np.asarray(ecg_s, dtype=float)
    radar = np.asarray(radar_s, dtype=float)
    matched = match_monotonic_one_to_one(ecg, radar, offset_s, tolerance_s)
    adjusted_radar = radar + float(offset_s)
    errors = np.asarray([adjusted_radar[r] - ecg[e] for r, e, _ in matched], dtype=float)

    interval_pairs: list[tuple[float, float]] = []
    runs: list[list[tuple[float, float]]] = []
    current_run: list[tuple[float, float]] = []
    for (r0, e0, _), (r1, e1, _) in zip(matched, matched[1:]):
        adjacent = (e1 == e0 + 1) and (r1 == r0 + 1)
        if adjacent:
            ecg_ibi = float((ecg[e1] - ecg[e0]) * 1000.0)
            radar_ibi = float((radar[r1] - radar[r0]) * 1000.0)
            valid = (
                ibi_min_ms <= ecg_ibi <= ibi_max_ms
                and ibi_min_ms <= radar_ibi <= ibi_max_ms
            )
            if valid:
                item = (ecg_ibi, radar_ibi)
                interval_pairs.append(item)
                current_run.append(item)
                continue
        if current_run:
            runs.append(current_run)
            current_run = []
    if current_run:
        runs.append(current_run)

    if interval_pairs:
        ecg_ibi = np.asarray([item[0] for item in interval_pairs], dtype=float)
        radar_ibi = np.asarray([item[1] for item in interval_pairs], dtype=float)
        diff = radar_ibi - ecg_ibi
        ibi_mae = float(np.mean(np.abs(diff)))
        ibi_rmse = float(np.sqrt(np.mean(diff**2)))
        ibi_bias = float(np.mean(diff))
    else:
        ibi_mae = ibi_rmse = ibi_bias = None

    longest_run = max(runs, key=len) if runs else []
    matched_ecg_rmssd = _rmssd([item[0] for item in longest_run])
    matched_radar_rmssd = _rmssd([item[1] for item in longest_run])
    rmssd_error = (
        abs(matched_radar_rmssd - matched_ecg_rmssd)
        if matched_ecg_rmssd is not None and matched_radar_rmssd is not None
        else None
    )

    matched_count = len(matched)
    radar_count = len(radar)
    ecg_count = len(ecg)
    return {
        "ecg_peak_count": ecg_count,
        "radar_peak_count": radar_count,
        "matched_beat_count": matched_count,
        "beat_precision": matched_count / radar_count if radar_count else None,
        "beat_recall": matched_count / ecg_count if ecg_count else None,
        "false_beat_rate": 1.0 - matched_count / radar_count if radar_count else None,
        "timing_error_signed_mean_ms": float(np.mean(errors) * 1000.0) if len(errors) else None,
        "timing_error_mae_ms": float(np.mean(np.abs(errors)) * 1000.0) if len(errors) else None,
        "timing_error_rmse_ms": float(np.sqrt(np.mean(errors**2)) * 1000.0) if len(errors) else None,
        "alignment_offset_s": float(offset_s),
        "match_tolerance_ms": float(tolerance_s * 1000.0),
        "matched_interval_count": len(interval_pairs),
        "ibi_mae_ms_matched": ibi_mae,
        "ibi_rmse_ms_matched": ibi_rmse,
        "ibi_bias_ms_matched": ibi_bias,
        "rmssd_run_interval_count": len(longest_run),
        "ecg_rmssd_matched_ms": matched_ecg_rmssd,
        "radar_rmssd_matched_ms": matched_radar_rmssd,
        "rmssd_abs_error_ms_matched": rmssd_error,
        "rmssd_usable": matched_ecg_rmssd is not None and matched_radar_rmssd is not None,
    }

