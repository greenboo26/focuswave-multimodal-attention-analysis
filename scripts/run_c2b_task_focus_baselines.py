"""C2b frozen task-focus baselines on the existing 30 s feature matrix.

This is deliberately a simple, grouped out-of-fold benchmark. It does not
read raw video/ADC, does not use HRV features, and does not tune on test folds.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, matthews_corrcoef,
                             precision_score, recall_score, roc_auc_score,
                             brier_score_loss)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MATRIX = Path(r"D:\Project\厚粲杯\11_数据\derived\j_m1_q0_71_rerun_v1\m1_q0_probe_matrix.csv")
MASTER = Path(r"D:\Project\厚粲杯\11_数据\derived\analysis_tables_v2\subject_session_master_v2.csv")
OUT = Path(r"D:\Project\厚粲杯\11_数据\derived\c2b_task_focus_baselines_v1")
SEED = 20260826


def metrics(y, p, threshold=0.5):
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)),
        "positive_n": int(y.sum()),
        "positive_rate": float(np.mean(y)),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else np.nan,
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else np.nan,
        "precision": float(precision_score(y, pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(MATRIX)
    master = pd.read_csv(MASTER, dtype=str)
    master["subject"] = master["single_experiment_id"].str.zfill(3)
    cross = master.drop_duplicates("subject").set_index("subject")["repeat_participant_id"].to_dict()
    df["subject"] = df["subject"].astype(str).str.zfill(3)
    df["group_subject_id"] = df["subject"].map(cross)
    df = df[df["group_subject_id"].notna()].copy()
    df["y"] = (df["label"] != 1).astype(int)
    df["probe_key"] = df["subject"] + "|" + df["block_num"].astype(str) + "|" + df["probe_id"].astype(str)

    context = ["block_num", "block_probe_fraction", "onset_rel_s"]
    behavior = ["prior_rt_mean", "prior_n_err"]
    basic = ["hr_bpm", "br_bpm", "q_extraction_ok", "q_frame_gap_fraction", "q_target_power_snr_db"]
    extended = [c for c in df.columns if c.startswith("m1_") or c.startswith("q_")]
    extended = [c for c in extended if c not in {"q_target_bin", "q_target_channel"} and c not in {"m1_window_start_ms", "m1_window_end_ms"}]
    sets = {
        "M0_context_only": context,
        "M1_behavior_only": context + behavior,
        "M2_mmwave_basic": context + basic,
        "M3_mmwave_extended": list(dict.fromkeys(context + basic + extended)),
        "M4_behavior_plus_mmwave": list(dict.fromkeys(context + behavior + basic + extended)),
    }
    groups = df["group_subject_id"].values
    y = df["y"].values
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = np.full(len(df), -1, dtype=int)
    for fold, (_, test) in enumerate(splitter.split(df, y, groups)):
        folds[test] = fold
    df["fold"] = folds
    df[["subject", "group_subject_id", "probe_key", "fold", "y"]].to_csv(OUT / "c2b_fold_assignments.csv", index=False)

    all_metrics, all_pred, importance = [], [], []
    for set_name, features in sets.items():
        X = df[features].apply(pd.to_numeric, errors="coerce")
        for model_name in ["dummy_prevalence", "logistic_l2", "hist_gradient_boosting"]:
            pred = np.full(len(df), np.nan)
            coefs = []
            for fold in range(5):
                train = folds != fold
                test = folds == fold
                if model_name == "dummy_prevalence":
                    pred[test] = y[train].mean()
                    continue
                if model_name == "logistic_l2":
                    model = Pipeline([("imp", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=SEED))])
                else:
                    model = Pipeline([("imp", SimpleImputer(strategy="median")), ("model", HistGradientBoostingClassifier(max_iter=100, learning_rate=0.05, max_leaf_nodes=7, l2_regularization=1.0, random_state=SEED))])
                model.fit(X.loc[train], y[train])
                pred[test] = model.predict_proba(X.loc[test])[:, 1]
                if model_name == "logistic_l2":
                    coefs.append(model.named_steps["model"].coef_[0])
            row = {"feature_set": set_name, "model": model_name, **metrics(y, pred)}
            row["n_features"] = len(features)
            all_metrics.append(row)
            all_pred.append(pd.DataFrame({"feature_set": set_name, "model": model_name, "subject": df["subject"], "group_subject_id": df["group_subject_id"], "probe_key": df["probe_key"], "fold": folds, "y": y, "prediction": pred}))
            if model_name == "logistic_l2":
                coef_mean = np.nanmean(np.vstack(coefs), axis=0) if coefs else np.full(len(features), np.nan)
                importance.extend({"feature_set": set_name, "feature": f, "mean_abs_coefficient": float(abs(c))} for f, c in zip(features, coef_mean))

    pd.DataFrame(all_metrics).to_csv(OUT / "c2b_model_metrics.csv", index=False)
    pd.concat(all_pred, ignore_index=True).to_csv(OUT / "c2b_oof_predictions.csv", index=False)
    pd.DataFrame(importance).to_csv(OUT / "c2b_feature_importance.csv", index=False)
    schema = []
    for name, features in sets.items():
        schema.extend({"feature_set": name, "feature": f, "source": "existing 30 s M1/Q0 matrix", "hrv_core": False} for f in features)
    pd.DataFrame(schema).drop_duplicates().to_csv(OUT / "c2b_feature_schema.csv", index=False)
    pd.DataFrame([{ "window_s": 10, "status": "not_available", "reason": "no equivalent precomputed 10 s feature matrix; not reconstructed from test results"}, {"window_s": 30, "status": "primary_completed", "reason": "existing M1/Q0 feature matrix"}, {"window_s": 60, "status": "not_available", "reason": "no equivalent precomputed 60 s feature matrix; not reconstructed from test results"}]).to_csv(OUT / "c2b_window_sensitivity.csv", index=False)
    pd.DataFrame(all_metrics).query("feature_set == 'M1_behavior_only' or feature_set == 'M4_behavior_plus_mmwave'").to_csv(OUT / "c2b_matched_subset_metrics.csv", index=False)
    manifest = {"status": "C2B_TASK_FOCUS_BASELINES_COMPLETE_WITH_WINDOW_BLOCKERS", "primary_window_s": 30, "sensitivity_windows_s": [10, 60], "label": "positive=non_fully_task_focused; probe_response in {2,3,4}", "grouping": "5-fold StratifiedGroupKFold by group_subject_id", "n_rows": int(len(df)), "n_groups": int(df["group_subject_id"].nunique()), "n_sessions": int(df["subject"].nunique()), "excluded_hrv": True, "excluded_rgb_nir": True, "notes": ["Existing reusable matrix has 1317 rows/71 sessions, not the full 1440-probe C2a manifest.", "10 s and 60 s sensitivity matrices are not available and were not reconstructed."], "seed": SEED}
    (OUT / "c2b_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = """# C2b task-focus baselines\n\n状态：`C2B_TASK_FOCUS_BASELINES_COMPLETE_WITH_WINDOW_BLOCKERS`\n\n主标签：`probe_response=1`（fully task-focused）对 `2/3/4`（non-fully task-focused）。主窗口为 probe 前 30 s。分组单位为 `group_subject_id`，使用 5-fold StratifiedGroupKFold；所有填补、标准化和模型拟合均在训练 fold 内完成。\n\n本轮实际复用的 M1/Q0 特征矩阵包含 1,317 probes、71 sessions、46 groups，因此不是 C2a 的完整 1,440-probe manifest。10 s/60 s 等价特征矩阵尚未生成，敏感性分析不能声称已完成。\n\n模型：M0 context-only、M1 behavior-only、M2 mmWave-basic、M3 mmWave-extended、M4 behavior+mmWave；每组包含 prevalence dummy、L2 logistic regression 和 HistGradientBoosting。IBI/RMSSD/SDNN、RGB、NIR 和深度模型均未使用。\n\n完整指标、OOF predictions、fold assignments 和 feature schema 位于同目录；OOF predictions 与 fold assignments 仅保留本地，不上传 GitHub。\n"""
    (OUT / "C2B_BASELINE_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
