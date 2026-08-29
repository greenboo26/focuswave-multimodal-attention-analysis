"""
experiment_video_motion.py — 摄像头运动量时间序列 × 行为事件
====================================================================
版本: v1.0 (2026-08-11)
功能: 从 NIR/RGB 视频提取 1Hz 运动量时间序列（帧差能量, 灰度下采样),
      与行为错误事件（commission）对齐: 错误前/后运动量变化
      （走神时头部运动减少 vs 唤醒时增加）, 并做正确按键对照。
依据: 多模态注意力追踪（NIH 1R61MH138713 项目含运动传感）;
      走神研究常见"行为静止/头部微动减少"关联。

数据: F:/预实验/sub-007_/nir/sub-007_nir.avi（1080p 30fps 42.9min）
      + beh CSV 事件（master_timeline 对齐）
输出: output/预实验/03_跨被试/09_预实验-优化实验/VIDEO-MOTION/
        motion_curve_summary.json + motion_vs_events.png
用法:
  cd 08_算法/scripts
  python experiment_video_motion.py --subject 007 --data-root F:/预实验
依赖: opencv-python, numpy
"""

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "VIDEO-MOTION"
SAMPLE_EVERY = 30      # 每 30 帧取 1 帧（30fps → 1Hz）
SCALE = 0.125          # 灰度缩放比例（1080p → 135x240）
MOTION_WIN = 5         # 运动量平滑窗（秒）


def extract_motion_series(subject: str, data_root: Path, mode: str = "nir"):
    """提取 1Hz 运动量序列（帧差能量, 平滑后）。返回 (t_sec, motion)。"""
    avi = data_root / f"sub-{subject}_" / mode / f"sub-{subject}_{mode}.avi"
    cap = cv2.VideoCapture(str(avi))
    if not cap.isOpened():
        return None, None
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
            small = cv2.resize(gray, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA).astype(np.float32)
            if prev is not None:
                energy = float(np.mean(np.abs(small - prev)))
                t_sec.append(idx / fps)
                motion.append(energy)
            prev = small
        idx += 1
        if idx % 9000 == 0:
            print(f"  已处理 {idx/fps/60:.0f}min...")
    cap.release()
    t = np.asarray(t_sec)
    m = np.asarray(motion)
    # 平滑
    k = MOTION_WIN
    kernel = np.ones(k) / k
    m_s = np.convolve(m, kernel, mode="same")
    return t, m_s


def load_events(data_root: Path, subject: str):
    """commission 与正确按键事件（相对视频起始的时间? 用 mmwave 对齐）。"""
    # 视频起始时间戳
    tl = data_root / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    mm_start = nir_start = None
    with open(tl, encoding="utf-8", newline="") as f:
        for parts in csv.reader(f):
            if len(parts) >= 3 and parts[0] == "mmwave_start":
                mm_start = int(parts[2])
            elif len(parts) >= 3 and parts[0] == "nir_start":
                nir_start = int(parts[2])
    if mm_start is None or nir_start is None:
        return None, None, None
    offset = (nir_start - mm_start) / 1000.0  # 视频相对 mmwave 的偏移（秒）
    comm, correct = [], []
    for fpath in sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv")):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    onset = int(float(r["absolute_onset_time"]))
                except (ValueError, KeyError):
                    continue
                rel = (onset - mm_start) / 1000.0 - offset  # 转为视频时间
                if rel < 5:
                    continue
                if r["is_no_go"] == "1" and r["response"] == "1":
                    comm.append(rel)
                elif r["is_no_go"] == "0" and r["response"] == "1":
                    correct.append(rel)
    return comm, correct, offset


def event_window_curve(t, motion, events, half=10):
    """事件锁定运动量: [-half, +half]s 窗口均值。"""
    vals = []
    for et in events:
        mask = (t >= et - half) & (t < et + half)
        if mask.sum() >= 5:
            vals.append(float(np.mean(motion[mask])))
    return vals


def main():
    parser = argparse.ArgumentParser(description="摄像头运动量×行为事件")
    parser.add_argument("--subject", type=str, default="007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    subject = args.subject.zfill(3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[sub-{subject}] 提取 NIR 运动量序列（1Hz, 42min 约 2500 点）...")
    t, motion = extract_motion_series(subject, data_root)
    if t is None:
        print("视频无法打开")
        return
    print(f"  运动量序列: {len(t)} 点, 均值 {np.mean(motion):.3f}")

    comm, correct, offset = load_events(data_root, subject)
    print(f"  commission {len(comm)}, 正确按键 {len(correct)}, 视频偏移 {offset:.1f}s")
    rng = np.random.default_rng(42)
    correct_s = sorted(rng.choice(correct, size=min(len(comm), len(correct)), replace=False))

    comm_m = event_window_curve(t, motion, comm)
    corr_m = event_window_curve(t, motion, correct_s)
    # 错误窗口运动量 vs 正确窗口（按键对照）
    result = {"subject": subject, "n_comm": len(comm_m), "n_correct": len(corr_m),
              "comm_motion_mean": round(float(np.mean(comm_m)), 4) if comm_m else None,
              "correct_motion_mean": round(float(np.mean(corr_m)), 4) if corr_m else None,
              "comm_motion_se": round(float(np.std(comm_m, ddof=1) / np.sqrt(len(comm_m))), 4) if len(comm_m) > 1 else None,
              "correct_motion_se": round(float(np.std(corr_m, ddof=1) / np.sqrt(len(corr_m))), 4) if len(corr_m) > 1 else None}
    with open(OUT_DIR / f"motion_curve_{subject}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  错误窗运动量: {result['comm_motion_mean']:.4f} vs 正确窗: {result['correct_motion_mean']:.4f}")

    # 图: 运动量时间序列 + 错误事件标记
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.plot(t / 60, motion, linewidth=0.6, color="#2e86c1", alpha=0.8)
    for et in comm:
        ax.axvline(et / 60, color="#c0392b", linewidth=0.3, alpha=0.4)
    ax.set_xlabel("时间 (min)")
    ax.set_ylabel("运动量 (帧差能量)")
    ax.set_title(f"sub-{subject} NIR 运动量时间序列（红=commission 错误）")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    png = OUT_DIR / f"motion_series_{subject}.png"
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"[png] {png}")


if __name__ == "__main__":
    main()


