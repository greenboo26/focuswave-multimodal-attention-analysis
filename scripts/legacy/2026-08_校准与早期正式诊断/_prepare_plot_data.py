"""
_prepare_plot_data.py — 正式实验第一批图表数据导出（长格式 CSV 供 R ggplot2）
============================================================================
功能: 从已完成的正式实验分析产物（行为汇总 CSV + 全程窗 JSON）导出绘图数据:
      1) 行为汇总长格式（5 行为有效被试 × 4 指标）
      2) 行为轨迹（Block 内 4 段 + Block 间 3 block 的 commission）
      3) 生理分布长格式（6 生理被试 × HR/SDNN/RMSSD 窗口级）

输入:
  output/06_正式实验/行为分析/behavior_summary.csv
  output/06_正式实验/SUB{XXX}-FULL/sub{XXX}_full_windows.json
  E:\\正式实验\\sub-XXX_\\beh\\（原始行为 CSV, 用于段级轨迹重算）

输出:
  output/06_正式实验/图表数据/{behavior_summary_long.csv,
                                trajectory_within.csv, trajectory_between.csv,
                                physio_dist_long.csv}

用法:
  cd 08_算法/scripts
  python3.14 _prepare_plot_data.py

依赖: numpy（无第三方）
"""

import csv
import glob
import json
from pathlib import Path

import numpy as np

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"E:\正式实验")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\90_历史归档\2026-08_早期正式实验")
PLOT_DIR = OUT_ROOT / "图表数据"
SUBJECTS_BEHAVIOR = ["011", "012", "013", "014", "016"]  # 行为有效（015 规则反排除）
SUBJECTS_PHYSIO = ["011", "012", "013", "014", "015", "016"]  # 生理全 6 人
RT_PREEMPT_MS = 150        # 预判按键阈值（8-13 定调）
N_SEG_PER_BLOCK = 4        # Block 内分段数


def load_trials(subject):
    """合并 3 个 block 行为 CSV 为试次列表（含 _block 标记）。

    Args:
        subject: 被试编号

    Returns:
        list[dict]: 试次列表
    """
    trials = []
    for fpath in sorted(glob.glob(str(DATA_ROOT / f"sub-{subject}_" / "beh" /
                                     f"sub-{subject}_Block*_beh.csv"))):
        blk = int(fpath.split("Block")[1].split("_")[0])
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                r["_block"] = blk
                trials.append(r)
    return trials


def comm_rate(trials):
    """计算一批试次的 commission 率。

    Args:
        trials: 试次列表

    Returns:
        float: commission 率（no-go 中误按比例）, 无 no-go 时 None
    """
    n_nogo = sum(1 for t in trials if t["is_no_go"] == "1")
    if not n_nogo:
        return None
    n_comm = sum(1 for t in trials if t["is_no_go"] == "1" and t["response"] == "1")
    return n_comm / n_nogo


def main():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. 行为汇总长格式 ──
    # 从 behavior_summary.csv 直接读（宽格式 → 长格式）
    summary = {}
    with open(OUT_ROOT / "行为分析" / "behavior_summary.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            summary[r["subject"]] = r

    with open(PLOT_DIR / "behavior_summary_long.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "metric", "value"])
        for s in SUBJECTS_BEHAVIOR:
            r = summary[s]
            # commission/omission/预判率 ×100 转百分比; RT 保留 ms
            w.writerow([s, "commission", round(float(r["comm_rate"]) * 100, 1)])
            w.writerow([s, "omission", round(float(r["omis_rate"]) * 100, 1)])
            w.writerow([s, "preempt_rate", round(float(r["preempt_rate"]) * 100, 1)])
            w.writerow([s, "rt_mean", round(float(r["rt_mean_ms"]), 1)])

    # ── 2. 行为轨迹（Block 内 4 段 + Block 间 3 block）──
    with open(PLOT_DIR / "trajectory_within.csv", "w", encoding="utf-8-sig", newline="") as fw, \
         open(PLOT_DIR / "trajectory_between.csv", "w", encoding="utf-8-sig", newline="") as fb:
        ww = csv.writer(fw)
        ww.writerow(["subject", "seg", "comm_rate"])
        wb = csv.writer(fb)
        wb.writerow(["subject", "block", "comm_rate"])

        for s in SUBJECTS_BEHAVIOR:
            trials = load_trials(s)
            # Block 内 4 段: 段位置 1-4, 跨 3 block 平均
            for seg_idx in range(N_SEG_PER_BLOCK):
                seg_vals = []
                for blk in [1, 2, 3]:
                    bt = [t for t in trials if t["_block"] == blk]
                    n_per = len(bt) // N_SEG_PER_BLOCK
                    seg = bt[seg_idx * n_per:(seg_idx + 1) * n_per]
                    cr = comm_rate(seg)
                    if cr is not None:
                        seg_vals.append(cr)
                if seg_vals:
                    ww.writerow([s, seg_idx + 1, round(float(np.mean(seg_vals)) * 100, 1)])
            # Block 间
            for blk in [1, 2, 3]:
                bt = [t for t in trials if t["_block"] == blk]
                cr = comm_rate(bt)
                wb.writerow([s, blk, round(cr * 100, 1)])

    # ── 3. 生理分布长格式（窗口级）──
    with open(PLOT_DIR / "physio_dist_long.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "metric", "value"])
        for s in SUBJECTS_PHYSIO:
            p = OUT_ROOT / f"SUB{s}-FULL" / f"sub{s}_full_windows.json"
            d = json.load(open(p, encoding="utf-8"))
            ok = [x for x in d["windows"] if x["quality"] == "ok"]
            for x in ok:
                for metric in ["hr_bpm", "sdnn_ms", "rmssd_ms"]:
                    if x.get(metric) is not None:
                        w.writerow([s, metric, round(x[metric], 2)])

    print("已生成图表数据:")
    for fn in ["behavior_summary_long.csv", "trajectory_within.csv",
               "trajectory_between.csv", "physio_dist_long.csv"]:
        print(f"  {PLOT_DIR / fn}")


if __name__ == "__main__":
    main()


