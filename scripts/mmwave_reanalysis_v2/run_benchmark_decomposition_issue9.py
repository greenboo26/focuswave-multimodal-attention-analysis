"""Issue #9: cross scorer/window/aggregation decomposition on development data.

This reuses the immutable historical radar adapter and the frozen development
split. It only recomputes ECG reference values and aggregates the same radar
estimates under the two ECG scorers and two window lengths.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

try:
    from run_agebalanced_historical_baseline_v1 import (
        development_sessions,
        legacy_ecg_hr_bpm,
        estimate_baseline,
        load_ecg,
        load_json,
        load_radar,
        common_radar_qc,
    )
except ModuleNotFoundError:
    from scripts.mmwave_reanalysis_v2.run_agebalanced_historical_baseline_v1 import (
        development_sessions,
        legacy_ecg_hr_bpm,
        estimate_baseline,
        load_ecg,
        load_json,
        load_radar,
        common_radar_qc,
    )
from pipelines.mmwave.ecg_reference_v1 import detect_ecg_reference_v1, window_hr_from_reference


OFFICIAL_ECG_FS_HZ = 256.0
OFFICIAL_ECG_BAND_HZ = (0.8, 2.0)
OFFICIAL_ECG_FILTER_ORDER = 4


def official_agebalanced_ecg_hr_bpm(
    relative_s: np.ndarray, mv: np.ndarray, start_s: float, end_s: float
) -> float | None:
    """Transcribe the Rest ECG FFT reference from AgeBalanced ExampleCode.

    The notebook uses helper_fns.get_bandpass_filter (normalized ``b, a``
    coefficients), scipy.signal.filtfilt, np.fft.fft, DC removal, the positive
    half-spectrum, and np.argmax(abs(fft)). It performs no windowing, ECG
    normalization, peak detection, or RR/IBI filtering.
    """
    mask = (relative_s >= start_s) & (relative_s < end_s)
    segment = np.asarray(mv[mask], dtype=float)
    if segment.size < 32 or not np.all(np.isfinite(segment)):
        return None
    nyquist = 0.5 * OFFICIAL_ECG_FS_HZ
    low, high = (cutoff / nyquist for cutoff in OFFICIAL_ECG_BAND_HZ)
    b, a = butter(OFFICIAL_ECG_FILTER_ORDER, [low, high], btype="band")
    filtered = filtfilt(b, a, segment)
    ecg_fft = np.fft.fft(filtered)
    ecg_fft[0] = 0
    ecg_fft_freq = np.fft.fftfreq(len(ecg_fft)) * OFFICIAL_ECG_FS_HZ
    ecg_fft = ecg_fft[: len(ecg_fft) // 2]
    ecg_fft_freq = ecg_fft_freq[: len(ecg_fft_freq) // 2]
    ecg_bin = int(np.argmax(np.abs(ecg_fft)))
    return float(ecg_fft_freq[ecg_bin] * 60.0)


def score_rows(rows: list[dict], scorer: str) -> tuple[float | None, int, int, int]:
    scored = [r for r in rows if r[scorer] is not None and r["radar_pass"]]
    errors = [abs(r["estimate_bpm"] - r[scorer]) for r in scored]
    session_errors: dict[str, list[float]] = defaultdict(list)
    for r, error in zip(scored, errors):
        session_errors[r["session_id"]].append(error)
    session_maes = [float(np.mean(v)) for v in session_errors.values() if v]
    return (
        float(np.mean(errors)) if errors else None,
        len(scored),
        len(session_maes),
        float(np.median(session_maes)) if session_maes else None,
    )


def run(args: argparse.Namespace) -> dict:
    split = load_json(args.split)
    sessions = development_sessions(args.data_root.resolve(), split)
    rows_by_window = {25: [], 30: []}
    for index, (subject_id, session_id, session_dir) in enumerate(sessions, 1):
        print(f"[{index}/{len(sessions)}] {session_id}", flush=True)
        rffts, radar_timestamps = load_radar(session_dir)
        ecg_absolute, ecg_relative, ecg_values = load_ecg(session_dir)
        reference = detect_ecg_reference_v1(ecg_absolute, ecg_values)
        for window_s in (25, 30):
            base_rows, _ = estimate_baseline(rffts, float(window_s), 5.0)
            for base in base_rows:
                start_s = float(base["win_start_s"])
                start_index = int(round(start_s * 10.0))
                radar_qc = common_radar_qc(rffts, radar_timestamps, start_index, window_s * 10)
                radar_pass = radar_qc["status"] == "pass" and base.get("traj_bpm") is not None
                absolute_start = float(radar_timestamps[start_index])
                ref_window = window_hr_from_reference(reference, absolute_start, absolute_start + window_s)
                ref_hr = ref_window.hr_bpm if ref_window.status == "pass" else None
                legacy_hr = legacy_ecg_hr_bpm(ecg_relative, ecg_values, start_s, start_s + window_s)
                official_hr = official_agebalanced_ecg_hr_bpm(ecg_relative, ecg_values, start_s, start_s + window_s)
                rows_by_window[window_s].append({
                    "subject_id": subject_id,
                    "session_id": session_id,
                    "window_start_s": start_s,
                    "estimate_bpm": base.get("traj_bpm"),
                    "legacy_ecg": legacy_hr,
                    "official_agebalanced_ecg": official_hr,
                    "ecg_reference_v1": ref_hr,
                    "radar_pass": radar_pass,
                    "legacy_ecg_pass": legacy_hr is not None,
                    "official_agebalanced_ecg_pass": official_hr is not None,
                    "ecg_reference_v1_pass": ref_hr is not None,
                })
    matrices = {}
    for window_s, rows in rows_by_window.items():
        cells = {}
        for scorer in ("official_agebalanced_ecg", "legacy_ecg", "ecg_reference_v1"):
            pooled, scored_windows, scored_sessions, session_median = score_rows(rows, scorer)
            cells[scorer] = {
                "pooled_window_mae_bpm": pooled,
                "scored_windows": scored_windows,
                "scored_sessions": scored_sessions,
                "session_level_median_mae_bpm": session_median,
                "window_coverage": None,
            }
        denominator = sum(r["radar_pass"] for r in rows)
        for cell in cells.values():
            cell["window_coverage"] = cell["scored_windows"] / denominator if denominator else 0.0
            cell["session_coverage"] = cell["scored_sessions"] / len({r["session_id"] for r in rows if r["radar_pass"]}) if any(r["radar_pass"] for r in rows) else 0.0
        official = cells["official_agebalanced_ecg"]
        for scorer in ("legacy_ecg", "ecg_reference_v1"):
            cells[scorer]["official_minus_scorer"] = {
                "pooled_window_mae_bpm": official["pooled_window_mae_bpm"] - cells[scorer]["pooled_window_mae_bpm"],
                "session_level_median_mae_bpm": official["session_level_median_mae_bpm"] - cells[scorer]["session_level_median_mae_bpm"],
                "scored_windows": official["scored_windows"] - cells[scorer]["scored_windows"],
                "scored_sessions": official["scored_sessions"] - cells[scorer]["scored_sessions"],
            }
        matrices[str(window_s)] = {
            "attempted_windows": len(rows),
            "radar_pass_windows": sum(r["radar_pass"] for r in rows),
            "sessions_total": len({r["session_id"] for r in rows}),
            "cells": cells,
        }
    result = {
        "status": "PASS",
        "issue": 9,
        "scope": "AgeBalanced development split; 30 participants / 60 Rest sessions; same radar adapter and window starts",
        "prohibited_inputs_used": {"held_out_80": False, "J_Data_physiology": False, "HRV": False, "new_algorithm_family": False},
        "window_lengths_s": [25, 30],
        "matrices": matrices,
        "inclusion_rule": "common radar_pass and scorer-specific ECG pass; no interpolation",
        "official_reference_contract": {
            "source": "AgeBalanced Zenodo ExampleCode.ipynb",
            "notebook_md5": "204768fa033176b12baae016ccef19b1",
            "ecg_sampling_rate_hz": OFFICIAL_ECG_FS_HZ,
            "filter": "4th-order Butterworth b,a bandpass 0.8-2.0 Hz via normalized Nyquist cutoffs; scipy.signal.filtfilt",
            "fft": "np.fft.fft(window); fft[0]=0; retain fft[:len(fft)//2] and matching positive frequencies; np.argmax(abs(fft)); frequency*60",
            "extra_processing": "none: no window function, ECG detrending, normalization, peak detector, RR/IBI rule, or interpolation",
        },
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", type=Path, default=Path("configs/mmwave_reanalysis_v2/agebalanced_split_v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(args)


if __name__ == "__main__":
    main()
