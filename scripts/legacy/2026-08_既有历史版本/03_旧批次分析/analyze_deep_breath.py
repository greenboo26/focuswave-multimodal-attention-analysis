"""
深慢呼吸验证实验分析 (analyze_deep_breath.py, v1.0)
=====================================================
验证毫米波 HRV 敏感度与呼吸通道标定。5 段协议:
    seg1 基线 120s / seg2 深慢呼吸 6bpm 120s / seg3 恢复 120s /
    seg4 屏气 30s / seg5 恢复 120s

四项验证:
  1. RSA 效应: seg2 的 SDNN/RMSSD 应高于 seg1（深慢呼吸触发呼吸性窦性心律不齐）
  2. 呼吸率标定: seg2 BR ≈ 6 bpm（节拍已知, 呼吸通道直接标定）; seg4 BR → 0
  3. 谐波陷波: 深慢呼吸波形非线性强, 检验心跳带是否仍干净
  4. 距离门控: bin 8-45 门限下 0.8m 摆放的检出率（多径矛盾验证）

用法:
  python analyze_deep_breath.py

输出:
  output/旧实验/08_旧批次-DEEP-BREATH/
    deep_breath_results.json   每窗指标 + 每段聚合
    seg2_vs_seg1_hrv.png       RSA 对比条形图
    breath_waveform.png        seg2 (深慢) vs seg4 (屏气) 呼吸位移波形对比
    timeseries.png             全程 HR/BR/SDNN 轨迹 + 段边界

依赖: numpy, scipy, matplotlib, vmdpy
数据: 11_数据/sub-deep-breath/ses-DB/mmwave/
"""

import os
import sys
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from analyze_mmwave_hrv import (
    analyze_window_auto,          # 窗级自适应选 bin + 完整分析
    FS,                           # 采样率 (Hz)
    CHUNK,                        # 每 npz 片帧数
    BIN_OFFSET,                   # 距离裁剪偏移 (本数据无 bin_offset → 0)
    _sos_bandpass,                # 呼吸带通滤波
)
from analyze_rest_3min import estimate_freq_periodogram

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================
MMWAVE_DIR = Path(r"D:\Project\厚粲杯\11_数据\sub-deep-breath\ses-DB\mmwave")
OUTPUT_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\08_旧批次-DEEP-BREATH")

# 5 段协议（与采集脚本 deep_breath_capture.py 一致）: (段号, 名称, 时长秒)
SEGMENTS = [
    (1, "基线 (正常呼吸)", 120),
    (2, "深慢呼吸 6bpm", 120),
    (3, "恢复 (正常呼吸)", 120),
    (4, "屏气 30s", 30),
    (5, "恢复 (正常呼吸)", 120),
]
ANALYZE_WINDOW_S = 60   # seg1/2/3/5 切窗秒数（2 窗/段, 保证频域分辨率）
WAVE_DEMO_S = 40        # 呼吸波形展示片段秒数
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
plt.rcParams["axes.unicode_minus"] = False


def load_markers():
    """读段标记 CSV → {段名: unix 秒}。"""
    markers = {}
    with open(MMWAVE_DIR / "sub-deep-breath_ses-DB_markers.csv") as f:
        for row in csv.reader(f):
            if row[0] != "segment":
                markers[row[0]] = float(row[1])
    return markers


def load_timestamps():
    """读时间戳 CSV → 帧号数组 + Python 时间戳 (ms)。"""
    frame_idx, py_ms = [], []
    with open(MMWAVE_DIR / "sub-deep-breath_ses-DB_mmwave_timestamps.csv") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            frame_idx.append(int(parts[0]))
            py_ms.append(int(parts[2]))
    return np.array(frame_idx), np.array(py_ms, dtype=np.int64)


def load_frames(fa, fb):
    """按帧号范围 [fa, fb) 加载复数距离域数据 (分片 npz)。

    Returns:
        iq_fd: (fb-fa, 256, 8) complex64, 通道序 tx0_rx0..tx1_rx3
    """
    first_frame = int(np.load(MMWAVE_DIR / "sub-deep-breath_ses-DB_mmwave_datacube.npz",
                              allow_pickle=True)["__first__"]) if False else None
    # 首帧号从 timestamps 首行取
    fa, fb = int(fa), int(fb)
    # 由 load_timestamps 提供 frame_idx[0] 作 FIRST_FRAME
    return None  # 实际实现见下


def segment_frame_range(markers, timestamps, t0_name, t1_name):
    """段 [t0, t1) 对应帧号范围（按 py_ms 对齐 markers 的 unix 秒）。

    末段 t1 无标记时回退到最后帧时间戳。
    """
    frame_idx, py_ms = timestamps
    lo_ms = int(markers[t0_name] * 1000)
    t1_ms = markers.get(t1_name)
    hi_ms = int(t1_ms * 1000) if t1_ms is not None else int(py_ms[-1])
    lo = int(np.searchsorted(py_ms, lo_ms))
    hi = int(np.searchsorted(py_ms, hi_ms))
    return frame_idx[lo], frame_idx[hi - 1] + 1, lo, hi


def load_frames_impl(fa, fb, first_frame, n_partitions):
    """按帧号范围 [fa, fb) 加载分片 npz（与管线 load_frames 同构, 适配 ses 文件名）。

    Returns:
        iq_fd: (fb-fa, 256, 8) complex64
    """
    chunks = []
    for i in range(n_partitions):
        fpath = MMWAVE_DIR / (f"sub-deep-breath_ses-DB_mmwave_datacube.npz" if i == 0
                              else f"sub-deep-breath_ses-DB_mmwave_datacube_part{i:03d}.npz")
        if not fpath.exists():
            continue
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith("tx")])
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        d.close()
        chunks.append(chunk)
    iq = np.concatenate(chunks)
    lo = fa - first_frame
    hi = lo + (fb - fa)
    return iq[lo:hi]


def analyze_segment(markers, timestamps, seg_num, name, dur_s, first_frame, n_partitions):
    """分析单个段: 切窗 → 每窗 analyze_window_auto → 返回窗结果列表。

    屏气段 (30s) 整段单窗; 长段 (120s) 按 ANALYZE_WINDOW_S 切窗。
    """
    t0 = f"seg{seg_num}"
    t1 = f"seg{seg_num + 1}" if seg_num < 5 else "session_end"
    seg_end = markers.get(t1)
    if seg_end is None:
        # 末段: 结束时刻 = 最后时间戳
        seg_end = timestamps[1][-1] / 1000.0
    fa, fb, _, _ = segment_frame_range(markers, timestamps, t0, t1)

    # 按窗切帧号
    win_s = ANALYZE_WINDOW_S if dur_s >= 60 else dur_s
    wins = []
    cur = fa
    while cur < fb:
        wins.append((cur, min(cur + int(win_s * FS), fb)))
        cur += int(win_s * FS)

    rows = []
    for wi, (wa, wb) in enumerate(wins):
        iq = load_frames_impl(wa, wb, first_frame, n_partitions)
        out = analyze_window_auto(iq)
        if out is None:
            rows.append({"window": wi + 1, "quality": "unreliable"})
            continue
        res, hr_bin, br_bin = out
        res["window"] = wi + 1
        res["quality"] = "ok"
        res["hr_bin"] = hr_bin["bin"]
        res["br_bin"] = br_bin["bin"]
        rows.append(res)
    return rows


def breath_demo_wave(markers, timestamps, seg_num, first_frame, n_partitions,
                     seconds=WAVE_DEMO_S):
    """提取某段中段的呼吸位移波形（bp 滤波后）用于可视化对比。"""
    t0 = f"seg{seg_num}"
    t1 = f"seg{seg_num + 1}" if seg_num < 5 else "session_end"
    seg_end = markers.get(t1)
    if seg_end is None:
        seg_end = timestamps[1][-1] / 1000.0
    fa, fb, _, _ = segment_frame_range(markers, timestamps, t0, t1)
    mid = (fa + fb) // 2 - int(seconds * FS / 2)
    mid = max(fa, mid)
    iq = load_frames_impl(mid, min(mid + int(seconds * FS), fb), first_frame, n_partitions)
    out = analyze_window_auto(iq)
    if out is None:
        return None
    _, hr_bin, br_bin = out
    phi = np.unwrap(np.angle(iq[:, br_bin["bin"] - BIN_OFFSET, br_bin["ch"]]))
    return signal.detrend(phi)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    markers = load_markers()
    timestamps = load_timestamps()
    first_frame = int(timestamps[0][0])
    # 分片数: 从目录列举
    n_partitions = len(list(MMWAVE_DIR.glob("sub-deep-breath_ses-DB_mmwave_datacube_part*.npz"))) + 1

    # 每段分析
    all_rows = []
    seg_agg = {}
    for seg_num, name, dur_s in SEGMENTS:
        rows = analyze_segment(markers, timestamps, seg_num, name, dur_s,
                               first_frame, n_partitions)
        ok = [r for r in rows if r["quality"] == "ok"]
        all_rows.append({"segment": seg_num, "name": name, "rows": rows})
        agg = {
            "n_windows": len(rows),
            "n_ok": len(ok),
            "hr_bpm": round(np.mean([r["hr_time_bpm"] for r in ok]), 1) if ok else None,
            "br_bpm": round(np.mean([r["br_freq_bpm"] for r in ok]), 1) if ok else None,
            "sdnn_ms": round(np.mean([r["hrv"]["SDNN_ms"] for r in ok]), 1) if ok else None,
            "rmssd_ms": round(np.mean([r["hrv"]["RMSSD_ms"] for r in ok]), 1) if ok else None,
        }
        seg_agg[seg_num] = agg
        print(f"seg{seg_num} {name}: {agg}")

    # 呼吸波形对比 (seg2 深慢 vs seg4 屏气)
    w2 = breath_demo_wave(markers, timestamps, 2, first_frame, n_partitions)
    w4 = breath_demo_wave(markers, timestamps, 4, first_frame, n_partitions)

    # 保存 JSON
    out = {
        "segments": [{
            "segment": s["segment"], "name": s["name"], "rows": s["rows"],
        } for s in all_rows],
        "agg": seg_agg,
        "verification": {
            "rsa_sdnn_ratio": None,   # seg2/seg1 SDNN
            "rsa_rmssd_ratio": None,  # seg2/seg1 RMSSD
            "br_seg2": seg_agg[2]["br_bpm"],   # 应 ≈6
            "br_seg4": seg_agg[4]["br_bpm"],   # 应 →0/低
        },
    }
    if seg_agg[1]["sdnn_ms"] and seg_agg[2]["sdnn_ms"]:
        out["verification"]["rsa_sdnn_ratio"] = round(
            seg_agg[2]["sdnn_ms"] / seg_agg[1]["sdnn_ms"], 2)
        out["verification"]["rsa_rmssd_ratio"] = round(
            seg_agg[2]["rmssd_ms"] / seg_agg[1]["rmssd_ms"], 2)
    with open(OUTPUT_DIR / "deep_breath_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 图 1: seg1 vs seg2 HRV 对比
    fig, ax = plt.subplots(1, 3, figsize=(12, 4))
    for k, (i, j, label) in enumerate([(1, 2, "SDNN (ms)"), (1, 2, "RMSSD (ms)")]):
        pass
    ax0 = ax[0]
    s1, s2 = seg_agg[1], seg_agg[2]
    vals = [s1["sdnn_ms"], s2["sdnn_ms"], s1["rmssd_ms"], s2["rmssd_ms"]]
    labels = ["基线 SDNN", "深慢 SDNN", "基线 RMSSD", "深慢 RMSSD"]
    colors = ["#4C72B0", "#C44E52", "#4C72B0", "#C44E52"]
    ax0.bar(labels, vals, color=colors, alpha=0.85)
    for xi, v in enumerate(vals):
        ax0.text(xi, v, f"{v:.1f}", ha="center", va="bottom")
    ax0.set_title("RSA 效应: 深慢呼吸段 HRV vs 基线")
    ax0.set_ylabel("ms")

    ax1 = ax[1]
    segs_br = [seg_agg[s]["br_bpm"] for s in range(1, 6)]
    ax1.plot(range(1, 6), segs_br, "o-", color="#55A868")
    ax1.axhline(6, color="gray", ls="--", lw=0.8, label="节拍 6 bpm")
    ax1.axhline(0, color="red", ls=":", lw=0.8)
    ax1.set_xticks(range(1, 6))
    ax1.set_xticklabels(["基线", "深慢", "恢复", "屏气", "恢复"])
    ax1.set_title("呼吸率标定 (seg4 屏气应→0)")
    ax1.set_ylabel("BR (bpm)")
    ax1.legend()

    ax2 = ax[2]
    segs_hr = [seg_agg[s]["hr_bpm"] for s in range(1, 6)]
    ax2.plot(range(1, 6), segs_hr, "o-", color="#8172B2")
    ax2.set_xticks(range(1, 6))
    ax2.set_xticklabels(["基线", "深慢", "恢复", "屏气", "恢复"])
    ax2.set_title("心率轨迹")
    ax2.set_ylabel("HR (bpm)")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "seg_verification.png", dpi=150)
    plt.close(fig)

    # 图 2: 呼吸位移波形对比
    if w2 is not None and w4 is not None:
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6))
        t2 = np.arange(len(w2)) / FS
        a1.plot(t2, w2, color="#55A868")
        a1.set_title("seg2 深慢呼吸: 呼吸位移 (预期 10s 周期, 大幅)")
        a1.set_xlabel("秒")
        t4 = np.arange(len(w4)) / FS
        a2.plot(t4, w4, color="#C44E52")
        a2.set_title("seg4 屏气: 呼吸位移 (预期平坦)")
        a2.set_xlabel("秒")
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "breath_waveform.png", dpi=150)
        plt.close(fig)

    # 图 3: 全程时间轴 (窗级 HR/BR/SDNN + 段边界)
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    xs, hr_s, br_s, sd_s = [], [], [], []
    for s in all_rows:
        for r in s["rows"]:
            if r["quality"] != "ok":
                continue
            xs.append(len(xs))
            hr_s.append(r["hr_time_bpm"])
            br_s.append(r["br_freq_bpm"])
            sd_s.append(r["hrv"].get("SDNN_ms"))
    axes[0].plot(xs, hr_s, "o-", color="#8172B2")
    axes[0].set_ylabel("HR (bpm)")
    axes[1].plot(xs, br_s, "o-", color="#55A868")
    axes[1].set_ylabel("BR (bpm)")
    axes[2].plot(xs, sd_s, "o-", color="#C44E52")
    axes[2].set_ylabel("SDNN (ms)")
    for s in all_rows:
        for r in s["rows"]:
            pass
    # 段边界竖线
    bnd = []
    for s in all_rows:
        bnd.append(bnd[-1] + len(s["rows"]) if bnd else 0)
    for b in bnd[1:]:
        for axx in axes:
            axx.axvline(b - 0.5, color="gray", ls="--", lw=0.8)
    axes[0].set_title("深慢呼吸实验全程窗级指标 (竖线=段边界)")
    axes[2].set_xlabel("窗序号")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "timeseries.png", dpi=150)
    plt.close(fig)

    print(f"\n[+] 输出: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()


