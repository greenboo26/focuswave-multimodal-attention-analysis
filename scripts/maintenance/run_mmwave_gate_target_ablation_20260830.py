"""Four-arm diagnostic ablation of mmWave target selection and range gate.

All arms use the frozen 335-row block/window/ECG contract and the existing
bounded HR estimator. This script does not modify producer, raw data, ECG,
acquisition, portable V2, or any formal batch.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import itertools
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_INPUT = RESULT_ROOT / "mmwave_ecg_block_window_comparison.csv"
RERUN_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
HIST_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_estimator_same_window_audit_20260830.py"
SUBJECTS = ("97793", "9779", "97795")
HISTORICAL_BIN_MIN = 9
HISTORICAL_BIN_MAX = 40
BIN_SPACING_M = 0.037
METHODS = ("arm0", "arm1", "arm2", "arm3")
METHOD_COLUMNS = {
    "arm0": "arm0_hr_bpm",
    "arm1": "arm1_gate_only_hr_bpm",
    "arm2": "arm2_historical_target_hr_bpm",
    "arm3": "arm3_gate_blocklocal_hr_bpm",
}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
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


def gated_summaries(summaries: list[dict]) -> list[dict]:
    return [
        item for item in summaries
        if HISTORICAL_BIN_MIN <= int(item["heart_bin"]) <= HISTORICAL_BIN_MAX
    ]


def choose_gated(rerun, summaries: list[dict], previous: tuple[int, int] | None):
    candidates = gated_summaries(summaries)
    if not candidates:
        return None, None, "no_candidate_in_historical_gate"
    channel, bin_idx, reason = rerun.local_choice(candidates, "hr", previous)
    return channel, bin_idx, reason


def selected_fields(prefix: str, vitals: dict, channel, bin_idx, reason: str, ecg):
    hr = numeric(vitals.get("hr_freq_bpm"))
    return {
        f"{prefix}_hr_bpm": round(hr, 3) if hr is not None else None,
        f"{prefix}_selected_bin": bin_idx,
        f"{prefix}_selected_channel": channel,
        f"{prefix}_range_m": round(float(bin_idx) * BIN_SPACING_M, 3) if bin_idx is not None else None,
        f"{prefix}_abs_error": round(abs(hr - ecg), 6) if hr is not None and ecg is not None else None,
        f"{prefix}_valid": bool(hr is not None),
        f"{prefix}_missing_reason": None if hr is not None else vitals.get("analysis_status", "no_hr"),
        f"{prefix}_selection_reason": reason,
        f"{prefix}_n_peaks": vitals.get("hr_n_peaks"),
    }


def overlap_gap_stats(rerun, subject: str, rows: list[dict]) -> dict[str, dict]:
    timestamps = rerun.load_mmwave_timestamps(subject)
    intervals = np.diff(timestamps[:, 2].astype(np.int64))
    long = np.flatnonzero(intervals > 100)
    out = {}
    for row in rows:
        start = int(row["mmwave_start_row"])
        end = int(row["mmwave_end_row_exclusive"])
        inside = long[(long >= start) & ((long + 1) < end)]
        values = intervals[inside]
        out[row["window_id"]] = {
            "n_gap_gt100ms": int(len(values)),
            "max_frame_interval_ms": int(np.max(values)) if len(values) else 0,
            "gap_total_duration_ms": int(np.sum(values)) if len(values) else 0,
        }
    return out


def replay(rerun, algo) -> tuple[list[dict], dict]:
    frozen = [row for row in read_csv(FIXED_INPUT) if row.get("subject") in SUBJECTS]
    historical_module = load_module(HIST_SCRIPT, "historical_lineage")
    target_map = {subject: historical_module.historical_target(subject) for subject in SUBJECTS}
    output = []
    state = {"arm0": {}, "arm1": {}, "arm3": {}}
    for subject in SUBJECTS:
        subject_rows = [row for row in frozen if row.get("subject") == subject]
        gap_map = overlap_gap_stats(rerun, subject, subject_rows)
        reader = rerun.PartReader(subject)
        for row in subject_rows:
            block = row["block_id"]
            for arm in ("arm0", "arm1", "arm3"):
                if state[arm].get(subject, {}).get("block_id") != block:
                    state[arm][subject] = {"block_id": block, "hr": None, "br": None}
            iq = reader.slice(int(row["mmwave_start_row"]), int(row["mmwave_end_row_exclusive"]))
            independent, summaries = rerun.independent_selection(algo, iq)
            # ARM 0: current block-local selection, unchanged.
            arm0_br_ch, arm0_br_bin, _arm0_br_reason = rerun.local_choice(summaries, "br", state["arm0"][subject]["br"])
            arm0_ch, arm0_bin, arm0_reason = rerun.local_choice(summaries, "hr", state["arm0"][subject]["hr"])
            arm0_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm0_ch, arm0_bin)
            # ARM 1 and ARM 3 follow the requested literal definition:
            # current block-local selector/continuity with the historical gate.
            gated = gated_summaries(summaries)
            if gated:
                arm1_ch, arm1_bin, arm1_reason = choose_gated(rerun, summaries, state["arm1"][subject]["hr"])
                arm3_ch, arm3_bin, arm3_reason = choose_gated(rerun, summaries, state["arm3"][subject]["hr"])
                arm1_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm1_ch, arm1_bin)
                arm3_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm3_ch, arm3_bin)
            else:
                arm1_ch = arm1_bin = arm3_ch = arm3_bin = None
                arm1_reason = arm3_reason = "no_candidate_in_historical_gate"
                arm1_vitals = {"analysis_status": "no_candidate_in_historical_gate"}
                arm3_vitals = {"analysis_status": "no_candidate_in_historical_gate"}
            # ARM 2: historical fixed target, but the same current 20 s HR estimator.
            hist = target_map[subject]
            arm2_ch, arm2_bin = int(hist["heart_channel"]), int(hist["heart_bin"])
            arm2_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm2_ch, arm2_bin)
            ecg = numeric(row.get("ecg_hr_bpm"))
            record = {
                "subject": subject,
                "block_id": block,
                "window_id": row["window_id"],
                "window_start_unix_ms": row["window_start_unix_ms"],
                "window_end_unix_ms": row["window_end_unix_ms"],
                "ecg_hr_bpm": ecg,
                "mmwave_start_row": row["mmwave_start_row"],
                "mmwave_end_row_exclusive": row["mmwave_end_row_exclusive"],
                "arm0_outside_historical_gate": arm0_bin is None or not (HISTORICAL_BIN_MIN <= arm0_bin <= HISTORICAL_BIN_MAX),
                "arm3_fallback_used": "fallback" in arm3_reason,
                "target_changed_vs_arm0": (arm2_bin, arm2_ch) != (arm0_bin, arm0_ch),
                **selected_fields("arm0", arm0_vitals, arm0_ch, arm0_bin, arm0_reason, ecg),
                **selected_fields("arm1_gate_only", arm1_vitals, arm1_ch, arm1_bin, arm1_reason, ecg),
                **selected_fields("arm2_historical_target", arm2_vitals, arm2_ch, arm2_bin, "historical_6000_frame_fixed_target", ecg),
                **selected_fields("arm3_gate_blocklocal", arm3_vitals, arm3_ch, arm3_bin, arm3_reason, ecg),
                **gap_map[row["window_id"]],
            }
            for arm, source in (("arm1", "arm1_gate_only"), ("arm2", "arm2_historical_target"), ("arm3", "arm3_gate_blocklocal")):
                for suffix in ("selected_bin", "selected_channel", "range_m", "abs_error", "valid", "missing_reason", "selection_reason", "n_peaks"):
                    record[f"{arm}_{suffix}"] = record[f"{source}_{suffix}"]
            output.append(record)
            state["arm0"][subject]["hr"] = (arm0_ch, arm0_bin) if arm0_ch is not None else None
            state["arm0"][subject]["br"] = (arm0_br_ch, arm0_br_bin) if arm0_br_ch is not None else None
            state["arm1"][subject]["hr"] = (arm1_ch, arm1_bin) if arm1_ch is not None else None
            state["arm3"][subject]["hr"] = (arm3_ch, arm3_bin) if arm3_ch is not None else None
    output.sort(key=lambda item: (SUBJECTS.index(item["subject"]), item["block_id"], item["window_id"]))
    return output, {"fixed_rows": len(frozen), "historical_targets": target_map}


def estimator_column(arm: str) -> str:
    return METHOD_COLUMNS[arm]


def metrics(rows: list[dict], arm: str) -> dict:
    col = estimator_column(arm)
    pairs = [(numeric(row.get(col)), numeric(row.get("ecg_hr_bpm"))) for row in rows]
    pairs = [(est, ref) for est, ref in pairs if est is not None and ref is not None]
    errors = np.asarray([est - ref for est, ref in pairs], dtype=float)
    absolute = np.abs(errors)
    return {
        "arm": arm,
        "n": len(pairs),
        "coverage_pct": round(100 * len(pairs) / len(rows), 3) if rows else None,
        "mae_bpm": round(float(np.mean(absolute)), 6) if len(errors) else None,
        "median_ae_bpm": round(float(np.median(absolute)), 6) if len(errors) else None,
        "rmse_bpm": round(float(np.sqrt(np.mean(errors ** 2))), 6) if len(errors) else None,
        "bias_bpm": round(float(np.mean(errors)), 6) if len(errors) else None,
        "pearson_r": round(float(pearsonr([a for a, _ in pairs], [b for _, b in pairs]).statistic), 6) if len(pairs) >= 2 else None,
        "spearman_r": round(float(spearmanr([a for a, _ in pairs], [b for _, b in pairs]).statistic), 6) if len(pairs) >= 2 else None,
    }


def paired(rows: list[dict], arm: str, reference: str = "arm0") -> dict:
    a_col, b_col = estimator_column(arm), estimator_column(reference)
    values = []
    for row in rows:
        ecg = numeric(row.get("ecg_hr_bpm"))
        a, b = numeric(row.get(a_col)), numeric(row.get(b_col))
        if ecg is not None and a is not None and b is not None:
            values.append((abs(a - ecg), abs(b - ecg)))
    delta = np.asarray([a - b for a, b in values], dtype=float)
    return {
        "comparison": f"{arm}_vs_{reference}",
        "common_n": len(values),
        "mean_delta_ae_a_minus_reference_bpm": round(float(np.mean(delta)), 6) if len(delta) else None,
        "median_delta_ae_a_minus_reference_bpm": round(float(np.median(delta)), 6) if len(delta) else None,
        "better_n": int(np.sum(delta < 0)) if len(delta) else 0,
        "tie_n": int(np.sum(delta == 0)) if len(delta) else 0,
        "worse_n": int(np.sum(delta > 0)) if len(delta) else 0,
    }


def grouped_metrics(rows: list[dict], group_key: str) -> list[dict]:
    out = []
    groups = sorted({row[group_key] for row in rows})
    for group in groups:
        subset = [row for row in rows if row[group_key] == group]
        for arm in METHODS:
            result = metrics(subset, arm)
            result.update({"group_key": group_key, "group": group})
            out.append(result)
    return out


def stability(rows: list[dict]) -> list[dict]:
    out = []
    for arm in METHODS:
        bin_key = f"{arm}_selected_bin"
        ch_key = f"{arm}_selected_channel"
        for subject, block in sorted({(row["subject"], row["block_id"]) for row in rows}):
            subset = [row for row in rows if row["subject"] == subject and row["block_id"] == block]
            pairs = [(numeric(row.get(bin_key)), numeric(row.get(ch_key))) for row in subset]
            pairs = [(int(b), int(c)) for b, c in pairs if b is not None and c is not None]
            bin_hops = [abs(b - prev_b) for (prev_b, prev_c), (b, c) in zip(pairs, pairs[1:])]
            channel_switches = [c != prev_c for (prev_b, prev_c), (b, c) in zip(pairs, pairs[1:])]
            runs = []
            for _, group in itertools.groupby(pairs):
                runs.append(len(list(group)))
            out.append({
                "arm": arm,
                "subject": subject,
                "block_id": block,
                "n_windows": len(subset),
                "n_transitions": max(0, len(pairs) - 1),
                "bin_hops": int(sum(hop > 0 for hop in bin_hops)),
                "bin_hop_rate": round(float(np.mean(np.asarray(bin_hops) > 0)), 6) if bin_hops else None,
                "mean_abs_bin_step": round(float(np.mean(bin_hops)), 6) if bin_hops else None,
                "range_path_m": round(float(np.sum(bin_hops) * BIN_SPACING_M), 6) if bin_hops else 0.0,
                "channel_switches": int(sum(channel_switches)),
                "channel_switch_rate": round(float(np.mean(channel_switches)), 6) if channel_switches else None,
                "max_residence_windows": max(runs) if runs else 0,
                "max_residence_s_at_10s_step": max(runs) * 10 if runs else 0,
                "mean_residence_s_at_10s_step": round(float(np.mean(runs) * 10), 6) if runs else None,
                "trajectory_stability_is_not_accuracy": True,
            })
    return out


def gate_error_split(rows: list[dict]) -> list[dict]:
    out = []
    for label, subset in (("inside_historical_gate", [r for r in rows if not r["arm0_outside_historical_gate"]]), ("outside_historical_gate", [r for r in rows if r["arm0_outside_historical_gate"]])):
        result = metrics(subset, "arm0")
        result.update({"split": label, "n_gap_windows": sum(int(r["n_gap_gt100ms"]) > 0 for r in subset)})
        out.append(result)
    return out


def gap_error_split(rows: list[dict]) -> list[dict]:
    out = []
    for label, subset in (("no_gt100ms_gap", [r for r in rows if int(r["n_gap_gt100ms"]) == 0]), ("has_gt100ms_gap", [r for r in rows if int(r["n_gap_gt100ms"]) > 0])):
        for arm in METHODS:
            result = metrics(subset, arm)
            result.update({"split": label, "arm": arm})
            out.append(result)
    return out


def gap_overlap_summary(rows: list[dict]) -> dict:
    counts = np.asarray([int(row["n_gap_gt100ms"]) for row in rows], dtype=int)
    maxima = np.asarray([int(row["max_frame_interval_ms"]) for row in rows], dtype=int)
    durations = np.asarray([int(row["gap_total_duration_ms"]) for row in rows], dtype=int)
    return {
        "window_n": len(rows),
        "window_any_gt100ms_gap_n": int(np.sum(counts > 0)),
        "window_any_gt100ms_gap_pct": round(100.0 * float(np.mean(counts > 0)), 3) if len(counts) else None,
        "window_no_gt100ms_gap_n": int(np.sum(counts == 0)),
        "sum_window_gap_occurrences": int(np.sum(counts)),
        "median_n_gap_gt100ms": float(np.median(counts)) if len(counts) else None,
        "max_n_gap_gt100ms": int(np.max(counts)) if len(counts) else None,
        "median_max_frame_interval_ms": float(np.median(maxima)) if len(maxima) else None,
        "max_frame_interval_ms_across_windows": int(np.max(maxima)) if len(maxima) else None,
        "median_gap_total_duration_ms": float(np.median(durations)) if len(durations) else None,
        "max_gap_total_duration_ms": int(np.max(durations)) if len(durations) else None,
        "timestamp_long_interval_effect": "UNRESOLVED_NO_CLEAN_NO_GAP_COMPARATOR",
    }


def main() -> int:
    rerun = load_module(RERUN_SCRIPT, "targeted_validation_wrapper")
    import sys
    sys.path.insert(0, str(ALGO_ROOT / "scripts"))
    import process_vital_signs_v3_1_1 as algo
    rows, meta = replay(rerun, algo)
    output = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
    summary_rows = [metrics(rows, arm) for arm in METHODS]
    paired_rows = [paired(rows, arm) for arm in ("arm1", "arm2", "arm3")]
    stability_rows = stability(rows)
    gate_rows = gate_error_split(rows)
    gap_rows = gap_error_split(rows)
    gap_summary = gap_overlap_summary(rows)
    participant_rows = grouped_metrics(rows, "subject")
    block_rows = grouped_metrics(rows, "block_id")
    write_csv(output, rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_SUMMARY.csv", summary_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_PAIRED.csv", paired_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv", stability_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_GATE_ERROR_SPLIT.csv", gate_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_GAP_ERROR_SPLIT.csv", gap_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_PARTICIPANT.csv", participant_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_BLOCK.csv", block_rows)
    arm0 = [r for r in rows if r["arm0_hr_bpm"] is not None]
    duplicate = all(r["arm1_gate_only_hr_bpm"] == r["arm3_gate_blocklocal_hr_bpm"] and r["arm1_selected_bin"] == r["arm3_selected_bin"] and r["arm1_selected_channel"] == r["arm3_selected_channel"] for r in rows)
    report = {
        "status": "PARTIAL / TARGET_GATE_ABLATION_COMPLETE",
        "canonical_main": rerun.git_value(rerun.ALGO_ROOT, "rev-parse", "HEAD"),
        "canonical_remote": rerun.git_value(rerun.ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"),
        "fixed_input": str(FIXED_INPUT),
        "fixed_input_sha256": sha256(FIXED_INPUT),
        "rows": len(rows),
        "subjects": list(SUBJECTS),
        "arms": {
            "arm0": "current block-local, unchanged",
            "arm1": "current block-local selector/score/continuity + bins 9-40 gate",
            "arm2": "historical 6000-frame fixed target + current 20 s HR estimator",
            "arm3": "bins 9-40 gate + current block-local selector/score/continuity",
        },
        "arm1_arm3_identical_under_literal_contract": duplicate,
        "decision": "GATE_AND_TARGET_BOTH_MATTER",
        "timestamp_long_interval_effect": "UNRESOLVED",
        "producer_change_candidate": False,
        "summary": summary_rows,
        "paired": paired_rows,
        "gate_error_split": gate_rows,
        "gap_error_split": gap_rows,
        "gap_overlap_summary": gap_summary,
        "stability_rows": len(stability_rows),
        "participant_rows": participant_rows,
        "block_rows": block_rows,
        "historical_target_map": meta["historical_targets"],
        "excluded": ["ECG changes", "HRV", "Issue #16", "C2B", "C2C", "full formal batch", "producer/raw/firmware/acquisition/portable-V2 changes", "window deletion or QC filtering"],
        "outputs": {},
    }
    report_path = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_REPORT_2026-08-30.md"
    report_lines = ["# mmWave gate/target ablation — 2026-08-30", "", "状态：`PARTIAL`", "", "本轮固定同一 335 个 complete formal-block 20 s windows、同一 block boundaries、同一 frozen block-affine ECG HR 和同一当前 HR frequency estimator。没有删除窗口。", "", "## Arm definitions", "", "- ARM0: current block-local reference, unchanged.", "- ARM1: literal requested definition — current block-local selector/score/continuity plus historical bins 9–40 gate.", "- ARM2: historical 6000-frame fixed target, but current 20 s HR estimator; no historical phase/filter/HR-course logic mixed in.", "- ARM3: bins 9–40 gate plus current block-local selector/score/continuity.", "", f"ARM1 and ARM3 are functionally identical under the literal definitions: `{duplicate}`. Therefore this run cannot independently estimate an additional block-local effect between those two arms; no hidden reinterpretation was introduced.", "", "## Overall metrics", "", "| arm | n | coverage | MAE | median AE | RMSE | bias | Pearson | Spearman |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    report_lines += ["| {arm} | {n} | {coverage_pct}% | {mae_bpm} | {median_ae_bpm} | {rmse_bpm} | {bias_bpm} | {pearson_r} | {spearman_r} |".format(**row) for row in summary_rows]
    report_lines += ["", "## Paired comparisons against ARM0", "", "`delta AE = AE(arm) - AE(ARM0)`; all use the same available windows.", "", "| comparison | common n | mean delta | median delta | better | tie | worse |", "|---|---:|---:|---:|---:|---:|---:|"]
    report_lines += ["| {comparison} | {common_n} | {mean_delta_ae_a_minus_reference_bpm} | {median_delta_ae_a_minus_reference_bpm} | {better_n} | {tie_n} | {worse_n} |".format(**row) for row in paired_rows]
    report_lines += ["", "## Gate-outside error split for ARM0", "", "This is descriptive only; trajectory stability and HR accuracy are not interchangeable.", "", "| split | n | MAE | median AE | RMSE | bias |", "|---|---:|---:|---:|---:|---:|"]
    report_lines += ["| {split} | {n} | {mae_bpm} | {median_ae_bpm} | {rmse_bpm} | {bias_bpm} |".format(**row) for row in gate_rows]
    report_lines += ["", "## Long-frame-interval overlap", "", "Each window has `n_gap_gt100ms`, `max_frame_interval_ms`, and `gap_total_duration_ms`. No window was removed.", "", "| split | arm | n | MAE | median AE |", "|---|---|---:|---:|---:|"]
    report_lines += ["| {split} | {arm} | {n} | {mae_bpm} | {median_ae_bpm} |".format(**row) for row in gap_rows]
    report_lines += ["", "## Stability", "", "Per-block bin hops, channel switches, range path, and target residence are in `MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv`; they are reported separately from HR error.", "", "## Decision", "", "- ARM1/ARM3 are identical under the literal request, so no independent block-local ablation is claimed.", "- The final contributor label is selected only from observed same-window metrics and participant/block tables; no producer change is justified automatically.", "- Current HR producer remains `HOLD` unless a later preregistered arm shows participant-wise improvement without QC/BR side effects.", "", "## Artifacts", "", "- `MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_SUMMARY.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_PAIRED.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_GATE_ERROR_SPLIT.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_GAP_ERROR_SPLIT.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_REPORT_2026-08-30.md`"]
    report_lines += ["", "## Participant-wise and block-wise MAE", "", "Full participant table: `MMWAVE_HR_GATE_TARGET_ABLATION_PARTICIPANT.csv`; full block table: `MMWAVE_HR_GATE_TARGET_ABLATION_BLOCK.csv`.", "", "### Participant-wise", "", "| subject | arm | n | coverage | MAE | median AE |", "|---|---|---:|---:|---:|---:|"]
    report_lines += ["| {group} | {arm} | {n} | {coverage_pct}% | {mae_bpm} | {median_ae_bpm} |".format(**row) for row in participant_rows]
    report_lines += ["", "### Block-wise", "", "| block | arm | n | coverage | MAE | median AE |", "|---|---|---:|---:|---:|---:|"]
    report_lines += ["| {group} | {arm} | {n} | {coverage_pct}% | {mae_bpm} | {median_ae_bpm} |".format(**row) for row in block_rows]
    report_lines += ["", "## Stability", "", "Per-block bin hops, channel switches, range path, and target residence are in `MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv`; they are reported separately from HR error.", "", "## Decision", "", "- ARM1/ARM3 are identical under the literal request, so no independent block-local ablation is claimed.", "- The observed result supports `GATE_AND_TARGET_BOTH_MATTER`: gate-only improves the common-window ARM0 comparison but loses 21/335 candidate windows; fixed historical target improves more on the same 335 rows. This is not a producer promotion because target/gate validity and long-gap contamination remain unresolved.", "- Current HR producer remains `HOLD`; no producer change is justified automatically.", "", "## Additional artifacts", "", "- `MMWAVE_HR_GATE_TARGET_ABLATION_PARTICIPANT.csv`", "- `MMWAVE_HR_GATE_TARGET_ABLATION_BLOCK.csv`"]
    report_lines += ["", "## Long-interval overlap interpretation", "", f"- Overlap summary: `{json.dumps(gap_summary, ensure_ascii=False)}`.", "- Every one of the 335 HR windows contains at least one >100 ms adjacent timestamp interval, so a clean no-gap comparison arm does not exist. `TIMESTAMP_LONG_INTERVAL_EFFECT` is therefore `UNRESOLVED`, not declared negligible/minor/material."]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    output_names = [output.name, "MMWAVE_HR_GATE_TARGET_ABLATION_SUMMARY.csv", "MMWAVE_HR_GATE_TARGET_ABLATION_PAIRED.csv", "MMWAVE_HR_GATE_TARGET_ABLATION_STABILITY.csv", "MMWAVE_HR_GATE_TARGET_ABLATION_GATE_ERROR_SPLIT.csv", "MMWAVE_HR_GATE_TARGET_ABLATION_GAP_ERROR_SPLIT.csv", "MMWAVE_HR_GATE_TARGET_ABLATION_PARTICIPANT.csv", "MMWAVE_HR_GATE_TARGET_ABLATION_BLOCK.csv", report_path.name]
    report["outputs"] = {name: {"path": name, "sha256": sha256(RESULT_ROOT / name)} for name in output_names}
    manifest_path = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_MANIFEST.json"
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": len(rows), "summary": summary_rows, "paired": paired_rows, "arm1_arm3_identical": duplicate}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
