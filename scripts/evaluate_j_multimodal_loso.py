"""Leakage-aware multimodal baselines for the current J:\\Data cohort.

The script combines the current, reprocessed probe-level mmWave outputs with
the already extracted timestamp-gated RGB/NIR proxy features.  The visual
features are reused only when their event time is within one second of the
current behavior probe.  Models are evaluated with leave-one-subject-out
cross-validation; no window from a held-out participant enters training.

HRV features remain an explicit experimental ablation because the current
pipeline has not reached ECG-grade beat-to-beat validity.  Keeping them in a
separate feature family lets the project test whether they add out-of-subject
predictive information without presenting them as validated physiology.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DEFAULT_CURRENT = ROOT / "output" / "J_Data_GROUP_SUMMARY" / "probe_summary.csv"
DEFAULT_FULL_ROOT = ROOT / "output"
DEFAULT_VISION = ROOT / "output" / "E_Data_FAST" / "crossmodal_features_enhanced_all.csv"
DEFAULT_DATA_ROOT = Path(r"J:\Data")
DEFAULT_OUTPUT = ROOT / "output" / "J_Data_MULTIMODAL_v1"

MMWAVE_RATES = ["hr_bpm", "br_bpm"]
MMWAVE_HRV_EXPERIMENTAL = ["log_sdnn_ms", "log_rmssd_ms"]
BEHAVIOR = ["prior_rt_mean", "prior_n_err"]
NULL_TIME = ["block_num", "block_probe_fraction", "onset_rel_s"]
QUALITY_ONLY = ["harmonics_corrected"]
VISION = [
    "rgb_motion",
    "rgb_luminance",
    "rgb_face_detected",
    "rgb_face_area_frac",
    "rgb_face_center_offset",
    "rgb_face_luminance",
    "nir_pupil_dark_fraction",
    "nir_eye_contrast",
    "nir_pupil_detected",
    "nir_pupil_radius_px",
    "nir_quality",
]

FEATURE_SETS = {
    "null_time_block": NULL_TIME,
    "quality_harmonic_flag": QUALITY_ONLY,
    "mmwave_rates": MMWAVE_RATES,
    "mmwave_rates_plus_hrv_experimental": MMWAVE_RATES + MMWAVE_HRV_EXPERIMENTAL,
    "vision_proxy": VISION,
    "behavior": BEHAVIOR,
    "mmwave_vision": MMWAVE_RATES + VISION,
    "mmwave_behavior": MMWAVE_RATES + BEHAVIOR,
    "multimodal_all_experimental": MMWAVE_RATES + MMWAVE_HRV_EXPERIMENTAL + VISION + BEHAVIOR,
    "time_plus_mmwave": NULL_TIME + MMWAVE_RATES,
    "time_plus_behavior": NULL_TIME + BEHAVIOR,
    "time_plus_mmwave_behavior": NULL_TIME + MMWAVE_RATES + BEHAVIOR,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_mmwave_timestamp(data_root: Path, subject: str) -> float:
    files = sorted((data_root / f"sub-{subject}_" / "mmwave").glob("*_timestamps.csv"))
    if not files:
        raise FileNotFoundError(f"No mmWave timestamps for sub-{subject}")
    with files[0].open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            try:
                return float(row[1])
            except ValueError:
                continue
    raise ValueError(f"No valid timestamps in {files[0]}")


def behavior_probes(data_root: Path, subject: str) -> list[dict]:
    rows: list[dict] = []
    beh_dir = data_root / f"sub-{subject}_" / "beh"
    for path in sorted(beh_dir.glob(f"sub-{subject}_Block*_beh.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("is_probe") == "1" and row.get("probe_response"):
                    rows.append(row)
    return rows


def current_probe_details(full_root: Path, subject: str) -> dict[int, dict]:
    path = full_root / f"J_Data_SUB{subject}_FULL" / f"sub{subject}_full_windows.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(row["probe_id"]): row for row in payload.get("probes", [])}


def nearest_visual(rows: list[dict], onset_rel_s: float, tolerance_s: float) -> tuple[dict | None, float | None]:
    if not rows:
        return None, None
    best = min(rows, key=lambda row: abs(float(row["onset_rel_s"]) - onset_rel_s))
    delta = abs(float(best["onset_rel_s"]) - onset_rel_s)
    return (best, delta) if delta <= tolerance_s else (None, delta)


def build_matrix(
    current_path: Path,
    full_root: Path,
    vision_path: Path,
    data_root: Path,
    tolerance_s: float,
) -> tuple[pd.DataFrame, dict]:
    current = pd.read_csv(current_path, dtype={"subject": str})
    current["subject"] = current["subject"].str.zfill(3)
    vision = pd.read_csv(vision_path, dtype={"subject": str})
    vision["subject"] = vision["subject"].str.zfill(3)
    vision_by_subject = {subject: group.to_dict("records") for subject, group in vision.groupby("subject")}

    records: list[dict] = []
    offsets: list[float] = []
    for subject, group in current.groupby("subject", sort=True):
        probes = behavior_probes(data_root, subject)
        details = current_probe_details(full_root, subject)
        mmwave_start = first_mmwave_timestamp(data_root, subject)
        block_counts = Counter(str(row.get("block_num", "")) for row in probes)
        block_seen: Counter[str] = Counter()
        probe_meta = {}
        for probe_index, probe in enumerate(probes, 1):
            block = str(probe.get("block_num", ""))
            block_seen[block] += 1
            count = block_counts[block]
            fraction = (block_seen[block] - 1) / (count - 1) if count > 1 else 0.0
            probe_meta[probe_index] = {
                "block_num": float(block) if block else np.nan,
                "block_probe_fraction": float(fraction),
                "probe_vigilance": float(probe["probe_vigilance"]) if probe.get("probe_vigilance") else np.nan,
            }
        for _, row in group.iterrows():
            probe_id = int(row["probe_id"])
            if probe_id < 1 or probe_id > len(probes):
                continue
            behavior = probes[probe_id - 1]
            onset_ms = float(behavior["probe_onset_time"])
            onset_rel_s = (onset_ms - mmwave_start) / 1000.0
            visual, delta = nearest_visual(vision_by_subject.get(subject, []), onset_rel_s, tolerance_s)
            detail = details.get(probe_id, {})
            record = {
                "subject": subject,
                "probe_id": probe_id,
                "probe_onset_ms": int(onset_ms),
                "onset_rel_s": onset_rel_s,
                **probe_meta[probe_id],
                "label": int(row["label"]),
                "label_name": row["label_name"],
                "hr_bpm": float(row["hr_bpm"]),
                "br_bpm": float(row["br_bpm"]),
                "sdnn_ms": float(row["sdnn_ms"]),
                "rmssd_ms": float(row["rmssd_ms"]),
                "log_sdnn_ms": float(np.log1p(float(row["sdnn_ms"]))),
                "log_rmssd_ms": float(np.log1p(float(row["rmssd_ms"]))),
                "prior_rt_mean": float(row["prior_rt_mean"]) if pd.notna(row["prior_rt_mean"]) else np.nan,
                "prior_n_err": float(detail.get("prior_n_err")) if detail.get("prior_n_err") is not None else np.nan,
                "harmonics_corrected": float(bool(detail.get("harmonics_corrected", False))),
                "vision_matched": int(visual is not None),
                "vision_time_delta_s": float(delta) if visual is not None else np.nan,
            }
            for feature in VISION:
                value = visual.get(feature) if visual is not None else None
                try:
                    record[feature] = float(value) if value not in (None, "") else np.nan
                except (TypeError, ValueError):
                    record[feature] = np.nan
            if visual is not None:
                offsets.append(float(delta))
            records.append(record)

    matrix = pd.DataFrame(records).sort_values(["subject", "probe_id"]).reset_index(drop=True)
    audit = {
        "current_trusted_probes": int(len(current)),
        "matrix_rows": int(len(matrix)),
        "subjects": int(matrix["subject"].nunique()),
        "vision_matched_rows": int(matrix["vision_matched"].sum()),
        "vision_matched_subjects": int(matrix.loc[matrix["vision_matched"] == 1, "subject"].nunique()),
        "vision_time_delta_s_median": float(np.median(offsets)) if offsets else None,
        "vision_time_delta_s_max": float(np.max(offsets)) if offsets else None,
        "label_counts": {str(k): int(v) for k, v in Counter(matrix["label"]).items()},
        "note": "Visual windows are legacy 60-s timestamp-gated proxies; current mmWave probe windows are 30 s.",
    }
    return matrix, audit


def subject_equal_weights(subjects: np.ndarray) -> np.ndarray:
    counts = Counter(subjects.tolist())
    return np.asarray([1.0 / counts[s] for s in subjects], dtype=float)


def model_factory(name: str, seed: int):
    if name == "logistic_l2":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0, random_state=seed),
        )
    if name == "random_forest":
        return make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            RandomForestClassifier(
                n_estimators=80,
                max_depth=5,
                min_samples_leaf=5,
                max_features="sqrt",
                class_weight="balanced_subsample",
                random_state=seed,
                n_jobs=-1,
            ),
        )
    raise ValueError(name)


def fit_weights(model, subjects: np.ndarray) -> dict:
    weights = subject_equal_weights(subjects)
    final_name = list(model.named_steps)[-1]
    return {f"{final_name}__sample_weight": weights}


def metric_bundle(y: np.ndarray, score: np.ndarray) -> dict:
    pred = (score >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, score)) if len(np.unique(y)) == 2 else None,
        "average_precision": float(average_precision_score(y, score)) if len(np.unique(y)) == 2 else None,
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
    }


def subject_bootstrap(
    predictions: pd.DataFrame,
    seed: int,
    repeats: int,
) -> dict:
    rng = np.random.default_rng(seed)
    subjects = predictions["subject"].unique()
    values = {"roc_auc": [], "average_precision": [], "balanced_accuracy": []}
    subject_array = predictions["subject"].to_numpy(str)
    y_all = predictions["y_true"].to_numpy(int)
    score_all = predictions["score"].to_numpy(float)
    by_subject = {s: np.flatnonzero(subject_array == s) for s in subjects}
    for _ in range(repeats):
        sampled = rng.choice(subjects, size=len(subjects), replace=True)
        sampled_indices = np.concatenate([by_subject[s] for s in sampled])
        y_boot = y_all[sampled_indices]
        score_boot = score_all[sampled_indices]
        if len(np.unique(y_boot)) < 2:
            continue
        metrics = metric_bundle(y_boot, score_boot)
        for key in values:
            if metrics[key] is not None:
                values[key].append(metrics[key])
    result = {}
    for key, vals in values.items():
        result[f"{key}_ci95"] = [float(x) for x in np.quantile(vals, [0.025, 0.975])] if vals else [None, None]
    result["bootstrap_repeats_valid"] = int(len(values["roc_auc"]))
    return result


def evaluate_one(
    data: pd.DataFrame,
    features: list[str],
    target_name: str,
    model_name: str,
    seed: int,
    bootstrap_repeats: int,
) -> tuple[dict, pd.DataFrame]:
    if target_name == "nonfocus_vs_focus":
        use = data[data["label"].isin([1, 2, 3, 4])].copy()
        use["target"] = (use["label"] != 1).astype(int)
    elif target_name == "mind_wandering_vs_focus":
        use = data[data["label"].isin([1, 3])].copy()
        use["target"] = (use["label"] == 3).astype(int)
    else:
        raise ValueError(target_name)

    all_predictions = []
    for fold_index, held_out in enumerate(sorted(use["subject"].unique())):
        train = use[use["subject"] != held_out]
        test = use[use["subject"] == held_out]
        if test.empty or train["target"].nunique() < 2:
            continue
        model = model_factory(model_name, seed + fold_index)
        model.fit(
            train[features].to_numpy(float),
            train["target"].to_numpy(int),
            **fit_weights(model, train["subject"].to_numpy(str)),
        )
        score = model.predict_proba(test[features].to_numpy(float))[:, 1]
        fold = test[["subject", "probe_id", "label"]].copy()
        fold["y_true"] = test["target"].to_numpy(int)
        fold["score"] = score
        all_predictions.append(fold)
    predictions = pd.concat(all_predictions, ignore_index=True)
    metrics = metric_bundle(predictions["y_true"].to_numpy(int), predictions["score"].to_numpy(float))
    metrics.update(subject_bootstrap(predictions, seed, bootstrap_repeats))
    metrics.update({
        "target": target_name,
        "model": model_name,
        "features": features,
        "n": int(len(predictions)),
        "subjects": int(predictions["subject"].nunique()),
        "positive_n": int(predictions["y_true"].sum()),
        "positive_rate": float(predictions["y_true"].mean()),
    })
    return metrics, predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--full-root", type=Path, default=DEFAULT_FULL_ROOT)
    parser.add_argument("--vision", type=Path, default=DEFAULT_VISION)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--vision-tolerance-s", type=float, default=1.0)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260824)
    parser.add_argument(
        "--models", nargs="+", choices=["logistic_l2", "random_forest"],
        default=["logistic_l2", "random_forest"],
    )
    parser.add_argument(
        "--feature-sets", nargs="+", choices=sorted(FEATURE_SETS),
        default=list(FEATURE_SETS),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    matrix, audit = build_matrix(
        args.current,
        args.full_root,
        args.vision,
        args.data_root,
        args.vision_tolerance_s,
    )
    matrix.to_csv(args.output / "multimodal_probe_matrix.csv", index=False, encoding="utf-8-sig")

    common = matrix[matrix["vision_matched"] == 1].copy()
    results = []
    prediction_frames = []
    result_path = args.output / "loso_results.csv"
    prediction_path = args.output / "loso_predictions.csv"

    def checkpoint() -> None:
        pd.DataFrame(results).to_csv(result_path, index=False, encoding="utf-8-sig")
        if prediction_frames:
            pd.concat(prediction_frames, ignore_index=True).to_csv(
                prediction_path, index=False, encoding="utf-8-sig"
            )

    for target in ("nonfocus_vs_focus", "mind_wandering_vs_focus"):
        for feature_set in args.feature_sets:
            features = FEATURE_SETS[feature_set]
            for model_name in args.models:
                metrics, predictions = evaluate_one(
                    common,
                    features,
                    target,
                    model_name,
                    args.seed,
                    args.bootstrap,
                )
                metrics["feature_set"] = feature_set
                metrics["cohort"] = "common_vision_matched"
                results.append(metrics)
                predictions["target"] = target
                predictions["model"] = model_name
                predictions["feature_set"] = feature_set
                predictions["cohort"] = "common_vision_matched"
                prediction_frames.append(predictions)
                checkpoint()
                print(
                    f"completed target={target} cohort=common feature_set={feature_set} "
                    f"model={model_name} auc={metrics['roc_auc']:.4f}",
                    flush=True,
                )

        # Full-cohort mmWave baselines establish the cost of restricting the
        # analysis to windows that also have reusable visual features.
        for feature_set in ("mmwave_rates", "mmwave_rates_plus_hrv_experimental"):
            if feature_set not in args.feature_sets:
                continue
            for model_name in args.models:
                metrics, predictions = evaluate_one(
                    matrix,
                    FEATURE_SETS[feature_set],
                    target,
                    model_name,
                    args.seed,
                    args.bootstrap,
                )
                metrics["feature_set"] = feature_set
                metrics["cohort"] = "full_current_mmwave"
                results.append(metrics)
                predictions["target"] = target
                predictions["model"] = model_name
                predictions["feature_set"] = feature_set
                predictions["cohort"] = "full_current_mmwave"
                prediction_frames.append(predictions)
                checkpoint()
                print(
                    f"completed target={target} cohort=full feature_set={feature_set} "
                    f"model={model_name} auc={metrics['roc_auc']:.4f}",
                    flush=True,
                )

    result_df = pd.DataFrame(results)
    checkpoint()

    payload = {
        "analysis_status": "exploratory_multimodal_baseline",
        "validation": "leave-one-subject-out; preprocessing fit on training subjects only",
        "positive_class": {
            "nonfocus_vs_focus": "labels 2/3/4",
            "mind_wandering_vs_focus": "label 3",
        },
        "audit": audit,
        "input_sha256": {
            str(args.current): sha256(args.current),
            str(args.vision): sha256(args.vision),
        },
        "feature_status": {
            "hr_br": "current reprocessed mmWave outputs",
            "sdnn_rmssd": "experimental ablation; not validated physiology",
            "rgb_nir": "legacy timestamp-gated proxies; not calibrated pupil diameter or landmark-grade behavior",
            "behavior": "pre-probe external features; not part of the pure-mmWave claim",
        },
        "results": results,
    }
    (args.output / "multimodal_loso_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    best_rows = []
    for (target, model), group in result_df[result_df["cohort"] == "common_vision_matched"].groupby(["target", "model"]):
        best = group.sort_values("roc_auc", ascending=False).iloc[0]
        best_rows.append(best)
    best_df = pd.DataFrame(best_rows)
    lines = [
        "# J\\Data 多模态严格留一被试基线",
        "",
        f"当前可信探针 {audit['matrix_rows']} 个，其中 {audit['vision_matched_rows']} 个可与既有 RGB/NIR 时间窗在 ±{args.vision_tolerance_s:g} 秒内对齐。",
        "",
        "## 验证约束",
        "",
        "- 每次完整留出一名被试，训练预处理不读取该被试。",
        "- 行为、视觉和 HRV 分别进入消融，不把融合结果写成纯毫米波性能。",
        "- SDNN/RMSSD 保留为算法候选特征，但不解释为已验证生理量。",
        "- RGB/NIR 是既有代理特征，不是真正瞳孔直径或精细面部动作。",
        "",
        "## 各目标最佳探索结果",
        "",
        "| 目标 | 模型 | 特征集 | n | 被试 | ROC AUC | 95% CI | 平衡准确率 |",
        "|---|---|---|---:|---:|---:|---|---:|",
    ]
    for _, row in best_df.iterrows():
        ci = row["roc_auc_ci95"]
        lines.append(
            f"| {row['target']} | {row['model']} | {row['feature_set']} | {int(row['n'])} | "
            f"{int(row['subjects'])} | {row['roc_auc']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | "
            f"{row['balanced_accuracy']:.3f} |"
        )
    lines += [
        "",
        "完整消融与置信区间见 `loso_results.csv`；逐窗留出预测见 `loso_predictions.csv`。",
        "",
        "本结果用于选择下一轮算法与模态，不构成确认性专注分类证据。",
    ]
    (args.output / "J_Data_多模态LOSO基线报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"audit": audit, "results": len(results), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
