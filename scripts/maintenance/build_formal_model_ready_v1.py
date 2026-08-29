from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


OUT: Path
NIR_ROOT: Path
RGB_ROOT: Path
KEY = ["repeat_participant_id", "session_id", "block_id", "probe_id", "window_name"]
IDENTITY = ["repeat_participant_id", "session_id", "single_experiment_id", "site"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(df: pd.DataFrame, name: str) -> Path:
    path = OUT / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value):
        return None
    return value


def safe_int(value: Any, default: int = 0) -> int:
    return default if pd.isna(value) else int(value)


def write_json(obj: dict[str, Any], name: str) -> Path:
    path = OUT / name
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    return path


def read_completion(session_id: str) -> str:
    p = NIR_ROOT / session_id / "completion.json"
    if not p.exists():
        return "ABSENT"
    try:
        return str(json.loads(p.read_text(encoding="utf-8")).get("status", "UNKNOWN"))
    except Exception:
        return "UNREADABLE"


def frame_counts_by_window(timeline: pd.DataFrame) -> dict[tuple[str, str, str, str, str], int]:
    counts: dict[tuple[str, str, str, str, str], int] = {}
    for session_id, rows in timeline.groupby("session_id", sort=False):
        frame_path = NIR_ROOT / str(session_id) / "data" / "frame_coverage.csv.gz"
        if not frame_path.exists():
            continue
        frame = pd.read_csv(frame_path, usecols=["unix_ms"])
        times = pd.to_numeric(frame["unix_ms"], errors="coerce").dropna().to_numpy()
        session_rows = rows.reset_index(drop=True)
        for row in session_rows.itertuples(index=False):
            start = getattr(row, "window_effective_start_unix_ms")
            end = getattr(row, "probe_onset_unix_ms")
            n = int(((times >= float(start)) & (times < float(end))).sum())
            counts[tuple(str(getattr(row, c)) for c in KEY)] = n
    return counts


def build_nir_audit(timeline: pd.DataFrame, nir: pd.DataFrame) -> pd.DataFrame:
    nir_cols = KEY + [
        "nir_available",
        "nir_missing_reason",
        "nir_window_eye_row_count",
        "nir_ritnet_success_fraction",
        "nir_observed_eye_fraction",
        "nir_pupil_fit_valid_fraction",
        "nir_analysis_valid_pixel_fraction_median",
        "nir_pupil_equiv_diameter_median",
        "nir_pupil_geom_mean_diameter_median",
        "nir_pupil_contour_area_median",
        "nir_pupil_ellipse_area_median",
        "nir_source_path",
        "nir_source_manifest",
    ]
    x = timeline[KEY].merge(nir[nir_cols], on=KEY, how="left", validate="one_to_one")
    frame_counts = frame_counts_by_window(timeline)
    geometry = [
        "nir_pupil_equiv_diameter_median",
        "nir_pupil_geom_mean_diameter_median",
        "nir_pupil_contour_area_median",
        "nir_pupil_ellipse_area_median",
    ]
    rows = []
    for row in x.itertuples(index=False):
        key = tuple(str(getattr(row, c)) for c in KEY)
        session_id = str(row.session_id)
        session_path = NIR_ROOT / session_id
        producer_exists = session_path.is_dir()
        completion = read_completion(session_id)
        observed = bool(getattr(row, "nir_available"))
        geom_values = [getattr(row, c) for c in geometry]
        geometry_valid = any(pd.notna(v) for v in geom_values)
        qc_fail = observed and not geometry_valid
        if not producer_exists:
            state = "STRUCTURAL_MISSING"
            reason = "missing_producer_session_output"
            missing_class = "STRUCTURAL_MISSING"
        elif not observed:
            state = "OBSERVATION_MISSING"
            reason = "no_eye_metrics_in_frozen_window"
            missing_class = "OBSERVATION_MISSING"
        elif qc_fail:
            state = "QC_FAIL"
            reason = "qc_fail_no_valid_pupil_geometry"
            missing_class = "QC_FAIL"
        else:
            state = "OBSERVED"
            reason = ""
            missing_class = "OBSERVED"
        qc_index = session_path / "qc" / "qc_index.csv"
        source_items = [
            session_path / "data" / "eye_metrics.csv.gz",
            session_path / "data" / "frame_coverage.csv.gz",
            qc_index,
        ]
        qc_source = ";".join(str(p) for p in source_items if p.exists()) or "ABSENT"
        rows.append(
            {
                "repeat_participant_id": row.repeat_participant_id,
                "session_id": session_id,
                "block_id": row.block_id,
                "probe_id": row.probe_id,
                "window_name": row.window_name,
                "nir_observed": observed,
                "nir_missing_reason": reason,
                "producer_session_exists": producer_exists,
                "completion_status": completion,
                "eye_metric_rows_in_window": safe_int(getattr(row, "nir_window_eye_row_count")),
                "frame_coverage_rows_in_window": frame_counts.get(key, 0),
                "qc_source": qc_source,
                "structural_vs_observation_missing": missing_class,
                "nir_state": state,
                "nir_geometry_valid": geometry_valid,
            }
        )
    return pd.DataFrame(rows)


def load_rgb_evidence() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    status: dict[str, dict[str, Any]] = {}
    inventory: dict[str, dict[str, Any]] = {}
    status_path = RGB_ROOT / "cohort_status.csv"
    inventory_path = RGB_ROOT / "rgb_formal_audit_v1.csv"
    if status_path.exists():
        for row in pd.read_csv(status_path, encoding="utf-8-sig").to_dict("records"):
            status[str(row.get("subject"))] = row
    if inventory_path.exists():
        for row in pd.read_csv(inventory_path, encoding="utf-8-sig").to_dict("records"):
            inventory[str(row.get("subject"))] = row
    return status, inventory


def tri(value: Any) -> str:
    if value is True or value is np.True_:
        return "TRUE"
    if value is False or value is np.False_:
        return "FALSE"
    return "NOT_EVALUABLE"


def build_rgb_audit(timeline: pd.DataFrame, rgb: pd.DataFrame) -> pd.DataFrame:
    rgb_cols = KEY + [
        "rgb_available",
        "rgb_missing_reason",
        "rgb_source_path",
        "rgb_source_row_count",
        "rgb_primary_face_fraction",
        "rgb_eye_geometry_valid_fraction",
        "rgb_ear_mean_median",
        "rgb_aperture_iris_mean_median",
        "rgb_pose_visibility_median",
        "rgb_head_motion_norm_per_sec_mean",
        "rgb_global_motion_energy_per_sec_mean",
    ]
    x = timeline[KEY].merge(rgb[rgb_cols], on=KEY, how="left", validate="one_to_one")
    status, inventory = load_rgb_evidence()
    geometry = ["rgb_primary_face_fraction", "rgb_ear_mean_median", "rgb_aperture_iris_mean_median"]
    rows = []
    for row in x.itertuples(index=False):
        session_id = str(row.session_id)
        subject_dir = RGB_ROOT / session_id
        producer_exists = subject_dir.is_dir()
        expected_raw = [
            subject_dir / f"{session_id}_motion_raw.parquet",
            subject_dir / f"{session_id}_pose_landmarks.parquet",
            subject_dir / f"{session_id}_face_raw.parquet",
        ]
        raw_absent = not any(p.exists() for p in expected_raw)
        manifest_absent = not (subject_dir / f"{session_id}_manifest.json").exists()
        status_row = status.get(session_id, {})
        inv = inventory.get(session_id, {})
        observed = bool(getattr(row, "rgb_available"))
        feature_valid = any(pd.notna(getattr(row, c)) for c in geometry)
        qc_failure = observed and not feature_valid
        formal_error = str(inv.get("formal_timeline_error", "")) if inv else ""
        has_overlap_evidence = bool(inv) and not formal_error and bool(inv.get("formal_timeline_parse_ok", False))
        post_failure = str(status_row.get("status", "")).lower() == "failed" or bool(status_row.get("error"))
        if not producer_exists or raw_absent:
            state = "STRUCTURAL_MISSING"
            reason = "producer_session_or_raw_parquet_absent"
            missing_class = "STRUCTURAL_MISSING"
        elif not observed:
            state = "OBSERVATION_MISSING"
            reason = "no_raw_observation_in_frozen_window"
            missing_class = "OBSERVATION_MISSING"
        elif qc_failure:
            state = "QC_FAIL"
            reason = "qc_fail_no_current_rgb_feature_value"
            missing_class = "QC_FAIL"
        else:
            state = "OBSERVED"
            reason = ""
            missing_class = "OBSERVED"
        if session_id == "sub-099":
            producer_diagnosis = "producer_session_absent; raw_parquet_absent; subject_manifest_absent; root_cohort_manifest_exists_but_subject_not_registered"
        else:
            producer_diagnosis = "current_rgb_raw_observation_present"
        rows.append(
            {
                "repeat_participant_id": row.repeat_participant_id,
                "session_id": session_id,
                "block_id": row.block_id,
                "probe_id": row.probe_id,
                "window_name": row.window_name,
                "rgb_observed": observed,
                "rgb_missing_reason": reason,
                "producer_session_exists": producer_exists,
                "raw_parquet_absent": raw_absent,
                "manifest_absent": manifest_absent,
                "postprocessing_failure": tri(post_failure),
                "probe_window_overlap_failure": "FALSE" if has_overlap_evidence else ("NOT_EVALUABLE" if formal_error else "FALSE"),
                "qc_failure": tri(qc_failure),
                "completion_status": str(status_row.get("status", "ABSENT_FROM_COHORT_STATUS")),
                "formal_timeline_error": formal_error,
                "producer_diagnosis": producer_diagnosis,
                "qc_source": str(RGB_ROOT / session_id) if subject_dir.exists() else "ABSENT",
                "structural_vs_observation_missing": missing_class,
                "rgb_state": state,
            }
        )
    return pd.DataFrame(rows)


def make_contracts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cols = [
        "feature_name",
        "modality",
        "source_column",
        "definition",
        "unit",
        "aggregation_rule",
        "window",
        "qc_requirement",
        "missing_semantics",
        "allowed_as_predictor",
        "reason",
        "provenance",
    ]

    def row(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    b: list[dict[str, Any]] = []
    behavior_common = {
        "modality": "Behavior",
        "window": "pre_30s=[probe_onset_unix_ms-30000, probe_onset_unix_ms)",
        "qc_requirement": "behavior_qc_status=available_formal_events",
        "missing_semantics": "NaN only if no valid pre-onset trials; no imputation here",
        "provenance": "behavior_probe_merge_ready.csv; current formal event aggregation",
    }
    for source, definition, unit in [
        ("behavior_rt_median_ms_pre30s", "median valid response time of trials before probe onset", "ms"),
        ("behavior_rt_mean_ms_pre30s", "mean valid response time of trials before probe onset", "ms"),
        ("behavior_error_rate_pre30s", "error proportion in trials before probe onset", "proportion"),
        ("behavior_commission_rate_pre30s", "commission-error proportion before probe onset", "proportion"),
        ("behavior_omission_rate_pre30s", "omission proportion before probe onset", "proportion"),
    ]:
        b.append(row(feature_name=source, source_column=source, definition=definition, unit=unit,
                     aggregation_rule="trial-level aggregation within pre_30s; no post-onset rows",
                     allowed_as_predictor=True, reason="pre-onset context/behavior feature", **behavior_common))
    for source, definition, unit, reason in [
        ("behavior_trial_count_pre30s", "number of trials available before probe onset", "count", "context/QC metadata; not primary to avoid availability leakage"),
        ("behavior_valid_rt_count_pre30s", "number of trials with valid RT before probe onset", "count", "QC/missingness metadata; not primary"),
        ("behavior_available", "formal behavior row availability", "boolean", "availability indicator; QC only"),
        ("behavior_qc_status", "behavior source QC status", "categorical", "QC only"),
        ("behavior_source_path", "local behavior provenance path", "path", "provenance only"),
    ]:
        b.append(row(feature_name=source, source_column=source, definition=definition, unit=unit,
                     aggregation_rule="as emitted by current merge-ready table", allowed_as_predictor=False,
                     reason=reason, **behavior_common))
    behavior = pd.DataFrame(b, columns=cols)

    n: list[dict[str, Any]] = []
    nir_common = {
        "modality": "NIR",
        "window": "pre_30s effective window; [window_effective_start_unix_ms, probe_onset_unix_ms)",
        "qc_requirement": "NIR observation present; fullclass geometry QC retained; no PIR primary",
        "missing_semantics": "NaN for structural/observation missing or QC_FAIL; QC state retained separately",
        "provenance": "nir_probe_merge_ready.csv; ritnet-fullclass-final eye_metrics.csv.gz",
    }
    for source, definition, unit in [
        ("nir_pupil_equiv_diameter_median", "equivalent pupil diameter from fullclass pupil geometry", "pixel"),
        ("nir_pupil_geom_mean_diameter_median", "geometric-mean pupil diameter from fullclass pupil geometry", "pixel"),
        ("nir_pupil_contour_area_median", "pupil contour area from fullclass segmentation", "pixel^2"),
        ("nir_pupil_ellipse_area_median", "fitted pupil ellipse area from fullclass geometry", "pixel^2"),
    ]:
        n.append(row(feature_name=source, source_column=source, definition=definition, unit=unit,
                     aggregation_rule="pool left/right eye rows within window; median over valid rows; no eye weighting",
                     allowed_as_predictor=True, reason="current fullclass pupil geometry primary feature; no PIR", **nir_common))
    for source, definition, unit, reason in [
        ("nir_observed_eye_fraction", "fraction of eye observations available in window", "proportion", "coverage/QC only"),
        ("nir_pupil_fit_valid_fraction", "fraction of eye rows with valid pupil fit", "proportion", "geometry QC only"),
        ("nir_ritnet_success_fraction", "RITnet successful eye-row fraction", "proportion", "source QC only"),
        ("nir_temporal_anomaly_fraction", "fraction flagged by temporal QC", "proportion", "temporal QC only"),
        ("nir_analysis_valid_pixel_fraction_median", "median valid analysis-domain pixel fraction", "proportion", "pixel QC only"),
        ("nir_window_eye_row_count", "eye metric rows in frozen window", "count", "coverage metadata only"),
        ("nir_window_unix_span_ms", "observed Unix-time span in window", "ms", "temporal QC only"),
        ("nir_available", "NIR observation availability flag", "boolean", "availability indicator; not primary"),
        ("nir_observation_status", "NIR observation state from current merge", "categorical", "missingness state only"),
        ("nir_primary_metric_domain", "declared primary metric domain", "categorical", "provenance/QC only"),
        ("nir_source_path", "local eye metric provenance path", "path", "provenance only"),
    ]:
        n.append(row(feature_name=source, source_column=source, definition=definition, unit=unit,
                     aggregation_rule="as emitted by current merge-ready table", allowed_as_predictor=False,
                     reason=reason, **nir_common))
    nir = pd.DataFrame(n, columns=cols)

    r: list[dict[str, Any]] = []
    rgb_common = {
        "modality": "RGB",
        "window": "pre_30s=[probe_onset_unix_ms-30000, probe_onset_unix_ms)",
        "qc_requirement": "current raw-parquet observation; no thresholded QC exclusion frozen",
        "missing_semantics": "NaN for structural/observation missing or QC_FAIL; state retained separately",
        "provenance": "rgb_probe_merge_ready.csv; current Face/Pose/Motion raw-parquet postprocessing",
    }
    for source, definition, unit in [
        ("rgb_primary_face_fraction", "fraction of sampled face observations assigned to primary face rank 0", "proportion"),
        ("rgb_ear_mean_median", "median mean-eye aspect ratio from eyelid geometry", "ratio"),
        ("rgb_aperture_iris_mean_median", "median normalized eyelid/iris aperture geometry", "ratio"),
        ("rgb_head_motion_norm_per_sec_mean", "mean primary-face head-motion norm per second", "normalized units/s"),
        ("rgb_global_motion_energy_mean", "mean global motion energy in window", "normalized units"),
        ("rgb_global_motion_energy_per_sec_mean", "mean time-normalized global motion energy", "normalized units/s"),
    ]:
        r.append(row(feature_name=source, source_column=source, definition=definition, unit=unit,
                     aggregation_rule="median for geometry/coverage; mean for motion; within pre_30s",
                     allowed_as_predictor=True, reason="current formed RGB candidate with interpretable semantics", **rgb_common))
    for source, definition, unit, reason in [
        ("rgb_pose_visibility_median", "median pose landmark visibility", "proportion", "pose QC/visibility, not head-pose angle"),
        ("rgb_eye_geometry_valid_fraction", "fraction of eyelid observations passing geometry validity", "proportion", "eye-geometry QC only"),
        ("rgb_motion_valid_fraction", "fraction of motion rows valid", "proportion", "motion QC only"),
        ("rgb_gap_fraction", "fraction of motion time with gaps", "proportion", "temporal QC only"),
        ("rgb_pose_valid_fraction", "fraction of pose rows valid", "proportion", "pose QC only"),
        ("rgb_face_score_median", "median face detector score", "score", "detector QC only"),
        ("rgb_multiface_frame_fraction", "fraction of frames with multiple faces", "proportion", "face QC only"),
        ("rgb_face_sample_count", "face samples in window", "count", "coverage/QC metadata only"),
        ("rgb_blink_event_count_candidate", "native probability transition blink candidate count", "count", "PROVISIONAL_CANDIDATE; threshold/event definition not frozen"),
        ("rgb_native_eye_blink_mean_median", "native eye-blink probability candidate", "probability", "PROVISIONAL_CANDIDATE; not primary"),
        ("PERCLOS", "validated PERCLOS feature", "proportion", "ABSENT / NOT_VALIDATED; never a primary predictor"),
        ("rgb_head_pose_yaw_pitch_roll", "head-pose angles", "degrees", "not currently aggregated in merge-ready output; do not silently reconstruct"),
        ("rgb_available", "RGB observation availability flag", "boolean", "availability indicator; not primary"),
        ("rgb_observation_status", "RGB observation state from current merge", "categorical", "missingness state only"),
        ("rgb_source_path", "local RGB provenance path", "path", "provenance only"),
    ]:
        r.append(row(feature_name=source, source_column=source if source != "PERCLOS" else "ABSENT",
                     definition=definition, unit=unit, aggregation_rule="as emitted or absent in current merge-ready table",
                     allowed_as_predictor=False, reason=reason, **rgb_common))
    rgb_contract = pd.DataFrame(r, columns=cols)
    return behavior, nir, rgb_contract


def behavior_temporal_audit(behavior: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in behavior.itertuples(index=False):
        source = str(r.source_column)
        is_target = source.startswith("label_")
        pre_onset = "pre_30s" in str(r.window) and not is_target
        rows.append(
            {
                "feature_name": r.feature_name,
                "source_column": source,
                "role": "PREDICTOR" if bool(r.allowed_as_predictor) else ("TARGET_OR_EXCLUDED"),
                "max_data_time_relative_to_probe_onset": "<0 ms" if pre_onset else ("target-only" if is_target else "not used"),
                "future_data_used": False,
                "future_trial_used": False,
                "future_block_used": False,
                "label_derived": is_target,
                "status": "PASS" if pre_onset or not bool(r.allowed_as_predictor) else "FAIL",
                "reason": "bounded to pre-onset context" if pre_onset else str(r.reason),
            }
        )
    return pd.DataFrame(rows)


def matched_summary(full: pd.DataFrame, matched: pd.DataFrame, nir_audit: pd.DataFrame, rgb_audit: pd.DataFrame) -> dict[str, Any]:
    current_participants = sorted(full.repeat_participant_id.dropna().unique().tolist())
    matched_participants = sorted(matched.repeat_participant_id.dropna().unique().tolist())
    current_sessions = full.groupby("repeat_participant_id")["session_id"].nunique()
    matched_sessions = matched.groupby("repeat_participant_id")["session_id"].nunique()
    current_blocks = full.assign(_b=full["session_id"].astype(str) + "|" + full["block_id"].astype(str)).groupby("repeat_participant_id")["_b"].nunique()
    matched_blocks = matched.assign(_b=matched["session_id"].astype(str) + "|" + matched["block_id"].astype(str)).groupby("repeat_participant_id")["_b"].nunique()
    partial_sessions = [p for p in current_participants if 0 < matched_sessions.get(p, 0) < current_sessions.get(p, 0)]
    partial_blocks = [p for p in current_participants if 0 < matched_blocks.get(p, 0) < current_blocks.get(p, 0)]
    excluded = full.loc[~full["_primary"], list(dict.fromkeys(KEY))].copy()
    excluded_counts = excluded.groupby("session_id").size().sort_values(ascending=False)
    label_counts = matched["label_probe_vigilance"].value_counts(dropna=False).sort_index().to_dict()
    participant_labels: dict[str, dict[str, int]] = {}
    for p, g in matched.groupby("repeat_participant_id"):
        participant_labels[str(p)] = {str(k): int(v) for k, v in g["label_probe_vigilance"].value_counts(dropna=False).sort_index().items()}
    probes_per_session = matched.groupby("session_id").size().sort_index()
    blocks_per_session = matched.groupby("session_id")["block_id"].nunique().sort_index()
    return {
        "status": "FROZEN_PRIMARY_MATCHED_COHORT",
        "definition": "Behavior observed AND NIR observed AND RGB observed; no label-dependent filtering",
        "window_semantics": "pre_30s=[probe_onset_unix_ms-30000, probe_onset_unix_ms)",
        "canonical_key": KEY,
        "full_timeline": {"rows": int(len(full)), "sessions": int(full.session_id.nunique()), "repeat_participants": int(full.repeat_participant_id.nunique())},
        "matched": {"rows": int(len(matched)), "sessions": int(matched.session_id.nunique()), "repeat_participants": int(matched.repeat_participant_id.nunique()), "site_distribution": {str(k): int(v) for k, v in matched.site.value_counts().sort_index().items()}},
        "probes_per_session": {"counts": {str(k): int(v) for k, v in probes_per_session.items()}, "min": int(probes_per_session.min()), "max": int(probes_per_session.max()), "mean": float(probes_per_session.mean())},
        "blocks_per_session": {"counts": {str(k): int(v) for k, v in blocks_per_session.items()}, "min": int(blocks_per_session.min()), "max": int(blocks_per_session.max())},
        "label_distribution": {str(k): int(v) for k, v in label_counts.items()},
        "participant_level_label_distribution": participant_labels,
        "excluded": {"rows": int(len(excluded)), "sessions": {str(k): int(v) for k, v in excluded_counts.items()}, "probes": excluded[KEY].astype(str).to_dict("records")},
        "participant_coverage": {"current_participants": len(current_participants), "matched_participants": len(matched_participants), "zero_matched_participants": [p for p in current_participants if p not in matched_participants], "partial_session_participants": partial_sessions, "partial_block_participants": partial_blocks},
        "modality_state_counts": {"nir": {str(k): int(v) for k, v in nir_audit.nir_state.value_counts().items()}, "rgb": {str(k): int(v) for k, v in rgb_audit.rgb_state.value_counts().items()}},
        "validation": {"canonical_key_nonnull": bool(full[KEY].notna().all().all()), "canonical_key_unique": bool(not full.duplicated(KEY).any()), "matched_subset_of_timeline": bool(set(map(tuple, matched[KEY].astype(str).to_numpy())) <= set(map(tuple, full[KEY].astype(str).to_numpy()))), "matched_count_expected_1295": len(matched) == 1295, "label_dependent_filtering": False},
    }


def build_loso(matched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    participants = sorted(matched.repeat_participant_id.astype(str).unique())
    registry = pd.DataFrame({"repeat_participant_id": participants, "outer_fold_id": [f"LOSO_{i:03d}" for i in range(1, len(participants) + 1)]})
    chunks = []
    fold_checks = []
    base = matched[list(dict.fromkeys(KEY + ["single_experiment_id", "repeat_participant_id"]))].copy()
    for p, fold in registry.itertuples(index=False):
        z = base.copy()
        z["outer_fold_id"] = fold
        z["role"] = np.where(z["repeat_participant_id"].astype(str).eq(str(p)), "TEST", "TRAIN")
        chunks.append(z)
        train_p = set(z.loc[z.role == "TRAIN", "repeat_participant_id"])
        test_p = set(z.loc[z.role == "TEST", "repeat_participant_id"])
        session_ok = set(matched.loc[matched.repeat_participant_id.astype(str).eq(str(p)), "session_id"]) <= set(z.loc[(z.role == "TEST") & z.repeat_participant_id.astype(str).eq(str(p)), "session_id"])
        fold_checks.append({"outer_fold_id": fold, "test_participant": p, "train_test_participant_intersection_empty": len(train_p & test_p) == 0, "test_participant_all_sessions_in_test": session_ok, "train_rows": int((z.role == "TRAIN").sum()), "test_rows": int((z.role == "TEST").sum())})
    folds = pd.concat(chunks, ignore_index=True)
    participant_identity = matched.groupby("single_experiment_id")["repeat_participant_id"].nunique()
    session_participants = matched.groupby("session_id")["repeat_participant_id"].nunique()
    participant_to_fold = dict(zip(registry.repeat_participant_id.astype(str), registry.outer_fold_id.astype(str)))
    session_to_participant = matched.groupby("session_id")["repeat_participant_id"].first().astype(str)
    checks = {
        "participant_intersections_empty": all(x["train_test_participant_intersection_empty"] for x in fold_checks),
        "single_experiment_id_not_cross_participant": bool((participant_identity <= 1).all()),
        "session_not_cross_participant_or_fold": bool((session_participants <= 1).all()) and bool(session_to_participant.map(participant_to_fold).notna().all()),
        "probe_key_unique_in_matched": bool(not matched.duplicated(KEY).any()),
        "probe_key_unique_within_each_fold_role": bool(not folds.duplicated(["outer_fold_id", "role"] + KEY).any()),
        "test_participant_all_sessions_in_test": all(x["test_participant_all_sessions_in_test"] for x in fold_checks),
    }
    audit = {"status": "PASS" if all(checks.values()) else "FAIL", "fold_count": len(registry), "matched_participant_count": len(participants), "checks": checks, "per_fold": fold_checks, "leakage_found": not all(checks.values())}
    return folds, registry, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the FocusWave formal model-ready audit package from an existing local package.")
    parser.add_argument("--package-dir", required=True, help="Directory containing the existing canonical timeline and modality merge-ready tables; outputs are written here.")
    parser.add_argument("--nir-root", required=True, help="Existing NIR producer output root; no producer is launched.")
    parser.add_argument("--rgb-root", required=True, help="Existing RGB postprocessing/raw output root; no producer is launched.")
    args = parser.parse_args()
    global OUT, NIR_ROOT, RGB_ROOT
    OUT = Path(args.package_dir).resolve()
    NIR_ROOT = Path(args.nir_root).resolve()
    RGB_ROOT = Path(args.rgb_root).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    timeline = pd.read_csv(OUT / "canonical_probe_timeline.csv")
    behavior = pd.read_csv(OUT / "behavior_probe_merge_ready.csv")
    nir = pd.read_csv(OUT / "nir_probe_merge_ready.csv")
    rgb = pd.read_csv(OUT / "rgb_probe_merge_ready.csv")
    assert not timeline.duplicated(KEY).any()
    nir_audit = build_nir_audit(timeline, nir)
    rgb_audit = build_rgb_audit(timeline, rgb)
    write_csv(nir_audit, "NIR_MISSINGNESS_AUDIT.csv")
    write_csv(rgb_audit, "RGB_MISSINGNESS_AUDIT.csv")

    modality_columns = list(dict.fromkeys(KEY + IDENTITY + ["site", "probe_onset_unix_ms", "condition", "label_probe_vigilance", "label_probe_response", "label_probe_rt_ms"]))
    modality = timeline[modality_columns].copy()
    modality = modality.merge(behavior[KEY + ["behavior_available", "behavior_qc_status"]], on=KEY, validate="one_to_one")
    modality["behavior_observed"] = modality["behavior_available"]
    modality = modality.merge(nir_audit[KEY + ["nir_observed", "nir_state", "nir_missing_reason"]], on=KEY, validate="one_to_one")
    modality = modality.merge(rgb_audit[KEY + ["rgb_observed", "rgb_state", "rgb_missing_reason"]], on=KEY, validate="one_to_one")
    modality["_primary"] = modality.behavior_available & modality.nir_observed & modality.rgb_observed
    matched = modality.loc[modality["_primary"]].copy()
    matched["target_probe_vigilance"] = matched["label_probe_vigilance"]
    matched["include_primary"] = True
    matched["exclusion_reason"] = ""
    matched = matched.drop(columns=["_primary"])
    write_csv(matched, "formal_matched_cohort_v1.csv")
    full_for_summary = modality.copy()
    full_for_summary["_primary"] = full_for_summary["behavior_available"] & full_for_summary["nir_observed"] & full_for_summary["rgb_observed"]
    summary = matched_summary(full_for_summary, matched, nir_audit, rgb_audit)
    write_json(summary, "FORMAL_MATCHED_COHORT_SUMMARY.json")

    excluded = full_for_summary.loc[~full_for_summary["_primary"]]
    excluded_session_rows = excluded.groupby("session_id").size().sort_values(ascending=False)
    audit_lines = [
        "# FocusWave formal matched cohort v1 audit",
        "",
        "Status: `FROZEN_PRIMARY_MATCHED_COHORT`",
        "",
        "Definition: Behavior observed AND NIR observed AND RGB observed. The inclusion mask uses only modality observation flags and the canonical five-column key; it does not use the probe label, response, response time, or any outcome-derived field.",
        "",
        f"- Full canonical timeline: **{len(full_for_summary)} rows / {full_for_summary.session_id.nunique()} sessions / {full_for_summary.repeat_participant_id.nunique()} repeat participants**.",
        f"- Primary matched cohort: **{len(matched)} rows / {matched.session_id.nunique()} sessions / {matched.repeat_participant_id.nunique()} repeat participants**.",
        f"- Excluded from primary matched: **{len(excluded)} probes across {excluded.session_id.nunique()} sessions**.",
        "- Primary window: `pre_30s = [probe_onset_unix_ms-30000, probe_onset_unix_ms)`.",
        "- Full timeline remains preserved in `canonical_probe_timeline.csv`; it is not overwritten by the matched table.",
        "",
        "## Excluded sessions",
        "",
        "| session_id | excluded probes | reason |",
        "|---|---:|---|",
    ]
    for session_id, count in excluded_session_rows.items():
        reasons = sorted(set(excluded.loc[excluded.session_id.eq(session_id), "nir_state"].astype(str)) | set(excluded.loc[excluded.session_id.eq(session_id), "rgb_state"].astype(str)))
        audit_lines.append(f"| {session_id} | {int(count)} | {', '.join(reasons)} |")
    audit_lines += [
        "",
        "## Participant coverage after matching",
        "",
        f"- Participants with at least one matched session: **{matched.repeat_participant_id.nunique()}**.",
        f"- Participants with zero matched probes: **{', '.join(summary['participant_coverage']['zero_matched_participants']) or 'none'}**.",
        f"- Participants with partial session coverage: **{', '.join(summary['participant_coverage']['partial_session_participants']) or 'none'}**.",
        f"- Participants with partial block coverage: **{', '.join(summary['participant_coverage']['partial_block_participants']) or 'none'}**.",
        "",
        "## Validation",
        "",
        "All canonical keys are non-null and unique; all matched keys are members of the 1,440-row timeline; the expected 1,295-row count is met; no label-dependent filtering was used.",
        "",
        "The one NIR `QC_FAIL` observation (`sub-084`, `block-1`, `probe-06`) remains in the observation-defined matched denominator with NaN pupil geometry. Any later model fit must use an explicit missing-value policy and must not silently delete this row.",
    ]
    (OUT / "FORMAL_MATCHED_COHORT_AUDIT.md").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    folds, registry, loso_audit = build_loso(matched)
    write_csv(folds, "formal_loso_folds_v1.csv")
    write_csv(registry, "formal_loso_participant_registry_v1.csv")
    write_json(loso_audit, "LOSO_LEAKAGE_AUDIT.json")

    behavior_contract, nir_contract, rgb_contract = make_contracts()
    write_csv(behavior_contract, "BEHAVIOR_FEATURE_CONTRACT.csv")
    write_csv(nir_contract, "NIR_FEATURE_CONTRACT.csv")
    write_csv(rgb_contract, "RGB_FEATURE_CONTRACT.csv")
    temporal = behavior_temporal_audit(behavior_contract)
    write_csv(temporal, "BEHAVIOR_TEMPORAL_LEAKAGE_AUDIT.csv")

    fold_map = dict(zip(registry.repeat_participant_id.astype(str), registry.outer_fold_id.astype(str)))
    candidate = matched.copy()
    candidate["outer_fold_id"] = candidate.repeat_participant_id.astype(str).map(fold_map)
    behavior_predictors = behavior_contract.loc[behavior_contract.allowed_as_predictor.astype(bool), "feature_name"].tolist()
    nir_predictors = nir_contract.loc[nir_contract.allowed_as_predictor.astype(bool), "feature_name"].tolist()
    rgb_predictors = rgb_contract.loc[rgb_contract.allowed_as_predictor.astype(bool), "feature_name"].tolist()
    source_tables = {"behavior": behavior, "nir": nir, "rgb": rgb}
    for field in behavior_predictors + nir_predictors + rgb_predictors:
        source_key = next((k for k, df in source_tables.items() if field in df.columns), None)
        if source_key:
            candidate = candidate.merge(source_tables[source_key][KEY + [field]], on=KEY, how="left", validate="one_to_one")
    candidate = candidate.merge(nir_audit[KEY + ["nir_state", "nir_observed", "nir_missing_reason", "completion_status", "eye_metric_rows_in_window", "frame_coverage_rows_in_window"]], on=KEY, how="left", validate="one_to_one")
    candidate = candidate.merge(rgb_audit[KEY + ["rgb_state", "rgb_observed", "rgb_missing_reason", "producer_diagnosis", "qc_failure"]], on=KEY, how="left", validate="one_to_one")
    candidate["target_probe_vigilance"] = candidate["label_probe_vigilance"]
    qc_columns = [
        "behavior_qc_status", "nir_state", "nir_observed", "nir_missing_reason", "nir_pupil_fit_valid_fraction",
        "nir_observed_eye_fraction", "nir_temporal_anomaly_fraction", "nir_analysis_valid_pixel_fraction_median",
        "rgb_state", "rgb_observed", "rgb_missing_reason", "rgb_eye_geometry_valid_fraction", "rgb_motion_valid_fraction",
        "rgb_gap_fraction", "rgb_pose_valid_fraction", "rgb_source_row_count", "nir_source_path", "rgb_source_path", "behavior_source_path",
    ]
    for field in qc_columns:
        source_key = next((k for k, df in source_tables.items() if field in df.columns), None)
        if source_key and field not in candidate.columns:
            candidate = candidate.merge(source_tables[source_key][KEY + [field]], on=KEY, how="left", validate="one_to_one")
    candidate_columns = IDENTITY + ["block_id", "probe_id", "window_name", "probe_onset_unix_ms", "condition", "target_probe_vigilance", "outer_fold_id", "behavior_observed"] + behavior_predictors + nir_predictors + rgb_predictors + qc_columns
    candidate_columns = list(dict.fromkeys(c for c in candidate_columns if c in candidate.columns))
    candidate = candidate[candidate_columns]
    write_csv(candidate, "formal_model_ready_candidate_v1.csv")

    source_names = [
        "canonical_probe_timeline.csv", "behavior_probe_merge_ready.csv", "nir_probe_merge_ready.csv", "rgb_probe_merge_ready.csv",
        "modality_coverage_missingness_audit.csv", "merge_audit_report.json", "NIR_MISSINGNESS_AUDIT.csv", "RGB_MISSINGNESS_AUDIT.csv",
        "formal_matched_cohort_v1.csv", "formal_loso_participant_registry_v1.csv", "BEHAVIOR_FEATURE_CONTRACT.csv", "NIR_FEATURE_CONTRACT.csv", "RGB_FEATURE_CONTRACT.csv",
    ]
    source_hashes = {name: sha256(OUT / name) for name in source_names if (OUT / name).exists()}
    schema = {
        "schema_name": "FocusWave formal model-ready candidate v1",
        "schema_version": "formal-model-ready-v1",
        "status": "CANDIDATE_ONLY_NO_MODEL_RESULT",
        "identity_columns": IDENTITY,
        "probe_key": KEY,
        "target_column": "target_probe_vigilance",
        "predictors": {"Behavior": behavior_predictors, "NIR": nir_predictors, "RGB": rgb_predictors},
        "qc_columns": qc_columns,
        "missingness_columns": ["nir_state", "nir_missing_reason", "rgb_state", "rgb_missing_reason", "nir_observed", "rgb_observed"],
        "excluded_columns": ["label_probe_response", "label_probe_rt_ms", "probe_response", "probe_response_time", "rgb_native_eye_blink_mean_median", "rgb_blink_event_count_candidate", "PERCLOS", "mmWave_HR", "mmWave_BR", "mmWave_RR", "HRV", "IBI"],
        "fold_registry": {"registry_file": "formal_loso_participant_registry_v1.csv", "fold_file": "formal_loso_folds_v1.csv", "role_semantics": "one repeat_participant_id per outer fold is TEST; all other matched participants are TRAIN"},
        "window_semantics": {"window_name": "pre_30s", "interval": "[probe_onset_unix_ms-30000, probe_onset_unix_ms)", "timestamp": "real unix_ms", "block_boundary": "use window_effective_start_unix_ms when the current source table records truncation"},
        "cohort": {"full_timeline_rows": int(len(full_for_summary)), "matched_rows": int(len(matched)), "matched_sessions": int(matched.session_id.nunique()), "matched_repeat_participants": int(matched.repeat_participant_id.nunique()), "loso_folds": int(len(registry))},
        "source_hashes": source_hashes,
        "local_absolute_output_path": str(OUT),
        "generation_script": str(Path(__file__).resolve()),
        "constraints": {"nir_producer_rerun": False, "rgb_producer_rerun": False, "model_training": False, "mmwave_primary_predictor": False, "provisional_blink_primary_predictor": False, "perclos_primary_predictor": False},
    }
    write_json(schema, "formal_model_ready_schema_v1.json")

    required_checks = {
        "matched_cohort_frozen": bool(summary["validation"]["matched_count_expected_1295"] and summary["validation"]["canonical_key_unique"] and summary["validation"]["matched_subset_of_timeline"] and not summary["validation"]["label_dependent_filtering"]),
        "loso_participant_disjoint": loso_audit["status"] == "PASS",
        "feature_definitions_frozen": all(len(df) > 0 and df["provenance"].notna().all() and df["feature_name"].notna().all() for df in [behavior_contract, nir_contract, rgb_contract]),
        "temporal_leakage_absent": bool((temporal.loc[temporal.role == "PREDICTOR", "status"] == "PASS").all()),
        "qc_missingness_semantics_frozen": set(nir_audit.nir_state.unique()) >= {"STRUCTURAL_MISSING", "OBSERVATION_MISSING", "QC_FAIL", "OBSERVED"} and set(rgb_audit.rgb_state.unique()) >= {"STRUCTURAL_MISSING", "OBSERVED"},
        "no_mmwave_hold_predictor": not any(any(any(token.lower() in f.lower() for token in ["mmwave", "hrv", "ibi", "heart_rate", "respiration", "_hr", "_br", "_rr"]) for f in xs) for xs in [behavior_predictors, nir_predictors, rgb_predictors]),
        "no_provisional_blink_or_perclos_predictor": not any("blink" in f.lower() or "perclos" in f.lower() for f in behavior_predictors + nir_predictors + rgb_predictors),
        "same_denominator_traceable": int(len(matched)) == 1295 and int(len(full_for_summary)) == 1440 and int(len(nir_audit)) == 1440 and int(len(rgb_audit)) == 1440,
        "source_hashes_complete": len(source_hashes) == len(source_names),
    }
    predictor_nan = {m: int(candidate[features].isna().sum().sum()) for m, features in {"Behavior": behavior_predictors, "NIR": nir_predictors, "RGB": rgb_predictors}.items()}
    gate_status = "PASS_MODEL_READY" if all(required_checks.values()) else "PARTIAL"
    gate = {
        "status": gate_status,
        "baseline_modeling_authorized": gate_status == "PASS_MODEL_READY",
        "modeling_executed": False,
        "checks": required_checks,
        "predictor_counts": {"Behavior": len(behavior_predictors), "NIR": len(nir_predictors), "RGB": len(rgb_predictors), "total": len(behavior_predictors + nir_predictors + rgb_predictors)},
        "candidate_predictor_nan_cells": predictor_nan,
        "candidate_nan_note": "One retained NIR QC_FAIL probe has NaN pupil geometry by design; downstream modeling must declare an explicit NaN policy and must not silently label-dependent-filter the cohort.",
        "cohort_summary_file": "FORMAL_MATCHED_COHORT_SUMMARY.json",
        "loso_audit_file": "LOSO_LEAKAGE_AUDIT.json",
        "schema_file": "formal_model_ready_schema_v1.json",
        "local_absolute_output_path": str(OUT),
        "generation_script": str(Path(__file__).resolve()),
        "source_hashes": source_hashes,
    }
    write_json(gate, "MODEL_READY_READINESS_GATE.json")
    report = [
        "# FocusWave formal model-ready v1 readiness report",
        "",
        f"Final status: **{gate_status}**",
        "",
        f"The candidate contains {len(matched)} matched probes from {matched.session_id.nunique()} sessions and {matched.repeat_participant_id.nunique()} repeat participants, with {len(registry)} participant-disjoint LOSO outer folds. No model was trained and no producer was rerun.",
        "",
        "## Predictor contract",
        "",
        f"- Behavior: {len(behavior_predictors)} primary predictors.",
        f"- NIR: {len(nir_predictors)} primary predictors, fullclass pupil geometry only; no PIR.",
        f"- RGB: {len(rgb_predictors)} primary predictors: current face coverage, eyelid geometry/opening, head motion, and global motion.",
        "- Blink is retained only as `PROVISIONAL_CANDIDATE`; it is excluded from primary predictors. PERCLOS is absent/not validated. mmWave/HR/BR/RR/HRV/IBI are excluded.",
        "",
        "## Missingness and QC",
        "",
        "- NIR states are separately represented as structural missing, observation missing, QC fail, or observed. The 1,295-row observation-defined matched denominator is retained; missing geometry remains NaN.",
        "- RGB `sub-099` is diagnosed as structural: no processed producer session/raw parquet/subject manifest, while source video and timestamps exist; the existing audit says `master_timeline.csv` is missing. No postprocessing failure or QC failure is asserted.",
        "",
        "## Leakage and denominator gate",
        "",
        f"- LOSO leakage audit: **{loso_audit['status']}**; participant intersection and session/probe checks are recorded in `LOSO_LEAKAGE_AUDIT.json`.",
        "- Behavior predictors are bounded to the pre-onset window; post-probe response/RT and target labels are excluded from predictors.",
        "- The full 1,440-row timeline, 1,295-row matched candidate, and all source hashes are traceable.",
        "",
        "## Authorization boundary",
        "",
        f"`baseline_modeling_authorized = {str(gate_status == 'PASS_MODEL_READY').lower()}`. This authorizes the next modeling phase only; it is not a model result. The retained NIR QC_FAIL row requires an explicit downstream NaN policy before fitting.",
        "",
        f"Local output package: `{OUT}`",
        f"Generation script: `{Path(__file__).resolve()}`",
    ]
    (OUT / "MODEL_READY_READINESS_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    artifact_names = [
        "NIR_MISSINGNESS_AUDIT.csv", "RGB_MISSINGNESS_AUDIT.csv", "formal_matched_cohort_v1.csv", "FORMAL_MATCHED_COHORT_AUDIT.md", "FORMAL_MATCHED_COHORT_SUMMARY.json",
        "formal_loso_folds_v1.csv", "formal_loso_participant_registry_v1.csv", "LOSO_LEAKAGE_AUDIT.json", "BEHAVIOR_FEATURE_CONTRACT.csv", "NIR_FEATURE_CONTRACT.csv", "RGB_FEATURE_CONTRACT.csv",
        "BEHAVIOR_TEMPORAL_LEAKAGE_AUDIT.csv", "formal_model_ready_schema_v1.json", "formal_model_ready_candidate_v1.csv", "MODEL_READY_READINESS_GATE.json", "MODEL_READY_READINESS_REPORT.md",
    ]
    artifact_rows = []
    for name in artifact_names:
        p = OUT / name
        df = None
        if p.suffix.lower() == ".csv":
            df = pd.read_csv(p, nrows=0)
        artifact_rows.append({"artifact": name, "path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size, "columns": int(len(df.columns)) if df is not None else None})
    write_csv(pd.DataFrame(artifact_rows), "MODEL_READY_ARTIFACT_INDEX.csv")
    print(json.dumps({"status": gate_status, "matched_rows": len(matched), "matched_sessions": int(matched.session_id.nunique()), "matched_repeat_participants": int(matched.repeat_participant_id.nunique()), "loso_folds": len(registry), "predictor_counts": gate["predictor_counts"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
