"""Controlled 20 s versus historical 60 s mmWave HR comparison.

This is an execution-layer audit only.  It reuses the existing v3.1.1
bandpass/periodogram/peak/course chain and the historical fixed target.  It
does not introduce an estimator, change the producer, or select a window
length from the resulting errors.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_20S_INPUT = RESULT_ROOT / "mmwave_ecg_block_window_comparison.csv"
HISTORICAL_SELECTION_ROOT = Path(
    r"D:\Project\厚粲杯\08_算法\output\20_生理金标准验证\06_HR_COURSE_99_CORRECTED_GATE"
)
DATA_ROOT = Path(r"D:\acq_mmwave_data")
SUBJECTS = ("97793", "9779", "97795")
SHORT_WINDOW_S = 20.0
HISTORICAL_WINDOW_S = 60.0
STEP_S = 10.0
BOUNDARY_GUARD_S = 5.0
FS_HZ = 100.0
HISTORICAL_BIN_SPACING_M = 0.037
HISTORICAL_GATE_BINS = (9, 40)
ECG24_EXPECTED_COUNTS = {"input_window_n": 335, "ECG_VALID": 325, "ECG_INVALID": 10, "UNRESOLVED": 0}
ECG24_LINEAGE_COMMIT = "d2d09f8ac502600d3a1241e33c429bd53756fa45"
ECG24_MANIFEST_REPO_PATH = "docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/ECG_ELIGIBILITY_MANIFEST.json"
ECG24_MANIFEST_COMMIT_SHA256 = "0806cb4f0e477788ee7cd604e3d04c811654fb692f2840767249982ebc5ba258"
ECG_VALID_RULE = (
    "#24 gold_standard_qa.ecg_qa: SOS 0.5-40 Hz; R-peak distance 0.30 s "
    "prominence 0.25; IBI 300-2000 ms; adjacent IBI change >20% rejected; "
    "valid IBI coverage >=0.80; minimum 3 valid IBI; marker mismatch warning only"
)
RUN_ID = "issue25_window_length_20260830"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
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
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unavailable"


def as_float(value):
    try:
        if value in (None, "", "nan", "NaN"):
            return None
        result = float(value)
        return result if np.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def bool_value(value) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def find_ecg24_root() -> Path | None:
    """Find the sibling #24 evidence package without requiring a fixed worktree name."""
    worktrees_root = ALGO_ROOT.parents[1] if len(ALGO_ROOT.parents) > 1 else None
    if worktrees_root is None or not worktrees_root.exists():
        return None
    candidates = sorted(
        path
        for path in worktrees_root.glob("*/08_算法/docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION")
        if path != RESULT_ROOT
        and (path / "ECG_ELIGIBILITY_MANIFEST.json").exists()
        and (path / "ECG_ELIGIBILITY_BLOCK_SUMMARY.csv").exists()
        and (path / "ECG_ARM_METRICS_VALID_DENOMINATOR.csv").exists()
    )
    return candidates[0] if candidates else None


def load_ecg24_evidence() -> dict:
    root = find_ecg24_root()
    if root is None:
        return {
            "source": "scheduler_supplied_issue24_aggregate",
            "root": None,
            "counts": dict(ECG24_EXPECTED_COUNTS),
            "files": {},
            "lineage": {},
        }
    manifest_path = root / "ECG_ELIGIBILITY_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    files = {
        name: {
            "path": str(root / name),
            "sha256": sha256(root / name),
        }
        for name in (
            "ECG_ELIGIBILITY_MANIFEST.json",
            "ECG_ELIGIBILITY_BLOCK_SUMMARY.csv",
            "ECG_ARM_METRICS_VALID_DENOMINATOR.csv",
        )
    }
    script = root.parents[3] / "scripts" / "maintenance" / "run_ecg_eligibility_dll_windows_20260830.py"
    if script.exists():
        files["issue24_eligibility_script"] = {"path": str(script), "sha256": sha256(script)}
    counts = {"input_window_n": 335, **manifest.get("eligibility_counts", {})}
    return {
        "source": "issue24_isolated_worktree_aggregate",
        "root": str(root),
        "counts": counts,
        "files": files,
        "lineage": {
            "issue24_commit": ECG24_LINEAGE_COMMIT,
            "manifest_repo_path": ECG24_MANIFEST_REPO_PATH,
            "manifest_commit_sha256": ECG24_MANIFEST_COMMIT_SHA256,
            "issue24_run_id": manifest.get("run_id"),
            "issue24_git_head": manifest.get("git", {}).get("head_at_run"),
            "issue24_origin_main": manifest.get("git", {}).get("origin_main_at_run"),
            "rules": manifest.get("rules", {}),
        },
    }


def ecg24_window(gold, ecg: np.ndarray, fs: float, start_sample: int, end_sample: int) -> dict:
    """Apply the exact #24 eligibility adapter to one ECG interval."""
    i0, i1 = int(start_sample), int(end_sample)
    if i0 < 0 or i1 > len(ecg) or i1 <= i0:
        return {
            "ecg_eligibility": "UNRESOLVED",
            "ecg_hr_bpm": None,
            "ecg_reject_reason": "ecg_sample_bounds_unresolved",
            "ecg_qa_note": "bounds",
            "ecg_n_rpeaks": 0,
            "ecg_n_valid_ibi": 0,
            "ecg_n_ibi_range_rejected": 0,
            "ecg_n_abnormal_fluctuation_rejected": 0,
            "ecg_effective_beat_coverage": 0.0,
            "ecg_quality_usable": False,
        }
    hr, qa = gold.ecg_qa(ecg, fs, i0, i1)
    reasons: list[str] = []
    if qa.get("note") == "too_short":
        reasons.append("short_window")
    if qa.get("note") == "too_few_peaks":
        reasons.append("too_few_rpeaks")
    if qa.get("note") == "too_few_ibi":
        reasons.append("insufficient_valid_ibi")
    if int(qa.get("n_ibi_range_rejected", 0) or 0) > 0:
        reasons.append("ibi_outside_plausible_300_2000ms")
    if int(qa.get("n_pc_rejected", 0) or 0) > 0:
        reasons.append("abnormal_adjacent_ibi_fluctuation_gt20pct")
    if float(qa.get("valid_ratio", 0.0) or 0.0) < 0.80:
        reasons.append("effective_beat_coverage_below_80pct")
    if hr is None and "insufficient_valid_ibi" not in reasons:
        reasons.append("no_finite_ecg_hr")
    status = "ECG_INVALID" if reasons else ("ECG_VALID" if hr is not None and qa.get("usable") else "ECG_INVALID")
    return {
        "ecg_eligibility": status,
        "ecg_hr_bpm": round(float(hr), 6) if hr is not None and np.isfinite(hr) else None,
        "ecg_reject_reason": "|".join(dict.fromkeys(reasons)) if reasons else "none",
        "ecg_qa_note": qa.get("note", ""),
        "ecg_n_rpeaks": qa.get("n_raw", 0),
        "ecg_n_valid_ibi": qa.get("n_kept", 0),
        "ecg_n_ibi_range_rejected": qa.get("n_ibi_range_rejected", 0),
        "ecg_n_abnormal_fluctuation_rejected": qa.get("n_pc_rejected", 0),
        "ecg_effective_beat_coverage": round(float(qa.get("valid_ratio", 0.0)), 6),
        "ecg_quality_usable": bool(qa.get("usable")),
    }


def local_interval_median_ms(timestamps: np.ndarray, start: int, end: int) -> float:
    values = np.asarray(timestamps[max(0, start) : min(len(timestamps), end), 2], dtype=float)
    diffs = np.diff(values)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    return float(np.median(diffs)) if len(diffs) else 10.0


def raw_coverage(timestamps: np.ndarray, start_ms: int, end_ms: int, local_median_ms: float) -> dict:
    dll = np.asarray(timestamps[:, 2], dtype=np.int64)
    i0 = int(np.searchsorted(dll, int(start_ms), side="left"))
    i1 = int(np.searchsorted(dll, int(end_ms), side="right"))
    count = max(0, i1 - i0)
    duration_ms = float(end_ms - start_ms)
    expected = duration_ms / local_median_ms + 1.0 if local_median_ms > 0 else 0.0
    coverage = min(count / expected, 1.0) if expected else 0.0
    if count:
        selected = dll[i0:i1]
        start_gap = float(selected[0] - start_ms)
        end_gap = float(end_ms - selected[-1])
        largest_internal = float(np.max(np.diff(selected))) if count > 1 else duration_ms
    else:
        start_gap = duration_ms
        end_gap = duration_ms
        largest_internal = duration_ms
    return {
        "start_row": i0,
        "end_row_exclusive": i1,
        "frame_count": count,
        "expected_frame_count": round(expected, 6),
        "coverage_fraction": round(coverage, 6),
        "local_interval_median_ms": round(local_median_ms, 6),
        "start_coverage_gap_ms": round(start_gap, 6),
        "end_coverage_gap_ms": round(end_gap, 6),
        "largest_internal_gap_ms": round(largest_internal, 6),
    }


def metric_rows(rows: list[dict], value_key: str, coverage_key: str, signal_key: str, window_s: float) -> dict:
    eligible = [
        row
        for row in rows
        if bool_value(row.get("ecg_valid_pair"))
        and as_float(row.get(value_key)) is not None
        and as_float(row.get("ecg_hr_pair_bpm")) is not None
    ]
    estimates = np.asarray([float(row[value_key]) for row in eligible], dtype=float)
    refs = np.asarray([float(row["ecg_hr_pair_bpm"]) for row in eligible], dtype=float)
    errors = estimates - refs
    coverage = np.asarray([float(row[coverage_key]) for row in rows], dtype=float)
    signal = np.asarray(
        [float(row[signal_key]) for row in rows if as_float(row.get(signal_key)) is not None], dtype=float
    )
    return {
        "window_s": window_s,
        "pair_grid_n": len(rows),
        "ecg_valid_pair_n": sum(bool_value(row.get("ecg_valid_pair")) for row in rows),
        "estimator_valid_n": sum(as_float(row.get(value_key)) is not None for row in rows),
        "metric_n": len(eligible),
        "coverage_mean": round(float(np.mean(coverage)), 6) if len(coverage) else None,
        "coverage_median": round(float(np.median(coverage)), 6) if len(coverage) else None,
        "signal_usable_ratio_mean": round(float(np.mean(signal)), 6) if len(signal) else None,
        "frequency_resolution_hz": round(FS_HZ / (window_s * FS_HZ), 9),
        "frequency_resolution_bpm": round(60.0 / window_s, 9),
        "mae_bpm": round(float(np.mean(np.abs(errors))), 6) if len(errors) else None,
        "median_ae_bpm": round(float(np.median(np.abs(errors))), 6) if len(errors) else None,
        "bias_estimator_minus_ecg_bpm": round(float(np.mean(errors)), 6) if len(errors) else None,
        "pearson_r": round(float(pearsonr(estimates, refs).statistic), 6) if len(errors) >= 2 else None,
        "spearman_r": round(float(spearmanr(estimates, refs).statistic), 6) if len(errors) >= 2 else None,
    }


def pairwise(rows: list[dict]) -> dict:
    common = [
        row
        for row in rows
        if bool_value(row.get("ecg_valid_pair"))
        and as_float(row.get("hr_20s_bpm")) is not None
        and as_float(row.get("hr_60s_bpm")) is not None
    ]
    delta = np.asarray(
        [abs(float(row["hr_20s_bpm"]) - float(row["ecg_hr_pair_bpm"])) - abs(float(row["hr_60s_bpm"]) - float(row["ecg_hr_pair_bpm"])) for row in common],
        dtype=float,
    )
    return {
        "common_n": len(common),
        "mean_ae_delta_20s_minus_60s_bpm": round(float(np.mean(delta)), 6) if len(delta) else None,
        "median_ae_delta_20s_minus_60s_bpm": round(float(np.median(delta)), 6) if len(delta) else None,
        "20s_better_n": int(np.sum(delta < 0)) if len(delta) else 0,
        "tie_n": int(np.sum(delta == 0)) if len(delta) else 0,
        "60s_better_n": int(np.sum(delta > 0)) if len(delta) else 0,
    }


def build_pair_rows(rerun, same, algo, gold) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    block_audits: list[dict] = []
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        events = rerun.load_events(subject)
        physical, _digital = rerun.decode_biopac_markers(subject)
        blocks, audits = rerun.block_intervals(subject, timestamps, events, physical)
        audit_by_id = {row["block_id"]: row for row in audits}
        reader = rerun.PartReader(subject)
        ecg, rsp, fs = rerun.load_ecg_reference(subject)
        target = same.historical_target(subject)
        for block in blocks:
            audit = audit_by_id[block["block_id"]]
            if block["status"] != "complete" or as_float(audit.get("ecg_fit_slope_samples_per_ms")) is None:
                continue
            block_start = int(block["start_event_unix_ms"])
            block_end = int(block["end_event_unix_ms"])
            guarded_start = block_start + int(BOUNDARY_GUARD_S * 1000)
            guarded_end = block_end - int(BOUNDARY_GUARD_S * 1000)
            block_i0 = int(np.searchsorted(timestamps[:, 2], guarded_start, side="left"))
            block_i1 = int(np.searchsorted(timestamps[:, 2], guarded_end, side="right"))
            median_ms = local_interval_median_ms(timestamps, block_i0, block_i1)
            slope = float(audit["ecg_fit_slope_samples_per_ms"])
            intercept = float(audit["ecg_fit_intercept_sample"])
            endpoint = guarded_start + int(HISTORICAL_WINDOW_S * 1000)
            index = 1
            while endpoint <= guarded_end:
                short_start = endpoint - int(SHORT_WINDOW_S * 1000)
                long_start = endpoint - int(HISTORICAL_WINDOW_S * 1000)
                short_cov = raw_coverage(timestamps, short_start, endpoint, median_ms)
                long_cov = raw_coverage(timestamps, long_start, endpoint, median_ms)
                if short_cov["frame_count"] == 0 or long_cov["frame_count"] == 0:
                    endpoint += int(STEP_S * 1000)
                    index += 1
                    continue
                short_iq = reader.slice(short_cov["start_row"], short_cov["end_row_exclusive"])
                long_iq = reader.slice(long_cov["start_row"], long_cov["end_row_exclusive"])
                short_est = same.historical_20s_adaptation(
                    algo, short_iq, target["heart_channel"], target["heart_bin"]
                )
                long_est = same.historical_20s_adaptation(
                    algo, long_iq, target["heart_channel"], target["heart_bin"]
                )
                short_i0 = int(round(slope * short_start + intercept))
                short_i1 = int(round(slope * endpoint + intercept))
                long_i0 = int(round(slope * long_start + intercept))
                long_i1 = int(round(slope * endpoint + intercept))
                short_ref = ecg24_window(gold, ecg, fs, short_i0, short_i1)
                long_ref = ecg24_window(gold, ecg, fs, long_i0, long_i1)
                short_valid = short_ref["ecg_eligibility"] == "ECG_VALID"
                long_valid = long_ref["ecg_eligibility"] == "ECG_VALID"
                pair_valid = short_valid and long_valid
                row = {
                    "subject": subject,
                    "block_id": block["block_id"],
                    "pair_id": f"{block['block_id']}_e{index:03d}",
                    "endpoint_unix_ms": endpoint,
                    "endpoint_s_from_block": round((endpoint - block_start) / 1000.0, 3),
                    "window_20s_start_unix_ms": short_start,
                    "window_20s_end_unix_ms": endpoint,
                    "window_60s_start_unix_ms": long_start,
                    "window_60s_end_unix_ms": endpoint,
                    "target_channel": target["heart_channel"],
                    "target_bin": target["heart_bin"],
                    "target_distance_m": round(target["heart_bin"] * HISTORICAL_BIN_SPACING_M, 3),
                    "target_source": target["source"],
                    "historical_gate_bins": f"{HISTORICAL_GATE_BINS[0]}-{HISTORICAL_GATE_BINS[1]}",
                    "mmwave_time_contract": "DLL_timestamp_column_3_searchsorted; block_event_markers; no_python_time_backfill",
                    "ecg_alignment_contract": "per_block_event_marker_to_physical_digital_pulse_affine_fit",
                    "ecg_valid_rule": ECG_VALID_RULE,
                    "ecg_20s_hr_bpm": short_ref.get("ecg_hr_bpm"),
                    "ecg_60s_hr_bpm": long_ref.get("ecg_hr_bpm"),
                    "ecg_hr_pair_bpm": short_ref.get("ecg_hr_bpm") if pair_valid else None,
                    "ecg_20s_status": short_ref.get("ecg_eligibility"),
                    "ecg_60s_status": long_ref.get("ecg_eligibility"),
                    "ecg_20s_reject_reason": short_ref.get("ecg_reject_reason"),
                    "ecg_60s_reject_reason": long_ref.get("ecg_reject_reason"),
                    "ecg_20s_n_rpeaks": short_ref.get("ecg_n_rpeaks"),
                    "ecg_60s_n_rpeaks": long_ref.get("ecg_n_rpeaks"),
                    "ecg_20s_valid_ibi": short_ref.get("ecg_n_valid_ibi"),
                    "ecg_60s_valid_ibi": long_ref.get("ecg_n_valid_ibi"),
                    "ecg_20s_effective_beat_coverage": short_ref.get("ecg_effective_beat_coverage"),
                    "ecg_60s_effective_beat_coverage": long_ref.get("ecg_effective_beat_coverage"),
                    "ecg_valid_pair": pair_valid,
                    "hr_20s_bpm": short_est["hr_bpm"],
                    "hr_60s_bpm": long_est["hr_bpm"],
                    "hr_20s_valid": short_est["valid"],
                    "hr_60s_valid": long_est["valid"],
                    "hr_20s_missing_reason": short_est["missing_reason"],
                    "hr_60s_missing_reason": long_est["missing_reason"],
                    "hr_20s_n_peaks": short_est["n_peaks"],
                    "hr_60s_n_peaks": long_est["n_peaks"],
                    "hr_20s_signal_usable_ratio": short_est["coverage"],
                    "hr_60s_signal_usable_ratio": long_est["coverage"],
                    "hr_20s_frequency_resolution_hz": round(FS_HZ / short_cov["frame_count"], 9),
                    "hr_60s_frequency_resolution_hz": round(FS_HZ / long_cov["frame_count"], 9),
                    "hr_20s_frequency_resolution_bpm": round(60.0 * FS_HZ / short_cov["frame_count"], 9),
                    "hr_60s_frequency_resolution_bpm": round(60.0 * FS_HZ / long_cov["frame_count"], 9),
                }
                row.update({f"20s_{key}": value for key, value in short_cov.items()})
                row.update({f"60s_{key}": value for key, value in long_cov.items()})
                rows.append(row)
                endpoint += int(STEP_S * 1000)
                index += 1
            block_audits.append(
                {
                    "subject": subject,
                    "block_id": block["block_id"],
                    "status": block["status"],
                    "pair_grid_n": sum(row["subject"] == subject and row["block_id"] == block["block_id"] for row in rows),
                    "block_start_unix_ms": block_start,
                    "block_end_unix_ms": block_end,
                    "guarded_start_unix_ms": guarded_start,
                    "guarded_end_unix_ms": guarded_end,
                    "local_interval_median_ms": median_ms,
                    "marker_sequence_exact": audit.get("marker_sequence_exact"),
                    "ecg_fit_residual_p95_ms": audit.get("ecg_fit_residual_p95_ms"),
                }
            )
    rows.sort(key=lambda row: (SUBJECTS.index(row["subject"]), row["block_id"], row["endpoint_unix_ms"]))
    return rows, block_audits


def build_report(rows: list[dict], metrics: list[dict], pair: dict, block_audits: list[dict], run: dict, ecg24: dict) -> str:
    by_window = {int(item["window_s"]): item for item in metrics}
    lines = [
        "# Issue #25 — controlled 20 s versus historical 60 s HR comparison",
        "",
        "状态：`PARTIAL / DIAGNOSTIC_ONLY`; formal window validity remains `UNRESOLVED`",
        "",
        "本报告只解决窗口来源与 formal validity 证据，不把短窗或长窗结果升级为 validated physiology。窗口长度在读取结果前预先固定为 20 s 与 trailing 60 s；没有按 MAE、相关或 coverage 选择长度。",
        "",
        "## 1. Direct conclusion",
        "",
        "- 20 s 首次进入当前证据链的来源是 commit `472735b6b6af5f98e92ab7815718e81863cb6098` 的 `scripts/maintenance/run_mmwave_targeted_validation_20260830.py`；目的为 block-local target continuity / ECG-aligned bounded diagnostic，非 HR formal window validation。",
        "- 历史 60 s 的真实 semantics 来自 `64634159d226ee1ed892d53e56fcf3697fbff9b8` 上的 `scripts/maintenance/run_hr_course_99_corrected.py` 与 `scripts/maintenance/build_hr_course_99_audit.py`：先以首 6000 frames 固定 target，再用 v3.1.1 的 HR course（25 s internal window、5 s step）对每个 60 s probe window 的 course points 做 `(t > onset-60) & (t <= onset)` median。",
        "- 当前受控比较使用同一 historical fixed target、同一 v3.1.1 bandpass/periodogram/peak/course chain、同一 block marker affine ECG alignment 和 DLL timestamp column 3；只改变 trailing window length。",
        "- 结论等级为 `UNRESOLVED`：本轮可提供 3 个 targeted sessions / complete blocks 的 diagnostic window-length evidence，但不足以把 20 s 或 60 s 宣称为 formal HR validity window。",
        "",
        "## 2. Pre-registered comparison contract",
        "",
        "- Pair endpoints start at `block_start + 5 s + 60 s`, then advance by 10 s until `block_end - 5 s`; each endpoint has `[end-20 s, end]` and `[end-60 s, end]`. Thus both windows remain inside the same complete block and the same 5 s boundary guard.",
        "- Target is fixed before window comparison from the historical corrected-gate selection artifact; no per-window target selection, no parameter sweep and no result-based length choice.",
        f"- ECG_VALID is the #24 eligibility adapter, not the old targeted-validation status field: 0.5–40 Hz third-order SOS, fixed 0.30 s R-peak distance and prominence 0.25, 300–2000 ms IBI, adjacent-IBI change >20% rejection, valid-beat coverage ≥80%, and ≥3 valid IBI. The #24 aggregate is {ecg24['counts'].get('ECG_VALID')} valid / {ecg24['counts'].get('ECG_INVALID')} invalid / {ecg24['counts'].get('UNRESOLVED')} unresolved out of {ecg24['counts'].get('input_window_n')}.",
        "- A pair enters metric calculations only when both the 20 s and trailing 60 s references independently pass that same ECG_VALID rule. Marker mismatch is retained as a warning when block-local affine mapping is available; it is not an independent ECG_INVALID cause.",
        "- `coverage_fraction` is timestamp-only frame coverage using the block-local DLL interval median; `signal_usable_ratio` is the existing v3.1.1 internal 10 s signal gate ratio. Neither was used to choose the preferred length.",
        "",
        "## 3. Frequency resolution, coverage and metrics",
        "",
        "| window | pair-grid n | ECG_VALID pair n | estimator valid n | metric n | mean coverage | median coverage | frequency resolution | MAE | median AE | bias (est−ECG) | Pearson r | Spearman r |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for window in (20, 60):
        item = by_window[window]
        lines.append(
            f"| {window} s | {item['pair_grid_n']} | {item['ecg_valid_pair_n']} | {item['estimator_valid_n']} | {item['metric_n']} | {item['coverage_mean']} | {item['coverage_median']} | {item['frequency_resolution_hz']} Hz / {item['frequency_resolution_bpm']} bpm | {item['mae_bpm']} | {item['median_ae_bpm']} | {item['bias_estimator_minus_ecg_bpm']} | {item['pearson_r']} | {item['spearman_r']} |"
        )
    lines += [
        "",
        f"Exact paired error contrast (20 s AE − 60 s AE): common n={pair['common_n']}, mean={pair['mean_ae_delta_20s_minus_60s_bpm']}, median={pair['median_ae_delta_20s_minus_60s_bpm']}, 20 s better={pair['20s_better_n']}, ties={pair['tie_n']}, 60 s better={pair['60s_better_n']}. This is descriptive and not a formal superiority test.",
        "",
        "The nominal periodogram bin spacing is `FS/N`: 20 s = 0.05 Hz = 3 bpm and 60 s = 0.016666667 Hz = 1 bpm. Per-window values are retained because DLL-time coverage can make observed N differ from nominal duration.",
        "",
        "## 4. Historical dependency chain",
        "",
        "- Filter: existing v3.1.1 4th-order SOS cardiac bandpass, 0.8–2.0 Hz (48–120 bpm).",
        "- PSD/spectral estimate: existing Hann-window periodogram with no new zero-padding or interpolation contract.",
        "- Peak estimate: existing adaptive-prominence `detect_peaks_heart_lo`, minimum distance and IBI validity rules; then existing segment correction, consensus and `estimate_hr_time_course` fusion.",
        "- Producer constraint: stored input is the existing 8-channel complex range-domain NPZ; no raw ADC/range FFT, firmware, channel calibration, target algorithm or producer code was changed.",
        "- Historical corrected target constraint: 0.037 m/bin, physical gate 0.30–1.50 m (bins 9–40), first-6000-frame selection then forced target for the full comparison. The current comparison reuses the target, but does not claim that current selection was independently rerun with that gate.",
        "",
        "## 5. Validity boundary and reuse rejection",
        "",
        "- Reused: `run_mmwave_estimator_same_window_audit_20260830.py`, its `historical_20s_adaptation` helper, `run_mmwave_targeted_validation_20260830.py` `PartReader`/DLL-time block mapping, `gold_standard_qa.py::ecg_qa` as the #24 adapter implementation, historical selection artifacts and #24 aggregate eligibility evidence.",
        f"- #24 dependency source: `{ecg24['source']}`; root `{ecg24.get('root')}`; issue24 run `{ecg24.get('lineage', {}).get('issue24_run_id')}`; issue24 HEAD `{ecg24.get('lineage', {}).get('issue24_git_head')}`. The current run independently reapplies the adapter to both durations; it does not substitute `ecg_status == valid`.",
        "- `REUSE_REJECTION_REASON`: the existing same-window audit only has the frozen 335-row 20 s denominator and deliberately marks strict historical 60 s as `NOT_APPLICABLE_TO_20S`; it does not construct 60 s DLL-time windows or compute the paired 60 s ECG_VALID reference. A minimal new execution wrapper was therefore required.",
        "- The result remains diagnostic/UNRESOLVED because the targeted set is not the full formal cohort, `97795` retains the documented `.acq` filename provenance limitation, and DLL-time frame coverage/timestamp provenance remains a validity limitation. No formal promotion is made.",
        "",
        "## 6. Execution and artifacts",
        "",
        f"- RUN_ID: `{RUN_ID}`",
        f"- Canonical HEAD at execution: `{run['canonical_head']}`; origin/main: `{run['origin_main']}`",
        f"- Input raw roots: `{DATA_ROOT}`; selected subjects: `{', '.join(SUBJECTS)}`; source rows: {len(rows)} paired endpoints.",
        "- Script output: `MMWAVE_WINDOW_LENGTH_COMPARISON.csv`, `MMWAVE_WINDOW_LENGTH_METRICS.csv`, `MMWAVE_WINDOW_LENGTH_BLOCK_AUDIT.csv`, `MMWAVE_WINDOW_LENGTH_COMPARISON_REPORT_2026-08-30.md`, `MMWAVE_WINDOW_LENGTH_COMPARISON_MANIFEST.json`.",
        "- Excluded: C2B/C2C, Issue #16, HRV, NIR/RGB, firmware, portable V2, raw mutation, producer modification and full formal batch.",
        "",
        "## 7. Block audit",
        "",
        "| subject | block | pair-grid n | marker sequence exact | ECG fit p95 ms | DLL median interval ms |",
        "|---|---|---:|---|---:|---:|",
    ]
    for item in block_audits:
        lines.append(
            f"| {item['subject']} | {item['block_id']} | {item['pair_grid_n']} | {item['marker_sequence_exact']} | {item['ecg_fit_residual_p95_ms']} | {item['local_interval_median_ms']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.path.insert(0, str(ALGO_ROOT / "scripts"))
    algo = load_module(ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py", "v311_issue25")
    gold = load_module(ALGO_ROOT / "scripts" / "gold_standard_qa.py", "gold_issue25")
    same = load_module(
        ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_estimator_same_window_audit_20260830.py",
        "same_window_issue25",
    )
    rerun = same.load_rerun_module()
    ecg24 = load_ecg24_evidence()
    rows, block_audits = build_pair_rows(rerun, same, algo, gold)
    metrics = [
        metric_rows(rows, "hr_20s_bpm", "20s_coverage_fraction", "hr_20s_signal_usable_ratio", SHORT_WINDOW_S),
        metric_rows(rows, "hr_60s_bpm", "60s_coverage_fraction", "hr_60s_signal_usable_ratio", HISTORICAL_WINDOW_S),
    ]
    pair = pairwise(rows)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    output_names = [
        "MMWAVE_WINDOW_LENGTH_COMPARISON.csv",
        "MMWAVE_WINDOW_LENGTH_METRICS.csv",
        "MMWAVE_WINDOW_LENGTH_BLOCK_AUDIT.csv",
        "MMWAVE_WINDOW_LENGTH_COMPARISON_REPORT_2026-08-30.md",
    ]
    write_csv(RESULT_ROOT / output_names[0], rows)
    write_csv(RESULT_ROOT / output_names[1], metrics)
    write_csv(RESULT_ROOT / output_names[2], block_audits)
    run = {
        "run_id": RUN_ID,
        "canonical_head": git(ALGO_ROOT, "rev-parse", "HEAD"),
        "canonical_main_head": git(ALGO_ROOT, "rev-parse", "HEAD"),
        "origin_main": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"),
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "producer_script": str(ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"),
        "producer_script_sha256": sha256(ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"),
        "fixed_20s_input": str(FIXED_20S_INPUT),
        "fixed_20s_input_sha256": sha256(FIXED_20S_INPUT),
        "historical_selection_root": str(HISTORICAL_SELECTION_ROOT),
        "subjects": list(SUBJECTS),
        "parameters": {
            "short_window_s": SHORT_WINDOW_S,
            "historical_window_s": HISTORICAL_WINDOW_S,
            "step_s": STEP_S,
            "boundary_guard_s": BOUNDARY_GUARD_S,
            "fs_hz": FS_HZ,
            "target_source": "historical corrected-gate _selection_60s artifact; fixed per subject",
            "mmwave_time_column": "DLL Unix ms in timestamp CSV column 3 / zero-based index 2",
            "ecg_valid_rule": ECG_VALID_RULE,
            "periodogram_resolution_formula": "FS/N; N is observed DLL-time frame count",
        },
        "reuse": {
            "reused_files": [
                "scripts/maintenance/run_mmwave_estimator_same_window_audit_20260830.py",
                "scripts/maintenance/run_mmwave_targeted_validation_20260830.py",
                "scripts/process_vital_signs_v3_1_1.py",
                "scripts/gold_standard_qa.py::ecg_qa (same implementation used by #24)",
                "scripts/maintenance/audit_historical_ecg_reference_chain_20260830.py",
                "output/20_生理金标准验证/06_HR_COURSE_99_CORRECTED_GATE/*/_selection_60s/*.json",
            ],
            "reuse_rejection_reason": "Existing same-window audit is 20 s-only and marks strict historical 60 s NOT_APPLICABLE_TO_20S; it lacks paired 60 s DLL-time windows and paired ECG_VALID references.",
        },
        "ecg24_dependency": ecg24,
        "ecg_eligibility": {
            "source": ecg24["source"],
            "full_input_n": ecg24["counts"].get("input_window_n"),
            "full_ECG_VALID_n": ecg24["counts"].get("ECG_VALID"),
            "full_ECG_INVALID_n": ecg24["counts"].get("ECG_INVALID"),
            "full_UNRESOLVED_n": ecg24["counts"].get("UNRESOLVED"),
            "paired_ECG_VALID_n": pair["common_n"],
            "pair_rule": ECG_VALID_RULE,
        },
        "counts": {"paired_rows": len(rows), "blocks": len(block_audits), "pairwise": pair},
        "metrics": metrics,
        "status": "PARTIAL / DIAGNOSTIC_ONLY",
        "conclusion": "diagnostic_window_length_comparison_formal_validity_unresolved",
        "verification": {
            "python_compile": "PASS (before execution)",
            "run_exit_code": 0,
            "fixed_grid_pair_rows": len(rows),
            "both_window_ECG_VALID_pairs": pair["common_n"],
            "empty_metric_guard": all(item["metric_n"] > 0 for item in metrics),
        },
        "reuse_rejection_reason": "Existing same-window audit is 20 s-only and marks strict historical 60 s NOT_APPLICABLE_TO_20S; it lacks paired 60 s DLL-time windows and paired ECG_VALID references.",
        "excluded": ["C2B", "C2C", "Issue #16", "HRV", "NIR", "RGB", "firmware", "portable V2", "producer modification", "raw mutation", "full formal batch"],
    }
    report_path = RESULT_ROOT / output_names[3]
    report_path.write_text(build_report(rows, metrics, pair, block_audits, run, ecg24), encoding="utf-8")
    run["outputs"] = [{"path": name, "sha256": sha256(RESULT_ROOT / name)} for name in output_names]
    manifest_path = RESULT_ROOT / "MMWAVE_WINDOW_LENGTH_COMPARISON_MANIFEST.json"
    manifest_path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "status": run["status"], "counts": run["counts"], "metrics": metrics}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
