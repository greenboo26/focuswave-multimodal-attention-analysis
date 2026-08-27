"""Re-score already-run AgeBalanced HR routes against the official ECG FFT reference.

This is a reference-endpoint repair, not a new algorithm benchmark. Radar route
implementations are imported from the historical, Task2R and Task2S runners.
Only the frozen AgeBalanced development split is read.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.mmwave_reanalysis_v2.run_agebalanced_historical_baseline_v1 import (
    common_radar_qc,
    development_sessions,
    estimate_baseline,
    load_ecg,
    load_json,
    load_radar,
    sha256_canonical,
    source_hash_lookup,
)
from scripts.mmwave_reanalysis_v2.run_benchmark_decomposition_issue9 import official_agebalanced_ecg_hr_bpm
from scripts.mmwave_reanalysis_v2.run_task2r_external_50s_v1 import estimate_external, estimate_project_50s
from scripts.mmwave_reanalysis_v2.run_task2s_lei2025_60s_v1 import lei_60s, project_60s


CONFIG = {
    "task": "official_reference_existing_routes_retest_v1",
    "reference": "AgeBalanced official Rest ECG FFT transcription from Zenodo 16760684 ExampleCode.ipynb",
    "development_only": True,
    "participants": 30,
    "sessions": 60,
    "windows": {"30s": {"window_s": 30, "step_s": 5}, "50s": {"window_s": 50, "step_s": 5}, "60s": {"window_s": 60, "step_s": 5}},
    "routes": ["project_historical_route_30s", "project_historical_route_50s", "ssa_vmd_adapted_50s", "project_historical_route_60s", "lei2025_ssa_adapted_60s"],
    "selection_or_tuning": "none; route implementations and parameters are inherited from prior bounded runs",
}


def route_rows(rffts: np.ndarray, route: str) -> list[dict[str, object]]:
    if route == "project_historical_route_30s":
        rows, _ = estimate_baseline(rffts, 30.0, 5.0)
        return [{"window_start_s": row["win_start_s"], "estimate_bpm": row.get("traj_bpm"), "quality": row.get("legacy_quality")} for row in rows]
    if route == "project_historical_route_50s":
        rows, _ = estimate_project_50s(rffts, 50.0, 5.0)
        return [{"window_start_s": row["win_start_s"], "estimate_bpm": row.get("traj_bpm"), "quality": row.get("legacy_quality")} for row in rows]
    if route == "ssa_vmd_adapted_50s":
        rows = estimate_external(rffts, 50.0, 5.0)
        return [{"window_start_s": row["window_start_s"], "estimate_bpm": row.get("estimate_bpm"), "quality": None} for row in rows]
    if route == "project_historical_route_60s":
        rows, _ = project_60s(rffts)
        return [{"window_start_s": row["win_start_s"], "estimate_bpm": row.get("traj_bpm"), "quality": row.get("legacy_quality")} for row in rows]
    if route == "lei2025_ssa_adapted_60s":
        rows, _ = lei_60s(rffts)
        return [{"window_start_s": row["win_start_s"], "estimate_bpm": row.get("traj_bpm"), "quality": None} for row in rows]
    raise ValueError(route)


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    scored = [row for row in rows if row["scored"]]
    errors = np.asarray([abs(float(row["estimate_bpm"]) - float(row["official_ecg_bpm"])) for row in scored], dtype=float)
    session_errors: dict[str, list[float]] = defaultdict(list)
    strata: dict[str, list[float]] = defaultdict(list)
    locks = Counter()
    for row, error in zip(scored, errors):
        session_errors[str(row["session_id"])].append(float(error))
        strata[str(row["quality_stratum"])].append(float(error))
        estimate = float(row["estimate_bpm"])
        reference = float(row["official_ecg_bpm"])
        tolerance = max(3.0, 0.05 * reference)
        if abs(estimate - 2 * reference) <= max(3.0, 0.1 * reference):
            locks["two_x_hr"] += 1
        elif abs(estimate - 0.5 * reference) <= max(3.0, 0.025 * reference):
            locks["half_x_hr"] += 1
        else:
            locks["none"] += 1
    estimates = np.asarray([float(row["estimate_bpm"]) for row in scored], dtype=float)
    references = np.asarray([float(row["official_ecg_bpm"]) for row in scored], dtype=float)
    differences = estimates - references
    return {
        "attempted_windows": len(rows),
        "scored_windows": len(scored),
        "scored_sessions": len(session_errors),
        "coverage": len(scored) / len(rows) if rows else 0.0,
        "pooled_mae_bpm": float(np.mean(errors)) if len(errors) else None,
        "median_session_mae_bpm": float(np.median([np.mean(v) for v in session_errors.values()])) if session_errors else None,
        "rmse_bpm": float(np.sqrt(np.mean(np.square(differences)))) if len(differences) else None,
        "pearson_r": float(pearsonr(estimates, references).statistic) if len(scored) >= 2 else None,
        "spearman_rho": float(spearmanr(estimates, references).statistic) if len(scored) >= 2 else None,
        "bland_altman_bias_bpm": float(np.mean(differences)) if len(differences) else None,
        "quality": {key: {"n": len(values), "mae_bpm": float(np.mean(values))} for key, values in sorted(strata.items())},
        "harmonic_locks": dict(locks),
        "extreme_error_ge_30_bpm": int(np.sum(errors >= 30.0)) if len(errors) else 0,
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    data_root = args.data_root.resolve()
    split = load_json(args.split)
    provenance = load_json(args.provenance)
    source_hashes = source_hash_lookup(provenance)
    sessions = development_sessions(data_root, split)
    rows_by_route: dict[str, list[dict[str, object]]] = {route: [] for route in CONFIG["routes"]}
    for index, (subject_id, session_id, session_dir) in enumerate(sessions, 1):
        print(f"[{index}/{len(sessions)}] {session_id}", flush=True)
        rffts, timestamps = load_radar(session_dir)
        _, relative_ecg, ecg_values = load_ecg(session_dir)
        relative_path = (session_dir.relative_to(data_root) / "radar_rFFTs.zlib").as_posix()
        input_hash = source_hashes.get(relative_path)
        for route in CONFIG["routes"]:
            route_window_s = 30.0 if route.endswith("30s") else 50.0 if route.endswith("50s") else 60.0
            for estimate_row in route_rows(rffts, route):
                start_s = float(estimate_row["window_start_s"])
                start_index = int(round(start_s * 10.0))
                estimate = estimate_row["estimate_bpm"]
                radar_qc = common_radar_qc(rffts, timestamps, start_index, int(route_window_s * 10))
                official = official_agebalanced_ecg_hr_bpm(relative_ecg, ecg_values, start_s, start_s + route_window_s)
                scored = radar_qc["status"] == "pass" and estimate is not None and official is not None
                rows_by_route[route].append({
                    "subject_id": subject_id, "session_id": session_id, "window_start_s": start_s,
                    "window_s": route_window_s, "estimate_bpm": estimate, "official_ecg_bpm": official,
                    "scored": scored, "quality_stratum": radar_qc["quality_stratum"],
                    "radar_qc_status": radar_qc["status"], "input_sha256": input_hash,
                })
    summary = {route: summarize(rows) for route, rows in rows_by_route.items()}
    result = {"status": "PASS_DEVELOPMENT_ONLY", "config_sha256": sha256_canonical(CONFIG), "config": CONFIG, "official_reference_contract": {"source": "Zenodo 16760684 ExampleCode.ipynb", "notebook_md5": "204768fa033176b12baae016ccef19b1", "sampling_rate_hz": 256, "filter": "4th-order Butterworth 0.8-2.0 Hz, filtfilt", "scorer": "FFT positive half-spectrum argmax times 60; no window/detrend/normalization/peak detector/interpolation"}, "routes": summary, "prohibited_inputs_used": {"held_out_80": False, "J_Data": False, "HRV": False, "new_algorithm_family": False}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.rows_output:
        args.rows_output.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for route, rows in rows_by_route.items() for row in [{"route": route, **item} for item in rows]) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows-output", type=Path)
    parser.add_argument("--provenance", default="configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json", type=Path)
    parser.add_argument("--split", default="configs/mmwave_reanalysis_v2/agebalanced_split_v1.json", type=Path)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
