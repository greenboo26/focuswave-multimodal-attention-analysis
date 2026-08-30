"""毫米波数据覆盖热图（统计结果图）。

116 场 × 20 probe 的 OBSERVED / STRUCTURAL_MISSING 矩阵（J 盘 72 场 + E 盘 44 场）。

数据输入：D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_probe_merge_ready.csv + mmwave_probe_merge_ready_E.csv
输出文件：docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/MMWAVE_COVERAGE_HEATMAP_2026-08-31.png（+svg）
项目：厚粲杯 FocusWave | 分析脚本 v1 | 创建日期：2026-08-31
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

DATA_J = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_probe_merge_ready.csv")
DATA_E = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_probe_merge_ready_E.csv")
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "results" / "2026-08-31_MMWAVE_PRE30S_SELECTOR_HR"

COLOR_OBS = "#0E7C7B"
COLOR_MISS = "#D8A7A7"

for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def load(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def main() -> None:
    rows = load(DATA_J) + load(DATA_E)
    sessions = sorted({r["session_id"] for r in rows}, key=lambda s: int(s.split("-")[1]))
    n_sess = len(sessions)
    n_probe = 20

    matrix = np.zeros((n_sess, n_probe), dtype=np.int8)
    for r in rows:
        i = sessions.index(r["session_id"])
        j = int(r["probe_id"].split("-")[1]) - 1
        matrix[i, j] = 1 if r["mmwave_state"] == "OBSERVED" else -1

    fig, ax = plt.subplots(figsize=(8.8, 6.6), dpi=300)
    cmap = matplotlib.colors.ListedColormap([COLOR_MISS, "white", COLOR_OBS])
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=-1, vmax=1, interpolation="nearest")
    ax.set_yticks(range(n_sess))
    ax.set_yticklabels(sessions, fontsize=5.6)
    ax.set_xticks(range(0, n_probe, 4))
    ax.set_xticklabels([f"p{i + 1}" for i in range(0, n_probe, 4)], fontsize=8)
    ax.set_xlabel("block 内 probe 序号", fontsize=10)
    ax.set_ylabel("session", fontsize=10)
    ax.grid(False)

    obs = int((matrix == 1).sum())
    miss = int((matrix == -1).sum())
    legend = [
        matplotlib.patches.Patch(color=COLOR_OBS, label=f"OBSERVED（{obs}）"),
        matplotlib.patches.Patch(color=COLOR_MISS, label=f"STRUCTURAL_MISSING（{miss}）"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=8.5, frameon=False, bbox_to_anchor=(1.0, -0.06))

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_COVERAGE_HEATMAP_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


if __name__ == "__main__":
    main()
