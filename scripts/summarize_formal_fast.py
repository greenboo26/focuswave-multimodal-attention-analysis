"""Summarize the six-subject formal mmWave probe analysis and make figures."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import mannwhitneyu


ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\Formal_mmwave_FAST")
data = json.loads((ROOT / "focus_discrimination.json").read_text(encoding="utf-8"))
rows = [w for s in data["subjects"] for w in s["windows"]]
labels = {int(k): v["label"] for k, v in data["summary"]["rmssd_by_attention"].items()}
plot_labels = {1: "Fully focused", 2: "TRI", 3: "Mind wandering", 4: "Blank mind"}
groups = {k: [float(w["rmssd_ms"]) for w in rows if w["attention"] == k] for k in labels}
hr_groups = {k: [float(w["hr_med_bpm"]) for w in rows if w["attention"] == k] for k in labels}

f, m = groups[1], groups[3]
u, p = mannwhitneyu(f, m, alternative="two-sided")
sp = np.sqrt(((len(f)-1)*np.var(f, ddof=1) + (len(m)-1)*np.var(m, ddof=1)) / (len(f)+len(m)-2))

summary = {
    "n_subjects": len(data["subjects"]),
    "n_windows": len(rows),
    "groups": {str(k): {"label": labels[k], "n": len(groups[k]),
                         "rmssd_mean_ms": round(float(np.mean(groups[k])), 3),
                         "rmssd_median_ms": round(float(np.median(groups[k])), 3),
                         "hr_mean_bpm": round(float(np.mean(hr_groups[k])), 3),
                         "hr_median_bpm": round(float(np.median(hr_groups[k])), 3)}
                for k in labels},
    "focus_vs_mind_wandering": {"u": float(u), "p": float(p),
                                "cohens_d": float((np.mean(m)-np.mean(f))/sp)},
    "caveat": "pooled probe-level comparison; only three subjects contain mind-wandering probes",
}
(ROOT / "formal_behavior_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

plt.figure(figsize=(8, 5))
plt.boxplot([groups[k] for k in labels], tick_labels=[plot_labels[k] for k in labels], showfliers=False)
plt.ylabel("mmWave RMSSD (ms)")
plt.title("Formal experiment: behavior probe vs mmWave RMSSD")
plt.grid(axis="y", alpha=.25)
plt.tight_layout()
plt.savefig(ROOT / "formal_rmssd_by_attention.png", dpi=180)
plt.close()

plt.figure(figsize=(8, 5))
plt.boxplot([hr_groups[k] for k in labels], tick_labels=[plot_labels[k] for k in labels], showfliers=False)
plt.ylabel("mmWave median heart rate (bpm)")
plt.title("Formal experiment: behavior probe vs mmWave heart rate")
plt.grid(axis="y", alpha=.25)
plt.tight_layout()
plt.savefig(ROOT / "formal_hr_by_attention.png", dpi=180)
plt.close()

print(json.dumps(summary, ensure_ascii=False, indent=2))
