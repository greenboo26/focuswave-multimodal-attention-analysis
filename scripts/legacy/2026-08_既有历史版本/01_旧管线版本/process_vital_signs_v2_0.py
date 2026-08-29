"""
Long-record mmWave vital-sign extraction pipeline (v2.0).

This version is the stabilized chunked workflow we used for the 47-minute
SXQ record:
1. scan all part*.npz chunks and accumulate range power,
2. select one global channel / breath bin / heart bin,
3. extract displacement from every chunk and concatenate,
4. run breath band-pass + optional VMD heart separation,
5. estimate HR / BR / HRV and save diagnostics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import signal

from process_vital_signs_v2 import FS, N_CH, extract_displacement, _sos_bandpass
from process_vital_signs_v3 import separate_vmd_heart_only
from process_vital_signs_v5 import detect_peaks_breath_robust


def _iter_tx_keys(npz_obj) -> list[str]:
    return sorted([key for key in npz_obj.keys() if key.startswith("tx")])


def _load_chunk(path: Path) -> np.ndarray:
    with np.load(path) as data:
        keys = _iter_tx_keys(data)
        if not keys:
            raise RuntimeError(f"No tx* arrays found in chunk: {path}")
        return np.stack([data[key] for key in keys], axis=-1).astype(np.complex64)


def _as_range_cube(iq_chunk: np.ndarray) -> np.ndarray:
    """
    Collector `.npz` / recovered `.bin` data is already 1D range-FFT output.
    Keep it in range domain instead of applying a second range FFT.
    """
    return np.asarray(iq_chunk, dtype=np.complex64)


def _iter_selected_chunks(
    npz_files: Iterable[Path],
    frame_start: int | None = None,
    frame_end: int | None = None,
) -> Iterable[np.ndarray]:
    cursor = 0
    for path in npz_files:
        iq_td = _load_chunk(path)
        n_local = iq_td.shape[0]
        local_start = 0 if frame_start is None else max(0, frame_start - cursor)
        local_end = n_local if frame_end is None else min(n_local, frame_end - cursor)
        if local_start < local_end:
            yield iq_td[local_start:local_end]
        cursor += n_local


def collect_npz_parts(parts_dir: Path, pattern: str = "sub-SXQ_mmwave_datacube_part*.npz") -> list[Path]:
    files = sorted(parts_dir.glob(pattern))
    if files:
        return files
    alt_pattern = pattern.replace("sub-SXQ", "sub-sxq")
    return sorted(parts_dir.glob(alt_pattern))


def accumulate_range_profile(
    npz_files: Iterable[Path],
    frame_start: int | None = None,
    frame_end: int | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    bin_power_acc = None
    channel_power = np.zeros(N_CH, dtype=np.float64)
    n_total = 0

    for index, iq_td in enumerate(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), start=1):
        iq_fd = _as_range_cube(iq_td)
        n_local = iq_td.shape[0]

        channel_power += np.mean(np.abs(iq_fd) ** 2, axis=(0, 1)) * n_local
        bin_power_local = np.mean(np.abs(iq_fd) ** 2, axis=0)
        if bin_power_acc is None:
            bin_power_acc = bin_power_local * n_local
        else:
            bin_power_acc += bin_power_local * n_local

        n_total += n_local
        if index % 50 == 0:
            print(f"[pass1] {index} chunks processed, {n_total} frames accumulated")

    if n_total == 0 or bin_power_acc is None:
        raise RuntimeError("No valid chunks were found for range-profile accumulation.")

    channel_power /= n_total
    bin_power_acc /= n_total
    return channel_power, bin_power_acc, n_total


def _phase_stability_score(phi: np.ndarray) -> tuple[float, dict]:
    """
    Estimate whether a bin's phase is stable enough for respiration tracking.
    Higher is better.
    """
    phi = np.asarray(phi, dtype=np.float64)
    if phi.size < 8:
        return 0.0, {"roughness": None, "jump_ratio": None, "osc_std": None}

    phi_dt = signal.detrend(phi, type="linear")
    osc_std = float(np.std(phi_dt))
    if osc_std < 1e-8:
        return 0.0, {"roughness": None, "jump_ratio": None, "osc_std": round(osc_std, 6)}

    dphi = np.diff(phi_dt)
    roughness = float(np.std(dphi) / max(osc_std, 1e-8))
    jump_ratio = float(np.percentile(np.abs(dphi), 95) / max(osc_std, 1e-8))
    stability = 1.0 / (1.0 + 0.9 * roughness + 0.35 * jump_ratio)
    return float(stability), {
        "roughness": round(roughness, 4),
        "jump_ratio": round(jump_ratio, 4),
        "osc_std": round(osc_std, 4),
    }


def select_bins_from_profile(
    bin_power_acc: np.ndarray,
    best_ch: int,
    iq_fd_sample: np.ndarray,
    n_frames_sample: int,
) -> tuple[int, int, list[tuple[int, float, float, float, float]]]:
    bin_power = bin_power_acc[:, best_ch]
    freqs = np.fft.rfftfreq(n_frames_sample, d=1 / FS)

    def build_candidates(require_phi_var: bool) -> list[tuple[int, float, float, float, float]]:
        power_thresh = float(np.max(bin_power)) * 0.01
        local_candidates: list[tuple[int, float, float, float, float]] = []
        for bin_idx in range(bin_power.shape[0]):
            if bin_power[bin_idx] < power_thresh:
                continue

            phi = np.unwrap(np.angle(iq_fd_sample[:, bin_idx, best_ch]))
            phi_var = float(np.var(phi))
            if require_phi_var and not (0.1 < phi_var < 50):
                continue

            pxx = np.abs(np.fft.rfft(phi - phi.mean())) ** 2
            noise = max(float(np.mean(pxx[(freqs >= 2.5) & (freqs <= 5.0)])), 1e-10)
            hr_snr = float(np.mean(pxx[(freqs >= 0.8) & (freqs <= 2.5)]) / noise)
            br_snr = float(np.mean(pxx[(freqs >= 0.1) & (freqs <= 0.5)]) / noise)
            phase_stability, _ = _phase_stability_score(phi)
            br_score = float(br_snr * phase_stability)
            local_candidates.append((int(bin_idx), hr_snr, br_snr, br_score, phase_stability))
        return local_candidates

    candidates = build_candidates(require_phi_var=True)
    if not candidates:
        candidates = build_candidates(require_phi_var=False)

    if not candidates:
        top_idx = int(np.argmax(bin_power))
        candidates = [(top_idx, 0.0, 0.0, 0.0, 0.0)]

    br_bin = max(candidates, key=lambda item: item[3])[0]
    hr_bin = max(candidates, key=lambda item: item[1])[0]
    return br_bin, hr_bin, candidates


def extract_displacement_all(
    npz_files: Iterable[Path],
    best_ch: int,
    br_bin: int,
    hr_bin: int,
    frame_start: int | None = None,
    frame_end: int | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    disp_br_chunks: list[np.ndarray] = []
    disp_hr_chunks: list[np.ndarray] = []
    n_total = 0

    for index, iq_td in enumerate(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), start=1):
        iq_fd = _as_range_cube(iq_td)
        n_local = iq_td.shape[0]

        disp_br_chunks.append(extract_displacement(iq_fd, br_bin, best_ch))
        disp_hr_chunks.append(extract_displacement(iq_fd, hr_bin, best_ch))
        n_total += n_local

        if index % 50 == 0:
            print(f"[pass2] {index} chunks processed, {n_total} frames extracted")

    if not disp_br_chunks or not disp_hr_chunks:
        raise RuntimeError("No displacement chunks were extracted.")

    return np.concatenate(disp_br_chunks), np.concatenate(disp_hr_chunks), n_total


def estimate_freq_periodogram(x: np.ndarray, lo_hz: float, hi_hz: float) -> float | None:
    freqs, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (freqs >= lo_hz) & (freqs <= hi_hz)
    if not np.any(mask):
        return None
    return float(freqs[mask][np.argmax(pxx[mask])])


def detect_peaks_heart_lo(x: np.ndarray, lo_bpm: float = 40, hi_bpm: float = 150) -> np.ndarray:
    x_std = float(np.std(x))
    if x_std < 1e-8:
        return np.array([], dtype=int)

    min_dist = max(int(FS * 60 / hi_bpm), int(FS * 0.3))
    best_peaks = np.array([], dtype=int)
    best_score = -1.0

    for prom_factor in [0.1, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01]:
        peaks, _ = signal.find_peaks(
            x,
            distance=min_dist,
            prominence=max(prom_factor * x_std, 1e-8),
        )
        if len(peaks) < 10:
            continue

        ibi = np.diff(peaks) / FS
        ibi = ibi[(ibi >= 60 / hi_bpm) & (ibi <= 60 / lo_bpm)]
        if len(ibi) < 5:
            continue

        cv = float(np.std(ibi) / np.mean(ibi))
        score = len(ibi) * (1 - min(cv, 1.0))
        if score > best_score:
            best_score = score
            best_peaks = peaks.copy()

    if len(best_peaks) < 2:
        return np.array([], dtype=int)

    best_lag = int(np.argmax(np.correlate(x, x, mode="full")[len(x) :]))
    if best_lag > 0:
        period_s = best_lag / FS
        if 60 / hi_bpm < period_s < 60 / lo_bpm:
            ref_ibi = period_s
        else:
            ref_ibi = float(np.median(np.diff(best_peaks) / FS))
    else:
        ref_ibi = float(np.median(np.diff(best_peaks) / FS))

    ibi = np.diff(best_peaks) / FS
    keep = np.ones(len(best_peaks), dtype=bool)
    for idx in range(len(best_peaks)):
        if idx == 0 and len(ibi) > 0:
            local_ibi = ibi[0]
        elif idx == len(best_peaks) - 1 and len(ibi) > 0:
            local_ibi = ibi[-1]
        elif 0 < idx < len(best_peaks) - 1:
            local_ibi = min(ibi[idx - 1], ibi[idx])
        else:
            continue

        if local_ibi < 0.3 * ref_ibi or local_ibi > 3.0 * ref_ibi:
            keep[idx] = False

    return best_peaks[keep]


def separate_vmd_heart_windowed(
    disp_hr: np.ndarray,
    hr_freq_hint: float | None = None,
    window_s: float = 60.0,
    step_s: float = 30.0,
) -> tuple[np.ndarray, dict]:
    """
    Run VMD on long signals window-by-window to avoid excessive memory use.

    Short signals still use the original full-length VMD path.
    """
    window_n = max(int(window_s * FS), 400)
    step_n = max(int(step_s * FS), 100)

    if len(disp_hr) <= window_n:
        heartbeat, info = separate_vmd_heart_only(disp_hr, hr_freq_hint=hr_freq_hint)
        info["windowed"] = False
        return heartbeat, info

    acc = np.zeros(len(disp_hr), dtype=np.float64)
    weights = np.zeros(len(disp_hr), dtype=np.float64)
    segments = []
    start = 0
    seg_idx = 0

    while start < len(disp_hr):
        end = min(start + window_n, len(disp_hr))
        segment = disp_hr[start:end]
        heartbeat_seg, seg_info = separate_vmd_heart_only(segment, hr_freq_hint=hr_freq_hint)

        seg_len = len(segment)
        hb_len = len(heartbeat_seg)
        if hb_len != seg_len:
            # VMD backends occasionally return a signal with an off-by-one length.
            if hb_len > seg_len:
                heartbeat_seg = np.asarray(heartbeat_seg[:seg_len], dtype=np.float64)
            else:
                pad_width = seg_len - hb_len
                heartbeat_seg = np.pad(
                    np.asarray(heartbeat_seg, dtype=np.float64),
                    (0, pad_width),
                    mode="edge",
                )
        else:
            heartbeat_seg = np.asarray(heartbeat_seg, dtype=np.float64)

        # Use a tapered overlap-add to reduce window-boundary jumps.
        if seg_len >= 8:
            taper = np.hanning(seg_len)
            if np.allclose(taper, 0):
                taper = np.ones(seg_len, dtype=np.float64)
            else:
                taper = np.maximum(taper, 1e-3)
        else:
            taper = np.ones(seg_len, dtype=np.float64)

        acc[start:end] += heartbeat_seg * taper
        weights[start:end] += taper

        segments.append(
            {
                "segment": seg_idx,
                "start_frame": int(start),
                "end_frame": int(end),
                "n_frames": int(end - start),
                "method": seg_info.get("method"),
                "heart_dom_freq_hz": seg_info.get("heart_dom_freq_hz"),
            }
        )

        if end >= len(disp_hr):
            break
        start += step_n
        seg_idx += 1

    weights[weights == 0] = 1.0
    heartbeat = acc / weights
    return heartbeat, {
        "method": "vmd_heart_windowed",
        "windowed": True,
        "window_s": window_s,
        "step_s": step_s,
        "n_segments": len(segments),
        "segments": segments,
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

    breath_bp = _sos_bandpass(disp_br, 0.1, 0.5)
    br_freq_bp = estimate_freq_periodogram(breath_bp, 0.1, 0.5)
    breath = breath_bp
    br_freq = br_freq_bp
    breath_sep = {"method": "bp_breath", "source": "br_bin_bandpass"}

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
    bp = detect_peaks_breath_robust(breath, lo_bpm=6, hi_bpm=30, br_freq_hint=br_freq)

    hrv = {}
    if len(hp) >= 4:
        ibi = np.diff(hp) / FS * 

