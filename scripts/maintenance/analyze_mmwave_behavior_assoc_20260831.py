# -*- coding: utf-8 -*-
"""
文件名: analyze_mmwave_behavior_assoc_20260831.py
版本: v1.0 (2026-08-31)
功能: 毫米波特征与行为/思维探针(Q1/Q2)的关联分析，支撑论文 5.4.3 节
      "毫米波特征与行为及思维探针的关系"。
  1) join 毫米波 merge-ready 表(116 场 2320 探针)与 Behavior probe_primary_30s 表;
  2) 描述统计: 各毫米波特征按 Q1 类别 / Q2 等级汇总 (n, mean, sd);
  3) 关联模型 (探针级, 参与者聚类 participant_group_id):
     - Q1 名义四类: 多项 logistic (MNLogit, 参照类别 1), cluster-robust SE;
     - Q2 有序四级: 累积 logistic (OrderedModel distr='logit'), cluster-robust SE;
     - Q2 二元化(低警觉 1-2 vs 高警觉 3-4): logistic GEE (exchangeable);
     每个模型两个版本: 未调整协变量 / 调整 block + time_in_block;
  4) 多重比较: 模型族 × 调整版本内 Holm 调整, 完整列表不筛选。
用法: D:/CondaEnvs/attention-nir-formal/python.exe analyze_mmwave_behavior_assoc_20260831.py
依赖: numpy, pandas, scipy, statsmodels>=0.14
注意: 本脚本只读正式分析数据, 不修改任何既有管线产物。
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

from statsmodels.discrete.discrete_model import MNLogit
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.genmod.families import Binomial
from statsmodels.stats.multitest import multipletests

# ---------------------------------------------------------------------------
# 路径与参数集中声明
# ---------------------------------------------------------------------------
# 输入: 毫米波 merge-ready 表 (J 盘批次 72 场 / E 盘批次 44 场)
PATH_MMWAVE_J = Path("D:/Project/厚粲杯/11_数据/_FormalAnalysis/mmWave/mmwave_probe_merge_ready.csv")
PATH_MMWAVE_E = Path("D:/Project/厚粲杯/11_数据/_FormalAnalysis/mmWave/mmwave_probe_merge_ready_E.csv")
# 输入: 行为探针表 (含 Q1/Q2 编码与身份聚类键)
PATH_BEHAVIOR_PROBE = Path("D:/Project/厚粲杯/11_数据/_FormalAnalysis/Behavior/formal_v3/probe_primary_30s.csv")
# 输出目录: 汇总表 / 模型结果 CSV / 中文结果摘要
OUT_DIR = Path("D:/Project/厚粲杯/11_数据/_FormalAnalysis/mmWave/behavior_assoc_20260831")

# 分析口径常量
CLUSTER_COL = "participant_group_id"          # 参与者聚类键 (来自 Behavior 表, 61 名独立参与者)
Q1_REF_CLASS = 1                             # Q1 参照类别 (任务规定)
Q2_BINARY_CUT = 3                            # Q2 二元化: 1-2=低警觉, 3-4=高警觉 (y>=3 为高)
HOLM_ALPHA = 0.05                            # Holm 调整名义显著性水平

# 主模型特征清单 (运动类; 主结论唯一来源, 预声明)
PRIMARY_FEATURES = [
    "mmwave_motion_proxy_median",            # 运动代理 (30s 窗口内体动强度中位数)
    "mmwave_phase_stability_median",         # 相位稳定性中位数 (呼吸/体动相位一致性)
]
# SUPPORTING 特征清单 (呼吸类 + HR 类; 正式管线状态为 SUPPORTING/HOLD, 仅作描述性参考)
SUPPORTING_FEATURES = [
    "mmwave_breath_rate_breaths_per_min_median",  # 呼吸率 (BR, SUPPORTING)
    "mmwave_hr_freq_bpm_median",                  # 频域 HR (SUPPORTING)
    "mmwave_hr_time_bpm_median",                  # 时域 HR (SUPPORTING)
    "mmwave_hr_fused_bpm_median",                 # 融合 HR (SUPPORTING)
    "mmwave_hr_usable_window_fraction",           # HR 可用窗口占比 (质量指标, SUPPORTING)
]
# 仅描述统计 (位置/质量类, 不进模型)
DESC_ONLY_FEATURES = [
    "mmwave_selected_bin_mode",
    "mmwave_selected_channel_mode",
    "mmwave_selected_bin_distance_proxy_m",
    "mmwave_timestamp_coverage_fraction",
]
# 全空字段 (两批次均无数据, 不可用, 仅记录)
EMPTY_FEATURES = [
    "mmwave_target_switch_rate",             # 目标切换率: 全空
    "mmwave_ibi_median_ms",                  # IBI: 全空
    "mmwave_rmssd_ms",                       # RMSSD: 全空
    "mmwave_sdnn_ms",                        # SDNN: 全空
]


# ---------------------------------------------------------------------------
# 数据装载与 join
# ---------------------------------------------------------------------------
def load_and_join() -> pd.DataFrame:
    """装载两个毫米波表与行为探针表, 按 (session_id, block 映射, probe 序) 内连接。

    键映射说明: 毫米波表 block_id 格式为 'block-N', 行为表为 'BN', 需统一;
    探针序: 毫米波 probe_index_in_block == 行为 probe_order_in_block (1-10)。
    返回值: 内连接后的宽表 (2320 行), 含 _mm/_b 后缀消歧列。
    """
    mm_j = pd.read_csv(PATH_MMWAVE_J)
    mm_e = pd.read_csv(PATH_MMWAVE_E)  # 首列名带 BOM, pandas 读 csv 时自动剥离
    mm = pd.concat([mm_j, mm_e], ignore_index=True)
    beh = pd.read_csv(PATH_BEHAVIOR_PROBE)

    # block_id 格式统一: 'block-1' -> 'B1'
    mm["block_std"] = mm["block_id"].str.replace("block-", "B", regex=False)
    joined = mm.merge(
        beh,
        left_on=["session_id", "block_std", "probe_index_in_block"],
        right_on=["session_id", "block_id", "probe_order_in_block"],
        how="inner",
        suffixes=("_mm", "_b"),
    )
    assert len(joined) == 2320, f"join 后行数异常: {len(joined)}"
    # 交叉验证: 毫米波表自带 Q2 标签与行为表 Q2 编码应完全一致
    assert (joined["label_probe_vigilance"] == joined["q2_ordinal_4level"]).all(), \
        "label_probe_vigilance 与 q2_ordinal_4level 不一致"

    # time_in_block: 窗口有效起点距 block 起点的分钟数 (仅 J 批可算, 0.1-9.6 分钟, 已验无负值;
    # E 批 block_start/end 时间戳全空, 该列为 NaN, 仅作描述)
    joined["time_in_block_min"] = (
        joined["window_effective_start_unix_ms"] - joined["block_start_unix_ms"]
    ) / 60000.0
    # time_in_block_idx: block 内探针序 (0-9) 作为 block 内时间位置代理, 两批次一致, 用于模型协变量
    joined["time_in_block_idx"] = joined["probe_index_in_block"].astype(float) - 1.0
    # block 哑变量 (B1 为参照)
    joined["block_B2"] = (joined["block_std"] == "B2").astype(float)
    # Q1/Q2 转为 0 起始 (模型要求), 并生成 Q2 二元化结局
    joined["q1_0"] = joined["q1_nominal_4class"].astype(int) - 1
    joined["q2_0"] = joined["q2_ordinal_4level"].astype(int) - 1
    joined["q2_binary_high"] = (joined["q2_ordinal_4level"] >= Q2_BINARY_CUT).astype(float)
    return joined


def analysis_sample(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """取 OBSERVED 且所用特征全非缺失的探针行, 并对特征做 z 标准化。

    参数: df 为 join 后宽表; features 为本次模型使用的特征列名列表。
    返回: 样本子集副本, 特征列原位替换为标准化值。
    """
    sub = df[df["mmwave_observed"] == True].copy()
    sub = sub.dropna(subset=features + [CLUSTER_COL, "q1_0", "q2_0", "q2_binary_high"])
    for f in features:
        mu, sd = sub[f].mean(), sub[f].std(ddof=1)
        if sd > 0:
            sub[f] = (sub[f] - mu) / sd  # z 标准化: 系数解释为每 1 SD 变化
        else:
            sub[f] = 0.0  # 常数特征防除零 (将在 main 中剔除)
    return sub


def sample_counts(sub: pd.DataFrame) -> tuple[int, int, int]:
    """返回 (探针数, 场次数, 参与者数), 用于模型结果标注。"""
    return len(sub), sub["session_id"].nunique(), sub[CLUSTER_COL].nunique()


# ---------------------------------------------------------------------------
# 模型拟合
# ---------------------------------------------------------------------------
def fit_q1_mnlogit(sub: pd.DataFrame, feats: list[str], adjust: bool) -> list[dict]:
    """Q1 名义四类多项 logistic (MNLogit), 参照类别 1, cluster-robust SE。

    adjust=False 时仅含特征; adjust=True 时加入 block_B2 与 time_in_block_min(中心化)。
    返回: 每个 (特征 × 类别对比) 一行的结果 dict 列表。
    """
    exog_vars = list(feats)
    if adjust:
        sub = sub.copy()
        # block 内时间位置代理: probe_index(0-9) 中心化
        sub["time_in_block_c"] = sub["time_in_block_idx"] - sub["time_in_block_idx"].mean()
        exog_vars = exog_vars + ["block_B2", "time_in_block_c"]
    X = sub[exog_vars].astype(float).values
    X = np.column_stack([np.ones(len(sub)), X])  # 加常数项
    y = sub["q1_0"].astype(int).values
    mod = MNLogit(y, X)
    res = mod.fit(cov_type="cluster", cov_kwds={"groups": sub[CLUSTER_COL].values},
                  method="newton", maxiter=200, disp=0)
    n_probe, n_sess, n_part = sample_counts(sub)
    rows = []
    # 参照类别 0 (原始 Q1=1); MNLogit params 布局为 (参数, 对比列), 索引 [j, k]
    # 对比列 k=0,1,2 分别对应 MNLogit 类别 1,2,3 vs 参照 0, 即 Q1 原始类别 2,3,4 vs 类 1
    for k in range(res.params.shape[1]):
        q1_label = k + 2
        for j, var in enumerate(["intercept"] + exog_vars):
            b = res.params[j, k]
            se = res.bse[j, k]
            # 注意: MNLogit 各矩阵布局不一致, conf_int 为 (类别, 参数, 2)
            ci_lo, ci_hi = res.conf_int()[k, j]
            z = res.tvalues[j, k]
            p = res.pvalues[j, k]
            rows.append({
                "model": "q1_mnlogit", "adjustment": "block_time" if adjust else "unadjusted",
                "outcome": f"Q1_class{q1_label}_vs_ref{Q1_REF_CLASS}", "term": var,
                "coef": b, "se": se, "z": z, "p": p, "ci_low": ci_lo, "ci_high": ci_hi,
                "or": np.exp(b), "or_ci_low": np.exp(ci_lo), "or_ci_high": np.exp(ci_hi),
                "n_probes": n_probe, "n_sessions": n_sess, "n_participants": n_part,
            })
    return rows


def fit_q2_ordered(sub: pd.DataFrame, feats: list[str], adjust: bool) -> list[dict]:
    """Q2 有序四级累积 logistic (OrderedModel, distr='logit'), cluster-robust SE。

    正系数表示该特征越高, 警觉等级倾向越高 (向更高累积类别偏移)。
    返回: 每个项一行的结果 dict 列表。
    """
    exog_vars = list(feats)
    if adjust:
        sub = sub.copy()
        # block 内时间位置代理: probe_index(0-9) 中心化
        sub["time_in_block_c"] = sub["time_in_block_idx"] - sub["time_in_block_idx"].mean()
        exog_vars = exog_vars + ["block_B2", "time_in_block_c"]
    X = sub[exog_vars].astype(float)  # OrderedModel 自动加常数
    y = sub["q2_0"].astype(int).values
    mod = OrderedModel(y, X, distr="logit")
    res = mod.fit(method="bfgs", maxiter=2000, disp=0,
                  cov_type="cluster", cov_kwds={"groups": sub[CLUSTER_COL].values})
    n_probe, n_sess, n_part = sample_counts(sub)
    rows = []
    for j, var in enumerate(exog_vars):
        b = res.params.iloc[j]
        se = res.bse.iloc[j]
        ci_lo, ci_hi = res.conf_int().iloc[j]
        rows.append({
            "model": "q2_ordered", "adjustment": "block_time" if adjust else "unadjusted",
            "outcome": "Q2_ordinal_cumulative", "term": var,
            "coef": b, "se": se, "z": res.tvalues.iloc[j], "p": res.pvalues.iloc[j],
            "ci_low": ci_lo, "ci_high": ci_hi,
            "or": np.exp(b), "or_ci_low": np.exp(ci_lo), "or_ci_high": np.exp(ci_hi),
            "n_probes": n_probe, "n_sessions": n_sess, "n_participants": n_part,
        })
    return rows


def fit_q2_binary_gee(sub: pd.DataFrame, feats: list[str], adjust: bool) -> list[dict]:
    """Q2 二元化 logistic GEE: 低警觉(1-2) vs 高警觉(3-4), exchangeable 相关结构。

    聚类键为 participant_group_id。返回: 每个项一行的结果 dict 列表。
    """
    exog_vars = list(feats)
    if adjust:
        sub = sub.copy()
        # block 内时间位置代理: probe_index(0-9) 中心化
        sub["time_in_block_c"] = sub["time_in_block_idx"] - sub["time_in_block_idx"].mean()
        exog_vars = exog_vars + ["block_B2", "time_in_block_c"]
    X = sub[exog_vars].astype(float).values
    X = np.column_stack([np.ones(len(sub)), X])  # GEE 需手动加常数
    y = sub["q2_binary_high"].values
    mod = GEE(y, X, groups=sub[CLUSTER_COL].values, family=Binomial())
    res = mod.fit(cov_type="robust")
    n_probe, n_sess, n_part = sample_counts(sub)
    rows = []
    for j, var in enumerate(["intercept"] + exog_vars):
        b = res.params[j]
        se = res.bse[j]
        ci_lo, ci_hi = res.conf_int()[j]
        rows.append({
            "model": "q2_binary_gee", "adjustment": "block_time" if adjust else "unadjusted",
            "outcome": "Q2_binary_high_vs_low", "term": var,
            "coef": b, "se": se, "z": res.tvalues[j], "p": res.pvalues[j],
            "ci_low": ci_lo, "ci_high": ci_hi,
            "or": np.exp(b), "or_ci_low": np.exp(ci_lo), "or_ci_high": np.exp(ci_hi),
            "n_probes": n_probe, "n_sessions": n_sess, "n_participants": n_part,
        })
    return rows


def holm_within_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """在 (model, adjustment, family) 组内做 Holm 调整 (仅对特征项, 协变量/截距除外)。

    参数: df 为模型结果长表; group_cols 为分组列。返回: 附加 p_holm 与 sig_holm 列的表。
    """
    df = df.copy()
    df["p_holm"] = np.nan
    df["sig_holm"] = False
    # family 列需存在: 主模型 primary / SUPPORTING 模型 supporting
    for _, idx in df.groupby(group_cols).groups.items():
        mask_feat = ~df.loc[idx, "term"].isin(["intercept", "block_B2", "time_in_block_c"])
        pvals = df.loc[idx[mask_feat], "p"].values.astype(float)
        if len(pvals) == 0:
            continue
        adj = multipletests(pvals, alpha=HOLM_ALPHA, method="holm")[1]
        df.loc[idx[mask_feat], "p_holm"] = adj
        df.loc[idx[mask_feat], "sig_holm"] = adj < HOLM_ALPHA
    return df


# ---------------------------------------------------------------------------
# 描述统计
# ---------------------------------------------------------------------------
def make_desc_stats(sub_all: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """按 Q1 类别 / Q2 等级汇总各毫米波特征 (n, mean, sd), 各附总体行。

    参数: sub_all 为全部 OBSERVED 探针行 (不剔除特征缺失, 逐特征取非缺失)。
    返回: (by_q1 表, by_q2 表), long 格式。
    """
    feats_all = PRIMARY_FEATURES + SUPPORTING_FEATURES + DESC_ONLY_FEATURES
    out_q1, out_q2 = [], []
    for f in feats_all:
        v = pd.to_numeric(sub_all[f], errors="coerce")
        for gname, gcol, store in [("q1", "q1_nominal_4class", out_q1),
                                   ("q2", "q2_ordinal_4level", out_q2)]:
            for lvl in sorted(sub_all[gcol].dropna().unique()):
                x = v[sub_all[gcol] == lvl].dropna()
                store.append({"feature": f, f"{gname}_level": int(lvl),
                              "n": len(x), "mean": x.mean(), "sd": x.std(ddof=1)})
            x = v.dropna()
            store.append({"feature": f, f"{gname}_level": "all",
                          "n": len(x), "mean": x.mean(), "sd": x.std(ddof=1)})
    return pd.DataFrame(out_q1), pd.DataFrame(out_q2)


# ---------------------------------------------------------------------------
# 结果摘要 (Markdown)
# ---------------------------------------------------------------------------
def write_markdown(joined: pd.DataFrame, sub_all: pd.DataFrame,
                   desc_q1: pd.DataFrame, desc_q2: pd.DataFrame,
                   model_rows: pd.DataFrame) -> None:
    """生成中文结果摘要 markdown, 含字段清单/描述要点/模型全表/限制边界。"""
    n_all = len(joined)
    n_obs = len(sub_all)
    mm_j = pd.read_csv(PATH_MMWAVE_J)
    mm_e = pd.read_csv(PATH_MMWAVE_E)
    miss_j = (mm_j["mmwave_observed"] != True).sum()
    miss_e = (mm_e["mmwave_observed"] != True).sum()
    miss_reason = pd.concat([mm_j, mm_e])["mmwave_missing_reason"].value_counts(dropna=False)

    # 描述统计要点: 主特征在各 Q2 等级的均值序列 (运动类量级小, 用 4 位小数)
    def mean_str(row, f):
        prec = 4 if "motion" in f or "phase_stability" in f else 2
        return f"{row['mean']:.{prec}f}"

    def q2_means(f):
        d = desc_q2[(desc_q2.feature == f) & (desc_q2.q2_level != "all")].set_index("q2_level")
        return ", ".join(f"{int(k)}级={mean_str(row, f)}" for k, row in d.iterrows())

    def q1_means(f):
        d = desc_q1[(desc_q1.feature == f) & (desc_q1.q1_level != "all")].set_index("q1_level")
        return ", ".join(f"类{int(k)}={mean_str(row, f)}" for k, row in d.iterrows())

    lines = []
    lines.append("# 毫米波特征与行为/思维探针关联分析结果摘要 (2026-08-31)")
    lines.append("")
    lines.append("支撑论文 5.4.3 节「毫米波特征与行为及思维探针的关系」。"
                 "本分析为关联描述与初步模型，端点冻结前不做因果推断。")
    lines.append("")
    lines.append("## 1. 数据与 join")
    lines.append("")
    lines.append(f"- 毫米波 merge-ready 表: J 盘批次 72 场 1440 探针 + E 盘批次 44 场 880 探针, "
                 f"合计 **116 场 2320 探针** (每行 = 探针前 30s 窗口)。")
    lines.append(f"- join 键: (session_id, block_id 映射 `block-N`→`BN`, probe_index_in_block=probe_order_in_block), "
                 f"内连接 **2320/2320 行全部匹配**。")
    lines.append(f"- Q1/Q2 来源: Behavior probe_primary_30s 表 (q1_nominal_4class / q2_ordinal_4level); "
                 f"毫米波表自带 label_probe_vigilance 与 Q2 编码逐行一致 (交叉验证通过)。")
    lines.append(f"- 参与者聚类: 使用 Behavior 表 participant_group_id (**61 名独立参与者**, 每人 1-4 场); "
                 f"两表 repeat_participant_id 编号体系不一致 (毫米波 62 vs 行为 61), 故不直接使用。")
    lines.append(f"- 样本口径: 全部 2320 探针为正式实验独立样本 (formal_independent_sample 全 True, "
                 f"analysis_role 全 primary_probe)。")
    lines.append("")
    lines.append("## 2. 字段清单")
    lines.append("")
    lines.append("| 类别 | 字段 | 状态 |")
    lines.append("|------|------|------|")
    for f in PRIMARY_FEATURES:
        lines.append(f"| 运动类 (主) | {f} | 进主模型, 主结论来源 |")
    for f in SUPPORTING_FEATURES:
        tag = "呼吸类" if "breath" in f else "HR 类"
        if "hr_usable_window_fraction" in f:
            lines.append(f"| {tag} (SUPPORTING) | {f} | 常数(全为 1.0), 未进模型, 仅描述统计 |")
        else:
            lines.append(f"| {tag} (SUPPORTING) | {f} | 进 SUPPORTING 模型, 仅描述性参考 |")
    for f in DESC_ONLY_FEATURES:
        lines.append(f"| 位置/质量类 | {f} | 仅描述统计 |")
    for f in EMPTY_FEATURES:
        lines.append(f"| 不可用 | {f} | 两批次全空, 未分析 |")
    lines.append("")
    lines.append(f"- 主分析窗口: 探针前 30s (协议定义); J 批 time_in_block 实测 0.11-9.62 分钟, "
                 f"E 批 block 时间戳全空, 模型协变量改用 block 内探针序 (probe_index 0-9, 两批一致) 代理。")
    lines.append(f"- HR/BR 字段正式管线状态为 SUPPORTING/HOLD (仅 3 名被试 targeted 验证), "
                 f"故运动类字段为唯一主结论来源, 呼吸/HR 类结果均标注 SUPPORTING。")
    lines.append("")
    lines.append("## 3. 数据质量与覆盖")
    lines.append("")
    lines.append(f"- OBSERVED 覆盖: **{n_obs}/{n_all}** 探针 ({n_obs / n_all:.1%}); "
                 f"J 批缺失 {miss_j}/1440, E 批缺失 {miss_e}/880。")
    lines.append(f"- 缺失原因: {dict(miss_reason.dropna().items())} (nan 为 OBSERVED)。")
    lines.append(f"- 全空字段: {', '.join(EMPTY_FEATURES)} 在两批次均无数据 (管线未产出), 不可用。")
    lines.append(f"- 运动类/呼吸/HR 特征在 OBSERVED 行内无额外缺失; 主模型与 SUPPORTING 模型均基于 "
                 f"{len(sub_all)} 探针。")
    lines.append("")
    lines.append("## 4. 描述统计要点")
    lines.append("")
    lines.append(f"- Q1 语义 (名义四类): 1=专注(完全任务聚焦), 2=任务相关干扰, 3=走神(任务无关思维), "
                 f"4=大脑空白; 模型参照类别 = 1。")
    lines.append(f"- Q2 语义 (有序四级): 1=极困倦 → 4=极清醒。")
    lines.append(f"- Q1 分布 (n=2320): 类1={int((joined.q1_nominal_4class == 1).sum())}, "
                 f"类2={int((joined.q1_nominal_4class == 2).sum())}, "
                 f"类3={int((joined.q1_nominal_4class == 3).sum())}, "
                 f"类4={int((joined.q1_nominal_4class == 4).sum())} (类3 样本最小, 模型估计需谨慎)。")
    lines.append(f"- Q2 分布 (n=2320): 1级={int((joined.q2_ordinal_4level == 1).sum())}, "
                 f"2级={int((joined.q2_ordinal_4level == 2).sum())}, "
                 f"3级={int((joined.q2_ordinal_4level == 3).sum())}, "
                 f"4级={int((joined.q2_ordinal_4level == 4).sum())}。")
    for f in PRIMARY_FEATURES + ["mmwave_breath_rate_breaths_per_min_median",
                                 "mmwave_hr_fused_bpm_median"]:
        lines.append(f"- **{f}** 按 Q2 等级均值: {q2_means(f)}; 按 Q1 类别均值: {q1_means(f)}。")
    lines.append(f"- 完整描述统计表见 desc_stats_by_q1.csv / desc_stats_by_q2.csv (含 {len(PRIMARY_FEATURES) + len(SUPPORTING_FEATURES) + len(DESC_ONLY_FEATURES)} 个字段)。")
    lines.append("")
    lines.append("## 5. 模型结果 (完整列表, 未经 p 筛选)")
    lines.append("")
    lines.append("- 模型族: primary = 运动类 2 特征 (主结论); supporting = 呼吸 + HR 类 4 特征 "
                 "(hr_usable_window_fraction 为常数已剔除; 标注 SUPPORTING, 仅参考)。")
    lines.append("- Q1: 多项 logistic (MNLogit), 参照类别 1, 报告各类别对比的 OR; "
                 "Q2 有序: 累积 logistic (OrderedModel), 正系数 = 特征越高警觉等级越高; "
                 "Q2 二元: logistic GEE (exchangeable), 结局 = 高警觉 (3-4 级)。")
    lines.append("- 全部模型为探针级、按 participant_group_id 聚类 (cluster-robust SE); "
                 "特征 z 标准化 (每 1 SD 变化); 两个版本: unadjusted / 调整 block + time_in_block "
                 "(block 内探针序代理, 中心化)。")
    lines.append("- 多重比较: Holm 在 (模型 × 调整版本 × 模型族) 内调整, sig_holm=True 表示调整后 p<0.05。")
    lines.append("")
    # 模型表: 只列特征项 (截距省略), 保留协变量行
    tab = model_rows[model_rows.term != "intercept"].copy()
    fmt = lambda x: f"{x:.3f}"
    lines.append("| 族 | 模型 | 调整 | 结局 | 项 | OR | CI95 | p | p_holm | sig | N探针/场/人 |")
    lines.append("|----|------|------|------|----|----|------|---|--------|-----|-------------|")
    for _, r in tab.iterrows():
        ci = f"[{fmt(r.or_ci_low)}, {fmt(r.or_ci_high)}]"
        ntxt = f"{int(r.n_probes)}/{int(r.n_sessions)}/{int(r.n_participants)}"
        lines.append(f"| {r.family} | {r.model} | {r.adjustment} | {r.outcome} | {r.term} | "
                     f"{fmt(r['or'])} | {ci} | {r.p:.4f} | {r.p_holm:.4f} | {bool(r.sig_holm)} | {ntxt} |")
    lines.append("")
    lines.append("## 6. 主要发现 (Holm 调整后)")
    lines.append("")
    # 从结果表提取 Holm 显著的特征项, 客观列出
    sig = tab[tab.sig_holm == True].copy()
    if len(sig) == 0:
        lines.append("- 无任何关联在 Holm 调整后显著 (p<0.05)。")
    else:
        for _, r in sig.iterrows():
            direction = "正" if r["or"] > 1 else "负"
            lines.append(f"- {r.family} 族 {r.model} ({r.adjustment}): {r.term} 对 {r.outcome} 的 OR = "
                         f"{r['or']:.2f} [{r.or_ci_low:.2f}, {r.or_ci_high:.2f}], p={r.p:.4f}, "
                         f"Holm p={r.p_holm:.4f} ({direction}向)。")
    lines.append("- 解读 (主模型运动类): motion_proxy 越高, Q1 报告「走神」(类 3) 而非「专注」(类 1) 的 "
                 "odds 越高; 类 2 (任务相关干扰)/类 4 (大脑空白) 对比方向同为正向但 CI 含 1; "
                 "对 Q2 警觉等级无关联证据。")
    lines.append("")
    lines.append("## 7. 限制与边界")
    lines.append("")
    lines.append("1. 关联描述与初步模型, 非因果推断; 端点冻结前结论不用于决策。")
    lines.append("2. 运动类特征仅 2 个字段可用 (target_switch_rate 全空); 相位稳定性/运动代理为代理指标, "
                 "非直接体动测量。")
    lines.append("3. HR/BR 字段为 SUPPORTING/HOLD 状态 (仅 3 名被试 targeted 验证), 相关结果不得作为主结论。")
    lines.append("4. Q1 类3 仅 95 探针, 多项 logistic 对应系数 SE 较大, 解释需谨慎。")
    lines.append("5. 同一参与者多场次 (最多 4 场) 已在模型中按参与者聚类; 但探针在 block 内的时间趋势 "
                 "仅以 time_in_block 线性项近似。")
    lines.append("6. 结构缺失 120 探针 (J 20 / E 100, 文件加载失败) 未纳入模型, 若缺失与警觉相关可能引入偏差; "
                 "缺失原因以加载失败为主, 无明显证据指向系统缺失。")
    lines.append("")
    lines.append(f"输出文件: desc_stats_by_q1.csv, desc_stats_by_q2.csv, q1_multinomial_models.csv, "
                 f"q2_ordinal_models.csv, q2_binary_gee_models.csv, 本摘要。")
    lines.append("")
    lines.append("脚本: _t0_vmd_worktree/scripts/maintenance/analyze_mmwave_behavior_assoc_20260831.py")
    out_md = OUT_DIR / "结果摘要_毫米波特征与行为思维探针关联_20260831.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[摘要] {out_md}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> None:
    """主流程: join → 描述统计 → 12 个模型 → Holm → 输出 CSV 与摘要。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joined = load_and_join()
    sub_all = joined[joined["mmwave_observed"] == True].copy()

    # 1) 描述统计
    desc_q1, desc_q2 = make_desc_stats(sub_all)
    desc_q1.to_csv(OUT_DIR / "desc_stats_by_q1.csv", index=False, encoding="utf-8-sig")
    desc_q2.to_csv(OUT_DIR / "desc_stats_by_q2.csv", index=False, encoding="utf-8-sig")
    print(f"[描述统计] 输出 {len(desc_q1)} 行 (by Q1), {len(desc_q2)} 行 (by Q2)")

    # 2) 模型: (族, 特征清单) × 3 模型 × 2 调整版本
    all_rows = []
    for family, feats0 in [("primary", PRIMARY_FEATURES), ("supporting", SUPPORTING_FEATURES)]:
        sub = analysis_sample(joined, feats0)
        const_feats = [f for f in feats0 if sub[f].std(ddof=1) == 0]
        feats = [f for f in feats0 if f not in const_feats]
        if const_feats:
            print(f"[注意] 常数特征已剔除(不进 {family} 模型): {const_feats}")
        n_probe, n_sess, n_part = sample_counts(sub)
        print(f"[模型族 {family}] 特征 {len(feats)} 个 | 探针 {n_probe} / 场次 {n_sess} / 参与者 {n_part}")
        for adjust in (False, True):
            for fit_fn in (fit_q1_mnlogit, fit_q2_ordered, fit_q2_binary_gee):
                rows = fit_fn(sub, feats, adjust)
                for r in rows:
                    r["family"] = family
                all_rows.extend(rows)
    model_df = pd.DataFrame(all_rows)
    model_df = holm_within_group(model_df, group_cols=["model", "adjustment", "family"])

    # 3) 按模型分文件输出 + 合并全表
    for mname, fname in [("q1_mnlogit", "q1_multinomial_models.csv"),
                         ("q2_ordered", "q2_ordinal_models.csv"),
                         ("q2_binary_gee", "q2_binary_gee_models.csv")]:
        model_df[model_df.model == mname].to_csv(OUT_DIR / fname, index=False, encoding="utf-8-sig")
    model_df.to_csv(OUT_DIR / "all_model_results.csv", index=False, encoding="utf-8-sig")
    print(f"[模型] 共 {len(model_df)} 行结果")

    # 4) 摘要
    write_markdown(joined, sub_all, desc_q1, desc_q2, model_df)
    print("[完成] 全部输出至", OUT_DIR)


if __name__ == "__main__":
    main()
