"""Run the bounded Task 2R 50 s project-vs-SSA+VMD comparison.

This is a method-native external artifact, not the 30 s product schema.  It
uses development participants only and writes no data into the repository.
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

from pipelines.mmwave.ssa_vmd_reference_v1 import estimate_window
from scripts.mmwave_reanalysis_v2.run_agebalanced_historical_baseline_v1 import (
    DATASET_ID,
    DATASET_VERSION,
    common_radar_qc,
    development_sessions,
    load_ecg,
    load_json,
    load_radar,
    select_top_bins,
    window_vitals,
    source_hash_lookup,
    sha256_canonical,
    window_hr_from_reference,
)
from pipelines.mmwave.ecg_reference_v1 import detect_ecg_reference_v1


WINDOW_S = 50.0
STEP_S = 5.0
CONFIG = {
    "task": "task2r_external_reference_50s_v1",
    "scope": "AgeBalanced development only; 30 participants x 2 Rest sessions",
    "window_s": WINDOW_S,
    "step_s": STEP_S,
    "radar_hz": 10.0,
    "phase_difference_alignment": "np.diff with first-sample prepend; preserves N radar frames so exact 500-frame recordings yield one 50 s window",
    "ecg_reference": "ecg_reference_v1",
    "project_route": {"source_commit": "f4a8c74d89ec28e005c537cbd5280a15dcb584e1"},
    "ssa_vmd": {
        "implementation_class": "paper_reimplementation/adapted",
        "ssa_L": 400,
        "ssa_rank": 40,
        "vmd_K": 5,
        "vmd_alpha": 1000,
        "vmd_tau": 0,
        "vmd_DC": 1,
        "vmd_init": 0,
        "vmd_tol": 1e-6,
        "mode_selection": "maximal_non_dc_HR_band_power; no_ECG_selection",
        "frequency_estimator": "periodogram_HR_band_peak",
    },
    "product_window_claim": False,
}


def profile_to_bin_signals(rffts: np.ndarray) -> tuple[list[int], list[np.ndarray]]:
    profile = np.mean(rffts, axis=1)
    selected = select_top_bins(profile)
    signals = []
    for index in selected:
        phase = np.unwrap(np.angle(profile[:, index]))
        difference = np.diff(phase, prepend=phase[0])
        smoothing_frames = int(0.25 * 10.0)
        signals.append(np.convolve(difference, np.ones(smoothing_frames) / smoothing_frames, mode="same"))
    return selected, signals


def estimate_project_50s(rffts: np.ndarray, window_s: float, step_s: float) -> tuple[list[dict[str, object]], list[int]]:
    """Run the historical estimator with the Task 2R length-preserving adapter."""
    profile = np.mean(rffts, axis=1)
    selected_bins, signals = profile_to_bin_signals(rffts)
    if not selected_bins:
        return [], []
    rows = window_vitals(signals[0], window_s, step_s)
    per_bin = [rows]
    for signal in signals[1:]:
        per_bin.append(window_vitals(signal, window_s, step_s))
    from scripts.mmwave_reanalysis_v2.run_agebalanced_historical_baseline_v1 import vote_bins

    return vote_bins(per_bin), selected_bins


def median_vote(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def estimate_external(rffts: np.ndarray, window_s: float, step_s: float) -> list[dict[str, object]]:
    selected_bins, signals = profile_to_bin_signals(rffts)
    frame_count = int(window_s * 10)
    step_count = int(step_s * 10)
    rows = []
    for start in range(0, len(rffts) - frame_count + 1, step_count):
        estimates = []
        mode_info = []
        for signal in signals:
            estimate, info = estimate_window(signal[start : start + frame_count])
            if estimate is not None:
                estimates.append(estimate)
            mode_info.append(info)
        rows.append({"window_start_s": start / 10.0, "estimate_bpm": median_vote(estimates), "selected_bins": selected_bins, "mode_info": mode_info})
    return rows


def harmonic_classification(estimate: float | None, reference: float | None) -> str:
    if estimate is None or reference is None:
        return "not_assessable"
    tolerance = max(3.0, 0.05 * reference)
    if abs(estimate - reference) <= tolerance:
        return "none"
    if abs(estimate - 2.0 * reference) <= max(3.0, 0.05 * 2.0 * reference):
        return "two_x_hr"
    if abs(estimate - 0.5 * reference) <= max(3.0, 0.05 * 0.5 * reference):
        return "half_x_hr"
    return "none"


def make_row(method_id: str, version: str, subject_id: str, session_id: str, start_s: float, estimate: float | None, radar_qc: dict[str, object], reference: object, reference_window: object, input_hash: str | None, config_hash: str, extra: dict[str, object] | None = None) -> dict[str, object]:
    scored = radar_qc["status"] == "pass" and reference_window.status == "pass" and estimate is not None
    ref_value = reference_window.hr_bpm if reference_window.status == "pass" else None
    return {
        "schema_version": "method_native_external_50s_v1",
        "comparison_role": "method_native_external",
        "product_window_claim": False,
        "run_id": "task2r_agebalanced_development_50s_v1",
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "subject_id": subject_id,
        "session_id": session_id,
        "split": "development",
        "window_id": f"{session_id}_{int(round(start_s * 1000)):08d}",
        "window_start_s": start_s,
        "window_end_s": start_s + WINDOW_S,
        "window_s": WINDOW_S,
        "method": {"id": method_id, "version": version, "implementation_class": "project_existing" if method_id.startswith("project") else "paper_reimplementation/adapted", "config_sha256": config_hash, "input_sha256": input_hash},
        "radar_qc": radar_qc,
        "reference_qc": {"ecg": {"status": reference_window.status, "available": True, "sampling_rate_hz": reference.sampling_rate_hz, "valid_ratio": reference_window.valid_ratio, "source_kind": "raw_waveform", "rejection_reason": reference_window.rejection_reason}, "rsp": {"status": "not_available", "available": False, "source_kind": "none", "rejection_reason": "NO_RSP"}},
        "sync": {"status": "pass", "timestamp_origin": "source_timestamps", "offset_ms": 0.0, "per_window_search_used": False},
        "hr": {"scorable": scored, "reference_value": ref_value, "estimate_value": estimate, "absolute_error": abs(estimate - ref_value) if scored else None},
        "harmonic_lock": {"classification": harmonic_classification(estimate, ref_value), "respiratory_harmonic": "NOT_ASSESSABLE", "reference_basis": "ecg_hr" if ref_value is not None else "none"},
        "failure_mode": None if scored else ("ECG_QC_FAIL" if reference_window.status != "pass" else "RADAR_QC_FAIL" if radar_qc["status"] != "pass" else "METHOD_REJECTED"),
        "outcome_status": "scored" if scored else "rejected",
        "extra": extra or {},
    }


def metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    scored = [row for row in rows if row["outcome_status"] == "scored"]
    pairs = [(float(row["hr"]["estimate_value"]), float(row["hr"]["reference_value"])) for row in scored]
    if not pairs:
        return {"attempted": len(rows), "scored": 0, "coverage": 0.0}
    estimates = np.array([pair[0] for pair in pairs])
    references = np.array([pair[1] for pair in pairs])
    errors = np.abs(estimates - references)
    differences = estimates - references
    pearson = float(pearsonr(estimates, references).statistic) if len(pairs) >= 2 else None
    spearman = float(spearmanr(estimates, references).statistic) if len(pairs) >= 2 else None
    strata = defaultdict(list)
    for row, error in zip(scored, errors):
        strata[row["radar_qc"]["quality_stratum"]].append(float(error))
    return {
        "attempted": len(rows), "scored": len(scored), "coverage": len(scored) / len(rows),
        "mae_bpm": float(np.mean(errors)), "median_ae_bpm": float(np.median(errors)), "rmse_bpm": float(np.sqrt(np.mean((estimates - references) ** 2))),
        "pearson_r": pearson, "spearman_rho": spearman, "bland_altman_bias_bpm": float(np.mean(differences)), "bland_altman_loa_bpm": [float(np.mean(differences) - 1.96 * np.std(differences, ddof=1)), float(np.mean(differences) + 1.96 * np.std(differences, ddof=1))] if len(differences) >= 2 else None,
        "p90_ae_bpm": float(np.percentile(errors, 90)),
        "harmonic_locks": dict(Counter(row["harmonic_lock"]["classification"] for row in scored)),
        "quality": {key: {"n": len(value), "mae_bpm": float(np.mean(value)), "median_ae_bpm": float(np.median(value))} for key, value in sorted(strata.items())},
        "failures": dict(Counter(row["failure_mode"] for row in rows if row["failure_mode"])),
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def run(args: argparse.Namespace) -> dict[str, object]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    data_root = args.data_root.resolve()
    split = load_json(args.split)
    provenance = load_json(args.provenance)
    sessions = development_sessions(data_root, split)
    source_hashes = source_hash_lookup(provenance)
    config_hash = sha256_canonical(CONFIG)
    project_rows: list[dict[str, object]] = []
    external_rows: list[dict[str, object]] = []
    for index, (subject_id, session_id, session_dir) in enumerate(sessions, start=1):
        print(f"[{index}/{len(sessions)}] {session_id}", flush=True)
        rffts, timestamps = load_radar(session_dir)
        ecg_absolute, _, ecg_values = load_ecg(session_dir)
        ecg_reference = detect_ecg_reference_v1(ecg_absolute, ecg_values)
        input_hash = source_hashes.get((session_dir.relative_to(data_root) / "radar_rFFTs.zlib").as_posix())
        historical, selected_bins = estimate_project_50s(rffts, WINDOW_S, STEP_S)
        external = estimate_external(rffts, WINDOW_S, STEP_S)
        for project, external_row in zip(historical, external):
            start_s = float(project["win_start_s"])
            start_index = int(round(start_s * 10))
            radar_qc = common_radar_qc(rffts, timestamps, start_index, int(WINDOW_S * 10))
            reference_window = window_hr_from_reference(ecg_reference, timestamps[start_index], timestamps[start_index] + WINDOW_S)
            project_rows.append(make_row("project_historical_route_50s", "f4a8c74_legacy_core_50s_adapter_v1", subject_id, session_id, start_s, project["traj_bpm"], radar_qc, ecg_reference, reference_window, input_hash, config_hash, {"selected_bins": selected_bins, "legacy_quality": project["legacy_quality"], "legacy_fields": project}))
            external_rows.append(make_row("ssa_vmd_ee_pcc_50s", "ssa_vmd_paper_reimplementation_adapted_v1", subject_id, session_id, start_s, external_row["estimate_bpm"], radar_qc, ecg_reference, reference_window, input_hash, config_hash, {"selected_bins": external_row["selected_bins"], "mode_info": external_row["mode_info"]}))
    project_metrics = metrics(project_rows)
    external_metrics = metrics(external_rows)
    report = {"status": "PASS_DEVELOPMENT_ONLY" if external_metrics.get("scored", 0) else "BLOCKED", "task": "Task 2R", "scope": "AgeBalanced development only; 30 participants / 60 Rest sessions", "config_sha256": config_hash, "parameters": CONFIG, "project_historical_route_50s": project_metrics, "ssa_vmd_ee_pcc_50s": external_metrics, "comparison": {"mae_delta_external_minus_project_bpm": external_metrics.get("mae_bpm") - project_metrics.get("mae_bpm") if external_metrics.get("mae_bpm") is not None and project_metrics.get("mae_bpm") is not None else None, "coverage_delta_external_minus_project": external_metrics.get("coverage", 0.0) - project_metrics.get("coverage", 0.0)}, "respiratory_harmonic_status": "NOT_ASSESSABLE_WITHOUT_RSP", "product_window_claim": False, "heldout_80_access": False}
    write_jsonl(output_dir / "method_native_external_50s_project_rows.jsonl", project_rows)
    write_jsonl(output_dir / "method_native_external_50s_ssa_vmd_rows.jsonl", external_rows)
    (output_dir / "task2r_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "task2r_config.json").write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provenance", default="configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json", type=Path)
    parser.add_argument("--split", default="configs/mmwave_reanalysis_v2/agebalanced_split_v1.json", type=Path)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({"status": report["status"], "config_sha256": report["config_sha256"], "project_mae": report["project_historical_route_50s"].get("mae_bpm"), "ssa_vmd_mae": report["ssa_vmd_ee_pcc_50s"].get("mae_bpm")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
