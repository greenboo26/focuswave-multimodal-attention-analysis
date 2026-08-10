"""
export_window_matrix.py — 预实验窗特征矩阵导出（统一分析入口）
====================================================================
版本: v1.0 (2026-08-11)
功能: 汇总全部被试全部可信窗的完整特征向量为一张表
      （被试 × 窗 × 特征）, 作为后续统计建模/机器学习分析的统一入口,
      对齐 NeuroKit interval-related 特征集思路。

特征: 生理（HR/BR/SDNN/RMSSD/SampEn/DFAα1/α2）+ 行为（RT 均值/SD、
      窗内试次/错误数）+ 质量（可信标记/心跳 bin/谐波修正）+ 探针标签。

数据: output/预实验/09_预实验-SUB{XXX}-FULL/sub{XXX}_full_windows.json
输出: output/预实验/09_预实验-窗特征矩阵/
        window_matrix.csv        ← 全被试可信窗特征表
        window_matrix_summary.json ← 窗数/被试数/缺失统计
用法:
  cd 08_算法/scripts
  python export_window_matrix.py
依赖: numpy
"""

import csv
import json
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent / "output" / "预实验"
OUT_DIR = OUT_ROOT / "09_预实验-窗特征矩阵"
SUBJECTS = ["000", "001", "002", "003", "004", "005", "006", "007"]
FEATURES = ["subject", "t_start_s", "quality", "hr_bpm", "br_bpm", "sdnn_ms",
            "rmssd_ms", "sampen", "dfa_alpha1", "dfa_alpha2", "rt_mean", "rt_sd",
            "n_trials", "n_err", "err_rate", "heart_bin", "harmonics_corrected",
            "probe_label"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    per_sub = {}
    for sub in SUBJECTS:
        p = OUT_ROOT / f"09_预实验-SUB{sub}-FULL" / f"sub{sub}_full_windows.json"
        if not p.exists():
            continue
        d = json.load(open(p, encoding="utf-8"))
        probes = {pr["probe_id"]: pr.get("label_name") for pr in d.get("probes", [])}
        ok = [w for w in d["windows"] if w.get("quality") == "ok"]
        n = 0
        for w in ok:
            row = {k: w.get(k) for k in FEATURES}
            row["subject"] = sub
            row["probe_label"] = probes.get(w.get("probe_id")) if w.get("probe_id") in probes else ""
            if w.get("n_trials"):
                row["err_rate"] = round(w["n_err"] / w["n_trials"], 4)
            rows.append(row)
            n += 1
        per_sub[sub] = n
        print(f"sub-{sub}: 可信窗 {n}")

    # 写出 CSV（utf-8-sig 供 Excel 直接打开）
    csv_path = OUT_DIR / "window_matrix.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURES)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # 摘要
    summary = {"n_subjects": sum(1 for v in per_sub.values() if v),
               "n_windows": len(rows),
               "per_subject": per_sub}
    for m in ["hr_bpm", "sdnn_ms", "rmssd_ms", "sampen", "dfa_alpha1", "rt_mean"]:
        vals = [r[m] for r in rows if r.get(m) is not None and r[m] == r[m]]
        summary[m] = {"n": len(vals), "median": round(float(np.median(vals)), 3),
                      "q1": round(float(np.percentile(vals, 25)), 3),
                      "q3": round(float(np.percentile(vals, 75)), 3)} if vals else None
    json_path = OUT_DIR / "window_matrix_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n[csv] {csv_path}（{len(rows)} 窗 × {len(FEATURES)} 特征）")
    print(f"[json] {json_path}")
    print(f"  生理特征覆盖: SampEn {summary['sampen']['n']} 窗, "
          f"DFAα1 {summary['dfa_alpha1']['n']} 窗")


if __name__ == "__main__":
    main()
