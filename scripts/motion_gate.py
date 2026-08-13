"""
motion_gate.py — 摄像头运动量前置质量门（正式实验可复用工具）
====================================================================
版本: v1.0 (2026-08-11)
功能: 从 NIR/RGB 视频提取 1Hz 运动量序列, 为毫米波 30s 窗标记
      运动伪影（运动量 > 被试内 P90 的窗标记为伪影）。
      依据: 预实验 6/6 被试显著发现（d 中位 -0.90, 见
      docs/方案/摄像头毫米波融合门控方案.md）。
用法:
  cd 08_算法/scripts
  python motion_gate.py --subject 007 --data-root F:/预实验 \
      --mmwave-windows 预实验/02_全程窗/09_预实验-SUB007-FULL/sub007_full_windows.json
输出: output/预实验/03_跨被试/09_预实验-优化实验/MOTION-GATE/
        motion_gate_007.csv（每窗: t_start, motion, artifact_flag）
依赖: opencv-python, numpy
"""

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "MOTION-GATE"
SAMPLE_EVERY = 30   # 30fps → 1Hz
SCALE = 0.125       # 灰度缩放
SMOOTH = 5          # 平滑窗（秒）
P90 = 90            # 伪影阈值百分位


def extract_motion(subject: str, data_root: Path, mode: str = "nir"):
    """1Hz 运动量序列（整体帧差, 与 experiment_video_motion 一致）。"""
    avi = data_root / f"sub-{subject}_" / mode / f"sub-{subject}_{mode}.avi"
    cap = cv2.VideoCapture(str(avi))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS)
    t_sec, motion = [], []
    prev = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % SAMPLE_EVERY == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, None, fx=SCALE, fy=SCALE,
                               interpolation=cv2.INTER_AREA).astype(np.float32)
            if prev is not None:
                t_sec.append(idx / fps)
                motion.append(float(np.mean(np.abs(small - prev))))
            prev = small
        idx += 1
    cap.release()
    m = np.convolve(np.asarray(motion), np.ones(SMOOTH) / SMOOTH, mode="same")
    return np.array(t_sec), m


def load_offset(data_root: Path, subject: str) -> float:
    """视频相对 mmwave 的偏移（秒）。"""
    tl = data_root / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    mm = nir = None
    with open(tl, encoding="utf-8", newline="") as f:
        for parts in csv.reader(f):
            if len(parts) >= 3:
                if parts[0] == "mmwave_start":
                    mm = int(parts[2])
                elif parts[0] == "nir_start":
                    nir = int(parts[2])
    return (nir - mm) / 1000.0 if mm and nir else 0.0


def main():
    parser = argparse.ArgumentParser(description="运动量前置质量门")
    parser.add_argument("--subject", type=str, default="007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    parser.add_argument("--mode", type=str, default="nir", choices=["nir", "rgb"])
    parser.add_argument("--mmwave-windows", type=str, default=None,
                        help="毫米波窗 json（full_windows 格式, 含 t_start_s/quality）")
    parser.add_argument("--pct", type=float, default=P90, help="伪影阈值百分位")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    subject = args.subject.zfill(3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[sub-{subject}] 提取 {args.mode} 运动量...")
    res = extract_motion(subject, data_root, args.mode)
    if res is None:
        print("视频无法打开")
        return
    t, motion = res
    offset = load_offset(data_root, subject)
    print(f"运动量 {len(t)} 点, offset={offset:.1f}s")

    # 读毫米波窗（若无则输出序列本身）
    if args.mmwave_windows:
        d = json.load(open(args.mmwave_windows, encoding="utf-8"))
        wins = d["windows"]
    else:
        wins = None

    rows = []
    if wins:
        thr = np.percentile(motion, args.pct)
        for w in wins:
            tv = float(w["t_start_s"]) + offset
            mask = (t >= tv) & (t < tv + 30)
            if mask.sum() < 10:
                continue
            mv = float(np.mean(motion[mask]))
            rows.append({"subject": subject, "t_start_s": w["t_start_s"],
                         "motion": round(mv, 4),
                         "artifact": int(mv > thr),
                         "quality": w.get("quality", "")})
        print(f"阈值 P{args.pct:.0f} = {thr:.2f}: 标记伪影窗 "
              f"{sum(1 for r in rows if r['artifact'])}/{len(rows)}")
    else:
        thr = np.percentile(motion, args.pct)
        for i in range(0, len(t), 30):
            seg = motion[i:i + 30]
            if len(seg) >= 10:
                rows.append({"subject": subject, "t_start_s": round(float(t[i]), 1),
                             "motion": round(float(np.mean(seg)), 4),
                             "artifact": int(float(np.mean(seg)) > thr),
                             "quality": ""})

    csv_path = OUT_DIR / f"motion_gate_{subject}.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "t_start_s", "motion",
                                               "artifact", "quality"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"[csv] {csv_path}（{len(rows)} 窗）")


if __name__ == "__main__":
    main()
