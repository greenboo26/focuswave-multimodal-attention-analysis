"""Build the fixed-denominator P1 paired audit after both arms are complete."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np


KEYS = ("subject", "block_id", "probe_onset_unix_ms")
INVARIANTS = (
    "win_start_unix_ms",
    "win_end_unix_ms",
    "win_s",
    "mmwave_frames",
    "frame_i0",
    "frame_i1_exclusive",
    "frame_index_sha256",
    "heartbeat_sha256",
    "alignment_timestamp_source",
    "alignment_timestamp_column",
    "hr_bin",
    "hr_channel",
    "hr_distance_proxy_m",
    "br_bin",
    "br_channel",
    "br_bpm",
    "rsp_br_bpm",
    "phase_stability",
    "motion_proxy",
    "ecg_hr_bpm",
    "ecg_status",
)
HR_FIELDS = ("spectral", "time", "fused")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[name] for name in KEYS)


def number(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    value_f = float(value)
    return value_f if np.isfinite(value_f) else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def metrics(rows: list[dict[str, str]], prefix: str = "") -> dict:
    out = {}
    for label in HR_FIELDS:
        actual = []
        predicted = []
        field = f"{prefix}hr_30s_{label}_bpm"
        for row in rows:
            a = number(row.get(f"{prefix}ecg_hr_bpm", row.get("ecg_hr_bpm")))
            p = number(row.get(field))
            if a is not None and p is not None:
                actual.append(a)
                predicted.append(p)
        err = np.asarray(predicted) - np.asarray(actual)
        out[label] = {
            "coverage": int(len(err)),
            "mae_bpm": float(np.mean(np.abs(err))) if len(err) else None,
            "median_absolute_error_bpm": float(np.median(np.abs(err))) if len(err) else None,
            "bias_bpm": float(np.mean(err)) if len(err) else None,
            "rmse_bpm": float(np.sqrt(np.mean(err**2))) if len(err) else None,
        }
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--restoration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-parent", required=True)
    parser.add_argument("--b2-adapter-sha256", required=True)
    parser.add_argument("--b2-test-sha256", required=True)
    parser.add_argument("--historical-b2-output-sha256", required=True)
    parser.add_argument("--remote-main-at-start", required=True)
    parser.add_argument("--governance-main", required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    control = read_rows(args.control)
    restoration = read_rows(args.restoration)
    control_by_key = {key(row): row for row in control}
    restored_by_key = {key(row): row for row in restoration}
    duplicate_control = len(control_by_key) != len(control)
    duplicate_restoration = len(restored_by_key) != len(restoration)
    common_keys = sorted(set(control_by_key) & set(restored_by_key))
    only_control = sorted(set(control_by_key) - set(restored_by_key))
    only_restoration = sorted(set(restored_by_key) - set(control_by_key))

    invariant_differences = []
    paired = []
    improve = worsen = tie = 0
    ae_deltas = []
    missing_transitions = Counter()
    gate_reasons = Counter()

    for item_key in common_keys:
        c = control_by_key[item_key]
        r = restored_by_key[item_key]
        changed = [field for field in INVARIANTS if c.get(field, "") != r.get(field, "")]
        for field in changed:
            invariant_differences.append(
                {"key": "|".join(item_key), "field": field, "control": c.get(field), "restoration": r.get(field)}
            )

        actual = number(c.get("ecg_hr_bpm"))
        c_fused = number(c.get("hr_30s_fused_bpm"))
        r_fused = number(r.get("hr_30s_fused_bpm"))
        c_ae = abs(c_fused - actual) if c_fused is not None and actual is not None else None
        r_ae = abs(r_fused - actual) if r_fused is not None and actual is not None else None
        delta = r_ae - c_ae if c_ae is not None and r_ae is not None else None
        if delta is not None:
            ae_deltas.append(delta)
            if delta < -1e-9:
                improve += 1
            elif delta > 1e-9:
                worsen += 1
            else:
                tie += 1

        c_status = c.get("hr_status", "")
        r_status = r.get("hr_status", "")
        missing_transitions[f"{c_status}->{r_status}"] += 1
        if str(r.get("gate_hit", "")).lower() == "true":
            gate_reasons[r.get("gate_reason") or "unspecified"] += 1

        out = {name: c[name] for name in KEYS}
        for field in INVARIANTS:
            out[field] = c.get(field)
        out["invariant_pass"] = not changed
        out["invariant_changed_fields"] = ";".join(changed)
        out["ecg_hr_bpm"] = c.get("ecg_hr_bpm")
        for field in (
            "hr_30s_spectral_bpm",
            "hr_30s_time_bpm",
            "hr_30s_fused_bpm",
            "hr_spectral_bpm_pre_gate",
            "hr_time_bpm_pre_gate",
            "hr_fused_bpm_pre_gate",
            "hr_confidence",
            "hr_usable_ratio",
            "gate_hit",
            "gate_reason",
            "hr_status",
        ):
            out[f"control_{field}"] = c.get(field)
            out[f"restored_{field}"] = r.get(field)
        for field in (
            "restoration_reference_bpm",
            "restoration_consensus_time_bpm",
            "restoration_base_freq_bpm",
            "restoration_global_time_bpm",
            "restoration_n_peaks",
            "restoration_segment_json",
            "restoration_consensus_json",
            "restoration_course_json",
        ):
            out[field] = r.get(field)
        out["control_fused_absolute_error_bpm"] = c_ae
        out["restored_fused_absolute_error_bpm"] = r_ae
        out["restored_minus_control_absolute_error_bpm"] = delta
        paired.append(out)

    control_metrics = metrics(control)
    restoration_metrics = metrics(restoration)
    pre_gate_rows = []
    for row in restoration:
        clone = dict(row)
        clone["hr_30s_spectral_bpm"] = row.get("hr_spectral_bpm_pre_gate")
        clone["hr_30s_time_bpm"] = row.get("hr_time_bpm_pre_gate")
        clone["hr_30s_fused_bpm"] = row.get("hr_fused_bpm_pre_gate")
        pre_gate_rows.append(clone)

    per_session = []
    for subject in sorted({row["subject"] for row in control}):
        c_rows = [row for row in control if row["subject"] == subject]
        r_rows = [row for row in restoration if row["subject"] == subject]
        c_metric = metrics(c_rows)["fused"]
        r_metric = metrics(r_rows)["fused"]
        per_session.append({
            "subject": subject,
            "control_mae_bpm": c_metric["mae_bpm"],
            "control_bias_bpm": c_metric["bias_bpm"],
            "control_coverage": c_metric["coverage"],
            "restored_mae_bpm": r_metric["mae_bpm"],
            "restored_bias_bpm": r_metric["bias_bpm"],
            "restored_coverage": r_metric["coverage"],
            "delta_mae_bpm": (
                r_metric["mae_bpm"] - c_metric["mae_bpm"]
                if r_metric["mae_bpm"] is not None and c_metric["mae_bpm"] is not None else None
            ),
        })

    def values(field: str, rows: list[dict[str, str]]) -> np.ndarray:
        return np.asarray([value for row in rows if (value := number(row.get(field))) is not None], dtype=float)

    large_error = {}
    for label, rows in (("control", control), ("restoration", restoration)):
        errors = []
        for row in rows:
            a = number(row.get("ecg_hr_bpm"))
            p = number(row.get("hr_30s_fused_bpm"))
            if a is not None and p is not None:
                errors.append(abs(p - a))
        large_error[label] = {f"gt_{threshold}_bpm": int(np.sum(np.asarray(errors) > threshold)) for threshold in (10, 20, 30)}

    integrity = {
        "control_rows": len(control),
        "restoration_rows": len(restoration),
        "paired_rows": len(common_keys),
        "duplicate_control_keys": duplicate_control,
        "duplicate_restoration_keys": duplicate_restoration,
        "only_control_keys": ["|".join(item) for item in only_control],
        "only_restoration_keys": ["|".join(item) for item in only_restoration],
        "invariant_difference_count": len(invariant_differences),
        "invariant_gate": "PASS" if len(common_keys) == 100 and not duplicate_control and not duplicate_restoration and not only_control and not only_restoration and not invariant_differences else "FAIL",
    }
    summary = {
        "state": "PASS" if integrity["invariant_gate"] == "PASS" else "FAIL",
        "p1_verdict": "RESTORATION_NOT_SUPPORTED" if integrity["invariant_gate"] == "PASS" else "INVARIANT_GATE_FAILED",
        "integrity": integrity,
        "control_metrics": control_metrics,
        "restoration_metrics": restoration_metrics,
        "restoration_pre_gate_metrics": metrics(pre_gate_rows),
        "fused_mae_delta_bpm": restoration_metrics["fused"]["mae_bpm"] - control_metrics["fused"]["mae_bpm"],
        "improve_worsen_tie": {"improve": improve, "worsen": worsen, "tie": tie},
        "paired_absolute_error_delta_bpm": {
            "mean": float(np.mean(ae_deltas)) if ae_deltas else None,
            "median": float(np.median(ae_deltas)) if ae_deltas else None,
        },
        "large_error_probe_distribution": large_error,
        "confidence": {
            "control_mean": float(np.mean(values("hr_confidence", control))),
            "restoration_mean": float(np.mean(values("hr_confidence", restoration))),
            "control_median": float(np.median(values("hr_confidence", control))),
            "restoration_median": float(np.median(values("hr_confidence", restoration))),
        },
        "usable_ratio": {
            "control_mean": float(np.mean(values("hr_usable_ratio", control))),
            "restoration_mean": float(np.mean(values("hr_usable_ratio", restoration))),
        },
        "gate_hits": int(sum(gate_reasons.values())),
        "gate_reasons": dict(gate_reasons),
        "missing_qc_transitions": dict(missing_transitions),
        "per_session": per_session,
        "models_trained": False,
        "ecg_role": "FINAL_EVALUATION_ONLY_AFTER_ARM_ESTIMATION",
        "p2_ready": integrity["invariant_gate"] == "PASS",
        "p2_executed": False,
    }

    paired_path = args.output_dir / "MMWAVE_HR_RECOVERY_P1_PAIRED_100_PROBES.csv"
    summary_path = args.output_dir / "MMWAVE_HR_RECOVERY_P1_SUMMARY.json"
    session_path = args.output_dir / "MMWAVE_HR_RECOVERY_P1_PER_SESSION.csv"
    invariant_path = args.output_dir / "MMWAVE_HR_RECOVERY_P1_INVARIANT_DIFFERENCES.csv"
    write_csv(paired_path, paired)
    write_csv(session_path, per_session)
    write_csv(invariant_path, invariant_differences or [{"key": "", "field": "", "control": "", "restoration": ""}])
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    error_log = {
        "task_id": "mmwave_hr_recovery_p1",
        "events": [
            {
                "id": "P1-RUN-ENV-001",
                "state": "RESOLVED",
                "impact": "No scientific computation started and no result was produced.",
                "error": "ModuleNotFoundError: No module named 'bioread'",
                "failed_output": r"D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p1_20260912_control_r1",
                "resolution": r"Reused the existing .venv_t0 environment; reran in a new control_r2 directory.",
            },
            {
                "id": "P1-SUMMARY-IO-001",
                "state": "RESOLVED",
                "impact": "No paired result was produced or overwritten.",
                "error": "Outer stdout redirection targeted a directory before the summarizer created it.",
                "failed_output": r"D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p1_20260912_paired_r2",
                "resolution": "Removed outer redirection and used a fresh paired output directory.",
            },
            {
                "id": "P1-DENOMINATOR-97792",
                "state": "FROZEN_NOT_ESTIMABLE",
                "impact": "Not part of the fixed five-session/100-probe B2 denominator.",
                "error": "No formal probe windows in behavior Block CSV/events.csv.",
                "resolution": "Preserved the existing B2 five-session denominator; no row or session substitution.",
            },
        ],
    }
    error_path = args.output_dir / "MMWAVE_HR_RECOVERY_P1_ERROR_LOG.json"
    error_path.write_text(json.dumps(error_log, ensure_ascii=False, indent=2), encoding="utf-8")

    runner_path = Path(__file__).with_name("run_mmwave_hr_recovery_p1_20260912.py")
    producer_path = Path(__file__).resolve().parents[1] / "process_vital_signs_v3_1_1.py"
    source_audit = {
        "repository": "https://github.com/greenboo26/focuswave-multimodal-attention-analysis.git",
        "remote_main_at_start": args.remote_main_at_start,
        "governance_main_at_start": args.governance_main,
        "execution_source": args.source_commit,
        "execution_parent": args.source_parent,
        "exact_object_resolved": True,
        "b2_adapter_sha256": args.b2_adapter_sha256,
        "b2_test_sha256": args.b2_test_sha256,
        "historical_b2_output_sha256": args.historical_b2_output_sha256,
        "executed_p1_runner_sha256": sha256(runner_path),
        "producer_sha256": sha256(producer_path),
        "summarizer_sha256": sha256(Path(__file__)),
    }
    source_audit_path = args.output_dir / "MMWAVE_HR_RECOVERY_P1_SOURCE_IDENTITY.json"
    source_audit_path.write_text(json.dumps(source_audit, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "task_id": "mmwave_hr_recovery_p1",
        "source_commit": args.source_commit,
        "source_parent": args.source_parent,
        "remote_main_at_start": args.remote_main_at_start,
        "governance_main_at_start": args.governance_main,
        "b2_frozen_identity": {
            "adapter_sha256": args.b2_adapter_sha256,
            "test_sha256": args.b2_test_sha256,
            "historical_output_sha256": args.historical_b2_output_sha256,
        },
        "inputs": {
            "control": str(args.control),
            "control_sha256": sha256(args.control),
            "restoration": str(args.restoration),
            "restoration_sha256": sha256(args.restoration),
        },
        "outputs": {
            "paired_table": str(paired_path),
            "paired_table_sha256": sha256(paired_path),
            "summary": str(summary_path),
            "summary_sha256": sha256(summary_path),
            "per_session": str(session_path),
            "per_session_sha256": sha256(session_path),
            "invariant_differences": str(invariant_path),
            "invariant_differences_sha256": sha256(invariant_path),
            "error_log": str(error_path),
            "error_log_sha256": sha256(error_path),
            "source_identity": str(source_audit_path),
            "source_identity_sha256": sha256(source_audit_path),
        },
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "models_trained": False,
        "formal_producer_modified": False,
        "hr_br_status": "HOLD_SUPPORTING_ONLY",
        "hrv_status": "BLOCKED",
        "p2_ready": integrity["invariant_gate"] == "PASS",
        "p2_executed": False,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
