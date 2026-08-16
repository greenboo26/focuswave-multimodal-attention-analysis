"""
analyze_formal_behavior.py — 正式实验第一批（E:\\正式实验）行为数据完整分析
==========================================================================
功能: 对行为有效被试（011/012/013/014/016）做 SART 行为指标的组级描述统计
      + Block 内轨迹（4 段）+ Block 间轨迹 + 探针标签描述 + 小样本统计检验。

数据: E:\\正式实验\\sub-XXX_\\beh\\（3 block × 432 试次）
排除: sub-015（规则完全做反, commission 100% + omission 100%, 行为无效）

用法:
  cd 08_算法/scripts
  python3.14 analyze_formal_behavior.py

输出:
  output/06_正式实验/行为分析/behavior_summary.csv     ← 个体+组级描述统计
  output/06_正式实验/行为分析/block_trajectory.csv     ← Block 内 4 段轨迹
  output/06_正式实验/行为分析/behavior_analysis.md     ← 汇总报告

依赖: numpy, scipy（仅标准库 + 两库）
"""

import csv
import glob
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"E:\正式实验")
OUT_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验\行为分析")
SUBJECTS_BEHAVIOR = ["011", "012", "013", "014", "016"]  # 行为有效被试（015 规则反排除）
SUBJECTS_PHYSIO = ["011", "012", "013", "014", "015", "016"]  # 生理被试（015 生理保留）
RT_PREEMPT_MS = 150        # 预判按键阈值: RT<150ms 不可能为真实视觉反应（8-13 定调）
N_SEG_PER_BLOCK = 4        # Block 内分段数（每 block 432 试次 / 4 = 108 试次/段）
PROBE_LABELS = {"1": "专注", "2": "任务相关干扰", "3": "走神", "4": "大脑空白"}


def load_trials(subject):
    """合并 3 个 block 行为 CSV 为试次列表（含 block_num 标记）。

    Args:
        subject: 被试编号

    Returns:
        list[dict]: 每试次原始字段 + block_num(int)
    """
    trials = []
    for fpath in sorted(glob.glob(str(DATA_ROOT / f"sub-{subject}_" / "beh" /
                                     f"sub-{subject}_Block*_beh.csv"))):
        blk = int(fpath.split("Block")[1].split("_")[0])
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                r["_block"] = blk
                trials.append(r)
    return trials


def trial_metrics(trials):
    """聚合一批试次的行为指标。

    Args:
        trials: 试次列表

    Returns:
        dict: n_trials/n_nogo/n_go/comm_rate/omis_rate/rt_mean/rt_med/rt_sd/preempt_rate
    """
    n_nogo = sum(1 for t in trials if t["is_no_go"] == "1")
    n_go = len(trials) - n_nogo
    n_comm = sum(1 for t in trials if t["is_no_go"] == "1" and t["response"] == "1")
    n_omis = sum(1 for t in trials if t["is_no_go"] == "0" and t["response"] == "0")
    rts = [float(t["rt"]) for t in trials
           if t["is_no_go"] == "0" and t["response"] == "1" and t["rt"]]
    n_preempt = sum(1 for r in rts if r < RT_PREEMPT_MS)
    rts_valid = [r for r in rts if r >= RT_PREEMPT_MS]
    return {
        "n_trials": len(trials),
        "n_nogo": n_nogo,
        "n_go": n_go,
        "comm_rate": n_comm / n_nogo if n_nogo else None,
        "omis_rate": n_omis / n_go if n_go else None,
        "rt_mean": float(np.mean(rts_valid)) if rts_valid else None,
        "rt_med": float(np.median(rts_valid)) if rts_valid else None,
        "rt_sd": float(np.std(rts_valid, ddof=1)) if len(rts_valid) > 1 else None,
        "preempt_rate": n_preempt / len(rts) if rts else None,
    }


def probe_distribution(trials):
    """统计探针标签分布。

    Args:
        trials: 试次列表

    Returns:
        dict: 标签 → 数量
    """
    dist = Counter()
    for t in trials:
        if t["is_probe"] == "1" and t["probe_response"]:
            dist[t["probe_response"]] += 1
    return dict(sorted(dist.items()))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("  正式实验第一批行为数据分析（行为有效被试 5 人）")
    print("=" * 70)

    # ── 1. 组级描述统计 ──
    all_trials = {s: load_trials(s) for s in SUBJECTS_BEHAVIOR}
    subj_metrics = {s: trial_metrics(all_trials[s]) for s in SUBJECTS_BEHAVIOR}

    print("\n[1/4] 组级描述统计")
    print(f"  {'被试':<6}{'comm%':>7}{'omis%':>7}{'RT均值':>8}{'RT中位':>8}{'RT_SD':>7}{'预判%':>7}")
    for s in SUBJECTS_BEHAVIOR:
        m = subj_metrics[s]
        print(f"  sub-{s:<3}{m['comm_rate']*100:>6.1f}{m['omis_rate']*100:>7.1f}"
              f"{m['rt_mean']:>8.1f}{m['rt_med']:>8.1f}{m['rt_sd']:>7.1f}"
              f"{m['preempt_rate']*100:>7.1f}")

    # 组级均值±SD
    for key, name in [("comm_rate", "commission"), ("omis_rate", "omission"),
                      ("rt_mean", "RT 均值"), ("rt_sd", "RT_SD"),
                      ("preempt_rate", "预判率")]:
        vals = [subj_metrics[s][key] for s in SUBJECTS_BEHAVIOR]
        print(f"  组级 {name}: {np.mean(vals):.3f} ± {np.std(vals, ddof=1):.3f} (n={len(vals)})")

    # ── 2. Block 间轨迹 ──
    print("\n[2/4] Block 间轨迹（Block1→2→3）")
    block_comm = {s: [] for s in SUBJECTS_BEHAVIOR}
    for s in SUBJECTS_BEHAVIOR:
        for blk in [1, 2, 3]:
            bt = [t for t in all_trials[s] if t["_block"] == blk]
            block_comm[s].append(trial_metrics(bt)["comm_rate"])
    for s in SUBJECTS_BEHAVIOR:
        print(f"  sub-{s}: " + " → ".join(f"{c*100:.1f}%" for c in block_comm[s]))
    # Friedman 检验（3 个 block 重复测量, n=5 非参数）
    mat = np.array([block_comm[s] for s in SUBJECTS_BEHAVIOR])
    stat, p = stats.friedmanchisquare(mat[:, 0], mat[:, 1], mat[:, 2])
    print(f"  Friedman χ²(2)={stat:.2f}, p={p:.3f}（n=5, 小样本探索性）")

    # ── 3. Block 内轨迹（4 段）──
    print("\n[3/4] Block 内轨迹（每 block 分 4 段, 段1→4）")
    seg_comm = {s: [] for s in SUBJECTS_BEHAVIOR}
    seg_rt = {s: [] for s in SUBJECTS_BEHAVIOR}
    for s in SUBJECTS_BEHAVIOR:
        for blk in [1, 2, 3]:
            bt = [t for t in all_trials[s] if t["_block"] == blk]
            n_per = len(bt) // N_SEG_PER_BLOCK
            for k in range(N_SEG_PER_BLOCK):
                seg = bt[k * n_per:(k + 1) * n_per]
                seg_comm[s].append(trial_metrics(seg)["comm_rate"])
                seg_rt[s].append(trial_metrics(seg)["rt_mean"])
    # 汇总 12 段（3 block × 4 段）取段位置均值
    for seg_idx in range(N_SEG_PER_BLOCK):
        idxs = [seg_idx + blk * N_SEG_PER_BLOCK for blk in range(3)]
        comms = [seg_comm[s][i] for s in SUBJECTS_BEHAVIOR for i in idxs]
        rts = [seg_rt[s][i] for s in SUBJECTS_BEHAVIOR for i in idxs]
        print(f"  段{seg_idx+1}: commission {np.mean(comms)*100:.1f}% | RT {np.mean(rts):.0f}ms")
    # 段1 vs 段4（配对 Wilcoxon, n=5）
    seg1 = [np.mean([seg_comm[s][blk * 4] for blk in range(3)]) for s in SUBJECTS_BEHAVIOR]
    seg4 = [np.mean([seg_comm[s][blk * 4 + 3] for blk in range(3)]) for s in SUBJECTS_BEHAVIOR]
    w, p = stats.wilcoxon(seg4, seg1)
    print(f"  段4-段1 commission Δ: 均值 {np.mean(np.array(seg4)-np.array(seg1))*100:+.1f}%, "
          f"Wilcoxon p={p:.3f}（n=5 探索性）")

    # ── 4. 探针标签描述 ──
    print("\n[4/4] 探针标签分布（描述性, 6 生理被试）")
    probe_all = Counter()
    for s in SUBJECTS_PHYSIO:
        trials = load_trials(s)
        dist = probe_distribution(trials)
        probe_all.update(dist)
        print(f"  sub-{s}: { {PROBE_LABELS.get(k,k): v for k,v in dist.items()} }")
    print(f"  总计: { {PROBE_LABELS.get(k,k): v for k,v in sorted(probe_all.items())} }")

    # ── 保存 CSV ──
    with open(OUT_DIR / "behavior_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "comm_rate", "omis_rate", "rt_mean_ms", "rt_med_ms",
                    "rt_sd_ms", "preempt_rate", "n_trials", "n_nogo", "n_go"])
        for s in SUBJECTS_BEHAVIOR:
            m = subj_metrics[s]
            w.writerow([s, round(m["comm_rate"], 4), round(m["omis_rate"], 4),
                        round(m["rt_mean"], 1), round(m["rt_med"], 1),
                        round(m["rt_sd"], 1), round(m["preempt_rate"], 4),
                        m["n_trials"], m["n_nogo"], m["n_go"]])
    print(f"\n已保存: {OUT_DIR / 'behavior_summary.csv'}")


if __name__ == "__main__":
    main()
