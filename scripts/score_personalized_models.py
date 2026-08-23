"""Score behavior-time-gated windows with exported subject calibration models."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import balanced_accuracy_score, roc_auc_score

from personalized_temporal_runtime import load_rows


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path, required=True, help="behavior-gated feature CSV")
    ap.add_argument("--models", type=Path, required=True, help="directory from --model-dir")
    ap.add_argument("--mode", default="mmwave_rgb_nir_behavior",
                    choices=("mmwave", "mmwave_rgb_nir", "mmwave_behavior", "mmwave_rgb_nir_behavior"))
    ap.add_argument("--crossmodal", type=Path)
    ap.add_argument("--behavior", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    rows = load_rows(args.features, args.crossmodal, args.behavior)
    model_paths = sorted(args.models.glob(f"{args.mode}__sub-*.json"))
    models = {}
    for path in model_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        models[str(payload["subject"]).zfill(3)] = payload

    scored = []
    for row in rows:
        subject = str(row["subject"]).zfill(3)
        model = models.get(subject)
        base = {"subject": subject, "onset_rel_s": row["onset_rel_s"], "attention": row.get("attention"),
                "attention_label": row.get("attention_label"), "mode": args.mode}
        if model is None:
            base.update({"phase": "no_model", "probability": None, "decision": "indeterminate", "reason": "no_subject_calibration_model"})
            scored.append(base)
            continue
        try:
            x = np.asarray([float(row[f]) for f in model["features"]], float)
        except (KeyError, TypeError, ValueError):
            base.update({"phase": "unknown", "probability": None, "decision": "indeterminate", "reason": "missing_feature"})
            scored.append(base)
            continue
        quality_flags = []
        if "hr_time_freq_gap_bpm" in row and float(row["hr_time_freq_gap_bpm"]) > 10:
            quality_flags.append("heart_time_frequency_disagreement")
        if "hr_signal_usable_ratio" in row and float(row["hr_signal_usable_ratio"]) < 0.8:
            quality_flags.append("heart_signal_usable_ratio_low")
        if not np.all(np.isfinite(x)):
            quality_flags.append("nonfinite_feature")
        if quality_flags:
            base.update({"phase": "test" if model.get("test_start_s") is not None and float(row["onset_rel_s"]) >= model["test_start_s"] else "calibration", "probability": None, "decision": "indeterminate", "reason": ";".join(quality_flags)})
            scored.append(base)
            continue
        z = (x - np.asarray(model["mean"], float)) / np.maximum(np.asarray(model["scale"], float), 1e-9)
        probability = sigmoid(float(model["intercept"]) + float(np.dot(np.asarray(model["coef"], float), z)))
        decision = "research_focused" if probability >= 0.65 else "research_nonfocused" if probability <= 0.35 else "indeterminate"
        phase = "test" if model.get("test_start_s") is not None and float(row["onset_rel_s"]) >= model["test_start_s"] else "calibration"
        base.update({"phase": phase, "probability": probability, "decision": decision, "reason": "quality_pass"})
        scored.append(base)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    test_rows = [r for r in scored if r.get("phase") == "test" and r.get("probability") is not None and r.get("attention") is not None]
    test_mw = [r for r in test_rows if str(r["attention"]) in {"1", "3"}]
    test_y = np.asarray([int(str(r["attention"]) == "1") for r in test_mw], int)
    test_p = np.asarray([float(r["probability"]) for r in test_mw], float)
    independent = {
        "n_test_windows": int(len(test_mw)),
        "n_test_subjects": int(len({r["subject"] for r in test_mw})),
        "focus_vs_mind_wandering_auc": float(roc_auc_score(test_y, test_p)) if len(set(test_y)) == 2 else None,
        "focus_vs_mind_wandering_balanced_accuracy": float(balanced_accuracy_score(test_y, test_p >= 0.5)) if len(set(test_y)) == 2 else None,
    }
    args.output.write_text(json.dumps({
        "protocol": "behavior-time-gated windows scored with subject-specific exported calibration models",
        "mode": args.mode,
        "n_models": len(models),
        "n_windows": len(scored),
        "decision_counts": {k: sum(r["decision"] == k for r in scored) for k in ("research_focused", "research_nonfocused", "indeterminate")},
        "independent_test_audit": independent,
        "rows": scored,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["subject", "onset_rel_s", "attention", "attention_label", "mode", "phase", "probability", "decision", "reason"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(scored)
    print(json.dumps({"n_models": len(models), "n_windows": len(scored), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
