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

from run_agebalanced_historical_baseline_v1 import (
    development_sessions,
    legacy_ecg_hr_bpm,
    estimate_baseline,
    load_ecg,
    load_json,
    load_radar,
    common_radar_qc,
)
from pipelines.mmwave.ecg_reference_v1 import detect_ecg_reference_v1, window_hr_from_reference


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
                rows_by_window[window_s].append({
                    "subject_id": subject_id,
                    "session_id": session_id,
                    "window_start_s": start_s,
                    "estimate_bpm": base.get("traj_bpm"),
                    "legacy_ecg": legacy_hr,
                    "ecg_reference_v1": ref_hr,
                    "radar_pass": radar_pass,
                    "legacy_ecg_pass": legacy_hr is not None,
                    "ecg_reference_v1_pass": ref_hr is not None,
                })
    matrices = {}
    for window_s, rows in rows_by_window.items():
        cells = {}
        for scorer in ("legacy_ecg", "ecg_reference_v1"):
            pooled, scored_windows, scored_sessions, session_median = score_rows(rows, scorer)
            cells[scorer] = {
                "pooled_window_mae_bpm": pooled,
                "scored_windows": scored_windows,
                "scored_sessions": scored_sessions,
                "session_level_median_mae_bpm": session_median,
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
