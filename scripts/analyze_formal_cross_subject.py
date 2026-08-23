"""
analyze_formal_cross_subject.py — 正式实验第一批跨被试汇总 + 稳健性检验
========================================================================
功能: 汇总 6 生理被试的 HR/HRV 分布 + 对 5 行为有效被试做行为×生理相关
      的跨被试一致性检验（Pearson/Spearman 重算 + 方向一致性 + Jackknife）。

输入: output/06_正式实验/SUB{XXX}-FULL/sub{XXX}_full_windows.json
输出: output/06_正式实验/跨被试/cross_subject_summary.csv + .md

用法:
  cd 08_算法/scripts
  python3.14 analyze_formal_cross_subject.py

依赖: numpy, scipy
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 参数声明
# ============================================================
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验")
OUT_DIR = OUT_ROOT / "跨被试"
SUBJECTS_BEHAVIOR = ["011", "012", "013", "014", "016"]  # 行为有效（015 规则反排除）
SUBJECTS_PHYSIO = ["011", "012", "013", "014", "015", "016"]  # 生理全 6 人
# 相关对: (生理指标, 行为指标) —— 与 analyze_mmwave_full.py 窗口级相关一致
CORR_PAIRS = [
    ("hr_bpm", "rt_mean"), ("hr_bpm", "rt_sd"),
    ("sdnn_ms", "rt_mean"), ("rmssd_ms", "rt_mean"),
    ("br_bpm", "rt_mean"), ("sdnn_ms", "n_err"),
    ("sdnn_ms", "preempt_rate"), ("rmssd_ms", "preempt_rate"),
]
PHYSIO_KEYS = ["hr_bpm", "br_bpm", "sdnn_ms", "rmssd_ms"]


def load_json(subject):
    """读取单被试全程窗 JSON。

    Args:
        subject: 被试编号

    Returns:
        dict: {windows, probes, correlations}
    """
    p = OUT_ROOT / f"SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    return json.load(open(p, encoding="utf-8"))


def recompute_corrs(windows, physio, behav):
    """从窗口级数据重算 Pearson 与 Spearman 相关（含显著性）。

    判伪标准（预实验定调）: Pearson 显著 + Spearman 必须也显著, 否则判伪相关。

    Args:
        windows: 全程窗列表
        physio: 生理字段名
        behav: 行为字段名

    Returns:
        dict: {pearson_r, pearson_p, spearman_r, spearman_p, n}
    """
    pairs = [(w[physio], w[behav]) for w in windows
             if w["quality"] == "ok" and w.get(physio) is not None and w.get(behav) is not None]
    if len(pairs) < 10:
        return None
    x = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])
    rp, pp = stats.pearsonr(x, y)
    rs, ps = stats.spearmanr(x, y)
    return {"pearson_r": round(float(rp), 3), "pearson_p": round(float(pp), 4),
            "spearman_r": round(float(rs), 3), "spearman_p": round(float(ps), 4),
            "n": len(pairs)}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("  正式实验第一批跨被试汇总 + 稳健性检验")
    print("=" * 70)

    data = {s: load_json(s) for s in SUBJECTS_PHYSIO}

    # ── 1. 生理分布汇总（6 人）──
    print("\n[1/3] 生理分布汇总（6 生理被试, 全程可信窗）")
    print(f"  {'被试':<6}{'可信窗':>6}{'HR中位':>8}{'HR范围':>14}{'SDNN':>7}{'RMSSD':>7}")
    physio_summary = {}
    for s in SUBJECTS_PHYSIO:
        ok = [w for w in data[s]["windows"] if w["quality"] == "ok"]
        for k in PHYSIO_KEYS:
            vals = [w[k] for w in ok if w.get(k) is not None]
            if k not in physio_summary:
                physio_summary[k] = {}
            physio_summary[k][s] = {"med": float(np.median(vals)),
                                    "mean": float(np.mean(vals)),
                                    "n": len(vals)}
        hrs = [w["hr_bpm"] for w in ok if w.get("hr_bpm") is not None]
        sdnn = physio_summary["sdnn_ms"][s]["med"]
        rmssd = physio_summary["rmssd_ms"][s]["med"]
        print(f"  sub-{s:<3}{len(ok):>6}{np.median(hrs):>8.1f}"
              f"{f'{min(hrs):.0f}-{max(hrs):.0f}':>14}{sdnn:>7.1f}{rmssd:>7.1f}")

    # ── 2. 行为×生理相关跨被试一致性（5 行为有效被试）──
    print("\n[2/3] 行为×生理相关跨被试一致性（5 行为有效被试）")
    print(f"  {'相关对':<22}{'Pearson中位':>11}{'Spearman中位':>12}{'方向(+/−)':>10}{'显著数':>6}")
    corr_summary = {}
    for physio, behav in CORR_PAIRS:
        pearson_rs, spearman_rs = [], []
        n_sig = 0
        for s in SUBJECTS_BEHAVIOR:
            c = recompute_corrs(data[s]["windows"], physio, behav)
            if c is None:
                continue
            pearson_rs.append(c["pearson_r"])
            spearman_rs.append(c["spearman_r"])
            if c["pearson_p"] < 0.05 and c["spearman_p"] < 0.05:
                n_sig += 1  # 双显著才计（判伪标准）
        if not pearson_rs:
            continue
        n_pos = sum(1 for r in pearson_rs if r > 0)
        n_neg = len(pearson_rs) - n_pos
        # 符号检验（二项, H0: 正负各半）
        sign_p = stats.binomtest(min(n_pos, n_neg), len(pearson_rs), 0.5).pvalue * 2
        corr_summary[f"{physio}~{behav}"] = {
            "pearson_rs": pearson_rs, "spearman_rs": spearman_rs,
            "n": len(pearson_rs), "n_pos": n_pos, "n_neg": n_neg,
            "n_sig": n_sig, "sign_p": round(sign_p, 3),
        }
        print(f"  {physio+'~'+behav:<22}{np.median(pearson_rs):>11.3f}"
              f"{np.median(spearman_rs):>12.3f}{f'{n_pos}/{n_neg}':>10}{n_sig:>6}")

    # ── 3. Jackknife 稳健性（逐个剔除被试看方向是否稳定）──
    print("\n[3/3] Jackknife 稳健性（逐个剔除被试, 剩余 Pearson r 中位方向）")
    for pair, info in corr_summary.items():
        physio, behav = pair.split("~")
        full_rs = []
        per_subj = {}
        for s in SUBJECTS_BEHAVIOR:
            c = recompute_corrs(data[s]["windows"], physio, behav)
            if c is not None:
                full_rs.append(c["pearson_r"])
                per_subj[s] = c["pearson_r"]
        # 逐个剔除
        signs = []
        for drop in SUBJECTS_BEHAVIOR:
            remain = [r for s, r in per_subj.items() if s != drop]
            if remain:
                signs.append("+" if np.median(remain) > 0 else "-")
        stable = len(set(signs)) == 1
        print(f"  {pair:<22} 全 r 中位 {np.median(full_rs):+.3f} | "
              f"剔除后方向 {'稳定' if stable else '不稳定'} ({signs})")

    # ── 保存 ──
    with open(OUT_DIR / "cross_subject_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
        import csv
        w = csv.writer(f)
        w.writerow(["subject", "n_ok_windows", "hr_med", "sdnn_med", "rmssd_med", "br_med"])
        for s in SUBJECTS_PHYSIO:
            ok = [x for x in data[s]["windows"] if x["quality"] == "ok"]
            w.writerow([s, len(ok),
                        round(physio_summary["hr_bpm"][s]["med"], 1),
                        round(physio_summary["sdnn_ms"][s]["med"], 1),
                        round(physio_summary["rmssd_ms"][s]["med"], 1),
                        round(physio_summary["br_bpm"][s]["med"], 1)])
    print(f"\n已保存: {OUT_DIR / 'cross_subject_summary.csv'}")


if __name__ == "__main__":
    main()
