"""Run the v3.1.1 vital-sign pipeline on one formal subject without touching formal outputs.

Purpose
-------
Quick A/B entry point for the 2026-08-15 expert suggestions already implemented in
process_vital_signs_v3_1_1.py:
- phase-stability / roughness-aware bin scoring
- 8-channel candidate search
- HR range capped at 120 bpm
- K=3 VMD (respiration / heartbeat / residual)
- respiration-guided mode handling
- 40 s VMD windows with 20 s step
- >10 bpm time/frequency disagreement warning / down-weighting

This script writes only to an experimental output directory. It does not overwrite the
existing formal SUBxxx-FULL results.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from process_vital_signs_v3_1_1 import analyze_long_record


def _read_radar_times_ms(path: Path) -> np.ndarray:
    values: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            candidates = []
            if len(row) >= 3:
                candidates.append(row[2])
            candidates.append(row[1])
            parsed = None
            for value in candidates:
                try:
                    parsed = float(value)
                    break
                except (TypeError, ValueError):
                    pass
            if parsed is not None:
                values.append(parsed)
    if not values:
        raise ValueError(f"No usable timestamps in {path}")
    return np.asarray(values, dtype=np.float64)


def _task_frame_bounds(timeline_path: Path, timestamps_path: Path) -> tuple[int | None, int | None, dict]:
    if not timeline_path.exists():
        return None, None, {"status": "timeline_missing"}

    sart_start = None
    last_block_stop = None
    with timeline_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            event = str(row.get("event", "")).strip()
            raw_ts = row.get("unix_ms") or row.get("timestamp_ms") or row.get("time_ms")
            if raw_ts in (None, ""):
                continue
            try:
                ts = float(raw_ts)
            except ValueError:
                continue
            if event == "sart_start" and sart_start is None:
                sart_start = ts
            elif event == "block_stop":
                last_block_stop = ts

    if sart_start is None or last_block_stop is None or last_block_stop <= sart_start:
        return None, None, {
            "status": "task_markers_incomplete",
            "sart_start_ms": sart_start,
            "last_block_stop_ms": last_block_stop,
        }

    radar_ms = _read_radar_times_ms(timestamps_path)
    frame_start = int(np.searchsorted(radar_ms, sart_start, side="left"))
    frame_end = int(np.searchsorted(radar_ms, last_block_stop, side="right"))
    frame_start = max(0, min(frame_start, len(radar_ms)))
    frame_end = max(frame_start, min(frame_end, len(radar_ms)))
    return frame_start, frame_end, {
        "status": "task_gate_applied",
        "sart_start_ms": sart_start,
        "last_block_stop_ms": last_block_stop,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "timestamp_rows": int(len(radar_ms)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental formal-data run with v3.1.1")
    parser.add_argument("--subject", required=True, help="Formal subject id, e.g. 175")
    parser.add_argument("--data-root", required=True, help="Root containing sub-XXX_ directories")
    parser.add_argument(
        "--output-root",
        default=r"D:\Project\厚粲杯\08_算法\output\experimental_formal_v311",
        help="Experimental output root; formal outputs are never overwritten",
    )
    parser.add_argument("--min-range-m", type=float, default=0.3)
    parser.add_argument("--max-range-m", type=float, default=1.5)
    args = parser.parse_args()

    subject = str(args.subject).strip().replace("sub-", "").replace("_", "").zfill(3)
    subject_dir = Path(args.data_root) / f"sub-{subject}_"
    mmwave_dir = subject_dir / "mmwave"
    timestamps_path = mmwave_dir / f"sub-{subject}_mmwave_timestamps.csv"
    timeline_path = subject_dir / "beh" / "master_timeline.csv"
    output_dir = Path(args.output_root) / f"SUB{subject}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not mmwave_dir.exists():
        raise FileNotFoundError(mmwave_dir)
    if not timestamps_path.exists():
        raise FileNotFoundError(timestamps_path)

    frame_start, frame_end, gate_info = _task_frame_bounds(timeline_path, timestamps_path)

    pattern = f"sub-{subject}_mmwave_datacube*.npz"
    result, _ = analyze_long_record(
        parts_dir=mmwave_dir,
        output_dir=output_dir,
        session=f"sub-{subject}_formal_v311",
        method="vmd_heart",
        pattern=pattern,
        frame_start=frame_start,
        frame_end=frame_end,
        min_range_m=args.min_range_m,
        max_range_m=args.max_range_m,
        timestamps_path=timestamps_path,
        behavior_session_label="formal_task",
        behavior_status=gate_info["status"],
    )

    summary = {
        "subject": subject,
        "pipeline": result.get("pipeline"),
        "version": result.get("version"),
        "task_gate": gate_info,
        "channels": result.get("channels"),
        "bins": result.get("bins"),
        "heart_rate": result.get("heart_rate"),
        "breath_rate": result.get("breath_rate"),
        "self_check": result.get("heart_rate", {}).get("self_check")
        or result.get("self_check"),
        "configuration": result.get("configuration"),
        "note": "experimental only; do not replace frozen formal outputs until A/B review",
    }
    summary_path = output_dir / f"sub-{subject}_formal_v311_quick_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[done] v3.1.1 experimental formal run")
    print(f"[subject] sub-{subject}")
    print(f"[task gate] {gate_info}")
    print(f"[output] {output_dir}")
    print(f"[summary] {summary_path}")


if __name__ == "__main__":
    main()
