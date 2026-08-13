"""
v2.1: keep the v2.0 pipeline, but make breath-rate estimation more conservative.

Main change:
- use time-domain breath peak intervals as a prior,
- choose spectrum peaks with harmonic checks,
- re-run peak detection with the selected frequency hint.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal

from process_vital_signs_v2 import FS, _sos_bandpass
from process_vital_signs_v2_0 import (
    collect_npz_parts,
    accumulate_range_profile,
    select_bins_from_profile,
    extract_displacement_all,
    estimate_freq_periodogram,
    detect_peaks_heart_lo,
    separate_vmd_heart_windowed,
    save_result,
    plot_result,
    _as_range_cube,
)
from process_vital_signs_v5 import detect_peaks_breath_robust


def _breath_candidates_from_spectrum(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    freqs, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (freqs >= 0.1) & (freqs <= 0.5)
    f_band = freqs[mask]
    p_band = pxx[mask]
    if len(f_band) == 0:
        return f_band, p_band, np.array([], dtype=int)
    peak_idx, _ = signal.find_peaks(p_band, distance=max(1, len(p_band) // 25))
    if len(peak_idx) == 0:
        peak_idx = np.array([int(np.argmax(p_band))], dtype=int)
    return f_band, p_band, peak_idx


def estimate_breath_rate_consensus(breath: np.ndarray) -> tuple[float | None, np.ndarray, dict]:
    bp_initial = detect_peaks_breath_robust(breath, lo_bpm=6, hi_bpm=30, br_freq_hint=None)
    br_time_hz = None
    if len(bp_initial) >= 2:
        br_time_hz = float(1.0 / np.mean(np.diff(bp_initial) / FS))

    f_band, p_band, peak_idx = _breath_candidates_from_spectrum(breath)
    if len(f_band) == 0:
        return None, bp_initial, {"method": "consensus_breath", "reason": "empty_band"}

    candidate_freqs = f_band[peak_idx]
    candidate_powers = p_band[peak_idx]
    order = np.argsort(candidate_powers)[::-1]
    candidate_freqs = candidate_freqs[order]
    candidate_powers = candidate_powers[order]

    chosen_hz = None
    reason = "top_spectral_peak"

    if br_time_hz is not None and len(candidate_freqs) > 0:
        close_mask = np.abs(candidate_freqs - br_time_hz) <= 0.08
        if np.any(close_mask):
            local_idx = np.argmax(candidate_powers[close_mask])
            chosen_hz = float(candidate_freqs[close_mask][local_idx])
            reason = "closest_to_time_rate"

    if chosen_hz is None and len(candidate_freqs) > 0:
        top_hz = float(candidate_freqs[0])
        top_power = float(candidate_powers[0])
        if top_hz >= 0.22:
            half_hz = top_hz / 2.0
            half_idx = int(np.argmin(np.abs(f_band - half_hz)))
            half_power = float(p_band[half_idx])
            if abs(f_band[half_idx] - half_hz) <= 0.04 and half_power >= 0.35 * top_power:
                chosen_hz = float(f_band[half_idx])
                reason = "half_harmonic_selected"

    if chosen_hz is None:
        chosen_hz = float(candidate_freqs[0]) if len(candidate_freqs) > 0 else estimate_freq_periodogram(breath, 0.1, 0.5)

    bp_final = detect_peaks_breath_robust(breath, lo_bpm=6, hi_bpm=30, br_freq_hint=chosen_hz)
    return chosen_hz, bp_final, {
        "method": "consensus_breath",
        "reason": reason,
        "time_rate_hz": round(br_time_hz, 4) if br_time_hz is not None else None,
        "spectral_top_hz": round(float(candidate_freqs[0]), 4) if len(candidate_freqs) > 0 else None,
    }


def analyze_displacement(
    disp_br: np.ndarray,
    disp_hr: np.ndarray,
    n_frames: int,
    method: str = "vmd_heart",
    session: str = "sub-sxq_ses-SART",
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    duration = n_frames / FS
    t = np.arange(n_frames) / FS

    breath = _sos_bandpass(disp_br, 0.1, 0.5)
    br_freq, bp, breath_sep = estimate_breath_rate_consensus(breath)
    breath_sep.update({"source": "br_bin_bandpass"})

    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)
    hr_freq_bp = estimate_freq_periodogram(heart_bp, 0.8, 2.5)
    if method == "vmd_heart":
        heartbeat, heart_sep = separate_vmd_heart_windowed(disp_hr, hr_freq_hint=hr_freq_bp)
        heart_pd = heartbeat
        hr_freq = estimate_freq_periodogram(heartbeat, 0.8, 2.5)
    else:
        heartbeat = heart_bp
        heart_pd = heart_bp
        hr_freq = hr_freq_bp
        heart_sep = {"method": "bp_heart", "source": "hr_bin_bandpass"}

    hp = detect_peaks_heart_lo(heart_pd, lo_bpm=40, hi_bpm=150)

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

    br_time_bpm = round(float(60 * FS / np.mean(np.diff(bp))), 1) if len(bp) >= 2 else None
    br_freq_bpm = round(float(br_freq * 60), 1) if br_freq else None
    br_conf = None
    if br_time_bpm is not None and br_freq_bpm is not None:
        br_conf = "high" if abs(br_freq_bpm - br_time_bpm) <= 2.0 else ("medium" if abs(br_freq_bpm - br_time_bpm) <= 5.0 else "low")

    result = {
        "session": session,
        "version": "v2.1",
        "pipeline": "chunked_long_record_consensus_breath",
        "duration_s": round(duration, 1),
        "frame_rate_hz": round(n_frames / duration, 1) if duration > 0 else FS,
        "method": method,
        "separation": {"breath": breath_sep, "heart": heart_sep},
        "heart_rate": {
            "freq_bpm": round(float(hr_freq * 60), 1) if hr_freq else None,
            "time_bpm": round(float(60 * FS / np.mean(np.diff(hp))), 1) if len(hp) >= 2 else None,
            "n_peaks": int(len(hp)),
        },
        "breath_rate": {
            "freq_bpm": br_freq_bpm,
            "time_bpm": br_time_bpm,
            "n_peaks": int(len(bp)),
            "confidence": br_conf,
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


def analyze_long_record(
    parts_dir: Path,
    output_dir: Path,
    session: str = "sub-sxq_ses-SART",
    method: str = "vmd_heart",
    pattern: str = "sub-SXQ_mmwave_datacube_part*.npz",
    breath_view_start_s: float | None = None,
    frame_start: int | None = None,
    frame_end: int | None = None,
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    npz_files = collect_npz_parts(parts_dir, pattern=pattern)
    if not npz_files:
        raise FileNotFoundError(f"No part files matched under: {parts_dir}")

    print(f"[info] found {len(npz_files)} chunk files")
    print(f"[info] parts dir: {parts_dir}")
    print(f"[info] output dir: {output_dir}")

    channel_power, bin_power_acc, _ = accumulate_range_profile(
        npz_files, frame_start=frame_start, frame_end=frame_end
    )
    best_ch = int(np.argmax(channel_power))

    from process_vital_signs_v2_0 import _iter_selected_chunks

    iq_sample = next(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), None)
    if iq_sample is None:
        raise RuntimeError("Selected frame range contains no data.")
    iq_fd_sample = _as_range_cube(iq_sample)

    br_bin, hr_bin, candidates = select_bins_from_profile(
        bin_power_acc, best_ch, iq_fd_sample, iq_sample.shape[0]
    )
    print(f"[bins] best_ch={best_ch}, breath_bin={br_bin}, heart_bin={hr_bin}, candidates={len(candidates)}")

    disp_br, disp_hr, n_frames = extract_displacement_all(
        npz_files,
        best_ch,
        br_bin,
        hr_bin,
        frame_start=frame_start,
        frame_end=frame_end,
    )
    result, waveforms = analyze_displacement(disp_br, disp_hr, n_frames, method=method, session=session)
    result["best_channel"] = best_ch
    result["bins"] = {"breath": br_bin, "heart": hr_bin}
    result["n_frames"] = n_frames

    save_result(result, waveforms, output_dir)
    plot_path = plot_result(result, waveforms, output_dir, breath_view_start_s=breath_view_start_s)
    print(f"[plot] {plot_path}")
    return result, waveforms
