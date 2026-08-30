"""Frozen, ECG-independent A/B for pre-selection complex-mean subtraction.

This diagnostic reuses the existing v3.1.1 range-profile selector and the
existing block-local continuity rule.  It neither changes the producer nor
computes HR/BR/ECG metrics.  Arm B only replaces the selector input cube with
its slow-time complex-mean-subtracted counterpart.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_NEARFIELD_PRESELECTION_AB"
WINDOWS = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "mmwave_ecg_block_window_comparison.csv"
TARGETED = ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
PRODUCER = ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
SUBJECTS = ("97793", "9779", "97795")
BIN_SPACING_M = 0.037
NEAR_020_MAX_BIN = 5  # bin * 0.037 < 0.20
NEAR_030_MAX_BIN = 8  # bin * 0.037 < 0.30


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def complex_mean_subtract(iq: np.ndarray) -> np.ndarray:
    """Slow-time complex mean subtraction; input is already range-domain."""
    return iq - np.mean(iq, axis=0, keepdims=True)


def independent_selection(rerun, algo, iq: np.ndarray) -> list[dict]:
    # This is the existing selector's public input calculation, retained
    # literally so neither candidate scoring nor channel logic changes.
    real = iq.real.astype(np.float64, copy=False)
    imag = iq.imag.astype(np.float64, copy=False)
    profile = np.mean(real * real + imag * imag, axis=0)
    return algo.select_separate_channels_bins(profile, iq, iq.shape[0])[-1]


def choose(rerun, summaries: list[dict], previous: dict) -> tuple[dict, dict]:
    hr_ch, hr_bin, hr_reason = rerun.local_choice(summaries, "hr", previous.get("hr"))
    br_ch, br_bin, br_reason = rerun.local_choice(summaries, "br", previous.get("br"))
    previous["hr"] = (hr_ch, hr_bin)
    previous["br"] = (br_ch, br_bin)
    return ({"channel": hr_ch, "bin": hr_bin, "reason": hr_reason},
            {"channel": br_ch, "bin": br_bin, "reason": br_reason})


def transition_metrics(rows: list[dict], arm: str, role: str) -> dict:
    pairs = []
    for subject, block in sorted({(r["subject"], r["block_id"]) for r in rows}):
        part = [r for r in rows if r["subject"] == subject and r["block_id"] == block]
        pairs.extend([(int(r[f"{arm}_{role}_bin"]), int(r[f"{arm}_{role}_channel"])) for r in part])
    transitions = max(0, len(pairs) - len({(r["subject"], r["block_id"]) for r in rows}))
    steps = list(zip(pairs, pairs[1:]))
    # Do not cross block boundaries: rebuild within each trajectory.
    bin_switches = channel_switches = 0
    residence = []
    for subject, block in sorted({(r["subject"], r["block_id"]) for r in rows}):
        part = [r for r in rows if r["subject"] == subject and r["block_id"] == block]
        path = [(int(r[f"{arm}_{role}_bin"]), int(r[f"{arm}_{role}_channel"])) for r in part]
        bin_switches += sum(a[0] != b[0] for a, b in zip(path, path[1:]))
        channel_switches += sum(a[1] != b[1] for a, b in zip(path, path[1:]))
        run, last = 0, None
        for item in path:
            run = run + 1 if item == last else 1
            residence.append(run)
            last = item
    return {"arm": arm, "role": role, "n_windows": len(rows), "n_transitions": transitions,
            "bin_switches": bin_switches, "channel_switches": channel_switches,
            "bin_switch_rate": round(bin_switches / transitions, 6) if transitions else None,
            "channel_switch_rate": round(channel_switches / transitions, 6) if transitions else None,
            "max_residence_windows": max(residence) if residence else 0,
            "median_residence_windows": round(float(np.median(residence)), 6) if residence else None}


def main() -> int:
    rerun = load_module(TARGETED, "nearfield_targeted")
    algo = load_module(PRODUCER, "nearfield_v311")
    frozen = [r for r in read_csv(WINDOWS) if r.get("subject") in SUBJECTS]
    if len(frozen) != 335:
        raise RuntimeError(f"Expected frozen 335-window diagnostic subset; got {len(frozen)}")
    states = {arm: {} for arm in ("A_raw", "B_complex_mean_subtracted")}
    rows, grid_rows = [], []
    for subject in SUBJECTS:
        reader = rerun.PartReader(subject)
        for source in [r for r in frozen if r["subject"] == subject]:
            block = source["block_id"]
            for arm in states:
                if states[arm].get(subject, {}).get("block") != block:
                    states[arm][subject] = {"block": block, "hr": None, "br": None}
            iq = reader.slice(int(source["mmwave_start_row"]), int(source["mmwave_end_row_exclusive"]))
            arms = {"A_raw": iq, "B_complex_mean_subtracted": complex_mean_subtract(iq)}
            record = {"subject": subject, "block_id": block, "window_id": source["window_id"]}
            for arm, selected_iq in arms.items():
                summaries = independent_selection(rerun, algo, selected_iq)
                hr, br = choose(rerun, summaries, states[arm][subject])
                record.update({f"{arm}_hr_bin": hr["bin"], f"{arm}_hr_channel": hr["channel"],
                               f"{arm}_hr_reason": hr["reason"], f"{arm}_br_bin": br["bin"],
                               f"{arm}_br_channel": br["channel"], f"{arm}_br_reason": br["reason"],
                               f"{arm}_candidate_channels": len(summaries)})
                power = np.mean(np.abs(selected_iq.astype(np.complex128)) ** 2, axis=0)
                for channel in range(power.shape[1]):
                    near = power[:NEAR_030_MAX_BIN + 1, channel]
                    grid_rows.append({"arm": arm, "subject": subject, "block_id": block,
                                      "channel": channel, "near_peak_bin": int(np.argmax(near)),
                                      "near_peak_power_ratio_to_channel_max": float(np.max(near) / np.max(power[:, channel]))})
            rows.append(record)
    summary = []
    for arm in ("A_raw", "B_complex_mean_subtracted"):
        for role in ("hr", "br"):
            bins = [int(r[f"{arm}_{role}_bin"]) for r in rows]
            channels = [int(r[f"{arm}_{role}_channel"]) for r in rows]
            summary.append({"arm": arm, "role": role, "metric": "selector_coverage", "value": round(len(bins) / len(rows), 6)})
            summary.append({"arm": arm, "role": role, "metric": "selected_lt_0_20_rate", "value": round(sum(b <= NEAR_020_MAX_BIN for b in bins) / len(bins), 6)})
            summary.append({"arm": arm, "role": role, "metric": "selected_lt_0_30_rate", "value": round(sum(b <= NEAR_030_MAX_BIN for b in bins) / len(bins), 6)})
            summary.append({"arm": arm, "role": role, "metric": "selected_bin_mode", "value": Counter(bins).most_common(1)[0][0]})
            summary.append({"arm": arm, "role": role, "metric": "selected_channel_mode", "value": Counter(channels).most_common(1)[0][0]})
    stability = [transition_metrics(rows, arm, role) for arm in ("A_raw", "B_complex_mean_subtracted") for role in ("hr", "br")]
    grid_summary = []
    for arm in ("A_raw", "B_complex_mean_subtracted"):
        for channel in range(8):
            values = [r for r in grid_rows if r["arm"] == arm and r["channel"] == channel]
            modes = Counter(r["near_peak_bin"] for r in values)
            grid_summary.append({"arm": arm, "channel": channel, "n_windows": len(values),
                                 "near_peak_bin_mode": modes.most_common(1)[0][0],
                                 "near_peak_mode_fraction": round(modes.most_common(1)[0][1] / len(values), 6),
                                 "near_peak_ratio_median": round(float(np.median([r["near_peak_power_ratio_to_channel_max"] for r in values])), 6)})
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(RESULT_ROOT / "MMWAVE_PRESELECTION_CLUTTER_AB_SUMMARY.csv", summary)
    write_csv(RESULT_ROOT / "MMWAVE_PRESELECTION_CLUTTER_AB_STABILITY.csv", stability)
    write_csv(RESULT_ROOT / "MMWAVE_PRESELECTION_CLUTTER_AB_CHANNEL_GRID.csv", grid_summary)
    report = ["# mmWave pre-selection clutter A/B — 2026-08-30", "", "Status: **PARTIAL / diagnostic-only**", "",
              "## Frozen contract", "", "- Subset: the existing 335 DLL-time, formal-block diagnostic windows from 97793/9779/97795.", "- A: existing raw mean-power profile and unchanged v3.1.1 candidate scoring/channel selector/block-local continuity.", "- B: the identical cube after slow-time complex-mean subtraction, then the same existing selector. This is post-Range-FFT research only; it does not imply any pre-FFT or firmware operation.", "- No ECG/RSP values, HR/BR estimates, gates, thresholds, or estimator outputs were read or used.", "", "## Result", "", "See the three CSV aggregates for selected-bin near-side rates, switching/residence, and channel-grid near-peak stability. The comparison is descriptive and cannot identify the reflector or validate a physical distance gate.", "", "## Decision rule", "", "A preprocessing change is not adopted by this diagnostic alone. It is eligible only if it reduces near-side selection and trajectory instability without coverage loss and is later separately authorized for a fixed-contract validation. Otherwise retain the current selector."]
    (RESULT_ROOT / "MMWAVE_PRESELECTION_CLUTTER_AB_REPORT_2026-08-30.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    outputs = sorted(RESULT_ROOT.glob("MMWAVE_PRESELECTION_CLUTTER_AB_*"))
    manifest = {"run_id": "MMWAVE_PRESELECTION_CLUTTER_AB_20260830", "status": "PARTIAL_DIAGNOSTIC_ONLY", "reuse_rejection_reason": "Existing assets contained display-only mean subtraction and no selector-integrated, same-window A/B aggregate; this minimal adapter reuses the existing selector without modifying it.", "input": {"windows": WINDOWS.name, "windows_sha256": sha256(WINDOWS), "producer_sha256": sha256(PRODUCER)}, "contract": {"n_windows": len(rows), "subjects": list(SUBJECTS), "bin_spacing_m": BIN_SPACING_M, "ecg_used": False, "pre_fft_claim": False}, "outputs": {p.name: sha256(p) for p in outputs}}
    (RESULT_ROOT / "MMWAVE_PRESELECTION_CLUTTER_AB_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "summary": summary, "stability": stability, "grid": grid_summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
