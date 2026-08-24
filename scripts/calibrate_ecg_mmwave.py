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

from path_registry import load_paths

from process_vital_signs_v2 import FS, N_CH, _sos_bandpass
from analyze_rest_3min import (select_bins_from_profile, analyze_displacement,
                               estimate_freq_periodogram)
from process_vital_signs_v9 import suppress_harmonics


# ============================================================
# 被试数据配置（每新增一场在此登记）
# ============================================================

# 各校准场次的数据路径: (acq 路径, 毫米波目录, events.csv 路径, mmwave 文件前缀)
# 2026-08-16 数据已从 11_数据/生理多导校正 迁移至 D:\acq_mmwave_results
PATHS = load_paths()
DATA_ROOT = str(Path(PATHS["calibration_root"]))
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
    'sub4': {
        'acq': DATA_ROOT + r"\sub-4_\sub4.acq",
        'mmwave_dir': DATA_ROOT + r"\sub-4_\mmwave",
        'events': DATA_ROOT + r"\sub-4_\cal\events.csv",
        'prefix': 'sub-4_mmwave',
        'output': 'sub4',
    },
    'sub5': {
        'acq': DATA_ROOT + r"\sub-5_\sub5.acq",
        'mmwave_dir': DATA_ROOT + r"\sub-5_\mmwave",
        'events': DATA_ROOT + r"\sub-5_\cal\events.csv",
        'prefix': 'sub-5_mmwave',
        'output': 'sub5',
    },
    'sub6': {
        'acq': DATA_ROOT + r"\sub-6_\sub6.acq",
        'mmwave_dir': DATA_ROOT + r"\sub-6_\mmwave",
        'events': DATA_ROOT + r"\sub-6_\cal\events.csv",
        'prefix': 'sub-6_mmwave',
        'output': 'sub6',
    },
}

# ECG R 峰检测参数
ECG_RPEAK_MIN_DIST_S = 0.3      # R 峰最小间距（秒），对应心率上限 ~200bpm
ECG_RPEAK_PROMINENCE = 0.25     # R 峰显著度阈值（峰相对局部谷底高度，V）
                                # 用 prominence 而非固定 height：对 R 波幅度漂移
                                # （呼吸调制/基线漂移导致后段 R 波变矮）鲁棒，
                                # 避免低幅度 R 波被漏检（漏检会造出 ~1000ms 假 IBI）

# 毫米波 IBI 提取方法: 'vmd_heart'（主线，需 vmdpy）或 'bp'（带通，无依赖）
# 2026-08-16 校准对照结论：深呼吸/恢复段 bp 与 vmd_heart 均锁半频（呼吸谐波
# 功率压过心跳基频，信号层面无解），但正常静息段 bp 达 13.6ms 优于 vmd（410ms），
# 故校准用 bp。
MMWAVE_METHOD = 'bp'

# 心跳分离器方法开关（vmdpy 缺失时自动回退 bp）
IBI_MIN_MS = 300                # 合法 IBI 下界（毫秒）
IBI_MAX_MS = 2000               # 合法 IBI 上界（毫秒）

# ── 伪迹剔除参数（2026-08-16 补：此前仅靠 IBI 硬范围过滤，运动/电极伪迹未剔除）──
# 依据：运动伪迹/电极松脱最终表现为 R 峰幅度离群 + 相邻 IBI 突跳 + 毫米波
#       幅度闪烁，需在信号级与 IBI 级两层剔除，否则污染整段 IBI 误差。
ECG_AMP_MAD_N = 3.0             # ECG R 峰幅度 MAD 离群倍数（默认 3.0，只抓极端离群，
                                #   留足呼吸调制对 R 波幅度的正常 ±波动余量，可调 2.5~4.0）
IBI_JUMP_MAD_N = 3.0            # 相邻 IBI 相对突跳 MAD 离群倍数（默认 3.0，
                                #   剔除异位搏动/漏检造出的假间期，可调 2.5~4.0）
MM_MOTION_WIN_S = 30.0          # 毫米波运动门控分窗时长（秒，默认 30s）
MM_MOTION_CV_THRESH = 0.25      # 毫米波幅度变异系数 CV 阈值（默认 0.25；
                                #   静态目标 CV<0.15，留足呼吸调制余量，超阈判运动）
NOTCH_Q_EXT = 30.0              # 扩展谐波陷波的品质因数 Q（默认 30，越高陷波带宽
                                #   越窄；深呼吸谐波间隔 ~0.126Hz，Q=30 时陷波带宽
                                #   ~f0/30，1Hz 处约 0.03Hz，不误伤相邻频点）

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

    if len(bounds) < 2 or len(ecg_bounds) < 2:
        return None

    a_vals = [m for m, _ in bounds]
    e_vals = [v for v, _ in ecg_bounds]

    # 子串匹配：在 ECG 侧值序列中找 events 值序列的子串（跳过早期作废残留）。
    # calibration_start(marker=1)/calibration_end(marker=2) 常在 Biopac 开始/
    # 停止记录边界外发出而丢失（2026-08-16 sub4/sub5 缺 marker=1 实测），
    # 故允许 events 侧去掉开头 0~2 个 marker 后再匹配。
    match = None
    for k in range(3):
        a_sub = a_vals[k:]
        if len(a_sub) < 2:
            break
        for i in range(len(e_vals) - len(a_sub) + 1):
            if e_vals[i:i + len(a_sub)] == a_sub:
                match = (k, i)
                break
        if match:
            break

    if match is None:
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
        k, i = match
        pairs = [(ecg_bounds[i + j][1], bounds[k + j][1])
                 for j in range(len(a_vals) - k)]
        if k > 0:
            print(f"[ALIGN] events 侧开头 {k} 个 marker 缺失，"
                  f"从第 {k} 个边界起匹配")

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
# 伪迹剔除工具（信号级 + IBI 生理一致性）
# ============================================================

def mad_threshold(values, n_sigma=3.0):
    """中位绝对偏差（MAD）自适应离群阈值。

    用中位而非均值、MAD 而非标准差，因为伪迹会拉偏均值/方差，
    使阈值本身被污染；MAD 对离群鲁棒。

    参数:
        values: np.ndarray 一维数值序列
        n_sigma: 离群判定倍数（默认 3.0）
    返回:
        (low, high) 下界与上界，超出 [low, high] 视为离群
    """
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    if mad == 0:
        # 序列几乎无波动（如恒定幅度），退化为宽范围，不做剔除
        return -np.inf, np.inf
    return med - n_sigma * mad, med + n_sigma * mad


def drop_ibi_artifacts(peak_unix, ibi):
    """IBI 生理一致性门控：剔除相邻间期突跳的伪迹拍。

    依据：正常窦性心律相邻 IBI 变化平缓（呼吸性窦性心律不齐 RSA 的
    波动通常 ±10~15%）；异位搏动、运动伪迹、峰漏检会造出相邻 IBI
    突跳 >25% 甚至翻倍的假间期。用 MAD 自适应阈值只抓极端突跳。

    参数:
        peak_unix: np.ndarray 峰时刻（unix_ms），长度 = len(ibi)，IBI[i] 的起始峰
        ibi: np.ndarray 间期（ms）
    返回:
        (peak_unix_clean, ibi_clean) 剔除后的序列（长度保持对齐）
    """
    if len(ibi) < 5:
        return peak_unix, ibi
    # 相邻 IBI 相对变化率 |ΔIBI| / IBI（分母用前一拍，避免除零）
    rel = np.abs(np.diff(ibi)) / np.maximum(ibi[:-1], 1.0)
    _, high = mad_threshold(rel, n_sigma=IBI_JUMP_MAD_N)
    jump_idx = np.where(rel > high)[0]
    if len(jump_idx) == 0:
        return peak_unix, ibi
    # 突跳 rel[i] 涉及 ibi[i] 与 ibi[i+1]，两者均判伪迹，保留其余
    bad = np.zeros(len(ibi), dtype=bool)
    for i in jump_idx:
        bad[i] = True
        bad[i + 1] = True
    keep = ~bad
    if keep.sum() < 5:
        return peak_unix, ibi
    return peak_unix[keep], ibi[keep]


def motion_window_mask(mag, fs, win_s=30.0, cv_thresh=0.25):
    """分窗幅度变异系数（CV）运动门控，返回 (n,) 布尔 mask（True=运动伪迹）。

    依据：静态人体目标的距离 bin 幅度稳定（CV<15%，见 select_bins_from_profile
    的幅度稳定性过滤）；运动导致目标跨 bin 移动 / 多径变化，幅度闪烁 CV
    显著升高。分窗（默认 30s）算 CV，超过阈值的窗整窗标记为运动伪迹。

    参数:
        mag: (n,) 选定 bin 的幅度序列
        fs: 帧率（Hz）
        win_s: 分窗时长（秒，默认 30s）
        cv_thresh: CV 阈值（默认 0.25，静态 <15% 留足呼吸调制余量）
    返回:
        (n,) bool mask，True 表示该帧被判运动伪迹
    """
    n = len(mag)
    win = int(fs * win_s)
    mask = np.zeros(n, dtype=bool)
    if n < win:
        return mask
    n_wins = n // win
    for w in range(n_wins):
        seg = mag[w * win:(w + 1) * win]
        cv = np.std(seg) / (np.mean(seg) + 1e-12)
        if cv > cv_thresh:
            mask[w * win:(w + 1) * win] = True
    return mask


def suppress_br_harmonics_ext(x, br_freq_hz, fs=FS, max_h=20):
    """呼吸谐波陷波扩展版：陷到心跳带上限的高次谐波。

    v9 的 suppress_harmonics 只陷 1/2/3 次谐波（f0>3.0 即停），对正常
    呼吸（0.3Hz，2/3 次谐波落心跳带）有效，但对刻意深呼吸（0.12Hz，
    污染谐波是第 7~19 次）失效。此扩展版陷掉心跳带 0.8-2.5Hz 内所有
    呼吸谐波，用高 Q 窄带陷波避免密集谐波下误伤心跳主频。

    参数:
        x: (n,) 相位位移序列
        br_freq_hz: 呼吸主频 (Hz)；None 时原样返回
        fs: 采样率
        max_h: 谐波次数上限（默认 20，覆盖 0.12Hz 深呼吸到 2.5Hz 的 ~20 次）
    返回:
        陷波后的序列
    """
    if br_freq_hz is None or br_freq_hz <= 0:
        return x
    y = x.copy()
    for h in range(1, max_h + 1):
        f0 = br_freq_hz * h
        if f0 > 2.5:      # 超出心跳带上限，停止
            break
        if f0 < 0.8:      # 低于心跳带（呼吸基频/低次谐波），不污染，跳过
            continue
        q = NOTCH_Q_EXT   # 高 Q 窄带，密集谐波下尽量不误伤相邻频点
        b, a = signal.iirnotch(f0, q, fs)
        y = signal.sosfiltfilt(signal.tf2sos(b, a), y)
    return y


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
    peaks, props = find_peaks(seg, distance=int(ECG_RPEAK_MIN_DIST_S * sr),
                              prominence=ECG_RPEAK_PROMINENCE)
    if len(peaks) < 5:
        return None, None

    # 伪迹剔除①：R 峰幅度 MAD 门控。运动/电极松脱产生异常高幅度尖峰，
    # 或某段基线漂移导致 R 波整体变矮，用 prominence 的 MAD 只抓极端离群，
    # 不误杀正常呼吸调制（R 波幅度随呼吸有节奏波动，属生理而非伪迹）。
    proms = props['prominences']
    lo_amp, hi_amp = mad_threshold(proms, n_sigma=ECG_AMP_MAD_N)
    keep = (proms >= lo_amp) & (proms <= hi_amp)
    n_drop_amp = int((~keep).sum())
    if n_drop_amp:
        print(f"    [ECG] 幅度 MAD 门控剔除 {n_drop_amp} 个伪 R 峰")
    peaks = peaks[keep]
    if len(peaks) < 5:
        return None, None

    # 峰时刻（绝对采样点 → unix_ms）
    peak_idx_abs = peaks + t0_idx
    peak_unix = offset + k * peak_idx_abs
    ibi = np.diff(peak_unix)   # 直接相邻峰时间差 = IBI（毫秒）

    # 剔除非法 IBI（硬范围）
    valid = (ibi >= IBI_MIN_MS) & (ibi <= IBI_MAX_MS)
    peak_start = peak_unix[:-1][valid]
    ibi_range = ibi[valid]

    # 伪迹剔除②：IBI 生理一致性（相邻突跳），剔除异位搏动/漏检假间期
    peak_clean, ibi_clean = drop_ibi_artifacts(peak_start, ibi_range)
    n_drop_ibi = len(ibi_range) - len(ibi_clean)
    if n_drop_ibi:
        print(f"    [ECG] IBI 异位剔除 {n_drop_ibi} 拍")
    return peak_clean, ibi_clean


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

    # 呼吸谐波陷波（2026-08-16 补）：呼吸波形非正弦，其 2/3 次谐波落入
    # 心跳带 0.8-2.5Hz，深呼吸/恢复段谐波功率盖过心跳基频，导致选频锁半频。
    # 用呼吸 bin 估呼吸主频，对心跳 bin 相位做 1/2/3 次谐波窄带陷波，
    # 挖掉呼吸谐波而不动心跳主频（FMCW notch filter 方法，见 v9 模块）。
    br_freq = estimate_freq_periodogram(
        _sos_bandpass(disp_br, 0.1, 0.5), 0.1, 0.5)
    disp_hr_clean = suppress_harmonics(disp_hr, br_freq)
    if br_freq is not None:
        print(f"    [mmWave] 呼吸主频 {br_freq:.3f}Hz，谐波陷波已应用")

    # 伪迹剔除：hr bin 幅度分窗 CV 运动门控。运动使目标跨 bin 移动，
    # 幅度剧烈闪烁（CV 显著高于静态 <15%），超阈窗内的心跳峰判运动伪迹。
    mag_hr = np.abs(iq[:, hr_bin, hr_ch])
    motion_mask = motion_window_mask(
        mag_hr, FS, win_s=MM_MOTION_WIN_S, cv_thresh=MM_MOTION_CV_THRESH)
    n_motion = int(motion_mask.sum())
    if n_motion:
        print(f"    [mmWave] 运动门控标记 {n_motion} 帧 "
              f"({n_motion / FS:.0f}s, CV>{MM_MOTION_CV_THRESH})")

    try:
        result, (t, breath, heartbeat, hp, bp) = analyze_displacement(
            disp_br, disp_hr_clean, n, method=method)
    except Exception as e:
        print(f"    [mmWave] 提取失败: {e}")
        return None, None

    if len(hp) < 5:
        return None, None

    # 剔除落在运动窗内的心跳峰（hp 是段内帧索引，与 motion_mask 对齐）
    hp = np.asarray(hp)
    hp_keep = hp[~motion_mask[hp]]
    n_drop_motion = len(hp) - len(hp_keep)
    if n_drop_motion:
        print(f"    [mmWave] 剔除运动窗内 {n_drop_motion} 个心跳峰")
    if len(hp_keep) < 5:
        return None, None

    peak_unix = frame_unix_ms[hp_keep]
    ibi = np.diff(peak_unix)
    valid = (ibi >= IBI_MIN_MS) & (ibi <= IBI_MAX_MS)
    peak_start = peak_unix[:-1][valid]
    ibi_range = ibi[valid]

    # IBI 生理一致性：剔除异位搏动/漏检假间期
    peak_clean, ibi_clean = drop_ibi_artifacts(peak_start, ibi_range)
    return peak_clean, ibi_clean


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

    OUTPUT_DIR = Path(PATHS["algorithm_root"]) / "output" / "校准" / cfg['output']
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
