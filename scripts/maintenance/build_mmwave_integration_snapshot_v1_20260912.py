"""Package the corrected DLL-time mmWave replay as integration snapshot v1.

This is an interface packager, not a physiological estimator.  It reads the
immutable J/E replay tables, attaches the governed participant identity, writes
one versioned local-only probe table, and runs a bounded Task-B/materialization
smoke against the current Attention-Analysis implementation.  It never changes
target selection, peak selection, fusion, window length, or HRV fields.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SNAPSHOT_VERSION = "mmwave_integration_snapshot_v1"
PRODUCER_REPOSITORY = "https://github.com/greenboo26/focuswave-multimodal-attention-analysis.git"
PRODUCER_COMMIT = "16729b2ef245f9304dae8674f3bac433bc02e98c"
PRODUCER_PATH = "scripts/process_vital_signs_v3_1_1.py"
ADAPTER_PATH = "scripts/maintenance/run_mmwave_probe_merge_ready_20260831.py"
COHORT_RUNNER_PATH = "scripts/maintenance/mmwave_frozen_cohort.py"
PRODUCER_HASH = "bc65c2d2c99ebdfedea2500579caeb45cb8918466cf788ade718806bdd351fda"
ADAPTER_HASH = "434f0c60234f6ae9c319e0f20f151cc1b0794b0be65645e8e5df372a0ae575e9"
COHORT_RUNNER_HASH = "035825eb44888a2dda36835c8094201bbf93affb0248ea39a2741051f785814a"
RUN_ID = "mmwave_integration_snapshot_v1_20260912_r4"
KEYS = ["participant_group_id", "session_id", "block_id", "probe_index_in_block"]
FIVE_KEYS = ["repeat_participant_id", "session_id", "source_block_id", "probe_id", "window_name"]
HR = "mmwave_hr_fused_bpm_median"
BR = "mmwave_breath_rate_breaths_per_min_median"
HRV_FIELDS = ["mmwave_ibi_median_ms", "mmwave_rmssd_ms", "mmwave_sdnn_ms"]
SMOKE_SESSIONS = ["sub-031", "sub-047", "sub-099"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strict_bool(series: pd.Series, name: str) -> pd.Series:
    text = series.astype("string").str.strip().str.lower()
    mapping = {"true": True, "1": True, "1.0": True, "yes": True,
               "false": False, "0": False, "0.0": False, "no": False}
    invalid = series.isna() | ~text.isin(mapping)
    if invalid.any():
        raise ValueError(f"{name}: invalid boolean rows={int(invalid.sum())}")
    return text.map(mapping).astype(bool)


def normalize_block(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.lower().str.replace("-", "", regex=False)
    text = text.str.replace("block", "", regex=False)
    numeric = pd.to_numeric(text.str.replace("b", "", regex=False), errors="coerce")
    if numeric.isna().any() or not numeric.isin([1, 2]).all():
        raise ValueError("block_id contains values outside formal b1/b2")
    return "b" + numeric.astype(int).astype(str)


def numeric_column(frame: pd.DataFrame, name: str, *, integer: bool = False) -> pd.Series:
    source = frame[name]
    blank = source.isna() | source.astype("string").str.strip().eq("")
    value = pd.to_numeric(source, errors="coerce")
    malformed = ~blank & value.isna()
    nonfinite = value.notna() & ~np.isfinite(value)
    if malformed.any() or nonfinite.any():
        raise ValueError(
            f"{name}: malformed={int(malformed.sum())}, nonfinite={int(nonfinite.sum())}"
        )
    if integer:
        noninteger = value.notna() & ~np.isclose(value, np.round(value), rtol=0.0, atol=0.0)
        if noninteger.any():
            raise ValueError(f"{name}: non-integer rows={int(noninteger.sum())}")
        return value.round().astype("Int64")
    return value.astype("Float64")


def classify_state(frame: pd.DataFrame) -> pd.DataFrame:
    observed = strict_bool(frame["mmwave_observed"], "mmwave_observed")
    loadable = strict_bool(frame["mmwave_loadable"], "mmwave_loadable")
    reason = frame["mmwave_missing_reason"].fillna("").astype(str)
    malformed = reason.str.startswith("ValueError:")
    absent = reason.str.startswith("FileNotFoundError:")

    out = pd.DataFrame(index=frame.index)
    out["source_availability_state"] = np.select(
        [observed, malformed, absent], ["PRESENT", "PRESENT", "ABSENT"], default="UNRESOLVED"
    )
    out["source_readability_state"] = np.select(
        [loadable, malformed, absent], ["READABLE", "UNREADABLE", "NOT_APPLICABLE"], default="UNRESOLVED"
    )
    out["estimability_state"] = np.where(
        observed & loadable & frame["mmwave_state"].eq("OBSERVED"), "ESTIMABLE", "NOT_ESTIMABLE"
    )
    out["measurement_qc_state"] = np.where(
        out["estimability_state"].eq("ESTIMABLE"), "PASS", "NOT_ASSESSED"
    )
    out["malformed_state"] = np.where(malformed, "MALFORMED", "NOT_MALFORMED")
    out["integration_state"] = np.select(
        [out["estimability_state"].eq("ESTIMABLE"), absent, malformed],
        ["AVAILABLE", "SOURCE_UNAVAILABLE", "SOURCE_MALFORMED"],
        default="UNRESOLVED",
    )
    return out


def field_role_rows() -> list[dict[str, Any]]:
    roles: dict[str, tuple[str, str, str]] = {
        "participant_group_id": ("identity", "canonical statistical participant identity", "id"),
        "repeat_participant_id": ("identity", "legacy/source participant identity", "id"),
        "session_id": ("identity", "acquisition session identity", "id"),
        "block_id": ("identity", "normalized formal block identity", "id"),
        "probe_index_in_block": ("identity", "probe ordinal within block", "index"),
        "probe_id": ("identity", "source probe identifier", "id"),
        "window_name": ("time", "formal window name", "name"),
        "window_nominal_start_unix_ms": ("time", "probe onset minus 30 seconds", "ms"),
        "window_effective_start_unix_ms": ("time", "nominal start truncated at formal block start when required", "ms"),
        "window_end_unix_ms": ("time", "right-exclusive probe onset", "ms"),
        "probe_onset_unix_ms": ("time", "formal probe onset", "ms"),
        "alignment_clock_source": ("provenance", "DLL host receive/enqueue timestamp", "name"),
        HR: ("scientific", "radar-derived heart-rate estimate; current formal fused representation", "bpm"),
        BR: ("scientific", "radar-derived respiration-rate estimate", "breaths_per_min"),
        "mmwave_timestamp_coverage_fraction": ("qc", "authoritative timestamp coverage", "fraction"),
        "mmwave_hr_mean_confidence": ("qc", "producer confidence summary; not physiological validity", "score"),
        "mmwave_hr_usable_window_fraction": ("qc", "legacy adapter availability-like field; not a scientific predictor", "fraction"),
        "mmwave_phase_stability_median": ("qc", "phase stability diagnostic", "score"),
        "mmwave_motion_proxy_median": ("diagnostic", "radar motion-like QC proxy; no current movement-feature qualification", "score"),
        "mmwave_hr_freq_bpm_median": ("diagnostic", "frequency-domain HR representation", "bpm"),
        "mmwave_hr_time_bpm_median": ("diagnostic", "time-domain HR representation", "bpm"),
        "mmwave_selected_bin_mode": ("diagnostic", "selected range-bin mode", "bin"),
        "mmwave_selected_channel_mode": ("diagnostic", "selected channel mode", "channel"),
        "mmwave_selected_bin_distance_proxy_m": ("diagnostic", "range-bin distance proxy; not measured chest distance", "m"),
        "mmwave_target_switch_rate": ("diagnostic", "target-switch metric when available", "fraction"),
        "source_availability_state": ("state", "source presence classification", "enum"),
        "source_readability_state": ("state", "source readability classification", "enum"),
        "estimability_state": ("state", "feature estimability classification", "enum"),
        "measurement_qc_state": ("state", "measurement QC state separate from source state", "enum"),
        "malformed_state": ("state", "malformed/error state separate from missingness", "enum"),
        "integration_state": ("state", "normalized integration availability state", "enum"),
        "producer_state": ("state", "unaltered producer/adapter row state", "enum"),
        "missing_reason": ("state", "unaltered failure reason", "reason"),
        "snapshot_version": ("provenance", "versioned replaceable interface identity", "version"),
        "producer_commit": ("provenance", "exact producer source commit", "git_sha"),
        "producer_adapter_version": ("provenance", "producer adapter pipeline version", "version"),
        "source_run_id": ("provenance", "source replay run identifier", "id"),
        "snapshot_run_id": ("provenance", "integration packaging run identifier", "id"),
        "mmwave_ibi_median_ms": ("prohibited", "radar inter-beat interval; blocked", "ms"),
        "mmwave_rmssd_ms": ("prohibited", "HRV RMSSD; blocked", "ms"),
        "mmwave_sdnn_ms": ("prohibited", "HRV SDNN; blocked", "ms"),
        "LF": ("prohibited", "HRV low-frequency power; not present", "unknown"),
        "HF": ("prohibited", "HRV high-frequency power; not present", "unknown"),
        "LF_HF": ("prohibited", "HRV LF/HF ratio; not present", "ratio"),
    }
    return [
        {"field": field, "role": role, "meaning": meaning, "unit": unit,
         "first_round_scientific_predictor": role == "scientific"}
        for field, (role, meaning, unit) in roles.items()
    ]


def registry_rows() -> list[dict[str, Any]]:
    common = {
        "raw_source": "post-Range-FFT complex ReportDataCube1D via current corrected producer",
        "required_devices": json.dumps(["mmwave"]),
        "preprocessing_dependencies": "DLL-time frame slicing; current selector/estimator contract",
        "snapshot_version": SNAPSHOT_VERSION,
    }
    return [
        {
            **common,
            "feature_id": "mmwave_hr_fused_v1",
            "scientific_feature_id": "radar_derived_heart_rate",
            "modality": "cardiopulmonary",
            "feature_type": "heart_rate",
            "predictor_column": HR,
            "scientific_meaning": "radar-derived heart-rate estimate",
            "unit": "bpm",
            "qc_dependency": "source readable; producer state OBSERVED",
            "estimability_rule": "finite fused HR under corrected DLL-time window",
            "standalone_eligibility": True,
            "behavior_increment_eligibility": True,
            "full_eligibility": True,
            "current_qualification_status": "PROVISIONAL_PHYSIOLOGY_LIMITED",
            "freeze_provisional_rationale": "interface frozen; current fused representation retained; physiology not fully validated",
        },
        {
            **common,
            "feature_id": "mmwave_br_v1",
            "scientific_feature_id": "radar_derived_respiration_rate",
            "modality": "cardiopulmonary",
            "feature_type": "respiration_rate",
            "predictor_column": BR,
            "scientific_meaning": "radar-derived respiration-rate estimate",
            "unit": "breaths_per_min",
            "qc_dependency": "source readable; producer state OBSERVED",
            "estimability_rule": "finite BR under corrected DLL-time window",
            "standalone_eligibility": True,
            "behavior_increment_eligibility": True,
            "full_eligibility": True,
            "current_qualification_status": "PROVISIONAL_PHYSIOLOGY_LIMITED",
            "freeze_provisional_rationale": "interface frozen; physiology not fully validated",
        },
        {
            **common,
            "feature_id": "mmwave_motion_proxy_v1",
            "scientific_feature_id": "radar_motion_proxy",
            "modality": "movement",
            "feature_type": "motion_proxy",
            "predictor_column": "mmwave_motion_proxy_median",
            "scientific_meaning": "radar motion-like proxy; scientific movement meaning not frozen",
            "unit": "score",
            "qc_dependency": "producer diagnostic availability",
            "estimability_rule": "finite producer diagnostic only",
            "standalone_eligibility": False,
            "behavior_increment_eligibility": False,
            "full_eligibility": False,
            "current_qualification_status": "DIAGNOSTIC_ONLY_NOT_MOVEMENT_QUALIFIED",
            "freeze_provisional_rationale": "current contract classifies field as signal diagnostic; no upgrade by integration task",
        },
    ]


def build_schema(columns: list[str]) -> dict[str, Any]:
    integer = {"probe_index_in_block", "window_nominal_start_unix_ms",
               "window_effective_start_unix_ms", "window_end_unix_ms", "probe_onset_unix_ms",
               "mmwave_selected_bin_mode", "mmwave_selected_channel_mode"}
    numeric = {HR, BR, "mmwave_timestamp_coverage_fraction", "mmwave_hr_mean_confidence",
               "mmwave_hr_usable_window_fraction", "mmwave_phase_stability_median",
               "mmwave_motion_proxy_median", "mmwave_hr_freq_bpm_median",
               "mmwave_hr_time_bpm_median", "mmwave_selected_bin_distance_proxy_m",
               "mmwave_target_switch_rate"}
    properties: dict[str, Any] = {}
    for column in columns:
        if column in integer:
            properties[column] = {"type": ["integer", "null"]}
        elif column in numeric:
            properties[column] = {"type": ["number", "null"]}
        else:
            properties[column] = {"type": ["string", "null"]}
    for column in KEYS + ["repeat_participant_id", "probe_id", "window_name",
                          "alignment_clock_source", "snapshot_version", "producer_commit"]:
        properties[column] = {"type": "string", "minLength": 1}
    properties["probe_index_in_block"] = {"type": "integer", "minimum": 1}
    properties["window_name"] = {"const": "pre_30s"}
    properties["alignment_clock_source"] = {"const": "dll_host_receive_enqueue"}
    properties["snapshot_version"] = {"const": SNAPSHOT_VERSION}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "focuswave:mmwave_integration_snapshot_v1",
        "title": "FocusWave mmWave integration snapshot v1 probe row",
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--j-table", type=Path, required=True)
    parser.add_argument("--e-table", type=Path, required=True)
    parser.add_argument("--identity-bridge", type=Path, required=True)
    parser.add_argument("--behavior-table", type=Path, required=True)
    parser.add_argument("--frozen-baseline", type=Path, required=True)
    parser.add_argument("--attention-repo", type=Path, required=True)
    parser.add_argument("--local-output-dir", type=Path, required=True)
    parser.add_argument("--tracked-output-dir", type=Path, required=True)
    args = parser.parse_args()

    # The inspected Attention-Analysis revision passes pandas BooleanArray
    # conditions directly to numpy.select.  Python-backed nullable strings are
    # accepted there; Arrow-backed strings raise before the interface audit can
    # run.  Set this before any CSV is read so derived string/boolean arrays use
    # the compatible representation.  Measurement and eligibility values are
    # unchanged.
    pd.options.mode.string_storage = "python"

    if args.local_output_dir.exists():
        raise FileExistsError(f"exclusive local output already exists: {args.local_output_dir}")
    args.local_output_dir.mkdir(parents=True)
    args.tracked_output_dir.mkdir(parents=True, exist_ok=True)

    j = pd.read_csv(args.j_table, dtype=str, keep_default_na=False)
    e = pd.read_csv(args.e_table, dtype=str, keep_default_na=False)
    source = pd.concat([j.assign(source_batch="J72"), e.assign(source_batch="E44")], ignore_index=True)
    source["source_block_id"] = source["block_id"]
    source["block_id"] = normalize_block(source["block_id"])
    source["probe_index_in_block"] = numeric_column(source, "probe_index_in_block", integer=True)

    bridge = pd.read_csv(args.identity_bridge, dtype=str, keep_default_na=False)
    required_bridge = {"session_id", "repeat_participant_id", "participant_group_id", "include", "identity_status"}
    if not required_bridge <= set(bridge):
        raise ValueError(f"identity bridge missing {sorted(required_bridge - set(bridge))}")
    if bridge["session_id"].duplicated().any():
        raise ValueError("identity bridge has duplicate session_id")
    bridge = bridge[strict_bool(bridge["include"], "identity bridge include")].copy()
    source = source.merge(
        bridge[["session_id", "repeat_participant_id", "participant_group_id", "identity_status"]],
        on=["session_id", "repeat_participant_id"], how="left", validate="many_to_one"
    )
    if source[["participant_group_id", "identity_status"]].isna().any().any():
        raise ValueError("snapshot rows lack governed participant identity")
    if not source["identity_status"].eq("verified").all():
        raise ValueError("snapshot includes non-verified participant identity")

    source["window_nominal_start_unix_ms"] = numeric_column(source, "window_start_unix_ms", integer=True)
    for column in ["window_effective_start_unix_ms", "window_end_unix_ms", "probe_onset_unix_ms"]:
        source[column] = numeric_column(source, column, integer=True)
    if not source["window_end_unix_ms"].eq(source["probe_onset_unix_ms"]).all():
        raise ValueError("window end is not the right-exclusive probe onset")
    if not source["window_nominal_start_unix_ms"].add(30000).eq(source["window_end_unix_ms"]).all():
        raise ValueError("nominal window is not 30 seconds")
    if not source["window_effective_start_unix_ms"].ge(source["window_nominal_start_unix_ms"]).all():
        raise ValueError("effective window starts before nominal window")
    if not source["window_effective_start_unix_ms"].lt(source["window_end_unix_ms"]).all():
        raise ValueError("effective window is empty or reversed")

    numeric = [HR, BR, "mmwave_timestamp_coverage_fraction", "mmwave_hr_mean_confidence",
               "mmwave_hr_usable_window_fraction", "mmwave_phase_stability_median",
               "mmwave_motion_proxy_median", "mmwave_hr_freq_bpm_median",
               "mmwave_hr_time_bpm_median", "mmwave_selected_bin_distance_proxy_m",
               "mmwave_target_switch_rate"]
    integer_optional = ["mmwave_selected_bin_mode", "mmwave_selected_channel_mode"]
    for column in numeric:
        source[column] = numeric_column(source, column)
    for column in integer_optional:
        source[column] = numeric_column(source, column, integer=True)
    if source[HRV_FIELDS].replace("", pd.NA).notna().any().any():
        raise ValueError("prohibited HRV/IBI field contains a value")

    states = classify_state(source)
    source = pd.concat([source, states], axis=1)
    estimable = source["estimability_state"].eq("ESTIMABLE")
    if source.loc[estimable, [HR, BR]].isna().any().any():
        raise ValueError("estimable row lacks HR or BR")
    if source.loc[~estimable, [HR, BR]].notna().any().any():
        raise ValueError("non-estimable row contains HR or BR")

    snapshot_columns = [
        "participant_group_id", "repeat_participant_id", "session_id", "block_id",
        "source_block_id", "probe_index_in_block", "probe_id", "window_name",
        "window_nominal_start_unix_ms", "window_effective_start_unix_ms",
        "window_end_unix_ms", "probe_onset_unix_ms", "alignment_clock_source",
        HR, BR, "mmwave_timestamp_coverage_fraction", "mmwave_hr_mean_confidence",
        "mmwave_hr_usable_window_fraction", "mmwave_phase_stability_median",
        "mmwave_motion_proxy_median", "mmwave_hr_freq_bpm_median", "mmwave_hr_time_bpm_median",
        "mmwave_selected_bin_mode", "mmwave_selected_channel_mode",
        "mmwave_selected_bin_distance_proxy_m", "mmwave_target_switch_rate",
        "source_availability_state", "source_readability_state", "estimability_state",
        "measurement_qc_state", "malformed_state", "integration_state", "producer_state",
        "missing_reason", "snapshot_version", "producer_commit", "producer_adapter_version",
        "source_run_id", "snapshot_run_id",
    ]
    source["alignment_clock_source"] = "dll_host_receive_enqueue"
    source["producer_state"] = source["mmwave_state"]
    source["missing_reason"] = source["mmwave_missing_reason"].replace("", pd.NA)
    source["snapshot_version"] = SNAPSHOT_VERSION
    source["producer_commit"] = PRODUCER_COMMIT
    source["producer_adapter_version"] = "issue34-dll-cutover-v1"
    source["source_run_id"] = source["mmwave_source_run_id"]
    source["snapshot_run_id"] = RUN_ID
    snapshot = source[snapshot_columns].copy()
    snapshot = snapshot.sort_values(KEYS, kind="stable").reset_index(drop=True)

    duplicate_count = int(snapshot.duplicated(FIVE_KEYS).sum())
    if duplicate_count:
        raise ValueError(f"duplicate five-key rows={duplicate_count}")
    expected_keys = set(map(tuple, source[FIVE_KEYS].astype(str).itertuples(index=False, name=None)))
    observed_keys = set(map(tuple, snapshot[FIVE_KEYS].astype(str).itertuples(index=False, name=None)))
    missing_keys = sorted(expected_keys - observed_keys)
    extra_keys = sorted(observed_keys - expected_keys)
    if missing_keys or extra_keys:
        raise ValueError(f"key mismatch missing={len(missing_keys)} extra={len(extra_keys)}")

    local_snapshot = args.local_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_PROBES_LOCAL_ONLY.csv"
    snapshot.to_csv(local_snapshot, index=False, encoding="utf-8-sig")

    behavior = pd.read_csv(args.behavior_table, low_memory=False)
    behavior = behavior[behavior["session_id"].isin(SMOKE_SESSIONS)].copy()
    behavior["block_id"] = normalize_block(behavior["block_id"])
    behavior["probe_index_in_block"] = pd.to_numeric(behavior["probe_order_in_block"], errors="raise").astype(int)
    behavior["window_name"] = "pre_30s"
    smoke = snapshot[snapshot["session_id"].isin(SMOKE_SESSIONS)].copy()
    if len(behavior) != 60 or len(smoke) != 60:
        raise ValueError(f"smoke requires 60 behavior/snapshot rows, got {len(behavior)}/{len(smoke)}")

    smoke_source = smoke.copy()
    smoke_source["source_present"] = smoke_source["source_availability_state"].eq("PRESENT")
    smoke_source["source_readable"] = smoke_source["source_readability_state"].eq("READABLE")
    smoke_source["native_qc_valid"] = smoke_source["measurement_qc_state"].eq("PASS")
    smoke_source["window_start_unix_ms"] = smoke_source["window_nominal_start_unix_ms"]
    smoke_source["block_start_unix_ms"] = smoke_source["window_effective_start_unix_ms"]
    smoke_source["block_end_unix_ms"] = smoke_source["window_end_unix_ms"]
    # Avoid pandas nullable Float64 propagating a nullable BooleanArray through
    # numpy.isfinite inside the current quality audit implementation.
    smoke_source[[HR, BR]] = smoke_source[[HR, BR]].astype("float64")
    behavior["raw_go_omission_rate"] = behavior["raw_go_omission_rate"].astype("float64")

    sys.path.insert(0, str(args.attention_repo / "src"))
    from attention_pipeline.multimodal_formal.analysis_sets import build_analysis_sets
    from attention_pipeline.multimodal_formal.quality_admission import audit_quality
    from attention_pipeline.multimodal_formal.supervised_input import materialize_supervised_input

    feature_blocks = {
        "behavior": ["raw_go_omission_rate"],
        "cardiopulmonary": [HR, BR],
    }
    audit = audit_quality(
        {"behavior": behavior, "cardiopulmonary": smoke_source}, feature_blocks
    )
    specs = {
        "cardiopulmonary_only_snapshot_v1": {
            "models": ["cardiopulmonary_snapshot_v1"],
            "required_features": {"cardiopulmonary": [HR, BR]},
            "required_outcomes": ["q1_nominal_4class"],
        },
        "behavior_vs_behavior_plus_cardiopulmonary_snapshot_v1": {
            "models": ["behavior_reference_smoke", "behavior_plus_cardiopulmonary_snapshot_v1"],
            "required_features": {
                "behavior": ["raw_go_omission_rate"],
                "cardiopulmonary": [HR, BR],
            },
            "required_outcomes": ["q1_nominal_4class"],
        },
    }
    analysis_sets, analysis_summary = build_analysis_sets(
        audit["formal_probe_identity"], audit["probe_feature_status"], specs
    )
    materialized = {}
    for set_id in specs:
        materialized[set_id] = materialize_supervised_input(
            analysis_sets,
            audit["probe_feature_status"],
            analysis_set_id=set_id,
            membership_type="included_complete",
            probe_metadata=behavior,
        )

    local_analysis = args.local_output_dir / "SCHEMA_SMOKE_TASK_B_ANALYSIS_SETS_LOCAL_ONLY.csv"
    local_status = args.local_output_dir / "SCHEMA_SMOKE_PROBE_FEATURE_STATUS_LOCAL_ONLY.csv"
    local_materialized = args.local_output_dir / "SCHEMA_SMOKE_TASK_A_MATERIALIZED_LOCAL_ONLY.csv"
    analysis_sets.to_csv(local_analysis, index=False, encoding="utf-8-sig")
    audit["probe_feature_status"].to_csv(local_status, index=False, encoding="utf-8-sig")
    materialized["behavior_vs_behavior_plus_cardiopulmonary_snapshot_v1"].to_csv(
        local_materialized, index=False, encoding="utf-8-sig"
    )

    required_json = {
        row.analysis_set_id: json.loads(row.required_features)
        for row in analysis_sets.drop_duplicates("analysis_set_id").itertuples(index=False)
    }
    if any("mmwave" in mapping for mapping in required_json.values()):
        raise ValueError("device name leaked into Task-B scientific modality mapping")
    if any(any(x in str(mapping) for x in ["nir", "rgb"]) for mapping in required_json.values()):
        raise ValueError("unrelated device/modality leaked into comparison-specific required_features")

    smoke_json = {
        "status": "PASS_INTERFACE_WITH_DOWNSTREAM_1_16_10_MIGRATION_PENDING",
        "attention_repository": "https://github.com/kyandi233-dev/Attention-Analysis.git",
        "attention_commit": "5c7c82c53fd06477b8eef3b3ffedb7c630ead1a5",
        "smoke_sessions": SMOKE_SESSIONS,
        "smoke_session_roles": {
            "sub-031": "available",
            "sub-047": "source_unavailable",
            "sub-099": "source_malformed_npz_timestamp_count_mismatch",
        },
        "input_probe_rows": 60,
        "input_duplicate_keys": int(smoke.duplicated(KEYS).sum()),
        "scientific_modalities_used": ["behavior", "cardiopulmonary"],
        "required_devices_for_cardiopulmonary": ["mmwave"],
        "required_features": required_json,
        "analysis_set_summary": analysis_summary.to_dict("records"),
        "materialized_rows": {key: int(len(value)) for key, value in materialized.items()},
        "materialized_duplicate_keys": {key: int(value.duplicated(KEYS).sum()) for key, value in materialized.items()},
        "materialized_columns": {key: value.columns.tolist() for key, value in materialized.items()},
        "hrv_columns_present": sorted(set(HRV_FIELDS) & set(local_materialized.name)),
        "models_trained": False,
        "task_b_interface": "PASS",
        "materialize_interface": "PASS",
        "task_a_schema_consumable": "PASS",
        "downstream_1_16_10_migration": "PENDING: RegisteredFeature.modality, PlannedModel.modalities, FeatureScheme modality/device split, comparison-plan and reporting",
        "local_only_outputs": [
            {"path": str(local_analysis), "rows": int(len(analysis_sets)), "sha256": sha256(local_analysis)},
            {"path": str(local_status), "rows": int(len(audit["probe_feature_status"])), "sha256": sha256(local_status)},
            {"path": str(local_materialized), "rows": int(len(materialized["behavior_vs_behavior_plus_cardiopulmonary_snapshot_v1"])), "sha256": sha256(local_materialized)},
        ],
    }
    smoke_json["hrv_columns_present"] = [c for c in materialized["behavior_vs_behavior_plus_cardiopulmonary_snapshot_v1"].columns if c in HRV_FIELDS]

    schema_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_SCHEMA.json"
    registry_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_FEATURE_REGISTRY_MAP.csv"
    role_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_FIELD_ROLE_MAP.csv"
    availability_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_AVAILABILITY_SUMMARY.csv"
    smoke_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_SCHEMA_SMOKE.json"
    error_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_ERROR_LOG.json"
    manifest_path = args.tracked_output_dir / "MMWAVE_INTEGRATION_SNAPSHOT_V1_MANIFEST.json"

    schema_path.write_text(json.dumps(build_schema(snapshot.columns.tolist()), indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(registry_rows()).to_csv(registry_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(field_role_rows()).to_csv(role_path, index=False, encoding="utf-8-sig")

    availability_rows = []
    for state, group in snapshot.groupby("integration_state", sort=True):
        availability_rows.append({
            "integration_state": state,
            "rows": int(len(group)),
            "sessions": int(group["session_id"].nunique()),
            "hr_finite": int(group[HR].notna().sum()),
            "br_finite": int(group[BR].notna().sum()),
        })
    availability_rows.append({
        "integration_state": "TOTAL",
        "rows": int(len(snapshot)),
        "sessions": int(snapshot["session_id"].nunique()),
        "hr_finite": int(snapshot[HR].notna().sum()),
        "br_finite": int(snapshot[BR].notna().sum()),
    })
    pd.DataFrame(availability_rows).to_csv(availability_path, index=False, encoding="utf-8-sig")
    smoke_path.write_text(json.dumps(smoke_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    error_path.write_text(json.dumps({
        "status": "PASS_WITH_RECORDED_LIMITATIONS",
        "errors": [],
        "problems": [
            {"id": "MMWAVE-V1-001", "status": "OPEN_EXTERNAL", "impact": "physiology limited", "detail": "Issue #35/#36 remain open; no algorithm or physiology freeze"},
            {"id": "MMWAVE-V1-002", "status": "DEFERRED", "impact": "no mmWave-derived movement scientific predictor", "detail": "motion proxy remains diagnostic-only"},
            {"id": "MMWAVE-V1-003", "status": "OPEN_EXTERNAL", "impact": "formal downstream model-plan migration pending", "detail": "Attention-Analysis 1.16.10 modality/device split not implemented at inspected commit"},
        ],
        "models_trained": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "task_id": "mmwave_integration_snapshot_v1_closure",
        "snapshot_version": SNAPSHOT_VERSION,
        "status": "PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reuse_gate": "PASS: reused corrected DLL-time replay and current Task-B/materialize implementation; no algorithm rerun",
        "source_repository": PRODUCER_REPOSITORY,
        "source_commit": PRODUCER_COMMIT,
        "producer": {"path": PRODUCER_PATH, "sha256": PRODUCER_HASH},
        "adapter": {"path": ADAPTER_PATH, "sha256": ADAPTER_HASH},
        "cohort_runner": {"path": COHORT_RUNNER_PATH, "sha256": COHORT_RUNNER_HASH},
        "input_manifest": {"path": str(args.frozen_baseline), "sha256": sha256(args.frozen_baseline)},
        "inputs": [
            {"path": str(args.j_table), "sha256": sha256(args.j_table), "rows": len(j), "sessions": int(j["session_id"].nunique())},
            {"path": str(args.e_table), "sha256": sha256(args.e_table), "rows": len(e), "sessions": int(e["session_id"].nunique())},
            {"path": str(args.identity_bridge), "sha256": sha256(args.identity_bridge), "rows": len(bridge)},
            {"path": str(args.behavior_table), "sha256": sha256(args.behavior_table), "role": "authoritative labels for schema smoke only"},
        ],
        "cohort": {"governed_sessions": 116, "participant_groups": int(snapshot["participant_group_id"].nunique()), "expected_probes": 2320},
        "availability": {
            "available_sessions": int(snapshot.loc[estimable, "session_id"].nunique()),
            "available_probes": int(estimable.sum()),
            "source_unavailable_probes": int(snapshot["integration_state"].eq("SOURCE_UNAVAILABLE").sum()),
            "source_malformed_probes": int(snapshot["integration_state"].eq("SOURCE_MALFORMED").sum()),
        },
        "key_contract": {
            "source_five_key": FIVE_KEYS,
            "task_b_key": KEYS,
            "expected_keys": len(expected_keys),
            "observed_keys": len(observed_keys),
            "duplicates": duplicate_count,
            "missing_keys": len(missing_keys),
            "extra_keys": len(extra_keys),
        },
        "time_contract": {
            "scientific_alignment_clock": "DLL host receive/enqueue timestamp column 1",
            "not_alignment_clock": "Python worker processing timestamp column 2",
            "window": "[window_effective_start_unix_ms, probe_onset_unix_ms)",
            "nominal_seconds": 30,
            "block_truncation": "required; no cross-block windows",
        },
        "science": {
            "cardiopulmonary_features": [HR, BR],
            "movement_features": [],
            "movement_note": "mmwave_motion_proxy_median remains diagnostic-only",
            "hr_representation": HR,
            "hr_status": "PROVISIONAL / PHYSIOLOGY_LIMITED",
            "br_status": "PROVISIONAL / PHYSIOLOGY_LIMITED",
            "hrv_status": "BLOCKED",
        },
        "local_detail": {"path": str(local_snapshot), "rows": len(snapshot), "sha256": sha256(local_snapshot), "local_only_reason": "probe-level participant-linked derived table"},
        "schema_smoke": smoke_json,
        "tracked_artifacts": [],
        "models_trained": False,
        "algorithm_frozen": False,
    }
    for path in [schema_path, registry_path, role_path, availability_path, smoke_path, error_path]:
        manifest["tracked_artifacts"].append({"path": path.name, "sha256": sha256(path)})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "snapshot": str(local_snapshot),
        "snapshot_sha256": sha256(local_snapshot),
        "rows": len(snapshot),
        "sessions": int(snapshot["session_id"].nunique()),
        "participant_groups": int(snapshot["participant_group_id"].nunique()),
        "available_sessions": int(snapshot.loc[estimable, "session_id"].nunique()),
        "available_probes": int(estimable.sum()),
        "tracked_output_dir": str(args.tracked_output_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
