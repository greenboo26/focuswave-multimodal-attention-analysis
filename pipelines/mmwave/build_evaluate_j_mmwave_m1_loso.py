"""Build raw mmWave M1/Q0 features and evaluate prespecified LOSO ablations.

This is deliberately separate from the established HR/BR pipeline.  It reads
only the 30 s interval immediately preceding each *already trusted* probe in
``J_Data_GROUP_SUMMARY/probe_summary.csv``.  The raw complex range cube is
never modified.  Target channel/range selection is deterministic, based only
on the signal in that window and never on probe labels.

Feature families
----------------
M1: detrended raw phase/micromotion, band powers, spectral peak/harmonic
    structure, and within-window temporal dynamics.  ``phase_peak_*`` values
    are signal descriptors, not validated physiological HR or BR.
M2: existing HR/BR plus explicitly experimental SDNN/RMSSD from the frozen
    trusted-probe table.
Q0: target-selection margin, power contrast, amplitude stability, phase-jump
    rate and timestamp continuity.  These are quality descriptors, not
    exclusions determined from labels.

Validation is leave-one-subject-out (LOSO).  Median imputation and scaling are
fit inside each training fold only; all models have fixed, untuned L2 logistic
regression settings.  Subject-resampled bootstrap confidence intervals are
computed from the held-out predictions.  M1/M2/M3 each include N0 by design,
so their comparison with N0 is a direct time/block-adjusted increment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal
from scipy.integrate import trapezoid
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DEFAULT_CURRENT = ROOT / "output" / "J_Data_GROUP_SUMMARY" / "probe_summary.csv"
DEFAULT_DATA_ROOT = Path(r"J:\Data")
DEFAULT_OUTPUT = ROOT / "output" / "J_Data_M1_RAW_Q0_v1"
DEFAULT_FULL_ROOT = ROOT / "output"

WINDOW_SECONDS = 30.0
MIN_WINDOW_SECONDS = 25.0
RANGE_BIN_MIN = 8
RANGE_BIN_MAX = 180
MAX_CANDIDATES_PER_CHANNEL = 12
SEED = 20260824

NULL_TIME = ["block_num", "block_probe_fraction", "onset_rel_s"]
BEHAVIOR = ["prior_rt_mean", "prior_n_err"]
M1_RAW = [
    "m1_phase_std_rad", "m1_phase_velocity_mad", "m1_phase_accel_mad",
    "m1_log_power_low", "m1_log_power_transition", "m1_log_power_micro", "m1_log_power_high",
    "m1_micro_power_fraction", "m1_phase_peak_micro_hz", "m1_micro_peak_share",
    "m1_micro_spectral_entropy", "m1_harmonic_overlap", "m1_harmonic_power_fraction",
    "m1_phase_std_cv_10s", "m1_micro_power_cv_10s", "m1_phase_trend_rad_s",
]
M2_DERIVED_EXPERIMENTAL = ["hr_bpm", "br_bpm", "log_sdnn_ms_experimental", "log_rmssd_ms_experimental"]
Q0_QUALITY = [
    "q_target_power_snr_db", "q_target_amplitude_cv", "q_phase_jump_fraction",
    "q_frame_gap_fraction", "q_frame_gap_duration_fraction", "q_frame_rate_hz", "q_selection_margin", "q_bin_stability_10s",
    "q_extraction_ok",
]

FEATURE_SETS = {
    "N0": NULL_TIME,
    "B0": NULL_TIME + BEHAVIOR,
    "M1": NULL_TIME + M1_RAW,
    "M2": NULL_TIME + M2_DERIVED_EXPERIMENTAL,
    "M3": NULL_TIME + M1_RAW + M2_DERIVED_EXPERIMENTAL + Q0_QUALITY,
    "F1": NULL_TIME + BEHAVIOR + M1_RAW + M2_DERIVED_EXPERIMENTAL + Q0_QUALITY,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_timestamps(path: Path) -> np.ndarray:
    """Read Python Unix milliseconds (column 3), falling back to column 2."""
    values: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            try:
                values.append(float(row[2] if len(row) >= 3 else row[1]))
            except (IndexError, ValueError):
                continue
    ts = np.asarray(values, dtype=float)
    if len(ts) < 2 or np.any(np.diff(ts) < 0):
        raise ValueError(f"毫米波时间戳缺失或非单调：{path}")
    return ts


def behavior_probes(data_root: Path, subject: str) -> list[dict]:
    rows: list[dict] = []
    beh_dir = data_root / f"sub-{subject}_" / "beh"
    for path in sorted(beh_dir.glob(f"sub-{subject}_Block*_beh.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows.extend(row for row in csv.DictReader(handle) if row.get("is_probe") == "1" and row.get("probe_response"))
    return rows


def prior_error_by_probe(full_root: Path, subject: str) -> dict[int, float]:
    """Read the same pre-probe error field used by the frozen B0 baseline."""
    path = full_root / f"J_Data_SUB{subject}_FULL" / f"sub{subject}_full_windows.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        int(row["probe_id"]): float(row["prior_n_err"])
        for row in payload.get("probes", [])
        if row.get("prior_n_err") is not None
    }


def probe_metadata(probes: list[dict]) -> dict[int, dict]:
    block_counts = Counter(str(row.get("block_num", "")) for row in probes)
    seen: Counter[str] = Counter()
    result: dict[int, dict] = {}
    for index, probe in enumerate(probes, 1):
        block = str(probe.get("block_num", ""))
        seen[block] += 1
        total = block_counts[block]
        result[index] = {
            "block_num": float(block) if block else np.nan,
            "block_probe_fraction": (seen[block] - 1) / (total - 1) if total > 1 else 0.0,
            "probe_onset_ms": float(probe["probe_onset_time"]),
        }
    return result


def ordered_npz_files(mmwave_dir: Path) -> list[Path]:
    files = sorted(mmwave_dir.glob("*_datacube_part*.npz"))
    base = sorted(mmwave_dir.glob("*_datacube.npz"))
    files = base + files
    if not files:
        raise FileNotFoundError(f"未找到毫米波 npz 分片：{mmwave_dir}")
    return files


@dataclass
class ChunkIndex:
    paths: list[Path]
    starts: np.ndarray
    ends: np.ndarray

    @classmethod
    def create(cls, mmwave_dir: Path) -> "ChunkIndex":
        paths = ordered_npz_files(mmwave_dir)
        counts: list[int] = []
        for path in paths:
            with np.load(path) as data:
                keys = sorted(k for k in data.files if k.startswith("tx"))
                if not keys:
                    raise ValueError(f"没有 tx* 复数数组：{path}")
                counts.append(int(data[keys[0]].shape[0]))
        ends = np.cumsum(np.asarray(counts, dtype=int))
        starts = np.r_[0, ends[:-1]]
        return cls(paths, starts, ends)

    def read(self, start: int, end: int) -> np.ndarray:
        """Read [start, end) from compressed chunks with bounded memory."""
        pieces: list[np.ndarray] = []
        hit = np.flatnonzero((self.ends > start) & (self.starts < end))
        for idx in hit:
            local_start = max(0, start - int(self.starts[idx]))
            local_end = min(int(self.ends[idx] - self.starts[idx]), end - int(self.starts[idx]))
            with np.load(self.paths[int(idx)]) as data:
                keys = sorted(k for k in data.files if k.startswith("tx"))
                pieces.append(np.stack([data[k][local_start:local_end] for k in keys], axis=-1).astype(np.complex64))
        if not pieces:
            raise ValueError(f"帧范围没有数据：{start}:{end}")
        return np.concatenate(pieces, axis=0)


def robust_mad(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    med = np.nanmedian(values)
    return float(np.nanmedian(np.abs(values - med)))


def band_power(freq: np.ndarray, power: np.ndarray, lo: float, hi: float) -> float:
    mask = (freq >= lo) & (freq <= hi) & np.isfinite(power)
    if mask.sum() < 2:
        return np.nan
    # NumPy 2.x removed np.trapz; SciPy's trapezoid has identical numerical
    # intent here and is available in the project analysis runtime.
    return float(trapezoid(power[mask], freq[mask]))


def peak_in_band(freq: np.ndarray, power: np.ndarray, lo: float, hi: float) -> tuple[float, float]:
    mask = (freq >= lo) & (freq <= hi) & np.isfinite(power)
    if not np.any(mask):
        return np.nan, np.nan
    f, p = freq[mask], power[mask]
    idx = int(np.argmax(p))
    return float(f[idx]), float(p[idx])


def normalized_entropy(power: np.ndarray) -> float:
    x = np.asarray(power, dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) < 2:
        return np.nan
    p = x / x.sum()
    return float(-(p * np.log(p)).sum() / np.log(len(p)))


def phase_series(cube: np.ndarray, bin_idx: int, channel: int) -> tuple[np.ndarray, np.ndarray]:
    z = cube[:, bin_idx, channel]
    phase = np.unwrap(np.angle(z)).astype(float)
    phase_dt = signal.detrend(phase, type="linear")
    return phase, phase_dt


def candidate_scores(cube: np.ndarray, fs: float) -> tuple[int, int, float, float, float]:
    """Return deterministic unlabeled target and its score/runner-up/power."""
    power = np.mean(np.abs(cube) ** 2, axis=0)  # bin x channel
    lo, hi = RANGE_BIN_MIN, min(RANGE_BIN_MAX, power.shape[0] - 1)
    candidates: list[tuple[float, int, int, float]] = []
    reference = float(np.median(power[lo:hi + 1])) + 1e-12
    for channel in range(power.shape[1]):
        indices = np.argsort(power[lo:hi + 1, channel])[-MAX_CANDIDATES_PER_CHANNEL:] + lo
        for bin_idx in indices:
            _, phase_dt = phase_series(cube, int(bin_idx), channel)
            amp = np.abs(cube[:, int(bin_idx), channel])
            amp_cv = float(np.std(amp) / (np.mean(amp) + 1e-12))
            # An unlabeled signal-quality score: phase modulation above noise,
            # sufficient return power, and a soft penalty for amplitude flicker.
            score = math.log1p(float(np.std(phase_dt))) + 0.18 * math.log1p(float(power[int(bin_idx), channel] / reference)) - 0.35 * min(amp_cv, 3.0)
            candidates.append((score, int(bin_idx), channel, float(power[int(bin_idx), channel])))
    if not candidates:
        raise ValueError("没有可用的目标距离单元候选")
    candidates.sort(reverse=True)
    best = candidates[0]
    runner_score = candidates[1][0] if len(candidates) > 1 else best[0]
    return best[1], best[2], float(best[0]), float(runner_score), float(best[3] / reference)


def subwindow_best_bins(cube: np.ndarray, fs: float, selected_bin: int) -> float:
    n = len(cube)
    bins: list[int] = []
    for start in np.linspace(0, n, 4, dtype=int)[:-1]:
        end = min(n, start + n // 3)
        if end - start < max(100, int(fs * 5)):
            continue
        b, _c, *_ = candidate_scores(cube[start:end], fs)
        bins.append(b)
    return float(np.mean(np.abs(np.asarray(bins) - selected_bin))) if bins else np.nan


def extract_features(cube: np.ndarray, timestamps_ms: np.ndarray) -> tuple[dict, dict]:
    """Extract one unlabeled M1/Q0 row; return row and plotting diagnostics."""
    dt_s = np.diff(timestamps_ms) / 1000.0
    duration_s = float((timestamps_ms[-1] - timestamps_ms[0]) / 1000.0)
    if duration_s <= 0:
        raise ValueError("时间戳窗口没有正时长")
    # The acquisition timestamps contain occasional long inter-frame gaps.
    # Frequency features must use elapsed time, not the modal short interval.
    # Resampling phase and magnitude onto an equal-duration grid preserves the
    # 30-second window's frequency scale while Q0 retains the gap diagnostic.
    fs = float((len(timestamps_ms) - 1) / duration_s)
    bin_idx, channel, score, runner, power_ratio = candidate_scores(cube, fs)
    phase, x_original = phase_series(cube, bin_idx, channel)
    amp_original = np.abs(cube[:, bin_idx, channel]).astype(float)
    time_original = (timestamps_ms - timestamps_ms[0]) / 1000.0
    keep = np.r_[True, np.diff(time_original) > 0]
    time_uniform = np.linspace(0.0, duration_s, len(timestamps_ms))
    x = np.interp(time_uniform, time_original[keep], x_original[keep])
    phase_uniform = np.interp(time_uniform, time_original[keep], phase[keep])
    amp = np.interp(time_uniform, time_original[keep], amp_original[keep])
    freq, power = signal.periodogram(x, fs=fs, detrend="linear", window="hann")
    low = band_power(freq, power, 0.08, 0.50)
    transition = band_power(freq, power, 0.50, 0.80)
    micro = band_power(freq, power, 0.80, 2.50)
    high = band_power(freq, power, 2.50, 5.00)
    total = band_power(freq, power, 0.08, 5.00)
    micro_mask = (freq >= 0.80) & (freq <= 2.50)
    micro_peak_hz, micro_peak_power = peak_in_band(freq, power, 0.80, 2.50)
    low_peak_hz, _ = peak_in_band(freq, power, 0.08, 0.50)
    micro_max = float(np.max(power[micro_mask])) if np.any(micro_mask) else np.nan
    harmonic_power = 0.0
    harmonic_hits = 0
    if np.isfinite(low_peak_hz) and low_peak_hz > 0:
        resolution = float(np.median(np.diff(freq))) if len(freq) > 1 else 0.03
        for k in range(2, 11):
            h = k * low_peak_hz
            if h > 2.50:
                break
            if h >= 0.80:
                local = np.abs(freq - h) <= max(1.5 * resolution, 0.025)
                if np.any(local):
                    harmonic_power += float(np.max(power[local]))
                    harmonic_hits += 1
    chunks = np.array_split(x, 3)
    chunk_std = np.asarray([np.std(part) for part in chunks if len(part) >= 20], float)
    chunk_micro = []
    for part in chunks:
        if len(part) < max(40, int(fs * 5)):
            continue
        f0, p0 = signal.periodogram(part, fs=fs, detrend="linear", window="hann")
        chunk_micro.append(band_power(f0, p0, 0.80, 2.50))
    dx = np.diff(x)
    ddx = np.diff(dx)
    gap_threshold = max(2.0 / fs, 2.5 * float(np.median(dt_s)))
    row = {
        "m1_phase_std_rad": float(np.std(x)),
        "m1_phase_velocity_mad": robust_mad(dx) * fs,
        "m1_phase_accel_mad": robust_mad(ddx) * fs * fs,
        "m1_log_power_low": float(np.log1p(low)),
        "m1_log_power_transition": float(np.log1p(transition)),
        "m1_log_power_micro": float(np.log1p(micro)),
        "m1_log_power_high": float(np.log1p(high)),
        "m1_micro_power_fraction": float(micro / (total + 1e-12)),
        "m1_phase_peak_micro_hz": micro_peak_hz,
        "m1_micro_peak_share": float(micro_peak_power / (micro_max + 1e-12)),
        "m1_micro_spectral_entropy": normalized_entropy(power[micro_mask]),
        "m1_harmonic_overlap": float(harmonic_hits),
        "m1_harmonic_power_fraction": float(harmonic_power / (micro + 1e-12)),
        "m1_phase_std_cv_10s": float(np.std(chunk_std) / (np.mean(chunk_std) + 1e-12)) if len(chunk_std) else np.nan,
        "m1_micro_power_cv_10s": float(np.std(chunk_micro) / (np.mean(chunk_micro) + 1e-12)) if chunk_micro else np.nan,
        "m1_phase_trend_rad_s": float(np.polyfit(time_uniform, phase_uniform, 1)[0]) if len(x) > 2 else np.nan,
        "q_target_power_snr_db": float(10 * np.log10(power_ratio + 1e-12)),
        "q_target_amplitude_cv": float(np.std(amp) / (np.mean(amp) + 1e-12)),
        "q_phase_jump_fraction": float(np.mean(np.abs(dx) > (np.pi / 2))),
        "q_frame_gap_fraction": float(np.mean(dt_s > gap_threshold)),
        "q_frame_gap_duration_fraction": float(np.sum(np.maximum(dt_s - 1.0 / fs, 0.0)) / duration_s),
        "q_frame_rate_hz": fs,
        "q_selection_margin": float(score - runner),
        "q_bin_stability_10s": subwindow_best_bins(cube, fs, bin_idx),
        "q_extraction_ok": 1.0,
        "q_target_bin": bin_idx,
        "q_target_channel": channel,
    }
    diag = {"phase": x, "amplitude": amp, "freq": freq, "power": power, "fs": fs, "target_bin": bin_idx, "target_channel": channel}
    return row, diag


def plot_diagnostic(diag: dict, output: Path, subject: str, probe_id: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(diag["phase"])
    amp = np.asarray(diag["amplitude"])
    t = np.arange(len(x)) / diag["fs"]
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), constrained_layout=True)
    axes[0].plot(t, x, linewidth=0.7)
    axes[0].set(title=f"sub-{subject}, probe {probe_id}: detrended raw phase (bin {diag['target_bin']}, ch {diag['target_channel']})", xlabel="seconds since window start (probe at 30 s)", ylabel="radians")
    axes[1].plot(t, amp, linewidth=0.7, color="#996633")
    axes[1].set(xlabel="seconds since window start (probe at 30 s)", ylabel="magnitude", title="Return-amplitude stability")
    f, p = np.asarray(diag["freq"]), np.asarray(diag["power"])
    axes[2].plot(f, p, linewidth=0.8)
    axes[2].axvspan(.08, .50, alpha=.12, color="#4c78a8", label="low")
    axes[2].axvspan(.80, 2.50, alpha=.12, color="#f58518", label="micro")
    axes[2].set(xlim=(0, 5), xlabel="Hz", ylabel="power", title="Raw-phase spectrum")
    axes[2].legend(frameon=False, ncol=2)
    fig.savefig(output, dpi=150)
    plt.close(fig)


def build_raw_matrix(current: pd.DataFrame, data_root: Path, full_root: Path, subjects: set[str] | None, diagnostic_subjects: set[str], output: Path) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    failures: list[dict] = []
    started = time.perf_counter()
    for subject, group in current.groupby("subject", sort=True):
        if subjects is not None and subject not in subjects:
            continue
        subject_dir = data_root / f"sub-{subject}_"
        try:
            ts_path = next((subject_dir / "mmwave").glob("*_timestamps.csv"))
            timestamps = load_timestamps(ts_path)
            chunks = ChunkIndex.create(subject_dir / "mmwave")
            if int(chunks.ends[-1]) != len(timestamps):
                raise ValueError(f"npz 帧数 {int(chunks.ends[-1])} 与时间戳行数 {len(timestamps)} 不一致")
            meta = probe_metadata(behavior_probes(data_root, subject))
            prior_errors = prior_error_by_probe(full_root, subject)
        except Exception as exc:
            for _, source in group.iterrows():
                failures.append({"subject": subject, "probe_id": int(source.probe_id), "reason": f"subject_setup: {exc}"})
            continue
        diagnostic_remaining = 3 if subject in diagnostic_subjects else 0
        for _, source in group.iterrows():
            probe_id = int(source.probe_id)
            base = source.to_dict()
            base["subject"] = subject
            base["probe_id"] = probe_id
            base["log_sdnn_ms_experimental"] = float(np.log1p(float(source.sdnn_ms)))
            base["log_rmssd_ms_experimental"] = float(np.log1p(float(source.rmssd_ms)))
            meta_row = meta.get(probe_id)
            if meta_row is None:
                failures.append({"subject": subject, "probe_id": probe_id, "reason": "behavior_probe_id_not_found"})
                continue
            onset_ms = meta_row["probe_onset_ms"]
            start_idx = int(np.searchsorted(timestamps, onset_ms - WINDOW_SECONDS * 1000, side="left"))
            end_idx = int(np.searchsorted(timestamps, onset_ms, side="left"))
            duration = (timestamps[end_idx - 1] - timestamps[start_idx]) / 1000 if end_idx > start_idx else 0
            base.update(meta_row, prior_n_err=prior_errors.get(probe_id, np.nan), onset_rel_s=(onset_ms - timestamps[0]) / 1000, m1_window_start_ms=float(onset_ms - WINDOW_SECONDS * 1000), m1_window_end_ms=float(onset_ms), m1_window_duration_s=float(duration))
            try:
                if duration < MIN_WINDOW_SECONDS:
                    raise ValueError(f"可用窗口不足 {MIN_WINDOW_SECONDS:g}s（{duration:.2f}s）")
                cube = chunks.read(start_idx, end_idx)
                raw, diag = extract_features(cube, timestamps[start_idx:end_idx])
                base.update(raw)
                if diagnostic_remaining:
                    plot_diagnostic(diag, output / "representative_diagnostics" / f"sub-{subject}_probe-{probe_id:02d}.png", subject, probe_id)
                    diagnostic_remaining -= 1
                del cube
            except Exception as exc:
                base.update({name: np.nan for name in M1_RAW + Q0_QUALITY})
                base["q_extraction_ok"] = 0.0
                failures.append({"subject": subject, "probe_id": probe_id, "reason": str(exc)})
            rows.append(base)
        elapsed = time.perf_counter() - started
        print(f"feature extraction: sub-{subject}; rows={len(rows)}; elapsed={elapsed / 60:.1f} min", flush=True)
    matrix = pd.DataFrame(rows).sort_values(["subject", "probe_id"]).reset_index(drop=True)
    audit = {
        "window_definition": "[probe_onset - 30 s, probe_onset), exact behavior Unix timestamp mapped to radar timestamp column 3",
        "trusted_input_rows_requested": int(len(current) if subjects is None else len(current[current.subject.isin(subjects)])),
        "feature_rows": int(len(matrix)),
        "subjects": int(matrix.subject.nunique()) if not matrix.empty else 0,
        "failures": failures,
        "n_failures": int(len(failures)),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "selection_policy": "unlabeled per-window phase modulation + return-power score; no probe labels, model outputs or external physiology used",
    }
    return matrix, audit


def subject_equal_weights(subjects: np.ndarray) -> np.ndarray:
    counts = Counter(subjects.tolist())
    return np.asarray([1.0 / counts[s] for s in subjects], dtype=float)


def metric_bundle(y: np.ndarray, score: np.ndarray) -> dict:
    pred = (score >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, score)) if len(np.unique(y)) == 2 else None,
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
    }


def evaluate_one(data: pd.DataFrame, features: list[str], target: str, bootstrap: int, seed: int) -> tuple[dict, pd.DataFrame]:
    use = data[data.label.isin([1, 2, 3, 4])].copy() if target == "nonfocus_vs_focus" else data[data.label.isin([1, 3])].copy()
    use["target"] = (use.label != 1).astype(int) if target == "nonfocus_vs_focus" else (use.label == 3).astype(int)
    predictions: list[pd.DataFrame] = []
    for fold, held_out in enumerate(sorted(use.subject.unique())):
        train, test = use[use.subject != held_out], use[use.subject == held_out]
        if train.target.nunique() < 2 or test.empty:
            continue
        model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0, random_state=seed + fold))
        model.fit(train[features].to_numpy(float), train.target.to_numpy(int), logisticregression__sample_weight=subject_equal_weights(train.subject.to_numpy(str)))
        frame = test[["subject", "probe_id", "label"]].copy()
        frame["y_true"] = test.target.to_numpy(int)
        frame["score"] = model.predict_proba(test[features].to_numpy(float))[:, 1]
        predictions.append(frame)
    pred = pd.concat(predictions, ignore_index=True)
    metrics = metric_bundle(pred.y_true.to_numpy(int), pred.score.to_numpy(float))
    rng = np.random.default_rng(seed)
    subject_list = pred.subject.unique()
    by_subject = {s: np.flatnonzero(pred.subject.to_numpy(str) == s) for s in subject_list}
    boots = {"roc_auc": [], "balanced_accuracy": []}
    for _ in range(bootstrap):
        sampled = rng.choice(subject_list, len(subject_list), replace=True)
        index = np.concatenate([by_subject[s] for s in sampled])
        y, score = pred.y_true.to_numpy(int)[index], pred.score.to_numpy(float)[index]
        if len(np.unique(y)) < 2:
            continue
        result = metric_bundle(y, score)
        for key in boots:
            boots[key].append(result[key])
    for key, values in boots.items():
        metrics[f"{key}_ci95"] = [float(v) for v in np.quantile(values, [.025, .975])] if values else [None, None]
    metrics.update({"target": target, "features": features, "n": int(len(pred)), "subjects": int(pred.subject.nunique()), "positive_n": int(pred.y_true.sum()), "positive_rate": float(pred.y_true.mean()), "bootstrap_valid": int(len(boots["roc_auc"]))})
    return metrics, pred


def bootstrap_deltas(predictions: dict[str, pd.DataFrame], target: str, bootstrap: int, seed: int) -> list[dict]:
    """Subject bootstrap CIs for each prespecified model's delta to N0 and B0."""
    reference = {name: frame[frame.target == target].set_index(["subject", "probe_id"])[["y_true", "score"]] for name, frame in predictions.items()}
    subjects = reference["N0"].index.get_level_values("subject").unique().to_numpy()
    rng = np.random.default_rng(seed + (0 if target == "nonfocus_vs_focus" else 1000))
    rows = []
    for name, frame in reference.items():
        joined_n0 = frame.join(reference["N0"], lsuffix="_model", rsuffix="_n0", how="inner")
        joined_b0 = frame.join(reference["B0"], lsuffix="_model", rsuffix="_b0", how="inner")
        def arrays_and_subject_index(joined: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
            subject_array = joined.index.get_level_values("subject").to_numpy(str)
            available = np.unique(subject_array)
            index = {s: np.flatnonzero(subject_array == s) for s in available}
            return (joined.y_true_model.to_numpy(int), joined.score_model.to_numpy(float), joined.score_n0.to_numpy(float) if "score_n0" in joined else joined.score_b0.to_numpy(float), available, index)
        y_n0, score_model_n0, score_ref_n0, subjects_n0, index_n0 = arrays_and_subject_index(joined_n0)
        y_b0, score_model_b0, score_ref_b0, subjects_b0, index_b0 = arrays_and_subject_index(joined_b0)
        values = {"delta_auc_vs_N0": [], "delta_auc_vs_B0": [], "delta_balanced_accuracy_vs_N0": [], "delta_balanced_accuracy_vs_B0": []}
        for _ in range(bootstrap):
            sample_n0 = rng.choice(subjects_n0, len(subjects_n0), replace=True)
            sample_b0 = rng.choice(subjects_b0, len(subjects_b0), replace=True)
            ia = np.concatenate([index_n0[s] for s in sample_n0])
            ib = np.concatenate([index_b0[s] for s in sample_b0])
            if len(np.unique(y_n0[ia])) < 2 or len(np.unique(y_b0[ib])) < 2:
                continue
            values["delta_auc_vs_N0"].append(roc_auc_score(y_n0[ia], score_model_n0[ia]) - roc_auc_score(y_n0[ia], score_ref_n0[ia]))
            values["delta_auc_vs_B0"].append(roc_auc_score(y_b0[ib], score_model_b0[ib]) - roc_auc_score(y_b0[ib], score_ref_b0[ib]))
            values["delta_balanced_accuracy_vs_N0"].append(balanced_accuracy_score(y_n0[ia], score_model_n0[ia] >= .5) - balanced_accuracy_score(y_n0[ia], score_ref_n0[ia] >= .5))
            values["delta_balanced_accuracy_vs_B0"].append(balanced_accuracy_score(y_b0[ib], score_model_b0[ib] >= .5) - balanced_accuracy_score(y_b0[ib], score_ref_b0[ib] >= .5))
        row = {"target": target, "feature_set": name}
        for key, vals in values.items():
            row[key] = float(np.mean(vals)) if vals else np.nan
            row[f"{key}_ci95"] = [float(v) for v in np.quantile(vals, [.025, .975])] if vals else [None, None]
        rows.append(row)
    return rows


def write_report(output: Path, audit: dict, results: list[dict], deltas: list[dict], input_path: Path) -> None:
    result_df = pd.DataFrame(results)
    lines = [
        "# J:\\Data 原始毫米波 M1/Q0 严格 LOSO 增量验证",
        "",
        "## 预设边界",
        "",
        f"- 输入是现有可信探针表的 {audit['feature_rows']} 行，覆盖 {audit['subjects']} 名被试。",
        "- 每个特征窗固定为探针前 30 秒，按行为 Unix 时间戳严格对齐至毫米波 Python Unix 时间戳列；不跨探针、休息或 block。",
        "- M1 的频谱峰为原始相位信号描述，不能解释为已验证心率或呼吸率；M2 的 SDNN/RMSSD 仍是实验性特征。",
        "- 留一被试交叉验证中，填补与标准化仅在训练被试拟合；逻辑回归超参数固定，未用标签选择原始信号目标或调参。",
        "",
        "## 特征集",
        "",
        "| 集合 | 定义 |",
        "|---|---|",
        "| N0 | 时间、Block、Block 内探针位置 |",
        "| B0 | N0 + 探针前行为 |",
        "| M1 | N0 + 原始相位/微动、频带功率、谱峰/谐波、时间动态 |",
        "| M2 | N0 + HR/BR + 实验性 SDNN/RMSSD |",
        "| M3 | N0 + M1 + M2 + Q0 质量变量 |",
        "| F1 | B0 + M3，检验毫米波相对行为的增量 |",
        "",
        "## LOSO 结果",
        "",
        "| 目标 | 特征集 | n | 被试 | AUC [被试 bootstrap 95% CI] | 平衡准确率 [95% CI] |",
        "|---|---|---:|---:|---|---|",
    ]
    for _, row in result_df.iterrows():
        auc_ci, ba_ci = row.roc_auc_ci95, row.balanced_accuracy_ci95
        lines.append(f"| {row.target} | {row.feature_set} | {int(row.n)} | {int(row.subjects)} | {row.roc_auc:.3f} [{auc_ci[0]:.3f}, {auc_ci[1]:.3f}] | {row.balanced_accuracy:.3f} [{ba_ci[0]:.3f}, {ba_ci[1]:.3f}] |")
    lines += ["", "## 相对增量", "", "| 目标 | 特征集 | ΔAUC vs N0 [95% CI] | ΔAUC vs B0 [95% CI] |", "|---|---|---|---|"]
    for row in deltas:
        n0, b0 = row["delta_auc_vs_N0_ci95"], row["delta_auc_vs_B0_ci95"]
        lines.append(f"| {row['target']} | {row['feature_set']} | {row['delta_auc_vs_N0']:.3f} [{n0[0]:.3f}, {n0[1]:.3f}] | {row['delta_auc_vs_B0']:.3f} [{b0[0]:.3f}, {b0[1]:.3f}] |")
    lines += ["", f"输入 SHA-256：`{sha256(input_path)}`。完整逐窗预测、失败审计和特征矩阵在本目录。", ""]
    (output / "J_Data_M1_Q0_LOSO报告.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--full-root", type=Path, default=DEFAULT_FULL_ROOT, help="既有逐被试 JSON 输出根目录，用于冻结的 B0 行为错误变量")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--subjects", nargs="*", help="仅提取指定被试，用于资源诊断，例如 056")
    parser.add_argument("--diagnostic-subjects", nargs="*", default=["056"], help="保存前三个代表性窗口的原始特征诊断图")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--extract-only", action="store_true", help="只构建原始特征矩阵，不运行 LOSO")
    parser.add_argument("--reuse-matrix", action="store_true", help="复用输出目录已有特征矩阵，仅运行 LOSO；不读取原始 npz")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    current = pd.read_csv(args.current, dtype={"subject": str})
    current["subject"] = current.subject.str.zfill(3)
    selected = {s.zfill(3) for s in args.subjects} if args.subjects else None
    matrix_path = args.output / "m1_q0_probe_matrix.csv"
    audit_path = args.output / "feature_extraction_audit.json"
    if args.reuse_matrix:
        if selected is not None:
            raise ValueError("--reuse-matrix 不能与 --subjects 同时使用")
        if not matrix_path.exists() or not audit_path.exists():
            raise FileNotFoundError("--reuse-matrix 需要同一输出目录中已有特征矩阵和审计文件")
        matrix = pd.read_csv(matrix_path, dtype={"subject": str})
        matrix["subject"] = matrix.subject.str.zfill(3)
        if "prior_n_err" not in matrix.columns:
            values: list[float] = []
            for _, row in matrix.iterrows():
                values.append(prior_error_by_probe(args.full_root, row.subject).get(int(row.probe_id), np.nan))
            matrix["prior_n_err"] = values
            matrix.to_csv(matrix_path, index=False, encoding="utf-8-sig")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["matrix_reused_for_loso"] = True
    else:
        matrix, audit = build_raw_matrix(current, args.data_root, args.full_root, selected, {s.zfill(3) for s in args.diagnostic_subjects}, args.output)
        matrix.to_csv(matrix_path, index=False, encoding="utf-8-sig")
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.extract_only:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return
    if selected is not None:
        raise ValueError("代表性被试诊断请使用 --extract-only；完整 LOSO 必须不限制 --subjects。")
    if matrix.empty or matrix.subject.nunique() < 3:
        raise ValueError("特征矩阵不足以完成 LOSO")
    results: list[dict] = []
    all_predictions: dict[str, pd.DataFrame] = {}
    for target in ("nonfocus_vs_focus", "mind_wandering_vs_focus"):
        for name, features in FEATURE_SETS.items():
            metrics, pred = evaluate_one(matrix, features, target, args.bootstrap, SEED)
            metrics["feature_set"] = name
            results.append(metrics)
            pred["target"] = target
            pred["feature_set"] = name
            all_predictions[f"{target}_{name}"] = pred
            print(f"LOSO: {target}, {name}, AUC={metrics['roc_auc']:.3f}", flush=True)
    prediction_out = pd.concat(all_predictions.values(), ignore_index=True)
    prediction_out.to_csv(args.output / "loso_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(results).to_csv(args.output / "loso_results.csv", index=False, encoding="utf-8-sig")
    deltas: list[dict] = []
    for target in ("nonfocus_vs_focus", "mind_wandering_vs_focus"):
        by_model = {name: all_predictions[f"{target}_{name}"] for name in FEATURE_SETS}
        deltas.extend(bootstrap_deltas(by_model, target, args.bootstrap, SEED))
    pd.DataFrame(deltas).to_csv(args.output / "incremental_deltas.csv", index=False, encoding="utf-8-sig")
    summary = {
        "analysis_status": "exploratory_raw_mmwave_incremental_validation",
        "validation": "LOSO; train-fold-only median imputation and standardization; fixed untuned L2 logistic regression; subject bootstrap CIs",
        "input_sha256": {str(args.current): sha256(args.current)},
        "feature_status": {"M1": "raw signal descriptors, not validated physiology", "M2": "HR/BR plus experimental HRV; not ECG-validated", "Q0": "label-free signal-quality descriptors"},
        "audit": audit,
        "feature_sets": FEATURE_SETS,
        "results": results,
        "incremental_deltas": deltas,
    }
    (args.output / "m1_q0_loso_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(args.output, audit, results, deltas, args.current)
    print(json.dumps({"audit": audit, "n_results": len(results), "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
