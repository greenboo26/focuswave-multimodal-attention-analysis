"""Extract timestamp-gated exploratory RGB/NIR features.

The NIR feature is deliberately named a pupil proxy: it is a dark-core/contrast
measure inside a fixed eye ROI, not a clinically calibrated pupil diameter.
This first version is intended for feasibility and quality auditing.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np


DATA_ROOT = Path(r"E:\Data")
WINDOW_S = 60.0
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def read_timestamps(path: Path) -> np.ndarray:
    values = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                values.append((int(float(row[0])), float(row[1])))
            except (ValueError, TypeError):
                continue
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    return arr[np.argsort(arr[:, 0])]


def frame_indices(ts: np.ndarray, start_ms: float, stop_ms: float, stride: int) -> np.ndarray:
    if len(ts) == 0:
        return np.empty(0, dtype=int)
    mask = (ts[:, 1] >= start_ms) & (ts[:, 1] <= stop_ms)
    idx = np.flatnonzero(mask)
    return idx[:: max(1, stride)]


def read_frames(video: cv2.VideoCapture, indices: np.ndarray):
    for idx in indices:
        video.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = video.read()
        if ok:
            yield int(idx), frame


def nir_proxy(frame: np.ndarray) -> dict[str, float]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Camera geometry is fixed in the experiment. These ROIs cover both eyes
    # in the observed NIR close-up while retaining enough margin for movement.
    boxes = ((100, 730, 390, 1010), (1120, 730, 1440, 1010))
    values = []
    valid = 0
    for x1, y1, x2, y2 in boxes:
        roi = gray[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        bg = cv2.GaussianBlur(roi, (51, 51), 0).astype(np.float32)
        dark = (bg - roi.astype(np.float32)) > 18.0
        # Suppress borders and hair/background; use the central eye area.
        h, w = dark.shape
        dark[: h // 5] = False
        dark[4 * h // 5 :] = False
        dark[:, : w // 10] = False
        dark[:, 9 * w // 10 :] = False
        frac = float(np.mean(dark))
        contrast = float(np.percentile(roi, 90) - np.percentile(roi, 10))
        values.append((frac, contrast))
        valid += int(np.isfinite(frac) and np.isfinite(contrast))
    if not values:
        return {"nir_pupil_dark_fraction": np.nan, "nir_eye_contrast": np.nan, "nir_quality": 0.0}
    return {
        "nir_pupil_dark_fraction": float(np.mean([x[0] for x in values])),
        "nir_eye_contrast": float(np.mean([x[1] for x in values])),
        "nir_quality": float(valid / 2.0),
    }


def nir_pupil_geometry(frame: np.ndarray) -> dict[str, float]:
    """Estimate pupil circle geometry from the fixed close-up NIR eye ROIs.

    This is a geometric research proxy, not calibrated pupil diameter. Hough
    candidates are selected near the center of each eye ROI to reduce eyelash
    and eyelid false positives.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    boxes = ((100, 730, 390, 1010), (1120, 730, 1440, 1010))
    radii, xs, ys = [], [], []
    for x1, y1, x2, y2 in boxes:
        roi = gray[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        # Downsample the fixed eye ROI for speed; report radius in original
        # pixels after rescaling the detected circle.
        roi_small = cv2.resize(roi, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        blurred = cv2.medianBlur(roi_small, 5)
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=15,
            param1=80, param2=16, minRadius=7, maxRadius=35,
        )
        if circles is None:
            continue
        h, w = roi_small.shape
        candidates = []
        for cx, cy, radius in circles[0]:
            distance = float(np.hypot(cx - w / 2.0, cy - h / 2.0))
            radius *= 2.0
            cx *= 2.0; cy *= 2.0
            if 15 <= radius <= 65 and cy > h * 2.0 * 0.25 and cy < h * 2.0 * 0.85:
                candidates.append((distance, cx, cy, radius))
        if candidates:
            _, cx, cy, radius = min(candidates, key=lambda z: z[0])
            radii.append(float(radius))
            xs.append(float(cx / (w * 2.0)))
            ys.append(float(cy / (h * 2.0)))
    if not radii:
        return {"nir_pupil_detected": 0.0, "nir_pupil_radius_px": np.nan,
                "nir_pupil_center_x": np.nan, "nir_pupil_center_y": np.nan}
    return {"nir_pupil_detected": float(len(radii) / 2.0),
            "nir_pupil_radius_px": float(np.mean(radii)),
            "nir_pupil_center_x": float(np.mean(xs)),
            "nir_pupil_center_y": float(np.mean(ys))}


def rgb_proxy(frame: np.ndarray, previous: np.ndarray | None) -> dict[str, float]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (160, 90))
    out = {"rgb_luminance": float(np.mean(gray)), "rgb_motion": np.nan,
           "rgb_face_detected": 0.0, "rgb_face_area_frac": np.nan,
           "rgb_face_center_offset": np.nan, "rgb_face_luminance": np.nan}
    face_small = cv2.resize(gray, (640, 360))
    faces = FACE_CASCADE.detectMultiScale(face_small, scaleFactor=1.1, minNeighbors=4, minSize=(70, 70))
    if len(faces):
        x, y, w, h = max(faces, key=lambda f: int(f[2] * f[3]))
        out["rgb_face_detected"] = 1.0
        out["rgb_face_area_frac"] = float((w * h) / (face_small.shape[0] * face_small.shape[1]))
        out["rgb_face_center_offset"] = float(np.hypot((x + w / 2) / face_small.shape[1] - .5, (y + h / 2) / face_small.shape[0] - .5))
        face = face_small[y:y + h, x:x + w]
        out["rgb_face_luminance"] = float(np.mean(face)) if face.size else np.nan
    if previous is not None:
        prev_small = cv2.resize(cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY), (160, 90))
        out["rgb_motion"] = float(np.mean(cv2.absdiff(small, prev_small)))
    return out


def subject_windows(probe_csv: Path, subject: str) -> list[dict[str, float]]:
    rows = []
    with probe_csv.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if str(row.get("subject", "")).zfill(3) != subject:
                continue
            onset = float(row["onset_rel_s"])
            rows.append({
                "subject": subject,
                "onset_rel_s": onset,
                "attention": row.get("attention", ""),
                "start_rel_s": onset - WINDOW_S,
                "stop_rel_s": onset,
            })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="056")
    ap.add_argument("--probe-csv", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--stride", type=int, default=15, help="video-frame stride; 15 = about 2 Hz at 30 fps")
    args = ap.parse_args()

    subject = str(args.subject).zfill(3)
    root = DATA_ROOT / f"sub-{subject}_"
    mw_ts = read_timestamps(root / "mmwave" / f"sub-{subject}_mmwave_timestamps.csv")
    rgb_ts = read_timestamps(root / "rgb" / f"sub-{subject}_rgb_timestamps.csv")
    nir_ts = read_timestamps(root / "nir" / f"sub-{subject}_nir_timestamps.csv")
    if len(mw_ts) == 0:
        raise RuntimeError(f"no mmWave timestamps for {subject}")
    mw_start = float(mw_ts[0, 1])
    windows = subject_windows(args.probe_csv, subject)
    rgb_video = cv2.VideoCapture(str(root / "rgb" / f"sub-{subject}_rgb.avi"))
    nir_video = cv2.VideoCapture(str(root / "nir" / f"sub-{subject}_nir.avi"))
    records = []
    for win in windows:
        start_ms = mw_start + win["start_rel_s"] * 1000.0
        stop_ms = mw_start + win["stop_rel_s"] * 1000.0
        rgb_idx = frame_indices(rgb_ts, start_ms, stop_ms, args.stride)
        nir_idx = frame_indices(nir_ts, start_ms, stop_ms, args.stride)
        rgb_rows = []
        prev = None
        for _, frame in read_frames(rgb_video, rgb_idx):
            rgb_rows.append(rgb_proxy(frame, prev))
            prev = frame
        nir_rows = [{**nir_proxy(frame), **nir_pupil_geometry(frame)} for _, frame in read_frames(nir_video, nir_idx)]
        rec = dict(win)
        rec.update({
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
        records.append(rec)
    rgb_video.release()
    nir_video.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        fields = list(records[0]) if records else ["subject", "onset_rel_s"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    meta = {
        "subject": subject,
        "n_windows": len(records),
        "stride": args.stride,
        "window_s": WINDOW_S,
        "feature_status": "exploratory_proxy",
        "warning": "NIR values are dark-core/contrast proxies, not calibrated pupil diameter.",
    }
    args.output.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
