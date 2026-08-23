"""Inventory the three principal data layers without conflating evidence levels."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
E = Path(r"E:\Data")
FORMAL = Path(r"D:\正式实验")
def resolve_acq_root() -> Path:
    configured = os.environ.get("ACQ_SOURCE_ROOT")
    candidates = ([Path(configured)] if configured else []) + [
        Path(r"D:\acq_mmwave_results"),
        Path(r"D:\acq\_mmwave\_results"),
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


ACQ = resolve_acq_root()
OUT = ROOT / "output" / "E_Data_FAST"


def main():
    e_dirs = sorted(E.glob("sub-*_")); formal_dirs = sorted(FORMAL.glob("sub-*_")); acq_dirs = sorted(ACQ.glob("sub-*_"))
    e_processed = [d for d in OUT.glob("sub-*_" ) if list(d.glob("*_vital_signs.npz"))]
    focus_rows = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
    e_behavior = len(set(r["subject"] for r in focus_rows))
    acq_probe_ids = {r["subject"] for r in csv.DictReader((ROOT / "output" / "ACQ_reference_20260821" / "reference_probes.csv").open(encoding="utf-8-sig"))}
    normalize = lambda name: name.replace("sub-", "").rstrip("_")
    # Count only E_Data subjects that actually have behavior-gated rows; an
    # unprocessed source directory is not yet a behavior-ready participant.
    e_ids = {normalize(r["subject"]) for r in focus_rows}
    formal_ids = {normalize(d.name) for d in formal_dirs}
    acq_ids = {normalize(s) for s in acq_probe_ids}
    unique_ids = e_ids | formal_ids | acq_ids
    formal_probe_rows = len(list(csv.DictReader((ROOT / "output" / "Formal_mmwave_FAST" / "focus_discrimination.csv").open(encoding="utf-8-sig"))))
    result = {
        "layers": {
            "E_Data": {"source_directories": len(e_dirs), "processed_subjects": len(e_processed), "behavior_aligned_subjects": e_behavior, "probe_windows": len(focus_rows), "time_gated": True},
            "formal_experiment": {"source_directories": len(formal_dirs), "behavior_probe_rows": formal_probe_rows, "evidence": "mmWave plus behavior, no ECG/RSP"},
            "acq_reference": {"source_directories": len(acq_dirs), "behavior_aligned_reference_subjects": len(acq_ids), "evidence": "ECG/RSP/mmWave, paired behavior subset"},
        },
        "behavior_ready_unique_subjects_lower_bound": len(unique_ids),
        "remaining_to_100_lower_bound": max(0, 100 - len(unique_ids)),
        "unique_subject_ids_by_layer": {"E_Data": sorted(e_ids), "formal_experiment": sorted(formal_ids), "acq_reference": sorted(acq_ids)},
        "warning": "The count is de-duplicated by normalized subject ID, but layers have different protocols and evidence levels; do not pool them as one homogeneous training cohort without harmonization.",
    }
    (OUT / "source_inventory_final.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
