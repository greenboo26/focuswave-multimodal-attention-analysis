"""
compare_v9.py — v9（定位+谐波抑制）vs 现有方法 探针窗对比
========================================================
对 001/007/008 的探针前 30s 窗, 分别跑:
  A. 现有方法: analyze_window_auto（窗级自适应选 bin + 多 bin 交叉验证）
  B. v9 方法:  analyze_window_v9（最高能量定位 + 相位方差 + 谐波陷波）
对比可用率、HR 分布、选中 bin 位置。

用法:
  cd 08_算法/scripts
  python compare_v9.py
"""

import sys
import os
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR.parent))  # scripts/ 父目录（含生产管线）

import analyze_mmwave_hrv as rhrv
import analyze_mmwave_full as fb
from process_vital_signs_v9 import analyze_window_v9


def run_subject(subj):
    """对单个被试的所有探针窗跑两种方法。"""
    rhrv.SUBJECT = subj
    rhrv.MMWAVE_DIR = rhrv.Path(rf"F:\sub-{subj}_\mmwave")
    rhrv.BEH_TIMELINE = rhrv.Path(rf"F:\sub-{subj}_\beh\master_timeline.csv")
    fb.SUBJECT = subj
    fb.BEH_DIR = fb.Path(rf"F:\sub-{subj}_\beh")
    frame_idx, py_ms = rhrv.load_timestamps()
    rhrv.FIRST_FRAME = int(frame_idx[0])
    rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK
    trials = fb.load_beh_trials()

    n_ok_a = n_ok_b = 0
    hr_a, hr_b, bin_b = [], [], []
    n_win = 0
    for t in [x for x in trials if x.get("probe_response")]:
        n_win += 1
        p0, p1 = t["probe_onset_ms"] - 30000, t["probe_onset_ms"]
        fa = max(int(np.searchsorted(py_ms, p0)), 0)
        fb_ = min(int(np.searchsorted(py_ms, p1)), len(frame_idx) - 1)
        if fb_ - fa < 1000:
            continue
        try:
            iq = rhrv.load_frames(int(frame_idx[fa]), int(frame_idx[fb_]))
        except IndexError:
            continue
        # A: 现有方法
        res_a = rhrv.analyze_window_auto(iq, method="vmd_heart")
        if res_a is not None:
            n_ok_a += 1
            hr_a.append(res_a[0].get("hr_time_bpm"))
        # B: v9 方法
        res_b = analyze_window_v9(iq, method="vmd_heart")
        if res_b is not None:
            hr_t = res_b.get("hr_time_bpm")
            if hr_t is not None and 40 <= hr_t <= 100:
                n_ok_b += 1
                hr_b.append(hr_t)
                bin_b.append(res_b["bin"])
    return n_win, n_ok_a, n_ok_b, hr_a, hr_b, bin_b


def main():
    print("=" * 60)
    print("  v9（定位+谐波抑制）vs 现有方法 — 探针窗对比")
    print("=" * 60)
    total_a = total_b = total_n = 0
    for subj in ["001", "007", "008"]:
        n_win, na, nb, hr_a, hr_b, bin_b = run_subject(subj)
        total_n += n_win
        total_a += na
        total_b += nb
        print(f"\nsub-{subj}: {n_win} 探针窗")
        print(f"  现有方法: {na}/{n_win} ({na / max(n_win, 1) * 100:.0f}%)"
              f"  HR={np.mean(hr_a):.1f}±{np.std(hr_a):.1f}" if hr_a else "  现有: 0")
        print(f"  v9:       {nb}/{n_win} ({nb / max(n_win, 1) * 100:.0f}%)"
              f"  HR={np.mean(hr_b):.1f}±{np.std(hr_b):.1f}"
              f"  bin=[{min(bin_b) if bin_b else '-'},{max(bin_b) if bin_b else '-'}]"
              if hr_b else "  v9: 0")
    print(f"\n合计: 现有 {total_a}/{total_n} ({total_a / total_n * 100:.0f}%), "
          f"v9 {total_b}/{total_n} ({total_b / total_n * 100:.0f}%)")


if __name__ == '__main__':
    main()


