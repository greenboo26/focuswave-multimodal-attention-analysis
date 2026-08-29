from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr, theilslopes


SCHEMA_VERSION = "focuswave-behavior-science-v3"
PRIMARY_WINDOW_SECONDS = 30
SENSITIVITY_WINDOWS_SECONDS = (10, 20, 30)
CANONICAL_METRICS = (
    "go_correct_rt_mean_ms",
    "go_correct_rt_median_ms",
    "go_correct_rt_sd_ms",
    "go_correct_rt_mad_ms",
    "go_correct_rt_iqr_ms",
    "go_correct_rt_cv",
    "go_correct_rt_theilsen_slope_ms_per_s",
    "omission_rate",
    "commission_rate",
    "dprime_loglinear",
    "criterion_c",
    "beta",
)
COUNT_FIELDS = (
    "total_trial_opportunities",
    "go_opportunities",
    "nogo_opportunities",
    "correct_go_rt_opportunities",
    "omission_numerator",
    "omission_denominator",
    "commission_numerator",
    "commission_denominator",
)


@dataclass(frozen=True)
class AnalysisConfig:
    primary_window_seconds: int = PRIMARY_WINDOW_SECONDS
    sensitivity_windows_seconds: tuple[int, ...] = SENSITIVITY_WINDOWS_SECONDS
    q1_reference_category: int = 1
    minimum_model_rows: int = 12
    minimum_participant_clusters: int = 3
    prediction_folds: int = 5
    error_overlap_policy: str = "nearest_event"
    error_baseline_offsets: tuple[int, ...] = (-3, -2, -1)
    rt_valid_min_ms: float = 100.0
    rt_valid_max_ms: float | None = None
    sdt_min_go_opportunities: int = 4
    sdt_min_nogo_opportunities: int = 2


class ContractError(ValueError):
    """Raised when input structure violates a v3 analysis contract."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_rate(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else math.nan


def _mad(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna()
    return float((x - x.median()).abs().median()) if len(x) else math.nan


def _sdt(go_hits: int, go_n: int, false_alarms: int, nogo_n: int, cfg: AnalysisConfig) -> dict[str, Any]:
    if go_n < cfg.sdt_min_go_opportunities or nogo_n < cfg.sdt_min_nogo_opportunities:
        return {
            "dprime_loglinear": math.nan,
            "criterion_c": math.nan,
            "beta": math.nan,
            "sdt_status": "rejected_low_opportunity",
        }
    hit = (go_hits + 0.5) / (go_n + 1.0)
    fa = (false_alarms + 0.5) / (nogo_n + 1.0)
    z_hit, z_fa = norm.ppf(hit), norm.ppf(fa)
    exponent = float(np.clip((z_fa * z_fa - z_hit * z_hit) / 2.0, -700, 700))
    return {
        "dprime_loglinear": float(z_hit - z_fa),
        "criterion_c": float(-(z_hit + z_fa) / 2.0),
        "beta": float(math.exp(exponent)),
        "sdt_status": "ok",
    }


def aggregate_behavior_metrics(frame: pd.DataFrame, cfg: AnalysisConfig | None = None) -> dict[str, Any]:
    """Calculate canonical behavior metrics without collapsing omission and commission.

    Go omission and No-Go commission remain separate outcomes and denominators. The
    function never creates a combined ``correct`` dependent variable.
    """
    cfg = cfg or AnalysisConfig()
    d = frame.copy()
    for column in ("is_no_go", "correct", "omission", "commission", "rt", "trial_time_s"):
        if column not in d:
            d[column] = np.nan
        d[column] = pd.to_numeric(d[column], errors="coerce")

    go = d.is_no_go.eq(0)
    nogo = d.is_no_go.eq(1)
    omission = go & d.omission.eq(1)
    commission = nogo & d.commission.eq(1)
    response_present = d.get("response", pd.Series(index=d.index, dtype=object)).notna()
    valid_rt = go & d.correct.eq(1) & response_present & d.rt.ge(cfg.rt_valid_min_ms)
    if cfg.rt_valid_max_ms is not None:
        valid_rt &= d.rt.le(cfg.rt_valid_max_ms)
    rt = d.loc[valid_rt, "rt"].astype(float)
    rt_time = d.loc[valid_rt, "trial_time_s"].astype(float)
    rt_n = len(rt)
    mean = float(rt.mean()) if rt_n else math.nan
    median = float(rt.median()) if rt_n else math.nan
    sd = float(rt.std(ddof=1)) if rt_n >= 2 else math.nan
    mad = _mad(rt)
    iqr = float(rt.quantile(.75) - rt.quantile(.25)) if rt_n else math.nan
    cv = float(sd / mean) if np.isfinite(sd) and np.isfinite(mean) and mean != 0 else math.nan
    slope = math.nan
    if rt_n >= 2 and rt_time.nunique() >= 2:
        x = rt_time - float(rt_time.min())
        slope = float(theilslopes(rt.to_numpy(), x.to_numpy()).slope)

    go_n, nogo_n = int(go.sum()), int(nogo.sum())
    omission_n, commission_n = int(omission.sum()), int(commission.sum())
    hits = int((go & d.correct.eq(1)).sum())
    result = {
        "total_trial_opportunities": int(len(d)),
        "go_opportunities": go_n,
        "nogo_opportunities": nogo_n,
        "correct_go_rt_opportunities": int(rt_n),
        "go_correct_rt_mean_ms": mean,
        "go_correct_rt_median_ms": median,
        "go_correct_rt_sd_ms": sd,
        "go_correct_rt_mad_ms": mad,
        "go_correct_rt_iqr_ms": iqr,
        "go_correct_rt_cv": cv,
        "go_correct_rt_theilsen_slope_ms_per_s": slope,
        "omission_numerator": omission_n,
        "omission_denominator": go_n,
        "omission_rate": _safe_rate(omission_n, go_n),
        "commission_numerator": commission_n,
        "commission_denominator": nogo_n,
        "commission_rate": _safe_rate(commission_n, nogo_n),
        "metric_unit": "RT=ms; RT slope=ms/s; omission/commission=proportion",
    }
    result.update(_sdt(hits, go_n, commission_n, nogo_n, cfg))
    return result


def _probe_event_id(frame: pd.DataFrame) -> pd.Series:
    if "synthetic_or_authorized_event_id" in frame:
        return frame["synthetic_or_authorized_event_id"].astype(str)
    if "anchor_trial_key" in frame:
        return frame["anchor_trial_key"].astype(str)
    needed = {"session_id", "block_id"}
    if not needed.issubset(frame.columns):
        raise ContractError("probe rows require event id or session_id/block_id")
    ordinal = frame.groupby(["session_id", "block_id"], sort=False).cumcount()
    return frame.session_id.astype(str) + "|" + frame.block_id.astype(str) + "|probe|" + ordinal.astype(str)


def build_probe_analysis_tables(window_metrics: pd.DataFrame, cfg: AnalysisConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return one-row-per-probe primary table and separate window sensitivity rows."""
    cfg = cfg or AnalysisConfig()
    d = window_metrics.copy()
    required = {"session_id", "block_id", "window_seconds_nominal"}
    missing = required - set(d.columns)
    if missing:
        raise ContractError(f"probe window table missing columns: {sorted(missing)}")
    if "window_type" in d:
        d = d[d.window_type.astype(str).eq("probe_preceding_seconds")].copy()
    d["window_seconds_nominal"] = pd.to_numeric(d.window_seconds_nominal, errors="coerce")
    d["synthetic_or_authorized_event_id"] = _probe_event_id(d)
    d["participant_cluster_ref"] = d.get(
        "participant_cluster_ref", d.get("anonymous_participant_group_id", "")
    ).astype(str)
    allowed = {float(x) for x in cfg.sensitivity_windows_seconds}
    sensitivity = d[d.window_seconds_nominal.isin(allowed)].copy()
    sensitivity["analysis_role"] = "window_sensitivity_only"
    sensitivity["formal_independent_sample"] = False
    key = ["synthetic_or_authorized_event_id", "window_seconds_nominal"]
    if sensitivity.duplicated(key).any():
        raise ContractError("duplicate probe/window sensitivity key")

    primary = sensitivity[sensitivity.window_seconds_nominal.eq(float(cfg.primary_window_seconds))].copy()
    if primary.empty:
        raise ContractError("primary probe window is unavailable")
    if primary.synthetic_or_authorized_event_id.duplicated().any():
        raise ContractError("primary probe table must contain one row per probe")
    primary["analysis_role"] = "primary_probe"
    primary["formal_independent_sample"] = True
    primary["probe_n_unit"] = "probe_event"
    return primary.reset_index(drop=True), sensitivity.reset_index(drop=True)


def _metric_columns(frame: pd.DataFrame) -> list[str]:
    return [m for m in CANONICAL_METRICS if m in frame.columns]


def build_b1_b2_pairs(block_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pair B1/B2 within session before any participant-level aggregation."""
    d = block_metrics.copy()
    participant = "participant_cluster_ref" if "participant_cluster_ref" in d else "anonymous_participant_group_id"
    required = {"session_id", "block_id", participant}
    missing = required - set(d.columns)
    if missing:
        raise ContractError(f"block table missing columns: {sorted(missing)}")
    d[participant] = d[participant].astype(str)
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    metrics = _metric_columns(d)

    # Repeated participants require explicit session order; never infer it from IDs/timestamps.
    session_counts = d[[participant, "session_id"]].drop_duplicates().groupby(participant).size()
    repeated = set(session_counts[session_counts.gt(1)].index)
    if repeated and "session_order" not in d:
        for cluster in sorted(repeated):
            failures.append({
                "analysis": "B1_B2",
                "participant_cluster_ref": cluster,
                "session_id": "",
                "status": "failed_missing_explicit_session_order",
                "reason": "repeat participant sessions must provide explicit session_order",
            })

    for session_id, s in d.groupby("session_id", sort=False):
        cluster_values = s[participant].dropna().astype(str).unique()
        cluster = cluster_values[0] if len(cluster_values) == 1 else ""
        if len(cluster_values) != 1:
            failures.append({"analysis": "B1_B2", "participant_cluster_ref": cluster,
                             "session_id": session_id, "status": "failed_participant_inconsistency",
                             "reason": "session maps to multiple participant clusters"})
            continue
        b1, b2 = s[s.block_id.astype(str).eq("B1")], s[s.block_id.astype(str).eq("B2")]
        if len(b1) != 1 or len(b2) != 1:
            failures.append({"analysis": "B1_B2", "participant_cluster_ref": cluster,
                             "session_id": session_id, "status": "failed_pair_cardinality",
                             "reason": f"expected one B1 and one B2; got B1={len(b1)}, B2={len(b2)}"})
            continue
        r1, r2 = b1.iloc[0], b2.iloc[0]
        base = {"session_id": session_id, "participant_cluster_ref": cluster,
                "pair_status": "ok_session_internal"}
        if "session_order" in s:
            orders = pd.to_numeric(s.session_order, errors="coerce").dropna().unique()
            base["session_order"] = float(orders[0]) if len(orders) == 1 else math.nan
            if cluster in repeated and len(orders) != 1:
                failures.append({"analysis": "B1_B2", "participant_cluster_ref": cluster,
                                 "session_id": session_id, "status": "failed_session_order_inconsistent",
                                 "reason": "repeat participant session has missing/inconsistent session_order"})
        for metric in metrics:
            v1, v2 = pd.to_numeric(pd.Series([r1.get(metric), r2.get(metric)]), errors="coerce")
            rows.append({**base, "metric": metric, "b1_value": float(v1) if np.isfinite(v1) else math.nan,
                         "b2_value": float(v2) if np.isfinite(v2) else math.nan,
                         "b2_minus_b1": float(v2 - v1) if np.isfinite(v1) and np.isfinite(v2) else math.nan})
    return pd.DataFrame(rows), pd.DataFrame(failures)


def build_participant_disjoint_folds(frame: pd.DataFrame, n_splits: int = 5) -> pd.DataFrame:
    """Assign all sessions/probes of one participant cluster to one prediction fold."""
    try:
        from sklearn.model_selection import GroupKFold
    except Exception as exc:  # pragma: no cover - dependency gate
        raise RuntimeError("scikit-learn is required for participant-disjoint prediction") from exc
    d = frame.copy()
    participant = "participant_cluster_ref" if "participant_cluster_ref" in d else "anonymous_participant_group_id"
    if participant not in d:
        raise ContractError("participant cluster column is required")
    groups = d[participant].astype(str)
    unique_groups = groups.nunique()
    if unique_groups < 2:
        raise ContractError("participant-disjoint prediction needs at least two participant clusters")
    splits = min(int(n_splits), unique_groups)
    fold = np.full(len(d), -1, dtype=int)
    splitter = GroupKFold(n_splits=splits)
    dummy_x = np.zeros((len(d), 1))
    for fold_id, (_, test_idx) in enumerate(splitter.split(dummy_x, groups=groups)):
        fold[test_idx] = fold_id
    out = d[[c for c in [participant, "session_id", "synthetic_or_authorized_event_id"] if c in d]].copy()
    out["fold_id"] = fold
    check = pd.DataFrame({"group": groups, "fold": fold}).groupby("group").fold.nunique()
    if not check.eq(1).all() or (fold < 0).any():
        raise RuntimeError("participant-disjoint fold leakage")
    out["split_contract"] = "participant_cluster_disjoint"
    return out


def prepare_error_trajectories(trajectory: pd.DataFrame, cfg: AnalysisConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve overlapping error windows and add within-participant/baseline changes."""
    cfg = cfg or AnalysisConfig()
    d = trajectory.copy()
    participant = "participant_cluster_ref" if "participant_cluster_ref" in d else "anonymous_participant_group_id"
    required = {participant, "session_id", "error_event_key", "trial_offset", "target_trial_key", "go_correct_rt_ms"}
    missing = required - set(d.columns)
    if missing:
        raise ContractError(f"error trajectory table missing columns: {sorted(missing)}")
    d[participant] = d[participant].astype(str)
    d["trial_offset"] = pd.to_numeric(d.trial_offset, errors="coerce")
    d["go_correct_rt_ms"] = pd.to_numeric(d.go_correct_rt_ms, errors="coerce")
    d["overlap_count"] = d.groupby(["session_id", "target_trial_key"])["error_event_key"].transform("nunique")
    overlap = d[d.overlap_count.gt(1) & d.target_trial_key.astype(str).ne("")].copy()

    if cfg.error_overlap_policy != "nearest_event":
        raise ContractError("v3 currently supports error_overlap_policy='nearest_event' only")
    ranked = d.assign(_abs_offset=d.trial_offset.abs()).sort_values(
        ["session_id", "target_trial_key", "_abs_offset", "error_event_key"], kind="stable"
    )
    has_target = ranked.target_trial_key.astype(str).ne("")
    kept_target = ranked[has_target].drop_duplicates(["session_id", "target_trial_key"], keep="first")
    kept_missing = ranked[~has_target]
    resolved = pd.concat([kept_target, kept_missing], ignore_index=True).drop(columns="_abs_offset")
    resolved["overlap_policy"] = cfg.error_overlap_policy
    resolved["overlap_resolved"] = resolved.overlap_count.gt(1)

    resolved["within_participant_centered_rt_ms"] = resolved.go_correct_rt_ms - resolved.groupby(participant).go_correct_rt_ms.transform("mean")
    baseline_mask = resolved.trial_offset.isin(cfg.error_baseline_offsets)
    baseline = (resolved[baseline_mask].groupby([participant, "error_event_key"], dropna=False).go_correct_rt_ms
                .mean().rename("event_pre_error_baseline_rt_ms").reset_index())
    resolved = resolved.merge(baseline, on=[participant, "error_event_key"], how="left")
    resolved["relative_to_pre_error_baseline_rt_ms"] = resolved.go_correct_rt_ms - resolved.event_pre_error_baseline_rt_ms
    resolved["baseline_status"] = np.where(resolved.event_pre_error_baseline_rt_ms.notna(), "available", "missing_pre_error_baseline")
    return resolved.sort_values(["session_id", "error_event_key", "trial_offset"]), overlap


def _relation_type(a: str, b: str) -> tuple[str, str]:
    pair = frozenset((a, b))
    mathematical = {
        frozenset(("accuracy", "error_rate")),
        frozenset(("commission_rate", "false_alarm_rate_raw")),
    }
    sdt = {"dprime_loglinear", "criterion_c", "beta"}
    if pair in mathematical:
        return "mathematical_identity_or_complement", "数学恒等/互补关系，不作为心理机制证据"
    if (a in sdt or b in sdt) and ({a, b} & {"commission_rate", "hit_rate_raw", "false_alarm_rate_raw"}):
        return "derived_redundancy", "共享计算成分的派生冗余，只作测量/QC解释"
    if a.startswith("go_correct_rt_") and b.startswith("go_correct_rt_"):
        return "same_measure_family", "同一RT分布的不同摘要，相关主要反映测量冗余"
    return "behavioral_association", "可作为描述性行为关系；机制解释仍需独立设计与正式推断"


def build_correlation_evidence(session_metrics: pd.DataFrame) -> pd.DataFrame:
    """Create a typed session-level correlation table with participant sensitivity."""
    d = session_metrics.copy()
    participant = "participant_cluster_ref" if "participant_cluster_ref" in d else "anonymous_participant_group_id"
    metrics = [m for m in CANONICAL_METRICS if m in d]
    rows: list[dict[str, Any]] = []
    for i, a in enumerate(metrics):
        for b in metrics[i + 1:]:
            x, y = pd.to_numeric(d[a], errors="coerce"), pd.to_numeric(d[b], errors="coerce")
            ok = x.notna() & y.notna()
            rho = float(spearmanr(x[ok], y[ok]).statistic) if ok.sum() >= 3 and x[ok].nunique() > 1 and y[ok].nunique() > 1 else math.nan
            relation_type, note = _relation_type(a, b)
            # Repeat-participant sensitivity: collapse sessions to participant means first.
            rho_participant = math.nan
            participant_n = math.nan
            if participant in d:
                p = d.loc[ok, [participant, a, b]].copy()
                p[a] = pd.to_numeric(p[a], errors="coerce"); p[b] = pd.to_numeric(p[b], errors="coerce")
                p = p.groupby(participant, as_index=False)[[a, b]].mean().dropna()
                participant_n = int(len(p))
                if len(p) >= 3 and p[a].nunique() > 1 and p[b].nunique() > 1:
                    rho_participant = float(spearmanr(p[a], p[b]).statistic)
            rows.append({"metric_a": a, "metric_b": b, "relation_type": relation_type,
                         "interpretation_boundary_zh": note, "observation_unit": "session",
                         "session_pair_n": int(ok.sum()), "spearman_session": rho,
                         "participant_aggregate_n": participant_n,
                         "spearman_participant_sensitivity": rho_participant,
                         "formal_inference": False})
    return pd.DataFrame(rows)


def _failure(name: str, family: str, outcome: str, reason: str, n_rows: int, n_participants: int,
             n_sessions: int, status: str = "failed") -> dict[str, Any]:
    return {"model_name": name, "model_family": family, "outcome": outcome,
            "status": status, "formal_inference": False, "n_rows": int(n_rows),
            "participant_cluster_n": int(n_participants), "session_n": int(n_sessions),
            "reason": reason}


def fit_q1_models(primary_probe: pd.DataFrame, cfg: AnalysisConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit nominal-Q1 repeated-measure models or emit auditable failure rows."""
    cfg = cfg or AnalysisConfig()
    try:
        import statsmodels.formula.api as smf
    except Exception as exc:
        failures = [_failure("Q1_backend", "mixedlm_nominal_predictor", "all", f"statsmodels unavailable: {exc}",
                             len(primary_probe), primary_probe.participant_cluster_ref.nunique(), primary_probe.session_id.nunique())]
        return pd.DataFrame(), pd.DataFrame(failures)

    d0 = primary_probe.copy()
    if "participant_cluster_ref" not in d0:
        raise ContractError("Q1 requires participant_cluster_ref")
    if "q1_nominal_4class" not in d0:
        raise ContractError("Q1 category is missing")
    d0["q1_nominal_4class"] = pd.to_numeric(d0.q1_nominal_4class, errors="coerce").astype("Int64")
    valid_levels = set(d0.q1_nominal_4class.dropna().astype(int))
    expected = {1, 2, 3, 4}
    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    if cfg.q1_reference_category not in valid_levels:
        failures.append(_failure("Q1_reference_gate", "mixedlm_nominal_predictor", "all",
                                 f"reference category {cfg.q1_reference_category} absent", len(d0),
                                 d0.participant_cluster_ref.nunique(), d0.session_id.nunique(), "failed_reference_category"))
        return pd.DataFrame(), pd.DataFrame(failures)
    missing_levels = expected - valid_levels
    if missing_levels:
        failures.append(_failure("Q1_category_gate", "mixedlm_nominal_predictor", "all",
                                 f"missing Q1 categories: {sorted(missing_levels)}", len(d0),
                                 d0.participant_cluster_ref.nunique(), d0.session_id.nunique(), "descriptive_only_missing_category"))

    for metric in _metric_columns(d0):
        d = d0.dropna(subset=[metric, "q1_nominal_4class", "participant_cluster_ref", "session_id"]).copy()
        n_p, n_s = d.participant_cluster_ref.nunique(), d.session_id.nunique()
        if len(d) < cfg.minimum_model_rows or n_p < cfg.minimum_participant_clusters:
            failures.append(_failure(f"Q1_{metric}", "mixedlm_nominal_predictor", metric,
                                     "insufficient rows/participant clusters", len(d), n_p, n_s,
                                     "failed_minimum_sample_gate"))
            continue
        try:
            formula = f"{metric} ~ C(q1_nominal_4class, Treatment(reference={cfg.q1_reference_category}))"
            model = smf.mixedlm(formula, d, groups=d["participant_cluster_ref"],
                                vc_formula={"session": "0 + C(session_id)"}, re_formula="1")
            fit = model.fit(reml=False, method="lbfgs", maxiter=500, disp=False)
            if not bool(getattr(fit, "converged", False)):
                failures.append(_failure(f"Q1_{metric}", "mixedlm_nominal_predictor", metric,
                                         "model did not converge", len(d), n_p, n_s, "failed_convergence"))
                continue
            for term in fit.fe_params.index:
                if term == "Intercept":
                    continue
                est = float(fit.fe_params[term]); se = float(fit.bse[term])
                results.append({"model_name": f"Q1_{metric}", "model_family": "mixedlm_nominal_predictor",
                                "outcome": metric, "term": term, "estimate": est, "se": se,
                                "ci_low": est - 1.96 * se, "ci_high": est + 1.96 * se,
                                "reference_category": cfg.q1_reference_category,
                                "observation_unit": "probe", "participant_cluster_n": n_p,
                                "session_n": n_s, "formal_inference": True, "status": "ok_converged"})
        except Exception as exc:
            failures.append(_failure(f"Q1_{metric}", "mixedlm_nominal_predictor", metric,
                                     f"{type(exc).__name__}: {exc}", len(d), n_p, n_s, "failed_exception"))
    return pd.DataFrame(results), pd.DataFrame(failures)


def q2_gate(primary_probe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fail closed: unclustered OrderedModel is never accepted as v3 formal inference."""
    d = primary_probe.copy()
    d["q2_ordinal_4level"] = pd.to_numeric(d.get("q2_ordinal_4level"), errors="coerce")
    desc_rows = []
    for level, g in d[d.q2_ordinal_4level.between(1, 4)].groupby("q2_ordinal_4level"):
        row = {"q2_level": int(level), "probe_n": int(len(g)), "session_n": int(g.session_id.nunique()),
               "participant_group_n": int(g.participant_cluster_ref.nunique()), "analysis_status": "descriptive_only"}
        for metric in _metric_columns(g):
            row[f"{metric}_mean"] = float(pd.to_numeric(g[metric], errors="coerce").mean())
        desc_rows.append(row)
    failure = _failure("Q2_formal_ordinal_gate", "clustered_ordinal_required", "q2_ordinal_4level",
                       "no audited participant/session-clustered ordinal backend is implemented; unclustered OrderedModel is forbidden",
                       len(d), d.participant_cluster_ref.nunique(), d.session_id.nunique(), "blocked_formal_inference")
    return pd.DataFrame(desc_rows), pd.DataFrame([failure])


def build_forest_manifest(model_results: pd.DataFrame) -> pd.DataFrame:
    """Assign every effect to a dimensionally homogeneous forest facet."""
    if model_results.empty:
        return pd.DataFrame(columns=["model_name", "outcome", "term", "facet", "unit", "estimand", "reference"])
    unit_map = {
        "go_correct_rt_mean_ms": "ms", "go_correct_rt_median_ms": "ms",
        "go_correct_rt_sd_ms": "ms", "go_correct_rt_mad_ms": "ms", "go_correct_rt_iqr_ms": "ms",
        "go_correct_rt_cv": "ratio", "go_correct_rt_theilsen_slope_ms_per_s": "ms/s",
        "omission_rate": "proportion", "commission_rate": "proportion",
        "dprime_loglinear": "SDT_dimensionless", "criterion_c": "SDT_dimensionless", "beta": "ratio",
    }
    out = model_results.copy()
    out["unit"] = out.outcome.map(unit_map).fillna("other")
    out["facet"] = out["unit"].map({"ms": "RT水平（毫秒）", "ms/s": "RT时间斜率（毫秒/秒）",
                                    "proportion": "错误概率（比例）", "ratio": "比率/变异系数",
                                    "SDT_dimensionless": "信号检测无量纲指标"}).fillna("其他量纲")
    out["estimand"] = "Q1类别相对参考类别的条件均值差"
    out["reference"] = out.get("reference_category", np.nan)
    out["cross_facet_visual_ranking_forbidden"] = True
    return out


def qc_denominator_table(trial: pd.DataFrame, primary_probe: pd.DataFrame, block: pd.DataFrame,
                         session: pd.DataFrame) -> pd.DataFrame:
    participant = "participant_cluster_ref" if "participant_cluster_ref" in session else "anonymous_participant_group_id"
    return pd.DataFrame([
        {"layer": "session", "count": int(session.session_id.nunique()), "denominator": int(session.session_id.nunique()),
         "observation_unit_zh": "场次", "repeat_handling_zh": "场次保留；推断时按参与者聚类"},
        {"layer": "participant_group", "count": int(session[participant].nunique()), "denominator": int(session[participant].nunique()),
         "observation_unit_zh": "当前匿名参与者分析组", "repeat_handling_zh": "重复场次归入同一参与者聚类"},
        {"layer": "block", "count": int(len(block)), "denominator": int(len(block)),
         "observation_unit_zh": "区块", "repeat_handling_zh": "区块嵌套于场次，不与场次共轴比较"},
        {"layer": "probe", "count": int(len(primary_probe)), "denominator": int(len(primary_probe)),
         "observation_unit_zh": "主探针事件", "repeat_handling_zh": "一probe一行；窗口敏感性不增加主样本量"},
        {"layer": "trial", "count": int(len(trial)), "denominator": int(len(trial)),
         "observation_unit_zh": "试次机会", "repeat_handling_zh": "仅用于派生指标分母，不作为独立参与者"},
    ])


def candidate_decision_table(metrics: Iterable[str]) -> pd.DataFrame:
    rows = []
    for metric in metrics:
        gate = "hard_gate" if metric in {"omission_rate", "commission_rate"} else "soft_recommendation"
        evidence = "separate Go/No-Go opportunity denominator contract" if metric in {"omission_rate", "commission_rate"} else "canonical multi-scale behavior metric contract"
        rows.append({"candidate": metric, "decision_class": gate, "decision": "eligible_for_review",
                     "evidence_source": evidence, "rule_version": SCHEMA_VERSION,
                     "review_status": "engineering_validated_only", "scientific_boundary": "not a validity or mechanism claim"})
    rows.append({"candidate": "Q2_formal_ordinal", "decision_class": "scientific_prohibited",
                 "decision": "blocked_until_clustered_ordinal_backend", "evidence_source": "behavior science v3 contract: unclustered OrderedModel forbidden",
                 "rule_version": SCHEMA_VERSION, "review_status": "hard_gate",
                 "scientific_boundary": "descriptive candidate only"})
    return pd.DataFrame(rows)


def _read_required_table(root: Path, name: str) -> pd.DataFrame:
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def run_formal_analysis(tables_dir: Path, output_dir: Path, cfg: AnalysisConfig | None = None) -> dict[str, Any]:
    """Run v3 on already-derived tables; never discovers raw cohorts or identity maps."""
    cfg = cfg or AnalysisConfig()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output_dir}")
    trial = _read_required_table(tables_dir, "trial_metrics.csv")
    windows = _read_required_table(tables_dir, "window_metrics.csv")
    block = _read_required_table(tables_dir, "block_metrics.csv")
    session = _read_required_table(tables_dir, "session_metrics.csv")
    trajectory = _read_required_table(tables_dir, "error_trajectory_metrics.csv")

    primary_probe, sensitivity = build_probe_analysis_tables(windows, cfg)
    for frame in (primary_probe, sensitivity, block, session, trajectory):
        if "participant_cluster_ref" not in frame and "anonymous_participant_group_id" in frame:
            frame["participant_cluster_ref"] = frame["anonymous_participant_group_id"].astype(str)
    pairs, pair_failures = build_b1_b2_pairs(block)
    error_resolved, error_overlaps = prepare_error_trajectories(trajectory, cfg)
    corr = build_correlation_evidence(session)
    q1_models, q1_failures = fit_q1_models(primary_probe, cfg)
    q2_desc, q2_failures = q2_gate(primary_probe)
    failures = pd.concat([pair_failures, q1_failures, q2_failures], ignore_index=True, sort=False)
    forest = build_forest_manifest(q1_models)
    qc = qc_denominator_table(trial, primary_probe, block, session)
    decisions = candidate_decision_table(CANONICAL_METRICS)
    folds = build_participant_disjoint_folds(primary_probe, cfg.prediction_folds)

    output_dir.mkdir(parents=True)
    outputs = {
        "probe_primary_metrics_v3.csv": primary_probe,
        "probe_window_sensitivity_v3.csv": sensitivity,
        "block_metrics_v3.csv": block,
        "session_metrics_v3.csv": session,
        "b1_b2_session_pairs_v3.csv": pairs,
        "error_trajectory_resolved_v3.csv": error_resolved,
        "error_overlap_audit_v3.csv": error_overlaps,
        "correlation_evidence_v3.csv": corr,
        "q1_model_results_v3.csv": q1_models,
        "q2_descriptive_v3.csv": q2_desc,
        "model_failures_v3.csv": failures,
        "forest_manifest_v3.csv": forest,
        "qc_denominators_v3.csv": qc,
        "candidate_decisions_v3.csv": decisions,
        "participant_disjoint_folds_v3.csv": folds,
    }
    hashes = {}
    for name, frame in outputs.items():
        path = output_dir / name
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        hashes[name] = _sha256(path)

    from .reporting import generate_chinese_report_assets
    figure_manifest, report_path = generate_chinese_report_assets(output_dir, primary_probe, block, session, qc, forest, failures)
    outputs["figure_manifest_v3.csv"] = figure_manifest

    participant = "participant_cluster_ref" if "participant_cluster_ref" in session else "anonymous_participant_group_id"
    session_per_participant = session[[participant, "session_id"]].drop_duplicates().groupby(participant).size()
    repeat_group_n = int(session_per_participant.eq(2).sum())
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "analysis_status": "v3_engineering_and_candidate_analysis",
        "formal_report_admission": "partial_only_where_model_formal_inference_true",
        "input_contract": "derived behavior tables only; no raw cohort discovery",
        "primary_probe_rule": "one probe event row at primary window; 10/20/30 sensitivity separate",
        "session_n": int(session.session_id.nunique()),
        "participant_group_n": int(session[participant].nunique()),
        "two_session_repeat_group_n": repeat_group_n,
        "cohort_counts_are_runtime_derived_not_hardcoded": True,
        "future_identity_remap_required": True,
        "go_omission_and_nogo_commission_modeled_separately": True,
        "q1_reference_category": cfg.q1_reference_category,
        "q2_formal_status": "blocked_without_clustered_ordinal_backend",
        "prediction_split": "participant_cluster_disjoint",
        "error_overlap_policy": cfg.error_overlap_policy,
        "error_baseline_offsets": list(cfg.error_baseline_offsets),
        "model_failure_rows": int(len(failures)),
        "formal_statistics_run": bool((q1_models.get("formal_inference", pd.Series(dtype=bool)) == True).any()),
        "engineering_validation_is_not_behavioral_validity": True,
        "mechanism_claims_authorized": False,
        "config": asdict(cfg),
        "output_sha256": hashes,
        "figure_manifest": "figure_manifest_v3.csv",
        "chinese_results_report": report_path.name,
    }
    manifest_path = output_dir / "report_manifest_v3.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="FocusWave behavior science v3 formal-analysis entrypoint")
    parser.add_argument("--tables-dir", type=Path, required=True, help="Directory containing derived behavior CSV tables")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--primary-window-seconds", type=int, default=PRIMARY_WINDOW_SECONDS)
    args = parser.parse_args(argv)
    cfg = AnalysisConfig(primary_window_seconds=args.primary_window_seconds)
    result = run_formal_analysis(args.tables_dir, args.output_dir, cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
