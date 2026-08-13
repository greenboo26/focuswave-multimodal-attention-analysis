"""
预实验休息阶段 HRV 变化分析（四角度）
====================================
基于 8 名被试（003-010, 剔除 000/001/002）的 REST-HRV 窗数据 (analyze_mmwave_hrv.py 输出),
回答四个问题:

  1. 段内恢复轨迹: 休息开始后 HRV 如何变化 (窗1 0-60s / 窗2 60-120s / 窗3 120-180s)
  2. 段间变化: rest1→rest5 任务疲劳是否累积、恢复能力是否衰减
  3. 任务 vs 休息对比: 休息是否产生 HRV 差异
  4. 个体恢复模式: 谁休息有效、谁无效 (呼应个体轨迹分类思路)

统计口径 (与行为报告一致): 每名被试先在段/窗内汇总, 再对被试间配对检验,
避免把重复事件冒充独立样本。

用法:
    cd 08_算法/scripts
    python analyze_rest_hrv_changes.py

输出: output/预实验/03_跨被试/09_预实验-restHRV变化/
"""

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"
REST_DIR = OUTPUT_ROOT / "预实验" / "02_全程窗"
BASELINE_CSV = (OUTPUT_ROOT / "预实验" / "03_跨被试"
                / "09_预实验-rest基线" / "rest_baseline_summary.csv")
OUT_DIR = OUTPUT_ROOT / "预实验" / "03_跨被试" / "09_预实验-restHRV变化"

SUBJECTS = ["003", "004", "005", "006", "007", "008", "009", "010"]  # 剔除 001/002 摆位失误 + 000 练习效应
METRICS = {"RMSSD (ms)": "RMSSD_ms", "SDNN (ms)": "SDNN_ms",
           "HR (bpm)": "hr_time_bpm", "BR (bpm)": "br_freq_bpm"}


def load_rest_windows(subject: str) -> list[dict]:
    """加载单被试休息段窗数据 (仅可信窗)。

    参数:
        subject: 被试编号
    返回:
        list[dict]: 窗条目 (segment/window/hrv/...)
    """
    path = REST_DIR / f"09_预实验-SUB{subject}-REST-HRV-v8" / f"sub{subject}_rest_hrv_windows.json"
    d = json.load(open(path, encoding="utf-8"))
    return [r for r in d.get("rows", []) if r.get("quality") == "ok"]


def window_metric(row: dict, metric: str) -> float | None:
    """取窗指标值 (HRV 走 hrv 子字典)。"""
    if metric in ("RMSSD_ms", "SDNN_ms"):
        return row.get("hrv", {}).get(metric)
    return row.get(metric)


def paired_test(vals: list[float]) -> tuple[float, float, int]:
    """单样本 t 检验 (配对差值), 返回 (均值差, p, n)。"""
    vals = [v for v in vals if v == v]  # 去 NaN
    if len(vals) < 3:
        return float("nan"), float("nan"), len(vals)
    t, p = stats.ttest_1samp(vals, 0)
    return float(np.mean(vals)), float(p), len(vals)


def zscore_subject(per_win: dict, label: str, ref_windows=(1, 2, 3)) -> dict:
    """被试内 z 标准化: 以该被试全部 rest 窗 (该指标) 的均值/标准差为参照。

    个体差异巨大 (RMSSD 5.5 倍), 直接跨被试平均绝对值会淹没效应。

    参数:
        per_win: {窗号: {label: 均值}} 被试内数据
        label: 指标名
        ref_windows: 参与参照统计的窗号
    返回:
        {窗号: z 值}, 参照分布方差为 0 时返回 None
    """
    ref = [per_win[w][label] for w in ref_windows
           if w in per_win and per_win[w].get(label) is not None]
    if len(ref) < 2:
        return {}
    mu, sd = np.mean(ref), np.std(ref, ddof=1)
    if sd == 0:
        return {}
    return {w: (per_win[w][label] - mu) / sd
            for w in per_win if per_win[w].get(label) is not None}


def angle1_within_segment(subjects: list[str]) -> dict:
    """角度1: 段内恢复轨迹 (窗1 vs 窗2 vs 窗3)。

    每被试先对段内同窗取均值 (5 段平均), 再做被试内 z 标准化
    (以该被试全部 rest 窗为参照), 最后跨被试统计 z 值。
    配对: 每被试 窗3-窗1 差值做单样本 t。
    """
    per_subject = {}
    for s in subjects:
        rows = load_rest_windows(s)
        per_win = {1: [], 2: [], 3: []}
        for r in rows:
            w = r.get("window")
            if w in per_win:
                for label, key in METRICS.items():
                    v = window_metric(r, key)
                    if v is not None:
                        per_win[w].append((label, v))
        # 段内同窗平均
        out = {1: {}, 2: {}, 3: {}}
        for w, items in per_win.items():
            for label in METRICS:
                vals = [v for l, v in items if l == label]
                out[w][label] = np.mean(vals) if vals else None
        # 被试内 z 标准化
        per_subject[s] = {}
        for label in METRICS:
            z = zscore_subject(out, label)
            for w, zv in z.items():
                per_subject[s].setdefault(w, {})[label] = zv

    result = {"by_window": {}, "w3_w1": {}}
    for label in METRICS:
        means = [np.mean([per_subject[s][w][label] for s in subjects
                         if per_subject[s].get(w, {}).get(label) is not None])
                 for w in (1, 2, 3)]
        ses = [np.std([per_subject[s][w][label] for s in subjects
                      if per_subject[s].get(w, {}).get(label) is not None],
                     ddof=1) / np.sqrt(9)
               for w in (1, 2, 3)]
        diffs = [per_subject[s][3][label] - per_subject[s][1][label]
                 for s in subjects
                 if per_subject[s].get(3, {}).get(label) is not None
                 and per_subject[s].get(1, {}).get(label) is not None]
        md, p, n = paired_test(diffs)
        result["by_window"][label] = {"means": means, "ses": ses}
        result["w3_w1"][label] = {"mean_diff": md, "p": p, "n": n}
    return result


def angle2_across_segments(subjects: list[str]) -> dict:
    """角度2: 段间变化 (rest1→rest5)。

    每被试每段对所有窗取均值, 再做被试内 z 标准化
    (以该被试全部段为参照), 最后跨被试统计段轨迹。
    rest1 vs rest5 配对检验。
    """
    per_subject = {}
    for s in subjects:
        rows = load_rest_windows(s)
        per_seg = {}
        for r in rows:
            seg = r.get("segment")
            per_seg.setdefault(seg, {})
            for label, key in METRICS.items():
                v = window_metric(r, key)
                if v is not None:
                    per_seg[seg].setdefault(label, []).append(v)
        seg_means = {seg: {label: np.mean(vals) for label, vals in m.items()}
                     for seg, m in per_seg.items()}
        # 被试内 z 标准化 (参照 = 该被试全部段)
        zs = {}
        for label in METRICS:
            ref = [seg_means[seg][label] for seg in seg_means
                   if seg_means[seg].get(label) is not None]
            if len(ref) < 2:
                continue
            mu, sd = np.mean(ref), np.std(ref, ddof=1)
            if sd == 0:
                continue
            for seg in seg_means:
                if seg_means[seg].get(label) is not None:
                    zs.setdefault(seg, {})[label] = (seg_means[seg][label] - mu) / sd
        per_subject[s] = zs

    result = {"by_segment": {}, "r5_r1": {}}
    for label in METRICS:
        means, ses = [], []
        for seg in [f"rest{i}" for i in range(1, 6)]:
            vals = [per_subject[s][seg][label] for s in subjects
                    if seg in per_subject[s] and per_subject[s][seg].get(label) is not None]
            means.append(np.mean(vals) if vals else None)
            ses.append(np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else None)
        diffs = [per_subject[s]["rest5"][label] - per_subject[s]["rest1"][label]
                 for s in subjects
                 if "rest5" in per_subject[s] and "rest1" in per_subject[s]
                 and per_subject[s]["rest5"].get(label) is not None
                 and per_subject[s]["rest1"].get(label) is not None]
        md, p, n = paired_test(diffs)
        result["by_segment"][label] = {"means": means, "ses": ses}
        result["r5_r1"][label] = {"mean_diff": md, "p": p, "n": n}
    return result


def angle3_rest_vs_task(subjects: list[str]) -> dict:
    """角度3: 任务 vs 休息对比 (rest_baseline_summary.csv 复核)。

    参数:
        subjects: 纳入分析的被试列表 (剔除摆位失误/练习效应)
    """
    rows = [r for r in csv.DictReader(open(BASELINE_CSV, encoding="utf-8-sig"))
            if r["subject"] in subjects]
    result = {}
    for rest_key, task_key, label in [
        ("rest_rmssd", "task_rmssd", "RMSSD (ms)"),
        ("rest_sdnn", "task_sdnn", "SDNN (ms)"),
        ("rest_hr", "task_hr", "HR (bpm)"),
        ("rest_br", "task_br", "BR (bpm)"),
    ]:
        pairs = [(float(r[rest_key]), float(r[task_key])) for r in rows
                 if r.get(rest_key) and r.get(task_key)]
        rest = np.mean([p[0] for p in pairs])
        task = np.mean([p[1] for p in pairs])
        diffs = [p[0] - p[1] for p in pairs]
        md, p, n = paired_test(diffs)
        result[label] = {"rest_mean": float(rest), "task_mean": float(task),
                         "mean_diff": md, "p": p, "n": n}
    return result


def angle4_individual_patterns(subjects: list[str]) -> dict:
    """角度4: 个体恢复模式 (窗1→窗3 RMSSD 变化方向分类)。"""
    patterns = {}
    for s in subjects:
        rows = load_rest_windows(s)
        per_win = {1: [], 3: []}
        for r in rows:
            w = r.get("window")
            if w in per_win:
                v = window_metric(r, "RMSSD_ms")
                if v is not None:
                    per_win[w].append(v)
        w1 = np.mean(per_win[1]) if per_win[1] else None
        w3 = np.mean(per_win[3]) if per_win[3] else None
        if w1 is not None and w3 is not None:
            delta = w3 - w1
            rel = delta / w1  # 相对变化
            patterns[s] = {"w1": w1, "w3": w3, "delta": delta, "rel": rel}
    return patterns


def plot_results(a1: dict, a2: dict, a3: dict, a4: dict, out_dir: Path) -> None:
    """四角度结果图 (中文字体已配置)。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    # 图1: 段内恢复轨迹 (2×2 布局)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, (label, d) in zip(axes.flat, a1["by_window"].items()):
        means = [m for m in d["means"] if m is not None]
        ses = [s for s in d["ses"] if s is not None]
        xs = np.arange(1, 4)[:len(means)]
        ax.errorbar(xs, means, yerr=ses, marker="o", capsize=4, color="#2e86c1")
        ax.set_xlabel("休息窗 (60s/窗)")
        ax.set_ylabel(label + " (z)")
        ax.set_title(f"{label} 段内轨迹\n窗3-窗1: {a1['w3_w1'][label]['mean_diff']:+.1f} "
                     f"(p={a1['w3_w1'][label]['p']:.3f})")
        ax.grid(True, alpha=0.3)
    fig.suptitle("休息段内 HRV 恢复轨迹（被试内 z 标准化后跨被试均值 ± SE）", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_dir / "rest_angle1_within_segment.png", dpi=150)
    plt.close(fig)

    # 图2: 段间变化 (2×2 布局)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, (label, d) in zip(axes.flat, a2["by_segment"].items()):
        means = [m for m in d["means"] if m is not None]
        ses = [s for s in d["ses"] if s is not None]
        xs = np.arange(1, 6)[:len(means)]
        ax.errorbar(xs, means, yerr=ses, marker="o", capsize=4, color="#c0392b")
        ax.set_xlabel("休息段序号")
        ax.set_ylabel(label + " (z)")
        ax.set_title(f"{label} 段间轨迹\nrest5-rest1: {a2['r5_r1'][label]['mean_diff']:+.1f} "
                     f"(p={a2['r5_r1'][label]['p']:.3f})")
        ax.grid(True, alpha=0.3)
    fig.suptitle("休息段间 HRV 变化（被试内 z 标准化后跨被试均值 ± SE）", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_dir / "rest_angle2_across_segments.png", dpi=150)
    plt.close(fig)

    # 图3: 任务 vs 休息
    rows = list(csv.DictReader(open(BASELINE_CSV, encoding="utf-8-sig")))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, (rest_key, task_key, label) in zip(
            axes, [("rest_rmssd", "task_rmssd", "RMSSD (ms)"),
                   ("rest_sdnn", "task_sdnn", "SDNN (ms)")]):
        for r in rows:
            if r.get(rest_key) and r.get(task_key):
                ax.plot([0, 1], [float(r[task_key]), float(r[rest_key])],
                        "o-", color="#95a5a6", alpha=0.6, markersize=4)
        ax.set_xticks([0, 1], ["任务", "休息"])
        ax.set_ylabel(label + " (z)")
        ax.set_title(f"{label} 任务 vs 休息\nΔ={a3[label]['mean_diff']:+.1f} "
                     f"(p={a3[label]['p']:.3f}, n={a3[label]['n']})")
        ax.grid(True, alpha=0.3)
    fig.suptitle("任务段 vs 休息段（每被试一条线, 原始值配对展示）", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_dir / "rest_angle3_rest_vs_task.png", dpi=150)
    plt.close(fig)

    # 图4: 个体恢复模式
    fig, ax = plt.subplots(figsize=(9, 4.5))
    subs = sorted(a4.keys())
    deltas = [a4[s]["delta"] for s in subs]
    colors = ["#27ae60" if d > 1 else ("#c0392b" if d < -1 else "#95a5a6")
              for d in deltas]
    ax.bar(subs, deltas, color=colors, alpha=0.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("被试")
    ax.set_ylabel("窗3 - 窗1 RMSSD 变化 (ms)")
    ax.set_title("个体恢复模式（被试内窗3-窗1 RMSSD 绝对差, 绿=恢复型, 红=反常型, 灰=平坦型）")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "rest_angle4_individual_patterns.png", dpi=150)
    plt.close(fig)


def main() -> None:
    """执行四角度分析并保存结果。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("预实验休息阶段 HRV 变化分析（8 名被试, 剔除 000/001/002）")
    print("=" * 60)

    a1 = angle1_within_segment(SUBJECTS)
    print("\n[角度1] 段内恢复轨迹 (窗3-窗1 配对, n=被试数):")
    for label, d in a1["w3_w1"].items():
        sig = "*" if d["p"] < 0.05 else ""
        print(f"  {label}: Δ={d['mean_diff']:+.2f}, p={d['p']:.3f}, n={d['n']} {sig}")

    a2 = angle2_across_segments(SUBJECTS)
    print("\n[角度2] 段间变化 (rest5-rest1 配对):")
    for label, d in a2["r5_r1"].items():
        sig = "*" if d["p"] < 0.05 else ""
        print(f"  {label}: Δ={d['mean_diff']:+.2f}, p={d['p']:.3f}, n={d['n']} {sig}")

    a3 = angle3_rest_vs_task(SUBJECTS)
    print("\n[角度3] 任务 vs 休息 (配对, n=9):")
    for label, d in a3.items():
        sig = "*" if d["p"] < 0.05 else ""
        print(f"  {label}: 休息 {d['rest_mean']:.1f} vs 任务 {d['task_mean']:.1f}, "
              f"Δ={d['mean_diff']:+.1f}, p={d['p']:.3f} {sig}")

    a4 = angle4_individual_patterns(SUBJECTS)
    print("\n[角度4] 个体恢复模式 (窗1→窗3 RMSSD):")
    n_up = sum(1 for s in a4 if a4[s]["delta"] > 1)
    n_flat = sum(1 for s in a4 if -1 <= a4[s]["delta"] <= 1)
    n_down = sum(1 for s in a4 if a4[s]["delta"] < -1)
    print(f"  恢复型 {n_up} 人, 平坦型 {n_flat} 人, 反常型 {n_down} 人")
    for s in sorted(a4):
        print(f"  {s}: 窗1={a4[s]['w1']:.1f} → 窗3={a4[s]['w3']:.1f} "
              f"(Δ={a4[s]['delta']:+.1f} ms, 相对 {a4[s]['rel']:+.0%})")

    # 保存 JSON + 图
    summary = {"angle1": a1, "angle2": a2, "angle3": a3,
               "angle4": {s: {k: round(v, 2) for k, v in d.items()} for s, d in a4.items()}}
    with open(OUT_DIR / "rest_hrv_changes_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    plot_results(a1, a2, a3, a4, OUT_DIR)
    print(f"\n输出: {OUT_DIR}")


if __name__ == "__main__":
    main()
