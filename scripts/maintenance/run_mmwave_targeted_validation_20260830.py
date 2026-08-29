"""Small, diagnostic-only mmWave continuity and harmonic A/B/C validation.

This script intentionally does not alter the producer or pass ECG/RSP into it.
It reuses the current target-selection functions on three prespecified sessions
and reads the existing current-algorithm 60-second outputs for A.  RSP is read
only for C validation labels.  The output is a diagnostic contract, not a new
production algorithm or a full formal batch.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


ALGO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_ALGO_ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DATA_ROOT = Path(r"D:\acq_mmwave_data")
EXTERNAL_OUTPUT_ROOT = EXTERNAL_ALGO_ROOT / "output" / "20_生理金标准验证" / "05_毫米波参照_FAST"
PILOT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1")
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FORMAL_BIN_SPACING_M = 0.037
WINDOWS = [(0, 2000), (1000, 3000), (2000, 4000), (3000, 5000), (4000, 6000)]
HARMONIC_TOLERANCE_BPM = 5.0


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ALGO_ROOT, text=True).strip()
    except Exception:
        return "unavailable"


def _session_assets(subject: str) -> dict:
    return {
        "subject": subject,
        "subject_dir": DATA_ROOT / f"sub-{subject}_",
        "mmwave_dir": DATA_ROOT / f"sub-{subject}_" / "mmwave",
        "acq": next(iter(sorted((DATA_ROOT / f"sub-{subject}_").glob("*.acq"))), None),
        "pilot": PILOT_ROOT / subject / "c1c_waveforms_replayed.npz",
    }


def _load_first_frames(mmwave_dir: Path, subject: str, n_frames: int = 6000) -> np.ndarray:
    """Load only the prespecified first 6000 frames; no full session read."""
    files = sorted(mmwave_dir.glob(f"sub-{subject}_mmwave_datacube_part*.npz"))
    if not files:
        raise FileNotFoundError(f"No part files for {subject}: {mmwave_dir}")
    chunks: list[np.ndarray] = []
    n = 0
    for path in files:
        with np.load(path) as data:
            keys = sorted(key for key in data.files if key.startswith("tx"))
            chunk = np.stack([data[key] for key in keys], axis=-1).astype(np.complex64)
        take = min(chunk.shape[0], n_frames - n)
        if take > 0:
            chunks.append(chunk[:take])
            n += take
        if n >= n_frames:
            break
    if n < n_frames:
        raise ValueError(f"Only {n} frames available for {subject}; expected {n_frames}")
    return np.concatenate(chunks, axis=0)


def _profile_selection(algo, iq: np.ndarray, start: int, end: int) -> dict:
    segment = iq[start:end]
    channel_power = np.mean(np.abs(segment) ** 2, axis=(0, 1))
    bin_power = np.mean(np.abs(segment) ** 2, axis=0)
    best_ch_auto = int(np.argmax(channel_power))
    br_ch, br_bin, hr_ch, hr_bin, summaries = algo.select_separate_channels_bins(
        bin_power, segment, segment.shape[0]
    )
    summary_by_channel = {int(item["channel"]): item for item in summaries}
    hr_summary = summary_by_channel[int(hr_ch)]
    br_summary = summary_by_channel[int(br_ch)]
    return {
        "frame_start": start,
        "frame_end": end,
        "window_s": [round(start / algo.FS, 3), round(end / algo.FS, 3)],
        "hr_bin": int(hr_bin),
        "hr_channel": int(hr_ch),
        "br_bin": int(br_bin),
        "br_channel": int(br_ch),
        "previous_hr_bin": None,
        "previous_hr_channel": None,
        "previous_br_bin": None,
        "previous_br_channel": None,
        "hr_bin_displacement": None,
        "br_bin_displacement": None,
        "hr_channel_switch": None,
        "br_channel_switch": None,
        "hr_bin_displacement_m_formal_0p037": None,
        "br_bin_displacement_m_formal_0p037": None,
        "auto_best_channel": best_ch_auto,
        "hr_selection_score": round(float(hr_summary["best_hr_selection_score"]), 6),
        "br_selection_score": round(float(br_summary["best_br_score"]), 6),
        "hr_phase_stability": round(float(hr_summary["best_hr_phase_stability"]), 6),
        "br_phase_stability": round(float(br_summary["best_br_phase_stability"]), 6),
        "selection_rationale": "current_select_separate_channels_bins_argmax_over_existing_scores",
        "existing_qc_status": "not_recomputed; current producer QC remains authoritative",
        "existing_motion_evidence": "not_available_in_this_mmwave_only_diagnostic",
        "phase_jump_status": "not_comparable_until_same_target_is_selected",
        "phase_boundary_jump_rad": None,
        "phase_jump_flag_gt_1rad": None,
        "channel_summary": summaries,
    }


def _raw_boundary_phase(algo, iq: np.ndarray, previous: dict, current: dict) -> tuple[str, float | None, bool | None]:
    same_hr = previous["hr_bin"] == current["hr_bin"] and previous["hr_channel"] == current["hr_channel"]
    if not same_hr:
        return "not_comparable_target_changed", None, None
    z_prev = iq[previous["frame_end"] - 1, previous["hr_bin"], previous["hr_channel"]]
    z_cur = iq[current["frame_start"], current["hr_bin"], current["hr_channel"]]
    delta = float(np.angle(z_cur * np.conj(z_prev)))
    return "same_target_raw_complex_boundary_delta", round(delta, 6), bool(abs(delta) > 1.0)


def build_continuity(algo) -> list[dict]:
    rows: list[dict] = []
    for subject in ("97793", "9779", "97795"):
        assets = _session_assets(subject)
        iq = _load_first_frames(assets["mmwave_dir"], subject)
        previous = None
        for index, (start, end) in enumerate(WINDOWS, start=1):
            row = _profile_selection(algo, iq, start, end)
            row.update({"session_id": f"sub-{subject}_ses-SART", "subject": subject, "window_id": f"w{index:02d}"})
            if previous is not None:
                row["previous_hr_bin"] = previous["hr_bin"]
                row["previous_hr_channel"] = previous["hr_channel"]
                row["previous_br_bin"] = previous["br_bin"]
                row["previous_br_channel"] = previous["br_channel"]
                row["hr_bin_displacement"] = abs(row["hr_bin"] - previous["hr_bin"])
                row["br_bin_displacement"] = abs(row["br_bin"] - previous["br_bin"])
                row["hr_channel_switch"] = row["hr_channel"] != previous["hr_channel"]
                row["br_channel_switch"] = row["br_channel"] != previous["br_channel"]
                row["hr_bin_displacement_m_formal_0p037"] = round(row["hr_bin_displacement"] * FORMAL_BIN_SPACING_M, 6)
                row["br_bin_displacement_m_formal_0p037"] = round(row["br_bin_displacement"] * FORMAL_BIN_SPACING_M, 6)
                status, delta, flag = _raw_boundary_phase(algo, iq, previous, row)
                row["phase_jump_status"] = status
                row["phase_boundary_jump_rad"] = delta
                row["phase_jump_flag_gt_1rad"] = flag
            rows.append(row)
            previous = row
    return rows


def _current_a_json(subject: str) -> Path:
    if subject == "97793":
        return EXTERNAL_OUTPUT_ROOT / "sub-97793_" / "sub-97793_ses-SART_mmwave_vital_signs.json"
    return EXTERNAL_OUTPUT_ROOT / f"sub-{subject}_" / "_selection_60s" / f"sub-{subject}_ses-SART_mmwave_vital_signs.json"


def _a_windows(subject: str) -> tuple[dict, list[dict]]:
    d = _json(_current_a_json(subject))
    windows = d.get("heart_rate", {}).get("segment_reference_correction", {}).get("windows", [])
    windows = [w for w in windows if float(w.get("end_s", 0)) <= 60.0 + 1e-6][:5]
    if len(windows) != 5:
        raise ValueError(f"Current A output for {subject} does not contain five 0-60 s windows")
    return d, windows


def _empty_reference() -> dict[tuple[float, float], dict[str, float | None]]:
    return {tuple(w): {"ecg_hr_bpm": None, "rsp_br_bpm": None} for w in [(0, 20), (10, 30), (20, 40), (30, 50), (40, 60)]}


def _external_reference_windows(subject: str) -> dict[tuple[float, float], dict[str, float | None]]:
    """C-only RSP reference; never passed to the radar producer."""
    try:
        sys.path.insert(0, str(ALGO_ROOT / "scripts"))
        import analyze_acq_reference as ref
        import bioread

        assets = _session_assets(subject)
        datafile = bioread.read_file(str(assets["acq"]))
        fs = float(datafile.samples_per_second)
        rsp_ch = ref._channel(datafile, ("rsp", "resp", "respiration"))
        if rsp_ch is None:
            return _empty_reference()
        acq_start = ref._acq_start_ms(datafile)
        mm_start = ref._mmwave_start_ms(assets["subject_dir"])
        offset = ((mm_start - acq_start) / 1000.0) if acq_start and mm_start else 0.0
        ecg_ch = ref._channel(datafile, ("ecg",))
        ecg = np.asarray(ecg_ch.data, dtype=float) if ecg_ch is not None else None
        rsp = np.asarray(rsp_ch.data, dtype=float)
        out = {}
        for start, end in [(0, 20), (10, 30), (20, 40), (30, 50), (40, 60)]:
            m = ref._peaks_and_metrics(ecg, rsp, fs, offset + start, offset + end)
            out[(start, end)] = {
                "ecg_hr_bpm": round(float(m["hr_ecg_bpm"]), 6) if m.get("hr_ecg_bpm") is not None else None,
                "rsp_br_bpm": round(float(m["br_rsp_bpm"]), 6) if m.get("br_rsp_bpm") is not None else None,
            }
        return out
    except Exception as exc:
        return _empty_reference()


def _near_harmonic(hr: float | None, br: float | None) -> tuple[bool, int | None, float | None]:
    if hr is None or br is None or br <= 0:
        return False, None, None
    candidates = [(k, k * br) for k in (2, 3) if 45.0 <= k * br <= 180.0]
    if not candidates:
        return False, None, None
    k, target = min(candidates, key=lambda item: abs(hr - item[1]))
    return bool(abs(hr - target) <= HARMONIC_TOLERANCE_BPM), int(k), round(float(target), 6)


def _guard_b(a_hr: float | None, radar_br: float | None, time_bpm: float | None) -> dict:
    flagged, k, target = _near_harmonic(a_hr, radar_br)
    if not flagged:
        return {"b_hr_bpm": a_hr, "b_flagged": False, "b_action": "retain_A", "harmonic_k": None, "harmonic_target_bpm": None, "candidate_changed": False, "changed_from_bpm": None, "changed_to_bpm": None}
    safe_time, _, _ = _near_harmonic(time_bpm, radar_br)
    if time_bpm is not None and 45.0 <= time_bpm <= 180.0 and not safe_time:
        return {"b_hr_bpm": time_bpm, "b_flagged": True, "b_action": "downweight_spectrum_use_radar_time_candidate", "harmonic_k": k, "harmonic_target_bpm": target, "candidate_changed": True, "changed_from_bpm": a_hr, "changed_to_bpm": time_bpm}
    return {"b_hr_bpm": None, "b_flagged": True, "b_action": "reject_no_safe_radar_candidate", "harmonic_k": k, "harmonic_target_bpm": target, "candidate_changed": True, "changed_from_bpm": a_hr, "changed_to_bpm": None}


def build_harmonic(algo) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    for subject in ("97793", "9779", "97795"):
        d, windows = _a_windows(subject)
        radar_br = d.get("breath_rate", {}).get("freq_bpm") or d.get("breath_rate", {}).get("time_bpm")
        reference_by_window = _external_reference_windows(subject)
        for w in windows:
            start, end = float(w["start_s"]), float(w["end_s"])
            a_hr = w.get("corrected_bpm")
            time_bpm = w.get("time_bpm")
            reference = reference_by_window.get((start, end), {"ecg_hr_bpm": None, "rsp_br_bpm": None})
            ecg_hr = reference.get("ecg_hr_bpm")
            rsp_br = reference.get("rsp_br_bpm")
            b = _guard_b(a_hr, float(radar_br) if radar_br is not None else None, time_bpm)
            c_flag, c_k, c_target = _near_harmonic(a_hr, rsp_br)
            row = {
                "session_id": f"sub-{subject}_ses-SART",
                "window_id": f"{int(start):02d}-{int(end):02d}s",
                "window_start_s": start,
                "window_end_s": end,
                "ecg_hr_bpm": ecg_hr,
                "radar_hr_A_bpm": a_hr,
                "radar_hr_B_bpm": b["b_hr_bpm"],
                "radar_br_bpm": radar_br,
                "external_rsp_br_C_only_bpm": rsp_br,
                "A_time_bpm_radar_only": time_bpm,
                "A_raw_freq_bpm": w.get("raw_freq_bpm"),
                "A_harmonic_relation_to_C": f"{c_k}x" if c_flag else "neither_or_not_within_tolerance",
                "B_harmonic_flag_to_radar_BR": b["b_flagged"],
                "B_action": b["b_action"],
                "B_harmonic_k": b["harmonic_k"],
                "B_harmonic_target_bpm": b["harmonic_target_bpm"],
                "candidate_changed": b["candidate_changed"],
                "changed_from_bpm": b["changed_from_bpm"],
                "changed_to_bpm": b["changed_to_bpm"],
                "C_harmonic_flag_external_only": c_flag,
                "C_harmonic_k_external_only": c_k,
                "C_harmonic_target_bpm_external_only": c_target,
                "C_is_production_input": False,
                "guard_rule": "radar-only BR; flag A HR within +/-5 bpm of 2x/3x BR; use radar time candidate only if it is non-harmonic, otherwise reject diagnostic candidate",
            }
            for label, value in (("A", a_hr), ("B", b["b_hr_bpm"])):
                row[f"{label}_error_bpm"] = round(abs(float(value) - float(ecg_hr)), 6) if value is not None and ecg_hr is not None else None
            rows.append(row)

    metrics: dict = {"methods": {}, "harmonic_definition": "external RSP C-only relation; +/-5 bpm around 2x/3x", "catastrophic_error_definition": "not frozen; quantile/extreme summaries only"}
    for method, key in (("A", "radar_hr_A_bpm"), ("B", "radar_hr_B_bpm")):
        errors = [r[f"{method}_error_bpm"] for r in rows if r[f"{method}_error_bpm"] is not None]
        harmonic = [r[f"{method}_error_bpm"] for r in rows if r["C_harmonic_flag_external_only"] and r[f"{method}_error_bpm"] is not None]
        nonharmonic = [r[f"{method}_error_bpm"] for r in rows if not r["C_harmonic_flag_external_only"] and r[f"{method}_error_bpm"] is not None]
        metrics["methods"][method] = {
            "n_rows_with_error": len(errors),
            "coverage_pct": round(100.0 * len(errors) / len(rows), 3),
            "mae_bpm": round(float(np.mean(errors)), 6) if errors else None,
            "median_abs_error_bpm": round(float(np.median(errors)), 6) if errors else None,
            "p95_abs_error_bpm": round(float(np.percentile(errors, 95)), 6) if errors else None,
            "max_abs_error_bpm": round(float(np.max(errors)), 6) if errors else None,
            "external_harmonic_n": len(harmonic),
            "external_harmonic_mae_bpm": round(float(np.mean(harmonic)), 6) if harmonic else None,
            "non_harmonic_n": len(nonharmonic),
            "non_harmonic_mae_bpm": round(float(np.mean(nonharmonic)), 6) if nonharmonic else None,
            "b_rejections": sum(r["B_action"] == "reject_no_safe_radar_candidate" for r in rows) if method == "B" else None,
        }
    metrics["decision"] = "B_not_proposed_for_producer_from_this_targeted_sample" if metrics["methods"]["B"]["mae_bpm"] is None or metrics["methods"]["B"]["mae_bpm"] >= metrics["methods"]["A"]["mae_bpm"] else "B_requires_independent_replication_before_producer_proposal"
    metrics["external_RSP_role"] = "validation_oracle_only_never_production_input"
    return rows, metrics


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    sys.path.insert(0, str(ALGO_ROOT / "scripts"))
    import process_vital_signs_v3_1_1 as algo

    continuity = build_continuity(algo)
    harmonic, metrics = build_harmonic(algo)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_csv(RESULT_ROOT / "target_continuity_diagnostic.csv", continuity)
    _write_csv(RESULT_ROOT / "harmonic_abc_window_metrics.csv", harmonic)
    continuity_summary = {
        "status": "TARGETED_CONTINUITY_COMPLETE",
        "sessions": ["97793", "9779", "97795"],
        "windows_per_session": len(WINDOWS),
        "transition_count": len(WINDOWS) - 1,
        "scope": "first 6000 frames only; five overlapping 20-second windows; no full batch",
        "hr_bin_hops": sum(bool(r["hr_bin_displacement"]) for r in continuity),
        "br_bin_hops": sum(bool(r["br_bin_displacement"]) for r in continuity),
        "hr_channel_switches": sum(bool(r["hr_channel_switch"]) for r in continuity),
        "br_channel_switches": sum(bool(r["br_channel_switch"]) for r in continuity),
        "transition_count_total": len([r for r in continuity if r["previous_hr_bin"] is not None]),
        "phase_jump_comparable_rows": sum(r["phase_jump_status"] == "same_target_raw_complex_boundary_delta" for r in continuity),
        "phase_jump_flag_gt_1rad": sum(bool(r["phase_jump_flag_gt_1rad"]) for r in continuity),
        "motion_evidence": "not_available; no no-motion inference made",
        "formal_bin_spacing_used_only_for_displacement_reporting_m": FORMAL_BIN_SPACING_M,
        "algorithm_change": False,
    }
    (RESULT_ROOT / "target_continuity_summary.json").write_text(json.dumps(continuity_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULT_ROOT / "harmonic_abc_summary.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "status": "MMWAVE_TARGETED_VALIDATION_COMPLETE",
        "producer_algorithm_modified": False,
        "portable_repo_modified": False,
        "issue_16": "PAUSED",
        "hrv": "BLOCKED",
        "external_rsp": "C_only_validation_reference_not_production_input",
        "producer_reference_commit": _git_commit(),
        "diagnostic_script_sha256": _sha256(Path(__file__)),
        "producer_script_sha256": _sha256(ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"),
        "inputs": [str(DATA_ROOT / f"sub-{s}_") for s in ("97793", "9779", "97795")],
        "a_current_outputs": [str(_current_a_json(s)) for s in ("97793", "9779", "97795")],
        "input_frame_range": {"start": 0, "end_exclusive": 6000, "window_frames": WINDOWS},
        "window_seconds_at_100hz": [[round(start / 100.0, 3), round(end / 100.0, 3)] for start, end in WINDOWS],
        "continuity_csv": str(RESULT_ROOT / "target_continuity_diagnostic.csv"),
        "harmonic_csv": str(RESULT_ROOT / "harmonic_abc_window_metrics.csv"),
    }
    for name in ("target_continuity_diagnostic.csv", "harmonic_abc_window_metrics.csv", "target_continuity_summary.json", "harmonic_abc_summary.json"):
        manifest[f"sha256_{name}"] = _sha256(RESULT_ROOT / name)
    (RESULT_ROOT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"continuity": continuity_summary, "harmonic": metrics}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
