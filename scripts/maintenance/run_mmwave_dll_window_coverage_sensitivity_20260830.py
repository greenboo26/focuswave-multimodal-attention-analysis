"""Run the pre-registered S0/S1/S2 denominator sensitivity on frozen HR rows.

This script filters the already computed DLL-time comparison only. It does not
rerun or modify the HR estimator, target selector, gate, filter, ECG reference,
or primary all-window outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
COMPARISON = RESULT_ROOT / "MMWAVE_TIME_SEMANTICS_HR_COMPARISON.csv"
COVERAGE = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT.csv"
COVERAGE_MANIFEST = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_MANIFEST.json"
ARMS = ("arm0", "arm1", "arm2")
SELECTIONS = {
    "S0_all_windows": lambda row: True,
    "S1_exclude_severely_incomplete": lambda row: row["coverage_class"] != "SEVERELY_INCOMPLETE",
    "S2_complete_only": lambda row: row["coverage_class"] == "COMPLETE",
}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
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


def numeric(value):
    if value in (None, "", "None", "nan", "NaN"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def calculate_metrics(rows: list[dict], selection: str, arm: str) -> dict:
    value_key = f"new_{arm}_hr_bpm"
    pairs = [(numeric(row.get(value_key)), numeric(row.get("ecg_hr_bpm"))) for row in rows]
    pairs = [(estimate, reference) for estimate, reference in pairs if estimate is not None and reference is not None]
    errors = np.asarray([estimate - reference for estimate, reference in pairs], dtype=float)
    absolute = np.abs(errors)
    estimates = [estimate for estimate, _ in pairs]
    references = [reference for _, reference in pairs]
    pearson = float(pearsonr(estimates, references).statistic) if len(pairs) >= 2 else None
    spearman = float(spearmanr(estimates, references).statistic) if len(pairs) >= 2 else None
    return {
        "selection": selection,
        "arm": arm,
        "selected_window_n": len(rows),
        "valid_n": len(pairs),
        "coverage_pct": round(100 * len(pairs) / len(rows), 3) if rows else None,
        "mae_bpm": round(float(np.mean(absolute)), 6) if len(errors) else None,
        "median_ae_bpm": round(float(np.median(absolute)), 6) if len(errors) else None,
        "rmse_bpm": round(float(np.sqrt(np.mean(errors ** 2))), 6) if len(errors) else None,
        "bias_bpm": round(float(np.mean(errors)), 6) if len(errors) else None,
        "pearson_r": round(pearson, 6) if pearson is not None else None,
        "spearman_r": round(spearman, 6) if spearman is not None else None,
    }


def main() -> int:
    comparison = read_csv(COMPARISON)
    coverage = read_csv(COVERAGE)
    coverage_by_key = {(row["subject"], row["block_id"], row["window_id"]): row for row in coverage}
    if len(comparison) != len(coverage) or set(coverage_by_key) != {(row["subject"], row["block_id"], row["window_id"]) for row in comparison}:
        raise RuntimeError("comparison and coverage keys do not match")
    joined = []
    for row in comparison:
        key = (row["subject"], row["block_id"], row["window_id"])
        joined.append({**row, **{f"coverage_{k}": v for k, v in coverage_by_key[key].items() if k not in {"subject", "block_id", "window_id"}}})
    metric_rows = []
    block_rows = []
    selection_rows = {}
    for selection, predicate in SELECTIONS.items():
        selected = [row for row in joined if predicate(coverage_by_key[(row["subject"], row["block_id"], row["window_id"])])]
        selection_rows[selection] = selected
        for arm in ARMS:
            metric_rows.append(calculate_metrics(selected, selection, arm))
        groups = sorted({(row["subject"], row["block_id"]) for row in selected})
        for subject, block_id in groups:
            block_selected = [row for row in selected if row["subject"] == subject and row["block_id"] == block_id]
            for arm in ARMS:
                valid_n = sum(numeric(row.get(f"new_{arm}_hr_bpm")) is not None and numeric(row.get("ecg_hr_bpm")) is not None for row in block_selected)
                block_rows.append({"selection": selection, "subject": subject, "block_id": block_id, "selected_window_n": len(block_selected), "valid_n": valid_n, "arm": arm})
    metric_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY.csv"
    block_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_BY_BLOCK.csv"
    write_csv(metric_path, metric_rows, ["selection", "arm", "selected_window_n", "valid_n", "coverage_pct", "mae_bpm", "median_ae_bpm", "rmse_bpm", "bias_bpm", "pearson_r", "spearman_r"])
    write_csv(block_path, block_rows, ["selection", "subject", "block_id", "selected_window_n", "valid_n", "arm"])
    s0 = selection_rows["S0_all_windows"]
    s2 = selection_rows["S2_complete_only"]
    delta = {}
    for arm in ARMS:
        s0_metrics = next(row for row in metric_rows if row["selection"] == "S0_all_windows" and row["arm"] == arm)
        s2_metrics = next(row for row in metric_rows if row["selection"] == "S2_complete_only" and row["arm"] == arm)
        delta[arm] = {"mae_delta_s2_minus_s0_bpm": round(s2_metrics["mae_bpm"] - s0_metrics["mae_bpm"], 6) if s0_metrics["mae_bpm"] is not None and s2_metrics["mae_bpm"] is not None else None, "valid_n_s0": s0_metrics["valid_n"], "valid_n_s2": s2_metrics["valid_n"]}
    report_lines = [
        "# mmWave DLL-time window coverage denominator sensitivity — 2026-08-30", "",
        "状态：`PARTIAL / COVERAGE_SENSITIVITY_COMPLETE`", "",
        "本轮只过滤已经完成的 DLL-time HR comparison rows；没有重跑或修改 HR estimator、target selector、gate、filter、ECG reference 或 primary all-window outputs。", "",
        "## Frozen selections", "",
        "- `S0_all_windows`: all 335 DLL-time windows, including severe coverage rows.",
        "- `S1_exclude_severely_incomplete`: exclude only rows marked `SEVERELY_INCOMPLETE` by the pre-frozen timestamp-only contract.",
        "- `S2_complete_only`: retain only rows marked `COMPLETE` by that same contract.",
        "- The coverage contract was frozen before this sensitivity and does not use ECG HR, radar HR, abs error, or arm performance.",
        f"- Selection sizes: S0=`{len(s0)}`, S1=`{len(selection_rows['S1_exclude_severely_incomplete'])}`, S2=`{len(s2)}`; S1 and S2 are identical here because no window is classified `PARTIAL`.", "",
        "## Metrics", "", "| selection | arm | selected n | valid n | coverage % | MAE | median AE | RMSE | bias | Pearson | Spearman |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    report_lines.extend(f"| {row['selection']} | {row['arm']} | {row['selected_window_n']} | {row['valid_n']} | {row['coverage_pct']} | {row['mae_bpm']} | {row['median_ae_bpm']} | {row['rmse_bpm']} | {row['bias_bpm']} | {row['pearson_r']} | {row['spearman_r']} |" for row in metric_rows)
    report_lines += ["", "## Subject/block remaining n", "", "The complete table is in `MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_BY_BLOCK.csv`; only `97795/block4` changes from 28 to 26 selected windows under S1/S2. Per-arm valid n is retained because ARM1 has estimator-level missing rows independent of coverage class.", "", "## Interpretation", "", f"- S0→S2 MAE deltas (bpm): `{delta}`.", "- Coverage finding: `SEVERE_COVERAGE_FAILURE_LOCALIZED_ONLY` and `COVERAGE_NOT_PRIMARY_HR_EXPLANATION`. Severe incompleteness is localized to two tail windows in 97795/block4; the 333 complete windows retain the high-error diagnostic pattern.", "- Any S1/S2 change is a validity sensitivity on complete acquisition windows, not an HR algorithm improvement and not a reason to delete or replace the S0 primary result.", "- HR/BR remain `HOLD`; HRV remains `BLOCKED`; Issue #16 remains `PAUSED`.", ""]
    report_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_REPORT_2026-08-30.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    manifest = {
        "status": "PARTIAL / COVERAGE_SENSITIVITY_COMPLETE",
        "canonical_algorithm_head_at_run": git(ALGO_ROOT, "rev-parse", "HEAD"),
        "canonical_algorithm_remote_main_at_run": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"),
        "comparison_input": str(COMPARISON), "comparison_input_sha256": sha256(COMPARISON),
        "coverage_input": str(COVERAGE), "coverage_input_sha256": sha256(COVERAGE),
        "coverage_manifest": str(COVERAGE_MANIFEST), "coverage_manifest_sha256": sha256(COVERAGE_MANIFEST),
        "selection_contract": {"S0_all_windows": "all windows", "S1_exclude_severely_incomplete": "coverage_class != SEVERELY_INCOMPLETE", "S2_complete_only": "coverage_class == COMPLETE", "frozen_before_metrics": True, "uses_hr_or_ecg": False},
        "selection_counts": {selection: len(rows) for selection, rows in selection_rows.items()},
        "severe_windows": [{key: coverage_by_key[(row["subject"], row["block_id"], row["window_id"])][key] for key in ("subject", "block_id", "window_id", "frame_count", "coverage_fraction", "end_coverage_gap_ms", "coverage_class")} for row in joined if coverage_by_key[(row["subject"], row["block_id"], row["window_id"])]["coverage_class"] == "SEVERELY_INCOMPLETE"],
        "metrics": metric_rows, "s0_to_s2_delta": delta,
        "interpretation": ["SEVERE_COVERAGE_FAILURE_LOCALIZED_ONLY", "COVERAGE_NOT_PRIMARY_HR_EXPLANATION"],
        "outputs": {},
    }
    for path in (metric_path, block_path, report_path):
        manifest["outputs"][path.name] = {"path": path.name, "sha256": sha256(path), "row_count": len(metric_rows) if path == metric_path else len(block_rows) if path == block_path else None}
    manifest_path = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_SENSITIVITY_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "selection_counts": manifest["selection_counts"], "metrics": metric_rows, "s0_to_s2_delta": delta, "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
