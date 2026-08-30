"""毫米波 HR 时间轨迹示例图（结果部分 5.4.2 用）。

sub-9779 的 20 个 pre_30s 窗口：毫米波 fused HR（25 s）曲线 + ECG 金标准点。
该被试为历史锁半频最严重者，展示完整链后的跟踪质量。

数据输入：D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831\sub-9779_pre30s_selector_hr.csv
输出文件：docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/MMWAVE_HR_TRAJECTORY_2026-08-31.png（+svg）
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
    r"\sub-9779_pre30s_selector_hr.csv"
)
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "results" / "2026-08-31_MMWAVE_PRE30S_SELECTOR_HR"

COLOR_MMWAVE = "#0E7C7B"
COLOR_ECG = "#C2543D"

for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    rows = list(csv.DictReader(DATA.open(encoding="utf-8-sig")))
    rows.sort(key=lambda r: int(r["probe_onset_unix_ms"]))
    t = np.arange(len(rows))
    ecg = np.array([float(r["ecg_hr_bpm"]) for r in rows])
    fused = np.array([float(r["hr_25s_fused_bpm"]) if r["hr_25s_fused_bpm"] else np.nan for r in rows])
    spectral = np.array([float(r["hr_25s_spectral_bpm"]) if r["hr_25s_spectral_bpm"] else np.nan for r in rows])

    fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=300)
    ax.plot(t, spectral, color="#A8B9C4", marker="o", markersize=3.2, linewidth=0.9,
            label="谱峰单独", alpha=0.85)
    ax.plot(t, fused, color=COLOR_MMWAVE, marker="o", markersize=4.0, linewidth=1.2,
            label="完整链（fusion）")
    ax.plot(t, ecg, color=COLOR_ECG, marker="s", markersize=4.5, linewidth=1.3,
            label="ECG 金标准")
    ax.set_xlabel("pre_30s 窗口序号", fontsize=10)
    ax.set_ylabel("心率（bpm）", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.set_ylim(45, 105)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_HR_TRAJECTORY_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


if __name__ == "__main__":
    main()
