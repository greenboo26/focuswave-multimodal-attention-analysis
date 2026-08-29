"""
休息段 HRV 每被试独立图
=======================
对 9 名被试各生成一张图: 5 个休息段（子图）内 30s 窗的
HRV 变化（RMSSD 实线 + SDNN 虚线），不可信窗留断点。

用法:
    cd 08_算法/scripts
    python plot_rest_hrv_per_subject.py

输出: output/预实验/03_跨被试/09_预实验-restHRV变化/per_subject/
"""

import json
from pathlib import Path

import numpy as np

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"
REST_DIR = OUTPUT_ROOT / "预实验" / "02_全程窗"
OUT_DIR = (OUTPUT_ROOT / "预实验" / "03_跨被试"
           / "09_预实验-restHRV变化" / "per_subject")

SUBJECTS = ["003", "004", "005", "006", "007", "008", "009", "010"]  # 剔除 001/002 摆位失误 + 000 练习效应
BASELINE_CSV = (OUTPUT_ROOT / "预实验" / "03_跨被试"
                / "09_预实验-rest基线" / "rest_baseline_summary.csv")


def load_windows(subject: str) -> list[dict]:
    """加载单被试 rest v8 全部窗（含 poor, 保留段/窗/时间/指标）。"""
    p = REST_DIR / f"09_预实验-SUB{subject}-REST-HRV-v8" / f"sub{subject}_rest_hrv_windows.json"
    d = json.load(open(p, encoding="utf-8"))
    return d.get("rows", [])


def load_task_baseline(subject: str) -> tuple[float | None, float | None]:
    """读基线表取该被试任务段 RMSSD/SDNN 均值（休息前对比参考）。

    参数:
        subject: 被试编号
    返回:
        (task_rmssd_ms, task_sdnn_ms), 缺失为 None
    """
    import csv
    for r in csv.DictReader(open(BASELINE_CSV, encoding="utf-8-sig")):
        if r["subject"] == subject:
            return (float(r["task_rmssd"]) if r.get("task_rmssd") else None,
                    float(r["task_sdnn"]) if r.get("task_sdnn") else None)
    return None, None


def plot_subject(subject: str) -> None:
    """画单被试 5 段休息 HRV 图（1×5 子图, RMSSD 实线 + SDNN 虚线,
    水平虚线 = 该被试任务段均值, 对比休息前后的 HRV 水平）。

    参数:
        subject: 被试编号
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    rows = load_windows(subject)
    task_rm, task_sd = load_task_baseline(subject)
    segs = sorted({r["segment"] for r in rows},
                  key=lambda x: int(x.replace("rest", "")))
    n_ok = sum(1 for r in rows if r.get("quality") == "ok")

    fig, axes = plt.subplots(1, len(segs), figsize=(3.2 * len(segs), 3.6),
                             sharey=True)
    if len(segs) == 1:
        axes = [axes]

    for ax, seg in zip(axes, segs):
        seg_rows = sorted([r for r in rows if r["segment"] == seg],
                          key=lambda x: x["window"])
        xs_ok, rm_ok, sd_ok = [], [], []
        for r in seg_rows:
            if r.get("quality") != "ok":
                continue
            t_mid = (r["t_start_s"] + r["t_end_s"]) / 2 / 60
            xs_ok.append(t_mid)
            rm_ok.append(r.get("hrv", {}).get("RMSSD_ms"))
            sd_ok.append(r.get("hrv", {}).get("SDNN_ms"))
        # 任务段均值参考线（休息前对比）
        if task_rm is not None:
            ax.axhline(task_rm, color="#2e86c1", linestyle=":", linewidth=1.2,
                       alpha=0.7)
        if task_sd is not None:
            ax.axhline(task_sd, color="#e67e22", linestyle=":", linewidth=1.2,
                       alpha=0.7)
        ax.plot(xs_ok, rm_ok, "o-", color="#2e86c1", markersize=5,
                label="RMSSD (休息)")
        ax.plot(xs_ok, sd_ok, "s--", color="#e67e22", markersize=4,
                label="SDNN (休息)")
        # 无可信窗/仅 1 窗时加标注, 避免看图疑惑
        n_ok_seg = len(xs_ok)
        if n_ok_seg == 0:
            ax.text(0.5, 0.5, "无可信窗", transform=ax.transAxes,
                    ha="center", va="center", color="#95a5a6", fontsize=11)
        elif n_ok_seg == 1:
            ax.text(0.5, 0.9, "仅 1 可信窗", transform=ax.transAxes,
                    ha="center", va="top", color="#95a5a6", fontsize=9)
        ax.set_title(seg.replace("rest", "休息"), fontsize=10)
        ax.set_xlabel("段内时间 (min)")
        if ax is axes[0]:
            ax.set_ylabel("HRV (ms)")
        ax.grid(True, alpha=0.3)

    handles, labels = axes[0].get_legend_handles_labels()
    # 图例加任务参考线
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], color="#2e86c1", linestyle=":",
                          label="任务 RMSSD 均值"))
    handles.append(Line2D([0], [0], color="#e67e22", linestyle=":",
                          label="任务 SDNN 均值"))
    fig.legend(handles=handles, loc="upper right", fontsize=8, ncol=2)
    fig.suptitle(f"sub-{subject} 休息段 HRV 变化 vs 任务均值"
                 f"（可信窗 n={n_ok}; 点线=任务段均值）", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / f"sub{subject}_rest_hrv_per_segment.png"
    fig.savefig(png, dpi=150)
    plt.close(fig)
    print(f"  {png.name} (可信 {n_ok}/{len(rows)} 窗, "
          f"任务 RMSSD={task_rm}, SDNN={task_sd})")


def main() -> None:
    """对 9 名被试逐一出图。"""
    print(f"输出目录: {OUT_DIR}")
    for s in SUBJECTS:
        plot_subject(s)
    print("完成")


if __name__ == "__main__":
    main()


