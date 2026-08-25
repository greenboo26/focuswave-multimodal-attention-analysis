"""参数化RGB运动门控工具。

只处理调用方提供的视频、RGB逐帧Unix毫秒时间戳和毫米波窗口CSV；不写入原始数据。
CSV至少需要两列：frame_index,rgb_unix_ms。窗口CSV至少需要：window_id,start_unix_ms,end_unix_ms。
"""

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np


def read_timestamps(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                try:
                    rows.append((int(row[0]), int(float(row[1]))))
                except ValueError:
                    pass
    return np.asarray(rows, dtype=np.int64)


def extract(video, timestamps, sample_fps=1.0, scale=0.125, smooth_s=5):
    ts = read_timestamps(timestamps)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    every = max(1, round(fps / sample_fps))
    times, motion, prev, index = [], [], None, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % every == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_AREA).astype(np.float32)
            if prev is not None and index < len(ts):
                times.append(int(ts[index, 1]))
                motion.append(float(np.mean(np.abs(small - prev))))
            prev = small
        index += 1
    cap.release()
    values = np.asarray(motion, dtype=float)
    smooth = np.convolve(values, np.ones(smooth_s) / smooth_s, mode="same")
    return np.asarray(times, dtype=np.int64), smooth


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--timestamps", required=True)
    p.add_argument("--windows", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    times, motion = extract(args.video, args.timestamps)
    threshold = float(np.percentile(motion, 90))
    rows = []
    with Path(args.windows).open(encoding="utf-8-sig", newline="") as f:
        for w in csv.DictReader(f):
            mask = (times >= int(w["start_unix_ms"])) & (times <= int(w["end_unix_ms"]))
            n = int(mask.sum())
            mean = float(np.mean(motion[mask])) if n else None
            rows.append({**w, "rgb_points": n, "rgb_motion_mean": mean,
                         "subject_p90_threshold": threshold,
                         "motion_gate": "pass" if mean is not None and mean <= threshold else "flag" if n else "unavailable"})
    with Path(args.output).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["motion_gate"])
        writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
