"""
analyze_preexp_robustness.py — 预实验全被试行为×毫米波相关稳健性检验
====================================================================
版本: v1.0 (2026-08-10)
功能: 对 analyze_mmwave_full.py 产出的全程窗结果做相关稳健性检验,
      验证"003 hr~RT 显著、000 rmssd~RT 边缘"这类相关是否稳健,
      排除离群窗/单一 block/分布形状（Pearson 假设）的虚假驱动。

检验维度:
  1. Pearson vs Spearman（分布形状稳健性）
  2. 分 block 相关（相关是否集中在某一任务条件）
  3. 剔除 HR 离群窗（1.5×IQR）后的相关
  4. 仅 n_trials ≥ 10 的窗（行为估计更稳的子集）
  5. 单窗 Jackknife（相关系数随逐窗剔除的变化范围）

探针窗补充: 可信探针的 HR/SDNN/RMSSD 描述统计与标签分布
  （预实验探针标签可能不平衡, 仅作基线描述）。

数据:
  输入: output/预实验/09_预实验-SUB{XXX}-FULL/sub{XXX}_full_windows.json
        + F:/预实验/sub-XXX_/beh/master_timeline.csv
  输出: output/预实验/03_跨被试/09_预实验-ROBUST-ALL/
        preexp_robustness.json   ← 全部检验结果
        preexp_robustness.txt    ← 可读报告

用法:
  cd 08_算法/scripts
  python analyze_preexp_robustness.py --data-root F:/预实验

依赖: numpy, scipy
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

SUBJECTS = ["000", "001", "002", "003", "004", "005", "006", "007"]  # 预实验全部有信号被试
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output" / "03_跨被试" / "09_预实验-ROBUST-ALL"
WINDOW_SEC = 30                      # 全程窗长（秒, 与 analyze_mmwave_full 一致）
MIN_TRIALS = 10                      # 行为估计稳定的最少窗内试次数
IQR_K = 1.5                          # 离群剔除系数（1.5×IQR 标准）

# 相关对: (毫米波指标, 行为指标)
CORR_PAIRS = [
    ("hr_bpm", "rt_mean"), ("hr_bpm", "rt_sd"),
    ("sdnn_ms", "rt_mean"), ("rmssd_ms", "rt_mean"),
    ("br_bpm", "rt_mean"), ("rmssd_ms", "n_err"),
]


# ============================================================
# 数据加载
# ============================================================

def load_windows(subject: str, out_root: Path) -> list[dict]:
    """读取全程窗 JSON（analyze_mmwave_full 产出）。"""
    path = out_root / "02_全程窗" / f"09_预实验-SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["windows"]


def load_block_map(data_root: Path, subject: str) -> dict:
    """解析 master_timeline.csv, 建立 mmwave 时间偏移 → block 标签映射。

    窗绝对时间 = mmwave_start_ms + t_start_s×1000; 落在
    [block_start, block_stop) 的窗归属该 block。

    参数:
        data_root: 数据根目录
        subject: 被试编号
    返回:
        dict: {"mmwave_start_ms": int, "blocks": [(label, t0_ms, t1_ms)]}
    """
    tl = data_root / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    mm_start = None
    blocks = []
    pending = None
    with open(tl, encoding="utf-8", newline="") as f:
        for parts in csv.reader(f):
            if len(parts) < 3 or not parts[2].strip().isdigit():
                continue
            event, detail, ts = parts[0], parts[1], int(parts[2])
            if event == "mmwave_start":
                mm_start = ts
            elif event == "block_start":
                pending = (detail, ts)
            elif event == "block_stop" and pending is not None:
                blocks.append((pending[0], pending[1], ts))
                pending = None
    if mm_start is None:
        raise ValueError(f"{subject} master_timeline 缺少 mmwave_start")
    return {"mmwave_start_ms": mm_start, "blocks": blocks}


def block_of_window(t_start_s: float, block_map: dict) -> str | None:
    """判断窗（相对 mmwave 的起始秒）属于哪个 block, 休息段返回 None。"""
    abs_ms = block_map["mmwave_start_ms"] + int((t_start_s + WINDOW_SEC / 2) * 1000)
    for label, t0, t1 in block_map["blocks"]:
        if t0 <= abs_ms < t1:
            return label
    return None


# ============================================================
# 相关检验
# ============================================================

def corr(xs, ys, method: str):
    """计算相关系数, 返回 (r, p, n)。"""
    x, y = np.asarray(xs, float), np.asarray(ys, float)
    if len(x) < 8:                                   # 样本过少不检验
        return None
    if method == "pearson":
        r, p = stats.pearsonr(x, y)
    else:
        r, p = stats.spearmanr(x, y)
    return {"r": round(float(r), 3), "p": round(float(p), 4), "n": int(len(x))}


def jackknife_corr(xs, ys):
    """逐窗剔除的单窗 Jackknife: 返回相关系数随剔除窗的变化区间。"""
    x, y = np.asarray(xs, float), np.asarray(ys, float)
    n = len(x)
    if n < 10:
        return None
    rs = []
    for i in range(n):
        keep = np.ones(n, bool)
        keep[i] = False
        r, _ = stats.pearsonr(x[keep], y[keep])
        rs.append(r)
    return {"min": round(float(np.min(rs)), 3), "max": round(float(np.max(rs)), 3),
            "range": round(float(np.max(rs) - np.min(rs)), 3)}


def robust_analysis(ok_windows: list[dict], block_map: dict) -> dict:
    """对可信窗集合做完整稳健性检验。

    参数:
        ok_windows: quality=ok 的全程窗
        block_map: block 时间映射
    返回:
        dict: 各检验维度的相关结果
    """
    out = {"n_windows": len(ok_windows)}

    # block 标签挂到每窗
    for w in ok_windows:
        w["_block"] = block_of_window(w["t_start_s"], block_map)

    # ── 1. 总体相关: Pearson + Spearman ──
    out["overall"] = {}
    for m, b in CORR_PAIRS:
        pairs = [(w[m], w[b]) for w in ok_windows
                 if w.get(m) is not None and w.get(b) is not None]
        if len(pairs) < 8:
            continue
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        out["overall"][f"{m}~{b}"] = {
            "pearson": corr(xs, ys, "pearson"),
            "spearman": corr(xs, ys, "spearman"),
            "jackknife_r": jackknife_corr(xs, ys),
        }

    # ── 2. 分 block 相关（hr~rt_mean, rmssd~rt_mean） ──
    out["by_block"] = {}
    for b_mm, b_beh in [("hr_bpm", "rt_mean"), ("rmssd_ms", "rt_mean")]:
        per_block = {}
        for label in sorted({w["_block"] for w in ok_windows if w["_block"]}):
            blk = [w for w in ok_windows if w["_block"] == label]
            pairs = [(w[b_mm], w[b_beh]) for w in blk
                     if w.get(b_mm) is not None and w.get(b_beh) is not None]
            if len(pairs) >= 8:
                per_block[label] = {
                    "n": len(pairs),
                    "pearson": corr([p[0] for p in pairs], [p[1] for p in pairs], "pearson"),
                }
        out["by_block"][f"{b_mm}~{b_beh}"] = per_block

    # ── 3. HR 离群剔除（1.5×IQR）后的相关 ──
    out["no_outlier_hr"] = {}
    hrs = [w["hr_bpm"] for w in ok_windows if w.get("hr_bpm")]
    if hrs:
        q1, q3 = np.percentile(hrs, [25, 75])
        lo, hi = q1 - IQR_K * (q3 - q1), q3 + IQR_K * (q3 - q1)
        sub = [w for w in ok_windows if w.get("hr_bpm") and lo <= w["hr_bpm"] <= hi]
        out["no_outlier_hr"]["range"] = [round(float(lo), 1), round(float(hi), 1)]
        for m, b in CORR_PAIRS:
            pairs = [(w[m], w[b]) for w in sub
                     if w.get(m) is not None and w.get(b) is not None]
            if len(pairs) >= 8:
                out["no_outlier_hr"][f"{m}~{b}"] = corr(
                    [p[0] for p in pairs], [p[1] for p in pairs], "pearson")

    # ── 4. 窗内试次数 ≥ MIN_TRIALS 的子集 ──
    out["min_trials"] = {}
    sub = [w for w in ok_windows if w.get("n_trials", 0) >= MIN_TRIALS]
    out["min_trials"]["n_windows"] = len(sub)
    for m, b in CORR_PAIRS:
        pairs = [(w[m], w[b]) for w in sub
                 if w.get(m) is not None and w.get(b) is not None]
        if len(pairs) >= 8:
            out["min_trials"][f"{m}~{b}"] = corr(
                [p[0] for p in pairs], [p[1] for p in pairs], "pearson")
    return out


# ============================================================
# 探针窗汇总
# ============================================================

def probe_summary(subject: str, out_root: Path) -> dict:
    """可信探针窗的 HR/HRV 描述统计与标签分布。"""
    path = out_root / "02_全程窗" / f"09_预实验-SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    with open(path, encoding="utf-8") as f:
        probes = json.load(f)["probes"]
    ok = [p for p in probes if p.get("quality") == "ok"]
    labels = {}
    for p in probes:
        labels[p["label_name"]] = labels.get(p["label_name"], 0) + 1
    summ = {"n_probes": len(probes), "n_ok": len(ok), "labels_all": labels,
            "labels_ok": {}, "metrics": {}}
    for p in ok:
        summ["labels_ok"][p["label_name"]] = summ["labels_ok"].get(p["label_name"], 0) + 1
    for m in ["hr_bpm", "sdnn_ms", "rmssd_ms", "br_bpm", "lf_hf"]:
        vals = [p[m] for p in ok if p.get(m) is not None]
        if vals:
            summ["metrics"][m] = {
                "median": round(float(np.median(vals)), 2),
                "mean": round(float(np.mean(vals)), 2),
                "sd": round(float(np.std(vals)), 2),
                "min": round(float(np.min(vals)), 2),
                "max": round(float(np.max(vals)), 2),
                "n": len(vals),
            }
    return summ


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="预实验相关稳健性检验")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_ROOT))
    args = parser.parse_args()

    data_root = Path(args.data_root)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_root = SCRIPT_DIR.parent / "output" / "预实验"

    result = {}
    print("=" * 60)
    print("  预实验全被试行为×毫米波相关稳健性检验")
    print("=" * 60)

    for subject in SUBJECTS:
        print(f"\n===== sub-{subject} =====")
        block_map = load_block_map(data_root, subject)
        wins = load_windows(subject, out_root)
        ok = [w for w in wins if w.get("quality") == "ok"]
        print(f"可信窗: {len(ok)}/{len(wins)}")
        result[subject] = {
            "robustness": robust_analysis(ok, block_map),
            "probes": probe_summary(subject, out_root),
        }

        # 控制台输出关键结果
        for key, v in result[subject]["robustness"]["overall"].items():
            pr, sp = v["pearson"], v["spearman"]
            if pr:
                jk = v["jackknife_r"]
                jk_str = f"Jackknife r∈{jk['min']}..{jk['max']}" if jk else "Jackknife n/a"
                print(f"  {key}: Pearson r={pr['r']} p={pr['p']} n={pr['n']} | "
                      f"Spearman r={sp['r']} p={sp['p']} | {jk_str}")

    # 保存
    json_path = out_dir / "preexp_robustness.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[json] {json_path}")

    # 可读报告
    txt_path = out_dir / "preexp_robustness.txt"
    lines = ["预实验全被试相关稳健性检验报告", "=" * 50, ""]
    for subject in SUBJECTS:
        lines.append(f"sub-{subject} 可信窗 {result[subject]['robustness']['n_windows']}")
        lines.append(f"  探针: {result[subject]['probes']['n_ok']}/{result[subject]['probes']['n_probes']} 可信, "
                     f"标签 {result[subject]['probes']['labels_all']}")
        for key, v in result[subject]["robustness"]["overall"].items():
            pr = v["pearson"]
            if pr:
                lines.append(f"  {key}: r={pr['r']} (p={pr['p']}, n={pr['n']}) | "
                             f"Spearman r={v['spearman']['r']} | "
                             f"Jackknife r∈[{v['jackknife_r']['min']}, {v['jackknife_r']['max']}]")
        lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[txt] {txt_path}")


if __name__ == "__main__":
    main()
