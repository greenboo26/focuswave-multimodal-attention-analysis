"""Aggregate the local-only baseline audit without exposing session identifiers."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def nums(rows: list[dict], key: str) -> np.ndarray:
    values = []
    for row in rows:
        value = row.get(key, "")
        if value not in ("", None):
            try:
                x = float(value)
                if np.isfinite(x):
                    values.append(x)
            except ValueError:
                pass
    return np.asarray(values, dtype=float)


def stats(rows: list[dict], key: str) -> dict:
    x = nums(rows, key)
    if not len(x):
        return {"n": 0}
    return {
        "n": int(len(x)),
        "min": float(np.min(x)),
        "p25": float(np.percentile(x, 25)),
        "median": float(np.median(x)),
        "p75": float(np.percentile(x, 75)),
        "p95": float(np.percentile(x, 95)),
        "max": float(np.max(x)),
        "mean": float(np.mean(x)),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, required=True)
    args = parser.parse_args()
    session_path = args.audit_dir / "baseline_session_audit.csv"
    window_path = args.audit_dir / "baseline_window_diagnostics_30s_audit_only.csv"
    sessions, windows = read_csv(session_path), read_csv(window_path)
    observed_sessions = [r for r in sessions if r["session_status"] == "OBSERVED"]
    marked_sessions = [r for r in sessions if r.get("timeline_available", "").lower() == "true"]
    observed_windows = [r for r in windows if r["window_status"] == "OBSERVED"]

    availability = []
    for batch in ("ALL", "J", "E"):
        group = sessions if batch == "ALL" else [r for r in sessions if r["batch"] == batch]
        counts = Counter(r["session_status"] for r in group)
        availability.append({
            "batch": batch,
            "frozen_sessions": len(group),
            "observed_sessions": counts.get("OBSERVED", 0),
            "structural_missing_sessions": counts.get("STRUCTURAL_MISSING", 0),
            "qc_fail_sessions": counts.get("QC_FAIL", 0),
            "availability_fraction": counts.get("OBSERVED", 0) / len(group),
        })
    with (args.audit_dir / "baseline_availability_summary.csv").open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(availability[0]))
        writer.writeheader(); writer.writerows(availability)

    missing_reasons = Counter()
    for row in sessions:
        if row["session_status"] != "OBSERVED":
            reason = row.get("failure_reason", "")
            if "master_timeline.csv" in reason:
                missing_reasons["master_timeline_absent"] += 1
            elif "no timestamps csv" in reason:
                missing_reasons["timestamp_csv_absent"] += 1
            elif "missing DLL host receive timestamp column" in reason:
                missing_reasons["timestamp_csv_empty"] += 1
            else:
                missing_reasons[reason or "unknown"] += 1

    bin_values = nums(observed_windows, "hr_selected_bin")
    hr_values = nums(observed_windows, "hr_fused_bpm_median")
    br_values = nums(observed_windows, "breath_rate_bpm_median")
    participant_ids = set()
    for filename in ("mmwave_probe_merge_ready.csv", "mmwave_probe_merge_ready_E.csv"):
        candidate = args.audit_dir.parent / filename
        if candidate.exists():
            participant_ids.update(r["repeat_participant_id"] for r in read_csv(candidate) if r.get("repeat_participant_id", "").strip())

    metric_keys = [
        "marker_envelope_ms", "marker_envelope_excess_over_logged_ms", "logged_rest_duration_s",
        "inferred_rest_frame_count", "inferred_rest_timestamp_span_ms", "inferred_rest_median_interval_ms",
        "inferred_rest_p95_interval_ms", "inferred_rest_gap_gt20ms", "inferred_rest_gap_gt50ms",
        "inferred_rest_gap_gt100ms", "inferred_rest_frame_id_gap_count", "inferred_rest_nominal_coverage_fraction",
        "hr_pair_persistence", "hr_bin_persistence", "hr_channel_persistence", "hr_unique_pairs",
        "hr_median_abs_bin_deviation_from_mode", "hr_longest_modal_pair_run",
    ]
    window_metric_keys = [
        "timestamp_coverage_fraction", "hr_freq_bpm_median", "hr_time_bpm_median", "hr_fused_bpm_median",
        "breath_rate_bpm_median", "hr_usable_window_fraction", "hr_mean_confidence", "motion_proxy",
        "hr_selection_score", "hr_selection_margin", "hr_selector_snr", "hr_phase_stability",
        "hr_target_power_mean", "hr_target_power_contrast_db", "hr_selected_bin", "hr_selected_channel",
    ]
    summary = {
        "schema": "focuswave_mmwave_baseline_personalization_audit_summary_v1",
        "denominators": {
            "frozen_sessions": len(sessions),
            "repeat_participant_groups_from_frozen_tables": len(participant_ids),
            "marked_sessions": len(marked_sessions),
            "observed_sessions": len(observed_sessions),
            "audit_windows_expected_for_observed_sessions": len(observed_sessions) * 6,
            "audit_windows_observed": len(observed_windows),
        },
        "availability": availability,
        "missing_reasons": dict(missing_reasons),
        "session_metrics": {key: stats(observed_sessions if not key.startswith("marker_") and key != "logged_rest_duration_s" else marked_sessions, key) for key in metric_keys},
        "window_metrics": {key: stats(observed_windows, key) for key in window_metric_keys},
        "selector_contract_descriptives": {
            "historical_gate_bins_9_to_40_windows": int(np.count_nonzero((bin_values >= 9) & (bin_values <= 40))),
            "historical_gate_bins_9_to_40_fraction": float(np.mean((bin_values >= 9) & (bin_values <= 40))),
            "outside_historical_gate_windows": int(np.count_nonzero((bin_values < 9) | (bin_values > 40))),
            "current_producer_hr_range_48_to_120_count": int(np.count_nonzero((hr_values >= 48) & (hr_values <= 120))),
            "current_producer_hr_range_48_to_120_denominator": int(len(hr_values)),
            "current_producer_br_range_6_to_30_count": int(np.count_nonzero((br_values >= 6) & (br_values <= 30))),
            "current_producer_br_range_6_to_30_denominator": int(len(br_values)),
        },
        "scientific_boundary": "Descriptive producer-range coverage is not ECG validation and does not admit HR/BR as formal outcomes.",
        "source_hashes": {session_path.name: sha256(session_path), window_path.name: sha256(window_path)},
    }
    summary_path = args.audit_dir / "baseline_audit_summary.json"
    with summary_path.open("x", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, allow_nan=False)
    manifest_path = args.audit_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path, rows in ((args.audit_dir / "baseline_availability_summary.csv", len(availability)), (summary_path, 1)):
        manifest["outputs"][path.name] = {"sha256": sha256(path), "rows": rows}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
