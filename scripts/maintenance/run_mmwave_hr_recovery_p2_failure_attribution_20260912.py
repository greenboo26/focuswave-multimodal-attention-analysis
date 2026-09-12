"""P2 retrospective failure attribution for the frozen B2 100-probe control.

ECG is read only after the current mmWave target and estimator outputs exist.
It labels diagnostic candidates and never changes production selection or a
threshold. Detailed rows are local-only; only aggregates enter Git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import signal


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
P1_RUNNER = ROOT / "scripts" / "maintenance" / "run_mmwave_hr_recovery_p1_20260912.py"
OLD_TRUTH = ROOT / "scripts" / "maintenance" / "run_ecg_valid_retrospective_spectral_truth_audit_20260830.py"
OLD_RECON = ROOT / "scripts" / "maintenance" / "run_mmwave_selector_path_reconciliation_20260830.py"
CONTROL = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p1_20260912_control_audit_r4\all_subjects_pre30s_selector_hr.csv")
DEFAULT_OUTPUT = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p2_failure_attribution_20260912_r1")
RESULT_DIR = ROOT / "docs" / "results" / "2026-09-12_MMWAVE_HR_RECOVERY_P2"
SUBJECTS = ("9779", "97793", "97794", "97795", "97796")
EXACT_MIN_BPM = 1.5
NEARBY_MIN_BPM = 6.0
WEAK_REL_PROMINENCE = 0.05
HARMONIC_TOL_BPM = 5.0
CORRECT_TOL_BPM = 5.0


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    return digest.hexdigest().upper()


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def key(row: dict) -> tuple[str, str, int]:
    return str(row["subject"]), str(row["block_id"]), int(float(row["probe_onset_unix_ms"]))


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def spectral_evidence(algo, heartbeat: np.ndarray, selected_bpm: float | None, ecg_bpm: float | None) -> dict:
    centered = signal.detrend(np.asarray(heartbeat, dtype=float), type="linear")
    nfft = 1 << int(np.ceil(np.log2(max(len(centered) * 8, 256))))
    freqs, pxx = signal.periodogram(centered, fs=algo.FS, window="hann", nfft=nfft, scaling="spectrum")
    mask = (freqs >= algo.HR_LO_HZ) & (freqs <= algo.HR_HI_HZ)
    f, p = freqs[mask], np.nan_to_num(pxx[mask], nan=0.0, posinf=0.0, neginf=0.0)
    resolution_bpm = algo.FS / nfft * 60.0
    exact_tol = max(0.5 * resolution_bpm, EXACT_MIN_BPM)
    nearby_tol = max(2.0 * resolution_bpm, NEARBY_MIN_BPM)
    if len(p) == 0:
        return {"candidates": [], "exact_tol": exact_tol, "nearby_tol": nearby_tol,
                "exact_available": False, "nearby_available": False}
    peaks, props = signal.find_peaks(p, prominence=0.0)
    if len(peaks) == 0:
        peaks = np.array([int(np.argmax(p))])
        prominences = np.array([0.0])
    else:
        prominences = props["prominences"]
    prom = {int(i): float(v) for i, v in zip(peaks, prominences)}
    order = peaks[np.argsort(p[peaks])[::-1]][:8]
    max_power = max(float(np.max(p)), 1e-12)
    candidates = []
    for rank, idx in enumerate(order, 1):
        bpm = float(f[idx] * 60.0)
        candidates.append({
            "rank": rank, "bpm": bpm, "power": float(p[idx]),
            "relative_power": float(p[idx] / max_power),
            "prominence": prom.get(int(idx), 0.0),
            "relative_prominence": prom.get(int(idx), 0.0) / max_power,
            "ecg_delta_bpm": abs(bpm - ecg_bpm) if ecg_bpm is not None else None,
            "selected_delta_bpm": abs(bpm - selected_bpm) if selected_bpm is not None else None,
        })
    nearest = min(candidates, key=lambda x: x["ecg_delta_bpm"]) if ecg_bpm is not None else None
    selected_candidate = min(candidates, key=lambda x: x["selected_delta_bpm"]) if selected_bpm is not None else None
    return {
        "candidates": candidates, "resolution_bpm": resolution_bpm,
        "exact_tol": exact_tol, "nearby_tol": nearby_tol,
        "nearest": nearest, "selected_candidate": selected_candidate,
        "exact_available": bool(nearest and nearest["ecg_delta_bpm"] <= exact_tol),
        "nearby_available": bool(nearest and nearest["ecg_delta_bpm"] <= nearby_tol),
    }


def harmonic_flags(ecg: float, values: dict[str, float | None], br: float | None) -> list[str]:
    flags = []
    for label, value in values.items():
        if value is None:
            continue
        if abs(value - ecg / 2.0) <= HARMONIC_TOL_BPM:
            flags.append(f"{label}_HALF_ECG")
        if abs(value - 2.0 * ecg) <= HARMONIC_TOL_BPM:
            flags.append(f"{label}_DOUBLE_ECG")
        if br is not None and any(abs(value - k * br) <= HARMONIC_TOL_BPM for k in (2, 3)):
            flags.append(f"{label}_NEAR_2X3X_BR")
    return flags


def classify(row: dict, selected: dict, alternate: dict) -> tuple[str, list[str], str]:
    ecg = number(row["ecg_hr_bpm"])
    fused = number(row["hr_30s_fused_bpm"])
    time = number(row["hr_30s_time_bpm"])
    spectral = number(row["hr_30s_spectral_bpm"])
    if ecg is None or fused is None or int(float(row["mmwave_frames"])) < 200:
        return "COVERAGE_OR_REFERENCE_LIMITATION", ["DIAGNOSTIC_ONLY", "ORACLE_ASSISTED"], "insufficient_coverage_or_reference"
    flags = ["DIAGNOSTIC_ONLY", "ORACLE_ASSISTED"]
    ae_f, ae_t, ae_s = abs(fused - ecg), abs(time - ecg), abs(spectral - ecg)
    if ae_f < ae_t - 1e-9:
        flags.append("FUSION_IMPROVED_VS_TIME")
    elif ae_f > ae_t + 1e-9:
        flags.append("FUSION_WORSENED_VS_TIME")
    else:
        flags.append("FUSION_TIED_VS_TIME")
    if ae_f < ae_s - 1e-9:
        flags.append("FUSION_IMPROVED_VS_SPECTRAL")
    elif ae_f > ae_s + 1e-9:
        flags.append("FUSION_WORSENED_VS_SPECTRAL")
    else:
        flags.append("FUSION_TIED_VS_SPECTRAL")
    if ae_t <= CORRECT_TOL_BPM and ae_f > CORRECT_TOL_BPM:
        flags.append("TIME_CORRECT_FUSION_WRONG")
    if ae_s <= CORRECT_TOL_BPM and ae_f > CORRECT_TOL_BPM:
        flags.append("SPECTRAL_CORRECT_FUSION_WRONG")
    if ae_t > CORRECT_TOL_BPM and ae_s > CORRECT_TOL_BPM:
        flags.append("TIME_AND_SPECTRAL_WRONG")
    flags.extend(harmonic_flags(ecg, {"FUSED": fused, "TIME": time, "SPECTRAL": spectral}, number(row.get("br_bpm"))))
    if ae_f <= CORRECT_TOL_BPM:
        primary = "CORRECT_OR_NEAR_CORRECT"
    elif any("HALF_ECG" in f or "DOUBLE_ECG" in f or "NEAR_2X3X_BR" in f for f in flags):
        primary = "HARMONIC_OR_HALF_DOUBLE_LOCK"
    elif selected["exact_available"]:
        primary = "SELECTED_TARGET_WRONG_PEAK"
    elif alternate.get("exact_available"):
        primary = "TARGET_BIN_CHANNEL_MISS"
    elif number(row.get("hr_usable_ratio")) is not None and number(row["hr_usable_ratio"]) < 0.5:
        primary = "MOTION_OR_SIGNAL_QUALITY"
    elif (selected.get("selected_candidate") or {}).get("relative_prominence", 0.0) < WEAK_REL_PROMINENCE:
        primary = "WEAK_OR_ABSENT_HEART_EVIDENCE"
    else:
        primary = "AMBIGUOUS"
    if selected["exact_available"]:
        old = "true_peak_selected_ecg_bin" if abs(spectral - ecg) <= selected["exact_tol"] else "true_peak_available_selected_target_but_wrong_selection"
    elif selected["nearby_available"]:
        old = "nearby_target_bin_channel"
    else:
        old = "absent_or_weak"
    return primary, sorted(set(flags)), old


def severity(ae: float) -> str:
    if ae <= 5:
        return "AE_LE_5"
    if ae <= 10:
        return "AE_5_TO_10"
    if ae <= 20:
        return "AE_10_TO_20"
    return "AE_GT_20"


def aggregate(rows: list[dict], group_fields: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in group_fields)].append(row)
    output = []
    for group, members in sorted(groups.items()):
        item = dict(zip(group_fields, group))
        item.update({
            "n": len(members),
            "fused_mae_bpm": float(np.mean([r["fused_ae_bpm"] for r in members])),
            "time_mae_bpm": float(np.mean([r["time_ae_bpm"] for r in members])),
            "spectral_mae_bpm": float(np.mean([r["spectral_ae_bpm"] for r in members])),
            "primary_counts_json": json.dumps(dict(Counter(r["PRIMARY_FAILURE_CLASS"] for r in members)), sort_keys=True),
            "selected_target_true_candidate_n": sum(bool(r["selected_target_exact_candidate_available"]) for r in members),
            "alternate_target_true_candidate_n": sum(bool(r["alternate_exact_candidate_available"]) for r in members),
            "mean_phase_stability": float(np.mean([r["phase_stability"] for r in members])),
            "mean_motion_proxy": float(np.mean([r["motion_proxy"] for r in members])),
            "mean_confidence": float(np.mean([r["hr_confidence"] for r in members])),
        })
        output.append(item)
    return output


def _reference_key(row: dict) -> tuple[str, int]:
    subject = str(row.get("session_id", row.get("subject", ""))).strip()
    subject = subject.removeprefix("sub-").removesuffix("_")
    onset = row.get("onset_ms", row.get("probe_onset_unix_ms"))
    return subject, int(float(onset))


def run(
    output_dir: Path,
    *,
    control_path: Path = CONTROL,
    result_dir: Path = RESULT_DIR,
    reference_csv: Path | None = None,
) -> tuple[list[dict], dict]:
    if output_dir.exists():
        raise FileExistsError(f"exclusive output exists: {output_dir}")
    output_dir.mkdir(parents=True)
    algo = load_module(PRODUCER, "p2_producer")
    p1 = load_module(P1_RUNNER, "p2_p1_contract")
    target = load_module(p1.TARGETED, "p2_target")
    p1.install_target_overrides(target)
    controls = read_csv(control_path)
    control_by_key = {key(row): row for row in controls}
    if len(controls) != 100 or len(control_by_key) != 100 or set(r["subject"] for r in controls) != set(SUBJECTS):
        raise AssertionError("frozen control denominator is not exact 5-session/100-probe")
    reference_by_key = {}
    if reference_csv is not None:
        reference_rows = read_csv(reference_csv)
        reference_by_key = {_reference_key(row): row for row in reference_rows}
        if len(reference_rows) != 100 or len(reference_by_key) != 100:
            raise AssertionError("strict reference override is not exact 100-probe")
    rows = []
    invariant_diffs = []
    previous_by_block = {}
    for subject in SUBJECTS:
        file_key = p1.FILE_KEY_OVERRIDES.get(subject, subject)
        probes = p1.load_probe_onsets(file_key)
        timestamps = target.load_mmwave_timestamps(file_key)
        events = target.load_events(file_key)
        physical, _ = target.decode_biopac_markers(file_key)
        blocks, alignment = target.block_intervals(file_key, timestamps, events, physical)
        reader = target.PartReader(file_key)
        block_map = {b["block_id"]: b for b in blocks}
        align_map = {a["block_id"]: a for a in alignment}
        ecg, rsp, ecg_fs = target.load_ecg_reference(file_key)
        for probe in probes:
            block_id, onset = probe["block_id"], probe["probe_onset_unix_ms"]
            block = block_map.get(block_id)
            if not block or block["status"] != "complete":
                continue
            win_start, win_end = max(onset - 30000, int(block["start_event_unix_ms"])), onset
            frame_time = p1.alignment_timestamps(timestamps)
            i0 = int(np.searchsorted(frame_time, win_start, side="left"))
            i1 = int(np.searchsorted(frame_time, win_end, side="left"))
            if i1 - i0 < 200:
                continue
            iq_fd = algo._as_range_cube(reader.slice(i0, i1))
            profile = np.mean(np.abs(iq_fd) ** 2, axis=0)
            br_ch, br_bin, hr_ch, hr_bin, channel_summaries = algo.select_separate_channels_bins(profile, iq_fd, len(iq_fd))
            heartbeat = algo._sos_bandpass(algo.extract_displacement(iq_fd, hr_bin, hr_ch), algo.HR_LO_HZ, algo.HR_HI_HZ)
            previous = previous_by_block.get((subject, block_id))
            step = p1.selector_step(algo, heartbeat, previous)
            previous_by_block[(subject, block_id)] = step["selector_next_previous_bpm"]
            align = align_map[block_id]
            e0 = int(round(align["ecg_fit_slope_samples_per_ms"] * win_start + align["ecg_fit_intercept_sample"]))
            e1 = int(round(align["ecg_fit_slope_samples_per_ms"] * win_end + align["ecg_fit_intercept_sample"]))
            ref = target.ecg_rsp_window(ecg, rsp, ecg_fs, e0, e1)
            strict_ref = reference_by_key.get((subject, onset)) if reference_by_key else None
            if reference_by_key and strict_ref is None:
                raise AssertionError(f"strict reference missing for {(subject, onset)}")
            if strict_ref is not None:
                ecg_usable = str(strict_ref.get("ecg_usable", "0")) == "1"
                ecg_bpm = number(strict_ref.get("ecg_hr_bpm_goldclean")) if ecg_usable else None
                rsp_bpm = number(strict_ref.get("rsp_br_bpm_goldclean"))
                ecg_status = "ECG_VALID" if ecg_usable else "ECG_INVALID"
            else:
                ecg_bpm = number(ref.get("ecg_hr_bpm"))
                rsp_bpm = number(ref.get("rsp_br_bpm"))
                ecg_status = ref.get("ecg_status")
            control = control_by_key[(subject, block_id, onset)]
            frame_ids = np.asarray(timestamps[i0:i1, 0], dtype="<i8")
            frame_hash = hashlib.sha256(frame_ids.tobytes()).hexdigest().upper()
            heart_hash = hashlib.sha256(np.asarray(heartbeat, dtype="<f8").tobytes()).hexdigest().upper()
            checks = {
                "hr_bin": hr_bin, "hr_channel": hr_ch, "br_bin": br_bin, "br_channel": br_ch,
                "frame_i0": i0, "frame_i1_exclusive": i1, "mmwave_frames": i1-i0,
                "frame_index_sha256": frame_hash, "heartbeat_sha256": heart_hash,
                "win_start_unix_ms": win_start, "win_end_unix_ms": win_end,
                "hr_30s_fused_bpm": step["selector_fused_bpm"],
                "hr_30s_time_bpm": step["selector_time_bpm"],
                "hr_30s_spectral_bpm": step["selector_bpm"],
            }
            if strict_ref is None:
                checks["ecg_hr_bpm"] = ecg_bpm
            for field, actual in checks.items():
                expected = control[field]
                same = str(actual) == expected if isinstance(actual, str) else abs(float(actual)-float(expected)) <= 1e-9
                if not same:
                    invariant_diffs.append({"subject": subject, "block_id": block_id, "onset": onset,
                                            "field": field, "expected": expected, "actual": actual})
            selected = spectral_evidence(algo, heartbeat, step["selector_bpm"], ecg_bpm)
            all_candidates = []
            for ch in range(iq_fd.shape[2]):
                _, _, candidates = algo.select_bins_from_profile(profile, ch, iq_fd, len(iq_fd))
                for bin_idx, hr_snr, _, _, phase_stability, selection_score in candidates:
                    if ch == hr_ch and bin_idx == hr_bin:
                        continue
                    hb = algo._sos_bandpass(algo.extract_displacement(iq_fd, bin_idx, ch), algo.HR_LO_HZ, algo.HR_HI_HZ)
                    evidence = spectral_evidence(algo, hb, None, ecg_bpm)
                    if evidence["exact_available"]:
                        nearest = evidence["nearest"]
                        all_candidates.append({"channel": ch, "bin": bin_idx, "hr_snr": hr_snr,
                            "phase_stability": phase_stability, "selection_score": selection_score,
                            "candidate_rank": nearest["rank"], "candidate_bpm": nearest["bpm"],
                            "ecg_delta_bpm": nearest["ecg_delta_bpm"],
                            "same_channel": ch == hr_ch, "bin_delta": abs(bin_idx-hr_bin)})
            alternate = {"exact_available": bool(all_candidates)}
            if all_candidates:
                best_alt = min(all_candidates, key=lambda x: (x["ecg_delta_bpm"], -x["selection_score"]))
                if best_alt["same_channel"] and best_alt["bin_delta"] == 1:
                    alt_location = "SAME_CHANNEL_ADJACENT_BIN"
                elif best_alt["same_channel"]:
                    alt_location = "SAME_CHANNEL_OTHER_BIN"
                elif best_alt["bin_delta"] <= 1:
                    alt_location = "OTHER_CHANNEL_SAME_OR_ADJACENT_BIN"
                else:
                    alt_location = "OTHER_CHANNEL_DISTANT_BIN"
            else:
                best_alt, alt_location = None, "NONE"
            phase_stability, phase_meta = algo._phase_stability_score(np.unwrap(np.angle(iq_fd[:, hr_bin, hr_ch])))
            motion = float(np.std(np.diff(algo.extract_displacement(iq_fd, hr_bin, hr_ch))))
            base = {**control, "ecg_hr_bpm": ecg_bpm, "ecg_status": ecg_status,
                    "rsp_br_bpm": rsp_bpm, "phase_stability": phase_stability,
                    "motion_proxy": motion, "hr_confidence": number(control["hr_confidence"]),
                    "hr_usable_ratio": number(control["hr_usable_ratio"])}
            primary, flags, old_class = classify(base, selected, alternate)
            fused, time_bpm, spectral_bpm = map(number, (control["hr_30s_fused_bpm"], control["hr_30s_time_bpm"], control["hr_30s_spectral_bpm"]))
            row = {**base,
                "PRIMARY_FAILURE_CLASS": primary, "SECONDARY_FLAGS": "|".join(flags),
                "old_truth_semantics_class": old_class, "severity": severity(abs(fused-ecg_bpm)),
                "fused_ae_bpm": abs(fused-ecg_bpm), "time_ae_bpm": abs(time_bpm-ecg_bpm),
                "spectral_ae_bpm": abs(spectral_bpm-ecg_bpm),
                "selected_target_exact_candidate_available": selected["exact_available"],
                "selected_target_nearby_candidate_available": selected["nearby_available"],
                "selected_candidate_rank": (selected.get("nearest") or {}).get("rank"),
                "selected_candidate_bpm": (selected.get("nearest") or {}).get("bpm"),
                "selected_candidate_ecg_delta_bpm": (selected.get("nearest") or {}).get("ecg_delta_bpm"),
                "selected_candidate_power": (selected.get("nearest") or {}).get("power"),
                "selected_candidate_relative_power": (selected.get("nearest") or {}).get("relative_power"),
                "selected_candidate_prominence": (selected.get("nearest") or {}).get("prominence"),
                "selected_candidate_relative_prominence": (selected.get("nearest") or {}).get("relative_prominence"),
                "exact_tolerance_bpm": selected["exact_tol"], "nearby_tolerance_bpm": selected["nearby_tol"],
                "alternate_exact_candidate_available": bool(all_candidates), "alternate_location": alt_location,
                "alternate_channel": (best_alt or {}).get("channel"), "alternate_bin": (best_alt or {}).get("bin"),
                "alternate_candidate_rank": (best_alt or {}).get("candidate_rank"),
                "alternate_candidate_bpm": (best_alt or {}).get("candidate_bpm"),
                "alternate_ecg_delta_bpm": (best_alt or {}).get("ecg_delta_bpm"),
                "alternate_selection_score": (best_alt or {}).get("selection_score"),
                "selected_phase_roughness": phase_meta.get("roughness"),
                "selected_phase_jump_ratio": phase_meta.get("jump_ratio"),
                "selected_channel_selection_margin": max(s["best_hr_selection_score"] for s in channel_summaries) - sorted([s["best_hr_selection_score"] for s in channel_summaries], reverse=True)[1],
                "candidate_json": json.dumps(selected["candidates"], sort_keys=True),
                "alternate_exact_candidates_json": json.dumps(all_candidates, sort_keys=True),
                "diagnostic_status": "DIAGNOSTIC_ONLY_ORACLE_ASSISTED",
            }
            rows.append(row)
    if len(rows) != 100 or invariant_diffs:
        write_csv(output_dir / "INVARIANT_DIFFERENCES.csv", invariant_diffs)
        raise AssertionError(f"P2 invariant failure: rows={len(rows)}, differences={len(invariant_diffs)}")
    table = output_dir / "MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv"
    write_csv(table, rows)
    per_session = aggregate(rows, ("subject",))
    severity_rows = aggregate(rows, ("severity",))
    result_dir.mkdir(parents=True, exist_ok=True)
    write_csv(result_dir / "MMWAVE_HR_RECOVERY_P2_PER_SESSION.csv", per_session)
    write_csv(result_dir / "MMWAVE_HR_RECOVERY_P2_SEVERITY_SUMMARY.csv", severity_rows)
    primary_counts = Counter(r["PRIMARY_FAILURE_CLASS"] for r in rows)
    fusion = {}
    for reference, field in (("time", "time_ae_bpm"), ("spectral", "spectral_ae_bpm")):
        fusion[reference] = {
            "improved": sum(r["fused_ae_bpm"] < r[field]-1e-9 for r in rows),
            "worsened": sum(r["fused_ae_bpm"] > r[field]+1e-9 for r in rows),
            "tied": sum(abs(r["fused_ae_bpm"]-r[field]) <= 1e-9 for r in rows),
        }
    summary = {
        "status": "PASS / FAILURE_ATTRIBUTION_COMPLETE", "n": 100,
        "primary_counts": dict(primary_counts),
        "primary_percentages": {k: v for k, v in primary_counts.items()},
        "mae": {"fused": float(np.mean([r["fused_ae_bpm"] for r in rows])),
                "time": float(np.mean([r["time_ae_bpm"] for r in rows])),
                "spectral": float(np.mean([r["spectral_ae_bpm"] for r in rows]))},
        "fusion": fusion,
        "selected_target_true_candidate_available": sum(r["selected_target_exact_candidate_available"] for r in rows),
        "alternate_target_true_candidate_available": sum(r["alternate_exact_candidate_available"] for r in rows),
        "per_session": per_session, "severity": severity_rows,
    }
    summary_path = result_dir / "MMWAVE_HR_RECOVERY_P2_AGGREGATE_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "task_id": "mmwave_hr_recovery_p2_failure_attribution",
        "status": summary["status"], "run_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_source_commit": git("rev-parse", "HEAD"), "execution_source_commit": "16729b2ef245f9304dae8674f3bac433bc02e98c",
        "cohort": {"sessions": list(SUBJECTS), "probes": 100},
        "window": "[probe_end - 30 s, probe_end)", "time_semantics": "DLL host receive/enqueue timestamp column 1",
        "ecg_role": "DIAGNOSTIC_ONLY / ORACLE_ASSISTED after mmWave candidate generation",
        "control_input": {"path": str(control_path), "sha256": sha256(control_path)},
        "reference_override": ({"path": str(reference_csv), "sha256": sha256(reference_csv)}
                               if reference_csv is not None else None),
        "local_output": {"path": str(table), "sha256": sha256(table), "rows": 100},
        "scripts": [{"path": str(p), "sha256": sha256(p)} for p in (Path(__file__), PRODUCER, P1_RUNNER, OLD_TRUTH, OLD_RECON)],
        "parameters": {"exact_tolerance": "max(0.5 * spectral resolution bpm, 1.5 bpm)",
            "nearby_tolerance": "max(2 * spectral resolution bpm, 6 bpm)",
            "weak_relative_prominence": WEAK_REL_PROMINENCE, "harmonic_tolerance_bpm": HARMONIC_TOL_BPM,
            "correct_or_near_correct_ae_bpm": CORRECT_TOL_BPM},
        "reuse_gate": "PASS",
        "reuse_rejection_reason": "Old nearby_target_bin_channel is a wider within-selected-target spectral tolerance, not physical bin proximity. P2 preserves it as old_truth_semantics_class and adds only topology labels over candidates generated by the unchanged current selector rules; adjacency means discrete bin delta=1 and is diagnostic-only.",
        "invariant_gate": "PASS; exact 100 keys and zero frozen-field differences",
        "python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
        "models_trained": False, "formal_producer_modified": False,
        "hr_br_status": "HOLD_SUPPORTING_ONLY", "hrv_status": "BLOCKED",
    }
    manifest_path = result_dir / "MMWAVE_HR_RECOVERY_P2_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows, {"summary": summary, "manifest": manifest, "manifest_path": manifest_path, "table": table}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--control", type=Path, default=CONTROL)
    parser.add_argument("--result-dir", type=Path, default=RESULT_DIR)
    parser.add_argument("--reference-csv", type=Path)
    args = parser.parse_args()
    rows, result = run(
        args.output_dir,
        control_path=args.control,
        result_dir=args.result_dir,
        reference_csv=args.reference_csv,
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"local_table={result['table']}")
    print(f"manifest={result['manifest_path']}")


if __name__ == "__main__":
    main()
