"""毫米波 fusion 纠错机制图（统计结果图）。

展示完整 selector 链的 time/frequency fusion 如何把谱峰锁错频率的 HR 拉回
ECG 真值附近。60 窗口 targeted 验证（3 被试），25s 配置。

数据输入：D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831\all_subjects_pre30s_selector_hr.csv
输出文件：docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/MMWAVE_FUSION_MECHANISM_2026-08-31.png（+svg）
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

# 仓库视觉原则：毫米波语义色（深青）+ 辅助浅灰蓝；颜色不是唯一编码（空心/实心区分）
COLOR_FUSED = "#0E7C7B"
COLOR_SPECTRAL = "#8FA6B2"
COLOR_REF = "#9A9A9A"

# 中文字体（中文心理学期刊：图内宋体 + Arial 数字）
for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    rows = list(csv.DictReader(DATA.open(encoding="utf-8-sig")))
    ecg = np.array([float(r["ecg_hr_bpm"]) for r in rows if r["ecg_hr_bpm"]])
    fused = np.array([float(r["hr_25s_fused_bpm"]) for r in rows if r["hr_25s_fused_bpm"] and r["ecg_hr_bpm"]])
    spectral = np.array([float(r["hr_25s_spectral_bpm"]) for r in rows if r["hr_25s_spectral_bpm"] and r["ecg_hr_bpm"]])
    ecg_f = np.array([float(r["ecg_hr_bpm"]) for r in rows if r["hr_25s_fused_bpm"] and r["ecg_hr_bpm"]])
    ecg_s = np.array([float(r["ecg_hr_bpm"]) for r in rows if r["hr_25s_spectral_bpm"] and r["ecg_hr_bpm"]])
    n = len(ecg_f)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=300)

    # 面板 A：散点（ECG vs 毫米波 HR），y=x 参考线
    ax = axes[0]
    lim = (45, 115)
    ax.plot(lim, lim, color=COLOR_REF, linestyle="--", linewidth=0.9, zorder=1)
    ax.scatter(ecg_s, spectral, s=34, facecolors="none", edgecolors=COLOR_SPECTRAL,
               linewidths=1.2, label="谱峰单独（未 fusion）", zorder=2)
    ax.scatter(ecg_f, fused, s=26, color=COLOR_FUSED, label="完整链（fusion 后）", zorder=3)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("ECG 心率（bpm）", fontsize=10.5)
    ax.set_ylabel("毫米波心率（bpm）", fontsize=10.5)
    ax.set_title("A 与金标准的一致性", fontsize=11.5)
    ax.tick_params(labelsize=9.5)
    ax.legend(fontsize=9, frameon=False, loc="upper left")

    # 面板 B：绝对误差箱线图
    ax = axes[1]
    err_fused = np.abs(fused - ecg_f)
    err_spectral = np.abs(spectral - ecg_s)
    bp = ax.boxplot(
        [err_spectral, err_fused],
        tick_labels=["谱峰单独", "完整链（fusion）"],
        widths=0.5,
        patch_artist=True,
        medianprops=dict(color="#1A1A1A", linewidth=1.4),
        whiskerprops=dict(color="#3A3A3A"),
        capprops=dict(color="#3A3A3A"),
        flierprops=dict(marker="o", markersize=3, markerfacecolor="none", markeredgecolor="#3A3A3A", alpha=0.5),
    )
    bp["boxes"][0].set_facecolor("#C9D6DC")
    bp["boxes"][1].set_facecolor(COLOR_FUSED)
    ax.set_ylabel("绝对误差 |HR - ECG|（bpm）", fontsize=10.5)
    ax.set_title("B 误差分布", fontsize=11.5)
    ax.tick_params(labelsize=9.5)
    ax.text(1, np.percentile(err_spectral, 92), f"MAE={np.mean(err_spectral):.1f}", ha="center", fontsize=9)
    ax.text(2, np.percentile(err_fused, 92), f"MAE={np.mean(err_fused):.1f}", ha="center", fontsize=9)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_FUSION_MECHANISM_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


if __name__ == "__main__":
    main()
