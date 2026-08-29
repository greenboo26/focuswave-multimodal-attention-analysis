"""
analyze_probe_effect.py — 探针（状态检查）前后的行为变化分析
====================================================================
版本: v1.0 (2026-08-11)
功能: 检验探针的干预效应: 探针出现前后 30s 的行为对比（RT 均值/错误数）。
      005 答卷自报"探针把我思绪拉回来了，变得更专注"——个体层面
      探针后行为是否恢复（RT 加快/错误减少）。
依据: Wiemers & Redick 2019（探针不改变整体表现, 但未测瞬间效应）;
      预实验答卷（005 自报拉回效应）。

数据: F:/预实验/sub-007_/beh/*.csv（探针时刻 + 行为）
输出: output/预实验/03_跨被试/09_预实验-优化实验/PROBE-EFFECT/
        probe_effect_summary.json
用法:
  cd 08_算法/scripts
  python analyze_probe_effect.py --subject 007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "PROBE-EFFECT"
BEFORE_S = 30.0   # 探针前窗口（秒）
AFTER_S = 30.0    # 探针后窗口（秒）


def main():
    parser = argparse.ArgumentParser(description="探针前后行为变化")
    parser.add_argument("--subject", type=str, default="007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    subject = args.subject.zfill(3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 收集所有 trial（时间, is_no_go, response, rt）
    trials = []
    for fpath in sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv")):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    onset = int(float(r["absolute_onset_time"]))
                except (ValueError, KeyError):
                    continue
                trials.append({"t": onset, "is_no_go": r["is_no_go"] == "1",
                               "resp": r["response"] == "1",
                               "rt": float(r["rt"]) if r.get("rt") else None,
                               "is_probe": r["is_probe"] == "1"})
    trials.sort(key=lambda x: x["t"])
    probes = [x for x in trials if x["is_probe"]]
    print(f"sub-{subject}: {len(trials)} trial, {len(probes)} 探针")

    # 探针后 30s 不包含下一个探针（避免重叠）
    results = []
    for i, pr in enumerate(probes):
        t0, t1 = pr["t"], pr["t"] + AFTER_S * 1000
        nxt = probes[i + 1]["t"] if i + 1 < len(probes) else t1 + 1
        t1 = min(t1, nxt)
        after = [x for x in trials if t0 < x["t"] < t1 and not x["is_probe"]]
        before = [x for x in trials if t0 - BEFORE_S * 1000 < x["t"] < t0]
        # go trial RT 均值 + 错误数（omission）
        def agg(ts):
            gos = [x for x in ts if not x["is_no_go"]]
            rt = np.mean([x["rt"] for x in gos if x["rt"] is not None]) if gos else None
            err = sum(1 for x in gos if not x["resp"])
            return rt, err
        rt_b, err_b = agg(before)
        rt_a, err_a = agg(after)
        results.append({"probe_idx": i, "rt_before": rt_b, "rt_after": rt_a,
                        "err_before": err_b, "err_after": err_a,
                        "n_before": len(before), "n_after": len(after)})

    # 配对检验
    rt_b = np.array([r["rt_before"] for r in results if r["rt_before"] and r["rt_after"]])
    rt_a = np.array([r["rt_after"] for r in results if r["rt_before"] and r["rt_after"]])
    eb = np.array([r["err_before"] for r in results])
    ea = np.array([r["err_after"] for r in results])
    out = {"n_probes": len(results),
           "rt_before_mean": round(float(np.mean(rt_b)), 1) if len(rt_b) else None,
           "rt_after_mean": round(float(np.mean(rt_a)), 1) if len(rt_a) else None,
           "err_before_mean": round(float(np.mean(eb)), 2) if len(eb) else None,
           "err_after_mean": round(float(np.mean(ea)), 2) if len(ea) else None}
    if len(rt_b) >= 5:
        t_, p_ = stats.ttest_rel(rt_b, rt_a)
        out["rt_paired_t"] = round(float(t_), 2)
        out["rt_paired_p"] = round(float(p_), 4)
    if len(eb) >= 5:
        t_, p_ = stats.ttest_rel(eb, ea)
        out["err_paired_t"] = round(float(t_), 2)
        out["err_paired_p"] = round(float(p_), 4)
    print(f"探针前 RT {out.get('rt_before_mean')} vs 探针后 {out.get('rt_after_mean')} "
          f"(p={out.get('rt_paired_p')})")
    print(f"探针前错误 {out.get('err_before_mean')} vs 探针后 {out.get('err_after_mean')} "
          f"(p={out.get('err_paired_p')})")
    with open(OUT_DIR / f"probe_effect_{subject}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / f'probe_effect_{subject}.json'}")


if __name__ == "__main__":
    main()


