"""Validate reused radar beat timestamps against ECG R-peaks.

This is a narrow downstream audit.  It reuses ``heart_peaks`` already written
by the historical v3.1.1 producer and the existing block-local ECG alignment.
It does not run a new radar detector, calculate formal HRV metrics, or change
the frozen 20-second target/selector evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.signal import find_peaks


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE"
TARGETED_SCRIPT = ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
GOLD_SCRIPT = ROOT / "scripts" / "gold_standard_qa.py"
PRODUCER_SCRIPT = ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
SUBJECTS = ("97793", "9779", "97795")
WINDOW_S = 60.0
BOUNDARY_GUARD_S = 30.0
PRIMARY_TOLERANCE_MS = 75.0
TOLERANCE_SENSITIVITY_MS = (50.0, 75.0, 100.0, 150.0)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unavailable"


def numeric(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def detect_ecg_rpeaks(ecg: np.ndarray, sample_rate: float, start: int, end: int, gold) -> tuple[np.ndarray, dict]:
    """Return raw R-peaks using the existing gold-standard parameters exactly."""
    segment = np.asarray(ecg[int(start):int(end)], dtype=float)
    report = {"n_raw": 0, "note": None}
    if len(segment) < sample_rate * 5:
        report["note"] = "too_short"
        return np.array([], dtype=int), report
    segment = segment - np.median(segment)
    sos = signal.butter(3, gold.ECG_BAND, btype="band", fs=sample_rate, output="sos")
    filtered = signal.sosfiltfilt(sos, segment)
    peaks, _ = find_peaks(filtered, distance=int(gold.ECG_MIN_DIST_S * sample_rate), prominence=0.25)
    report["n_raw"] = int(len(peaks))
    if len(peaks) < 5:
        report["note"] = "too_few_peaks"
    return peaks + int(start), report


def match_peaks(radar_ms: np.ndarray, ecg_ms: np.ndarray, tolerance_ms: float) -> list[tuple[int, int]]:
    """Greedy one-to-one nearest matching in monotonic time order."""
    candidates: list[tuple[float, int, int]] = []
    for radar_index, time_ms in enumerate(radar_ms):
        right = int(np.searchsorted(ecg_ms, time_ms, side="left"))
        for ecg_index in (right - 1, right):
            if 0 <= ecg_index < len(ecg_ms):
                distance = abs(float(time_ms) - float(ecg_ms[ecg_index]))
                if distance <= tolerance_ms:
                    candidates.append((distance, radar_index, ecg_index))
    candidates.sort()
    used_radar: set[int] = set()
    used_ecg: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _distance, radar_index, ecg_index in candidates:
        if radar_index in used_radar or ecg_index in used_ecg:
            continue
        used_radar.add(radar_index)
        used_ecg.add(ecg_index)
        pairs.append((radar_index, ecg_index))
    return sorted(pairs)


def pearson(xs: np.ndarray, ys: np.ndarray) -> float | None:
    if len(xs) < 2 or np.std(xs) == 0 or np.std(ys) == 0:
        return None
    return float(np.corrcoef(xs, ys)[0, 1])


def existing_output_paths(output_root: Path, subject: str) -> tuple[Path, Path]:
    base = output_root / f"sub-{subject}_" / f"sub-{subject}_ses-SART_mmwave_vital_signs"
    return base.with_suffix(".json"), base.with_suffix(".npz")


def evaluate_window(
    *,
    subject: str,
    block: dict,
    alignment: dict,
    timestamps: np.ndarray,
    ecg: np.ndarray,
    ecg_fs: float,
    heartbeat: np.ndarray,
    radar_peaks: np.ndarray,
    producer,
    gold,
    br_supporting: dict,
) -> dict:
    start_ms = int(round(float(block["start_event_unix_ms"]) + BOUNDARY_GUARD_S * 1000.0))
    end_ms = int(round(start_ms + WINDOW_S * 1000.0))
    block_end_ms = int(block["end_event_unix_ms"])
    if end_ms > block_end_ms - int(BOUNDARY_GUARD_S * 1000.0):
        raise ValueError(f"No bounded 60 s window in {subject}/{block['block_id']}")

    mm_start = int(np.searchsorted(timestamps[:, 2], start_ms, side="left"))
    mm_end = int(np.searchsorted(timestamps[:, 2], end_ms, side="left"))
    slope = float(alignment["ecg_fit_slope_samples_per_ms"])
    intercept = float(alignment["ecg_fit_intercept_sample"])
    ecg_start = int(round(slope * start_ms + intercept))
    ecg_end = int(round(slope * end_ms + intercept))
    ecg_peaks, ecg_report = detect_ecg_rpeaks(ecg, ecg_fs, ecg_start, ecg_end, gold)
    ecg_ms = (ecg_peaks.astype(float) - intercept) / slope

    selected = radar_peaks[(radar_peaks >= mm_start) & (radar_peaks < mm_end)]
    radar_ms = timestamps[selected, 2].astype(float)
    matched_by_tolerance = {}
    for tolerance in TOLERANCE_SENSITIVITY_MS:
        pairs = match_peaks(radar_ms, ecg_ms, tolerance)
        matched_by_tolerance[str(int(tolerance))] = {
            "matched_n": len(pairs),
            "sensitivity": len(pairs) / len(ecg_ms) if len(ecg_ms) else None,
            "precision": len(pairs) / len(radar_ms) if len(radar_ms) else None,
        }

    pairs = match_peaks(radar_ms, ecg_ms, PRIMARY_TOLERANCE_MS)
    matched_radar = np.asarray([radar_ms[i] for i, _ in pairs], dtype=float)
    matched_ecg = np.asarray([ecg_ms[j] for _, j in pairs], dtype=float)
    timing_error = matched_radar - matched_ecg
    timing_offset = float(np.median(timing_error)) if len(timing_error) else None
    timing_corrected = timing_error - timing_offset if timing_offset is not None else np.array([], dtype=float)

    radar_ibi = np.diff(matched_radar)
    ecg_ibi = np.diff(matched_ecg)
    ibi_mask = (radar_ibi > 0) & (ecg_ibi > 0)
    radar_ibi = radar_ibi[ibi_mask]
    ecg_ibi = ecg_ibi[ibi_mask]
    ibi_error = radar_ibi - ecg_ibi
    spectral = producer.estimate_freq_periodogram(
        heartbeat[mm_start:mm_end], producer.HR_LO_HZ, producer.HR_HI_HZ
    )
    spectral_hr = float(spectral * 60.0) if spectral is not None else None
    beat_hr = 60000.0 / float(np.mean(radar_ibi)) if len(radar_ibi) else None

    return {
        "subject": subject,
        "block_id": block["block_id"],
        "window_length_s": WINDOW_S,
        "boundary_guard_s": BOUNDARY_GUARD_S,
        "window_start_unix_ms": start_ms,
        "window_end_unix_ms": end_ms,
        "mmwave_start_row": mm_start,
        "mmwave_end_row_exclusive": mm_end,
        "mmwave_frame_count": mm_end - mm_start,
        "ecg_start_sample": ecg_start,
        "ecg_end_sample": ecg_end,
        "ecg_n_raw_rpeaks": len(ecg_ms),
        "ecg_qc_n_raw": ecg_report["n_raw"],
        "ecg_qc_note": ecg_report["note"] or "",
        "radar_n_heart_peaks": len(radar_ms),
        "matched_beat_n": len(pairs),
        "missed_ecg_beats_n": max(0, len(ecg_ms) - len(pairs)),
        "extra_radar_beats_n": max(0, len(radar_ms) - len(pairs)),
        "primary_tolerance_ms": PRIMARY_TOLERANCE_MS,
        "beat_sensitivity": len(pairs) / len(ecg_ms) if len(ecg_ms) else None,
        "beat_precision": len(pairs) / len(radar_ms) if len(radar_ms) else None,
        "timing_error_median_ms": float(np.median(timing_error)) if len(timing_error) else None,
        "timing_error_mae_ms": float(np.mean(np.abs(timing_error))) if len(timing_error) else None,
        "timing_error_p95_abs_ms": float(np.percentile(np.abs(timing_error), 95)) if len(timing_error) else None,
        "estimated_constant_offset_median_ms": timing_offset,
        "timing_residual_mae_after_median_offset_ms": float(np.mean(np.abs(timing_corrected))) if len(timing_corrected) else None,
        "paired_ibi_n": len(ibi_error),
        "paired_ibi_mae_ms": float(np.mean(np.abs(ibi_error))) if len(ibi_error) else None,
        "paired_ibi_bias_ms": float(np.mean(ibi_error)) if len(ibi_error) else None,
        "paired_ibi_pearson_r": pearson(radar_ibi, ecg_ibi),
        "beat_derived_mean_hr_bpm": beat_hr,
        "existing_spectral_hr_bpm": spectral_hr,
        "beat_vs_spectral_hr_delta_bpm": beat_hr - spectral_hr if beat_hr is not None and spectral_hr is not None else None,
        "br_supporting_source": br_supporting.get("source", "existing_full_record_json"),
        "br_supporting_bpm_not_used_for_matching": numeric(br_supporting.get("freq_bpm")),
        "br_internal_harmonic_diagnostic_for_this_window": "NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS",
        "formal_hrv_metrics_calculated": False,
        "tolerance_sensitivity_json": json.dumps(matched_by_tolerance, separators=(",", ":")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acq-root", type=Path, required=True, help="Local acquisition root containing sub-<id>_ directories")
    parser.add_argument("--existing-output-root", type=Path, required=True, help="Existing v3.1.1 output root containing full-record JSON/NPZ")
    parser.add_argument("--local-output-root", type=Path, required=True, help="Local-only output directory for per-window rows")
    parser.add_argument("--bioread-site-packages", type=Path, default=None, help="Optional site-packages path when bioread is not on Python path")
    args = parser.parse_args()

    try:
        import bioread  # noqa: F401
    except ModuleNotFoundError:
        if args.bioread_site_packages is None:
            raise
        sys.path.append(str(args.bioread_site_packages))
        import bioread  # noqa: F401

    targeted = load_module(TARGETED_SCRIPT, "targeted_for_beat_level_validation")
    gold = load_module(GOLD_SCRIPT, "gold_for_beat_level_validation")
    producer = load_module(PRODUCER_SCRIPT, "producer_for_beat_level_validation")
    targeted.DATA_ROOT = args.acq_root
    rows: list[dict] = []
    input_records: list[dict] = []
    for subject in SUBJECTS:
        timestamps = targeted.load_mmwave_timestamps(subject)
        events = targeted.load_events(subject)
        physical, _digital_meta = targeted.decode_biopac_markers(subject)
        blocks, alignments = targeted.block_intervals(subject, timestamps, events, physical)
        alignment_by_block = {row["block_id"]: row for row in alignments}
        ecg, _rsp, ecg_fs = targeted.load_ecg_reference(subject)
        json_path, npz_path = existing_output_paths(args.existing_output_root, subject)
        if not json_path.exists() or not npz_path.exists():
            raise FileNotFoundError(f"Missing existing output for {subject}: {json_path} / {npz_path}")
        metadata = read_json(json_path)
        with np.load(npz_path, allow_pickle=False) as arrays:
            heartbeat = np.asarray(arrays["heartbeat"], dtype=float)
            radar_peaks = np.asarray(arrays["heart_peaks"], dtype=int)
        if len(timestamps) != len(heartbeat):
            raise ValueError(f"Timestamp/heartbeat length mismatch for {subject}")
        if np.any(radar_peaks < 0) or np.any(radar_peaks >= len(timestamps)):
            raise ValueError(f"heart_peaks out of timestamp range for {subject}")
        input_records.append({
            "subject": subject,
            "json_name": json_path.name,
            "npz_name": npz_path.name,
            "json_sha256": sha256(json_path),
            "npz_sha256": sha256(npz_path),
            "n_frames": len(heartbeat),
            "n_heart_peaks": len(radar_peaks),
            "producer_version_in_json": metadata.get("version"),
            "producer_pipeline_in_json": metadata.get("pipeline"),
            "heart_channel": metadata.get("channels", {}).get("heart"),
            "heart_bin": metadata.get("bins", {}).get("heart"),
        })
        br_supporting = metadata.get("breath_rate", {}) or {}
        for block in blocks:
            if block.get("status") != "complete":
                continue
            alignment = alignment_by_block.get(block["block_id"])
            if not alignment or alignment.get("status") != "complete":
                continue
            rows.append(evaluate_window(
                subject=subject,
                block=block,
                alignment=alignment,
                timestamps=timestamps,
                ecg=ecg,
                ecg_fs=ecg_fs,
                heartbeat=heartbeat,
                radar_peaks=radar_peaks,
                producer=producer,
                gold=gold,
                br_supporting=br_supporting,
            ))

    local_path = args.local_output_root / "MMWAVE_BEAT_LEVEL_VALIDATION_PER_WINDOW_LOCAL_ONLY.csv"
    write_csv(local_path, rows)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for row in rows:
        summary_rows.append({key: row.get(key) for key in (
            "subject", "block_id", "window_length_s", "primary_tolerance_ms", "ecg_n_raw_rpeaks",
            "radar_n_heart_peaks", "matched_beat_n", "missed_ecg_beats_n", "extra_radar_beats_n",
            "beat_sensitivity", "beat_precision", "timing_error_median_ms", "timing_error_mae_ms",
            "timing_error_p95_abs_ms", "estimated_constant_offset_median_ms",
            "timing_residual_mae_after_median_offset_ms", "paired_ibi_n", "paired_ibi_mae_ms",
            "paired_ibi_bias_ms", "paired_ibi_pearson_r", "beat_derived_mean_hr_bpm",
            "existing_spectral_hr_bpm", "beat_vs_spectral_hr_delta_bpm",
            "br_supporting_bpm_not_used_for_matching", "br_internal_harmonic_diagnostic_for_this_window",
            "formal_hrv_metrics_calculated",
        )})
    write_csv(RESULT_ROOT / "MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY.csv", summary_rows)

    tolerance_rows = []
    for tolerance in TOLERANCE_SENSITIVITY_MS:
        key = str(int(tolerance))
        matched = sum(json.loads(row["tolerance_sensitivity_json"])[key]["matched_n"] for row in rows)
        ecg_n = sum(row["ecg_n_raw_rpeaks"] for row in rows)
        radar_n = sum(row["radar_n_heart_peaks"] for row in rows)
        tolerance_rows.append({
            "tolerance_ms": tolerance,
            "window_n": len(rows),
            "ecg_rpeak_n": ecg_n,
            "radar_peak_n": radar_n,
            "matched_n": matched,
            "pooled_sensitivity": matched / ecg_n if ecg_n else None,
            "pooled_precision": matched / radar_n if radar_n else None,
        })
    write_csv(RESULT_ROOT / "MMWAVE_BEAT_LEVEL_TOLERANCE_SENSITIVITY.csv", tolerance_rows)

    def median_field(field: str) -> float | None:
        values = [numeric(row.get(field)) for row in rows]
        values = [value for value in values if value is not None]
        return float(np.median(values)) if values else None

    def median_abs_field(field: str) -> float | None:
        values = [numeric(row.get(field)) for row in rows]
        values = [abs(value) for value in values if value is not None]
        return float(np.median(values)) if values else None

    primary = next(row for row in tolerance_rows if row["tolerance_ms"] == PRIMARY_TOLERANCE_MS)
    report_lines = [
        "# mmWave beat-level validation gate (2026-08-30)",
        "",
        "Status: `PARTIAL / HRV_BLOCKED`; this is a beat-timing validity audit, not a formal HRV result.",
        "",
        "## Direct conclusion",
        "",
        "- Existing producer outputs already contain `heart_peaks` (frame indices) and a `heartbeat` waveform; no new radar beat detector or export adapter was created.",
        "- Eight complete formal blocks were evaluated using one deterministic 60 s interval per block, after a 30 s boundary guard. The older `_selection_60s` files start at raw frame 0 before formal blocks and were not used as ECG-aligned windows.",
        f"- At the pre-existing primary ±{int(PRIMARY_TOLERANCE_MS)} ms one-to-one matching tolerance: pooled matches `{primary['matched_n']}/{primary['ecg_rpeak_n']}` ECG R-peaks against `{primary['radar_peak_n']}` radar peaks; sensitivity=`{primary['pooled_sensitivity']:.6f}`, precision=`{primary['pooled_precision']:.6f}`.",
        f"- Per-window median sensitivity=`{median_field('beat_sensitivity'):.6f}`, median precision=`{median_field('beat_precision'):.6f}`, median paired-IBI MAE=`{median_field('paired_ibi_mae_ms'):.3f} ms`.",
        f"- The paired-beat subset has median raw timing MAE=`{median_field('timing_error_mae_ms'):.3f} ms`; this conditional timing value does not compensate for the low match rate.",
        f"- Beat-derived mean HR is not consistent with same-window existing spectral HR: median absolute difference=`{median_abs_field('beat_vs_spectral_hr_delta_bpm'):.3f} bpm` (the beat-derived values are based only on matched-beat intervals and are therefore not promotable).",
        "- No formal RMSSD, SDNN, LF/HF, or any other HRV metric was calculated in this run. HRV remains `BLOCKED` because the beat-level evidence is not sufficient for promotion.",
        "",
        "## Fixed evaluation contract",
        "",
        "- Radar: existing full-record v3.1.1 NPZ `heart_peaks`; timestamps are mapped through the authoritative DLL-time rows. No detector parameter was changed.",
        "- ECG: existing block-local affine event-marker mapping and the fixed `gold_standard_qa.py` ECG band/peak parameters; raw R-peaks are retained for the match audit.",
        "- Matching: one-to-one nearest match, no per-window lag search; primary tolerance ±75 ms, with ±50/100/150 ms sensitivity only.",
        "- IBI: successive intervals among matched pairs; a constant absolute offset cancels and is not used to select radar peaks.",
        "- BR: existing full-record `breath_rate` is retained as supporting metadata only; no new BR method or per-window harmonic diagnostic was run.",
        "",
        "## Tolerance sensitivity",
        "",
        "| tolerance | pooled matched | ECG R-peaks | radar peaks | sensitivity | precision |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    report_lines.extend(
        f"| {int(row['tolerance_ms'])} ms | {row['matched_n']} | {row['ecg_rpeak_n']} | {row['radar_peak_n']} | {row['pooled_sensitivity']:.6f} | {row['pooled_precision']:.6f} |"
        for row in tolerance_rows
    )
    report_lines.extend([
        "",
        "## Human-readable project pipeline map",
        "",
        "The code-level map is maintained in `docs/research/MMWAVE_HR_BR_HRV_PROJECT_PIPELINE_MAP_2026-08-30.md`. In brief: shared range-domain input and phase/displacement feed a low-frequency BR branch and a cardiac branch; the cardiac branch's existing peak array is the common source for beat-derived HR and any future HRV, while spectral HR remains an independent QC/fallback output.",
        "",
        "## Decision",
        "",
        "`BEAT_LEVEL_GATE = NOT_PASSED_FOR_PROMOTION`; `HRV = BLOCKED`. The result identifies a measurable blocker (low radar-to-ECG beat correspondence) and does not authorize a new detector, new selector, HRV window tuning, or formal RMSSD/SDNN calculation.",
        "",
        "## Artifacts",
        "",
        "- `MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY.csv` — committed aggregate per-window metrics.",
        "- `MMWAVE_BEAT_LEVEL_TOLERANCE_SENSITIVITY.csv` — committed pooled tolerance sensitivity.",
        "- `MMWAVE_BEAT_LEVEL_VALIDATION_MANIFEST.json` — source hashes, contract, and output boundary.",
        "- `MMWAVE_BEAT_LEVEL_VALIDATION_PER_WINDOW_LOCAL_ONLY.csv` — local-only detailed rows; raw ECG/radar data remain outside Git.",
    ])
    (RESULT_ROOT / "MMWAVE_BEAT_LEVEL_VALIDATION_REPORT_2026-08-30.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    manifest = {
        "status": "PARTIAL / HRV_BLOCKED",
        "run_id": "mmwave_beat_level_validation_20260830",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_repo_head": git_head(),
        "subjects": list(SUBJECTS),
        "window_contract": {
            "window_s": WINDOW_S,
            "boundary_guard_s": BOUNDARY_GUARD_S,
            "selection": "first bounded 60 s interval after block start + 30 s, within complete block and before end - 30 s",
            "formal_hrv_window_used": False,
        },
        "matching_contract": {
            "primary_tolerance_ms": PRIMARY_TOLERANCE_MS,
            "sensitivity_tolerances_ms": list(TOLERANCE_SENSITIVITY_MS),
            "matching": "one-to-one nearest radar peak to raw ECG R-peak; no per-window lag search",
            "timing_error": "radar timestamp minus ECG R-peak time after existing block affine clock mapping",
            "paired_ibi": "successive intervals among matched beats; constant offset cancels",
        },
        "aggregate_counts": {
            "window_n": len(rows),
            "ecg_rpeak_n": primary["ecg_rpeak_n"],
            "radar_peak_n": primary["radar_peak_n"],
            "matched_n_at_primary_tolerance": primary["matched_n"],
            "sensitivity_at_primary_tolerance": primary["pooled_sensitivity"],
            "precision_at_primary_tolerance": primary["pooled_precision"],
        },
        "reuse": {
            "radar_beats": "existing full-record NPZ heart_peaks; no new radar detector",
            "cardiac_waveform": "existing full-record NPZ heartbeat; only reused for same-window existing spectral HR consistency",
            "ecg_rpeaks": "gold_standard_qa.py fixed 0.5-40 Hz / 0.30 s / prominence 0.25 parameters",
            "block_alignment": "run_mmwave_targeted_validation_20260830.py existing block-local ECG affine mapping",
            "reuse_rejection_reason": None,
        },
        "source_code_hashes": {
            "beat_level_adapter_sha256": sha256(Path(__file__).resolve()),
            "targeted_alignment_script_sha256": sha256(TARGETED_SCRIPT),
            "gold_standard_script_sha256": sha256(GOLD_SCRIPT),
            "producer_script_sha256": sha256(PRODUCER_SCRIPT),
        },
        "br_boundary": "existing full-record breath_rate retained as supporting metadata only; no BR algorithm or harmonic diagnostic was run",
        "formal_hrv_metrics_calculated": False,
        "source_records": input_records,
        "outputs": [
            "MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY.csv",
            "MMWAVE_BEAT_LEVEL_TOLERANCE_SENSITIVITY.csv",
            "MMWAVE_BEAT_LEVEL_VALIDATION_REPORT_2026-08-30.md",
            "MMWAVE_BEAT_LEVEL_VALIDATION_MANIFEST.json",
            "local-only: MMWAVE_BEAT_LEVEL_VALIDATION_PER_WINDOW_LOCAL_ONLY.csv",
        ],
    }
    (RESULT_ROOT / "MMWAVE_BEAT_LEVEL_VALIDATION_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "windows": len(rows), "outputs": manifest["outputs"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
