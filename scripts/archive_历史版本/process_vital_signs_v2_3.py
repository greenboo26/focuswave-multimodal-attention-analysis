"""
v2.3: keep the current v2.2 pipeline, and add selected-channel range-FFT
figures for the final breath/heart channel choices.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from process_vital_signs_v2 import FS
from process_vital_signs_v2_0 import (
    _as_range_cube,
    _iter_selected_chunks,
    collect_npz_parts,
    accumulate_range_profile,
    save_result,
    plot_result,
    save_range_fft_map,
    save_range_fft_channel_grid,
)
from process_vital_signs_v2_2 import (
    analyze_displacement,
    extract_displacement_separate,
    select_separate_channels_bins,
)


SDK_DEFAULT_BIN_SPACING_M = 0.08
SDK_DEFAULT_RANGE_BIAS_M = 0.0


def _bin_to_distance_m(
    bin_idx: int | np.ndarray,
    bin_spacing_m: float,
    range_bias_m: float = 0.0,
) -> np.ndarray:
    return np.asarray(bin_idx, dtype=np.float64) * float(bin_spacing_m) - float(range_bias_m)


def _distance_gate_to_bin_mask(
    n_bins: int,
    min_range_m: float | None,
    max_range_m: float | None,
    bin_spacing_m: float,
    range_bias_m: float = 0.0,
) -> np.ndarray:
    dist_axis_m = _bin_to_distance_m(np.arange(n_bins), bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
    mask = np.ones(n_bins, dtype=bool)
    if min_range_m is not None:
        mask &= dist_axis_m >= float(min_range_m)
    if max_range_m is not None:
        mask &= dist_axis_m <= float(max_range_m)
    return mask


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
    result["version"] = "v2.3"
    return result, waveforms
