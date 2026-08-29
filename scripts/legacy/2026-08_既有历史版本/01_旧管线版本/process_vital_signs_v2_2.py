"""
v2.2: keep the v2.1 long-record pipeline, but add a MATLAB-style
respiration preprocessing branch and choose the better breath candidate.

Important:
- this is not a strict reproduction of the original MATLAB filter object,
  because `coe3.mat` is not yet available as Python-readable coefficients;
- instead, we approximate the MATLAB idea with:
  displacement -> first difference -> 5-point moving average -> band-pass
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal

from process_vital_signs_v2 import FS, WAVELENGTH_MM, _sos_bandpass
from process_vital_signs_v2_0 import (
    collect_npz_parts,
    accumulate_range_profile,
    select_bins_from_profile,
    estimate_freq_periodogram,
    detect_peaks_heart_lo,
    separate_vmd_heart_windowed,
    save_result,
    plot_result,
    save_range_fft_map,
    save_range_fft_channel_grid,
    _iter_selected_chunks,
    _as_range_cube,
)
from process_vital_signs_v2_1 import estimate_breath_rate_consensus


def _movmean(x: np.ndarray, win: int = 5) -> np.ndarray:
    if win <= 1 or len(x) < 3:
        return np.asarray(x, dtype=np.float64)
    kernel = np.ones(win, dtype=np.float64) / float(win)
    return np.convolve(np.asarray(x, dtype=np.float64), kernel, mode="same")


def _breath_remove_baseline(disp_br: np.ndarray) -> np.ndarray:
    """Remove slow linear baseline drift before respiration filtering."""
    disp_br = np.asarray(disp_br, dtype=np.float64)
    if disp_br.size < 4:
        return disp_br - np.mean(disp_br)
    return signal.detrend(disp_br, type="linear")


def _breath_preprocess_matlab_style(disp_br: np.ndarray) -> np.ndarray:
    """
    Approximate the MATLAB respiration front-end:
    unwrap-phase difference -> movmean(5) -> breath band-pass.

    Here we only have displacement, so we use:
    displacement difference -> movmean(5) -> band-pass
    """
    disp_br = _breath_remove_baseline(disp_br)
    diff_sig = np.diff(disp_br, prepend=disp_br[0])
    smooth_sig = _movmean(diff_sig, win=5)
    breath = _sos_bandpass(smooth_sig, 0.1, 0.5)
    return breath


def _breath_band_metrics(breath: np.ndarray) -> dict:
    freqs, pxx = signal.periodogram(breath, fs=FS, window="hann")
    mask = (freqs >= 0.1) & (freqs <= 0.5)
    if not np.any(mask):
        return {
            "top_hz": None,
            "top_power": 0.0,
            "median_power": 0.0,
            "snr_like": 0.0,
            "band_power": 0.0,
        }

    f_band = freqs[mask]
    p_band = pxx[mask]
    top_idx = int(np.argmax(p_band))
    top_power = float(p_band[top_idx])
    median_power = float(np.median(p_band)) if len(p_band) > 0 else 0.0
    snr_like = top_power / max(median_power, 1e-12)
    return {
        "top_hz": float(f_band[top_idx]),
        "top_power": top_power,
        "median_power": median_power,
        "snr_like": float(snr_like),
        "band_power": float(np.sum(p_band)),
    }


def _score_breath_candidate(
    breath: np.ndarray,
    br_freq_hz: float | None,
    bp: np.ndarray,
) -> tuple[float, dict]:
    metrics = _breath_band_metrics(breath)

    time_bpm = None
    if len(bp) >= 2:
        time_bpm = float(60.0 * FS / np.mean(np.diff(bp)))

    freq_bpm = float(br_freq_hz * 60.0) if br_freq_hz else None
    mismatch = abs(freq_bpm - time_bpm) if (freq_bpm is not None and time_bpm is not None) else 20.0

    # Lower roughness means the candidate is less jagged after filtering.
    roughness = float(np.std(np.diff(breath))) / max(float(np.std(breath)), 1e-8)
    peak_bonus = min(len(bp), 30) * 0.08
    score = metrics["snr_like"] - 0.8 * mismatch - 0.6 * roughness + peak_bonus
    if len(bp) < 2:
        score -= 12.0

    return float(score), {
        "score": round(float(score), 3),
        "time_bpm": round(time_bpm, 1) if time_bpm is not None else None,
        "freq_bpm": round(freq_bpm, 1) if freq_bpm is not None else None,
        "mismatch_bpm": round(float(mismatch), 1),
        "roughness": round(float(roughness), 3),
        "snr_like": round(float(metrics["snr_like"]), 3),
        "band_top_hz": round(float(metrics["top_hz"]), 4) if metrics["top_hz"] is not None else None,
        "n_peaks": int(len(bp)),
    }


def _select_breath_candidate(
    disp_br: np.ndarray,
) -> tuple[np.ndarray, float | None, np.ndarray, dict]:
    disp_br_detrended = _breath_remove_baseline(disp_br)

    breath_bp = _sos_bandpass(disp_br_detrended, 0.1, 0.5)
    br_freq_bp, bp_bp, info_bp = estimate_breath_rate_consensus(breath_bp)
    score_bp, score_info_bp = _score_breath_candidate(breath_bp, br_freq_bp, bp_bp)
    info_bp = {
        **info_bp,
        "source": "br_bin_bandpass",
        "branch": "baseline_bandpass",
        "baseline_removal": "linear_detrend",
        "selection_score": score_info_bp,
    }

    breath_mat = _breath_preprocess_matlab_style(disp_br)
    br_freq_mat, bp_mat, info_mat = estimate_breath_rate_consensus(breath_mat)
    score_mat, score_info_mat = _score_breath_candidate(breath_mat, br_freq_mat, bp_mat)
    info_mat = {
        **info_mat,
        "source": "br_bin_diff_movmean_bandpass",
        "branch": "matlab_style_preprocess",
        "baseline_removal": "linear_detrend",
        "selection_score": score_info_mat,
    }

    if score_mat > score_bp:
        chosen = "matlab_style_preprocess"
        breath, br_freq, bp, info = breath_mat, br_freq_mat, bp_mat, info_mat
    else:
        chosen = "baseline_bandpass"
        breath, br_freq, bp, info = breath_bp, br_freq_bp, bp_bp, info_bp

    info["candidate_compare"] = {
        "chosen_branch": chosen,
        "baseline_bandpass": score_info_bp,
        "matlab_style_preprocess": score_info_mat,
    }
    return breath, br_freq, bp, info


def select_separate_channels_bins(
    bin_power_acc: np.ndarray,
    iq_fd_sample: np.ndarray,
    n_frames_sample: int,
    channel_override: int | None = None,
) -> tuple[int, int, int, int, list[dict]]:
    summaries: list[dict] = []

    if channel_override is not None:
        channels = [int(channel_override)]
    else:
        channels = list(range(bin_power_acc.shape[1]))

    for ch in channels:
        br_bin, hr_bin, candidates = select_bins_from_profile(
            bin_power_acc, ch, iq_fd_sample, n_frames_sample
        )
        if not candidates:
            continue
        best_hr = max(candidates, key=lambda item: item[1])
        best_br = max(candidates, key=lambda item: item[3])
        summaries.append(
            {
                "channel": ch,
                "breath_bin": int(br_bin),
                "heart_bin": int(hr_bin),
                "best_hr_snr": float(best_hr[1]),
                "best_br_snr": float(best_br[2]),
                "best_br_score": float(best_br[3]),
                "best_br_phase_stability": float(best_br[4]),
                "n_candidates": int(len(candidates)),
            }
        )

    if not summaries:
        raise RuntimeError("No valid channel/bin candidates were found.")

    breath_choice = max(summaries, key=lambda item: item["best_br_score"])
    heart_choice = max(summaries, key=lambda item: item["best_hr_snr"])
    return (
        int(breath_choice["channel"]),
        int(breath_choice["breath_bin"]),
        int(heart_choice["channel"]),
        int(heart_choice["heart_bin"]),
        summaries,
    )


def extract_displacement_separate(
    npz_files: list[Path],
    br_ch: int,
    br_bin: int,
    hr_ch: int,
    hr_bin: int,
    frame_start: int | None = None,
    frame_end: int | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    from process_vital_signs_v2 import extract_displacement

    phase_br_chunks: list[np.ndarray] = []
    disp_hr_chunks: list[np.ndarray] = []
    n_total = 0

    for index, iq_td in enumerate(
        _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end),
        start=1,
    ):
        iq_fd = _as_range_cube(iq_td)
        n_local = iq_td.shape[0]

        phase_br_chunks.append(np.angle(iq_fd[:, br_bin, br_ch]).astype(np.float64))
        disp_hr_chunks.append(extract_displacement(iq_fd, hr_bin, hr_ch))
        n_total += n_local

        if index % 50 == 0:
            print(f"[pass2] {index} chunks processed, {n_total} frames extracted")

    if not phase_br_chunks or not disp_hr_chunks:
        raise RuntimeError("No displacement chunks were extracted.")

    phi_br = np.unwrap(np.concatenate(phase_br_chunks, axis=0))
    disp_br = WAVELENGTH_MM * phi_br / (4 * np.pi)
    return disp_br, np.concatenate(disp_hr_chunks), n_total


def analyze_displacement(
    disp_br: np.ndarray,
    disp_hr: np.ndarray,
    n_frames: int,
    method: str = "vmd_heart",
    session: str = "sub-sxq_ses-SART",
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    duration = n_frames / FS
    t = np.arange(n_frames) / FS

    breath, br_freq, bp, breath_sep = _select_breath_candidate(disp_br)

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
        gap = abs(br_freq_bpm - br_time_bpm)
        br_conf = "high" if gap <= 2.0 else ("medium" if gap <= 5.0 else "low")

    result = {
        "session": session,
        "version": "v2.2",
        "pipeline": "chunked_long_record_matlab_style_breath_compare",
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
    channel_override: int | None = None,
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
    best_ch_auto = int(np.argmax(channel_power))
    best_ch = int(channel_override) if channel_override is not None else best_ch_auto

    iq_sample = next(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), None)
    if iq_sample is None:
        raise RuntimeError("Selected frame range contains no data.")
    iq_fd_sample = _as_range_cube(iq_sample)

    br_ch, br_bin, hr_ch, hr_bin, channel_summaries = select_separate_channels_bins(
        bin_power_acc,
        iq_fd_sample,
        iq_sample.shape[0],
        channel_override=channel_override,
    )
    print(
        f"[bins] breath_ch={br_ch}, breath_bin={br_bin}, "
        f"heart_ch={hr_ch}, heart_bin={hr_bin}, auto_best_ch={best_ch_auto}"
    )

    disp_br, disp_hr, n_frames = extract_displacement_separate(
        npz_files,
        br_ch,
        br_bin,
        hr_ch,
        hr_bin,
        frame_start=frame_start,
        frame_end=frame_end,
    )
    result, waveforms = analyze_displacement(disp_br, disp_hr, n_frames, method=method, session=session)
    result["best_channel"] = br_ch
    result["auto_best_channel"] = best_ch_auto
    result["channels"] = {"breath": br_ch, "heart": hr_ch}
    result["channel_selection"] = channel_summaries
    result["bins"] = {"breath": br_bin, "heart": hr_bin}
    result["n_frames"] = n_frames

    save_result(result, waveforms, output_dir)
    plot_path = plot_result(result, waveforms, output_dir, breath_view_start_s=breath_view_start_s)
    range_fft_raw_path, range_fft_diag_path = save_range_fft_map(
        npz_files,
        output_dir,
        session=session,
        best_ch=br_ch,
        frame_start=frame_start,
        frame_end=frame_end,
    )
    range_fft_grid_raw_path, range_fft_grid_diag_path = save_range_fft_channel_grid(
        npz_files,
        output_dir,
        session=session,
        frame_start=frame_start,
        frame_end=frame_end,
    )
    print(f"[plot] {plot_path}")
    print(f"[range_fft_raw] {range_fft_raw_path}")
    print(f"[range_fft_diag] {range_fft_diag_path}")
    print(f"[range_fft_grid_raw] {range_fft_grid_raw_path}")
    print(f"[range_fft_grid_diag] {range_fft_grid_diag_path}")
    return result, waveforms


