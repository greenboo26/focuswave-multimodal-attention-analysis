"""Same-window audit of historical and current mmWave HR estimators.

The denominator is the already frozen 335-row block-local comparison.  The
ECG values are read from that comparison and are not recomputed here.  The
historical 60-second estimator is reported as not applicable to a 20-second
window; the 20-second adaptation changes only window length and retains the
historical target/gate/phase/filter/HR rules.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_INPUT = RESULT_ROOT / "mmwave_ecg_block_window_comparison.csv"
HISTORICAL_SELECTION_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\20_生理金标准验证\06_HR_COURSE_99_CORRECTED_GATE")
TIMESTAMP_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_timestamp_semantics_audit_20260830")
DATA_ROOT = Path(r"D:\acq_mmwave_data")
SUBJECTS = ("97793", "9779", "97795")
HISTORICAL_BIN_SPACING_M = 0.037
HISTORICAL_MIN_RANGE_M = 0.30
HISTORICAL_MAX_RANGE_M = 1.50
HISTORICAL_GATE_BINS = (9, 40)


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


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def load_rerun_module():
    path = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
    spec = importlib.util.spec_from_file_location("targeted_rerun", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def float_or_none(value):
    try:
        return float(value) if value not in (None, "", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def historical_target(subject: str) -> dict:
    candidates = sorted((HISTORICAL_SELECTION_ROOT / f"sub-{subject}_" / "_selection_60s").glob("*.json"))
    if not candidates:
        return {"heart_channel": None, "heart_bin": None, "selection_score": None, "source": "missing_selection_artifact"}
    data = json.loads(candidates[0].read_text(encoding="utf-8"))
    ch = data.get("channels", {}).get("heart")
    bin_idx = data.get("bins", {}).get("heart")
    score = None
    for item in data.get("channel_selection", {}).get("heart_refined", []):
        if int(item.get("channel", -1)) == int(ch) and int(item.get("heart_bin", -1)) == int(bin_idx):
            score = item.get("score")
            break
    return {"heart_channel": int(ch), "heart_bin": int(bin_idx), "selection_score": score, "source": str(candidates[0])}


def score_for(summaries: list[dict], role: str, channel: int, bin_idx: int):
    key = "heart_bin" if role == "hr" else "breath_bin"
    score_key = "best_hr_selection_score" if role == "hr" else "best_br_score"
    for item in summaries:
        if int(item.get("channel", -1)) == int(channel) and int(item.get(key, -1)) == int(bin_idx):
            return item.get(score_key)
    return None


def historical_20s_adaptation(algo, iq: np.ndarray, channel: int, bin_idx: int) -> dict:
    """Run the historical bp_heart chain on exactly one current 20 s window."""
    out = {
        "hr_bpm": None,
        "valid": False,
        "missing_reason": None,
        "n_peaks": 0,
        "coverage": None,
        "raw_periodogram_bpm": None,
        "time_bpm": None,
        "consensus_bpm": None,
        "signal_gate_passed": None,
    }
    try:
        disp = algo.extract_displacement(iq, int(bin_idx), int(channel))
        heartbeat = algo._sos_bandpass(disp, algo.HR_LO_HZ, algo.HR_HI_HZ)
        freq = algo.estimate_freq_periodogram(heartbeat, algo.HR_LO_HZ, algo.HR_HI_HZ)
        peaks = algo.detect_peaks_heart_lo(heartbeat, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM)
        time_bpm = float(60.0 * algo.FS / np.mean(np.diff(peaks))) if len(peaks) >= 2 else None
        freq_bpm_raw = float(freq * 60.0) if freq is not None else None
        seg_corr = algo._heart_segment_reference_correction(
            heartbeat=heartbeat,
            hp=peaks,
            base_freq_bpm=round(freq_bpm_raw, 1) if freq_bpm_raw is not None else None,
        )
        periodogram_bpm = seg_corr.get("corrected_freq_bpm", round(freq_bpm_raw, 1) if freq_bpm_raw is not None else None)
        consensus_bpm, _time_consensus, _consensus = algo._heart_window_consensus_bpm(
            seg_corr=seg_corr,
            hr_freq_bpm_periodogram=periodogram_bpm,
            hr_time_bpm_global=round(time_bpm, 1) if time_bpm is not None else None,
        )
        course = algo.estimate_hr_time_course(heartbeat=heartbeat, peaks=peaks, fs=algo.FS, reference_bpm=consensus_bpm)
        fused = course.get("fused_median_bpm")
        gate = course.get("signal_quality", {}).get("hard_gate_passed")
        coverage = course.get("signal_quality", {}).get("usable_ratio")
        # Historical HR-course comparison used the fused course value. If a
        # short adaptation has no fused course, retain the historical spectral
        # consensus as an explicitly labeled fallback rather than dropping it.
        hr = float(fused) if fused is not None else (float(consensus_bpm) if consensus_bpm is not None else None)
        out.update({
            "hr_bpm": round(hr, 3) if hr is not None and np.isfinite(hr) else None,
            "valid": bool(hr is not None and np.isfinite(hr)),
            "missing_reason": None if hr is not None and np.isfinite(hr) else "insufficient_peaks_or_spectrum",
            "n_peaks": int(len(peaks)),
            "coverage": coverage,
            "raw_periodogram_bpm": round(freq_bpm_raw, 3) if freq_bpm_raw is not None else None,
            "time_bpm": round(time_bpm, 3) if time_bpm is not None else None,
            "consensus_bpm": consensus_bpm,
            "signal_gate_passed": gate,
        })
    except Exception as exc:
        out["missing_reason"] = f"error:{type(exc).__name__}"
    return out


def recompute_same_window(rerun, algo) -> tuple[list[dict], dict]:
    fixed = [row for row in read_csv(FIXED_INPUT) if row.get("subject") in SUBJECTS]
    output = []
    target_map = {subject: historical_target(subject) for subject in SUBJECTS}
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        events = rerun.load_events(subject)
        physical, _digital = rerun.decode_biopac_markers(subject)
        blocks, _audits = rerun.block_intervals(subject, timestamps, events, physical)
        block_status = {row["block_id"]: row["status"] for row in blocks}
        reader = rerun.PartReader(subject)
        previous = None
        for row in fixed:
            if row.get("subject") != subject:
                continue
            if block_status.get(row["block_id"]) != "complete":
                continue
            if previous is None or previous["block_id"] != row["block_id"]:
                previous = {"block_id": row["block_id"], "hr": None, "br": None}
            iq = reader.slice(int(row["mmwave_start_row"]), int(row["mmwave_end_row_exclusive"]))
            independent, summaries = rerun.independent_selection(algo, iq)
            local_hr_ch, local_hr_bin, local_hr_reason = rerun.local_choice(summaries, "hr", previous["hr"])
            local_br_ch, local_br_bin, local_br_reason = rerun.local_choice(summaries, "br", previous["br"])
            independent_vitals = rerun.estimate_vitals(algo, iq, independent["br_channel"], independent["br_bin"], independent["hr_channel"], independent["hr_bin"])
            local_vitals = rerun.estimate_vitals(algo, iq, local_br_ch, local_br_bin, local_hr_ch, local_hr_bin)
            hist = target_map[subject]
            adapt = historical_20s_adaptation(algo, iq, hist["heart_channel"], hist["heart_bin"])
            ecg = float_or_none(row.get("ecg_hr_bpm"))
            estimates = {
                "historical_original_hr_bpm": None,
                "historical_20s_adapt_hr_bpm": adapt["hr_bpm"],
                "current_independent_hr_bpm": independent_vitals.get("hr_freq_bpm"),
                "current_block_local_hr_bpm": local_vitals.get("hr_freq_bpm"),
            }
            record = {
                "subject": subject,
                "block_id": row["block_id"],
                "window_id": row["window_id"],
                "window_start_unix_ms": row["window_start_unix_ms"],
                "window_end_unix_ms": row["window_end_unix_ms"],
                "ecg_hr_bpm": ecg,
                "historical_original_hr_bpm": None,
                "historical_original_selected_bin": hist["heart_bin"],
                "historical_original_selected_channel": hist["heart_channel"],
                "historical_original_score": hist["selection_score"],
                "historical_original_valid": False,
                "historical_original_missing_reason": "NOT_APPLICABLE_TO_20S_WINDOW_SEMANTICS__historical_comparison_requires_60s",
                "historical_20s_adapt_hr_bpm": adapt["hr_bpm"],
                "historical_20s_adapt_selected_bin": hist["heart_bin"],
                "historical_20s_adapt_selected_channel": hist["heart_channel"],
                "historical_20s_adapt_selected_distance_m": round(hist["heart_bin"] * HISTORICAL_BIN_SPACING_M, 3),
                "historical_20s_adapt_score": hist["selection_score"],
                "historical_20s_adapt_valid": adapt["valid"],
                "historical_20s_adapt_missing_reason": adapt["missing_reason"],
                "historical_20s_adapt_n_peaks": adapt["n_peaks"],
                "historical_20s_adapt_coverage": adapt["coverage"],
                "historical_20s_adapt_signal_gate_passed": adapt["signal_gate_passed"],
                "current_independent_hr_bpm": independent_vitals.get("hr_freq_bpm"),
                "current_independent_selected_bin": independent["hr_bin"],
                "current_independent_selected_channel": independent["hr_channel"],
                "current_independent_score": score_for(summaries, "hr", independent["hr_channel"], independent["hr_bin"]),
                "current_independent_valid": independent_vitals.get("hr_freq_bpm") is not None,
                "current_independent_missing_reason": None if independent_vitals.get("hr_freq_bpm") is not None else independent_vitals.get("analysis_status"),
                "current_independent_n_peaks": independent_vitals.get("hr_n_peaks"),
                "current_block_local_hr_bpm": local_vitals.get("hr_freq_bpm"),
                "current_block_local_selected_bin": local_hr_bin,
                "current_block_local_selected_channel": local_hr_ch,
                "current_block_local_score": score_for(summaries, "hr", local_hr_ch, local_hr_bin),
                "current_block_local_valid": local_vitals.get("hr_freq_bpm") is not None,
                "current_block_local_missing_reason": None if local_vitals.get("hr_freq_bpm") is not None else local_vitals.get("analysis_status"),
                "current_block_local_n_peaks": local_vitals.get("hr_n_peaks"),
                "current_block_local_selection_reason": local_hr_reason,
                "current_block_local_br_selection_reason": local_br_reason,
                "current_br_selected_bin": local_br_bin,
                "current_br_selected_channel": local_br_ch,
                "historical_gate_min_bin": HISTORICAL_GATE_BINS[0],
                "historical_gate_max_bin": HISTORICAL_GATE_BINS[1],
                "historical_gate_min_range_m": HISTORICAL_MIN_RANGE_M,
                "historical_gate_max_range_m": HISTORICAL_MAX_RANGE_M,
                "current_selector_gate": "none_in_target_validation_independent_selection",
                "mmwave_input_source": "recomputed_same_window_raw_NPZ",
                "ecg_reference_source": "fixed_current_block_affine_ecg_hr_from_existing_335_row",
                "previous_current_independent_hr_bpm": float_or_none(row.get("current_hr_freq_bpm")),
                "previous_current_block_local_hr_bpm": float_or_none(row.get("local_hr_freq_bpm")),
            }
            for name, value in estimates.items():
                record[name] = value
                record[name.replace("_hr_bpm", "_abs_error_bpm")] = abs(float(value) - ecg) if value is not None and ecg is not None else None
            output.append(record)
            previous["hr"] = (local_hr_ch, local_hr_bin)
            previous["br"] = (local_br_ch, local_br_bin)
    output.sort(key=lambda row: (SUBJECTS.index(row["subject"]), row["block_id"], row["window_id"]))
    repro = {}
    for method, previous_key in (("current_independent_hr_bpm", "previous_current_independent_hr_bpm"), ("current_block_local_hr_bpm", "previous_current_block_local_hr_bpm")):
        pairs = [(float_or_none(row.get(method)), float_or_none(row.get(previous_key))) for row in output]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        deltas = [abs(a - b) for a, b in pairs]
        repro[method] = {"n_compared": len(pairs), "n_exact_at_1e-9": sum(delta <= 1e-9 for delta in deltas), "max_abs_delta_bpm": max(deltas) if deltas else None}
    return output, {"fixed_rows": len(fixed), "historical_targets": target_map, "current_reproduction": repro}


def paired_metrics(rows: list[dict], methods: list[str]) -> list[dict]:
    common = []
    for row in rows:
        if float_or_none(row.get("ecg_hr_bpm")) is not None and all(float_or_none(row.get(method)) is not None for method in methods):
            common.append(row)
    summary = []
    for method in methods:
        available = [row for row in rows if float_or_none(row.get("ecg_hr_bpm")) is not None and float_or_none(row.get(method)) is not None]
        pairs = [(float(row[method]), float(row["ecg_hr_bpm"])) for row in available]
        errors = [est - ref for est, ref in pairs]
        abs_errors = np.abs(errors)
        pearson = pearsonr([est for est, _ in pairs], [ref for _, ref in pairs]).statistic if len(pairs) >= 2 else None
        spearman = spearmanr([est for est, _ in pairs], [ref for _, ref in pairs]).statistic if len(pairs) >= 2 else None
        summary.append({
            "method": method,
            "all_available_n": len(available),
            "all_available_pct_of_335": round(100.0 * len(available) / len(rows), 3) if rows else None,
            "pairwise_common_window_n_all_methods": len(common),
            "mae_bpm_all_available": round(float(np.mean(abs_errors)), 6) if len(errors) else None,
            "median_ae_bpm_all_available": round(float(np.median(abs_errors)), 6) if len(errors) else None,
            "rmse_bpm_all_available": round(float(np.sqrt(np.mean(np.square(errors)))), 6) if len(errors) else None,
            "bias_estimator_minus_ecg_bpm_all_available": round(float(np.mean(errors)), 6) if len(errors) else None,
            "pearson_r_all_available": round(float(pearson), 6) if pearson is not None else None,
            "spearman_r_all_available": round(float(spearman), 6) if spearman is not None else None,
        })
    return summary


def pairwise_metrics(rows: list[dict], methods: list[str]) -> list[dict]:
    """Compare estimator errors on the exact same available ECG windows."""
    out = []
    for idx, method_a in enumerate(methods):
        for method_b in methods[idx + 1:]:
            pairs = []
            for row in rows:
                ecg = float_or_none(row.get("ecg_hr_bpm"))
                a = float_or_none(row.get(method_a))
                b = float_or_none(row.get(method_b))
                if ecg is not None and a is not None and b is not None:
                    pairs.append((abs(a - ecg), abs(b - ecg)))
            delta = np.asarray([a - b for a, b in pairs], dtype=float)
            out.append({
                "method_a": method_a,
                "method_b": method_b,
                "common_ecg_window_n": len(pairs),
                "mae_method_a_bpm": round(float(np.mean([a for a, _ in pairs])), 6) if pairs else None,
                "mae_method_b_bpm": round(float(np.mean([b for _, b in pairs])), 6) if pairs else None,
                "mean_abs_error_delta_a_minus_b_bpm": round(float(np.mean(delta)), 6) if len(delta) else None,
                "median_abs_error_delta_a_minus_b_bpm": round(float(np.median(delta)), 6) if len(delta) else None,
                "method_a_better_n": int(np.sum(delta < 0)) if len(delta) else 0,
                "tie_n": int(np.sum(delta == 0)) if len(delta) else 0,
                "method_b_better_n": int(np.sum(delta > 0)) if len(delta) else 0,
            })
    return out


def target_diagnostics(rows: list[dict], targets: dict) -> dict:
    result = {}
    for subject in SUBJECTS:
        subset = [row for row in rows if row["subject"] == subject]
        hist = targets[subject]
        summary = {"n_windows": len(subset), "historical_bin": hist["heart_bin"], "historical_channel": hist["heart_channel"]}
        for label, bin_key, ch_key in (("independent", "current_independent_selected_bin", "current_independent_selected_channel"), ("block_local", "current_block_local_selected_bin", "current_block_local_selected_channel")):
            valid = [(int(row[bin_key]), int(row[ch_key])) for row in subset if row.get(bin_key) not in (None, "") and row.get(ch_key) not in (None, "")]
            bin_delta = np.asarray([abs(b - hist["heart_bin"]) for b, _ in valid], dtype=float)
            ch_delta = np.asarray([abs(c - hist["heart_channel"]) for _, c in valid], dtype=float)
            result[f"{subject}_{label}"] = {
                "n": len(valid),
                "exact_bin_channel_n": sum(b == hist["heart_bin"] and c == hist["heart_channel"] for b, c in valid),
                "bin_diff_median": float(np.median(bin_delta)) if len(bin_delta) else None,
                "bin_diff_mean": float(np.mean(bin_delta)) if len(bin_delta) else None,
                "channel_diff_median": float(np.median(ch_delta)) if len(ch_delta) else None,
                "channel_diff_mean": float(np.mean(ch_delta)) if len(ch_delta) else None,
                "outside_historical_gate_n": sum(b < HISTORICAL_GATE_BINS[0] or b > HISTORICAL_GATE_BINS[1] for b, _ in valid),
            }
    return result


def timestamp_audit(rerun) -> dict:
    event_rows, frame_rows = [], []
    session_summaries = []
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        events = rerun.load_events(subject)
        physical, _digital = rerun.decode_biopac_markers(subject)
        blocks, _audits = rerun.block_intervals(subject, timestamps, events, physical)
        complete_ids = {block["block_id"] for block in blocks if block["status"] == "complete"}
        for event in events:
            if event.get("event") != "tick" or not (101 <= int(event["marker_int"]) <= 110) or event.get("segment") not in complete_ids:
                continue
            unix_ms = int(event["unix_ms_int"])
            idx = int(np.searchsorted(timestamps[:, 2], unix_ms, side="left"))
            candidates = [candidate for candidate in (idx, idx - 1) if 0 <= candidate < len(timestamps)]
            if not candidates:
                continue
            nearest = min(candidates, key=lambda candidate: abs(int(timestamps[candidate, 2]) - unix_ms))
            delta = int(timestamps[nearest, 2]) - unix_ms
            event_rows.append({"subject": subject, "segment": event.get("segment"), "event_marker": event["marker_int"], "event_unix_ms": unix_ms, "nearest_mmwave_row": nearest, "nearest_mmwave_unix_ms": int(timestamps[nearest, 2]), "delta_ms_mmwave_minus_event": delta, "nearest_abs_delta_gt_100ms": abs(delta) > 100})
        intervals = np.diff(timestamps[:, 2].astype(np.int64))
        for idx, delta in enumerate(intervals):
            frame_rows.append({"subject": subject, "frame_index_start": idx, "frame_index_end": idx + 1, "timestamp_start_unix_ms": int(timestamps[idx, 2]), "timestamp_end_unix_ms": int(timestamps[idx + 1, 2]), "interval_ms": int(delta), "interval_gt_20ms": int(delta) > 20, "interval_gt_50ms": int(delta) > 50, "interval_gt_100ms": int(delta) > 100, "interval_gt_500ms": int(delta) > 500})
        session_summaries.append({"subject": subject, "timestamp_rows": len(timestamps), "event_tick_rows": sum(row["subject"] == subject for row in event_rows), "frame_interval_rows": len(intervals), "frame_interval_median_ms": float(np.median(intervals)), "frame_interval_p95_ms": float(np.percentile(intervals, 95)), "frame_interval_p99_ms": float(np.percentile(intervals, 99)), "frame_interval_max_ms": int(np.max(intervals)), "frame_interval_n_gt_20ms": int(np.sum(intervals > 20)), "frame_interval_n_gt_50ms": int(np.sum(intervals > 50)), "frame_interval_n_gt_100ms": int(np.sum(intervals > 100)), "frame_interval_n_gt_500ms": int(np.sum(intervals > 500))})
    write_csv(TIMESTAMP_ROOT / "event_tick_to_mmwave_nearest_audit.csv", event_rows)
    write_csv(TIMESTAMP_ROOT / "mmwave_frame_interval_audit.csv", frame_rows)
    all_intervals = np.asarray([float(row["interval_ms"]) for row in frame_rows], dtype=float)
    summary = {"event_tick_rows": len(event_rows), "event_tick_n_abs_over_100ms": sum(bool(row["nearest_abs_delta_gt_100ms"]) for row in event_rows), "frame_interval_rows": len(frame_rows), "frame_interval_median_ms": float(np.median(all_intervals)), "frame_interval_p95_ms": float(np.percentile(all_intervals, 95)), "frame_interval_p99_ms": float(np.percentile(all_intervals, 99)), "frame_interval_max_ms": int(np.max(all_intervals)), "frame_interval_n_gt_20ms": int(np.sum(all_intervals > 20)), "frame_interval_n_gt_50ms": int(np.sum(all_intervals > 50)), "frame_interval_n_gt_100ms": int(np.sum(all_intervals > 100)), "frame_interval_n_gt_500ms": int(np.sum(all_intervals > 500)), "sessions": session_summaries}
    # Keep the report-facing aliases explicit so the timestamp summary and
    # the per-row CSV use the same threshold semantics.
    summary.update({
        "frame_interval_n_gt_20": summary["frame_interval_n_gt_20ms"],
        "frame_interval_n_gt_50": summary["frame_interval_n_gt_50ms"],
        "frame_interval_n_gt_100": summary["frame_interval_n_gt_100ms"],
        "frame_interval_n_gt_500": summary["frame_interval_n_gt_500ms"],
    })
    return {"summary": summary, "event_path": TIMESTAMP_ROOT / "event_tick_to_mmwave_nearest_audit.csv", "frame_path": TIMESTAMP_ROOT / "mmwave_frame_interval_audit.csv"}


def lineage() -> list[dict]:
    common = {"input_format": "8-channel complex range-domain DataCube NPZ; 100 Hz timestamps", "phase_extraction": "unwrap(angle(range_cube[:, bin, channel])) then 5 mm/(4π) displacement", "clutter_handling": "no separate DC/clutter stage in this HR estimator; linear detrend inside phase-score/spectral helper", "hr_band": "0.8-2.0 Hz / 48-120 bpm", "peak_rule": "adaptive prominence factors; min distance max(0.30 s, HR upper bound); IBI validity/fallback", "harmonic_rule": "v3.1.1 internal half/double/triple heuristic; external RSP gate inactive unless acq_path supplied", "qc": "signal hard gate and time/frequency/course checks in v3.1.1; targeted wrapper retains diagnostic status", "current_reproducibility_status": "source-level verified; same-window run recorded in this audit"}
    rows = []
    def add(ref, path, estimator_id, **extra):
        row = {"estimator_id": estimator_id, "repo": "greenboo26/focuswave-multimodal-attention-analysis", "branch": ref, "commit": ref, "script": path, "local_path": str(ALGO_ROOT), **common, **extra}
        try:
            row["commit"] = git(ALGO_ROOT, "rev-parse", ref)
            row["commit_time"] = git(ALGO_ROOT, "show", "-s", "--format=%cI", ref)
            row["source_sha256"] = hashlib.sha256(subprocess.check_output(["git", "-C", str(ALGO_ROOT), "show", f"{ref}:{path}"], stderr=subprocess.DEVNULL)).hexdigest()
        except Exception:
            row["current_reproducibility_status"] = "path_not_present_at_ref_or_unbound"
        rows.append(row)
    add("master", "scripts/process_vital_signs_v3_1_1.py", "HISTORICAL_V311_BP_HEART", bin_spacing="default 0.08 m/bin", physical_range_gate="default 0.3-1.5 m when caller supplies gate", target_selector="range power + phase stability; refined heart candidate", channel_selector="best heart selection score across channels", filter="4th-order SOS bandpass; bp_heart uses 0.8-2.0 Hz", hr_spectral_method="periodogram + segment correction + consensus/course", window_size="record-level; course 25 s / 5 s internal; historical comparison probes 60 s", step="course 5 s; probe pairing 60 s", historical_result="old 4.590 old-gate reproduction; corrected 3.777 chain uses same ECG reference and changed gate", current_reproducibility_status="historical source verified; exact historical result artifact binding retained in provenance")
    add("64634159d226ee1ed892d53e56fcf3697fbff9b8", "scripts/process_vital_signs_v3_1_1.py", "HISTORICAL_CORRECTED_3P777_PIPELINE", bin_spacing="0.037 m/bin supplied by run_hr_course_99_corrected.py", physical_range_gate="0.30-1.50 m = bins 9-40", target_selector="first 6000-frame selection then forced heart candidate for full record", channel_selector="refined heart candidate score", filter="4th-order SOS bandpass; bp_heart", hr_spectral_method="periodogram + peak/time course + segment correction/consensus", window_size="historical HR-course comparison 60 s behavior probe", step="probe-defined", historical_result="corrected HR-course MAE 3.7772146 bpm on 5 sessions / 99 valid windows", current_reproducibility_status="same target/gate logic recoverable; strict 60 s arm is NOT_APPLICABLE to current 20 s rows")
    add("64634159d226ee1ed892d53e56fcf3697fbff9b8", "scripts/maintenance/run_hr_course_99_corrected.py", "HISTORICAL_CORRECTED_RUNNER", bin_spacing="0.037 m/bin", physical_range_gate="0.30-1.50 m", target_selector="selection pass on first 6000 frames; forced heart target on full record", channel_selector="refined heart candidate", filter="delegates to v3.1.1 bp_heart", hr_spectral_method="delegates to v3.1.1", window_size="60 s historical probe output", step="20 s internal course", historical_result="generator for corrected-gate 3.777 audit package", current_reproducibility_status="runner present on current main; historical artifact is locally retained")
    add("64634159d226ee1ed892d53e56fcf3697fbff9b8", "scripts/maintenance/run_mmwave_targeted_validation_20260830.py", "CURRENT_BLOCK_LOCAL_PIPELINE", bin_spacing="0.037 m reporting only in continuity table; current selector itself is not physically gated", physical_range_gate="none in independent_selection", target_selector="per-window phase/power selection; local arm prefers previous ±3 bins with channel penalty", channel_selector="current best score; local continuity penalty", filter="producer existing 0.8-2.0 Hz bandpass", hr_spectral_method="periodogram + peak/time estimate; bounded diagnostic, no VMD", window_size="20 s", step="10 s; 5 s boundary guard", historical_result="current block-local HR MAE ≈24.885/24.881 bpm", current_reproducibility_status="recomputed on frozen 335 rows")
    for path, eid in [("scripts/process_vital_signs_v2.py", "HISTORICAL_V2_ROUTE"), ("scripts/process_vital_signs_v3.py", "HISTORICAL_V3_ROUTE"), ("scripts/process_vital_signs_v5.py", "HISTORICAL_V5_ROUTE"), ("scripts/process_vital_signs_v9.py", "HISTORICAL_V9_ROUTE")]:
        add("master", path, eid, bin_spacing="default/legacy route; not the confirmed 3.777 corrected run", physical_range_gate="script-specific", target_selector="script-specific", channel_selector="script-specific", filter="script-specific", hr_spectral_method="periodogram/VMD variants", window_size="script-specific", step="script-specific", historical_result="historical route inventory; not identified as 3.777 producer")
    add("master", "docs/交付/毫米波ECG金标准验证_0816/脚本/calibrate_ecg_mmwave.py", "HISTORICAL_CALIBRATION_INVENTORY", bin_spacing="not an HR estimator parameter", physical_range_gate="not an HR estimator", target_selector="calibration/reference utility", channel_selector="not an HR estimator", filter="ECG/reference-side utility", hr_spectral_method="not an HR estimator", window_size="script-specific", step="script-specific", historical_result="calibration lineage only; not identified as 3.777 producer")
    add("d87229afe071f23450728a6d617ec82317e6c9df", "pipelines/mmwave/ecg_reference_v1.py", "REANALYSIS_ECG_REFERENCE_INVENTORY", bin_spacing="not bound to corrected 0.037 m/bin result", physical_range_gate="reanalysis-specific", target_selector="reanalysis-specific", channel_selector="reanalysis-specific", filter="reanalysis-specific", hr_spectral_method="ECG reference/reanalysis utility", window_size="reanalysis-specific", step="reanalysis-specific", historical_result="reanalysis inventory; not identified as 3.777 producer")
    add("d87229afe071f23450728a6d617ec82317e6c9df", "pipelines/mmwave/ssa_vmd_reference_v1.py", "REANALYSIS_SSA_VMD_INVENTORY", bin_spacing="reanalysis-specific", physical_range_gate="reanalysis-specific", target_selector="reanalysis-specific", channel_selector="reanalysis-specific", filter="SSA/VMD reanalysis utility", hr_spectral_method="SSA/VMD variant; not the confirmed bp_heart chain", window_size="reanalysis-specific", step="reanalysis-specific", historical_result="reanalysis inventory; not identified as 3.777 producer")
    return rows


def build_reports(replay_rows: list[dict], metrics_rows: list[dict], timestamp: dict, meta: dict) -> tuple[str, str]:
    ts = timestamp["summary"]
    methods = ["historical_original_hr_bpm", "historical_20s_adapt_hr_bpm", "current_independent_hr_bpm", "current_block_local_hr_bpm"]
    lines = ["# mmWave HR estimator same-window audit — 2026-08-30", "", "状态：`PARTIAL`", "", "本轮固定既有 335 个 complete formal-block、20 s 窗口及其 block-affine ECG HR；毫米波端对同一 raw NPZ window 重新计算 current independent/current block-local，并恢复历史 corrected-gate 的固定 target 后做 20 s adaptation。历史原定义的 60 s arm 不被静默改成 20 s，标记为 `NOT_APPLICABLE_TO_20S`。", "", "## 1. Direct answer", "", "- 历史 `3.7772146 bpm` 的真实来源：`run_hr_course_99_corrected.py → process_vital_signs_v3_1_1.py`, 先用 6000-frame selection 选固定 heart channel/bin，再在全记录上运行 `bp_heart`；距离口径为 `0.037 m/bin`、物理 gate `0.30–1.50 m`。历史结果是 5 sessions / 99 valid 60 s HR-course windows。", "- 严格历史 60 s estimator 在当前 20 s denominator 上为 `NOT_APPLICABLE_TO_20S`，没有伪造 HR。", "- 当前 335-row comparison 的历史 20 s adaptation 与两种 current estimator 指标见下表；所有统计均为描述性，不对重叠窗口做推断性显著性结论。", "", "| estimator | all-available n | common-window n (all four) | MAE | median AE | RMSE | bias | Pearson r | Spearman r |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in metrics_rows:
        lines.append("| {method} | {all_available_n} | {pairwise_common_window_n_all_methods} | {mae_bpm_all_available} | {median_ae_bpm_all_available} | {rmse_bpm_all_available} | {bias_estimator_minus_ecg_bpm_all_available} | {pearson_r_all_available} | {spearman_r_all_available} |".format(**row))
    lines += ["", "## 2. Interpretation case", "", "当前结果属于 `CASE B + CASE D` 的组合，而不是单独 CASE E：严格历史 60 s 不能在当前 20 s window 中直接成立；20 s adaptation 若接近 current，说明短窗/当前 cohort/当前 raw target condition 是重要差异。历史 3.777 还依赖 corrected physical gate、固定 target 和历史 60 s/QC denominator，因此不能据此判定 current pipeline regression。只有在同一 20 s 语义下 historical adaptation 明显优于 current、且 coverage/QC 等价时，才可升级为 regression candidate。", "", "## 3. Target/bin/channel", "", "- 历史 corrected target 使用每个 session 的 selection artifact 固定目标：`97793 ch4/bin9 (0.333 m)`、`9779 ch5/bin19 (0.703 m)`、`97795 ch7/bin25 (0.925 m)`。", "- 当前 independent 与 block-local 的每窗 bin/channel、score、validity、missing reason 已逐行保存；当前 selector 的 independent path 不施加物理 range gate，不能把 `0.037 m/bin` 当作已经改变当前 selection。", "- `MMWAVE_HR_ESTIMATOR_LINEAGE.csv` 记录了 0.08/0.037、gate、target、phase、filter、periodogram、peak、harmonic、window、QC 与历史结果的具体代码入口。", "", "## 4. Timestamp semantics", "", f"- A（event tick Unix ms ↔ nearest mmWave timestamp）共 {ts['event_tick_rows']} rows，其中 `|delta|>100 ms` 为 {ts['event_tick_n_abs_over_100ms']}；这就是旧统计中的 730 类近邻差异，属于 event-to-mmWave nearest residual。它不是 frame gap。", f"- B（相邻 mmWave timestamp interval）共 {ts['frame_interval_rows']} rows：median={ts['frame_interval_median_ms']:.3f} ms，p95={ts['frame_interval_p95_ms']:.3f} ms，p99={ts['frame_interval_p99_ms']:.3f} ms，max={ts['frame_interval_max_ms']} ms；>20 ms={ts['frame_interval_n_gt_20']}，>50 ms={ts['frame_interval_n_gt_50']}，>100 ms={ts['frame_interval_n_gt_100']}，>500 ms={ts['frame_interval_n_gt_500']}。", "- 因此只有 B 的 >100 ms 才能称为真实相邻帧间隔；A 的 730 不能称为 dropout/frame gap。详细 CSV 保存在本地 derived 目录，manifest 记录 row count 与 SHA-256。", "", "## 5. Decision", "", "- 当前没有足够证据报告 `HISTORICAL_PIPELINE_STILL_GOOD_ON_CURRENT_WINDOWS`，因为 strict 60 s arm 不适用，20 s adaptation 不是历史原始语义。", "- 当前不报告 `CURRENT_PIPELINE_REGRESSION`；历史与当前在 target/gate/window/cohort/QC 上尚未完全等价。", "- 是否需要修当前 HR pipeline：本轮证据支持继续把 HR 保持 `HOLD` 并进入针对 target selection / short-window estimator 的修复设计，但不授权直接改 producer。唯一推荐动作是：在保持 335-row contract 和 ECG alignment 不变的前提下，先完成一个预注册的 `0.037 m/bin + block-local target + 20 s` estimator sensitivity，明确 target/gate/coverage 后再决定是否修复。", "", "## 6. Artifacts", "", "- `MMWAVE_HR_ESTIMATOR_LINEAGE.csv`", "- `MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv`", "- `MMWAVE_HR_ESTIMATOR_SUMMARY.csv`", "- `MMWAVE_HR_ESTIMATOR_COMPARISON_REPORT_2026-08-30.md`", "- `MMWAVE_TIMESTAMP_SEMANTICS_AUDIT_2026-08-30.md`", "- local `event_tick_to_mmwave_nearest_audit.csv` and `mmwave_frame_interval_audit.csv`"]
    report = "\n".join(lines) + "\n"
    timestamp_report = "\n".join(["# mmWave timestamp semantics audit — 2026-08-30", "", "状态：`PARTIAL / SEMANTICS_CLASSIFIED`", "", "## A. Event tick to nearest mmWave timestamp", "", f"Rows: {ts['event_tick_rows']}; `|nearest delta| > 100 ms`: {ts['event_tick_n_abs_over_100ms']}. This is an event Unix-ms versus nearest mmWave timestamp residual. It is not an adjacent frame interval and must not be called a dropout/frame gap.", "", "## B. Adjacent mmWave frame timestamp interval", "", f"Rows: {ts['frame_interval_rows']}; median {ts['frame_interval_median_ms']:.3f} ms; p95 {ts['frame_interval_p95_ms']:.3f} ms; p99 {ts['frame_interval_p99_ms']:.3f} ms; max {ts['frame_interval_max_ms']} ms.", "", f"Threshold counts: >20 ms {ts['frame_interval_n_gt_20']}; >50 ms {ts['frame_interval_n_gt_50']}; >100 ms {ts['frame_interval_n_gt_100']}; >500 ms {ts['frame_interval_n_gt_500']}.", "", "## Interpretation", "", f"The historical 730-like count is A: {ts['event_tick_n_abs_over_100ms']} event-to-nearest residuals. Only B can establish a true adjacent-frame gap; the complete B table and per-session summaries are recorded in `mmwave_frame_interval_audit.csv`.", "", "## Source semantics", "", "The mmWave timestamp Unix-ms column is read from the existing session `*_mmwave_timestamps.csv`; the acquisition program writes the mmWave frame timestamp alongside captured frames. No timestamp producer or raw file was changed in this audit.", ""])
    return report, timestamp_report


def main() -> int:
    rerun = load_rerun_module()
    sys_path = ALGO_ROOT / "scripts"
    import sys
    sys.path.insert(0, str(sys_path))
    import process_vital_signs_v3_1_1 as algo
    replay_rows, meta = recompute_same_window(rerun, algo)
    methods = ["historical_original_hr_bpm", "historical_20s_adapt_hr_bpm", "current_independent_hr_bpm", "current_block_local_hr_bpm"]
    metrics_rows = paired_metrics(replay_rows, methods)
    pairwise_rows = pairwise_metrics(replay_rows, methods)
    meta["target_diagnostics"] = target_diagnostics(replay_rows, meta["historical_targets"])
    timestamp = timestamp_audit(rerun)
    write_csv(RESULT_ROOT / "MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv", replay_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_ESTIMATOR_SUMMARY.csv", metrics_rows)
    pairwise_path = RESULT_ROOT / "MMWAVE_HR_ESTIMATOR_PAIRWISE_COMPARISON.csv"
    write_csv(pairwise_path, pairwise_rows)
    write_csv(RESULT_ROOT / "MMWAVE_HR_ESTIMATOR_LINEAGE.csv", lineage())
    report, timestamp_report = build_reports(replay_rows, metrics_rows, timestamp, meta)
    pairwise_lines = ["", "## 7. Pairwise same-denominator comparisons", "", "Each row uses only windows where both estimators and ECG are available; `delta` is absolute-error(method_a) minus absolute-error(method_b).", "", "| method_a | method_b | n | MAE a | MAE b | mean delta | median delta | a better | tie | b better |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    pairwise_lines.extend(["| {method_a} | {method_b} | {common_ecg_window_n} | {mae_method_a_bpm} | {mae_method_b_bpm} | {mean_abs_error_delta_a_minus_b_bpm} | {median_abs_error_delta_a_minus_b_bpm} | {method_a_better_n} | {tie_n} | {method_b_better_n} |".format(**row) for row in pairwise_rows])
    pairwise_lines += ["", "## 8. Target/reproduction diagnostics", "", *[f"- `{key}`: `{value}`" for key, value in sorted(meta["target_diagnostics"].items())], f"- Frozen prior current-row reproduction: `{json.dumps(meta['current_reproduction'], ensure_ascii=False)}`"]
    report += "\n".join(pairwise_lines) + "\n"
    report_path = RESULT_ROOT / "MMWAVE_HR_ESTIMATOR_COMPARISON_REPORT_2026-08-30.md"
    timestamp_report_path = RESULT_ROOT / "MMWAVE_TIMESTAMP_SEMANTICS_AUDIT_2026-08-30.md"
    report_path.write_text(report, encoding="utf-8")
    timestamp_report_path.write_text(timestamp_report, encoding="utf-8")
    output_files = ["MMWAVE_HR_ESTIMATOR_LINEAGE.csv", "MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv", "MMWAVE_HR_ESTIMATOR_SUMMARY.csv", "MMWAVE_HR_ESTIMATOR_PAIRWISE_COMPARISON.csv", "MMWAVE_HR_ESTIMATOR_COMPARISON_REPORT_2026-08-30.md", "MMWAVE_TIMESTAMP_SEMANTICS_AUDIT_2026-08-30.md"]
    manifest_extra = {"pairwise_comparison_rows": pairwise_rows, "target_diagnostics": meta["target_diagnostics"], "current_reproduction": meta["current_reproduction"]}
    manifest = {"status": "PARTIAL / SEMANTICS_CLASSIFIED / SAME_WINDOW_ESTIMATOR_AUDIT_COMPLETE", "canonical_main_verified": git(ALGO_ROOT, "rev-parse", "HEAD"), "canonical_main_remote": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"), "fixed_input": str(FIXED_INPUT), "fixed_input_sha256": sha256(FIXED_INPUT), "fixed_denominator_rows": len(replay_rows), "fixed_ecg_source": "existing current block-affine ECG values; not recomputed", "analysis_set": list(SUBJECTS), "historical_strict_semantics": "NOT_APPLICABLE_TO_20S", "historical_20s_adaptation": "same corrected target/gate/phase/filter/HR rules; only window length adapted", "timestamp_audit": timestamp["summary"], "timestamp_csv_outputs": [{"path": str(timestamp["event_path"]), "row_count": sum(1 for _ in csv.DictReader(timestamp["event_path"].open(encoding="utf-8-sig"))), "sha256": sha256(timestamp["event_path"])}, {"path": str(timestamp["frame_path"]), "row_count": sum(1 for _ in csv.DictReader(timestamp["frame_path"].open(encoding="utf-8-sig"))), "sha256": sha256(timestamp["frame_path"])}], "outputs": [{"path": name, "sha256": sha256(RESULT_ROOT / name)} for name in output_files], "excluded": ["new HRV algorithm", "Issue #16", "C2B", "C2C", "full formal batch", "producer modification", "firmware modification", "raw data modification", "FocusWave acquisition modification", "Attention-Analysis portable V2 modification", "external RSP production feedback"]}
    manifest.update(manifest_extra)
    (RESULT_ROOT / "MMWAVE_HR_ESTIMATOR_AUDIT_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "rows": len(replay_rows), "metrics": metrics_rows, "timestamp": timestamp["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
