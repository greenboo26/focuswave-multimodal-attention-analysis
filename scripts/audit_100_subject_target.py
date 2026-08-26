"""Audit whether the current cohort meets the 100-subject collection gates."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"
DATA = Path(r"E:\Data")


def labels(rows):
    return Counter(str(r.get("attention", "")) for r in rows)


def core_ok(rows):
    """At least three fully-focused and three mind-wandering probes."""
    c = labels(rows)
    return c["1"] >= 3 and c["3"] >= 3


def has_both_core_labels(rows):
    c = labels(rows)
    return c["1"] >= 1 and c["3"] >= 1


def main():
    focus_rows = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
    runtime_rows = list(csv.DictReader((OUT / "runtime_focus_system_eval.csv").open(encoding="utf-8-sig")))
    by_focus = defaultdict(list)
    by_runtime = defaultdict(list)
    for row in focus_rows:
        by_focus[row["subject"]].append(row)
    for row in runtime_rows:
        by_runtime[row["subject"]].append(row)

    source_dirs = {d.name.replace("sub-", "").rstrip("_"): d for d in DATA.glob("sub-*_ ".replace(" ", ""))}
    source_ids = set(source_dirs)
    rows = []
    for subject in sorted(source_ids | set(by_focus)):
        probes = sorted(by_focus.get(subject, []), key=lambda x: float(x["onset_rel_s"]))
        mid = len(probes) // 2
        first, last = probes[:mid], probes[mid:]
        quality = by_runtime.get(subject, [])
        usable = sum(r.get("quality") == "usable_for_hr" for r in quality)
        total_labels = labels(probes)
        source_dir = source_dirs.get(subject)
        has_mmwave = bool(source_dir and any((source_dir / "mmwave").rglob("*")) if source_dir and (source_dir / "mmwave").exists() else False)
        has_rgb = bool(source_dir and any((source_dir / "rgb").rglob("*")) if source_dir and (source_dir / "rgb").exists() else False)
        has_nir = bool(source_dir and any((source_dir / "nir").rglob("*")) if source_dir and (source_dir / "nir").exists() else False)
        rows.append({
            "subject": subject,
            "source_directory": subject in source_ids,
            "has_mmwave": has_mmwave,
            "has_rgb": has_rgb,
            "has_nir": has_nir,
            "missing_required_modalities": [m for m, ok in (("mmwave", has_mmwave), ("rgb", has_rgb), ("nir", has_nir)) if not ok],
            "processed": bool(probes),
            "n_probes": len(probes),
            "usable_for_hr_windows": usable,
            "label_1_focus": total_labels["1"],
            "label_2_tri": total_labels["2"],
            "label_3_task_unrelated_thought": total_labels["3"],
            "label_4_mind_blank": total_labels["4"],
            "calibration_core_ok": core_ok(first),
            "test_core_ok": core_ok(last),
            "calibration_has_focus_and_mw": has_both_core_labels(first),
            "test_has_focus_and_mw": has_both_core_labels(last),
            "subject_ready_for_personalized_validation": core_ok(first) and core_ok(last),
        })

    ready = [r for r in rows if r["subject_ready_for_personalized_validation"]]
    summary = {
        "target_subjects": 100,
        "source_subjects": len(source_ids),
        "processed_subjects": sum(r["processed"] for r in rows),
        "processed_gap_to_target": max(0, 100 - sum(r["processed"] for r in rows)),
        "subjects_ready_for_personalized_validation": len(ready),
        "ready_gap_to_target": max(0, 100 - len(ready)),
        "subjects_with_both_core_labels_in_calibration": sum(r["calibration_has_focus_and_mw"] for r in rows),
        "subjects_with_both_core_labels_in_test": sum(r["test_has_focus_and_mw"] for r in rows),
        "label_coverage_rule": "at least 3 focus and 3 mind-wandering probes in both first and second half",
        "recommendation": "Collect missing subjects and prioritize mind-wandering probes in both temporal halves; do not use directory count alone as the final N.",
    }
    result = {"summary": summary, "subjects": rows}
    (OUT / "target_100_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "target_100_audit.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = list(rows[0]) if rows else ["subject"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
