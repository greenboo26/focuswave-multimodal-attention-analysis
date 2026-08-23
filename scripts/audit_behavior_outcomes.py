"""Audit SART trial outcomes and align objective behavior to mmWave probes."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DATA = Path(r"E:\Data")
OUT = ROOT / "output" / "E_Data_FAST"


def as_float(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def timeline_start(subject):
    path = DATA / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    if not path.exists():
        return np.nan
    for row in read_csv(path):
        if row.get("event") == "mmwave_start":
            return as_float(row.get("unix_ms"))
    return np.nan


def metric_rows(trials):
    vals = {k: [as_float(r.get(k)) for r in trials] for k in ("correct", "commission", "omission", "rt", "is_no_go")}
    finite_rt = np.asarray(vals["rt"], float); finite_rt = finite_rt[np.isfinite(finite_rt)]
    no_go = np.asarray(vals["is_no_go"], float) == 1
    correct = np.asarray(vals["correct"], float)
    return {
        "n_trials": len(trials),
        "accuracy": float(np.nanmean(vals["correct"])) if trials else np.nan,
        "commission_rate": float(np.nanmean(vals["commission"])) if trials else np.nan,
        "omission_rate": float(np.nanmean(vals["omission"])) if trials else np.nan,
        "n_no_go": int(no_go.sum()),
        "no_go_accuracy": float(np.nanmean(correct[no_go])) if no_go.any() else np.nan,
        "rt_median_ms": float(np.median(finite_rt)) if finite_rt.size else np.nan,
        "rt_sd_ms": float(np.std(finite_rt, ddof=1)) if finite_rt.size > 1 else np.nan,
    }


def main():
    focus = read_csv(OUT / "focus_discrimination.csv")
    by_focus = defaultdict(list)
    for row in focus:
        by_focus[row["subject"]].append(row)
    subject_summary, probe_rows = [], []
    for subject in sorted(by_focus):
        beh_dir = DATA / f"sub-{subject}_" / "beh"
        files = sorted(beh_dir.glob(f"sub-{subject}_*_beh.csv"))
        all_rows = [r for f in files for r in read_csv(f)]
        trials = [r for r in all_rows if r.get("is_probe") != "1"]
        base = metric_rows(trials)
        base["subject"] = subject; base["n_behavior_files"] = len(files)
        subject_summary.append(base)
        start_ms = timeline_start(subject)
        probes = [r for r in all_rows if r.get("is_probe") == "1" and as_float(r.get("probe_onset_time")) == as_float(r.get("probe_onset_time"))]
        for p in probes:
            onset = as_float(p.get("probe_onset_time"))
            prior = [r for r in trials if np.isfinite(as_float(r.get("absolute_onset_time"))) and onset - 60000 <= as_float(r.get("absolute_onset_time")) < onset]
            m = metric_rows(prior)
            probe_rows.append({"subject": subject, "onset_rel_s": (onset - start_ms) / 1000.0 if np.isfinite(start_ms) else np.nan,
                               "attention": p.get("probe_response"), "vigilance": p.get("probe_vigilance"), **m})

    # 主分析已按 SART block 和多模态起止时间门控；行为效标必须使用同一窗口集合。
    gated = {(r["subject"], round(float(r["onset_rel_s"]), 1)) for r in focus}
    probe_rows = [r for r in probe_rows if (r["subject"], round(float(r["onset_rel_s"]), 1)) in gated]

    with (OUT / "behavior_subject_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["subject", "n_behavior_files", "n_trials", "accuracy", "commission_rate", "omission_rate", "n_no_go", "no_go_accuracy", "rt_median_ms", "rt_sd_ms"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows({k: r.get(k) for k in fields} for r in subject_summary)
    with (OUT / "behavior_probe_windows.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = list(probe_rows[0]) if probe_rows else ["subject", "onset_rel_s", "attention"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(probe_rows)

    stats = {"n_subjects": len(subject_summary), "n_trials": int(sum(r["n_trials"] for r in subject_summary)), "n_probe_windows": len(probe_rows), "by_attention": {}}
    for label in ("1", "2", "3", "4"):
        rr = [r for r in probe_rows if r["attention"] == label]
        stats["by_attention"][label] = {"n": len(rr), "accuracy_median": float(np.nanmedian([r["accuracy"] for r in rr])) if rr else None,
                                         "commission_median": float(np.nanmedian([r["commission_rate"] for r in rr])) if rr else None,
                                         "rt_median_ms": float(np.nanmedian([r["rt_median_ms"] for r in rr])) if rr else None}
    pairs = [(float(r["attention"]), r["accuracy"]) for r in probe_rows if r["attention"] in ("1", "2", "3", "4") and np.isfinite(r["accuracy"])]
    if len(pairs) >= 3:
        rho, p = spearmanr([x[0] for x in pairs], [x[1] for x in pairs])
        stats["probe_attention_vs_prior_accuracy_spearman"] = {"rho": float(rho), "p": float(p), "n": len(pairs)}
    stats["note"] = "Behavior outcomes are aligned as audit/criterion variables; they are not used as mmWave model inputs in the current system."
    (OUT / "behavior_outcome_audit.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
