"""毫米波 BR（呼吸率）验证散点图（统计结果图）。

毫米波 BR vs RSP 呼吸带金标准，targeted 验证 3 被试。

数据输入：D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831\all_subjects_pre30s_selector_hr.csv
输出文件：docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/MMWAVE_BR_SCATTER_2026-08-31.png（+svg）
项目：厚粲杯 FocusWave | 分析脚本 v1 | 创建日期：2026-08-31
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

DATA = Path(
    r"D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831"
    r"\all_subjects_pre30s_selector_hr.csv"
)
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "results" / "2026-08-31_MMWAVE_PRE30S_SELECTOR_HR"

COLOR_POINT = "#0E7C7B"
COLOR_REF = "#9A9A9A"

for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    rows = list(csv.DictReader(DATA.open(encoding="utf-8-sig")))
    pairs = [
        (float(r["rsp_br_bpm"]), float(r["br_bpm"]))
        for r in rows
        if r["rsp_br_bpm"] and r["br_bpm"]
    ]
    rsp = np.array([p[0] for p in pairs])
    br = np.array([p[1] for p in pairs])
    err = np.abs(br - rsp)
    mae = float(np.mean(err))
    medae = float(np.median(err))
    n = len(pairs)

    fig, ax = plt.subplots(figsize=(6.6, 5.2), dpi=300)
    lim = (4, 32)
    ax.plot(lim, lim, color=COLOR_REF, linestyle="--", linewidth=0.9, zorder=1)
    ax.scatter(rsp, br, s=34, color=COLOR_POINT, alpha=0.8, edgecolors="white", linewidths=0.4, zorder=2)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("RSP 呼吸率（次/分）", fontsize=10.5)
    ax.set_ylabel("毫米波呼吸率（次/分）", fontsize=10.5)
    ax.tick_params(labelsize=9.5)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_BR_SCATTER_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


if __name__ == "__main__":
    main()
