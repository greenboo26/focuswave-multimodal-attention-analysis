"""Fit a subject's first-half probe model and score the later half.

This is a research calibration runtime, not a deployment classifier. It keeps
subjects with insufficient calibration labels as indeterminate instead of
silently borrowing labels from the test half.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


LEGACY_MM = ["rmssd_ms", "sdnn_ms", "hr_med_bpm", "z_rmssd", "n_peaks"]
# Default runtime features are restricted to quantities that survived the
# independent ECG/RSP audit. HRV remains available only as an explicit
# exploratory option, because the current mmWave RMSSD/SDNN agreement is poor.
VALIDATED_MM = ["hr_med_bpm", "n_peaks", "hr_time_freq_gap_bpm",
                "hr_signal_usable_ratio", "hr_confidence", "hr_signal_std_10s_mm"]
EXTRA = ["breath_rate_bpm", "breath_rate_spectral_bpm", "breath_rate_time_freq_gap_bpm", "hr_time_freq_gap_bpm", "hr_confidence", "hr_signal_std_10s_mm"]
VIS = ["rgb_motion", "rgb_luminance", "nir_pupil_dark_fraction", "nir_eye_contrast"]
BEH = ["beh_accuracy", "beh_commission_rate", "beh_omission_rate", "beh_rt_median_ms", "beh_rt_sd_ms"]


def load_rows(mm_path: Path, cm_path: Path | None, behavior_path: Path | None = None) -> list[dict]:
    with mm_path.open(encoding="utf-8-sig", newline="") as f:
        mm = list(csv.DictReader(f))
    cmap = {}
    if cm_path:
        with cm_path.open(encoding="utf-8-sig", newline="") as f:
            cmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in csv.DictReader(f)}
    bmap = {}
    if behavior_path:
        with behavior_path.open(encoding="utf-8-sig", newline="") as f:
            bmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in csv.DictReader(f)}
    out = []
    for r in mm:
        key = (str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1))
        x = dict(r)
        if key in cmap:
            x.update({k: v for k, v in cmap[key].items() if k not in {"subject", "onset_rel_s", "attention"}})
        if key in bmap:
            x.update({f"beh_{k}": v for k, v in bmap[key].items() if k not in {"subject", "onset_rel_s", "attention"} and k in {"accuracy", "commission_rate", "omission_rate", "rt_median_ms", "rt_sd_ms"}})
        x["subject"] = key[0]
        x["onset_rel_s"] = float(r["onset_rel_s"])
        x["y"] = int(r["attention"] == "1")
        out.append(x)
    return out


def fit_and_score(rows: list[dict], features: list[str], model_dir: Path | None = None,
                  model_tag: str = "model") -> dict:
    by_subject = {}
    for row in rows:
        try:
            row["x"] = np.asarray([float(row[f]) for f in features], float)
        except (KeyError, ValueError, TypeError):
            row["x"] = None
        by_subject.setdefault(row["subject"], []).append(row)
    records = []
    for subject, subject_rows in sorted(by_subject.items()):
        subject_rows = sorted(subject_rows, key=lambda r: r["onset_rel_s"])
        split = max(1, len(subject_rows) // 2)
        calibration = subject_rows[:split]
        test = subject_rows[split:]
        calibration = [r for r in calibration if r["x"] is not None and np.all(np.isfinite(r["x"]))]
        test = [r for r in test if r["x"] is not None and np.all(np.isfinite(r["x"]))]
        y_cal = np.asarray([r["y"] for r in calibration], int)
        base = {"subject": subject, "calibration_n": len(calibration), "test_n": len(test), "features": features}
        if len(calibration) < 6 or len(set(y_cal)) < 2:
            base.update({"status": "indeterminate_insufficient_calibration", "calibration_positive_n": int(y_cal.sum()) if len(y_cal) else 0, "scores": []})
            records.append(base)
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        model.fit(np.asarray([r["x"] for r in calibration]), y_cal)
        if model_dir is not None:
            scaler = model.named_steps["standardscaler"]
            classifier = model.named_steps["logisticregression"]
            model_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "protocol": "first-half subject calibration, later independent scoring",
                "subject": subject,
                "model_tag": model_tag,
                "features": features,
                "mean": scaler.mean_.tolist(),
                "scale": scaler.scale_.tolist(),
                "coef": classifier.coef_[0].tolist(),
                "intercept": float(classifier.intercept_[0]),
                "calibration_n": int(len(calibration)),
                "calibration_positive_n": int(y_cal.sum()),
                "calibration_end_s": float(max(r["onset_rel_s"] for r in calibration)),
                "test_start_s": float(min(r["onset_rel_s"] for r in test)) if test else None,
                "decision_thresholds": {"nonfocused": 0.35, "focused": 0.65},
                "warning": "Research model; not clinically or deployment validated.",
            }
            (model_dir / f"{model_tag}__sub-{subject}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        scores = model.predict_proba(np.asarray([r["x"] for r in test]))[:, 1] if test else np.asarray([])
        base.update({
            "status": "scored",
            "calibration_positive_n": int(y_cal.sum()),
            "test_positive_n": int(sum(r["y"] for r in test)),
            "scores": [{"subject": subject, "onset_rel_s": r["onset_rel_s"], "attention": int(r["attention"]), "y": r["y"], "probability": float(p), "decision": "research_focused" if p >= .65 else "research_nonfocused" if p <= .35 else "indeterminate"} for r, p in zip(test, scores)],
        })
        records.append(base)
    scored_rows = [s for r in records if r["status"] == "scored" for s in r["scores"]]

    def evaluation(rows, name):
        if name == "focus_vs_mind_wandering":
            rows = [r for r in rows if r["attention"] in (1, 3)]
        y = np.asarray([r["y"] for r in rows], int)
        p = np.asarray([r["probability"] for r in rows], float)
        if len(y) == 0 or len(set(y)) < 2:
            return {"n_test_windows": int(len(y)), "n_test_subjects": 0, "auc": None, "balanced_accuracy": None}
        subjects = sorted({r["subject"] for r in rows})
        rng = np.random.default_rng(7)
        boot_auc, boot_bacc = [], []
        by_subject = {s: [r for r in rows if r["subject"] == s] for s in subjects}
        for _ in range(1000):
            sampled = rng.choice(subjects, size=len(subjects), replace=True)
            sample_rows = [r for s in sampled for r in by_subject[s]]
            sy = np.asarray([r["y"] for r in sample_rows], int)
            sp = np.asarray([r["probability"] for r in sample_rows], float)
            if len(set(sy)) == 2:
                boot_auc.append(float(roc_auc_score(sy, sp)))
                boot_bacc.append(float(balanced_accuracy_score(sy, sp >= 0.5)))
        q = lambda x: [float(v) for v in np.percentile(x, [2.5, 50, 97.5])] if x else None
        return {
            "n_test_windows": int(len(y)),
            "n_test_subjects": int(len(subjects)),
            "auc": float(roc_auc_score(y, p)),
            "balanced_accuracy": float(balanced_accuracy_score(y, p >= 0.5)),
            "subject_bootstrap": {
                "n_bootstrap": 1000,
                "auc_2.5_50_97.5": q(boot_auc),
                "balanced_accuracy_2.5_50_97.5": q(boot_bacc),
            },
        }

    return {
        "features": features,
        "n_subjects": len(records),
        "n_scored_subjects": sum(r["status"] == "scored" for r in records),
        "n_test_windows": len(scored_rows),
        "evaluations": {
            "focus_vs_all_nonfocus": evaluation(scored_rows, "focus_vs_all_nonfocus"),
            "focus_vs_mind_wandering": evaluation(scored_rows, "focus_vs_mind_wandering"),
        },
        "records": records,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmwave", type=Path, required=True)
    ap.add_argument("--crossmodal", type=Path)
    ap.add_argument("--behavior", type=Path, help="optional prior-window SART behavior features")
    ap.add_argument("--behavior-assisted", action="store_true", help="also fit behavior-assisted modes; behavior is not a pure mmWave deployment input")
    ap.add_argument("--expanded-vitals", action="store_true", help="include window breath and HR quality features")
    ap.add_argument("--physiology-profile", choices=("validated", "legacy_hrv"), default="validated",
                    help="validated=heart/quality features only; legacy_hrv restores exploratory HRV features")
    ap.add_argument("--model-dir", type=Path, help="optional directory for exported per-subject calibration models")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = load_rows(args.mmwave, args.crossmodal, args.behavior)
    feature_set = (VALIDATED_MM if args.physiology_profile == "validated" else LEGACY_MM) + (EXTRA if args.expanded_vitals else [])
    result = {
        "protocol": "first half labeled calibration, second half independent scoring",
        "behavior_assisted": bool(args.behavior and args.behavior_assisted),
        "behavior_temporal_rule": "behavior features are aggregated from the 60 s interval before each probe onset",
        "behavior_features": BEH if args.behavior and args.behavior_assisted else [],
        "behavior_target_excluded_from_features": True,
        "physiology_profile": args.physiology_profile,
        "hrv_default_disabled": args.physiology_profile == "validated",
        "mmwave_only": fit_and_score(rows, feature_set, args.model_dir, "mmwave"),
        "mmwave_rgb_nir": fit_and_score(rows, feature_set + VIS, args.model_dir, "mmwave_rgb_nir") if args.crossmodal else None,
        "mmwave_behavior": fit_and_score(rows, feature_set + BEH, args.model_dir, "mmwave_behavior") if args.behavior and args.behavior_assisted else None,
        "mmwave_rgb_nir_behavior": fit_and_score(rows, feature_set + VIS + BEH, args.model_dir, "mmwave_rgb_nir_behavior") if args.behavior and args.behavior_assisted and args.crossmodal else None,
        "warning": "Research calibration only; subjects without two calibration classes remain indeterminate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (None if v is None else {x: v[x] for x in ("n_subjects", "n_scored_subjects")}) for k, v in result.items() if isinstance(v, dict)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
