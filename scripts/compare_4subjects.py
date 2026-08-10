"""
compare_4subjects.py — 四被试（001/007/008/SXQ）对比图与统计汇总
================================================================
读 08_旧批次-SUBXXX-FULL 的全程/探针 JSON, 输出:
  output/08_旧批次-SUBJECTS-COMPARE/
    subjects_compare.png      ← 探针标签特征对比（HR/SDNN/RT × 4 标签 × 4 被试）
    subjects_usability.png    ← 可用率对比（全程窗/探针窗）
    subjects_summary.json     ← 统计汇总（供文档引用）

用法:
  cd 08_算法/scripts
  python compare_4subjects.py
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

OUTPUT_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\08_旧批次-SUBJECTS-COMPARE")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUBJECTS = ["001", "007", "008", "SXQ"]
LABELS = ["专注", "任务相关干扰", "走神", "大脑空白"]


def load_subject(subj):
    d = json.load(open(
        rf"D:\Project\厚粲杯\08_算法\output\08_旧批次-SUB{subj}-FULL\sub{subj}_full_windows.json",
        encoding="utf-8"))
    return d


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    data = {s: load_subject(s) for s in SUBJECTS}

    # ═══ 1. 可用率对比 ═══
    rows = []
    for s in SUBJECTS:
        d = data[s]
        n_w = len(d["windows"])
        ok_w = sum(1 for w in d["windows"] if w["quality"] == "ok")
        n_p = len(d["probes"])
        ok_p = sum(1 for p in d["probes"] if p["quality"] == "ok")
        rows.append({"subject": s, "n_win": n_w, "ok_win": ok_w,
                     "n_probe": n_p, "ok_probe": ok_p})
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    xs = np.arange(len(SUBJECTS))
    for ax_, key, nkey, title in [
        (ax[0], "ok_win", "n_win", "全程窗可用率 (30s 滑动)"),
        (ax[1], "ok_probe", "n_probe", "探针窗可用率"),
    ]:
        vals = [r[key] / max(r[nkey], 1) * 100 for r in rows]
        ax_.bar(xs, vals, color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"], alpha=0.85)
        for x, v, n in zip(xs, vals, [r[nkey] for r in rows]):
            ax_.text(x, v + 1, f"{v:.0f}% ({n})", ha="center", fontsize=10)
        ax_.set_xticks(xs)
        ax_.set_xticklabels(SUBJECTS)
        ax_.set_ylim(0, 115)
        ax_.set_title(title)
        ax_.set_ylabel("可用率 (%)")
        ax_.grid(axis="y", alpha=0.3)
    fig.suptitle("四被试毫米波特征可用率对比（统一管线 v1.3）", fontsize=13)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "subjects_usability.png", dpi=150)
    plt.close()
    print(f"[png] {OUTPUT_DIR / 'subjects_usability.png'}")

    # ═══ 2. 探针标签特征对比 ═══
    # 特征集: HR/SDNN/RMSSD/LF-HF/BR/RT（RMSSD 与 LF/HF 由管线已提取, 文献（Corcoran 2025 / Bortolla 2022）
    # 显示走神-迷走介导（RMSSD/RSA）链接比 SDNN 更直接; BR 验证呼吸-心率耦合背景）
    metrics = [("hr_bpm", "HR (bpm)", "心率"), ("sdnn_ms", "SDNN (ms)", "时域 HRV"),
               ("rmssd_ms", "RMSSD (ms)", "迷走介导 HRV"),
               ("lf_hf", "LF/HF", "频域 HRV"), ("br_bpm", "BR (bpm)", "呼吸"),
               ("prior_rt_mean", "探针前 RT (ms)", "行为")]
    fig, axes = plt.subplots(2, 3, figsize=(16, 10.5))
    axes = axes.flatten()
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    for ax, (key, ylab, kind) in zip(axes, metrics):
        for si, s in enumerate(SUBJECTS):
            d = data[s]
            ok = [p for p in d["probes"] if p["quality"] == "ok" and p.get(key) is not None]
            # 每个标签的均值点（x = 标签位置 + 被试偏移）
            for li, lab in enumerate(LABELS):
                vals = [p[key] for p in ok if p["label_name"] == lab]
                if vals:
                    x = li + (si - 1.5) * 0.18
                    ax.plot(x, np.mean(vals), "o", color=colors[si], markersize=6,
                            alpha=0.8)
                    # 个体散点（透明度低）
                    ax.scatter([x] * len(vals), vals, s=10, color=colors[si], alpha=0.15)
        ax.set_xticks(range(4))
        ax.set_xticklabels(LABELS, rotation=12)
        ax.set_ylabel(ylab)
        ax.set_title(f"{key} [{kind}]")
        ax.grid(alpha=0.3)
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
                          markersize=8, label=s) for s, c in zip(SUBJECTS, colors)]
    axes[0].legend(handles=handles, loc="upper left", fontsize=9)
    fig.suptitle("探针标签 × 特征（四被试, 点=被试均值, 淡点=个体）", fontsize=13)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "subjects_compare.png", dpi=150)
    plt.close()
    print(f"[png] {OUTPUT_DIR / 'subjects_compare.png'}")

    # ═══ 3. 统计汇总 ═══
    from scipy import stats as sps
    KEYS = [("hr", "hr_bpm"), ("sdnn", "sdnn_ms"), ("rmssd", "rmssd_ms"),
            ("lfhf", "lf_hf"), ("br", "br_bpm"), ("rt", "prior_rt_mean")]
    agg = {lab: {k: [] for k, _ in KEYS} for lab in LABELS}
    per_subj = {}
    for s in SUBJECTS:
        per_subj[s] = {lab: {k: [] for k, _ in KEYS} for lab in LABELS}
        for p in data[s]["probes"]:
            if p["quality"] != "ok":
                continue
            lab = p["label_name"]
            for k, field in KEYS:
                v = p.get(field)
                if v is not None:
                    agg[lab][k].append(float(v))
                    per_subj[s][lab][k].append(float(v))

    summary = {"usability": rows, "label_stats": {}, "tests": {}}
    for lab in LABELS:
        summary["label_stats"][lab] = {
            k: {"n": len(v), "mean": round(float(np.mean(v)), 1),
                "sd": round(float(np.std(v)), 1)}
            for k, v in agg[lab].items() if v}
    summary["per_subject"] = {
        s: {lab: {k: round(float(np.mean(v)), 1) for k, v in d.items() if v}
            for lab, d in ps.items()} for s, ps in per_subj.items()}

    # KW + 事后（干扰 vs 其他, 走神 vs 其他）
    for key, name in [("hr", "HR"), ("sdnn", "SDNN"), ("rmssd", "RMSSD"),
                      ("lfhf", "LF_HF"), ("br", "BR")]:
        groups = [agg[lab][key] for lab in LABELS if agg[lab][key]]
        if len(groups) >= 3:
            H, p = sps.kruskal(*groups)
            summary["tests"][f"{name}_kruskal"] = {"H": round(H, 2), "p": round(p, 4)}
        others = [v for lab in LABELS if lab != "任务相关干扰" for v in agg[lab][key]]
        a = agg["任务相关干扰"][key]
        if len(a) >= 5 and len(others) >= 5:
            u, p = sps.mannwhitneyu(a, others)
            summary["tests"][f"{name}_干扰vs其他"] = {"U": int(u), "p": round(p, 4)}
        others2 = [v for lab in LABELS if lab != "走神" for v in agg[lab][key]]
        a2 = agg["走神"][key]
        if len(a2) >= 5 and len(others2) >= 5:
            u, p = sps.mannwhitneyu(a2, others2)
            summary["tests"][f"{name}_走神vs其他"] = {"U": int(u), "p": round(p, 4)}

    with open(OUTPUT_DIR / "subjects_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUTPUT_DIR / 'subjects_summary.json'}")

    # 打印汇总
    print("\n=== 探针标签合并统计 ===")
    for lab in LABELS:
        s = summary["label_stats"][lab]
        line = f"{lab:<8} n={s['hr']['n']:<3} HR={s['hr']['mean']}±{s['hr']['sd']}"
        for k, label in [("sdnn", "SDNN"), ("rmssd", "RMSSD"), ("lfhf", "LF/HF"),
                         ("br", "BR"), ("rt", "RT")]:
            if k in s and s[k]["n"] > 0:
                line += f"  {label}={s[k]['mean']}±{s[k]['sd']}"
        print(f"  {line}")
    print("\n=== 检验 ===")
    for k, v in summary["tests"].items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
