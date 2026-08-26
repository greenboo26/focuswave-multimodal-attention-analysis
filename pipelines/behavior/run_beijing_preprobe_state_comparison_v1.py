"""Compare pre-probe behavior by the frozen BB probe-state contrast.

Input is the existing 1,400-row probe_event_level_behavior.csv.  This script
does not rebuild identity, timelines, trials, or probe mappings.
"""
from pathlib import Path
import json
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


OUT = Path(r"D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1")
INPUT = OUT / "probe_event_level_behavior.csv"
WINDOWS = (10, 20, 30)
METRICS = {
    "error_rate": "error_rate",
    "rt_median_ms": "rt_median_ms",
    "rt_sd_ms": "rt_sd_ms",
}


def bh_fdr(p_values):
    p = np.asarray(p_values, dtype=float)
    out = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    if not ok.any():
        return out
    order = np.argsort(p[ok])
    ranked = p[ok][order]
    q = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    restored = np.empty_like(q)
    restored[order] = np.minimum(q, 1.0)
    out[ok] = restored
    return out


def fit_gee(data, outcome, formula=None):
    required = [outcome, "target_label1", "repeat_participant_id"]
    if formula and "probe_progress" in formula:
        required.append("probe_progress")
    if formula and "block_num" in formula:
        required.append("block_num")
    d = data.dropna(subset=required).copy()
    if d["target_label1"].nunique() < 2 or d["repeat_participant_id"].nunique() < 3:
        return {"n": len(d), "participants": d["repeat_participant_id"].nunique(), "beta": np.nan, "ci_low": np.nan, "ci_high": np.nan, "p_value": np.nan, "status": "insufficient_groups"}
    d["target_label1"] = d["target_label1"].astype(float)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = smf.gee(
                formula or f"{outcome} ~ target_label1",
                groups="repeat_participant_id",
                data=d,
                cov_struct=sm.cov_struct.Exchangeable(),
                family=sm.families.Gaussian(),
            ).fit()
        term = model.params["target_label1"]
        ci = model.conf_int().loc["target_label1"]
        return {"n": len(d), "participants": d["repeat_participant_id"].nunique(), "beta": term, "ci_low": ci.iloc[0], "ci_high": ci.iloc[1], "p_value": model.pvalues["target_label1"], "status": "ok"}
    except Exception as exc:
        return {"n": len(d), "participants": d["repeat_participant_id"].nunique(), "beta": np.nan, "ci_low": np.nan, "ci_high": np.nan, "p_value": np.nan, "status": f"failed:{type(exc).__name__}"}


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)
    probes = pd.read_csv(INPUT)
    probes["target_label1"] = pd.to_numeric(probes["target_label1"], errors="coerce")
    probes["state_name"] = np.where(probes["target_label1"].eq(1), "完全任务聚焦", "其他非完全任务聚焦")

    desc_rows = []
    model_rows = []
    for window in WINDOWS:
        for metric, prefix in METRICS.items():
            col = f"pre{window}_{prefix}" if metric != prefix else f"pre{window}_{metric}"
            # METRICS values intentionally map to the existing column suffixes.
            if metric == "error_rate":
                col = f"pre{window}_error_rate"
            elif metric == "rt_median_ms":
                col = f"pre{window}_rt_median_ms"
            elif metric == "rt_sd_ms":
                col = f"pre{window}_rt_sd_ms"
            d = probes[["subject", "repeat_participant_id", "target_label1", "state_name", "probe_progress", "block_num", col]].rename(columns={col: "value"})
            for state, g in d.groupby("state_name", dropna=False):
                vals = pd.to_numeric(g["value"], errors="coerce").dropna()
                desc_rows.append({
                    "window_s": window, "metric": metric, "state": state,
                    "n_probe": int(vals.size), "n_participant": int(g.loc[vals.index, "repeat_participant_id"].nunique()),
                    "mean": vals.mean(), "sd": vals.std(ddof=1), "median": vals.median(),
                })
            d_model = d.rename(columns={"value": "outcome"})
            result = fit_gee(d_model, "outcome")
            result.update({"window_s": window, "metric": metric, "contrast": "完全任务聚焦 - 其他非完全任务聚焦"})
            model_rows.append(result)

            adjusted = fit_gee(
                d_model,
                "outcome",
                formula="outcome ~ target_label1 + probe_progress + C(block_num)",
            )
            adjusted.update({"window_s": window, "metric": metric, "contrast": "完全任务聚焦 - 其他非完全任务聚焦; adjusted for probe_progress + block_num"})
            model_rows.append(adjusted)

    desc = pd.DataFrame(desc_rows)
    models = pd.DataFrame(model_rows)
    models["q_bh"] = bh_fdr(models["p_value"].to_numpy())
    desc.to_csv(OUT / "preprobe_state_group_descriptives.csv", index=False, encoding="utf-8-sig")
    models.to_csv(OUT / "preprobe_state_group_gee.csv", index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    order = ["完全任务聚焦", "其他非完全任务聚焦"]
    for ax, (metric, suffix, title) in zip(axes, [("error_rate", "error_rate", "错误率"), ("rt_median_ms", "rt_median_ms", "RT 中位数（ms）"), ("rt_sd_ms", "rt_sd_ms", "RT 标准差（ms）")]):
        plot = []
        for window in WINDOWS:
            for state in order:
                row = desc[(desc.window_s == window) & (desc.metric == metric) & (desc.state == state)]
                plot.append({"window_s": window, "state": state, "mean": row["mean"].iloc[0] if len(row) else np.nan})
        p = pd.DataFrame(plot)
        for state, g in p.groupby("state"):
            ax.plot(g["window_s"], g["mean"], marker="o", label=state)
        ax.set_title(title)
        ax.set_xlabel("Probe 前窗口（s）")
        ax.grid(alpha=.25)
    axes[0].set_ylabel("均值")
    axes[-1].legend(frameon=False, fontsize=8)
    fig.suptitle("北京 Probe 前行为：按 Probe 状态分组")
    fig.savefig(OUT / "fig_preprobe_state_group_comparison.png", dpi=180)
    plt.close(fig)

    manifest = {
        "run_id": "BEIJING_PREPROBE_STATE_COMPARISON_V1",
        "input": str(INPUT),
        "input_rows": int(len(probes)),
        "windows_s": list(WINDOWS),
        "contrast": "target_label1=1 vs target_label1=0",
        "outcomes": list(METRICS),
        "model": "Gaussian GEE with exchangeable working correlation, clustered by repeat_participant_id; adjusted model adds probe_progress and block_num",
        "multiplicity": "Benjamini-Hochberg FDR across 18 unadjusted and adjusted tests",
        "identity_or_timeline_rebuild": False,
        "formal_state_semantics": "1=完全任务聚焦; 0=其他非完全任务聚焦; 2/3/4 not collapsed into generic mind-wandering",
    }
    (OUT / "preprobe_state_group_run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"input_rows": len(probes), "descriptives": str(OUT / "preprobe_state_group_descriptives.csv"), "gee": str(OUT / "preprobe_state_group_gee.csv")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
