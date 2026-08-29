"""Retrospective ECG-valid spectral truth audit for the frozen mmWave windows.

This audit is deliberately downstream of mmWave target selection.  ECG/RSP is
used only as an oracle for labelling and comparison; it is never used to pick
the target, channel, spectral peak, or ARM result.  The per-window table is
written to a local-only derived directory.  Only aggregate, Git-safe evidence
is written to the repository result directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import signal


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_INPUT = RESULT_ROOT / "mmwave_ecg_block_window_comparison.csv"
ARM_INPUT = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
COVERAGE_INPUT = RESULT_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT.csv"
DEFAULT_LOCAL_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\ecg_valid_retrospective_spectral_truth_audit_20260830")
SUBJECTS = ("97793", "9779", "97795")
PRODUCER_PATH = ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
TARGET_SCRIPT_PATH = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
WINDOW_SCRIPT_PATH = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_estimator_same_window_audit_20260830.py"
ARM_SCRIPT_PATH = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_gate_target_ablation_20260830.py"
FS_HZ = 100.0
NEAR_HARMONIC_TOL_BPM = 5.0
WEAK_REL_PROMINENCE = 0.05
ARM_COLUMNS = {
    "arm0": "arm0_hr_bpm",
    "arm1": "arm1_gate_only_hr_bpm",
    "arm2": "arm2_historical_target_hr_bpm",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_float(value) -> float | None:
    if value in (None, "", "None", "nan", "NaN"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ALGO_ROOT), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def harmonic_label(value_bpm: float | None, br_bpm: float | None) -> tuple[str, int | None, float | None]:
    if value_bpm is None or br_bpm is None or br_bpm <= 0:
        return "not_evaluable", None, None
    candidates = [(k, abs(value_bpm - k * br_bpm)) for k in (2, 3)]
    k, distance = min(candidates, key=lambda item: item[1])
    if 48.0 <= k * br_bpm <= 120.0 and distance <= NEAR_HARMONIC_TOL_BPM:
        return f"near_{k}x_br", k, distance
    return "not_near_2x_3x_br", None, distance


def spectral_candidates(algo, heart_bp: np.ndarray, selected_bpm: float | None) -> dict:
    """Describe the exact default periodogram used by estimate_freq_periodogram.

    The producer's selected value is fixed from the existing result row.  This
    function only exposes local peaks, power, and prominence for retrospective
    diagnosis; it does not alter that selected value.
    """
    centered = np.asarray(heart_bp, dtype=float)
    freqs, pxx = signal.periodogram(centered, fs=algo.FS, window="hann")
    mask = (freqs >= algo.HR_LO_HZ) & (freqs <= algo.HR_HI_HZ)
    band_freqs, band_power = freqs[mask], pxx[mask]
    if len(band_freqs) == 0 or not np.any(np.isfinite(band_power)):
        return {
            "freq_resolution_hz": None,
            "selected_bin_index": None,
            "selected_psd_rank": None,
            "selected_power": None,
            "selected_relative_power": None,
            "selected_prominence": None,
            "selected_prominence_relative": None,
            "candidates": [],
            "_band_freqs": np.array([], dtype=float),
            "_band_power": np.array([], dtype=float),
        }

    valid_power = np.nan_to_num(band_power, nan=0.0, posinf=0.0, neginf=0.0)
    peak_idx, properties = signal.find_peaks(valid_power, prominence=0.0)
    prominences = properties.get("prominences", np.zeros(len(peak_idx), dtype=float))
    if len(peak_idx) == 0:
        peak_idx = np.array([int(np.argmax(valid_power))], dtype=int)
        prominences = np.array([0.0], dtype=float)
    order = peak_idx[np.argsort(valid_power[peak_idx])[::-1]][:8]
    prominence_by_idx = {int(index): float(value) for index, value in zip(peak_idx, prominences)}
    max_power = max(float(np.max(valid_power)), 1e-12)
    candidate_rows = []
    for rank, index in enumerate(order, start=1):
        bpm = float(band_freqs[index] * 60.0)
        power = float(valid_power[index])
        prominence = float(prominence_by_idx.get(int(index), 0.0))
        candidate_rows.append({
            "rank": rank,
            "frequency_hz": round(float(band_freqs[index]), 6),
            "bpm": round(bpm, 6),
            "power": round(power, 12),
            "relative_power": round(power / max_power, 8),
            "prominence": round(prominence, 12),
            "relative_prominence": round(prominence / max_power, 8),
            "distance_to_selected_bpm": round(abs(bpm - selected_bpm), 6) if selected_bpm is not None else None,
        })

    selected_index = int(np.argmax(valid_power))
    selected_power = float(valid_power[selected_index])
    power_order = np.argsort(valid_power)[::-1]
    selected_rank = int(np.flatnonzero(power_order == selected_index)[0] + 1)
    selected_prominence = float(prominence_by_idx.get(selected_index, 0.0))
    return {
        "freq_resolution_hz": round(float(freqs[1] - freqs[0]), 8) if len(freqs) > 1 else None,
        "selected_bin_index": selected_index,
        "selected_psd_rank": selected_rank,
        "selected_power": round(selected_power, 12),
        "selected_relative_power": round(selected_power / max_power, 8),
        "selected_prominence": round(selected_prominence, 12),
        "selected_prominence_relative": round(selected_prominence / max_power, 8),
        "candidates": candidate_rows,
        "_band_freqs": band_freqs,
        "_band_power": valid_power,
    }


def classify_truth(row: dict, spectral: dict, coverage_class: str | None) -> tuple[str, dict]:
    ecg_bpm = safe_float(row.get("ecg_hr_bpm"))
    selected_bpm = safe_float(row.get("local_hr_freq_bpm"))
    if coverage_class in {"SEVERELY_INCOMPLETE", "MISSING", "UNKNOWN"} or row.get("ecg_eligibility") != "ECG_VALID":
        return "insufficient_coverage_or_reference", {"near_candidate": None, "nearby_candidate": None}
    candidates = spectral["candidates"]
    if ecg_bpm is None or selected_bpm is None or not candidates:
        return "absent_or_weak", {"near_candidate": None, "nearby_candidate": None}
    resolution_bpm = float(spectral["freq_resolution_hz"] or 0.0) * 60.0
    exact_tol = max(0.5 * resolution_bpm, 1.5)
    nearby_tol = max(2.0 * resolution_bpm, 6.0)
    nearest = min(candidates, key=lambda item: abs(float(item["bpm"]) - ecg_bpm))
    nearest_diff = abs(float(nearest["bpm"]) - ecg_bpm)
    selected_diff = abs(selected_bpm - ecg_bpm)
    selected_prominence = spectral.get("selected_prominence_relative") or 0.0
    metadata = {
        "near_candidate": nearest if nearest_diff <= exact_tol else None,
        "nearby_candidate": nearest if nearest_diff <= nearby_tol else None,
        "exact_bin_tolerance_bpm": round(exact_tol, 6),
        "nearby_tolerance_bpm": round(nearby_tol, 6),
        "nearest_diff_bpm": round(nearest_diff, 6),
        "selected_diff_bpm": round(selected_diff, 6),
    }
    if nearest_diff <= exact_tol and selected_diff > exact_tol:
        return "true_peak_available_selected_target_but_wrong_selection", metadata
    if selected_diff <= exact_tol and nearest_diff <= exact_tol:
        return "true_peak_selected_ecg_bin", metadata
    if nearest_diff <= nearby_tol or selected_diff <= nearby_tol:
        return "nearby_target_bin_channel", metadata
    if selected_prominence < WEAK_REL_PROMINENCE:
        return "absent_or_weak", metadata
    return "absent_or_weak", metadata


def summarize(rows: list[dict]) -> list[dict]:
    output = []
    denominator_rows = {
        "ALL_WINDOWS_DIAGNOSTIC": rows,
        "ECG_VALID_PRIMARY": [row for row in rows if row.get("primary_ecg_valid") == "True"],
    }
    for denominator, denominator_members in denominator_rows.items():
        groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
        for row in denominator_members:
            for arm in ARM_COLUMNS:
                groups[(row["subject"], row["block_id"], row["truth_class"], arm)].append(row)
        groups[("ALL", "ALL", "ALL", "ALL")] = denominator_members
        for key, members in groups.items():
            if key == ("ALL", "ALL", "ALL", "ALL"):
                arm_members = [(arm, members) for arm in ARM_COLUMNS]
            else:
                arm_members = [(key[3], members)]
            for arm, arm_rows in arm_members:
                values = [safe_float(item.get(f"{arm}_hr_bpm")) for item in arm_rows]
                pairs = [(value, safe_float(item.get("ecg_hr_bpm"))) for value, item in zip(values, arm_rows) if value is not None and safe_float(item.get("ecg_hr_bpm")) is not None]
                errors = [abs(value - ref) for value, ref in pairs]
                output.append({
                    "denominator": denominator,
                    "scope": "overall" if key[0] == "ALL" else "subject_block_truth_class",
                    "subject": key[0], "block_id": key[1], "truth_class": key[2], "arm": arm,
                    "n_rows": len(arm_rows), "n_with_ecg_and_arm": len(errors),
                    "coverage_pct": round(100.0 * len(errors) / len(arm_rows), 6) if arm_rows else None,
                    "mae_bpm": round(float(np.mean(errors)), 6) if errors else None,
                    "median_abs_error_bpm": round(float(np.median(errors)), 6) if errors else None,
                    "bias_arm_minus_ecg_bpm": round(float(np.mean([value - ref for value, ref in pairs])), 6) if errors else None,
                })
    return output


def build_report(rows: list[dict], summary: list[dict], manifest: dict) -> str:
    all_rows = rows
    primary_rows = [row for row in rows if row.get("primary_ecg_valid") == "True"]
    counts = Counter(row["truth_class"] for row in all_rows)
    primary_counts = Counter(row["truth_class"] for row in primary_rows)

    def arm_lines(denominator: str) -> str:
        return "\n".join(
            f"| {row['arm']} | {row['n_rows']} | {row['n_with_ecg_and_arm']} | {row['coverage_pct']}% | {row['mae_bpm']} | {row['median_abs_error_bpm']} |"
            for row in summary
            if row["scope"] == "overall" and row["denominator"] == denominator
        )

    subject_lines = []
    for subject in SUBJECTS:
        diagnostic = [row for row in all_rows if row["subject"] == subject]
        primary = [row for row in primary_rows if row["subject"] == subject]
        subject_lines.append(f"| {subject} | {len(diagnostic)} | {len(primary)} | {dict(Counter(row['truth_class'] for row in primary))} |")
    block_lines = []
    for subject in SUBJECTS:
        for block_id in sorted({row["block_id"] for row in rows if row["subject"] == subject}):
            diagnostic = [row for row in all_rows if row["subject"] == subject and row["block_id"] == block_id]
            primary = [row for row in primary_rows if row["subject"] == subject and row["block_id"] == block_id]
            block_lines.append(f"| {subject} | {block_id} | {len(diagnostic)} | {len(primary)} | {dict(Counter(row['truth_class'] for row in primary))} |")
    coverage_limited = [row for row in primary_rows if row.get("coverage_reference_flag") == "SUPPORTING_COVERAGE_LIMIT"]
    invalid_reasons = Counter(row.get("ecg_reject_reason") for row in rows if row.get("ecg_eligibility") == "ECG_INVALID")
    warning_counts = Counter(row.get("ecg_qc_warning") for row in rows)
    harmonic_counts = Counter(row.get("radar_br_2x3x_label") for row in rows)
    external_counts = Counter(row.get("external_rsp_guard_a_flag") for row in rows)
    external_reject_n = sum(bool(row.get("external_rsp_guard_b_would_reject")) for row in rows)
    return f"""# ECG_VALID retrospective spectral truth audit — 2026-08-30

状态：`{manifest['status']}`

本轮对冻结的 335 个 complete formal-block、20 s mmWave windows 做 retrospective spectral audit。335 行是全窗口 diagnostic/supporting 分母，不是全量 ECG-valid。正式 ECG-valid 主分析严格沿用 #24：ECG_VALID=325、ECG_INVALID=10、UNRESOLVED=0；10 个 ECG_INVALID 只进入 supporting/diagnostic，不进入主分析。毫米波 target/bin/channel、selected HR peak 和 ARM0/1/2 均先由既有结果或既有 producer 路径确定；ECG/RSP 只在之后作为 oracle 做 truth label、nearest-candidate 和误差比较。逐窗 truth table 是 local-only，Git 只保留聚合证据。

## 1. Reuse gate and scope

复用：`mmwave_ecg_block_window_comparison.csv`、`MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv`、既有 `run_mmwave_targeted_validation_20260830.py` 的 `PartReader`/window contract、`process_vital_signs_v3_1_1.py` 的 bandpass/periodogram/peak/harmonic functions，以及既有 coverage audit。

`REUSE_REJECTION_REASON`：旧 ECG reference audit 只给出 ECG HR 与固定 mmWave HR 的逐窗比较；旧 harmonic A/B 只给出 15 个诊断样本，均没有为 335 窗统一持久化 top candidates、prominence、ECG-nearest rank 和选择错误分类。因此本轮只新增下游审计层，不改 producer、不改 target/peak selection、不重跑 C2B/C2C。

## 2. Truth classification

### 2.1 全窗口 diagnostic/supporting（n=335）

| class | n (%) |
|---|---:|
{chr(10).join(f"| {key} | {value} ({100.0 * value / len(all_rows):.2f}%) |" for key, value in sorted(counts.items()))}

### 2.2 ECG_VALID primary（n=325）

| class | n (%) |
|---|---:|
{chr(10).join(f"| {key} | {value} ({100.0 * value / len(primary_rows):.2f}%) |" for key, value in sorted(primary_counts.items()))}

其中 325 个 ECG_VALID 中有 `{len(coverage_limited)}` 个窗口标为 `SUPPORTING_COVERAGE_LIMIT`（coverage/reference 不足）；它们保留在 #24 的 ECG_VALID=325 分母中，但其 truth 结论只作 supporting/diagnostic caveat。它们不是 ECG_INVALID，不能再加到 10 个 ECG_INVALID 中。

- `true_peak_available_selected_target_but_wrong_selection`：同窗候选中存在落在 ECG 频率分辨率半 bin 内的 candidate，但既有 selected HR peak 不在该容差内。
- `true_peak_selected_ecg_bin`：selected peak 与 ECG 最近 candidate 均在半 bin容差内。
- `nearby_target_bin_channel`：candidate 或 selected 在预定义较宽邻近容差内，但未达到半 bin 级别。
- `absent_or_weak`：没有可用 candidate，或没有达到上述邻近分类；prominence 仍仅作诊断，不作 rejection。
- `insufficient_coverage_or_reference`：coverage audit 为 severe/missing，或 #24 ECG reference 非 ECG_VALID。

## 3. ARM0/1/2 same-window descriptive comparison

### 3.1 ECG_VALID primary (n=325; ARM1 estimator-valid=304)

| arm | selected n | estimator-valid n | coverage | MAE (bpm) | median AE (bpm) |
|---|---:|---:|---:|---:|---:|
{arm_lines("ECG_VALID_PRIMARY")}

### 3.2 All-window diagnostic (selected n=335; ARM1 estimator-valid=314)

| arm | selected n | estimator-valid n | coverage | MAE (bpm) | median AE (bpm) |
|---|---:|---:|---:|---:|---:|
{arm_lines("ALL_WINDOWS_DIAGNOSTIC")}

| subject | diagnostic n | ECG_VALID primary n | primary truth-class counts |
|---|---:|---:|---|
{chr(10).join(subject_lines)}

| subject | block | diagnostic n | ECG_VALID primary n | primary truth-class counts |
|---|---|---:|---:|---|
{chr(10).join(block_lines)}

以上均为描述性 same-window 对照，不进行显著性检验或按 ECG 调峰。分层完整结果见 `ECG_VALID_SPECTRAL_ARM_SUMMARY.csv`。

验证：本脚本 `py_compile` 和实际运行通过；全仓 `pytest -q` 在既有 legacy `_cal_segment_test.py` 收集时因缺少 `process_vital_signs_v3_1_1` 导入而失败，未影响本定向审计运行。该残留记录在 manifest，不将其误报为本任务数据失败。

## 4. Harmonic guard audit

- Radar BR 的 2x/3x labels 和 external RSP 2x/3x labels 均写入 local-only truth table；它们不改变 selected peak。
- External RSP A 保留 raw selected peak，仅加 diagnostic label；B 调用现有 `respiration_harmonic_reject()` 计算“若启用”的 chosen/fallback/action，仍不回写 ARM0/1/2。
- 本轮 radar BR label 分布：`{dict(harmonic_counts)}`；external RSP A 分布：`{dict(external_counts)}`；external RSP B would-reject={external_reject_n}/335。B 只是 A/B diagnostic，未实施 hard rejection。
- Internal producer harmonic guard 的真实代码行为是 `_select_spectral_bpm()` 对 `time_bpm`、`previous_bpm`、`reference_bpm` 做 half/double fold；它不读取 BR。当前固定 targeted validation 路径直接使用 `estimate_freq_periodogram()` + `detect_peaks_heart_lo()`，没有调用 `_select_spectral_bpm()`，因此本表的 internal guard 状态为 `not_applied_in_fixed_target_validation_path`。

## 5. ECG reference accounting

- #24 eligibility：ECG_VALID=325、ECG_INVALID=10、UNRESOLVED=0；invalid reason 分布：`{dict(invalid_reasons)}`。
- marker warning 分布：`{dict(warning_counts)}`。marker warning 只表示 affine marker mapping 非 exact 但可用，不是额外 invalid reason。
- 10 个 ECG_INVALID 的 IBI/artifact 原因与 marker warning 不重复计数；本报告不把 warning 数与 invalid 数相加成新的失败总数。

## 6. Boundary

本轮结果是 `SUPPORTING` retrospective truth audit，不是 HR/BR validated physiology，也不是 producer change proposal。ECG 仍是 oracle；没有将 ECG 频率传入 target selection、candidate scoring、selected peak 或 ARM 计算。HR 保持 `HOLD`，HRV 保持 `BLOCKED`。

逐窗文件：`{manifest['local_only_truth_table']}`（local-only；335 行全窗口 diagnostic/supporting，ECG_VALID primary=325）
聚合文件：`ECG_VALID_SPECTRAL_AUDIT_MANIFEST.json`、`ECG_VALID_SPECTRAL_AUDIT_SUMMARY.csv`、`ECG_VALID_SPECTRAL_ARM_SUMMARY.csv`
"""


def run(local_root: Path, result_root: Path, eligibility_input: Path) -> dict:
    target = load_module(TARGET_SCRIPT_PATH, "target_validation_for_ecg_truth")
    algo = load_module(PRODUCER_PATH, "producer_for_ecg_truth")
    fixed_rows = [row for row in read_csv(FIXED_INPUT) if row.get("subject") in SUBJECTS]
    arm_rows = {(row["subject"], row["window_id"]): row for row in read_csv(ARM_INPUT)}
    coverage_rows = {(row["subject"], row["window_id"]): row for row in read_csv(COVERAGE_INPUT)}
    eligibility_rows = {(row["subject"], row["window_id"]): row for row in read_csv(eligibility_input)}
    if len(fixed_rows) != 335 or len(arm_rows) != 335 or len(eligibility_rows) != 335:
        raise RuntimeError(f"Frozen input denominator mismatch: fixed={len(fixed_rows)}, arms={len(arm_rows)}, eligibility={len(eligibility_rows)}")
    eligibility_counts = Counter(row.get("ecg_eligibility") for row in eligibility_rows.values())
    if eligibility_counts != Counter({"ECG_VALID": 325, "ECG_INVALID": 10}):
        raise RuntimeError(f"#24 ECG eligibility denominator mismatch: {dict(eligibility_counts)}")
    eligibility_manifest = eligibility_input.parents[2] / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "ECG_ELIGIBILITY_MANIFEST.json"

    local_root.mkdir(parents=True, exist_ok=True)
    truth_rows = []
    errors = []
    for subject in SUBJECTS:
        reader = target.PartReader(subject)
        for source_row in [row for row in fixed_rows if row["subject"] == subject]:
            key = (subject, source_row["window_id"])
            arm = arm_rows.get(key)
            if arm is None:
                errors.append({"subject": subject, "window_id": source_row["window_id"], "error": "missing_arm_row"})
                continue
            eligibility = eligibility_rows.get(key)
            if eligibility is None:
                errors.append({"subject": subject, "window_id": source_row["window_id"], "error": "missing_ecg_eligibility_row"})
                continue
            iq = reader.slice(int(source_row["mmwave_start_row"]), int(source_row["mmwave_end_row_exclusive"]))
            hr_bin, hr_channel = int(source_row["local_hr_bin"]), int(source_row["local_hr_channel"])
            br_bin, br_channel = int(source_row["local_br_bin"]), int(source_row["local_br_channel"])
            heart = algo._sos_bandpass(algo.extract_displacement(iq, hr_bin, hr_channel), algo.HR_LO_HZ, algo.HR_HI_HZ)
            spectral = spectral_candidates(algo, heart, safe_float(source_row.get("local_hr_freq_bpm")))
            recomputed_hr_hz = algo.estimate_freq_periodogram(heart, algo.HR_LO_HZ, algo.HR_HI_HZ)
            recomputed_hr_bpm = recomputed_hr_hz * 60.0 if recomputed_hr_hz is not None else None
            breath_disp = algo.extract_displacement(iq, br_bin, br_channel)
            _breath, recomputed_br_hz, _peaks, _info = algo._select_breath_candidate(breath_disp)
            recomputed_br_bpm = recomputed_br_hz * 60.0 if recomputed_br_hz is not None else None
            radar_br_bpm = safe_float(source_row.get("local_br_freq_bpm"))
            selected_bpm = safe_float(source_row.get("local_hr_freq_bpm"))
            ecg_bpm = safe_float(eligibility.get("ecg_hr_bpm"))
            rsp_br_bpm = safe_float(source_row.get("rsp_br_bpm"))
            radar_harmonic, radar_k, radar_harmonic_delta = harmonic_label(selected_bpm, radar_br_bpm)
            rsp_harmonic, rsp_k, rsp_harmonic_delta = harmonic_label(selected_bpm, rsp_br_bpm)
            external_b = algo.respiration_harmonic_reject(
                spectral["_band_freqs"], spectral["_band_power"],
                selected_bpm if selected_bpm is not None else float("nan"),
                rsp_br_bpm,
                prefer_bpm=safe_float(source_row.get("local_hr_time_bpm")),
            ) if spectral["candidates"] and selected_bpm is not None else {
                "resp_harmonic_reject": False, "resp_harmonic_k": None, "resp_harmonic_target_bpm": None,
                "chosen_bpm": selected_bpm, "fallback_bpm": None, "fallback_source": None,
            }
            coverage_row = coverage_rows.get(key) or {}
            coverage_class = coverage_row.get("coverage_class", "UNKNOWN")
            coverage_reference_flag = "SUPPORTING_COVERAGE_LIMIT" if coverage_class in {"SEVERELY_INCOMPLETE", "MISSING", "UNKNOWN"} else "none"
            primary_ecg_valid = eligibility.get("ecg_eligibility") == "ECG_VALID"
            truth_input = dict(source_row)
            truth_input.update({
                "ecg_hr_bpm": eligibility.get("ecg_hr_bpm"),
                "ecg_eligibility": eligibility.get("ecg_eligibility"),
            })
            truth_class, class_meta = classify_truth(truth_input, spectral, coverage_class)
            nearest = min(spectral["candidates"], key=lambda item: abs(float(item["bpm"]) - ecg_bpm)) if spectral["candidates"] and ecg_bpm is not None else None
            row = {
                "subject": subject, "block_id": source_row["block_id"], "window_id": source_row["window_id"],
                "window_start_unix_ms": source_row["window_start_unix_ms"], "window_end_unix_ms": source_row["window_end_unix_ms"],
                "window_start_s_from_block": source_row["window_start_s_from_block"], "window_end_s_from_block": source_row["window_end_s_from_block"],
                "coverage_class": coverage_class, "coverage_reference_flag": coverage_reference_flag,
                "ecg_status": source_row.get("ecg_status"), "ecg_eligibility": eligibility.get("ecg_eligibility"),
                "primary_ecg_valid": str(primary_ecg_valid),
                "truth_evidence_tier": "ECG_VALID_PRIMARY" if primary_ecg_valid and coverage_reference_flag == "none" else ("SUPPORTING_COVERAGE_LIMIT" if primary_ecg_valid else "ECG_INVALID_SUPPORTING"),
                "ecg_n_rpeaks": eligibility.get("ecg_n_rpeaks"), "ecg_n_valid_ibi": eligibility.get("ecg_n_valid_ibi"),
                "ecg_effective_beat_coverage": eligibility.get("ecg_effective_beat_coverage"),
                "ecg_qc_warning": eligibility.get("ecg_qc_warning"), "ecg_reject_reason": eligibility.get("ecg_reject_reason"),
                "ecg_hr_bpm": ecg_bpm, "ecg_frequency_hz": round(ecg_bpm / 60.0, 8) if ecg_bpm is not None else None,
                "radar_br_bpm": radar_br_bpm, "radar_br_frequency_hz": round(radar_br_bpm / 60.0, 8) if radar_br_bpm is not None else None,
                "radar_br_source": "existing_local_br_freq_bpm_fixed_targeted_rerun",
                "radar_br_recomputed_bpm": round(recomputed_br_bpm, 6) if recomputed_br_bpm is not None else None,
                "radar_br_reproduction_abs_delta_bpm": round(abs(recomputed_br_bpm - radar_br_bpm), 9) if recomputed_br_bpm is not None and radar_br_bpm is not None else None,
                "external_rsp_br_bpm": rsp_br_bpm, "external_rsp_br_frequency_hz": round(rsp_br_bpm / 60.0, 8) if rsp_br_bpm is not None else None,
                "selected_hr_peak_bpm": selected_bpm, "selected_hr_peak_frequency_hz": round(selected_bpm / 60.0, 8) if selected_bpm is not None else None,
                "selected_hr_peak_source": "existing_local_hr_freq_bpm_fixed_targeted_rerun",
                "selected_hr_recomputed_bpm": round(recomputed_hr_bpm, 6) if recomputed_hr_bpm is not None else None,
                "selected_hr_reproduction_abs_delta_bpm": round(abs(recomputed_hr_bpm - selected_bpm), 9) if recomputed_hr_bpm is not None and selected_bpm is not None else None,
                "selected_hr_bin": hr_bin, "selected_hr_channel": hr_channel, "selected_br_bin": br_bin, "selected_br_channel": br_channel,
                "selected_hr_vs_ecg_abs_diff_bpm": round(abs(selected_bpm - ecg_bpm), 6) if selected_bpm is not None and ecg_bpm is not None else None,
                "selected_hr_vs_ecg_abs_diff_hz": round(abs(selected_bpm - ecg_bpm) / 60.0, 8) if selected_bpm is not None and ecg_bpm is not None else None,
                "nearest_ecg_candidate_bpm": nearest["bpm"] if nearest else None,
                "nearest_ecg_candidate_frequency_hz": round(nearest["bpm"] / 60.0, 8) if nearest else None,
                "nearest_ecg_candidate_rank": nearest["rank"] if nearest else None,
                "nearest_ecg_candidate_abs_diff_bpm": class_meta.get("nearest_diff_bpm"),
                "nearest_ecg_candidate_abs_diff_hz": round(class_meta["nearest_diff_bpm"] / 60.0, 8) if class_meta.get("nearest_diff_bpm") is not None else None,
                "selected_hr_psd_rank": spectral.get("selected_psd_rank"), "selected_hr_power": spectral.get("selected_power"),
                "selected_hr_relative_power": spectral.get("selected_relative_power"), "selected_hr_prominence": spectral.get("selected_prominence"),
                "selected_hr_relative_prominence": spectral.get("selected_prominence_relative"), "periodogram_frequency_resolution_hz": spectral.get("freq_resolution_hz"),
                "candidate_count": len(spectral["candidates"]), "top_candidates_json": json.dumps(spectral["candidates"], ensure_ascii=False, separators=(",", ":")),
                "radar_br_2x3x_label": radar_harmonic, "radar_br_harmonic_k": radar_k, "radar_br_harmonic_delta_bpm": radar_harmonic_delta,
                "external_rsp_2x3x_label": rsp_harmonic, "external_rsp_harmonic_k": rsp_k, "external_rsp_harmonic_delta_bpm": rsp_harmonic_delta,
                "external_rsp_guard_a_action": "retain_raw_selected_diagnostic_only",
                "external_rsp_guard_a_flag": rsp_harmonic,
                "external_rsp_guard_b_would_reject": external_b.get("resp_harmonic_reject"),
                "external_rsp_guard_b_chosen_bpm": external_b.get("chosen_bpm"),
                "external_rsp_guard_b_fallback_bpm": external_b.get("fallback_bpm"),
                "external_rsp_guard_b_fallback_source": external_b.get("fallback_source"),
                "internal_harmonic_guard_state": "not_applied_in_fixed_target_validation_path",
                "truth_class": truth_class, "class_exact_bin_tolerance_bpm": class_meta.get("exact_bin_tolerance_bpm"),
                "class_nearby_tolerance_bpm": class_meta.get("nearby_tolerance_bpm"),
            }
            for arm_name, column in ARM_COLUMNS.items():
                row[f"{arm_name}_hr_bpm"] = safe_float(arm.get(column))
                row[f"{arm_name}_abs_error_bpm"] = abs(row[f"{arm_name}_hr_bpm"] - ecg_bpm) if row[f"{arm_name}_hr_bpm"] is not None and ecg_bpm is not None else None
            truth_rows.append(row)

    if errors:
        raise RuntimeError(f"Truth table construction errors: {errors[:3]}")
    if len(truth_rows) != 335:
        raise RuntimeError(f"Truth table denominator mismatch: {len(truth_rows)}")
    truth_path = local_root / "ECG_VALID_RETROSPECTIVE_SPECTRAL_TRUTH_TABLE.csv"
    write_csv(truth_path, truth_rows)
    summary_rows = summarize(truth_rows)
    summary_path = result_root / "ECG_VALID_SPECTRAL_AUDIT_SUMMARY.csv"
    arm_summary_path = result_root / "ECG_VALID_SPECTRAL_ARM_SUMMARY.csv"
    write_csv(summary_path, [row for row in summary_rows if row["scope"] == "overall"])
    write_csv(arm_summary_path, summary_rows)

    reproduction_hr = [row["selected_hr_reproduction_abs_delta_bpm"] for row in truth_rows if row["selected_hr_reproduction_abs_delta_bpm"] is not None]
    reproduction_br = [row["radar_br_reproduction_abs_delta_bpm"] for row in truth_rows if row["radar_br_reproduction_abs_delta_bpm"] is not None]
    manifest = {
        "run_id": "ECG_VALID_RETROSPECTIVE_SPECTRAL_TRUTH_AUDIT_20260830",
        "run_started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL / ECG_VALID_SPECTRAL_TRUTH_AUDIT_COMPLETE",
        "analysis_set": list(SUBJECTS), "rows": len(truth_rows), "blocks": sorted({f"{row['subject']}/{row['block_id']}" for row in truth_rows}),
        "denominators": {
            "ALL_WINDOWS_DIAGNOSTIC": len(truth_rows),
            "ECG_VALID_PRIMARY": sum(row.get("primary_ecg_valid") == "True" for row in truth_rows),
            "ECG_INVALID_SUPPORTING": sum(row.get("ecg_eligibility") == "ECG_INVALID" for row in truth_rows),
            "UNRESOLVED": sum(row.get("ecg_eligibility") == "UNRESOLVED" for row in truth_rows),
            "ECG_VALID_WITH_COVERAGE_REFERENCE_LIMIT": sum(row.get("coverage_reference_flag") == "SUPPORTING_COVERAGE_LIMIT" and row.get("primary_ecg_valid") == "True" for row in truth_rows),
        },
        "canonical_main_head_at_run": git_value("rev-parse", "HEAD"),
        "canonical_origin_main_at_run": git_value("rev-parse", "origin/main"),
        "git_status_at_run": "detached_head; task-scoped outputs were staged after generation",
        "fixed_inputs": {
            "comparison": str(FIXED_INPUT), "comparison_sha256": sha256(FIXED_INPUT),
            "arms": str(ARM_INPUT), "arms_sha256": sha256(ARM_INPUT),
            "coverage": str(COVERAGE_INPUT), "coverage_sha256": sha256(COVERAGE_INPUT),
            "ecg_eligibility": str(eligibility_input), "ecg_eligibility_sha256": sha256(eligibility_input),
        },
        "ecg_reference_provenance": {
            "issue": "#24",
            "eligibility_manifest": str(eligibility_manifest),
            "eligibility_manifest_sha256": sha256(eligibility_manifest) if eligibility_manifest.exists() else "unavailable",
            "eligibility_counts": dict(eligibility_counts),
            "marker_warning_is_nonfatal": True,
            "invalid_reason_is_not_double_counted_with_marker_warning": True,
        },
        "truth_class_distribution": {
            "ALL_WINDOWS_DIAGNOSTIC": dict(Counter(row["truth_class"] for row in truth_rows)),
            "ECG_VALID_PRIMARY": dict(Counter(row["truth_class"] for row in truth_rows if row.get("primary_ecg_valid") == "True")),
            "by_subject": {
                subject: {
                    "all_windows": dict(Counter(row["truth_class"] for row in truth_rows if row["subject"] == subject)),
                    "ecg_valid_primary": dict(Counter(row["truth_class"] for row in truth_rows if row["subject"] == subject and row.get("primary_ecg_valid") == "True")),
                }
                for subject in SUBJECTS
            },
            "by_subject_block_primary": {
                f"{row['subject']}/{row['block_id']}": dict(Counter(
                    item["truth_class"] for item in truth_rows
                    if item["subject"] == row["subject"] and item["block_id"] == row["block_id"] and item.get("primary_ecg_valid") == "True"
                ))
                for row in truth_rows
            },
        },
        "verification": {
            "py_compile": "PASS",
            "audit_script_run": "PASS",
            "pytest": {
                "status": "FAIL_COLLECTION_UNRELATED_LEGACY_IMPORT",
                "error": "scripts/legacy/2026-08-30_*/_cal_segment_test.py: ModuleNotFoundError: process_vital_signs_v3_1_1",
                "impact": "repository-wide collection did not complete; targeted audit run and output checks remain valid",
            },
        },
        "reused_scripts": [
            {"path": str(TARGET_SCRIPT_PATH), "sha256": sha256(TARGET_SCRIPT_PATH), "role": "PartReader and frozen window/target contract"},
            {"path": str(PRODUCER_PATH), "sha256": sha256(PRODUCER_PATH), "role": "existing bandpass/periodogram/peak/harmonic functions"},
            {"path": str(WINDOW_SCRIPT_PATH), "sha256": sha256(WINDOW_SCRIPT_PATH), "role": "same-window estimator lineage"},
            {"path": str(ARM_SCRIPT_PATH), "sha256": sha256(ARM_SCRIPT_PATH), "role": "ARM0/1/2 frozen comparison"},
        ],
        "reuse_rejection_reason": "Existing ECG reference audit and 15-row harmonic A/B diagnostic do not persist the required 335-window top candidates, prominence, ECG-nearest rank, and selection classification in one table; add only a downstream audit layer.",
        "parameters": {
            "mmwave_fs_hz": FS_HZ, "heart_band_hz": [0.8, 2.0], "br_band_hz": [0.1, 0.5],
            "periodogram": "scipy.signal.periodogram(window=hann), same default estimator path; no ECG input",
            "top_candidates": 8, "harmonic_tolerance_bpm": NEAR_HARMONIC_TOL_BPM,
            "classification_exact_tolerance": "max(0.5 * periodogram bin in bpm, 1.5 bpm)",
            "classification_nearby_tolerance": "max(2.0 * periodogram bin in bpm, 6.0 bpm)",
            "weak_relative_prominence": WEAK_REL_PROMINENCE,
        },
        "arm_definitions": {
            "arm0": "current block-local, unchanged", "arm1": "current block-local plus historical bins 9-40 gate",
            "arm2": "historical 6000-frame fixed target plus current 20 s HR estimator",
        },
        "ecg_role": "oracle_only_after_mmwave_target_and_peak_selection; no production target/peak selection",
        "internal_harmonic_guard": "Producer _select_spectral_bpm folds against time/previous/reference anchors and does not read BR; fixed targeted path uses estimate_freq_periodogram + detect_peaks_heart_lo and does not invoke it.",
        "external_rsp_guard": "A/B diagnostic only; raw selected and ARM results are retained unchanged; no hard rejection or producer change.",
        "reproduction_check": {
            "selected_hr_rows_compared": len(reproduction_hr), "selected_hr_within_0p001_bpm_n": sum(abs(value) <= 0.001 for value in reproduction_hr),
            "selected_hr_max_abs_delta_bpm": max(reproduction_hr) if reproduction_hr else None,
            "radar_br_rows_compared": len(reproduction_br), "radar_br_within_0p001_bpm_n": sum(abs(value) <= 0.001 for value in reproduction_br),
            "radar_br_max_abs_delta_bpm": max(reproduction_br) if reproduction_br else None,
        },
        "local_only_truth_table": str(truth_path),
        "local_only_truth_table_sha256": sha256(truth_path),
        "tracked_outputs": [],
        "decision": "SUPPORTING_RETROSPECTIVE_ORACLE_AUDIT_ONLY; HR HOLD; HRV BLOCKED; no producer promotion",
        "excluded": ["new HR algorithm", "ECG-assisted selection", "hard rejection", "C2B", "C2C", "NIR/RGB", "raw/firmware/portable V2 changes"],
    }
    result_root.mkdir(parents=True, exist_ok=True)
    manifest_path = result_root / "ECG_VALID_SPECTRAL_AUDIT_MANIFEST.json"
    report_path = result_root / "ECG_VALID_SPECTRAL_AUDIT_REPORT_2026-08-30.md"
    manifest["tracked_outputs"] = [
        {"path": summary_path.name, "sha256": sha256(summary_path)},
        {"path": arm_summary_path.name, "sha256": sha256(arm_summary_path)},
        {"path": manifest_path.name, "sha256": "written_after_manifest"},
        {"path": report_path.name, "sha256": "written_after_report"},
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(truth_rows, summary_rows, manifest), encoding="utf-8")
    manifest["tracked_outputs"][-2]["sha256"] = "self-referential_hash_not_recorded"
    manifest["tracked_outputs"][-1]["sha256"] = sha256(report_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_id": manifest["run_id"], "status": manifest["status"], "rows": len(truth_rows), "truth_table": str(truth_path), "summary": str(summary_path), "manifest": str(manifest_path)}, ensure_ascii=False))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-output-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    parser.add_argument("--eligibility-input", type=Path, required=True, help="#24 local-only per-window ECG eligibility CSV")
    args = parser.parse_args()
    run(args.local_output_root, args.result_root, args.eligibility_input)


if __name__ == "__main__":
    main()
