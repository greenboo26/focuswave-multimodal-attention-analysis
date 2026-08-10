"""
毫米波雷达生命体征提取 v9 — 定位 + 谐波抑制架构
========================================================
v1-v8 的局限（文献调研结论, 2026-08-07）:
  1. 定位方式（SNR 选 bin）8 个版本从未改进 —— 选的是"检测最方便"
     的位置, 不是"人体位置"; 人体直达 bin 呼吸谐波污染时被迫逃到
     多径/墙反射位置, 导致 bin 漂移与可用率不稳
  2. 无静态杂波消除
  3. 无呼吸谐波定向抑制（呼吸波形非正弦, 谐波落入心跳带 0.8-2.5Hz）

v9 基于文献调研重构（Chen2024 DR-MUSIC / Wang2021 mmHRV /
FMCW2025 notch filter 方法）:
  1. 定位: 最高能量距离门（人体=场景最强反射, Chen2024）
     + 相位方差判别人体/墙（人体高方差, 静态物体低方差, Wang2021）
  2. 静态杂波: 相位均值对消
  3. 谐波抑制: 呼吸主频 + 2/3 次谐波 iirnotch 陷波
  4. 心跳: 复用 v3 heart-only VMD + 窄带逐拍检测
  5. 呼吸: 复用 v5 稳健检测

用法:
  python process_vital_signs_v9.py  # 单元自检（无数据时打印帮助）

依赖: numpy, scipy, vmdpy
"""

import sys
import os
import numpy as np
from scipy import signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from process_vital_signs_v2 import FS, N_CH, _sos_bandpass
from process_vital_signs_v3 import separate_vmd_heart_only
from process_vital_signs_v5 import detect_peaks_breath_robust

# ============================================================
# 配置
# ============================================================

PHASE_VAR_MIN = 0.1    # 相位方差下界: 低于此视为静态物体/墙（无生理调制）
PHASE_VAR_MAX = 50.0   # 相位方差上界: 高于此视为噪声/大幅运动
NOTCH_Q = 30           # 陷波 Q 值（大=窄带宽, 只杀谐波不伤心跳）
NOTCH_Q_H3 = 40        # 3 次谐波离心跳主频近, 用更窄的陷波


# ============================================================
# 1. 定位（最高能量距离门 + 相位方差人体判别）
# ============================================================

def locate_target(iq):
    """定位人体目标: 最高能量距离门 + 相位方差判别。

    依据:
      - Chen2024: 人体是场景最强反射, 距离 FFT 后选最高能量距离门
      - Wang2021 mmHRV: 人体相位方差高（含呼吸/心跳相位调制）,
        静态物体（墙/家具）相位方差低 —— 区分"真人体"与"墙反射"

    参数:
        iq: (n, 256, 8) complex64 距离域数据
    返回:
        (ch, bin, phase_var) 或 None（无合格目标）
    """
    power = np.mean(np.abs(iq) ** 2, axis=0)  # (256, 8)
    best = None
    for ch in range(N_CH):
        bp = power[:, ch]
        b = int(np.argmax(bp))
        # 相位方差判别: 只有人体位置才有持续的呼吸/心跳相位调制
        phi = np.unwrap(np.angle(iq[:, b, ch]))
        var = np.var(phi)
        if not (PHASE_VAR_MIN < var < PHASE_VAR_MAX):
            continue  # 墙/静态物体（低方差）或噪声（高方差）
        score = float(bp[b])
        if best is None or score > best[0]:
            best = (score, ch, b, float(var))
    if best is None:
        return None
    return best[1], best[2], best[3]


# ============================================================
# 2. 静态杂波消除 + 3. 呼吸谐波抑制
# ============================================================

def remove_static_clutter(disp):
    """静态杂波消除: 相位均值对消（Chen2024 第 2 步）。

    静止物体贡献的相位是常数, 减去均值即消除;
    仅保留随时间变化的呼吸/心跳相位调制。
    """
    return disp - np.mean(disp)


def suppress_harmonics(x, br_freq_hz, fs=FS):
    """呼吸谐波抑制: 呼吸主频及 2/3 次谐波处 iirnotch 陷波。

    呼吸波形非正弦, 谐波（尤其 2/3 次）落入心跳带 0.8-2.5Hz,
    是心跳检测的主要污染源（FMCW2025 notch filter 方法）。
    陷波只杀呼吸谐波窄带, 不动心跳主频。

    参数:
        x: (n,) 相位位移序列
        br_freq_hz: 呼吸主频 (Hz); None 时跳过
        fs: 采样率
    返回:
        陷波后的序列
    """
    if br_freq_hz is None:
        return x
    y = x.copy()
    for h in range(1, 4):
        f0 = br_freq_hz * h
        if f0 > 3.0:   # 超出心跳带上限（0.8-2.5Hz）, 无污染意义
            break
        q = NOTCH_Q_H3 if h == 3 else NOTCH_Q
        b, a = signal.iirnotch(f0, q, fs)
        y = signal.sosfiltfilt(signal.tf2sos(b, a), y)
    return y


# ============================================================
# 4. 心跳峰值检测（窄带逐拍, 复用现有）
# ============================================================

def detect_heart_peaks_narrowband(heartbeat, hr_freq):
    """窄带逐拍心跳峰值检测（v1.4 主线方法, 混入呼吸谐波/噪声峰）。

    频域主峰 ±0.05Hz 窄带带通后逐拍取局部最大。
    """
    hp = np.array([], dtype=int)
    if hr_freq is None:
        return hp
    lo_nb, hi_nb = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
    sos_hp = signal.butter(4, [lo_nb, hi_nb], btype='band', fs=FS, output='sos')
    xn = signal.sosfiltfilt(sos_hp, heartbeat)
    ref = 1.0 / hr_freq
    n_pts = len(xn)
    peaks_list = []
    i = 0
    while i < n_pts:
        lo_i, hi_i = int(i + 0.75 * ref * FS), min(int(i + 1.35 * ref * FS), n_pts)
        if lo_i >= n_pts or hi_i <= lo_i:
            break
        p = lo_i + np.argmax(xn[lo_i:hi_i])
        peaks_list.append(p)
        i = p + 1
    return np.array(peaks_list, dtype=int)


# ============================================================
# 5. 单窗完整分析（v9 管线）
# ============================================================

def analyze_window_v9(iq, method="vmd_heart"):
    """v9 单窗分析: 定位 → 杂波消除 → 谐波抑制 → 心跳/呼吸提取。

    参数:
        iq: (n, 256, 8) complex64 窗数据
        method: 心跳分离方法 bp | vmd_heart
    返回:
        dict（HR/BR/HRV/bin）或 None（定位失败或检测不可信）
    """
    # 1. 定位人体（最高能量 + 相位方差判别）
    target = locate_target(iq)
    if target is None:
        return None
    ch, b, var = target
    disp = np.unwrap(np.angle(iq[:, b, ch]))
    # 2. 静态杂波消除
    disp = remove_static_clutter(disp)
    # 3. 呼吸主频（谐波抑制的输入）
    breath_bp = _sos_bandpass(disp, 0.1, 0.5)
    br_freq = _estimate_freq(breath_bp, 0.1, 0.5)
    # 4. 呼吸谐波陷波 → 心跳
    disp_clean = suppress_harmonics(disp, br_freq)
    heart_bp = _sos_bandpass(disp_clean, 0.8, 2.5)
    hr_freq_bp = _estimate_freq(heart_bp, 0.8, 2.5)
    if method == "vmd_heart" and hr_freq_bp is not None:
        heartbeat, _ = separate_vmd_heart_only(disp_clean, hr_freq_hint=hr_freq_bp)
        hr_freq = _estimate_freq(heartbeat, 0.8, 2.5)
        if hr_freq is None or not (0.5 <= hr_freq <= 2.0):
            heartbeat, hr_freq = heart_bp, hr_freq_bp  # 倍频保护
    else:
        heartbeat, hr_freq = heart_bp, hr_freq_bp
    # 5. 峰值检测
    hp = detect_heart_peaks_narrowband(heartbeat, hr_freq)
    bp = detect_peaks_breath_robust(breath_bp, lo_bpm=6, hi_bpm=30,
                                    br_freq_hint=br_freq)
    # 6. HRV（时域 + 频域, 复用现有函数）
    from analyze_rest_3min import compute_hrv_time, compute_hrv_frequency
    hrv = {}
    if len(hp) >= 5:
        ibi_ms = np.diff(hp) / FS * 1000
        ibi_clean = ibi_ms[(ibi_ms >= 300) & (ibi_ms <= 2000)]
        if len(ibi_clean) >= 5:
            hrv = compute_hrv_time(ibi_clean)
            hrv["frequency"] = compute_hrv_frequency(ibi_clean)
    hr_t = round(float(60 * FS / np.mean(np.diff(hp))), 1) if len(hp) >= 2 else None
    return {
        "ch": ch, "bin": b, "phase_var": round(var, 2),
        "hr_freq_bpm": round(float(hr_freq * 60), 1) if hr_freq else None,
        "hr_time_bpm": hr_t,
        "br_freq_bpm": round(float(br_freq * 60), 1) if br_freq else None,
        "n_heart_peaks": int(len(hp)),
        "hrv": hrv,
    }


def _estimate_freq(x, lo_hz, hi_hz):
    """周期图主频估计（局部函数, 避免额外 import）。"""
    f, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (f >= lo_hz) & (f <= hi_hz)
    if not np.any(mask):
        return None
    return float(f[mask][np.argmax(pxx[mask])])


if __name__ == "__main__":
    print("process_vital_signs_v9 — 定位 + 谐波抑制架构")
    print("单元自检: 生成模拟人体信号验证定位与谐波抑制")
    rng = np.random.default_rng(0)
    n = 3000
    t = np.arange(n) / FS
    # 模拟: 呼吸 0.25Hz + 心跳 1.2Hz + 谐波 + 噪声
    disp = (2.0 * np.sin(2 * np.pi * 0.25 * t)
            + 0.6 * np.sin(2 * np.pi * 0.5 * t)      # 呼吸 2 次谐波
            + 0.3 * np.sin(2 * np.pi * 0.75 * t)     # 呼吸 3 次谐波
            + 0.25 * np.sin(2 * np.pi * 1.2 * t)     # 心跳
            + 0.05 * rng.standard_normal(n))
    # 谐波抑制
    br_freq = _estimate_freq(_sos_bandpass(disp, 0.1, 0.5), 0.1, 0.5)
    clean = suppress_harmonics(disp, br_freq)
    # 对比抑制前后心跳带功率
    def band_pow(x, lo, hi):
        f, p = signal.periodogram(x, fs=FS, window="hann")
        m = (f >= lo) & (f <= hi)
        return float(np.sum(p[m]))
    p_hr_before = band_pow(disp, 0.8, 2.5)
    p_hr_after = band_pow(clean, 0.8, 2.5)
    print(f"  呼吸主频: {br_freq * 60:.1f} bpm")
    print(f"  心跳带功率: 抑制前 {p_hr_before:.2f} → 抑制后 {p_hr_after:.2f} "
          f"({(p_hr_after / max(p_hr_before, 1e-12)):.1f}x)")
    # 心跳主频定位验证
    hr_before = _estimate_freq(_sos_bandpass(disp, 0.8, 2.5), 0.8, 2.5)
    hr_after = _estimate_freq(_sos_bandpass(clean, 0.8, 2.5), 0.8, 2.5)
    print(f"  心跳主频: 抑制前 {hr_before * 60:.1f} bpm, 抑制后 {hr_after * 60:.1f} bpm (真值 72)")
