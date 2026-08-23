"""Evaluate the conservative runtime prototype on aligned E:Data probe windows."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from mmwave_focus_system import MODEL_DEFAULT, add_attention_score, extract_window


ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"
CSV_PATH = OUT / "focus_discrimination.csv"
JSON_PATH = OUT / "focus_discrimination.json"


def median_session_hr(npz_path: Path) -> float:
    d = np.load(npz_path, allow_pickle=True)
    x = np.asarray(d.get("hr_course_fused_bpm", []), float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else 80.0


def main() -> None:
    aligned = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    subject_meta = {s["subject"]: s for s in aligned["subjects"] if "windows" in s}
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    out_rows = []
    cache = {}
    for r in rows:
        sub = r["subject"]
        npz = OUT / f"sub-{sub}_" / f"sub-{sub}_ses-SART_mmwave_vital_signs.npz"
        if not npz.exists() or sub not in subject_meta:
            continue
        if sub not in cache:
            cache[sub] = median_session_hr(npz)
        baseline = subject_meta[sub].get("baseline_rmssd_ms") or 300.0
        feature = extract_window(
            npz, float(r["onset_rel_s"]), baseline_rmssd_ms=float(baseline),
            allow_experimental_hrv=True,
        )
        if feature["rmssd_raw_ms"] is not None and feature["heart_rate_bpm"] is not None:
            score = add_attention_score(feature, cache[sub], float(baseline), MODEL_DEFAULT)
        else:
            score = {"research_focus_probability": None, "research_decision": "indeterminate"}
        out_rows.append({
            "subject": sub, "onset_rel_s": float(r["onset_rel_s"]),
            "attention": int(r["attention"]), "attention_label": r["attention_label"],
            "quality": feature["quality"], "quality_flags": ";".join(feature["quality_flags"]),
            "heart_rate_bpm": feature["heart_rate_bpm"], "rmssd_raw_ms": feature["rmssd_raw_ms"],
            "ibi_valid_ratio": feature["ibi_valid_ratio"], "n_peaks": feature["n_peaks"],
            "research_focus_probability": score.get("research_focus_probability"),
            "research_decision": score.get("research_decision", "indeterminate"),
        })

    comparable = [r for r in out_rows if r["research_decision"] != "indeterminate"]
    # The runtime score uses focused/nonfocused; TRI, mind-wandering and blank are nonfocused.
    y = [int(r["attention"] == 1) for r in comparable]
    pred = [int(r["research_decision"] == "research_focused") for r in comparable]
    cm = [[0, 0], [0, 0]]
    for a, b in zip(y, pred):
        cm[a][b] += 1
    tnr = cm[0][0] / sum(cm[0]) if sum(cm[0]) else None
    tpr = cm[1][1] / sum(cm[1]) if sum(cm[1]) else None
    summary = {
        "n_input_windows": len(rows), "n_evaluated_windows": len(out_rows),
        "n_subjects": len({r["subject"] for r in out_rows}),
        "quality_counts": dict(Counter(r["quality"] for r in out_rows)),
        "decision_counts": dict(Counter(r["research_decision"] for r in out_rows)),
        "indeterminate_rate": sum(r["research_decision"] == "indeterminate" for r in out_rows) / len(out_rows) if out_rows else None,
        "classified_windows": len(comparable), "confusion_matrix_rows_true_0_1_cols_pred_0_1": cm,
        "classified_balanced_accuracy": ((tnr + tpr) / 2) if tnr is not None and tpr is not None else None,
        "warning": "The model was trained on the small formal set and this is an audit of runtime behavior, not deployment validation.",
    }
    (OUT / "runtime_focus_system_eval.json").write_text(json.dumps({"summary": summary, "rows": out_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "runtime_focus_system_eval.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0]) if out_rows else ["subject"])
        writer.writeheader(); writer.writerows(out_rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
