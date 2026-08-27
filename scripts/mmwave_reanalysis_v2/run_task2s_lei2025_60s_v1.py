"""Run the bounded Task 2S Lei-2025 SSA core comparison on development data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from pipelines.mmwave.ecg_reference_v1 import detect_ecg_reference_v1, window_hr_from_reference
from pipelines.mmwave.lei2025_ssa_harmonic_removal_v1 import remove_harmonics
from scripts.mmwave_reanalysis_v2.run_agebalanced_historical_baseline_v1 import (
    DATASET_ID, DATASET_VERSION, common_radar_qc, development_sessions, load_ecg, load_json, load_radar,
    select_top_bins, window_vitals, vote_bins, source_hash_lookup, sha256_canonical,
)
from scripts.mmwave_reanalysis_v2.run_task2r_external_50s_v1 import harmonic_classification, metrics, profile_to_bin_signals


WINDOW_S = 60.0
STEP_S = 5.0
CONFIG = {
    "task": "task2s_lei2025_ssa_harmonic_removal_v1",
    "scope": "AgeBalanced development only; 30 participants x 2 Rest sessions",
    "window_s": WINDOW_S,
    "step_s": STEP_S,
    "radar_hz": 10.0,
    "phase_difference_alignment": "np.diff with first-sample prepend; preserves N radar frames",
    "ecg_reference": "ecg_reference_v1",
    "project_route": {"source_commit": "f4a8c74d89ec28e005c537cbd5280a15dcb584e1"},
    "lei_ssa_core": {
        "implementation_class": "paper_reimplementation/adapted",
        "ssa_L": "floor(n/2)",
        "first_rank": 2,
        "harmonic_targets": [2, 3],
        "harmonic_amplitude": "std(first_two_SSA_respiratory_components)",
        "harmonic_phase": "zero_phase",
        "second_ssa_harmonic_components": 2,
        "second_ssa_denoise": "singular_value_ge_all_singular_value_mean",
        "hr_estimator": "existing_project_window_vitals_HPS_time_fusion",
    },
    "product_window_claim": False,
}


def phase_signals(rffts: np.ndarray) -> tuple[list[int], list[np.ndarray]]:
    profile = np.mean(rffts, axis=1)
    selected = select_top_bins(profile)
    signals = []
    for index in selected:
        phase = np.unwrap(np.angle(profile[:, index]))
        difference = np.diff(phase, prepend=phase[0])
        smooth = int(0.25 * 10.0)
        signals.append(np.convolve(difference, np.ones(smooth) / smooth, mode="same"))
    return selected, signals


def project_60s(rffts: np.ndarray) -> tuple[list[dict[str, object]], list[int]]:
    selected, signals = phase_signals(rffts)
    if not signals:
        return [], []
    per_bin = [window_vitals(signal, WINDOW_S, STEP_S) for signal in signals]
    return vote_bins(per_bin), selected


def lei_60s(rffts: np.ndarray) -> tuple[list[dict[str, object]], list[int]]:
    selected, signals = phase_signals(rffts)
    if not signals:
        return [], []
    per_bin = []
    infos = []
    for signal in signals:
        cleaned, info = remove_harmonics(signal)
        per_bin.append(window_vitals(cleaned, WINDOW_S, STEP_S))
        infos.append(info)
    merged = vote_bins(per_bin)
    for row in merged:
        row["lei_ssa_info"] = infos
    return merged, selected


def make_row(method_id: str, version: str, subject_id: str, session_id: str, start_s: float, estimate: float | None, radar_qc: dict[str, object], reference: object, reference_window: object, input_hash: str | None, config_hash: str, extra: dict[str, object]) -> dict[str, object]:
    scored = radar_qc["status"] == "pass" and reference_window.status == "pass" and estimate is not None
    ref_value = reference_window.hr_bpm if reference_window.status == "pass" else None
    rejection_reason = None if scored else ("ECG_QC_FAIL" if reference_window.status != "pass" else "RADAR_QC_FAIL" if radar_qc["status"] != "pass" else "METHOD_REJECTED")
    return {
        "schema_version": "per_window_benchmark_v1",
        "run_id": "task2s_agebalanced_development_60s_v1",
        "dataset_id": DATASET_ID, "dataset_version": DATASET_VERSION,
        "subject_id": subject_id, "session_id": session_id, "split": "development",
        "window_id": f"{session_id}_{int(round(start_s * 1000)):08d}",
        "window_start_s": start_s, "window_end_s": start_s + WINDOW_S, "window_length_s": 60,
        "method": {"id": method_id, "version": version, "implementation_class": "project_existing" if method_id.startswith("project") else "paper_reimplementation", "source_commit": "f4a8c74d89ec28e005c537cbd5280a15dcb584e1" if method_id.startswith("project") else None, "config_sha256": config_hash, "input_sha256": input_hash},
        "radar_qc": radar_qc,
        "reference_qc": {"ecg": {"status": reference_window.status, "available": True, "sampling_rate_hz": reference.sampling_rate_hz, "valid_ratio": reference_window.valid_ratio, "source_kind": "raw_waveform", "rejection_reason": reference_window.rejection_reason}, "rsp": {"status": "not_available", "available": False, "sampling_rate_hz": None, "valid_ratio": None, "source_kind": "none", "rejection_reason": "NO_RSP"}, "r_peaks": {"status": reference_window.status, "available": reference_window.status == "pass", "sampling_rate_hz": reference.sampling_rate_hz, "valid_ratio": reference_window.valid_ratio, "source_kind": "derived_events" if reference_window.status == "pass" else "none", "rejection_reason": reference_window.rejection_reason}},
        "sync": {"status": "pass", "timestamp_origin": "source_timestamps", "offset_ms": 0.0, "offset_source": "source_timestamps", "per_window_search_used": False},
        "hr": {"scorable": scored, "reference_value": ref_value, "estimate_value": estimate, "absolute_error": abs(estimate - ref_value) if scored else None},
        "br": {"scorable": False, "reference_value": None, "estimate_value": None, "absolute_error": None},
        "beat": {"scorable": False, "status": "blocked_hrv", "match_tolerance_ms": 75, "reference_count": None, "estimate_count": None, "matched_count": None, "precision": None, "recall": None, "f1": None, "timing_mae_ms": None, "ibi_mae_ms": None},
        "harmonic_lock": {"classification": harmonic_classification(estimate, ref_value) if scored else "not_assessable", "reference_basis": "ecg_hr" if ref_value is not None else "none", "tolerance_bpm": 3.0 if ref_value is not None else None},
        "outcome_status": "scored" if scored else "rejected", "rejection_reason": rejection_reason,
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
    source_hashes = source_hash_lookup(provenance)
    sessions = development_sessions(data_root, split)
    config_hash = sha256_canonical(CONFIG)
    project_rows: list[dict[str, object]] = []
    lei_rows: list[dict[str, object]] = []
    attempted_sessions = 0
    for index, (subject_id, session_id, session_dir) in enumerate(sessions, start=1):
        print(f"[{index}/{len(sessions)}] {session_id}", flush=True)
        rffts, timestamps = load_radar(session_dir)
        project, selected_project = project_60s(rffts)
        lei, selected_lei = lei_60s(rffts)
        if project and lei:
            attempted_sessions += 1
        input_hash = source_hashes.get((session_dir.relative_to(data_root) / "radar_rFFTs.zlib").as_posix())
        absolute_ecg, _, values = load_ecg(session_dir)
        reference = detect_ecg_reference_v1(absolute_ecg, values)
        for project_row, lei_row in zip(project, lei):
            start_s = float(project_row["win_start_s"])
            start_index = int(round(start_s * 10))
            radar_qc = common_radar_qc(rffts, timestamps, start_index, int(WINDOW_S * 10))
            reference_window = window_hr_from_reference(reference, timestamps[start_index], timestamps[start_index] + WINDOW_S)
            project_rows.append(make_row("project_historical_route_60s", "f4a8c74_legacy_core_60s_adapter_v1", subject_id, session_id, start_s, project_row["traj_bpm"], radar_qc, reference, reference_window, input_hash, config_hash, {"selected_bins": selected_project, "legacy_quality": project_row["legacy_quality"], "legacy_fields": project_row}))
            lei_rows.append(make_row("lei2025_ssa_harmonic_removal_60s", "lei2025_ssa_core_adapted_v1", subject_id, session_id, start_s, lei_row["traj_bpm"], radar_qc, reference, reference_window, input_hash, config_hash, {"selected_bins": selected_lei, "lei_ssa_info": lei_row.get("lei_ssa_info", [])}))
    # The historical Task2R summarizer predates the frozen schema and reads
    # failure_mode; adapt only its in-memory view to rejection_reason so that
    # persisted rows remain per_window_benchmark_v1-compliant.
    project_metrics = metrics([dict(row, failure_mode=row["rejection_reason"]) for row in project_rows])
    lei_metrics = metrics([dict(row, failure_mode=row["rejection_reason"]) for row in lei_rows])
    for metric, rows in ((project_metrics, project_rows), (lei_metrics, lei_rows)):
        metric["extreme_error_definition"] = "absolute_error_ge_30_bpm"
        metric["extreme_error_count_abs_error_ge_30_bpm"] = sum(
            1 for row in rows
            if row.get("outcome_status") == "scored"
            and float(row["hr"]["absolute_error"]) >= 30.0
        )
    report = {"status": "PASS_DEVELOPMENT_ONLY", "task": "Task 2S", "scope": "AgeBalanced development only; 30 participants / 60 Rest sessions", "config_sha256": config_hash, "parameters": CONFIG, "session_summary": {"total_development_sessions": len(sessions), "sessions_with_60s_windows": attempted_sessions}, "project_historical_route_60s": project_metrics, "lei2025_ssa_harmonic_removal_60s": lei_metrics, "comparison": {"mae_delta_lei_minus_project_bpm": lei_metrics.get("mae_bpm") - project_metrics.get("mae_bpm") if lei_metrics.get("mae_bpm") is not None and project_metrics.get("mae_bpm") is not None else None, "coverage_delta_lei_minus_project": lei_metrics.get("coverage", 0.0) - project_metrics.get("coverage", 0.0)}, "respiratory_harmonic_status": "NOT_ASSESSABLE_WITHOUT_RSP", "product_window_claim": False, "heldout_80_access": False}
    write_jsonl(output_dir / "method_native_lei2025_60s_project_rows.jsonl", project_rows)
    write_jsonl(output_dir / "method_native_lei2025_60s_lei_rows.jsonl", lei_rows)
    (output_dir / "task2s_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "task2s_config.json").write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provenance", default="configs/mmwave_reanalysis_v2/agebalanced_provenance_v1.json", type=Path)
    parser.add_argument("--split", default="configs/mmwave_reanalysis_v2/agebalanced_split_v1.json", type=Path)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({"status": report["status"], "config_sha256": report["config_sha256"], "project_mae": report["project_historical_route_60s"].get("mae_bpm"), "lei_mae": report["lei2025_ssa_harmonic_removal_60s"].get("mae_bpm")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
