"""Audit attention-label coverage for personalized calibration and testing."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def counts(rows):
    c = Counter(int(r["attention"]) for r in rows)
    return {str(k): int(c.get(k, 0)) for k in (1, 2, 3, 4)}


def main():
    rows = list(csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
    by = defaultdict(list)
    for r in rows: by[r["subject"]].append(r)
    table = []
    for s, rr in sorted(by.items()):
        cut = len(rr) // 2
        first, last = rr[:cut], rr[cut:]
        table.append({"subject": s, "n_total": len(rr), "total": counts(rr),
                      "calibration_first_half": counts(first), "test_second_half": counts(last),
                      "both_classes_in_calibration": len({r["attention"] == "1" for r in first}) > 1,
                      "focus_and_mw_in_calibration": {"1", "3"}.issubset({r["attention"] for r in first}),
                      "both_classes_in_test": len({r["attention"] == "1" for r in last}) > 1,
                      "focus_and_mw_in_test": {"1", "3"}.issubset({r["attention"] for r in last})})
    summary = {
        "n_subjects": len(table), "n_windows": len(rows),
        "total_label_counts": counts(rows),
        "eligible_for_focus_vs_all_temporal_calibration": sum(x["both_classes_in_calibration"] for x in table),
        "eligible_for_focus_vs_mw_temporal_calibration": sum(x["focus_and_mw_in_calibration"] for x in table),
        "eligible_for_focus_vs_all_temporal_test": sum(x["both_classes_in_test"] for x in table),
        "eligible_for_focus_vs_mw_temporal_test": sum(x["focus_and_mw_in_test"] for x in table),
        "recommendation": "Prioritize repeated labeled mind-wandering probes in both the early calibration and later test segments; total N alone is insufficient.",
    }
    out = {"summary": summary, "subjects": table}
    (OUT / "label_coverage_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "label_coverage_audit.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["subject", "n_total", "both_classes_in_calibration", "focus_and_mw_in_calibration", "both_classes_in_test", "focus_and_mw_in_test"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows([{k: r[k] for k in fields} for r in table])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
