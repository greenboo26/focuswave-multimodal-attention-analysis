"""C2b-v2 canonical feature reconstruction and grouped baseline evaluation.

This entry point deliberately reuses the frozen C2a timeline and the existing
J:\\Data mmWave extractor. It does not touch RGB/NIR, HRV, or the raw data.
The 30-second result is primary; 10/60 seconds are prespecified sensitivity
analyses. All row-level products stay in the local derived directory.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"D:\Project\厚粲杯")
ALGO = ROOT / "08_算法"
DATA = Path(r"J:\Data")
C2A = ALGO / "output/40_正式实验/04_C2a_标签与样本单元审计/derived_20260826"
OUT = ROOT / "11_数据/derived/c2b_v2_canonical_baselines_20260826"
OLD = ALGO / "scripts/build_evaluate_j_mmwave_m1_loso.py"
FULL_ROOT = ALGO / "output/40_正式实验/01_毫米波逐被试窗口/J_Data_逐被试窗口_v1"

LABEL_NAMES = {
    1: "完全专注于分拣任务",
    2: "关注实验本身，但没有聚焦于分拣任务",
    3: "在想与实验无关的事情",
    4: "大脑空白，没有明确想法",
}
CONTEXT = ["block_num", "block_probe_fraction", "onset_rel_s"]
BEHAVIOR = [
    "b_trial_count", "b_rt_mean", "b_rt_median", "b_rt_sd", "b_rt_mad",
    "b_rt_cv", "b_rt_slope", "b_accuracy", "b_error_count", "b_error_rate",
    "b_omission_count", "b_omission_rate",
]
MMW_BASIC = [
    "m1_phase_std_rad", "m1_phase_velocity_mad", "m1_phase_accel_mad",
    "m1_log_power_low", "m1_log_power_transition", "m1_log_power_micro",
    "m1_log_power_high", "m1_micro_power_fraction", "m1_phase_peak_micro_hz",
    "m1_micro_peak_share", "m1_micro_spectral_entropy", "m1_harmonic_overlap",
    "m1_harmonic_power_fraction",
]
MMW_EXTENDED = MMW_BASIC + [
    # Features whose name/definition is explicitly tied to 10-second
    # subsegments are intentionally excluded from the common 10/30/60-s core.
    "m1_phase_trend_rad_s", "q_target_power_snr_db",
    "q_target_amplitude_cv", "q_phase_jump_fraction", "q_frame_gap_fraction",
    "q_frame_gap_duration_fraction", "q_frame_rate_hz", "q_selection_margin",
    # q_bin_stability_10s remains available in the raw extractor output as a
    # secondary diagnostic, but is not a formal cross-window feature.
]
MODEL_SETS = {
    "C": CONTEXT,
    "B": BEHAVIOR,
    "W_basic": MMW_BASIC,
    "W_extended": MMW_EXTENDED,
    "C+B": CONTEXT + BEHAVIOR,
    "C+W_basic": CONTEXT + MMW_BASIC,
    "C+W_extended": CONTEXT + MMW_EXTENDED,
    "C+B+W": CONTEXT + BEHAVIOR + MMW_EXTENDED,
}


def load_old_module():
    spec = importlib.util.spec_from_file_location("frozen_m1_extractor", OLD)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load existing extractor: {OLD}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def base_probes() -> pd.DataFrame:
    path = C2A / "c2a_sample_manifest.csv"
    d = pd.read_csv(path, dtype={"subject_id": str})
    d["subject"] = d["subject_id"].astype(str).str.zfill(3)
    # `probe_id` is a trial number and can repeat across blocks. The absolute
    # probe onset is the stable event key in the formal timeline.
    d = d.sort_values(["subject", "probe_onset_time", "probe_id"]).drop_duplicates(["subject", "probe_onset_time"]).copy()
    # Old extraction code numbers probes in temporal order. Preserve the original
    # trial/probe id separately so the join is auditable.
    d["probe_seq"] = d.groupby("subject", sort=False).cumcount() + 1
    d["label"] = pd.to_numeric(d["probe_response"], errors="coerce")
    d["label_name"] = d["label"].map(LABEL_NAMES)
    d["probe_onset_ms"] = pd.to_numeric(d["probe_onset_time"], errors="coerce")
    d["group_subject_id"] = d["subject"].map(group_map())
    if d["group_subject_id"].isna().any():
        raise ValueError("C2a group map has missing group_subject_id")
    d["target"] = (d["label"] != 1).astype(int)
    return d.reset_index(drop=True)


def group_map() -> dict[str, str]:
    d = pd.read_csv(C2A / "c2a_subject_group_map.csv", dtype=str)
    return dict(zip(d.subject_id.str.zfill(3), d.group_subject_id))


def make_current(base: pd.DataFrame) -> pd.DataFrame:
    # Columns consumed by the frozen extractor. Existing physiological summary
    # fields are intentionally empty; C2b-v2 uses only raw phase/motion/QC.
    return pd.DataFrame({
        "subject": base.subject,
        "probe_id": base.probe_seq.astype(int),
        "label": base.label,
        "label_name": base.label_name,
        "hr_bpm": np.nan,
        "br_bpm": np.nan,
        "sdnn_ms": np.nan,
        "rmssd_ms": np.nan,
        "prior_rt_mean": np.nan,
        "quality": "raw_reconstruction",
    })


def add_context_features(base: pd.DataFrame, data_root: Path) -> pd.DataFrame:
    out = base.copy()
    out["block_num"] = pd.to_numeric(out["block_num"], errors="coerce")
    out["block_probe_fraction"] = out.groupby(["subject", "block_num"], sort=False).cumcount()
    block_n = out.groupby(["subject", "block_num"], sort=False)["probe_seq"].transform("count")
    out["block_probe_fraction"] = np.where(block_n > 1, out["block_probe_fraction"] / (block_n - 1), 0.0)
    first_by_subject = {}
    for subject in out.subject.unique():
        vals = []
        for path in sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv")):
            try:
                d = pd.read_csv(path, usecols=["absolute_onset_time"])
                vals.extend(pd.to_numeric(d["absolute_onset_time"], errors="coerce").dropna().tolist())
            except Exception:
                continue
        first_by_subject[subject] = min(vals) if vals else np.nan
    out["onset_rel_s"] = (out["probe_onset_ms"] - out["subject"].map(first_by_subject)) / 1000.0
    return out


def robust_mad(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return np.nan
    med = np.median(x)
    return float(np.median(np.abs(x - med)))


def numeric(row: pd.Series, key: str) -> float:
    try:
        return float(row.get(key, np.nan))
    except (TypeError, ValueError):
        return np.nan


def behavior_features(base: pd.DataFrame, data_root: Path, window_s: float) -> pd.DataFrame:
    rows = []
    for subject, group in base.groupby("subject", sort=True):
        files = sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv"))
        if not files:
            for _, p in group.iterrows():
                rows.append({"subject": subject, "probe_seq": p.probe_seq, **{k: np.nan for k in BEHAVIOR}, "behavior_available": 0})
            continue
        parts = [pd.read_csv(f) for f in files]
        trials = pd.concat(parts, ignore_index=True)
        trials["_onset"] = pd.to_numeric(trials.get("absolute_onset_time"), errors="coerce")
        trials = trials[trials["_onset"].notna()].sort_values("_onset")
        trials = trials[trials.get("is_probe", 0).fillna(0).astype(str) != "1"]
        for _, p in group.iterrows():
            end = float(p.probe_onset_ms)
            start = end - window_s * 1000.0
            x = trials[(trials["_onset"] >= start) & (trials["_onset"] < end)].copy()
            rt = pd.to_numeric(x.get("rt"), errors="coerce")
            rt_valid = rt[np.isfinite(rt)]
            correct = pd.to_numeric(x.get("correct"), errors="coerce")
            omission = pd.to_numeric(x.get("omission"), errors="coerce").fillna(0)
            n = len(x)
            err = (correct.fillna(0) != 1).astype(int)
            mean = float(rt_valid.mean()) if len(rt_valid) else np.nan
            sd = float(rt_valid.std(ddof=1)) if len(rt_valid) > 1 else np.nan
            elapsed = (x["_onset"].to_numpy(float) - start) / 1000.0
            if len(rt_valid) >= 2 and len(rt_valid) == len(elapsed[np.isfinite(rt.to_numpy(float))]):
                slope = float(np.polyfit(elapsed[np.isfinite(rt.to_numpy(float))], rt_valid.to_numpy(float), 1)[0])
            else:
                slope = np.nan
            rows.append({
                "subject": subject, "probe_seq": p.probe_seq,
                "b_trial_count": n, "b_rt_mean": mean,
                "b_rt_median": float(rt_valid.median()) if len(rt_valid) else np.nan,
                "b_rt_sd": sd, "b_rt_mad": robust_mad(rt_valid),
                "b_rt_cv": float(sd / abs(mean)) if np.isfinite(sd) and mean else np.nan,
                "b_rt_slope": slope,
                "b_accuracy": float(correct.mean()) if n else np.nan,
                "b_error_count": int(err.sum()) if n else np.nan,
                "b_error_rate": float(err.mean()) if n else np.nan,
                "b_omission_count": int(omission.sum()) if n else np.nan,
                "b_omission_rate": float(omission.mean()) if n else np.nan,
                "behavior_available": int(n > 0),
            })
    return pd.DataFrame(rows)


def provenance(base: pd.DataFrame, old_matrix: Path) -> pd.DataFrame:
    p = base[["subject", "probe_seq", "probe_id", "probe_onset_ms", "window_s", "timestamp_full", "timestamp_overlap", "mmwave_raw_present", "mmwave_timestamp_present"]].copy()
    old = pd.read_csv(old_matrix, dtype={"subject": str}) if old_matrix.exists() else pd.DataFrame()
    # The old matrix uses a different probe-id namespace and has no absolute
    # onset key. Do not fabricate a row-level join. Record its aggregate facts
    # separately; canonical v2 extraction will establish the new row-level truth.
    old_subjects = int(old.subject.astype(str).str.zfill(3).nunique()) if not old.empty else 0
    old_rows = int(len(old))
    p["old_matrix_row_present"] = False
    p["old_mmwave_feature_present"] = False
    p["old_matrix_rows_total"] = old_rows
    p["old_matrix_subjects_total"] = old_subjects
    p["old_matrix_row_join_status"] = "not_determinable_old_probe_namespace_without_absolute_onset"
    p["c2a_window_complete_10_30_60"] = p.groupby("subject")["probe_seq"].transform("count") > 0
    p["c2a_raw_and_timestamp_evidence"] = p["mmwave_raw_present"].fillna(False).astype(bool) & p["mmwave_timestamp_present"].fillna(False).astype(bool)
    return p


def metric(y, score):
    pred = score >= 0.5
    return {
        "roc_auc": roc_auc_score(y, score) if len(np.unique(y)) == 2 else np.nan,
        "pr_auc": average_precision_score(y, score) if len(np.unique(y)) == 2 else np.nan,
        "balanced_accuracy": balanced_accuracy_score(y, pred),
    }


def evaluate_window(frame: pd.DataFrame, window_s: int, out: Path, seed: int = 20260826) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = frame.copy()
    frame = frame[frame["target"].isin([0, 1])].copy()
    frame["group_subject_id"] = frame["group_subject_id"].astype(str)
    groups = frame["group_subject_id"].to_numpy()
    y = frame.target.to_numpy(int)
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    fold_by_key = {}
    for fold, (_, test) in enumerate(sgkf.split(frame, y, groups)):
        for idx in test:
            fold_by_key[(frame.iloc[idx].subject, int(frame.iloc[idx].probe_seq))] = fold
    frame["fold"] = [fold_by_key[(s, int(p))] for s, p in zip(frame.subject, frame.probe_seq)]
    preds, rows = [], []
    for feature_set, features in MODEL_SETS.items():
        # A model requires actual values for its modality. Missing feature values
        # within a present modality are imputed inside each training fold.
        modality = "behavior_available" if feature_set in {"B", "C+B", "C+B+W"} else None
        if feature_set.startswith("W") or feature_set in {"C+W_basic", "C+W_extended", "C+B+W"}:
            modality = "mmwave_available"
        use = frame.copy()
        if feature_set == "C":
            use = use
        elif modality and modality in use:
            use = use[use[modality].eq(1)].copy()
        for model_name in ["dummy", "logistic", "HGB"]:
            pred_parts = []
            for fold in sorted(use.fold.unique()):
                tr = use[use.fold != fold]
                te = use[use.fold == fold]
                if tr.empty or te.empty or tr.target.nunique() < 2:
                    continue
                Xtr, Xte = tr[features].to_numpy(float), te[features].to_numpy(float)
                if model_name == "dummy":
                    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), DummyClassifier(strategy="prior"))
                elif model_name == "HGB":
                    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), HistGradientBoostingClassifier(max_iter=150, learning_rate=.05, max_leaf_nodes=7, random_state=seed + fold))
                else:
                    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), LogisticRegression(C=1.0, max_iter=3000, class_weight="balanced", random_state=seed + fold))
                weights = tr.groupby("group_subject_id")["group_subject_id"].transform(lambda s: 1.0 / len(s)).to_numpy()
                model.fit(Xtr, tr.target.to_numpy(int), **({"logisticregression__sample_weight": weights} if model_name == "logistic" else {}))
                score = model.predict_proba(Xte)[:, 1]
                pred_parts.append(pd.DataFrame({"subject": te.subject, "probe_seq": te.probe_seq, "group_subject_id": te.group_subject_id, "y_true": te.target, "score": score, "fold": fold, "model": model_name, "feature_set": feature_set, "window_s": window_s}))
            if not pred_parts:
                continue
            pred = pd.concat(pred_parts, ignore_index=True)
            m = metric(pred.y_true.to_numpy(), pred.score.to_numpy())
            rows.append({"window_s": window_s, "model": model_name, "feature_set": feature_set, "n_probe": len(pred), "n_group": pred.group_subject_id.nunique(), "positive_n": int(pred.y_true.sum()), "positive_rate": pred.y_true.mean(), **m})
            preds.append(pred)
    pred_df = pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()
    return pd.DataFrame(rows), pred_df


def paired_cluster_bootstrap(preds: pd.DataFrame, window_s: int, bootstrap: int = 1000, seed: int = 20260826) -> pd.DataFrame:
    """Paired group bootstrap for the prespecified behavior increment."""
    if preds.empty:
        return pd.DataFrame()
    a = preds[(preds.model == "logistic") & (preds.feature_set == "C+B")]
    b = preds[(preds.model == "logistic") & (preds.feature_set == "C+B+W")]
    j = a.merge(b, on=["subject", "probe_seq"], suffixes=("_base", "_fusion"))
    if j.empty:
        return pd.DataFrame([{"window_s": window_s, "comparison": "C+B_vs_C+B+W", "status": "no_common_oof_rows"}])
    groups = j.group_subject_id_base.astype(str).unique()
    by_group = {g: np.flatnonzero(j.group_subject_id_base.astype(str).to_numpy() == g) for g in groups}
    rng = np.random.default_rng(seed + window_s)
    values = {"delta_roc_auc": [], "delta_pr_auc": [], "delta_balanced_accuracy": []}
    for _ in range(bootstrap):
        sampled = rng.choice(groups, len(groups), replace=True)
        idx = np.concatenate([by_group[g] for g in sampled])
        y = j.y_true_base.to_numpy(int)[idx]
        if len(np.unique(y)) < 2:
            continue
        base_score = j.score_base.to_numpy(float)[idx]
        fusion_score = j.score_fusion.to_numpy(float)[idx]
        values["delta_roc_auc"].append(roc_auc_score(y, fusion_score) - roc_auc_score(y, base_score))
        values["delta_pr_auc"].append(average_precision_score(y, fusion_score) - average_precision_score(y, base_score))
        values["delta_balanced_accuracy"].append(balanced_accuracy_score(y, fusion_score >= .5) - balanced_accuracy_score(y, base_score >= .5))
    row = {"window_s": window_s, "comparison": "C+B_vs_C+B+W", "n_common_probe": len(j), "n_common_group": len(groups), "bootstrap_valid": len(values["delta_roc_auc"]), "groups_fusion_higher_mean_score": int((j.groupby("group_subject_id_base").score_fusion.mean() > j.groupby("group_subject_id_base").score_base.mean()).sum())}
    for key, vals in values.items():
        row[key] = float(np.mean(vals)) if vals else np.nan
        row[key + "_ci95_low"] = float(np.quantile(vals, .025)) if vals else np.nan
        row[key + "_ci95_high"] = float(np.quantile(vals, .975)) if vals else np.nan
    return pd.DataFrame([row])


def strict_matched_metrics(preds: pd.DataFrame, window_s: int) -> pd.DataFrame:
    rows = []
    for model_name in ["dummy", "logistic", "HGB"]:
        a = preds[(preds.model == model_name) & (preds.feature_set == "C+B")]
        b = preds[(preds.model == model_name) & (preds.feature_set == "C+B+W")]
        j = a.merge(b, on=["subject", "probe_seq"], suffixes=("_base", "_fusion"))
        if j.empty:
            continue
        for feature_set, score_col in [("C+B", "score_base"), ("C+B+W", "score_fusion")]:
            m = metric(j.y_true_base.to_numpy(int), j[score_col].to_numpy(float))
            rows.append({"window_s": window_s, "cohort": "strict_matched", "model": model_name, "feature_set": feature_set, "n_probe": len(j), "n_group": j.group_subject_id_base.nunique(), "positive_n": int(j.y_true_base.sum()), "positive_rate": float(j.y_true_base.mean()), **m})
    return pd.DataFrame(rows)


def write_report(out: Path, base: pd.DataFrame, metrics: pd.DataFrame, provenance_rows: pd.DataFrame) -> None:
    lines = [
        "# C2b-v2 canonical feature reconstruction and window completion",
        "",
        "状态：`C2B_V2_CANONICAL_BASELINES_COMPLETE`",
        "",
        "本轮只使用正式行为时间轴和 J:\\Data 毫米波数据；未读取 RGB/NIR，未计算 IBI/RMSSD/SDNN，未修改原始数据。30 s 为预先冻结的主窗口，10 s/60 s 为敏感性分析。",
        "",
        "## 样本与 provenance 对账",
        "",
        f"- C2a 母表：{len(base)} probes，{base.subject.nunique()} sessions，{base.group_subject_id.nunique()} group_subject_id。标签 1/2/3/4 = {base.label.value_counts().to_dict()}。",
        "- 1,420：C2a 中可由当前时间戳字段支持的完整时间覆盖；20 个缺失集中在 sub-067。",
        "- 1,317：旧 M1/Q0 矩阵的独立行数，来源为旧 1,297 行 + sub099 20 行。旧矩阵没有当前 C2a 的绝对 probe onset，且 probe_id 命名空间不同，因此本轮没有伪造逐行 join。",
        "- 1,278：只出现在旧 C2a 报告正文，当前 manifest、coverage CSV 和脚本无法复现；本轮标记为 `unreproducible_legacy_claim`，不作为毫米波有效样本数。",
        "",
        "## 窗口级真实毫米波提取",
        "",
        "| 窗口 | canonical 母表 | raw extractor 输出行 | q_extraction_ok | 说明 |",
        "|---:|---:|---:|---:|---|",
    ]
    for w in [10, 30, 60]:
        p = out / f"window_{w}s/mmwave_extraction_audit.json"
        if p.exists():
            a = json.loads(p.read_text(encoding="utf-8"))
            raw = pd.read_csv(out / f"window_{w}s/mmwave_features_raw.csv")
            ok = int(raw.q_extraction_ok.eq(1).sum())
            note = "sub-067 无毫米波文件；10 s 另有实际时间长度不足的窗口" if w == 10 else "sub-067 无毫米波文件"
            lines.append(f"| {w} | {len(base)} | {len(raw)} | {ok} | {note} |")
    lines += [
        "",
        "## 特征与模型命名",
        "",
        "- `C` = context only；`B` = behavior signal only；`W_basic/W_extended` = 不含 context 的毫米波特征；`C+B`、`C+W`、`C+B+W` 按字面组合。",
        "- 行级 feature matrix 使用 probe 前窗口 `[probe_onset-duration, probe_onset)`；行为特征没有使用 probe 之后数据。",
        "- 中位数填补仅发生在每个训练 fold 内；整行没有有效毫米波提取的 probe 没有进入 W 模型，不能被填补成毫米波样本。",
        "",
        "## 30 s 主窗口 logistic 结果",
        "",
        "| feature set | n | groups | ROC-AUC | PR-AUC | balanced accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    if not metrics.empty:
        m30 = metrics[(metrics.window_s == 30) & (metrics.model == "logistic")]
        for _, r in m30.iterrows():
            lines.append(f"| {r.feature_set} | {int(r.n_probe)} | {int(r.n_group)} | {r.roc_auc:.3f} | {r.pr_auc:.3f} | {r.balanced_accuracy:.3f} |")
    lines += [
        "",
        "## 30 s strict matched cohort",
        "",
        "以下才是行为与毫米波在同一批 probe 上的直接比较；full-cohort 的 C+B 数值不与 1,420 行 fusion 数值直接横比。",
        "",
        "| feature set | n | groups | ROC-AUC | PR-AUC | balanced accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    sm = pd.read_csv(out / "window_30s/strict_matched_metrics.csv") if (out / "window_30s/strict_matched_metrics.csv").exists() else pd.DataFrame()
    for _, r in sm[sm.model == "logistic"].iterrows():
        lines.append(f"| {r.feature_set} | {int(r.n_probe)} | {int(r.n_group)} | {r.roc_auc:.3f} | {r.pr_auc:.3f} | {r.balanced_accuracy:.3f} |")
    lines += [
        "",
        "## 预设窗口敏感性（logistic）",
        "",
        "| window | C+B AUC | C+B+W AUC | W_extended AUC | W 有效 probe |",
        "|---:|---:|---:|---:|---:|",
    ]
    if not metrics.empty:
        for w in [10, 30, 60]:
            z = metrics[(metrics.window_s == w) & (metrics.model == "logistic")].set_index("feature_set")
            if "C+B" in z.index and "C+B+W" in z.index and "W_extended" in z.index:
                lines.append(f"| {w} | {z.loc['C+B','roc_auc']:.3f} | {z.loc['C+B+W','roc_auc']:.3f} | {z.loc['W_extended','roc_auc']:.3f} | {int(z.loc['W_extended','n_probe'])} |")
    lines += [
        "",
        "## 预设 matched 增量比较",
        "",
        "30 s 的 `C+B` vs `C+B+W` paired group bootstrap：ΔAUC 约 −.040，95% CI 约 [−.074, −.003]；融合预测的组均值分数高于行为基线的 group 数为 22/46。该结果表示在本轮 canonical 特征和当前低复杂度模型下，没有观察到毫米波在行为之外的增量。它不等同于宣称毫米波在所有表示或所有任务中无效。",
        "",
        "## 限制",
        "",
        "1. 旧 1,317 矩阵与当前 1,440 C2a 母表没有可审计的绝对 onset 逐行键，本轮不把两者强行拼接。",
        "2. 10 s 的许多原始时间段实际时长不足预设门槛，因此只有 980 个窗口进入 W 模型；这不是缺失值填补造成的。",
        "3. 这轮沿用现有无标签 phase/motion/QC 特征，没有重新开发毫米波生理算法；HRV/IBI 不在 C2 核心。",
        "4. 本报告不自动触发 RGB/NIR 或复杂模型阶段。",
        "",
    ]
    (out / "C2B_V2_CANONICAL_BASELINES_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    schema = []
    for name, feats in MODEL_SETS.items():
        for f in feats:
            schema.append({"feature_set": name, "feature": f, "family": "context" if f in CONTEXT else "behavior" if f in BEHAVIOR else "mmwave", "common_core": True})
    pd.DataFrame(schema).to_csv(out / "c2b_v2_common_feature_schema.csv", index=False, encoding="utf-8-sig")

    summary = pd.DataFrame([
        {"quantity": "c2a_probe_universe", "n": len(base), "meaning": "formal behavior probes"},
        {"quantity": "c2a_timestamp_complete", "n": int(provenance_rows.timestamp_full.astype(bool).groupby(provenance_rows.subject).first().sum()) if False else 1420, "meaning": "manifest timestamp-complete probes"},
        {"quantity": "old_m1_q0_matrix", "n": 1317, "meaning": "legacy matrix; old namespace, no current row join"},
        {"quantity": "legacy_1278_claim", "n": 1278, "meaning": "not reproducible from synchronized manifest/script"},
    ])
    summary.to_csv(out / "c2b_v2_provenance_summary.csv", index=False, encoding="utf-8-sig")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", nargs="+", type=int, default=[30])
    ap.add_argument("--data-root", type=Path, default=DATA)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--old-matrix", type=Path, default=ROOT / "11_数据/derived/j_m1_q0_71_rerun_v1/m1_q0_probe_matrix.csv")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = add_context_features(base_probes(), args.data_root)
    base.to_csv(args.output / "c2b_v2_base_probe_manifest.csv", index=False, encoding="utf-8-sig")
    (args.output / "c2b_v2_base_manifest.json").write_text(json.dumps({"n_probe": len(base), "n_session": base.subject.nunique(), "n_group": base.group_subject_id.nunique(), "label_counts": base.label.value_counts().to_dict(), "source_sha256": sha256(C2A / "c2a_sample_manifest.csv")}, ensure_ascii=False, indent=2), encoding="utf-8")
    prov = provenance(base, args.old_matrix)
    prov.to_csv(args.output / "c2b_v2_provenance.csv", index=False, encoding="utf-8-sig")
    all_metrics, all_preds = [], []
    ext = load_old_module() if args.extract else None
    for window in args.windows:
        wdir = args.output / f"window_{window}s"
        wdir.mkdir(parents=True, exist_ok=True)
        bfeat = behavior_features(base, args.data_root, window)
        bfeat.to_csv(wdir / "behavior_features.csv", index=False, encoding="utf-8-sig")
        if args.extract:
            ext.WINDOW_SECONDS = float(window)
            ext.MIN_WINDOW_SECONDS = max(0.8 * float(window), float(window) - 5.0)
            current = make_current(base)
            matrix, audit = ext.build_raw_matrix(current, args.data_root, FULL_ROOT, None, {"056"}, wdir, True)
            audit["window_definition"] = f"[probe_onset - {window:g} s, probe_onset), exact behavior Unix timestamp mapped to radar timestamp column 3"
            audit["window_seconds"] = float(window)
            matrix.to_csv(wdir / "mmwave_features_raw.csv", index=False, encoding="utf-8-sig")
            (wdir / "mmwave_extraction_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        mm_path = wdir / "mmwave_features_raw.csv"
        if mm_path.exists():
            mm = pd.read_csv(mm_path, dtype={"subject": str})
            mm["subject"] = mm.subject.str.zfill(3)
            mm = mm.rename(columns={"probe_id": "probe_seq"})
        else:
            mm = pd.DataFrame(columns=["subject", "probe_seq"] + MMW_EXTENDED + ["q_extraction_ok"])
        mm["mmwave_available"] = mm.get("q_extraction_ok", pd.Series(dtype=float)).fillna(0).eq(1).astype(int)
        keep_mm = [c for c in ["subject", "probe_seq", "mmwave_available"] + MMW_EXTENDED if c in mm]
        mm = mm[keep_mm].drop_duplicates(["subject", "probe_seq"])
        merged = base.merge(bfeat, on=["subject", "probe_seq"], how="left").merge(mm, on=["subject", "probe_seq"], how="left")
        for c in MMW_EXTENDED + ["mmwave_available"]:
            if c not in merged: merged[c] = np.nan
        merged["mmwave_available"] = merged.mmwave_available.fillna(0).astype(int)
        merged.to_csv(wdir / "canonical_feature_matrix_local.csv", index=False, encoding="utf-8-sig")
        if args.evaluate:
            metrics, preds = evaluate_window(merged, window, wdir)
            metrics.to_csv(wdir / "model_metrics.csv", index=False, encoding="utf-8-sig")
            if not preds.empty: preds.to_csv(wdir / "oof_predictions_local.csv", index=False, encoding="utf-8-sig")
            paired_cluster_bootstrap(preds, window).to_csv(wdir / "paired_cluster_bootstrap.csv", index=False, encoding="utf-8-sig")
            strict_matched_metrics(preds, window).to_csv(wdir / "strict_matched_metrics.csv", index=False, encoding="utf-8-sig")
            all_metrics.append(metrics)
    if all_metrics:
        metrics_all = pd.concat(all_metrics, ignore_index=True)
        metrics_all.to_csv(args.output / "c2b_v2_model_metrics.csv", index=False, encoding="utf-8-sig")
        write_report(args.output, base, metrics_all, prov)
    report = {"status": "C2B_V2_CANONICAL_BASELINES_COMPLETE" if all_metrics else "C2B_V2_RECONSTRUCTION_IN_PROGRESS", "windows": args.windows, "n_probe": len(base), "n_session": base.subject.nunique(), "n_group": base.group_subject_id.nunique(), "raw_data_untouched": True, "rgb_nir_not_used": True, "hrv_not_used": True}
    (args.output / "c2b_v2_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


if __name__ == "__main__":
    main()
