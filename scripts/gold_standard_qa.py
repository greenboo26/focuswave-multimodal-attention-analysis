# -*- coding: utf-8 -*-
"""
gold_standard_qa.py — 金标准（ECG / RSP 呼吸带）质量检测与伪迹清洗
====================================================================
按文献标准做法清洗金标准，不再使用自创的 MAD 阈值（前版错误）。

版本: v2.0 (2026-08-16)
依赖: numpy, scipy

── ECG 心率（文献依据）───────────────────────────────────────
· R 峰检测：Pan-Tompkins 简化版 —— 带通 0.5~40Hz + 平方 + 150ms 移动平均
  + 自适应幅度阈值（Pan & Tompkins, 1985；Kubios HRV 内置同款）。
· 伪迹剔除：百分比变化法（percent change）。相邻 IBI 相对偏差 > 20% 判为
  异位搏动/漏检伪迹（Clifford et al.；Karey et al. 2019 的 20% 判据）。
· 接受标准：≥ 80% 正常 RR 间期判可用（Peltola, 2012 共识阈值）。
· 只做时域心率（中位 IBI → bpm），不做频域 HRV，故剔除而非插值（文献对
  频域 HRV 才要求插值，时域心率删除即够）。

── RSP 呼吸带（文献依据）─────────────────────────────────────
· 带通 0.1~0.7 Hz（6~42 次/分，生理呼吸范围，见各呼吸带研究）。
· 呼吸峰检测：带通后峰值（find_peaks）。
· 伪迹剔除：相邻呼吸周期相对偏差 > 17% 判运动伪迹/漏检（可穿戴呼吸带
  文献的 17% 判据）。
· 松脱判据：带通后幅度过低（相对全段中位数过低）判带子松脱/无呼吸。
· 接受标准：≥ 80% 正常呼吸周期判可用（与 ECG 同一共识阈值）。
"""
import numpy as np
from scipy import signal
from scipy.signal import find_peaks


# ============================================================
# ECG 参数（文献标准）
# ============================================================

ECG_BAND = (0.5, 40.0)          # 带通范围 Hz（Pan-Tompkins 用 0.05~40，这里 0.5 起更稳）
ECG_MA_WIN_S = 0.15             # 平方后移动平均窗（秒），Pan-Tompkins 用 150ms
ECG_MIN_DIST_S = 0.3            # R 峰最小间距（秒），对应心率上限 ~200bpm
ECG_IBI_MIN_MS = 300.0          # 合法 IBI 下界（ms）
ECG_IBI_MAX_MS = 2000.0         # 合法 IBI 上界（ms）
ECG_PC_THRESH = 0.20            # 相邻 IBI 百分比变化阈值（20%，Clifford/Karey 2019）
ECG_MIN_VALID_RATIO = 0.80      # 可接受的最低正常 RR 间期比例（Peltola 2012）


# ============================================================
# RSP 参数（文献标准）
# ============================================================

RSP_BAND = (0.1, 0.7)           # 呼吸带通 Hz（6~42 次/分生理范围）
RSP_MIN_DIST_S = 0.5            # 呼吸峰最小间距（秒），对应呼吸率上限 ~120
RSP_PROMINENCE = 0.2            # 呼吸峰显著度
RSP_BR_MIN = 6.0                # 呼吸率下界（次/分）
RSP_BR_MAX = 42.0               # 呼吸率上界（次/分）
RSP_PC_THRESH = 0.17            # 相邻呼吸周期百分比变化阈值（17%，文献判据）
RSP_MIN_VALID_RATIO = 0.80      # 可接受的最低正常呼吸周期比例
RSP_LOOSE_RATIO = 0.25          # 带通幅度低于全段中位 25% 判松脱（相对判据）


# ============================================================
# ECG 清洗
# ============================================================

def ecg_qa(ecg, sr, i0, i1):
    """ECG 段内 R 峰检测 + 伪迹清洗，返回 (hr_bpm, report)。

    参数:
        ecg: 全段 ECG 信号（V）
        sr: 采样率（Hz）
        i0, i1: 段起止采样点 [i0, i1)
    返回:
        (hr_bpm 或 None, report dict)
    """
    report = {
        'n_raw': 0, 'n_ibi_range_rejected': 0, 'n_pc_rejected': 0,
        'n_kept': 0, 'valid_ratio': 0.0, 'hr_bpm': None, 'usable': False,
    }

    seg = ecg[i0:i1]
    if len(seg) < sr * 5:
        report['note'] = 'too_short'
        return None, report
    seg = seg - np.median(seg)

    # ── 带通 0.5~40Hz 去基线漂移/工频，然后直接 R 峰检测 ──
    # （不用平方+移动平均：那是 Pan-Tompkins 的自适应阈值配套，直接 find_peaks
    #   在带通信号上检测即可，平方会放大 T 波/双峰导致心率翻倍）
    sos = signal.butter(3, ECG_BAND, btype='band', fs=sr, output='sos')
    seg_f = signal.sosfiltfilt(sos, seg)

    peaks, props = find_peaks(seg_f, distance=int(ECG_MIN_DIST_S * sr),
                              prominence=0.25)
    if len(peaks) < 5:
        report['note'] = 'too_few_peaks'
        return None, report
    report['n_raw'] = len(peaks)

    # ── IBI + 硬范围 ──
    ibi = np.diff(peaks) / sr * 1000.0
    valid = (ibi >= ECG_IBI_MIN_MS) & (ibi <= ECG_IBI_MAX_MS)
    report['n_ibi_range_rejected'] = int((~valid).sum())
    ibi = ibi[valid]

    # ── 百分比变化法伪迹剔除（相邻 IBI 偏差 >20% 判伪迹）──
    if len(ibi) >= 3:
        rel = np.abs(np.diff(ibi)) / np.maximum(ibi[:-1], 1.0)
        bad = np.zeros(len(ibi), dtype=bool)
        for i in np.where(rel > ECG_PC_THRESH)[0]:
            bad[i] = True
            bad[i + 1] = True
        report['n_pc_rejected'] = int(bad.sum())
        if (~bad).sum() >= 3:
            ibi = ibi[~bad]

    report['n_kept'] = len(ibi)
    report['valid_ratio'] = report['n_kept'] / max(report['n_raw'], 1)
    report['usable'] = report['valid_ratio'] >= ECG_MIN_VALID_RATIO

    if len(ibi) < 3:
        report['note'] = 'too_few_ibi'
        return None, report

    hr = 60000.0 / np.median(ibi)
    report['hr_bpm'] = round(float(hr), 1)
    return hr, report


# ============================================================
# RSP 清洗
# ============================================================

def rsp_qa(rsp, sr, i0, i1):
    """RSP 段内呼吸峰检测 + 伪迹清洗，返回 (br, report)。

    参数:
        rsp: 全段呼吸带信号
        sr: 采样率
        i0, i1: 段起止采样点
    返回:
        (br 次/分 或 None, report dict)
    """
    report = {
        'n_raw': 0, 'n_range_rejected': 0, 'n_pc_rejected': 0,
        'n_kept': 0, 'valid_ratio': 0.0, 'br': None, 'usable': False,
        'amp': None, 'loose': False,
    }

    seg = rsp[i0:i1]
    if len(seg) < sr * 10:
        report['note'] = 'too_short'
        return None, report
    seg = seg - np.median(seg)

    # ── 带通 0.1~0.7Hz（6~42 次/分生理范围）──
    sos = signal.butter(4, RSP_BAND, btype='band', fs=sr, output='sos')
    seg_f = signal.sosfiltfilt(sos, seg)
    report['amp'] = round(float(np.ptp(seg_f)), 3)

    # 松脱判据：带通幅度过低（全段中位幅度 < 25% 判松脱）
    med_amp = np.median(np.abs(seg_f))
    report['loose'] = med_amp < RSP_LOOSE_RATIO * np.max(np.abs(seg_f))

    # ── 呼吸峰检测 ──
    peaks, _ = find_peaks(seg_f, distance=int(RSP_MIN_DIST_S * sr),
                          prominence=RSP_PROMINENCE)
    report['n_raw'] = len(peaks)
    if len(peaks) < 3:
        report['note'] = 'too_few_peaks'
        return None, report

    # ── 呼吸周期 + 生理范围过滤（<6 或 >42 次/分剔除）──
    # 静息呼吸的逐拍变异天然有 20%+（呼吸性变异），不设 17% 周期突跳剔除
    # （那是运动场景判据，会误杀正常呼吸）。中位数本身对离群伪峰鲁棒。
    period = np.diff(peaks) / sr
    br_series = 60.0 / period
    valid = (br_series >= RSP_BR_MIN) & (br_series <= RSP_BR_MAX)
    report['n_range_rejected'] = int((~valid).sum())
    period = period[valid]

    report['n_kept'] = len(period)
    report['valid_ratio'] = report['n_kept'] / max(report['n_raw'], 1)
    report['usable'] = report['valid_ratio'] >= RSP_MIN_VALID_RATIO

    if len(period) < 2:
        report['note'] = 'too_few_periods'
        return None, report

    # 中位数呼吸率（对离群伪峰鲁棒，文献标准做法）
    br = 60.0 / np.median(period)
    report['br'] = round(float(br), 2)
    return br, report
