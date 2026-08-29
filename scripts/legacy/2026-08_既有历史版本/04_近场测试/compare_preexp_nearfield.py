"""
compare_preexp_nearfield.py — 预实验全部场次 + 0812test 距离-近场强度对比
=====================================================================
版本: v1.0 (2026-08-12)
功能: 合并 analyze_preexp_nearfield.py 的两批输出 (预实验 + 0812test),
      统一呈现全部场次的人体距离与近场峰强度关系:
        1. 汇总表 (按人体距离排序)
        2. 近场峰强度箱线图 (按距离分组着色)
        3. 近场/人体比 vs 人体距离散点 (30s 窗级)

输入: 两个 summary csv (场次, t0_sec, nf_peak, body_peak, nf_body_ratio,
      body_bin, body_m)

用法:
  cd 08_算法/scripts
  python compare_preexp_nearfield.py

输出:
  output/preexp_range_compare/nearfield_compare.png  ← 三合一对比图
  output/preexp_range_compare/compare_stats.md       ← 汇总表

依赖: numpy, matplotlib
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"
OUT_DIR = OUTPUT_ROOT / "preexp_range_compare"

# 距离分组: <0.33m 近距(旁瓣侵入), 0.33-0.45m 甜点, >0.8m 远距(SNR低)
NEAR_CUT_M = 0.33
FAR_CUT_M = 0.80

# 历史质量标注（来自质量评估记录, 仅用于表格备注）
QUALITY_NOTE = {
    "000": "43% 可信", "001": "摆位失误", "002": "摆位失误",
    "003": "46% 可信", "004": "全可信", "005": "全可信",
    "006": "全可信", "007": "全可信", "008": "60% 可信",
    "009": "100% 可信", "010": "待评估",
    "08121": "0812test 按键", "08122": "0812test 不动",
    "08123": "0812test 离1m",
}


def load_summary(path: Path) -> list[dict]:
    """读取汇总 csv 为行字典列表。

    参数:
        path: summary csv 路径
    返回:
        list[dict]: 每行一条, 数值字段已转换
    """
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["nf_peak"] = float(r["nf_peak"])
            r["body_peak"] = float(r["body_peak"])
            r["nf_body_ratio"] = float(r["nf_body_ratio"])
            r["body_m"] = float(r["body_m"])
            rows.append(r)
    return rows


def main():
    """合并两批 csv → 汇总表 + 对比图。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = (load_summary(OUTPUT_ROOT / "preexp_range_v2" / "preexp_range_summary.csv")
                + load_summary(OUTPUT_ROOT / "preexp_range_0812_v2" / "preexp_range_summary.csv"))

    # ── 汇总表 ──
    subjects = sorted({r["subject"] for r in all_rows})
    stats = []
    for sub in subjects:
        rows = [r for r in all_rows if r["subject"] == sub]
        dm = np.median([r["body_m"] for r in rows])
        d_lo, d_hi = np.percentile([r["body_m"] for r in rows], [25, 75])
        nf = np.median([r["nf_peak"] for r in rows])
        nf_lo, nf_hi = np.percentile([r["nf_peak"] for r in rows], [25, 75])
        ratio = np.median([r["nf_body_ratio"] for r in rows])
        stats.append({"sub": sub, "n": len(rows), "dm": dm, "d_lo": d_lo,
                      "d_hi": d_hi, "nf": nf, "nf_lo": nf_lo, "nf_hi": nf_hi,
                      "ratio": ratio})
    stats.sort(key=lambda s: s["dm"])

    lines = ["# 预实验 + 0812test: 人体距离与近场强度对比\n"]
    lines.append("| 场次 | 窗数 | 人体距离中位 (m) | 距离 IQR (m) | 近场峰中位 | 近场 IQR | 近场/人体 | 备注 |")
    lines.append("|------|------|-----------------|-------------|-----------|----------|----------|------|")
    for s in stats:
        lines.append(f"| {s['sub']} | {s['n']} | {s['dm']:.2f} | {s['d_lo']:.2f}-{s['d_hi']:.2f} "
                     f"| {s['nf']:.3f} | {s['nf_lo']:.3f}-{s['nf_hi']:.3f} "
                     f"| {s['ratio']:.2f} | {QUALITY_NOTE.get(s['sub'], '')} |")
    (OUT_DIR / "compare_stats.md").write_text("\n".join(lines), encoding="utf-8")

    # ── 三合一图 ──
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    # 图1: 近场峰强度箱线, 按距离排序
    ax = axes[0]
    colors = []
    for s in stats:
        colors.append("#d62728" if s["dm"] < NEAR_CUT_M
                      else ("#2ca02c" if s["dm"] < FAR_CUT_M else "#1f77b4"))
    data = [[r["nf_peak"] for r in all_rows if r["subject"] == s["sub"]]
            for s in stats]
    bp = ax.boxplot(data, tick_labels=[s["sub"] for s in stats],
                    patch_artist=True, widths=0.6)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.set_ylabel("近场峰强度 (bin2-6)")
    ax.set_title("近场峰强度 (按人体距离升序)")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#d62728", label=f"近距 <{NEAR_CUT_M}m"),
                       Patch(color="#2ca02c", label=f"甜点 {NEAR_CUT_M}-{FAR_CUT_M}m"),
                       Patch(color="#1f77b4", label=f"远距 >{FAR_CUT_M}m")],
              fontsize=8, loc="upper right")

    # 图2: 近场/人体比 vs 人体距离 (窗级散点)
    ax = axes[1]
    for s in stats:
        rows = [r for r in all_rows if r["subject"] == s["sub"]]
        c = "#d62728" if s["dm"] < NEAR_CUT_M else ("#2ca02c" if s["dm"] < FAR_CUT_M else "#1f77b4")
        ax.scatter([r["body_m"] for r in rows], [r["nf_body_ratio"] for r in rows],
                   s=10, alpha=0.55, color=c, label=s["sub"] if s["dm"] < NEAR_CUT_M else None)
    ax.axhline(1.0, color="gray", ls="--", lw=0.8)
    ax.set_xlabel("人体距离 (m)")
    ax.set_ylabel("近场峰/人体峰比")
    ax.set_title("近场/人体比 vs 人体距离 (30s 窗)")
    ax.legend(fontsize=7, ncol=2, title="近距场次")

    # 图3: 人体距离与近场强度的均值对比柱状
    ax = axes[2]
    x = np.arange(len(stats))
    ax.bar(x - 0.2, [s["dm"] for s in stats], width=0.4, color="#888888",
           label="人体距离 (m)")
    ax.bar(x + 0.2, [s["ratio"] for s in stats], width=0.4,
           color=[("#d62728" if s["dm"] < NEAR_CUT_M
                   else ("#2ca02c" if s["dm"] < FAR_CUT_M else "#1f77b4"))
                  for s in stats],
           label="近场/人体比")
    ax.set_xticks(x, [s["sub"] for s in stats], rotation=45, fontsize=8)
    ax.set_ylabel("距离 (m) / 比值")
    ax.set_title("人体距离 vs 近场/人体比")
    ax.legend(fontsize=8)

    fig.suptitle("预实验全部场次 + 0812test: 人体距离与近场杂波强度", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT_DIR / "nearfield_compare.png", dpi=120)
    plt.close(fig)

    print("\n".join(lines))
    print(f"\n输出: {OUT_DIR / 'nearfield_compare.png'}")


if __name__ == "__main__":
    main()


