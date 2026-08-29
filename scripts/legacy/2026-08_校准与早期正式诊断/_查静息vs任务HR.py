"""
_查静息vs任务HR.py — 正式实验 6 被试静息基线 vs 任务段 HR 对比
================================================================
背景: 9779（金标准被试）ECG 显示其静息心率 85、任务段 84.7~88.4，
      但毫米波任务段检出 56~61（半频锁定）。需判断正式实验 6 被试
      的毫米波 HR（54.7~66.4）是真实低心率还是也锁了半频。

方法: 静息基线（180s, 无按键, 毫米波相对可信）HR 作为"真实静息心率"
      的代理。若基线 HR ≈ 任务段 HR（均 55~65），说明被试真实心率低,
      任务段值可信; 若基线 HR 高（85+）而任务段掉到 55~65, 说明任务
      段锁半频。

数据: E:\\正式实验\\sub-XXX_\\（mmwave + beh/master_timeline.csv）

用法:
  cd 08_算法/scripts
  python3.14 _查静息vs任务HR.py

依赖: numpy（复用 analyze_mmwave_hrv 管线）
"""

import csv
from pathlib import Path

import numpy as np

import analyze_mmwave_hrv as rhrv
from analyze_mmwave_hrv import load_timestamps, load_frames, analyze_window_auto

# ============================================================
# 参数声明
# ============================================================
DATA_ROOT = Path(r"E:\正式实验")
SUBJECTS = ["011", "012", "013", "014", "015", "016"]
WINDOW_MS = 30_000   # 窗长 30s（与质量评估/全程窗一致）
STEP_MS = 30_000     # 无重叠步进


def load_segments(subject):
    """从 master_timeline 提取 baseline 与各 block 的 (start_ms, stop_ms)。

    Args:
        subject: 被试编号

    Returns:
        dict: {'baseline': (start, stop), 'block1': (start, stop), ...}
    """
    segs = {}
    with open(DATA_ROOT / f"sub-{subject}_" / "beh" / "master_timeline.csv",
              encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            ev = r["event"]
            # 跳过非时间戳行（python_version/psychopy_version 等尾部元数据）
            if ev not in ("baseline_start", "baseline_stop",
                          "block_start", "block_stop"):
                continue
            ms = int(r["unix_ms"])
            if ev == "baseline_start":
                segs["baseline"] = [ms, None]
            elif ev == "baseline_stop":
                segs["baseline"][1] = ms
            elif ev == "block_start":
                blk = int(r["detail"].split("_")[0].replace("Block", ""))
                segs[f"block{blk}"] = [ms, None]
            elif ev == "block_stop":
                blk = int(r["detail"].split("_")[0].replace("Block", ""))
                segs[f"block{blk}"][1] = ms
    # 只保留起止齐全的段
    return {k: tuple(v) for k, v in segs.items() if v[1] is not None}


def segment_hr(subject, seg_name, t0_ms, t1_ms, py_ms, frame_idx):
    """提取某段内 30s 窗的 HR 列表。

    Args:
        subject: 被试编号
        seg_name: 段名
        t0_ms/t1_ms: 段起止 unix_ms
        py_ms/frame_idx: 毫米波时间戳

    Returns:
        list[float]: 各 30s 窗的 HR（不可信窗为 None）
    """
    hrs = []
    for t in range(t0_ms, t1_ms, STEP_MS):
        w0, w1 = t, t + WINDOW_MS
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w1))
        fa = min(max(fa, 0), len(frame_idx) - 1)
        fb = min(fb, len(frame_idx) - 1)
        if fb - fa < 500:  # 少于约 5s 数据
            hrs.append(None)
            continue
        iq = load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
        res = analyze_window_auto(iq, method="vmd_heart")
        if res is None:
            hrs.append(None)
        else:
            hrs.append(res[0].get("hr_time_bpm"))
    return hrs


def main():
    print("=" * 72)
    print("  正式实验 6 被试：静息基线 HR vs 任务段 HR")
    print("  （静息基线无按键，毫米波相对可信，作为真实静息心率代理）")
    print("=" * 72)

    for s in SUBJECTS:
        rhrv.SUBJECT = s
        rhrv.DATA_ROOT = DATA_ROOT
        rhrv.MMWAVE_DIR = DATA_ROOT / f"sub-{s}_" / "mmwave"
        rhrv.BEH_TIMELINE = DATA_ROOT / f"sub-{s}_" / "beh" / "master_timeline.csv"
        frame_idx, py_ms = load_timestamps()
        rhrv.FIRST_FRAME = int(frame_idx[0])
        rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK

        segs = load_segments(s)
        print(f"\n=== sub-{s} ===")
        for seg_name in ["baseline", "block1", "block2", "block3"]:
            if seg_name not in segs:
                print(f"  {seg_name:<10} 无数据")
                continue
            t0, t1 = segs[seg_name]
            hrs = segment_hr(s, seg_name, t0, t1, py_ms, frame_idx)
            valid = [h for h in hrs if h is not None]
            if valid:
                med = np.median(valid)
                print(f"  {seg_name:<10} {(t1-t0)/1000:>5.0f}s  "
                      f"HR中位 {med:>5.1f}  范围 {min(valid):.0f}-{max(valid):.0f}  "
                      f"可信窗 {len(valid)}/{len(hrs)}")
            else:
                print(f"  {seg_name:<10} {(t1-t0)/1000:>5.0f}s  无可信窗")


if __name__ == "__main__":
    main()


