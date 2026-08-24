"""Frozen-evaluator cross-session validation for RS6240 S1 versus T0.

This entry point intentionally excludes the evaluator-development session
``sub-97793_`` and uses the frozen global offset ``+0.365 s`` without any
per-session or per-model re-estimation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from evaluate_rs6240_multichannel_ecg_v1 import (  # noqa: E402
    MODELS,
    REFERENCE,
    build_model,
    ecg_clean_peaks,
    load_window,
    read_csv,
)
from rs6240_ecg_evaluator_v1 import evaluate_matched_beats  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "rs6240_ecg_cross_session_v1"
FROZEN_OFFSET_S = 0.365
TOLERANCE_S = 0.15
DEV_SESSION = "sub-97793_"
DATA_SESSION_ALIASES = {"sub-97794_": "sub-97994_"}
MODELS_TO_COMPARE = {"S1": MODELS["S1"], "T0": MODELS["T0"]}


def mean_value(rows: list[dict], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return float(np.mean(values)) if values else None


def paired_delta(rows: list[dict], key: str) -> float | None:
    values = []
    for onset in sorted({row["onset_ms"] for row in rows}):
        pair = {row["model"]: row for row in rows if row["onset_ms"] == onset}
        if "S1" not in pair or "T0" not in pair:
            continue
        s1, t0 = pair["S1"], pair["T0"]
        if s1.get(key) in (None, "") or t0.get(key) in (None, ""):
            continue
        values.append(float(t0[key]) - float(s1[key]))
    return float(np.mean(values)) if values else None


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Write every expected artifact, including an empty header-only failure file.

    A previous failed attempt can otherwise leave stale rows in ``failures.csv``
    after a later successful re-run, which makes the outputs internally
    inconsistent even when the summary reports zero failures.
    """
    if not rows and not fieldnames:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    references = [row for row in read_csv(REFERENCE) if row["session_id"] != DEV_SESSION]
    expected_sessions = sorted({row["session_id"] for row in references})
    if len(references) != 80 or expected_sessions != ["sub-97794_", "sub-97795_", "sub-97796_", "sub-9779_"]:
        raise RuntimeError(f"Unexpected cross-session reference set: {expected_sessions}, n={len(references)}")

    rows: list[dict] = []
    errors: list[dict] = []
    for index, ref in enumerate(references, start=1):
        session = ref["session_id"]
        data_session = DATA_SESSION_ALIASES.get(session, session)
        onset_ms = int(ref["onset_ms"])
        try:
            cube, frame_start, frame_end = load_window(data_session, onset_ms - 30000, onset_ms)
            ecg = ecg_clean_peaks(data_session, float(ref["onset_acq_s"]))
            for model, channels in MODELS_TO_COMPARE.items():
                payload = build_model(cube, data_session, model, channels)
                analysis = payload["analysis"]
                heart_rate = analysis["result"].get("heart_rate", {})
                pred_hr = heart_rate.get("time_bpm")
                ecg_hr = ecg["hr_bpm"]
                matched = evaluate_matched_beats(
                    ecg["peaks_s"],
                    analysis["peaks_s"],
                    FROZEN_OFFSET_S,
                    tolerance_s=TOLERANCE_S,
                )
                rows.append({
                    "evaluator_version": "ECG evaluator v1",
                    "offset_status": "frozen",
                    "global_offset_s": FROZEN_OFFSET_S,
                    "session": session,
                    "data_session": data_session,
                    "onset_ms": onset_ms,
                    "attention": ref["attention"],
                    "frame_start": frame_start,
                    "frame_end": frame_end,
                    "model": model,
                    "channels": "|".join(map(str, payload["meta"]["channels"])),
                    "range_bin": payload["meta"]["bin"],
                    "ecg_hr_bpm": ecg_hr,
                    "pred_hr_bpm": pred_hr,
                    "hr_abs_error_bpm": abs(float(pred_hr) - ecg_hr) if pred_hr is not None and ecg_hr is not None else None,
                    "resp_harmonic_mislock": int(any(abs(float(analysis["raw_hr_bpm"]) - harmonic * float(ref["rsp_br_bpm_goldclean"])) <= 5.0 for harmonic in (2.0, 3.0))) if analysis["raw_hr_bpm"] is not None and ref.get("rsp_br_bpm_goldclean") else None,
                    **matched,
                })
            print(f"processed {index}/{len(references)} {session} onset={onset_ms} frames={frame_end-frame_start}")
        except Exception as exc:  # preserve failures explicitly instead of hiding them
            errors.append({"session": session, "onset_ms": onset_ms, "error_type": type(exc).__name__, "error": str(exc)})
            print(f"FAILED {session} onset={onset_ms}: {type(exc).__name__}: {exc}")

    metric_keys = [
        "hr_abs_error_bpm",
        "ibi_mae_ms_matched",
        "ibi_rmse_ms_matched",
        "beat_recall",
        "rmssd_abs_error_ms_matched",
        "resp_harmonic_mislock",
    ]
    session_model_summary = []
    session_deltas = []
    for session in expected_sessions:
        session_rows = [row for row in rows if row["session"] == session]
        for model in MODELS_TO_COMPARE:
            model_rows = [row for row in session_rows if row["model"] == model]
            session_model_summary.append({
                "session": session,
                "model": model,
                "n_windows_expected": 20,
                "n_windows_completed": len(model_rows),
                "matched_ibi_usable_windows": sum(int(float(row["matched_interval_count"]) > 0) for row in model_rows),
                "matched_rmssd_usable_windows": sum(int(str(row["rmssd_usable"]).lower() == "true") for row in model_rows),
                **{key: mean_value(model_rows, key) for key in metric_keys},
            })
        session_deltas.append({
            "session": session,
            "n_windows_expected": 20,
            "n_windows_completed": len({row["onset_ms"] for row in session_rows}),
            "global_offset_s": FROZEN_OFFSET_S,
            "delta_definition": "T0 - S1; lower is better except beat_recall",
            **{f"delta_{key}_T0_minus_S1": paired_delta(session_rows, key) for key in metric_keys},
        })

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "window_metrics.csv", rows)
    write_csv(OUT / "session_model_summary.csv", session_model_summary)
    write_csv(OUT / "session_deltas_T0_minus_S1.csv", session_deltas)
    write_csv(OUT / "failures.csv", errors, fieldnames=["session", "onset_ms", "error_type", "error"])
    summary = {
        "evaluator_version": "ECG evaluator v1",
        "development_session_excluded": DEV_SESSION,
        "sessions": expected_sessions,
        "reference_windows": len(references),
        "completed_windows": len({(row["session"], row["onset_ms"]) for row in rows}),
        "failed_windows": len(errors),
        "fixed_global_offset_s": FROZEN_OFFSET_S,
        "matching_tolerance_ms": TOLERANCE_S * 1000.0,
        "models": ["S1", "T0"],
        "outputs": ["window_metrics.csv", "session_model_summary.csv", "session_deltas_T0_minus_S1.csv", "failures.csv"],
        "notes": [
            "The +0.365 s offset is frozen from the evaluator-development session and was not re-estimated here.",
            "No per-session, per-window, or per-model ECG-based tuning was performed.",
            "Session deltas are paired mean T0-S1 differences over windows present for both models.",
            "This is an experimental cross-session validation and does not modify the S1 mainline baseline.",
        ],
    }
    with (OUT / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
