"""Run the conservative mmWave attention prototype on new NPZ records."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import numpy as np

from mmwave_focus_system import MODEL_DEFAULT, add_attention_score, extract_window


def peak_seconds(d):
    t = np.asarray(d["t"], float)
    p = np.asarray(d.get("heart_peaks", []), float).ravel()
    if len(p) and np.nanmax(p) > np.nanmax(t) + 1:
        p = t[np.clip(p.astype(int), 0, len(t) - 1)]
    return p[np.isfinite(p)]


def baseline_rmssd(p, baseline_s):
    p = p[p <= baseline_s]
    ibi = np.diff(p)
    ibi = ibi[(ibi >= .30) & (ibi <= 2.0)]
    return float(np.sqrt(np.mean(np.diff(ibi) ** 2)) * 1000) if len(ibi) >= 3 else 300.0


def run_one(path, step_s, window_s, model_path, behavior_windows=None):
    d = np.load(path, allow_pickle=True)
    t = np.asarray(d["t"], float)
    p = peak_seconds(d)
    hc = np.asarray(d.get("hr_course_fused_bpm", []), float)
    hc = hc[np.isfinite(hc)]
    session_hr = float(np.median(hc)) if len(hc) else 80.0
    base = baseline_rmssd(p, 180.0)
    rows = []
    if behavior_windows is None:
        ends = np.arange(180.0 + window_s, float(t[-1]) + 1e-9, step_s).tolist()
        metadata = {}
    else:
        ends = [float(r["onset_rel_s"]) for r in behavior_windows]
        metadata = {float(r["onset_rel_s"]): r for r in behavior_windows}
    for end in ends:
        f = extract_window(path, end, window_s=window_s, baseline_rmssd_ms=base, allow_experimental_hrv=True)
        if f["rmssd_raw_ms"] is not None and f["heart_rate_bpm"] is not None:
            s = add_attention_score(f, session_hr, base, model_path)
        else:
            s = {"research_focus_probability": None, "research_decision": "indeterminate"}
        extra = metadata.get(float(end), {})
        rows.append({"record": path.stem, **{k: v for k, v in extra.items() if k not in {"record", "onset_rel_s"}}, **f, **s})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="one NPZ or a directory containing processed vital-sign NPZ files")
    ap.add_argument("output", type=Path)
    ap.add_argument("--windows-csv", type=Path, help="behavior-gated windows CSV; requires subject or record and onset_rel_s")
    ap.add_argument("--step-s", type=float, default=30.0)
    ap.add_argument("--window-s", type=float, default=60.0)
    ap.add_argument("--model", type=Path, default=MODEL_DEFAULT)
    ap.add_argument("--allow-ungated-timeline", action="store_true", help="diagnostic only: allow full-timeline sliding windows without behavior timestamps")
    args = ap.parse_args()
    if args.windows_csv is None and not args.allow_ungated_timeline:
        ap.error("behavior time gating is required; provide --windows-csv, or explicitly use --allow-ungated-timeline for diagnostic-only runs")
    if args.input.is_file():
        files = [args.input]
        duplicate_subjects = 0
    else:
        candidates = sorted(args.input.rglob("*_vital_signs.npz"))
        # A processed subject may also contain an internal _selection_60s copy.
        # The runtime must select one canonical full-session NPZ per subject, or
        # behavior windows would be scored twice.
        grouped = {}
        for p in candidates:
            match = re.search(r"sub-(\d{3})", p.stem)
            key = match.group(1) if match else p.stem
            grouped.setdefault(key, []).append(p)
        duplicate_subjects = sum(len(v) > 1 for v in grouped.values())
        files = []
        for key, paths in sorted(grouped.items()):
            files.append(sorted(paths, key=lambda p: ("_selection_60s" in str(p), len(p.parts), str(p)))[0])
    behavior_map = None
    if args.windows_csv:
        with args.windows_csv.open(encoding="utf-8-sig", newline="") as f:
            behavior_rows = list(csv.DictReader(f))
        if not behavior_rows or "onset_rel_s" not in behavior_rows[0]:
            ap.error("--windows-csv must contain onset_rel_s")
        behavior_map = {}
        for r in behavior_rows:
            key = str(r.get("subject") or r.get("record") or "").replace("sub-", "").replace("_", "").zfill(3)
            behavior_map.setdefault(key, []).append(r)
    rows = []
    for p in files:
        match = re.search(r"sub-(\d{3})", p.stem)
        subject = match.group(1) if match else p.stem
        if behavior_map is not None:
            windows = behavior_map.get(subject, [])
            if not windows:
                continue
        else:
            windows = None
        rows.extend(run_one(p, args.step_s, args.window_s, args.model, windows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps({"n_records": len(files), "n_windows": len(rows), "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = list(rows[0]) if rows else ["record"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(json.dumps({"n_records": len(files), "duplicate_subject_groups_collapsed": duplicate_subjects, "n_windows": len(rows), "behavior_time_gated": args.windows_csv is not None, "json": str(args.output.with_suffix('.json'))}, ensure_ascii=False))


if __name__ == "__main__": main()
