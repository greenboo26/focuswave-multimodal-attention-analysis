# -*- coding: utf-8 -*-
"""
scan_new_batch_quality.py — 正式实验新批次(031起)质量扫描 + 距离FFT图生成
========================================================================
文件名: scan_new_batch_quality.py
版本: v1.0 (2026-08-20)
功能: 对 E:/正式实验 从 sub-031 起的新批次被试做毫米波数据质量扫描,
      输出质量汇总 CSV, 并为每个有效被试生成距离FFT热图
      (raw/diag 单通道 + 8通道网格)。

方法:
  1. 质量扫描: 复用 _scan_quality.scan_subject 的核心逻辑
     (accumulate_range_profile 定位人体 → 选心跳bin → 位移(mm)带通 →
      10s窗std分布 vs 0.0005mm 专家噪声阈值)
  2. 距离FFT图: 复用 process_vital_signs_v3_1_1 的
     save_range_fft_map / save_range_fft_channel_grid, 取中段30s窗口

用法:
  cd 08_算法/scripts
  python scan_new_batch_quality.py --scan-only        # 只做质量扫描
  python scan_new_batch_quality.py --fft-only         # 只画距离FFT图
  python scan_new_batch_quality.py                    # 两者都做
  python scan_new_batch_quality.py --subjects 031 032  # 只处理指定被试

输出:
  output/质量扫描/正式实验_quality_new.csv   ← 新批次质量汇总
  output/06_正式实验/距离FFT/sub-XXX/*.png   ← 距离FFT图

依赖: numpy, scipy, matplotlib
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# 复用既有质量扫描逻辑与管线函数
import _scan_quality as sq
import process_vital_signs_v3_1_1 as algo

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

ROOT = Path(r"E:/正式实验")               # 数据根目录
SUBJECT_START = 31                        # 起始被试号（031 起为本次新增批次）
EXTRA_SUBJECTS = ["061", "9504"]          # 批次外但同目录的补充被试
QUALITY_OUT = Path(r"D:\Project\厚粲杯\08_算法\output\质量扫描") / "正式实验_quality_new.csv"
FFT_OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验\距离FFT")
VIEW_LEN_S = 30.0                         # 距离FFT图窗口时长(s), 取数据中段
MAX_PLOT_FRAMES = 1200                    # 距离FFT热图最大绘制帧数


def collect_subjects(root: Path, start: int, extra: list[str]) -> list[str]:
    """收集从 start 起的全部被试号（含 extra, 去重, 按数值排序）。"""
    subs = set(extra)
    for d in root.glob("sub-*_"):
        sid = d.name.replace("sub-", "").rstrip("_")
        if sid.isdigit() and int(sid) >= start:
            subs.add(sid)
    return sorted(subs, key=lambda x: int(x))


def scan_subject_quality(sub_dir: Path, s: str) -> dict:
    """扫描单个被试质量, 空数据目录返回 error 标记, 失败返回 error 详情。

    返回 dict 必含 subject 字段（sq.scan_subject 的返回不含该字段,
    由本函数统一补上）。
    """
    mm_dir = sub_dir / "mmwave"
    prefix = f"sub-{s}_mmwave"
    if not mm_dir.exists():
        return {"subject": s, "prefix": prefix, "error": "no_mmwave_dir"}

    # 主npz + part 分片全部收集
    npz_files = algo.collect_npz_parts(mm_dir, pattern=f"{prefix}_datacube_part*.npz")
    if not npz_files:
        # 可能是录制失败（meta frame_count=0, 无分片）
        meta = mm_dir / f"{prefix}.meta.json"
        if meta.exists():
            import json
            with open(meta, encoding="utf-8") as f:
                info = json.load(f)
            fc = info.get("frame_count", 0)
            return {"subject": s, "prefix": prefix, "error": "no_npz",
                    "meta_frame_count": fc}
        return {"subject": s, "prefix": prefix, "error": "no_npz"}
    r = sq.scan_subject(mm_dir, prefix)
    r["subject"] = s
    return r


def gen_fft_plots(sub_dir: Path, s: str, out_dir: Path) -> list[str]:
    """为单个有效被试生成距离FFT图, 返回生成的png路径列表。

    复用了 v3_1_1 的 save_range_fft_map（单通道 raw/diag）与
    save_range_fft_channel_grid（8通道网格 raw/diag）。
    """
    mm_dir = sub_dir / "mmwave"
    prefix = f"sub-{s}_mmwave"
    npz_files = algo.collect_npz_parts(mm_dir, pattern=f"{prefix}_datacube_part*.npz")
    if not npz_files:
        return []

    session = f"sub-{s}_ses-SART"
    pngs = []
    # 1) 单通道图（自动选最佳通道）
    p1, p2 = algo.save_range_fft_map(
        npz_files, out_dir, session,
        view_len_s=VIEW_LEN_S, max_plot_frames=MAX_PLOT_FRAMES)
    pngs.extend([p1, p2])
    # 2) 8通道网格图
    p3, p4 = algo.save_range_fft_channel_grid(
        npz_files, out_dir, session,
        view_len_s=VIEW_LEN_S, max_plot_frames=MAX_PLOT_FRAMES)
    pngs.extend([p3, p4])
    return [str(p) for p in pngs]


def main():
    ap = argparse.ArgumentParser(description="正式实验新批次质量扫描 + 距离FFT图")
    ap.add_argument("--scan-only", action="store_true", help="只做质量扫描")
    ap.add_argument("--fft-only", action="store_true", help="只画距离FFT图")
    ap.add_argument("--subjects", nargs="+", default=[], help="只处理指定被试")
    args = ap.parse_args()

    do_scan = not args.fft_only
    do_fft = not args.scan_only

    subjects = (args.subjects if args.subjects
                else collect_subjects(ROOT, SUBJECT_START, EXTRA_SUBJECTS))
    print(f"处理被试 ({len(subjects)}): {subjects}")

    rows = []
    for s in subjects:
        sub_dir = ROOT / f"sub-{s}_"
        print(f"=== sub-{s} ===")

        # 1) 质量扫描
        if do_scan:
            r = scan_subject_quality(sub_dir, s)
            rows.append(r)
            if "error" in r:
                print(f"  [质量] ERROR: {r['error']}"
                      + (f" (meta_frame_count={r['meta_frame_count']})"
                         if "meta_frame_count" in r else ""))
            else:
                print(f"  [质量] 心跳std中位={r['std_mm_median']}mm "
                      f"可用率={r['usable_ratio']} "
                      f"相位稳定性={r['phase_stability']} "
                      f"hr_bin={r['hr_bin']}({r['hr_bin_dist_m']}m)")

        # 2) 距离FFT图（仅有效数据）
        if do_fft:
            out_dir = FFT_OUT_ROOT / f"sub-{s}_"
            out_dir.mkdir(parents=True, exist_ok=True)
            pngs = gen_fft_plots(sub_dir, s, out_dir)
            if pngs:
                print(f"  [FFT] {len(pngs)} 张: {out_dir}")
            else:
                print(f"  [FFT] 无有效数据, 跳过")

    # 输出质量 CSV
    if do_scan and rows:
        QUALITY_OUT.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ['subject', 'prefix', 'n_frames', 'duration_s', 'best_ch',
                      'hr_ch', 'hr_bin', 'hr_bin_dist_m', 'hr_ch_power_ratio',
                      'phase_stability', 'n_windows', 'std_mm_median', 'std_mm_p25',
                      'std_mm_p75', 'std_mm_min', 'std_mm_max', 'usable_ratio',
                      'below_threshold_ratio', 'error', 'meta_frame_count']
        with open(QUALITY_OUT, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f"\n[out] 质量CSV: {QUALITY_OUT}")

        ok = [r for r in rows if "error" not in r]
        print(f"===== 新批次质量汇总 ({len(ok)}/{len(rows)} 有效) =====")
        if ok:
            meds = np.array([r["std_mm_median"] for r in ok])
            usable = np.array([r["usable_ratio"] for r in ok])
            print(f"  心跳std中位(mm): {np.min(meds):.5f} ~ {np.max(meds):.5f}, "
                  f"整体中位 {np.median(meds):.5f}")
            print(f"  可用率: 中位 {np.median(usable):.3f}, "
                  f"<50%: {sum(1 for u in usable if u < 0.5)}/{len(usable)}")
        else:
            print("  全部被试无有效数据")


if __name__ == "__main__":
    main()
