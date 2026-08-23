"""
analyze_formal_probe_centric.py — 正式实验第一批探针中心分析（新框架 A）
========================================================================
背景（2026-08-16 方法学重构）:
  原"全程 30s 连续窗 + SDNN 相关"框架废弃，原因:
    1. 30s 短窗算 SDNN 不符 HRV 规范（SDNN 需 ≥5min）
    2. 30s 窗粒度与秒级注意波动错配
    3. 探针标签（瞬间状态）与全程连续切块语义不符
  新框架以"探针"为分析单位（Corcoran 2025 范式）:
    样本 = 180 探针（6 被试 × 30）;
    特征 = 探针前 30s 的 HR / RMSSD / BR（短窗只用 RMSSD, 不用 SDNN）;
    标签 = 注意状态(问题1) + 清醒程度(问题2, probe_vigilance)。

功能:
  1) 探针前 30s 生理特征描述
  2) 注意状态二分类对比（专注 vs 非专注, 被试内 z-score 后）
  3) 清醒程度 × 生理 Spearman 相关（被试内 z-score 合并）

数据: output/06_正式实验/SUB{XXX}-FULL/sub{XXX}_full_windows.json（探针前30s生理）
      + 行为 CSV（probe_response/probe_vigilance）

重要: 无 ECG 金标准, HR/RMSSD 数值未验证倍频/半频锁定, 结论定级=探索性。

用法:
  cd 08_算法/scripts
  python3.14 analyze_formal_probe_centric.py

输出:
  output/06_正式实验/探针中心/probe_centric_summary.csv + .md
  控制台汇总

依赖: numpy, scipy
"""

import csv
import glob
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"D:\正式实验")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验")
OUT_DIR = OUT_ROOT / "探针中心"
SUBJECTS = ["011", "012", "013", "014", "015", "016"]  # 生理全 6 人
# 短窗（探针前 30s）只用这三个指标: HR / RMSSD / BR（SDNN 需 ≥5min, 短窗不用）
PROBE_FEATURES = ["hr_bpm", "rmssd_ms", "br_bpm"]
FEATURE_CN = {"hr_bpm": "心率 HR (bpm)", "rmssd_ms": "RMSSD (ms)", "br_bpm": "呼吸率 BR (bpm)"}
ATTENTION_LABELS = {"1": "专注", "2": "任务干扰", "3": "走神", "4": "大脑空白"}
VIGILANCE_LABELS = {1: "极度困倦", 2: "比较困倦", 3: "比较清醒", 4: "极度清醒"}


def load_probe_data(subject):
    """合并单被试的探针标签（CSV）与探针前 30s 生理（JSON）。

    已验证 JSON probes 顺序与 CSV 探针顺序一致（按 block×trial）。

    Args:
        subject: 被试编号

    Returns:
        list[dict]: 每探针 {attention, vigilance, hr, rmssd, br}
    """
    # 标签: 从行为 CSV
    labels = []
    for f in sorted(glob.glob(str(DATA_ROOT / f"sub-{subject}_" / "beh" /
                                 f"sub-{subject}_Block*_beh.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r["is_probe"] == "1" and r["probe_response"]:
                labels.append({
                    "attention": r["probe_response"],
                    "vigilance": int(r["probe_vigilance"]) if r["probe_vigilance"] else None,
                })
    # 生理: 从 JSON
    jd = json.load(open(OUT_ROOT / f"SUB{subject}-FULL" / f"sub{subject}_full_windows.json",
                        encoding="utf-8"))
    jprobes = jd["probes"]
    # 合并（取 min 长度, 顺序对齐已验证）
    out = []
    for lab, jp in zip(labels, jprobes):
        rec = {"subject": subject, "attention": lab["attention"],
               "vigilance": lab["vigilance"], "quality": jp.get("quality")}
        for feat in PROBE_FEATURES:
            rec[feat] = jp.get(feat) if jp.get("quality") == "ok" else None
        out.append(rec)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("  正式实验第一批探针中心分析（新框架 A）")
    print("  分析单位 = 探针; 特征 = 探针前 30s HR/RMSSD/BR")
    print("  注意: 无 ECG 金标准, 结论定级 = 探索性/信号存在性")
    print("=" * 72)

    # ── 收集全被试探针 ──
    all_probes = []
    for s in SUBJECTS:
        all_probes.extend(load_probe_data(s))
    ok_probes = [p for p in all_probes if p["quality"] == "ok"]
    if not all_probes:
        print("\n[数据] 未加载到正式实验探针，已跳过探针统计并保留空结果。请检查 DATA_ROOT 和输出 JSON。")
        with open(OUT_DIR / "probe_centric_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerow(["subject", "attention", "vigilance", "quality", "hr_bpm", "rmssd_ms", "br_bpm"])
        return
    print(f"\n[数据] 探针总数 {len(all_probes)}, 生理可信 {len(ok_probes)} "
          f"({len(ok_probes)/len(all_probes)*100:.0f}%)")

    # ── 1. 探针前 30s 生理特征描述 ──
    print("\n[1/3] 探针前 30s 生理特征描述（可信探针）")
    print(f"  {'特征':<16}{'中位':>8}{'均值':>8}{'SD':>8}{'范围':>16}{'n':>5}")
    for feat in PROBE_FEATURES:
        vals = [p[feat] for p in ok_probes if p.get(feat) is not None]
        if vals:
            print(f"  {FEATURE_CN[feat]:<16}{np.median(vals):>8.1f}{np.mean(vals):>8.1f}"
                  f"{np.std(vals):>8.1f}{f'{min(vals):.0f}-{max(vals):.0f}':>16}{len(vals):>5}")

    # ── 2. 注意状态二分类（专注 vs 非专注）──
    print("\n[2/3] 注意状态二分类对比（专注 vs 非专注, 被试内 z-score 后）")
    print("  （探针标签 80% 专注, 故用二分类; 非专注=任务干扰+走神+空白）")
    for feat in PROBE_FEATURES:
        z_on, z_off = [], []
        for s in SUBJECTS:
            subj = [p for p in ok_probes if p["subject"] == s and p.get(feat) is not None]
            vals = np.array([p[feat] for p in subj])
            if len(vals) < 5 or np.std(vals) == 0:
                continue
            z = (vals - np.mean(vals)) / np.std(vals)
            for p, zi in zip(subj, z):
                if p["attention"] == "1":
                    z_on.append(zi)
                else:
                    z_off.append(zi)
        if len(z_on) >= 5 and len(z_off) >= 5:
            # Mann-Whitney（非参数, 样本不独立时保守）
            u, p_mw = stats.mannwhitneyu(z_on, z_off, alternative="two-sided")
            # Cohen's d（z 分数差即标准化效应量）
            d = (np.mean(z_on) - np.mean(z_off)) / np.sqrt(
                ((len(z_on)-1)*np.var(z_on, ddof=1) + (len(z_off)-1)*np.var(z_off, ddof=1))
                / (len(z_on)+len(z_off)-2)) if len(z_on) > 1 and len(z_off) > 1 else 0
            print(f"  {FEATURE_CN[feat]:<16} 专注(n={len(z_on)}) vs 非专注(n={len(z_off)}): "
                  f"d={d:+.2f}, Mann-Whitney p={p_mw:.3f}")

    # ── 3. 清醒程度 × 生理 Spearman 相关 ──
    print("\n[3/3] 清醒程度（probe_vigilance, 4 点）× 生理 Spearman 相关")
    print("  （被试内 z-score 合并; 清醒程度分布偏清醒, 困倦样本少）")
    for feat in PROBE_FEATURES:
        z_pairs = []
        for s in SUBJECTS:
            subj = [p for p in ok_probes if p["subject"] == s and p.get(feat) is not None
                    and p.get("vigilance") is not None]
            if len(subj) < 5:
                continue
            vals = np.array([p[feat] for p in subj])
            z = (vals - np.mean(vals)) / (np.std(vals) + 1e-9)
            z_pairs.extend([(subj[i]["vigilance"], z[i]) for i in range(len(subj))])
        if len(z_pairs) >= 10:
            rho, pval = stats.spearmanr([x[0] for x in z_pairs], [x[1] for x in z_pairs])
            print(f"  {FEATURE_CN[feat]:<16} rho={rho:+.3f}, p={pval:.3f}, n={len(z_pairs)}")

    # ── 保存 ──
    with open(OUT_DIR / "probe_centric_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "attention", "vigilance", "quality", "hr_bpm",
                    "rmssd_ms", "br_bpm"])
        for p in all_probes:
            w.writerow([p["subject"], p["attention"], p["vigilance"], p["quality"],
                        p.get("hr_bpm"), p.get("rmssd_ms"), p.get("br_bpm")])

    # 注意状态×清醒程度 分布（描述）
    cross = Counter((p["attention"], p["vigilance"]) for p in all_probes
                    if p["vigilance"] is not None)
    print(f"\n[附录] 注意状态 × 清醒程度 交叉（n={sum(cross.values())}）")
    print(f"  {'注意状态':<10}" + "".join(f"{VIGILANCE_LABELS[v][:4]:>8}" for v in [1,2,3,4]))
    for a in ["1", "2", "3", "4"]:
        row = [cross.get((a, v), 0) for v in [1, 2, 3, 4]]
        print(f"  {ATTENTION_LABELS[a]:<10}" + "".join(f"{c:>8}" for c in row))

    print(f"\n已保存: {OUT_DIR / 'probe_centric_summary.csv'}")


if __name__ == "__main__":
    main()
