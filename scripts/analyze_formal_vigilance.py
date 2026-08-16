"""
analyze_formal_vigilance.py — 正式实验第一批警觉度（清醒程度）补充分析
========================================================================
背景: 正式实验探针为两问式（CHANGELOG v3.0, 2026-08-14）:
      - 问题1 probe_response:   注意状态 4 分类（1 专注/2 任务相关干扰/3 走神/4 大脑空白）
      - 问题2 probe_vigilance:  警觉度 4 点 Likert（1 极度困倦 → 4 极度清醒）, 对标 Corcoran 2025
      本脚本补充此前遗漏的警觉度维度分析。

功能: 1) 警觉度分布（6 生理被试）; 2) 警觉度 × 生理指标（探针前 30s 窗）
      Spearman 相关（分被试 + 跨被试 z-score 合并）; 3) 注意状态 × 警觉度 交叉。

数据: 行为 CSV（probe_vigilance）+ 已有 JSON（probes 生理特征, 顺序已验证对齐）

用法:
  cd 08_算法/scripts
  python3.14 analyze_formal_vigilance.py

输出:
  output/06_正式实验/图表数据/vigilance_*.csv（分布/相关/交叉）
  控制台汇总

依赖: numpy, scipy
"""

import csv
import glob
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"E:\正式实验")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验")
PLOT_DIR = OUT_ROOT / "图表数据"
SUBJECTS = ["011", "012", "013", "014", "015", "016"]  # 生理全 6 人
VIGILANCE_LABELS = {1: "极度困倦", 2: "比较困倦", 3: "比较清醒", 4: "极度清醒"}
PHYSIO_KEYS = ["hr_bpm", "sdnn_ms", "rmssd_ms", "br_bpm"]


def load_probe_vigilance(subject):
    """按 block×trial 顺序提取探针的 (probe_response, probe_vigilance, probe_rt)。

    Args:
        subject: 被试编号

    Returns:
        list[dict]: 每探针含 response/vigilance/vigilance_rt
    """
    probes = []
    for f in sorted(glob.glob(str(DATA_ROOT / f"sub-{subject}_" / "beh" /
                                 f"sub-{subject}_Block*_beh.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r["is_probe"] == "1" and r["probe_response"]:
                probes.append({
                    "response": r["probe_response"],
                    "vigilance": int(r["probe_vigilance"]) if r["probe_vigilance"] else None,
                })
    return probes


def main():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("  正式实验第一批警觉度（清醒程度）补充分析")
    print("=" * 70)

    # ── 1. 警觉度分布 ──
    print("\n[1/3] 警觉度分布（6 生理被试, 每被试 30 探针）")
    print(f"  {'被试':<6}{'极度困倦(1)':>10}{'比较困倦(2)':>10}{'比较清醒(3)':>10}{'极度清醒(4)':>10}{'中位数':>6}")
    all_vig = Counter()
    per_subj = {}
    for s in SUBJECTS:
        probes = load_probe_vigilance(s)
        vigs = [p["vigilance"] for p in probes if p["vigilance"] is not None]
        c = Counter(vigs)
        per_subj[s] = {"vigs": vigs, "probes": probes}
        all_vig.update(c)
        med = np.median(vigs)
        print(f"  sub-{s:<3}{c.get(1,0):>10}{c.get(2,0):>10}{c.get(3,0):>10}{c.get(4,0):>10}{med:>6.1f}")

    n_total = sum(all_vig.values())
    print(f"  总计: {dict(sorted(all_vig.items()))} (n={n_total})")
    print(f"  组级均值 {np.mean([v for s in SUBJECTS for v in per_subj[s]['vigs']]):.2f}")

    # 保存分布 CSV
    with open(PLOT_DIR / "vigilance_dist.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "vigilance"])
        for s in SUBJECTS:
            for v in per_subj[s]["vigs"]:
                w.writerow([s, v])

    # ── 2. 警觉度 × 生理指标 Spearman 相关 ──
    print("\n[2/3] 警觉度 × 生理指标（探针前 30s 窗）Spearman 相关")
    # 从 JSON 读生理特征（顺序与 CSV 探针一致, 已验证）
    json_probes = {}
    for s in SUBJECTS:
        d = json.load(open(OUT_ROOT / f"SUB{s}-FULL" / f"sub{s}_full_windows.json",
                           encoding="utf-8"))
        json_probes[s] = d["probes"]

    print(f"  {'被试':<6}{'n':>4}" +
          "".join(f"{k:>12}" for k in PHYSIO_KEYS))
    per_subj_corr = {k: [] for k in PHYSIO_KEYS}
    for s in SUBJECTS:
        vigs = per_subj[s]["vigs"]
        jp = json_probes[s]
        n_min = min(len(vigs), len(jp))
        row = f"  sub-{s:<3}{n_min:>4}"
        for key in PHYSIO_KEYS:
            # 收集 (vigilance, physio) 对, 仅 quality==ok 且值非 None
            pairs = []
            for v, p in zip(vigs[:n_min], jp[:n_min]):
                if v is not None and p.get("quality") == "ok" and p.get(key) is not None:
                    pairs.append((v, p[key]))
            if len(pairs) >= 5:
                rho, pval = stats.spearmanr([x[0] for x in pairs], [x[1] for x in pairs])
                per_subj_corr[key].append(rho)
                row += f"{rho:>12.3f}"
            else:
                row += f"{'—':>12}"
        print(row)

    # 跨被试合并（z-score 标准化生理指标后合并所有探针窗）
    print("\n  跨被试合并（被试内 z-score 后 Spearman）:")
    for key in PHYSIO_KEYS:
        z_pairs = []
        for s in SUBJECTS:
            vigs = per_subj[s]["vigs"]
            jp = json_probes[s]
            vals = []
            for v, p in zip(vigs, jp):
                if v is not None and p.get("quality") == "ok" and p.get(key) is not None:
                    vals.append((v, p[key]))
            if len(vals) >= 5:
                physio_vals = np.array([x[1] for x in vals])
                z = (physio_vals - np.mean(physio_vals)) / (np.std(physio_vals) + 1e-9)
                z_pairs.extend([(vals[i][0], z[i]) for i in range(len(vals))])
        if len(z_pairs) >= 10:
            rho, pval = stats.spearmanr([x[0] for x in z_pairs], [x[1] for x in z_pairs])
            print(f"    {key:<12} rho={rho:+.3f}, p={pval:.3f}, n={len(z_pairs)}")
        else:
            print(f"    {key:<12} n={len(z_pairs)} 不足")

    # 保存相关 CSV
    with open(PLOT_DIR / "vigilance_physio_corr.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "metric", "spearman_rho"])
        for s in SUBJECTS:
            vigs = per_subj[s]["vigs"]
            jp = json_probes[s]
            for key in PHYSIO_KEYS:
                pairs = []
                for v, p in zip(vigs, jp):
                    if v is not None and p.get("quality") == "ok" and p.get(key) is not None:
                        pairs.append((v, p[key]))
                if len(pairs) >= 5:
                    rho, _ = stats.spearmanr([x[0] for x in pairs], [x[1] for x in pairs])
                    w.writerow([s, key, round(rho, 3)])

    # ── 3. 注意状态 × 警觉度 交叉 ──
    print("\n[3/3] 注意状态 × 警觉度 交叉（6 被试合计）")
    cross = Counter()
    for s in SUBJECTS:
        for p in per_subj[s]["probes"]:
            if p["vigilance"] is not None:
                cross[(p["response"], p["vigilance"])] += 1
    print(f"  {'注意状态':<12}{'困倦(1)':>8}{'困倦(2)':>8}{'清醒(3)':>8}{'清醒(4)':>8}{'合计':>6}")
    resp_labels = {"1": "专注", "2": "任务干扰", "3": "走神", "4": "空白"}
    for r in ["1", "2", "3", "4"]:
        row = [cross.get((r, v), 0) for v in [1, 2, 3, 4]]
        print(f"  {resp_labels[r]:<12}{row[0]:>8}{row[1]:>8}{row[2]:>8}{row[3]:>8}{sum(row):>6}")

    with open(PLOT_DIR / "vigilance_attention_cross.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["attention", "vigilance", "count"])
        for (r, v), c in sorted(cross.items()):
            w.writerow([r, v, c])

    print(f"\n已保存: {PLOT_DIR / 'vigilance_*.csv'}")


if __name__ == "__main__":
    main()
