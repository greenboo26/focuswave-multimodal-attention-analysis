"""Timestamp-aware RS6240 channel coherence audit.

The first audit used ``scipy.signal.coherence(..., fs=100)`` on frame-indexed
arrays. This script keeps that legacy value for comparison, then recomputes
coherence after mapping each channel to a uniform time grid based on the
recorded device or host timestamps. Large timestamp gaps split the record;
coherence is never computed across such a discontinuity.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import signal


ROOT = Path(__file__).resolve().parents[1]
RAW = Path(r"D:\acq_mmwave_data")
OUT = ROOT / "work" / "rs6240_timestamp_coherence_v1"
FRAME_FS = 100.0
BR_BAND = (0.1, 0.5)
HR_BAND = (0.8, 2.0)
CHANNELS = [f"tx{tx}_rx{rx}" for tx in range(2) for rx in range(4)]
SESSIONS = ["sub-3_", "sub-4_", "sub-97793_"]
MAX_FRAMES = 6000
MIN_SEGMENT_FRAMES = 256
GAP_FACTOR = 1.5


def ordered_npz_files(mmwave_dir: Path) -> list[Path]:
    return sorted(mmwave_dir.glob("*_mmwave_datacube.npz")) + sorted(mmwave_dir.glob("*_mmwave_datacube_part*.npz"))


def load_cube(files: list[Path], max_frames: int) -> tuple[np.ndarray, int]:
    chunks = []
    total = 0
    for path in files:
        with np.load(path, allow_pickle=False) as data:
            keys = sorted(k for k in data.files if k.startswith("tx"))
            shapes = {data[k].shape for k in keys}
            if len(keys) != 8 or len(shapes) != 1:
                continue
            take = min(max_frames - total, int(data[keys[0]].shape[0]))
            if take <= 0:
                break
            chunks.append(np.stack([data[k][:take] for k in keys], axis=-1).astype(np.complex64))
            total += take
            if total >= max_frames:
                break
    if not chunks:
        raise RuntimeError(f"No valid 8-channel NPZ data in {files[0].parent}")
    return np.concatenate(chunks, axis=0), total


def load_timestamps(path: Path, max_frames: int) -> np.ndarray:
    rows = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 3:
                continue
            try:
                rows.append((int(row[0]), int(row[1]), int(row[2])))
            except ValueError:
                continue
            if len(rows) >= max_frames:
                break
    return np.asarray(rows, dtype=np.int64)


def choose_bins(cube: np.ndarray, n_bins: int = 5) -> list[int]:
    profile = np.mean(np.abs(cube) ** 2, axis=(0, 2))
    valid = np.arange(len(profile))
    valid = valid[(valid >= 4) & (valid < len(profile) - 2)]
    order = valid[np.argsort(profile[valid])[::-1]]
    selected = []
    for idx in order:
        if all(abs(int(idx) - old) >= 3 for old in selected):
            selected.append(int(idx))
        if len(selected) >= n_bins:
            break
    return selected


def band_mean_coherence(x: np.ndarray, y: np.ndarray, fs: float, band: tuple[float, float]) -> float:
    nperseg = min(1024, len(x))
    if nperseg < MIN_SEGMENT_FRAMES:
        return float("nan")
    freqs, coh = signal.coherence(x, y, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)
    mask = (freqs >= band[0]) & (freqs <= band[1])
    return float(np.nanmean(coh[mask])) if np.any(mask) else float("nan")


def timestamp_segments(values: np.ndarray, timestamps_ms: np.ndarray) -> tuple[list[np.ndarray], dict]:
    """Resample phase values to uniform median-dt grids without crossing gaps."""

    ts = np.asarray(timestamps_ms, dtype=float)
    x = np.asarray(values, dtype=float)
    if len(ts) != len(x) or len(ts) < 2:
        return [], {"input_frames": len(x), "segments": 0, "gap_count": None, "median_dt_ms": None}
    dt = np.diff(ts)
    positive = dt[dt > 0]
    if not len(positive):
        return [], {"input_frames": len(x), "segments": 0, "gap_count": None, "median_dt_ms": None}
    median_dt = float(np.median(positive))
    gap_mask = dt > median_dt * GAP_FACTOR
    cut_points = [0] + (np.where(gap_mask)[0] + 1).tolist() + [len(x)]
    segments = []
    for start, end in zip(cut_points, cut_points[1:]):
        if end - start < MIN_SEGMENT_FRAMES:
            continue
        grid = np.arange(ts[start], ts[end - 1] + median_dt * 0.5, median_dt)
        if len(grid) < MIN_SEGMENT_FRAMES:
            continue
        segments.append(np.interp(grid, ts[start:end], x[start:end]))
    return segments, {
        "input_frames": len(x),
        "segments": len(segments),
        "gap_count": int(np.sum(gap_mask)),
        "median_dt_ms": median_dt,
        "resampled_fs_hz": 1000.0 / median_dt,
        "gap_threshold_ms": median_dt * GAP_FACTOR,
        "discarded_short_gap_segments": max(0, len(cut_points) - 1 - len(segments)),
    }


def timestamp_aware_coherence(x: np.ndarray, y: np.ndarray, timestamps_ms: np.ndarray, band: tuple[float, float]) -> tuple[float, dict]:
    x_segments, info_x = timestamp_segments(x, timestamps_ms)
    y_segments, info_y = timestamp_segments(y, timestamps_ms)
    n = min(len(x_segments), len(y_segments))
    if n == 0:
        return float("nan"), {**info_x, "paired_segments": 0}
    dt = float(info_x["median_dt_ms"])
    fs = 1000.0 / dt
    values = [band_mean_coherence(x_segments[i], y_segments[i], fs, band) for i in range(n)]
    weights = [len(x_segments[i]) for i in range(n)]
    valid = [i for i, value in enumerate(values) if np.isfinite(value)]
    result = float(np.average([values[i] for i in valid], weights=[weights[i] for i in valid])) if valid else float("nan")
    return result, {
        **info_x,
        "paired_segments": n,
        "coherence_segments_used": len(valid),
        "coherence_weighted_by": "resampled segment frame count",
    }


def legacy_coherence(x: np.ndarray, y: np.ndarray, band: tuple[float, float]) -> float:
    return band_mean_coherence(x, y, FRAME_FS, band)


def timestamp_quality_row(session: str, ts: np.ndarray, column: int, source: str) -> dict:
    values = ts[:, column].astype(float)
    dt = np.diff(values)
    duration_s = (values[-1] - values[0]) / 1000.0
    positive = dt[dt > 0]
    return {
        "session": session,
        "timestamp_source": source,
        "frames": len(ts),
        "duration_s": float(duration_s),
        "effective_hz": float((len(ts) - 1) / duration_s) if duration_s > 0 else None,
        "median_dt_ms": float(np.median(positive)) if len(positive) else None,
        "p95_dt_ms": float(np.percentile(positive, 95)) if len(positive) else None,
        "max_dt_ms": float(np.max(positive)) if len(positive) else None,
        "gaps_gt_15ms": int(np.sum(dt > 15.0)),
        "nonpositive_deltas": int(np.sum(dt <= 0)),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    coherence_rows = []
    timestamp_rows = []
    selected_bins = {}
    for session in SESSIONS:
        mmwave = RAW / session / "mmwave"
        files = ordered_npz_files(mmwave)
        cube, n_frames = load_cube(files, MAX_FRAMES)
        ts = load_timestamps(mmwave / f"{session.rstrip('_')}_mmwave_timestamps.csv", n_frames)
        if len(ts) != n_frames:
            raise RuntimeError(f"Timestamp/NPZ length mismatch for {session}: {len(ts)} vs {n_frames}")
        bins = choose_bins(cube)
        selected_bins[session] = bins
        timestamp_rows.extend([
            timestamp_quality_row(session, ts, 1, "device_ms"),
            timestamp_quality_row(session, ts, 2, "host_ms"),
        ])
        for bin_idx in bins:
            phase = np.unwrap(np.angle(cube[:, bin_idx, :]), axis=0)
            for i in range(8):
                for j in range(i + 1, 8):
                    pair = f"{CHANNELS[i]}__{CHANNELS[j]}"
                    same_tx = (i // 4) == (j // 4)
                    for timestamp_source, column in (("device_ms", 1), ("host_ms", 2)):
                        ts_ms = ts[:, column]
                        coh_hr, info = timestamp_aware_coherence(phase[:, i], phase[:, j], ts_ms, HR_BAND)
                        coh_br, _ = timestamp_aware_coherence(phase[:, i], phase[:, j], ts_ms, BR_BAND)
                        coherence_rows.append({
                            "session": session,
                            "range_bin": bin_idx,
                            "pair": pair,
                            "ch_i": CHANNELS[i],
                            "ch_j": CHANNELS[j],
                            "same_tx": same_tx,
                            "timestamp_source": timestamp_source,
                            "coherence_hr_timestamp_aware": coh_hr,
                            "coherence_br_timestamp_aware": coh_br,
                            "coherence_hr_legacy_frame_index": legacy_coherence(phase[:, i], phase[:, j], HR_BAND),
                            "coherence_br_legacy_frame_index": legacy_coherence(phase[:, i], phase[:, j], BR_BAND),
                            **info,
                        })
        print(f"audited {session}: frames={n_frames}, bins={bins}")

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "pairwise_coherence_timestamp_aware.csv", coherence_rows)
    write_csv(OUT / "timestamp_quality.csv", timestamp_rows)
    summary = {
        "sessions": SESSIONS,
        "max_frames_per_session": MAX_FRAMES,
        "bands_hz": {"br": BR_BAND, "hr": HR_BAND},
        "timestamp_sources": {"device_ms": 1, "host_ms": 2},
        "gap_policy": {"gap_factor_of_median_dt": GAP_FACTOR, "minimum_segment_frames": MIN_SEGMENT_FRAMES, "cross_gap_interpolation": False},
        "selected_range_bins": selected_bins,
        "finite_timestamp_aware_hr_rows_by_source": {
            source: int(sum(np.isfinite(float(row["coherence_hr_timestamp_aware"])) for row in coherence_rows if row["timestamp_source"] == source))
            for source in ("device_ms", "host_ms")
        },
        "legacy_method": "frame-index arrays with fs=100 Hz",
        "primary_method": "timestamp interpolation to median-dt uniform grid, segment at large gaps, weighted mean coherence",
        "notes": [
            "This output is a correction audit; it does not by itself establish same-Tx superiority.",
            "Device timestamp is primary; host timestamp is a sensitivity comparison.",
            "After device-timestamp correction, the same-Tx versus cross-Tx direction remains unchanged; this still does not establish same-Tx superiority.",
            "Host timestamp has many large gaps and produced no usable cardiac-band segment under the strict gap policy.",
        ],
    }
    with (OUT / "audit_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(OUT), "rows": len(coherence_rows), "sessions": SESSIONS}, ensure_ascii=False))


if __name__ == "__main__":
    main()
