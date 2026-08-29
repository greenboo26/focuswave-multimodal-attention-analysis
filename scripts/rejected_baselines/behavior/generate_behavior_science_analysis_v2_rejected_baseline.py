"""被判退的行为科学 v2 基线，仅供网页修复审阅，不得作为正式分析入口。

本文件保留原失败脚本的统计实现；本仓库副本只把机器私有输入根目录改为
环境变量/相对路径，避免提交本机数据盘路径。不要在此文件上继续临时修统计逻辑。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from scipy import stats

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.miscmodels.ordinal_model import OrderedModel
    SM_AVAILABLE = True
except Exception:
    SM_AVAILABLE = False


# 原脚本的本机数据根目录已脱敏；该 rejected baseline 默认没有可运行输入。
ROOT = Path(os.environ.get("FOCUSWAVE_REJECTED_BASELINE_ROOT", "rejected-baseline-input"))
TABLES = ROOT / "tables"
ANALYSIS = ROOT / "analysis-v2"
FIGURES = ROOT / "figures-v2"
FIGDATA = FIGURES / "data"
for p in (ANALYSIS, FIGURES, FIGDATA):
    p.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    Path(r"C:/Windows/Fonts/msyh.ttc"), Path(r"C:/Windows/Fonts/msyhbd.ttc"),
    Path(r"C:/Windows/Fonts/simhei.ttf"), Path(r"C:/Windows/Fonts/simkai.ttf"),
]
existing_fonts = [str(p) for p in FONT_CANDIDATES if p.exists()]
font_path = next((p for p in FONT_CANDIDATES if p.exists()), None)
font_name = "DejaVu Sans"
if font_path is not None:
    try:
        font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
        matplotlib.rcParams["font.family"] = font_name
    except Exception:
        matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["figure.dpi"] = 120
matplotlib.rcParams["savefig.dpi"] = 320
matplotlib.rcParams["font.size"] = 10
FONT_RECORD = {
    "platform": platform.platform(), "font_candidates": existing_fonts,
    "selected_font_path": str(font_path) if font_path else None,
    "selected_font_name": font_name, "font_exists": bool(font_path),
    "matplotlib_version": matplotlib.__version__, "test_text": "中文标题 坐标轴 图例",
}
(ANALYSIS / "font_discovery.json").write_text(json.dumps(FONT_RECORD, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / name, low_memory=False)


trial = read_csv("trial_metrics.csv")
window = read_csv("window_metrics.csv")
cycle = read_csv("phase_cycle_metrics.csv")
block = read_csv("block_metrics.csv")
session = read_csv("session_metrics.csv")
trajectory = read_csv("error_trajectory_metrics.csv")
for df in (trial, window, cycle, block, session, trajectory):
    for c in ["anonymous_participant_group_id", "session_id", "block_id", "error_type"]:
        if c in df.columns:
            df[c] = df[c].astype(str)


def numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


metric_cols = [
    "go_correct_rt_mean_ms", "go_correct_rt_median_ms", "go_correct_rt_sd_ms",
    "go_correct_rt_mad_ms", "go_correct_rt_iqr_ms", "go_correct_rt_cv",
    "go_correct_rt_theilsen_slope_ms_per_s", "commission_rate", "omission_rate",
    "accuracy", "error_rate", "dprime_loglinear", "criterion_c", "beta",
]
for df in (window, cycle, block, session):
    numeric(df, metric_cols + ["cycle_index", "phase_cycle_id", "window_seconds_nominal", "q1_nominal_4class", "q2_ordinal_4level"])
numeric(trajectory, ["trial_offset", "go_correct_rt_ms", "opportunity_count", "numerator", "denominator"])


def save_df(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def ci_mean(x: pd.Series) -> tuple[float, float, int]:
    a = pd.to_numeric(x, errors="coerce").dropna().to_numpy(dtype=float)
    n = len(a)
    if n == 0:
        return np.nan, np.nan, 0
    m = float(np.mean(a))
    if n < 2:
        return m, np.nan, n
    se = float(np.std(a, ddof=1) / math.sqrt(n))
    return m, m - 1.96 * se, n if False else m + 1.96 * se


def summary_stats(x: pd.Series) -> dict:
    a = pd.to_numeric(x, errors="coerce").dropna().to_numpy(dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": np.nan, "median": np.nan, "sd": np.nan, "q1": np.nan, "q3": np.nan, "iqr": np.nan, "outlier_n": 0}
    q1, q3 = np.percentile(a, [25, 75]); iqr = q3 - q1
    out = ((a < q1 - 1.5 * iqr) | (a > q3 + 1.5 * iqr)) if iqr > 0 else np.zeros(len(a), dtype=bool)
    return {"n": len(a), "mean": float(np.mean(a)), "median": float(np.median(a)), "sd": float(np.std(a, ddof=1)) if len(a)>1 else np.nan,
            "q1": float(q1), "q3": float(q3), "iqr": float(iqr), "outlier_n": int(out.sum())}


metric_labels = {
    "go_correct_rt_mean_ms": "正确Go反应时均值（毫秒）", "go_correct_rt_median_ms": "正确Go反应时中位数（毫秒）",
    "go_correct_rt_sd_ms": "正确Go反应时标准差（毫秒）", "go_correct_rt_mad_ms": "正确Go反应时MAD（毫秒）",
    "go_correct_rt_iqr_ms": "正确Go反应时IQR（毫秒）", "go_correct_rt_cv": "正确Go反应时变异系数",
    "go_correct_rt_theilsen_slope_ms_per_s": "正确Go反应时斜率（毫秒/秒）", "commission_rate": "误按率（commission）",
    "omission_rate": "遗漏率（omission）", "accuracy": "准确率（accuracy）", "error_rate": "错误率",
    "dprime_loglinear": "辨别力d′（d-prime）", "criterion_c": "判据c（criterion）", "beta": "反应偏向β（beta）",
}
short_metrics = ["go_correct_rt_mean_ms", "go_correct_rt_median_ms", "go_correct_rt_cv", "go_correct_rt_theilsen_slope_ms_per_s", "commission_rate", "omission_rate", "accuracy", "dprime_loglinear", "criterion_c", "beta"]


scale_frames = {"session": session, "block": block, "cycle": cycle, "probe_window": window[window["window_type"].eq("probe_preceding_seconds")].copy()}
rows = []
for scale, df in scale_frames.items():
    for m in short_metrics:
        if m not in df: continue
        s = summary_stats(df[m])
        rows.append({"scale": scale, "metric": m, "metric_label": metric_labels[m], **s})
overall = pd.DataFrame(rows)
save_df(overall, ANALYSIS / "overall_distribution_summary.csv")

qc_rows = []
for name, df in [("trial",trial),("probe_window",scale_frames["probe_window"]),("cycle",cycle),("block",block),("session",session),("error_trajectory",trajectory)]:
    qc_rows.append({"table":name,"rows":len(df),"columns":len(df.columns),"session_n":df["session_id"].nunique() if "session_id" in df else np.nan,
                    "group_n":df["anonymous_participant_group_id"].nunique() if "anonymous_participant_group_id" in df else np.nan,
                    "null_group_n":int(df["anonymous_participant_group_id"].isna().sum()) if "anonymous_participant_group_id" in df else np.nan})
qcs = pd.DataFrame(qc_rows)
save_df(qcs, ANALYSIS / "qc_v2_summary.csv")
sample = pd.DataFrame([
    {"项目":"采集场次（session）","数量":int(session.session_id.nunique())},
    {"项目":"当前队列匿名参与者分析组","数量":int(session.anonymous_participant_group_id.nunique())},
    {"项目":"双场重复组","数量":int((session.groupby("anonymous_participant_group_id").size()==2).sum())},
    {"项目":"双场重复涉及场次","数量":int((session.groupby("anonymous_participant_group_id").size()==2).sum()*2)},
    {"项目":"Q1有效探针回答","数量":int(trial["q1_nominal_4class"].notna().sum())},
    {"项目":"Q2有效探针回答","数量":int(trial["q2_ordinal_4level"].notna().sum())},
])
save_df(sample, ANALYSIS / "sample_summary_v2.csv")


def rank_corr(a: pd.Series, b: pd.Series) -> float:
    x = pd.to_numeric(a, errors="coerce"); y = pd.to_numeric(b, errors="coerce")
    ok = x.notna() & y.notna()
    if ok.sum() < 3 or x[ok].nunique() < 2 or y[ok].nunique() < 2: return np.nan
    return float(stats.spearmanr(x[ok], y[ok]).statistic)


session_numeric = session.set_index("session_id")[short_metrics].copy()
corr = pd.DataFrame(index=short_metrics, columns=short_metrics, dtype=float)
for a in short_metrics:
    for b in short_metrics:
        corr.loc[a,b] = rank_corr(session_numeric[a], session_numeric[b])
save_df(corr.reset_index().rename(columns={"index":"metric"}), ANALYSIS / "session_spearman_correlation_v2.csv")
construct = pd.DataFrame([
    {"metric":m,"metric_label":metric_labels[m],"construct":("速度" if "rt_" in m and m not in ["commission_rate","omission_rate"] else "准确性/错误" if m in ["commission_rate","omission_rate","accuracy"] else "信号检测" if m in ["dprime_loglinear","criterion_c","beta"] else "速度-稳定性")} for m in short_metrics
])
save_df(construct, ANALYSIS / "metric_construct_map_v2.csv")


model_rows = []
model_diag = []

def add_model_failure(name, model_type, outcome, predictor, n, groups, status, warning):
    model_rows.append({"model_name":name,"model_type":model_type,"outcome":outcome,"predictor":predictor,"term":predictor,
                       "estimate":np.nan,"se":np.nan,"ci_low":np.nan,"ci_high":np.nan,"effect_size":np.nan,
                       "n_rows":n,"n_groups":groups,"status":status,"warning":warning})


def fit_mixed(name: str, df: pd.DataFrame, formula: str, outcome: str, predictor_hint: str) -> object | None:
    d = df.copy()
    needed = [outcome, "anonymous_participant_group_id"]
    d = d.dropna(subset=[c for c in needed if c in d]).copy()
    d = d[d["anonymous_participant_group_id"].ne("nan")]
    n = len(d)
    ng = d["anonymous_participant_group_id"].nunique() if n else 0
    if n < 10 or ng < 3 or not SM_AVAILABLE:
        add_model_failure(name,"mixedlm",outcome,predictor_hint,n,ng,"not_estimable","样本或统计包不足，保留失败")
        return None
    warn = []
    try:
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            md = smf.mixedlm(formula, d, groups=d["anonymous_participant_group_id"], re_formula="1")
            res = md.fit(reml=False, method="lbfgs", maxiter=500, disp=False)
            warn = [str(w.message) for w in ws]
        converged = bool(getattr(res, "converged", False))
        model_diag.append({"model_name":name,"model_type":"mixedlm","n_rows":n,"n_groups":ng,"converged":converged,
                           "random_intercept":"anonymous_participant_group_id","warning":" | ".join(warn),
                           "singular_or_boundary":any("boundary" in w.lower() or "singular" in w.lower() for w in warn)})
        fixed = [p for p in res.params.index if p != "Group Var" and not str(p).startswith("anonymous")]
        for term in fixed:
            if term.lower() in ("intercept",): continue
            est = float(res.params[term]); se = float(res.bse[term]) if np.isfinite(res.bse[term]) else np.nan
            model_rows.append({"model_name":name,"model_type":"mixedlm","outcome":outcome,"predictor":predictor_hint,"term":term,
                               "estimate":est,"se":se,"ci_low":est-1.96*se if np.isfinite(se) else np.nan,
                               "ci_high":est+1.96*se if np.isfinite(se) else np.nan,"effect_size":est,
                               "n_rows":n,"n_groups":ng,"status":"ok_converged" if converged else "ok_not_converged","warning":" | ".join(warn)})
        return res
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        model_diag.append({"model_name":name,"model_type":"mixedlm","n_rows":n,"n_groups":ng,"converged":False,
                           "random_intercept":"anonymous_participant_group_id","warning":msg,"singular_or_boundary":("singular" in msg.lower())})
        add_model_failure(name,"mixedlm",outcome,predictor_hint,n,ng,"failed_preserve_random_intercept",msg)
        return None


# B1-B2 block effects: session remains a session-level observation, group is the random intercept.
block["block_id"] = block["block_id"].astype(str)
for m in ["go_correct_rt_mean_ms","go_correct_rt_median_ms","go_correct_rt_cv","go_correct_rt_theilsen_slope_ms_per_s","commission_rate","omission_rate","accuracy","dprime_loglinear","criterion_c","beta"]:
    fit_mixed("B1_B2_"+m, block, f"{m} ~ C(block_id)", m, "B2_vs_B1")

# Time-on-task: cycle index remains within-session, with group random intercept.
cycle_ok = cycle[cycle["calculation_status"].astype(str).str.contains("ok|valid", case=False, regex=True, na=False)].copy()
if cycle_ok.empty: cycle_ok = cycle.copy()
cycle_ok["cycle_index"] = cycle_ok["phase_cycle_id"]
time_res = fit_mixed("time_on_task_rt", cycle_ok, "go_correct_rt_mean_ms ~ cycle_index + C(block_id)", "go_correct_rt_mean_ms", "cycle_index")
fit_mixed("time_on_task_error", cycle_ok, "error_rate ~ cycle_index + C(block_id)", "error_rate", "cycle_index")

# Probe-window Q1 nominal model: Q1 categories are explicitly categorical, not 1-4 continuous.
probe = window[window["window_type"].eq("probe_preceding_seconds")].copy()
probe["q1_nominal_4class"] = probe["q1_nominal_4class"].astype("Int64").astype(str)
probe["q2_ordinal_4level"] = probe["q2_ordinal_4level"].astype("Int64")
probe["window_seconds_nominal"] = probe["window_seconds_nominal"].astype(str)
for m in ["go_correct_rt_mean_ms","go_correct_rt_cv","go_correct_rt_theilsen_slope_ms_per_s","error_rate"]:
    q1d = probe[probe["q1_nominal_4class"].isin(["1","2","3","4"])].copy()
    fit_mixed("probe_Q1_"+m, q1d, f"{m} ~ C(q1_nominal_4class) + C(window_seconds_nominal)", m, "Q1_nominal_4class")

# Q2 ordinal sensitivity: OrderedModel preserves ordinal thresholds; statsmodels OrderedModel has no random intercept.
ordinal_rows = []
for m in ["go_correct_rt_mean_ms","go_correct_rt_cv","go_correct_rt_theilsen_slope_ms_per_s","error_rate"]:
    d = probe.dropna(subset=["q2_ordinal_4level",m]).copy()
    d = d[d["q2_ordinal_4level"].between(1,4)]
    n, ng = len(d), d["anonymous_participant_group_id"].nunique()
    if n < 20 or not SM_AVAILABLE:
        add_model_failure("probe_Q2_"+m,"ordered_logit_sensitivity","q2_ordinal_4level",m,n,ng,"not_estimable","OrderedModel或样本不足；不将Q2当连续")
        continue
    try:
        X = pd.DataFrame({"metric":(d[m]-d[m].mean())/(d[m].std(ddof=0) or 1.0)})
        X = pd.concat([X, pd.get_dummies(d["window_seconds_nominal"], prefix="window", drop_first=True, dtype=float)], axis=1)
        y = d["q2_ordinal_4level"].astype(int)
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            om = OrderedModel(y, X, distr="logit")
            rr = om.fit(method="bfgs", disp=False, maxiter=500)
        est = float(rr.params["metric"]); se = float(rr.bse["metric"])
        ordinal_rows.append({"model_name":"probe_Q2_"+m,"model_type":"ordered_logit_sensitivity_no_random_intercept","outcome":"q2_ordinal_4level","predictor":m,"term":"metric_standardized",
                             "estimate":est,"se":se,"ci_low":est-1.96*se,"ci_high":est+1.96*se,"effect_size":est,"n_rows":n,"n_groups":ng,
                             "status":"ok_ordinal_sensitivity","warning":"Q2为有序四级；OrderedModel不含参与者随机截距，作为敏感性分析；"+" | ".join(str(w.message) for w in ws)})
    except Exception as exc:
        add_model_failure("probe_Q2_"+m,"ordered_logit_sensitivity_no_random_intercept","q2_ordinal_4level",m,n,ng,"failed_preserve_ordinal","%s: %s"%(type(exc).__name__,exc))
if ordinal_rows: model_rows.extend(ordinal_rows)

models = pd.DataFrame(model_rows)
save_df(models, ANALYSIS / "model_results_v2.csv")
save_df(pd.DataFrame(model_diag), ANALYSIS / "model_diagnostics_v2.csv")


# Time-on-task fixed-effect prediction band (fixed effects only; session/group random effects are not silently added).
pred_rows = []
if time_res is not None:
    pnames = list(time_res.fe_params.index)
    cov = time_res.cov_params().loc[pnames, pnames]
    for b in ["B1","B2"]:
        for c in range(1,25):
            v = np.array([1.0 if p=="Intercept" else float(c) if p=="cycle_index" else 1.0 if (p=="C(block_id)[T.B2]" and b=="B2") else 0.0 for p in pnames])
            mu = float(np.dot(v, time_res.fe_params.to_numpy()))
            se = float(np.sqrt(max(0.0, np.dot(v, np.dot(cov.to_numpy(), v)))))
            pred_rows.append({"block_id":b,"cycle_index":c,"prediction_ms":mu,"ci_low":mu-1.96*se,"ci_high":mu+1.96*se,"prediction_basis":"fixed effects only"})
save_df(pd.DataFrame(pred_rows), ANALYSIS / "time_on_task_predictions_v2.csv")


# Error trajectory summary at each offset; n_valid is retained as a first-class field.
traj_rows = []
for (et, off), d in trajectory.groupby(["error_type","trial_offset"], dropna=False):
    a = pd.to_numeric(d["go_correct_rt_ms"], errors="coerce").dropna()
    m = float(a.mean()) if len(a) else np.nan
    se = float(a.std(ddof=1)/math.sqrt(len(a))) if len(a)>1 else np.nan
    traj_rows.append({"error_type":et,"trial_offset":off,"n_valid":len(a),"rt_mean_ms":m,"ci_low":m-1.96*se if np.isfinite(se) else np.nan,"ci_high":m+1.96*se if np.isfinite(se) else np.nan})
traj_summary = pd.DataFrame(traj_rows).sort_values(["error_type","trial_offset"])
save_df(traj_summary, ANALYSIS / "error_trajectory_summary_v2.csv")

# Repeat-session paired data, anonymized for reporting as R1-R6 rather than group keys.
repeat_rows = []
pair_i = 0
for gid, d in session.groupby("anonymous_participant_group_id"):
    if len(d) != 2: continue
    pair_i += 1
    d = d.sort_values("session_id").reset_index(drop=True)
    for j, r in d.iterrows():
        for m in ["go_correct_rt_mean_ms","go_correct_rt_median_ms","go_correct_rt_cv","accuracy","dprime_loglinear"]:
            repeat_rows.append({"repeat_pair":"R%d"%pair_i,"session_order":j+1,"metric":m,"value":r[m]})
repeat_df = pd.DataFrame(repeat_rows)
save_df(repeat_df, ANALYSIS / "repeat_session_plot_data_v2.csv")

# Speed-accuracy relationship, with Pearson and rank correlation.
sa = session[["session_id","go_correct_rt_mean_ms","error_rate","accuracy","anonymous_participant_group_id"]].copy()
pear = rank = np.nan
ok = sa[["go_correct_rt_mean_ms","error_rate"]].dropna()
if len(ok)>2:
    pear = float(stats.pearsonr(ok.iloc[:,0],ok.iloc[:,1]).statistic)
    rank = float(stats.spearmanr(ok.iloc[:,0],ok.iloc[:,1]).statistic)
speed_summary = pd.DataFrame([{"n_sessions":len(ok),"pearson_rt_error":pear,"spearman_rt_error":rank,"note":"Spearman为等级相关；不将场次视为独立自然人"}])
save_df(speed_summary, ANALYSIS / "speed_accuracy_summary_v2.csv")
save_df(sa.drop(columns=["anonymous_participant_group_id"]), ANALYSIS / "speed_accuracy_plot_data_v2.csv")

# Candidate decision matrix: transparent multi-criterion screen, not significance-only selection.
candidate = []
coverage = overall.pivot(index="metric",columns="scale",values="n")
for m in short_metrics:
    stab = float("nan")
    candidate.append({"metric":m,"metric_label":metric_labels[m],"construct":construct.set_index("metric").loc[m,"construct"],
                      "session_coverage":int(coverage.loc[m,"session"]) if m in coverage.index else 0,
                      "block_coverage":int(coverage.loc[m,"block"]) if m in coverage.index else 0,
                      "window_coverage":int(coverage.loc[m,"probe_window"]) if m in coverage.index else 0,
                      "interpretability":1 if m in ["go_correct_rt_mean_ms","go_correct_rt_median_ms","commission_rate","omission_rate","accuracy"] else 0,
                      "stability_available":0,"speed_accuracy_complement":1 if m in ["go_correct_rt_mean_ms","error_rate","accuracy"] else 0,
                      "sdt_opportunity_gate":1 if m in ["dprime_loglinear","criterion_c","beta"] else 0,
                      "provisional_role":"初始锚点候选" if m in ["go_correct_rt_mean_ms","accuracy","error_rate"] else "互补/敏感性候选"})
candidate_df = pd.DataFrame(candidate)
save_df(candidate_df, ANALYSIS / "metric_candidate_decision_matrix_v2.csv")


figure_records = []
def fig_save(fig, figure_id, data: pd.DataFrame, purpose: str, notes: str = ""):
    data_path = FIGDATA / (figure_id + ".csv")
    save_df(data, data_path)
    path = FIGURES / (figure_id + ".png")
    fig.savefig(path, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    figure_records.append({"figure_id":figure_id,"filename":path.name,"data_csv":str(data_path.relative_to(ROOT)),"purpose":purpose,"dpi":320,"font_path":str(font_path) if font_path else "","font_name":font_name,"status":"generated","notes":notes})


def title(ax, s): ax.set_title(s, pad=10, fontsize=11)

# 1. Sample, response ratings and QC.
fig, axs = plt.subplots(2,2,figsize=(12,8))
axs[0,0].barh(sample["项目"],sample["数量"],color=["#4472C4","#70AD47","#ED7D31","#A5A5A5","#5B9BD5","#FFC000"]); title(axs[0,0],"样本与有效探针回答"); axs[0,0].set_xlabel("数量")
q1 = trial["q1_nominal_4class"].value_counts().reindex([1,2,3,4]).fillna(0); axs[0,1].bar(["Q1-1","Q1-2","Q1-3","Q1-4"],q1,color="#5B9BD5"); title(axs[0,1],"Q1名义四类原始编码分布"); axs[0,1].set_ylabel("回答数")
q2 = trial["q2_ordinal_4level"].value_counts().reindex([1,2,3,4]).fillna(0); axs[1,0].bar(["Q2-1","Q2-2","Q2-3","Q2-4"],q2,color="#70AD47"); title(axs[1,0],"Q2有序四级原始编码分布"); axs[1,0].set_ylabel("回答数")
miss = pd.DataFrame({"字段组":["试次主字段","窗口主字段","场次主字段","错误轨迹主字段"],"缺失比例":[trial[["session_id","correct","rt"]].isna().mean().mean(),window[["session_id","q1_nominal_4class","q2_ordinal_4level"]].isna().mean().mean(),session[["session_id","anonymous_participant_group_id"]].isna().mean().mean(),trajectory[["error_type","trial_offset","go_correct_rt_ms"]].isna().mean().mean()]}); axs[1,1].bar(miss["字段组"],miss["缺失比例"]*100,color="#C00000"); axs[1,1].tick_params(axis="x",rotation=30); title(axs[1,1],"关键字段缺失比例（%）"); axs[1,1].set_ylabel("百分比")
fig.tight_layout(); fig_save(fig,"01_sample_qc_ratings",pd.concat([sample.rename(columns={"项目":"label","数量":"value"}),miss.rename(columns={"字段组":"label","缺失比例":"value"})],ignore_index=True),"样本、Q1/Q2分布与关键字段缺失/QC")

# 2. Overall distributions and outlier counts.
plot_metrics = ["go_correct_rt_mean_ms","go_correct_rt_median_ms","go_correct_rt_cv","go_correct_rt_theilsen_slope_ms_per_s","commission_rate","omission_rate","accuracy","dprime_loglinear","beta"]
fig, axs = plt.subplots(3,3,figsize=(14,11))
for ax,m in zip(axs.flat,plot_metrics):
    vals=[]; labs=[]
    for scale,df in [("session",session),("block",block)]:
        if m in df:
            v=pd.to_numeric(df[m],errors="coerce").dropna(); vals.append(v); labs.append(scale)
    ax.boxplot(vals,labels=labs,showfliers=True); title(ax,metric_labels[m]); ax.grid(axis="y",alpha=.2)
fig.tight_layout(); fig_save(fig,"02_overall_distributions_outliers",overall[overall.metric.isin(plot_metrics)],"RT、错误、准确率和SDT指标多尺度总体分布及离群诊断")

# 3. Spearman redundancy heatmap.
fig, ax = plt.subplots(figsize=(12,10)); mat=corr.to_numpy(dtype=float); im=ax.imshow(mat,vmin=-1,vmax=1,cmap="coolwarm"); fig.colorbar(im,ax=ax,label="Spearman等级相关系数"); ax.set_xticks(range(len(short_metrics)),[metric_labels[x] for x in short_metrics],rotation=65,ha="right"); ax.set_yticks(range(len(short_metrics)),[metric_labels[x] for x in short_metrics]);
for i in range(len(short_metrics)):
    for j in range(len(short_metrics)):
        if np.isfinite(mat[i,j]): ax.text(j,i,f"{mat[i,j]:.2f}",ha="center",va="center",fontsize=7)
title(ax,"场次尺度指标Spearman相关与冗余热图"); fig.tight_layout(); fig_save(fig,"03_spearman_redundancy_constructs",corr.reset_index().rename(columns={"index":"metric"}),"初始/二级指标内部关系与构念覆盖")

# 4. B1-B2 paired trajectories.
bwide=block.pivot(index="session_id",columns="block_id",values=plot_metrics[0]).dropna(how="all"); pdata=[]
for sid,r in bwide.iterrows(): pdata += [{"session_order":sid,"block_id":b,"value":r.get(b,np.nan)} for b in ["B1","B2"]]
fig, axs=plt.subplots(2,2,figsize=(12,9)); chosen=["go_correct_rt_mean_ms","go_correct_rt_cv","accuracy","dprime_loglinear"]
for ax,m in zip(axs.flat,chosen):
    w=block.pivot(index="session_id",columns="block_id",values=m)
    for _,r in w.iterrows(): ax.plot([1,2],[r.get("B1",np.nan),r.get("B2",np.nan)],color="#9EADBF",alpha=.45,lw=.8)
    means=w[["B1","B2"]].mean(); sem=w[["B1","B2"]].std()/np.sqrt(w[["B1","B2"]].count()); ax.errorbar([1,2],means,yerr=1.96*sem,fmt="o-",color="#C00000",lw=2,capsize=4,label="总体均值±95%CI"); ax.set_xticks([1,2],["B1","B2"]); title(ax,metric_labels[m]); ax.legend(fontsize=8); ax.grid(axis="y",alpha=.2)
fig.tight_layout(); fig_save(fig,"04_b1_b2_paired_trajectories",block[["session_id","block_id"]+chosen],"B1-B2场次配对轨迹、总体估计与不确定区间","细线代表场次级记录，不代表独立自然人")

# 5. Time-on-task trend and prediction bands.
ct=cycle.groupby(["block_id","phase_cycle_id"],as_index=False).agg(rt_mean=("go_correct_rt_mean_ms","mean"),rt_sd=("go_correct_rt_mean_ms","std"),n=("go_correct_rt_mean_ms","count"),error_rate=("error_rate","mean")); ct["ci_low"]=ct.rt_mean-1.96*ct.rt_sd/np.sqrt(ct.n.clip(lower=1)); ct["ci_high"]=ct.rt_mean+1.96*ct.rt_sd/np.sqrt(ct.n.clip(lower=1));
fig,axs=plt.subplots(1,2,figsize=(13,5));
for b,g in ct.groupby("block_id"): axs[0].plot(g.phase_cycle_id,g.rt_mean,marker="o",label=b); axs[0].fill_between(g.phase_cycle_id,g.ci_low,g.ci_high,alpha=.15); axs[1].plot(g.phase_cycle_id,g.error_rate,marker="o",label=b)
if pred_rows:
    pp=pd.DataFrame(pred_rows)
    for b,g in pp.groupby("block_id"): axs[0].plot(g.cycle_index,g.prediction_ms,"--",label=b+"模型预测"); axs[0].fill_between(g.cycle_index,g.ci_low,g.ci_high,alpha=.10)
title(axs[0],"Time-on-task：正确Go反应时随cycle变化"); axs[0].set_xlabel("cycle"); axs[0].set_ylabel("毫秒"); axs[0].legend(fontsize=8); title(axs[1],"Time-on-task：错误率随cycle变化"); axs[1].set_xlabel("cycle"); axs[1].set_ylabel("错误率"); axs[1].legend(); fig.tight_layout(); fig_save(fig,"05_time_on_task_trend_prediction",pd.concat([ct,pd.DataFrame(pred_rows).rename(columns={"prediction_ms":"rt_mean"})],ignore_index=True),"cycle/time-on-task趋势及固定效应模型预测带")

# 6. Probe-window Q1/Q2 relation.
rel=[]
for rating_col,rating_name,levels in [("q1_nominal_4class","Q1名义",[1,2,3,4]),("q2_ordinal_4level","Q2有序",[1,2,3,4])]:
    for m in ["go_correct_rt_mean_ms","go_correct_rt_cv","go_correct_rt_theilsen_slope_ms_per_s","error_rate"]:
        for lev in levels:
            a=probe[probe[rating_col].astype(str).eq(str(lev))][m].dropna(); mean=float(a.mean()) if len(a) else np.nan; se=float(a.std(ddof=1)/np.sqrt(len(a))) if len(a)>1 else np.nan; rel.append({"rating":rating_name,"rating_level":lev,"metric":m,"mean":mean,"ci_low":mean-1.96*se if np.isfinite(se) else np.nan,"ci_high":mean+1.96*se if np.isfinite(se) else np.nan,"n":len(a)})
rel_df=pd.DataFrame(rel); fig,axs=plt.subplots(2,4,figsize=(16,8));
for row,(rn,sub) in enumerate(rel_df.groupby("rating")):
    for ax,(m,g) in zip(axs[row],sub.groupby("metric")):
        ax.errorbar(g.rating_level,g["mean"],yerr=[g["mean"]-g["ci_low"],g["ci_high"]-g["mean"]],fmt="o-",color="#4472C4"); ax.set_xticks([1,2,3,4]); ax.set_xlabel("等级"); title(ax,rn+"："+metric_labels[m]);
        for _,r in g.iterrows():
            if np.isfinite(r["mean"]): ax.text(r.rating_level,r["mean"],f"n={int(r.n)}",fontsize=7,ha="center",va="bottom")
fig.tight_layout(); fig_save(fig,"06_probe_window_q1_q2_relations",rel_df,"探针前窗口RT、RT_CV、RT slope、错误率与Q1/Q2关系；保留原始n","Q1使用名义分类混合模型；Q2使用有序logit敏感性分析并明确无随机截距限制")

# 7. Error before/after trajectories.
fig,ax=plt.subplots(figsize=(11,6));
for et,g in traj_summary.groupby("error_type"):
    ax.plot(g.trial_offset,g.rt_mean_ms,marker="o",label=str(et)); ax.fill_between(g.trial_offset,g.ci_low,g.ci_high,alpha=.15);
    for _,r in g.iterrows():
        if np.isfinite(r.rt_mean_ms): ax.text(r.trial_offset,r.rt_mean_ms,f"n={int(r.n_valid)}",fontsize=7,ha="center",va="bottom")
ax.axvline(0,color="k",lw=.8,ls="--"); ax.set_xlabel("错误事件相对试次偏移（trial offset）"); ax.set_ylabel("正确Go反应时（毫秒）"); title(ax,"commission/omission错误前后RT轨迹"); ax.legend(title="错误类型"); fig.tight_layout(); fig_save(fig,"07_error_before_after_trajectory",traj_summary,"错误前后RT轨迹、各offset有效样本数与不确定区间")

# 8. Speed-accuracy tradeoff.
fig,ax=plt.subplots(figsize=(8,6)); ax.scatter(sa.go_correct_rt_mean_ms,sa.error_rate,s=35,alpha=.75,color="#4472C4"); ax.set_xlabel("正确Go反应时均值（毫秒）"); ax.set_ylabel("错误率"); title(ax,"速度—准确率权衡：场次描述"); ax.text(.03,.97,f"n={len(ok)}\nPearson r={pear:.2f}\nSpearman ρ={rank:.2f}",transform=ax.transAxes,va="top",bbox=dict(facecolor="white",alpha=.8)); ax.grid(alpha=.2); fig.tight_layout(); fig_save(fig,"08_speed_accuracy_tradeoff",sa.drop(columns=["anonymous_participant_group_id"]),"速度—准确率散点、Pearson与Spearman等级相关")

# 9. Six repeat groups connected within pair.
fig,axs=plt.subplots(1,5,figsize=(18,5));
for ax,m in zip(axs,["go_correct_rt_mean_ms","go_correct_rt_median_ms","go_correct_rt_cv","accuracy","dprime_loglinear"]):
    d=repeat_df[repeat_df.metric.eq(m)]
    for pair,g in d.groupby("repeat_pair"): ax.plot(g.session_order,g.value,marker="o",label=pair)
    ax.set_xticks([1,2],["场次1","场次2"]); title(ax,metric_labels[m]); ax.grid(axis="y",alpha=.2)
axs[-1].legend(title="双场重复组",fontsize=8); fig.tight_layout(); fig_save(fig,"09_repeat_group_connected_pairs",repeat_df,"6个双场重复组逐组连线的一致性描述","使用R1-R6替代匿名组键，不展示具体匿名标识")

# 10. Mixed model forest.
forest=models[(models.status.astype(str).str.startswith("ok")) & models.term.notna() & ~models.term.astype(str).str.contains("window_seconds",na=False)].copy().tail(24)
if forest.empty: forest=models[models.estimate.notna()].copy()
def forest_label(r):
    n=str(r.model_name); t=str(r.term)
    prefix="B1→B2" if n.startswith("B1_B2") else "时间过程" if n.startswith("time_on_task") else "Q1探针窗口" if n.startswith("probe_Q1") else "Q2探针窗口"
    metric="Q2有序等级" if str(r.outcome)=="q2_ordinal_4level" else metric_labels.get(str(r.outcome),str(r.outcome))
    if "block_id" in t: term="B2相对B1"
    elif "q1_nominal_4class" in t: term="Q1名义等级对比"
    elif "window_seconds_nominal" in t: term="窗口长度对比"
    elif "cycle_index" in t: term="每增加1个cycle"
    elif "metric_standardized" in t: term="指标每增加1个标准差"
    else: term=t
    return prefix+"｜"+metric+"｜"+term
forest["label"]=forest.apply(forest_label,axis=1); forest=forest.sort_values("estimate"); y=np.arange(len(forest)); fig,ax=plt.subplots(figsize=(12,max(6,0.32*len(forest)))); ax.errorbar(forest.estimate,y,xerr=[forest.estimate-forest.ci_low,forest.ci_high-forest.estimate],fmt="o",color="#C00000"); ax.axvline(0,color="k",lw=.8); ax.set_yticks(y,forest.label); ax.set_xlabel("估计值（95% CI）"); title(ax,"混合模型与Q2有序敏感性结果森林图"); ax.grid(axis="x",alpha=.2); fig.tight_layout(); fig_save(fig,"10_mixed_model_forest",forest,"混合模型估计、95%CI、效应方向和状态")

# 11. Participant-disjoint prediction baseline.
pred_path=ROOT/"analysis"/"participant_disjoint_fold_metrics.csv"; pred_df=pd.read_csv(pred_path) if pred_path.exists() else pd.DataFrame()
if not pred_df.empty:
    fig,ax=plt.subplots(figsize=(9,5));
    for model,color,label in [("ridge","#4472C4","参与者互斥Ridge"),("dummy_mean","#A5A5A5","均值基线")]:
        sub=pred_df[pred_df["model"].astype(str).eq(model)].sort_values("fold_id")
        if not sub.empty: ax.plot(sub["fold_id"],sub["mae"],marker="o",label=label,color=color)
    ax.set_xlabel("互斥折号"); ax.set_ylabel("MAE（越低越好）"); title(ax,"参与者互斥预测与均值基线对照（补充）"); ax.legend(); ax.grid(alpha=.2); fig.tight_layout(); fig_save(fig,"11_participant_disjoint_prediction_baseline",pred_df,"参与者互斥预测与均值基线，仅作补充")
else:
    fig,ax=plt.subplots(figsize=(8,4)); ax.text(.5,.5,"未找到互斥预测明细，保留失败说明",ha="center",va="center"); ax.axis("off"); fig_save(fig,"11_participant_disjoint_prediction_baseline",pd.DataFrame([{"status":"missing_source"}]),"参与者互斥预测补充图","源表缺失，未虚构结果")

# 12. Candidate matrix and flow.
cm=candidate_df.set_index("metric")["interpretability"].to_numpy(); criteria=["interpretability","speed_accuracy_complement","sdt_opportunity_gate","session_coverage","block_coverage","window_coverage"]; mat2=candidate_df[criteria].copy(); mat2["session_coverage"]=(mat2["session_coverage"]>=44).astype(int); mat2["block_coverage"]=(mat2["block_coverage"]>=88).astype(int); mat2["window_coverage"]=(mat2["window_coverage"]>=100).astype(int); mat2.index=candidate_df.metric_label; fig,axs=plt.subplots(1,2,figsize=(15,8),gridspec_kw={"width_ratios":[1.8,1]}); im=axs[0].imshow(mat2.to_numpy(),aspect="auto",cmap="YlGn",vmin=0,vmax=1); axs[0].set_xticks(range(len(criteria)),["可解释","速度-准确互补","SDT机会门","session覆盖","block覆盖","窗口覆盖"],rotation=55,ha="right"); axs[0].set_yticks(range(len(mat2)),mat2.index); title(axs[0],"指标候选多标准筛选矩阵");
for i in range(len(mat2)):
    for j in range(len(criteria)): axs[0].text(j,i,str(int(mat2.iloc[i,j])),ha="center",va="center",fontsize=8)
axs[1].axis("off"); axs[1].text(.05,.9,"候选流程（不以显著性单独筛选）",fontsize=12,weight="bold"); axs[1].text(.08,.72,"数据契约/QC\n↓\n构念覆盖与冗余\n↓\n多尺度可计算性\n↓\n重复场次稳定性\n↓\n速度—准确率权衡\n↓\n主锚点 + 互补指标 + 待复核",fontsize=11,va="top",bbox=dict(boxstyle="round",facecolor="#EAF2F8")); fig.tight_layout(); fig_save(fig,"12_metric_candidate_decision_flow",candidate_df,"指标候选筛选决策矩阵与流程图","候选筛选不是终稿结论；需结合身份冻结和后续复核")

save_df(pd.DataFrame(figure_records), FIGURES / "figure_manifest.csv")

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

all_outputs=[]
for p in sorted(list(ANALYSIS.rglob("*"))+list(FIGURES.rglob("*"))):
    if p.is_file(): all_outputs.append({"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":sha256(p)})
run = {"analysis_version":"behavior_science_analysis_v2","scientific_status":"formal_behavior_descriptive_and_model_candidate_outputs; no_final_cohort_inference_claim",
       "input_root":str(ROOT),"table_rows":{"trial":len(trial),"window":len(window),"cycle":len(cycle),"block":len(block),"session":len(session),"trajectory":len(trajectory)},
       "session_n":int(session.session_id.nunique()),"anonymous_group_n":int(session.anonymous_participant_group_id.nunique()),"repeat_group_n":int((session.groupby("anonymous_participant_group_id").size()==2).sum()),
       "python":sys.executable,"python_version":sys.version,"font":FONT_RECORD,"figure_n":len(figure_records),"outputs":all_outputs,
       "model_note":"anonymous_participant_group_id作为混合模型随机截距；session保持场次级记录；Q1名义分类；Q2有序logit敏感性不含随机截距并已标注。"}
(ANALYSIS/"analysis_v2_run_manifest.json").write_text(json.dumps(run,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
print(json.dumps({"status":"ok","figures":len(figure_records),"models":len(models),"analysis":str(ANALYSIS),"figures_dir":str(FIGURES),"font":FONT_RECORD},ensure_ascii=False))
