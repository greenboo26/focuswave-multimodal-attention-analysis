from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

from extract_crossmodal_features import (
    DATA_ROOT,
    WINDOW_S,
    frame_indices,
    nir_pupil_geometry,
    nir_proxy,
    read_frames,
    read_timestamps,
    rgb_proxy,
    subject_windows,
)


def extract(subject: str, probe_csv: Path, stride: int) -> list[dict]:
    root = DATA_ROOT / f"sub-{subject}_"
    mw_path = root / "mmwave" / f"sub-{subject}_mmwave_timestamps.csv"
    rgb_path = root / "rgb" / f"sub-{subject}_rgb_timestamps.csv"
    nir_path = root / "nir" / f"sub-{subject}_nir_timestamps.csv"
    if not mw_path.exists() or not rgb_path.exists() or not nir_path.exists():
        return []
    mw_ts = read_timestamps(mw_path)
    rgb_ts = read_timestamps(rgb_path)
    nir_ts = read_timestamps(nir_path)
    if not len(mw_ts) or not len(rgb_ts) or not len(nir_ts):
        return []
    rgb_path = root / "rgb" / f"sub-{subject}_rgb.avi"
    nir_path = root / "nir" / f"sub-{subject}_nir.avi"
    if not rgb_path.exists() or not nir_path.exists():
        return []
    rgb_video = cv2.VideoCapture(str(rgb_path))
    nir_video = cv2.VideoCapture(str(nir_path))
    out = []
    mw_start = float(mw_ts[0, 1])
    for win in subject_windows(probe_csv, subject):
        start_ms = mw_start + win["start_rel_s"] * 1000.0
        stop_ms = mw_start + win["stop_rel_s"] * 1000.0
        rgb_idx = frame_indices(rgb_ts, start_ms, stop_ms, stride)
        nir_idx = frame_indices(nir_ts, start_ms, stop_ms, stride)
        rgb_rows = []
        prev = None
        for _, frame in read_frames(rgb_video, rgb_idx):
            rgb_rows.append(rgb_proxy(frame, prev))
            prev = frame
        nir_rows = [{**nir_proxy(frame), **nir_pupil_geometry(frame)} for _, frame in read_frames(nir_video, nir_idx)]
        row = dict(win)
        row.update({
            "rgb_n": len(rgb_rows),
            "nir_n": len(nir_rows),
            "rgb_luminance": float(np.nanmean([x["rgb_luminance"] for x in rgb_rows])) if rgb_rows else np.nan,
            "rgb_motion": float(np.nanmean([x["rgb_motion"] for x in rgb_rows])) if rgb_rows else np.nan,
            "rgb_face_detected": float(np.nanmean([x["rgb_face_detected"] for x in rgb_rows])) if rgb_rows else 0.0,
            "rgb_face_area_frac": float(np.nanmean([x["rgb_face_area_frac"] for x in rgb_rows])) if rgb_rows else np.nan,
            "rgb_face_center_offset": float(np.nanmean([x["rgb_face_center_offset"] for x in rgb_rows])) if rgb_rows else np.nan,
            "rgb_face_luminance": float(np.nanmean([x["rgb_face_luminance"] for x in rgb_rows])) if rgb_rows else np.nan,
            "nir_pupil_dark_fraction": float(np.nanmean([x["nir_pupil_dark_fraction"] for x in nir_rows])) if nir_rows else np.nan,
            "nir_eye_contrast": float(np.nanmean([x["nir_eye_contrast"] for x in nir_rows])) if nir_rows else np.nan,
            "nir_pupil_detected": float(np.nanmean([x["nir_pupil_detected"] for x in nir_rows])) if nir_rows else 0.0,
            "nir_pupil_radius_px": float(np.nanmean([x["nir_pupil_radius_px"] for x in nir_rows])) if nir_rows else np.nan,
            "nir_pupil_center_x": float(np.nanmean([x["nir_pupil_center_x"] for x in nir_rows])) if nir_rows else np.nan,
            "nir_pupil_center_y": float(np.nanmean([x["nir_pupil_center_y"] for x in nir_rows])) if nir_rows else np.nan,
            "nir_quality": float(np.nanmean([x["nir_quality"] for x in nir_rows])) if nir_rows else 0.0,
            "timestamp_gate": "full_window_in_mmwave_clock",
        })
        out.append(row)
    rgb_video.release()
    nir_video.release()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-csv", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--subjects", nargs="*", default=None)
    ap.add_argument("--stride", type=int, default=60)
    args = ap.parse_args()
    if args.subjects:
        subjects = [str(x).zfill(3) for x in args.subjects]
    else:
        subjects = sorted(p.name[4:7] for p in DATA_ROOT.glob("sub-???_") if (p / "mmwave").exists())
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for i, subject in enumerate(subjects, 1):
        got = extract(subject, args.probe_csv, args.stride)
        rows.extend(got)
        print(f"{i}/{len(subjects)} sub-{subject}: {len(got)} windows", flush=True)
        if i % 5 == 0:
            fields = list(rows[0]) if rows else ["subject", "onset_rel_s"]
            with args.output.with_suffix(".partial.csv").open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
    fields = list(rows[0]) if rows else ["subject", "onset_rel_s"]
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
