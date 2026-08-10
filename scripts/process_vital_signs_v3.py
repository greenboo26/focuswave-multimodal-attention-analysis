"""
Vital-sign extraction v3.

This version keeps baseline respiration extraction and only applies VMD to the
heart pipeline. The goal is to make heart peak detection and IBI estimation
more stable without coupling respiration and heartbeat into the same VMD step.
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
    detect_peaks_breath,
)


def _load_vmd():
    try:
        from sktime.libs.vmdpy import VMD
        return VMD, "sktime.libs.vmdpy"
    except Exception:
        from vmdpy import VMD
        return VMD, "vmdpy"


def _heart_mode_score(mode_signal, freqs, hr_mask, hr_freq_hint):
    _, pxx = signal.periodogram(mode_signal, fs=FS, window="hann")
    band_energy = float(np.sum(pxx[hr_mask]))
    if band_energy <= 0:
        return -np.inf, None

    dom_idx = np.argmax(pxx[hr_mask])
    dom_freq = float(freqs[hr_mask][dom_idx])
    if not 0.8 <= dom_freq <= 2.5:
        return -np.inf, dom_freq

    score = band_energy
    if hr_freq_hint is not None:
        score /= (1.0 + abs(dom_freq - hr_freq_hint))
    return score, dom_freq


def separate_vmd_heart_only(disp_hr, hr_freq_hint=None):
    """
    Use VMD only on the heart-bin displacement.

    Returns
    -------
    heartbeat : np.ndarray
    info : dict
    """
    if len(disp_hr) < 200:
        return _sos_bandpass(disp_hr, 0.8, 2.5), {
            "method": "bp_fallback_short_signal",
            "reason": "n_frames_lt_200",
        }

    VMD, backend = _load_vmd()
    u, _, omega = VMD(disp_hr, alpha=1000, tau=0, K=4, DC=False, init=1, tol=1e-6)

    freqs = np.fft.rfftfreq(len(disp_hr), d=1 / FS)
    hr_mask = (freqs >= 0.8) & (freqs <= 2.5)
    best_idx = None
    best_score = -np.inf
    best_freq = None
    mode_summary = []

    for k in range(u.shape[0]):
        score, dom_freq = _heart_mode_score(u[k], freqs, hr_mask, hr_freq_hint)
        center_freq = float(omega[-1, k] * FS)
        mode_summary.append(
            {
                "mode": int(k),
                "center_freq_hz": round(center_freq, 3),
                "dom_freq_hz": round(dom_freq, 3) if dom_freq is not None else None,
                "score": round(float(score), 3) if np.isfinite(score) else None,
            }
        )
        if score > best_score:
            best_score = score
            best_idx = k
            best_freq = dom_freq

    if best_idx is None or not np.isfinite(best_score):
        return _sos_bandpass(disp_hr, 0.8, 2.5), {
            "method": "bp_fallback_no_valid_mode",
            "reason": "no_valid_heart_mode",
            "backend": backend,
            "modes": mode_summary,
        }

    heartbeat = u[best_idx]
    if best_freq is not None:
        lo = max(0.8, best_freq - 0.35)
        hi = min(2.5, best_freq + 0.35)
        if hi > lo:
            heartbeat = _sos_bandpass(heartbeat, lo, hi)

    return heartbeat, {
        "method": "vmd_heart_only",
        "backend": backend,
        "heart_mode": int(best_idx),
        "heart_dom_freq_hz": round(float(best_freq), 3) if best_freq is not None else None,
        "modes": mode_summary,
    }


def _artifact_stem(session, method):
    return f"{session}_v3_{method}_vital_signs"


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

    breath = _sos_bandpass(disp_br, 0.1, 0.5)
    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)

    f, pxx_b = signal.periodogram(breath, fs=FS, window="hann")
    _, pxx_h = signal.periodogram(heart_bp, fs=FS, window="hann")
    br_mask = (f >= 0.1) & (f <= 0.5)
    hr_mask = (f >= 0.8) & (f <= 2.5)
    br_freq = f[br_mask][np.argmax(pxx_b[br_mask])] if br_mask.any() else None
    hr_freq = f[hr_mask][np.argmax(pxx_h[hr_mask])] if hr_mask.any() else None

    if method == "vmd_heart":
        heartbeat, sep_info = separate_vmd_heart_only(disp_hr, hr_freq_hint=hr_freq)
        heart_pd = heartbeat
    else:
        heartbeat = heart_bp
        sep_info = {
            "method": "bp_dual_bin",
            "breath_source": "br_bin_bandpass",
            "heart_source": "hr_bin_bandpass",
        }
        heart_pd = heart_bp

    hp = detect_peaks_heart(heart_pd)
    bp = detect_peaks_breath(breath, 1.5)

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
                "note": "Time-domain HRV only. Interpret cautiously before reference validation.",
            }

    result = {
        "session": session,
        "version": "v3",
        "duration_s": round(duration, 1),
        "frame_rate_hz": round(n_frames / duration, 1),
        "method": method,
        "separation": sep_info,
        "best_channel": int(best_ch),
        "bins": {"breath": int(br_bin), "heart": int(hr_bin)},
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
    n_frames = len(t)
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
    parser = argparse.ArgumentParser(description="Vital-sign extraction v3")
    parser.add_argument("data_path", help="Path to datacube.bin or npz")
    parser.add_argument(
        "--method",
        "-m",
        choices=["bp", "vmd", "vmd_heart"],
        default="bp",
        help="bp=baseline dual-bin bandpass; vmd_heart=VMD for heart only",
    )
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--no-plot", action="store_true", help="Skip plot generation")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else None
    result, waveforms = analyze(args.data_path, method=args.method, output_dir=out_dir)
    session = result["session"]

    print(f"\n[{result['method']}] {session} ({result['duration_s']}s)")
    print(f"{'metric':<12} {'freq':>10} {'time':>10}")
    print("-" * 36)
    hr = result["heart_rate"]
    br = result["breath_rate"]
    print(f"{'HR':<12} {str(hr['freq_bpm'])+' BPM' if hr['freq_bpm'] else 'N/A':>10} {str(hr['time_bpm'])+' BPM' if hr['time_bpm'] else 'N/A':>10}")
    print(f"{'BR':<12} {str(br['freq_bpm'])+' BPM' if br['freq_bpm'] else 'N/A':>10} {str(br['time_bpm'])+' BPM' if br['time_bpm'] else 'N/A':>10}")
    print(f"{'breath_ptp':<12} {result['displacement_mm']['breath_ptp']:.2f} mm")
    print(f"{'heart_ptp':<12} {result['displacement_mm']['heart_ptp']:.2f} mm")
    if result["hrv"]:
        print(f"SDNN={result['hrv']['SDNN_ms']} ms  RMSSD={result['hrv']['RMSSD_ms']} ms")
    print(f"separation={result['separation']['method']}")

    output_dir = Path(args.output) if args.output else Path(args.data_path).parent
    if not args.no_plot:
        png_path = plot(result, waveforms, output_dir, session)
        print(f"plot: {png_path}")

    stem = _artifact_stem(session, result["method"])
    print(f"json: {output_dir / f'{stem}.json'}")


if __name__ == "__main__":
    main()
