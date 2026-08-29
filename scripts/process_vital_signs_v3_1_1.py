"""v3.1.1 mainline with phase-stable selection and guarded HR fusion."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import signal

FS = 100.0
N_CH = 8
WAVELENGTH_MM = 5.0

SDK_DEFAULT_BIN_SPACING_M = 0.08
SDK_DEFAULT_RANGE_BIAS_M = 0.0

HR_LO_HZ = 0.8
HR_HI_HZ = 2.0
HR_LO_BPM = HR_LO_HZ * 60.0
HR_HI_BPM = HR_HI_HZ * 60.0
BR_LO_HZ = 0.1
BR_HI_HZ = 0.5
HR_TIME_FREQ_WARNING_BPM = 10.0
HEART_SIGNAL_QC_WINDOW_S = 10.0
MIN_HEART_WINDOW_STD_MM = 0.0005
MIN_HEART_CANDIDATE_COVERAGE = 0.50


class CandidateSelectionError(RuntimeError):
    """No finite, quality-eligible channel/range-bin candidate was returned."""

    def __init__(self, reason: str, summaries: list[dict] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.summaries = summaries or []


def _strict_json_value(value):
    """Convert NumPy values and non-finite floats to standard-JSON values."""
    if isinstance(value, dict):
        return {str(key): _strict_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strict_json_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_strict_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _strict_json_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def strict_json_dumps(payload: object, **kwargs) -> str:
    """Serialize only RFC-compliant JSON; NaN and Infinity can never be emitted."""
    return json.dumps(_strict_json_value(payload), allow_nan=False, **kwargs)


def load_radar_timestamps(path: Path) -> tuple[np.ndarray, np.ndarray]:
    frame_ids: list[int] = []
    timestamps_ms: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            try:
                frame_id = int(row[0])
                timestamp_ms = float(row[2] if len(row) >= 3 else row[1])
            except ValueError:
                continue
            frame_ids.append(frame_id)
            timestamps_ms.append(timestamp_ms)
    if not timestamps_ms:
        raise ValueError(f"No valid radar timestamps found in: {path}")
    return np.asarray(frame_ids, dtype=np.int64), np.asarray(timestamps_ms, dtype=np.float64)


def load_behavior_markers(path: Path) -> list[dict]:
    markers: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                unix_ms = float(row["unix_sec"]) * 1000.0
            except (KeyError, TypeError, ValueError):
                continue
            markers.append({"label": str(row.get("segment", "")).strip(), "unix_ms": unix_ms})
    if not markers:
        raise ValueError(f"No valid behavior markers found in: {path}")
    return sorted(markers, key=lambda item: item["unix_ms"])


def _nearest_frame_index(timestamps_ms: np.ndarray, timestamp_ms: float) -> int:
    insert_at = int(np.searchsorted(timestamps_ms, timestamp_ms, side="left"))
    if insert_at <= 0:
        return 0
    if insert_at >= len(timestamps_ms):
        return len(timestamps_ms) - 1
    before = insert_at - 1
    if abs(timestamps_ms[before] - timestamp_ms) <= abs(timestamps_ms[insert_at] - timestamp_ms):
        return before
    return insert_at


def _summarize_segment(result: dict, heart_peaks: np.ndarray, start_s: float, end_s: float, fs: float) -> dict:
    points = result.get("heart_rate", {}).get("time_course", {}).get("points", [])
    selected = [point for point in points if start_s <= float(point.get("time_s", -1)) < end_s]

    def median_value(key: str) -> float | None:
        values = [float(point[key]) for point in selected if point.get(key) is not None and np.isfinite(point[key])]
        return round(float(np.median(values)), 2) if values else None

    peak_times = np.asarray(heart_peaks, dtype=float) / fs
    n_peaks = int(np.count_nonzero((peak_times >= start_s) & (peak_times < end_s)))
    confidences = [float(point.get("confidence", 0.0)) for point in selected]
    usable = [bool(point.get("usable", point.get("confidence", 0.0) >= 0.25)) for point in selected]
    return {
        "n_hr_windows": len(selected),
        "n_heart_peaks": n_peaks,
        "time_median_bpm": median_value("time_bpm"),
        "freq_median_bpm": median_value("freq_bpm"),
        "fused_median_bpm": median_value("fused_bpm"),
        "mean_confidence": round(float(np.mean(confidences)), 3) if confidences else None,
        "usable_window_ratio": round(float(np.mean(usable)), 3) if usable else None,
    }


def attach_behavior_alignment(
    result: dict,
    waveforms: tuple,
    timestamps_path: Path,
    markers_path: Path | None = None,
    session_label: str | None = None,
    event_level_status: str | None = None,
    frame_start: int | None = None,
) -> dict:
    t, _, _, heart_peaks, _ = waveforms
    _, all_timestamps_ms = load_radar_timestamps(timestamps_path)
    inferred_legacy_offset = False
    if frame_start is None and len(all_timestamps_ms) - len(t) == 1000:
        selected_start = 1000
        inferred_legacy_offset = True
    else:
        selected_start = int(frame_start or 0)
    selected_end = selected_start + len(t)
    if selected_end > len(all_timestamps_ms):
        raise ValueError(
            f"Waveform/timestamp mismatch: selected frames {selected_start}:{selected_end}, "
            f"but timestamp file has {len(all_timestamps_ms)} rows"
        )
    timestamps_ms = all_timestamps_ms[selected_start:selected_end]
    fs = float(result.get("frame_rate_hz", FS))
    segments: list[dict] = []

    if markers_path is not None:
        markers = [marker for marker in load_behavior_markers(markers_path) if marker["label"] != "session_start"]
        for index, marker in enumerate(markers):
            start_index = _nearest_frame_index(timestamps_ms, marker["unix_ms"])
            if index + 1 < len(markers):
                end_index = _nearest_frame_index(timestamps_ms, markers[index + 1]["unix_ms"])
            else:
                end_index = len(timestamps_ms)
            start_index = max(0, min(start_index, len(timestamps_ms)))
            end_index = max(start_index, min(end_index, len(timestamps_ms)))
            start_s = start_index / fs
            end_s = end_index / fs
            segments.append(
                {
                    "label": marker["label"],
                    "start_s": round(start_s, 3),
                    "end_s": round(end_s, 3),
                    "duration_s": round(end_s - start_s, 3),
                    "start_sample": start_index,
                    "end_sample": end_index,
                    "marker_unix_ms": round(marker["unix_ms"], 3),
                    "hr_summary": _summarize_segment(result, np.asarray(heart_peaks), start_s, end_s, fs),
                }
            )
        status = "event_markers_aligned"
        source_type = "marker_csv"
    else:
        start_s = 0.0
        end_s = len(t) / fs
        segments.append(
            {
                "label": session_label or result.get("session", "session"),
                "start_s": start_s,
                "end_s": round(end_s, 3),
                "duration_s": round(end_s, 3),
                "start_sample": 0,
                "end_sample": len(t),
                "hr_summary": _summarize_segment(result, np.asarray(heart_peaks), start_s, end_s, fs),
            }
        )
        status = event_level_status or "session_only"
        source_type = "session_metadata"

    result["behavior_alignment"] = {
        "status": status,
        "source_type": source_type,
        "timestamps_path": str(timestamps_path),
        "markers_path": str(markers_path) if markers_path is not None else None,
        "timestamp_column": "python_receive_unix_ms",
        "mapping": "behavior timestamp -> nearest radar frame -> waveform sample index",
        "timestamp_rows": int(len(all_timestamps_ms)),
        "waveform_samples": int(len(t)),
        "selected_frame_start": selected_start,
        "legacy_first_chunk_offset_inferred": inferred_legacy_offset,
        "frame_count_matches": bool(len(timestamps_ms) == len(t)),
        "segments": segments,
    }
    result["data_completeness"] = {
        "radar_timestamp_rows": int(len(all_timestamps_ms)),
        "waveform_samples": int(len(t)),
        "leading_collector_frames_omitted": selected_start,
        "complete_against_timestamp_file": bool(selected_start == 0 and len(t) == len(all_timestamps_ms)),
    }
    return result


def plot_behavior_aligned_heart(result: dict, waveforms: tuple, output_dir: Path) -> Path | None:
    alignment = result.get("behavior_alignment", {})
    segments = alignment.get("segments", [])
    if alignment.get("status") != "event_markers_aligned" or not segments:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    t, _, heartbeat, heart_peaks, _ = waveforms
    heart_peaks = np.asarray(heart_peaks, dtype=int)
    n_rows = len(segments) + 2
    fig, axes = plt.subplots(n_rows, 1, figsize=(17, 2.35 * n_rows), constrained_layout=True)
    fig.suptitle(f"Behavior-aligned heart waveform - {result['session']} (complete record)", fontsize=14)

    axes[0].plot(t, heartbeat, color="#b91c1c", linewidth=0.35, alpha=0.8)
    axes[0].set_title("Complete heart waveform (no last-20-second truncation)")
    axes[0].set_ylabel("Displacement (mm)")
    axes[0].grid(True, alpha=0.25)

    course_points = result.get("heart_rate", {}).get("time_course", {}).get("points", [])
    if course_points:
        course_t = np.asarray([point["time_s"] for point in course_points], dtype=float)
        fused = np.asarray([np.nan if point.get("fused_bpm") is None else point["fused_bpm"] for point in course_points])
        local_freq = np.asarray([np.nan if point.get("freq_bpm") is None else point["freq_bpm"] for point in course_points])
        axes[1].plot(course_t, local_freq, color="#2563eb", linewidth=0.8, alpha=0.55, label="Local frequency")
        axes[1].plot(course_t, fused, color="#b91c1c", linewidth=1.7, label="Fused HR")
        axes[1].set_ylim(40, 140)
        axes[1].legend(loc="upper right", fontsize=8)
    axes[1].set_title("HR time course aligned to behavior markers")
    axes[1].set_ylabel("BPM")
    axes[1].grid(True, alpha=0.25)

    for boundary_segment in segments[1:]:
        boundary = boundary_segment["start_s"]
        for ax in axes[:2]:
            ax.axvline(boundary, color="#374151", ls=":", linewidth=0.9)
            ax.text(
                boundary,
                0.97,
                boundary_segment["label"],
                transform=ax.get_xaxis_transform(),
                ha="left",
                va="top",
                fontsize=8,
            )

    colors = ["#b91c1c", "#2563eb", "#047857", "#a16207", "#7c3aed"]
    for row, segment in enumerate(segments, start=2):
        start = int(segment["start_sample"])
        end = int(segment["end_sample"])
        mask_peaks = heart_peaks[(heart_peaks >= start) & (heart_peaks < end)]
        axes[row].plot(t[start:end], heartbeat[start:end], color=colors[(row - 2) % len(colors)], linewidth=0.45)
        axes[row].plot(t[mask_peaks], heartbeat[mask_peaks], "kx", markersize=2, alpha=0.5)
        summary = segment.get("hr_summary", {})
        axes[row].set_title(
            f"{segment['label']}: {segment['start_s']:.1f}-{segment['end_s']:.1f} s | "
            f"fused HR median {summary.get('fused_median_bpm')} BPM"
        )
        axes[row].set_ylabel("Displacement (mm)")
        axes[row].grid(True, alpha=0.25)
    axes[-1].set_xlabel("Analysis time (s)")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{result['session']}_heart_behavior_aligned.png"
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def extract_displacement(iq_fd: np.ndarray, bin_idx: int, ch: int) -> np.ndarray:
    phi = np.unwrap(np.angle(iq_fd[:, bin_idx, ch]))
    return WAVELENGTH_MM * phi / (4 * np.pi)


def _sos_bandpass(x: np.ndarray, lo_hz: float, hi_hz: float) -> np.ndarray:
    sos = signal.butter(4, [lo_hz, hi_hz], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def _load_vmd():
    # The production environment pins the small direct dependency.  Do not
    # silently switch to sktime's vendored copy because that changes the
    # dependency surface without changing the requested method.
    from vmdpy import VMD

    return VMD, "vmdpy"


def _heart_mode_score(mode_signal: np.ndarray, freqs: np.ndarray, hr_mask: np.ndarray, hr_freq_hint: float | None):
    _, pxx = signal.periodogram(mode_signal, fs=FS, window="hann")
    band_energy = float(np.sum(pxx[hr_mask]))
    if band_energy <= 0:
        return -np.inf, None
    dom_idx = int(np.argmax(pxx[hr_mask]))
    dom_freq = float(freqs[hr_mask][dom_idx])
    if not HR_LO_HZ <= dom_freq <= HR_HI_HZ:
        return -np.inf, dom_freq
    score = band_energy
    if hr_freq_hint is not None:
        # A high-energy respiratory harmonic must not displace the global heart-band anchor.
        score *= float(np.exp(-abs(dom_freq - hr_freq_hint) / 0.10))
    return score, dom_freq


def separate_vmd_heart_only(
    disp_hr: np.ndarray,
    hr_freq_hint: float | None = None,
    br_freq_hint: float | None = None,
) -> tuple[np.ndarray, dict]:
    if len(disp_hr) < 200:
        return _sos_bandpass(disp_hr, HR_LO_HZ, HR_HI_HZ), {
            "method": "bp_fallback_short_signal",
            "reason": "n_frames_lt_200",
        }

    VMD, backend = _load_vmd()
    # K=3 explicitly models respiration, heartbeat and residual/noise structure.
    u, _, omega = VMD(disp_hr, alpha=1000, tau=0, K=3, DC=False, init=1, tol=1e-6)

    freqs = np.fft.rfftfreq(len(disp_hr), d=1 / FS)
    hr_mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    br_mask = (freqs >= BR_LO_HZ) & (freqs <= BR_HI_HZ)
    mode_dom_freqs: list[float | None] = []
    mode_br_energy: list[float] = []
    for mode_signal in u:
        _, mode_pxx = signal.periodogram(mode_signal, fs=FS, window="hann")
        valid = (freqs > 0.0) & (freqs <= 5.0)
        mode_dom_freqs.append(float(freqs[valid][np.argmax(mode_pxx[valid])]) if np.any(valid) else None)
        mode_br_energy.append(float(np.sum(mode_pxx[br_mask])))

    if br_freq_hint is not None:
        breathing_idx = min(
            range(u.shape[0]),
            key=lambda idx: abs((mode_dom_freqs[idx] if mode_dom_freqs[idx] is not None else 99.0) - br_freq_hint),
        )
    else:
        breathing_idx = int(np.argmax(mode_br_energy))
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
                "role": "respiration" if k == breathing_idx else "heart_candidate",
                "center_freq_hz": round(center_freq, 3),
                "overall_dom_freq_hz": round(mode_dom_freqs[k], 3) if mode_dom_freqs[k] is not None else None,
                "dom_freq_hz": round(dom_freq, 3) if dom_freq is not None else None,
                "score": round(float(score), 3) if np.isfinite(score) else None,
            }
        )
        if score > best_score:
            best_score = score
            best_idx = k
            best_freq = dom_freq

    if best_idx is None or not np.isfinite(best_score):
        return _sos_bandpass(disp_hr, HR_LO_HZ, HR_HI_HZ), {
            "method": "bp_fallback_no_valid_mode",
            "reason": "no_valid_heart_mode",
            "backend": backend,
            "modes": mode_summary,
        }

    heartbeat = u[best_idx]
    for mode in mode_summary:
        if mode["mode"] == best_idx and best_idx == breathing_idx:
            mode["role"] = "respiration_heart_mixed"
        elif mode["mode"] == best_idx:
            mode["role"] = "heartbeat"
        elif mode["mode"] != breathing_idx:
            mode["role"] = "noise_residual"
    if best_freq is not None:
        lo = max(HR_LO_HZ, best_freq - 0.35)
        hi = min(HR_HI_HZ, best_freq + 0.35)
        if hi > lo:
            heartbeat = _sos_bandpass(heartbeat, lo, hi)

    return heartbeat, {
        "method": "vmd_heart_only",
        "backend": backend,
        "k": 3,
        "decomposition_roles": ["respiration", "heartbeat", "noise_residual"],
        "mixed_respiration_heart_mode": bool(best_idx == breathing_idx),
        "breath_frequency_hint_hz": round(float(br_freq_hint), 3) if br_freq_hint is not None else None,
        "breath_mode": int(breathing_idx),
        "heart_mode": int(best_idx),
        "heart_dom_freq_hz": round(float(best_freq), 3) if best_freq is not None else None,
        "modes": mode_summary,
    }


def _autocorr_period_breath(x: np.ndarray, lo_bpm: float = 6, hi_bpm: float = 30):
    x = np.asarray(x)
    if len(x) < 10:
        return None
    x0 = x - np.mean(x)
    ac = signal.correlate(x0, x0, mode="full")
    ac = ac[len(ac) // 2 :]
    min_lag = int(FS * 60 / hi_bpm)
    max_lag = int(FS * 60 / lo_bpm)
    max_lag = min(max_lag, len(ac) - 1)
    if min_lag >= max_lag:
        return None
    peaks, _ = signal.find_peaks(ac[min_lag : max_lag + 1])
    if len(peaks) == 0:
        return None
    best_lag = min_lag + peaks[int(np.argmax(ac[min_lag + peaks]))]
    return best_lag / FS


def detect_peaks_breath_robust(
    x: np.ndarray,
    lo_bpm: float = 6,
    hi_bpm: float = 30,
    br_freq_hint: float | None = None,
) -> np.ndarray:
    x = np.asarray(x)
    x_std = np.std(x)
    if x_std < 1e-8:
        return np.array([], dtype=int)

    win = max(5, int(FS * 0.35))
    if win % 2 == 0:
        win += 1
    if win >= len(x):
        win = len(x) - 1 if len(x) % 2 == 0 else len(x)
    if win >= 5:
        xs = signal.savgol_filter(x, window_length=win, polyorder=2, mode="interp")
    else:
        xs = x.copy()

    ref_period = _autocorr_period_breath(xs, lo_bpm=lo_bpm, hi_bpm=hi_bpm)
    if br_freq_hint is not None and br_freq_hint > 0:
        hint_period = 1.0 / br_freq_hint
        if ref_period is None:
            ref_period = hint_period
        else:
            ref_period = 0.6 * ref_period + 0.4 * hint_period

    min_dist = int(FS * 60 / hi_bpm)
    if ref_period is not None:
        min_dist = max(min_dist, int(0.7 * ref_period * FS))

    best_peaks = np.array([], dtype=int)
    best_score = -np.inf

    for prom_factor in [0.40, 0.32, 0.26, 0.20, 0.14, 0.10]:
        prominence = max(prom_factor * np.std(xs), 1e-6)
        peaks, _ = signal.find_peaks(xs, distance=min_dist, prominence=prominence)
        if len(peaks) < 2:
            continue

        ibi = np.diff(peaks) / FS
        valid = ibi[(ibi >= 60 / hi_bpm) & (ibi <= 60 / lo_bpm)]
        if len(valid) < 1:
            continue

        cv = np.std(valid) / max(np.mean(valid), 1e-6) if len(valid) >= 2 else 0.0
        score = len(peaks) * (1 - min(cv, 1))

        if ref_period is not None:
            score /= 1 + abs(np.mean(valid) - ref_period)

        time_bpm = 60.0 / max(np.mean(valid), 1e-6)
        if br_freq_hint is not None and br_freq_hint > 0:
            br_bpm_hint = br_freq_hint * 60.0
            score /= 1 + abs(time_bpm - br_bpm_hint) / 6.0

        expected_cycles = (len(x) / FS) * ((br_freq_hint * 60.0) if br_freq_hint else time_bpm) / 60.0
        if expected_cycles > 0:
            score /= 1 + abs(len(peaks) - expected_cycles) / max(expected_cycles, 1.0)

        if score > best_score:
            best_score = score
            best_peaks = peaks.copy()

    if len(best_peaks) < 2:
        return np.array([], dtype=int)

    ref_interval = ref_period
    if ref_interval is None:
        ref_interval = np.median(np.diff(best_peaks) / FS)

    cleaned = [int(best_peaks[0])]
    for idx in range(1, len(best_peaks)):
        gap = (best_peaks[idx] - cleaned[-1]) / FS
        if gap < 0.5 * ref_interval:
            continue
        if 1.7 * ref_interval < gap < 3.0 * ref_interval:
            est = cleaned[-1] + int(ref_interval * FS)
            lo = max(0, est - int(0.35 * FS))
            hi = min(len(xs), est + int(0.35 * FS))
            if hi > lo:
                repaired = lo + int(np.argmax(xs[lo:hi]))
                cleaned.append(repaired)
        cleaned.append(int(best_peaks[idx]))

    cleaned = np.array(cleaned, dtype=int)
    if len(cleaned) < 2:
        return cleaned

    intervals = np.diff(cleaned) / FS
    ok = np.ones(len(cleaned), dtype=bool)
    for i in range(1, len(cleaned)):
        if intervals[i - 1] < 0.5 * ref_interval or intervals[i - 1] > 2.5 * ref_interval:
            ok[i] = False
    return cleaned[ok]


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
            local_idx = int(np.argmax(candidate_powers[close_mask]))
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


def _movmean(x: np.ndarray, win: int = 5) -> np.ndarray:
    if win <= 1 or len(x) < 3:
        return np.asarray(x, dtype=np.float64)
    kernel = np.ones(win, dtype=np.float64) / float(win)
    return np.convolve(np.asarray(x, dtype=np.float64), kernel, mode="same")


def _breath_remove_baseline(disp_br: np.ndarray) -> np.ndarray:
    disp_br = np.asarray(disp_br, dtype=np.float64)
    if disp_br.size < 4:
        return disp_br - np.mean(disp_br)
    return signal.detrend(disp_br, type="linear")


def _breath_preprocess_matlab_style(disp_br: np.ndarray) -> np.ndarray:
    disp_br = _breath_remove_baseline(disp_br)
    diff_sig = np.diff(disp_br, prepend=disp_br[0])
    smooth_sig = _movmean(diff_sig, win=5)
    return _sos_bandpass(smooth_sig, 0.1, 0.5)


def _breath_band_metrics(breath: np.ndarray) -> dict:
    freqs, pxx = signal.periodogram(breath, fs=FS, window="hann")
    mask = (freqs >= 0.1) & (freqs <= 0.5)
    if not np.any(mask):
        return {"top_hz": None, "top_power": 0.0, "median_power": 0.0, "snr_like": 0.0, "band_power": 0.0}
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


def _score_breath_candidate(breath: np.ndarray, br_freq_hz: float | None, bp: np.ndarray) -> tuple[float, dict]:
    metrics = _breath_band_metrics(breath)
    time_bpm = None
    if len(bp) >= 2:
        time_bpm = float(60.0 * FS / np.mean(np.diff(bp)))
    freq_bpm = float(br_freq_hz * 60.0) if br_freq_hz else None
    mismatch = abs(freq_bpm - time_bpm) if (freq_bpm is not None and time_bpm is not None) else 20.0
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


def _select_breath_candidate(disp_br: np.ndarray) -> tuple[np.ndarray, float | None, np.ndarray, dict]:
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


def _finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _robust_time_bpm(peak_times_s: np.ndarray, reference_bpm: float | None) -> tuple[float | None, float]:
    if len(peak_times_s) < 4:
        return None, 0.0
    ibi = np.diff(peak_times_s)
    ibi = ibi[(ibi >= 60.0 / HR_HI_BPM) & (ibi <= 60.0 / HR_LO_BPM)]
    if len(ibi) < 3:
        return None, 0.0
    if reference_bpm is not None and HR_LO_BPM <= reference_bpm <= HR_HI_BPM:
        reference_ibi = 60.0 / reference_bpm
        multiples = np.maximum(1, np.rint(ibi / reference_ibi).astype(int))
        missed = (multiples >= 2) & (multiples <= 3) & (np.abs(ibi / multiples - reference_ibi) <= 0.22 * reference_ibi)
        ibi = ibi.copy()
        ibi[missed] /= multiples[missed]
    median_ibi = float(np.median(ibi))
    abs_dev = np.abs(ibi - median_ibi)
    mad = float(np.median(abs_dev))
    tolerance = max(0.10, 3.5 * 1.4826 * mad, 0.20 * median_ibi)
    clean = ibi[abs_dev <= tolerance]
    if len(clean) < 3:
        return None, 0.0
    bpm = 60.0 / float(np.median(clean))
    robust_cv = 1.4826 * float(np.median(np.abs(clean - np.median(clean)))) / max(float(np.median(clean)), 1e-6)
    count_quality = min(1.0, len(clean) / 10.0)
    regularity_quality = float(np.exp(-5.0 * robust_cv))
    return bpm, float(np.clip(count_quality * regularity_quality, 0.0, 1.0))


def _fold_harmonic(value_bpm: float | None, anchor_bpm: float | None, lo_bpm: float, hi_bpm: float) -> tuple[float | None, bool]:
    if value_bpm is None or anchor_bpm is None:
        return value_bpm, False
    value_bpm = float(value_bpm)
    anchor_bpm = float(anchor_bpm)
    half = value_bpm / 2.0
    if lo_bpm <= half <= hi_bpm and abs(half - anchor_bpm) <= 0.20 * anchor_bpm:
        return half, True
    double = value_bpm * 2.0
    if lo_bpm <= double <= hi_bpm and abs(double - anchor_bpm) <= 0.20 * anchor_bpm:
        return double, True
    return value_bpm, False


def _spectral_candidates(segment: np.ndarray, fs: float, lo_bpm: float, hi_bpm: float) -> tuple[np.ndarray, np.ndarray]:
    if len(segment) < max(16, int(round(4.0 * fs))):
        return np.array([], dtype=float), np.array([], dtype=float)
    centered = signal.detrend(np.asarray(segment, dtype=float), type="linear")
    nfft = 1 << int(np.ceil(np.log2(max(len(centered) * 8, 256))))
    freqs, pxx = signal.periodogram(centered, fs=fs, window="hann", nfft=nfft, scaling="spectrum")
    mask = (freqs >= lo_bpm / 60.0) & (freqs <= hi_bpm / 60.0)
    band_freqs = freqs[mask]
    band_power = pxx[mask]
    if len(band_freqs) < 3 or not np.any(band_power > 0):
        return np.array([], dtype=float), np.array([], dtype=float)
    peak_idx, _ = signal.find_peaks(band_power)
    if len(peak_idx) == 0:
        peak_idx = np.array([int(np.argmax(band_power))])
    order = peak_idx[np.argsort(band_power[peak_idx])[::-1]][:8]
    return band_freqs[order] * 60.0, band_power[order]


def _select_spectral_bpm(
    segment: np.ndarray,
    fs: float,
    lo_bpm: float,
    hi_bpm: float,
    time_bpm: float | None,
    previous_bpm: float | None,
    reference_bpm: float | None,
) -> tuple[float | None, float]:
    candidates, powers = _spectral_candidates(segment, fs, lo_bpm, hi_bpm)
    if len(candidates) == 0:
        return None, 0.0
    relative_power = powers / max(float(np.max(powers)), 1e-12)
    scores = np.log(np.maximum(relative_power, 1e-8))
    if time_bpm is not None:
        scores -= 0.035 * np.abs(candidates - time_bpm)
    if previous_bpm is not None:
        scores -= 0.025 * np.abs(candidates - previous_bpm)
    if reference_bpm is not None:
        scores -= 0.010 * np.abs(candidates - reference_bpm)
    best = int(np.argmax(scores))
    selected = float(candidates[best])
    selected, harmonic_folded = _fold_harmonic(selected, time_bpm or previous_bpm or reference_bpm, lo_bpm, hi_bpm)
    if not harmonic_folded and reference_bpm is not None:
        selected, harmonic_folded = _fold_harmonic(selected, reference_bpm, lo_bpm, hi_bpm)
    quality = float(np.sqrt(relative_power[best]))
    if time_bpm is not None:
        quality *= float(np.exp(-abs(selected - time_bpm) / 20.0))
    if harmonic_folded:
        quality *= 0.85
    return selected, float(np.clip(quality, 0.0, 1.0))


def _smooth_track(values: np.ndarray, confidence: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    confidence = np.asarray(confidence, dtype=float)
    if len(values) == 0 or not np.any(np.isfinite(values)):
        return values.copy()
    valid = np.isfinite(values)
    x = np.arange(len(values), dtype=float)
    filled = values.copy()
    reliable = valid & np.isfinite(confidence) & (confidence >= 0.12)
    anchors = reliable if np.count_nonzero(reliable) >= 2 else valid
    filled[~anchors] = np.interp(x[~anchors], x[anchors], values[anchors])
    if len(filled) >= 3:
        filled = signal.medfilt(filled, kernel_size=3)
    smoothed = filled.copy()
    max_step_bpm = 7.0
    for idx in range(1, len(smoothed)):
        alpha = 0.20 + 0.30 * float(np.clip(confidence[idx], 0.0, 1.0))
        target = alpha * filled[idx] + (1.0 - alpha) * smoothed[idx - 1]
        smoothed[idx] = np.clip(target, smoothed[idx - 1] - max_step_bpm, smoothed[idx - 1] + max_step_bpm)
    for idx in range(len(smoothed) - 2, -1, -1):
        alpha = 0.20 + 0.30 * float(np.clip(confidence[idx], 0.0, 1.0))
        target = alpha * smoothed[idx] + (1.0 - alpha) * smoothed[idx + 1]
        smoothed[idx] = np.clip(target, smoothed[idx + 1] - max_step_bpm, smoothed[idx + 1] + max_step_bpm)
    return smoothed


def _summary_metrics(time_bpms: np.ndarray, freq_bpms: np.ndarray, fused_bpms: np.ndarray, confidence: np.ndarray) -> dict:
    valid_fused = fused_bpms[np.isfinite(fused_bpms)]
    both = np.isfinite(time_bpms) & np.isfinite(freq_bpms)
    agreement = np.abs(time_bpms[both] - freq_bpms[both])
    jumps = np.abs(np.diff(valid_fused)) if len(valid_fused) >= 2 else np.array([], dtype=float)
    high_quality = both & (np.abs(time_bpms - freq_bpms) <= 5.0) & (confidence >= 0.50)
    usable_quality = both & (np.abs(time_bpms - freq_bpms) <= 12.0) & (confidence >= 0.20)
    return {
        "n_points": int(len(fused_bpms)),
        "coverage_pct": round(100.0 * float(np.mean(np.isfinite(fused_bpms))), 1) if len(fused_bpms) else 0.0,
        "median_bpm": round(float(np.median(valid_fused)), 1) if len(valid_fused) else None,
        "std_bpm": round(float(np.std(valid_fused)), 2) if len(valid_fused) else None,
        "jump_p95_bpm": round(float(np.percentile(jumps, 95)), 2) if len(jumps) else None,
        "time_freq_agreement_median_bpm": round(float(np.median(agreement)), 2) if len(agreement) else None,
        "time_freq_agreement_p95_bpm": round(float(np.percentile(agreement, 95)), 2) if len(agreement) else None,
        "time_freq_within_5bpm_pct": round(100.0 * float(np.mean(agreement <= 5.0)), 1) if len(agreement) else None,
        "median_confidence": round(float(np.nanmedian(confidence)), 3) if np.any(np.isfinite(confidence)) else None,
        "high_quality_pct": round(100.0 * float(np.mean(high_quality)), 1) if len(fused_bpms) else 0.0,
        "usable_quality_pct": round(100.0 * float(np.mean(usable_quality)), 1) if len(fused_bpms) else 0.0,
    }


def _interval_metrics(intervals_s: np.ndarray) -> dict:
    intervals_s = np.asarray(intervals_s, dtype=float)
    intervals_s = intervals_s[np.isfinite(intervals_s) & (intervals_s > 0)]
    if len(intervals_s) == 0:
        return {
            "n_intervals": 0,
            "median_bpm": None,
            "std_bpm": None,
            "jump_p95_bpm": None,
            "jumps_over_10bpm_pct": None,
            "p01_bpm": None,
            "p99_bpm": None,
        }
    bpm = 60.0 / intervals_s
    jumps = np.abs(np.diff(bpm)) if len(bpm) >= 2 else np.array([], dtype=float)
    return {
        "n_intervals": int(len(bpm)),
        "median_bpm": round(float(np.median(bpm)), 1) if len(bpm) else None,
        "std_bpm": round(float(np.std(bpm)), 2) if len(bpm) else None,
        "jump_p95_bpm": round(float(np.percentile(jumps, 95)), 2) if len(jumps) else None,
        "jumps_over_10bpm_pct": round(100.0 * float(np.mean(jumps > 10.0)), 1) if len(jumps) else None,
        "p01_bpm": round(float(np.percentile(bpm, 1)), 1) if len(bpm) else None,
        "p99_bpm": round(float(np.percentile(bpm, 99)), 1) if len(bpm) else None,
    }


def _raw_beat_metrics(peaks: np.ndarray, fs: float) -> dict:
    peaks = np.asarray(peaks, dtype=int)
    return _interval_metrics(np.diff(peaks) / float(fs)) if len(peaks) >= 2 else _interval_metrics(np.array([]))


def estimate_hr_time_course(
    heartbeat: np.ndarray,
    peaks: np.ndarray,
    fs: float,
    reference_bpm: float | None = None,
    window_s: float = 25.0,
    step_s: float = 5.0,
    lo_bpm: float = HR_LO_BPM,
    hi_bpm: float = HR_HI_BPM,
) -> dict:
    heartbeat = np.asarray(heartbeat, dtype=float)
    peaks = np.asarray(peaks, dtype=int)
    duration_s = len(heartbeat) / float(fs)
    if len(heartbeat) == 0 or duration_s < 4.0:
        return {
            "method": "robust_local_ibi_spectrum_fusion_v311_hard_signal_gate",
            "window_s": float(window_s),
            "step_s": float(step_s),
            "points": [],
            "signal_quality": {
                "window_s": HEART_SIGNAL_QC_WINDOW_S,
                "min_std_mm": MIN_HEART_WINDOW_STD_MM,
                "usable_count": 0,
                "rejected_count": 0,
                "usable_ratio": 0.0,
            },
            "metrics": _summary_metrics(*(np.array([], dtype=float) for _ in range(4))),
        }

    centers = np.arange(0.0, duration_s + 0.5 * step_s, step_s)
    half_window = 0.5 * window_s
    peak_times = peaks / float(fs)
    time_values: list[float] = []
    freq_values: list[float] = []
    fused_values: list[float] = []
    confidence_values: list[float] = []
    disagreement_warnings: list[bool] = []
    signal_std_values: list[float] = []
    signal_usable_values: list[bool] = []
    previous_bpm = reference_bpm

    for center in centers:
        if duration_s <= window_s:
            start_s = 0.0
            end_s = duration_s
        else:
            start_s = float(np.clip(center - half_window, 0.0, duration_s - window_s))
            end_s = start_s + window_s
        start_idx = int(round(start_s * fs))
        end_idx = int(round(end_s * fs))
        if duration_s <= HEART_SIGNAL_QC_WINDOW_S:
            qc_start_s = 0.0
            qc_end_s = duration_s
        else:
            qc_start_s = float(
                np.clip(center - 0.5 * HEART_SIGNAL_QC_WINDOW_S, 0.0, duration_s - HEART_SIGNAL_QC_WINDOW_S)
            )
            qc_end_s = qc_start_s + HEART_SIGNAL_QC_WINDOW_S
        qc_start_idx = int(round(qc_start_s * fs))
        qc_end_idx = int(round(qc_end_s * fs))
        signal_std_10s = float(np.std(heartbeat[qc_start_idx:qc_end_idx]))
        signal_usable = bool(np.isfinite(signal_std_10s) and signal_std_10s >= MIN_HEART_WINDOW_STD_MM)
        signal_std_values.append(signal_std_10s)
        signal_usable_values.append(signal_usable)

        if not signal_usable:
            time_values.append(np.nan)
            freq_values.append(np.nan)
            fused_values.append(np.nan)
            confidence_values.append(0.0)
            disagreement_warnings.append(False)
            continue

        local_peak_times = peak_times[(peak_times >= start_s) & (peak_times < end_s)]
        anchor_bpm = previous_bpm or reference_bpm
        time_bpm, time_quality = _robust_time_bpm(local_peak_times, anchor_bpm)
        time_bpm, time_harmonic_folded = _fold_harmonic(time_bpm, anchor_bpm, lo_bpm, hi_bpm)
        if not time_harmonic_folded and reference_bpm is not None:
            time_bpm, time_harmonic_folded = _fold_harmonic(time_bpm, reference_bpm, lo_bpm, hi_bpm)
        if time_harmonic_folded:
            time_quality *= 0.85
        freq_bpm, freq_quality = _select_spectral_bpm(
            heartbeat[start_idx:end_idx], fs, lo_bpm, hi_bpm, time_bpm, previous_bpm, reference_bpm
        )

        if time_bpm is not None and freq_bpm is not None:
            gap = abs(time_bpm - freq_bpm)
            agreement_quality = float(np.exp(-gap / 12.0))
            wt = max(0.05, time_quality)
            wf = max(0.05, freq_quality)
            disagreement_warning = gap > HR_TIME_FREQ_WARNING_BPM
            if not disagreement_warning:
                fused = (wt * time_bpm + wf * freq_bpm) / (wt + wf)
                confidence = agreement_quality * np.sqrt(time_quality * freq_quality)
            else:
                anchor = anchor_bpm if anchor_bpm is not None else time_bpm
                if abs(time_bpm - anchor) <= abs(freq_bpm - anchor):
                    fused = time_bpm
                    confidence = 0.10 * time_quality * agreement_quality
                else:
                    fused = freq_bpm
                    confidence = 0.10 * freq_quality * agreement_quality
        elif time_bpm is not None:
            fused = time_bpm
            confidence = 0.45 * time_quality
            disagreement_warning = False
        elif freq_bpm is not None:
            fused = freq_bpm
            confidence = 0.35 * freq_quality
            disagreement_warning = False
        else:
            fused = np.nan
            confidence = 0.0
            disagreement_warning = False

        if np.isfinite(fused) and (previous_bpm is None or confidence >= 0.12):
            previous_bpm = float(fused) if previous_bpm is None else 0.8 * float(previous_bpm) + 0.2 * float(fused)
        time_values.append(np.nan if time_bpm is None else time_bpm)
        freq_values.append(np.nan if freq_bpm is None else freq_bpm)
        fused_values.append(float(fused))
        confidence_values.append(float(np.clip(confidence, 0.0, 1.0)))
        disagreement_warnings.append(bool(disagreement_warning))

    time_arr = np.asarray(time_values, dtype=float)
    freq_arr = np.asarray(freq_values, dtype=float)
    fused_raw = np.asarray(fused_values, dtype=float)
    confidence_arr = np.asarray(confidence_values, dtype=float)
    signal_usable_arr = np.asarray(signal_usable_values, dtype=bool)
    fused_smooth = _smooth_track(fused_raw, confidence_arr)
    # Hard-rejected weak windows must remain missing after interpolation/smoothing.
    fused_smooth[~signal_usable_arr] = np.nan

    points = []
    for idx, center in enumerate(centers):
        gap = abs(float(time_values[idx]) - float(freq_values[idx])) if np.isfinite(time_values[idx]) and np.isfinite(freq_values[idx]) else None
        if not signal_usable_values[idx]:
            quality = "rejected"
        elif gap is not None and gap <= 5.0 and confidence_values[idx] >= 0.50:
            quality = "high"
        elif gap is not None and gap <= 12.0 and confidence_values[idx] >= 0.20:
            quality = "medium"
        else:
            quality = "low"
        points.append(
            {
                "time_s": round(float(center), 2),
                "time_bpm": round(time_values[idx], 2) if np.isfinite(time_values[idx]) else None,
                "freq_bpm": round(freq_values[idx], 2) if np.isfinite(freq_values[idx]) else None,
                "fused_raw_bpm": round(fused_values[idx], 2) if np.isfinite(fused_values[idx]) else None,
                "fused_bpm": round(float(fused_smooth[idx]), 2) if np.isfinite(fused_smooth[idx]) else None,
                "confidence": round(confidence_values[idx], 3),
                "time_freq_gap_bpm": round(gap, 2) if gap is not None else None,
                "agreement_warning": disagreement_warnings[idx],
                "warning": (
                    "weak_heart_signal_std_below_threshold"
                    if not signal_usable_values[idx]
                    else ("time_frequency_gap_gt_10_bpm" if disagreement_warnings[idx] else None)
                ),
                "signal_qc_window_s": HEART_SIGNAL_QC_WINDOW_S,
                "signal_std_10s_mm": round(signal_std_values[idx], 8),
                "signal_usable": signal_usable_values[idx],
                "quality": quality,
            }
        )

    valid_time = time_arr[np.isfinite(time_arr)]
    valid_freq = freq_arr[np.isfinite(freq_arr)]
    valid_fused = fused_smooth[np.isfinite(fused_smooth)]
    if len(centers) == 1:
        nearest_center_idx = np.zeros(len(peak_times), dtype=int)
    else:
        right = np.clip(np.searchsorted(centers, peak_times), 1, len(centers) - 1)
        left = right - 1
        nearest_center_idx = np.where(
            np.abs(peak_times - centers[left]) <= np.abs(centers[right] - peak_times), left, right
        )
    peak_signal_usable = signal_usable_arr[nearest_center_idx] if len(peaks) else np.array([], dtype=bool)
    gated_peaks = peaks[peak_signal_usable]
    gated_intervals_s = np.diff(peaks) / float(fs) if len(peaks) >= 2 else np.array([], dtype=float)
    if len(gated_intervals_s):
        gated_intervals_s = gated_intervals_s[peak_signal_usable[:-1] & peak_signal_usable[1:]]
    usable_count = int(np.count_nonzero(signal_usable_arr))
    rejected_count = int(len(signal_usable_arr) - usable_count)
    usable_ratio = float(np.mean(signal_usable_arr)) if len(signal_usable_arr) else 0.0
    return {
        "method": "robust_local_ibi_spectrum_fusion_v311_hard_signal_gate",
        "window_s": float(window_s),
        "step_s": float(step_s),
        "reference_bpm": round(float(reference_bpm), 1) if reference_bpm is not None else None,
        "time_median_bpm": round(float(np.median(valid_time)), 1) if len(valid_time) else None,
        "freq_median_bpm": round(float(np.median(valid_freq)), 1) if len(valid_freq) else None,
        "fused_median_bpm": round(float(np.median(valid_fused)), 1) if len(valid_fused) else None,
        "raw_beat_metrics": _interval_metrics(gated_intervals_s),
        "raw_beat_metrics_all_windows": _raw_beat_metrics(peaks, fs),
        "n_peaks_signal_usable": int(len(gated_peaks)),
        "signal_quality": {
            "window_s": HEART_SIGNAL_QC_WINDOW_S,
            "min_std_mm": MIN_HEART_WINDOW_STD_MM,
            "usable_count": usable_count,
            "rejected_count": rejected_count,
            "usable_ratio": round(usable_ratio, 4),
            "hard_gate_passed": bool(usable_ratio >= MIN_HEART_CANDIDATE_COVERAGE),
            "candidate_min_usable_ratio": MIN_HEART_CANDIDATE_COVERAGE,
            "median_std_mm": round(float(np.median(signal_std_values)), 8) if signal_std_values else None,
            "min_observed_std_mm": round(float(np.min(signal_std_values)), 8) if signal_std_values else None,
        },
        "self_check": {
            "time_frequency_warning_threshold_bpm": HR_TIME_FREQ_WARNING_BPM,
            "warning_count": int(sum(disagreement_warnings)),
            "warning_ratio": round(float(np.mean(disagreement_warnings)), 3) if disagreement_warnings else 0.0,
            "weak_signal_rejected_count": rejected_count,
            "weak_signal_rejected_ratio": round(1.0 - usable_ratio, 4),
        },
        "points": points,
        "metrics": _summary_metrics(time_arr, freq_arr, fused_smooth, confidence_arr),
    }


def _peak_signal_gate_mask(peaks: np.ndarray, fs: float, time_course: dict) -> np.ndarray:
    peaks = np.asarray(peaks, dtype=int)
    points = time_course.get("points", [])
    if len(peaks) == 0 or not points:
        return np.zeros(len(peaks), dtype=bool)
    centers = np.asarray([point["time_s"] for point in points], dtype=float)
    usable = np.asarray([bool(point.get("signal_usable", False)) for point in points], dtype=bool)
    peak_times = peaks / float(fs)
    if len(centers) == 1:
        nearest = np.zeros(len(peaks), dtype=int)
    else:
        right = np.clip(np.searchsorted(centers, peak_times), 1, len(centers) - 1)
        left = right - 1
        nearest = np.where(
            np.abs(peak_times - centers[left]) <= np.abs(centers[right] - peak_times), left, right
        )
    return usable[nearest]


def _filter_peaks_by_signal_gate(peaks: np.ndarray, fs: float, time_course: dict) -> np.ndarray:
    peaks = np.asarray(peaks, dtype=int)
    return peaks[_peak_signal_gate_mask(peaks, fs, time_course)]


def _iter_tx_keys(npz_obj) -> list[str]:
    return sorted([key for key in npz_obj.keys() if key.startswith("tx")])


def _load_chunk(path: Path) -> np.ndarray:
    with np.load(path) as data:
        keys = _iter_tx_keys(data)
        if not keys:
            raise RuntimeError(f"No tx* arrays found in chunk: {path}")
        return np.stack([data[key] for key in keys], axis=-1).astype(np.complex64)


def _as_range_cube(iq_chunk: np.ndarray) -> np.ndarray:
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
    matched_pattern = pattern
    if not files:
        matched_pattern = pattern.replace("sub-SXQ", "sub-sxq")
        files = sorted(parts_dir.glob(matched_pattern))
    marker = "_part*.npz"
    if marker in matched_pattern:
        base_name = matched_pattern.replace(marker, ".npz")
        base_files = sorted(parts_dir.glob(base_name))
        if base_files:
            files = base_files + files
    return files


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
) -> tuple[int, int, list[tuple[int, float, float, float, float, float]]]:
    bin_power = np.asarray(bin_power_acc[:, best_ch], dtype=np.float64)
    freqs = np.fft.rfftfreq(n_frames_sample, d=1 / FS)

    if n_frames_sample < 8 or iq_fd_sample.shape[0] < 8:
        raise CandidateSelectionError("INSUFFICIENT_SELECTION_FRAMES")
    if not np.all(np.isfinite(bin_power)):
        raise CandidateSelectionError("NONFINITE_RANGE_POWER")
    positive_power = bin_power[bin_power > 0.0]
    if positive_power.size == 0:
        raise CandidateSelectionError("EMPTY_OR_ZERO_RANGE_POWER")
    hr_mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    br_mask = (freqs >= BR_LO_HZ) & (freqs <= BR_HI_HZ)
    noise_mask = (freqs >= 2.5) & (freqs <= 5.0)
    if not np.any(hr_mask) or not np.any(br_mask) or not np.any(noise_mask):
        raise CandidateSelectionError("EMPTY_SPECTRAL_BASELINE")

    def build_candidates(require_phi_var: bool) -> list[tuple[int, float, float, float, float, float]]:
        power_thresh = float(np.max(positive_power)) * 0.01
        local_candidates: list[tuple[int, float, float, float, float, float]] = []
        for bin_idx in range(bin_power.shape[0]):
            if bin_power[bin_idx] < power_thresh:
                continue
            phi = np.unwrap(np.angle(iq_fd_sample[:, bin_idx, best_ch]))
            if not np.all(np.isfinite(phi)):
                continue
            phi_var = float(np.var(phi))
            if not np.isfinite(phi_var):
                continue
            if require_phi_var and not (0.1 < phi_var < 50):
                continue
            phi_detrended = signal.detrend(phi, type="linear")
            pxx = np.abs(np.fft.rfft(phi_detrended)) ** 2
            if not np.all(np.isfinite(pxx)):
                continue
            noise_raw = float(np.mean(pxx[noise_mask]))
            if not np.isfinite(noise_raw) or noise_raw < 0.0:
                continue
            noise = max(noise_raw, 1e-10)
            hr_snr = float(np.mean(pxx[hr_mask]) / noise)
            br_snr = float(np.mean(pxx[br_mask]) / noise)
            phase_stability, _ = _phase_stability_score(phi)
            br_score = float(br_snr * phase_stability)
            # Compress SNR so one large spectral spike cannot overwhelm phase roughness.
            heart_score = float(np.log1p(max(hr_snr, 0.0)) * phase_stability**2)
            if not all(np.isfinite(value) for value in (hr_snr, br_snr, phase_stability, br_score, heart_score)):
                continue
            local_candidates.append((int(bin_idx), hr_snr, br_snr, br_score, phase_stability, heart_score))
        return local_candidates

    candidates = build_candidates(require_phi_var=True)
    if not candidates:
        candidates = build_candidates(require_phi_var=False)
    if not candidates:
        raise CandidateSelectionError("NO_FINITE_CHANNEL_BIN_CANDIDATES")
    br_bin = max(candidates, key=lambda item: item[3])[0]
    hr_bin = max(candidates, key=lambda item: item[5])[0]
    return br_bin, hr_bin, candidates


def estimate_freq_periodogram(x: np.ndarray, lo_hz: float, hi_hz: float) -> float | None:
    freqs, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (freqs >= lo_hz) & (freqs <= hi_hz)
    if not np.any(mask):
        return None
    return float(freqs[mask][np.argmax(pxx[mask])])


def detect_peaks_heart_lo(x: np.ndarray, lo_bpm: float = HR_LO_BPM, hi_bpm: float = HR_HI_BPM) -> np.ndarray:
    x_std = float(np.std(x))
    if x_std < 1e-8:
        return np.array([], dtype=int)

    min_dist = max(int(FS * 60 / hi_bpm), int(FS * 0.3))
    best_peaks = np.array([], dtype=int)
    best_score = -1.0

    for prom_factor in [0.1, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01]:
        peaks, _ = signal.find_peaks(x, distance=min_dist, prominence=max(prom_factor * x_std, 1e-8))
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
    br_freq_hint: float | None = None,
    window_s: float = 40.0,
    step_s: float = 20.0,
) -> tuple[np.ndarray, dict]:
    window_n = max(int(window_s * FS), 400)
    step_n = max(int(step_s * FS), 100)
    if len(disp_hr) <= window_n:
        heartbeat, info = separate_vmd_heart_only(disp_hr, hr_freq_hint=hr_freq_hint, br_freq_hint=br_freq_hint)
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
        heartbeat_seg, seg_info = separate_vmd_heart_only(
            segment,
            hr_freq_hint=hr_freq_hint,
            br_freq_hint=br_freq_hint,
        )
        seg_len = len(segment)
        hb_len = len(heartbeat_seg)
        if hb_len != seg_len:
            if hb_len > seg_len:
                heartbeat_seg = np.asarray(heartbeat_seg[:seg_len], dtype=np.float64)
            else:
                heartbeat_seg = np.pad(np.asarray(heartbeat_seg, dtype=np.float64), (0, seg_len - hb_len), mode="edge")
        else:
            heartbeat_seg = np.asarray(heartbeat_seg, dtype=np.float64)

        if seg_len >= 8:
            taper = np.hanning(seg_len)
            taper = np.ones(seg_len, dtype=np.float64) if np.allclose(taper, 0) else np.maximum(taper, 1e-3)
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
                "breath_mode": seg_info.get("breath_mode"),
                "heart_mode": seg_info.get("heart_mode"),
                "mixed_respiration_heart_mode": seg_info.get("mixed_respiration_heart_mode", False),
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
        "k": 3,
        "breath_frequency_hint_hz": round(float(br_freq_hint), 3) if br_freq_hint is not None else None,
        "n_segments": len(segments),
        "segments": segments,
    }


def select_separate_channels_bins(
    bin_power_acc: np.ndarray,
    iq_fd_sample: np.ndarray,
    n_frames_sample: int,
    channel_override: int | None = None,
) -> tuple[int, int, int, int, list[dict]]:
    summaries: list[dict] = []
    valid_summaries: list[dict] = []
    channels = [int(channel_override)] if channel_override is not None else list(range(bin_power_acc.shape[1]))
    for ch in channels:
        try:
            br_bin, hr_bin, candidates = select_bins_from_profile(bin_power_acc, ch, iq_fd_sample, n_frames_sample)
        except CandidateSelectionError as exc:
            summaries.append({
                "channel": ch,
                "algorithm_returned": False,
                "quality_valid": False,
                "selection_status": "rejected",
                "failure_reason": exc.reason,
                "n_candidates": 0,
            })
            continue
        if not candidates:
            continue
        best_hr = max(candidates, key=lambda item: item[5])
        best_br = max(candidates, key=lambda item: item[3])
        summary = {
                "channel": ch,
                "breath_bin": int(br_bin),
                "heart_bin": int(hr_bin),
                "best_hr_snr": float(best_hr[1]),
                "best_hr_phase_stability": float(best_hr[4]),
                "best_hr_selection_score": float(best_hr[5]),
                "best_br_snr": float(best_br[2]),
                "best_br_score": float(best_br[3]),
                "best_br_phase_stability": float(best_br[4]),
                "n_candidates": int(len(candidates)),
                "algorithm_returned": True,
                "quality_valid": True,
                "selection_status": "eligible_not_selected",
                "failure_reason": None,
            }
        summaries.append(summary)
        valid_summaries.append(summary)
    if not valid_summaries:
        raise CandidateSelectionError("NO_VALID_CHANNEL_BIN_SELECTION", summaries=summaries)
    breath_choice = max(valid_summaries, key=lambda item: item["best_br_score"])
    heart_choice = max(valid_summaries, key=lambda item: item["best_hr_selection_score"])
    for item in valid_summaries:
        breath_selected = item is breath_choice
        heart_selected = item is heart_choice
        if breath_selected and heart_selected:
            item["selection_status"] = "selected_breath_and_heart"
        elif breath_selected:
            item["selection_status"] = "selected_breath"
        elif heart_selected:
            item["selection_status"] = "selected_heart"
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
    phase_br_chunks: list[np.ndarray] = []
    disp_hr_chunks: list[np.ndarray] = []
    n_total = 0
    for index, iq_td in enumerate(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), start=1):
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


def save_result(
    result: dict,
    waveforms: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{result['session']}_mmwave_vital_signs.json"
    json_path.write_text(strict_json_dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    t, breath, heartbeat, hp, bp = waveforms
    npz_path = output_dir / f"{result['session']}_mmwave_vital_signs.npz"
    payload = {
        "t": t,
        "breath": breath,
        "heartbeat": heartbeat,
        "heart_peaks": hp,
        "breath_peaks": bp,
        "chest_bin": result["bins"]["breath"],
        "heart_bin": result["bins"]["heart"],
        "best_ch": result["best_channel"],
    }
    course = result.get("heart_rate", {}).get("time_course", {})
    points = course.get("points", [])
    if points:
        payload.update(
            hr_course_time_s=np.asarray([point["time_s"] for point in points], dtype=float),
            hr_course_time_bpm=np.asarray([np.nan if point.get("time_bpm") is None else point["time_bpm"] for point in points], dtype=float),
            hr_course_freq_bpm=np.asarray([np.nan if point.get("freq_bpm") is None else point["freq_bpm"] for point in points], dtype=float),
            hr_course_fused_raw_bpm=np.asarray([np.nan if point.get("fused_raw_bpm") is None else point["fused_raw_bpm"] for point in points], dtype=float),
            hr_course_fused_bpm=np.asarray([np.nan if point.get("fused_bpm") is None else point["fused_bpm"] for point in points], dtype=float),
            hr_course_confidence=np.asarray([point.get("confidence", 0.0) for point in points], dtype=float),
            hr_course_time_freq_gap_bpm=np.asarray([np.nan if point.get("time_freq_gap_bpm") is None else point["time_freq_gap_bpm"] for point in points], dtype=float),
            hr_course_agreement_warning=np.asarray([bool(point.get("agreement_warning", False)) for point in points], dtype=np.int8),
            hr_course_signal_std_10s_mm=np.asarray([point.get("signal_std_10s_mm", np.nan) for point in points], dtype=float),
            hr_course_signal_usable=np.asarray([bool(point.get("signal_usable", False)) for point in points], dtype=np.int8),
            hr_course_quality_code=np.asarray([{"rejected": -1, "low": 0, "medium": 1, "high": 2}.get(point.get("quality"), 0) for point in points], dtype=np.int8),
        )
    np.savez(npz_path, **payload)
    return json_path, npz_path


def save_range_fft_map(
    npz_files: Iterable[Path],
    output_dir: Path,
    session: str,
    best_ch: int | None = None,
    frame_start: int | None = None,
    frame_end: int | None = None,
    max_plot_frames: int = 1200,
    view_start_s: float | None = None,
    view_len_s: float = 30.0,
) -> tuple[Path, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    slices: list[np.ndarray] = []
    for iq_td in _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
        amp = np.abs(_as_range_cube(iq_td))
        amp_map = np.mean(amp, axis=2) if best_ch is None else amp[:, :, best_ch]
        slices.append(np.asarray(amp_map, dtype=np.float32))
    if not slices:
        raise RuntimeError("No frames were available for range-FFT plotting.")

    raw_map = np.concatenate(slices, axis=0)
    total_frames = raw_map.shape[0]
    duration_s = total_frames / FS
    if view_start_s is None:
        view_start_s = max(0.0, duration_s / 2 - view_len_s / 2) if duration_s > view_len_s else 0.0
    view_end_s = min(duration_s, view_start_s + view_len_s)
    start_idx = int(max(0, round(view_start_s * FS)))
    end_idx = int(min(total_frames, round(view_end_s * FS)))
    if end_idx <= start_idx:
        start_idx = 0
        end_idx = total_frames
    raw_map = raw_map[start_idx:end_idx]

    if raw_map.shape[0] > max_plot_frames:
        edges = np.linspace(0, raw_map.shape[0], max_plot_frames + 1, dtype=int)
        reduced = [np.mean(raw_map[edges[idx] : edges[idx + 1]], axis=0) for idx in range(max_plot_frames) if len(raw_map[edges[idx] : edges[idx + 1]]) > 0]
        raw_map = np.vstack(reduced)

    def _plot_map(data: np.ndarray, title: str, cbar_label: str, png_path: Path) -> Path:
        fig, ax = plt.subplots(figsize=(12, 6))
        im = ax.imshow(
            data,
            aspect="auto",
            origin="lower",
            cmap="viridis",
            interpolation="nearest",
            vmin=float(np.percentile(data, 5)),
            vmax=float(np.percentile(data, 99)),
        )
        ax.set_xlabel("Range bin")
        ax.set_ylabel("Chirp / frame index")
        ax.set_title(title)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label(cbar_label)
        plt.tight_layout()
        plt.savefig(png_path, dpi=150)
        plt.close()
        return png_path

    ch_label = f"ch{best_ch}" if best_ch is not None else "mean channels"
    raw_db = 20.0 * np.log10(raw_map + 1e-6)
    raw_png_path = output_dir / f"{session}_range_fft_map_raw.png"
    _plot_map(raw_db, f"Range FFT map (raw dB) - {session} ({ch_label}, {view_start_s:.0f}-{view_end_s:.0f} s)", "Amplitude (dB, relative)", raw_png_path)

    diag_map = np.abs(raw_map - np.mean(raw_map, axis=0, keepdims=True))
    diag_db = 20.0 * np.log10(diag_map + 1e-6)
    diag_png_path = output_dir / f"{session}_range_fft_map_diag.png"
    _plot_map(diag_db, f"Range FFT map (clutter removed, dB) - {session} ({ch_label}, {view_start_s:.0f}-{view_end_s:.0f} s)", "Amplitude (dB, relative)", diag_png_path)
    return raw_png_path, diag_png_path


def save_range_fft_channel_grid(
    npz_files: Iterable[Path],
    output_dir: Path,
    session: str,
    frame_start: int | None = None,
    frame_end: int | None = None,
    max_plot_frames: int = 800,
    view_start_s: float | None = None,
    view_len_s: float = 30.0,
) -> tuple[Path, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    slices: list[np.ndarray] = []
    for iq_td in _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
        slices.append(np.abs(_as_range_cube(iq_td)).astype(np.float32))
    if not slices:
        raise RuntimeError("No frames were available for channel-grid range-FFT plotting.")

    amp_all = np.concatenate(slices, axis=0)
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
        reduced = [np.mean(amp_all[edges[idx] : edges[idx + 1]], axis=0) for idx in range(max_plot_frames) if len(amp_all[edges[idx] : edges[idx + 1]]) > 0]
        amp_all = np.stack(reduced, axis=0)

    diag_maps = []
    raw_maps = []
    for ch in range(amp_all.shape[2]):
        ch_map = amp_all[:, :, ch]
        raw_maps.append(ch_map)
        ch_diag = np.abs(ch_map - np.mean(ch_map, axis=0, keepdims=True))
        diag_maps.append(20.0 * np.log10(ch_diag + 1e-6))

    def _plot_grid(maps: list[np.ndarray], title: str, cbar_label: str, png_path: Path, q_lo: float, q_hi: float) -> Path:
        all_vals = np.concatenate([m.ravel() for m in maps])
        vmin = float(np.percentile(all_vals, q_lo))
        vmax = float(np.percentile(all_vals, q_hi))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
            vmin = float(np.min(all_vals))
            vmax = float(np.max(all_vals))
        fig, axes = plt.subplots(2, 4, figsize=(18, 8), sharex=True, sharey=True)
        for ch, ax in enumerate(axes.ravel()):
            im = ax.imshow(maps[ch], aspect="auto", origin="lower", cmap="viridis", interpolation="nearest", vmin=vmin, vmax=vmax)
            ax.set_title(f"ch{ch}")
            ax.set_xlabel("Range bin")
            if ch % 4 == 0:
                ax.set_ylabel("Chirp / frame index")
        fig.suptitle(title, fontsize=14)
        cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.92)
        cbar.set_label(cbar_label)
        plt.tight_layout(rect=[0, 0, 0.96, 0.95])
        plt.savefig(png_path, dpi=150)
        plt.close()
        return png_path

    raw_png_path = output_dir / f"{session}_range_fft_channel_grid_raw_linear.png"
    _plot_grid(raw_maps, f"Range FFT channel grid (raw linear) - {session} ({view_start_s:.0f}-{view_end_s:.0f} s)", "Amplitude (linear)", raw_png_path, 5, 99)
    diag_png_path = output_dir / f"{session}_range_fft_channel_grid_diag_db.png"
    _plot_grid(diag_maps, f"Range FFT diagnostic grid (clutter removed, dB) - {session} ({view_start_s:.0f}-{view_end_s:.0f} s)", "Amplitude (dB, relative)", diag_png_path, 5, 99)
    return raw_png_path, diag_png_path


def plot_result(
    result: dict,
    waveforms: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    output_dir: Path,
    breath_view_start_s: float | None = None,
    breath_view_len_s: float = 60.0,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    t, breath, heartbeat, hp, bp = waveforms
    duration = result["duration_s"]
    session = result["session"]
    method = result["method"]
    version = result.get("version", "unknown")

    fig, axes = plt.subplots(3, 2, figsize=(16, 10))
    fig.suptitle(f"Vital signs - {session} ({duration / 60:.1f} min) [{version}, {method}]", fontsize=14)

    ax = axes[0, 0]
    if breath_view_start_s is None:
        breath_view_start_s = 120.0 if duration >= 240 else max(0.0, duration / 2 - breath_view_len_s / 2)
    breath_view_start_s = min(max(0.0, breath_view_start_s), max(0.0, duration - 1 / FS))
    breath_view_end_s = min(duration, breath_view_start_s + breath_view_len_s)
    breath_mask = (t >= breath_view_start_s) & (t < breath_view_end_s)
    if not np.any(breath_mask):
        breath_mask = np.ones_like(t, dtype=bool)
        breath_view_start_s = float(t[0]) if len(t) else 0.0
        breath_view_end_s = float(t[-1]) if len(t) else 0.0
    t_show = t[breath_mask]
    ax.plot(t_show, breath[breath_mask], "g-", alpha=0.8, linewidth=0.5)
    if len(bp) > 0:
        breath_idx = np.flatnonzero(breath_mask)
        bp_show = bp[(bp >= breath_idx[0]) & (bp <= breath_idx[-1])]
        ax.plot(t[bp_show], breath[bp_show], "gx", markersize=4)
    ax.set_xlim(breath_view_start_s, breath_view_end_s)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    br_val = result["breath_rate"]["time_bpm"] or result["breath_rate"]["freq_bpm"] or 0
    ax.set_title(f"Breath waveform - {breath_view_start_s:.0f}-{breath_view_end_s:.0f} s ({br_val} BPM, {result['breath_rate']['n_peaks']} peaks)")
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    heart_view = result.get("visualization", {}).get("heart_waveform_view", "last_20_s")
    if heart_view == "full":
        mask = np.ones_like(t, dtype=bool)
        heart_view_title = "full record"
    else:
        start_t = max(0, duration - 20)
        mask = t >= start_t
        heart_view_title = "last 20 s"
    ax.plot(t[mask], heartbeat[mask], "r-", alpha=0.8, linewidth=0.5)
    if len(hp) > 0:
        hp_show = hp[(hp >= np.flatnonzero(mask)[0]) & (hp < len(t))]
        marker_size = 2 if heart_view == "full" else 4
        ax.plot(t[hp_show], heartbeat[hp_show], "rx", markersize=marker_size)
    behavior_segments = result.get("behavior_alignment", {}).get("segments", [])
    if heart_view == "full":
        for segment in behavior_segments[1:]:
            boundary = segment.get("start_s")
            if boundary is not None:
                ax.axvline(boundary, color="#374151", ls=":", linewidth=0.8, alpha=0.75)
                ax.text(boundary, 0.98, segment.get("label", ""), transform=ax.get_xaxis_transform(), ha="left", va="top", fontsize=7, color="#374151")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    hr_val = result["heart_rate"]["time_bpm"] or result["heart_rate"]["freq_bpm"] or 0
    ax.set_title(f"Heart waveform - {heart_view_title} ({hr_val} BPM, {result['heart_rate']['n_peaks']} peaks)")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    f_b, pxx_b = signal.periodogram(breath, fs=FS, window="hann")
    ax.semilogy(f_b, pxx_b, "g-")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power")
    ax.set_title("Breath spectrum")
    for limit in [0.1, 0.5]:
        ax.axvline(limit, color="gray", ls=":", alpha=0.5)

    ax = axes[1, 1]
    f_h, pxx_h = signal.periodogram(heartbeat, fs=FS, window="hann")
    ax.semilogy(f_h, pxx_h, "r-")
    ax.set_xlim(0, 4)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power")
    ax.set_title("Heart spectrum")
    for limit in [HR_LO_HZ, HR_HI_HZ]:
        ax.axvline(limit, color="gray", ls=":", alpha=0.5)

    ax = axes[2, 0]
    course = result.get("heart_rate", {}).get("time_course", {})
    course_points = course.get("points", [])
    if course_points:
        course_t = np.asarray([point["time_s"] for point in course_points], dtype=float)
        time_bpm = np.asarray([np.nan if point.get("time_bpm") is None else point["time_bpm"] for point in course_points], dtype=float)
        freq_bpm = np.asarray([np.nan if point.get("freq_bpm") is None else point["freq_bpm"] for point in course_points], dtype=float)
        fused_bpm = np.asarray([np.nan if point.get("fused_bpm") is None else point["fused_bpm"] for point in course_points], dtype=float)
        confidence = np.asarray([point.get("confidence", 0.0) for point in course_points], dtype=float)
        if len(hp) >= 2:
            raw_hr = 60 / (np.diff(hp) / FS)
            ax.scatter(t[hp[1:]], raw_hr, s=3, color="#ef9a9a", alpha=0.15, linewidths=0, label="Raw beat IBI")
        ax.plot(course_t, time_bpm, color="#f59e0b", alpha=0.55, linewidth=0.8, label="Local time")
        ax.plot(course_t, freq_bpm, color="#2563eb", alpha=0.55, linewidth=0.8, label="Local frequency")
        ax.plot(course_t, fused_bpm, color="#b91c1c", linewidth=1.8, label="Fused HR")
        for segment in behavior_segments[1:]:
            boundary = segment.get("start_s")
            if boundary is not None:
                ax.axvline(boundary, color="#374151", ls=":", linewidth=0.8, alpha=0.65)
        low_conf = confidence < 0.25
        if np.any(low_conf):
            ax.scatter(course_t[low_conf], fused_bpm[low_conf], s=10, facecolors="none", edgecolors="#6b7280", alpha=0.65)
        ax.set_ylim(HR_LO_BPM - 5, HR_HI_BPM + 5)
        metrics = course.get("metrics", {})
        ax.set_title(f"HR time course - robust time/frequency fusion (p95 jump {metrics.get('jump_p95_bpm', 'NA')} BPM)")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Heart Rate (BPM)")
        ax.legend(loc="upper left", fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)
    elif len(hp) >= 2:
        hr_ts = 60 / (np.diff(hp) / FS)
        ax.plot(t[hp[1:]], hr_ts, "r.-", alpha=0.5, markersize=2, linewidth=0.5)
        ax.set_ylim(HR_LO_BPM - 5, HR_HI_BPM + 5)
        ax.set_title(f"HR time course ({len(hp) - 1} beats)")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Heart Rate (BPM)")
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, "Insufficient heart peaks", transform=ax.transAxes, ha="center", va="center")

    ax = axes[2, 1]
    if len(bp) >= 2:
        br_ts = 60 / (np.diff(bp) / FS)
        ax.plot(t[bp[1:]], br_ts, "g.-", alpha=0.5, markersize=2, linewidth=0.5)
        ax.set_ylim(5, 30)
        ax.set_title(f"BR time course ({len(bp) - 1} breaths)")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Breath Rate (BPM)")
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, "Insufficient breath peaks", transform=ax.transAxes, ha="center", va="center")

    plt.tight_layout()
    png_path = output_dir / f"{session}_mmwave_vital_signs.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def _nearest_spectral_power(freqs: np.ndarray, pxx: np.ndarray, target_hz: float) -> float:
    if target_hz <= 0 or len(freqs) == 0:
        return 0.0
    idx = int(np.argmin(np.abs(freqs - target_hz)))
    return float(pxx[idx])


def respiration_harmonic_reject(
    freqs: np.ndarray,
    pxx: np.ndarray,
    raw_bpm: float,
    ext_br_bpm: float | None,
    prefer_bpm: float | None = None,
    ext_br_tol_bpm: float = 5.0,
    harmonics: tuple[int, ...] = (2, 3),
    min_fallback_power_ratio: float = 0.5,
) -> dict:
    """Reject an HR candidate that lands on a respiration harmonic k*ext_br_bpm.

    The external respiration rate (ext_br_bpm, e.g. from a chest belt / RSP channel)
    is a strong prior the mmWave pipeline otherwise ignores. When the raw max-power HR
    peak coincides with 2*br / 3*br (the exact failure mode of subjects 97795/97796,
    where mmWave locked onto the respiration 2nd/3rd harmonic instead of the heartbeat),
    we do NOT blindly trust the next spectral peak -- it may be noise if the true
    heartbeat is weak. Correction priority:
      1. prefer_bpm (the time/peak-domain estimate) if it is clean (not a resp harmonic);
      2. the next-strongest spectral peak with power >= min_fallback_power_ratio of the
         raw peak AND not a respiration harmonic;
      3. if nothing confident, keep raw_bpm but flag resp_harmonic_reject so downstream
         quality gates can down-weight the window.
    See 0816 gold-standard report (锁半频=强而错). This is the only pending "real new
    action" from that report: RSP is already used on the gold-standard side
    (validate_gold_anchor.py) but never fed back into mmWave candidate selection.
    Backward compatible: pass ext_br_bpm=None to disable.
    """
    out = {
        "resp_harmonic_reject": False,
        "resp_harmonic_k": None,
        "resp_harmonic_target_bpm": None,
        "chosen_bpm": raw_bpm,
        "fallback_bpm": None,
        "fallback_source": None,
    }
    if ext_br_bpm is None or ext_br_bpm <= 0:
        return out

    def _is_harmonic(bpm: float) -> bool:
        return any(
            HR_LO_BPM <= k * ext_br_bpm <= HR_HI_BPM and abs(bpm - k * ext_br_bpm) <= ext_br_tol_bpm
            for k in harmonics
        )

    if not _is_harmonic(raw_bpm):
        return out

    out["resp_harmonic_reject"] = True
    best_k, best_d = None, 1e9
    for k in harmonics:
        if HR_LO_BPM <= k * ext_br_bpm <= HR_HI_BPM:
            d = abs(raw_bpm - k * ext_br_bpm)
            if d < best_d:
                best_k, best_d = k, d
    out["resp_harmonic_k"] = best_k
    out["resp_harmonic_target_bpm"] = round(best_k * ext_br_bpm, 1) if best_k is not None else None

    # 1) prefer the time/peak-domain estimate if it is clean
    if prefer_bpm is not None and HR_LO_BPM <= prefer_bpm <= HR_HI_BPM and not _is_harmonic(prefer_bpm):
        out["chosen_bpm"] = prefer_bpm
        out["fallback_bpm"] = round(prefer_bpm, 1)
        out["fallback_source"] = "time_domain"
        return out

    # 2) next-strongest spectral peak meeting power + harmonic constraints
    band_mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    band_freqs = freqs[band_mask]
    band_pxx = pxx[band_mask]
    raw_power = float(np.max(band_pxx)) if len(band_pxx) else 0.0
    if len(band_freqs) > 0:
        order = np.argsort(band_pxx)[::-1]
        for idx in order:
            cand_bpm = float(band_freqs[idx] * 60.0)
            cand_power = float(band_pxx[idx])
            if cand_power < min_fallback_power_ratio * raw_power:
                break  # remaining peaks are all too weak to be credible
            if not _is_harmonic(cand_bpm):
                out["fallback_bpm"] = round(cand_bpm, 1)
                out["chosen_bpm"] = out["fallback_bpm"]
                out["fallback_source"] = "spectrum_next_peak"
                break
    # 3) else keep raw_bpm but flagged (downstream gate should distrust it)
    return out


def _window_hr_candidates(heartbeat_seg: np.ndarray, peaks_seg: np.ndarray, ref_bpm: float | None, ext_br_bpm: float | None = None) -> dict:
    freqs, pxx = signal.periodogram(heartbeat_seg, fs=FS, window="hann")
    mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    if not np.any(mask):
        return {"raw_freq_bpm": None, "time_bpm": None, "corrected_bpm": None, "harmonic_lock": False, "reason": "no_spectrum"}
    band_freqs = freqs[mask]
    band_pxx = pxx[mask]
    raw_hz = float(band_freqs[int(np.argmax(band_pxx))])
    raw_bpm = raw_hz * 60.0

    time_bpm = None
    if len(peaks_seg) >= 2:
        ibi = np.diff(peaks_seg) / FS
        ibi = ibi[(ibi >= 60.0 / HR_HI_BPM) & (ibi <= 60.0 / HR_LO_BPM)]
        if len(ibi) >= 2:
            time_bpm = float(60.0 / np.mean(ibi))

    # Approach ①: external RSP prior gate. If the raw spectrum peak is a respiration
    # harmonic (2*br / 3*br), prefer the time-domain estimate if clean, else the
    # next-strongest non-harmonic spectral peak; if neither is confident, keep raw
    # but flag it so downstream quality gates can down-weight the window.
    resp_rej = respiration_harmonic_reject(freqs, pxx, raw_bpm, ext_br_bpm, prefer_bpm=time_bpm)
    if resp_rej["resp_harmonic_reject"] and resp_rej["fallback_source"] is not None:
        raw_bpm = resp_rej["chosen_bpm"]
        raw_hz = raw_bpm / 60.0

    corrected_bpm = raw_bpm
    harmonic_lock = False
    reason = "raw_spectrum"

    if ref_bpm is not None:
        harmonic_targets = [("double", ref_bpm * 2.0, 4.0), ("triple", ref_bpm * 3.0, 6.0), ("half", ref_bpm * 0.5, 3.0)]
        for label, target_bpm, tol_bpm in harmonic_targets:
            if abs(raw_bpm - target_bpm) <= tol_bpm:
                harmonic_lock = True
                if time_bpm is not None and abs(time_bpm - ref_bpm) <= 8.0:
                    corrected_bpm = time_bpm
                    reason = f"harmonic_lock_{label}_use_time"
                else:
                    corrected_bpm = ref_bpm
                    reason = f"harmonic_lock_{label}_use_ref"
                break
        if not harmonic_lock and time_bpm is not None and abs(raw_bpm - ref_bpm) >= 12.0 and abs(time_bpm - ref_bpm) <= 8.0:
            corrected_bpm = time_bpm
            reason = "jump_use_time_reference"

    return {
        "raw_freq_bpm": round(raw_bpm, 1),
        "time_bpm": round(time_bpm, 1) if time_bpm is not None else None,
        "corrected_bpm": round(corrected_bpm, 1),
        "harmonic_lock": bool(harmonic_lock),
        "reason": reason,
        "resp_harmonic_reject": bool(resp_rej["resp_harmonic_reject"]),
        "resp_harmonic_k": resp_rej["resp_harmonic_k"],
        "resp_harmonic_br_bpm": round(float(ext_br_bpm), 1) if ext_br_bpm is not None else None,
        "raw_power": round(float(np.max(band_pxx)), 6),
        "half_power": round(_nearest_spectral_power(band_freqs, band_pxx, raw_hz * 0.5), 6),
        "double_power": round(_nearest_spectral_power(band_freqs, band_pxx, raw_hz * 2.0), 6),
    }


def _heart_segment_reference_correction(heartbeat: np.ndarray, hp: np.ndarray, base_freq_bpm: float | None, ext_br_bpm: float | None = None) -> dict:
    win_s = 20.0
    step_s = 10.0
    win = int(round(win_s * FS))
    step = int(round(step_s * FS))
    n = len(heartbeat)
    if n < win:
        return {
            "window_s": win_s,
            "step_s": step_s,
            "windows": [],
            "n_harmonic_locked": 0,
            "corrected_freq_bpm": round(base_freq_bpm, 1) if base_freq_bpm is not None else None,
            "corrected_from_segments": False,
        }

    peak_set = np.asarray(hp, dtype=int)
    windows = []
    valid_time_bpms: list[float] = []
    for start in range(0, n - win + 1, step):
        end = start + win
        local_peaks = peak_set[(peak_set >= start) & (peak_set < end)] - start
        time_bpm = None
        if len(local_peaks) >= 2:
            ibi = np.diff(local_peaks) / FS
            ibi = ibi[(ibi >= 60.0 / HR_HI_BPM) & (ibi <= 60.0 / HR_LO_BPM)]
            if len(ibi) >= 2:
                time_bpm = float(60.0 / np.mean(ibi))
                valid_time_bpms.append(time_bpm)
        windows.append({"start_frame": start, "end_frame": end, "time_bpm_seed": time_bpm})

    ref_bpm = float(np.median(valid_time_bpms)) if valid_time_bpms else base_freq_bpm
    corrected_values: list[float] = []
    harmonic_locked = 0
    resp_rejected = 0
    corrected_window_count = 0
    detailed_windows = []
    current_ref = ref_bpm

    for item in windows:
        start = int(item["start_frame"])
        end = int(item["end_frame"])
        seg = heartbeat[start:end]
        local_peaks = peak_set[(peak_set >= start) & (peak_set < end)] - start
        info = _window_hr_candidates(seg, local_peaks, current_ref, ext_br_bpm=ext_br_bpm)
        if info["harmonic_lock"]:
            harmonic_locked += 1
        if info.get("resp_harmonic_reject"):
            resp_rejected += 1
        if info["reason"] != "raw_spectrum":
            corrected_window_count += 1
        corrected = info["corrected_bpm"]
        if corrected is not None:
            corrected_values.append(float(corrected))
            current_ref = float(corrected) if current_ref is None else 0.7 * float(current_ref) + 0.3 * float(corrected)
        detailed_windows.append({"start_s": round(start / FS, 1), "end_s": round(end / FS, 1), **info, "reference_bpm": round(current_ref, 1) if current_ref is not None else None})

    corrected_freq_bpm = float(np.median(corrected_values)) if corrected_window_count > 0 and corrected_values else base_freq_bpm
    return {
        "window_s": win_s,
        "step_s": step_s,
        "windows": detailed_windows,
        "n_harmonic_locked": int(harmonic_locked),
        "n_resp_harmonic_rejected": int(resp_rejected),
        "n_corrected_windows": int(corrected_window_count),
        "corrected_freq_bpm": round(corrected_freq_bpm, 1) if corrected_freq_bpm is not None else None,
        "corrected_from_segments": bool(corrected_window_count > 0),
        "initial_reference_bpm": round(ref_bpm, 1) if ref_bpm is not None else None,
    }


def _score_heart_candidate_result(
    hr_freq_bpm: float | None,
    hr_time_bpm: float | None,
    seg_corr: dict,
    n_peaks: int,
    time_course: dict | None = None,
) -> tuple[float, dict]:
    gap = abs(hr_freq_bpm - hr_time_bpm) if (hr_freq_bpm is not None and hr_time_bpm is not None) else 999.0
    windows = seg_corr.get("windows", [])
    raw_vals = [w["raw_freq_bpm"] for w in windows if w.get("raw_freq_bpm") is not None]
    corr_vals = [w["corrected_bpm"] for w in windows if w.get("corrected_bpm") is not None]
    time_vals = [w["time_bpm"] for w in windows if w.get("time_bpm") is not None]
    raw_std = float(np.std(raw_vals, ddof=1)) if len(raw_vals) >= 2 else 999.0
    corr_std = float(np.std(corr_vals, ddof=1)) if len(corr_vals) >= 2 else raw_std
    time_std = float(np.std(time_vals, ddof=1)) if len(time_vals) >= 2 else 999.0
    harmonic_locked = int(seg_corr.get("n_harmonic_locked", 0))
    corrected_windows = int(seg_corr.get("n_corrected_windows", 0))
    peak_bonus = min(n_peaks / 100.0, 8.0)
    course_metrics = (time_course or {}).get("metrics", {})
    course_std = course_metrics.get("std_bpm")
    course_jump_p95 = course_metrics.get("jump_p95_bpm")
    course_agreement_p95 = course_metrics.get("time_freq_agreement_p95_bpm")
    course_confidence = course_metrics.get("median_confidence")
    raw_metrics = (time_course or {}).get("raw_beat_metrics", {})
    raw_beat_std = raw_metrics.get("std_bpm")
    raw_beat_jump_p95 = raw_metrics.get("jump_p95_bpm")
    raw_beat_jump_ratio = raw_metrics.get("jumps_over_10bpm_pct")
    signal_quality = (time_course or {}).get("signal_quality", {})
    signal_usable_ratio = float(signal_quality.get("usable_ratio", 0.0))
    signal_hard_gate_passed = bool(signal_quality.get("hard_gate_passed", False))
    score = 40.0 - 1.8 * min(gap, 30.0) - 0.5 * min(raw_std, 40.0) - 0.4 * min(corr_std, 40.0) - 0.2 * min(time_std, 40.0) - 1.5 * harmonic_locked - 0.4 * corrected_windows + peak_bonus
    agreement_warning = bool(np.isfinite(gap) and gap > HR_TIME_FREQ_WARNING_BPM)
    if agreement_warning:
        score -= 20.0
    if course_std is not None:
        score -= 0.35 * min(float(course_std), 25.0)
    if course_jump_p95 is not None:
        score -= 0.45 * min(float(course_jump_p95), 20.0)
    if course_agreement_p95 is not None:
        score -= 0.15 * min(float(course_agreement_p95), 30.0)
    if course_confidence is not None:
        score += 5.0 * float(course_confidence)
    # Raw beat regularity must remain visible; smoothing alone must not make a noisy candidate look good.
    if raw_beat_std is not None:
        score -= 0.10 * min(float(raw_beat_std), 50.0)
    if raw_beat_jump_p95 is not None:
        score -= 0.15 * min(float(raw_beat_jump_p95), 60.0)
    if raw_beat_jump_ratio is not None:
        score -= 0.35 * min(float(raw_beat_jump_ratio), 100.0)
    score -= 30.0 * (1.0 - signal_usable_ratio)
    if not signal_hard_gate_passed:
        score = -1_000_000.0
    return float(score), {
        "gap_bpm": round(gap, 2),
        "agreement_warning": agreement_warning,
        "warning": "time_frequency_gap_gt_10_bpm" if agreement_warning else None,
        "raw_window_std_bpm": round(raw_std, 2) if np.isfinite(raw_std) else None,
        "corrected_window_std_bpm": round(corr_std, 2) if np.isfinite(corr_std) else None,
        "time_window_std_bpm": round(time_std, 2) if np.isfinite(time_std) else None,
        "n_harmonic_locked": harmonic_locked,
        "n_corrected_windows": corrected_windows,
        "time_course_std_bpm": course_std,
        "time_course_jump_p95_bpm": course_jump_p95,
        "time_course_agreement_p95_bpm": course_agreement_p95,
        "time_course_median_confidence": course_confidence,
        "raw_beat_std_bpm": raw_beat_std,
        "raw_beat_jump_p95_bpm": raw_beat_jump_p95,
        "raw_beat_jumps_over_10bpm_pct": raw_beat_jump_ratio,
        "signal_usable_ratio": round(signal_usable_ratio, 4),
        "signal_hard_gate_passed": signal_hard_gate_passed,
        "signal_gate_rejection": None if signal_hard_gate_passed else "usable_ratio_below_0.50",
    }


def _heart_window_consensus_bpm(
    seg_corr: dict,
    hr_freq_bpm_periodogram: float | None,
    hr_time_bpm_global: float | None,
) -> tuple[float | None, float | None, dict]:
    windows = seg_corr.get("windows", [])
    corrected_vals = [float(w["corrected_bpm"]) for w in windows if w.get("corrected_bpm") is not None]
    time_vals = [float(w["time_bpm"]) for w in windows if w.get("time_bpm") is not None]
    fused_vals = [
        0.5 * (float(w["corrected_bpm"]) + float(w["time_bpm"]))
        for w in windows
        if w.get("corrected_bpm") is not None and w.get("time_bpm") is not None and abs(float(w["corrected_bpm"]) - float(w["time_bpm"])) <= 8.0
    ]

    stable_records: list[dict] = []
    for w in windows:
        corrected = w.get("corrected_bpm")
        time_bpm = w.get("time_bpm")
        rep = None
        source = None
        agreement = None
        if corrected is not None and time_bpm is not None:
            agreement = abs(float(corrected) - float(time_bpm))
            if agreement <= 8.0:
                rep = 0.5 * (float(corrected) + float(time_bpm))
                source = "fused"
            else:
                rep = float(time_bpm)
                source = "time_only"
        elif time_bpm is not None:
            rep = float(time_bpm)
            source = "time_only"
        elif corrected is not None:
            rep = float(corrected)
            source = "corrected_only"
        if rep is not None:
            stable_records.append(
                {
                    "value": float(rep),
                    "source": source,
                    "agreement": agreement,
                    "time_bpm": float(time_bpm) if time_bpm is not None else None,
                    "corrected_bpm": float(corrected) if corrected is not None else None,
                }
            )

    clusters: list[list[dict]] = []
    for rec in sorted(stable_records, key=lambda item: item["value"]):
        if not clusters:
            clusters.append([rec])
            continue
        prev_center = float(np.median([item["value"] for item in clusters[-1]]))
        if abs(rec["value"] - prev_center) <= 6.0:
            clusters[-1].append(rec)
        else:
            clusters.append([rec])

    cluster_summaries = []
    best_cluster: list[dict] | None = None
    best_cluster_score = -1e9
    for idx, cluster in enumerate(clusters):
        values = [item["value"] for item in cluster]
        fused_count = sum(1 for item in cluster if item["source"] == "fused")
        time_count = sum(1 for item in cluster if item["source"] == "time_only")
        corrected_count = sum(1 for item in cluster if item["source"] == "corrected_only")
        center = float(np.median(values))
        std = float(np.std(values, ddof=1)) if len(values) >= 2 else 0.0
        gap_to_global_time = abs(center - float(hr_time_bpm_global)) if hr_time_bpm_global is not None else 0.0
        score = 3.0 * len(values) + 1.5 * fused_count + 0.4 * time_count - 0.6 * std - 0.15 * gap_to_global_time
        cluster_summaries.append(
            {
                "cluster": int(idx),
                "count": int(len(values)),
                "median_bpm": round(center, 1),
                "std_bpm": round(std, 2),
                "fused_count": int(fused_count),
                "time_count": int(time_count),
                "corrected_count": int(corrected_count),
                "score": round(score, 2),
            }
        )
        if score > best_cluster_score:
            best_cluster_score = score
            best_cluster = cluster

    source = "periodogram_corrected"
    value = float(hr_freq_bpm_periodogram) if hr_freq_bpm_periodogram is not None else None
    gap_global = abs(float(hr_freq_bpm_periodogram) - float(hr_time_bpm_global)) if (hr_freq_bpm_periodogram is not None and hr_time_bpm_global is not None) else None
    corr_std = float(np.std(corrected_vals, ddof=1)) if len(corrected_vals) >= 2 else None

    if best_cluster is not None:
        best_cluster_vals = [item["value"] for item in best_cluster]
        best_cluster_center = float(np.median(best_cluster_vals))
        best_cluster_count = len(best_cluster_vals)
        best_cluster_time_vals = [float(item["time_bpm"]) for item in best_cluster if item.get("time_bpm") is not None]
        best_cluster_time_median = float(np.median(best_cluster_time_vals)) if best_cluster_time_vals else None
    else:
        best_cluster_center = None
        best_cluster_count = 0
        best_cluster_time_median = None

    time_value = float(hr_time_bpm_global) if hr_time_bpm_global is not None else None
    time_source = "global_time_peaks"

    if best_cluster_center is not None and best_cluster_count >= 5 and (gap_global is None or gap_global > 3.0 or (corr_std is not None and corr_std > 8.0)):
        value = best_cluster_center
        source = "window_cluster_median"
        if best_cluster_time_median is not None:
            time_value = best_cluster_time_median
            time_source = "window_cluster_time_median"
    elif gap_global is not None and gap_global > 3.0:
        if len(fused_vals) >= 5:
            value = float(np.median(fused_vals))
            source = "window_fused_median"
        elif len(time_vals) >= 5:
            value = float(np.median(time_vals))
            source = "window_time_median"
        elif len(corrected_vals) >= 5:
            value = float(np.median(corrected_vals))
            source = "window_corrected_median"
    elif gap_global is not None and corr_std is not None and corr_std > 10.0 and len(fused_vals) >= 5:
        value = float(np.median(fused_vals))
        source = "window_fused_median_highvar"
        if time_vals:
            time_value = float(np.median(time_vals))
            time_source = "window_time_median_highvar"

    return (
        round(value, 1) if value is not None else None,
        round(time_value, 1) if time_value is not None else None,
        {
            "source": source,
            "time_source": time_source,
            "global_gap_bpm": round(float(gap_global), 2) if gap_global is not None else None,
            "n_window_corrected": int(len(corrected_vals)),
            "n_window_time": int(len(time_vals)),
            "n_window_fused": int(len(fused_vals)),
            "window_corrected_median_bpm": round(float(np.median(corrected_vals)), 1) if corrected_vals else None,
            "window_time_median_bpm": round(float(np.median(time_vals)), 1) if time_vals else None,
            "window_fused_median_bpm": round(float(np.median(fused_vals)), 1) if fused_vals else None,
            "window_corrected_std_bpm": round(corr_std, 2) if corr_std is not None else None,
            "cluster_count": int(len(cluster_summaries)),
            "best_cluster_count": int(best_cluster_count),
            "best_cluster_median_bpm": round(best_cluster_center, 1) if best_cluster_center is not None else None,
            "best_cluster_time_median_bpm": round(best_cluster_time_median, 1) if best_cluster_time_median is not None else None,
            "clusters": cluster_summaries,
        },
    )


def _evaluate_heart_candidate(
    npz_files: list[Path],
    ch: int,
    bin_idx: int,
    method: str = "vmd_heart",
    frame_start: int | None = None,
    frame_end: int | None = None,
    ext_br_bpm: float | None = None,
) -> dict:
    disp_chunks: list[np.ndarray] = []
    for iq_td in _iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
        iq_fd = _as_range_cube(iq_td)
        disp_chunks.append(extract_displacement(iq_fd, bin_idx, ch))
    if not disp_chunks:
        raise RuntimeError("No displacement extracted for heart candidate.")

    disp_hr = np.concatenate(disp_chunks)
    breath_hint_signal = _sos_bandpass(disp_hr, BR_LO_HZ, BR_HI_HZ)
    br_freq_hint = estimate_freq_periodogram(breath_hint_signal, BR_LO_HZ, BR_HI_HZ)
    heart_bp = _sos_bandpass(disp_hr, HR_LO_HZ, HR_HI_HZ)
    hr_freq_bp = estimate_freq_periodogram(heart_bp, HR_LO_HZ, HR_HI_HZ)
    if method == "vmd_heart":
        heartbeat, heart_sep = separate_vmd_heart_windowed(
            disp_hr,
            hr_freq_hint=hr_freq_bp,
            br_freq_hint=br_freq_hint,
        )
        heart_pd = heartbeat
        hr_freq = estimate_freq_periodogram(heartbeat, HR_LO_HZ, HR_HI_HZ)
    else:
        heartbeat = heart_bp
        heart_pd = heart_bp
        hr_freq = hr_freq_bp
        heart_sep = {"method": "bp_heart", "source": "hr_bin_bandpass"}

    hp = detect_peaks_heart_lo(heart_pd, lo_bpm=HR_LO_BPM, hi_bpm=HR_HI_BPM)
    hr_time_bpm = float(60 * FS / np.mean(np.diff(hp))) if len(hp) >= 2 else None
    hr_freq_bpm_raw = float(hr_freq * 60) if hr_freq else None
    seg_corr = _heart_segment_reference_correction(
        heartbeat=heart_pd,
        hp=hp,
        base_freq_bpm=round(hr_freq_bpm_raw, 1) if hr_freq_bpm_raw is not None else None,
        ext_br_bpm=ext_br_bpm,
    )
    hr_freq_bpm_periodogram = seg_corr.get("corrected_freq_bpm", round(hr_freq_bpm_raw, 1) if hr_freq_bpm_raw is not None else None)
    hr_freq_bpm, hr_time_bpm_consensus, hr_consensus = _heart_window_consensus_bpm(
        seg_corr=seg_corr,
        hr_freq_bpm_periodogram=hr_freq_bpm_periodogram,
        hr_time_bpm_global=round(hr_time_bpm, 1) if hr_time_bpm is not None else None,
    )
    hr_time_bpm_final = hr_time_bpm_consensus if hr_time_bpm_consensus is not None else (round(hr_time_bpm, 1) if hr_time_bpm is not None else None)
    hr_time_course = estimate_hr_time_course(heartbeat=heart_pd, peaks=hp, fs=FS, reference_bpm=hr_freq_bpm)
    score, score_info = _score_heart_candidate_result(hr_freq_bpm=hr_freq_bpm, hr_time_bpm=hr_time_bpm_final, seg_corr=seg_corr, n_peaks=len(hp), time_course=hr_time_course)
    return {
        "channel": int(ch),
        "heart_bin": int(bin_idx),
        "score": round(score, 3),
        "freq_bpm": round(hr_freq_bpm, 1) if hr_freq_bpm is not None else None,
        "freq_bpm_raw": round(hr_freq_bpm_raw, 1) if hr_freq_bpm_raw is not None else None,
        "freq_bpm_periodogram": hr_freq_bpm_periodogram,
        "time_bpm": hr_time_bpm_final,
        "time_bpm_global": round(hr_time_bpm, 1) if hr_time_bpm is not None else None,
        "n_peaks": int(len(hp)),
        "heart_waveform_std_mm": round(float(np.std(heart_pd)), 8),
        "breath_frequency_hint_hz": round(float(br_freq_hint), 4) if br_freq_hint is not None else None,
        "segment_method": heart_sep.get("method"),
        "segment_count": heart_sep.get("n_segments"),
        "segment_reference_correction": seg_corr,
        "window_consensus": hr_consensus,
        "time_course": hr_time_course,
        **score_info,
    }


def _select_refined_heart_candidate(
    npz_files: list[Path],
    bin_power_acc: np.ndarray,
    iq_fd_sample: np.ndarray,
    n_frames_sample: int,
    method: str = "vmd_heart",
    frame_start: int | None = None,
    frame_end: int | None = None,
    channel_override: int | None = None,
    top_k_per_channel: int = 1,
    reference_candidates: list[tuple[int, int]] | None = None,
    ext_br_bpm: float | None = None,
) -> tuple[int, int, list[dict]]:
    channels = [int(channel_override)] if channel_override is not None else list(range(bin_power_acc.shape[1]))
    candidates_to_eval: list[tuple[int, int, float, float, float]] = []
    selection_failures: list[dict] = []
    for ch in channels:
        try:
            _br_bin, _hr_bin, candidates = select_bins_from_profile(bin_power_acc, ch, iq_fd_sample, n_frames_sample)
        except CandidateSelectionError as exc:
            selection_failures.append({"channel": ch, "algorithm_returned": False, "quality_valid": False,
                                       "selection_status": "rejected", "failure_reason": exc.reason})
            continue
        if not candidates:
            continue
        top = sorted(candidates, key=lambda item: item[5], reverse=True)[: max(1, int(top_k_per_channel))]
        for bin_idx, hr_snr, _br_snr, _br_score, phase_stability, heart_score in top:
            candidates_to_eval.append((int(ch), int(bin_idx), float(hr_snr), float(phase_stability), float(heart_score)))

    for ch, bin_idx in reference_candidates or []:
        if channel_override is None or int(ch) == int(channel_override):
            candidates_to_eval.append((int(ch), int(bin_idx), 0.0, 0.0, 0.0))

    unique_candidates: dict[tuple[int, int], tuple[float, float, float]] = {}
    for ch, bin_idx, hr_snr, phase_stability, heart_score in candidates_to_eval:
        previous = unique_candidates.get((ch, bin_idx))
        if previous is None or heart_score > previous[2]:
            unique_candidates[(ch, bin_idx)] = (hr_snr, phase_stability, heart_score)

    evaluations = []
    reference_set = {(int(ch), int(bin_idx)) for ch, bin_idx in (reference_candidates or [])}
    total = len(unique_candidates)
    for idx, ((ch, bin_idx), (hr_snr, phase_stability, heart_score)) in enumerate(unique_candidates.items(), start=1):
        print(
            f"[heart-refine] {idx}/{total} ch={ch} bin={bin_idx} "
            f"sample_hr_snr={hr_snr:.2f} phase_stability={phase_stability:.3f} selection_score={heart_score:.3f}"
        )
        item = _evaluate_heart_candidate(npz_files=npz_files, ch=ch, bin_idx=bin_idx, method=method, frame_start=frame_start, frame_end=frame_end, ext_br_bpm=ext_br_bpm)
        item["sample_hr_snr"] = round(hr_snr, 3)
        item["sample_phase_stability"] = round(phase_stability, 4)
        item["sample_selection_score"] = round(heart_score, 4)
        item["candidate_source"] = "validated_reference" if (ch, bin_idx) in reference_set else "phase_stable_auto"
        item["score"] = round(float(item["score"]) + 2.0 * heart_score, 3)
        evaluations.append(item)

    if not evaluations:
        raise CandidateSelectionError("NO_REFINED_HEART_CANDIDATES_EVALUATED", summaries=selection_failures)

    evaluations.sort(key=lambda x: x["score"], reverse=True)
    for item in evaluations:
        item.update(algorithm_returned=True, quality_valid=bool(item.get("signal_hard_gate_passed", False)),
                    selection_status="eligible_not_selected", failure_reason=None)
    passing = [item for item in evaluations if item.get("signal_hard_gate_passed", False)]
    if not passing:
        for item in evaluations:
            item.update(quality_valid=False, selection_status="rejected",
                        failure_reason="HEART_SIGNAL_STRENGTH_HARD_GATE_FAILED")
        raise CandidateSelectionError("ALL_HEART_CANDIDATES_FAILED_SIGNAL_GATE",
                                      summaries=evaluations + selection_failures)
    best = passing[0]
    best["selection_status"] = "selected"
    return int(best["channel"]), int(best["heart_bin"]), evaluations + selection_failures


def _analyze_displacement_v23(
    disp_br: np.ndarray,
    disp_hr: np.ndarray,
    n_frames: int,
    method: str = "vmd_heart",
    session: str = "sub-sxq_ses-SART",
    ext_br_bpm: float | None = None,
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    duration = n_frames / FS
    t = np.arange(n_frames) / FS
    breath, br_freq, bp, breath_sep = _select_breath_candidate(disp_br)

    heart_bp = _sos_bandpass(disp_hr, HR_LO_HZ, HR_HI_HZ)
    hr_freq_bp = estimate_freq_periodogram(heart_bp, HR_LO_HZ, HR_HI_HZ)
    if method == "vmd_heart":
        heartbeat, heart_sep = separate_vmd_heart_windowed(
            disp_hr,
            hr_freq_hint=hr_freq_bp,
            br_freq_hint=br_freq,
        )
        heart_pd = heartbeat
        hr_freq = estimate_freq_periodogram(heartbeat, HR_LO_HZ, HR_HI_HZ)
    else:
        heartbeat = heart_bp
        heart_pd = heart_bp
        hr_freq = hr_freq_bp
        heart_sep = {"method": "bp_heart", "source": "hr_bin_bandpass"}

    hp = detect_peaks_heart_lo(heart_pd, lo_bpm=HR_LO_BPM, hi_bpm=HR_HI_BPM)
    hr_time_bpm = round(float(60 * FS / np.mean(np.diff(hp))), 1) if len(hp) >= 2 else None
    hr_freq_bpm_raw = round(float(hr_freq * 60), 1) if hr_freq else None
    hr_seg_corr = _heart_segment_reference_correction(heartbeat=heart_pd, hp=hp, base_freq_bpm=hr_freq_bpm_raw, ext_br_bpm=ext_br_bpm)
    hr_freq_bpm_periodogram = hr_seg_corr.get("corrected_freq_bpm", hr_freq_bpm_raw)
    hr_freq_bpm, hr_time_bpm_consensus, hr_window_consensus = _heart_window_consensus_bpm(
        seg_corr=hr_seg_corr, hr_freq_bpm_periodogram=hr_freq_bpm_periodogram, hr_time_bpm_global=hr_time_bpm
    )
    hr_time_bpm_final = hr_time_bpm_consensus if hr_time_bpm_consensus is not None else hr_time_bpm
    hr_time_course = estimate_hr_time_course(heartbeat=heart_pd, peaks=hp, fs=FS, reference_bpm=hr_freq_bpm)
    hr_freq_bpm_pre_gate = hr_freq_bpm
    hr_time_bpm_pre_gate = hr_time_bpm_final
    record_signal_gate_passed = bool(hr_time_course.get("signal_quality", {}).get("hard_gate_passed", False))
    if not record_signal_gate_passed:
        hr_freq_bpm = None
        hr_time_bpm_final = None
    global_hr_gap = (
        abs(float(hr_freq_bpm) - float(hr_time_bpm_final))
        if hr_freq_bpm is not None and hr_time_bpm_final is not None
        else None
    )
    global_agreement_warning = bool(global_hr_gap is not None and global_hr_gap > HR_TIME_FREQ_WARNING_BPM)

    hrv = {}
    hp_signal_gate_mask = _peak_signal_gate_mask(hp, FS, hr_time_course)
    hp_hrv = hp[hp_signal_gate_mask]
    if record_signal_gate_passed and len(hp_hrv) >= 4:
        ibi = np.diff(hp) / FS * 1000
        ibi = ibi[hp_signal_gate_mask[:-1] & hp_signal_gate_mask[1:]]
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
        "version": "v2.3",
        "pipeline": "chunked_long_record_v23_with_hr_segment_reference_correction",
        "duration_s": round(duration, 1),
        "frame_rate_hz": round(n_frames / duration, 1) if duration > 0 else FS,
        "method": method,
        "separation": {"breath": breath_sep, "heart": heart_sep},
        "heart_rate": {
            "freq_bpm": hr_freq_bpm,
            "freq_bpm_pre_signal_gate": hr_freq_bpm_pre_gate,
            "freq_bpm_raw": hr_freq_bpm_raw,
            "freq_bpm_periodogram": hr_freq_bpm_periodogram,
            "time_bpm": hr_time_bpm_final,
            "time_bpm_pre_signal_gate": hr_time_bpm_pre_gate,
            "time_bpm_global": hr_time_bpm,
            "n_peaks": int(len(hp)),
            "n_peaks_signal_usable": int(len(hp_hrv)),
            "segment_reference_correction": hr_seg_corr,
            "window_consensus": hr_window_consensus,
            "fused_bpm": hr_time_course.get("fused_median_bpm"),
            "self_check": {
                "heart_waveform_std_mm": round(float(np.std(heart_pd)), 8),
                "heart_waveform_ptp_mm": round(float(np.ptp(heart_pd)), 8),
                "time_frequency_gap_bpm": round(global_hr_gap, 2) if global_hr_gap is not None else None,
                "agreement_warning": global_agreement_warning,
                "warning": "time_frequency_gap_gt_10_bpm" if global_agreement_warning else None,
                "hr_range_bpm": [HR_LO_BPM, HR_HI_BPM],
                "signal_quality": hr_time_course.get("signal_quality", {}),
            },
            "time_course": hr_time_course,
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


def _bin_to_distance_m(bin_idx: int | np.ndarray, bin_spacing_m: float, range_bias_m: float = 0.0) -> np.ndarray:
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

    amp_all = np.concatenate(slices, axis=0)
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
        reduced = [np.mean(amp_all[edges[idx] : edges[idx + 1]], axis=0) for idx in range(max_plot_frames) if len(amp_all[edges[idx] : edges[idx + 1]]) > 0]
        amp_all = np.stack(reduced, axis=0)

    ch_maps = [("Breath", breath_ch, breath_bin, amp_all[:, :, breath_ch]), ("Heart", heart_ch, heart_bin, amp_all[:, :, heart_ch])]
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
        im = ax.imshow(ch_map, aspect="auto", origin="lower", cmap="viridis", interpolation="nearest", vmin=vmin, vmax=vmax, extent=extent)
        bin_dist_m = float(_bin_to_distance_m(bin_idx, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m))
        ax.axvline(bin_dist_m, color="red", linestyle="--", linewidth=1.2, alpha=0.9)
        ax.set_title(f"{label} channel ch{ch} (bin {bin_idx}, {bin_dist_m:.2f} m)")
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Chirp / frame index")
        ax.set_xlim(0.0, 3.0)  # clip to human-relevant range; static clutter at ~5 m (wall) excluded

    fig.suptitle(f"Selected-channel Range FFT - {session} ({view_start_s:.0f}-{view_end_s:.0f} s)", fontsize=14)
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
    ax.set_xlabel("Frame index")
    ax.set_ylabel("Phase (rad)")
    ax.set_title(f"Raw phase - breath ch{breath_ch}, bin {breath_bin} ({dist_m:.2f} m), {view_start_s:.0f}-{view_end_s:.0f} s")
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
    ax.set_xlabel("Frame index")
    ax.set_ylabel("Unwrapped phase (rad)")
    ax.set_title(f"Unwrapped phase - breath ch{breath_ch}, bin {breath_bin} ({dist_m:.2f} m), {view_start_s:.0f}-{view_end_s:.0f} s")
    ax.grid(True, alpha=0.25)
    plt.tight_layout()

    png_path = output_dir / f"{session}_breath_unwrapped_phase.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    return png_path


def _analyze_long_record_with_forced_heart_candidate_v23(
    parts_dir: Path,
    output_dir: Path,
    heart_ch: int,
    heart_bin: int,
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
    ext_br_bpm: float | None = None,
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    npz_files = collect_npz_parts(parts_dir, pattern=pattern)
    if not npz_files:
        raise FileNotFoundError(f"No part files matched under: {parts_dir}")

    print(f"[info] found {len(npz_files)} chunk files")
    print(f"[info] parts dir: {parts_dir}")
    print(f"[info] output dir: {output_dir}")

    channel_power, bin_power_acc, _ = accumulate_range_profile(npz_files, frame_start=frame_start, frame_end=frame_end)
    best_ch_auto = int(np.argmax(channel_power))
    iq_sample = next(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), None)
    if iq_sample is None:
        raise RuntimeError("Selected frame range contains no data.")
    iq_fd_sample = _as_range_cube(iq_sample)

    gate_mask = _distance_gate_to_bin_mask(bin_power_acc.shape[0], min_range_m, max_range_m, bin_spacing_m, range_bias_m)
    if not np.any(gate_mask):
        raise RuntimeError("Distance gate excluded all range bins. Please check min/max range settings.")

    bin_power_acc_gated = np.array(bin_power_acc, copy=True)
    bin_power_acc_gated[~gate_mask, :] = 0.0
    br_ch, br_bin, _hr_ch_gate, _hr_bin_gate, breath_gate_summaries = select_separate_channels_bins(
        bin_power_acc_gated, iq_fd_sample, iq_sample.shape[0], channel_override=channel_override
    )

    disp_br, disp_hr, n_frames = extract_displacement_separate(
        npz_files, br_ch, br_bin, int(heart_ch), int(heart_bin), frame_start=frame_start, frame_end=frame_end
    )
    result, waveforms = _analyze_displacement_v23(disp_br, disp_hr, n_frames, method=method, session=session, ext_br_bpm=ext_br_bpm)
    result["external_respiration_bpm"] = round(ext_br_bpm, 1) if ext_br_bpm is not None else None
    result["best_channel"] = br_ch
    result["auto_best_channel"] = best_ch_auto
    result["channels"] = {"breath": br_ch, "heart": int(heart_ch)}
    result["channel_selection"] = {
        "breath_gated": breath_gate_summaries,
        "heart_forced": {"channel": int(heart_ch), "heart_bin": int(heart_bin), "reason": "manual_forced_candidate"},
    }
    result["bins"] = {"breath": br_bin, "heart": int(heart_bin)}
    result["n_frames"] = n_frames
    result["distance_axis"] = {
        "bin_spacing_m": round(float(bin_spacing_m), 4),
        "range_bias_m": round(float(range_bias_m), 4),
        "min_range_m": min_range_m,
        "max_range_m": max_range_m,
        "breath_distance_m": round(float(_bin_to_distance_m(br_bin, bin_spacing_m, range_bias_m)), 3),
        "heart_distance_m": round(float(_bin_to_distance_m(heart_bin, bin_spacing_m, range_bias_m)), 3),
        "gate_applies_to": "breath_only",
    }

    save_result(result, waveforms, output_dir)
    plot_path = plot_result(result, waveforms, output_dir, breath_view_start_s=breath_view_start_s)
    range_fft_raw_path, range_fft_diag_path = save_range_fft_map(npz_files, output_dir, session=session, best_ch=br_ch, frame_start=frame_start, frame_end=frame_end)
    range_fft_grid_raw_path, range_fft_grid_diag_path = save_range_fft_channel_grid(npz_files, output_dir, session=session, frame_start=frame_start, frame_end=frame_end)
    fft_png = save_selected_channel_range_fft(npz_files=npz_files, output_dir=output_dir, session=session, breath_ch=int(br_ch), breath_bin=int(br_bin), heart_ch=int(heart_ch), heart_bin=int(heart_bin), frame_start=frame_start, frame_end=frame_end, view_start_s=breath_view_start_s, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
    phase_png = save_breath_raw_phase_plot(npz_files=npz_files, output_dir=output_dir, session=session, breath_ch=int(br_ch), breath_bin=int(br_bin), frame_start=frame_start, frame_end=frame_end, view_start_s=breath_view_start_s, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
    unwrap_phase_png = save_breath_unwrapped_phase_plot(npz_files=npz_files, output_dir=output_dir, session=session, breath_ch=int(br_ch), breath_bin=int(br_bin), frame_start=frame_start, frame_end=frame_end, view_start_s=breath_view_start_s, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
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


def _analyze_long_record_v23(
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
    heart_reference_candidates: list[tuple[int, int]] | None = None,
    ext_br_bpm: float | None = None,
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    npz_files = collect_npz_parts(parts_dir, pattern=pattern)
    if not npz_files:
        raise FileNotFoundError(f"No part files matched under: {parts_dir}")

    print(f"[info] found {len(npz_files)} chunk files")
    print(f"[info] parts dir: {parts_dir}")
    print(f"[info] output dir: {output_dir}")

    channel_power, bin_power_acc, _ = accumulate_range_profile(npz_files, frame_start=frame_start, frame_end=frame_end)
    best_ch_auto = int(np.argmax(channel_power))
    iq_sample = next(_iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end), None)
    if iq_sample is None:
        raise RuntimeError("Selected frame range contains no data.")
    iq_fd_sample = _as_range_cube(iq_sample)

    gate_mask = _distance_gate_to_bin_mask(bin_power_acc.shape[0], min_range_m, max_range_m, bin_spacing_m, range_bias_m)
    if not np.any(gate_mask):
        raise RuntimeError("Distance gate excluded all range bins. Please check min/max range settings.")

    bin_power_acc_gated = np.array(bin_power_acc, copy=True)
    bin_power_acc_gated[~gate_mask, :] = 0.0
    br_ch, br_bin, _hr_ch_gate, _hr_bin_gate, breath_gate_summaries = select_separate_channels_bins(
        bin_power_acc_gated, iq_fd_sample, iq_sample.shape[0], channel_override=channel_override
    )
    _br_ch_full, _br_bin_full, _hr_ch_initial, _hr_bin_initial, heart_full_summaries = select_separate_channels_bins(
        bin_power_acc, iq_fd_sample, iq_sample.shape[0], channel_override=channel_override
    )
    hr_ch, hr_bin, heart_refined_summaries = _select_refined_heart_candidate(
        npz_files=npz_files,
        # 心跳 bin 候选同样施加距离门控（2026-08-16 修：此前用全距离
        # bin_power_acc，sub-013/016 心跳 bin 选到 20m 远端杂波 bin=252/247，
        # 60GHz 桌面雷达物理上探测不到该距离，是选 bin 缺陷而非数据问题）。
        bin_power_acc=bin_power_acc_gated,
        iq_fd_sample=iq_fd_sample,
        n_frames_sample=iq_sample.shape[0],
        method=method,
        frame_start=frame_start,
        frame_end=frame_end,
        channel_override=channel_override,
        top_k_per_channel=1,
        reference_candidates=heart_reference_candidates,
    )
    print(f"[bins] breath_ch={br_ch}, breath_bin={br_bin}, heart_ch={hr_ch}, heart_bin={hr_bin}, auto_best_ch={best_ch_auto}")

    disp_br, disp_hr, n_frames = extract_displacement_separate(npz_files, br_ch, br_bin, hr_ch, hr_bin, frame_start=frame_start, frame_end=frame_end)
    result, waveforms = _analyze_displacement_v23(disp_br, disp_hr, n_frames, method=method, session=session, ext_br_bpm=ext_br_bpm)
    result["external_respiration_bpm"] = round(ext_br_bpm, 1) if ext_br_bpm is not None else None
    result["best_channel"] = br_ch
    result["auto_best_channel"] = best_ch_auto
    result["channels"] = {"breath": br_ch, "heart": hr_ch}
    result["channel_selection"] = {"breath_gated": breath_gate_summaries, "heart_full_range": heart_full_summaries, "heart_refined": heart_refined_summaries}
    result["bins"] = {"breath": br_bin, "heart": hr_bin}
    result["n_frames"] = n_frames
    result["distance_axis"] = {
        "bin_spacing_m": round(float(bin_spacing_m), 4),
        "range_bias_m": round(float(range_bias_m), 4),
        "min_range_m": min_range_m,
        "max_range_m": max_range_m,
        "breath_distance_m": round(float(_bin_to_distance_m(br_bin, bin_spacing_m, range_bias_m)), 3),
        "heart_distance_m": round(float(_bin_to_distance_m(hr_bin, bin_spacing_m, range_bias_m)), 3),
        "gate_applies_to": "breath_and_heart",
    }

    save_result(result, waveforms, output_dir)
    plot_path = plot_result(result, waveforms, output_dir, breath_view_start_s=breath_view_start_s)
    range_fft_raw_path, range_fft_diag_path = save_range_fft_map(npz_files, output_dir, session=session, best_ch=br_ch, frame_start=frame_start, frame_end=frame_end)
    range_fft_grid_raw_path, range_fft_grid_diag_path = save_range_fft_channel_grid(npz_files, output_dir, session=session, frame_start=frame_start, frame_end=frame_end)
    channels = result.get("channels", {})
    fft_png = save_selected_channel_range_fft(npz_files=npz_files, output_dir=output_dir, session=session, breath_ch=int(channels.get("breath", result["best_channel"])), breath_bin=int(result["bins"]["breath"]), heart_ch=int(channels.get("heart", result["best_channel"])), heart_bin=int(result["bins"]["heart"]), frame_start=frame_start, frame_end=frame_end, view_start_s=breath_view_start_s, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
    phase_png = save_breath_raw_phase_plot(npz_files=npz_files, output_dir=output_dir, session=session, breath_ch=int(channels.get("breath", result["best_channel"])), breath_bin=int(result["bins"]["breath"]), frame_start=frame_start, frame_end=frame_end, view_start_s=breath_view_start_s, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
    unwrap_phase_png = save_breath_unwrapped_phase_plot(npz_files=npz_files, output_dir=output_dir, session=session, breath_ch=int(channels.get("breath", result["best_channel"])), breath_bin=int(result["bins"]["breath"]), frame_start=frame_start, frame_end=frame_end, view_start_s=breath_view_start_s, bin_spacing_m=bin_spacing_m, range_bias_m=range_bias_m)
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


def estimate_respiration_bpm_from_acq(acq_path) -> float | None:
    """从 Biopac .acq 金标准文件提取呼吸带(RSP)全段中位呼吸率, 作为毫米波侧
    候选心率门控的外部先验 ext_br_bpm (approach ① / A2 接线)。

    这是 0816 报告点明的「呼吸带应是必做项」的落地: 此前 RSP 只在金标准侧
    (validate_gold_anchor.py) 用, 从未喂进毫米波侧候选频率判定。本函数把 RSP
    呼吸率接到 respiration_harmonic_reject, 直接剔除落在 2*br / 3*br 附近的候选,
    正面解决 97795/97796 那种「质量门控全绿却锁半频」的强而错。

    退化策略(保证向后兼容):
      · 无 bioread / 读取失败        -> 返回 None (门控不触发)
      · .acq 无 RSP 通道(如 sub-2_)  -> 返回 None (门控自动禁用)
      · 复用 gold_standard_qa.rsp_qa 项目标准清洗; 模块不可导入则退化为内联带通+峰值
    仅做全段中位估计(呼吸率段内较稳, 见 0816 报告 21/25 次/分); 如需逐窗可变,
    后续可把返回值改为按时间轴的分段数组并透传 array 版 ext_br_bpm。
    """
    try:
        import bioread
    except Exception:
        return None
    try:
        da = bioread.read_file(str(acq_path))
    except Exception:
        return None
    sr = da.samples_per_second
    rsp_idx = next((i for i, c in enumerate(da.channels) if "RSP" in str(c.name).upper()), None)
    if rsp_idx is None:
        return None
    rsp = np.asarray(da.channels[rsp_idx].data).astype(float)
    if len(rsp) < sr * 10:
        return None

    # 优先复用项目标准 RSP 清洗(与金标准侧一致)
    try:
        from gold_standard_qa import rsp_qa
        br, rep = rsp_qa(rsp, sr, 0, len(rsp))
        if br is not None and rep.get("usable"):
            return float(br)
        # 不可用时仍返回中位估计: 门控自带 ±容差, 弱先验优于无
        return float(br) if br is not None else None
    except Exception:
        pass

    # 退化: 内联带通 + 峰值(与 gold_standard_qa 参数一致)
    seg = rsp - np.median(rsp)
    sos = signal.butter(4, (0.1, 0.7), btype="band", fs=sr, output="sos")
    seg_f = signal.sosfiltfilt(sos, seg)
    peaks, _ = signal.find_peaks(seg_f, distance=int(0.5 * sr), prominence=0.2)
    if len(peaks) < 3:
        return None
    period = np.diff(peaks) / sr
    period = period[(period >= 60.0 / 42.0) & (period <= 60.0 / 6.0)]
    if len(period) < 2:
        return None
    return float(60.0 / np.median(period))


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
    bin_spacing_m: float = 0.08,
    range_bias_m: float = 0.0,
    forced_heart_ch: int | None = None,
    forced_heart_bin: int | None = None,
    timestamps_path: Path | None = None,
    behavior_markers_path: Path | None = None,
    behavior_session_label: str | None = None,
    behavior_status: str | None = None,
    heart_waveform_view: str = "last_20_s",
    heart_reference_candidates: list[tuple[int, int]] | None = None,
    ext_br_bpm: float | None = None,
    acq_path: str | Path | None = None,
) -> tuple[dict, tuple]:
    if (forced_heart_ch is None) ^ (forced_heart_bin is None):
        raise ValueError("forced_heart_ch and forced_heart_bin must be provided together.")

    # Approach ① (A2): 从 Biopac .acq 金标准提取 RSP 呼吸率, 作为毫米波侧外部先验
    # ext_br_bpm。此前提案只在金标准侧用 RSP, 从未喂进毫米波候选频率判定; 现在接上。
    # 若显式传入 ext_br_bpm 则优先, acq_path 仅作自动派生(向后兼容)。
    if ext_br_bpm is None and acq_path is not None:
        ext_br_bpm = estimate_respiration_bpm_from_acq(acq_path)
        if ext_br_bpm is not None:
            print(f"[RSP gate] acq={acq_path} -> ext_br_bpm={ext_br_bpm:.1f} (呼吸带先验已接入毫米波侧)")
        else:
            print("[RSP gate] acq 无 RSP 通道或读取失败 -> 门控自动禁用(向后兼容)")

    runner = _analyze_long_record_v23
    kwargs = dict(
        parts_dir=parts_dir,
        output_dir=output_dir,
        session=session,
        method=method,
        pattern=pattern,
        breath_view_start_s=breath_view_start_s,
        frame_start=frame_start,
        frame_end=frame_end,
        channel_override=channel_override,
        min_range_m=min_range_m,
        max_range_m=max_range_m,
        bin_spacing_m=bin_spacing_m,
        range_bias_m=range_bias_m,
        ext_br_bpm=ext_br_bpm,
    )
    if forced_heart_ch is not None and forced_heart_bin is not None:
        runner = _analyze_long_record_with_forced_heart_candidate_v23
        kwargs["heart_ch"] = int(forced_heart_ch)
        kwargs["heart_bin"] = int(forced_heart_bin)
    else:
        kwargs["heart_reference_candidates"] = heart_reference_candidates

    result, waveforms = runner(**kwargs)
    forced_selection = forced_heart_ch is not None and forced_heart_bin is not None
    result["algorithm_returned"] = True
    result["quality_valid"] = not forced_selection
    result["selection_status"] = "forced_candidate_unvalidated" if forced_selection else "selected"
    result["failure_reason"] = None if not forced_selection else "FORCED_HEART_CANDIDATE_REQUIRES_EXTERNAL_JUSTIFICATION"
    result["version"] = "v3.1.1"
    result["pipeline"] = "v3.1.1_phase_stable_bins_k3_breath_guided_vmd_guarded_hr_fusion"
    result["parent_version"] = "v3.1"
    result["configuration"] = {
        "heart_range_bpm": [HR_LO_BPM, HR_HI_BPM],
        "vmd_k": 3,
        "vmd_window_s": 40.0,
        "vmd_step_s": 20.0,
        "heart_bin_selection": "log1p_hr_snr_times_phase_stability_squared",
        "time_frequency_warning_bpm": HR_TIME_FREQ_WARNING_BPM,
        "heart_signal_hard_gate": {
            "window_s": HEART_SIGNAL_QC_WINDOW_S,
            "min_std_mm": MIN_HEART_WINDOW_STD_MM,
            "candidate_min_usable_ratio": MIN_HEART_CANDIDATE_COVERAGE,
            "rejected_output": "null_with_explicit_status",
        },
    }
    result["usable_dataset_scope"] = ["sub-deep-breath", "sub-rest_3min", "sxq"]
    result["visualization"] = {"heart_waveform_view": heart_waveform_view}

    if timestamps_path is not None:
        attach_behavior_alignment(
            result,
            waveforms,
            timestamps_path=timestamps_path,
            markers_path=behavior_markers_path,
            session_label=behavior_session_label,
            event_level_status=behavior_status,
            frame_start=frame_start,
        )

    save_result(result, waveforms, output_dir)
    plot_result(result, waveforms, output_dir, breath_view_start_s=breath_view_start_s)
    behavior_plot = plot_behavior_aligned_heart(result, waveforms, output_dir)
    if behavior_plot is not None:
        print(f"[behavior plot] {behavior_plot}")
    return result, waveforms
