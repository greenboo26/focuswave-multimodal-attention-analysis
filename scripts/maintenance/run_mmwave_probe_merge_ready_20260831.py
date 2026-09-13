"""mmWave probe merge-ready adapter with the formal M1 time contract.

This runner keeps the existing HR/BR estimator path but repairs producer-side
time/provenance semantics:
- science clock = timestamp CSV zero-based column 1 (DLL host receive/enqueue);
- formal frame membership = [window_effective_start_unix_ms, probe_onset_unix_ms);
- exact right exclusion at probe onset;
- mmwave_hr_usable_window_fraction = producer course signal_quality.usable_ratio;
- per-probe old-vs-new frame-membership audit is emitted locally.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ALGO_ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
CONTRACT_PATH = ALGO_ROOT / "scripts" / "maintenance" / "mmwave_probe_contract.py"
TIMELINE = Path(
    r"C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave"
    r"\outputs\FocusWave_formal_multimodal_v2_2026-08-30\canonical_probe_timeline.csv"
)
OUT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave")
DATA_ROOTS = (Path(r"E:\正式实验"), Path(r"J:\Data"))
FS = 100.0
COURSE_S = 25.0
BIN_SPACING_M = 0.037
MIN_FRAMES = 200
RUN_ID = "mmwave_probe_merge_ready_contract_m1_20260913"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract_module():
    return load_module(CONTRACT_PATH, "mmwave_probe_contract_m1")


def selector_step(algo, heartbeat: np.ndarray, previous_bpm: float | None) -> dict:
    """Existing selector chain; M1 does not alter estimator selection."""
    peaks = np.asarray(
        algo.detect_peaks_heart_lo(
            heartbeat, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM
        ),
        dtype=int,
    )
    anchor = previous_bpm
    time_bpm, time_quality = algo._robust_time_bpm(peaks / float(FS), anchor)
    time_bpm, time_folded = algo._fold_harmonic(
        time_bpm, anchor, algo.HR_LO_BPM, algo.HR_HI_BPM
    )
    if time_folded:
        time_quality *= 0.85
    selected, frequency_quality = algo._select_spectral_bpm(
        heartbeat,
        FS,
        algo.HR_LO_BPM,
        algo.HR_HI_BPM,
        time_bpm,
        previous_bpm,
        None,
    )
    if time_bpm is not None and selected is not None:
        gap = abs(time_bpm - selected)
        agreement = float(np.exp(-gap / 12.0))
        wt, wf = max(0.05, time_quality), max(0.05, frequency_quality)
        if gap <= algo.HR_TIME_FREQ_WARNING_BPM:
            fused = (wt * time_bpm + wf * selected) / (wt + wf)
            confidence = agreement * np.sqrt(time_quality * frequency_quality)
        else:
            fused = (
                time_bpm
                if (anchor is None or abs(time_bpm - anchor) <= abs(selected - anchor))
                else selected
            )
            confidence = (
                0.10
                * (time_quality if fused == time_bpm else frequency_quality)
                * agreement
            )
    elif time_bpm is not None:
        fused, confidence = time_bpm, 0.45 * time_quality
    elif selected is not None:
        fused, confidence = selected, 0.35 * frequency_quality
    else:
        fused, confidence = None, 0.0
    next_previous = previous_bpm
    if fused is not None and (previous_bpm is None or confidence >= 0.12):
        next_previous = (
            float(fused)
            if previous_bpm is None
            else 0.8 * float(previous_bpm) + 0.2 * float(fused)
        )
    return {
        "spectral_bpm": selected,
        "time_bpm": time_bpm,
        "fused_bpm": fused,
        "confidence": confidence,
        "next_previous_bpm": next_previous,
        "n_peaks": int(len(peaks)),
    }


def producer_usable_ratio(algo, heartbeat: np.ndarray) -> float | None:
    """Return the producer-defined course usable ratio without changing HR outputs."""
    peaks = np.asarray(
        algo.detect_peaks_heart_lo(
            heartbeat, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM
        ),
        dtype=int,
    )
    try:
        course = algo.estimate_hr_time_course(
            heartbeat=heartbeat,
            peaks=peaks,
            fs=FS,
            reference_bpm=None,
            window_s=COURSE_S,
            step_s=5.0,
        )
    except Exception:
        return None
    value = course.get("signal_quality", {}).get("usable_ratio")
    if value is None:
        return None
    value = float(value)
    if not np.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"producer usable_ratio outside [0,1]: {value}")
    return value


def find_session_root(session: str) -> Path | None:
    for root in DATA_ROOTS:
        candidate = root / f"{session}_" / "mmwave"
        if candidate.is_dir():
            return candidate
    return None


def load_timestamps(mmw_root: Path) -> np.ndarray:
    path = next(mmw_root.glob("*_mmwave_timestamps.csv"), None)
    if path is None:
        raise FileNotFoundError(f"{mmw_root}: no timestamps csv")
    values = np.atleast_2d(np.loadtxt(path, delimiter=",", dtype=np.int64))
    if values.shape[1] < 3:
        raise ValueError(f"{path}: fewer than 3 columns")
    return values[:, :3]


def load_npz_files(mmw_root: Path, session: str) -> list[Path]:
    base = mmw_root / f"{session}_mmwave_datacube.npz"
    parts = sorted(mmw_root.glob(f"{session}_mmwave_datacube_part*.npz"))
    files = ([base] if base.exists() else []) + parts
    if not files:
        raise FileNotFoundError(f"{mmw_root}: no NPZ files")
    return files


def slice_iq(files: list[Path], start: int, end: int) -> np.ndarray:
    chunks: list[np.ndarray] = []
    cursor = 0
    for path in files:
        with np.load(path) as data:
            keys = sorted(key for key in data.files if key.startswith("tx"))
            if not keys:
                raise RuntimeError(f"{path}: no tx arrays")
            n = int(data[keys[0]].shape[0])
            if cursor + n <= start:
                cursor += n
                continue
            if cursor >= end:
                break
            lo = max(0, start - cursor)
            hi = min(n, end - cursor)
            if lo < hi:
                chunks.append(
                    np.stack([data[key][lo:hi] for key in keys], axis=-1).astype(
                        np.complex64
                    )
                )
            cursor += n
    if not chunks:
        raise RuntimeError(f"No frames for {start}:{end}")
    return np.concatenate(chunks, axis=0)


def process_probe(
    algo,
    row: dict,
    files: list[Path],
    timestamps: np.ndarray,
    previous_by_block: dict,
    *,
    frame_audit_rows: list[dict] | None = None,
    contract=None,
) -> dict:
    """One canonical probe row -> merge-ready row under the frozen M1 contract."""
    contract = contract or load_contract_module()
    block_id = row["block_id"]
    formal = contract.select_frame_window(row, timestamps)
    legacy = contract.select_legacy_frame_window(row, timestamps)
    if frame_audit_rows is not None:
        frame_audit_rows.append(contract.frame_audit_row(row, formal, legacy))

    i0, i1 = formal.i0, formal.i1_exclusive
    n_frames = formal.n_frames
    science_ts = timestamps[:, contract.SCIENCE_TIMESTAMP_COL].astype(np.int64)
    ts_window = science_ts[i0:i1]

    if n_frames > 1:
        intervals = np.diff(ts_window)
        median_interval_ms = float(np.median(intervals)) if len(intervals) else None
    else:
        median_interval_ms = None
    duration_ms = formal.probe_onset_unix_ms - formal.effective_start_unix_ms
    expected_frames = duration_ms / median_interval_ms if median_interval_ms else None
    coverage = n_frames / expected_frames if expected_frames else None
    coverage = (
        float(min(max(coverage, 0.0), 1.0)) if coverage is not None else None
    )

    out = dict(row)
    if n_frames < MIN_FRAMES:
        out.update(
            {
                "mmwave_state": "QC_FAIL",
                "mmwave_observed": True,
                "mmwave_missing_reason": "insufficient_frames",
                "mmwave_loadable": True,
                "mmwave_timestamp_coverage_fraction": coverage,
            }
        )
        return out

    try:
        iq = slice_iq(files, i0, i1)
    except Exception:
        out.update(
            {
                "mmwave_state": "STRUCTURAL_MISSING",
                "mmwave_observed": False,
                "mmwave_missing_reason": "npz_slice_failed",
                "mmwave_loadable": False,
            }
        )
        return out

    iq_fd = algo._as_range_cube(iq)
    bin_power_acc = np.mean(np.abs(iq_fd) ** 2, axis=0)
    try:
        br_ch, br_bin, hr_ch, hr_bin, _ = algo.select_separate_channels_bins(
            bin_power_acc, iq_fd, iq_fd.shape[0]
        )
    except Exception:
        out.update(
            {
                "mmwave_state": "QC_FAIL",
                "mmwave_observed": True,
                "mmwave_missing_reason": "no_valid_bin_channel_candidates",
                "mmwave_loadable": True,
                "mmwave_timestamp_coverage_fraction": coverage,
            }
        )
        return out

    disp = algo.extract_displacement(iq_fd, hr_bin, hr_ch)
    heartbeat = algo._sos_bandpass(disp, algo.HR_LO_HZ, algo.HR_HI_HZ)

    previous = previous_by_block.get(block_id)
    step30 = selector_step(algo, heartbeat, previous)
    n25 = int(COURSE_S * FS)
    step25 = (
        selector_step(algo, heartbeat[-n25:], previous)
        if len(heartbeat) >= n25
        else None
    )
    hr_step = step25 if step25 is not None else step30
    usable_ratio = producer_usable_ratio(algo, heartbeat)

    phi_br = np.unwrap(np.angle(iq_fd[:, br_bin, br_ch]))
    disp_br = algo.WAVELENGTH_MM * phi_br / (4 * np.pi)
    try:
        _, br_freq, _, _ = algo._select_breath_candidate(disp_br)
        br_bpm = br_freq * 60.0 if br_freq is not None else None
    except Exception:
        br_bpm = None

    phi_hr = np.unwrap(np.angle(iq_fd[:, hr_bin, hr_ch]))
    stability, _ = algo._phase_stability_score(phi_hr)
    motion_proxy = float(np.std(np.diff(disp))) if len(disp) > 1 else None

    out.update(
        {
            "mmwave_state": "OBSERVED",
            "mmwave_observed": True,
            "mmwave_missing_reason": None,
            "mmwave_loadable": True,
            "mmwave_timestamp_coverage_fraction": round(coverage, 4)
            if coverage is not None
            else None,
            "mmwave_hr_freq_bpm_median": round(hr_step["spectral_bpm"], 3)
            if hr_step["spectral_bpm"] is not None
            else None,
            "mmwave_hr_time_bpm_median": round(hr_step["time_bpm"], 3)
            if hr_step["time_bpm"] is not None
            else None,
            "mmwave_hr_fused_bpm_median": round(hr_step["fused_bpm"], 3)
            if hr_step["fused_bpm"] is not None
            else None,
            "mmwave_breath_rate_breaths_per_min_median": round(br_bpm, 3)
            if br_bpm is not None
            else None,
            "mmwave_hr_usable_window_fraction": round(usable_ratio, 4)
            if usable_ratio is not None
            else None,
            "mmwave_hr_mean_confidence": round(hr_step["confidence"], 4)
            if hr_step["confidence"] is not None
            else None,
            "mmwave_selected_bin_mode": int(hr_bin),
            "mmwave_selected_channel_mode": int(hr_ch),
            "mmwave_selected_bin_distance_proxy_m": round(
                float(hr_bin) * BIN_SPACING_M, 3
            ),
            "mmwave_target_switch_rate": None,
            "mmwave_phase_stability_median": round(stability, 4)
            if stability is not None
            else None,
            "mmwave_motion_proxy_median": round(motion_proxy, 6)
            if motion_proxy is not None
            else None,
            "mmwave_ibi_median_ms": None,
            "mmwave_rmssd_ms": None,
            "mmwave_sdnn_ms": None,
        }
    )
    previous_by_block[block_id] = hr_step["next_previous_bpm"]
    return out


def build_output_fields(timeline: Path = TIMELINE) -> list[str]:
    with timeline.open(encoding="utf-8-sig", newline="") as handle:
        timeline_fields = list(csv.DictReader(handle).fieldnames or [])
    mmwave_fields = [
        "mmwave_state",
        "mmwave_observed",
        "mmwave_missing_reason",
        "mmwave_source_run_id",
        "mmwave_source_commit",
        "mmwave_loadable",
        "mmwave_timestamp_coverage_fraction",
        "mmwave_hr_freq_bpm_median",
        "mmwave_hr_time_bpm_median",
        "mmwave_hr_fused_bpm_median",
        "mmwave_breath_rate_breaths_per_min_median",
        "mmwave_hr_usable_window_fraction",
        "mmwave_hr_mean_confidence",
        "mmwave_selected_bin_mode",
        "mmwave_selected_channel_mode",
        "mmwave_selected_bin_distance_proxy_m",
        "mmwave_target_switch_rate",
        "mmwave_phase_stability_median",
        "mmwave_motion_proxy_median",
        "mmwave_ibi_median_ms",
        "mmwave_rmssd_ms",
        "mmwave_sdnn_ms",
    ]
    return timeline_fields + [field for field in mmwave_fields if field not in timeline_fields]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_provenance() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            return subprocess.check_output(
                ["git", "-C", str(ALGO_ROOT), *args],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return None

    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    status = git("status", "--porcelain")
    clean = status == "" if status is not None else False
    return {
        "source_commit": head,
        "source_branch": branch,
        "source_worktree_clean": clean,
        "source_code_provenance_closed_for_this_run": bool(head and clean),
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", nargs="*", default=None)
    parser.add_argument("--timeline", type=Path, default=TIMELINE)
    parser.add_argument("--output-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    contract = load_contract_module()
    algo = load_module(PRODUCER, "producer_merge_ready_m1")
    rows = list(csv.DictReader(args.timeline.open(encoding="utf-8-sig")))
    sessions = sorted({row["session_id"] for row in rows})
    if args.sessions:
        sessions = [session for session in sessions if session in args.sessions]

    print(
        f"处理 {len(sessions)} sessions / "
        f"{sum(1 for row in rows if row['session_id'] in sessions)} probe 窗口"
    )
    out_rows: list[dict] = []
    frame_audit_rows: list[dict] = []

    for session in sessions:
        mmw_root = find_session_root(session)
        session_rows = [row for row in rows if row["session_id"] == session]
        previous_by_block: dict[str, float | None] = {}

        if mmw_root is None:
            for row in session_rows:
                base = dict(row)
                base.update(
                    {
                        "mmwave_state": "STRUCTURAL_MISSING",
                        "mmwave_observed": False,
                        "mmwave_missing_reason": "no_mmwave_directory",
                        "mmwave_loadable": False,
                    }
                )
                out_rows.append(base)
                frame_audit_rows.append(
                    contract.frame_audit_stub(
                        row, "SOURCE_UNAVAILABLE", "no_mmwave_directory"
                    )
                )
            continue

        try:
            timestamps = load_timestamps(mmw_root)
            files = load_npz_files(mmw_root, session)
        except Exception as exc:
            for row in session_rows:
                base = dict(row)
                base.update(
                    {
                        "mmwave_state": "STRUCTURAL_MISSING",
                        "mmwave_observed": False,
                        "mmwave_missing_reason": f"load_failed:{type(exc).__name__}",
                        "mmwave_loadable": False,
                    }
                )
                out_rows.append(base)
                frame_audit_rows.append(
                    contract.frame_audit_stub(
                        row,
                        "SOURCE_MALFORMED",
                        f"load_failed:{type(exc).__name__}",
                    )
                )
            continue

        for row in session_rows:
            out_rows.append(
                process_probe(
                    algo,
                    row,
                    files,
                    timestamps,
                    previous_by_block,
                    frame_audit_rows=frame_audit_rows,
                    contract=contract,
                )
            )

    args.output_root.mkdir(parents=True, exist_ok=True)
    provenance = git_provenance()
    for row in out_rows:
        row["mmwave_source_run_id"] = RUN_ID
        row["mmwave_source_commit"] = provenance["source_commit"]

    fields = build_output_fields(args.timeline)
    out_csv = args.output_root / "mmwave_probe_merge_ready.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)

    frame_audit = args.output_root / "mmwave_probe_frame_membership_audit.csv"
    write_rows(frame_audit, frame_audit_rows)

    state_counts: dict[str, int] = {}
    for row in out_rows:
        state = str(row.get("mmwave_state", "?"))
        state_counts[state] = state_counts.get(state, 0) + 1

    source_files = {
        "adapter": Path(__file__).resolve(),
        "contract": CONTRACT_PATH,
        "producer": PRODUCER,
    }
    manifest = {
        "schema": "mmwave_probe_merge_ready_v1",
        "run_id": RUN_ID,
        "rows": len(out_rows),
        "sessions": len(sessions),
        "state_counts": state_counts,
        "physiology_role": "SUPPORTING_HOLD / NOT_PRIMARY",
        "hrv_fields": "EXCLUDE / null",
        "hr_estimator": "unchanged_full_selector_chain_25s_course_fused",
        "br_estimator": "unchanged_select_separate_channels_bins + _select_breath_candidate",
        "science_clock_source": contract.SCIENCE_CLOCK_SOURCE,
        "science_timestamp_column_index": contract.SCIENCE_TIMESTAMP_COL,
        "qc_timestamp_column_index": contract.QC_TIMESTAMP_COL,
        "window_contract": contract.WINDOW_CONTRACT,
        "right_endpoint_exclusive": True,
        "effective_start_used_for_slicing": True,
        "hr_usable_window_fraction_semantics": "producer estimate_hr_time_course signal_quality.usable_ratio",
        "frame_membership_audit": str(frame_audit),
        "timeline_source": str(args.timeline),
        **provenance,
        "source_hashes_sha256": {
            name: sha256(path) for name, path in source_files.items()
        },
        "models_trained": False,
        "q1_q2_used_for_acceptance": False,
        "snapshot_v2_formed": False,
    }
    manifest_path = args.output_root / "mmwave_probe_merge_ready_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"输出: {out_csv}")
    print(f"frame audit: {frame_audit}")
    print(f"manifest: {manifest_path}")
    print(f"状态分布: {state_counts}")


if __name__ == "__main__":
    main()
