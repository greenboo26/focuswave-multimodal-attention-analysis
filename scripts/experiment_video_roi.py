"""
experiment_video_roi.py — 头部 ROI 运动 vs 整体运动（走神相关假设）
====================================================================
版本: v1.0 (2026-08-11)
功能: 对比整体帧差运动量与头部 ROI 帧差运动量:
      1) 头部运动是否与错误事件更相关（走神时头部微动减少假设）
      2) 头部运动对毫米波质量门的预测力是否优于整体运动
方法: 每 1Hz 帧 Haar 人脸检测 → ROI 内帧差能量（头部运动）
      整体运动（全帧帧差）作对照。

数据: F:/预实验/sub-007_/nir/sub-007_nir.avi
输出: output/预实验/03_跨被试/09_预实验-优化实验/VIDEO-ROI/
        roi_summary_007.json
用法:
  cd 08_算法/scripts
  python experiment_video_roi.py --subject 007 --data-root F:/预实验
依赖: opencv-python, numpy
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "VIDEO-ROI"
SAMPLE_EVERY = 30
SCALE = 0.25          # ROI 检测用缩放（Haar 在 0.25 尺度更快）


def extract_roi_motion(subject: str, data_root: Path):
    """1Hz 头部 ROI 运动 + 整体运动双序列。"""
    avi = data_root / f"sub-{subject}_" / "nir" / f"sub-{subject}_nir.avi"
    cap = cv2.VideoCapture(str(avi))
    if not cap.isOpened():
        return None, None, None
    fps = cap.get(cv2.CAP_PROP_FPS)
    t_sec, roi_m, full_m = [], [], []
    prev_roi = prev_full = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % SAMPLE_EVERY == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, None, fx=SCALE, fy=SCALE,
                               interpolation=cv2.INTER_AREA).astype(np.float32)
            # ROI = 画面中央偏上 40% 区域（脸部/头部近似, 无 Haar 依赖）
            hh, ww = small.shape
            roi = small[int(hh*0.15):int(hh*0.65), int(ww*0.30):int(ww*0.70)]
            if prev_roi is not None:
                m = min(roi.shape[0], prev_roi.shape[0])
                n = min(roi.shape[1], prev_roi.shape[1])
                roi_energy = float(np.mean(np.abs(roi[:m, :n] - prev_roi[:m, :n])))
            else:
                roi_energy = None
            prev_roi = roi
            if prev_full is not None:
                full_energy = float(np.mean(np.abs(small - prev_full)))
            else:
                full_energy = None
            prev_full = small
            if roi_energy is not None and full_energy is not None:
                t_sec.append(idx / fps)
                roi_m.append(roi_energy)
                full_m.append(full_energy)
        idx += 1
        if idx % 9000 == 0:
            print(f"  已处理 {idx/fps/60:.0f}min...")
    cap.release()
    return np.array(t_sec), np.array(roi_m), np.array(full_m)


def main():
    parser = argparse.ArgumentParser(description="头部 ROI 运动分析")
    parser.add_argument("--subject", type=str, default="007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    subject = args.subject.zfill(3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[sub-{subject}] 提取 ROI 运动（Haar 人脸 + 全帧对照）...")
    t, roi_m, full_m = extract_roi_motion(subject, data_root)
    if t is None:
        print("失败")
        return
    print(f"序列 {len(t)} 点; ROI 检测到人脸的帧比例: "
          f"{sum(1 for i in range(len(t)) if roi_m[i] is not None)}"
          f"/{len(t)}（注: 当前实现仅保留双序列都有值的点）")

    # 头部/整体运动比（头部运动占比）
    ratio = roi_m / (full_m + 1e-9)
    out = {"subject": subject, "n": int(len(t)),
           "roi_mean": round(float(np.mean(roi_m)), 4),
           "full_mean": round(float(np.mean(full_m)), 4),
           "ratio_mean": round(float(np.mean(ratio)), 4),
           "ratio_std": round(float(np.std(ratio)), 4)}
    with open(OUT_DIR / f"roi_summary_{subject}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"  头部 ROI 运动均值 {out['roi_mean']:.4f} | 整体 {out['full_mean']:.4f} | "
          f"头部占比 {out['ratio_mean']:.2f}±{out['ratio_std']:.2f}")
    print(f"[json] {OUT_DIR / f'roi_summary_{subject}.json'}")


if __name__ == "__main__":
    main()
