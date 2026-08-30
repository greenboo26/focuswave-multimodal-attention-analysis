"""毫米波信号处理流程路线图（报告 4.5.4 方法部分用）。

raw ADC IQ -> 距离 FFT -> 通道/距离单元选择 -> 相位位移 -> 带通分离
-> 时/频域估计 -> fusion -> 质量门控 -> HR/BR/运动指标 -> 分析窗口。

数据输入：无（纯框图）
输出文件：D:/Project/厚粲杯/08_算法/output/06_正式实验/毫米波验证图_0831/MMWAVE_PIPELINE_DIAGRAM_2026-08-31.png（+svg）
项目：厚粲杯 FocusWave | 分析脚本 v1 | 创建日期：2026-08-31
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_DIR = Path(
    r"D:\Project\厚粲杯\08_算法\output\06_正式实验\毫米波验证图_0831"
)

COLOR_MAIN = "#0E7C7B"
COLOR_BR = "#4A7BA6"
COLOR_HR = "#C2543D"
COLOR_OUT = "#5A6B7B"
FILL_MAIN = "#EAF4F4"
FILL_BR = "#EDF3F8"
FILL_HR = "#F9EDEB"
FILL_OUT = "#EEF1F4"
LINE_GRAY = "#8A9AA5"
LINE_DARK = "#4A5B66"

for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def box(ax, x, y, w, h, text, edge, fill, fs=9.5, line_width=1.1):
    """画一个圆角矩形流程框，文字居中。"""
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.06,rounding_size=0.10",
        linewidth=line_width, edgecolor=edge, facecolor=fill,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color="#1F2D33", linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, color=LINE_DARK, lw=1.2):
    """画水平或垂直箭头。"""
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=12,
        linewidth=lw, color=color,
    ))


def line(ax, x1, y1, x2, y2, color=LINE_GRAY, lw=1.1):
    """画无箭头线段（折线总线用）。"""
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw,
            solid_capstyle="round")


def main() -> None:
    fig, ax = plt.subplots(figsize=(10.6, 7.6), dpi=300)
    ax.set_xlim(0, 10.6)
    ax.set_ylim(0, 7.6)
    ax.axis("off")

    BW, BH = 1.62, 0.92
    y1 = 6.25
    y2 = 4.65
    y3 = 3.05
    y4 = 1.45
    y5 = 0.15

    # 第一行：信号形成
    box(ax, 0.18, y1, BW, BH, "8 通道 I/Q 原始数据\n（66 GHz，约 99 Hz）",
        COLOR_MAIN, FILL_MAIN)
    box(ax, 2.30, y1, BW, BH, "加窗 + 256 点\n距离 FFT", COLOR_MAIN, FILL_MAIN)
    box(ax, 4.42, y1, BW, BH, "通道与距离单元选择\n（功率、SNR、时间稳定性）",
        COLOR_MAIN, FILL_MAIN)
    box(ax, 6.54, y1, BW, BH, "相位展开\n胸壁相对位移", COLOR_MAIN, FILL_MAIN)

    arrow(ax, 1.80, y1 + BH / 2, 2.30, y1 + BH / 2)
    arrow(ax, 3.92, y1 + BH / 2, 4.42, y1 + BH / 2)
    arrow(ax, 6.04, y1 + BH / 2, 6.54, y1 + BH / 2)

    # 第二行：带通分离（呼吸与心搏并行分支）+ 运动指标
    box(ax, 0.18, y2, BW, BH, "呼吸成分带通\n0.10～0.50 Hz", COLOR_BR, FILL_BR)
    box(ax, 2.30, y2, BW, BH, "心搏成分带通\n0.8～2.0 Hz", COLOR_HR, FILL_HR)
    box(ax, 4.42, y2, BW, BH, "VMD 窄带补充\n（K=3，呼吸频率引导）",
        COLOR_MAIN, FILL_MAIN, fs=9)
    box(ax, 6.54, y2, BW, BH, "身体运动\n质量指标", COLOR_OUT, FILL_OUT)

    # 位移 -> 呼吸/心搏 并行分支（正交折线）
    bus_y = y2 + BH + 0.42
    line(ax, 7.35, y1, 7.35, bus_y)
    line(ax, 7.35, bus_y, 0.99, bus_y)
    line(ax, 0.99, bus_y, 0.99, y2 + BH, LINE_GRAY)
    line(ax, 3.11, bus_y, 3.11, y2 + BH)
    arrow(ax, 0.99, y2 + BH + 0.18, 0.99, y2 + BH, color=LINE_GRAY)
    arrow(ax, 3.11, y2 + BH + 0.18, 3.11, y2 + BH)
    # 心搏带通 -> VMD 补充
    arrow(ax, 3.92, y2 + BH / 2, 4.42, y2 + BH / 2, color=LINE_GRAY)

    # 第三行：估计
    box(ax, 0.18, y3, BW, BH, "呼吸率估计\n（频域谱峰）", COLOR_BR, FILL_BR)
    box(ax, 2.30, y3, BW, BH, "时域峰间隔\n稳健估计", COLOR_HR, FILL_HR)
    box(ax, 4.42, y3, BW, BH, "频域谱峰估计", COLOR_HR, FILL_HR)

    arrow(ax, 0.99, y2, 0.99, y3 + BH, color=LINE_GRAY)
    arrow(ax, 3.11, y2, 3.11, y3 + BH)
    arrow(ax, 5.23, y2, 5.23, y3 + BH, color=LINE_GRAY)

    # 第四行：fusion -> 质量门控 -> 输出
    box(ax, 2.30, y4, BW, BH, "时频一致性融合", COLOR_MAIN, FILL_MAIN)
    box(ax, 4.42, y4, BW, BH, "质量门控\n（SNR、相位连续性、\n反射位置稳定性）",
        COLOR_MAIN, FILL_MAIN, fs=8.8)
    box(ax, 6.54, y4, BW, BH, "HR / BR /\n身体运动指标", COLOR_OUT, FILL_OUT)

    arrow(ax, 3.11, y3, 3.11, y4 + BH)
    arrow(ax, 5.23, y3, 5.23, y4 + BH, color=LINE_GRAY)
    arrow(ax, 3.92, y4 + BH / 2, 4.42, y4 + BH / 2)
    arrow(ax, 6.04, y4 + BH / 2, 6.54, y4 + BH / 2)
    # 运动指标并入最终输出
    line(ax, 7.35, y2, 7.35, y4 + BH + 0.18)
    arrow(ax, 7.35, y4 + BH + 0.18, 7.35, y4 + BH, color=LINE_GRAY)

    # 第五行：分析窗口（正交折线总线）
    box(ax, 0.18, y5, 4.0, BH, "Block 时间进程", COLOR_OUT, FILL_OUT)
    box(ax, 4.80, y5, 2.4, BH, "试次 / 错误前窗口", COLOR_OUT, FILL_OUT)
    box(ax, 7.80, y5, 2.4, BH, "探针前窗口", COLOR_OUT, FILL_OUT)

    bus_y5 = y5 + BH + 0.26
    line(ax, 7.35, y4, 7.35, bus_y5)
    line(ax, 7.35, bus_y5, 2.18, bus_y5)
    line(ax, 2.18, bus_y5, 2.18, y5 + BH)
    line(ax, 6.00, bus_y5, 6.00, y5 + BH)
    line(ax, 9.00, bus_y5, 9.00, y5 + BH)
    arrow(ax, 2.18, y5 + BH + 0.18, 2.18, y5 + BH, color=LINE_GRAY)
    arrow(ax, 6.00, y5 + BH + 0.18, 6.00, y5 + BH, color=LINE_GRAY)
    arrow(ax, 9.00, y5 + BH + 0.18, 9.00, y5 + BH, color=LINE_GRAY)

    fig.tight_layout(pad=0.3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_PIPELINE_DIAGRAM_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


if __name__ == "__main__":
    main()
