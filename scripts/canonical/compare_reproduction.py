#!/usr/bin/env python
"""Compare a canonical rerun with an already accepted local aggregate package.

This checker is intentionally aggregate-only. It never requires participant-level
predictions or raw data. String/categorical and integer count columns must match
exactly; floating-point columns use one predeclared tolerance for the comparison.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

FILES = {
    "behavior_baseline_v2": ["final_baseline_metrics.csv", "REPORT_FOLDS_V1.csv"],
    "behavior_longitudinal_v1": ["model_results.csv", "preprobe_window_trajectories.csv", "recovery_b1late_b2early.csv"],
    "behavior_preprobe_v1": ["preprobe_state_group_descriptives.csv", "preprobe_state_group_gee.csv"],
    "questionnaire_q1_v1": ["questionnaire_probe_association.csv", "questionnaire_behavior_association.csv", "questionnaire_ordinal_clustered_model.csv"],
    "mmwave_c1_alignment_v1": ["c1_alignment_lag_sweep_detail.csv", "c1_alignment_lag_sweep_primary_summary.csv", "c1_alignment_unavailable_methods.csv"],
    "mmwave_m1_v1": ["loso_results.csv", "incremental_deltas.csv"],
    "mmwave_c2b_v2": ["c2b_v2_model_metrics.csv", "window_30s/strict_matched_metrics.csv", "window_30s/paired_cluster_bootstrap.csv"],
    "mmwave_c2c_v1": ["c2c_model_metrics_aggregate.csv", "c2c_primary_increment_aggregate.csv", "c2c_calibration_coverage_aggregate.csv"],
    "beijing_sensor_increment_v1": ["common_probe_coverage.csv", "common_probe_incremental_models.csv", "sensor_state_group_summary_primary_common.csv"],
}


def integer_like(series: pd.Series) -> bool:
    x = pd.to_numeric(series, errors="coerce")
    finite = x[np.isfinite(x)]
    return bool(len(finite)) and bool(np.all(np.abs(finite - np.round(finite)) < 1e-12))


def canonicalize(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    exact: list[str] = []
    numeric: list[str] = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            if integer_like(df[col]) and (col.startswith("n_") or col.endswith("_n") or col in {"fold", "window_s", "sessions", "subjects", "matched_beats", "ecg_beats", "radar_beats", "bootstrap_valid"}):
                exact.append(col)
            else:
                numeric.append(col)
        else:
            exact.append(col)
    if exact:
        key = df[exact].fillna("<NA>").astype(str).agg("\x1f".join, axis=1)
        order = np.argsort(key.to_numpy(), kind="stable")
        df = df.iloc[order].reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    return df, exact, numeric


def compare_csv(expected: Path, actual: Path, atol: float, rtol: float) -> dict:
    if not expected.is_file() or not actual.is_file():
        return {"status": "FAIL", "reason": "missing_file", "expected_exists": expected.is_file(), "actual_exists": actual.is_file()}
    e = pd.read_csv(expected)
    a = pd.read_csv(actual)
    if list(e.columns) != list(a.columns):
        return {"status": "FAIL", "reason": "column_mismatch", "expected_columns": list(e.columns), "actual_columns": list(a.columns)}
    if e.shape != a.shape:
        return {"status": "FAIL", "reason": "shape_mismatch", "expected_shape": e.shape, "actual_shape": a.shape}
    e, exact, numeric = canonicalize(e)
    a, exact_a, numeric_a = canonicalize(a)
    if exact != exact_a or numeric != numeric_a:
        return {"status": "FAIL", "reason": "type_classification_mismatch"}
    exact_failures = []
    for col in exact:
        ev = e[col].fillna("<NA>").astype(str).to_numpy()
        av = a[col].fillna("<NA>").astype(str).to_numpy()
        if not np.array_equal(ev, av):
            exact_failures.append(col)
    numeric_failures = []
    max_abs_error = {}
    for col in numeric:
        ev = pd.to_numeric(e[col], errors="coerce").to_numpy(float)
        av = pd.to_numeric(a[col], errors="coerce").to_numpy(float)
        diff = np.abs(ev - av)
        finite = diff[np.isfinite(diff)]
        max_abs_error[col] = float(np.max(finite)) if len(finite) else 0.0
        if not np.allclose(ev, av, atol=atol, rtol=rtol, equal_nan=True):
            numeric_failures.append(col)
    ok = not exact_failures and not numeric_failures
    return {
        "status": "PASS" if ok else "FAIL",
        "rows": len(e),
        "exact_columns": exact,
        "numeric_columns": numeric,
        "exact_failures": exact_failures,
        "numeric_failures": numeric_failures,
        "max_abs_error": max_abs_error,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("analysis", choices=sorted(FILES))
    ap.add_argument("--expected", type=Path, required=True, help="already accepted aggregate package")
    ap.add_argument("--actual", type=Path, required=True, help="new canonical rerun package")
    ap.add_argument("--atol", type=float, default=1e-8)
    ap.add_argument("--rtol", type=float, default=1e-7)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    rows = {}
    for rel in FILES[args.analysis]:
        rows[rel] = compare_csv(args.expected / rel, args.actual / rel, args.atol, args.rtol)
    status = "PASS" if all(v["status"] == "PASS" for v in rows.values()) else "FAIL"
    result = {
        "schema_version": "focuswave-reproduction-equivalence-v1",
        "analysis_id": args.analysis,
        "status": status,
        "atol": args.atol,
        "rtol": args.rtol,
        "files": rows,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    if status != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
