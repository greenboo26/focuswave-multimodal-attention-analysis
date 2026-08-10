"""
v2.4-lite: simplified respiration refinement based on v2.3.
Keep the proven upgrades, but temporarily roll back the most bias-prone parts.
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

BREATH_HP_CUTOFF_HZ = 0.025
BREATH_STEP_Z_THRESHOLD = 12.0


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
    hp_cutoff_hz: float = BREATH_HP_CUTOFF_HZ,
    step_z_threshold: float = BREATH_STEP_Z_THRESHOLD,
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
    step_suppressed, step_info = _suppress_phase_steps(linear, z_thresh=step_z_threshold)
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
        "step_z_threshold": round(float(step_z_threshold), 3),
        "step_info": step_info,
        "baseline_std": round(float(np.std(baseline)), 4),
        "residual_std": round(float(np.std(strong)), 4),
        "baseline_to_residual_ratio": round(float(np.std(baseline) / max(np.std(strong), 1e-8)), 4),
    }


def _neighbor_bins(center_bin: int, n_bins: int, radius: int = 1) -> list[int]:
    return [bin_idx for bin_idx in range(center_bin - radius, center_bin + radius + 1) if 0 <= bin_idx < n_bins]


def _neighbor_channels(center_ch: int, n_ch: int, radius: int = 0) -> list[int]:
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
    candidate_channels = _neighbor_channels(br_ch, n_ch=bin_power_acc.shape[1], radius=0)
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
        phase_stability, phase_