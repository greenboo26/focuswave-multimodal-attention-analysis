"""Audit DLL-time 20 s window acquisition completeness before HR sensitivity.

The coverage contract is intentionally independent of ECG, radar HR, error,
and arm performance. It uses only DLL timestamps, block markers, and the
frozen 20 s/10 s/5 s window definition. It does not alter any source data or
HR estimator and does not remove windows from the primary result.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
DATA_ROOT = Path(r"D:\acq_mmwave_data")
WINDOWS = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv"
RECON_MANIFEST = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_MANIFEST.json"
WRAPPER = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
RECON_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_dll_time_window_reconstruction_20260830.py"
SUBJECTS = ("97793", "9779", "97795")
WINDOW_DURATION_MS = 20_000
COMPLETE_COVERAGE_MIN = 0.95
PARTIAL_COVERAGE_MIN = 0.50
NORMAL_BOUNDARY_MULTIPLIER = 3.0
SEVERE_GAP_MS = 1_000.0
NORMAL_INTERNAL_MAX_MS = 1_000.0


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "subject", "block_id", "window_id", "window_start_unix_ms", "window_end_unix_ms",
        "first_dll_frame_time", "last_dll_frame_time", "frame_count", "effective_local_hz",
        "local_interval_median_ms", "local_interval_p5_ms", "local_interval_p95_ms",
        "expected_frame_count", "coverage_fraction", "dll_span_ms", "start_coverage_gap_ms",
        "end_coverage_gap_ms", "largest_internal_gap_ms", "coverage_class",
        "coverage_exclusion_candidate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception:
        return "unavailable"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_interval_stats(dll_ts: np.ndarray, start_ms: int, end_ms: int) -> dict:
    selected = dll_ts[(dll_ts >= start_ms) & (dll_ts <= end_ms)]
    intervals = np.diff(selected).astype(float)
    if len(intervals) == 0:
        return {"median": None, "p5": None, "p95": None, "effective_hz": None}
    median = float(np.median(intervals))
    return {
        "median": median,
        "p5": float(np.percentile(intervals, 5)),
        "p95": float(np.percentile(intervals, 95)),
        "effective_hz": 1000.0 / median if median > 0 else None,
    }


def classify(coverage: float, start_gap: float, end_gap: float, largest_internal_gap: float, median_ms: float) -> tuple[str, str]:
    normal_boundary = max(NORMAL_BOUNDARY_MULTIPLIER * median_ms, 50.0)
    severe_boundary = max(SEVERE_GAP_MS, 5.0 * median_ms)
    if coverage >= COMPLETE_COVERAGE_MIN and start_gap <= normal_boundary and end_gap <= normal_boundary and largest_internal_gap <= NORMAL_INTERNAL_MAX_MS:
        return "COMPLETE", "False"
    severe = coverage < PARTIAL_COVERAGE_MIN or start_gap > severe_boundary or end_gap > severe_boundary or largest_internal_gap > NORMAL_INTERNAL_MAX_MS
    return ("SEVERELY_INCOMPLETE" if severe else "PARTIAL", "True" if severe else "False")


def main() -> int:
    rerun = load_module(WRAPPER, "targeted_wrapper_for_coverage")
    recon = load_module(RECON_SCRIPT, "reconstruction_for_coverage")
    windows = read_csv(WINDOWS)
    output_rows = []
    rate_summary = {}
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        dll_ts = timestamps[:, 1].astype(np.int64)
        subject_windows = [row for row in windows if row["subject"] == subject]
        for block_id in sorted({row["block_id"] for row in subject_windows}):
            block_rows = [row for row in subject_windows if row["block_id"] == block_id]
            block_start = min(int(row["window_start_unix_ms"]) - 5_000 for row in block_rows)
            block_end = max(int(row["window_end_unix_ms"]) + 5_000 for row in block_rows)
            rate_summary[f"{subject}/{block_id}"] = local_interval_stats(dll_ts, block_start, block_end)
        for row in subject_windows:
            start_ms = int(row["window_start_unix_ms"])
            end_ms = int(row["window_end_unix_ms"])
            rate = rate_summary[f"{subject}/{row['block_id']}"]
            selected = dll_ts[(dll_ts >= start_ms) & (dll_ts <= end_ms)]
            frame_count = int(len(selected))
            expected = (WINDOW_DURATION_MS / rate["median"] + 1.0) if rate["median"] else 0.0
            coverage = min(frame_count / expected, 1.0) if expected else 0.0
            if frame_count:
                first = int(selected[0])
                last = int(selected[-1])
                dll_span = int(last - first)
                start_gap = float(max(0, first - start_ms))
                end_gap = float(max(0, end_ms - last))
                largest_internal = float(np.max(np.diff(selected))) if frame_count > 1 else float(WINDOW_DURATION_MS)
            else:
                first = last = dll_span = None
                start_gap = end_gap = float(WINDOW_DURATION_MS)
                largest_internal = float(WINDOW_DURATION_MS)
            coverage_class, exclusion = classify(coverage, start_gap, end_gap, largest_internal, rate["median"] or WINDOW_DURATION_MS)
            output_rows.append({
                "subject": subject,
                "block_id": row["block_id"],
                "window_id": row["window_id"],
                "window_start_unix_ms": start_ms,
                "window_end_unix_ms": end_ms,
                "first_dll_frame_time": first,
                "last_dll_frame_time": last,
                "frame_count": frame_count,
                "effective_local_hz": round(rate["effective_hz"], 6) if rate["effective_hz"] is not None else None,
                "local_interval_median_ms": round(rate["median"], 6) if rate["median"] is not None else None,
                "local_interval_p5_ms": round(rate["p5"], 6) if rate["p5"] is not None else None,
                "local_interval_p95_ms": round(rate["p95"], 6) if rate["p95"] is not None else None,
                "expected_frame_count": round(expected, 6),
                "coverage_fraction": round(coverage, 6),
                "dll_span_ms": dll_span,
                "start_coverage_gap_ms": round(start_gap, 6),
                "end_coverage_gap_ms": round(end_gap, 6),
                "largest_internal_gap_ms": round(largest_internal, 6),
                "coverage_class": coverage_class,
                "coverage_exclusion_candidate": exclusion,
            })
    output_rows.sort(key=lambda row: (SUBJECTS.index(row["subject"]), row["block_id"], row["window_id"]))
    output_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT.csv"
    write_csv(output_path, output_rows)
    class_counts = {name: sum(row["coverage_class"] == name for row in output_rows) for name in ("COMPLETE", "PARTIAL", "SEVERELY_INCOMPLETE")}
    block_counts = {}
    for row in output_rows:
        key = f"{row['subject']}/{row['block_id']}"
        block_counts.setdefault(key, {name: 0 for name in ("COMPLETE", "PARTIAL", "SEVERELY_INCOMPLETE")})
        block_counts[key][row["coverage_class"]] += 1
    short = [row for row in output_rows if row["coverage_class"] != "COMPLETE"]
    report_lines = [
        "# mmWave DLL-time window coverage audit — 2026-08-30", "",
        "状态：`COVERAGE_CONTRACT_FROZEN / HR-INDEPENDENT`", "",
        f"- Input: frozen DLL-time windows `{len(output_rows)}`; the primary ARM0/ARM1/ARM2 full-window outputs are not deleted or overwritten.",
        "- Coverage uses only DLL timestamps and the frozen block/window boundaries; ECG HR, radar HR, abs error, and arm performance are not used to define thresholds.",
        "- Local frame rate per subject/block: median interval, p5, p95, and effective Hz=`1000/median_interval_ms`; expected count=`20,000/median_interval_ms + 1`.",
        "- Frozen classes: `COMPLETE` if coverage ≥0.95, both boundary gaps ≤max(3×median interval, 50 ms), and largest internal gap ≤1,000 ms; `SEVERELY_INCOMPLETE` if coverage <0.50, a boundary gap >max(1,000 ms, 5×median interval), or an internal gap >1,000 ms; otherwise `PARTIAL`.",
        f"- Counts: `{class_counts}`; exclusion candidates are flags only and do not delete primary windows.", "",
        "## Subject/block local rates", "", "| subject/block | median interval ms | p5 ms | p95 ms | effective Hz |", "|---|---:|---:|---:|---:|",
    ]
    for key in sorted(rate_summary):
        rate = rate_summary[key]
        report_lines.append(f"| {key} | {rate['median']:.6f} | {rate['p5']:.6f} | {rate['p95']:.6f} | {rate['effective_hz']:.6f} |")
    report_lines += ["", "## Non-complete windows", "", "| subject | block | window | frames | coverage | start gap ms | end gap ms | largest internal gap ms | class |", "|---|---|---|---:|---:|---:|---:|---:|---|"]
    for row in short:
        report_lines.append(f"| {row['subject']} | {row['block_id']} | {row['window_id']} | {row['frame_count']} | {row['coverage_fraction']} | {row['start_coverage_gap_ms']} | {row['end_coverage_gap_ms']} | {row['largest_internal_gap_ms']} | {row['coverage_class']} |")
    report_lines += ["", "## 97795/block4", "", "The final 97795/block4 window is independently marked `SEVERELY_INCOMPLETE`: it has 46 DLL frames and an approximately 19.8 s end gap inside the guarded 20 s window. The preceding affected tail window is also classified by the same frozen boundary rule. No Python-time backfill, synthetic timestamp, padding, or HR-based exclusion is applied.", "", "## Decision", "", "This is a denominator sensitivity contract, not an algorithm improvement claim. The primary all-window DLL-time results remain the full 335-window results; S0/S1/S2 are reported separately after this contract is frozen.", ""]
    report_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_REPORT_2026-08-30.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    manifest = {
        "status": "COVERAGE_CONTRACT_FROZEN / HR-INDEPENDENT",
        "canonical_algorithm_head_at_run": git(ALGO_ROOT, "rev-parse", "HEAD"),
        "canonical_algorithm_remote_main_at_run": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"),
        "window_input": str(WINDOWS), "window_input_sha256": sha256(WINDOWS),
        "reconstruction_manifest": str(RECON_MANIFEST), "reconstruction_manifest_sha256": sha256(RECON_MANIFEST),
        "contract": {"window_duration_ms": WINDOW_DURATION_MS, "complete_coverage_min": COMPLETE_COVERAGE_MIN, "partial_coverage_min": PARTIAL_COVERAGE_MIN, "normal_boundary_multiplier": NORMAL_BOUNDARY_MULTIPLIER, "severe_gap_ms": SEVERE_GAP_MS, "normal_internal_max_ms": NORMAL_INTERNAL_MAX_MS, "uses_hr_or_ecg": False},
        "class_counts": class_counts, "block_counts": block_counts, "local_rate_summary": rate_summary,
        "short_window_count": len(short),
        "short_windows": [{key: row[key] for key in ("subject", "block_id", "window_id", "frame_count", "coverage_fraction", "end_coverage_gap_ms", "coverage_class")} for row in short],
        "outputs": {},
    }
    for path in (output_path, report_path):
        manifest["outputs"][path.name] = {"path": path.name, "sha256": sha256(path), "row_count": len(output_rows) if path.suffix == ".csv" else None}
    manifest_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "class_counts": class_counts, "block_counts": block_counts, "short_windows": manifest["short_windows"], "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
