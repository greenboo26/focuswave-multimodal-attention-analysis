"""
摸底_正式行为.py — 正式实验第一批（E:\\正式实验）行为数据健康度摸底
================================================================
功能: 统计 6 被试（011~016）的 SART 行为指标，定位数据异常（重点 sub-015）。
输出: 控制台汇总表 + 06_正式实验-行为摸底.csv

用法:
  cd 08_算法/scripts
  python3.14 _摸底_正式行为.py

依赖: 标准库 csv（无第三方依赖）
"""

import csv
import glob
import os
from pathlib import Path

DATA_ROOT = Path(r"E:\正式实验")
SUBJECTS = ["011", "012", "013", "014", "015", "016"]
RT_PREEMPT_MS = 150  # 预判按键阈值: RT<150ms 不可能为真实视觉反应（8-13 定调）
OUT_CSV = Path(r"D:\Project\厚粲杯\08_算法\output\90_历史归档\2026-08_早期正式实验\06_正式实验-行为摸底.csv")


def load_block_trials(beh_dir, subject):
    """合并 3 个 block 行为 CSV 为试次列表。

    Args:
        beh_dir: 行为数据目录
        subject: 被试编号

    Returns:
        list[dict]: 每试次原始字段字典
    """
    trials = []
    for fpath in sorted(glob.glob(str(beh_dir / f"sub-{subject}_Block*_beh.csv"))):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            trials.extend(list(csv.DictReader(f)))
    return trials


def summarize(subject):
    """统计单被试行为指标。

    Args:
        subject: 被试编号

    Returns:
        dict: 各行为指标汇总
    """
    trials = load_block_trials(DATA_ROOT / f"sub-{subject}_" / "beh", subject)
    n = len(trials)
    n_nogo = sum(1 for t in trials if t["is_no_go"] == "1")
    n_go = n - n_nogo

    # commission = no-go 误按（response==1 且 is_no_go）
    n_comm = sum(1 for t in trials if t["is_no_go"] == "1" and t["response"] == "1")
    # omission = go 漏按（response==0 且 非 no_go）
    n_omis = sum(1 for t in trials if t["is_no_go"] == "0" and t["response"] == "0")

    # RT（go 且按下键，仅真反应）
    rts = [float(t["rt"]) for t in trials
           if t["is_no_go"] == "0" and t["response"] == "1" and t["rt"]]
    n_preempt = sum(1 for r in rts if r < RT_PREEMPT_MS)
    rts_valid = [r for r in rts if r >= RT_PREEMPT_MS]

    # 探针标签分布（is_probe==1 且有 probe_response）
    n_probe = sum(1 for t in trials if t["is_probe"] == "1" and t["probe_response"])
    probe_labels = {}
    for t in trials:
        if t["is_probe"] == "1" and t["probe_response"]:
            probe_labels[t["probe_response"]] = probe_labels.get(t["probe_response"], 0) + 1

    def _mean(vals):
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "subject": subject,
        "n_trials": n,
        "n_nogo": n_nogo,
        "n_go": n_go,
        "n_comm": n_comm,
        "comm_rate_pct": round(100 * n_comm / n_nogo, 1) if n_nogo else None,
        "n_omis": n_omis,
        "omis_rate_pct": round(100 * n_omis / n_go, 1) if n_go else None,
        "rt_mean_ms": _mean(rts_valid),
        "rt_med_ms": round(sorted(rts_valid)[len(rts_valid) // 2], 1) if rts_valid else None,
        "rt_sd_ms": round((sum((r - _mean(rts_valid)) ** 2 for r in rts_valid) / (len(rts_valid) - 1)) ** 0.5, 1) if len(rts_valid) > 1 else None,
        "preempt_n": n_preempt,
        "preempt_rate_pct": round(100 * n_preempt / len(rts), 1) if rts else None,
        "n_probe": n_probe,
        "probe_labels": probe_labels,
    }


def main():
    print("=" * 70)
    print("  正式实验第一批（E:\\正式实验）行为数据摸底")
    print("=" * 70)
    rows = []
    for s in SUBJECTS:
        r = summarize(s)
        rows.append(r)
        print(f"\nsub-{s}: 试次 {r['n_trials']} (go {r['n_go']}/no-go {r['n_nogo']})")
        print(f"  commission {r['n_comm']}/{r['n_nogo']} = {r['comm_rate_pct']}%  |  "
              f"omission {r['n_omis']}/{r['n_go']} = {r['omis_rate_pct']}%")
        print(f"  RT: mean {r['rt_mean_ms']} / med {r['rt_med_ms']} / sd {r['rt_sd_ms']} ms  |  "
              f"预判 {r['preempt_n']} ({r['preempt_rate_pct']}%)")
        print(f"  探针 {r['n_probe']} 个, 标签分布 {r['probe_labels']}")

    # 保存 CSV（探针标签拆列）
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        header = ["subject", "n_trials", "n_nogo", "n_go", "n_comm", "comm_rate_pct",
                  "n_omis", "omis_rate_pct", "rt_mean_ms", "rt_med_ms", "rt_sd_ms",
                  "preempt_n", "preempt_rate_pct", "n_probe",
                  "probe_1", "probe_2", "probe_3", "probe_4"]
        w.writerow(header)
        for r in rows:
            w.writerow([
                r["subject"], r["n_trials"], r["n_nogo"], r["n_go"], r["n_comm"],
                r["comm_rate_pct"], r["n_omis"], r["omis_rate_pct"], r["rt_mean_ms"],
                r["rt_med_ms"], r["rt_sd_ms"], r["preempt_n"], r["preempt_rate_pct"],
                r["n_probe"],
                r["probe_labels"].get("1", 0), r["probe_labels"].get("2", 0),
                r["probe_labels"].get("3", 0), r["probe_labels"].get("4", 0),
            ])
    print(f"\n已保存: {OUT_CSV}")


if __name__ == "__main__":
    main()


