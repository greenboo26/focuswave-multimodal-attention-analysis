"""
毫米波雷达生命体征提取 v1 — Baseline
=======================================
基于 Paterniani 2023 (Proc. IEEE) 标准方案。

流程:
  时域IQ → 距离FFT → SNR选bin → 相位提取 → 带通滤波 → 频谱/峰值检测

用法:
  python process_vital_signs_v1.py <datacube.bin路径>

依赖:
  numpy, scipy, matplotlib
"""
import struct, json, sys, argparse
import numpy as np
from scipy import signal
from pathlib import Path

# ============================================================
# 参数配置（可根据实验设置修改）
# ============================================================
FS = 100.0          # 帧率 (Hz)。默认 100fps，实际以采集为准
N_SAMPLES = 256     # 每 chirp ADC 采样数。需与固件配置一致
N_CH = 8            # 虚拟通道数。RS6240 为 2T4R = 8
FRAME_SIZE = 8196   # 每帧字节数 (PSIC 格式)
HEADER_SIZE = 32    # 全局头字节数 (PSIC 格式)
WAVELENGTH_MM = 5.0 # 60GHz 波长 (mm)。用于相位→位移换算


def parse_data(path):
    """解析 datacube.bin → 时域IQ数组 (n_frames, n_samples, n_ch)

    Parameters
    ----------
    path : Path
        .datacube.bin 文件路径（PSIC 格式）。

    Returns
    -------
    iq : np.ndarray, shape (n_frames, 256, 8)
        8 通道时域复 IQ 数据。
    n_frames : int
        总帧数。
    """
    raw = path.read_bytes()
    n_frames = (len(raw) - HEADER_SIZE) // FRAME_SIZE
    iq = np.zeros((n_frames, N_SAMPLES, N_CH), dtype=np.complex64)
    pos = HEADER_SIZE
    for i in range(n_frames):
        pos += 4                                    # 帧序号
        for s in range(N_SAMPLES):
            for ch in range(N_CH):
                v = struct.unpack('<I', raw[pos:pos+4])[0]
                imag = v & 0xFFFF
                if imag >= 0x8000: imag -= 0x10000
                real = (v >> 16) & 0xFFFF
                if real >= 0x8000: real -= 0x10000
                iq[i, s, ch] = complex(real, imag)
                pos += 4
    return iq, n_frames


def range_fft(iq_td):
    """时域IQ → 距离FFT (汉宁窗, 取正频率)

    参数
    ----
    iq_td : np.ndarray, shape (n_frames, 256, 8)
    Returns
    -------
    iq_fd : np.ndarray, shape (n_frames, 129, 8)
    """
    win = np.hanning(N_SAMPLES)
    fd = np.fft.fft(iq_td * win[None, :, None], n=N_SAMPLES, axis=1)
    return fd[:, :N_SAMPLES // 2 + 1, :]


def select_bins(iq_fd, n_frames):
    """按相位频谱SNR自动选最佳距离门和通道。

    对每个距离门计算相位方差（排除静止目标和纯噪声），
    然后选呼吸频段 (0.1-0.5Hz) 和心跳频段 (0.8-2.5Hz) SNR 最高的 bin。

    Returns
    -------
    best_ch : int
    br_bin, hr_bin : int
    """
    ch_power = np.mean(np.abs(iq_fd) ** 2, axis=(0, 1))
    best_ch = int(np.argmax(ch_power))

    freqs = np.fft.rfftfreq(n_frames, d=1 / FS)
    candidates = []
    for b in range(iq_fd.shape[1]):
        phi = np.unwrap(np.angle(iq_fd[:, b, best_ch]))
        phi_var = np.var(phi)
        if not (0.1 < phi_var < 50):
            continue
        pxx = np.abs(np.fft.rfft(phi - phi.mean())) ** 2
        noise = max(np.mean(pxx[(freqs >= 2.5) & (freqs <= 5.0)]), 1e-10)
        hr_snr = np.mean(pxx[(freqs >= 0.8) & (freqs <= 2.5)]) / noise
        br_snr = np.mean(pxx[(freqs >= 0.1) & (freqs <= 0.5)]) / noise
        candidates.append((b, hr_snr, br_snr))

    if not candidates:
        raise RuntimeError("未找到有效距离门")

    br_bin = max(candidates, key=lambda x: x[2])[0]
    hr_bin = max(candidates, key=lambda x: x[1])[0]
    return best_ch, br_bin, hr_bin


def extract_displacement(iq_fd, bin_idx, ch):
    """相位提取 → 胸壁位移 (mm)

    相位解卷绕后按 波长/(4π) 换算为毫米位移。

    Returns
    -------
    disp : np.ndarray
    """
    phi = np.unwrap(np.angle(iq_fd[:, bin_idx, ch]))
    return WAVELENGTH_MM * phi / (4 * np.pi)


def sos_bandpass(x, lo_hz, hi_hz):
    """SOS格式带通滤波（数值稳定，适合低截止频率）"""
    sos = signal.butter(4, [lo_hz, hi_hz], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)


def detect_peaks(x, min_dist_s, prom_factor=0.3):
    """简单峰值检测。

    Parameters
    ----------
    x : np.ndarray
    min_dist_s : float
        最小间隔（秒）。呼吸约 1.5s，心跳约 0.4s。
    prom_factor : float
        峰显著性系数（相对于 std 的倍数）。

    Returns
    -------
    peaks : np.ndarray
    """
    prom = max(prom_factor * np.std(x), 1e-6)
    peaks, _ = signal.find_peaks(x, distance=int(min_dist_s * FS), prominence=prom)
    return peaks


def analyze(data_path, output_dir=None):
    """完整分析流程。

    解析 bin → FFT → 选 bin → 带通滤波 → 频谱/峰值 → HR/BR/HRV。

    Parameters
    ----------
    data_path : str or Path
        .datacube.bin 文件路径。
    output_dir : Path or None
        输出目录（默认与数据同目录）。

    Returns
    -------
    result : dict
    waveforms : tuple
    """
    data_path = Path(data_path)
    session = data_path.stem.replace("_datacube", "")
    if output_dir is None:
        output_dir = data_path.parent

    # 1-2. 解析 + FFT
    iq_td, n_frames = parse_data(data_path)
    iq_fd = range_fft(iq_td)
    duration = n_frames / FS

    # 3. 选bin
    best_ch, br_bin, hr_bin = select_bins(iq_fd, n_frames)

    # 4. 位移提取
    disp_b = extract_displacement(iq_fd, br_bin, best_ch)
    disp_h = extract_displacement(iq_fd, hr_bin, best_ch)

    # 5. 带通滤波
    breath = sos_bandpass(disp_b, 0.1, 0.5)
    heartbeat = sos_bandpass(disp_h, 0.8, 2.5)

    # 6. 频域分析
    f, pxx_b = signal.periodogram(breath, fs=FS, window='hann')
    _, pxx_h = signal.periodogram(heartbeat, fs=FS, window='hann')

    br_mask = (f >= 0.1) & (f <= 0.5)
    hr_mask = (f >= 0.8) & (f <= 2.5)
    br_freq = f[br_mask][np.argmax(pxx_b[br_mask])] if br_mask.any() else None
    hr_freq = f[hr_mask][np.argmax(pxx_h[hr_mask])] if hr_mask.any() else None

    # 7. 时域峰值检测
    hp = detect_peaks(heartbeat, 0.4)
    bp = detect_peaks(breath, 1.5)

    # 8. HRV
    hr_info = {}
    if len(hp) >= 4:
        ibi = np.diff(hp) / FS * 1000
        ibi_clean = ibi[(ibi >= 300) & (ibi <= 2000)]
        if len(ibi_clean) >= 4:
            hr_info = {
                "SDNN_ms": round(float(np.std(ibi_clean, ddof=1)), 1),
                "RMSSD_ms": round(float(np.sqrt(np.mean(np.diff(ibi_clean) ** 2))), 1),
                "mean_IBI_ms": round(float(np.mean(ibi_clean)), 1),
            }

    result = {
        "session": session,
        "duration_s": round(duration, 1),
        "frame_rate_hz": FS,
        "method": "bp",
        "best_channel": best_ch,
        "bins": {"breath": br_bin, "heart": hr_bin},
        "heart_rate": {
            "freq_bpm": round(hr_freq * 60, 1) if hr_freq else None,
            "time_bpm": round(float(60 * FS / np.mean(np.diff(hp))), 1)
                        if len(hp) >= 2 else None,
            "n_peaks": int(len(hp)),
        },
        "breath_rate": {
            "freq_bpm": round(br_freq * 60, 1) if br_freq else None,
            "time_bpm": round(float(60 * FS / np.mean(np.diff(bp))), 1)
                        if len(bp) >= 2 else None,
            "n_peaks": int(len(bp)),
        },
        "displacement_mm": {
            "breath_ptp": round(float(np.ptp(breath)), 2),
            "heart_ptp": round(float(np.ptp(heartbeat)), 2),
            "breath_std": round(float(np.std(breath)), 3),
            "heart_std": round(float(np.std(heartbeat)), 3),
        },
        "hrv": hr_info,
    }

    # 保存结果
    json_path = output_dir / f"{session}_vital_signs.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    npz_path = output_dir / f"{session}_vital_signs.npz"
    np.savez(npz_path,
             t=np.arange(n_frames) / FS, breath=breath, heartbeat=heartbeat,
             heart_peaks=hp, breath_peaks=bp,
             chest_bin=br_bin, heart_bin=hr_bin, best_ch=best_ch)

    return result, (np.arange(n_frames) / FS, breath, heartbeat, hp, bp,
                    iq_fd, best_ch, br_bin, hr_bin)


def plot(result, waveforms, output_dir, session):
    """生成 3×2 子图分析图。"""
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DengXian']
    plt.rcParams['axes.unicode_minus'] = False

    t, breath, heartbeat, hp, bp, iq_fd, best_ch, br_bin, hr_bin = waveforms
    n_frames = len(t)
    duration = result["duration_s"]

    fig, axes = plt.subplots(3, 2, figsize=(16, 10))
    fig.suptitle(f"生命体征分析 — {session} ({duration}s)", fontsize=14)

    ax = axes[0, 0]
    rp = np.mean(np.abs(iq_fd) ** 2, axis=(0, 2))
    ax.plot(rp)
    ax.axvline(br_bin, color='g', ls='--', alpha=0.5, label=f'呼吸 bin {br_bin}')
    ax.axvline(hr_bin, color='r', ls='--', alpha=0.5, label=f'心跳 bin {hr_bin}')
    ax.set_xlabel('距离门'); ax.set_ylabel('功率')
    ax.set_title('距离剖面'); ax.legend(); ax.set_xlim(0, 128)

    ax = axes[0, 1]
    n_disp = min(1000, len(t))
    ax.plot(t[:n_disp], extract_displacement(iq_fd, br_bin, best_ch)[:n_disp],
            alpha=0.7, label='呼吸门位移')
    ax.plot(t[:n_disp], extract_displacement(iq_fd, hr_bin, best_ch)[:n_disp],
            alpha=0.7, label='心跳门位移')
    ax.set_xlabel('时间 (s)'); ax.set_ylabel('位移 (mm)')
    ax.set_title('原始位移 (前10s)'); ax.legend()

    ax = axes[1, 0]
    ax.plot(t, breath, 'g-', alpha=0.8)
    if len(bp) > 0:
        ax.plot(t[bp], breath[bp], 'gx', markersize=5)
    ax.set_xlim(0, 30); ax.set_xlabel('时间 (s)'); ax.set_ylabel('mm')
    br_val = result['breath_rate']['time_bpm'] or result['breath_rate']['freq_bpm'] or 0
    ax.set_title(f'呼吸波形 ({br_val} BPM)'); ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.plot(t, heartbeat, 'r-', alpha=0.8)
    if len(hp) > 0:
        ax.plot(t[hp], heartbeat[hp], 'rx', markersize=4)
    start = max(0, n_frames // FS - 20)
    end = n_frames // FS
    ax.set_xlim(start, min(end, duration)); ax.set_xlabel('时间 (s)'); ax.set_ylabel('mm')
    hr_val = result['heart_rate']['time_bpm'] or result['heart_rate']['freq_bpm'] or 0
    ax.set_title(f'心跳波形 ({hr_val} BPM, {result["heart_rate"]["n_peaks"]}拍)')
    ax.grid(True, alpha=0.3)

    ax = axes[2, 0]
    f, pxx = signal.periodogram(breath, fs=FS, window='hann')
    ax.plot(f, pxx, 'g-')
    ax.set_xlim(0, 1); ax.set_xlabel('频率 (Hz)'); ax.set_ylabel('功率')
    ax.set_title('呼吸频谱')
    for lim in [0.1, 0.5]:
        ax.axvline(lim, color='gray', ls=':', alpha=0.5)

    ax = axes[2, 1]
    f, pxx = signal.periodogram(heartbeat, fs=FS, window='hann')
    ax.plot(f, pxx, 'r-')
    ax.set_xlim(0, 4); ax.set_xlabel('频率 (Hz)'); ax.set_ylabel('功率')
    ax.set_title('心跳频谱')
    for lim in [0.8, 2.5]:
        ax.axvline(lim, color='gray', ls=':', alpha=0.5)

    plt.tight_layout()
    png_path = output_dir / f"{session}_vital_signs.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="毫米波雷达生命体征提取 (Baseline)")
    parser.add_argument("data_path", help="datacube.bin 文件路径")
    parser.add_argument("--output", "-o", help="输出目录 (默认: 数据所在目录)")
    parser.add_argument("--no-plot", action="store_true", help="跳过绘图")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else None
    result, waveforms = analyze(args.data_path, out_dir)
    session = result["session"]

    print(f"\n会话: {session}  ({result['duration_s']}s)")
    print(f"{'指标':<12} {'频域':>10} {'时域':>10}")
    print("-" * 34)
    hr = result['heart_rate']
    br = result['breath_rate']
    print(f"{'心率(HR)':<12} {str(hr['freq_bpm'])+' BPM' if hr['freq_bpm'] else 'N/A':>10}"
          f" {str(hr['time_bpm'])+' BPM' if hr['time_bpm'] else 'N/A':>10}")
    print(f"{'呼吸率(BR)':<12} {str(br['freq_bpm'])+' BPM' if br['freq_bpm'] else 'N/A':>10}"
          f" {str(br['time_bpm'])+' BPM' if br['time_bpm'] else 'N/A':>10}")
    print(f"{'呼吸幅度':<12} {result['displacement_mm']['breath_ptp']:.1f} mm")
    print(f"{'心跳幅度':<12} {result['displacement_mm']['heart_ptp']:.1f} mm")
    if result['hrv']:
        print(f"SDNN={result['hrv']['SDNN_ms']}ms  RMSSD={result['hrv']['RMSSD_ms']}ms")

    if not args.no_plot:
        png_path = plot(result, waveforms,
                        Path(args.output) if args.output else Path(args.data_path).parent,
                        session)
        print(f"图: {png_path}")

    out_p = Path(args.output) if args.output else Path(args.data_path).parent
    print(f"结果: {out_p / f'{session}_vital_signs.json'}")


if __name__ == "__main__":
    main()
