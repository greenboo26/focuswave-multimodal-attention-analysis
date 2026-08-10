"""
analyze_rest_3min.py — 3 分钟静止毫米波数据分析（HR / BR / HRV）
============================================================
按当前算法主线（vmd_heart + bp）分析 11_数据/sub-rest_3min_ 的
3 分钟静止数据。相比 47min 脚本，额外计算频域 HRV（LF/HF），
因 3 分钟窗口达到短时 HRV 的下限，频域指标可算但分辨率有限。

v1.1 修正 (2026-08-06):
  去掉 range_fft —— npz 的 256 点已是距离域 (0xC2 datacube =
  Interval0 RFFT 输出), 二次 FFT 破坏相位结构导致心跳 SNR 掉 5 倍、
  HRV 异常偏高 (SDNN 241ms)。直接对原始复数取相位后
  SDNN 51-61ms 回到正常范围。

用法:
  cd 08_算法/scripts
  python analyze_rest_3min.py

输出:
  output/旧实验/08_旧批次-REST-3min/v1/
    sub-rest_3min_mmwave_vital_signs.json   ← 体征指标（含 HRV 时域+频域）
    sub-rest_3min_mmwave_vital_signs.npz    ← 波形数据（呼吸/心跳/峰值）
    sub-rest_3min_mmwave_vital_signs.png    ← 诊断图

依赖:
  numpy, scipy, matplotlib, vmdpy
"""

import os
import sys
import json
import glob
import time as time_mod
from pathlib import Path

import numpy as np
from scipy import signal

# ── 将当前目录加入 sys.path，以便导入 v2/v3/v5 模块 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from process_vital_signs_v2 import (
    FS, N_CH,
    _sos_bandpass,
)
from process_vital_signs_v3 import separate_vmd_heart_only
from process_vital_signs_v5 import detect_peaks_breath_robust


# ============================================================
# 配置
# ============================================================

# 数据目录: 3 分钟静止数据的 npz 分片
DATA_DIR = Path(r"D:\Project\厚粲杯\11_数据\sub-rest_3min_\mmwave")
# 输出目录
OUTPUT_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\08_旧批次-REST-3min\v1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 分析参数
METHOD = "vmd_heart"           # bp | vmd_heart（当前主线: 心跳用 VMD, 呼吸用 bp）
CHUNK_SIZE = 1000              # 每片帧数（与 npz 分片一致）
HRV_RS_FS = 4.0                # HRV 频域重采样率 (Hz)，Task Force 1996 建议 2-4 Hz


# ============================================================
# 第一步: 累积 range profile → 选 bin
# ============================================================

def accumulate_range_profile(npz_files):
    """遍历所有 npz 分片，累积各通道各 bin 的平均功率。

    v1.1: npz 的 256 点已是距离域 (0xC2 datacube 距离 FFT 输出)，
    不再做 range_fft，直接对原始复数累积功率。

    Returns:
        ch_power: (8,) 各通道总平均功率
        bin_power_acc: (256, 8) 各通道各 bin 的累积功率和
        n_total: 总帧数
    """
    bin_power_acc = None
    ch_power = np.zeros(N_CH)
    n_total = 0

    for i, fpath in enumerate(npz_files):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        # stack → (n_frames_local, 256, 8)，256 已是距离 bin
        iq_fd = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        n_local = iq_fd.shape[0]

        # 通道功率累积
        ch_power += np.mean(np.abs(iq_fd) ** 2, axis=(0, 1)) * n_local

        # 各 bin 功率累积 (按通道)
        bin_power_local = np.mean(np.abs(iq_fd) ** 2, axis=0)  # (256, 8)
        if bin_power_acc is None:
            bin_power_acc = bin_power_local * n_local
        else:
            bin_power_acc += bin_power_local * n_local

        n_total += n_local
        d.close()

    ch_power /= n_total
    bin_power_acc /= n_total
    return ch_power, bin_power_acc, n_total


def select_bins_from_profile(bin_power_acc, best_ch, iq_fd_sample, n_frames_sample):
    """基于累积功率谱 + 采样相位数据选择呼吸和心跳 bin。

    用一段样本数据计算每个候选 bin 的 SNR，避免对全部帧解相位。

    v1.1: 遍历所有通道找 (ch, bin) 心跳 SNR 最优组合，避免单通道
    选到呼吸强但心跳弱的 bin（人体位置的心跳信号集中在特定通道）。

    v1.3: 1% 功率阈值以 0.3m 以外 (bin>=8) 的峰值为基准, 避开发射泄漏
    近场 (预实验 002 实测近场功率为人体位置 807 倍, 用全局峰值做阈值
    会把真实人体 bin 全部排除 → 0/87 可信窗)。
    """
    freqs = np.fft.rfftfreq(n_frames_sample, d=1 / FS)

    candidates = []
    for ch in range(N_CH):
        bin_power = bin_power_acc[:, ch]
        # 近场 bin<8 (0.3m 内) 为发射泄漏/近距杂波, 不作为功率基准
        power_thresh = np.max(bin_power[8:]) * 0.01
        for b in range(bin_power.shape[0]):
            if bin_power[b] < power_thresh:
                continue
            phi = np.unwrap(np.angle(iq_fd_sample[:, b, ch]))
            phi_var = np.var(phi)
            if not (0.1 < phi_var < 50):
                continue
            pxx = np.abs(np.fft.rfft(phi - phi.mean())) ** 2
            noise = max(np.mean(pxx[(freqs >= 2.5) & (freqs <= 5.0)]), 1e-10)
            hr_snr = np.mean(pxx[(freqs >= 0.8) & (freqs <= 2.5)]) / noise
            br_snr = np.mean(pxx[(freqs >= 0.1) & (freqs <= 0.5)]) / noise
            candidates.append((int(ch), int(b), float(hr_snr), float(br_snr)))

    if not candidates:
        raise RuntimeError("未找到有效距离门 — 检查数据质量")

    # 先按幅度稳定性过滤噪声 bin: 噪声 bin 幅度闪烁大 (CV 27-57%),
    # 且 1/f 噪声导致呼吸/心跳 SNR 虚高 (如 bin33 家族全通道 CV>40%)。
    # 真实点目标幅度稳定, CV 一般 < 15%。
    valid = []
    for ch, b, hr_snr, br_snr in candidates:
        mag = np.abs(iq_fd_sample[:, b, ch])
        cv_amp = np.std(mag) / (np.mean(mag) + 1e-12)
        if cv_amp < 0.15:
            valid.append((ch, b, hr_snr, br_snr))
    if not valid:
        # 全部被过滤: 数据质量差, 退回原始 SNR 最高的候选并警告
        print("  [WARN] 所有候选 bin 幅度不稳定, 退回原始 SNR 排序")
        valid = candidates

    br_ch, br_bin, _, br_snr = max(valid, key=lambda x: x[3])

    # 心跳 bin: 对全部幅度稳定候选做窄带一致性校验, 选 IBI 最稳定的。
    # 经验 (2026-08-06): 心跳带干净的位置 (如墙反射多径 bin89) 的
    # IBI CV 最低, 而人体直达 bin 呼吸谐波污染重, SNR 高但 HRV 乱。
    # 校验规则 (全部通过才有效):
    #   1. 心跳带 PTP 生理量级: < 3 rad (真实胸壁心跳 0.05-1.5 rad,
    #      伪影可达 14.8 rad)
    #   2. 窄带一致性: 频域主峰 fpk 的 ±0.05Hz 窄带内逐拍检测,
    #      检测 HR 与频域 HR 差 < 3 BPM
    best = None  # (cv, ch, b)
    for ch, b, snr, _ in valid:
        phi = np.unwrap(np.angle(iq_fd_sample[:, b, ch]))
        x = phi - phi.mean()
        f_phi, pxx_phi = np.fft.rfftfreq(len(x), 1 / FS), np.abs(np.fft.rfft(x)) ** 2
        m = (f_phi >= 0.7) & (f_phi <= 1.3)
        fpk = f_phi[m][np.argmax(pxx_phi[m])]
        # 窄带逐拍检测
        lo, hi = fpk - 0.05, fpk + 0.05
        sos = signal.butter(4, [lo, hi], btype='band', fs=FS, output='sos')
        xn = signal.sosfiltfilt(sos, phi)
        if np.ptp(xn) > 3.0:
            continue
        ref = 1.0 / fpk
        n_pts = len(xn)
        peaks = []
        i = 0
        while i < n_pts:
            lo_i, hi_i = int(i + 0.75 * ref * FS), min(int(i + 1.35 * ref * FS), n_pts)
            if lo_i >= n_pts or hi_i <= lo_i:
                break
            p = lo_i + np.argmax(xn[lo_i:hi_i])
            peaks.append(p)
            i = p + 1
        ibi = np.diff(peaks) / FS * 1000
        ibi = ibi[(ibi >= 400) & (ibi <= 2000)]
        if len(ibi) < 3:
            continue
        hr_peak = 60000 / np.mean(ibi)
        cv = np.std(ibi) / np.mean(ibi)
        if abs(hr_peak - fpk * 60) < 3.0 and cv < 0.15:
            if best is None or cv < best[0]:
                best = (cv, ch, b, hr_peak)
    if best is None:
        hr_ch, hr_bin, hr_snr = valid[0][0], valid[0][1], valid[0][2]
    else:
        _, hr_ch, hr_bin, _ = best
        hr_snr = next(c[2] for c in valid if c[0] == hr_ch and c[1] == hr_bin)
    return br_ch, br_bin, hr_ch, hr_bin, candidates


# ============================================================
# 第二步: 逐片提取位移 → 拼接
# ============================================================

def extract_displacement_all(npz_files, br_ch, br_bin, hr_ch, hr_bin):
    """逐片加载，直接对距离域复数取相位提取位移信号。

    v1.1: npz 的 256 点已是距离域，相位解调直接用原始复数，
    不再做 range_fft。呼吸/心跳可来自不同 (通道, bin)。
    """
    disp_br_chunks = []
    disp_hr_chunks = []
    n_total = 0

    for fpath in npz_files:
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        iq_fd = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        n_local = iq_fd.shape[0]

        disp_br = np.unwrap(np.angle(iq_fd[:, br_bin, br_ch]))
        disp_hr = np.unwrap(np.angle(iq_fd[:, hr_bin, hr_ch]))
        disp_br_chunks.append(disp_br)
        disp_hr_chunks.append(disp_hr)

        n_total += n_local
        d.close()

    disp_br_full = np.concatenate(disp_br_chunks)
    disp_hr_full = np.concatenate(disp_hr_chunks)
    return disp_br_full, disp_hr_full, n_total


# ============================================================
# 第三步: 体征提取
# ============================================================

def estimate_freq_periodogram(x, lo_hz, hi_hz):
    """周期图估计主频 (Hz)，范围内无峰返回 None。"""
    f, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (f >= lo_hz) & (f <= hi_hz)
    if not np.any(mask):
        return None
    return float(f[mask][np.argmax(pxx[mask])])


def detect_peaks_heart_lo(x, lo_bpm=40, hi_bpm=150):
    """
    低心率版心跳峰值检测 — 基于 detect_peaks_heart 逻辑，
    但放宽 lo_bpm 并用更低的 prominence 阈值。
    """
    n = len(x)
    x_std = np.std(x)
    if x_std < 1e-8:
        return np.array([], dtype=int)

    min_dist = max(int(FS * 60 / hi_bpm), int(FS * 0.3))
    best_peaks = np.array([], dtype=int)
    best_score = -1

    # 降低 prominence 因子 + 放宽 lo_bpm
    for prom_factor in [0.1, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01]:
        candidates, props = signal.find_peaks(
            x, distance=min_dist,
            prominence=max(prom_factor * x_std, 1e-8))

        if len(candidates) < 10:
            continue

        ibi = np.diff(candidates) / FS
        ibi = ibi[(ibi >= 60 / hi_bpm) & (ibi <= 60 / lo_bpm)]
        if len(ibi) < 5:
            continue
        cv = np.std(ibi) / np.mean(ibi)
        score = len(ibi) * (1 - min(cv, 1))
        if score > best_score:
            best_score = score
            best_peaks = candidates.copy()

    if len(best_peaks) < 2:
        return np.array([], dtype=int)

    # 用自相关周期做校正
    best_lag = np.argmax(np.correlate(x, x, mode='full')[len(x):])
    if best_lag > 0:
        period_s = best_lag / FS
        if 60/hi_bpm < period_s < 60/lo_bpm:
            ref_ibi = period_s
        else:
            ref_ibi = np.median(np.diff(best_peaks) / FS)
    else:
        ref_ibi = np.median(np.diff(best_peaks) / FS)

    # 去除异常间隔 (放宽到 0.3x–3.0x)
    ibi = np.diff(best_peaks) / FS
    ok = np.ones(len(best_peaks), dtype=bool)
    for i in range(len(best_peaks)):
        if i == 0 and len(ibi) > 0:
            if ibi[0] < 0.3 * ref_ibi or ibi[0] > 3.0 * ref_ibi:
                ok[i] = False
        elif i == len(best_peaks) - 1 and len(ibi) > 0:
            if ibi[-1] < 0.3 * ref_ibi or ibi[-1] > 3.0 * ref_ibi:
                ok[i] = False
        elif i > 0 and i < len(best_peaks) - 1:
            local_ibi = min(ibi[i - 1], ibi[i])
            if local_ibi < 0.3 * ref_ibi or local_ibi > 3.0 * ref_ibi:
                ok[i] = False
    cleaned = best_peaks[ok]
    return cleaned


def compute_hrv_time(ibi_ms):
    """时域 HRV: SDNN / RMSSD / mean_IBI / pNN50。

    ibi_ms: 清洗后的逐拍间期 (毫秒)。
    """
    sdnn = float(np.std(ibi_ms, ddof=1))
    rmssd = float(np.sqrt(np.mean(np.diff(ibi_ms) ** 2)))
    nn50 = float(np.sum(np.abs(np.diff(ibi_ms)) > 50))
    pnn50 = float(nn50 / (len(ibi_ms) - 1) * 100)
    return {
        "SDNN_ms": round(sdnn, 1),
        "RMSSD_ms": round(rmssd, 1),
        "mean_IBI_ms": round(float(np.mean(ibi_ms)), 1),
        "pNN50_pct": round(pnn50, 1),
        "n_intervals": int(len(ibi_ms)),
    }


def compute_hrv_frequency(ibi_ms):
    """频域 HRV: VLF / LF / HF / LF_HF（Welch + 4 Hz 样条重采样）。

    Task Force 1996 标准频带:
      VLF 0.003-0.04 Hz, LF 0.04-0.15 Hz, HF 0.15-0.40 Hz
    注意: 3 分钟窗口的 VLF 分辨率不足，仅报告供参考。
    """
    ibi_s = ibi_ms / 1000.0
    t_ibi = np.concatenate([[0], np.cumsum(ibi_s)])  # 每个峰的时间点

    # 4 Hz 三次样条插值 → 均匀时间序列
    t_rs = np.arange(0, t_ibi[-1], 1.0 / HRV_RS_FS)
    interp = np.interp(t_rs, t_ibi, np.concatenate([[ibi_s[0]], ibi_s]))
    # 去除线性趋势（Kubios 默认 detrend）
    trend = np.polyval(np.polyfit(t_rs, interp, 1), t_rs)
    x = interp - trend

    # Welch PSD（hann 窗, 256 点 → 频率分辨率 ~0.0156 Hz，够分辨 LF/HF 带）
    f, psd = signal.welch(x, fs=HRV_RS_FS, window="hann", nperseg=256)
    psd *= 1e6  # s²/Hz → ms²/Hz（v1.1 修正: 原 ×1000 小 1000 倍）

    def band_power(f0, f1):
        m = (f >= f0) & (f <= f1)
        if not np.any(m):
            return 0.0
        return float(np.trapezoid(psd[m], f[m]))

    vlf = band_power(0.003, 0.04)
    lf = band_power(0.04, 0.15)
    hf = band_power(0.15, 0.40)
    tp = vlf + lf + hf
    return {
        "VLF_ms2": round(vlf, 1),
        "LF_ms2": round(lf, 1),
        "HF_ms2": round(hf, 1),
        "LF_HF": round(lf / hf, 2) if hf > 0 else None,
        "TP_ms2": round(tp, 1),
    }


def analyze_displacement(disp_br, disp_hr, n_frames, method="vmd_heart"):
    """对拼接后的位移信号做分离、峰值检测、体征估计（含 HRV）。"""
    duration = n_frames / FS
    t = np.arange(n_frames) / FS

    # ── 呼吸 (bp 分离) ──
    breath_bp = _sos_bandpass(disp_br, 0.1, 0.5)
    br_freq_bp = estimate_freq_periodogram(breath_bp, 0.1, 0.5)
    breath = breath_bp
    br_freq = br_freq_bp
    breath_sep = {"method": "bp_breath", "source": "br_bin_bandpass"}

    # ── 心跳 (vmd_heart 分离) ──
    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)
    hr_freq_bp = estimate_freq_periodogram(heart_bp, 0.8, 2.5)

    if method == "vmd_heart":
        heartbeat, heart_sep = separate_vmd_heart_only(
            disp_hr, hr_freq_hint=hr_freq_bp
        )
        heart_pd = heartbeat
        hr_freq = estimate_freq_periodogram(heartbeat, 0.8, 2.5)
    else:
        heartbeat = heart_bp
        heart_pd = heart_bp
        hr_freq = hr_freq_bp
        heart_sep = {"method": "bp_heart", "source": "hr_bin_bandpass"}

    # ── 峰值检测 ──
    # 心跳: 窄带约束逐拍检测 (v1.4)。宽带峰检测在心跳带混入呼吸谐波/
    # 噪声峰导致 IBI 乱 (SDNN 80-200ms 伪高), 窄带 (频域主峰 ±0.05Hz)
    # 逐拍取 max 稳定 (实测 SDNN 26ms)。
    hp = np.array([], dtype=int)
    if hr_freq is not None:
        lo_nb, hi_nb = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
        sos_hp = signal.butter(4, [lo_nb, hi_nb], btype='band', fs=FS, output='sos')
        xn = signal.sosfiltfilt(sos_hp, heart_pd)
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
        hp = np.array(peaks_list, dtype=int)
    bp = detect_peaks_breath_robust(breath, lo_bpm=6, hi_bpm=30,
                                    br_freq_hint=br_freq)

    # ── HRV (时域 + 频域) ──
    hrv = {}
    if len(hp) >= 5:
        ibi_ms = np.diff(hp) / FS * 1000
        # 伪影剔除: 仅保留 300-2000 ms 的合理间期
        ibi_clean = ibi_ms[(ibi_ms >= 300) & (ibi_ms <= 2000)]
        if len(ibi_clean) >= 5:
            hrv = compute_hrv_time(ibi_clean)
            hrv["frequency"] = compute_hrv_frequency(ibi_clean)

    result = {
        "session": "sub-rest_3min_ses-REST",
        "version": "v1_vmd_heart",
        "duration_s": round(duration, 1),
        "frame_rate_hz": round(n_frames / duration, 1),
        "method": method,
        "separation": {"breath": breath_sep, "heart": heart_sep},
        "heart_rate": {
            "freq_bpm": round(float(hr_freq * 60), 1) if hr_freq else None,
            "time_bpm": round(float(60 * FS / np.mean(np.diff(hp))), 1) if len(hp) >= 2 else None,
            "n_peaks": int(len(hp)),
        },
        "breath_rate": {
            "freq_bpm": round(float(br_freq * 60), 1) if br_freq else None,
            "time_bpm": round(float(60 * FS / np.mean(np.diff(bp))), 1) if len(bp) >= 2 else None,
            "n_peaks": int(len(bp)),
        },
        "displacement_mm": {
            "breath_ptp": round(float(np.ptp(breath)), 2),
            "heart_ptp": round(float(np.ptp(heartbeat)), 2),
            "breath_std": round(float(np.std(breath)), 3),
            "heart_std": round(float(np.std(heartbeat)), 3),
        },
        "hrv": hrv,
    }

    return result, (t, breath, heartbeat, hp, bp)


# ============================================================
# 第四步: 绘图
# ============================================================

def plot_result(result, waveforms, output_dir, png_name):
    """6 面板诊断图: 呼吸/心跳波形、频谱、HR/BR 全程趋势。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    t, breath, heartbeat, hp, bp = waveforms
    duration = result["duration_s"]
    session = result["session"]
    method = result["method"]
    br_bin = result.get("bins", {}).get("breath", "?")
    hr_bin = result.get("bins", {}).get("heart", "?")

    fig, axes = plt.subplots(3, 2, figsize=(16, 10))
    fig.suptitle(f"Vital Signs — {session} ({duration/60:.0f} min) [{method}]",
                 fontsize=14)

    # ── 呼吸波形 (前60秒) ──
    ax = axes[0, 0]
    t_show = t[:min(int(60 * FS), len(t))]
    ax.plot(t_show, breath[:len(t_show)], "g-", alpha=0.8, linewidth=0.5)
    if len(bp) > 0:
        bp_show = bp[bp < len(t_show)]
        ax.plot(t[bp_show], breath[bp_show], "gx", markersize=5)
    ax.set_xlim(0, min(60, duration))
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    br_val = result["breath_rate"]["time_bpm"] or result["breath_rate"]["freq_bpm"] or 0
    ax.set_title(f"Breath waveform — first 60s ({br_val} BPM, "
                 f"{result['breath_rate']['n_peaks']} peaks)")
    ax.grid(True, alpha=0.3)

    # ── 心跳波形 (最后20秒) ──
    ax = axes[0, 1]
    start_t = max(0, duration - 20)
    mask = (t >= start_t)
    t_show = t[mask]
    ax.plot(t_show, heartbeat[mask], "r-", alpha=0.8, linewidth=0.5)
    if len(hp) > 0:
        hp_show = hp[(hp >= mask.argmax()) & (hp < len(t))]
        ax.plot(t[hp_show], heartbeat[hp_show], "rx", markersize=4)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    hr_val = result["heart_rate"]["time_bpm"] or result["heart_rate"]["freq_bpm"] or 0
    ax.set_title(f"Heart waveform — last 20s ({hr_val} BPM, "
                 f"{result['heart_rate']['n_peaks']} peaks)")
    ax.grid(True, alpha=0.3)

    # ── 呼吸频谱 ──
    ax = axes[1, 0]
    f_b, pxx_b = signal.periodogram(breath, fs=FS, window="hann")
    ax.semilogy(f_b, pxx_b, "g-")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power")
    ax.set_title("Breath spectrum")
    for lim in [0.1, 0.5]:
        ax.axvline(lim, color="gray", ls=":", alpha=0.5)
    br_freq = result["breath_rate"]["freq_bpm"]
    if br_freq:
        ax.axvline(br_freq / 60, color="green", ls="--", alpha=0.7,
                   label=f"{br_freq} BPM")
        ax.legend()

    # ── 心跳频谱 ──
    ax = axes[1, 1]
    f_h, pxx_h = signal.periodogram(heartbeat, fs=FS, window="hann")
    ax.semilogy(f_h, pxx_h, "r-")
    ax.set_xlim(0, 4)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power")
    ax.set_title("Heart spectrum")
    for lim in [0.8, 2.5]:
        ax.axvline(lim, color="gray", ls=":", alpha=0.5)
    hr_freq = result["heart_rate"]["freq_bpm"]
    if hr_freq:
        ax.axvline(hr_freq / 60, color="red", ls="--", alpha=0.7,
                   label=f"{hr_freq} BPM")
        ax.legend()

    # ── 全程心率趋势 ──
    ax = axes[2, 0]
    if len(hp) >= 2:
        hr_ts = 60 / (np.diff(hp) / FS)
        hr_t = t[hp[1:]]
        ax.plot(hr_t, hr_ts, "r.-", alpha=0.5, markersize=2, linewidth=0.5)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Heart Rate (BPM)")
        ax.set_title(f"HR time course ({len(hp)-1} beats)")
        ax.grid(True, alpha=0.3)
        ax.set_ylim(40, 140)
    else:
        ax.text(0.5, 0.5, "Insufficient peaks for trend",
                transform=ax.transAxes, ha='center', va='center')

    # ── 全程呼吸率趋势 ──
    ax = axes[2, 1]
    if len(bp) >= 2:
        br_ts = 60 / (np.diff(bp) / FS)
        br_t = t[bp[1:]]
        ax.plot(br_t, br_ts, "g.-", alpha=0.5, markersize=2, linewidth=0.5)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Breath Rate (BPM)")
        ax.set_title(f"BR time course ({len(bp)-1} breaths)")
        ax.grid(True, alpha=0.3)
        ax.set_ylim(5, 30)
    else:
        ax.text(0.5, 0.5, "Insufficient peaks for trend",
                transform=ax.transAxes, ha='center', va='center')

    plt.tight_layout()
    png_path = output_dir / png_name
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  [plot] {png_path}")
    return png_path


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="3min REST mmWave 生命体征分析")
    parser.add_argument("--br-ch", type=int, default=None, help="呼吸通道 (默认自动)")
    parser.add_argument("--br-bin", type=int, default=None, help="呼吸 bin (默认自动)")
    parser.add_argument("--hr-ch", type=int, default=None, help="心跳通道 (默认自动)")
    parser.add_argument("--hr-bin", type=int, default=None, help="心跳 bin (默认自动)")
    args = parser.parse_args()

    print("=" * 55)
    print("  REST-3min mmWave Vital Signs Analysis")
    print("=" * 55)

    # ── 收集 npz 分片 (块0 不带 part 前缀, 其余带 partNNN) ──
    npz_files = sorted(glob.glob(str(DATA_DIR / "sub-rest_3min_mmwave_datacube*.npz")))
    if not npz_files:
        print(f"[ERROR] 未找到 npz 分片: {DATA_DIR}")
        return
    print(f"\n[INFO] 找到 {len(npz_files)} 个 npz 分片")
    print(f"[INFO] 输出目录: {OUTPUT_DIR}")

    t_start = time_mod.time()

    # ═══════════════════════════════════════════════════════
    # Pass 1: 累积 range profile
    # ═══════════════════════════════════════════════════════
    print("\n── Pass 1: 累积 range power profile ──")
    ch_power, bin_power_acc, n_total = accumulate_range_profile(npz_files)
    best_ch = int(np.argmax(ch_power))
    print(f"\n  总帧数: {n_total}")
    print(f"  最佳通道: {best_ch}")

    # ── 用前 4 片 (40 秒) 样本做 bin 选择, 避免单片数据 SNR 估计不稳 ──
    sample_parts = []
    for fpath in npz_files[:4]:
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        sample_parts.append(np.stack([d[k] for k in keys], axis=-1).astype(np.complex64))
        d.close()
    iq_fd_sample = np.concatenate(sample_parts)

    br_ch, br_bin, hr_ch, hr_bin, candidates = select_bins_from_profile(
        bin_power_acc, best_ch, iq_fd_sample, iq_fd_sample.shape[0]
    )
    # 命令行显式覆盖 (数据验证后推荐: 本数据 ch4/bin89 心跳最干净)
    if args.br_ch is not None and args.br_bin is not None:
        br_ch, br_bin = args.br_ch, args.br_bin
    if args.hr_ch is not None and args.hr_bin is not None:
        hr_ch, hr_bin = args.hr_ch, args.hr_bin
    def _snr(ch, b, kind):
        for c in candidates:
            if c[0] == ch and c[1] == b:
                return c[2] if kind == 'hr' else c[3]
        return 0.0
    print(f"  呼吸 (ch{br_ch}, bin {br_bin}): SNR {_snr(br_ch, br_bin, 'br'):.1f}")
    print(f"  心跳 (ch{hr_ch}, bin {hr_bin}): SNR {_snr(hr_ch, hr_bin, 'hr'):.1f}")
    print(f"  候选 (ch,bin) 数: {len(candidates)}")

    # ═══════════════════════════════════════════════════════
    # Pass 2: 提取位移
    # ═══════════════════════════════════════════════════════
    print(f"\n── Pass 2: 提取位移 (br: ch{br_ch}/bin{br_bin}, hr: ch{hr_ch}/bin{hr_bin}) ──")
    disp_br, disp_hr, n_frames = extract_displacement_all(
        npz_files, br_ch, br_bin, hr_ch, hr_bin
    )
    print(f"  位移序列长度: {len(disp_br)} 帧 ({len(disp_br)/FS/60:.1f} min)")
    print(f"  BR 位移 PTP: {np.ptp(disp_br):.2f} mm")
    print(f"  HR 位移 PTP: {np.ptp(disp_hr):.2f} mm")

    # ═══════════════════════════════════════════════════════
    # Pass 3: 体征提取
    # ═══════════════════════════════════════════════════════
    print(f"\n── Pass 3: 生命体征提取 [{METHOD}] ──")
    result, waveforms = analyze_displacement(disp_br, disp_hr, n_frames, method=METHOD)
    # 补充 bin 信息
    result["best_channel"] = best_ch
    result["bins"] = {"breath": br_bin, "heart": hr_bin,
                      "breath_ch": br_ch, "heart_ch": hr_ch}
    result["n_frames"] = n_frames
    result["elapsed_s"] = round(time_mod.time() - t_start, 1)

    # ── 打印结果 ──
    hr = result["heart_rate"]
    br = result["breath_rate"]
    print(f"\n  {'指标':<12} {'频域':>12} {'时域':>12}")
    print(f"  {'-'*36}")
    print(f"  {'HR (BPM)':<12} {str(hr['freq_bpm']):>12} {str(hr['time_bpm']):>12}")
    print(f"  {'BR (BPM)':<12} {str(br['freq_bpm']):>12} {str(br['time_bpm']):>12}")

    hrv = result["hrv"]
    if hrv:
        print(f"\n  ── HRV (时域) ──")
        for k in ["mean_IBI_ms", "SDNN_ms", "RMSSD_ms", "pNN50_pct"]:
            print(f"  {k:<14}: {hrv[k]}")
        if "frequency" in hrv:
            hf = hrv["frequency"]
            print(f"  ── HRV (频域, ms²) ──")
            for k in ["VLF_ms2", "LF_ms2", "HF_ms2", "LF_HF", "TP_ms2"]:
                print(f"  {k:<14}: {hf[k]}")
    else:
        print("\n  [WARN] 心跳峰值不足, 无法计算 HRV")

    # ── 绘图 ──
    print("\n── Pass 4: 绘图 ──")
    plot_result(result, waveforms, OUTPUT_DIR,
                "sub-rest_3min_mmwave_vital_signs.png")

    # ── 保存 json ──
    json_path = OUTPUT_DIR / "sub-rest_3min_mmwave_vital_signs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [json] {json_path}")

    # ── 保存波形 npz ──
    t, breath, heartbeat, hp, bp = waveforms
    npz_path = OUTPUT_DIR / "sub-rest_3min_mmwave_vital_signs.npz"
    np.savez(
        npz_path,
        time_s=t,
        breath_mm=breath,
        heartbeat_mm=heartbeat,
        heart_peaks_idx=hp,
        breath_peaks_idx=bp,
    )
    print(f"  [npz] {npz_path}")
    print(f"\n完成, 耗时 {result['elapsed_s']} s")


if __name__ == '__main__':
    main()
