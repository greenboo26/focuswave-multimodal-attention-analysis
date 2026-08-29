"""Versioned, multi-scale formal BB behavior producer.

The producer reads only an external frozen file/session manifest and an
external anonymous participant-group map.  It does not discover cohorts from
directory names and does not contain a 44-session or 38-group constant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import theilslopes


SCHEMA_VERSION = "focuswave-formal-bb-behavior-v1"
EVIDENCE_COMMIT = "171b081f3a3f9d06496c7b8d36915eebd4e2a3bb"
REQUIRED_MANIFEST_COLUMNS = {
    "session_id", "block_id", "behavior_path", "include", "exclusion_reason",
    "source_contract",
}
REQUIRED_IDENTITY_COLUMNS = {
    "session_id", "anonymous_participant_group_id", "identity_status",
}
REQUIRED_TRIAL_COLUMNS = {
    "subject_id", "block_num", "trial_num", "cycle_num", "is_no_go",
    "response", "rt", "correct", "commission", "omission", "is_probe",
    "probe_response", "probe_vigilance", "absolute_onset_time",
    "probe_onset_time",
}
FORBIDDEN_DERIVED_COLUMNS = {
    "pre_go_rt_cv", "dprime_loglinear", "fullclass_pupil_to_iris_diameter_ratio",
}
LEGACY_PATH_PATTERN = re.compile(r"(^|[\\/])(bbb|050-sart-formal)([\\/]|$)", re.I)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _as_seconds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    finite = values[np.isfinite(values)]
    if len(finite) and float(finite.abs().median()) > 1e10:
        values = values / 1000.0
    return values


def _join_reason(*parts: str | None) -> str:
    return ";".join(dict.fromkeys(str(x) for x in parts if x))


def _load_inputs(
    manifest_path: Path,
    identity_path: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = pd.read_csv(manifest_path, dtype=str).fillna("")
    identity = pd.read_csv(identity_path, dtype=str).fillna("")
    missing = REQUIRED_MANIFEST_COLUMNS - set(manifest.columns)
    if missing:
        raise ValueError(f"session manifest missing columns: {sorted(missing)}")
    missing = REQUIRED_IDENTITY_COLUMNS - set(identity.columns)
    if missing:
        raise ValueError(f"identity map missing columns: {sorted(missing)}")
    if manifest.duplicated(["session_id", "block_id", "behavior_path"]).any():
        raise ValueError("session manifest has duplicate session/block/file rows")
    if identity.duplicated("session_id").any():
        raise ValueError("identity map must contain one row per session")

    explicit_exclusions = set(config.get("explicit_excluded_session_ids", []))
    manifest["selected"] = manifest["include"].map(_truthy)
    manifest.loc[manifest.session_id.isin(explicit_exclusions), "selected"] = False
    manifest.loc[
        manifest.session_id.isin(explicit_exclusions) & manifest.exclusion_reason.eq(""),
        "exclusion_reason",
    ] = "explicit_config_exclusion"
    selected = manifest[manifest.selected].copy()
    if selected.empty:
        raise ValueError("frozen manifest selected no behavior files")
    accepted = set(config["accepted_source_contracts"])
    bad_contract = selected.loc[~selected.source_contract.isin(accepted), "source_contract"].unique()
    if len(bad_contract):
        raise ValueError(f"rejected source_contract values: {sorted(bad_contract)}")
    legacy = selected.behavior_path.map(lambda x: bool(LEGACY_PATH_PATTERN.search(x)))
    if legacy.any():
        raise ValueError("legacy BBB/050-sart-formal input path rejected")

    needed_sessions = set(selected.session_id)
    mapped_sessions = set(identity.session_id)
    missing_identity = needed_sessions - mapped_sessions
    if missing_identity:
        raise ValueError(f"sessions missing anonymous participant group: {sorted(missing_identity)}")
    used_identity = identity[identity.session_id.isin(needed_sessions)].copy()
    if (used_identity.anonymous_participant_group_id.str.strip() == "").any():
        raise ValueError("anonymous_participant_group_id must be non-empty")

    frames: list[pd.DataFrame] = []
    for row in selected.itertuples(index=False):
        path = Path(row.behavior_path)
        if not path.is_absolute():
            path = manifest_path.parent / path
        if not path.is_file():
            raise FileNotFoundError(path)
        source = pd.read_csv(path, encoding="utf-8-sig")
        missing_trial = REQUIRED_TRIAL_COLUMNS - set(source.columns)
        if missing_trial:
            raise ValueError(f"{path} missing raw trial columns: {sorted(missing_trial)}")
        forbidden = FORBIDDEN_DERIVED_COLUMNS & set(source.columns)
        if forbidden:
            raise ValueError(f"derived/legacy input columns rejected in {path}: {sorted(forbidden)}")
        source_subjects = source.subject_id.dropna().astype(str).unique()
        if len(source_subjects) != 1:
            raise ValueError(f"{path} must contain exactly one source subject_id")
        source = source.copy()
        source["source_subject_id"] = str(source_subjects[0])
        source["session_id"] = row.session_id
        source["block_id"] = str(row.block_id)
        source["source_path"] = str(path)
        source["source_sha256"] = _sha256(path)
        frames.append(source)
    trials = pd.concat(frames, ignore_index=True, sort=False)
    trials = trials.merge(
        used_identity[list(REQUIRED_IDENTITY_COLUMNS)], on="session_id", how="left", validate="many_to_one"
    )
    return manifest, used_identity, trials


def _prepare_trials(trials: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = trials.copy()
    numeric = [
        "block_num", "trial_num", "cycle_num", "is_no_go", "rt", "correct",
        "commission", "omission", "is_probe", "probe_response", "probe_vigilance",
    ]
    for column in numeric:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["trial_time_s"] = _as_seconds(out.absolute_onset_time)
    out["probe_time_s"] = _as_seconds(out.probe_onset_time)
    out["trial_key"] = (
        out.session_id.astype(str) + "|" + out.block_id.astype(str) + "|" + out.trial_num.astype("Int64").astype(str)
    )
    if out.trial_key.duplicated().any():
        raise ValueError("trial unique key collision")
    response_present = out.response.notna() & out.response.astype(str).str.strip().ne("")
    rt_min = float(config["rt_valid_min_ms"])
    rt_max = config.get("rt_valid_max_ms")
    rt_valid = out.rt.ge(rt_min)
    if rt_max is not None:
        rt_valid &= out.rt.le(float(rt_max))
    out["go_correct_rt_valid"] = (
        out.is_no_go.eq(0) & out.correct.eq(1) & response_present & rt_valid
    )
    out["go_correct_rt_ms"] = out.rt.where(out.go_correct_rt_valid)
    out["go_opportunities"] = out.is_no_go.eq(0).astype(int)
    out["nogo_opportunities"] = out.is_no_go.eq(1).astype(int)
    out["commission_numerator"] = (out.is_no_go.eq(1) & out.commission.eq(1)).astype(int)
    out["omission_numerator"] = (out.is_no_go.eq(0) & out.omission.eq(1)).astype(int)
    out["hit_numerator"] = (out.is_no_go.eq(0) & out.correct.eq(1)).astype(int)
    out["correct_numerator"] = out.correct.eq(1).astype(int)
    out["error_numerator"] = out.commission_numerator + out.omission_numerator
    out["correct_go_rt_opportunities"] = out.go_correct_rt_valid.astype(int)
    out["q1_nominal_4class"] = out.probe_response.where(out.probe_response.isin([1, 2, 3, 4]))
    out["q2_ordinal_4level"] = out.probe_vigilance.where(out.probe_vigilance.isin([1, 2, 3, 4]))
    out["metric_unit"] = "trial flags; RT=ms; time=s"
    out["calculation_status"] = "ok"
    invalid_q = out.is_probe.eq(1) & (
        out.q1_nominal_4class.isna() | out.q2_ordinal_4level.isna()
    )
    out["qc_reason"] = np.where(invalid_q, "invalid_or_missing_probe_response", "")
    return out.sort_values(["session_id", "block_id", "trial_time_s", "trial_num"]).reset_index(drop=True)


def _safe_rate(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else math.nan


def _sdt(go_hits: int, go_n: int, false_alarms: int, nogo_n: int, cfg: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "hit_numerator": go_hits,
        "hit_denominator": go_n,
        "false_alarm_numerator": false_alarms,
        "false_alarm_denominator": nogo_n,
        "hit_rate_raw": _safe_rate(go_hits, go_n),
        "false_alarm_rate_raw": _safe_rate(false_alarms, nogo_n),
        "sdt_correction": "loglinear_0.5_over_n_plus_1",
    }
    if go_n < int(cfg["sdt_min_go_opportunities"]) or nogo_n < int(cfg["sdt_min_nogo_opportunities"]):
        result.update({
            "hit_rate_corrected": math.nan, "false_alarm_rate_corrected": math.nan,
            "dprime_loglinear": math.nan, "criterion_c": math.nan, "beta": math.nan,
            "sdt_status": "rejected_low_opportunity",
        })
        return result
    hit = (go_hits + 0.5) / (go_n + 1.0)
    fa = (false_alarms + 0.5) / (nogo_n + 1.0)
    normal = NormalDist()
    z_hit, z_fa = normal.inv_cdf(hit), normal.inv_cdf(fa)
    exponent = (z_fa * z_fa - z_hit * z_hit) / 2.0
    result.update({
        "hit_rate_corrected": hit,
        "false_alarm_rate_corrected": fa,
        "dprime_loglinear": z_hit - z_fa,
        "criterion_c": -(z_hit + z_fa) / 2.0,
        "beta": math.exp(max(min(exponent, 700), -700)),
        "sdt_status": "ok",
    })
    return result


def _summary(frame: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    total = int(len(frame))
    go_n = int(frame.go_opportunities.sum())
    nogo_n = int(frame.nogo_opportunities.sum())
    commissions = int(frame.commission_numerator.sum())
    omissions = int(frame.omission_numerator.sum())
    hits = int(frame.hit_numerator.sum())
    correct = int(frame.correct_numerator.sum())
    error = commissions + omissions
    rt_frame = frame.loc[frame.go_correct_rt_valid & frame.go_correct_rt_ms.notna(), ["go_correct_rt_ms", "trial_time_s"]]
    rt = rt_frame.go_correct_rt_ms.astype(float)
    rt_n = int(len(rt))
    reasons: list[str] = []
    min_summary = int(cfg["rt_min_count_summary"])
    min_dispersion = int(cfg["rt_min_count_dispersion"])
    min_slope = int(cfg["rt_min_count_slope"])
    mean = float(rt.mean()) if rt_n >= min_summary else math.nan
    median = float(rt.median()) if rt_n >= min_summary else math.nan
    sd = float(rt.std(ddof=1)) if rt_n >= max(2, min_dispersion) else math.nan
    mad = float((rt - rt.median()).abs().median()) if rt_n >= min_dispersion else math.nan
    iqr = float(rt.quantile(0.75) - rt.quantile(0.25)) if rt_n >= min_dispersion else math.nan
    cv = float(sd / mean) if np.isfinite(sd) and np.isfinite(mean) and mean != 0 else math.nan
    slope = math.nan
    if rt_n >= min_slope and rt_frame.trial_time_s.nunique() >= 2:
        x = rt_frame.trial_time_s.astype(float) - float(rt_frame.trial_time_s.min())
        slope = float(theilslopes(rt.to_numpy(), x.to_numpy()).slope)
    else:
        reasons.append("insufficient_rt_for_robust_slope")
    if rt_n < min_dispersion:
        reasons.append("insufficient_rt_for_dispersion")
    sdt = _sdt(hits, go_n, commissions, nogo_n, cfg)
    if sdt["sdt_status"] != "ok":
        reasons.append(sdt["sdt_status"])
    result = {
        "total_trial_opportunities": total,
        "go_opportunities": go_n,
        "nogo_opportunities": nogo_n,
        "correct_go_rt_opportunities": rt_n,
        "commission_numerator": commissions,
        "commission_denominator": nogo_n,
        "commission_rate": _safe_rate(commissions, nogo_n),
        "omission_numerator": omissions,
        "omission_denominator": go_n,
        "omission_rate": _safe_rate(omissions, go_n),
        "accuracy_numerator": correct,
        "accuracy_denominator": total,
        "accuracy": _safe_rate(correct, total),
        "error_numerator": error,
        "error_denominator": total,
        "error_rate": _safe_rate(error, total),
        "go_correct_rt_mean_ms": mean,
        "go_correct_rt_median_ms": median,
        "go_correct_rt_sd_ms": sd,
        "go_correct_rt_mad_ms": mad,
        "go_correct_rt_iqr_ms": iqr,
        "go_correct_rt_cv": cv,
        "go_correct_rt_theilsen_slope_ms_per_s": slope,
        "metric_unit": "rates=proportion; RT=ms; RT slope=ms/s",
        "calculation_status": "ok" if not reasons else "partial",
        "qc_reason": _join_reason(*reasons),
    }
    result.update(sdt)
    # Compatibility aliases for the existing 12 pre-probe engineering fields.
    result.update({
        "trial_count": total, "rt_mean": mean, "rt_median": median, "rt_sd": sd,
        "rt_mad": mad, "rt_cv": cv, "rt_slope": slope,
        "error_count": error, "omission_count": omissions,
    })
    return result


def _aggregate(trials: pd.DataFrame, group_columns: list[str], cfg: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, frame in trials.groupby(group_columns, dropna=False, sort=True):
        keys = key if isinstance(key, tuple) else (key,)
        row = dict(zip(group_columns, keys))
        row.update(_summary(frame, cfg))
        rows.append(row)
    return pd.DataFrame(rows)


def _select_probe_preceding_trials(
    trials: pd.DataFrame,
    probe: Any,
    *,
    start: float,
    end: float,
) -> pd.DataFrame:
    """Select only non-probe behavior trials preceding one probe anchor.

    Session and Block identity are part of the membership predicate so this
    helper remains safe even if a caller passes a wider frame than one Block.
    The anchor key is excluded independently of timestamps because a probe's
    questionnaire onset can occur after its anchored trial onset.
    """
    return trials[
        trials.session_id.eq(probe.session_id)
        & trials.block_id.eq(probe.block_id)
        & trials.is_probe.eq(0)
        & trials.trial_key.ne(probe.trial_key)
        & trials.trial_time_s.ge(start)
        & trials.trial_time_s.lt(end)
    ]


def _probe_windows(trials: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_columns = ["session_id", "block_id"]
    for (session_id, block_id), block in trials.groupby(group_columns, sort=True):
        probes = block[block.is_probe.eq(1)]
        for probe in probes.itertuples(index=False):
            anchor = probe.probe_time_s if np.isfinite(probe.probe_time_s) else probe.trial_time_s
            anchor_source = "probe_onset_time" if np.isfinite(probe.probe_time_s) else "absolute_onset_time_fallback"
            for width in cfg["probe_window_seconds"]:
                start, end = float(anchor) - float(width), float(anchor)
                selected = _select_probe_preceding_trials(
                    block, probe, start=start, end=end
                )
                row = {
                    "session_id": session_id,
                    "anonymous_participant_group_id": probe.anonymous_participant_group_id,
                    "block_id": block_id,
                    "window_key": f"{probe.trial_key}|pre{width}s",
                    "window_type": "probe_preceding_seconds",
                    "window_seconds_nominal": float(width),
                    "window_start_s": start,
                    "window_end_s_exclusive": end,
                    "anchor_trial_key": probe.trial_key,
                    "anchor_source": anchor_source,
                    "q1_nominal_4class": probe.q1_nominal_4class,
                    "q2_ordinal_4level": probe.q2_ordinal_4level,
                }
                row.update(_summary(selected, cfg))
                if anchor_source.endswith("fallback"):
                    row["qc_reason"] = _join_reason(row["qc_reason"], anchor_source)
                    row["calculation_status"] = "partial"
                rows.append(row)
        finite = block[np.isfinite(block.trial_time_s)]
        if finite.empty:
            continue
        origin = float(finite.trial_time_s.min())
        final = float(finite.trial_time_s.max())
        for width in cfg["fixed_window_seconds"]:
            width = float(width)
            index = 0
            start = origin
            while start <= final:
                end = start + width
                selected = block[block.trial_time_s.ge(start) & block.trial_time_s.lt(end)]
                row = {
                    "session_id": session_id,
                    "anonymous_participant_group_id": block.anonymous_participant_group_id.iloc[0],
                    "block_id": block_id,
                    "window_key": f"{session_id}|{block_id}|fixed{int(width)}s|{index:04d}",
                    "window_type": "fixed_seconds",
                    "window_seconds_nominal": width,
                    "window_start_s": start,
                    "window_end_s_exclusive": end,
                    "anchor_trial_key": "",
                    "anchor_source": "block_first_trial",
                    "q1_nominal_4class": math.nan,
                    "q2_ordinal_4level": math.nan,
                }
                row.update(_summary(selected, cfg))
                rows.append(row)
                index += 1
                start = end
    result = pd.DataFrame(rows)
    if not result.empty and result.window_key.duplicated().any():
        raise RuntimeError("window unique key collision")
    return result


def _phase_cycle(trials: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if "phase" in trials.columns and trials.phase.notna().any():
        phase = trials.copy()
        phase["phase_cycle_type"] = "phase"
        phase["phase_cycle_id"] = phase.phase.astype(str)
        frames.append(phase)
    cycle = trials.copy()
    cycle["phase_cycle_type"] = "cycle"
    cycle["phase_cycle_id"] = cycle.cycle_num.astype("Int64").astype(str)
    frames.append(cycle)
    long = pd.concat(frames, ignore_index=True)
    return _aggregate(
        long,
        ["session_id", "anonymous_participant_group_id", "block_id", "phase_cycle_type", "phase_cycle_id"],
        cfg,
    )


def _error_trajectories(trials: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    offsets = [int(x) for x in cfg["error_trajectory_trial_offsets"]]
    for (session_id, block_id), block in trials.groupby(["session_id", "block_id"], sort=True):
        block = block.sort_values(["trial_time_s", "trial_num"]).reset_index(drop=True)
        errors = block.index[block.error_numerator.gt(0)]
        for event_number, event_index in enumerate(errors, start=1):
            event = block.loc[event_index]
            event_type = "commission" if event.commission_numerator else "omission"
            event_key = f"{session_id}|{block_id}|{event_type}|{event_number:04d}"
            for offset in offsets:
                target_index = event_index + offset
                target = block.loc[target_index] if 0 <= target_index < len(block) else None
                value = float(target.go_correct_rt_ms) if target is not None and np.isfinite(target.go_correct_rt_ms) else math.nan
                rows.append({
                    "session_id": session_id,
                    "anonymous_participant_group_id": event.anonymous_participant_group_id,
                    "block_id": block_id,
                    "error_event_key": event_key,
                    "error_type": event_type,
                    "trial_offset": offset,
                    "target_trial_key": "" if target is None else target.trial_key,
                    "go_correct_rt_ms": value,
                    "opportunity_count": int(target is not None),
                    "numerator": int(np.isfinite(value)),
                    "denominator": int(target is not None),
                    "metric_unit": "RT=ms; offset=trial",
                    "calculation_status": "ok" if np.isfinite(value) else "not_calculable",
                    "qc_reason": "" if np.isfinite(value) else ("window_boundary" if target is None else "target_not_correct_go_rt"),
                })
    return pd.DataFrame(rows)


def produce(
    manifest_path: Path,
    identity_path: Path,
    config_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Produce five standard tables plus error-event trajectories and a manifest."""
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output_dir}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"config schema_version must be {SCHEMA_VERSION}")
    manifest, identity, raw_trials = _load_inputs(manifest_path, identity_path, config)
    trials = _prepare_trials(raw_trials, config)
    windows = _probe_windows(trials, config)
    phase_cycle = _phase_cycle(trials, config)
    phase_cycle.insert(
        0,
        "phase_cycle_key",
        phase_cycle.session_id.astype(str) + "|" + phase_cycle.block_id.astype(str)
        + "|" + phase_cycle.phase_cycle_type.astype(str) + "|" + phase_cycle.phase_cycle_id.astype(str),
    )
    blocks = _aggregate(
        trials,
        ["session_id", "anonymous_participant_group_id", "block_id"],
        config,
    )
    blocks.insert(0, "block_key", blocks.session_id.astype(str) + "|" + blocks.block_id.astype(str))
    sessions = _aggregate(
        trials,
        ["session_id", "anonymous_participant_group_id"],
        config,
    )
    sessions.insert(0, "session_key", sessions.session_id.astype(str))
    trajectories = _error_trajectories(trials, config)

    output_dir.mkdir(parents=True)
    tables = {
        "trial_metrics.csv": trials,
        "window_metrics.csv": windows,
        "phase_cycle_metrics.csv": phase_cycle,
        "block_metrics.csv": blocks,
        "session_metrics.csv": sessions,
        "error_trajectory_metrics.csv": trajectories,
    }
    hashes: dict[str, str] = {}
    for name, table in tables.items():
        path = output_dir / name
        table.to_csv(path, index=False, encoding="utf-8-sig")
        hashes[name] = _sha256(path)
    run_manifest = {
        "schema_version": SCHEMA_VERSION,
        "scientific_status": "derived_metrics_only_no_formal_inference",
        "evidence_repository_commit": EVIDENCE_COMMIT,
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": _sha256(manifest_path),
        "identity_map": str(identity_path),
        "identity_map_sha256": _sha256(identity_path),
        "config": str(config_path),
        "config_sha256": _sha256(config_path),
        "selected_session_count": int(trials.session_id.nunique()),
        "selected_participant_group_count": int(identity.anonymous_participant_group_id.nunique()),
        "excluded_manifest_rows": int((~manifest.selected).sum()),
        "table_rows": {name: int(len(table)) for name, table in tables.items()},
        "output_sha256": hashes,
        "cohort_size_hardcoded": False,
        "formal_statistics_run": False,
    }
    manifest_out = output_dir / "run_manifest.json"
    manifest_out.write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_manifest


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-manifest", type=Path, required=True)
    parser.add_argument("--identity-map", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = produce(args.session_manifest, args.identity_map, args.config, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
