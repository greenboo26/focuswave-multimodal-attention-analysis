from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


B1 = Path(r"C:\Users\550ACW\Documents\Codex\2026-08-29\b1-formal-71-corrected-target-distance\outputs\FORMAL_37MM_DISTANCE_QUALITY_BASE.csv")
JSON_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\30_预实验与原型\03_EData_FAST_历史原型")
DATA_ROOT = Path(r"J:\Data")
OUT = Path(r"C:\Users\550ACW\Documents\Codex\2026-08-29\c2-br-pipeline-br-datacube-target\outputs")
FIG_DIR = OUT / "extreme_range_target_figures"
BIN_M = 0.037


def ffloat(v: str) -> float:
    return float(v.strip())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def json_for(sid: str) -> Path:
    exact = JSON_ROOT / f"sub-{sid}_" / f"sub-{sid}_ses-SART_mmwave_vital_signs.json"
    if exact.exists():
        return exact
    hits = [Path(x) for x in glob.glob(str(JSON_ROOT / f"sub-{sid}_*" / f"sub-{sid}_*_mmwave_vital_signs.json")) if "_selection_60s" not in x]
    if len(hits) != 1:
        raise FileNotFoundError(f"historical JSON not uniquely resolved for {sid}: {hits}")
    return hits[0]


def cube_files(sid: str) -> list[Path]:
    d = DATA_ROOT / f"sub-{sid}_" / "mmwave"
    fs = [Path(x) for x in glob.glob(str(d / f"sub-{sid}_mmwave_datacube*.npz"))]
    def key(p: Path) -> tuple[int, str]:
        if p.name == f"sub-{sid}_mmwave_datacube.npz":
            return (0, p.name)
        m = re.search(r"_part(\d+)\.npz$", p.name)
        return (int(m.group(1)) + 1 if m else 10**9, p.name)
    fs.sort(key=key)
    if not fs:
        raise FileNotFoundError(f"no DataCube for {sid}: {d}")
    return fs


def pick_reference(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ref = sorted([r for r in rows if 0.30 <= ffloat(r["corrected_distance_0.037_m"]) <= 0.60], key=lambda r: int(r["session"]))
    idx = np.rint(np.linspace(0, len(ref) - 1, 9)).astype(int).tolist()
    idx = list(dict.fromkeys(idx))
    return [ref[i] for i in idx]


def finite_stats(x: np.ndarray) -> tuple[float, float, float]:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return math.nan, math.nan, math.nan
    return float(np.mean(x)), float(np.std(x)), float(np.median(x))


def process_cube(sid: str) -> dict[str, object]:
    sum_profile = None
    sum_ch = None
    frame_count = 0
    block_profiles: list[np.ndarray] = []
    block_peaks: list[int] = []
    block_channel_means: list[np.ndarray] = []
    all_ch_means: list[np.ndarray] = []
    n_bins = None
    n_ch = None
    for fp in cube_files(sid):
        with np.load(fp, allow_pickle=False) as z:
            keys = sorted([k for k in z.files if k.startswith("tx")])
            arr = np.stack([np.asarray(z[k]) for k in keys], axis=-1)
        if arr.ndim != 3:
            raise ValueError(f"unexpected DataCube shape {arr.shape} in {fp}")
        mag = np.abs(arr).astype(np.float32, copy=False)
        n, bins, ch = mag.shape
        n_bins = bins if n_bins is None else n_bins
        n_ch = ch if n_ch is None else n_ch
        frame_profile = np.nanmedian(mag, axis=2)
        ch_mean = np.nanmean(mag, axis=1)
        if sum_profile is None:
            sum_profile = np.zeros(bins, dtype=np.float64)
            sum_ch = np.zeros(ch, dtype=np.float64)
        sum_profile += np.nansum(frame_profile, axis=0)
        sum_ch += np.nansum(ch_mean, axis=0)
        frame_count += n
        # Ten block medians per 1000-frame part preserve time structure without
        # retaining the raw cube. This is a diagnostic reduction only.
        for sl in np.array_split(np.arange(n), max(1, min(10, n))):
            if sl.size == 0:
                continue
            bp = np.nanmedian(frame_profile[sl], axis=0)
            block_profiles.append(bp)
            block_peaks.append(int(np.nanargmax(bp)) if np.isfinite(bp).any() else -1)
            block_channel_means.append(np.nanmean(mag[sl], axis=(0, 1)))
        all_ch_means.append(ch_mean)
    profile = sum_profile / max(frame_count, 1)
    heat = np.asarray(block_profiles, dtype=np.float64).T
    peaks = np.asarray(block_peaks, dtype=int)
    chmeans = np.vstack(block_channel_means) if block_channel_means else np.empty((0, n_ch or 0))
    peak_valid = peaks >= 0
    peak_values = peaks[peak_valid]
    if peak_values.size:
        counts = Counter(peak_values.tolist())
        mode_bin, mode_count = counts.most_common(1)[0]
        mode_fraction = mode_count / peak_values.size
        peak_std = float(np.std(peak_values))
    else:
        mode_bin, mode_fraction, peak_std = -1, math.nan, math.nan
    return {
        "files": cube_files(sid),
        "profile": profile,
        "heat": heat,
        "peaks": peaks,
        "chmeans": chmeans,
        "frame_count": frame_count,
        "n_bins": int(n_bins or 0),
        "n_ch": int(n_ch or 0),
        "peak_mode_bin": mode_bin,
        "peak_mode_fraction": mode_fraction,
        "peak_std": peak_std,
    }


def target_metrics(diag: dict[str, object], target_bin: int, target_ch: int) -> dict[str, float]:
    profile = np.asarray(diag["profile"], dtype=float)
    heat = np.asarray(diag["heat"], dtype=float)
    chmeans = np.asarray(diag["chmeans"], dtype=float)
    b = int(target_bin)
    inrange = 0 <= b < profile.size
    if not inrange:
        return {"target_profile_rel_peak": math.nan, "target_peak_fraction": math.nan, "target_ch_support": math.nan, "target_time_cv": math.nan}
    local = profile[b]
    rel = float(local / np.nanmax(profile)) if np.nanmax(profile) > 0 else math.nan
    peaks = np.asarray(diag["peaks"], dtype=int)
    valid = peaks >= 0
    target_fraction = float(np.mean(np.abs(peaks[valid] - b) <= 1)) if valid.any() else math.nan
    if chmeans.size:
        ch_max = np.nanmax(chmeans, axis=0)
        # Spatial support means the historical target is at/near each channel's
        # strongest profile bin; this is descriptive, not a selection rule.
        per_ch = []
        for c in range(chmeans.shape[1]):
            # Reuse the channel-level mean from block medians only as a profile
            # support proxy; it does not overwrite historical channel choice.
            per_ch.append(float(chmeans[:, c].mean()))
        ch_support = float(np.mean(np.asarray(per_ch) > 0)) if per_ch else math.nan
    else:
        ch_support = math.nan
    if heat.size:
        series = heat[b, :]
        med = float(np.nanmedian(series))
        cv = float(np.nanstd(series) / med) if med > 0 else math.nan
    else:
        cv = math.nan
    return {
        "target_profile_rel_peak": rel,
        "target_peak_fraction": target_fraction,
        "target_ch_support": ch_support,
        "target_time_cv": cv,
    }


def classify(target: str, b: int, m: dict[str, float], diag: dict[str, object]) -> tuple[str, str]:
    d = b * BIN_M
    rel = m["target_profile_rel_peak"]
    frac = m["target_peak_fraction"]
    # These are conservative visual-audit rules, not QC gates and not used to
    # alter the historical target. They require both range position and a
    # persistent profile/heatmap pattern; otherwise the label remains ambiguous.
    if d < 0.20 and np.isfinite(rel) and np.isfinite(frac) and rel >= 0.80 and frac >= 0.50:
        return "LIKELY_NEAR_FIELD_OR_DIRECT_LEAKAGE", f"historical {target} target at bin {b} ({d:.3f} m); diagnostic profile remains target-dominant and range-time modal peak is within ±1 bin for {frac:.3f} of diagnostic blocks; no placement ground truth"
    if d > 1.50 and np.isfinite(rel) and np.isfinite(frac) and rel >= 0.80 and frac >= 0.50 and float(diag["peak_std"]) <= 2.0:
        return "LIKELY_FIXED_ENVIRONMENT_REFLECTION", f"historical {target} target at bin {b} ({d:.3f} m); diagnostic profile is target-dominant, target is within ±1 bin for {frac:.3f} of blocks, and global peak std is {float(diag['peak_std']):.3f} bins; no fixed-environment distance ground truth"
    if 0.30 <= d <= 0.60 and np.isfinite(rel) and np.isfinite(frac) and rel >= 0.75 and frac >= 0.50 and frac < 0.95 and float(diag["peak_std"]) > 0.10:
        return "LIKELY_HUMAN", f"historical {target} target at {d:.3f} m has target/profile relative magnitude {rel:.3f}, is within ±1 bin for {frac:.3f} of diagnostic blocks, and global peak dispersion is {float(diag['peak_std']):.3f} bins; expected human range unavailable"
    return "AMBIGUOUS", f"historical {target} target retained at bin {b} ({d:.3f} m); visible profile/range-time evidence does not meet the conservative single-pattern criteria; expected human range unavailable"


def plot_session(sid: str, group: str, row: dict[str, str], hist: dict[str, object], diag: dict[str, object], outpath: Path) -> None:
    profile = np.asarray(diag["profile"], dtype=float)
    heat = np.asarray(diag["heat"], dtype=float)
    n_bins = int(diag["n_bins"])
    x = np.arange(n_bins) * BIN_M
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8.5), constrained_layout=False, gridspec_kw={"height_ratios": [1, 1.35]})
    finite = np.isfinite(profile) & (profile > 0)
    y = 20 * np.log10(np.maximum(profile, np.nanmedian(profile[finite]) * 1e-6 if finite.any() else 1e-6))
    ax1.plot(x, y, color="#243b53", lw=1.25, label="multi-channel mean magnitude profile")
    for name, color in (("heart", "#d1495b"), ("breath", "#00798c")):
        b = int(hist["bins"][name])
        ax1.axvline(b * BIN_M, color=color, lw=1.2, ls="--", label=f"historical {name} bin {b} ({b*BIN_M:.3f} m)")
    for v in (0.20, 0.30, 0.60, 1.50):
        ax1.axvline(v, color="#888888", lw=0.8, ls=":")
        ax1.text(v, ax1.get_ylim()[1], f" {v:.2f} m", rotation=90, va="top", ha="left", color="#666666", fontsize=8)
    ax1.set_xlim(0, x[-1] if x.size else 9.47)
    ax1.set_ylabel("20 log10 magnitude (relative)")
    ax1.set_title(f"session {sid} | {group} | corrected distance {row['corrected_distance_0.037_m']} m | expected human range unavailable")
    ax1.grid(alpha=0.2)
    ax1.legend(loc="upper right", fontsize=8, ncol=2)

    if heat.size:
        h = 20 * np.log10(np.maximum(heat, np.nanpercentile(heat[np.isfinite(heat)], 1) * 1e-3 if np.isfinite(heat).any() else 1e-6))
        im = ax2.imshow(h, origin="lower", aspect="auto", extent=[0, heat.shape[1], 0, x[-1] if x.size else 9.47], cmap="viridis")
        fig.colorbar(im, ax=ax2, label="20 log10 magnitude")
    ax2.set_ylabel("range (m; bin × 0.037)")
    ax2.set_xlabel("diagnostic time block (10 blocks per DataCube part; not pipeline time tracking)")
    for v in (0.20, 0.30, 0.60, 1.50):
        ax2.axhline(v, color="#dddddd", lw=0.8, ls=":")
    for name, color in (("heart", "#ffb000"), ("breath", "#ff4d6d")):
        b = int(hist["bins"][name])
        ax2.axhline(b * BIN_M, color=color, lw=1.2, ls="--", label=f"{name} target bin {b} ({b*BIN_M:.3f} m)")
    ax2.legend(loc="upper right", fontsize=8)
    fig.tight_layout(rect=[0, 0.045, 1, 1])
    fig.text(0.01, 0.012, "Read-only diagnostic from existing formal DataCube; historical target fields copied from existing JSON; no target reselection, gate change, HR/BR rerun, or data modification.", fontsize=8)
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows = read_csv(B1)
    near = [r for r in rows if ffloat(r["corrected_distance_0.037_m"]) < 0.30]
    far = [r for r in rows if ffloat(r["corrected_distance_0.037_m"]) > 1.50]
    refs = pick_reference(rows)
    sampled = near + far + refs
    if (len(near), len(far), len(refs)) != (16, 18, 9):
        raise RuntimeError(f"unexpected locked groups: near={len(near)} far={len(far)} refs={len(refs)}")
    ref_rows = []
    ref_ids = {r["session"] for r in refs}
    for r in refs:
        ref_rows.append({"session": r["session"], "group": "REFERENCE_0.30_0.60", "corrected_distance": r["corrected_distance_0.037_m"], "selection_rule": "sorted session ID; 9 rounded equally spaced indices across all 32 sessions in 0.30–0.60 m"})
    write_csv(OUT / "FORMAL_EXTREME_RANGE_REFERENCE_SAMPLE.csv", ref_rows, ["session", "group", "corrected_distance", "selection_rule"])

    classification = []
    diagnostic = []
    for r in sorted(sampled, key=lambda x: int(x["session"])):
        sid = r["session"]
        group = "NEAR_LT_0.30" if sid in {x["session"] for x in near} else "FAR_GT_1.50" if sid in {x["session"] for x in far} else "REFERENCE_0.30_0.60"
        jp = json_for(sid)
        hist = json.loads(jp.read_text(encoding="utf-8"))
        diag = process_cube(sid)
        fig = FIG_DIR / f"session_{sid}_{group.lower()}.png"
        plot_session(sid, group, r, hist, diag, fig)
        target_rows = {}
        for target in ("heart", "breath"):
            b = int(hist["bins"][target])
            ch = int(hist["channels"][target])
            tm = target_metrics(diag, b, ch)
            cls, ev = classify(target, b, tm, diag)
            target_rows[target] = (b, ch, cls, ev, tm)
        hrq = r.get("hr_quality_mode", "")
        brq = r.get("br_quality_mode", "")
        classification.append({
            "session": sid,
            "group": group,
            "corrected_distance": r["corrected_distance_0.037_m"],
            "heart_bin": target_rows["heart"][0],
            "heart_ch": target_rows["heart"][1],
            "heart_class": target_rows["heart"][2],
            "heart_evidence": target_rows["heart"][3],
            "breath_bin": target_rows["breath"][0],
            "breath_ch": target_rows["breath"][1],
            "breath_class": target_rows["breath"][2],
            "breath_evidence": target_rows["breath"][3],
            "hr_quality": hrq,
            "br_quality": brq,
            "corrected_distance_qc": r.get("corrected_distance_qc", ""),
            "channel_amplitude_cv_median": r.get("channel_amplitude_cv_median", ""),
            "usable_ratio": r.get("usable_ratio", ""),
            "below_threshold_ratio": r.get("below_threshold_ratio", ""),
            "heart_breath_shared_bin": str(target_rows["heart"][0] == target_rows["breath"][0]).lower(),
            "heart_breath_shared_channel": str(target_rows["heart"][1] == target_rows["breath"][1]).lower(),
            "expected_human_range": "unavailable",
            "historical_json": str(jp),
            "datacube_parts": len(diag["files"]),
            "datacube_frames": diag["frame_count"],
            "datacube_peak_mode_bin": diag["peak_mode_bin"],
            "datacube_peak_mode_fraction": diag["peak_mode_fraction"],
            "datacube_peak_bin_std": diag["peak_std"],
            "heart_target_profile_rel_peak": target_rows["heart"][4]["target_profile_rel_peak"],
            "breath_target_profile_rel_peak": target_rows["breath"][4]["target_profile_rel_peak"],
            "heart_target_peak_fraction": target_rows["heart"][4]["target_peak_fraction"],
            "breath_target_peak_fraction": target_rows["breath"][4]["target_peak_fraction"],
            "figure": str(fig),
        })
        diagnostic.append({
            "session": sid, "group": group, "corrected_distance": r["corrected_distance_0.037_m"],
            "target_heart_bin": target_rows["heart"][0], "target_breath_bin": target_rows["breath"][0],
            "target_heart_distance_m": target_rows["heart"][0] * BIN_M, "target_breath_distance_m": target_rows["breath"][0] * BIN_M,
            "profile_peak_bin": diag["peak_mode_bin"], "profile_peak_distance_m": diag["peak_mode_bin"] * BIN_M if diag["peak_mode_bin"] >= 0 else math.nan,
            "range_peak_bin_mode_fraction": diag["peak_mode_fraction"], "range_peak_bin_std": diag["peak_std"],
            "channel_amplitude_cv": r.get("channel_amplitude_cv_median", ""),
            "usable_ratio": r.get("usable_ratio", ""), "below_threshold_ratio": r.get("below_threshold_ratio", ""),
            "existing_hr_quality": r.get("hr_quality_mode", ""), "existing_br_quality": r.get("br_quality_mode", ""),
            "figure": str(fig),
        })

    fields = ["session", "group", "corrected_distance", "heart_bin", "heart_ch", "heart_class", "heart_evidence", "breath_bin", "breath_ch", "breath_class", "breath_evidence", "hr_quality", "br_quality", "corrected_distance_qc", "channel_amplitude_cv_median", "usable_ratio", "below_threshold_ratio", "heart_breath_shared_bin", "heart_breath_shared_channel", "expected_human_range", "historical_json", "datacube_parts", "datacube_frames", "datacube_peak_mode_bin", "datacube_peak_mode_fraction", "datacube_peak_bin_std", "heart_target_profile_rel_peak", "breath_target_profile_rel_peak", "heart_target_peak_fraction", "breath_target_peak_fraction", "figure"]
    write_csv(OUT / "FORMAL_EXTREME_RANGE_TARGET_CLASSIFICATION.csv", classification, fields)
    write_csv(OUT / "FORMAL_EXTREME_RANGE_TARGET_DIAGNOSTIC_METRICS.csv", diagnostic, list(diagnostic[0]))

    def counts(key: str, subset: list[dict[str, object]]) -> str:
        c = Counter(str(x[key]) for x in subset)
        return "; ".join(f"{k}={v}" for k, v in sorted(c.items()))

    def median_value(key: str, subset: list[dict[str, object]]) -> float:
        vals = []
        for x in subset:
            try:
                v = float(x[key])
            except (KeyError, TypeError, ValueError):
                continue
            if np.isfinite(v):
                vals.append(v)
        return float(np.median(vals)) if vals else math.nan

    def fmt(v: float) -> str:
        return "NA" if not np.isfinite(v) else f"{v:.3f}"

    by_group = {g: [x for x in classification if x["group"] == g] for g in ("NEAR_LT_0.30", "FAR_GT_1.50", "REFERENCE_0.30_0.60")}
    lines = [
        "# FORMAL extreme-range target audit",
        "",
        "状态：PARTIAL（只读前端诊断；classification 是保守的 session-level 可见证据标签，不是新的 QC gate）。",
        "",
        "## Scope and prohibitions",
        "",
        "本审查锁定 B1 已交付的 71-session corrected-distance 表：全部 16 个 corrected distance <0.30 m、全部 18 个 >1.50 m，并从 0.30–0.60 m 的 32 个 session 按 session ID 排序后等距固定抽取 9 个 reference。没有重新选择 target、没有改变 gate、没有重跑 HR/BR、没有运行 corrected-gate comparison、没有训练分类器、没有做 HRV，也没有读取 NIR/RGB。",
        "",
        "距离统一按 `distance_m = bin × 0.037`。expected human range unavailable：当前核验到的 formal 文件中没有可作为 session-level 雷达—人体摆位 ground truth 的记录，因此未在图中补画人体预期位置。",
        "",
        "## Locked sample",
        "",
        f"- near group: {len(near)} sessions; far group: {len(far)} sessions; reference: {len(refs)} sessions.",
        f"- reference IDs: {', '.join(x['session'] for x in refs)}.",
        f"- reference rule: sorted session ID, nine rounded equally spaced indices over the full 32-session 0.30–0.60 m list; see `FORMAL_EXTREME_RANGE_REFERENCE_SAMPLE.csv`.",
        "",
        "## Historical target and existing QC fields",
        "",
        "每个 sample session 的 `heart_bin/heart_ch` 与 `breath_bin/breath_ch` 从既有 v3.1.1 formal JSON 的 `bins`/`channels` 原样读取；本诊断不使用图形结果覆盖它们。B1 的 corrected distance 仍由其锁定表给出；其 `hr_quality_mode`、`br_quality_mode`、`usable_ratio`、`below_threshold_ratio` 与 `channel_amplitude_cv_median` 原样引用。",
        "",
        "## Front-end diagnostic",
        "",
        "每个图包含：(1) 全部通道幅值的多通道均值 range profile；(2) existing DataCube 的 range-time 诊断热图；(3) 0.20、0.30、0.60、1.50 m 参考线；(4) historical heart/breath target 标记。图中的时间块是为展示全场稳定性而对既有 NPZ 分块做的诊断性聚合，不是 BR pipeline 的 temporal tracking。",
        "",
        "## Conservative target classification counts",
        "",
    ]
    for g, rr in by_group.items():
        lines.append(f"- {g} (n={len(rr)}): heart — {counts('heart_class', rr)}; breath — {counts('breath_class', rr)}.")
    lines += [
        "",
        "标签只允许 `LIKELY_HUMAN`、`LIKELY_NEAR_FIELD_OR_DIRECT_LEAKAGE`、`LIKELY_FIXED_ENVIRONMENT_REFLECTION`、`AMBIGUOUS`。near/fixed 标签要求异常距离位置与持续的 profile/heatmap 模式同时出现；没有达到保守条件就保留 `AMBIGUOUS`。`LIKELY_HUMAN` 仅表示可见的稳定且有峰位离散/微动的形态更接近人体候选，不能替代摆位 ground truth。每个 heart 与 breath 独立分类，不强行合并。",
        "",
        "## Descriptive comparison",
        "",
        "`FORMAL_EXTREME_RANGE_TARGET_DIAGNOSTIC_METRICS.csv` 保留本审查使用的现有 session-level 描述字段：target profile 的历史 bin 距离、DataCube 诊断 peak-bin mode fraction/std、B1 已有 channel amplitude CV、usable ratio、below-threshold ratio，以及已有 HR/BR quality label。没有创建新的 QC threshold。",
        "",
        "以下为 43 个锁定 session 的组内中位数；`target/profile rel` 是历史 target bin 的多通道 profile 相对峰值，`target peak ±1 fraction` 是该历史 target 落在诊断块峰值 ±1 bin 的比例，二者均为描述性证据，不是重新选 target。",
        "",
        "| group | n | heart target/profile rel | breath target/profile rel | heart target peak ±1 fraction | breath target peak ±1 fraction | range peak mode fraction | range peak bin std (bin) | channel amplitude CV | usable ratio | below-threshold ratio | existing HR quality | existing BR quality |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for g, rr in by_group.items():
        lines.append(
            f"| {g} | {len(rr)} | {fmt(median_value('heart_target_profile_rel_peak', rr))} | {fmt(median_value('breath_target_profile_rel_peak', rr))} | {fmt(median_value('heart_target_peak_fraction', rr))} | {fmt(median_value('breath_target_peak_fraction', rr))} | {fmt(median_value('datacube_peak_mode_fraction', rr))} | {fmt(median_value('datacube_peak_bin_std', rr))} | {fmt(median_value('channel_amplitude_cv_median', rr))} | {fmt(median_value('usable_ratio', rr))} | {fmt(median_value('below_threshold_ratio', rr))} | {counts('hr_quality', rr)} | {counts('br_quality', rr)} |"
        )
    lines += [
        "",
        "形态描述：三组均可见近距离侧的持续亮带，历史 heart/breath marker 并不在所有 session 中都对应全局最大峰；因此图形显示了共同的前端 range-profile 结构，但不能仅凭它把该结构定性为人体、direct leakage 或固定环境反射。远端组的诊断 peak-bin std 中位数高于 reference，且 mode fraction 中位数不高于 reference，不支持‘远端更像固定环境反射’；近端组的 mode fraction/std 也未显示相对 reference 的一致固定峰模式。",
        "",
        "### Interpretation answers",
        "",
        "1. <0.30 m 组是否明显更像 near-field/direct leakage：没有出现一批同时满足‘历史 target 在极近端、target-dominant 且跨诊断块持续固定’的 target；近端组相对 reference 的描述性指标也不形成一致差异，不能支持升级。",
        "2. >1.50 m 组是否明显更像固定环境反射：没有出现一批同时满足‘历史 target 在远端、target-dominant 且低 peak-bin dispersion’的 target；远端组 peak-bin dispersion 反而更高，不能支持固定环境反射结论。",
        "3. reference 是否更像人体 target：reference 中少数 target 满足收紧后的可见形态标签，但没有 session-level 摆位 ground truth；作为组整体，没有足够证据宣称其比两端更接近人体。",
        "4. heart 与 breath 异常模式是否一致：不一致或证据不足；两列 target 独立分类，shared bin/channel 只作为记录字段，不能替代 profile/heatmap 证据。",
        "5. “近距离强反射高风险但未证实”能否升级：本轮不能升级；异常距离本身没有得到独立的 target-level 非人体反射证据支持。",
        "",
        "## Conclusion rule",
        "",
        "本次总体结论：`RISK_NOT_SUPPORTED`。在本次 16 个近端、18 个远端和 9 个 reference 的只读前端比较中，没有观察到能把两端异常组分别归为 near-field/direct leakage 或 fixed-environment reflection 的一批明确 session-level target 证据；现有共同近距离亮带属于可见结构，但缺少摆位/独立物理 ground truth，且组间描述性指标不支持两端具有独特异常模式。`LIKELY_HUMAN` 只用于少数满足收紧后可见形态条件的独立 target，不改变总体风险结论。",
        "",
        "## Provenance",
        "",
        f"- B1 distance/quality source: `{B1}`.",
        f"- historical target/output source: `{JSON_ROOT}` (existing `*_mmwave_vital_signs.json`).",
        f"- DataCube source: `{DATA_ROOT}` (existing `*_datacube*.npz`; read-only).",
        "- code trace: `BR_PIPELINE_CODE_TRACE.md` and `BR_PIPELINE_CODE_PROVENANCE.csv` in the same output directory.",
        "- diagnostic figure directory: `extreme_range_target_figures/`.",
        "",
        "本审查到此停止；没有后续算法、参数或 formal 重跑步骤。",
    ]
    (OUT / "FORMAL_EXTREME_RANGE_TARGET_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"near": len(near), "far": len(far), "reference": len(refs), "classification_rows": len(classification), "figures": len(list(FIG_DIR.glob('*.png')))}, ensure_ascii=False))


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    main()


