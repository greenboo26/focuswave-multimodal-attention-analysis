"""Diagnostic constant-delay sweep for frozen C1 beat timestamps.

No raw ADC is read. Existing ECG peaks and radar beat timestamps saved by C1c
and C1d are reused. Lag sign follows the frozen C1 evaluator: adjusted radar
time = radar time - delay_ms / 1000.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ALGO = Path(r"D:\Project\厚粲杯\08_算法")
C1 = Path(r"D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1")
OUT = Path(r"D:\Project\厚粲杯\11_数据\derived\c1_alignment_robustness_audit_v1")
SUBJECTS = ["97793", "9779", "97795"]
TOLERANCES = [50.0, 75.0, 100.0, 150.0]
FIXED_DELAY_MS = -18.000000000000682
LAGS = np.arange(-250.0, 250.0 + 0.001, 5.0)


def load_c1():
    path = ALGO / "scripts/run_c1c_mmhrv_pilot.py"
    spec = importlib.util.spec_from_file_location("c1_frozen_metrics", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_assets(subject: str):
    c1c = np.load(C1 / subject / "c1c_waveforms_replayed.npz")
    c1d = np.load(C1 / subject / "c1d_similarity_dp_assets.npz")
    return {
        "c1c_local_peak": np.asarray(c1c["local_peak_times_s"], float),
        "c1d_radarbeat_global_dp": np.asarray(c1d["dp_peak_times_s"], float),
        "ecg": np.asarray(c1c["ecg_peak_times_s"], float),
    }


def main():
    c1 = load_c1()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    unavailable = []
    for subject in SUBJECTS:
        a = load_assets(subject)
        for method in ["c1c_local_peak", "c1d_radarbeat_global_dp"]:
            est, ref = a[method], a["ecg"]
            for tol in TOLERANCES:
                fixed = c1.metrics(ref, est, tol, FIXED_DELAY_MS)
                sweep = [(float(lag), c1.metrics(ref, est, tol, float(lag))) for lag in LAGS]
                best_lag, best = max(sweep, key=lambda x: (x[1]["f1"] if x[1]["f1"] is not None else -1.0, x[1]["recall"] if x[1]["recall"] is not None else -1.0, -abs(x[0])))
                rows.append({
                    "subject": subject, "method": method, "tolerance_ms": tol,
                    "fixed_delay_ms": FIXED_DELAY_MS, "optimal_constant_delay_ms": best_lag,
                    "fixed_f1": fixed["f1"], "optimal_f1": best["f1"],
                    "fixed_recall": fixed["recall"], "optimal_recall": best["recall"],
                    "fixed_precision": fixed["precision"], "optimal_precision": best["precision"],
                    "f1_gain": best["f1"] - fixed["f1"], "recall_gain": best["recall"] - fixed["recall"],
                    "fixed_ibi_mae_ms": fixed["ibi_mae_ms"], "optimal_ibi_mae_ms": best["ibi_mae_ms"],
                    "fixed_timing_mae_ms": fixed["timing_mae_ms"], "optimal_timing_mae_ms": best["timing_mae_ms"],
                    "ecg_beats": fixed["ecg_beats"], "radar_beats": fixed["radar_beats"],
                })
        unavailable.extend([
            {"subject": subject, "method": "c1b_project_bandpass", "status": "timestamp_asset_not_saved_no_raw_recompute_allowed"},
            {"subject": subject, "method": "c1b_python_amf", "status": "timestamp_asset_not_saved_no_raw_recompute_allowed"},
            {"subject": subject, "method": "c1b_v311_vmd", "status": "timestamp_asset_not_saved_no_raw_recompute_allowed"},
        ])
    detail = pd.DataFrame(rows)
    detail.to_csv(OUT / "c1_alignment_lag_sweep_detail.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(unavailable).to_csv(OUT / "c1_alignment_unavailable_methods.csv", index=False, encoding="utf-8-sig")

    primary = detail[detail.tolerance_ms == 75.0]
    summary = primary.groupby("method", as_index=False).agg(
        sessions=("subject", "nunique"), mean_fixed_f1=("fixed_f1", "mean"), mean_optimal_f1=("optimal_f1", "mean"),
        mean_f1_gain=("f1_gain", "mean"), sessions_f1_gain_ge_010=("f1_gain", lambda x: int((x >= .10).sum())),
        mean_fixed_recall=("fixed_recall", "mean"), mean_optimal_recall=("optimal_recall", "mean"),
        mean_recall_gain=("recall_gain", "mean"), mean_fixed_ibi_mae_ms=("fixed_ibi_mae_ms", "mean"),
        mean_optimal_ibi_mae_ms=("optimal_ibi_mae_ms", "mean"), mean_optimal_delay_ms=("optimal_constant_delay_ms", "mean"),
    )
    summary.to_csv(OUT / "c1_alignment_lag_sweep_primary_summary.csv", index=False, encoding="utf-8-sig")
    material = bool((primary.f1_gain >= .10).sum() >= 2 and (primary.optimal_f1.mean() - primary.fixed_f1.mean()) >= .10)
    status = "C1_ALIGNMENT_ASSUMPTION_INVALID_REOPEN_HRV" if material else "C1_ALIGNMENT_AUDIT_PASS_STOP_HRV_CONFIRMED"
    manifest = {
        "status": status, "scope": "frozen C1c/C1d timestamp assets only", "subjects": SUBJECTS,
        "methods_available": ["c1c_local_peak", "c1d_radarbeat_global_dp"],
        "methods_unavailable": ["c1b_project_bandpass", "c1b_python_amf", "c1b_v311_vmd"],
        "delay_convention": "adjusted_radar = radar - delay_ms/1000; frozen delay = -18 ms",
        "lag_grid_ms": [-250.0, 250.0, 5.0], "tolerances_ms": TOLERANCES,
        "raw_adc_read": False, "front_end_changed": False, "ecg_used_for_tuning": False,
        "material_improvement_rule": "mean F1 gain >= 0.10 and >=2/3 sessions gain >=0.10 at primary ±75 ms",
    }
    (OUT / "c1_alignment_robustness_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# C1 alignment robustness audit",
        "",
        f"Status: `{status}`",
        "",
        "本审计只读取 C1c replay 与 C1d backend 已保存的 ECG/radar beat timestamps；没有读取 raw ADC，没有修改前端、VMD、峰检测或使用 ECG 调参。delay 符号与冻结 evaluator 一致：adjusted radar = radar - delay_ms/1000。",
        "",
        "## Primary ±75 ms",
        "",
        "| method | mean fixed F1 | mean optimal-lag F1 | mean gain | sessions gain >= .10 | mean fixed recall | mean optimal recall | mean optimal delay |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in summary.iterrows():
        lines.append(f"| {r['method']} | {r['mean_fixed_f1']:.3f} | {r['mean_optimal_f1']:.3f} | {r['mean_f1_gain']:.3f} | {int(r['sessions_f1_gain_ge_010'])}/3 | {r['mean_fixed_recall']:.3f} | {r['mean_optimal_recall']:.3f} | {r['mean_optimal_delay_ms']:.1f} ms |")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "- Lag sweep is diagnostic only, not a formal performance result.",
        "- C1b baseline timestamp assets were not saved in the C1c replay package; they were not regenerated because this audit forbids raw/front-end recomputation.",
        "- IBI fields are reported using the same evaluator and matched-beat rule; changing lag can change the matched subset, so they are not interpreted as an invariant full-sequence IBI test.",
        "- The final status applies to the two available frozen timestamp methods only; the unavailable C1b methods are explicitly listed in `c1_alignment_unavailable_methods.csv`.",
    ]
    (OUT / "C1_ALIGNMENT_ROBUSTNESS_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
