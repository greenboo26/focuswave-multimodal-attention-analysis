"""
analyze_formal_block_level.py — 正式实验第一批 block 级慢变量分析（新框架 C）
============================================================================
背景（2026-08-16 方法学重构）:
  原"全程 30s 连续窗 + SDNN 相关"废弃; 本脚本回答"分钟级生理状态 vs 行为表现"。
  分析单位 = block（约 9 分钟, 符合 HRV SDNN ≥5min 下限）:
    样本 = 5 行为有效被试 × 3 block = 15;
    生理 = block 内 30s 窗聚合的 HR / RMSSD / BR 中位数（RMSSD 短时稳定, 可聚合）;
    行为 = block commission 率 / RT 均值。

  SDNN 说明: 严格 block 级 SDNN 需长窗逐拍重算（复杂度高, n=15 样本下无统计意义）,
  本脚本暂不重算长窗 SDNN, 改用 RMSSD（短时稳定指标）作为副交感代表。

功能: block 级生理 vs 行为相关（Pearson/Spearman, 被试内 z-score 后）。

数据: master_timeline（block 边界）+ JSON windows（30s 窗生理）+ 行为 CSV

重要: 无 ECG 金标准; n=15 样本太小, 结论定级=探索性/描述。

用法:
  cd 08_算法/scripts
  python3.14 analyze_formal_block_level.py

输出:
  output/06_正式实验/block级/block_level_summary.csv + .md
  控制台汇总

依赖: numpy, scipy
"""

import csv
import glob
import json
from pathlib import Path

import numpy as np
from scipy import stats

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"E:\正式实验")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验")
OUT_DIR = OUT_ROOT / "block级"
SUBJECTS = ["011", "012", "013", "014", "016"]  # 行为有效 5 人
BLOCKS = [1, 2, 3]
PHYSIO_KEYS = ["hr_bpm", "rmssd_ms", "br_bpm"]


def load_block_bounds(subject):
    """从 master_timeline 提取 block 绝对起止 ms。

    Args:
        subject: 被试编号

    Returns:
        dict: {block_num: (start_ms, stop_ms)}
    """
    bounds = {}
    with open(DATA_ROOT / f"sub-{subject}_" / "beh" / "master_timeline.csv",
              encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["event"] == "block_start":
                blk = int(r["detail"].split("_")[0].replace("Block", ""))
                bounds[blk] = [int(r["unix_ms"]), None]
            elif r["event"] == "block_stop":
                blk = int(r["detail"].split("_")[0].replace("Block", ""))
                if blk in bounds:
                    bounds[blk][1] = int(r["unix_ms"])
    return {k: tuple(v) for k, v in bounds.items() if v[1] is not None}


def block_behavior(subject, block):
    """算 block 的 commission 率与 RT 均值（剔预判 RT<150ms）。

    Args:
        subject/block: 被试/block 号

    Returns:
        dict: {comm_rate, rt_mean}
    """
    trials = []
    for f in sorted(glob.glob(str(DATA_ROOT / f"sub-{subject}_" / "beh" /
                                 f"sub-{subject}_Block{block}_B_beh.csv"))):
        trials = list(csv.DictReader(open(f, encoding="utf-8-sig")))
    n_nogo = sum(1 for t in trials if t["is_no_go"] == "1")
    n_comm = sum(1 for t in trials if t["is_no_go"] == "1" and t["response"] == "1")
    rts = [float(t["rt"]) for t in trials
           if t["is_no_go"] == "0" and t["response"] == "1" and t["rt"]
           and float(t["rt"]) >= 150]
    return {
        "comm_rate": n_comm / n_nogo if n_nogo else None,
        "rt_mean": float(np.mean(rts)) if rts else None,
    }


def block_physio(subject, block, bounds):
    """聚合 block 时间范围内的 30s 窗生理中位数。

    Args:
        subject/block: 被试/block
        bounds: block 起止 ms

    Returns:
        dict: {hr_bpm, rmssd_ms, br_bpm 的中位数}
    """
    jd = json.load(open(OUT_ROOT / f"SUB{subject}-FULL" / f"sub{subject}_full_windows.json",
                        encoding="utf-8"))
    windows = jd["windows"]
    # windows 的 t_start_s 是相对 span_start（sart_start）; 需换算
    # 从 master_timeline 读 sart_start
    sart_start = None
    with open(DATA_ROOT / f"sub-{subject}_" / "beh" / "master_timeline.csv",
              encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["event"] == "sart_start":
                sart_start = int(r["unix_ms"])
    start_ms, stop_ms = bounds
    t0 = (start_ms - sart_start) / 1000  # block 相对 sart_start 的秒
    t1 = (stop_ms - sart_start) / 1000

    out = {}
    for key in PHYSIO_KEYS:
        vals = [w[key] for w in windows
                if w["quality"] == "ok" and w.get(key) is not None
                and t0 <= (w["t_start_s"] + w["t_end_s"]) / 2 < t1]
        out[key] = float(np.median(vals)) if vals else None
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("  正式实验第一批 block 级慢变量分析（新框架 C）")
    print("  分析单位 = block（约 9min）; n = 5 被试 × 3 block = 15")
    print("  注意: 无 ECG 金标准; n=15 太小, 结论定级 = 探索性/描述")
    print("=" * 72)

    rows = []
    for s in SUBJECTS:
        bounds = load_block_bounds(s)
        for blk in BLOCKS:
            beh = block_behavior(s, blk)
            phy = block_physio(s, blk, bounds[blk])
            rows.append({"subject": s, "block": blk, **beh, **phy})

    # ── 描述 ──
    print("\n[描述] block 级（每行 = 1 个 block）")
    print(f"  {'被试':<5}{'Block':>6}{'comm%':>7}{'RT':>6}{'HR':>7}{'RMSSD':>7}{'BR':>6}")
    for r in rows:
        print(f"  {r['subject']:<5}{r['block']:>6}"
              f"{r['comm_rate']*100:>6.1f}{r['rt_mean']:>6.0f}"
              f"{r['hr_bpm']:>7.1f}{r['rmssd_ms']:>7.1f}{r['br_bpm']:>6.1f}")

    # ── 相关（被试内 z-score 后）──
    print("\n[相关] 生理 × 行为（被试内 z-score 后 Spearman）")
    for pkey in PHYSIO_KEYS:
        for bkey in ["comm_rate", "rt_mean"]:
            z_pairs = []
            for s in SUBJECTS:
                subj = [r for r in rows if r["subject"] == s
                        and r.get(pkey) is not None and r.get(bkey) is not None]
                if len(subj) < 3:
                    continue
                vals = np.array([r[pkey] for r in subj])
                z = (vals - np.mean(vals)) / (np.std(vals) + 1e-9)
                z_pairs.extend([(subj[i][bkey], z[i]) for i in range(len(subj))])
            if len(z_pairs) >= 8:
                rho, p = stats.spearmanr([x[0] for x in z_pairs], [x[1] for x in z_pairs])
                print(f"  {pkey:<12}~{bkey:<10} rho={rho:+.3f}, p={p:.3f}, n={len(z_pairs)}")

    # ── 保存 ──
    with open(OUT_DIR / "block_level_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "block", "comm_rate", "rt_mean",
                    "hr_bpm", "rmssd_ms", "br_bpm"])
        for r in rows:
            w.writerow([r["subject"], r["block"], r["comm_rate"], r["rt_mean"],
                        r["hr_bpm"], r["rmssd_ms"], r["br_bpm"]])
    print(f"\n已保存: {OUT_DIR / 'block_level_summary.csv'}")


if __name__ == "__main__":
    main()
