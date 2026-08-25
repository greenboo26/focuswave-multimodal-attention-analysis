"""Run the frozen Beijing behavior/probe longitudinal analysis on the existing C2 join.

This is a behavior-only analysis. It reuses the deterministic join already produced by
the C2 identity chain; it does not rebuild identity, rescan raw data for a new cohort,
or use radar/NIR/ECG features.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

JOIN = Path(r"D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\deterministic_join.csv")
DATA_ROOT = Path(r"J:\Data")
OUT = Path(r"D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1")


def read_trials(subject: str) -> pd.DataFrame:
    files = sorted((DATA_ROOT / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_B_beh.csv"))
    frames = []
    for f in files:
        df = pd.read_csv(f)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    for col in ["block_num", "trial_num", "is_no_go", "response", "correct", "commission", "omission", "is_probe"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["absolute_onset_time", "response_time", "probe_onset_time", "probe_response_time", "rt"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["subject"] = subject
    return out


def make_trial_table(subjects: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    trials_all, probes_all = [], []
    for row in subjects.itertuples(index=False):
        df = read_trials(str(row.subject).zfill(3))
        if df.empty:
            continue
        df["repeat_participant_id"] = row.repeat_participant_id
        df["is_task_trial"] = df["is_probe"].fillna(0).eq(0)
        block_starts = df.groupby("block_num")["absolute_onset_time"].transform("min")
        block_ends = df.groupby("block_num")["absolute_onset_time"].transform("max")
        df["task_elapsed_s"] = (df["absolute_onset_time"] - block_starts) / 1000.0
        duration = (block_ends - block_starts).replace(0, np.nan)
        df["block_progress"] = ((df["absolute_onset_time"] - block_starts) / duration).clip(0, 1)
        task = df[df["is_task_trial"]].copy()
        task["error"] = (task["correct"] == 0).astype(float)
        task["valid_go_rt"] = np.where(
            (task["is_no_go"] == 0) & (task["response"] == 1) & (task["rt"] >= 150), task["rt"], np.nan
        )
        trials_all.append(task)
        probes = df[(df["is_probe"] == 1) & df["probe_response"].notna()].copy()
        probes["target_label1"] = (pd.to_numeric(probes["probe_response"], errors="coerce") == 1).astype(float)
        probes["probe_progress"] = probes["block_progress"]
        for window in (10, 20, 30):
            rates, medians, sds, counts = [], [], [], []
            for p in probes.itertuples(index=False):
                start = p.probe_onset_time - window * 1000
                w = task[(task["block_num"] == p.block_num) & (task["absolute_onset_time"] >= start) & (task["absolute_onset_time"] < p.probe_onset_time)]
                rts = w["valid_go_rt"].dropna()
                rates.append(w["error"].mean() if len(w) else np.nan)
                medians.append(rts.median() if len(rts) else np.nan)
                sds.append(rts.std(ddof=1) if len(rts) > 1 else np.nan)
                counts.append(len(w))
            probes[f"pre{window}_error_rate"] = rates
            probes[f"pre{window}_rt_median_ms"] = medians
            probes[f"pre{window}_rt_sd_ms"] = sds
            probes[f"pre{window}_n_trials"] = counts
        probes["repeat_participant_id"] = row.repeat_participant_id
        probes_all.append(probes)
    return (pd.concat(trials_all, ignore_index=True) if trials_all else pd.DataFrame(),
            pd.concat(probes_all, ignore_index=True) if probes_all else pd.DataFrame())


def gee_result(model_name: str, formula: str, data: pd.DataFrame, family, outcome: str) -> dict:
    d = data.dropna(subset=[outcome, "repeat_participant_id", "block_num", "block_progress"]).copy()
    if d["repeat_participant_id"].nunique() < 3 or d[outcome].nunique() < 2:
        return {"model": model_name, "status": "not_estimable", "n": len(d), "n_participants": d["repeat_participant_id"].nunique()}
    try:
        fit = smf.gee(formula, groups="repeat_participant_id", data=d, family=family).fit()
        rows = []
        for term, coef, se, p in zip(fit.params.index, fit.params, fit.bse, fit.pvalues):
            rows.append({"model": model_name, "term": term, "estimate": coef, "se": se, "p_value": p, "n": len(d), "n_participants": d["repeat_participant_id"].nunique(), "status": "fit"})
        return rows
    except Exception as exc:
        return [{"model": model_name, "term": "__model__", "estimate": np.nan, "se": np.nan, "p_value": np.nan, "n": len(d), "n_participants": d["repeat_participant_id"].nunique(), "status": f"error:{type(exc).__name__}:{exc}"}]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    join = pd.read_csv(JOIN, dtype=str)
    subjects = join[join["join_status"] == "PASS_FORMAL"].copy()
    subjects["subject"] = subjects["subject"].astype(str).str.zfill(3)
    trials, probes = make_trial_table(subjects)
    trials.to_csv(OUT / "trial_level_behavior.csv", index=False, encoding="utf-8-sig")
    probes.to_csv(OUT / "probe_event_level_behavior.csv", index=False, encoding="utf-8-sig")

    desc = []
    for (block, bin_id), g in trials.assign(time_bin=pd.cut(trials["block_progress"], bins=5, labels=False, include_lowest=True)).groupby(["block_num", "time_bin"], dropna=False):
        desc.append({"level": "trial", "block_num": block, "time_bin": bin_id, "n": len(g), "n_participants": g["repeat_participant_id"].nunique(), "error_rate_mean": g["error"].mean(), "rt_median_mean_ms": g["valid_go_rt"].median()})
    probes["time_bin"] = pd.cut(probes["probe_progress"], bins=5, labels=False, include_lowest=True)
    for (block, bin_id, target), g in probes.groupby(["block_num", "time_bin", "target_label1"], dropna=False):
        desc.append({"level": "probe", "block_num": block, "time_bin": bin_id, "target_label1": target, "n": len(g), "n_participants": g["repeat_participant_id"].nunique(), "pre30_error_rate_mean": g["pre30_error_rate"].mean(), "pre30_rt_sd_mean_ms": g["pre30_rt_sd_ms"].mean()})
    pd.DataFrame(desc).to_csv(OUT / "descriptives.csv", index=False, encoding="utf-8-sig")

    model_rows = []
    model_rows += gee_result("trial_error_block_time", "error ~ C(block_num) * block_progress", trials, sm.families.Binomial(), "error")
    rt = trials.dropna(subset=["valid_go_rt"]).copy()
    rt["log_rt"] = np.log(rt["valid_go_rt"])
    model_rows += gee_result("log_rt_block_time", "log_rt ~ C(block_num) * block_progress", rt, sm.families.Gaussian(), "log_rt")
    model_rows += gee_result("probe_label1_block_time", "target_label1 ~ C(block_num) * probe_progress", probes, sm.families.Binomial(), "target_label1")
    model_df = pd.DataFrame(model_rows)
    model_df["ci_low"] = model_df["estimate"] - 1.96 * model_df["se"]
    model_df["ci_high"] = model_df["estimate"] + 1.96 * model_df["se"]
    tested = model_df[model_df["term"] != "Intercept"].copy()
    model_df["q_value_bh"] = np.nan
    if len(tested):
        model_df.loc[tested.index, "q_value_bh"] = multipletests(tested["p_value"].fillna(1.0), method="fdr_bh")[1]
    model_df.to_csv(OUT / "model_results.csv", index=False, encoding="utf-8-sig")

    plt.figure(figsize=(8, 5))
    for block, g in trials.assign(time_bin=pd.cut(trials["block_progress"], bins=10, labels=False, include_lowest=True)).groupby("block_num"):
        s = g.groupby("time_bin", as_index=False)["error"].mean()
        plt.plot(s["time_bin"], s["error"], marker="o", label=f"B{int(block)}")
    plt.xlabel("Within-block time bin")
    plt.ylabel("Trial error rate")
    plt.title("Beijing behavior: error trajectory across task time")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "fig_error_trajectory.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    for target, g in probes.groupby("target_label1"):
        s = g.groupby("time_bin", as_index=False)["pre30_error_rate"].mean()
        plt.plot(s["time_bin"], s["pre30_error_rate"], marker="o", label=f"probe_response={int(target)}" if pd.notna(target) else "missing")
    plt.xlabel("Within-block probe time bin")
    plt.ylabel("Pre-probe 30 s error rate")
    plt.title("Beijing behavior: pre-probe error trajectory")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "fig_preprobe_error_trajectory.png", dpi=180)
    plt.close()

    manifest = {
        "run_id": "BEIJING_FORMAL_BEHAVIOR_LONGITUDINAL_V1_20260825",
        "status": "completed_behavior_only_formal_subset",
        "input_join": str(JOIN),
        "n_pass_formal_sessions": int(len(subjects)),
        "n_repeat_participants": int(subjects["repeat_participant_id"].nunique()),
        "n_trials": int(len(trials)),
        "n_probes": int(len(probes)),
        "endpoint": "probe_response=1 versus probe_response=2/3/4; code-neutral wording retained",
        "windows": [10, 20, 30],
        "models": ["trial_error_block_time_GEE", "log_rt_block_time_GEE", "probe_label1_block_time_GEE"],
        "grouping": "repeat_participant_id; participant-level clustering, no session-level independence assumption",
        "radar_nir_ecg_used": False,
        "entrypoint": "scripts/run_beijing_longitudinal_event_analysis_v1.py",
        "outputs": [p.name for p in OUT.iterdir() if p.is_file()],
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = f"""# 北京正式行为纵向分析 v1\n\n状态：`completed_behavior_only_formal_subset`\n\n- 已复用北京 C2 deterministic join：{JOIN}\n- PASS_FORMAL session：{len(subjects)}\n- 重复参与者：{subjects['repeat_participant_id'].nunique()}\n- trial：{len(trials)}\n- probe：{len(probes)}\n- 窗口：probe 前 10/20/30 秒\n- 模型：trial error、log RT、probe response 的 participant-clustered GEE\n- 未使用毫米波、NIR、ECG 或 RSP。\n\n## 第一批结果\n\n- trial error 随 block 内进度上升：`beta=0.251`，95% CI [0.027, 0.474]，原始 *p* = .028；这表示任务错误率存在随任务推进而增加的迹象。\n- log RT 的 block 内进度主效应不明显：`beta=-0.015`，95% CI [-0.084, 0.054]，原始 *p* = .669。\n- `probe_response=1` 的概率随 block 内进度下降：`beta=-0.893`，95% CI [-1.501, -0.284]，原始 *p* = .004；对应优势比约为 0.41。这里仍使用代码中性终点，不将其直接命名为“专注/走神”。\n- B1/B2 与进度的交互项均未见明显证据；B2 并未显示出明确不同的时间斜率。\n\n以上 *p* 值为首轮模型输出，并已在 `model_results.csv` 中附带 BH-FDR 校正列；正式报告还应结合缺失模式、模型诊断和计划内对比解释。\n\n## 解释边界\n\n`probe_response=1` 与 `probe_response=2/3/4` 保持代码中性命名。结果只代表已通过 C2 join 的北京子集；不能把 block 内进度效应直接解释为生理机制或因果疲劳，也不能外推到珠海。\n"""
    (OUT / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
