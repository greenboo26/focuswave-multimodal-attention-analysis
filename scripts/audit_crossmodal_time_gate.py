"""Audit RGB/NIR/mmWave timestamp inclusion under the behavior-time gate."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DATA = Path(r"E:\Data")
OUT = ROOT / "output" / "E_Data_FAST"


def events(subject):
    p = DATA / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    if not p.exists(): return [], []
    rows = list(csv.DictReader(p.open(encoding="utf-8-sig", newline="")))
    starts, stops, modality = {}, {}, {"rgb": [[], []], "nir": [[], []], "mmwave": [[], []]}
    for r in rows:
        try: ms = int(float(r.get("unix_ms", "")))
        except Exception: continue
        e, d = r.get("event", ""), r.get("detail", "")
        if e == "block_start": starts[d] = ms
        elif e == "block_stop": stops[d] = ms
        for m in modality:
            if e == f"{m}_start": modality[m][0].append(ms)
            if e == f"{m}_stop": modality[m][1].append(ms)
    intervals = [(s, stops[d]) for d, s in starts.items() if d in stops and stops[d] > s]
    if not intervals:
        sart_s = next((int(float(r["unix_ms"])) for r in rows if r.get("event") == "sart_start"), None)
        sart_e = next((int(float(r["unix_ms"])) for r in rows if r.get("event") == "sart_stop"), None)
        intervals = [(sart_s, sart_e)] if sart_s and sart_e and sart_e > sart_s else []
    return intervals, modality


def ts_values(path):
    vals = []
    if not path.exists(): return np.array([])
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2: continue
            try: vals.append(float(row[1]))
            except (ValueError, TypeError): pass
    return np.asarray(vals, float)


def main():
    records = []
    for d in sorted(DATA.glob("sub-*_")):
        subject = d.name.replace("sub-", "").rstrip("_")
        intervals, modality = events(subject)
        if not intervals: continue
        for m in ("rgb", "nir", "mmwave"):
            p = d / m / f"sub-{subject}_{m}_timestamps.csv"
            t = ts_values(p)
            inside = np.zeros(len(t), bool)
            for a, b in intervals: inside |= (t >= a) & (t <= b)
            mod_start = max(modality[m][0]) if modality[m][0] else None
            mod_stop = min(modality[m][1]) if modality[m][1] else None
            records.append({"subject": subject, "modality": m, "timestamp_file": p.exists(), "n_frames": int(len(t)),
                            "n_inside_sart_blocks": int(inside.sum()), "n_outside_sart_blocks": int((~inside).sum()),
                            "fraction_inside_sart_blocks": float(inside.mean()) if len(t) else None,
                            "record_start_ms": float(t.min()) if len(t) else None, "record_stop_ms": float(t.max()) if len(t) else None,
                            "timeline_modality_start_ms": mod_start, "timeline_modality_stop_ms": mod_stop})
    with (OUT / "crossmodal_time_gate.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = list(records[0]) if records else ["subject", "modality"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(records)
    summary = {"n_subjects": len(set(r["subject"] for r in records)), "records": len(records), "by_modality": {}}
    for m in ("rgb", "nir", "mmwave"):
        rr = [r for r in records if r["modality"] == m]
        summary["by_modality"][m] = {"n_subjects": len(rr), "frames": int(sum(r["n_frames"] for r in rr)), "inside_sart_frames": int(sum(r["n_inside_sart_blocks"] for r in rr)), "outside_sart_frames": int(sum(r["n_outside_sart_blocks"] for r in rr))}
    summary["rule"] = "Only frames/windows fully inside behavior-defined SART block intervals are eligible for cross-modal analysis; pre/post and practice/rest frames are excluded."
    (OUT / "crossmodal_time_gate.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
