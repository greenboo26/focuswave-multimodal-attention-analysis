"""毫米波 HR Bland-Altman 一致性图（统计结果图）。

25 s fused 配置（完整 selector 链）vs ECG 金标准，targeted 验证 3 被试。

数据输入：D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831\all_subjects_pre30s_selector_hr.csv
输出文件：docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/MMWAVE_BLAND_ALTMAN_HR_2026-08-31.png（+svg）
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

# 仓库视觉原则：毫米波语义色（深青）
COLOR_POINT = "#0E7C7B"
COLOR_BIAS = "#1A1A1A"
COLOR_LOA = "#9A9A9A"

for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    rows = list(csv.DictReader(DATA.open(encoding="utf-8-sig")))
    pairs = [
        (float(r["ecg_hr_bpm"]), float(r["hr_25s_fused_bpm"]))
        for r in rows
        if r["ecg_hr_bpm"] and r["hr_25s_fused_bpm"]
    ]
    ecg = np.array([p[0] for p in pairs])
    fused = np.array([p[1] for p in pairs])
    mean_hr = (ecg + fused) / 2.0
    diff = fused - ecg
    bias = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1))
    loa_lo = bias - 1.96 * sd
    loa_hi = bias + 1.96 * sd
    mae = float(np.mean(np.abs(diff)))
    n = len(pairs)

    fig, ax = plt.subplots(figsize=(7.6, 5.0), dpi=300)
    ax.scatter(mean_hr, diff, s=30, color=COLOR_POINT, alpha=0.75, edgecolors="white", linewidths=0.4)
    xlim = (min(mean_hr) - 3, max(mean_hr) + 3)
    ax.axhline(bias, color=COLOR_BIAS, linewidth=1.1)
    ax.axhline(loa_hi, color=COLOR_LOA, linestyle="--", linewidth=0.9)
    ax.axhline(loa_lo, color=COLOR_LOA, linestyle="--", linewidth=0.9)
    ax.axhline(0, color="#CCCCCC", linewidth=0.7)
    ax.text(xlim[1] - 0.3, bias + 1.2, f"bias = {bias:.1f}", ha="right", fontsize=9.5, color=COLOR_BIAS)
    ax.text(xlim[1] - 0.3, loa_hi + 1.2, f"+1.96 SD = {loa_hi:.1f}", ha="right", fontsize=9, color="#666666")
    ax.text(xlim[1] - 0.3, loa_lo - 2.5, f"-1.96 SD = {loa_lo:.1f}", ha="right", fontsize=9, color="#666666")
    ax.set_xlim(xlim)
    ax.set_xlabel("（毫米波 HR + ECG HR）/ 2（bpm）", fontsize=10.5)
    ax.set_ylabel("毫米波 HR - ECG HR（bpm）", fontsize=10.5)
    ax.tick_params(labelsize=9.5)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_BLAND_ALTMAN_HR_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


if __name__ == "__main__":
    main()
