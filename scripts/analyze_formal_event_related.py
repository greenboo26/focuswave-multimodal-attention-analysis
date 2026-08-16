"""
analyze_formal_event_related.py — 正式实验第一批事件相关分析（新框架 B）
========================================================================
背景（2026-08-16 方法学重构）:
  原"全程 30s 连续窗"废弃; 本脚本用"事件锚定窗"——以 commission（NoGo 误按）
  为锚点, 对比错误前 30s vs 错误后 30s 的生理, 检验"错误是否伴随生理变化"。

  预实验教训（08-13/08-14）:
    1. "错误窗 BR 效应"实为错误后反馈反应, 错误前无差异（非前兆）
    2. NoGo 密集时前后窗重叠其他 commission, 功效不足
  本脚本: 排除前后窗含其他 commission 的事件（间隔 <60s 剔除）,
  用配对 Wilcoxon（后 vs 前）检验反馈反应。

功能: 提取 commission 事件前/后 30s 的 HR/RMSSD/BR, 配对比较。

数据: 毫米波原始 npz + 行为 CSV（commission 事件 onset）

重要: 无 ECG 金标准, HR/RMSSD 数值未验证, 结论定级=探索性。

用法:
  cd 08_算法/scripts
  python3.14 analyze_formal_event_related.py

输出:
  output/06_正式实验/事件相关/event_related_summary.csv + .md
  控制台汇总

依赖: numpy, scipy
"""

import csv
import glob
from pathlib import Path

import numpy as np
from scipy import stats

import analyze_mmwave_hrv as rhrv
from analyze_mmwave_hrv import load_timestamps, load_frames, analyze_window_auto

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"E:\正式实验")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验")
OUT_DIR = OUT_ROOT / "事件相关"
SUBJECTS = ["011", "012", "013", "014", "016"]  # 行为有效 5 人（015 规则反排除）
PRE_MS = 30_000     # 错误前窗长（ms）
POST_MS = 30_000    # 错误后窗长（ms）
MIN_GAP_MS = 60_000  # 事件最小间隔: 前后窗含其他 commission 则剔除
FEATURES = ["hr_bpm", "rmssd_ms", "br_bpm"]  # 短窗只用 RMSSD, 不用 SDNN


def load_commission_events(subject):
    """提取 commission 事件 onset_ms（NoGo 误按）。

    Args:
        subject: 被试编号

    Returns:
        list[int]: 事件绝对 onset_ms（升序）
    """
    events = []
    for f in sorted(glob.glob(str(DATA_ROOT / f"sub-{subject}_" / "beh" /
                                 f"sub-{subject}_Block*_beh.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r["is_no_go"] == "1" and r["response"] == "1":
                events.append(int(float(r["absolute_onset_time"])))
    events.sort()
    return events


def filter_isolated_events(events, gap_ms=MIN_GAP_MS):
    """保留前后 60s 内无其他 commission 的孤立事件（避免窗重叠）。

    Args:
        events: onset_ms 升序列表
        gap_ms: 最小间隔

    Returns:
        list[int]: 孤立事件 onset_ms
    """
    isolated = []
    for i, e in enumerate(events):
        left_ok = (i == 0) or (e - events[i - 1] >= gap_ms)
        right_ok = (i == len(events) - 1) or (events[i + 1] - e >= gap_ms)
        if left_ok and right_ok:
            isolated.append(e)
    return isolated


def analyze_event(subject, onset_ms, py_ms, frame_idx):
    """提取事件前/后 30s 生理。

    Args:
        subject: 被试编号
        onset_ms: 事件 onset
        py_ms/frame_idx: 时间戳

    Returns:
        dict: {pre: {hr,rmssd,br}, post: {...}} 或 None（数据不足）
    """
    def _win(t0_ms, t1_ms):
        fa = int(np.searchsorted(py_ms, t0_ms))
        fb = int(np.searchsorted(py_ms, t1_ms))
        fa = min(max(fa, 0), len(frame_idx) - 1)
        fb = min(fb, len(frame_idx) - 1)
        if fb - fa < 1000:  # 少于 ~10s 数据
            return None
        iq = load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
        res = analyze_window_auto(iq, method="vmd_heart")
        if res is None:
            return None
        return {
            "hr_bpm": res[0].get("hr_time_bpm"),
            "rmssd_ms": res[0].get("hrv", {}).get("RMSSD_ms"),
            "br_bpm": res[0].get("br_freq_bpm"),
        }

    pre = _win(onset_ms - PRE_MS, onset_ms)
    post = _win(onset_ms, onset_ms + POST_MS)
    if pre is None or post is None:
        return None
    return {"pre": pre, "post": post}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("  正式实验第一批事件相关分析（新框架 B）")
    print("  锚点 = commission（NoGo 误按）; 对比错误前/后 30s")
    print("  注意: 无 ECG 金标准, 结论定级 = 探索性")
    print("=" * 72)

    all_records = []
    for s in SUBJECTS:
        # 设置模块全局变量
        rhrv.SUBJECT = s.zfill(3)
        rhrv.DATA_ROOT = DATA_ROOT
        rhrv.MMWAVE_DIR = DATA_ROOT / f"sub-{s}_" / "mmwave"
        rhrv.BEH_TIMELINE = DATA_ROOT / f"sub-{s}_" / "beh" / "master_timeline.csv"
        frame_idx, py_ms = load_timestamps()
        rhrv.FIRST_FRAME = int(frame_idx[0])
        rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK

        events = load_commission_events(s)
        isolated = filter_isolated_events(events)
        print(f"\nsub-{s}: commission {len(events)} 个, 孤立（可分析）{len(isolated)} 个")

        n_ok = 0
        for onset in isolated:
            rec = analyze_event(s, onset, py_ms, frame_idx)
            if rec is None:
                continue
            n_ok += 1
            for phase, data in rec.items():
                all_records.append({
                    "subject": s, "onset_ms": onset, "phase": phase, **data
                })
        print(f"  提取成功 {n_ok} 个事件（前/后窗均有效）")

    print(f"\n[汇总] 有效事件记录 {len(all_records)} 条")

    # ── 配对比较（后 vs 前）──
    print("\n配对比较（错误后 vs 错误前, 被试内 z-score 后配对 Wilcoxon）")
    for feat in FEATURES:
        deltas = []  # 每事件 post - pre
        for s in SUBJECTS:
            subj = [r for r in all_records if r["subject"] == s and r.get(feat) is not None]
            # 按事件配对
            events = {}
            for r in subj:
                events.setdefault(r["onset_ms"], {})[r["phase"]] = r[feat]
            for onset, phases in events.items():
                if "pre" in phases and "post" in phases:
                    deltas.append(phases["post"] - phases["pre"])
        if len(deltas) >= 5:
            w, p = stats.wilcoxon(deltas)
            print(f"  {feat:<12} Δ(post-pre) 中位 {np.median(deltas):+.1f}, "
                  f"Wilcoxon p={p:.3f}, n={len(deltas)}")

    # ── 保存 ──
    with open(OUT_DIR / "event_related_summary.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "onset_ms", "phase", "hr_bpm", "rmssd_ms", "br_bpm"])
        for r in all_records:
            w.writerow([r["subject"], r["onset_ms"], r["phase"],
                        r.get("hr_bpm"), r.get("rmssd_ms"), r.get("br_bpm")])
    print(f"\n已保存: {OUT_DIR / 'event_related_summary.csv'}")


if __name__ == "__main__":
    main()
