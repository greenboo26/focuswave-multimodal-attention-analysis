"""
Vital-sign extraction v7.

Based on v5:
- keep the validated heart-only VMD branch
- add wavelet denoising when PyWavelets is available
- add STFT-based frequency guidance for respiration / heartbeat estimation

This is an experimental branch for the "EMD / wavelet / time-frequency"
improvement line, implemented here with wavelet + time-frequency first.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

from process_vital_signs_v2 import (
    FS,
    load_data,
    range_fft,
    select_bins,
    extract_displacement,
    _sos_bandpass,
    detect_peaks_heart,
)
from process_vital_signs_v3 import separate_vmd_heart_only
from process_vital_signs_v5 import detect_peaks_breath_robust


def _artifact_stem(session, method):
    return f"{session}_v7_{method}_vital_signs"


def _load_pywt():
    try:
        import pywt
        return pywt
    except Exception:
        return None


def wavelet_denoise_signal(x, wavelet="db4", level=None):
    """
    Wavelet denoising with a universal threshold.

    If PyWavelets is not available, return the original signal unchanged.
    """
    pywt = _load_pywt()
    if pywt is None:
        return x.copy(), {"enabled": False, "reason": "pywt_not_installed"}

    x = np.asarray(x, dtype=float)
    max_level = pywt.dwt_max_level(len(x), pywt.Wavelet(wavelet).dec_len)
    if max_level < 1:
        return x.copy(), {"enabled": False, "reason": "signal_too_short"}
    if level is None:
        level = min(3, max_level)

    coeffs = pywt.wavedec(x, wavelet, level=level, mode="symmetric")
    detail = coeffs[-1]
    sigma = np.median(np.abs(detail)) / 0.6745 if len(detail) else 0.0
    uthresh = sigma * np.sqrt(2 * np.log(max(len(x), 2)))
    denoised_coeffs = [coeffs[0]]
    for c in coeffs[1:]:
        denoised_coeffs.append(pywt.threshold(c, value=uthresh, mode="soft"))
    x_hat = pywt.waverec(denoised_coeffs, wavelet, mode="symmetric")
    x_hat = x_hat[: len(x)]
    return x_hat, {
        "enabled": True,
        "wavelet": wavelet,
        "level": int(level),
        "threshold": float(uthresh),
    }


def estimate_freq_stft(x, lo_hz, hi_hz):
    """
    Estimate a dominant frequency in a band using STFT / spectrogram.
    """
    x = np.asarray(x, dtype=float)
    if len(x) < 32:
        return None

    nperseg = min(256, len(x))
    if nperseg < 32:
        return None
    noverlap = nperseg // 2
    f, _, sxx = signal.spectrogram(
        x,
        fs=FS,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        detrend=False,
        scaling="density",
        mode="magnitude",
    )
    mask = (f >= lo_hz) & (f <= hi_hz)
    if not np.any(mask):
        return None
    band = sxx[mask]
    if band.size == 0:
        return None
    dom_idx = np.argmax(band, axis=0)
    dom_freqs = f[mask][dom_idx]
    if len(dom_freqs) == 0:
        return None
    return float(np.median(dom_freqs))


def estimate_freq_periodogram(x, lo_hz, hi_hz):
    f, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (f >= lo_hz) & (f <= hi_hz)
    if not np.any(mask):
        return None
    return float(f[mask][np.argmax(pxx[mask])])


def blend_freq_hint(freq_a, freq_b):
    if freq_a is None:
        return freq_b
    if freq_b is None:
        return freq_a
    return float(0.6 * freq_a + 0.4 * freq_b)


def analyze(data_path, method="bp", output_dir=None):
    data_path = Path(data_path)
    session = data_path.stem.replace("_datacube", "").replace("_vital_signs", "")
    method = "vmd_heart" if method == "vmd" else method

    if output_dir is None:
        output_dir = data_path.parent

    iq_td = load_data(data_path)
    if iq_td.ndim == 2:
        iq_td = iq_td[:, :, None]
    iq_fd = range_fft(iq_td)
    n_frames = iq_fd.shape[0]
    duration = n_frames / FS

    best_ch, br_bin, hr_bin = select_bins(iq_fd, n_frames)

    disp_br = extract_displacement(iq_fd, br_bin, best_ch)
    disp_hr = extract_displacement(iq_fd, hr_bin, best_ch)

    breath_raw = _sos_bandpass(disp_br, 0.1, 0.5)
    breath, breath_wavelet_info = wavelet_denoise_signal(breath_raw, wavelet="db4")

    heart_bp_raw = _sos_bandpass(disp_hr, 0.8, 2.5)
    heart_bp, heart_wavelet_info = wavelet_denoise_signal(heart_bp_raw, wavelet="db4")

    br_freq_pd = estimate_freq_periodogram(breath, 0.1, 0.5)
    br_freq_tf = estimate_freq_stft(breath, 0.1, 0.5)
    br_freq = blend_freq_hint(br_freq_pd, br_freq_tf)

    hr_freq_pd = estimate_freq_periodogram(heart_bp, 0.8, 2.5)
    hr_freq_tf = estimate_freq_stft(heart_bp, 0.8, 2.5)
    hr_freq = blend_freq_hint(hr_freq_pd, hr_freq_tf)

    if method == "vmd_heart":
        heartbeat_raw, sep_info = separate_vmd_heart_only(disp_hr, hr_freq_hint=hr_freq)
        heartbeat, heart_vmd_wavelet_info = wavelet_denoise_signal(heartbeat_raw, wavelet="db4")
        hr_freq_pd = estimate_freq_periodogram(heartbeat, 0.8, 2.5)
        hr_freq_tf = estimate_freq_stft(heartbeat, 0.8, 2.5)
        hr_freq = blend_freq_hint(hr_freq_pd, hr_freq_tf)
        if hr_freq is not None:
            lo = max(0.8, hr_freq - 0.35)
            hi = min(2.5, hr_freq + 0.35)
            if hi > lo:
                heart_pd = _sos_bandpass(heartbeat, lo, hi)
            else:
                heart_pd = heartbeat
        else:
            heart_pd = heartbeat
        heart_wavelet_used = heart_vmd_wavelet_info
    else:
        heartbeat = heart_bp
        heart_pd = heart_bp
        sep_info = {
            "method": "bp_dual_bin",
            "breath_source": "br_bin_bandpass_wavelet",
            "heart_source": "hr_bin_bandpass_wavelet",
            "breath_cycle_detector": "v5_peak_detector_with_tf_hint",
        }
        heart_wavelet_used = heart_wavelet_info

    hp = detect_peaks_heart(heart_pd)
    bp = detect_peaks_breath_robust(breath, lo_bpm=6, hi_bpm=30, br_freq_hint=br_freq)

    hrv = {}
    if len(hp) >= 4:
        ibi = np.diff(hp) / FS * 1000
        ibi_clean = ibi[(ibi >= 300) & (ibi <= 2000)]
        if len(ibi_clean) >= 4:
            hrv = {
                "SDNN_ms": round(float(np.std(ibi_clean, ddof=1)), 1),
                "RMSSD_ms": round(float(np.sqrt(np.mean(np.diff(ibi_clean) ** 2))), 1),
                "mean_IBI_ms": round(float(np.mean(ibi_clean)), 1),
                "note": "Time-domain HRV only. Interpret cautiously before reference validation.",
            }

    result = {
        "session": session,
        "version": "v7",
        "duration_s": round(duration, 1),
        "frame_rate_hz": round(n_frames / duration, 1),
        "method": method,
        "separation": sep_info,
        "best_channel": int(best_ch),
        "bins": {"breath": int(br_bin), "heart": int(hr_bin)},
        "frequency_hints_hz": {
            "breath_periodogram": round(br_freq_pd, 3) if br_freq_pd is not None else None,
            "breath_stft": round(br_freq_tf, 3) if br_freq_tf is not None else None,
            "heart_periodogram": round(hr_freq_pd, 3) if hr_freq_pd is not None else None,
            "heart_stft": round(hr_freq_tf, 3) if hr_freq_tf is not None else None,
        },
        "wavelet": {
            "breath": breath_wavelet_info,
            "heart": heart_wavelet_used,
        },
        "heart_rate": {
            "freq_bpm": round(float(hr_freq * 60), 1) if hr_freq is not None else None,
            "time_bpm": round(float(60 * FS / np.mean(np.diff(hp))), 1) if len(hp) >= 2 else None,
            "n_peaks": int(len(hp)),
        },
        "breath_rate": {
            "freq_bpm": round(float(br_freq * 60), 1) if br_freq is not None else None,
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

    stem = _artifact_stem(session, method)
    json_path = output_dir / f"{stem}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    npz_path = output_dir / f"{stem}.npz"
    np.savez(
        npz_path,
        t=np.arange(n_frames) / FS,
        breath=breath,
        heartbeat=heartbeat,
        heart_peaks=hp,
        breath_peaks=bp,
        chest_bin=br_bin,
        heart_bin=hr_bin,
        best_ch=best_ch,
    )

    return result, (
        np.arange(n_frames) / FS,
        breath,
        heartbeat,
        hp,
        bp,
        iq_fd,
        best_ch,
        br_bin,
        hr_bin,
        stem,
    )


def plot(result, waveforms, output_dir, session):
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    t, breath, heartbeat, hp, bp, iq_fd, best_ch, br_bin, hr_bin, stem = waveforms
    duration = result["duration_s"]
    method = result["method"]

    fig, axes = plt.subplots(3, 2, figsize=(16, 10))
    fig.suptitle(f"Vital signs analysis - {session} ({duration}s) [{method}]", fontsize=14)

    ax = axes[0, 0]
    rp = np.mean(np.abs(iq_fd) ** 2, axis=(0, 2))
    ax.plot(rp)
    ax.axvline(br_bin, color="g", ls="--", alpha=0.5, label=f"breath bin {br_bin}")
    ax.axvline(hr_bin, color="r", ls="--", alpha=0.5, label=f"heart bin {hr_bin}")
    ax.set_xlabel("range bin")
    ax.set_ylabel("power")
    ax.set_title("Range profile")
    ax.legend()
    ax.set_xlim(0, 128)

    ax = axes[0, 1]
    n_disp = min(1000, len(t))
    ax.plot(t[:n_disp], extract_displacement(iq_fd, br_bin, best_ch)[:n_disp], alpha=0.7, label="breath-bin disp")
    ax.plot(t[:n_disp], extract_displacement(iq_fd, hr_bin, best_ch)[:n_disp], alpha=0.7, label="heart-bin disp")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("mm")
    ax.set_title("Raw displacement (first 10 s)")
    ax.legend()

    ax = axes[1, 0]
    ax.plot(t, breath, "g-", alpha=0.8)
    if len(bp) > 0:
        ax.plot(t[bp], breath[bp], "gx", markersize=5)
    ax.set_xlim(0, min(30, duration))
    ax.set_xlabel("time (s)")
    ax.set_ylabel("mm")
    br_val = result["breath_rate"]["time_bpm"] or result["breath_rate"]["freq_bpm"] or 0
    ax.set_title(f"Breath waveform ({br_val} BPM)")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.plot(t, heartbeat, "r-", alpha=0.8)
    if len(hp) > 0:
        ax.plot(t[hp], heartbeat[hp], "rx", markersize=4)
    ax.set_xlim(max(0, duration - 20), duration)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("mm")
    hr_val = result["heart_rate"]["time_bpm"] or result["heart_rate"]["freq_bpm"] or 0
    ax.set_title(f"Heart waveform ({hr_val} BPM, {result['heart_rate']['n_peaks']} peaks)")
    ax.grid(True, alpha=0.3)

    ax = axes[2, 0]
    f_b, pxx_b = signal.periodogram(breath, fs=FS, window="hann")
    ax.plot(f_b, pxx_b, "g-")
    ax.set_xlim(0, 1)
    ax.set_xlabel("freq (Hz)")
    ax.set_ylabel("power")
    ax.set_title("Breath spectrum")
    for lim in [0.1, 0.5]:
        ax.axvline(lim, color="gray", ls=":", alpha=0.5)

    ax = axes[2, 1]
    f_h, pxx_h = signal.periodogram(heartbeat, fs=FS, window="hann")
    ax.plot(f_h, pxx_h, "r-")
    ax.set_xlim(0, 4)
    ax.set_xlabel("freq (Hz)")
    ax.set_ylabel("power")
    ax.set_title("Heart spectrum")
    for lim in [0.8, 2.5]:
        ax.axvline(lim, color="gray", ls=":", alpha=0.5)

    plt.tight_layout()
    png_path = output_dir / f"{stem}.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def main():
    parser = argparse.ArgumentParser(description="Vital-sign extraction v7")
    parser.add_argument("data_path", help="Path to datacube.bin or npz")
    parser.add_argument(
        "--method",
        "-m",
        choices=["bp", "vmd", "vmd_heart"],
        default="bp",
        help="bp=baseline; vmd_heart=VMD for heart only",
    )
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--no-plot", action="store_true", help="Skip plot generation")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else None
    result, waveforms = analyze(args.data_path, method=args.method, output_dir=out_dir)

    print(f"\n[{result['method']}] {result['session']} ({result['duration_s']}s)")
    print(f"{'metric':<12} {'freq':>10} {'time':>10}")
    print("-" * 36)
    hr = result["heart_rate"]
    br = result["breath_rate"]
    print(f"{'HR':<12} {str(hr['freq_bpm'])+' BPM' if hr['freq_bpm'] else 'N/A':>10} {str(hr['time_bpm'])+' BPM' if hr['time_bpm'] else 'N/A':>10}")
    print(f"{'BR':<12} {str(br['freq_bpm'])+' BPM' if br['freq_bpm'] else 'N/A':>10} {str(br['time_bpm'])+' BPM' if br['time_bpm'] else 'N/A':>10}")

    output_dir = Path(args.output) if args.output else Path(args.data_path).parent
    if not args.no_plot:
        png_path = plot(result, waveforms, output_dir, result["session"])
        print(f"plot: {png_path}")

    stem = _artifact_stem(result["session"], result["method"])
    print(f"json: {output_dir / f'{stem}.json'}")


if __name__ == "__main__":
    main()


