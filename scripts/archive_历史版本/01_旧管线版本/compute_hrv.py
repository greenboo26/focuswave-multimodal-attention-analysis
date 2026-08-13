"""
compute_hrv.py — SXQ 全套心率变异性分析
=========================================
在 v8 心跳信号基础上做 IBI 清洗 + 时域/频域/非线性 HRV。

用法:
  cd 08_算法/scripts
  python compute_hrv.py

输出:
  output/06_SXQ-47min/v1/
    sub-sxq_ses-SART_mmwave_hrv.json
    sub-sxq_ses-SART_mmwave_hrv.png
"""

import json
import numpy as np
from pathlib import Path
from scipy import signal, interpolate

FS = 100.0

# ── 路径 ──
NPZ_PATH = Path(r"D:\Project\厚粲杯\08_算法\output\06_SXQ-47min\v1"
                r"\sub-sxq_ses-SART_mmwave_vital_signs.npz")
OUTPUT_DIR = NPZ_PATH.parent


def load_peaks():
    """加载心跳信号和峰值。"""
    d = np.load(NPZ_PATH)
    t = d['t']
    heartbeat = d['heartbeat']
    hp = d['heart_peaks']
    return t, heartbeat, hp


def clean_ibi(hp, fs=FS):
    """
    IBI 轻度清洗：仅移除生理范围外的 + 远离中位数 3×IQR 的极端值。
    返回清洗后的峰值索引和 IBI 序列。
    """
    ibi_raw = np.diff(hp) / fs * 1000  # ms

    # 仅过滤明确异常值
    q1, q3 = np.percentile(ibi_raw, [25, 75])
    iqr = q3 - q1
    lo = max(300, q1 - 3 * iqr)
    hi = min(2000, q3 + 3 * iqr)

    ok = (ibi_raw >= lo) & (ibi_raw <= hi)

    hp_clean = hp[np.concatenate([[True], ok])]
    ibi_clean = np.diff(hp_clean) / fs * 1000

    return hp_clean, ibi_clean, {
        "raw_n_peaks": len(hp),
        "clean_n_peaks": len(hp_clean),
        "removed_pct": round((1 - len(hp_clean) / len(hp)) * 100, 1),
        "bounds_ms": [round(lo, 1), round(hi, 1)],
        "raw_ibi_median_ms": round(float(np.median(ibi_raw)), 1),
    }


def time_domain_hrv(ibi_ms):
    """时域 HRV 指标。"""
    nn = np.diff(ibi_ms)  # successive differences

    result = {
        "mean_IBI_ms": round(float(np.mean(ibi_ms)), 1),
        "SDNN_ms": round(float(np.std(ibi_ms, ddof=1)), 1),
        "RMSSD_ms": round(float(np.sqrt(np.mean(nn ** 2))), 1),
        "pNN50_pct": round(float(np.mean(np.abs(nn) > 50) * 100), 1),
        "median_IBI_ms": round(float(np.median(ibi_ms)), 1),
        "n_beats": len(ibi_ms) + 1,
    }

    # 5-min segment SDANN
    fs_equiv = 1000 / np.mean(ibi_ms)  # approx Hz
    seg_len_beats = int(5 * 60 * fs_equiv)
    if seg_len_beats > 0 and len(ibi_ms) >= seg_len_beats:
        seg_means = []
        for start in range(0, len(ibi_ms) - seg_len_beats, seg_len_beats):
            seg_means.append(np.mean(ibi_ms[start:start + seg_len_beats]))
        if seg_means:
            result["SDANN_ms"] = round(float(np.std(seg_means, ddof=1)), 1)

    return result


def frequency_domain_hrv(hp_clean, t_total, fs=FS):
    """
    频域 HRV — 用 Lomb-Scargle（非均匀 IBIs）+ Welch PSD（心跳波形残差）。

    返回 VLF/LF/HF 功率和 LF/HF ratio。
    """
    # ── 方法 1: IBI 插值 + Welch ──
    ibi_t = hp_clean[1:] / fs  # IBI 对应的时间点（用后一个峰的时间）
    ibi_val = np.diff(hp_clean) / fs * 1000

    if len(ibi_val) < 10:
        return {"error": "insufficient beats for frequency analysis"}

    # 插值到均匀网格 (4 Hz, 标准 HRV 分析)
    fs_interp = 4.0
    t_interp = np.arange(ibi_t[0], ibi_t[-1], 1 / fs_interp)
    # 三次样条插值
    try:
        ibi_interp = interpolate.interp1d(
            ibi_t, ibi_val, kind='cubic',
            bounds_error=False, fill_value='extrapolate'
        )(t_interp)
    except Exception:
        # 如果三次样条失败，回退到线性
        ibi_interp = np.interp(t_interp, ibi_t, ibi_val)

    # 去趋势
    ibi_interp -= np.polyval(np.polyfit(t_interp, ibi_interp, 1), t_interp)

    # Welch PSD
    nperseg = min(256, len(ibi_interp) // 2)
    f_w, pxx_w = signal.welch(ibi_interp, fs=fs_interp, nperseg=nperseg,
                               window='hann')

    def band_power(f, pxx, lo, hi):
        mask = (f >= lo) & (f < hi)
        if not np.any(mask):
            return 0.0
        return float(np.trapezoid(pxx[mask], f[mask]))

    vlf_pow = band_power(f_w, pxx_w, 0.003, 0.04)
    lf_pow = band_power(f_w, pxx_w, 0.04, 0.15)
    hf_pow = band_power(f_w, pxx_w, 0.15, 0.4)
    total = vlf_pow + lf_pow + hf_pow
    lf_hf = lf_pow / hf_pow if hf_pow > 0 else None

    freq_result = {
        "VLF_ms2": round(vlf_pow, 2),
        "LF_ms2": round(lf_pow, 2),
        "HF_ms2": round(hf_pow, 2),
        "LF_HF_ratio": round(lf_hf, 2) if lf_hf else None,
        # 归一化单位
        "LF_nu": round(lf_pow / (lf_pow + hf_pow) * 100, 1) if (lf_pow + hf_pow) > 0 else None,
        "HF_nu": round(hf_pow / (lf_pow + hf_pow) * 100, 1) if (lf_pow + hf_pow) > 0 else None,
        "total_power_ms2": round(total, 2),
        "method": "IBI_interpolation_Welch",
        "note": "4Hz interpolation, detrended, Welch nperseg=256",
    }

    return freq_result


def nonlinear_hrv(ibi_ms):
    """非线性 HRV — Poincaré SD1/SD2。"""
    if len(ibi_ms) < 10:
        return {}

    x = ibi_ms[:-1]
    y = ibi_ms[1:]

    sd1 = np.std(y - x, ddof=1) / np.sqrt(2)
    sd2 = np.std(y + x, ddof=1) / np.sqrt(2)

    return {
        "SD1_ms": round(float(sd1), 1),
        "SD2_ms": round(float(sd2), 1),
        "SD1_SD2_ratio": round(float(sd1 / sd2), 2) if sd2 > 0 else None,
        "note": "Poincare plot: SD1=short-term, SD2=long-term variability",
    }


def plot_hrv(t, heartbeat, hp_clean, ibi_ms, freq_result, output_dir):
    """生成 HRV 综合图。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("HRV Analysis — sub-sxq SART 47min", fontsize=14)

    # ── (0,0): Heart waveform (first 30s) ──
    ax = axes[0, 0]
    n_show = min(int(30 * FS), len(t))
    ax.plot(t[:n_show], heartbeat[:n_show], 'r-', alpha=0.7, linewidth=0.5)
    hp_show = hp_clean[hp_clean < n_show]
    ax.plot(t[hp_show], heartbeat[hp_show], 'rx', markersize=5)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    ax.set_title("Heart waveform — first 30s")
    ax.grid(True, alpha=0.3)

    # ── (0,1): IBI time series ──
    ax = axes[0, 1]
    ibi_t = hp_clean[1:] / FS / 60  # minutes
    ax.plot(ibi_t, ibi_ms, 'b.-', alpha=0.5, markersize=2, linewidth=0.5)
    ax.axhline(np.mean(ibi_ms), color='orange', ls='--', alpha=0.7,
               label=f"mean={np.mean(ibi_ms):.0f}ms")
    ax.set_xlabel("Time (min)")
    ax.set_ylabel("IBI (ms)")
    ax.set_title(f"IBI time series ({len(ibi_ms)} beats)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── (0,2): Poincaré plot ──
    ax = axes[0, 2]
    if len(ibi_ms) >= 10:
        ax.scatter(ibi_ms[:-1], ibi_ms[1:], c='blue', alpha=0.3, s=5)
        sd1 = np.std(ibi_ms[1:] - ibi_ms[:-1], ddof=1) / np.sqrt(2)
        sd2 = np.std(ibi_ms[1:] + ibi_ms[:-1], ddof=1) / np.sqrt(2)
        m = np.mean(ibi_ms)
        ax.plot([m - sd2, m + sd2], [m - sd2, m + sd2], 'orange', lw=1.5,
                label=f"SD2={sd2:.0f}")
        ax.plot([m, m], [m - sd1, m + sd1], 'green', lw=1.5,
                label=f"SD1={sd1:.0f}")
        ax.plot([m - sd1, m + sd1], [m, m], 'green', lw=1.5)
        ax.set_xlim(m - 3*sd2, m + 3*sd2)
        ax.set_ylim(m - 3*sd2, m + 3*sd2)
        ax.legend()
    ax.set_xlabel("IBI(n) (ms)")
    ax.set_ylabel("IBI(n+1) (ms)")
    ax.set_title("Poincaré plot")
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    # ── (1,0): IBI histogram ──
    ax = axes[1, 0]
    ax.hist(ibi_ms, bins=60, color='steelblue', alpha=0.7, edgecolor='white')
    ax.axvline(np.mean(ibi_ms), color='red', ls='--',
               label=f"Mean={np.mean(ibi_ms):.0f}ms")
    ax.axvline(np.median(ibi_ms), color='orange', ls='--',
               label=f"Med={np.median(ibi_ms):.0f}ms")
    ax.set_xlabel("IBI (ms)")
    ax.set_ylabel("Count")
    ax.set_title("IBI distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── (1,1): IBI spectrum (Lomb-Scargle) ──
    ax = axes[1, 1]
    ibi_t_full = hp_clean[1:] / FS
    ibi_val_full = ibi_ms
    f_ls = np.linspace(0.003, 0.5, 500)
    try:
        pxx_ls = signal.lombscargle(ibi_t_full, ibi_val_full - np.mean(ibi_val_full),
                                    2 * np.pi * f_ls, normalize=True)
        ax.semilogy(f_ls, pxx_ls, 'navy')
        for band, lo, hi, color in [
            ('VLF', 0.003, 0.04, 'gray'),
            ('LF', 0.04, 0.15, 'blue'),
            ('HF', 0.15, 0.4, 'red'),
        ]:
            ax.axvspan(lo, hi, alpha=0.1, color=color, label=f"{band}")
        ax.legend(fontsize=8)
    except Exception as e:
        ax.text(0.5, 0.5, f"Lomb-Scargle failed: {e}",
                transform=ax.transAxes, ha='center')
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Normalized Power")
    ax.set_title("IBI spectrum (Lomb-Scargle)")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 0.5)

    # ── (1,2): HR trend (1-min windows) ──
    ax = axes[1, 2]
    window_min = 1.0
    window_beats = int(window_min * 60 / (np.mean(ibi_ms) / 1000))
    if window_beats >= 5 and len(ibi_ms) >= window_beats:
        hr_smooth = []
        t_smooth = []
        for i in range(0, len(ibi_ms) - window_beats, max(1, window_beats // 4)):
            win = ibi_ms[i:i + window_beats]
            hr_smooth.append(60000 / np.mean(win))
            t_smooth.append(ibi_t[i + window_beats // 2])
        ax.plot(t_smooth, hr_smooth, 'r-', alpha=0.8, linewidth=0.8)
        ax.axhline(np.mean(hr_smooth), color='orange', ls='--',
                   label=f"Mean={np.mean(hr_smooth):.0f} BPM")
        ax.legend()
    ax.set_xlabel("Time (min)")
    ax.set_ylabel("HR (BPM)")
    ax.set_title("HR trend (1-min sliding windows)")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = output_dir / "sub-sxq_ses-SART_mmwave_hrv.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 55)
    print("  SXQ HRV Analysis")
    print("=" * 55)

    # ── 加载 ──
    t, heartbeat, hp_raw = load_peaks()
    print(f"\n[LOAD] {len(hp_raw)} raw peaks, "
          f"duration={t[-1]/60:.1f}min")

    # ── IBI 清洗 ──
    hp_clean, ibi_ms, clean_info = clean_ibi(hp_raw)
    print(f"\n── IBI 清洗 ──")
    print(f"  原始峰数: {clean_info['raw_n_peaks']}")
    print(f"  清洗后: {clean_info['clean_n_peaks']} "
          f"(-{clean_info['removed_pct']}%)")
    print(f"  原始 IBI 中位数: {clean_info['raw_ibi_median_ms']} ms")

    # ── 时域 HRV ──
    td = time_domain_hrv(ibi_ms)
    print(f"\n── 时域 HRV ──")
    print(f"  Mean IBI:  {td['mean_IBI_ms']} ms")
    print(f"  SDNN:      {td['SDNN_ms']} ms")
    print(f"  RMSSD:     {td['RMSSD_ms']} ms")
    print(f"  pNN50:     {td['pNN50_pct']} %")
    if 'SDANN_ms' in td:
        print(f"  SDANN:     {td['SDANN_ms']} ms")

    # ── 频域 HRV ──
    fd = frequency_domain_hrv(hp_clean, t[-1])
    print(f"\n── 频域 HRV ──")
    if 'error' in fd:
        print(f"  ERROR: {fd['error']}")
    else:
        print(f"  VLF:       {fd['VLF_ms2']} ms²")
        print(f"  LF:        {fd['LF_ms2']} ms²")
        print(f"  HF:        {fd['HF_ms2']} ms²")
        print(f"  LF/HF:     {fd['LF_HF_ratio']}")
        print(f"  LF nu:     {fd['LF_nu']}")
        print(f"  HF nu:     {fd['HF_nu']}")
        print(f"  Total:     {fd['total_power_ms2']} ms²")

    # ── 非线性 HRV ──
    nl = nonlinear_hrv(ibi_ms)
    print(f"\n── 非线性 HRV ──")
    print(f"  SD1:       {nl['SD1_ms']} ms (短程变异)")
    print(f"  SD2:       {nl['SD2_ms']} ms (长程变异)")
    print(f"  SD1/SD2:   {nl['SD1_SD2_ratio']}")

    # ── 汇总保存 ──
    hrv_result = {
        "session": "sub-sxq_ses-SART",
        "duration_min": round(t[-1] / 60, 1),
        "cleaning": clean_info,
        "time_domain": td,
        "frequency_domain": fd,
        "nonlinear": nl,
    }

    json_path = OUTPUT_DIR / "sub-sxq_ses-SART_mmwave_hrv.json"
    json_path.write_text(
        json.dumps(hrv_result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n  [json] {json_path}")

    # ── 绘图 ──
    png_path = plot_hrv(t, heartbeat, hp_clean, ibi_ms, fd, OUTPUT_DIR)
    print(f"  [plot] {png_path}")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
