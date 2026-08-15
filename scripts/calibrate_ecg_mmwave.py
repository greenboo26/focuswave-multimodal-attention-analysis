# -*- coding: utf-8 -*-
"""
calibrate_ecg_mmwave.py — 毫米波×ECG 双机校准分析
====================================================
文件名：calibrate_ecg_mmwave.py
版本：v1.0（2026-08-15）
功能：对比「毫米波心跳 IBI」与「ECG 金标准 IBI」，标定毫米波 HR/HRV 精度。
      目标 IBI 误差 8~20ms 量级。

数据来源（2026-08-15 cal01 校准场次）:
  ECG 金标准: E:/0815.acq（Biopac MP160, 2000Hz, ECG100C 模拟通道
              + D8~D15 数字通道存并口 marker）
  毫米波:     E:/FocusWave_3.0.15/03-data/sub-cal01_/mmwave/
              （npz 距离域复数 + timestamps.csv 帧级 Unix 时间戳）
  事件:       E:/FocusWave_3.0.15/03-data/sub-cal01_/cal/events.csv
              （marker 值 + Unix 毫秒时间戳，A 机时钟）

时间对齐原理:
  A 机（毫米波 + marker 发送）与 B 机（ECG）各自时钟独立。
  marker 值同时出现在两机: 并口脉冲进 ECG 数字通道（B 机采样点 idx），
  发送时刻的 Unix 毫秒记在 events.csv（A 机）。
  用同一 marker 值匹配两边，线性拟合 idx ↔ unix_ms，实现双机时间轴对齐。
  （两机时钟存在微小漂移，实测 1030s 漂 ~144ms，线性拟合可消除。）

处理流程:
  1. 读 events.csv → marker 值 + unix_ms
  2. 读 ECG .acq → ECG 信号 + 数字通道合成 marker 脉冲 (值, 采样点)
  3. 值序列匹配 → 线性拟合 idx ↔ unix_ms
  4. 按 5 段分别: ECG R 峰 IBI / 毫米波心跳 IBI（复用 v9/rest3min 管线）
  5. 时间对齐两 IBI → MAE / RMSE / 误差标准差

用法:
  cd 08_算法/scripts
  python calibrate_ecg_mmwave.py

依赖: numpy, scipy, bioread, vmdpy（毫米波心跳 VMD 分离需要）
      若 vmdpy 缺失，脚本自动回退 bp 带通方法（精度略降）。

输出: output/校准/cal01/
  calibration_result.json   分 5 段 + 汇总误差指标
  calibration_result.csv    逐拍对比明细
  calibration_summary.png   分段误差柱状图
"""

import os
import sys
import json
import csv
import glob
import argparse
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.signal import find_peaks

# ── 复用毫米波生命体征提取管线 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from process_vital_signs_v2 import FS, N_CH
from analyze_rest_3min import select_bins_from_profile, analyze_displacement


# ============================================================
# 被试数据配置（每新增一场在此登记）
# ============================================================

# 各校准场次的数据路径: (acq 路径, 毫米波目录, events.csv 路径, mmwave 文件前缀)
DATA_ROOT = r"D:\Project\厚粲杯\11_数据\生理多导校正"
SUBJECTS = {
    'sub1': {
        'acq': DATA_ROOT + r"\sub-cal01_\cal01.acq",
        'mmwave_dir': DATA_ROOT + r"\sub-cal01_\mmwave",
        'events': DATA_ROOT + r"\sub-cal01_\cal\events.csv",
        'prefix': 'sub-cal01_mmwave',
        'output': 'cal01',
    },
    'sub2': {
        'acq': DATA_ROOT + r"\sub-2_\sub2.acq",
        'mmwave_dir': DATA_ROOT + r"\sub-2_\mmwave",
        'events': DATA_ROOT + r"\sub-2_\cal\events.csv",
        'prefix': 'sub-2_mmwave',
        'output': 'sub2',
    },
    'sub3': {
        'acq': DATA_ROOT + r"\sub-3_\sub3.acq",
        'mmwave_dir': DATA_ROOT + r"\sub-3_\mmwave",
        'events': DATA_ROOT + r"\sub-3_\cal\events.csv",
        'prefix': 'sub-3_mmwave',
        'output': 'sub3',
    },
}

# ECG R 峰检测参数
ECG_RPEAK_MIN_DIST_S = 0.3      # R 峰最小间距（秒），对应心率上限 ~200bpm
ECG_RPEAK_PROMINENCE = 0.25     # R 峰显著度阈值（峰相对局部谷底高度，V）
                                # 用 prominence 而非固定 height：对 R 波幅度漂移
                                # （呼吸调制/基线漂移导致后段 R 波变矮）鲁棒，
                                # 避免低幅度 R 波被漏检（漏检会造出 ~1000ms 假 IBI）

# 毫米波 IBI 提取方法: 'vmd_heart'（主线，需 vmdpy）或 'bp'（带通，无依赖）
MMWAVE_METHOD = 'bp'

# 心跳分离器方法开关（vmdpy 缺失时自动回退 bp）
IBI_MIN_MS = 300                # 合法 IBI 下界（毫秒）
IBI_MAX_MS = 2000               # 合法 IBI 上界（毫秒）

# 校准协议 4 段定义（段名，用于与 events.csv 匹配；运动段已移除）
SEGMENTS = ['rest1', 'deep_breath', 'breath_hold', 'rest2']


# ============================================================
# 1. 读事件与 ECG
# ============================================================

def read_events(path):
    """读 events.csv，返回 [(marker值, unix_ms, event, segment)]。

    参数:
        path: events.csv 路径
    返回:
        list of tuple (marker:int, unix_ms:int, event:str, segment:str)
    """
    events = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mv = row.get('marker', '').strip()
            if mv == '':
                continue
            events.append((int(mv), int(row['unix_ms']),
                           row['event'], row.get('segment', '')))
    return events


def read_ecg_and_markers(acq_path):
    """读 ECG .acq，返回 ECG 信号、采样率、marker 脉冲列表。

    按通道名自动识别 ECG 通道（sub1/sub2 是 ECG100C，sub3 是 ECG,RSPEC-R，
    通道索引会变），避免硬编码 channels[0]。
    数字通道 D8~D15 按名字找 STP Input 0~7，合成 8-bit 十进制值，
    找上升沿脉冲得 (值, 采样点)。

    参数:
        acq_path: .acq 文件路径
    返回:
        (ecg: np.ndarray, sr: float, pulses: list[(value:int, idx:int)])
    """
    import bioread
    d = bioread.read_file(acq_path)
    sr = d.samples_per_second

    # 按通道名识别 ECG（含 'ECG' 的模拟通道）
    ecg_idx = None
    stp_indices = []   # 数字通道（STP Input 0~7）的索引，按编号排序
    for i, ch in enumerate(d.channels):
        name = str(ch.name)
        if ecg_idx is None and 'ECG' in name.upper():
            ecg_idx = i
        if 'STP Input' in name:
            # 提取编号：'Digital (STP Input 0)' -> 0
            num = int(name.split('STP Input ')[1].split(')')[0])
            stp_indices.append((num, i))
    if ecg_idx is None:
        raise ValueError(f"未找到 ECG 通道: {[c.name for c in d.channels]}")
    ecg = np.asarray(d.channels[ecg_idx].data).astype(float)
    print(f"[ECG] 识别 ECG 通道 [{ecg_idx}] {d.channels[ecg_idx].name!r}")

    # 8 位数字通道（STP Input 0~7）→ 十进制值（STP Input 0 = 最低位）
    stp_indices.sort()   # 按编号 0..7 排序
    bits = [(np.asarray(d.channels[i].data) > 2.5).astype(int)
            for num, i in stp_indices[:8]]
    if len(bits) != 8:
        raise ValueError(f"数字通道不足 8 个: {len(bits)}")
    val = sum(bits[b] * (1 << b) for b in range(8))
    val = np.asarray(val)

    # 找非零脉冲上升沿（0 → 非0）
    rising = np.where((val[1:] != 0) & (val[:-1] == 0))[0] + 1
    pulses = [(int(val[r]), int(r)) for r in rising]
    return ecg, sr, pulses


# ============================================================
# 2. 时间对齐（marker 值匹配 + 线性拟合）
# ============================================================

def align_clocks(pulses, events, sr):
    """用段边界 marker 值序列匹配，线性拟合 ECG 采样点 ↔ unix_ms。

    只取 marker 值 <100 的段边界事件（calibration_start/end + segment_start/end），
    这些值唯一不循环；段内每秒的 tick 时间码（101~110 循环）不参与对齐，
    否则循环值会导致匹配错乱。

    匹配策略: 在 ECG 侧 <100 的脉冲值序列中，找 events 值序列的子串，
    自动跳过早期作废场次残留的重复 marker（如胸带未就绪的半途退出）。

    参数:
        pulses: ECG 侧脉冲 [(value, idx)]
        events: A 机事件 [(marker, unix_ms, event, segment)]
        sr: ECG 采样率
    返回:
        (offset_ms: float, ms_per_sample: float)  满足 unix_ms = offset_ms + ms_per_sample * idx
        失败返回 None
    """
    # 只取段边界事件（值 <100，唯一不循环）
    bounds = [(m, u) for (m, u, e, s) in events if m < 100]
    # ECG 侧 <100 的脉冲
    ecg_bounds = [(v, idx) for (v, idx) in pulses if v < 100]

    if len(bounds) < 2 or len(ecg_bounds) < len(bounds):
        return None

    a_vals = [m for m, _ in bounds]
    e_vals = [v for v, _ in ecg_bounds]
    n_a = len(a_vals)

    # 子串匹配：在 ECG 侧值序列中找 events 值序列（跳过早期作废残留）
    match_start = None
    for i in range(len(e_vals) - n_a + 1):
        if e_vals[i:i + n_a] == a_vals:
            match_start = i
            break

    if match_start is None:
        # 完整子串未匹配（可能个别 marker 噪声），回退：贪心顺序匹配唯一值
        from collections import defaultdict
        by_value = defaultdict(list)
        for v, idx in ecg_bounds:
            by_value[v].append(idx)
        pairs = []
        for m, u in bounds:
            cand = by_value.get(m)
            if not cand:
                continue
            # 取与已匹配点时间间距最一致的候选
            if pairs:
                idx_arr = np.array([p[0] for p in pairs], dtype=float)
                unix_arr = np.array([p[1] for p in pairs], dtype=float)
                kk = np.polyfit(unix_arr, idx_arr, 1)[0]
                pred = idx_arr[-1] + kk * (u - unix_arr[-1])
                pairs.append((min(cand, key=lambda c: abs(c - pred)), u))
            else:
                pairs.append((min(cand), u))
    else:
        pairs = [(ecg_bounds[match_start + j][1], bounds[j][1])
                 for j in range(n_a)]

    if len(pairs) < 2:
        return None

    idx_arr = np.array([p[0] for p in pairs], dtype=float)
    unix_arr = np.array([p[1] for p in pairs], dtype=float)
    # 线性拟合 unix_ms = offset + k * idx
    k, offset = np.polyfit(idx_arr, unix_arr, 1)
    # 打印对齐质量
    resid = unix_arr - (offset + k * idx_arr)
    print(f"[ALIGN] 匹配 {len(pairs)}/{len(bounds)} 个段边界 marker, "
          f"拟合残差 max={np.max(np.abs(resid)):.2f}ms, "
          f"k={k:.6f} ms/采样点 (理论 0.5)")
    return offset, k


# ============================================================
# 3. ECG IBI 提取（分段）
# ============================================================

def ecg_ibi_segment(ecg, sr, t0_idx, t1_idx, align):
    """在 ECG 段内检测 R 峰，返回 (峰时刻 unix_ms, IBI 毫秒)。

    参数:
        ecg: 全段 ECG 信号
        sr: 采样率
        t0_idx, t1_idx: 段起止采样点
        align: (offset, k) 线性映射 unix_ms = offset + k*idx
    返回:
        (peak_unix_ms: np.ndarray, ibi_ms: np.ndarray) 或 (None, None)
    """
    offset, k = align
    seg = ecg[t0_idx:t1_idx]
    if len(seg) < sr * 5:
        return None, None
    # prominence 检测：峰相对局部谷底高度，对 R 波幅度漂移鲁棒（修漏检）
    peaks, _ = find_peaks(seg, distance=int(ECG_RPEAK_MIN_DIST_S * sr),
                          prominence=ECG_RPEAK_PROMINENCE)
    if len(peaks) < 5:
        return None, None
    # 峰时刻（绝对采样点 → unix_ms）
    peak_idx_abs = peaks + t0_idx
    peak_unix = offset + k * peak_idx_abs
    # 峰时刻（绝对采样点 → unix_ms）
    ibi = np.diff(peak_unix)   # 直接相邻峰时间差 = IBI（毫秒）
    # 剔除非法 IBI
    valid = (ibi >= IBI_MIN_MS) & (ibi <= IBI_MAX_MS)
    # 保留峰时刻（与 IBI 对齐：IBI[i] 是 peak[i] → peak[i+1]）
    return peak_unix[:-1][valid], ibi[valid]


# ============================================================
# 4. 毫米波 IBI 提取（分段）
# ============================================================

def read_mmwave_segment(mmwave_dir, prefix, frame_idx0, frame_idx1):
    """读毫米波指定帧区间（全局帧索引），返回距离域复数 (n, 256, 8)。

    参数:
        mmwave_dir: 毫米波数据目录（含分块 npz）
        prefix: mmwave 文件前缀（如 'sub-2_mmwave'）
        frame_idx0, frame_idx1: 全局帧索引区间（闭区间）
    返回:
        iq: (n, 256, 8) complex64
    """
    chunk_start = (frame_idx0 // 1000) * 1000
    chunk_end = (frame_idx1 // 1000 + 1) * 1000
    chunks = []
    for g in range(chunk_start, chunk_end, 1000):
        if g == 0:
            f = os.path.join(mmwave_dir, f'{prefix}_datacube.npz')
        else:
            f = os.path.join(mmwave_dir,
                             f'{prefix}_datacube_part{g // 1000:03d}.npz')
        d = np.load(f)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        iq = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        chunks.append(iq)
        d.close()
    iq_full = np.concatenate(chunks, axis=0)
    iq = iq_full[frame_idx0 - chunk_start: frame_idx1 - chunk_start + 1]
    return iq


def mmwave_ibi_segment(iq, frame_unix_ms, method='bp'):
    """在毫米波段内提取心跳峰值，返回 (峰时刻 unix_ms, IBI 毫秒)。

    参数:
        iq: (n, 256, 8) 距离域复数
        frame_unix_ms: (n,) 每帧的 unix_ms
        method: 'vmd_heart' 或 'bp'
    返回:
        (peak_unix_ms, ibi_ms) 或 (None, None)
    """
    n = iq.shape[0]
    if n < FS * 20:   # 至少 20 秒
        return None, None

    # 选 bin
    bin_power_acc = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(bin_power_acc, axis=0)))
    try:
        br_ch, br_bin, hr_ch, hr_bin, _ = select_bins_from_profile(
            bin_power_acc, best_ch, iq, n)
    except Exception as e:
        print(f"    [mmWave] 选 bin 失败: {e}")
        return None, None

    disp_br = np.unwrap(np.angle(iq[:, br_bin, br_ch]))
    disp_hr = np.unwrap(np.angle(iq[:, hr_bin, hr_ch]))

    try:
        result, (t, breath, heartbeat, hp, bp) = analyze_displacement(
            disp_br, disp_hr, n, method=method)
    except Exception as e:
        print(f"    [mmWave] 提取失败: {e}")
        return None, None

    if len(hp) < 5:
        return None, None

    peak_unix = frame_unix_ms[np.asarray(hp)]
    ibi = np.diff(peak_unix)
    valid = (ibi >= IBI_MIN_MS) & (ibi <= IBI_MAX_MS)
    return peak_unix[:-1][valid], ibi[valid]


# ============================================================
# 5. IBI 对比（时间对齐 + 误差）
# ============================================================

def compare_ibi(ecg_peak_unix, ecg_ibi, mm_peak_unix, mm_ibi,
                match_tol_ms=250.0):
    """把毫米波 IBI 对齐到 ECG IBI 时间网格，算误差。

    以 ECG 峰时刻为基准，每个 ECG IBI 找时间最近的毫米波 IBI（容差内），
    计算逐拍绝对误差，得 MAE / RMSE / 误差标准差。

    参数:
        ecg_peak_unix, ecg_ibi: ECG 峰时刻与 IBI
        mm_peak_unix, mm_ibi: 毫米波峰时刻与 IBI
        match_tol_ms: 峰时刻匹配容差（毫秒）
    返回:
        dict 或 None
    """
    if len(ecg_ibi) < 5 or len(mm_ibi) < 5:
        return None
    errs = []
    for i in range(len(ecg_ibi)):
        t = ecg_peak_unix[i]
        # 找毫米波峰时刻最近的
        j = np.argmin(np.abs(mm_peak_unix - t))
        if abs(mm_peak_unix[j] - t) > match_tol_ms:
            continue
        errs.append(mm_ibi[j] - ecg_ibi[i])
    if len(errs) < 5:
        return None
    errs = np.array(errs)
    return {
        'n_matched': int(len(errs)),
        'mae_ms': float(np.mean(np.abs(errs))),
        'rmse_ms': float(np.sqrt(np.mean(errs ** 2))),
        'mean_bias_ms': float(np.mean(errs)),
        'sd_ms': float(np.std(errs)),
        'n_ecg': int(len(ecg_ibi)),
        'n_mm': int(len(mm_ibi)),
    }


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='毫米波×ECG 双机校准分析')
    parser.add_argument('--subject', default='sub2',
                        choices=list(SUBJECTS.keys()),
                        help='校准场次（默认 sub2）')
    args = parser.parse_args()
    cfg = SUBJECTS[args.subject]

    print("=" * 60)
    print(f"  毫米波 × ECG 双机校准分析（{args.subject}）")
    print("=" * 60)

    OUTPUT_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\校准") / cfg['output']
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 读数据 ──
    events = read_events(cfg['events'])
    print(f"[EVENTS] 读到 {len(events)} 个事件")

    ecg, ecg_sr, pulses = read_ecg_and_markers(cfg['acq'])
    print(f"[ECG] 采样率 {ecg_sr}Hz, 时长 {len(ecg)/ecg_sr:.1f}s, "
          f"{len(pulses)} 个数字脉冲")

    # ── 时间对齐 ──
    align = align_clocks(pulses, events, ecg_sr)
    if align is None:
        print("[ERROR] 时间对齐失败，无法继续")
        return
    offset, k = align

    # ── 毫米波帧时间戳 ──
    ts_path = os.path.join(cfg['mmwave_dir'], f"{cfg['prefix']}_timestamps.csv")
    ts = np.loadtxt(ts_path, delimiter=',')
    frame_unix_ms = ts[:, 2]           # 第 3 列 Python unix_ms
    n_frames = len(frame_unix_ms)
    print(f"[mmWave] {n_frames} 帧, unix_ms 范围 "
          f"{frame_unix_ms[0]:.0f} ~ {frame_unix_ms[-1]:.0f}")

    # ── 段边界（从 events 提取 segment_start/end 的 unix_ms）──
    seg_bounds = {}
    for mv, unix_ms, event, seg in events:
        if event == 'segment_start':
            seg_bounds.setdefault(seg, {})['start'] = unix_ms
        elif event == 'segment_end':
            seg_bounds.setdefault(seg, {})['end'] = unix_ms

    results = {}
    all_rows = []

    for seg_name in SEGMENTS:
        b = seg_bounds.get(seg_name)
        if not b or 'start' not in b or 'end' not in b:
            print(f"\n[{seg_name}] 无段边界，跳过")
            continue
        t0_unix, t1_unix = b['start'], b['end']
        print(f"\n[{seg_name}] unix {t0_unix} ~ {t1_unix} "
              f"({(t1_unix-t0_unix)/1000:.0f}s)")

        # ECG 段采样点区间（用对齐映射反推）
        t0_idx = int((t0_unix - offset) / k)
        t1_idx = int((t1_unix - offset) / k)
        ecg_peak, ecg_ibi = ecg_ibi_segment(ecg, ecg_sr, t0_idx, t1_idx, align)
        if ecg_peak is None:
            print(f"  [ECG] 未检出足够 R 峰，跳过")
            continue
        print(f"  [ECG] {len(ecg_ibi)} 个 IBI, "
              f"均值 {np.mean(ecg_ibi):.1f}ms")

        # 毫米波段帧区间
        f0 = np.searchsorted(frame_unix_ms, t0_unix)
        f1 = np.searchsorted(frame_unix_ms, t1_unix) - 1
        if f1 - f0 < FS * 20:
            print(f"  [mmWave] 帧数不足，跳过")
            continue
        iq = read_mmwave_segment(cfg['mmwave_dir'], cfg['prefix'], f0, f1)
        mm_peak, mm_ibi = mmwave_ibi_segment(iq, frame_unix_ms[f0:f1 + 1],
                                             method=MMWAVE_METHOD)
        del iq
        if mm_peak is None:
            print(f"  [mmWave] 未检出足够心跳，跳过")
            continue
        print(f"  [mmWave] {len(mm_ibi)} 个 IBI, "
              f"均值 {np.mean(mm_ibi):.1f}ms")

        # 对比
        cmp = compare_ibi(ecg_peak, ecg_ibi, mm_peak, mm_ibi)
        if cmp is None:
            print(f"  [对比] 匹配不足，跳过")
            continue
        results[seg_name] = {
            'ecg_hr_bpm': round(60000 / np.mean(ecg_ibi), 1),
            'mm_hr_bpm': round(60000 / np.mean(mm_ibi), 1),
            **cmp,
        }
        print(f"  [对比] MAE={cmp['mae_ms']:.1f}ms  "
              f"RMSE={cmp['rmse_ms']:.1f}ms  "
              f"SD={cmp['sd_ms']:.1f}ms  bias={cmp['mean_bias_ms']:.1f}ms  "
              f"匹配 {cmp['n_matched']} 拍")

        # 逐拍明细
        for i in range(len(ecg_ibi)):
            t = ecg_peak[i]
            j = np.argmin(np.abs(mm_peak - t))
            if abs(mm_peak[j] - t) <= 250.0:
                all_rows.append([seg_name, ecg_peak[i], mm_peak[j],
                                 ecg_ibi[i], mm_ibi[j],
                                 mm_ibi[j] - ecg_ibi[i]])

    # ── 汇总输出 ──
    print("\n" + "=" * 60)
    print("  校准结果汇总")
    print("=" * 60)
    if results:
        all_mae = [r['mae_ms'] for r in results.values()]
        print(f"  各段 MAE: " +
              "  ".join(f"{s}={results[s]['mae_ms']:.1f}ms" for s in results))
        print(f"  整体 MAE 均值 = {np.mean(all_mae):.1f}ms")

    out_json = OUTPUT_DIR / 'calibration_result.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({'segments': results,
                   'align': {'offset_ms': offset, 'ms_per_sample': k}},
                  f, ensure_ascii=False, indent=2)
    print(f"[OUT] -> {out_json}")

    if all_rows:
        out_csv = OUTPUT_DIR / 'calibration_result.csv'
        with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['segment', 'ecg_peak_unix', 'mm_peak_unix',
                        'ecg_ibi_ms', 'mm_ibi_ms', 'err_ms'])
            w.writerows(all_rows)
        print(f"[OUT] -> {out_csv} ({len(all_rows)} 行)")

    return results


if __name__ == '__main__':
    main()
