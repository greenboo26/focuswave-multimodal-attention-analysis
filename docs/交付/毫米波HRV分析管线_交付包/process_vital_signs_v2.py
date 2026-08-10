"""
毫米波雷达生命体征提取 v2
=========================
支持两种分离方法：
  bp   — 带通滤波 (baseline, 默认)
  vmd  — 变分模态分解 (升级方案, 更纯净)

用法:
  python process_vital_signs_v2.py <datacube.bin或.npz路径> [--method vmd]

依赖:
  numpy, scipy, matplotlib, vmdpy
"""
import struct, json, sys, argparse
import numpy as np
from scipy import signal
from pathlib import Path

FS = 100.0          # 帧率 (Hz)
N_SAMPLES = 256     # 每chirp ADC采样数
N_CH = 8            # 虚拟通道数 (2T4R)
WAVELENGTH_MM = 5.0 # 60GHz 波长 (mm)

# ---------- 数据加载 ----------

def load_data(data_path):
    """自动识别 bin/npz 并加载为 IQ 数组 (n_frames, 256, 8)"""
    path = Path(data_path)
    if path.suffix == '.npz':
        d = np.load(path)
        keys = [k for k in d.keys() if k.startswith('tx')]
        if not keys:
            raise ValueError(f'npz 中未找到 tx* 通道数据: {list(d.keys())}')
        return np.stack([d[k] for k in keys], axis=-1)
    else:
        return _parse_bin(path)

def _parse_bin(path):
    """解析 datacube.bin → (n_frames, 256, 8)"""
    HEADER_SIZE = 32
    FRAME_SIZE = 8196
    raw = path.read_bytes()
    n_frames = (len(raw) - HEADER_SIZE) // FRAME_SIZE
    iq = np.zeros((n_frames, N_SAMPLES, N_CH), dtype=np.complex64)
    pos = HEADER_SIZE
    for i in range(n_frames):
        pos += 4
        for s in range(N_SAMPLES):
            for ch in range(N_CH):
                v = struct.unpack('<I', raw[pos:pos+4])[0]
                imag = v & 0xFFFF
                if imag >= 0x8000: imag -= 0x10000
                real = (v >> 16) & 0xFFFF
                if real >= 0x8000: real -= 0x10000
                iq[i, s, ch] = complex(real, imag)
                pos += 4
    return iq

# ---------- 距离FFT ----------

def range_fft(iq_td):
    """时域IQ → 距离FFT (汉宁窗, 取正频率)"""
    win = np.hanning(N_SAMPLES)
    fd = np.fft.fft(iq_td * win[None, :, None], n=N_SAMPLES, axis=1)
    return fd[:, :N_SAMPLES // 2 + 1, :]

# ---------- 选bin ----------

def select_bins(iq_fd, n_frames):
    """按相位频谱SNR自动选最佳通道、呼吸bin、心跳bin"""
    ch_power = np.mean(np.abs(iq_fd) ** 2, axis=(0, 1))
    best_ch = int(np.argmax(ch_power))
    # 各 bin 平均功率（用于排除边缘噪声bin）
    bin_power = np.mean(np.abs(iq_fd[:, :, best_ch]) ** 2, axis=0)
    power_thresh = np.max(bin_power) * 0.01  # 1% 最大功率
    freqs = np.fft.rfftfreq(n_frames, d=1 / FS)
    candidates = []
    for b in range(iq_fd.shape[1]):
        if bin_power[b] < power_thresh:
            continue
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
    """相位提取 → 胸壁位移 (mm)"""
    phi = np.unwrap(np.angle(iq_fd[:, bin_idx, ch]))
    return WAVELENGTH_MM * phi / (4 * np.pi)

# ---------- 分离方法 ----------

def _sos_bandpass(x, lo_hz, hi_hz):
    """SOS格式带通滤波"""
    sos = signal.butter(4, [lo_hz, hi_hz], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)

def separate_bp(disp):
    """Baseline: 带通滤波分离呼吸/心跳"""
    breath = _sos_bandpass(disp, 0.1, 0.5)
    heartbeat = _sos_bandpass(disp, 0.8, 2.5)
    return breath, heartbeat, {'method': 'bp'}

def separate_vmd(disp):
    """VMD: 变分模态分解分离呼吸/心跳。

    Parameters
    ----------
    disp : np.ndarray
        胸壁位移信号 (n_frames,)，由 extract_displacement() 产生。

    Returns
    -------
    breath, heartbeat : np.ndarray
        分离后的呼吸和心跳信号。
    info : dict
        VMD 分解信息：method, br_mode, hr_mode, n_modes, center_freqs。

    Notes
    -----
    VMD 参数 (alpha=1000, K=4) 经参数扫描确定。
    如果帧数 < 200 或心率超出 30-200 BPM，自动回退到带通滤波。
    """
    from vmdpy import VMD
    # 如果帧数过少则回退到带通
    if len(disp) < 200:
        return separate_bp(disp)

    # VMD 参数: alpha=1000, tau=0, K=4, DC=False, init=1, tol=1e-6
    u, u_hat, omega = VMD(disp, alpha=1000, tau=0, K=4,
                           DC=False, init=1, tol=1e-6)

    # 自动识别呼吸 mode (0.1-0.5Hz) 和心跳 mode (0.8-2.5Hz)
    # 使用原始频段能量（非归一化），避免低能量噪声模态被偏好
    br_energy = []
    hr_energy = []
    mode_cf = []
    for k in range(u.shape[0]):
        f, pxx = signal.periodogram(u[k], fs=FS, window='hann')
        br_energy.append(np.sum(pxx[(f >= 0.1) & (f <= 0.5)]))
        hr_energy.append(np.sum(pxx[(f >= 0.8) & (f <= 2.5)]))
        mode_cf.append(float(omega[-1, k] * FS))

    br_mode = int(np.argmax(br_energy))
    hr_mode = int(np.argmax(hr_energy))
    hr_bpm = mode_cf[hr_mode] * 60

    # 如果呼吸和心跳 mode 相同，或心率超出正常范围（<30 或 >200 BPM），回退到带通
    if br_mode == hr_mode or hr_bpm < 30 or hr_bpm > 200:
        return separate_bp(disp)

    info = {
        'method': 'vmd',
        'br_mode': br_mode,
        'hr_mode': hr_mode,
        'n_modes': u.shape[0],
        'center_freqs': [float(omega[-1, k] * FS) for k in range(u.shape[0])],
    }
    return u[br_mode], u[hr_mode], info

# ---------- 峰值检测 ----------

def _autocorr_peak_detect(x, lo_bpm=48, hi_bpm=150):
    """用自相关估计主周期 → 约束峰值搜索窗口"""
    n = len(x)
    ac = signal.correlate(x - np.mean(x), x - np.mean(x), mode='same')
    ac = ac[n // 2:]  # 正半轴
    # 在预期心率范围内找自相关峰值
    min_lag = int(FS * 60 / hi_bpm)
    max_lag = int(FS * 60 / lo_bpm)
    if max_lag >= len(ac):
        max_lag = len(ac) - 1
    if min_lag >= max_lag:
        return None, None
    peak_lags, _ = signal.find_peaks(ac[min_lag:max_lag + 1])
    if len(peak_lags) == 0:
        return None, None
    best_lag = min_lag + peak_lags[np.argmax(ac[min_lag + peak_lags])]
    period_s = best_lag / FS
    return best_lag, period_s


def detect_peaks_heart(x, lo_bpm=48, hi_bpm=150):
    """
    鲁棒心跳峰值检测。

    策略：先用 prominence 检测（对 clean 信号效果好），
    结合自相关周期做 IBI 校正。

    Parameters
    ----------
    x : np.ndarray
        心跳信号（已分离），单位一般 mm。
    lo_bpm, hi_bpm : int
        心率范围下限和上限 BPM (默认 48-150)。
        根据实验任务调整：静息态可收窄，运动后可放宽。

    Returns
    -------
    peaks : np.ndarray
        检测到的心跳峰值位置（帧索引）。
    """
    n = len(x)
    x_std = np.std(x)
    if x_std < 1e-8:
        return np.array([], dtype=int)

    min_dist = max(int(FS * 60 / hi_bpm), int(FS * 0.3))

    # 用多个 prominence 阈值，选效果最好的
    best_peaks = np.array([], dtype=int)
    best_score = -1

    for prom_factor in [0.2, 0.15, 0.1, 0.05]:
        candidates, props = signal.find_peaks(
            x, distance=min_dist,
            prominence=max(prom_factor * x_std, 1e-6))

        if len(candidates) < 3:
            continue

        # 用 IBI 稳定性评分：CV 越小越好
        ibi = np.diff(candidates) / FS
        ibi = ibi[(ibi >= 60/hi_bpm) & (ibi <= 60/lo_bpm)]
        if len(ibi) < 2:
            continue
        cv = np.std(ibi) / np.mean(ibi)
        score = len(ibi) * (1 - min(cv, 1))  # 峰数多 + CV 低 = 分高
        if score > best_score:
            best_score = score
            best_peaks = candidates.copy()

    if len(best_peaks) < 2:
        return np.array([], dtype=int)

    # 用自相关周期做校正
    best_lag, period_s = _autocorr_peak_detect(x, lo_bpm, hi_bpm)
    ref_ibi = period_s if (period_s and 60/hi_bpm < period_s < 60/lo_bpm) else np.median(np.diff(best_peaks)/FS)

    # 去除异常间隔
    ibi = np.diff(best_peaks) / FS
    ok = np.ones(len(best_peaks), dtype=bool)
    for i in range(len(best_peaks)):
        if i == 0 and len(ibi) > 0:
            if ibi[0] < 0.35 * ref_ibi or ibi[0] > 2.5 * ref_ibi:
                ok[i] = False
        elif i == len(best_peaks) - 1 and len(ibi) > 0:
            if ibi[-1] < 0.35 * ref_ibi or ibi[-1] > 2.5 * ref_ibi:
                ok[i] = False
        elif i > 0 and i < len(best_peaks) - 1:
            local_ibi = min(ibi[i - 1], ibi[i])
            if local_ibi < 0.35 * ref_ibi or local_ibi > 2.5 * ref_ibi:
                ok[i] = False
    cleaned = best_peaks[ok]

    # 补漏
    if len(cleaned) >= 3:
        final = [cleaned[0]]
        for i in range(1, len(cleaned)):
            gap = (cleaned[i] - final[-1]) / FS
            if gap > 1.5 * ref_ibi and gap < 3.5 * ref_ibi:
                est = final[-1] + int(ref_ibi * FS)
                lo = max(0, est - int(0.1 * FS))
                hi = min(n, est + int(0.1 * FS))
                if hi > lo:
                    final.append(lo + np.argmax(x[lo:hi]))
            elif gap <= 60 / lo_bpm:
                final.append(cleaned[i])
        cleaned = np.array(final, dtype=int)

    return cleaned


def detect_peaks_breath(x, min_dist_s=1.5):
    """呼吸峰值检测"""
    x_std = np.std(x)
    if x_std < 1e-8:
        return np.array([], dtype=int)
    min_dist = int(min_dist_s * FS)
    peaks, _ = signal.find_peaks(x, distance=min_dist,
                                  prominence=max(0.3 * x_std, 1e-6))
    return peaks

# ---------- 主流程 ----------

def analyze(data_path, method='bp', output_dir=None):
    """完整分析流程"""
    data_path = Path(data_path)
    session = data_path.stem.replace('_datacube', '').replace('_vital_signs', '')

    if output_dir is None:
        output_dir = data_path.parent

    # 加载 + FFT
    iq_td = load_data(data_path)
    if iq_td.ndim == 2:
        iq_td = iq_td[:, :, None]
    iq_fd = range_fft(iq_td)
    n_frames = iq_fd.shape[0]
    duration = n_frames / FS

    # 选 bin
    best_ch, br_bin, hr_bin = select_bins(iq_fd, n_frames)

    # 位移
    disp_br = extract_displacement(iq_fd, br_bin, best_ch)
    disp_hr = extract_displacement(iq_fd, hr_bin, best_ch)

    # === 频率估计（统一用 baseline 带通 + periodogram，稳定可靠）===
    breath_bp = _sos_bandpass(disp_br, 0.1, 0.5)
    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)
    f, pxx_b = signal.periodogram(breath_bp, fs=FS, window='hann')
    _, pxx_h = signal.periodogram(heart_bp, fs=FS, window='hann')
    br_mask = (f >= 0.1) & (f <= 0.5)
    hr_mask = (f >= 0.8) & (f <= 2.5)
    br_freq = f[br_mask][np.argmax(pxx_b[br_mask])] if br_mask.any() else None
    hr_freq = f[hr_mask][np.argmax(pxx_h[hr_mask])] if hr_mask.any() else None

    # === 信号分离 ===
    if method == 'vmd':
        breath, heartbeat_vmd, sep_info = separate_vmd(disp_hr)
        heartbeat = heartbeat_vmd
        # VMD 信号用频域 HR 窄带引导峰值检测
        if hr_freq:
            lo = max(0.5, hr_freq - 0.4)
            hi = min(3.5, hr_freq + 0.6)
            sos = signal.butter(4, [lo, hi], btype='band', fs=FS, output='sos')
            heart_pd = signal.sosfiltfilt(sos, heartbeat_vmd)
        else:
            heart_pd = heart_bp
    else:
        breath, heartbeat, sep_info = separate_bp(disp_br)
        heart_pd = heart_bp  # 统一用 HR bin 带通信号

    hp = detect_peaks_heart(heart_pd)
    bp = detect_peaks_breath(breath, 1.5)

    # HRV
    hrv = {}
    ibi_ms = None
    if len(hp) >= 4:
        ibi = np.diff(hp) / FS * 1000
        ibi_clean = ibi[(ibi >= 300) & (ibi <= 2000)]
        if len(ibi_clean) >= 4:
            ibi_ms = ibi_clean
            hrv = {
                "SDNN_ms": round(float(np.std(ibi_clean, ddof=1)), 1),
                "RMSSD_ms": round(float(np.sqrt(np.mean(np.diff(ibi_clean) ** 2))), 1),
                "mean_IBI_ms": round(float(np.mean(ibi_clean)), 1),
                "note": "信噪比受限, 仅供参考; Wang 2021 VMD 方法可改进"
            }

    result = {
        "session": session,
        "duration_s": round(duration, 1),
        "frame_rate_hz": round(n_frames / duration, 1),
        "method": method,
        "separation": sep_info,
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
        "hrv": hrv,
    }

    # 保存 JSON
    json_path = output_dir / f"{session}_vital_signs.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    # 保存波形
    npz_path = output_dir / f"{session}_vital_signs.npz"
    np.savez(npz_path,
             t=np.arange(n_frames) / FS, breath=breath, heartbeat=heartbeat,
             heart_peaks=hp, breath_peaks=bp,
             chest_bin=br_bin, heart_bin=hr_bin, best_ch=best_ch)

    return result, (np.arange(n_frames) / FS, breath, heartbeat, hp, bp,
                    iq_fd, best_ch, br_bin, hr_bin)


# ---------- 绘图 ----------

def plot(result, waveforms, output_dir, session):
    """生成 3×2 子图分析图：距离剖面、位移、呼吸/心跳波形、频谱。"""
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DengXian']
    plt.rcParams['axes.unicode_minus'] = False

    t, breath, heartbeat, hp, bp, iq_fd, best_ch, br_bin, hr_bin = waveforms
    n_frames = len(t)
    duration = result["duration_s"]
    method = result["method"]

    fig, axes = plt.subplots(3, 2, figsize=(16, 10))
    fig.suptitle(f"生命体征分析 — {session} ({duration}s) [{method}]", fontsize=14)

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
    ax.set_title(f'原始位移 (前10s) [{method}]'); ax.legend()

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


# ---------- CLI ----------

def main():
    """命令行入口：解析参数 → 分析 → 输出结果和图表。"""
    parser = argparse.ArgumentParser(description="毫米波雷达生命体征提取")
    parser.add_argument("data_path", help="datacube.bin 或 .npz 文件路径")
    parser.add_argument("--method", "-m", choices=['bp', 'vmd'], default='bp',
                        help="分离方法: bp=带通滤波, vmd=变分模态分解 (默认: bp)")
    parser.add_argument("--output", "-o", help="输出目录 (默认: 数据所在目录)")
    parser.add_argument("--no-plot", action="store_true", help="跳过绘图")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else None
    result, waveforms = analyze(args.data_path, method=args.method, output_dir=out_dir)
    session = result["session"]

    print(f"\n[{args.method}] {session}  ({result['duration_s']}s)")
    print(f"{'指标':<12} {'频域':>10} {'时域':>10}")
    print("-" * 34)
    hr = result['heart_rate']
    br = result['breath_rate']
    print(f"{'心率(HR)':<12} {str(hr['freq_bpm'])+' BPM' if hr['freq_bpm'] else 'N/A':>10} {str(hr['time_bpm'])+' BPM' if hr['time_bpm'] else 'N/A':>10}")
    print(f"{'呼吸率(BR)':<12} {str(br['freq_bpm'])+' BPM' if br['freq_bpm'] else 'N/A':>10} {str(br['time_bpm'])+' BPM' if br['time_bpm'] else 'N/A':>10}")
    print(f"{'呼吸幅度':<12} {result['displacement_mm']['breath_ptp']:.1f} mm")
    print(f"{'心跳幅度':<12} {result['displacement_mm']['heart_ptp']:.1f} mm")
    if result['hrv']:
        print(f"SDNN={result['hrv']['SDNN_ms']}ms  RMSSD={result['hrv']['RMSSD_ms']}ms")
    print(f"方法: {args.method}")

    if not args.no_plot:
        png_path = plot(result, waveforms, Path(args.output) if args.output else Path(args.data_path).parent, session)
        print(f"图: {png_path}")

    out_p = Path(args.output) if args.output else Path(args.data_path).parent
    print(f"结果: {out_p / f'{session}_vital_signs.json'}")


if __name__ == "__main__":
    main()
