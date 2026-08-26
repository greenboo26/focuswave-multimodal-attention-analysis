"""
plot_formal_all.py — 正式实验第一批全部图表（matplotlib 中文期刊规范）
========================================================================
功能: 用 matplotlib 绘制 5 张正式实验第一批图表（替换 R 版, 字体系统稳定）:
      图1 行为汇总 / 图2 行为轨迹 / 图3 生理分布 / 图4 警觉度分布 / 图5 注意×警觉交叉

数据: output/06_正式实验/图表数据/{behavior_summary_long.csv, trajectory_within.csv,
      trajectory_between.csv, physio_dist_long.csv, vigilance_dist.csv,
      vigilance_attention_cross.csv}

输出: output/06_正式实验/图表数据/{behavior_summary, behavior_trajectory,
      physio_dist, vigilance_dist, vigilance_cross}.png

规范: chart-config 方案 A（中文心理学期刊）——SimHei 黑体标题/SimSun 宋体刻度,
      Set2 色盲友好配色, 无网格仅边框

用法:
  cd 08_算法/scripts
  python3.14 plot_formal_all.py

依赖: pandas, matplotlib, numpy
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ============================================================
# 参数声明
# ============================================================
DATA_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验\图表数据")
# 系统中文字体（显式加载, 规避 R 字体系统故障）
font_manager.fontManager.addfont("C:/Windows/Fonts/simhei.ttf")
font_manager.fontManager.addfont("C:/Windows/Fonts/simsun.ttc")
plt.rcParams["font.sans-serif"] = ["SimHei", "SimSun", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

# 字体大小（明显放大: 标题20/轴16/刻度14/图例14）
F_TITLE = 20
F_AXIS = 16
F_TICK = 14
F_LEGEND = 14
DPI = 200

# Set2 色盲友好色板（chart-config 规范）
SET2 = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3",
        "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"]
SUBJ_BEHAV = ["011", "012", "013", "014", "016"]       # 行为有效 5 人
SUBJ_PHYSIO = ["011", "012", "013", "014", "015", "016"]  # 生理 6 人


def _apply_cn_style(ax, title=None, xlabel=None, ylabel=None):
    """应用中文期刊样式: 无网格 + 边框 + 大字体。

    Args:
        ax: matplotlib 轴
        title/xlabel/ylabel: 文本（黑体）
    """
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color("grey")
        spine.set_linewidth(0.8)
    if title:
        ax.set_title(title, fontsize=F_TITLE, fontfamily="SimHei", pad=14)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=F_AXIS, fontfamily="SimHei", labelpad=8)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=F_AXIS, fontfamily="SimHei", labelpad=8)
    ax.tick_params(labelsize=F_TICK)


def fig1_behavior_summary():
    """图1: 行为汇总（4 面板: 误按率/遗漏率/预判率/反应时）。"""
    df = pd.read_csv(DATA_DIR / "behavior_summary_long.csv", encoding="utf-8-sig")
    df["subject"] = df["subject"].astype(str).str.zfill(3)
    metric_cn = {"commission": "误按率 (%)", "omission": "遗漏率 (%)",
                 "preempt_rate": "预判率 (%)", "rt_mean": "反应时 (ms)"}
    df["metric_cn"] = df["metric"].map(metric_cn)

    fig, axes = plt.subplots(1, 4, figsize=(14.5, 4.6))
    for ax, (m, cn) in zip(axes, metric_cn.items()):
        sub = df[df["metric"] == m]
        colors = [SET2[SUBJ_BEHAV.index(s)] for s in sub["subject"]]
        ax.bar(sub["subject"], sub["value"], color=colors, width=0.62, alpha=0.85)
        ax.scatter(sub["subject"], sub["value"], s=50, facecolor="white",
                   edgecolor="grey", linewidth=1.0, zorder=3)
        _apply_cn_style(ax, title=cn, xlabel="被试编号")
        ax.set_xticklabels(SUBJ_BEHAV, fontfamily="SimSun")
    fig.suptitle("正式实验第一批 SART 行为指标",
                 fontsize=22, fontfamily="SimHei", y=1.02)
    fig.text(0.5, 0.92, "行为有效被试 5 人（sub-015 规则理解错误已排除）",
             ha="center", fontsize=13, fontfamily="SimSun", color="grey")
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(DATA_DIR / "behavior_summary.png", dpi=DPI, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def fig2_behavior_trajectory():
    """图2: 行为轨迹（左 Block 内 4 段 / 右 Block 间 3 block）。"""
    within = pd.read_csv(DATA_DIR / "trajectory_within.csv", encoding="utf-8-sig")
    between = pd.read_csv(DATA_DIR / "trajectory_between.csv", encoding="utf-8-sig")
    within["subject"] = within["subject"].astype(str).str.zfill(3)
    between["subject"] = between["subject"].astype(str).str.zfill(3)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左: Block 内
    ax = axes[0]
    for s in SUBJ_BEHAV:
        d = within[within["subject"] == s]
        ax.plot(d["seg"], d["comm_rate"], color="grey", linewidth=0.8, alpha=0.7)
        ax.scatter(d["seg"], d["comm_rate"], color="grey", s=20, alpha=0.7)
    grp = within.groupby("seg")["comm_rate"].mean()
    ax.plot(grp.index, grp.values, color="#D95F02", linewidth=2.2)
    ax.scatter(grp.index, grp.values, color="#D95F02", s=70, marker="D", zorder=3)
    ax.set_xticks([1, 2, 3, 4])
    _apply_cn_style(ax, title="Block 内轨迹", xlabel="Block 内段位", ylabel="误按率 (%)")

    # 右: Block 间
    ax = axes[1]
    for s in SUBJ_BEHAV:
        d = between[between["subject"] == s]
        ax.plot(d["block"], d["comm_rate"], color="grey", linewidth=0.8, alpha=0.7)
        ax.scatter(d["block"], d["comm_rate"], color="grey", s=20, alpha=0.7)
    grp = between.groupby("block")["comm_rate"].mean()
    ax.plot(grp.index, grp.values, color="#D95F02", linewidth=2.2)
    ax.scatter(grp.index, grp.values, color="#D95F02", s=70, marker="D", zorder=3)
    ax.set_xticks([1, 2, 3])
    _apply_cn_style(ax, title="Block 间轨迹", xlabel="Block", ylabel="误按率 (%)")

    fig.suptitle("正式实验第一批误按率轨迹", fontsize=22, fontfamily="SimHei", y=1.02)
    fig.text(0.5, 0.93, "个体灰线 + 组均值橙线（n = 5）",
             ha="center", fontsize=13, fontfamily="SimSun", color="grey")
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(DATA_DIR / "behavior_trajectory.png", dpi=DPI, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def fig3_physio_dist():
    """图3: 生理分布（3 面板: HR/SDNN/RMSSD, 小提琴+箱线）。"""
    df = pd.read_csv(DATA_DIR / "physio_dist_long.csv", encoding="utf-8-sig")
    df["subject"] = df["subject"].astype(str).str.zfill(3)
    metric_cn = {"hr_bpm": "心率 (bpm)", "sdnn_ms": "SDNN (ms)", "rmssd_ms": "RMSSD (ms)"}
    df["metric_cn"] = df["metric"].map(metric_cn)

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5))
    for ax, (m, cn) in zip(axes, metric_cn.items()):
        sub = df[df["metric"] == m]
        datasets = [sub[sub["subject"] == s]["value"].dropna().values
                    for s in SUBJ_PHYSIO]
        colors = [SET2[i] for i in range(len(SUBJ_PHYSIO))]
        vp = ax.violinplot(datasets, positions=range(len(SUBJ_PHYSIO)),
                           showmeans=False, showextrema=False)
        for body, c in zip(vp["bodies"], colors):
            body.set_facecolor(c)
            body.set_alpha(0.55)
            body.set_edgecolor("grey")
            body.set_linewidth(0.6)
        bp = ax.boxplot(datasets, positions=range(len(SUBJ_PHYSIO)),
                        widths=0.18, patch_artist=True,
                        showfliers=True, flierprops=dict(markersize=3, alpha=0.4))
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor("white")
            patch.set_alpha(0.9)
            patch.set_linewidth(0.8)
        for key in ["whiskers", "caps", "medians"]:
            for ln in bp[key]:
                ln.set_color("black")
                ln.set_linewidth(0.8)
        _apply_cn_style(ax, title=cn, xlabel="被试编号")
        ax.set_xticks(range(len(SUBJ_PHYSIO)))
        ax.set_xticklabels(SUBJ_PHYSIO, fontfamily="SimSun")

    fig.suptitle("正式实验第一批毫米波生理指标分布", fontsize=22, fontfamily="SimHei", y=1.02)
    fig.text(0.5, 0.92, "6 生理被试全程可信窗（sub-015 行为无效但生理保留）",
             ha="center", fontsize=13, fontfamily="SimSun", color="grey")
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(DATA_DIR / "physio_dist.png", dpi=DPI, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def fig4_vigilance_dist():
    """图4: 警觉度分布（6 被试 × 4 点, 堆叠柱）。"""
    df = pd.read_csv(DATA_DIR / "vigilance_dist.csv", encoding="utf-8-sig")
    df["subject"] = df["subject"].astype(str).str.zfill(3)
    vig_labels = {1: "极度困倦", 2: "比较困倦", 3: "比较清醒", 4: "极度清醒"}
    df["vigilance_cn"] = df["vigilance"].map(vig_labels)

    # 堆叠: 每被试 × 4 警觉度计数
    pivot = df.pivot_table(index="subject", columns="vigilance_cn",
                           values="vigilance", aggfunc="count",
                           observed=False).fillna(0)
    pivot = pivot.reindex(columns=list(vig_labels.values()))
    # OrRd 反向: 困倦=深红, 清醒=浅
    orrd = ["#7f0000", "#b30000", "#fc9272", "#fee0d2"]

    fig, ax = plt.subplots(figsize=(11, 5))
    bottom = np.zeros(len(SUBJ_PHYSIO))
    for i, cn in enumerate(vig_labels.values()):
        vals = pivot[cn].values
        ax.bar(range(len(SUBJ_PHYSIO)), vals, bottom=bottom, width=0.62,
               color=orrd[i], label=cn)
        bottom += vals
    _apply_cn_style(ax, title=None, xlabel="被试编号", ylabel="探针数（个）")
    ax.set_xticks(range(len(SUBJ_PHYSIO)))
    ax.set_xticklabels(SUBJ_PHYSIO, fontfamily="SimSun")
    ax.legend(title="警觉度", fontsize=F_LEGEND, title_fontsize=F_LEGEND,
              loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    ax.set_title("正式实验第一批警觉度（清醒程度）分布",
                 fontsize=F_TITLE, fontfamily="SimHei", pad=14)
    ax.text(0.5, -0.18, "每被试 30 探针, 1=极度困倦 → 4=极度清醒",
            transform=ax.transAxes, ha="center", fontsize=13,
            fontfamily="SimSun", color="grey")
    fig.savefig(DATA_DIR / "vigilance_dist.png", dpi=DPI, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def fig5_vigilance_cross():
    """图5: 注意状态 × 警觉度 交叉（比例堆叠）。"""
    df = pd.read_csv(DATA_DIR / "vigilance_attention_cross.csv", encoding="utf-8-sig")
    att_labels = {1: "完全任务聚焦", 2: "实验相关但未聚焦分拣任务", 3: "任务无关思维", 4: "思维空白"}
    vig_labels = {1: "极度困倦", 2: "比较困倦", 3: "比较清醒", 4: "极度清醒"}
    df["attention_cn"] = df["attention"].map(att_labels)
    df["vigilance_cn"] = df["vigilance"].map(vig_labels)

    pivot = df.pivot_table(index="attention_cn", columns="vigilance_cn",
                           values="count", aggfunc="sum",
                           observed=False).fillna(0)
    pivot = pivot.reindex(columns=list(vig_labels.values()))
    pivot = pivot.div(pivot.sum(axis=1), axis=0)  # 转比例
    orrd = ["#7f0000", "#b30000", "#fc9272", "#fee0d2"]

    fig, ax = plt.subplots(figsize=(10, 5))
    cats = list(att_labels.values())
    bottom = np.zeros(len(cats))
    for i, cn in enumerate(vig_labels.values()):
        vals = pivot[cn].values
        ax.bar(range(len(cats)), vals, bottom=bottom, width=0.6,
               color=orrd[i], label=cn)
        bottom += vals
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    _apply_cn_style(ax, title=None, xlabel="注意状态", ylabel="比例")
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, fontfamily="SimSun")
    ax.legend(title="警觉度", fontsize=F_LEGEND, title_fontsize=F_LEGEND,
              loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    ax.set_title("注意状态 × 警觉度（清醒程度）交叉",
                 fontsize=F_TITLE, fontfamily="SimHei", pad=14)
    ax.text(0.5, -0.18, "走神/大脑空白状态下困倦比例高于专注（6 被试 180 探针）",
            transform=ax.transAxes, ha="center", fontsize=13,
            fontfamily="SimSun", color="grey")
    fig.savefig(DATA_DIR / "vigilance_cross.png", dpi=DPI, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig1_behavior_summary()
    fig2_behavior_trajectory()
    fig3_physio_dist()
    fig4_vigilance_dist()
    fig5_vigilance_cross()
    print("5 张图已全部生成（matplotlib, 大字体）")
