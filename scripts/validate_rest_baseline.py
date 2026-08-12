"""
validate_rest_baseline.py — 个体静息基线提取与有效性验证
====================================================================
版本: v1.0 (2026-08-12)
功能: 对预实验全部场次:
        1. 提取静息基线: 每场次 5 个 rest 段、每段 3×60s 窗,
           基线取窗 2-3（60-180s, 避开进入休息的过渡窗 1）
        2. 验证休息有效性:
           a) rest vs 任务段: HR 应更低、RMSSD/SDNN 应更高（配对检验）
           b) rest 段间一致性: 5 段 RMSSD 变异系数 (CV)
           c) 段内稳定性: 窗 1→2→3 的 RMSSD 轨迹（检验 3 分钟休息必要性）
        3. 输出: 每被试基线表 + 汇总统计

输入: output/预实验/02_全程窗/09_预实验-SUB{XXX}-REST-HRV/sub{XXX}_rest_hrv_windows.json
      output/预实验/02_全程窗/09_预实验-SUB{XXX}-FULL/sub{XXX}_full_windows.json
输出: output/预实验/03_跨被试/09_预实验-rest基线/
        rest_baseline_summary.csv   ← 每被试基线表
        rest_baseline_stats.md      ← 汇总统计
用法:
  cd 08_算法/scripts
  python validate_rest_baseline.py
依赖: numpy, scipy
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent / "output" / "预实验"
REST_DIR = OUT_ROOT / "02_全程窗"
FULL_DIR = OUT_ROOT / "02_全程窗"
OUT_DIR = OUT_ROOT / "03_跨被试" / "09_预实验-rest基线"
SUBJECTS = ["000", "003", "004", "005", "006", "007", "008", "009", "010"]
BASELINE_WINDOWS = (2, 3)   # 基线取 rest 段窗 2-3（60-180s, 跳过过渡窗 1）


def rest_rows(subject: str) -> list[dict]:
    """读取 rest HRV 窗数据（quality=ok）。

    参数:
        subject: 被试编号
    返回:
        list[dict]: 每窗一条（含 segment/window/指标）
    """
    p = REST_DIR / f"09_预实验-SUB{subject}-REST-HRV" / f"sub{subject}_rest_hrv_windows.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return [r for r in d["rows"] if r.get("quality") == "ok"]


def full_rows(subject: str) -> list[dict]:
    """读取全程任务窗数据（quality=ok, 不含休息段）。

    参数:
        subject: 被试编号
    返回:
        list[dict]: 每窗一条
    """
    p = FULL_DIR / f"09_预实验-SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return [r for r in d["windows"] if r.get("quality") == "ok"]


def main():
    """汇总基线表 + 有效性验证 + 统计。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for sub in SUBJECTS:
        rows = rest_rows(sub)
        task = full_rows(sub)
        # 基线: rest 窗 2-3 全部 ok 窗均值
        base = [r for r in rows if r["window"] in BASELINE_WINDOWS]
        b = {}
        for k, src in [("hr", "hr_time_bpm"), ("br", "br_freq_bpm")]:
            vals = [r[src] for r in base
                    if r.get(src) is not None and isinstance(r[src], (int, float))]
            b[k] = float(np.mean(vals)) if vals else float("nan")
        # SDNN/RMSSD 在嵌套 hrv 结构内
        for k, src in [("sdnn", "SDNN_ms"), ("rmssd", "RMSSD_ms")]:
            vals = [r["hrv"][src] for r in base
                    if r.get("hrv") and isinstance(r["hrv"].get(src), (int, float))]
            b[k] = float(np.mean(vals)) if vals else float("nan")
        # 任务段均值
        t = {}
        for k, src in [("hr", "hr_bpm"), ("br", "br_bpm"),
                       ("sdnn", "sdnn_ms"), ("rmssd", "rmssd_ms")]:
            vals = [r[src] for r in task
                    if r.get(src) is not None and isinstance(r[src], (int, float))]
            t[k] = float(np.mean(vals)) if vals else float("nan")
        # rest 段间一致性: 每段 RMSSD 均值 → 5 段 CV
        per_seg = {}
        for r in rows:
            v = r.get("hrv", {}).get("RMSSD_ms") if r.get("hrv") else None
            if v is not None and isinstance(v, (int, float)):
                per_seg.setdefault(r["segment"], []).append(float(v))
        seg_means = [np.mean(v) for v in per_seg.values()]
        cv = (np.std(seg_means, ddof=1) / np.mean(seg_means)) if len(seg_means) > 1 else float("nan")
        summary.append({"subject": sub, "n_rest_windows": len(rows),
                        **{f"rest_{k}": b[k] for k in b},
                        **{f"task_{k}": t[k] for k in t},
                        "rest_cv_rmssd": cv})

    # ── 保存基线表 ──
    with open(OUT_DIR / "rest_baseline_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "n_rest_windows", "rest_hr", "rest_br", "rest_sdnn",
                    "rest_rmssd", "task_hr", "task_br", "task_sdnn", "task_rmssd",
                    "rest_cv_rmssd"])
        for s in summary:
            w.writerow([s["subject"], s["n_rest_windows"], s["rest_hr"],
                        s["rest_br"], s["rest_sdnn"], s["rest_rmssd"],
                        s["task_hr"], s["task_br"], s["task_sdnn"], s["task_rmssd"],
                        s["rest_cv_rmssd"]])

    # ── 有效性验证 ──
    lines = ["# 静息基线提取与有效性验证\n"]
    lines.append("| 场次 | rest窗数 | 静息HR | 静息RMSSD | 静息SDNN | 任务HR | 任务RMSSD | rest RMSSD CV |")
    lines.append("|------|---------|--------|-----------|----------|--------|-----------|--------------|")
    for s in summary:
        lines.append(f"| {s['subject']} | {s['n_rest_windows']} | {s['rest_hr']:.1f} "
                     f"| {s['rest_rmssd']:.1f} | {s['rest_sdnn']:.1f} "
                     f"| {s['task_hr']:.1f} | {s['task_rmssd']:.1f} "
                     f"| {s['rest_cv_rmssd']:.2f} |")

    # 配对检验 rest vs 任务
    lines.append("\n## 休息有效性: rest vs 任务（配对 Wilcoxon, n=9）")
    for k, name in [("hr", "HR"), ("rmssd", "RMSSD"), ("sdnn", "SDNN"), ("br", "BR")]:
        vr = np.array([s[f"rest_{k}"] for s in summary if np.isfinite(s[f"rest_{k}"])])
        vt = np.array([s[f"task_{k}"] for s in summary if np.isfinite(s[f"task_{k}"])])
        if len(vr) >= 6 and len(vt) >= 6:
            diff = vr - vt
            if np.std(diff) > 0:
                stat, p = stats.wilcoxon(diff)
                direction = "rest 更低" if np.mean(vr) < np.mean(vt) else "rest 更高"
                lines.append(f"- {name}: rest {np.mean(vr):.1f} vs 任务 {np.mean(vt):.1f}, "
                             f"W={stat:.0f}, p={p:.3f} ({direction})")
            else:
                lines.append(f"- {name}: 所有场次差异为 0, 无法检验")
    lines.append("- 有效性判据: 静息 HR < 任务 HR 且静息 RMSSD > 任务 RMSSD 视为休息段"
                 "有效（副交感占优）; 相反模式需标记该场次休息段可疑")

    # 段内稳定性: RMSSD 窗 1/2/3 轨迹（跨场次均值）
    lines.append("\n## 休息段内稳定性: RMSSD 窗 1→2→3 轨迹（跨场次均值）")
    for k in (1, 2, 3):
        vals = []
        for sub in SUBJECTS:
            rows = rest_rows(sub)
            vv = [r["hrv"]["RMSSD_ms"] for r in rows if r["window"] == k
                  and r.get("hrv") and isinstance(r["hrv"].get("RMSSD_ms"), (int, float))]
            if vv:
                vals.append(np.mean(vv))
        if vals:
            lines.append(f"- 窗{k} (0-60s): RMSSD 跨场次均值 {np.mean(vals):.1f} ms")

    (OUT_DIR / "rest_baseline_stats.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\n输出: {OUT_DIR / 'rest_baseline_summary.csv'}")


if __name__ == "__main__":
    main()
