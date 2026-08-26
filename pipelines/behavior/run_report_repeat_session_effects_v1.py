#!/usr/bin/env python
"""REPORT_REPEAT_SESSION_EFFECTS_V1: Beijing repeated formal-session effects.

The script intentionally reuses the frozen Beijing canonical probe master.  It
does not read radar, RGB, NIR, or raw behaviour files, and it never rebuilds a
participant identity mapping.  Pseudonymous row-level audit material is written
only to the local derived output directory; the Git-facing directory receives
only de-identified aggregate model tables, a method report, and a figure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.regression.mixed_linear_model import MixedLM


INPUT = Path(r"D:\Project\厚粲杯\11_数据\derived\beijing_zhuhai_canonical_harmonization_v1\beijing_zhuhai_shared_probe_master.csv")
DEFAULT_OUT = Path(r"D:\Project\厚粲杯\11_数据\derived\report_repeat_session_effects_v1")
DEFAULT_GITHUB_OUT = Path(__file__).resolve().parents[1] / "docs" / "results" / "report_repeat_session_effects_v1"
SEED = 20260826


def bh_adjust(values: pd.Series) -> pd.Series:
    """Benjamini-Hochberg adjustment for the eight pre-specified focal tests."""
    p = values.to_numpy(dtype=float)
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    result = np.empty_like(p)
    result[order] = np.minimum(adjusted, 1.0)
    return pd.Series(result, index=values.index)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_and_prepare(source: Path) -> pd.DataFrame:
    df = pd.read_csv(source)
    needed = {
        "repeat_participant_id", "session_id", "site", "formal_session_index",
        "shared_protocol_progress", "probe_response", "pre10_error_rate",
        "pre10_rt_median_ms", "pre10_rt_sd_ms", "pre10_n_trials",
    }
    missing = needed.difference(df.columns)
    if missing:
        raise RuntimeError(f"Frozen canonical input is missing required fields: {sorted(missing)}")
    df = df.loc[df["site"].eq("Beijing")].copy()
    for col in ["formal_session_index", "shared_protocol_progress", "probe_response",
                "pre10_error_rate", "pre10_rt_median_ms", "pre10_rt_sd_ms", "pre10_n_trials"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["probe_state"] = (df["probe_response"] == 1).astype(float)
    df["progress"] = df["shared_protocol_progress"]
    df["session_order"] = df["formal_session_index"]
    df["progress_x_session"] = df["progress"] * df["session_order"]
    df["error_count"] = np.rint(df["pre10_error_rate"] * df["pre10_n_trials"])
    df["error_count"] = df["error_count"].clip(lower=0)
    df["error_count"] = np.minimum(df["error_count"], df["pre10_n_trials"])
    # Positive, finite fields are the already-available reliable pre-probe summaries.
    df["log_rt_median"] = np.log(df["pre10_rt_median_ms"].where(df["pre10_rt_median_ms"] > 0))
    df["log_rt_sd"] = np.log(df["pre10_rt_sd_ms"].where(df["pre10_rt_sd_ms"] > 0))
    if df["repeat_participant_id"].isna().any() or df["session_order"].isna().any():
        raise RuntimeError("Frozen canonical input has missing repeat participant or session-order keys.")
    return df


def fit_binary(data: pd.DataFrame, outcome: str, name: str) -> pd.DataFrame:
    """Random-intercept logistic model; VB posterior supplies CI and normal-tail p."""
    d = data[[outcome, "progress", "session_order", "progress_x_session", "repeat_participant_id"]].dropna().copy()
    model = BinomialBayesMixedGLM.from_formula(
        f"{outcome} ~ progress + session_order + progress_x_session",
        {"participant_intercept": "0 + C(repeat_participant_id)"}, d,
    )
    fitted = model.fit_vb()
    terms = ["progress", "session_order", "progress_x_session"]
    estimates = pd.DataFrame({
        "term": terms,
        "estimate": fitted.fe_mean[1:],
        "se": fitted.fe_sd[1:],
    })
    estimates["ci95_low"] = estimates["estimate"] - 1.96 * estimates["se"]
    estimates["ci95_high"] = estimates["estimate"] + 1.96 * estimates["se"]
    estimates["p_nominal"] = 2 * norm.sf(np.abs(estimates["estimate"] / estimates["se"]))
    estimates["effect_size"] = np.exp(estimates["estimate"])
    estimates["effect_ci95_low"] = np.exp(estimates["ci95_low"])
    estimates["effect_ci95_high"] = np.exp(estimates["ci95_high"])
    estimates["effect_size_label"] = "OR"
    estimates["model_type"] = "random-intercept logistic mixed model (variational Bayes)"
    estimates["outcome"] = name
    estimates["n_probes"] = len(d)
    estimates["n_participants"] = d["repeat_participant_id"].nunique()
    estimates["n_sessions"] = data.loc[d.index, "session_id"].nunique()
    return estimates


def expand_binomial_counts(data: pd.DataFrame) -> pd.DataFrame:
    """Represent pre10 error numerator/denominator as an exact binomial likelihood."""
    pieces = []
    columns = ["error_count", "pre10_n_trials", "progress", "session_order", "progress_x_session", "repeat_participant_id", "session_id"]
    for row in data[columns].dropna().itertuples(index=False):
        n = int(row.pre10_n_trials)
        errors = int(row.error_count)
        if n <= 0:
            continue
        piece = pd.DataFrame({
            "error": np.r_[np.ones(errors), np.zeros(n - errors)],
            "progress": row.progress,
            "session_order": row.session_order,
            "progress_x_session": row.progress_x_session,
            "repeat_participant_id": row.repeat_participant_id,
            "session_id": row.session_id,
        })
        pieces.append(piece)
    if not pieces:
        raise RuntimeError("No usable pre10 error numerator/denominator rows in frozen input.")
    return pd.concat(pieces, ignore_index=True)


def fit_continuous(data: pd.DataFrame, outcome: str, name: str) -> pd.DataFrame:
    d = data[[outcome, "progress", "session_order", "progress_x_session", "repeat_participant_id"]].dropna().copy()
    fitted = MixedLM.from_formula(
        f"{outcome} ~ progress + session_order + progress_x_session",
        groups="repeat_participant_id", re_formula="1", data=d,
    # BFGS is deliberate: with this data statsmodels' default L-BFGS can falsely
    # settle at a zero-variance, infinite-likelihood boundary. BFGS/CG/Powell
    # independently reach the same finite non-zero random-intercept solution.
    ).fit(reml=False, method="bfgs", maxiter=2000, disp=False)
    terms = ["progress", "session_order", "progress_x_session"]
    estimates = pd.DataFrame({
        "term": terms,
        "estimate": fitted.fe_params.loc[terms].to_numpy(),
        "se": fitted.bse_fe.loc[terms].to_numpy(),
    })
    estimates["ci95_low"] = estimates["estimate"] - 1.96 * estimates["se"]
    estimates["ci95_high"] = estimates["estimate"] + 1.96 * estimates["se"]
    estimates["p_nominal"] = 2 * norm.sf(np.abs(estimates["estimate"] / estimates["se"]))
    estimates["effect_size"] = estimates["estimate"]
    estimates["effect_ci95_low"] = estimates["ci95_low"]
    estimates["effect_ci95_high"] = estimates["ci95_high"]
    estimates["effect_size_label"] = "beta (log-ms)"
    estimates["model_type"] = "linear mixed model with participant random intercept"
    estimates["random_intercept_variance"] = float(fitted.cov_re.iloc[0, 0])
    estimates["outcome"] = name
    estimates["n_probes"] = len(d)
    estimates["n_participants"] = d["repeat_participant_id"].nunique()
    estimates["n_sessions"] = data.loc[d.index, "session_id"].nunique()
    return estimates


def model_set(data: pd.DataFrame, analysis: str) -> pd.DataFrame:
    state = fit_binary(data, "probe_state", "probe_state: response=1 fully task-focused")
    expanded = expand_binomial_counts(data)
    error = fit_binary(expanded, "error", "pre10 error rate (binomial numerator/denominator)")
    error["n_probes"] = len(data)
    rt = fit_continuous(data, "log_rt_median", "pre10 RT median")
    variability = fit_continuous(data, "log_rt_sd", "pre10 RT variability (SD)")
    result = pd.concat([state, error, rt, variability], ignore_index=True)
    result.insert(0, "analysis", analysis)
    return result


def plot_predictions(data: pd.DataFrame, out: Path) -> None:
    """Report-level descriptive plot; model inference remains in the tables."""
    plot = data.copy()
    plot["session_group"] = plot["session_order"].astype(int).astype(str)
    summary = plot.groupby(["session_group", "session_order"], as_index=False).agg(
        probe_state=("probe_state", "mean"), error_rate=("pre10_error_rate", "mean"),
        rt_ms=("pre10_rt_median_ms", "median"), rt_sd_ms=("pre10_rt_sd_ms", "median"),
    ).sort_values("session_order")
    plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False})
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.2), constrained_layout=True)
    panels = [
        ("probe_state", "Probe fully task-focused proportion", "#1f6f8b"),
        ("error_rate", "Pre10 error rate", "#b85c38"),
        ("rt_ms", "Pre10 median RT (ms)", "#4f772d"),
        ("rt_sd_ms", "Pre10 RT variability, SD (ms)", "#745296"),
    ]
    for ax, (column, label, color) in zip(axes.flat, panels):
        ax.plot(summary["session_order"], summary[column], color=color, marker="o", linewidth=2)
        ax.set_xticks(summary["session_order"])
        ax.set_xlabel("Formal session order")
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("北京正式实验：重复 session 的描述性模式（模型控制 protocol progress 并处理 participant 聚类）", fontsize=12)
    fig.savefig(out / "figure_repeat_session_effects.png", dpi=240)
    plt.close(fig)


def write_report(out: Path, primary: pd.DataFrame, sensitivity: pd.DataFrame, data: pd.DataFrame) -> None:
    focal = primary[primary["term"].isin(["session_order", "progress_x_session"])].copy()
    sensitivity_focal = sensitivity[sensitivity["term"].isin(["session_order", "progress_x_session"])].copy()
    comparison = focal.merge(sensitivity_focal, on=["outcome", "term"], suffixes=("_primary", "_earliest3"))
    comparison["direction_same"] = np.sign(comparison["estimate_primary"]) == np.sign(comparison["estimate_earliest3"])
    change_text = "；".join(
        f"{r.outcome}/{r.term}: {'同向' if r.direction_same else '方向改变'}"
        for r in comparison.itertuples()
    )
    state_main = comparison[(comparison["outcome"] == "probe_state: response=1 fully task-focused") & (comparison["term"] == "session_order")].iloc[0]
    state_interaction = comparison[(comparison["outcome"] == "probe_state: response=1 fully task-focused") & (comparison["term"] == "progress_x_session")].iloc[0]
    error_main = comparison[(comparison["outcome"] == "pre10 error rate (binomial numerator/denominator)") & (comparison["term"] == "session_order")].iloc[0]
    error_interaction = comparison[(comparison["outcome"] == "pre10 error rate (binomial numerator/denominator)") & (comparison["term"] == "progress_x_session")].iloc[0]
    rt_main = comparison[(comparison["outcome"] == "pre10 RT median") & (comparison["term"] == "session_order")].iloc[0]
    session_counts = data[["repeat_participant_id", "session_id", "session_order"]].drop_duplicates()
    fourth = int((session_counts["session_order"] >= 4).sum())
    text = f"""# REPORT_REPEAT_SESSION_EFFECTS_V1

## 结论与范围

本报告检验北京正式实验中的重复 session/练习效应。主分析保留所有可用 session，包括第 4 次及以上 session；输入为冻结的 `beijing_zhuhai_shared_probe_master.csv` 中 Beijing 行，不读取毫米波、RGB、NIR 或原始行为文件，也不重做身份恢复。样本为 {len(data)} 个 probe、{session_counts['session_id'].nunique()} 场正式 session、{session_counts['repeat_participant_id'].nunique()} 名具有 `repeat_participant_id` 的 participant；第 4 次及以上有 {fourth} 场 session。

冻结主模型为 `outcome ~ progress + formal_session_index + progress × formal_session_index + (1|participant)`。`progress` 为 canonical `shared_protocol_progress`（0--1）；因此 `session_order` 主效应是 protocol progress=0 时每增加一次正式 session 的差异，交互项表示 session-order 斜率随进度变化。二元 probe state（response=1, fully task-focused）与 pre10 error 使用随机截距 logistic mixed model；RT median 和 RT variability（pre10 RT SD）采用 log(ms) 线性混合模型。对模型表中四个结局的八个预定义 `session_order`/交互焦点检验实施 BH-FDR；progress 项保留在表内以完整报告模型，但不扩展校正 family。

## 主要模型结果

详见 `repeat_session_models.csv`。二元结局的 effect size 为 OR，连续结局的 effect size 为 beta（log-ms）。`p_nominal` 为拟合分布近似双侧 p 值，`p_bh_focal_8` 是上述有限的预定义 8 项 FDR 校正。变分 Bayes logistic mixed model 的 CI/p 值是近似推断，需与小样本高阶 session 稀疏性一同解释。

## 预先定义敏感性

敏感性分析对每名 participant 只保留最早 3 场 (`formal_session_index <= 3`)，不删除主分析的任何行。完整结果见 `repeat_session_sensitivity.csv`。主分析与敏感性中 session-order 与 progress 交互的符号比较为：{change_text}。该比较只回答第 4 次单一 session 是否显著改变方向/估计，不能作为对高阶 session 的充分精确性证明。

敏感性改变了部分主要 session-order 结论：fully task-focused 的 session-order OR 从主分析 {state_main.effect_size_primary:.2f}（FDR p={state_main.p_bh_focal_8_primary:.3g}）变为最早三场 {state_main.effect_size_earliest3:.2f}（FDR p={state_main.p_bh_focal_8_earliest3:.3g}），后者不再精确；RT median 的 session-order beta 则从主分析 FDR p={rt_main.p_bh_focal_8_primary:.3g} 变为最早三场 FDR p={rt_main.p_bh_focal_8_earliest3:.3g}。相反，fully task-focused 的 progress 交互（主/敏感性 OR={state_interaction.effect_size_primary:.2f}/{state_interaction.effect_size_earliest3:.2f}）以及 error 的 session-order（OR={error_main.effect_size_primary:.2f}/{error_main.effect_size_earliest3:.2f}）和 progress 交互（OR={error_interaction.effect_size_primary:.2f}/{error_interaction.effect_size_earliest3:.2f}）方向一致且均保持 FDR 后显著。因此，不能把包含第 4 次 session 的 fully task-focused 起始主效应或 RT 主效应写成稳健的重复练习结论；较稳健的信号是 error 的 session-order/进度交互与 probe-state 的进度交互。

## 限制

- `formal_session_index=4` 只有一场、一个 participant；对高阶重复练习效应的区间会不稳定，不能据此主张一般化的第 4 次效应。
- 这是已有 canonical probe 层的关联模型，session order 可能与未测量的招募、日程或设备因素混杂，不构成随机化练习效应因果估计。
- pre10 行为窗口彼此可能重叠；error 的分子/分母被作为可复用的窗口汇总建模，不能替代对 trial-level serial dependence 的专门分析。
- 结果只适用于冻结北京正式协议及其已确认的 response=1 构念，不推广到珠海或其他程序版本。

## 可复现产物与脱敏边界

- `repeat_session_models.csv`、`repeat_session_sensitivity.csv`、`figure_repeat_session_effects.png` 和本报告为脱敏聚合交付物，可随 Git 提交。
- `local_input_audit.csv` 保留 pseudonymous participant/session 行级资格信息，只在本地 derived 目录保存，不复制至 GitHub。
"""
    (out / "REPORT_REPEAT_SESSION_EFFECTS_RESULT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--github-out", type=Path, default=DEFAULT_GITHUB_OUT)
    args = parser.parse_args()
    out, github_out = args.out, args.github_out
    out.mkdir(parents=True, exist_ok=True)
    data = validate_and_prepare(INPUT)
    # Local-only identity audit is deliberately excluded from github_out.
    data[["repeat_participant_id", "session_id", "session_order", "progress"]].to_csv(out / "local_input_audit.csv", index=False, encoding="utf-8-sig")
    primary = model_set(data, "primary_all_sessions")
    earliest3 = data.loc[data["session_order"] <= 3].copy()
    sensitivity = model_set(earliest3, "sensitivity_earliest_three_sessions_per_participant")
    focal_mask = primary["term"].isin(["session_order", "progress_x_session"])
    adjusted_primary = bh_adjust(primary.loc[focal_mask, "p_nominal"])
    primary["p_bh_focal_8"] = np.nan
    sensitivity["p_bh_focal_8"] = np.nan
    primary.loc[focal_mask, "p_bh_focal_8"] = adjusted_primary.to_numpy()
    s_mask = sensitivity["term"].isin(["session_order", "progress_x_session"])
    sensitivity.loc[s_mask, "p_bh_focal_8"] = bh_adjust(sensitivity.loc[s_mask, "p_nominal"]).to_numpy()
    primary.to_csv(out / "repeat_session_models.csv", index=False, encoding="utf-8-sig")
    sensitivity.to_csv(out / "repeat_session_sensitivity.csv", index=False, encoding="utf-8-sig")
    plot_predictions(data, out)
    manifest = {
        "run_id": "REPORT_REPEAT_SESSION_EFFECTS_V1_20260826",
        "input": str(INPUT), "input_sha256": sha256(INPUT), "input_rows_beijing": int(len(data)),
        "n_sessions": int(data["session_id"].nunique()), "n_participants": int(data["repeat_participant_id"].nunique()),
        "session_index_counts": {str(k): int(v) for k, v in data[["session_id", "session_order"]].drop_duplicates()["session_order"].value_counts().sort_index().items()},
        "primary": "all formal sessions; random participant intercept", "sensitivity": "earliest three sessions per participant",
        "excluded_modalities": ["mmWave", "RGB", "NIR"], "seed": SEED,
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(out, primary, sensitivity, data)
    github_out.mkdir(parents=True, exist_ok=True)
    for name in ["repeat_session_models.csv", "repeat_session_sensitivity.csv", "REPORT_REPEAT_SESSION_EFFECTS_RESULT.md", "figure_repeat_session_effects.png"]:
        shutil.copy2(out / name, github_out / name)


if __name__ == "__main__":
    main()
