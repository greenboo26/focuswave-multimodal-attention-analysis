# -*- coding: utf-8 -*-
"""解析 BIOPAC .acq 参考信号，并与毫米波/行为时间轴对齐。

输出：
1. ECG R 峰、呼吸峰、HR、BR、SDNN、RMSSD 的窗口级参考指标；
2. 与 SART 探针标签对齐的 reference_probes.csv；
3. 质量摘要和参考信号示例图。

注意：BIOPAC 文件的首个事件标记作为采集起点，绝对时间用行为
master_timeline.csv 的 mmwave_start 校正，不能假设毫米波与 BIOPAC 同时启动。
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

import bioread
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, sosfiltfilt

def _resolve_acq_root() -> Path:
    """Resolve the synchronized ECG/RSP/mmWave root across the two path spellings."""
    candidates = []
    configured = os.environ.get("ACQ_SOURCE_ROOT")
    if configured:
        candidates.append(Path(configured))
    candidates.extend([
        Path(r"D:\acq_mmwave_results"),
        Path(r"D:\acq\_mmwave\_results"),
    ])
    return next((p for p in candidates if p.exists()), candidates[0])


DATA_ROOT = _resolve_acq_root()
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821")
WINDOW_S = 60.0
VALIDATION_WINDOW_S = 30.0


def _bandpass(x: np.ndarray, fs: float, lo: float, hi: float, order: int = 4) -> np.ndarray:
    sos = butter(order, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, x.astype(float))


def _acq_start_ms(datafile) -> int | None:
    t = datafile.earliest_marker_created_at
    return int(t.timestamp() * 1000) if t is not None else None


def _read_csv_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _mmwave_start_ms(sub_dir: Path) -> int | None:
    mt = sub_dir / "beh" / "master_timeline.csv"
    if mt.exists():
        for r in _read_csv_rows(mt):
            if (r.get("event") or "").startswith("mmwave_start"):
                return int(float(r["unix_ms"]))
    ev = sub_dir / "cal" / "events.csv"
    if ev.exists():
        for r in _read_csv_rows(ev):
            if r.get("event") == "calibration_start":
                return int(float(r["unix_ms"]))
    ts_files = sorted((sub_dir / "mmwave").glob("*_timestamps.csv"))
    if ts_files:
        with open(ts_files[0], encoding="utf-8-sig", newline="") as fh:
            rd = csv.reader(fh); next(rd, None); row = next(rd, None)
            if row and len(row) >= 3:
                return int(float(row[2]))
    return None


def _find_acq(sub_dir: Path) -> Path | None:
    return next(iter(sorted(sub_dir.glob("*.acq"))), None)


def _channel(datafile, patterns: tuple[str, ...]):
    for c in datafile.channels:
        name = c.name.lower()
        if any(p.lower() in name for p in patterns):
            return c
    return None


def _peaks_and_metrics(ecg: np.ndarray, rsp: np.ndarray | None, fs: float, start_s: float, end_s: float) -> dict:
    lo = max(0, int(start_s * fs)); hi = min(len(ecg), int(end_s * fs))
    if hi - lo < int(10 * fs):
        return {"valid": False, "reason": "short_window"}
    ecg_w = ecg[lo:hi]
    ecg_bp = _bandpass(ecg_w, fs, 5.0, min(35.0, fs / 2 - 1))
    robust = np.median(np.abs(ecg_bp - np.median(ecg_bp))) * 1.4826
    # 成人静息/任务状态的参考 HR 通常低于 130 bpm；较长最小峰距可避免
    # 把 T 波或高频伪峰重复计作 R 峰。后续仍以 ECG 原波形人工抽查为准。
    prominence = max(float(robust) * 1.2, float(np.std(ecg_bp)) * 0.25, 1e-6)
    r_idx, props = find_peaks(ecg_bp, distance=int(0.45 * fs), prominence=prominence)
    r_t = (r_idx + lo) / fs
    ibi = np.diff(r_t)
    good = np.isfinite(ibi) & (ibi >= 0.30) & (ibi <= 2.00)
    ibi = ibi[good]
    hr = 60.0 / np.median(ibi) if len(ibi) >= 3 else np.nan
    rmssd = np.sqrt(np.mean(np.diff(ibi) ** 2)) * 1000 if len(ibi) >= 3 else np.nan
    sdnn = np.std(ibi, ddof=1) * 1000 if len(ibi) >= 3 else np.nan
    out = {"valid": bool(len(ibi) >= 3), "n_rpeaks": int(len(r_idx)), "n_ibi": int(len(ibi)),
           "hr_ecg_bpm": float(hr) if np.isfinite(hr) else None,
           "rmssd_ecg_ms": float(rmssd) if np.isfinite(rmssd) else None,
           "sdnn_ecg_ms": float(sdnn) if np.isfinite(sdnn) else None,
           "ecg_prominence": float(prominence)}
    if rsp is not None:
        rsp_w = rsp[lo:hi]
        rsp_bp = _bandpass(rsp_w, fs, 0.08, min(0.7, fs / 2 - 1))
        rprom = max(float(np.std(rsp_bp)) * 0.15, 1e-9)
        p_idx, _ = find_peaks(rsp_bp, distance=int(1.5 * fs), prominence=rprom)
        p_t = (p_idx + lo) / fs
        p_ibi = np.diff(p_t)
        p_ibi = p_ibi[(p_ibi >= 2.0) & (p_ibi <= 10.0)]
        out["n_breath_peaks"] = int(len(p_idx))
        out["br_rsp_bpm"] = float(60.0 / np.median(p_ibi)) if len(p_ibi) >= 2 else None
    return out


def _behavior_valid_span_ms(sub_dir: Path) -> tuple[int | None, int | None]:
    """Return the SART-only analysis span from the behavior timeline.

    The probe window is defined by behavior timestamps, not by the length of
    the physiological file.  This prevents baseline, instructions, practice,
    abort/cleanup and other pre/post records from entering the reference set.
    """
    timeline = sub_dir / "beh" / "master_timeline.csv"
    events = sub_dir / "beh" / "events.csv"
    rows = _read_csv_rows(timeline if timeline.exists() else events) if (timeline.exists() or events.exists()) else []
    sart_start = None
    end_candidates = []
    block_starts = []
    block_ends = []
    for r in rows:
        event = (r.get("event") or "").strip()
        try:
            ts = int(float(r.get("unix_ms", 0) or 0))
        except Exception:
            continue
        if event == "sart_start":
            sart_start = ts
        if event == "segment_start" and (r.get("segment") or "").lower().startswith("block"):
            block_starts.append(ts)
        if event in {"segment_end", "block_stop"} and (r.get("segment") or r.get("detail") or "").lower().startswith("block"):
            block_ends.append(ts)
        if event in {"block_stop", "experiment_abort", "mmwave_stop", "experiment_stop"}:
            if sart_start is not None and ts >= sart_start:
                end_candidates.append(ts)
    if sart_start is None and block_starts:
        sart_start = min(block_starts)
    # Use the end of the last valid block.  Taking the first block end would
    # silently discard later probes; taking experiment_stop could include
    # post-task cleanup after an abort.
    if block_ends:
        end_ms = max(block_ends)
    else:
        end_ms = max(end_candidates) if end_candidates else None
    return sart_start, end_ms


def _probe_rows(sub_dir: Path, acq_start_ms: int) -> list[dict]:
    out = []
    valid_start_ms, valid_end_ms = _behavior_valid_span_ms(sub_dir)
    for f in sorted((sub_dir / "beh").glob("*_beh.csv")):
        for r in _read_csv_rows(f):
            try:
                if int(float(r.get("is_probe", 0) or 0)) != 1:
                    continue
                onset_ms = int(float(r.get("probe_onset_time", 0) or 0))
                attention = int(float(r.get("probe_response", 0) or 0))
            except Exception:
                continue
            if onset_ms <= 0 or attention not in (1, 2, 3, 4):
                continue
            # Strict behavior gate: only probes inside the actual SART span
            # are eligible.  Practice and post-abort records are excluded.
            if valid_start_ms is not None and onset_ms < valid_start_ms:
                continue
            if valid_end_ms is not None and onset_ms > valid_end_ms:
                continue
            out.append({"onset_ms": onset_ms, "attention": attention,
                        "vigilance": int(float(r.get("probe_vigilance", 0) or 0)),
                        "onset_acq_s": (onset_ms - acq_start_ms) / 1000.0,
                        "behavior_valid_start_ms": valid_start_ms,
                        "behavior_valid_end_ms": valid_end_ms})
    return out


def analyze_subject(sub_dir: Path) -> dict:
    acq = _find_acq(sub_dir)
    if acq is None:
        return {"subject": sub_dir.name, "error": "no_acq"}
    df = bioread.read_file(str(acq))
    fs = float(df.samples_per_second)
    ec = _channel(df, ("ecg",))
    rsp = _channel(df, ("rsp", "resp", "respiration"))
    if ec is None:
        return {"subject": sub_dir.name, "error": "no_ecg", "channels": [c.name for c in df.channels]}
    ecg = np.asarray(ec.data, dtype=float)
    resp = np.asarray(rsp.data, dtype=float) if rsp is not None else None
    acq_start = _acq_start_ms(df)
    mm_start = _mmwave_start_ms(sub_dir)
    result = {"subject": sub_dir.name, "acq_file": str(acq), "fs_hz": fs,
              "duration_s": len(ecg) / fs, "ecg_channel": ec.name,
              "resp_channel": rsp.name if rsp else None, "acq_start_ms": acq_start,
              "mmwave_start_ms": mm_start, "offset_mmwave_from_acq_s":
              (mm_start - acq_start) / 1000 if mm_start and acq_start else None,
              "probes": []}
    if acq_start and (sub_dir / "beh").exists():
        for p in _probe_rows(sub_dir, acq_start):
            if p["onset_acq_s"] < WINDOW_S:
                continue
            m = _peaks_and_metrics(ecg, resp, fs, p["onset_acq_s"] - WINDOW_S, p["onset_acq_s"])
            m30 = _peaks_and_metrics(ecg, resp, fs,
                                     p["onset_acq_s"] - VALIDATION_WINDOW_S,
                                     p["onset_acq_s"])
            p.update(m)
            p.update({f"{k}_30s": v for k, v in m30.items()})
            result["probes"].append(p)
    # Calibration / no-probe records: use non-overlapping 60 s windows.
    if not result["probes"]:
        starts = np.arange(0, max(0, len(ecg) / fs - WINDOW_S), WINDOW_S)
        result["windows"] = [{"start_s": float(s), "end_s": float(s + WINDOW_S),
                               **_peaks_and_metrics(ecg, resp, fs, float(s), float(s + WINDOW_S))}
                              for s in starts]
    return result


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = [analyze_subject(p) for p in sorted(DATA_ROOT.glob("sub-*")) if p.is_dir()]
    (OUT_ROOT / "reference_metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(OUT_ROOT / "reference_probes.csv", "w", newline="", encoding="utf-8-sig") as fh:
        fields = ["subject", "onset_ms", "onset_acq_s", "attention", "vigilance", "hr_ecg_bpm", "br_rsp_bpm", "rmssd_ecg_ms", "sdnn_ecg_ms", "n_rpeaks", "n_ibi", "valid"]
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore"); w.writeheader()
        for s in rows:
            for p in s.get("probes", []):
                w.writerow({"subject": s["subject"], **p})
    summary = []
    for s in rows:
        vals = s.get("probes", []) or s.get("windows", [])
        summary.append({"subject": s["subject"], "n_windows": len(vals),
                        "n_valid_hrv": sum(bool(x.get("valid")) for x in vals),
                        "median_hr_ecg_bpm": float(np.nanmedian([x["hr_ecg_bpm"] for x in vals if x.get("hr_ecg_bpm") is not None])) if any(x.get("hr_ecg_bpm") is not None for x in vals) else None,
                        "median_br_rsp_bpm": float(np.nanmedian([x["br_rsp_bpm"] for x in vals if x.get("br_rsp_bpm") is not None])) if any(x.get("br_rsp_bpm") is not None for x in vals) else None})
    (OUT_ROOT / "reference_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
