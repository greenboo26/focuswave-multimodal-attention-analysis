"""Attach existing Beijing NIR/mmWave features to the verified behavior timeline.

No identity recovery or raw-data processing is performed here. Existing C3
metadata crosswalk, NIR probe table, non-NIR feature table, and behavior probe
table are joined on subject + probe_id; absolute onset is audited.
"""
from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
import statsmodels.formula.api as smf


DERIVED = Path(r"D:\Project\厚粲杯\11_数据\derived")
BEHAVIOR = DERIVED / "beijing_c2_identity_reuse_event_analysis_v2/formal_behavior_longitudinal_v1/probe_event_level_behavior.csv"
NIR = DERIVED / "current_j_nir_mmwave_analysis_input_v2/current_j_nir_mmwave_analysis_input.csv"
CROSSWALK = DERIVED / "c3_identity_coverage_crosswalk_v1/identity_crosswalk.csv"
MMWAVE = DERIVED / "non_nir_window_analysis_input_v1/non_nir_window_analysis_input.csv"
OUT = DERIVED / "beijing_sensor_increment_v1"

BEHAVIOR_FEATURES = ["probe_progress", "block_num", "pre10_error_rate", "pre10_rt_median_ms", "pre10_rt_sd_ms"]
MMWAVE_FEATURES = ["br_bpm", "m1_micro_power_fraction", "m1_phase_std_cv_10s", "q_target_power_snr_db", "q_selection_margin", "q_phase_jump_fraction", "q_bin_stability_10s", "q_extraction_ok"]
NIR_FEATURES = ["nir_pupil_diameter_median", "nir_pupil_diameter_iqr", "nir_pupil_diameter_slope_per_s"]


def safe_name(text):
    return text.replace(" ", "_").replace("+", "plus")


def grouped_oof_auc(data, features):
    d = data.dropna(subset=features + ["target_label1", "repeat_participant_id"]).copy()
    d = d[d["target_label1"].isin([0, 1])]
    if d.empty or d["repeat_participant_id"].nunique() < 3 or d["target_label1"].nunique() < 2:
        return {"n_probe": len(d), "n_participant": d["repeat_participant_id"].nunique(), "auc": np.nan, "brier": np.nan, "status": "insufficient"}
    preds = []
    y_all = []
    groups = d["repeat_participant_id"].astype(str)
    for group in sorted(groups.unique()):
        train = d[groups != group]
        test = d[groups == group]
        # Only the training fold must contain both classes. A single-class
        # held-out participant still has valid probabilities and must remain in
        # pooled OOF AUC/Brier evaluation.
        if train["target_label1"].nunique() < 2:
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0, solver="liblinear"))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(train[features], train["target_label1"])
        preds.extend(model.predict_proba(test[features])[:, 1])
        y_all.extend(test["target_label1"])
    if len(set(y_all)) < 2:
        return {"n_probe": len(d), "n_participant": d["repeat_participant_id"].nunique(), "auc": np.nan, "brier": np.nan, "status": "no_valid_test_class"}
    return {"n_probe": len(d), "n_participant": d["repeat_participant_id"].nunique(), "auc": roc_auc_score(y_all, preds), "brier": brier_score_loss(y_all, preds), "status": "ok"}


def sensor_state_summary(data, features):
    rows = []
    for feature in features:
        d = data[["repeat_participant_id_final", "target_label1", "probe_progress", "block_num", feature]].copy()
        d = d.dropna()
        for state, g in d.groupby("target_label1"):
            rows.append({"feature": feature, "state": "完全任务聚焦" if state == 1 else "其他非完全任务聚焦", "n_probe": len(g), "n_participant": g["repeat_participant_id_final"].nunique(), "mean": g[feature].mean(), "sd": g[feature].std(ddof=1), "median": g[feature].median()})
        if d["target_label1"].nunique() < 2 or d["repeat_participant_id_final"].nunique() < 3:
            continue
        try:
            fit = smf.gee(f"{feature} ~ target_label1 + probe_progress + C(block_num)", groups="repeat_participant_id_final", data=d, cov_struct=sm.cov_struct.Exchangeable(), family=sm.families.Gaussian()).fit()
            coef = fit.params.get("target_label1", np.nan)
            ci = fit.conf_int().loc["target_label1"]
            rows.append({"feature": feature, "state": "adjusted_contrast", "n_probe": len(d), "n_participant": d["repeat_participant_id_final"].nunique(), "mean": coef, "sd": ci.iloc[0], "median": ci.iloc[1], "p_value": fit.pvalues.get("target_label1", np.nan)})
        except Exception:
            pass
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    behavior = pd.read_csv(BEHAVIOR)
    nir = pd.read_csv(NIR)
    crosswalk = pd.read_csv(CROSSWALK)
    mmwave = pd.read_csv(MMWAVE)

    # Reuse the existing resolved metadata crosswalk; no feature-based inference.
    cw = crosswalk[["nir_subject", "recording_id", "session_id", "single_experiment_id", "repeat_participant_id", "identity_status", "mapping_confidence"]].copy()
    nir = nir.merge(cw, left_on="subject", right_on="nir_subject", how="left", suffixes=("", "_crosswalk"))
    crosswalk_id = nir.get("repeat_participant_id_crosswalk", pd.Series(index=nir.index, dtype=object))
    nir["repeat_participant_id"] = crosswalk_id.combine_first(nir.get("repeat_participant_id"))
    nir["repeat_participant_id"] = nir["repeat_participant_id"].replace("", np.nan)
    nir.to_csv(OUT / "beijing_nir_probe_with_existing_identity.csv", index=False, encoding="utf-8-sig")

    b = behavior.copy()
    b["target_label1"] = pd.to_numeric(b["target_label1"], errors="coerce")
    b["probe_onset_ms_behavior"] = pd.to_numeric(b["probe_onset_time"], errors="coerce")
    n = nir.copy()
    n["probe_onset_ms_nir"] = pd.to_numeric(n["probe_onset_ms_nir"], errors="coerce")
    m = mmwave.copy()
    m["probe_onset_ms_mmw"] = pd.to_numeric(m["probe_onset_ms"], errors="coerce")
    if "mmwave_available" not in m.columns:
        m["mmwave_available"] = pd.to_numeric(m.get("q_extraction_ok", 0), errors="coerce").fillna(0).eq(1)

    # Keep only the fields needed for the common-probe analysis.
    b_cols = ["subject", "repeat_participant_id", "target_label1", "probe_onset_ms_behavior"] + BEHAVIOR_FEATURES
    n_cols = ["subject", "probe_id", "repeat_participant_id", "nir_quality_tier", "nir_include_primary", "nir_include_sensitivity", "probe_onset_ms_nir"] + NIR_FEATURES
    m_cols = ["subject", "probe_id", "repeat_participant_id", "probe_onset_ms_mmw", "quality", "mmwave_available"] + [x for x in MMWAVE_FEATURES if x in m.columns]
    # Behavior probe_event_level_behavior has no explicit probe_id. Use the
    # frozen absolute Unix-ms event time, then retain sensor probe_id for audit.
    common = b[b_cols].merge(n[n_cols], left_on=["subject", "probe_onset_ms_behavior"], right_on=["subject", "probe_onset_ms_nir"], how="left", suffixes=("", "_nir"))
    common = common.merge(m[m_cols], left_on=["subject", "probe_onset_ms_behavior"], right_on=["subject", "probe_onset_ms_mmw"], how="left", suffixes=("", "_mmwave"))
    mmw_id = common["repeat_participant_id_mmw"] if "repeat_participant_id_mmw" in common.columns else pd.Series(np.nan, index=common.index)
    nir_id = common["repeat_participant_id_nir"] if "repeat_participant_id_nir" in common.columns else pd.Series(np.nan, index=common.index)
    common["repeat_participant_id_final"] = common["repeat_participant_id"].fillna(nir_id).fillna(mmw_id)
    common["nir_identity_resolved"] = common["repeat_participant_id_nir"].notna()
    common["nir_onset_error_ms"] = common["probe_onset_ms_nir"] - common["probe_onset_ms_behavior"]
    common["mmwave_onset_error_ms"] = common["probe_onset_ms_mmw"] - common["probe_onset_ms_behavior"]
    common["nir_primary_eligible"] = common["nir_include_primary"].fillna(False).astype(bool) & common["nir_identity_resolved"]
    common["nir_sensitivity_eligible"] = common["nir_include_sensitivity"].fillna(False).astype(bool) & common["nir_identity_resolved"]
    common["mmwave_eligible"] = common["mmwave_available"].fillna(False).astype(bool)
    common.to_csv(OUT / "beijing_behavior_nir_mmwave_common_probe.csv", index=False, encoding="utf-8-sig")

    # Coverage is reported separately from model eligibility.
    coverage = []
    for name, mask in {
        "behavior_all": pd.Series(True, index=common.index),
        "nir_identity_resolved": common["nir_identity_resolved"],
        "nir_primary_ge80": common["nir_primary_eligible"],
        "nir_sensitivity_ge50": common["nir_sensitivity_eligible"],
        "mmwave_available": common["mmwave_eligible"],
        "nir_primary_and_mmwave": common["nir_primary_eligible"] & common["mmwave_eligible"],
    }.items():
        sub = common[mask]
        coverage.append({"set": name, "n_probe": len(sub), "n_subject": sub["subject"].nunique(), "n_participant": sub["repeat_participant_id_final"].dropna().nunique(), "n_session": sub["subject"].nunique()})
    pd.DataFrame(coverage).to_csv(OUT / "common_probe_coverage.csv", index=False, encoding="utf-8-sig")

    mmwave_features = BEHAVIOR_FEATURES + [x for x in MMWAVE_FEATURES if x in common.columns]
    both_mask = common["nir_primary_eligible"] & common["mmwave_eligible"]
    model_specs = [
        ("behavior_all", pd.Series(True, index=common.index), BEHAVIOR_FEATURES),
        ("behavior_base_mmwave_subset", common["mmwave_eligible"], BEHAVIOR_FEATURES),
        ("behavior_plus_mmwave", common["mmwave_eligible"], mmwave_features),
        ("behavior_base_nir_primary_subset", common["nir_primary_eligible"], BEHAVIOR_FEATURES),
        ("behavior_plus_nir_primary", common["nir_primary_eligible"], BEHAVIOR_FEATURES + NIR_FEATURES),
        ("behavior_base_both_primary_subset", both_mask, BEHAVIOR_FEATURES),
        ("behavior_plus_both_primary", both_mask, mmwave_features + NIR_FEATURES),
    ]
    rows = []
    for name, mask, features in model_specs:
        d = common[mask].copy()
        d = d.drop(columns=["repeat_participant_id"], errors="ignore").rename(columns={"repeat_participant_id_final": "repeat_participant_id"})
        result = grouped_oof_auc(d, features)
        result.update({"model": name, "features": ";".join(features)})
        rows.append(result)
    models = pd.DataFrame(rows)
    base_auc = models.set_index("model")["auc"]
    models["delta_auc_same_subset"] = np.nan
    same_subset_base = {
        "behavior_plus_mmwave": "behavior_base_mmwave_subset",
        "behavior_plus_nir_primary": "behavior_base_nir_primary_subset",
        "behavior_plus_both_primary": "behavior_base_both_primary_subset",
    }
    for model_name, base_name in same_subset_base.items():
        models.loc[models["model"] == model_name, "delta_auc_same_subset"] = models.loc[models["model"] == model_name, "auc"].iloc[0] - base_auc.get(base_name, np.nan)
    models.to_csv(OUT / "common_probe_incremental_models.csv", index=False, encoding="utf-8-sig")

    sensor_subset = common[common["nir_primary_eligible"] & common["mmwave_eligible"]].copy()
    sensor_summary = sensor_state_summary(sensor_subset, [x for x in MMWAVE_FEATURES + NIR_FEATURES if x in sensor_subset.columns])
    sensor_summary.to_csv(OUT / "sensor_state_group_summary_primary_common.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "run_id": "BEIJING_SENSOR_INCREMENT_V1",
        "inputs": {"behavior": str(BEHAVIOR), "nir": str(NIR), "identity_crosswalk": str(CROSSWALK), "mmwave": str(MMWAVE)},
        "join_key": "subject + exact absolute Unix-ms probe onset; sensor probe_id retained for audit because behavior event table has no explicit probe_id",
        "identity_policy": "reuse c3_identity_coverage_crosswalk_v1; no feature-based or new identity recovery",
        "model": "participant-disjoint leave-one-repeat-participant-out logistic regression with fixed standardized features",
        "behavior_features": BEHAVIOR_FEATURES,
        "mmwave_features": MMWAVE_FEATURES,
        "nir_features": NIR_FEATURES,
        "hrv_claim": False,
        "status": "common-probe integration and incremental baseline complete",
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"common_rows": len(common), "coverage": coverage, "models": rows}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
