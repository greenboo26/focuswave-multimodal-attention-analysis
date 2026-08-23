"""Create the final E:Data quality/probe summary after batch extraction."""
from pathlib import Path
import csv
import json
import math
import statistics

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import mannwhitneyu


DATA_ROOT = Path(r"E:\Data")
OUT = Path(r"D:\Project\厚粲杯\08_算法\output\E_Data_FAST")

all_dirs = sorted(DATA_ROOT.glob("sub-*_"))
rows = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
rows = [r for r in rows if "error" not in r]
complete = {r["subject"] for r in rows}
all_subjects = {d.name.replace("sub-", "").rstrip("_") for d in all_dirs}
missing = sorted(all_subjects - complete)
raw_subjects = sorted(
    d.name.replace("sub-", "").rstrip("_")
    for d in all_dirs
    if any((d / "mmwave").glob("*.npz"))
)
no_mmwave_subjects = sorted(set(all_subjects) - set(raw_subjects))
nonempty_unprocessed = sorted(set(raw_subjects) - set(complete))

def finite_vals(key):
    return [float(r[key]) for r in rows if isinstance(r.get(key), (int, float)) and math.isfinite(float(r[key]))]

hr = finite_vals("hr_time_bpm")
br = finite_vals("br_time_bpm")
agreement = [abs(float(r["hr_time_bpm"]) - float(r["hr_freq_bpm"])) for r in rows]
quality_counts = {
    "hr_40_100": sum(40 <= x <= 100 for x in hr),
    "br_12_25": sum(12 <= x <= 25 for x in br),
    "br_outside_12_25": sum(x < 12 or x > 25 for x in br),
    "hr_time_frequency_gap_le_5": sum(x <= 5 for x in agreement),
    "exploratory_hrv_available": sum(r.get("RMSSD_ms") is not None for r in rows),
}

probe_rows = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
groups = {str(k): [float(r["rmssd_ms"]) for r in probe_rows if r["attention"] == str(k)] for k in range(1, 5)}
u, p = mannwhitneyu(groups["1"], groups["3"], alternative="two-sided")
sp = math.sqrt(((len(groups["1"])-1)*statistics.pvariance(groups["1"])
                + (len(groups["3"])-1)*statistics.pvariance(groups["3"]))
               / (len(groups["1"])+len(groups["3"])-2))
focus_d = (statistics.mean(groups["3"]) - statistics.mean(groups["1"])) / sp

lopo = json.loads((OUT / "focus_lopo.json").read_text(encoding="utf-8"))["analyses"]
summary = {
    "source_subject_directories": len(all_subjects),
    "complete_subjects": len(complete),
    "raw_mmwave_subjects": len(raw_subjects),
    "no_mmwave_subjects": len(no_mmwave_subjects),
    "no_mmwave_subjects_list": no_mmwave_subjects,
    "nonempty_unprocessed_or_failed_subjects": len(nonempty_unprocessed),
    "nonempty_unprocessed_or_failed": nonempty_unprocessed,
    "quality": {
        "hr_n": len(hr), "hr_median_bpm": statistics.median(hr), "hr_min_bpm": min(hr), "hr_max_bpm": max(hr),
        "br_n": len(br), "br_median_bpm": statistics.median(br), "br_min_bpm": min(br), "br_max_bpm": max(br),
        "hr_time_frequency_gap_median_bpm": statistics.median(agreement),
        **quality_counts,
    },
    "probe_windows": len(probe_rows),
    "probe_label_counts": {str(k): len(v) for k, v in groups.items()},
    "rmssd_by_attention": {str(k): {"n": len(v), "mean_ms": statistics.mean(v), "median_ms": statistics.median(v)}
                           for k, v in groups.items() if v},
    "focus_vs_mind_wandering_rmssd": {"u": float(u), "p": float(p), "cohens_d": float(focus_d)},
    "leave_one_subject_out": {
        k: {x: v[x] for x in ("n", "n_subjects", "auc", "balanced_accuracy")}
        for k, v in lopo.items() if v is not None
    },
    "interpretation": "HR is extractable in most complete records; BR and mmWave HRV require quality review and ECG calibration; focus classification remains exploratory and near chance.",
}
(OUT / "final_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

plt.figure(figsize=(9, 5))
plt.hist(hr, bins=12, alpha=.75, label="HR time estimate")
plt.hist(br, bins=12, alpha=.75, label="BR time estimate")
plt.xlabel("Rate (beats/min or breaths/min)")
plt.ylabel("Subjects")
plt.title("E:Data complete-subject rate distributions")
plt.legend()
plt.grid(alpha=.25)
plt.tight_layout()
plt.savefig(OUT / "final_hr_br_distribution.png", dpi=180)
plt.close()
print(json.dumps({"complete_subjects": len(complete), "missing": len(missing), "probes": len(probe_rows), "quality": quality_counts, "lopo": summary["leave_one_subject_out"]}, ensure_ascii=False))
