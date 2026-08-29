from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


METRIC_LABELS_ZH = {
    "go_correct_rt_mean_ms": "正确Go反应时均值（毫秒）",
    "go_correct_rt_median_ms": "正确Go反应时中位数（毫秒）",
    "go_correct_rt_sd_ms": "正确Go反应时标准差（毫秒）",
    "go_correct_rt_mad_ms": "正确Go反应时MAD（毫秒）",
    "go_correct_rt_iqr_ms": "正确Go反应时IQR（毫秒）",
    "go_correct_rt_cv": "正确Go反应时变异系数",
    "go_correct_rt_theilsen_slope_ms_per_s": "正确Go反应时Theil–Sen斜率（毫秒/秒）",
    "omission_rate": "Go遗漏率",
    "commission_rate": "No-Go误按率",
    "dprime_loglinear": "辨别力 d′",
    "criterion_c": "判据 c",
    "beta": "反应偏向 β",
}


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _q1_category_figure(primary_probe: pd.DataFrame, out: Path) -> dict[str, Any]:
    metric = "go_correct_rt_mean_ms"
    d = primary_probe.copy()
    d["q1_nominal_4class"] = pd.to_numeric(d.get("q1_nominal_4class"), errors="coerce")
    d[metric] = pd.to_numeric(d.get(metric), errors="coerce")
    rows = []
    for level in [1, 2, 3, 4]:
        x = d.loc[d.q1_nominal_4class.eq(level), metric].dropna()
        mean = float(x.mean()) if len(x) else math.nan
        se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else math.nan
        rows.append({"Q1类别": str(level), "均值": mean, "下限": mean - 1.96 * se if np.isfinite(se) else math.nan,
                     "上限": mean + 1.96 * se if np.isfinite(se) else math.nan, "probe_n": int(len(x))})
    p = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 5))
    yerr = np.vstack([p["均值"] - p["下限"], p["上限"] - p["均值"]])
    ax.errorbar(np.arange(4), p["均值"], yerr=yerr, fmt="o", linestyle="none", capsize=4)
    ax.set_xticks(np.arange(4), ["Q1-1", "Q1-2", "Q1-3", "Q1-4"])
    ax.set_xlabel("Q1无序类别（类别间不连线）")
    ax.set_ylabel(METRIC_LABELS_ZH[metric])
    ax.set_title("Q1类别与探针前行为：无序类别点估计")
    ax.grid(axis="y", alpha=.2)
    path = out / "fig_q1_nominal_categories.png"
    _save(fig, path)
    p.to_csv(out / "fig_q1_nominal_categories_data.csv", index=False, encoding="utf-8-sig")
    return {"figure_id": "q1_nominal_categories", "filename": path.name,
            "observation_unit": "probe", "denominator": "每个Q1类别内有效主probe数",
            "model_status": "descriptive_plot; formal model status stored separately",
            "scientific_boundary_zh": "Q1为无序类别；图中不连线、不解释等距趋势"}


def _qc_figures(qc: pd.DataFrame, out: Path) -> list[dict[str, Any]]:
    records = []
    for row in qc.itertuples(index=False):
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.bar([str(row.observation_unit_zh)], [float(row.count)])
        ax.set_ylabel("计数")
        ax.set_title(f"QC计数：{row.observation_unit_zh}")
        ax.text(0, float(row.count), f"n={int(row.count)} / 分母={int(row.denominator)}", ha="center", va="bottom")
        path = out / f"fig_qc_{row.layer}.png"
        _save(fig, path)
        records.append({"figure_id": f"qc_{row.layer}", "filename": path.name,
                        "observation_unit": row.layer, "denominator": int(row.denominator),
                        "model_status": "engineering_qc_only",
                        "scientific_boundary_zh": str(row.repeat_handling_zh)})
    return records


def _multiscale_figures(block: pd.DataFrame, session: pd.DataFrame, out: Path) -> list[dict[str, Any]]:
    records = []
    for layer, d in [("block", block), ("session", session)]:
        metrics = [m for m in ["go_correct_rt_mean_ms", "go_correct_rt_median_ms", "go_correct_rt_cv",
                               "omission_rate", "commission_rate", "dprime_loglinear", "criterion_c", "beta"] if m in d]
        if not metrics:
            continue
        summary = []
        for metric in metrics:
            x = pd.to_numeric(d[metric], errors="coerce").dropna()
            summary.append({"metric": metric, "label": METRIC_LABELS_ZH.get(metric, metric),
                            "mean": float(x.mean()) if len(x) else math.nan, "n": int(len(x))})
        s = pd.DataFrame(summary)
        # Separate unit families so visually incomparable metrics are never placed on one axis.
        families = {
            "RT_ms": ["go_correct_rt_mean_ms", "go_correct_rt_median_ms"],
            "rate": ["omission_rate", "commission_rate"],
            "ratio": ["go_correct_rt_cv", "beta"],
            "sdt": ["dprime_loglinear", "criterion_c"],
        }
        for family, names in families.items():
            sub = s[s.metric.isin(names)].copy()
            if sub.empty:
                continue
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.bar(sub.label, sub["mean"])
            ax.tick_params(axis="x", rotation=20)
            ax.set_title(f"{layer}层级：{family}指标（同量纲面板）")
            ax.set_ylabel({"RT_ms": "毫秒", "rate": "比例", "ratio": "比率", "sdt": "无量纲SDT"}[family])
            path = out / f"fig_{layer}_{family}.png"
            _save(fig, path)
            sub.to_csv(out / f"fig_{layer}_{family}_data.csv", index=False, encoding="utf-8-sig")
            records.append({"figure_id": f"{layer}_{family}", "filename": path.name,
                            "observation_unit": layer, "denominator": f"各指标有效{layer}行数，见配套data.csv的n",
                            "model_status": "descriptive_only",
                            "scientific_boundary_zh": "不同量纲分图，不允许跨量纲视觉排序"})
    return records


def _forest_figures(forest: pd.DataFrame, out: Path) -> list[dict[str, Any]]:
    records = []
    if forest.empty:
        return records
    for facet, d in forest.groupby("facet", sort=False):
        d = d.dropna(subset=["estimate", "ci_low", "ci_high"]).copy()
        if d.empty:
            continue
        d["label"] = d["outcome"].map(METRIC_LABELS_ZH).fillna(d["outcome"]) + "｜" + d["term"].astype(str)
        y = np.arange(len(d))
        fig, ax = plt.subplots(figsize=(10, max(4, .45 * len(d))))
        ax.errorbar(d.estimate, y, xerr=[d.estimate - d.ci_low, d.ci_high - d.estimate], fmt="o")
        ax.axvline(0, linewidth=.8)
        ax.set_yticks(y, d.label)
        ax.set_xlabel(f"估计值（95% CI）；单位：{d.unit.iloc[0]}")
        ax.set_title(f"正式效应森林图分面：{facet}")
        ax.grid(axis="x", alpha=.2)
        safe = str(facet).replace("/", "_").replace("（", "_").replace("）", "_")
        path = out / f"fig_forest_{safe}.png"
        _save(fig, path)
        records.append({"figure_id": f"forest_{safe}", "filename": path.name,
                        "observation_unit": "probe repeated-measures model",
                        "denominator": "每个模型的probe/session/participant N见模型结果表",
                        "model_status": "formal_only_for_rows_with_formal_inference=true",
                        "scientific_boundary_zh": "仅同一量纲分面内展示；不得按横坐标大小跨分面排序"})
    return records


def generate_chinese_report_assets(output_dir: Path, primary_probe: pd.DataFrame, block: pd.DataFrame,
                                   session: pd.DataFrame, qc: pd.DataFrame, forest: pd.DataFrame,
                                   failures: pd.DataFrame) -> tuple[pd.DataFrame, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [_q1_category_figure(primary_probe, output_dir)]
    records.extend(_qc_figures(qc, output_dir))
    records.extend(_multiscale_figures(block, session, output_dir))
    records.extend(_forest_figures(forest, output_dir))
    manifest = pd.DataFrame(records)
    manifest.to_csv(output_dir / "figure_manifest_v3.csv", index=False, encoding="utf-8-sig")

    participant = "participant_cluster_ref" if "participant_cluster_ref" in session else "anonymous_participant_group_id"
    session_n = int(session.session_id.nunique())
    participant_n = int(session[participant].nunique())
    repeat_n = int(session[[participant, "session_id"]].drop_duplicates().groupby(participant).size().eq(2).sum())
    failure_n = int(len(failures))
    lines = [
        "# 行为科学 v3 结果与准入说明",
        "",
        "## 1. 数据层级与分析单位",
        "",
        f"本次运行从输入表动态得到 {session_n} 个 session、{participant_n} 个当前匿名参与者分析组，其中双场重复组为 {repeat_n} 个。上述数字属于运行时队列审计，不是写死在代码中的永久身份常量。主 probe 表严格一 probe 一行；10/20/30 秒窗口只存在于独立敏感性表，不增加主分析样本量。未来队列扩展后必须重新构建完整匿名身份映射。",
        "",
        "## 2. 行为指标",
        "",
        "probe、block、session 层输出均保留正确 Go 反应时均值/中位数、SD、MAD、IQR、CV、Theil–Sen RT斜率，以及 Go omission（遗漏）和 No-Go commission（误按）的独立分子、分母和比例。信号检测指标 d′、c、β 仅在机会数门控通过时计算。Go 遗漏与 No-Go 误按不合并成一个 correct 因变量。",
        "",
        "## 3. Q1 / Q2 与重复测量",
        "",
        "Q1 固定按四类无序分类处理，图中类别不连线；正式模型只有在 participant 随机效应、session 嵌套方差结构、参考类别、类别完整性和收敛门均通过时才进入正式结果表。Q2 是四级有序结果；当前实现没有经过审计的 participant/session 聚类有序模型后端，因此正式 Q2 推断 fail closed，仅输出描述性候选结果，禁止使用无聚类 OrderedModel 冒充正式推断。",
        "",
        "## 4. B1–B2、错误事件与重复参与者",
        "",
        "B1–B2 先在同一 session 内唯一配对，再保留 participant 聚类供后续不确定性估计；重复参与者的 session_order 必须显式提供，不从 session ID 或时间排序推断。错误轨迹对同一 target trial 被多个错误事件覆盖的情况采用 nearest-event 规则去重，并同时保存 overlap audit；另输出参与者内中心化值和预错误基线差值。",
        "",
        "## 5. 相关、森林图、QC 与候选准入",
        "",
        "相关关系逐对分类为数学恒等/互补、共享派生冗余、同测量族冗余或行为关联；前三类不得写成心理机制证据。森林图按结果族和量纲分面。QC 的 session、participant group、block、probe、trial 分开成图并各自给出分母，不放在同一可比较计数轴。候选矩阵保存证据来源、规则版本、硬门控/软建议/科学禁止状态，不使用无证据 0/1 作为最终准入。",
        "",
        "## 6. 失败、限制与正式报告边界",
        "",
        f"本次运行记录了 {failure_n} 条模型或契约失败记录。失败必须进入 `model_failures_v3.csv`，不得以空表或缺失图形静默隐藏。工程测试、代码可执行性和合成 fixture 通过只代表工程/方法合同得到验证，不代表行为测量效度、真实队列统计结论或心理机制已经获得正式准入。",
    ]
    report_path = output_dir / "行为科学v3结果与准入说明.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest, report_path
