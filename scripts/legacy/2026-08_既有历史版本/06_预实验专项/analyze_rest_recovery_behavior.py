"""
休息恢复效应的行为检验（Block 内轨迹）
======================================
思路（用户提出）: 若休息有效, Block 内应有"开头好→末尾差"的疲劳轨迹,
且每个 Block 开头（休息后）应比上一 Block 末尾（休息前）表现更好。

分析:
  1. 每 Block 216 试次分 4 段（各 54 试次）
  2. 每段 commission 率 / omission 率 / RT 中位数
  3. Block 内轨迹（段1→段4）+ 休息前后对比（本 Block 段4 vs 下一 Block 段1）
  4. 被试内配对检验（n=8, 003-010; 剔除 001/002 摆位失误 + 000 练习效应）

用法:
    cd 08_算法/scripts
    python analyze_rest_recovery_behavior.py

输出: output/预实验/03_跨被试/09_预实验-restHRV变化/behavior_recovery/
"""

import csv
from pathlib import Path

import numpy as np
from scipy import stats

# ============================================================
# 配置
# ============================================================
DATA_ROOT = Path("J:/预实验")
SUBJECTS = ["003", "004", "005", "006", "007", "008", "009", "010"]  # 剔除 001/002 摆位失误 + 000 练习效应
N_SEG = 4               # 每 Block 分段数 (216/4=54 试次)
RT_PREEMPT_MS = 150     # RT 低于此判预判按键 (<150ms 不可能真实视觉反应)
OUT_DIR = (Path(__file__).resolve().parent.parent / "output" / "预实验"
           / "03_跨被试" / "09_预实验-restHRV变化" / "behavior_recovery")


def load_block(subject: str, block: int) -> list[dict]:
    """加载单被试单 Block 的逐试次数据。

    参数:
        subject: 被试编号
        block: Block 序号 (1-6)
    返回:
        list[dict]: 试次行
    """
    # Block 文件名带条件 (Block1_A 等), 用 glob 匹配
    for f in (DATA_ROOT / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block{block}_*_beh.csv"):
        return list(csv.DictReader(open(f, encoding="utf-8-sig")))
    return []


def seg_metrics(trials: list[dict]) -> dict:
    """一段试次的分型指标。

    预判是规律任务的自然策略（SART 机制: 规律→自动化→走神）, 不做设计
    干预, 只在数据层分型:
      - commission 分型: 真误按 (RT≥150) vs 预判性误按 (RT<150)
      - 预判率: correct 试次中 RT<150 比例 = 自动化/策略依赖指标
      - omission 含预判性漏按成分（被试预判"是苹果"故意不按但错）,
        自报校准见问卷第 4 题, 本函数保留原始 omission 供对比

    参数:
        trials: 一段试次
    返回:
        dict: {commission_true, commission_preempt, preempt_rate,
               omission, rt_median}
    """
    n_go = sum(1 for t in trials if t.get("is_no_go") == "0")
    n_nogo = sum(1 for t in trials if t.get("is_no_go") == "1")
    n_comm_true = sum(1 for t in trials if t.get("commission") == "1"
                      and t.get("rt") and float(t["rt"]) >= RT_PREEMPT_MS)
    n_comm_pre = sum(1 for t in trials if t.get("commission") == "1"
                     and t.get("rt") and float(t["rt"]) < RT_PREEMPT_MS)
    n_omiss = sum(1 for t in trials if t.get("omission") == "1")
    n_correct = sum(1 for t in trials if t.get("correct") == "1" and t.get("rt"))
    n_preempt_correct = sum(1 for t in trials if t.get("correct") == "1"
                            and t.get("rt") and float(t["rt"]) < RT_PREEMPT_MS)
    rts = [float(t["rt"]) for t in trials
           if t.get("correct") == "1" and t.get("rt")
           and RT_PREEMPT_MS <= float(t["rt"]) < 1200]
    return {
        "commission_true": n_comm_true / n_nogo if n_nogo else float("nan"),
        "commission_preempt": n_comm_pre / n_nogo if n_nogo else float("nan"),
        "preempt_rate": n_preempt_correct / n_correct if n_correct else float("nan"),
        "omission": n_omiss / n_go if n_go else float("nan"),
        "rt_median": float(np.median(rts)) if rts else float("nan"),
    }


def paired(vals: list[float]) -> tuple[float, float, int]:
    """单样本 t 检验, 返回 (均值, p, n)。"""
    vals = [v for v in vals if v == v]
    if len(vals) < 3:
        return float("nan"), float("nan"), len(vals)
    t, p = stats.ttest_1samp(vals, 0)
    return float(np.mean(vals)), float(p), len(vals)


def main() -> None:
    """分析 Block 内轨迹与休息前后对比。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 每被试每 Block 4 段指标
    sub_block_seg = {}
    for s in SUBJECTS:
        for b in range(1, 7):
            trials = load_block(s, b)
            if not trials:
                continue
            n = len(trials)
            seg_size = n // N_SEG
            for k in range(N_SEG):
                seg = trials[k * seg_size:(k + 1) * seg_size]
                sub_block_seg[(s, b, k + 1)] = seg_metrics(seg)

    # 1. Block 内轨迹: 段1 vs 段4 (每被试每 Block 配对)
    print("=" * 60)
    print("休息恢复效应的行为检验（8 名被试 003-010, 每 Block 分 4 段, 预判分型）")
    print("=" * 60)
    print("\n[1] Block 内轨迹 (段4 - 段1):")
    for name, key in [("真误按率", "commission_true"),
                      ("预判误按率", "commission_preempt"),
                      ("预判率 (correct 中 RT<150)", "preempt_rate"),
                      ("omission 率 (含预判性漏按)", "omission"),
                      ("RT 中位 (ms, 剔预判)", "rt_median")]:
        diffs = []
        for s in SUBJECTS:
            for b in range(1, 7):
                if (s, b, 1) in sub_block_seg and (s, b, 4) in sub_block_seg:
                    d = sub_block_seg[(s, b, 4)][key] - sub_block_seg[(s, b, 1)][key]
                    if d == d:
                        diffs.append(d)
        m, p, n = paired(diffs)
        sig = "*" if p < 0.05 else ""
        print(f"  {name}: Δ={m:+.4f}, p={p:.3f}, n={n} {sig}")

    # 2. 休息前后对比: 本 Block 段4 vs 下一 Block 段1
    print("\n[2] 休息前后对比 (下一 Block 段1 - 本 Block 段4):")
    for name, key in [("真误按率", "commission_true"),
                      ("预判误按率", "commission_preempt"),
                      ("预判率 (correct 中 RT<150)", "preempt_rate"),
                      ("omission 率 (含预判性漏按)", "omission"),
                      ("RT 中位 (ms, 剔预判)", "rt_median")]:
        diffs = []
        for s in SUBJECTS:
            for b in range(1, 6):  # Block1-5 → 与 Block2-6 对比
                if (s, b, 4) in sub_block_seg and (s, b + 1, 1) in sub_block_seg:
                    d = sub_block_seg[(s, b + 1, 1)][key] - sub_block_seg[(s, b, 4)][key]
                    if d == d:
                        diffs.append(d)
        m, p, n = paired(diffs)
        sig = "*" if p < 0.05 else ""
        print(f"  {name}: Δ={m:+.4f}, p={p:.3f}, n={n} {sig}")

    # 3. 轨迹图 (5 指标 2×3 布局)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, (name, key) in zip(axes.flat, [
            ("真误按率", "commission_true"),
            ("预判误按率", "commission_preempt"),
            ("预判率 (RT<150)", "preempt_rate"),
            ("omission 率", "omission"),
            ("RT 中位 (ms, 剔预判)", "rt_median")]):
        for b in range(1, 7):
            xs, ys = [], []
            for k in range(1, 5):
                vals = [sub_block_seg[(s, b, k)][key] for s in SUBJECTS
                        if (s, b, k) in sub_block_seg]
                vals = [v for v in vals if v == v]
                if vals:
                    xs.append(k)
                    ys.append(np.mean(vals))
            ax.plot(xs, ys, "o-", label=f"Block{b}", alpha=0.7, markersize=4)
        ax.set_xlabel("Block 内分段 (1=开头, 4=末尾)")
        ax.set_ylabel(name)
        ax.set_title(f"{name} Block 内轨迹")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
    axes[1, 2].axis("off")  # 第 6 格空
    fig.suptitle("Block 内行为轨迹（预判分型, 8 人均值）", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "behavior_block_trajectory.png", dpi=150)
    plt.close(fig)
    print(f"\n图: {OUT_DIR / 'behavior_block_trajectory.png'}")


if __name__ == "__main__":
    main()


