"""
v2.4: keep the stable v2.3 pipeline, but strengthen the respiration side with:
1. stronger baseline removal,
2. local 3-bin fusion around the chosen breath bin,
3. explicit breath-quality metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import signal

from process_vital_signs_v2 import FS, WAVELENGTH_MM, _sos_bandpass, extract_displacement
from process_vital_signs_v2_0 import (
    _as_range_cube,
    _phase_stability_score,
    accumulate_range_profile,
    _iter_selected_chunks,
    collect_npz_parts,
    detect_peaks_heart_lo,
    estimate_freq_periodogram,
    plot_result,
    save_range_fft_channel_grid,
    save_range_fft_map,
    save_result,
    separate_vmd_heart_windowed,
)
from process_vital_signs_v2_1 import estimate_breath_rate_consensus
from process_vital_signs_v2_2 import (
    _movmean,
    _score_breath_candidate,
    select_separate_channels_bins,
)
from process_vital_signs_v2_3 import (
    SDK_DEFAULT_BIN_SPACING_M,
    SDK_DEFAULT_RANGE_BIAS_M,
    _bin_to_distance_m,
    _distance_gate_to_bin_mask,
    save_breath_raw_phase_plot,
    save_breath_unwrapped_phase_plot,
    save_selected_channel_range_fft,
)


def save_selected_channel_range_fft(
    npz_files: Iterable[Path],
    output_dir: Path,
    session: str,
    breath_ch: int,
    breath_bin: int,
    heart_ch: int,
    heart_bin: int,
    frame_start: int | None = None,
    frame_end: int | None = None,
    view_start_s: float | None = None,
    view_len_s: float = 30.0,
    max_plot_frames: int = 1200,
    bin_spacing_m: float = SDK_DEFAULT_BIN_SPACING_M,
    range_bias_m: float = SDK_DEFAULT_RANGE_BIAS_M,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    slices: list[np.ndarray] = []
    for iq_td in _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
        slices.append(np.abs(_as_range_cube(iq_td)).astype(np.float32))

    if not slices:
        raise RuntimeError("No frames were available for selected-channel range-FFT plotting.")

    amp_all = np.concatenate(slices, axis=0)  # (time, bin, ch)
    total_frames = amp_all.shape[0]
    duration_s = total_frames / FS

    if view_start_s is None:
        view_start_s = max(0.0, duration_s / 2 - view_len_s / 2) if duration_s > view_len_s else 0.0
    view_end_s = min(duration_s, view_start_s + view_len_s)

    start_idx = int(max(0, round(view_start_s * FS)))
    end_idx = int(min(total_frames, round(view_end_s * FS)))
    if end_idx <= start_idx:
        start_idx = 0
        end_idx = total_frames
    amp_all = amp_all[start_idx:end_idx]

    if amp_all.shape[0] > max_plot_frames:
        edges = np.linspace(0, amp_all.shape[0], max_plot_frames + 1, dtype=int)
        reduced = []
        for idx in range(max_plot_frames):
            seg = amp_all[edges[idx] : edges[idx + 1]]
            if len(seg) == 0:
                continue
            reduced.append(np.mean(seg, axis=0))
        amp_all = np.stack(reduced, axis=0)

    ch_maps = [
        ("Breath", breath_ch, breath_bin, amp_all[:, :, breath_ch]),
        ("Heart", heart_ch, heart_bin, amp_all[:, :, heart_ch]),
    ]
    all_vals = np.concatenate([m[3].ravel() for m in ch_maps])
    vmin = float(np.percentile(all_vals, 5))
    vmax = float(np.percentile(all_vals, 99))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin = float(np.min(all_vals))
        vmax = float(np.max(all_vals))

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    n_bins = amp_all.shape[1]
    dist_axis_m = _bin_to_distance_m(np.arange(n_bins), bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
    extent = [float(dist_axis_m[0]), float(dist_axis_m[-1]), 0, amp_all.shape[0] - 1]
    for ax, (label, ch, bin_idx, ch_map) in zip(axes, ch_maps):
        im = ax.imshow(
            ch_map,
            aspect="auto",
            origin="lower",
            cmap="viridis",
            interpolation="nearest",
            vmin=vmin,
            vmax=vmax,
            extent=extent,
        )
        bin_dist_m = float(_bin_to_distance_m(bin_idx, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m))
        ax.axvline(bin_dist_m, color="red", linestyle="--", linewidth=1.2, alpha=0.9)
        ax.set_title(f"{label} channel ch{ch} (bin {bin_idx}, {bin_dist_m:.2f} m)")
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Chirp / frame index")

    fig.suptitle(
        f"Selected-channel Range FFT - {session} ({view_start_s:.0f}-{view_end_s:.0f} s)",
        fontsize=14,
    )
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.92)
    cbar.set_label("Amplitude (linear)")
    plt.tight_layout(rect=[0, 0, 0.96, 0.94])

    png_path = output_dir / f"{session}_selected_channel_range_fft.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def save_breath_raw_phase_plot(
    npz_files: Iterable[Path],
    output_dir: Path,
    session: str,
    breath_ch: int,
    breath_bin: int,
    frame_start: int | None = None,
    frame_end: int | None = None,
    view_start_s: float | None = None,
    view_len_s: float = 60.0,
    bin_spacing_m: float = SDK_DEFAULT_BIN_SPACING_M,
    range_bias_m: float = SDK_DEFAULT_RANGE_BIAS_M,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    phase_chunks: list[np.ndarray] = []
    for iq_td in _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
        iq_fd = _as_range_cube(iq_td)
        phase_chunks.append(np.angle(iq_fd[:, breath_bin, breath_ch]).astype(np.float32))

    if not phase_chunks:
        raise RuntimeError("No frames were available for breath raw phase plotting.")

    angle_target = np.concatenate(phase_chunks, axis=0)
    total_frames = angle_target.shape[0]
    duration_s = total_frames / FS

    if view_start_s is None:
        view_start_s = max(0.0, duration_s / 2 - view_len_s / 2) if duration_s > view_len_s else 0.0
    view_end_s = min(duration_s, view_start_s + view_len_s)

    start_idx = int(max(0, round(view_start_s * FS)))
    end_idx = int(min(total_frames, round(view_end_s * FS)))
    if end_idx <= start_idx:
        start_idx = 0
        end_idx = total_frames

    angle_view = angle_target[start_idx:end_idx]
    x = np.arange(start_idx, end_idx)
    dist_m = float(_bin_to_distance_m(breath_bin, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m))

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(x, angle_view, linewidth=0.8, color="#1f77b4")
    ax.set_xlabel("时间/点数（N）：对应每个 chirp")
    ax.set_ylabel("相位")
    ax.set_title(
        f"未展开相位信号 - 呼吸通道 ch{breath_ch}, bin {breath_bin} ({dist_m:.2f} m), "
        f"{view_start_s:.0f}-{view_end_s:.0f} s"
    )
    ax.grid(True, alpha=0.25)
    plt.tight_layout()

    png_path = output_dir / f"{session}_breath_raw_phase.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def save_breath_unwrapped_phase_plot(
    npz_files: Iterable[Path],
    output_dir: Path,
    session: str,
    breath_ch: int,
    breath_bin: int,
    frame_start: int | None = None,
    frame_end: int | None = None,
    view_start_s: float | None = None,
    view_len_s: float = 60.0,
    bin_spacing_m: float = SDK_DEFAULT_BIN_SPACING_M,
    range_bias_m: float = SDK_DEFAULT_RANGE_BIAS_M,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    phase_chunks: list[np.ndarray] = []
    for iq_td in _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
        iq_fd = _as_range_cube(iq_td)
        phase_chunks.append(np.angle(iq_fd[:, breath_bin, breath_ch]).astype(np.float32))

    if not phase_chunks:
        raise RuntimeError("No frames were available for breath unwrapped phase plotting.")

    angle_target = np.concatenate(phase_chunks, axis=0)
    total_frames = angle_target.shape[0]
    duration_s = total_frames / FS

    if view_start_s is None:
        view_start_s = max(0.0, duration_s / 2 - view_len_s / 2) if duration_s > view_len_s else 0.0
    view_end_s = min(duration_s, view_start_s + view_len_s)

    start_idx = int(max(0, round(view_start_s * FS)))
    end_idx = int(min(total_frames, round(view_end_s * FS)))
    if end_idx <= start_idx:
        start_idx = 0
        end_idx = total_frames

    unwrap_target = np.unwrap(angle_target)
    unwrap_view = unwrap_target[start_idx:end_idx]
    x = np.arange(start_idx, end_idx)
    dist_m = float(_bin_to_distance_m(breath_bin, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m))

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(x, unwrap_view, linewidth=0.9, color="#d62728")
    ax.set_xlabel("时间/点数 (N)：对应每个 chirp")
    ax.set_ylabel("相位 (rad)")
    ax.set_title(
        f"解缠后的相位 - 呼吸通道 ch{breath_ch}, bin {breath_bin} ({dist_m:.2f} m), "
        f"{view_start_s:.0f}-{view_end_s:.0f} s"
    )
    ax.grid(True, alpha=0.25)
    plt.tight_layout()

    png_path = output_dir / f"{session}_breath_unwrapped_phase.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def _odd_kernel_size(window_s: float, fs: float, max_len: int) -> int:
    kernel = max(5, int(round(window_s * fs)))
    kernel = min(kernel, max_len if max_len % 2 == 1 else max_len - 1)
    if kernel % 2 == 0:
        kernel -= 1
    return max(kernel, 3)


def _robust_mad(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    med = np.median(x)
    return float(np.median(np.abs(x - med)) + 1e-8)


def _suppress_phase_steps(x: np.ndarray, z_thresh: float = 8.0) -> tuple[np.ndarray, dict]:
    x = np.asarray(x, dtype=np.float64)
    if x.size < 8:
        return x.copy(), {"step_count": 0, "step_threshold": None}

    dx = np.diff(x)
    dx_med = np.median(dx)
    dx_mad = _robust_mad(dx)
    robust_z = np.abs(dx - dx_med) / max(1.4826 * dx_mad, 1e-8)
    step_idx = np.flatnonzero(robust_z > z_thresh)

    corrected = x.copy()
    cumulative_offset = 0.0
    prev = 0
    for idx in step_idx:
        jump = corrected[idx + 1] - corrected[idx]
        cumulative_offset += jump
        corrected[idx + 1 :] -= jump
        prev = idx

    return corrected, {
        "step_count": int(len(step_idx)),
        "step_indices": [int(i) for i in step_idx[:20]],
        "step_threshold": round(float(z_thresh), 3),
        "dx_mad": round(float(dx_mad), 6),
        "total_step_offset": round(float(cumulative_offset), 4),
    }


def _breath_remove_baseline_strong(
    disp_br: np.ndarray,
    median_window_s: float = 10.0,
    hp_cutoff_hz: float = 0.035,
) -> tuple[np.ndarray, dict]:
    x = np.asarray(disp_br, dtype=np.float64)
    if x.size < 8:
        centered = x - np.mean(x)
        return centered, {
            "method": "center_only",
            "median_window_s": median_window_s,
            "hp_cutoff_hz": hp_cutoff_hz,
            "baseline_std": round(float(np.std(x - centered)), 6),
        }

    linear = signal.detrend(x, type="linear")
    step_suppressed, step_info = _suppress_phase_steps(linear, z_thresh=8.0)
    kernel = _odd_kernel_size(median_window_s, FS, len(step_suppressed))
    baseline = signal.medfilt(step_suppressed, kernel_size=kernel) if kernel >= 3 else np.zeros_like(step_suppressed)
    residual = step_suppressed - baseline

    sos = signal.butter(2, hp_cutoff_hz, btype="highpass", fs=FS, output="sos")
    strong = signal.sosfiltfilt(sos, residual).astype(np.float64)
    return strong, {
        "method": "linear_detrend_plus_step_suppression_plus_median_plus_highpass",
        "median_window_s": median_window_s,
        "median_kernel": int(kernel),
        "hp_cutoff_hz": hp_cutoff_hz,
        "step_info": step_info,
        "baseline_std": round(float(np.std(baseline)), 4),
        "residual_std": round(float(np.std(strong)), 4),
        "baseline_to_residual_ratio": round(float(np.std(baseline) / max(np.std(strong), 1e-8)), 4),
    }


def _neighbor_bins(center_bin: int, n_bins: int, radius: int = 1) -> list[int]:
    return [bin_idx for bin_idx in range(center_bin - radius, center_bin + radius + 1) if 0 <= bin_idx < n_bins]


def _neighbor_channels(center_ch: int, n_ch: int, radius: int = 2) -> list[int]:
    return [ch for ch in range(center_ch - radius, center_ch + radius + 1) if 0 <= ch < n_ch]


def _extract_breath_fusion_displacement(
    npz_files: list[Path],
    br_ch: int,
    br_bin: int,
    hr_ch: int,
    hr_bin: int,
    bin_power_acc: np.ndarray,
    frame_start: int | None = None,
    frame_end: int | None = None,
) -> tuple[np.ndarray, np.ndarray, int, dict]:
    candidate_bins = _neighbor_bins(br_bin, n_bins=bin_power_acc.shape[0], radius=1)
    candidate_channels = _neighbor_channels(br_ch, n_ch=bin_power_acc.shape[1], radius=2)
    candidate_keys = [(ch, bin_idx) for ch in candidate_channels for bin_idx in candidate_bins]
    phase_chunks: dict[tuple[int, int], list[np.ndarray]] = {key: [] for key in candidate_keys}
    disp_hr_chunks: list[np.ndarray] = []
    n_total = 0

    for index, iq_td in enumerate(
        _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end),
        start=1,
    ):
        iq_fd = _as_range_cube(iq_td)
        for ch, bin_idx in candidate_keys:
            phase_chunks[(ch, bin_idx)].append(np.angle(iq_fd[:, bin_idx, ch]).astype(np.float64))
        disp_hr_chunks.append(extract_displacement(iq_fd, hr_bin, hr_ch))
        n_total += iq_td.shape[0]
        if index % 50 == 0:
            print(f"[pass2] {index} chunks processed, {n_total} frames extracted")

    if not disp_hr_chunks or any(len(chunks) == 0 for chunks in phase_chunks.values()):
        raise RuntimeError("No displacement chunks were extracted for v2.4 fusion.")

    candidate_series: list[dict] = []
    center_freq_hz = None
    center_bin_power = float(bin_power_acc[br_bin, br_ch])

    for ch, bin_idx in candidate_keys:
        phi = np.unwrap(np.concatenate(phase_chunks[(ch, bin_idx)], axis=0))
        disp = WAVELENGTH_MM * phi / (4 * np.pi)
        strong_disp, base_info = _breath_remove_baseline_strong(disp)
        breath_sig = _sos_bandpass(strong_disp, 0.1, 0.5)
        br_freq_hz, _, _ = estimate_breath_rate_consensus(breath_sig)
        phase_stability, phase_info = _phase_stability_score(phi)
        power_rel = float(bin_power_acc[bin_idx, ch] / max(center_bin_power, 1e-8))
        channel_rel = float(np.mean(bin_power_acc[candidate_bins, ch]) / max(np.mean(bin_power_acc[candidate_bins, br_ch]), 1e-8))
        if ch == br_ch and bin_idx == br_bin:
            center_freq_hz = br_freq_hz
        candidate_series.append(
            {
                "channel": int(ch),
                "bin": int(bin_idx),
                "phi": phi,
                "disp": disp,
                "strong_disp": strong_disp,
                "breath_sig": breath_sig,
                "freq_hz": br_freq_hz,
                "phase_stability": float(phase_stability),
                "power_rel": power_rel,
                "channel_rel": channel_rel,
                "phase_info": phase_info,
                "baseline_info": base_info,
            }
        )

    if center_freq_hz is None:
        freqs = [item["freq_hz"] for item in candidate_series if item["freq_hz"] is not None]
        center_freq_hz = float(np.median(freqs)) if freqs else None

    raw_weights = []
    for item in candidate_series:
        freq_hz = item["freq_hz"]
        if center_freq_hz is None or freq_hz is None:
            freq_consistency = 0.7
        else:
            freq_consistency = float(np.exp(-abs(freq_hz - center_freq_hz) / 0.08))
        ch_consistency = float(np.exp(-abs(item["channel"] - br_ch) / 2.0))
        raw_weight = (
            max(item["power_rel"], 0.12)
            * max(item["channel_rel"], 0.25)
            * (0.30 + item["phase_stability"])
            * freq_consistency
            * ch_consistency
        )
        item["freq_consistency"] = round(freq_consistency, 4)
        item["channel_consistency"] = round(ch_consistency, 4)
        item["raw_weight"] = float(raw_weight)
        raw_weights.append(raw_weight)

    raw_weights = np.asarray(raw_weights, dtype=np.float64)
    if np.all(raw_weights <= 0):
        raw_weights = np.ones_like(raw_weights)
    weights = raw_weights / np.sum(raw_weights)

    disp_stack = np.stack([item["disp"] - np.mean(item["disp"]) for item in candidate_series], axis=0)
    disp_br_fused = np.sum(weights[:, None] * disp_stack, axis=0)

    for item, weight in zip(candidate_series, weights):
        item["final_weight"] = round(float(weight), 4)

    neighbor_freqs = [item["freq_hz"] * 60.0 for item in candidate_series if item["freq_hz"] is not None]
    fusion_info = {
        "enabled": True,
        "channel": int(br_ch),
        "center_bin": int(br_bin),
        "candidate_channels": [int(ch) for ch in candidate_channels],
        "candidate_bins": [int(bin_idx) for bin_idx in candidate_bins],
        "center_freq_bpm": round(float(center_freq_hz * 60.0), 2) if center_freq_hz is not None else None,
        "neighbor_freq_std_bpm": round(float(np.std(neighbor_freqs)), 3) if len(neighbor_freqs) >= 2 else None,
        "weights": [
            {
                "channel": item["channel"],
                "bin": item["bin"],
                "power_rel": round(float(item["power_rel"]), 4),
                "channel_rel": round(float(item["channel_rel"]), 4),
                "phase_stability": round(float(item["phase_stability"]), 4),
                "freq_bpm": round(float(item["freq_hz"] * 60.0), 2) if item["freq_hz"] is not None else None,
                "freq_consistency": item["freq_consistency"],
                "channel_consistency": item["channel_consistency"],
                "final_weight": item["final_weight"],
            }
            for item in candidate_series
        ],
    }
    return disp_br_fused, np.concatenate(disp_hr_chunks), n_total, fusion_info


def _select_breath_candidate_v24(
    disp_br: np.ndarray,
    freq_prior_hz: float | None = None,
) -> tuple[np.ndarray, float | None, np.ndarray, dict, np.ndarray, dict]:
    strong_disp, baseline_info = _breath_remove_baseline_strong(disp_br)

    breath_bp = _sos_bandpass(strong_disp, 0.1, 0.5)
    br_freq_bp, bp_bp, info_bp = estimate_breath_rate_consensus(breath_bp)
    score_bp, score_info_bp = _score_breath_candidate(breath_bp, br_freq_bp, bp_bp)
    if freq_prior_hz is not None and br_freq_bp is not None:
        score_bp -= 3.0 * abs(br_freq_bp - freq_prior_hz) * 60.0
    info_bp = {
        **info_bp,
        "source": "strong_baseline_bandpass",
        "branch": "strong_baseline_bandpass",
        "baseline_removal": baseline_info,
        "selection_score": score_info_bp,
    }

    diff_sig = np.diff(strong_disp, prepend=strong_disp[0])
    smooth_sig = _movmean(diff_sig, win=5)
    breath_mat = _sos_bandpass(smooth_sig, 0.1, 0.5)
    br_freq_mat, bp_mat, info_mat = estimate_breath_rate_consensus(breath_mat)
    score_mat, score_info_mat = _score_breath_candidate(breath_mat, br_freq_mat, bp_mat)
    if freq_prior_hz is not None and br_freq_mat is not None:
        score_mat -= 3.0 * abs(br_freq_mat - freq_prior_hz) * 60.0
    info_mat = {
        **info_mat,
        "source": "strong_baseline_diff_movmean_bandpass",
        "branch": "strong_baseline_matlab_style",
        "baseline_removal": baseline_info,
        "selection_score": score_info_mat,
    }

    if score_mat > score_bp:
        chosen = "strong_baseline_matlab_style"
        breath, br_freq, bp, info = breath_mat, br_freq_mat, bp_mat, info_mat
    else:
        chosen = "strong_baseline_bandpass"
        breath, br_freq, bp, info = breath_bp, br_freq_bp, bp_bp, info_bp

    info["candidate_compare"] = {
        "chosen_branch": chosen,
        "strong_baseline_bandpass": score_info_bp,
        "strong_baseline_matlab_style": score_info_mat,
    }
    return breath, br_freq, bp, info, strong_disp, baseline_info


def _sliding_breath_rate_series(
    breath: np.ndarray,
    window_s: float = 30.0,
    step_s: float = 10.0,
) -> list[float]:
    window_n = int(window_s * FS)
    step_n = int(step_s * FS)
    if len(breath) < window_n or window_n <= 0 or step_n <= 0:
        return []

    series: list[float] = []
    for start in range(0, len(breath) - window_n + 1, step_n):
        seg = breath[start : start + window_n]
        seg_freq_hz, seg_peaks, _ = estimate_breath_rate_consensus(seg)
        if seg_freq_hz is not None and len(seg_peaks) >= 2:
            series.append(float(seg_freq_hz * 60.0))
    return series


def _window_quality_metrics(
    strong_disp: np.ndarray,
    breath: np.ndarray,
    start: int,
    end: int,
) -> dict:
    seg_disp = strong_disp[start:end]
    seg_breath = breath[start:end]
    if len(seg_disp) < int(10 * FS):
        return {"usable": False}

    dseg = np.diff(seg_disp)
    disp_std = float(np.std(seg_disp))
    jump_ratio = float(np.percentile(np.abs(dseg), 95) / max(disp_std, 1e-8))
    slope = float(np.polyfit(np.arange(len(seg_disp)), seg_disp, 1)[0])

    seg_freq_hz, seg_bp, _ = estimate_breath_rate_consensus(seg_breath)
    peak_interval_cv = None
    seg_time_bpm = None
    if len(seg_bp) >= 3:
        intervals = np.diff(seg_bp) / FS
        peak_interval_cv = float(np.std(intervals) / max(np.mean(intervals), 1e-8))
        seg_time_bpm = float(60.0 / np.mean(intervals))

    freqs, pxx = signal.periodogram(seg_breath, fs=FS, window="hann")
    mask = (freqs >= 0.1) & (freqs <= 0.5)
    fundamental_to_harmonic = 0.0
    if np.any(mask):
        f_band = freqs[mask]
        p_band = pxx[mask]
        if seg_freq_hz is None:
            seg_freq_hz = float(f_band[int(np.argmax(p_band))])
        f0_mask = np.abs(f_band - seg_freq_hz) <= 0.03
        h0 = min(seg_freq_hz * 2.0, 0.5)
        h0_mask = np.abs(f_band - h0) <= 0.03
        fundamental_power = float(np.sum(p_band[f0_mask]))
        harmonic_power = float(np.sum(p_band[h0_mask])) if np.any(h0_mask) else 0.0
        fundamental_to_harmonic = float(fundamental_power / max(harmonic_power, 1e-8))

    score = 0.0
    score += max(0.0, 2.0 - jump_ratio)
    score += max(0.0, 1.0 - abs(slope) * 200.0)
    score += min(fundamental_to_harmonic, 3.0) / 1.5
    if peak_interval_cv is not None:
        score += max(0.0, 1.0 - peak_interval_cv)
    usable = score >= 2.0 and (seg_freq_hz is not None)
    return {
        "usable": usable,
        "score": round(float(score), 4),
        "jump_ratio": round(jump_ratio, 4),
        "baseline_slope": round(slope, 6),
        "fundamental_to_harmonic": round(fundamental_to_harmonic, 4),
        "peak_interval_cv": round(peak_interval_cv, 4) if peak_interval_cv is not None else None,
        "freq_bpm": round(float(seg_freq_hz * 60.0), 2) if seg_freq_hz is not None else None,
        "time_bpm": round(float(seg_time_bpm), 2) if seg_time_bpm is not None else None,
        "n_peaks": int(len(seg_bp)) if seg_bp is not None else 0,
    }


def _stable_window_breath_aggregate(
    strong_disp: np.ndarray,
    breath: np.ndarray,
) -> dict:
    window_n = int(30.0 * FS)
    step_n = int(10.0 * FS)
    windows: list[dict] = []
    freq_vals = []
    time_vals = []
    weights = []

    for start in range(0, max(len(breath) - window_n + 1, 1), step_n):
        end = min(start + window_n, len(breath))
        if end - start < int(20.0 * FS):
            continue
        metrics = _window_quality_metrics(strong_disp, breath, start, end)
        metrics["start_s"] = round(start / FS, 2)
        metrics["end_s"] = round(end / FS, 2)
        windows.append(metrics)
        if metrics["usable"] and metrics.get("freq_bpm") is not None and metrics.get("time_bpm") is not None:
            freq_vals.append(float(metrics["freq_bpm"]))
            time_vals.append(float(metrics["time_bpm"]))
            weights.append(max(float(metrics["score"]), 0.1))

    usable_ratio = float(sum(1 for win in windows if win["usable"]) / max(len(windows), 1))
    if weights:
        weights_arr = np.asarray(weights, dtype=np.float64)
        weights_arr /= np.sum(weights_arr)
        freq_bpm = float(np.sum(weights_arr * np.asarray(freq_vals)))
        time_bpm = float(np.sum(weights_arr * np.asarray(time_vals)))
    else:
        freq_bpm = None
        time_bpm = None

    return {
        "window_s": 30.0,
        "step_s": 10.0,
        "usable_ratio": round(usable_ratio, 4),
        "n_windows": int(len(windows)),
        "n_usable_windows": int(sum(1 for win in windows if win["usable"])),
        "freq_bpm": round(freq_bpm, 2) if freq_bpm is not None else None,
        "time_bpm": round(time_bpm, 2) if time_bpm is not None else None,
        "windows": windows,
    }


def _compute_breath_quality(
    disp_br_raw: np.ndarray,
    strong_disp: np.ndarray,
    breath: np.ndarray,
    bp: np.ndarray,
    br_freq_hz: float | None,
    baseline_info: dict,
    fusion_info: dict,
    window_info: dict,
) -> dict:
    freqs, pxx = signal.periodogram(breath, fs=FS, window="hann")
    mask = (freqs >= 0.1) & (freqs <= 0.5)
    f_band = freqs[mask]
    p_band = pxx[mask]
    total_band_power = float(np.sum(p_band))

    if len(f_band) > 0 and total_band_power > 0:
        if br_freq_hz is None:
            main_hz = float(f_band[int(np.argmax(p_band))])
        else:
            main_hz = float(br_freq_hz)
        main_mask = np.abs(f_band - main_hz) <= 0.03
        concentration = float(np.sum(p_band[main_mask]) / total_band_power)
    else:
        concentration = 0.0

    sliding_br = _sliding_breath_rate_series(breath, window_s=30.0, step_s=10.0)
    peak_interval_cv = None
    if len(bp) >= 3:
        intervals = np.diff(bp) / FS
        peak_interval_cv = float(np.std(intervals) / max(np.mean(intervals), 1e-8))

    raw_std = float(np.std(disp_br_raw))
    strong_std = float(np.std(strong_disp))
    drift_ratio = float(max(raw_std - strong_std, 0.0) / max(raw_std, 1e-8))

    quality_score = 0.0
    quality_score += 2.0 * concentration
    quality_score += 0.8 * (1.0 - min(drift_ratio, 1.0))
    if peak_interval_cv is not None:
        quality_score += 0.8 * (1.0 - min(peak_interval_cv, 1.0))
    if sliding_br:
        sliding_std = float(np.std(sliding_br))
        quality_score += 0.8 * max(0.0, 1.0 - sliding_std / 3.0)
    else:
        sliding_std = None
    if fusion_info.get("neighbor_freq_std_bpm") is not None:
        quality_score += 0.6 * max(0.0, 1.0 - float(fusion_info["neighbor_freq_std_bpm"]) / 3.0)
    if window_info.get("usable_ratio") is not None:
        quality_score += 1.0 * float(window_info["usable_ratio"])

    label = "high" if quality_score >= 3.2 else ("medium" if quality_score >= 2.2 else "low")
    return {
        "label": label,
        "score": round(float(quality_score), 3),
        "baseline_drift_ratio": round(drift_ratio, 4),
        "baseline_info": baseline_info,
        "band_energy_concentration": round(concentration, 4),
        "sliding_br_std_bpm": round(sliding_std, 4) if sliding_std is not None else None,
        "sliding_br_series_bpm": [round(float(x), 2) for x in sliding_br],
        "peak_interval_cv": round(peak_interval_cv, 4) if peak_interval_cv is not None else None,
        "neighbor_freq_std_bpm": fusion_info.get("neighbor_freq_std_bpm"),
        "usable_window_ratio": window_info.get("usable_ratio"),
        "n_usable_windows": window_info.get("n_usable_windows"),
    }


def analyze_displacement_v24(
    disp_br: np.ndarray,
    disp_hr: np.ndarray,
    n_frames: int,
    method: str = "vmd_heart",
    session: str = "sub-sxq_ses-SART",
    fusion_info: dict | None = None,
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    duration = n_frames / FS
    t = np.arange(n_frames) / FS

    freq_prior_hz = None
    if fusion_info and fusion_info.get("center_freq_bpm") is not None:
        freq_prior_hz = float(fusion_info["center_freq_bpm"]) / 60.0

    breath, br_freq, bp, breath_sep, strong_disp, baseline_info = _select_breath_candidate_v24(
        disp_br,
        freq_prior_hz=freq_prior_hz,
    )
    window_info = _stable_window_breath_aggregate(strong_disp, breath)

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
    if window_info.get("freq_bpm") is not None:
        br_freq_bpm = round(float(window_info["freq_bpm"]), 1)
    if window_info.get("time_bpm") is not None:
        br_time_bpm = round(float(window_info["time_bpm"]), 1)
    br_conf = None
    if br_time_bpm is not None and br_freq_bpm is not None:
        gap = abs(br_freq_bpm - br_time_bpm)
        if window_info.get("usable_ratio", 0.0) >= 0.6:
            br_conf = "high" if gap <= 2.0 else ("medium" if gap <= 5.0 else "low")
        else:
            br_conf = "medium" if gap <= 2.0 else "low"

    breath_quality = _compute_breath_quality(
        disp_br_raw=disp_br,
        strong_disp=strong_disp,
        breath=breath,
        bp=bp,
        br_freq_hz=br_freq,
        baseline_info=baseline_info,
        fusion_info=fusion_info or {},
        window_info=window_info,
    )

    result = {
        "session": session,
        "version": "v2.4",
        "pipeline": "chunked_long_record_strong_breath",
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
        "breath_quality": breath_quality,
        "breath_windows": window_info,
        "displacement_mm": {
            "breath_ptp": round(float(np.ptp(breath)), 2),
            "heart_ptp": round(float(np.ptp(heartbeat)), 2),
            "breath_std": round(float(np.std(breath)), 3),
            "heart_std": round(float(np.std(heartbeat)), 3),
        },
        "hrv": hrv,
        "breath_fusion": fusion_info or {"enabled": False},
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
    min_range_m: float | None = 0.3,
    max_range_m: float | None = 1.5,
    bin_spacing_m: float = SDK_DEFAULT_BIN_SPACING_M,
    range_bias_m: float = SDK_DEFAULT_RANGE_BIAS_M,
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

    iq_sample = next(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), None)
    if iq_sample is None:
        raise RuntimeError("Selected frame range contains no data.")
    iq_fd_sample = _as_range_cube(iq_sample)

    gate_mask = _distance_gate_to_bin_mask(
        n_bins=bin_power_acc.shape[0],
        min_range_m=min_range_m,
        max_range_m=max_range_m,
        bin_spacing_m=bin_spacing_m,
        range_bias_m=range_bias_m,
    )
    if not np.any(gate_mask):
        raise RuntimeError("Distance gate excluded all range bins. Please check min/max range settings.")

    bin_power_acc_gated = np.array(bin_power_acc, copy=True)
    bin_power_acc_gated[~gate_mask, :] = 0.0

    br_ch, br_bin, _hr_ch_gate, _hr_bin_gate, breath_gate_summaries = select_separate_channels_bins(
        bin_power_acc_gated,
        iq_fd_sample,
        iq_sample.shape[0],
        channel_override=channel_override,
    )
    _br_ch_full, _br_bin_full, hr_ch, hr_bin, heart_full_summaries = select_separate_channels_bins(
        bin_power_acc,
        iq_fd_sample,
        iq_sample.shape[0],
        channel_override=channel_override,
    )
    print(
        f"[bins] breath_ch={br_ch}, breath_bin={br_bin}, "
        f"heart_ch={hr_ch}, heart_bin={hr_bin}, auto_best_ch={best_ch_auto}"
    )

    disp_br, disp_hr, n_frames, fusion_info = _extract_breath_fusion_displacement(
        npz_files,
        br_ch,
        br_bin,
        hr_ch,
        hr_bin,
        bin_power_acc=bin_power_acc,
        frame_start=frame_start,
        frame_end=frame_end,
    )
    result, waveforms = analyze_displacement_v24(
        disp_br,
        disp_hr,
        n_frames,
        method=method,
        session=session,
        fusion_info=fusion_info,
    )
    result["best_channel"] = br_ch
    result["auto_best_channel"] = best_ch_auto
    result["channels"] = {"breath": br_ch, "heart": hr_ch}
    result["channel_selection"] = {
        "breath_gated": breath_gate_summaries,
        "heart_full_range": heart_full_summaries,
    }
    result["bins"] = {"breath": br_bin, "heart": hr_bin}
    result["n_frames"] = n_frames
    result["distance_axis"] = {
        "bin_spacing_m": round(float(bin_spacing_m), 4),
        "range_bias_m": round(float(range_bias_m), 4),
        "min_range_m": min_range_m,
        "max_range_m": max_range_m,
        "breath_distance_m": round(float(_bin_to_distance_m(br_bin, bin_spacing_m, range_bias_m)), 3),
        "heart_distance_m": round(float(_bin_to_distance_m(hr_bin, bin_spacing_m, range_bias_m)), 3),
        "gate_applies_to": "breath_only",
    }
    result["breath_fusion"] = fusion_info

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

    channels = result.get("channels", {})
    fft_png = save_selected_channel_range_fft(
        npz_files=npz_files,
        output_dir=output_dir,
        session=session,
        breath_ch=int(channels.get("breath", result["best_channel"])),
        breath_bin=int(result["bins"]["breath"]),
        heart_ch=int(channels.get("heart", result["best_channel"])),
        heart_bin=int(result["bins"]["heart"]),
        frame_start=frame_start,
        frame_end=frame_end,
        view_start_s=breath_view_start_s,
        bin_spacing_m=bin_spacing_m,
        range_bias_m=range_bias_m,
    )
    phase_png = save_breath_raw_phase_plot(
        npz_files=npz_files,
        output_dir=output_dir,
        session=session,
        breath_ch=int(channels.get("breath", result["best_channel"])),
        breath_bin=int(result["bins"]["breath"]),
        frame_start=frame_start,
        frame_end=frame_end,
        view_start_s=breath_view_start_s,
        bin_spacing_m=bin_spacing_m,
        range_bias_m=range_bias_m,
    )
    unwrap_phase_png = save_breath_unwrapped_phase_plot(
        npz_files=npz_files,
        output_dir=output_dir,
        session=session,
        breath_ch=int(channels.get("breath", result["best_channel"])),
        breath_bin=int(result["bins"]["breath"]),
        frame_start=frame_start,
        frame_end=frame_end,
        view_start_s=breath_view_start_s,
        bin_spacing_m=bin_spacing_m,
        range_bias_m=range_bias_m,
    )
    print(f"[plot] {plot_path}")
    print(f"[range_fft_raw] {range_fft_raw_path}")
    print(f"[range_fft_diag] {range_fft_diag_path}")
    print(f"[range_fft_grid_raw] {range_fft_grid_raw_path}")
    print(f"[range_fft_grid_diag] {range_fft_grid_diag_path}")
    print(f"[selected_range_fft] {fft_png}")
    print(f"[breath_raw_phase] {phase_png}")
    print(f"[breath_unwrapped_phase] {unwrap_phase_png}")
    result["version"] = "v2.4"
    return result, waveforms
