"""
compare_preexp_hrv.py — 预实验全被试（000-007）HR/HRV 跨被试分布对比
====================================================================
版本: v1.0 (2026-08-10)
功能: 对 8 个预实验被试的可信窗做跨被试分布对比:
      HR/SDNN/RMSSD/BR 生理指标 + RT/误错率行为指标 + 可用率 + 探针标签分布
数据: 09_预实验-SUB{XXX}-FULL/sub{XXX}_full_windows.json（analyze_mmwave_full 产出）
输出: output/预实验/03_跨被试/09_预实验-SUBJECTS-COMPARE/
        preexp_hrv_distributions.png  ← 生理指标小提琴图（2×2）
        preexp_behavior_distributions.png ← RT/误错率小提琴图（1×2）
        preexp_usability_probes.png   ← 可用率条形图 + 探针标签分布
        preexp_hrv_summary.json       ← 各被试指标中位数/IQR/探针标签统计
用法:
  cd 08_算法/scripts
  python compare_preexp_hrv.py
依赖: numpy, matplotlib
"""

import json
import glob
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent / "output" / "预实验"
OUT_DIR = OUT_ROOT / "03_跨被试" / "09_预实验-SUBJECTS-COMPARE"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUBJECTS = ["000", "001", "002", "003", "004", "005", "006", "007"]
PHYSIO_METRICS = [("hr_bpm", "心率 (bpm)"), ("sdnn_ms", "SDNN (ms)"),
                  ("rmssd_ms", "RMSSD (ms)"), ("br_bpm", "呼吸率 (bpm)")]
BEHAV_METRICS = [("rt_mean", "RT 均值 (ms)"), ("err_rate", "误错率 (误按/trial)")]
PROBE_LABELS = ["专注", "任务相关干扰", "走神", "大脑空白"]

# ============================================================
# 数据加载
# ============================================================

def load_ok_windows(subject: str) -> tuple[list[dict], list[dict]]:
    """读取某被试可信窗与探针。

    参数:
        subject: 被试编号（3 位）
    返回:
        (ok_windows, probes): 可信窗列表（quality=ok, 含生理字段）,
                              探针列表
    """
    path = OUT_ROOT / "02_全程窗" / f"09_预实验-SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    if not path.exists():
        return [], []
    d = json.load(open(path, encoding="utf-8"))
    ok = [w for w in d["windows"] if w.get("quality") == "ok"]
    # 误错率 = 窗内错误数 / 试次数
    for w in ok:
        w["err_rate"] = (w["n_err"] / w["n_trials"]) if w.get("n_trials") else None
    return ok, d.get("probes", [])


def summary(vals: list[float]) -> dict:
    """中位数与 IQR 描述统计。"""
    a = np.asarray(vals, float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)),
            "median": round(float(np.median(a)), 2),
            "q1": round(float(np.percentile(a, 25)), 2),
            "q3": round(float(np.percentile(a, 75)), 2)}


# ============================================================
# 绘图
# ============================================================

def _setup_font():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def plot_physio(data: dict, plt):
    """生理指标 2×2 小提琴图（HR/SDNN/RMSSD/BR）。"""
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax, (m, label) in zip(axes.flat, PHYSIO_METRICS):
        cols, positions, labels_ = [], [], []
        for i, sub in enumerate(SUBJECTS):
            vals = [w[m] for w in data[sub]["ok"] if w.get(m) is not None]
            if vals:
                cols.append(vals)
                positions.append(i)
                labels_.append(f"sub-{sub}")
        if cols:
            parts = ax.violinplot(cols, positions=positions, showmeans=True,
                                  widths=0.7, showextrema=False)
            for pc in parts["bodies"]:
                pc.set_alpha(0.6)
            parts["cmeans"].set_color("#c0392b")
            parts["cmeans"].set_linewidth(1.2)
            # 箱线内核
            for i, c in zip(positions, cols):
                ax.boxplot(c, positions=[i], widths=0.18, showfliers=False,
                           medianprops=dict(color="black", linewidth=1))
        ax.axhline(np.median([v for c in cols for v in c]) if cols else None,
                   color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels_, rotation=45)
        ax.set_ylabel(label)
        ax.set_title(f"{label} 跨被试分布")
        ax.grid(True, alpha=0.3, axis="y")
    plt.suptitle("预实验 000-007 生理指标跨被试分布（可信窗）", fontsize=13)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "preexp_hrv_distributions.png", dpi=150)
    plt.close()


def plot_behavior(data: dict, plt):
    """行为指标 1×2 小提琴图（RT / 误错率）。"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, (m, label) in zip(axes, BEHAV_METRICS):
        cols, positions, labels_ = [], [], []
        for i, sub in enumerate(SUBJECTS):
            vals = [w[m] for w in data[sub]["ok"] if w.get(m) is not None]
            if vals:
                cols.append(vals)
                positions.append(i)
                labels_.append(f"sub-{sub}")
        if cols:
            parts = ax.violinplot(cols, positions=positions, showmeans=True,
                                  widths=0.7, showextrema=False)
            for pc in parts["bodies"]:
                pc.set_alpha(0.6)
            parts["cmeans"].set_color("#c0392b")
            for i, c in zip(positions, cols):
                ax.boxplot(c, positions=[i], widths=0.18, showfliers=False,
                           medianprops=dict(color="black", linewidth=1))
        ax.set_xticks(positions)
        ax.set_xticklabels(labels_, rotation=45)
        ax.set_ylabel(label)
        ax.set_title(f"{label} 跨被试分布")
        ax.grid(True, alpha=0.3, axis="y")
    plt.suptitle("预实验 000-007 行为指标跨被试分布（可信窗）", fontsize=13)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "preexp_behavior_distributions.png", dpi=150)
    plt.close()


def plot_usability_probes(data: dict, plt):
    """可用率条形图 + 探针标签分布堆叠图。"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    ax = axes[0]
    subs = [f"sub-{s}" for s in SUBJECTS]
    ratios = [data[s]["ok_ratio"] for s in SUBJECTS]
    colors = ["#27ae60" if r >= 0.7 else ("#f39c12" if r >= 0.3 else "#c0392b")
              for r in ratios]
    ax.bar(subs, [r * 100 for r in ratios], color=colors, alpha=0.85)
    ax.axhline(70, color="green", linestyle="--", linewidth=1)
    ax.axhline(30, color="red", linestyle="--", linewidth=1)
    ax.set_ylabel("可信窗比例 (%)")
    ax.set_title("全程窗可用率（质量评估口径）")
    ax.grid(True, alpha=0.3, axis="y")
    ax.set_ylim(0, 100)

    ax = axes[1]
    x = np.arange(len(SUBJECTS))
    bottoms = np.zeros(len(SUBJECTS))
    label_colors = {"专注": "#2e86c1", "任务相关干扰": "#e67e22",
                    "走神": "#8e44ad", "大脑空白": "#7f8c8d"}
    for lab in PROBE_LABELS:
        counts = [data[s]["probe_labels"].get(lab, 0) for s in SUBJECTS]
        ax.bar(x, counts, bottom=bottoms, label=lab,
               color=label_colors.get(lab, "#95a5a6"))
        bottoms += np.array(counts)
    ax.set_xticks(x)
    ax.set_xticklabels([f"sub-{s}" for s in SUBJECTS])
    ax.set_ylabel("探针数")
    ax.set_title("探针标签分布（含不可信）")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    plt.suptitle("预实验 000-007 可用率与探针标签分布", fontsize=13)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "preexp_usability_probes.png", dpi=150)
    plt.close()


# ============================================================
# 主流程
# ============================================================

def main():
    data = {}
    for sub in SUBJECTS:
        ok, probes = load_ok_windows(sub)
        probe_labels = {}
        for p in probes:
            lab = p.get("label_name", "未知")
            probe_labels[lab] = probe_labels.get(lab, 0) + 1
        data[sub] = {
            "ok": ok,
            "probes": probes,
            "probe_labels": probe_labels,
            "ok_ratio": len(ok) / max(1, len(ok) + sum(1 for w in ok if False)),
        }
        # ok_ratio 应为 可信窗/总窗: 需要总窗数, 这里从 json 再读
        jpath = OUT_ROOT / "02_全程窗" / f"09_预实验-SUB{sub}-FULL" / f"sub{sub}_full_windows.json"
        if jpath.exists():
            total = len(json.load(open(jpath, encoding="utf-8"))["windows"])
            data[sub]["ok_ratio"] = len(ok) / total if total else 0.0
        print(f"sub-{sub}: 可信窗 {len(ok)}, 可用率 {data[sub]['ok_ratio']:.0%}, "
              f"探针 {sum(probe_labels.values())} 个 {probe_labels}")

    plt = _setup_font()
    plot_physio(data, plt)
    plot_behavior(data, plt)
    plot_usability_probes(data, plt)
    print(f"[png] {OUT_DIR}/preexp_hrv_distributions.png")
    print(f"[png] {OUT_DIR}/preexp_behavior_distributions.png")
    print(f"[png] {OUT_DIR}/preexp_usability_probes.png")

    # 汇总 JSON
    summ = {}
    for sub in SUBJECTS:
        s = {"n_ok": len(data[sub]["ok"]),
             "ok_ratio": round(data[sub]["ok_ratio"], 3),
             "probe_labels": data[sub]["probe_labels"]}
        for m, _ in PHYSIO_METRICS + BEHAV_METRICS:
            vals = [w[m] for w in data[sub]["ok"] if w.get(m) is not None]
            s[m] = summary(vals)
        summ[sub] = s
    with open(OUT_DIR / "preexp_hrv_summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR}/preexp_hrv_summary.json")


if __name__ == "__main__":
    main()
