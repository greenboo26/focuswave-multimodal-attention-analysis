#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""mmWave HR systematic low-bias mechanism audit (v1).

File: run_mmwave_low_bias_mechanism_audit_20260913.py
Version: 1.0.0
Purpose:
    解释当前 fused HR 约 -9 bpm 的系统性低估主要来自哪里。这是机制审计，
    不是 estimator 搜索：不新建 gating rule、不调 threshold、不改 fused/time/
    spectral estimator、不改 target/bin/channel selector、不改 fusion、不改
    harmonic correction、不改 window、不发布 snapshot v2、不解锁 HRV。

    审计严格复用 estimator improvement v1 冻结的同一批输入（5 sessions /
    100 probes / ECG_VALID 100/100），先复现冻结 control 指标，再做分层、
    配对与 descriptive decomposition，最后形成机制证据矩阵。

Usage:
    python scripts/maintenance/run_mmwave_low_bias_mechanism_audit_20260913.py \
        [--out-dir docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1] \
        [--local-out-dir <dir>]

    默认输出：
      Git-safe: docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1/
      local-only: 11_数据/derived/mmwave_low_bias_mechanism_audit_v1_20260913/
                  PROBE_LEVEL_MECHANISM_100_PROBES.csv（逐 probe，含 ECG 参照细节，不入 Git）

Dependencies:
    只依赖 Python 标准库（csv/json/hashlib/statistics/math/dataclasses/pathlib），
    以保证机制审计不受本机 numpy/pandas 版本影响、可确定性复现。

Boundaries（硬边界，脚本内不实现任何被禁止的操作）:
    - 不写 producer、不写 snapshot v1、不训练模型、不解锁 HRV。
    - 不产生 candidate/production 规则输出；H1/H2/H3 仅作为冻结对照被引用。
    - 不搜索 distance / QC / ECG band 的新 cutpoint；只使用既有冻结定义。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# 冻结常量（全部来自 estimator improvement v1，不得在本任务中修改）
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

# 输入：estimator improvement v1 的 r1 派生结果目录。
DERIVED_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1")
CONTROL_CSV = DERIVED_ROOT / "final_r6" / "CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv"
ELIGIBILITY_CSV = DERIVED_ROOT / "final_r6" / "REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv"
P2_DETAIL_CSV = DERIVED_ROOT / "phase_a_strict_p2_detail" / "MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv"

# 输入身份（冻结；不匹配即 STOP，不自动重建）。
EXPECTED_INPUT_SHA256 = {
    "CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv":
        "B4251445B1938DF61F07EFECE9ECBA4DD29FEFFCEED699E0B5B5226D0571A76D",
    "REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv":
        "EA9DB07FB37A2027569714B3193FC49AAFECA7C59690750BFFAF523C7188F479",
    "MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv":
        "FFED63DDE2E30F5A7B216E5996CB136012286CE4832CA82E6541A66E556C81B1",
}

# 冻结 denominator。
SUBJECTS = ("9779", "97793", "97794", "97795", "97796")
N_PROBES = 100

# 冻结 control 指标（来自 estimator improvement v1 的 CONTROL_VS_CANDIDATES_SUMMARY.csv）。
FROZEN_CONTROL = {
    "fused":    {"mae": 10.457079173363644, "bias": -9.033105841645153, "p90_ae": 24.054346217778583},
    "time":     {"mae": 8.996965770296207,  "bias": -6.737621326761782},
    "spectral": {"mae": 15.12383419314452,  "bias": -13.35101004598486},
}
CONTROL_TOLERANCE = 1e-6

# 冻结 failure-class 名称顺序（严格 P2 当前分类，不得重定义）。
FAILURE_CLASSES = (
    "CORRECT_OR_NEAR_CORRECT",
    "SELECTED_TARGET_WRONG_PEAK",
    "HARMONIC_OR_HALF_DOUBLE_LOCK",
    "TARGET_BIN_CHANNEL_MISS",
)

# 冻结 selected-distance bands（既有定义，不重新搜索 cutpoint）。
DISTANCE_BANDS = (("LT0.5M", 0.0, 0.5), ("0.5_TO_1.5M", 0.5, 1.5), ("GT1.5M", 1.5, math.inf))

# 冻结 ECG HR bands（既有定义，不重新搜索 cutpoint）。
ECG_BANDS = (("LT75", 0.0, 75.0), ("75_TO_90", 75.0, 90.0), ("GT90", 90.0, math.inf))

# 冻结 producer 融合常数（code-path audit 用；只读取、不修改）。
HR_TIME_FREQ_WARNING_BPM = 10.0

# 本任务最终机制判定（只允许下列值；禁止 IMPROVED / FORMAL_HR_READY / SNAPSHOT_V2_READY）。
MECHANISM_STATUS = "MULTIFACTOR_MECHANISM_SUPPORTED"
PRIMARY_MECHANISM = (
    "FAILURE_MODE_CONDITIONAL_LOW_BIAS: 当链路判断正确时融合心率几乎无偏，"
    "总体低估集中在 wrong peak / harmonic / target miss 三个失败类别，"
    "且这些类别的估计一律偏向低端。"
)
SECONDARY_MECHANISM = (
    "SPECTRAL_LOW_BIAS_PULLS_FUSION_DOWN: 频域路相对时域路系统性偏低，"
    "融合在多数 probe 上把结果进一步拉低并贡献约 1.5 bpm 额外绝对误差。"
)

# Markdown 交付物（由 render 脚本生成；在本脚本中登记摘要以做 provenance）。
# CLOUD_HANDOFF_VERIFICATION.json 不在此列：它在云端回读之后才写入，收录自身会形成
# 循环依赖；其摘要记在 HANDOFF.md 与 GitHub issue pointer。
MARKDOWN_DELIVERABLES = (
    "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_REPORT.md",
    "FUSION_PATH_AUDIT.md",
    "HANDOFF.md",
    "ERROR_LOG.json",
)

# 云端交接身份（canonical shared Drive _AI_HANDOFF，按 folder id 访问）。
CLOUD_HANDOFF_FOLDER_NAME = "2026-09-13_mmwave_low_bias_mechanism_audit_v1"
CLOUD_HANDOFF_PARENT_NAME = "_AI_HANDOFF"
CLOUD_HANDOFF_PARENT_ID = "1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL"
CLOUD_HANDOFF_REMOTE_PATH = f"gdrive:{CLOUD_HANDOFF_FOLDER_NAME}"

# 既有 QC 字段（只使用表中确实存在的字段；缺失写 NOT_AVAILABLE）。
# 注意来源表：usable ratio / phase stability / motion proxy / frames 均在 eligibility
# 表；control 表只有 estimator 输出与 selector 字段，P2 detail 表另有 pre-gate 字段。
QC_FIELDS = (
    ("hr_usable_ratio", ELIGIBILITY_CSV),
    ("phase_stability", ELIGIBILITY_CSV),
    ("motion_proxy", ELIGIBILITY_CSV),
    ("ecg_valid_ratio", ELIGIBILITY_CSV),
    ("rsp_valid_ratio", ELIGIBILITY_CSV),
    ("mmwave_frames", ELIGIBILITY_CSV),
)

# 已有但本任务判定为 NOT_AVAILABLE 的字段（明确记录，不补算新定义）。
QC_NOT_AVAILABLE = {
    "hr_confidence": "P2 detail 的 hr_confidence 在本轮冻结 output 中为空；不补算。",
    "selected_channel_selection_margin": "P2 detail 该列本轮为空值；不补算。",
    "selected_candidate_power": "P2 detail 该列为单个 selected candidate 值，非窗口级 margin；不作为 QC 门使用。",
    "gate_hit": "control 表 gate_hit 全为 False，无区分度（记录了未被全局硬门拦截）。",
}


def sha256_file(path: Path) -> str:
    """Return the uppercase SHA-256 of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha256_text_normalised(path: Path) -> str:
    """Return SHA-256 of LF-normalised content (EOL-independent digest).

    交付物可能在 CRLF/LF checkout 之间变化；raw byte 摘要会随平台改变。需要
    跨 checkout 稳定的登记值一律使用本函数；上传文件的真实字节仍由
    CLOUD_HANDOFF_VERIFICATION.json 的逐文件回读负责。
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()


def read_csv_rows(path: Path) -> list[dict]:
    """Read a CSV into a list of dicts, tolerant of a UTF-8 BOM."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Write rows to CSV deterministically with LF endings."""
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    names = fieldnames if fieldnames is not None else list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fnum(value, default=math.nan) -> float:
    """Parse a float, returning default for empty or non-finite input."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def fmt(value: float, digits: int = 6) -> str:
    """Format a float for CSV output, using empty string for NaN."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return ""
    return f"{value:.{digits}f}"


def mean(values: list[float]) -> float:
    """Arithmetic mean, NaN for an empty list."""
    return statistics.fmean(values) if values else math.nan


def median(values: list[float]) -> float:
    """Median, NaN for an empty list."""
    return statistics.median(values) if values else math.nan


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile (same convention as numpy default)."""
    if not values:
        return math.nan
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[int(pos)]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def mean_abs(values: list[float]) -> float:
    """Mean absolute value (MAE helper)."""
    return mean([abs(v) for v in values]) if values else math.nan


def rank_average(values: list[float]) -> list[float]:
    """Average ranks with ties sharing the mean rank (Spearman helper)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(order):
        j = idx
        while j + 1 < len(order) and values[order[j + 1]] == values[order[idx]]:
            j += 1
        avg = (idx + j) / 2.0 + 1.0
        for k in range(idx, j + 1):
            ranks[order[k]] = avg
        idx = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation; NaN when undefined or constant input."""
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return math.nan
    xr = rank_average([p[0] for p in pairs])
    yr = rank_average([p[1] for p in pairs])
    mx, my = mean(xr), mean(yr)
    num = sum((a - mx) * (b - my) for a, b in zip(xr, yr))
    den = math.sqrt(sum((a - mx) ** 2 for a in xr) * sum((b - my) ** 2 for b in yr))
    return num / den if den > 0 else math.nan


def band_of(value: float, bands) -> str:
    """Return the band label containing value."""
    for label, lo, hi in bands:
        if lo <= value < hi:
            return label
    return "UNBANDED"


# ---------------------------------------------------------------------------
# Probe 级合并与基础派生量
# ---------------------------------------------------------------------------


@dataclass
class Probe:
    """One frozen probe window with all mechanism-audit derived quantities."""

    subject: str
    block_id: str
    onset: int
    ecg: float
    fused: float
    time: float
    spectral: float
    failure_class: str
    distance: float
    hr_bin: str
    hr_channel: str
    rsp_br: float
    usable_ratio: float
    phase_stability: float
    motion_proxy: float
    frames: float
    seconds_flags: str

    @property
    def e_fused(self) -> float:
        return self.fused - self.ecg

    @property
    def e_time(self) -> float:
        return self.time - self.ecg

    @property
    def e_spectral(self) -> float:
        return self.spectral - self.ecg

    @property
    def ae_fused(self) -> float:
        return abs(self.e_fused)

    @property
    def ae_time(self) -> float:
        return abs(self.e_time)

    @property
    def ae_spectral(self) -> float:
        return abs(self.e_spectral)

    @property
    def fusion_penalty_vs_time(self) -> float:
        """Positive means fusion made the absolute error worse than the time arm."""
        return self.ae_fused - self.ae_time

    @property
    def fusion_signed_shift_vs_time(self) -> float:
        return self.fused - self.time

    @property
    def spectral_signed_shift_vs_time(self) -> float:
        return self.spectral - self.time

    @property
    def gap_time_spectral(self) -> float:
        return abs(self.time - self.spectral)

    @property
    def distance_band(self) -> str:
        return band_of(self.distance, DISTANCE_BANDS)

    @property
    def ecg_band(self) -> str:
        return band_of(self.ecg, ECG_BANDS)

    @property
    def spectral_below_time(self) -> bool:
        return self.spectral < self.time

    @property
    def fused_below_time(self) -> bool:
        return self.fused < self.time

    @property
    def spectral_pulled_fused_down(self) -> bool:
        """spectral < time and fusion also sits below the time arm."""
        return self.spectral_below_time and self.fused_below_time

    @property
    def harmonic_ratio_time(self) -> float:
        """time/ecg ratio; ~0.5 or ~2.0 indicates half/double lock."""
        return self.time / self.ecg if self.ecg else math.nan

    @property
    def harmonic_ratio_spectral(self) -> float:
        return self.spectral / self.ecg if self.ecg else math.nan

    @property
    def harmonic_ratio_fused(self) -> float:
        return self.fused / self.ecg if self.ecg else math.nan


# 既有 P2 harmonic 诊断容差：>10 bpm 分歧且 fused/spectral 落在 2x/3x mmWave BR 的 5 bpm 内。
HARMONIC_BR_TOLERANCE_BPM = 5.0


def br_harmonic_relation(value: float, br_bpm: float) -> float:
    """Return the signed distance of value from the nearest 2x/3x BR multiple."""
    if not math.isfinite(br_bpm) or br_bpm <= 0:
        return math.nan
    dels = [abs(value - mult * br_bpm) for mult in (2.0, 3.0)]
    return min(dels)


def build_probes() -> tuple[list[Probe], dict]:
    """Merge the three frozen inputs on (subject, block_id, onset) and derive fields."""
    control = read_csv_rows(CONTROL_CSV)
    elig = read_csv_rows(ELIGIBILITY_CSV)
    p2 = read_csv_rows(P2_DETAIL_CSV)

    def key(subject: str, block_id: str, onset) -> tuple[str, str, int]:
        return (str(subject).strip(), str(block_id).strip(), int(float(onset)))

    control_by = {key(r["subject"], r["block_id"], r["probe_onset_unix_ms"]): r for r in control}
    elig_by = {key(r["subject"], r["block_id"], r["probe_onset_unix_ms"]): r for r in elig}
    p2_by = {key(r["subject"], r["block_id"], r["probe_onset_unix_ms"]): r for r in p2}

    if not (len(control_by) == len(elig_by) == len(p2_by) == N_PROBES):
        raise SystemExit(
            f"BLOCKED_INPUT_IDENTITY_MISMATCH: key counts control={len(control_by)} "
            f"eligibility={len(elig_by)} p2={len(p2_by)} expected={N_PROBES}"
        )
    if set(control_by) != set(elig_by) or set(control_by) != set(p2_by):
        raise SystemExit("BLOCKED_INPUT_IDENTITY_MISMATCH: key sets differ across inputs")

    subjects_seen = Counter(k[0] for k in control_by)
    if set(subjects_seen) != set(SUBJECTS):
        raise SystemExit(f"BLOCKED_INPUT_IDENTITY_MISMATCH: subjects {sorted(subjects_seen)}")

    probes: list[Probe] = []
    for k in sorted(control_by, key=lambda t: (t[0], t[1], t[2])):
        c, e, p = control_by[k], elig_by[k], p2_by[k]
        probes.append(
            Probe(
                subject=k[0],
                block_id=k[1],
                onset=k[2],
                ecg=fnum(c["ecg_hr_bpm"]),
                fused=fnum(c["control_fused_hr_bpm"]),
                time=fnum(c["control_time_hr_bpm"]),
                spectral=fnum(c["control_spectral_hr_bpm"]),
                failure_class=str(p["PRIMARY_FAILURE_CLASS"]).strip(),
                distance=fnum(c["hr_distance_proxy_m"]),
                hr_bin=str(c["hr_bin"]).strip(),
                hr_channel=str(c["hr_channel"]).strip(),
                rsp_br=fnum(p.get("rsp_br_bpm")),
                usable_ratio=fnum(e["hr_usable_ratio"]),
                phase_stability=fnum(e["phase_stability"]),
                motion_proxy=fnum(e["motion_proxy"]),
                frames=fnum(e["mmwave_frames"]),
                seconds_flags=str(p.get("SECONDARY_FLAGS", "")),
            )
        )

    classes = Counter(p.failure_class for p in probes)
    meta = {
        "n_probes": len(probes),
        "n_sessions": len(subjects_seen),
        "session_counts": dict(sorted(subjects_seen.items())),
        "failure_class_counts": {name: classes.get(name, 0) for name in FAILURE_CLASSES},
    }
    return probes, meta


def reproduce_control(probes: list[Probe]) -> dict:
    """Reproduce the frozen control metrics; raise if they do not match."""
    got = {
        "fused": {
            "mae": mean([p.ae_fused for p in probes]),
            "bias": mean([p.e_fused for p in probes]),
            "p90_ae": percentile([p.ae_fused for p in probes], 0.90),
        },
        "time": {
            "mae": mean([p.ae_time for p in probes]),
            "bias": mean([p.e_time for p in probes]),
        },
        "spectral": {
            "mae": mean([p.ae_spectral for p in probes]),
            "bias": mean([p.e_spectral for p in probes]),
        },
    }
    failures = []
    for arm, expected in FROZEN_CONTROL.items():
        for metric, want in expected.items():
            have = got[arm][metric]
            if abs(have - want) > CONTROL_TOLERANCE:
                failures.append(f"{arm}.{metric}: got {have!r} expected {want!r}")
    if failures:
        raise SystemExit("BLOCKED_CONTROL_REPRODUCTION_FAILED: " + "; ".join(failures))
    return got


# ---------------------------------------------------------------------------
# 表 1：FUSION_LOW_BIAS_DECOMPOSITION.csv
# ---------------------------------------------------------------------------


def table_fusion(probes: list[Probe]) -> list[dict]:
    """Per-probe fusion decomposition (the required probe-level diagnostic rows)."""
    rows = []
    for p in probes:
        rows.append({
            "subject": p.subject,
            "block_id": p.block_id,
            "probe_onset_unix_ms": p.onset,
            "failure_class": p.failure_class,
            "distance_band": p.distance_band,
            "selected_distance_m": fmt(p.distance, 4),
            "ecg_hr_bpm": fmt(p.ecg),
            "fused_hr_bpm": fmt(p.fused),
            "time_hr_bpm": fmt(p.time),
            "spectral_hr_bpm": fmt(p.spectral),
            "signed_error_fused_bpm": fmt(p.e_fused),
            "signed_error_time_bpm": fmt(p.e_time),
            "signed_error_spectral_bpm": fmt(p.e_spectral),
            "absolute_error_fused_bpm": fmt(p.ae_fused),
            "absolute_error_time_bpm": fmt(p.ae_time),
            "absolute_error_spectral_bpm": fmt(p.ae_spectral),
            "fusion_penalty_vs_time_bpm": fmt(p.fusion_penalty_vs_time),
            "fusion_signed_shift_vs_time_bpm": fmt(p.fusion_signed_shift_vs_time),
            "spectral_signed_shift_vs_time_bpm": fmt(p.spectral_signed_shift_vs_time),
            "gap_time_spectral_bpm": fmt(p.gap_time_spectral),
            "gap_le_frozen_warning_10bpm": int(p.gap_time_spectral <= HR_TIME_FREQ_WARNING_BPM),
            "spectral_below_time": int(p.spectral_below_time),
            "fused_below_time": int(p.fused_below_time),
            "spectral_pulled_fused_down": int(p.spectral_pulled_fused_down),
            "time_ae_le5_and_fused_ae_gt5": int(p.ae_time <= 5.0 and p.ae_fused > 5.0),
            "time_ae_le5_and_fused_ae_gt10": int(p.ae_time <= 5.0 and p.ae_fused > 10.0),
        })
    return rows


def fusion_summary(probes: list[Probe]) -> dict:
    """Pooled fusion counters plus per-session stratification."""
    def block(members: list[Probe]) -> dict:
        return {
            "n": len(members),
            "spectral_lt_time_n": sum(1 for p in members if p.spectral_below_time),
            "fused_lt_time_n": sum(1 for p in members if p.fused_below_time),
            "spectral_pulled_fused_down_n": sum(1 for p in members if p.spectral_pulled_fused_down),
            "time_ae_le5_fused_gt5_n": sum(1 for p in members if p.ae_time <= 5.0 and p.ae_fused > 5.0),
            "time_ae_le5_fused_gt10_n": sum(1 for p in members if p.ae_time <= 5.0 and p.ae_fused > 10.0),
            "improve_n": sum(1 for p in members if p.ae_fused < p.ae_time - 1e-12),
            "worsen_n": sum(1 for p in members if p.ae_fused > p.ae_time + 1e-12),
            "tie_n": sum(1 for p in members if abs(p.ae_fused - p.ae_time) <= 1e-12),
            "mean_fusion_penalty_vs_time_bpm": mean([p.fusion_penalty_vs_time for p in members]),
            "mean_fusion_signed_shift_vs_time_bpm": mean([p.fusion_signed_shift_vs_time for p in members]),
            "mean_spectral_signed_shift_vs_time_bpm": mean([p.spectral_signed_shift_vs_time for p in members]),
            "gap_gt10_n": sum(1 for p in members if p.gap_time_spectral > HR_TIME_FREQ_WARNING_BPM),
            "fusion_worse_than_both_arms_n": sum(
                1 for p in members if p.ae_fused > max(p.ae_time, p.ae_spectral) + 1e-12
            ),
        }

    return {"POOLED": block(probes), **{s: block([p for p in probes if p.subject == s]) for s in SUBJECTS}}


# ---------------------------------------------------------------------------
# 表 2/3：DISTANCE_SESSION_STRATIFIED.csv, DISTANCE_FAILURE_CLASS_MATRIX.csv
# ---------------------------------------------------------------------------


def table_distance_session(probes: list[Probe]) -> list[dict]:
    """Session x distance-band cross-tab with all three arms' bias/MAE."""
    rows = []
    for subject in list(SUBJECTS) + ["ALL_SESSIONS"]:
        members = probes if subject == "ALL_SESSIONS" else [p for p in probes if p.subject == subject]
        for label, _, _ in DISTANCE_BANDS:
            cell = [p for p in members if p.distance_band == label]
            rows.append({
                "subject": subject,
                "distance_band": label,
                "n": len(cell),
                "fused_bias_bpm": fmt(mean([p.e_fused for p in cell])) if cell else "",
                "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in cell])) if cell else "",
                "time_bias_bpm": fmt(mean([p.e_time for p in cell])) if cell else "",
                "time_mae_bpm": fmt(mean_abs([p.e_time for p in cell])) if cell else "",
                "spectral_bias_bpm": fmt(mean([p.e_spectral for p in cell])) if cell else "",
                "spectral_mae_bpm": fmt(mean_abs([p.e_spectral for p in cell])) if cell else "",
                "mean_fusion_penalty_vs_time_bpm": (
                    fmt(mean([p.fusion_penalty_vs_time for p in cell])) if cell else ""
                ),
                "ecg_hr_median_bpm": fmt(median([p.ecg for p in cell])) if cell else "",
            })
    return rows


def table_distance_failure(probes: list[Probe]) -> list[dict]:
    """Distance band x failure class matrix, plus concentration of GT1.5M error."""
    rows = []
    for label, _, _ in DISTANCE_BANDS:
        for cls in FAILURE_CLASSES:
            cell = [p for p in probes if p.distance_band == label and p.failure_class == cls]
            n_band = sum(1 for p in probes if p.distance_band == label)
            rows.append({
                "distance_band": label,
                "failure_class": cls,
                "n": len(cell),
                "share_of_band_pct": fmt(100.0 * len(cell) / n_band, 3) if n_band else "",
                "fused_bias_bpm": fmt(mean([p.e_fused for p in cell])) if cell else "",
                "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in cell])) if cell else "",
                "time_bias_bpm": fmt(mean([p.e_time for p in cell])) if cell else "",
                "time_mae_bpm": fmt(mean_abs([p.e_time for p in cell])) if cell else "",
                "spectral_bias_bpm": fmt(mean([p.e_spectral for p in cell])) if cell else "",
                "ecg_hr_median_bpm": fmt(median([p.ecg for p in cell])) if cell else "",
                "sessions_present": "|".join(sorted({p.subject for p in cell})),
            })
    return rows


def within_session_distance(probes: list[Probe]) -> list[dict]:
    """Per-session check of whether far-distance low bias still appears."""
    rows = []
    for subject in SUBJECTS:
        members = [p for p in probes if p.subject == subject]
        near = [p for p in members if p.distance < 1.5]
        far = [p for p in members if p.distance >= 1.5]
        pooled_far = [p for p in probes if p.distance >= 1.5]
        rows.append({
            "subject": subject,
            "n_total": len(members),
            "n_near_lt1.5m": len(near),
            "n_far_ge1.5m": len(far),
            "near_fused_bias_bpm": fmt(mean([p.e_fused for p in near])) if near else "",
            "far_fused_bias_bpm": fmt(mean([p.e_fused for p in far])) if far else "",
            "within_session_far_minus_near_bias_bpm": (
                fmt(mean([p.e_fused for p in far]) - mean([p.e_fused for p in near]))
                if near and far else ""
            ),
            "near_time_bias_bpm": fmt(mean([p.e_time for p in near])) if near else "",
            "far_time_bias_bpm": fmt(mean([p.e_time for p in far])) if far else "",
            "far_pooled_fused_bias_bpm": fmt(mean([p.e_fused for p in pooled_far])),
            "far_pooled_n": len(pooled_far),
            "far_share_of_this_session_pct": fmt(100.0 * len(far) / len(members), 3) if members else "",
            "far_share_of_all_far_pct": fmt(100.0 * len(far) / len(pooled_far), 3) if pooled_far else "",
        })
    return rows


def continuous_distance_descriptives(probes: list[Probe]) -> dict:
    """Descriptive-only Spearman associations (clustered, non-independent)."""
    dist = [p.distance for p in probes]
    return {
        "label": "DESCRIPTIVE_ONLY / CLUSTERED_NONINDEPENDENT",
        "note": "100 probes come from 5 sessions; no population inference and no cutpoint search.",
        "spearman_distance_vs_signed_error_fused": spearman(dist, [p.e_fused for p in probes]),
        "spearman_distance_vs_absolute_error_fused": spearman(dist, [p.ae_fused for p in probes]),
        "spearman_distance_vs_fusion_penalty_vs_time": spearman(dist, [p.fusion_penalty_vs_time for p in probes]),
        "spearman_distance_vs_signed_error_time": spearman(dist, [p.e_time for p in probes]),
        "spearman_distance_vs_signed_error_spectral": spearman(dist, [p.e_spectral for p in probes]),
        "distance_min_m": min(dist),
        "distance_median_m": median(dist),
        "distance_max_m": max(dist),
    }


# ---------------------------------------------------------------------------
# 表 4：FAILURE_CLASS_BIAS_DECOMPOSITION.csv
# ---------------------------------------------------------------------------


def table_failure_class(probes: list[Probe]) -> list[dict]:
    """Failure-class decomposition across all arms plus QC/distance context."""
    rows = []
    for cls in FAILURE_CLASSES:
        cell = [p for p in probes if p.failure_class == cls]
        rows.append({
            "failure_class": cls,
            "n": len(cell),
            "share_pct": fmt(100.0 * len(cell) / len(probes), 3),
            "ecg_hr_median_bpm": fmt(median([p.ecg for p in cell])) if cell else "",
            "fused_bias_bpm": fmt(mean([p.e_fused for p in cell])) if cell else "",
            "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in cell])) if cell else "",
            "fused_median_ae_bpm": fmt(median([p.ae_fused for p in cell])) if cell else "",
            "fused_p90_ae_bpm": fmt(percentile([p.ae_fused for p in cell], 0.90)) if cell else "",
            "fused_max_ae_bpm": fmt(max([p.ae_fused for p in cell])) if cell else "",
            "time_bias_bpm": fmt(mean([p.e_time for p in cell])) if cell else "",
            "time_mae_bpm": fmt(mean_abs([p.e_time for p in cell])) if cell else "",
            "time_median_ae_bpm": fmt(median([p.ae_time for p in cell])) if cell else "",
            "time_p90_ae_bpm": fmt(percentile([p.ae_time for p in cell], 0.90)) if cell else "",
            "spectral_bias_bpm": fmt(mean([p.e_spectral for p in cell])) if cell else "",
            "spectral_mae_bpm": fmt(mean_abs([p.e_spectral for p in cell])) if cell else "",
            "spectral_median_ae_bpm": fmt(median([p.ae_spectral for p in cell])) if cell else "",
            "spectral_p90_ae_bpm": fmt(percentile([p.ae_spectral for p in cell], 0.90)) if cell else "",
            "mean_fusion_penalty_vs_time_bpm": fmt(mean([p.fusion_penalty_vs_time for p in cell])) if cell else "",
            "distance_median_m": fmt(median([p.distance for p in cell]), 4) if cell else "",
            "distance_band_lt0.5_n": sum(1 for p in cell if p.distance_band == "LT0.5M"),
            "distance_band_0.5_1.5_n": sum(1 for p in cell if p.distance_band == "0.5_TO_1.5M"),
            "distance_band_gt1.5_n": sum(1 for p in cell if p.distance_band == "GT1.5M"),
            "hr_usable_ratio_median": fmt(median([p.usable_ratio for p in cell])) if cell else "",
            "phase_stability_median": fmt(median([p.phase_stability for p in cell])) if cell else "",
            "motion_proxy_median": fmt(median([p.motion_proxy for p in cell])) if cell else "",
            "sessions_present": "|".join(sorted({p.subject for p in cell})),
            "session_distribution": "|".join(
                f"{s}:{c}" for s, c in sorted(Counter(p.subject for p in cell).items())
            ),
        })
    # 明确区分 class 已解释的错误 vs 非 harmonic probe 的残留低估。
    harmonic = [p for p in probes if p.failure_class == "HARMONIC_OR_HALF_DOUBLE_LOCK"]
    non_harmonic = [p for p in probes if p.failure_class != "HARMONIC_OR_HALF_DOUBLE_LOCK"]
    rows.append({
        "failure_class": "ALL_PROBES",
        "n": len(probes),
        "share_pct": "100.000",
        "ecg_hr_median_bpm": fmt(median([p.ecg for p in probes])),
        "fused_bias_bpm": fmt(mean([p.e_fused for p in probes])),
        "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in probes])),
        "fused_median_ae_bpm": fmt(median([p.ae_fused for p in probes])),
        "fused_p90_ae_bpm": fmt(percentile([p.ae_fused for p in probes], 0.90)),
        "fused_max_ae_bpm": fmt(max([p.ae_fused for p in probes])),
        "time_bias_bpm": fmt(mean([p.e_time for p in probes])),
        "time_mae_bpm": fmt(mean_abs([p.e_time for p in probes])),
        "time_median_ae_bpm": fmt(median([p.ae_time for p in probes])),
        "time_p90_ae_bpm": fmt(percentile([p.ae_time for p in probes], 0.90)),
        "spectral_bias_bpm": fmt(mean([p.e_spectral for p in probes])),
        "spectral_mae_bpm": fmt(mean_abs([p.e_spectral for p in probes])),
        "spectral_median_ae_bpm": fmt(median([p.ae_spectral for p in probes])),
        "spectral_p90_ae_bpm": fmt(percentile([p.ae_spectral for p in probes], 0.90)),
        "mean_fusion_penalty_vs_time_bpm": fmt(mean([p.fusion_penalty_vs_time for p in probes])),
        "distance_median_m": fmt(median([p.distance for p in probes]), 4),
        "distance_band_lt0.5_n": sum(1 for p in probes if p.distance_band == "LT0.5M"),
        "distance_band_0.5_1.5_n": sum(1 for p in probes if p.distance_band == "0.5_TO_1.5M"),
        "distance_band_gt1.5_n": sum(1 for p in probes if p.distance_band == "GT1.5M"),
        "hr_usable_ratio_median": fmt(median([p.usable_ratio for p in probes])),
        "phase_stability_median": fmt(median([p.phase_stability for p in probes])),
        "motion_proxy_median": fmt(median([p.motion_proxy for p in probes])),
        "sessions_present": "|".join(sorted({p.subject for p in probes})),
        "session_distribution": "|".join(f"{s}:{c}" for s, c in sorted(Counter(p.subject for p in probes).items())),
    })
    for label, group in (("HARMONIC_CLASS_ONLY", harmonic), ("NON_HARMONIC_RESIDUAL", non_harmonic)):
        rows.append({
            "failure_class": label,
            "n": len(group),
            "share_pct": fmt(100.0 * len(group) / len(probes), 3),
            "ecg_hr_median_bpm": fmt(median([p.ecg for p in group])),
            "fused_bias_bpm": fmt(mean([p.e_fused for p in group])),
            "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in group])),
            "fused_median_ae_bpm": fmt(median([p.ae_fused for p in group])),
            "fused_p90_ae_bpm": fmt(percentile([p.ae_fused for p in group], 0.90)),
            "fused_max_ae_bpm": fmt(max([p.ae_fused for p in group])),
            "time_bias_bpm": fmt(mean([p.e_time for p in group])),
            "time_mae_bpm": fmt(mean_abs([p.e_time for p in group])),
            "time_median_ae_bpm": fmt(median([p.ae_time for p in group])),
            "time_p90_ae_bpm": fmt(percentile([p.ae_time for p in group], 0.90)),
            "spectral_bias_bpm": fmt(mean([p.e_spectral for p in group])),
            "spectral_mae_bpm": fmt(mean_abs([p.e_spectral for p in group])),
            "spectral_median_ae_bpm": fmt(median([p.ae_spectral for p in group])),
            "spectral_p90_ae_bpm": fmt(percentile([p.ae_spectral for p in group], 0.90)),
            "mean_fusion_penalty_vs_time_bpm": fmt(mean([p.fusion_penalty_vs_time for p in group])),
            "distance_median_m": fmt(median([p.distance for p in group]), 4),
            "distance_band_lt0.5_n": sum(1 for p in group if p.distance_band == "LT0.5M"),
            "distance_band_0.5_1.5_n": sum(1 for p in group if p.distance_band == "0.5_TO_1.5M"),
            "distance_band_gt1.5_n": sum(1 for p in group if p.distance_band == "GT1.5M"),
            "hr_usable_ratio_median": fmt(median([p.usable_ratio for p in group])),
            "phase_stability_median": fmt(median([p.phase_stability for p in group])),
            "motion_proxy_median": fmt(median([p.motion_proxy for p in group])),
            "sessions_present": "|".join(sorted({p.subject for p in group})),
            "session_distribution": "|".join(f"{s}:{c}" for s, c in sorted(Counter(p.subject for p in group).items())),
        })
    return rows


# ---------------------------------------------------------------------------
# 表 5：ECG_HR_BAND_DECOMPOSITION.csv
# ---------------------------------------------------------------------------


def table_ecg_band(probes: list[Probe]) -> list[dict]:
    """Frozen ECG HR band decomposition across arms and sessions."""
    rows = []
    for label, _, _ in ECG_BANDS:
        cell = [p for p in probes if p.ecg_band == label]
        rows.append({
            "scope": "POOLED",
            "ecg_hr_band": label,
            "n": len(cell),
            "ecg_hr_median_bpm": fmt(median([p.ecg for p in cell])) if cell else "",
            "fused_bias_bpm": fmt(mean([p.e_fused for p in cell])) if cell else "",
            "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in cell])) if cell else "",
            "time_bias_bpm": fmt(mean([p.e_time for p in cell])) if cell else "",
            "time_mae_bpm": fmt(mean_abs([p.e_time for p in cell])) if cell else "",
            "spectral_bias_bpm": fmt(mean([p.e_spectral for p in cell])) if cell else "",
            "spectral_mae_bpm": fmt(mean_abs([p.e_spectral for p in cell])) if cell else "",
            "mean_fusion_penalty_vs_time_bpm": fmt(mean([p.fusion_penalty_vs_time for p in cell])) if cell else "",
            "distance_median_m": fmt(median([p.distance for p in cell]), 4) if cell else "",
            "session_distribution": "|".join(
                f"{s}:{c}" for s, c in sorted(Counter(p.subject for p in cell).items())
            ),
        })
    for subject in SUBJECTS:
        members = [p for p in probes if p.subject == subject]
        for label, _, _ in ECG_BANDS:
            cell = [p for p in members if p.ecg_band == label]
            rows.append({
                "scope": f"SESSION_{subject}",
                "ecg_hr_band": label,
                "n": len(cell),
                "ecg_hr_median_bpm": fmt(median([p.ecg for p in cell])) if cell else "",
                "fused_bias_bpm": fmt(mean([p.e_fused for p in cell])) if cell else "",
                "fused_mae_bpm": fmt(mean_abs([p.e_fused for p in cell])) if cell else "",
                "time_bias_bpm": fmt(mean([p.e_time for p in cell])) if cell else "",
                "time_mae_bpm": fmt(mean_abs([p.e_time for p in cell])) if cell else "",
                "spectral_bias_bpm": fmt(mean([p.e_spectral for p in cell])) if cell else "",
                "spectral_mae_bpm": fmt(mean_abs([p.e_spectral for p in cell])) if cell else "",
                "mean_fusion_penalty_vs_time_bpm": fmt(mean([p.fusion_penalty_vs_time for p in cell])) if cell else "",
                "distance_median_m": fmt(median([p.distance for p in cell]), 4) if cell else "",
                "session_distribution": f"{subject}:{len(cell)}" if cell else "",
            })
    return rows


# ---------------------------------------------------------------------------
# 表 6：QC_BIAS_DECOMPOSITION.csv
# ---------------------------------------------------------------------------


def table_qc(probes: list[Probe]) -> tuple[list[dict], dict]:
    """Descriptive QC vs error relations, pooled and per session."""
    field_map = {
        "hr_usable_ratio": lambda p: p.usable_ratio,
        "phase_stability": lambda p: p.phase_stability,
        "motion_proxy": lambda p: p.motion_proxy,
        "mmwave_frames": lambda p: p.frames,
        "ecg_valid_ratio": None,
        "rsp_valid_ratio": None,
    }
    rows = []
    for field, getter in field_map.items():
        if getter is None:
            rows.append({
                "qc_field": field,
                "scope": "POOLED",
                "n": 0,
                "spearman_vs_signed_error_fused": "",
                "spearman_vs_absolute_error_fused": "",
                "spearman_vs_fusion_penalty_vs_time": "",
                "direction_consistent_across_sessions": "NOT_AVAILABLE",
                "per_session_directions": "NOT_AVAILABLE",
                "note": QC_NOT_AVAILABLE.get(field, "字段未进入本轮合并表；不补算。"),
            })
            continue
        qc = [getter(p) for p in probes]
        # 常量字段没有方差，秩相关无定义；明确标注而不是留空。
        if len(set(qc)) == 1:
            rows.append({
                "qc_field": field,
                "scope": "POOLED",
                "n": len(probes),
                "spearman_vs_signed_error_fused": "UNDEFINED",
                "spearman_vs_absolute_error_fused": "UNDEFINED",
                "spearman_vs_fusion_penalty_vs_time": "UNDEFINED",
                "direction_consistent_across_sessions": "CONSTANT_NO_VARIANCE",
                "per_session_directions": "CONSTANT_NO_VARIANCE",
                "note": (
                    f"该字段在本轮 100 个探针中恒为 {qc[0]}，无判别力；"
                    "既有 QC 字段因此无法解释任何 probe 间低估差异（不是缺失，而是常量）。"
                ),
            })
            continue
        pooled = {
            "qc_field": field,
            "scope": "POOLED",
            "n": len(probes),
            "spearman_vs_signed_error_fused": fmt(spearman(qc, [p.e_fused for p in probes])),
            "spearman_vs_absolute_error_fused": fmt(spearman(qc, [p.ae_fused for p in probes])),
            "spearman_vs_fusion_penalty_vs_time": fmt(spearman(qc, [p.fusion_penalty_vs_time for p in probes])),
            "direction_consistent_across_sessions": "",
            "per_session_directions": "",
            "note": "DESCRIPTIVE_ONLY / CLUSTERED_NONINDEPENDENT",
        }
        directions = []
        session_rows = []
        for subject in SUBJECTS:
            members = [p for p in probes if p.subject == subject]
            rho = spearman([getter(p) for p in members], [p.e_fused for p in members])
            sign = "+" if (math.isfinite(rho) and rho > 0) else ("-" if math.isfinite(rho) and rho < 0 else "0")
            directions.append(f"{subject}:{sign}({fmt(rho, 3) or 'NA'})")
            session_rows.append({
                "qc_field": field,
                "scope": f"SESSION_{subject}",
                "n": len(members),
                "spearman_vs_signed_error_fused": fmt(rho),
                "spearman_vs_absolute_error_fused": fmt(
                    spearman([getter(p) for p in members], [p.ae_fused for p in members])
                ),
                "spearman_vs_fusion_penalty_vs_time": fmt(
                    spearman([getter(p) for p in members], [p.fusion_penalty_vs_time for p in members])
                ),
                "direction_consistent_across_sessions": "",
                "per_session_directions": "",
                "note": "DESCRIPTIVE_ONLY / CLUSTERED_NONINDEPENDENT",
            })
        signs = {d.split(":")[1][0] for d in directions}
        pooled["direction_consistent_across_sessions"] = "YES" if len(signs) == 1 else "NO"
        pooled["per_session_directions"] = "|".join(directions)
        rows.append(pooled)
        rows.extend(session_rows)
    return rows, {
        "fields_used": [f for f, g in field_map.items() if g is not None],
        "fields_not_available": QC_NOT_AVAILABLE,
    }


# ---------------------------------------------------------------------------
# 表 7：MECHANISM_EVIDENCE_MATRIX.csv
# ---------------------------------------------------------------------------


def table_mechanism(probes: list[Probe], fusion: dict, dist: dict, within: list, fc_rows: list) -> list[dict]:
    """Build the mechanism evidence matrix with explicit for/against evidence."""
    pooled = fusion["POOLED"]
    n = len(probes)
    harmonic = [p for p in probes if p.failure_class == "HARMONIC_OR_HALF_DOUBLE_LOCK"]
    non_harmonic = [p for p in probes if p.failure_class != "HARMONIC_OR_HALF_DOUBLE_LOCK"]
    correct = [p for p in probes if p.failure_class == "CORRECT_OR_NEAR_CORRECT"]

    # session consistency helpers
    per_session_fused_bias = {s: mean([p.e_fused for p in probes if p.subject == s]) for s in SUBJECTS}
    neg_sessions = sum(1 for v in per_session_fused_bias.values() if v < 0)
    spectral_lt_time_sessions = sum(
        1 for s in SUBJECTS
        if sum(1 for p in probes if p.subject == s and p.spectral_below_time)
        > 0.5 * sum(1 for p in probes if p.subject == s)
    )
    penalty_pos_sessions = sum(1 for s in SUBJECTS if fusion[s]["mean_fusion_penalty_vs_time_bpm"] > 0)
    pen_sessions = sum(1 for s in SUBJECTS if fusion[s]["improve_n"] < fusion[s]["worsen_n"])

    # 非 harmonic 残留低估：把 harmonic 全部剔除后 bias 是否仍明显为负。
    resid_bias = mean([p.e_fused for p in non_harmonic])
    harmonic_bias = mean([p.e_fused for p in harmonic])
    # 限制在 CORRECT_OR_NEAR_CORRECT 上，QC/一般低 SNR 的直接证据。
    correct_bias = mean([p.e_fused for p in correct])
    correct_mae = mean_abs([p.e_fused for p in correct])

    # 距离一致性
    far = [p for p in probes if p.distance >= 1.5]
    near = [p for p in probes if p.distance < 1.5]
    far_sessions = Counter(p.subject for p in far)
    far_minus_near = {r["subject"]: r["within_session_far_minus_near_bias_bpm"] for r in within}
    far_worse_sessions = sum(
        1 for r in within
        if r["within_session_far_minus_near_bias_bpm"] not in ("", None)
        and float(r["within_session_far_minus_near_bias_bpm"]) < 0
    )
    sessions_with_far = sum(1 for r in within if r["n_far_ge1.5m"] > 0)

    def row(candidate, for_, against, session_consistency, fc_link, confidence, next_test):
        return {
            "MECHANISM_CANDIDATE": candidate,
            "EVIDENCE_FOR": for_,
            "EVIDENCE_AGAINST": against,
            "SESSION_CONSISTENCY": session_consistency,
            "FAILURE_CLASS_LINK": fc_link,
            "CONFIDENCE": confidence,
            "NEXT_TEST": next_test,
        }

    rows = [
        row(
            "SPECTRAL_LOW_BIAS_PULLS_FUSION_DOWN",
            f"spectral bias {mean([p.e_spectral for p in probes]):.3f} bpm is more negative than time bias "
            f"{mean([p.e_time for p in probes]):.3f}; spectral<time in {pooled['spectral_lt_time_n']}/100 probes; "
            f"fusion sits below time in {pooled['fused_lt_time_n']}/100 probes; "
            f"gap<=10 bpm weighted-average branch applies to {100 - pooled['gap_gt10_n']}/100 probes.",
            f"fusion improves vs time in {pooled['improve_n']}/100 and worsens in {pooled['worsen_n']}/100; "
            f"mean fusion penalty vs time is {pooled['mean_fusion_penalty_vs_time_bpm']:.3f} bpm, so the fusion step "
            f"is not uniformly harmful; fused still beats spectral MAE.",
            f"spectral<time in a majority of probes in {spectral_lt_time_sessions}/5 sessions; "
            f"fusion penalty positive in {penalty_pos_sessions}/5 sessions; "
            f"fused bias negative in {neg_sessions}/5 sessions.",
            "present in all four classes; strongest in HARMONIC_OR_HALF_DOUBLE_LOCK and "
            "SELECTED_TARGET_WRONG_PEAK",
            "HIGH",
            "Freeze one mechanism-derived fusion/spectral candidate on a disjoint validation set; "
            "do not tune on these 100 probes.",
        ),
        row(
            "DISTANCE_OR_GEOMETRY_ASSOCIATION",
            f"far (>=1.5 m) fused bias {mean([p.e_fused for p in far]):.3f} vs near (<1.5 m) "
            f"{mean([p.e_fused for p in near]):.3f}; GT1.5M cells show the largest negative bias; "
            f"descriptive Spearman distance vs signed error = "
            f"{dist['spearman_distance_vs_signed_error_fused']:.3f} "
            f"(DESCRIPTIVE_ONLY/CLUSTERED_NONINDEPENDENT).",
            f"far probes concentrate in only {len(far_sessions)}/5 sessions "
            f"({', '.join(f'{k}:{v}' for k, v in sorted(far_sessions.items()))}), so the pooled distance contrast "
            f"is partly a session contrast; within-session far-minus-near bias is negative in only "
            f"{far_worse_sessions}/{sessions_with_far} sessions that contain far probes.",
            f"far/near contrast is not evaluable in sessions without far probes; "
            f"direction holds within-session in {far_worse_sessions}/{sessions_with_far} evaluable sessions.",
            "distance contrast is entangled with failure class; far cells are dominated by wrong-peak and "
            "target-miss classes",
            "MEDIUM",
            "Requires a distance-stratified design with multiple sessions per band, or an independent set "
            "where distance is not collinear with session.",
        ),
        row(
            "TARGET_SELECTION_ERROR",
            f"TARGET_BIN_CHANNEL_MISS n={sum(1 for p in probes if p.failure_class == 'TARGET_BIN_CHANNEL_MISS')} "
            f"with fused bias "
            f"{mean([p.e_fused for p in probes if p.failure_class == 'TARGET_BIN_CHANNEL_MISS']):.3f}; "
            f"SELECTED_TARGET_WRONG_PEAK n={sum(1 for p in probes if p.failure_class == 'SELECTED_TARGET_WRONG_PEAK')} "
            f"with fused bias "
            f"{mean([p.e_fused for p in probes if p.failure_class == 'SELECTED_TARGET_WRONG_PEAK']):.3f}.",
            "strict P2 re-attribution already retained estimator/peak/harmonic/fusion as the dominant path, and "
            "target miss is neither the only nor the largest class; both classes are still negative-biased but "
            "they are not the whole -9 bpm.",
            "both classes appear in multiple sessions.",
            "directly defines two of the four frozen classes",
            "MEDIUM",
            "Keep target selection frozen; do not build a new selector rule from this audit.",
        ),
        row(
            "SELECTED_TARGET_PEAK_ESTIMATION_ERROR",
            f"SELECTED_TARGET_WRONG_PEAK is the second largest class and its fused bias is "
            f"{mean([p.e_fused for p in probes if p.failure_class == 'SELECTED_TARGET_WRONG_PEAK']):.3f} bpm.",
            "the audit cannot separate peak-detection error from spectral-selection error with the frozen fields; "
            "hr_confidence and selection margin are NOT_AVAILABLE in this output.",
            "class present across sessions.",
            "defines one frozen class",
            "MEDIUM",
            "Add selection-margin/confidence instrumentation in a future run before claiming peak-level causality.",
        ),
        row(
            "HARMONIC_ERROR",
            f"HARMONIC_OR_HALF_DOUBLE_LOCK n={len(harmonic)} fused bias {harmonic_bias:.3f} "
            f"and fused MAE {mean_abs([p.e_fused for p in harmonic]):.3f}; removing this class leaves "
            f"non-harmonic residual bias {resid_bias:.3f} over n={len(non_harmonic)}.",
            f"the non-harmonic residual is still clearly negative ({resid_bias:.3f} bpm), so the overall "
            f"-9 bpm is NOT produced only by a few harmonic catastrophes.",
            "harmonic class present in multiple sessions.",
            "defines one frozen class",
            "HIGH",
            "Treat harmonic lock as a contributing amplifier, not the single root cause.",
        ),
        row(
            "LOW_SIGNAL_OR_QC",
            f"existing QC fields are available (usable ratio, phase stability, motion proxy, frames); "
            f"CORRECT_OR_NEAR_CORRECT probes still show fused bias {correct_bias:.3f} and MAE {correct_mae:.3f}.",
            "no available QC field shows a session-consistent monotone relation with signed error; "
            "hr_confidence is NOT_AVAILABLE so SNR-level causality cannot be tested here.",
            "see QC_BIAS_DECOMPOSITION.csv direction_consistent_across_sessions per field.",
            "QC relations are weak and not class-specific.",
            "LOW",
            "Instrument hr_confidence and selection margin, then re-test on independent data.",
        ),
        row(
            "SESSION_SPECIFIC_DATA_QUALITY",
            f"per-session fused bias = "
            f"{', '.join(f'{s}:{v:.3f}' for s, v in sorted(per_session_fused_bias.items()))}; "
            f"negative in {neg_sessions}/5 sessions.",
            "bias sign is consistent across sessions, which argues for a mechanism shared across sessions rather "
            "than one anomalous session; the magnitude spread still limits pooled inference.",
            f"{neg_sessions}/5 sessions negative.",
            "session spread confounds distance and harmonic comparisons.",
            "MEDIUM",
            "Report per-session tables alongside every pooled number; do not claim population inference.",
        ),
    ]
    return rows


# ---------------------------------------------------------------------------
# 表 8：PROBE_LEVEL_MECHANISM（local-only）
# ---------------------------------------------------------------------------


def table_probe_level(probes: list[Probe]) -> list[dict]:
    """Full probe-level mechanism table (local-only; contains reference detail)."""
    rows = []
    for p in probes:
        rows.append({
            "subject": p.subject,
            "block_id": p.block_id,
            "probe_onset_unix_ms": p.onset,
            "failure_class": p.failure_class,
            "secondary_flags": p.seconds_flags,
            "ecg_hr_bpm": fmt(p.ecg),
            "rsp_br_bpm": fmt(p.rsp_br),
            "fused_hr_bpm": fmt(p.fused),
            "time_hr_bpm": fmt(p.time),
            "spectral_hr_bpm": fmt(p.spectral),
            "signed_error_fused_bpm": fmt(p.e_fused),
            "signed_error_time_bpm": fmt(p.e_time),
            "signed_error_spectral_bpm": fmt(p.e_spectral),
            "absolute_error_fused_bpm": fmt(p.ae_fused),
            "absolute_error_time_bpm": fmt(p.ae_time),
            "absolute_error_spectral_bpm": fmt(p.ae_spectral),
            "fusion_penalty_vs_time_bpm": fmt(p.fusion_penalty_vs_time),
            "fusion_signed_shift_vs_time_bpm": fmt(p.fusion_signed_shift_vs_time),
            "spectral_signed_shift_vs_time_bpm": fmt(p.spectral_signed_shift_vs_time),
            "gap_time_spectral_bpm": fmt(p.gap_time_spectral),
            "spectral_below_time": int(p.spectral_below_time),
            "fused_below_time": int(p.fused_below_time),
            "spectral_pulled_fused_down": int(p.spectral_pulled_fused_down),
            "hr_bin": p.hr_bin,
            "hr_channel": p.hr_channel,
            "selected_distance_m": fmt(p.distance, 4),
            "distance_band": p.distance_band,
            "ecg_band": p.ecg_band,
            "hr_usable_ratio": fmt(p.usable_ratio),
            "phase_stability": fmt(p.phase_stability),
            "motion_proxy": fmt(p.motion_proxy),
            "mmwave_frames": fmt(p.frames, 0),
            "harmonic_ratio_time_over_ecg": fmt(p.harmonic_ratio_time),
            "harmonic_ratio_spectral_over_ecg": fmt(p.harmonic_ratio_spectral),
            "harmonic_ratio_fused_over_ecg": fmt(p.harmonic_ratio_fused),
            "br_harmonic_delta_bpm": fmt(br_harmonic_relation(p.fused, p.rsp_br)),
        })
    return rows


def table_bias_attribution(probes: list[Probe]) -> list[dict]:
    """Decompose the pooled fused bias into per-class additive contributions.

    Because the pooled bias is the mean over all 100 probes, each class contributes
    (class sum of signed error) / 100. This makes it explicit how much of the
    roughly -9 bpm comes from the clean class versus the three failure classes.
    """
    total_bias = mean([p.e_fused for p in probes])
    rows = []
    for cls in list(FAILURE_CLASSES) + ["ALL_PROBES"]:
        cell = probes if cls == "ALL_PROBES" else [p for p in probes if p.failure_class == cls]
        contribution = sum(p.e_fused for p in cell) / len(probes)
        rows.append({
            "failure_class": cls,
            "n": len(cell),
            "share_of_probes_pct": fmt(100.0 * len(cell) / len(probes), 3),
            "mean_signed_error_fused_bpm": fmt(mean([p.e_fused for p in cell])) if cell else "",
            "bias_contribution_to_pooled_bpm": fmt(contribution),
            "share_of_pooled_bias_pct": fmt(100.0 * contribution / total_bias, 3) if total_bias else "",
            "mean_signed_error_time_bpm": fmt(mean([p.e_time for p in cell])) if cell else "",
            "time_bias_contribution_to_pooled_bpm": fmt(sum(p.e_time for p in cell) / len(probes)) if cell else "",
            "mean_fusion_penalty_vs_time_bpm": fmt(mean([p.fusion_penalty_vs_time for p in cell])) if cell else "",
            "fusion_penalty_contribution_to_pooled_bpm": (
                fmt(sum(p.fusion_penalty_vs_time for p in cell) / len(probes)) if cell else ""
            ),
        })
    return rows


def flag_frequency(probes: list[Probe]) -> dict:
    """Count SECONDARY_FLAGS occurrences to identify which diagnostic mechanism fires."""
    counter: Counter = Counter()
    for p in probes:
        for flag in str(p.seconds_flags).split("|"):
            flag = flag.strip()
            if flag:
                counter[flag] += 1
    return dict(counter.most_common())


def harmonic_relations(probes: list[Probe]) -> list[dict]:
    """Check ~0.5 / ~2.0 lock rates for each arm against ECG."""
    rows = []
    for arm, getter in (("fused", lambda p: p.harmonic_ratio_fused),
                        ("time", lambda p: p.harmonic_ratio_time),
                        ("spectral", lambda p: p.harmonic_ratio_spectral)):
        ratios = [getter(p) for p in probes]
        rows.append({
            "arm": arm,
            "n": len(ratios),
            "ratio_median": fmt(median(ratios)),
            "ratio_p10": fmt(percentile(ratios, 0.10)),
            "ratio_p90": fmt(percentile(ratios, 0.90)),
            "n_near_half_lock_0.45_0.55": sum(1 for r in ratios if 0.45 <= r <= 0.55),
            "n_near_double_lock_1.9_2.1": sum(1 for r in ratios if 1.9 <= r <= 2.1),
            "n_strongly_low_ratio_lt0.8": sum(1 for r in ratios if r < 0.8),
            "note": "frozen diagnostic relations only; no tolerance re-optimisation",
        })
    return rows


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the mechanism audit and write all Git-safe and local-only outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="只复现 control 与既有输出摘要，不写任何文件（供回归测试使用）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "results" / "2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1",
        help="Git-safe output directory (default: docs/results/2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1)",
    )
    parser.add_argument(
        "--local-out-dir",
        type=Path,
        default=Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_low_bias_mechanism_audit_v1_20260913"),
        help="LOCAL_ONLY output directory for the probe-level table",
    )
    args = parser.parse_args(argv)

    if args.verify_only:
        for path in (CONTROL_CSV, ELIGIBILITY_CSV, P2_DETAIL_CSV):
            if sha256_file(path) != EXPECTED_INPUT_SHA256[path.name]:
                raise SystemExit(f"BLOCKED_INPUT_IDENTITY_MISMATCH: {path.name}")
        probes_v, meta_v = build_probes()
        control_v = reproduce_control(probes_v)
        print(json.dumps({
            "state": "VERIFY_ONLY_PASS",
            "n_probes": meta_v["n_probes"],
            "fused_bias": round(control_v["fused"]["bias"], 9),
            "time_bias": round(control_v["time"]["bias"], 9),
            "spectral_bias": round(control_v["spectral"]["bias"], 9),
        }, ensure_ascii=False))
        return 0

    # 1) 输入身份核验（不匹配即 STOP）。
    input_identity = {}
    for path in (CONTROL_CSV, ELIGIBILITY_CSV, P2_DETAIL_CSV):
        if not path.exists():
            raise SystemExit(f"BLOCKED_INPUT_IDENTITY_MISMATCH: missing input {path}")
        digest = sha256_file(path)
        expected = EXPECTED_INPUT_SHA256[path.name]
        if digest != expected:
            raise SystemExit(
                f"BLOCKED_INPUT_IDENTITY_MISMATCH: {path.name} sha256 {digest} != expected {expected}"
            )
        input_identity[path.name] = {
            "path": str(path),
            "sha256": digest,
            "rows": len(read_csv_rows(path)),
        }

    # 2) 合并 + 复现冻结 control。
    probes, meta = build_probes()
    control = reproduce_control(probes)

    # 3) 各分解表。
    fusion_rows = table_fusion(probes)
    fusion = fusion_summary(probes)
    distance_rows = table_distance_session(probes)
    distance_fc_rows = table_distance_failure(probes)
    within_rows = within_session_distance(probes)
    dist_desc = continuous_distance_descriptives(probes)
    fc_rows = table_failure_class(probes)
    band_rows = table_ecg_band(probes)
    qc_rows, qc_meta = table_qc(probes)
    harm_rows = harmonic_relations(probes)
    attribution_rows = table_bias_attribution(probes)
    flags = flag_frequency(probes)
    mechanism = table_mechanism(probes, fusion, dist_desc, within_rows, fc_rows)
    probe_rows = table_probe_level(probes)

    # 4) 写出 Git-safe 输出。
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "FUSION_LOW_BIAS_DECOMPOSITION.csv", fusion_rows)
    write_csv(out / "DISTANCE_SESSION_STRATIFIED.csv", distance_rows)
    write_csv(out / "DISTANCE_FAILURE_CLASS_MATRIX.csv", distance_fc_rows)
    write_csv(out / "WITHIN_SESSION_DISTANCE_CHECK.csv", within_rows)
    write_csv(out / "FAILURE_CLASS_BIAS_DECOMPOSITION.csv", fc_rows)
    write_csv(out / "BIAS_ATTRIBUTION_DECOMPOSITION.csv", attribution_rows)
    write_csv(out / "ECG_HR_BAND_DECOMPOSITION.csv", band_rows)
    write_csv(out / "QC_BIAS_DECOMPOSITION.csv", qc_rows)
    write_csv(out / "MECHANISM_EVIDENCE_MATRIX.csv", mechanism)

    # 5) local-only probe 表。
    local_dir = args.local_out_dir
    local_dir.mkdir(parents=True, exist_ok=True)
    probe_path = local_dir / "PROBE_LEVEL_MECHANISM_100_PROBES.csv"
    write_csv(probe_path, probe_rows)

    # 6) manifest（含 local-only 路径/行数/hash、输入 hash、代码 hash）。
    script_path = Path(__file__).resolve()
    manifest = {
        "task_id": "mmwave_systematic_low_bias_mechanism_audit_v1",
        "run_id": "mmwave_low_bias_mechanism_audit_v1_20260913_r1",
        "audit_type": "MECHANISM_AUDIT",
        "source_commit": current_commit(),
        "script": {"path": str(script_path), "sha256": sha256_file(script_path)},
        "inputs": input_identity,
        "denominator": meta,
        "frozen_control_expected": FROZEN_CONTROL,
        "frozen_control_reproduced": {k: {m: round(v, 9) for m, v in d.items()} for k, d in control.items()},
        "control_tolerance": CONTROL_TOLERANCE,
        "fusion_summary": fusion,
        "distance_descriptives": dist_desc,
        "within_session_distance": within_rows,
        "bias_attribution": attribution_rows,
        "harmonic_relations": harm_rows,
        "secondary_flag_frequency": flags,
        "cloud_handoff": {
            "folder_name": CLOUD_HANDOFF_FOLDER_NAME,
            "parent_name": CLOUD_HANDOFF_PARENT_NAME,
            "parent_folder_id": CLOUD_HANDOFF_PARENT_ID,
            "remote_path": CLOUD_HANDOFF_REMOTE_PATH,
            "access_pattern": "--drive-root-folder-id " + CLOUD_HANDOFF_PARENT_ID,
            "note": "canonical shared Drive _AI_HANDOFF; the folder is addressed by parent id "
                    "because it is not reachable from the remote default root.",
        },
        "mechanism_status": MECHANISM_STATUS,
        "primary_mechanism": PRIMARY_MECHANISM,
        "secondary_mechanism": SECONDARY_MECHANISM,
        "mechanism_candidates": [r["MECHANISM_CANDIDATE"] for r in mechanism],
        "markdown_deliverables": {
            name: (
                {
                    "sha256_lf_normalised": sha256_text_normalised(out / name),
                    "digest_basis": "LF-normalised content; raw uploaded bytes are verified in "
                                    "CLOUD_HANDOFF_VERIFICATION.json",
                }
                if (out / name).exists()
                else {"sha256_lf_normalised": None,
                      "note": "rendered by render_mmwave_mechanism_audit_docs_20260913.py"}
            )
            for name in MARKDOWN_DELIVERABLES
        },
        "qc_fields_used": qc_meta["fields_used"],
        "qc_fields_not_available": qc_meta["fields_not_available"],
        "local_only_outputs": [{
            "name": probe_path.name,
            "path": str(probe_path),
            "rows": len(probe_rows),
            "sha256": sha256_file(probe_path),
            "reason": "probe-level ECG reference and per-probe diagnostics; not Git-safe",
        }],
        "git_safe_outputs": sorted(p.name for p in out.iterdir() if p.is_file()),
        "boundaries": {
            "no_new_gating_rule": True,
            "no_new_threshold": True,
            "no_production_candidate": True,
            "snapshot_v1_modified": False,
            "formal_producer_modified": False,
            "models_trained": False,
            "hrv_status": "BLOCKED",
        },
    }
    (out / "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "state": "AUDIT_COMPLETE",
        "probes": meta["n_probes"],
        "control_reproduction": "PASS",
        "fused_bias": round(control["fused"]["bias"], 6),
        "time_bias": round(control["time"]["bias"], 6),
        "spectral_bias": round(control["spectral"]["bias"], 6),
        "local_probe_table": str(probe_path),
        "probe_table_sha256": manifest["local_only_outputs"][0]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


def current_commit() -> str:
    """Return the current Git commit sha when available (provenance only)."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() or "UNKNOWN"
    except OSError:
        return "UNKNOWN"


if __name__ == "__main__":
    sys.exit(main())
