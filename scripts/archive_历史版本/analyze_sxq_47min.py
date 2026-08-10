"""
analyze_sxq_47min.py — SXQ 47分钟 SART 毫米波数据分析
=====================================================
分块加载 280 个 npz 分片，累积计算 range profile 后选 bin，
再逐片提取位移并拼接，最后用 v8 pipeline 做生命体征提取。

用法:
  cd 08_算法/scripts
  python analyze_sxq_47min.py

输出:
  output/06_SXQ-47min/v1/
    sub-sxq_ses-SART_mmwave_vital_signs.json  ← 体征指标
    sub-sxq_ses-SART_mmwave_vital_signs.npz   ← 波形数据
    sub-sxq_ses-SART_mmwave_vital_signs.png   ← 诊断图

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

# ── 将当前目录加入 sys.path，以便导入 v2/v3/v5/v8 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from process_vital_signs_v2 import (
    FS, N_SAMPLES, N_CH, WAVELENGTH_MM,
    range_fft, extract_displacement, _sos_bandpass, detect_peaks_heart,
)
from process_vital_signs_v3 import separate_vmd_heart_only
from process_vital_signs_v5 import detect_peaks_breath_robust


# ============================================================
# 配置
# ============================================================

# 数据目录 (npz 分片)
DATA_DIR = Path(r"D:\Project\厚粲杯\05_实验\_AttentionTest\03-data\mmwave")
# 输出目录
OUTPUT_DIR = Path(r"D:\Project\厚粲杯\08_算法\output\06_SXQ-47min\v1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 分析参数
METHOD = "vmd_heart"           # bp | vmd_heart
CHUNK_SIZE = 1000               # 每片帧数 (与 npz 分片一致)

# ============================================================
# 第一步: 累积 range profile → 选 bin
# ============================================================

def accumulate_range_profile(npz_files):
    """遍历所有 npz 分片，累积各通道各 bin 的平均功率。

    Returns:
        ch_power: (8,) 各通道总平均功率
        bin_power_acc: (129, 8) 各通道各 bin 的累积功率和
        n_total: 总帧数
    """
    bin_power_acc = None
    ch_power = np.zeros(N_CH)
    n_total = 0

    for i, fpath in enumerate(npz_files):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        # stack → (n_frames_local, 256, 8)
        iq_td = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        n_local = iq_td.shape[0]

        # range_fft → (n_local, 129, 8)
        iq_fd = range_fft(iq_td)

        # 通道功率累积
        ch_power += np.mean(np.abs(iq_fd) ** 2, axis=(0, 1)) * n_local

        # 各 bin 功率累积 (按通道)
        bin_power_local = np.mean(np.abs(iq_fd) ** 2, axis=0)  # (129, 8)
        if bin_power_acc is None:
            bin_power_acc = bin_power_local * n_local
        else:
            bin_power_acc += bin_power_local * n_local

        n_total += n_local
        d.close()

        if (i + 1) % 50 == 0:
            print(f"  [pass 1] {i+1}/{len(npz_files)} 片已处理, "
                  f"{n_total} 帧累积")

    ch_power /= n_total
    bin_power_acc /= n_total
    return ch_power, bin_power_acc, n_total


def select_bins_from_profile(bin_power_acc, best_ch, iq_fd_sample, n_frames_sample):
    """基于累积功率谱 + 采样相位数据选择呼吸和心跳 bin。

    用一小段数据计算每个候选 bin 的 SNR，避免对全部帧解相位。
    """
    bin_power = bin_power_acc[:, best_ch]
    power_thresh = np.max(bin_power) * 0.01
    freqs = np.fft.rfftfreq(n_frames_sample, d=1 / FS)

    candidates = []
    for b in range(bin_power.shape[0]):
        if bin_power[b] < power_thresh:
            continue
        phi = np.unwrap(np.angle(iq_fd_sample[:, b, best_ch]))
        phi_var = np.var(phi)
        if not (0.1 < phi_var < 50):
            continue
        pxx = np.abs(np.fft.rfft(phi - phi.mean())) ** 2
        noise = max(np.mean(pxx[(freqs >= 2.5) & (freqs <= 5.0)]), 1e-10)
        hr_snr = np.mean(pxx[(freqs >= 0.8) & (freqs <= 2.5)]) / noise
        br_snr = np.mean(pxx[(freqs >= 0.1) & (freqs <= 0.5)]) / noise
        candidates.append((int(b), float(hr_snr), float(br_snr)))

    if not candidates:
        raise RuntimeError("未找到有效距离门 — 检查数据质量")

    br_bin = max(candidates, key=lambda x: x[2])[0]
    hr_bin = max(candidates, key=lambda x: x[1])[0]
    return br_bin, hr_bin, candidates


# ============================================================
# 第二步: 逐片提取位移 → 拼接
# ============================================================

def extract_displacement_all(npz_files, best_ch, br_bin, hr_bin):
    """逐片加载、range_fft、提取呼吸和心跳距离门的位移信号。"""
    disp_br_chunks = []
    disp_hr_chunks = []
    n_total = 0

    for i, fpath in enumerate(npz_files):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        iq_td = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        iq_fd = range_fft(iq_td)
        n_local = iq_td.shape[0]

        disp_br = extract_displacement(iq_fd, br_bin, best_ch)
        disp_hr = extract_displacement(iq_fd, hr_bin, best_ch)
        disp_br_chunks.append(disp_br)
        disp_hr_chunks.append(disp_hr)

        n_total += n_local
        d.close()

        if (i + 1) % 50 == 0:
            print(f"  [pass 2] {i+1}/{len(npz_files)} 片, "
                  f"{n_total} 帧位移已提取")

    disp_br_full = np.concatenate(disp_br_chunks)
    disp_hr_full = np.concatenate(disp_hr_chunks)
    return disp_br_full, disp_hr_full, n_total


# ============================================================
# 第三步: 体征提取
# ============================================================

def estimate_freq_periodogram(x, lo_hz, hi_hz):
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


def analyze_displacement(disp_br, disp_hr, n_frames, method="vmd_heart"):
    """对拼接后的位移信号做分离、峰值检测、体征估计。"""
    duration = n_frames / FS
    t = np.arange(n_frames) / FS

    # ── 呼吸 ──
    breath_bp = _sos_bandpass(disp_br, 0.1, 0.5)
    br_freq_bp = estimate_freq_periodogram(breath_bp, 0.1, 0.5)
    breath = breath_bp
    br_freq = br_freq_bp
    breath_sep = {"method": "bp_breath", "source": "br_bin_bandpass"}

    # ── 心跳 ──
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

    # ── 峰值检测 (低心率适配) ──
    hp = detect_peaks_heart_lo(heart_pd, lo_bpm=40, hi_bpm=150)
    bp = detect_peaks_breath_robust(breath, lo_bpm=6, hi_bpm=30,
                                    br_freq_hint=br_freq)

    # ── HRV ──
    hrv = {}
    if len(hp) >= 4:
        ibi = np.diff(hp) / FS * 1000
        ibi_clean = ibi[(ibi >= 300) & (ibi <= 2000)]
        if len(ibi_clean) >= 4:
            hrv = {
                "SDNN_ms": round(float(np.std(ibi_clean, ddof=1)), 1),
                "RMSSD_ms": round(float(np.sqrt(np.mean(np.diff(ibi_clean) ** 2))), 1),
                "mean_IBI_ms": round(float(np.mean(ibi_clean)), 1),
            }

    result = {
        "session": "sub-sxq_ses-SART",
        "version": "v8_chunked",
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

def plot_result(result, waveforms, output_dir):
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
    png_path = output_dir / "sub-sxq_ses-SART_mmwave_vital_signs.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  [plot] {png_path}")
    return png_path


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 55)
    print("  SXQ 47min mmWave Vital Signs Analysis")
    print("=" * 55)

    # ── 收集 npz 分片 ──
    npz_files = sorted(glob.glob(
        str(DATA_DIR / "sub-sxq_mmwave_datacube_part*.npz")
    ))
    if not npz_files:
        # 尝试大写 (兼容旧命名)
        npz_files = sorted(glob.glob(
            str(DATA_DIR / "sub-SXQ_mmwave_datacube_part*.npz")
        ))
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
    print(f"  通道功率: {[f'{p:.4f}' for p in ch_power]}")
    print(f"  最佳通道: {best_ch}")

    # ── 用第一片数据做 bin 选择 ──
    d0 = np.load(npz_files[0])
    keys = sorted([k for k in d0.keys() if k.startswith('tx')])
    iq_sample = np.stack([d0[k] for k in keys], axis=-1).astype(np.complex64)
    iq_fd_sample = range_fft(iq_sample)
    d0.close()

    br_bin, hr_bin, candidates = select_bins_from_profile(
        bin_power_acc, best_ch, iq_fd_sample, iq_sample.shape[0]
    )
    print(f"  呼吸 bin: {br_bin} (SNR: {next(c[2] for c in candidates if c[0]==br_bin):.1f})")
    print(f"  心跳 bin: {hr_bin} (SNR: {next(c[1] for c in candidates if c[0]==hr_bin):.1f})")
    print(f"  候选 bin 数: {len(candidates)}")

    # ═══════════════════════════════════════════════════════
    # Pass 2: 提取位移
    # ═══════════════════════════════════════════════════════
    print(f"\n── Pass 2: 提取位移 (ch={best_ch}, br_bin={br_bin}, hr_bin={hr_bin}) ──")
    disp_br, disp_hr, n_frames = extract_displacement_all(
        npz_files, best_ch, br_bin, hr_bin
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
    result["bins"] = {"breath": br_bin, "heart": hr_bin}
    result["n_frames"] = n_frames
    result["elapsed_s"] = round(time_mod.time() - t_start, 1)

    # ── 打印结果 ──
    hr = result["heart_rate"]
    br = result["breath_rate"]
    print(f"\n  {'指标':<12} {'频域':>12} {'时域':>12}")
    print(f"  {'-'*36}")
    print(f"  {'HR (BPM)':<12} "
          f"{str(hr['freq_bpm']) if hr['freq_bpm'] else 'N/A':>12} "
          f"{str(hr['time_bpm']) if hr['time_bpm'] else 'N/A':>12}")
    print(f"  {'BR (BPM)':<12} "
          f"{str(br['freq_bpm']) if br['freq_bpm'] else 'N/A':>12} "
          f"{str(br['time_bpm']) if br['time_bpm'] else 'N/A':>12}")
    if result["hrv"]:
        h = result["hrv"]
        print(f"\n  HRV: SDNN={h['SDNN_ms']}ms, "
              f"RMSSD={h['RMSSD_ms']}ms, "
              f"meanIBI={h['mean_IBI_ms']}ms")

    # ═══════════════════════════════════════════════════════
    # 保存结果
    # ═══════════════════════════════════════════════════════
    print(f"\n── 保存 ──")

    # JSON
    json_path = OUTPUT_DIR / "sub-sxq_ses-SART_mmwave_vital_signs.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  [json] {json_path}")

    # NPZ
    t, breath, heartbeat, hp, bp = waveforms
    npz_path = OUTPUT_DIR / "sub-sxq_ses-SART_mmwave_vital_signs.npz"
    np.savez(
        npz_path,
        t=t,
        breath=breath,
        heartbeat=heartbeat,
        heart_peaks=hp,
        breath_peaks=bp,
        chest_bin=br_bin,
        heart_bin=hr_bin,
        best_ch=best_ch,
    )
    print(f"  [npz] {npz_path}")

    # Plot
    plot_result(result, waveforms, OUTPUT_DIR)

    elapsed = time_mod.time() - t_start
    print(f"\n[DONE] 总耗时: {elapsed:.1f}s ({elapsed/60:.1f}min)")


if __name__ == "__main__":
    main()
