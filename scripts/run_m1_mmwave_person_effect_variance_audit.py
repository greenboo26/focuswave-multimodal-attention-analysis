"""M1: variance audit for the frozen C2b-v2/C2C mmWave feature family.

This diagnostic deliberately consumes existing 30-s probe features only.  It
does not open J:\\Data, recreate radar features, fit a prediction model, or
change the C2C calibration.  ``group_subject_id`` is the established repeat
participant identity and ``subject`` is the formal session identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(r"D:\Project\厚粲杯")
C2B = ROOT / "11_数据" / "derived" / "c2b_v2_canonical_baselines_20260826"
C2C = ROOT / "11_数据" / "derived" / "c2c_within_subject_normalization_v1"
OUT = ROOT / "11_数据" / "derived" / "m1_mmwave_person_effect_variance_audit_v1"
W = [
    "m1_phase_std_rad", "m1_phase_velocity_mad", "m1_phase_accel_mad",
    "m1_log_power_low", "m1_log_power_transition", "m1_log_power_micro",
    "m1_log_power_high", "m1_micro_power_fraction", "m1_phase_peak_micro_hz",
    "m1_micro_peak_share", "m1_micro_spectral_entropy", "m1_harmonic_overlap",
    "m1_harmonic_power_fraction", "m1_phase_trend_rad_s", "q_target_power_snr_db",
    "q_target_amplitude_cv", "q_phase_jump_fraction", "q_frame_gap_fraction",
    "q_frame_gap_duration_fraction", "q_frame_rate_hz", "q_selection_margin",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def fit_components(frame: pd.DataFrame, value: str, adjusted: bool) -> dict:
    """REML nested random-intercept decomposition with explicit non-estimate state."""
    d = frame[["participant_id", "session_id", "block_num", "block_probe_fraction", value]].copy()
    d[value] = pd.to_numeric(d[value], errors="coerce")
    d["block_num"] = pd.to_numeric(d["block_num"], errors="coerce")
    d["block_probe_fraction"] = pd.to_numeric(d["block_probe_fraction"], errors="coerce")
    need = ["participant_id", "session_id", value]
    if adjusted:
        need += ["block_num", "block_probe_fraction"]
    d = d.dropna(subset=need).copy()
    base = {
        "n_probe": len(d), "n_session": int(d.session_id.nunique()),
        "n_participant": int(d.participant_id.nunique()), "adjusted": adjusted,
    }
    repeated_people = d.groupby("participant_id").session_id.nunique()
    if len(d) < 8 or d.session_id.nunique() < 3 or d.participant_id.nunique() < 2 or (repeated_people >= 2).sum() < 2:
        return {**base, "status": "not_estimable_insufficient_nested_repetition"}
    formula = f"Q('{value}') ~ 1" + (" + C(block_num) + block_probe_fraction" if adjusted else "")
    try:
        model = smf.mixedlm(
            formula, d, groups=d["participant_id"], re_formula="1",
            vc_formula={"session_within_person": "0 + C(session_id)"},
        )
        # Boundary estimates are scientifically meaningful here (a component can
        # be near zero).  A deterministic derivative-free retry is used only
        # when L-BFGS fails to converge; the same likelihood/model is retained.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = model.fit(reml=True, method="lbfgs", maxiter=1000, disp=False)
            if not bool(result.converged):
                result = model.fit(reml=True, method="powell", maxiter=3000, disp=False)
        participant = max(float(np.asarray(result.cov_re)[0, 0]), 0.0)
        session = max(float(result.vcomp[0]), 0.0) if len(result.vcomp) else np.nan
        probe = max(float(result.scale), 0.0)
        total = participant + session + probe
        if not np.isfinite(total) or total <= 0:
            return {**base, "status": "not_estimable_nonpositive_total_variance"}
        return {
            **base, "status": "ok" if bool(result.converged) else "fit_not_converged_use_with_caution",
            "participant_variance": participant, "session_within_person_variance": session,
            "within_session_probe_variance": probe, "total_variance": total,
            "icc_person": participant / total, "session_variance_proportion": session / total,
            "probe_variance_proportion": probe / total,
        }
    except Exception as exc:
        return {**base, "status": f"not_estimable_{type(exc).__name__}"}


def analyse(frame: pd.DataFrame, family: str, scale: str, adjusted: bool) -> pd.DataFrame:
    rows = []
    for feature in W:
        value = feature if scale == "absolute" else f"within_z__{feature}"
        r = fit_components(frame, value, adjusted)
        r.update({"feature": feature, "feature_value_column": value, "feature_family": family, "scale": scale})
        rows.append(r)
    return pd.DataFrame(rows)


def similarity(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Session centroid pairs after robust global scaling; no identifiers leave the summary."""
    d = frame[["participant_id", "session_id", *W]].copy()
    for f in W:
        d[f] = pd.to_numeric(d[f], errors="coerce")
        med = d[f].median()
        mad = (d[f] - med).abs().median()
        d[f] = (d[f] - med) / (1.4826 * mad) if np.isfinite(mad) and mad > 0 else np.nan
    centroids = d.groupby(["participant_id", "session_id"], as_index=False)[W].mean()
    # Mean imputation is only for pairwise centroid geometry, never for variance models.
    centroids[W] = centroids[W].fillna(centroids[W].mean())
    pairs = []
    values = centroids[W].to_numpy(float)
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            a, b = values[i], values[j]
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            cosine = float(np.dot(a, b) / denom) if denom > 0 else np.nan
            corr = float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else np.nan
            pairs.append({
                "pair_type": "within_person" if centroids.participant_id.iat[i] == centroids.participant_id.iat[j] else "between_person",
                "euclidean_distance": float(np.linalg.norm(a - b)), "cosine_similarity": cosine,
                "feature_profile_correlation": corr,
            })
    pair_df = pd.DataFrame(pairs)
    summary = pair_df.groupby("pair_type").agg(
        n_pairs=("pair_type", "size"),
        mean_distance=("euclidean_distance", "mean"), median_distance=("euclidean_distance", "median"),
        mean_cosine_similarity=("cosine_similarity", "mean"), median_cosine_similarity=("cosine_similarity", "median"),
        mean_feature_profile_correlation=("feature_profile_correlation", "mean"),
        median_feature_profile_correlation=("feature_profile_correlation", "median"),
    ).reset_index()
    eligible = centroids.groupby("participant_id").session_id.nunique()
    coverage = pd.DataFrame([{
        "pair_type": "coverage", "n_pairs": int((eligible >= 2).sum()),
        "mean_distance": np.nan, "median_distance": np.nan, "mean_cosine_similarity": np.nan,
        "median_cosine_similarity": np.nan, "mean_feature_profile_correlation": np.nan,
        "median_feature_profile_correlation": np.nan,
        "note": "n_pairs is participants with at least two eligible formal sessions; pair rows are intentionally not exported",
    }])
    return pd.concat([summary, coverage], ignore_index=True), pair_df


def render_report(out: Path, icc: pd.DataFrame, compare: pd.DataFrame, variance: pd.DataFrame, sim: pd.DataFrame, manifest: dict) -> None:
    absolute_common = compare[compare.status.str.startswith("ok") | compare.status.eq("fit_not_converged_use_with_caution")]
    med_abs = absolute_common.icc_absolute.median(); med_within = absolute_common.icc_within.median(); med_delta = absolute_common.delta_icc.median()
    strongest = absolute_common.sort_values("icc_absolute", ascending=False).iloc[0]
    raw = icc.query("feature_family == 'C2b-v2_all_sessions' and scale == 'absolute' and adjusted == False")
    raw_ok = raw[raw.status.isin(["ok", "fit_not_converged_use_with_caution"])]
    adj = variance.query("scale == 'absolute' and adjusted == True")
    adj_ok = adj[adj.status.isin(["ok", "fit_not_converged_use_with_caution"])]
    raw_med = raw_ok.icc_person.median(); adj_med = adj_ok.icc_person.median()
    # Decision is prespecified to prevent a label selected from a single exceptional feature.
    if med_abs >= 0.20 and med_within <= 0.10 and med_delta <= -0.10:
        decision = "A STRONG_PERSON_EFFECT_REMOVED_BY_CALIBRATION"
    elif med_within >= 0.20:
        decision = "B STRONG_PERSON_EFFECT_PERSISTS_AFTER_CALIBRATION"
    else:
        decision = "C LIMITED_STABLE_PERSON_EFFECT_IN_CURRENT_FEATURES"
    s = sim.set_index("pair_type")
    lines = [
        "# M1 mmWave person-effect variance audit", "", f"## Final decision: `{decision}`", "",
        "This is a diagnostic of the frozen 30-s C2b-v2/C2C W feature family, not a physiological identity claim or a predictive-model result.", "",
        "## Inputs and identity", "",
        f"- C2b-v2 input: `{manifest['inputs']['c2b_30s']['path']}` ({manifest['inputs']['c2b_30s']['rows']} rows).",
        f"- C2C input: `{manifest['inputs']['c2c_30s']['path']}` ({manifest['inputs']['c2c_30s']['rows']} rows total; {manifest['c2c_common_rows']} existing within-calibrated rows from {manifest['c2c_common_sessions']} sessions and {manifest['c2c_common_participants']} participants); C2C CURRENT primary window is 30 s.",
        "- Identity convention fixed by C2b/C2C: `group_subject_id` = repeat participant; `subject` = formal session. The audit retains these only locally and exports no identifiers.",
        f"- Feature family: {len(W)} pre-existing m1/q probe features; missing values are listwise excluded feature-by-feature, never re-extracted or imputed for variance components.", "",
        "## Three-level variance decomposition", "",
        "For each feature, REML linear mixed model: `feature ~ 1 + (1|repeat_participant_id) + (1|repeat_participant_id:session_id)`. Residual is within-session/probe variance. ICC_person is participant variance / total variance; session proportion is session-within-person variance / total variance.",
        f"- C2b-v2 all-session absolute ICC: median {raw_med:.3f}, IQR [{raw_ok.icc_person.quantile(.25):.3f}, {raw_ok.icc_person.quantile(.75):.3f}] across {len(raw_ok)}/{len(W)} estimable features.",
        f"- Highest all-session absolute ICC: `{raw_ok.sort_values('icc_person', ascending=False).iloc[0].feature}` = {raw_ok.icc_person.max():.3f}. Near-zero (ICC < .01): {', '.join(raw_ok.loc[raw_ok.icc_person < .01, 'feature'].tolist()) or 'none'}.", "",
        "## Calibration comparison on the same C2C-covered probe cohort", "",
        f"- Median ICC_absolute = {med_abs:.3f}; median ICC_within = {med_within:.3f}; median ΔICC (within - absolute) = {med_delta:.3f}.",
        f"- Strongest absolute feature in the common cohort: `{strongest.feature}` (absolute {strongest.icc_absolute:.3f}, within {strongest.icc_within:.3f}, Δ {strongest.delta_icc:.3f}).", "",
        "## Context-adjusted sensitivity", "",
        "The sensitivity model adds frozen block as a categorical fixed effect and `block_probe_fraction` as within-block/experiment progress. It intentionally removes predictable task context before allocating residual stable between-person variation.",
        f"- Median absolute ICC: raw {raw_med:.3f}, context-adjusted {adj_med:.3f}; change {adj_med - raw_med:+.3f}.", "",
        "## Cross-session centroid geometry", "",
        "Centroids are session means of the 21 absolute features after robust global (median/MAD) feature scaling. Distances and correlations are descriptive, not identity-classifier accuracy.",
        f"- Eligible repeat participants (>=2 formal sessions): {int(s.loc['coverage', 'n_pairs'])}.",
        f"- Within person: {int(s.loc['within_person', 'n_pairs'])} pairs, median distance {s.loc['within_person', 'median_distance']:.3f}, median cosine {s.loc['within_person', 'median_cosine_similarity']:.3f}, median profile correlation {s.loc['within_person', 'median_feature_profile_correlation']:.3f}.",
        f"- Between person: {int(s.loc['between_person', 'n_pairs'])} pairs, median distance {s.loc['between_person', 'median_distance']:.3f}, median cosine {s.loc['between_person', 'median_cosine_similarity']:.3f}, median profile correlation {s.loc['between_person', 'median_feature_profile_correlation']:.3f}.", "",
        "## Limits", "",
        "- C2C baseline extraction covered 70/72 sessions, but the all-21-feature complete within-z comparison has 59 sessions because a zero/missing session MAD makes at least one within-z undefined. This deterministic availability restriction is reported rather than repaired or imputed.",
        "- Variance components are feature-wise Gaussian mixed-model summaries. Features with non-convergence are retained with an explicit caution status; failed estimates are not silently replaced.",
        "- Baseline robust-z calibrates against a session's own resting distribution. A lower ICC therefore indicates reduced stable scale/location differences in these features, not proof that all person-specific signal has disappeared.",
    ]
    (out / "M1_MMWAVE_PERSON_EFFECT_VARIANCE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest["decision"] = decision
    manifest["summary"] = {"median_icc_absolute_common": safe_float(med_abs), "median_icc_within": safe_float(med_within), "median_delta_icc": safe_float(med_delta), "strongest_feature": strongest.feature}
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    default_public = Path(__file__).resolve().parents[1] / "docs" / "results" / "m1_mmwave_person_effect_variance_audit_v1"
    ap = argparse.ArgumentParser(); ap.add_argument("--output", type=Path, default=OUT); ap.add_argument("--public-output", type=Path, default=default_public); args = ap.parse_args(); out = args.output; out.mkdir(parents=True, exist_ok=True)
    p2b = C2B / "window_30s" / "canonical_feature_matrix_local.csv"; p2c = C2C / "c2c_feature_matrix_local_30s.csv"
    absolute = pd.read_csv(p2b, dtype={"subject": str, "group_subject_id": str})
    c2c = pd.read_csv(p2c, dtype={"subject": str, "group_subject_id": str})
    for d in (absolute, c2c):
        d["session_id"] = d["subject"].astype(str).str.zfill(3); d["participant_id"] = d["group_subject_id"].astype(str)
    # C2C common cohort is defined only by existing robust-z availability; absolute values are retained unchanged.
    common = c2c[c2c["within_available"].eq(1)].copy()
    icc_all = analyse(absolute, "C2b-v2_all_sessions", "absolute", False)
    icc_common_abs = analyse(common, "C2C_common_cohort", "absolute", False)
    icc_common_within = analyse(common, "C2C_common_cohort", "within", False)
    context = analyse(absolute, "C2b-v2_all_sessions", "absolute", True)
    icc = pd.concat([icc_all, icc_common_abs, icc_common_within], ignore_index=True)
    icc.to_csv(out / "mmwave_feature_person_icc.csv", index=False, encoding="utf-8-sig")
    variance = pd.concat([icc_all, context], ignore_index=True)
    variance.to_csv(out / "mmwave_variance_components.csv", index=False, encoding="utf-8-sig")
    compare = icc_common_abs[["feature", "icc_person", "session_variance_proportion", "status", "n_probe", "n_session", "n_participant"]].merge(
        icc_common_within[["feature", "icc_person", "session_variance_proportion", "status"]], on="feature", suffixes=("_absolute", "_within"), how="outer"
    )
    compare = compare.rename(columns={"icc_person_absolute": "icc_absolute", "icc_person_within": "icc_within", "session_variance_proportion_absolute": "session_proportion_absolute", "session_variance_proportion_within": "session_proportion_within", "status_absolute": "status"})
    compare["delta_icc"] = compare.icc_within - compare.icc_absolute
    compare.to_csv(out / "mmwave_absolute_vs_within_icc.csv", index=False, encoding="utf-8-sig")
    sim, _local_pairs = similarity(common)
    sim.to_csv(out / "mmwave_cross_session_similarity.csv", index=False, encoding="utf-8-sig")
    plot = compare.sort_values("icc_absolute")
    fig, ax = plt.subplots(figsize=(8, 7)); ax.scatter(plot.icc_absolute, plot.icc_within, color="#247ba0", s=42)
    # Labels are reserved for non-trivial ICCs to keep the report figure legible.
    for _, r in plot.loc[plot[["icc_absolute", "icc_within"]].max(axis=1).ge(.05)].iterrows():
        ax.annotate(r.feature.replace("m1_", "").replace("q_", ""), (r.icc_absolute, r.icc_within), fontsize=6, alpha=.8)
    high = max(float(np.nanmax(plot.icc_absolute)), float(np.nanmax(plot.icc_within)), .05); ax.plot([0, high], [0, high], "--", color="#777777", linewidth=1)
    ax.set(xlabel="Participant ICC: absolute feature", ylabel="Participant ICC: within-calibrated feature", xlim=(0, high * 1.08), ylim=(0, high * 1.08), title="M1: C2C resting calibration and stable person variance")
    fig.tight_layout(); fig.savefig(out / "absolute_vs_within_calibrated_icc.png", dpi=300); plt.close(fig)
    manifest = {"analysis": "M1_MMWAVE_PERSON_EFFECT_VARIANCE_AUDIT", "created_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform(), "identity": {"repeat_participant_id": "group_subject_id", "session_id": "subject"}, "inputs": {"c2b_30s": {"path": str(p2b), "sha256": sha256(p2b), "rows": len(absolute), "fields": list(absolute.columns)}, "c2c_30s": {"path": str(p2c), "sha256": sha256(p2c), "rows": len(c2c), "fields": list(c2c.columns)}}, "c2c_common_rows": len(common), "c2c_common_sessions": int(common.session_id.nunique()), "c2c_common_participants": int(common.participant_id.nunique()), "features": W, "missing_handling": "feature-wise listwise deletion for mixed models; centroid geometry uses global feature mean only after centroid construction", "minimum_repeat_session_condition": "cross-session within-person pairs require >=2 C2C-covered formal sessions; variance model requires >=2 participants with >=2 sessions", "context_sensitivity": "fixed C(block_num) + block_probe_fraction"}
    render_report(out, icc, compare, variance, sim, manifest)
    # The committed package has only feature/pair-type aggregates and provenance.
    # Local C2b/C2C matrices and identities stay in D:\\Project derived storage.
    args.public_output.mkdir(parents=True, exist_ok=True)
    for name in ["mmwave_feature_person_icc.csv", "mmwave_absolute_vs_within_icc.csv", "mmwave_variance_components.csv", "mmwave_cross_session_similarity.csv", "M1_MMWAVE_PERSON_EFFECT_VARIANCE_AUDIT.md", "absolute_vs_within_calibrated_icc.png", "run_manifest.json"]:
        shutil.copy2(out / name, args.public_output / name)


if __name__ == "__main__": main()
