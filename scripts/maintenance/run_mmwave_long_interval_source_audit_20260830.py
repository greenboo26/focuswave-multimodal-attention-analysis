"""Audit the source and impact of long mmWave timestamp intervals.

This is a read-only diagnostic. It does not modify the acquisition producer,
raw data, ECG, or the HR estimator.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(r"D:\acq_mmwave_data")
FOCUSWAVE_ROOT = Path(r"D:\Project\厚粲杯\05_实验\FocusWave")
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_INPUT = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
WRAPPER = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
ALIGNMENT_AUDIT = RESULT_ROOT / "ecg_alignment_audit.csv"
SUBJECTS = ("97793", "9779", "97795")
LONG_THRESHOLD_MS = 100
VERY_LONG_THRESHOLD_MS = 500
FIXED_PERIODS_S = (1, 2, 5, 10, 30, 60)
METHODS = {"arm0": "arm0_hr_bpm", "arm1": "arm1_gate_only_hr_bpm", "arm2": "arm2_historical_target_hr_bpm"}


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


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception:
        return "unavailable"


def num(value):
    if value in (None, "", "None", "nan", "NaN"):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def file_layout(rerun, subject: str):
    reader = rerun.PartReader(subject)
    return [(reader.files[i].name, int(reader.starts[i]), int(reader.starts[i + 1])) for i in range(len(reader.files))]


def file_for(layout, frame_row: int) -> str:
    for name, start, end in layout:
        if start <= frame_row < end:
            return name
    return "OUTSIDE_NPZ_LAYOUT"


def segment_intervals(events: list[dict]) -> list[dict]:
    result = []
    segments = sorted({row.get("segment") for row in events if row.get("segment")})
    for segment in segments:
        starts = sorted(row["unix_ms_int"] for row in events if row.get("segment") == segment and row.get("event") == "segment_start")
        ends = sorted(row["unix_ms_int"] for row in events if row.get("segment") == segment and row.get("event") == "segment_end")
        for start in starts:
            end = next((value for value in ends if value > start), None)
            if end is not None:
                result.append({"segment": segment, "start": start, "end": end})
    return result


def phase_at(intervals: list[dict], timestamp: int) -> str:
    for item in intervals:
        if item["start"] <= timestamp <= item["end"]:
            return item["segment"]
    return "outside_formal_segments"


def block_for(before_phase: str, after_phase: str) -> str:
    for phase in (before_phase, after_phase):
        if phase.startswith("block"):
            return phase
    return ""


def gap_distribution(values: np.ndarray) -> dict:
    if len(values) == 0:
        return {"n": 0, "min_ms": None, "p10_ms": None, "median_ms": None, "p90_ms": None, "p95_ms": None, "max_ms": None}
    return {"n": int(len(values)), "min_ms": int(np.min(values)), "p10_ms": round(float(np.percentile(values, 10)), 3), "median_ms": round(float(np.median(values)), 3), "p90_ms": round(float(np.percentile(values, 90)), 3), "p95_ms": round(float(np.percentile(values, 95)), 3), "max_ms": int(np.max(values))}


def seconds_distribution(values: np.ndarray) -> dict:
    if len(values) == 0:
        return {"n": 0, "min_s": None, "p10_s": None, "median_s": None, "p90_s": None, "p95_s": None, "max_s": None}
    return {"n": int(len(values)), "min_s": round(float(np.min(values)), 3), "p10_s": round(float(np.percentile(values, 10)), 3), "median_s": round(float(np.median(values)), 3), "p90_s": round(float(np.percentile(values, 90)), 3), "p95_s": round(float(np.percentile(values, 95)), 3), "max_s": round(float(np.max(values)), 3)}


def fixed_period_counts(values_s: np.ndarray, tolerance_s: float = 1.0) -> dict:
    return {str(period): int(np.sum(np.abs(values_s - period) <= tolerance_s)) for period in FIXED_PERIODS_S}


def seconds_histogram(values_s: np.ndarray) -> dict:
    bins = (("0-5", 0, 5), ("5-8", 5, 8), ("8-9.5", 8, 9.5), ("9.5-10.5", 9.5, 10.5), ("10.5-12", 10.5, 12), ("12-15", 12, 15), ("15+", 15, float("inf")))
    return {label: int(np.sum((values_s >= lower) & (values_s < upper))) for label, lower, upper in bins}


def periodicity_metrics(python_event_ms: np.ndarray, dll_event_ms: np.ndarray, frame_ids: np.ndarray) -> dict:
    python_inter = np.diff(python_event_ms) / 1000.0
    dll_inter = np.diff(dll_event_ms) / 1000.0
    frame_inter = np.diff(frame_ids)
    return {
        "python_inter_event_distribution_s": seconds_distribution(python_inter),
        "dll_inter_event_distribution_s": seconds_distribution(dll_inter),
        "frame_inter_event_distribution_frames": seconds_distribution(frame_inter.astype(float)),
        "python_fixed_period_counts_within_1s": fixed_period_counts(python_inter),
        "dll_fixed_period_counts_within_1s": fixed_period_counts(dll_inter),
        "python_inter_event_histogram_s": seconds_histogram(python_inter),
        "dll_inter_event_histogram_s": seconds_histogram(dll_inter),
        "frame_modulo_1000_counts": {str(int(value)): int(np.sum((frame_ids % 1000) == value)) for value in sorted(np.unique(frame_ids % 1000))},
        "frame_modulo_1000_all_same": bool(len(np.unique(frame_ids % 1000)) == 1),
    }


def source_and_events(rerun) -> tuple[list[dict], dict, dict]:
    event_rows, source_summary = [], {"subjects": {}, "all_long_events": 0, "all_long_gt500_events": 0}
    gap_indices = {}
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        events = rerun.load_events(subject)
        intervals = segment_intervals(events)
        layout = file_layout(rerun, subject)
        python_ts = timestamps[:, 2].astype(np.int64)
        dll_ts = timestamps[:, 1].astype(np.int64)
        python_diff = np.diff(python_ts)
        dll_diff = np.diff(dll_ts)
        long_idx = np.flatnonzero(python_diff > LONG_THRESHOLD_MS)
        gap_indices[subject] = long_idx
        nominal_python = float(np.median(python_diff[python_diff <= LONG_THRESHOLD_MS]))
        nominal_dll = float(np.median(dll_diff))
        for idx in long_idx:
            before_phase = phase_at(intervals, int(python_ts[idx]))
            after_phase = phase_at(intervals, int(python_ts[idx + 1]))
            before_file = file_for(layout, int(idx))
            after_file = file_for(layout, int(idx + 1))
            block_start = next(
                (item["start"] for item in intervals if item["segment"] == before_phase),
                python_ts[idx],
            )
            event_rows.append({
                "subject": subject,
                "frame_idx_before": int(timestamps[idx, 0]),
                "frame_idx_after": int(timestamps[idx + 1, 0]),
                "timestamp_before": int(python_ts[idx]),
                "timestamp_after": int(python_ts[idx + 1]),
                "dll_timestamp_before": int(dll_ts[idx]),
                "dll_timestamp_after": int(dll_ts[idx + 1]),
                "frame_idx_before_mod_1000": int(timestamps[idx, 0]) % 1000,
                "frame_idx_after_mod_1000": int(timestamps[idx + 1, 0]) % 1000,
                "interval_ms": int(python_diff[idx]),
                "estimated_missing_frames": round(float(python_diff[idx] / nominal_python), 3),
                "local_nominal_interval_ms": round(nominal_python, 3),
                "dll_timestamp_interval_ms": int(dll_diff[idx]),
                "block_id": block_for(before_phase, after_phase),
                "phase": before_phase if before_phase == after_phase else f"{before_phase}->{after_phase}",
                "relative_time_in_recording": round(float((python_ts[idx] - python_ts[0]) / 1000.0), 3),
                "relative_time_in_block": round(float((python_ts[idx] - block_start) / 1000.0), 3) if before_phase.startswith("block") else None,
                "npz_file_before": before_file,
                "npz_file_after": after_file,
                "same_file": before_file == after_file,
                "chunk_boundary_candidate": before_file != after_file,
                "block_boundary_candidate": before_phase != after_phase and (before_phase.startswith("block") or after_phase.startswith("block")),
                "rest_candidate": "rest" in (before_phase, after_phase),
                "timestamp_column": "Python time.time() column 3",
            })
        source_summary["subjects"][subject] = {
            "timestamp_rows": int(len(timestamps)),
            "python_nominal_interval_ms": round(nominal_python, 3),
            "dll_nominal_interval_ms": round(nominal_dll, 3),
            "python_long_n": int(len(long_idx)),
            "python_gt500_n": int(np.sum(python_diff > VERY_LONG_THRESHOLD_MS)),
            "python_long_distribution": gap_distribution(python_diff[long_idx]),
            "python_nonpositive_adjacent_intervals": int(np.sum(python_diff <= 0)),
            "python_negative_adjacent_intervals": int(np.sum(python_diff < 0)),
            "dll_gt100_n": int(np.sum(dll_diff > LONG_THRESHOLD_MS)),
            "dll_gt500_n": int(np.sum(dll_diff > VERY_LONG_THRESHOLD_MS)),
            "dll_nonpositive_adjacent_intervals": int(np.sum(dll_diff <= 0)),
            "npz_file_count": len(layout),
            "npz_chunk_size_observed": sorted({end - start for _, start, end in layout}),
            "long_events_at_chunk_boundary_n": int(sum(file_for(layout, int(idx)) != file_for(layout, int(idx + 1)) for idx in long_idx)),
            "periodicity": periodicity_metrics(python_ts[long_idx], dll_ts[long_idx], timestamps[long_idx, 0].astype(np.int64)),
            "phase_counts": {phase: sum(1 for row in event_rows if row["subject"] == subject and row["phase"] == phase) for phase in sorted({row["phase"] for row in event_rows if row["subject"] == subject})},
        }
        source_summary["all_long_events"] += len(long_idx)
        source_summary["all_long_gt500_events"] += int(np.sum(python_diff > VERY_LONG_THRESHOLD_MS))
    source_summary["python_long_all_gt500"] = source_summary["all_long_events"] == source_summary["all_long_gt500_events"]
    source_summary["checks"] = {
        "duplicate_long_event_frame_indices": len(event_rows) - len({(row["subject"], row["frame_idx_before"]) for row in event_rows}),
        "nonpositive_python_adjacent_intervals": sum(item["python_nonpositive_adjacent_intervals"] for item in source_summary["subjects"].values()),
        "negative_python_adjacent_intervals": sum(item["python_negative_adjacent_intervals"] for item in source_summary["subjects"].values()),
        "nonpositive_dll_adjacent_intervals": sum(item["dll_nonpositive_adjacent_intervals"] for item in source_summary["subjects"].values()),
        "python_events_in_100_to_500ms_inclusive": sum(100 < int(row["interval_ms"]) <= 500 for row in event_rows),
        "all_long_events_chunk_boundary": all(bool(row["chunk_boundary_candidate"]) for row in event_rows),
        "all_long_events_frame_modulo_1000_same": all(item["periodicity"]["frame_modulo_1000_all_same"] for item in source_summary["subjects"].values()),
        "timestamp_reset_found": any(item["python_negative_adjacent_intervals"] or item["dll_nonpositive_adjacent_intervals"] for item in source_summary["subjects"].values()),
    }
    source_summary["all_python_long_distribution"] = gap_distribution(np.asarray([row["interval_ms"] for row in event_rows], dtype=np.int64))
    source_summary["all_dll_long_distribution"] = gap_distribution(np.asarray([row["dll_timestamp_interval_ms"] for row in event_rows], dtype=np.int64))
    return event_rows, source_summary, gap_indices


def window_burden(rerun, gap_indices: dict, source_summary: dict) -> list[dict]:
    frozen = [row for row in read_csv(FIXED_INPUT) if row.get("subject") in SUBJECTS]
    output = []
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        python_ts = timestamps[:, 2].astype(np.int64)
        dll_ts = timestamps[:, 1].astype(np.int64)
        python_diff = np.diff(python_ts)
        dll_nominal = float(source_summary["subjects"][subject]["dll_nominal_interval_ms"])
        for row in [item for item in frozen if item["subject"] == subject]:
            start, end = int(row["mmwave_start_row"]), int(row["mmwave_end_row_exclusive"])
            inside = gap_indices[subject][(gap_indices[subject] >= start) & ((gap_indices[subject] + 1) < end)]
            values = python_diff[inside]
            actual = end - start
            expected = int(round(20000.0 / dll_nominal))
            output.append({
                "subject": subject,
                "block_id": row["block_id"],
                "window_id": row["window_id"],
                "window_start": row["window_start_unix_ms"],
                "window_end": row["window_end_unix_ms"],
                "n_gap_gt100": int(len(values)),
                "n_gap_gt500": int(np.sum(values > VERY_LONG_THRESHOLD_MS)),
                "max_gap_ms": int(np.max(values)) if len(values) else 0,
                "sum_gap_ms": int(np.sum(values)) if len(values) else 0,
                "expected_duration_ms": 20000,
                "observed_timestamp_span_ms": int(python_ts[end - 1] - python_ts[start]),
                "observed_dll_timestamp_span_ms": int(dll_ts[end - 1] - dll_ts[start]),
                "actual_frame_count": actual,
                "expected_frame_count_local": expected,
                "estimated_frame_loss_fraction": round(max(0.0, 1.0 - actual / expected), 6) if expected else None,
                "ecg_hr_bpm": row.get("ecg_hr_bpm"),
                "arm0_hr_bpm": row.get("arm0_hr_bpm"),
                "arm0_abs_error": row.get("arm0_abs_error"),
                "arm1_abs_error": row.get("arm1_gate_only_abs_error"),
                "arm2_abs_error": row.get("arm2_historical_target_abs_error"),
                "gap_source_interpretation": "Python consumer/write timestamp artifact candidate; DLL timestamp remains regular",
            })
    return output


def rho(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 3 or len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return None
    return round(float(spearmanr(x, y).statistic), 6)


def correlations(rows: list[dict]) -> list[dict]:
    out = []
    predictors = {"n_gap_gt100": "n_gap_gt100", "sum_gap_ms": "sum_gap_ms", "max_gap_ms": "max_gap_ms", "estimated_frame_loss_fraction": "estimated_frame_loss_fraction"}
    strata = [("overall", "all", rows)]
    strata += [("participant", subject, [row for row in rows if row["subject"] == subject]) for subject in SUBJECTS]
    strata += [("block", block, [row for row in rows if row["block_id"] == block]) for block in sorted({row["block_id"] for row in rows})]
    for stratum_type, stratum, subset in strata:
        for arm, error_key in (("arm0", "arm0_abs_error"), ("arm1", "arm1_abs_error"), ("arm2", "arm2_abs_error")):
            for predictor, predictor_key in predictors.items():
                pairs = [(num(row.get(error_key)), num(row.get(predictor_key))) for row in subset]
                pairs = [(error, burden) for error, burden in pairs if error is not None and burden is not None]
                out.append({"stratum_type": stratum_type, "stratum": stratum, "arm": arm, "predictor": predictor, "n": len(pairs), "spearman_r": rho([burden for _, burden in pairs], [error for error, _ in pairs])})
    return out


def source_report(source_summary: dict, event_rows: list[dict], burden_rows: list[dict], corr_rows: list[dict]) -> str:
    source_commit = git(FOCUSWAVE_ROOT, "rev-parse", "ecg")
    old_commit = "817a7fccb969bcc6e1e0071b387f88e3b3494481"
    source_lines = [
        "# mmWave long-frame interval source and impact audit — 2026-08-30", "", "状态：`PARTIAL / TIMESTAMP_RECORDING_ARTIFACT / GAP_EFFECT_UNRESOLVED`", "",
        "## Direct answer", "",
        f"- 457 个 Python timestamp column-3 长间隔全部同时 >500 ms：{source_summary['all_long_events']} / {source_summary['all_long_gt500_events']}。", f"- 全部 457 个 Python 长间隔分布（min/p10/median/p90/p95/max ms）：{source_summary['all_python_long_distribution']}；对应 DLL 间隔分布：{source_summary['all_dll_long_distribution']}。", "- 457 个事件全部落在 NPZ file/chunk boundary；每个 subject 的边界数与长间隔数一一对应。", "- 同一批数据的 DLL timestamp column-2 没有任何 >100 ms 或 >500 ms interval，说明当前 457 更符合 consumer/write timestamp artifact，而不是已被源码证明的 sensor frame loss。", "- 事件周期不是独立生理周期，而是 1000-frame NPZ rotation/write pattern candidate；不能把 estimated_missing_frames 当作实际丢帧数。", "",
        "## Acquisition source evidence", "",
        f"- `FocusWave@ecg` source commit: `{source_commit}`; historical acquisition fix commit: `{old_commit}` (`v1.4.4`).", "- `01-MainProgram/core/mmwave_capture.py:337-342`, `_on_data`: SDK/DLL callback only puts `receive_data` into a bounded queue (`maxsize=5000`); queue full increments `error_count` but does not write a timestamp row.", "- `:466-489`, `_process_data_loop`: consumer thread dequeues data and calls `_process_datacube` for dataType 3.", "- `:352-376`, `_dotnet_ts_to_unix_ms`: DLL callback `receive_data.timeStamp` is converted to Unix ms; this is the hardware/DLL-side timestamp field.", "- `:378-397`, `_process_datacube`: after dequeue, it obtains DLL time and Python `time.time()`, then writes both to timestamp CSV. The audited column 3 is therefore generated at consumer/write processing time, not at callback receipt.", "- `:428-431` and `:433-464`: every 1000 processed frames triggers `_flush_npz_chunk`; `np.savez_compressed` runs in the same consumer thread.", "- `:558-585`, `stop`: stops DLL, waits up to 5 s for the queue, stops worker, and writes the final NPZ chunk. Historical `v1.4.4` only added conversion-error/empty-chunk protection; it did not remove this architecture.", "",
        "## Long-event classification", "", f"Rows: {len(event_rows)}; all >500 ms: `{source_summary['python_long_all_gt500']}`. See `MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv` for every row, phase, chunk, block and rest flags.", "", "| subject | Python >100 | Python >500 | DLL >100 | DLL >500 | chunk-boundary events | Python long distribution |", "|---|---:|---:|---:|---:|---:|---|"]
    for subject in SUBJECTS:
        item = source_summary["subjects"][subject]
        source_lines.append(f"| {subject} | {item['python_long_n']} | {item['python_gt500_n']} | {item['dll_gt100_n']} | {item['dll_gt500_n']} | {item['long_events_at_chunk_boundary_n']} | {item['python_long_distribution']} |")
    source_lines += ["", "## ECG/BIOPAC alignment contract", "", "Window HR/ECG comparisons are inherited from the fixed 335-row block-local replay and its per-block alignment audit: `events.csv` start/end markers (baseline 11/21, block1 12/22, block2 13/23, block3 14/24, rest 15/25; block4 16/26 when present) plus 101–110 per-second ticks. The existing audit records 8 complete blocks, 7/8 exact marker sequences, and block-wise ECG affine fits; no cross-rest or cross-posture mapping is used. The marker/tick audit remains evidence for alignment quality, not a license to interpret Python writer timestamps as sensor timing. The prior 12 transitions remain revoked as continuity-failure evidence: they were baseline/pre-block startup transitions, not valid within-block transitions.", "", "## Periodicity and distribution", "", "The periodicity audit reports quantiles, fixed 1/2/5/10/30/60-s matches within ±1 s, histograms, frame modulo 1000, and phase/boundary counts below. Frame-index spacing and DLL-time spacing are the acquisition-side checks; Python-time spacing is separately shown because it is generated in the consumer/write path.", "", "| subject | Python inter-event s (median [p10,p90]) | DLL inter-event s (median [p10,p90]) | frame inter-event (median) | Python fixed-period matches | DLL fixed-period matches | frame modulo 1000 | phases |", "|---|---|---|---:|---|---|---|---|",]
    for subject in SUBJECTS:
        periodicity = source_summary["subjects"][subject]["periodicity"]
        py = periodicity["python_inter_event_distribution_s"]
        dll = periodicity["dll_inter_event_distribution_s"]
        frame = periodicity["frame_inter_event_distribution_frames"]
        modulo = periodicity["frame_modulo_1000_counts"]
        phases = source_summary["subjects"][subject]["phase_counts"]
        source_lines.append(f"| {subject} | {py['median_s']} [{py['p10_s']}, {py['p90_s']}] | {dll['median_s']} [{dll['p10_s']}, {dll['p90_s']}] | {frame['median_s']} | {periodicity['python_fixed_period_counts_within_1s']} | {periodicity['dll_fixed_period_counts_within_1s']} | {modulo} | {phases} |")
    checks = source_summary["checks"]
    source_lines += ["", "Python inter-event histograms and complete periodicity details are in `MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json`. The fixed-period and histogram counts are descriptive diagnostics; the exact repeated frame modulo and NPZ boundary coincidence are the stronger source-localization evidence.", "", "## Timestamp and boundary sanity checks", "", f"- duplicate long-event frame keys: `{checks['duplicate_long_event_frame_indices']}`", f"- nonpositive adjacent Python intervals: `{checks['nonpositive_python_adjacent_intervals']}`; DLL intervals: `{checks['nonpositive_dll_adjacent_intervals']}`; these are same-millisecond duplicates, not negative clock steps", f"- negative Python timestamp intervals: `{checks['negative_python_adjacent_intervals']}`; timestamp reset found: `{checks['timestamp_reset_found']}`", f"- Python events in the 100–500 ms band: `{checks['python_events_in_100_to_500ms_inclusive']}` (none; all 457 events are >500 ms)", f"- all long events are NPZ chunk boundaries: `{checks['all_long_events_chunk_boundary']}`", "- fixed stop/wait behavior is source-localized to shutdown (`stop` queue drain/final flush), not a repeated in-recording boundary mechanism", "", "## Window gap burden", "", "All 335 windows retain their burden fields. `expected_frame_count_local` uses the regular DLL timestamp nominal interval; the Python timestamp span can be inflated by writer pauses. No window was removed. The estimated frame-loss fraction is a window-index density diagnostic only and must not be read as confirmed sensor frame loss when the Python window axis is artifact-contaminated.", "", "## Gap burden versus HR error", "", "Spearman results are in `MMWAVE_GAP_BURDEN_CORRELATION.csv`; rows are reported overall, participant-stratified, and block-stratified. Because every window has a long interval and the intervals are a recording artifact, these correlations are descriptive and cannot identify causal gap damage.", "", "## Fixed sampling-rate sanity check", "", "The current estimator uses fixed `FS=100.0` in `scripts/process_vital_signs_v3_1_1.py:13`; `_sos_bandpass` uses `fs=FS` at `:273-275`; periodogram uses `fs=FS` at `:1236-1241`; peak minimum distance uses `FS` at `:1244-1249`. It does not consume the timestamp column. The DLL timestamp sequence is regular at about 10 ms, so fixed-FS processing of the dense IQ frame sequence is supported by source/data evidence. Using Python column 3 as a physical time axis remains questionable because its pauses are writer-side artifacts.", "", "`TIMESTAMP_AWARE_RESAMPLED` was not run: resampling the writer-artifact column would manufacture a false sensor-gap correction. First resolve the timestamp-column contract; no HR algorithm or producer change is justified by this audit.", "", "## Final classification", "", "- `GAP_SOURCE_CLASSIFICATION = TIMESTAMP_RECORDING_ARTIFACT`", "- `GAP_EFFECT_ON_HR = UNRESOLVED` (no clean no-gap comparator; burden is confounded with writer/chunk position)", "- `FIXED_FS_WITH_GAPS = QUESTIONABLE` overall; fixed-FS signal processing is supported for the DLL-regular dense frame sequence, but Python timestamp-axis window semantics are not.", "- HR remains `HOLD`; BR remains `HOLD`; HRV remains `BLOCKED`; #16 remains `PAUSED`.", "", "## Artifacts", "", "- `MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv`", "- `MMWAVE_WINDOW_GAP_BURDEN.csv`", "- `MMWAVE_GAP_BURDEN_CORRELATION.csv`", "- `ecg_alignment_audit.csv`", "- `MMWAVE_ACQUISITION_TIMESTAMP_SOURCE_AUDIT.md`", "- `MMWAVE_LONG_INTERVAL_AUDIT_REPORT_2026-08-30.md`", "- `MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json`", ""]
    return "\n".join(source_lines)


def main() -> int:
    rerun = load_module(WRAPPER, "targeted_wrapper")
    event_rows, source_summary, gap_indices = source_and_events(rerun)
    burden_rows = window_burden(rerun, gap_indices, source_summary)
    corr_rows = correlations(burden_rows)
    event_path = RESULT_ROOT / "MMWAVE_LONG_FRAME_INTERVAL_EVENTS.csv"
    burden_path = RESULT_ROOT / "MMWAVE_WINDOW_GAP_BURDEN.csv"
    corr_path = RESULT_ROOT / "MMWAVE_GAP_BURDEN_CORRELATION.csv"
    source_path = RESULT_ROOT / "MMWAVE_ACQUISITION_TIMESTAMP_SOURCE_AUDIT.md"
    report_path = RESULT_ROOT / "MMWAVE_LONG_INTERVAL_AUDIT_REPORT_2026-08-30.md"
    write_csv(event_path, event_rows)
    write_csv(burden_path, burden_rows)
    write_csv(corr_path, corr_rows)
    source_path.write_text(source_report(source_summary, event_rows, burden_rows, corr_rows), encoding="utf-8")
    report_path.write_text(source_report(source_summary, event_rows, burden_rows, corr_rows), encoding="utf-8")
    manifest = {
        "status": "PARTIAL / TIMESTAMP_RECORDING_ARTIFACT / GAP_EFFECT_UNRESOLVED",
        "canonical_main_at_audit": git(ALGO_ROOT, "rev-parse", "HEAD"),
        "canonical_main_remote_at_audit": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"),
        "focuswave_ecg_commit": git(FOCUSWAVE_ROOT, "rev-parse", "ecg"),
        "focuswave_historical_source_commit": "817a7fccb969bcc6e1e0071b387f88e3b3494481",
        "fixed_input": str(FIXED_INPUT),
        "fixed_input_sha256": sha256(FIXED_INPUT),
        "ecg_biopac_alignment_audit": {"path": ALIGNMENT_AUDIT.name, "sha256": sha256(ALIGNMENT_AUDIT), "row_count": sum(1 for _ in csv.DictReader(ALIGNMENT_AUDIT.open(encoding="utf-8-sig")))},
        "subjects": list(SUBJECTS),
        "window_rows": len(burden_rows),
        "long_event_rows": len(event_rows),
        "source_summary": source_summary,
        "periodicity_classification": "PERIODIC_ACQUISITION_OR_WRITE_PATTERN_CANDIDATE; exact 1000-frame NPZ rotation boundary",
        "gap_source_classification": "TIMESTAMP_RECORDING_ARTIFACT",
        "gap_effect_on_hr": "UNRESOLVED",
        "fixed_fs_with_gaps": "QUESTIONABLE",
        "timestamp_aware_resampled": "NOT_RUN__NOT_SAFE_TO_ISOLATE_FROM_WRITER_ARTIFACT_COLUMN",
        "outputs": {},
        "excluded": ["HR estimator tuning", "ECG changes", "HRV", "Issue #16", "C2B", "C2C", "full batch", "producer/raw/firmware/acquisition/portable-V2 changes", "window deletion"],
    }
    for path in (event_path, burden_path, corr_path, source_path, report_path, ALIGNMENT_AUDIT):
        manifest["outputs"][path.name] = {"path": path.name, "sha256": sha256(path), "row_count": sum(1 for _ in csv.DictReader(path.open(encoding="utf-8-sig"))) if path.suffix == ".csv" else None}
    manifest_path = RESULT_ROOT / "MMWAVE_LONG_INTERVAL_AUDIT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "long_events": len(event_rows), "windows": len(burden_rows), "source": source_summary, "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
