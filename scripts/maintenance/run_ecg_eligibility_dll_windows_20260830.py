"""Freeze ECG reference eligibility for the 335 DLL-time mmWave windows.

This is a narrow adapter around existing project code.  It reuses the frozen
gold_standard_qa ECG cleaning rules and the existing block-marker affine
mapping, then recomputes the already-produced ARM0/ARM1/ARM2 descriptive
metrics on ECG_VALID windows only.  It does not select mmWave targets, run an
estimator, alter raw data, or tune any threshold from mmWave error.

The per-window eligibility table is deliberately local-only under ``work/``;
Git receives only aggregate evidence and the reproducibility manifest.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
WINDOW_INPUT = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv"
ARM_INPUT = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
TARGETED_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
GOLD_QA_SCRIPT = ALGO_ROOT / "scripts" / "gold_standard_qa.py"
LOCAL_ROOT = ALGO_ROOT / "work" / "ecg_eligibility_dll_windows_20260830"
LOCAL_WINDOW_OUTPUT = LOCAL_ROOT / "ECG_DLL_WINDOW_ELIGIBILITY_LOCAL_ONLY.csv"
SUBJECTS = ("97793", "9779", "97795")
WINDOW_EXPECTED = 335
ECG_MIN_VALID_RATIO = 0.80
MARKER_WARNING = "marker_sequence_not_exact_but_block_affine_fit_available"
ARM_COLUMNS = {
    "arm0": "fixed_arm0_hr_bpm",
    "arm1": "fixed_arm1_hr_bpm",
    "arm2": "fixed_arm2_hr_bpm",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def numeric(value):
    if value in (None, "", "None", "nan", "NaN"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ALGO_ROOT), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unavailable"


def window_key(row: dict) -> tuple[str, str, str]:
    return row["subject"], row["block_id"], row["window_id"]


def eligibility_reasons(report: dict, hr) -> list[str]:
    reasons: list[str] = []
    note = report.get("note")
    if note == "too_short":
        reasons.append("short_window")
    if note == "too_few_peaks":
        reasons.append("too_few_rpeaks")
    if note == "too_few_ibi":
        reasons.append("insufficient_valid_ibi")
    if int(report.get("n_ibi_range_rejected", 0) or 0) > 0:
        reasons.append("ibi_outside_plausible_300_2000ms")
    if int(report.get("n_pc_rejected", 0) or 0) > 0:
        reasons.append("abnormal_adjacent_ibi_fluctuation_gt20pct")
    if float(report.get("valid_ratio", 0.0) or 0.0) < ECG_MIN_VALID_RATIO:
        reasons.append("effective_beat_coverage_below_80pct")
    if hr is None and "insufficient_valid_ibi" not in reasons:
        reasons.append("no_finite_ecg_hr")
    return list(dict.fromkeys(reasons))


def summarize_metrics(rows: list[dict], denominator: str, arm: str) -> dict:
    selected = rows if denominator == "ALL_WINDOWS_DIAGNOSTIC" else [r for r in rows if r["ecg_eligibility"] == denominator]
    column = ARM_COLUMNS[arm]
    pairs = [(numeric(r.get(column)), numeric(r.get("ecg_hr_bpm"))) for r in selected]
    pairs = [(estimate, reference) for estimate, reference in pairs if estimate is not None and reference is not None]
    errors = np.asarray([estimate - reference for estimate, reference in pairs], dtype=float)
    absolute = np.abs(errors)
    return {
        "denominator": denominator,
        "arm": arm,
        "selected_window_n": len(selected),
        "estimator_valid_n": len(pairs),
        "coverage_pct_of_denominator": round(100.0 * len(pairs) / len(selected), 3) if selected else None,
        "mae_bpm": round(float(np.mean(absolute)), 6) if len(errors) else None,
        "median_ae_bpm": round(float(np.median(absolute)), 6) if len(errors) else None,
        "rmse_bpm": round(float(np.sqrt(np.mean(errors ** 2))), 6) if len(errors) else None,
        "bias_mmwave_minus_ecg_bpm": round(float(np.mean(errors)), 6) if len(errors) else None,
        "pearson_r": round(float(pearsonr([a for a, _ in pairs], [b for _, b in pairs]).statistic), 6) if len(pairs) >= 2 else None,
        "spearman_r": round(float(spearmanr([a for a, _ in pairs], [b for _, b in pairs]).statistic), 6) if len(pairs) >= 2 else None,
        "interpretation": "ECG_VALID_primary" if denominator == "ECG_VALID" else "diagnostic_only_not_validity_denominator",
    }


def build_report(summary: dict, reason_rows: list[dict], block_rows: list[dict], metric_rows: list[dict], failures: list[dict]) -> str:
    valid_n = summary["eligibility_counts"].get("ECG_VALID", 0)
    invalid_n = summary["eligibility_counts"].get("ECG_INVALID", 0)
    unresolved_n = summary["eligibility_counts"].get("UNRESOLVED", 0)
    primary = [r for r in metric_rows if r["denominator"] == "ECG_VALID"]
    lines = [
        "# ECG reference eligibility for DLL-time windows — 2026-08-30",
        "",
        "状态：`PARTIAL / ECG_REFERENCE_ELIGIBILITY_COMPLETE`",
        "",
        "本报告只冻结 ECG reference eligibility。ECG 规则复用 `scripts/gold_standard_qa.py`；窗口时间到 ECG sample 的映射复用既有 block marker affine mapping。毫米波 ARM0/ARM1/ARM2 估计值固定读取既有 ablation CSV，未重新选择 target/bin/channel，也未用毫米波误差筛选 ECG。",
        "",
        "## 1. Eligibility result",
        "",
        f"- Input windows: `{summary['input_window_n']}`; expected: `{WINDOW_EXPECTED}`.",
        f"- `ECG_VALID`: `{valid_n}`; `ECG_INVALID`: `{invalid_n}`; `UNRESOLVED`: `{unresolved_n}`.",
        "- `ECG_VALID` requires a complete block with usable block-marker affine mapping, at least 3 valid IBI, no rejected interval/artifact reason, and effective valid-beat coverage ≥80%.",
        "- A non-exact marker sequence is retained as a warning when the block affine fit is available; it is not silently converted into a valid/invalid physiology decision.",
        "",
        "## 2. Reused ECG rules",
        "",
        "- Bandpass: 0.5–40 Hz, third-order SOS.",
        "- R-peak: fixed 0.30 s minimum distance and fixed prominence 0.25.",
        "- IBI plausibility: 300–2000 ms; out-of-range intervals are rejected.",
        "- Artifact rejection: adjacent IBI relative change >20% marks both neighboring intervals as artifact candidates.",
        "- Effective beat coverage: kept valid IBI / raw detected R-peak count ≥80%; no interpolation is introduced.",
        "- Window gate: any out-of-range IBI or >20% adjacent-IBI artifact rejection makes that window `ECG_INVALID`; the reason is kept separately from marker warnings.",
        "- Rest, posture-adjustment, boundary and incomplete-block periods are excluded structurally by the frozen DLL-time block window input.",
        "",
        "## 3. Reason distribution",
        "",
        "| eligibility | reason | windows |",
        "|---|---|---:|",
    ]
    for row in reason_rows:
        lines.append(f"| {row['eligibility']} | {row['reason']} | {row['window_n']} |")
    lines += [
        "",
        "## 4. ARM0/ARM1/ARM2 on ECG_VALID denominator",
        "",
        "这些是固定既有毫米波 estimator 输出在新 ECG_VALID 分母上的描述性重算；它们不改变 estimator、target、gate 或历史 ARM 定义。",
        "",
        "| arm | n selected | estimator-valid n | MAE bpm | median AE | RMSE | bias |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in primary:
        lines.append(f"| {row['arm']} | {row['selected_window_n']} | {row['estimator_valid_n']} | {row['mae_bpm']} | {row['median_ae_bpm']} | {row['rmse_bpm']} | {row['bias_mmwave_minus_ecg_bpm']} |")
    lines += [
        "",
        "## 5. All-window diagnostic",
        "",
        "All-window metrics are retained only as diagnostic context. They are not a validity denominator because ECG_INVALID and UNRESOLVED windows remain present and are not converted into evidence of mmWave error.",
        "",
        "| arm | n selected | estimator-valid n | MAE bpm | interpretation |",
        "|---|---:|---:|---:|---|",
    ]
    for row in metric_rows:
        if row["denominator"] == "ALL_WINDOWS_DIAGNOSTIC":
            lines.append(f"| {row['arm']} | {row['selected_window_n']} | {row['estimator_valid_n']} | {row['mae_bpm']} | {row['interpretation']} |")
    lines += [
        "",
        "## 6. Block and failure audit",
        "",
        "Per-window reject reasons are in the local-only CSV listed in the manifest. Aggregate block evidence is committed in `ECG_ELIGIBILITY_BLOCK_SUMMARY.csv`.",
        "",
        "| subject | block | windows | ECG_VALID | ECG_INVALID | UNRESOLVED | marker warning |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in block_rows:
        lines.append(f"| {row['subject']} | {row['block_id']} | {row['window_n']} | {row['ECG_VALID_n']} | {row['ECG_INVALID_n']} | {row['UNRESOLVED_n']} | {row['marker_warning_n']} |")
    if failures:
        lines += ["", "Unresolved execution items:"]
        for failure in failures:
            lines.append(f"- `{failure['subject']}/{failure['block_id']}/{failure['window_id']}`: {failure['reason']}")
    else:
        lines += ["", "No execution-level unresolved rows occurred."]
    lines += [
        "",
        "## 7. Boundary",
        "",
        "This closes the requested ECG eligibility layer for the current 335-window diagnostic comparison. It does not make the 20 s window scientifically canonical, does not validate HR/BR for the formal cohort, and does not open HRV. HR remains `HOLD`; HRV remains `BLOCKED`; #16 remains `PAUSED`.",
        "",
        "## 8. Evidence",
        "",
        "- `ECG_ELIGIBILITY_REASON_DISTRIBUTION.csv` — committed aggregate reasons.",
        "- `ECG_ELIGIBILITY_BLOCK_SUMMARY.csv` — committed per-block counts and marker warnings.",
        "- `ECG_ARM_METRICS_VALID_DENOMINATOR.csv` — committed ECG_VALID and all-window diagnostic metrics.",
        "- `ECG_ELIGIBILITY_MANIFEST.json` — inputs, hashes, parameters, run ID and local-only row-level output path.",
        "- `work/ecg_eligibility_dll_windows_20260830/ECG_DLL_WINDOW_ELIGIBILITY_LOCAL_ONLY.csv` — local-only per-window evidence with every reject reason.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    run_id = f"ecg_eligibility_dll_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    if not WINDOW_INPUT.exists() or not ARM_INPUT.exists():
        raise FileNotFoundError(f"Required fixed input missing: {WINDOW_INPUT} / {ARM_INPUT}")
    targeted = load_module(TARGETED_SCRIPT, "targeted_for_ecg_eligibility")
    gold = load_module(GOLD_QA_SCRIPT, "gold_standard_for_ecg_eligibility")
    window_rows = read_csv(WINDOW_INPUT)
    arm_rows = {window_key(row): row for row in read_csv(ARM_INPUT)}
    if len(window_rows) != WINDOW_EXPECTED:
        raise RuntimeError(f"Expected {WINDOW_EXPECTED} DLL-time windows, found {len(window_rows)}")
    if len(arm_rows) != WINDOW_EXPECTED:
        raise RuntimeError(f"Expected {WINDOW_EXPECTED} fixed ARM rows, found {len(arm_rows)}")

    enriched: list[dict] = []
    failures: list[dict] = []
    block_cache: dict[str, tuple[list[dict], dict[str, dict], dict[str, dict], np.ndarray, np.ndarray, float, str, dict]] = {}
    for subject in SUBJECTS:
        timestamps = targeted.load_mmwave_timestamps(subject)
        events = targeted.load_events(subject)
        physical, digital_meta = targeted.decode_biopac_markers(subject)
        blocks, audits = targeted.block_intervals(subject, timestamps, events, physical)
        block_map = {row["block_id"]: row for row in blocks}
        audit_map = {row["block_id"]: row for row in audits}
        ecg, _rsp, fs = targeted.load_ecg_reference(subject)
        block_cache[subject] = (blocks, block_map, audit_map, ecg, timestamps, fs, str(digital_meta["acq_path"]), digital_meta)

    for source in window_rows:
        subject, block_id, window_id = window_key(source)
        blocks, block_map, audit_map, ecg, _timestamps, fs, acq_file, digital_meta = block_cache[subject]
        block = block_map.get(block_id)
        audit = audit_map.get(block_id, {})
        reject_reasons: list[str] = []
        warnings: list[str] = []
        status = "UNRESOLVED"
        hr = None
        qa = {
            "n_raw": 0,
            "n_ibi_range_rejected": 0,
            "n_pc_rejected": 0,
            "n_kept": 0,
            "valid_ratio": 0.0,
            "usable": False,
            "note": None,
        }
        ecg_start_sample = None
        ecg_end_sample = None
        marker_warning = ""
        if block is None:
            reject_reasons.append("block_not_found")
        elif block.get("status") != "complete":
            reject_reasons.append("block_not_complete")
        slope = numeric(audit.get("ecg_fit_slope_samples_per_ms")) if block else None
        intercept = numeric(audit.get("ecg_fit_intercept_sample")) if block else None
        if block and audit.get("marker_sequence_exact") is False:
            marker_warning = MARKER_WARNING
            warnings.append(marker_warning)
        if not reject_reasons and (slope is None or intercept is None):
            reject_reasons.append("block_marker_affine_mapping_unavailable")
        if not reject_reasons:
            ecg_start_sample = int(round(slope * int(source["window_start_unix_ms"]) + intercept))
            ecg_end_sample = int(round(slope * int(source["window_end_unix_ms"]) + intercept))
            if ecg_start_sample < 0 or ecg_end_sample > len(ecg) or ecg_end_sample <= ecg_start_sample:
                reject_reasons.append("ecg_sample_bounds_unresolved")
            else:
                hr, qa = gold.ecg_qa(ecg, fs, ecg_start_sample, ecg_end_sample)
                reject_reasons.extend(eligibility_reasons(qa, hr))
        if block is None or (block and block.get("status") != "complete") or "block_marker_affine_mapping_unavailable" in reject_reasons or "ecg_sample_bounds_unresolved" in reject_reasons:
            status = "UNRESOLVED"
        elif reject_reasons:
            status = "ECG_INVALID"
        elif hr is not None and qa.get("usable") and float(qa.get("valid_ratio", 0.0)) >= ECG_MIN_VALID_RATIO:
            status = "ECG_VALID"
        else:
            status = "ECG_INVALID"
        if status == "UNRESOLVED":
            failures.append({"subject": subject, "block_id": block_id, "window_id": window_id, "reason": "|".join(reject_reasons) or "unresolved_execution_state"})
        fixed_arm = arm_rows[(subject, block_id, window_id)]
        enriched.append({
            **source,
            "ecg_eligibility": status,
            "ecg_reject_reason": "|".join(reject_reasons) if reject_reasons else "none",
            "ecg_qc_warning": "|".join(warnings) if warnings else "none",
            "ecg_hr_bpm": round(float(hr), 6) if hr is not None else None,
            "ecg_n_rpeaks": qa.get("n_raw"),
            "ecg_n_ibi_range_rejected": qa.get("n_ibi_range_rejected"),
            "ecg_n_abnormal_fluctuation_rejected": qa.get("n_pc_rejected"),
            "ecg_n_valid_ibi": qa.get("n_kept"),
            "ecg_effective_beat_coverage": round(float(qa.get("valid_ratio", 0.0)), 6),
            "ecg_quality_usable": bool(qa.get("usable")),
            "ecg_qa_note": qa.get("note") or "",
            "ecg_start_sample": ecg_start_sample,
            "ecg_end_sample": ecg_end_sample,
            "ecg_fit_residual_p95_ms": audit.get("ecg_fit_residual_p95_ms"),
            "marker_sequence_exact": audit.get("marker_sequence_exact"),
            "marker_mismatch_count": audit.get("marker_mismatch_count"),
            "acq_file": acq_file,
            "acq_filename_verdict": "directory_subject_matches_basename_typo" if subject == "97795" and Path(acq_file).name == "97995.acq" else "subject_basename_match",
            "fixed_arm0_hr_bpm": fixed_arm.get("arm0_hr_bpm"),
            "fixed_arm1_hr_bpm": fixed_arm.get("arm1_gate_only_hr_bpm"),
            "fixed_arm2_hr_bpm": fixed_arm.get("arm2_historical_target_hr_bpm"),
        })

    enriched.sort(key=lambda row: (SUBJECTS.index(row["subject"]), row["block_id"], row["window_id"]))
    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(LOCAL_WINDOW_OUTPUT, enriched)

    eligibility_counter = Counter(row["ecg_eligibility"] for row in enriched)
    eligibility_counts = {
        label: int(eligibility_counter.get(label, 0))
        for label in ("ECG_VALID", "ECG_INVALID", "UNRESOLVED")
    }
    reason_counts = Counter()
    for row in enriched:
        for reason in (row["ecg_reject_reason"] or "none").split("|"):
            reason_counts[(row["ecg_eligibility"], reason)] += 1
    reason_rows = [
        {"eligibility": eligibility, "reason": reason, "window_n": count}
        for (eligibility, reason), count in sorted(reason_counts.items())
    ]
    block_rows = []
    for subject in SUBJECTS:
        for block_id in sorted({row["block_id"] for row in enriched if row["subject"] == subject}):
            subset = [row for row in enriched if row["subject"] == subject and row["block_id"] == block_id]
            block_rows.append({
                "subject": subject,
                "block_id": block_id,
                "window_n": len(subset),
                "ECG_VALID_n": sum(row["ecg_eligibility"] == "ECG_VALID" for row in subset),
                "ECG_INVALID_n": sum(row["ecg_eligibility"] == "ECG_INVALID" for row in subset),
                "UNRESOLVED_n": sum(row["ecg_eligibility"] == "UNRESOLVED" for row in subset),
                "marker_warning_n": sum(bool(row["marker_sequence_exact"] is False) for row in subset),
                "marker_sequence_exact": all(row["marker_sequence_exact"] is not False for row in subset),
                "acq_filename_verdict": sorted({row["acq_filename_verdict"] for row in subset})[0],
            })

    metric_rows = []
    for denominator in ("ECG_VALID", "ALL_WINDOWS_DIAGNOSTIC"):
        for arm in ("arm0", "arm1", "arm2"):
            metric_rows.append(summarize_metrics(enriched, denominator, arm))

    summary = {
        "status": "PARTIAL / ECG_REFERENCE_ELIGIBILITY_COMPLETE",
        "run_id": run_id,
        "analysis_set": list(SUBJECTS),
        "input_window_n": len(enriched),
        "eligibility_counts": dict(sorted(eligibility_counts.items())),
        "reason_distribution": reason_rows,
        "block_summary_rows": len(block_rows),
        "execution_failures": failures,
        "rules": {
            "filter": "gold_standard_qa.ecg_qa: third-order SOS 0.5-40 Hz",
            "r_peak": "find_peaks distance 0.30 s, prominence 0.25",
            "ibi_plausibility_ms": [300.0, 2000.0],
            "artifact_rejection": "adjacent IBI relative change >20%; both adjacent intervals marked",
            "effective_beat_coverage": "kept valid IBI / raw detected R-peak count >=0.80",
            "minimum_valid_ibi": 3,
            "window_eligibility": "invalid if any IBI plausibility/artifact rejection reason, insufficient valid IBI, or coverage <0.80",
            "block_rule": "complete formal block + block-local ECG affine marker mapping; rest/posture/boundary excluded",
            "marker_mismatch": "warning only when affine fit remains available; not silently treated as validity",
        },
        "input_sha256": {
            "dll_time_windows": sha256(WINDOW_INPUT),
            "fixed_arm_rows": sha256(ARM_INPUT),
            "targeted_script": sha256(TARGETED_SCRIPT),
            "gold_standard_qa_script": sha256(GOLD_QA_SCRIPT),
            "eligibility_script": sha256(Path(__file__).resolve()),
        },
        "git": {
            "head_at_run": git_value("rev-parse", "HEAD"),
            "origin_main_at_run": git_value("rev-parse", "origin/main"),
        },
        "excluded": [
            "mmWave estimator rerun",
            "mmWave error-based ECG selection",
            "new estimator or parameter search",
            "Issue #16",
            "C2B/C2C",
            "HRV",
            "raw/acquisition/producer/firmware/portable-V2 changes",
        ],
        "outputs": {},
    }
    write_csv(RESULT_ROOT / "ECG_ELIGIBILITY_REASON_DISTRIBUTION.csv", reason_rows)
    write_csv(RESULT_ROOT / "ECG_ELIGIBILITY_BLOCK_SUMMARY.csv", block_rows)
    write_csv(RESULT_ROOT / "ECG_ARM_METRICS_VALID_DENOMINATOR.csv", metric_rows)
    report_path = RESULT_ROOT / "ECG_REFERENCE_ELIGIBILITY_REPORT_2026-08-30.md"
    report_path.write_text(build_report(summary, reason_rows, block_rows, metric_rows, failures), encoding="utf-8")
    manifest_path = RESULT_ROOT / "ECG_ELIGIBILITY_MANIFEST.json"
    output_files = [
        ("ECG_ELIGIBILITY_REASON_DISTRIBUTION.csv", "tracked_aggregate"),
        ("ECG_ELIGIBILITY_BLOCK_SUMMARY.csv", "tracked_aggregate"),
        ("ECG_ARM_METRICS_VALID_DENOMINATOR.csv", "tracked_aggregate"),
        ("ECG_REFERENCE_ELIGIBILITY_REPORT_2026-08-30.md", "tracked_report"),
        (str(LOCAL_WINDOW_OUTPUT.relative_to(ALGO_ROOT)), "local_only_row_level"),
    ]
    for rel, role in output_files:
        path = RESULT_ROOT / rel if role.startswith("tracked") else ALGO_ROOT / rel
        summary["outputs"][rel] = {"role": role, "path": str(path), "sha256": sha256(path), "row_count": len(read_csv(path)) if path.suffix.lower() == ".csv" else None}
    summary["manifest_path"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "status": summary["status"], "eligibility_counts": summary["eligibility_counts"], "metrics": metric_rows, "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
