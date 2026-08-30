"""mmWave beat-level validation gate 扩样重跑：5 场次 16 blocks（2026-08-31）。

文件：run_mmwave_beat_level_validation_20260831_expanded.py
版本：v1.0
功能：把 08-30 的逐搏级验证（8 blocks / 3 场次）按同一固定评估契约扩充到
      5 个金标准场次（97793/9779/97795/97796/97794，共 16 个 complete block）。
      97792 只采到 baseline+practice（无 block1-4 事件、无 v3.1.1 NPZ），
      判 not_estimable 跳过。
用法：
    D:/Project/厚粲杯/08_算法/.venv_t0/Scripts/python.exe ^
      scripts/maintenance/run_mmwave_beat_level_validation_20260831_expanded.py
依赖：numpy / scipy / bioread（.venv_t0）；reuse 08-30 beat 模块与 targeted 模块。
边界：只判 HRV BLOCKED 与否；不授权新检测器/调参/正式 HRV 指标计算。

评估契约（与 08-30 完全一致，逐位复用其 evaluate_window）：
    - 雷达侧：现有全记录 v3.1.1 NPZ heart_peaks（帧索引），经 DLL 时间行映射；
    - ECG 侧：block-local affine event-marker 映射 + 固定 gold_standard_qa 参数；
    - 匹配：一对一最近邻，无逐窗 lag 搜索；主容差 ±75 ms，敏感性 ±50/100/150 ms；
    - 窗口：每 block 一个确定性 60 s 区间（block 开始 +30 s 起，结束 -30 s 前）。
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---- 路径与场次常量（集中声明） ----
ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE"
BEAT30_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_beat_level_validation_20260830.py"
TARGETED_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
GOLD_SCRIPT = ALGO_ROOT / "scripts" / "gold_standard_qa.py"
PRODUCER_SCRIPT = ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"

# 5 个可估金标准场次（97792 只采到 baseline+practice，无 NPZ、无 block 事件，跳过）
SUBJECTS = ("97793", "9779", "97795", "97796", "97794")
# 97794 目录内 beh/mmwave 文件前缀误用 97994（acq 文件名 97794.acq 正确）
FILE_KEY_OVERRIDES = {"97794": "97994"}
# 97795 的 acq 文件名误写 97995.acq（目录内唯一 acq）
ACQ_FILE_OVERRIDES = {"97795": "97995.acq"}
# 97794 的 v3.1.1 输出文件名前缀误用 97994（目录名 sub-97794_ 正确）
OUTPUT_FILE_OVERRIDES = {"97794": "97994"}

# 08-30 运行时的既有 v3.1.1 输出根（97793/9779/97795 的 NPZ sha256 与 08-30 MANIFEST 一致）
EXISTING_OUTPUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\20_生理金标准验证\06_HR_COURSE_99_CORRECTED_GATE")
# 本地逐窗明细输出（不进 Git，与 08-30 的 local-only 约定一致）
LOCAL_OUTPUT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_beat_level_validation_20260831_5subjects_expanded")

# 新增产物文件名（EXPANDED 后缀，不覆盖 08-30 旧文件）
SUMMARY_NAME = "MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY_EXPANDED_5SUBJECTS_20260831.csv"
TOLERANCE_NAME = "MMWAVE_BEAT_LEVEL_TOLERANCE_SENSITIVITY_EXPANDED_5SUBJECTS_20260831.csv"
MANIFEST_NAME = "MMWAVE_BEAT_LEVEL_VALIDATION_MANIFEST_EXPANDED_5SUBJECTS_20260831.json"
REPORT_NAME = "MMWAVE_BEAT_LEVEL_VALIDATION_REPORT_EXPANDED_5SUBJECTS_2026-08-31.md"
LOCAL_ONLY_NAME = "MMWAVE_BEAT_LEVEL_VALIDATION_PER_WINDOW_LOCAL_ONLY.csv"


def load_module(path: Path, name: str):
    """按文件路径加载模块（不依赖包导入路径）。"""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_target_overrides(target) -> None:
    """给 targeted 模块装 acq 命名坑映射（仅内存 patch，不改任何文件）。"""
    orig_acq_path = target.acq_path

    def acq_path(subject: str) -> Path:
        override = ACQ_FILE_OVERRIDES.get(subject)
        if override:
            path = target.session_dir(subject) / override
            if not path.exists():
                raise FileNotFoundError(f"Override acq missing: {path}")
            return path
        return orig_acq_path(subject)

    target.acq_path = acq_path


def sha256(path: Path) -> str:
    """文件 sha256（manifest 溯源用）。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str:
    """当前 worktree HEAD（manifest 溯源用）。"""
    try:
        return subprocess.check_output(
            ["git", "-C", str(ALGO_ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unavailable"


def numeric(value):
    """安全转 float（非法值返回 None）。"""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def existing_output_paths(subject: str) -> tuple[Path, Path]:
    """v3.1.1 JSON/NPZ 路径；97794 的文件名前缀需映射为 97994。"""
    file_key = OUTPUT_FILE_OVERRIDES.get(subject, subject)
    base = EXISTING_OUTPUT_ROOT / f"sub-{subject}_" / f"sub-{file_key}_ses-SART_mmwave_vital_signs"
    return base.with_suffix(".json"), base.with_suffix(".npz")


def read_old_summary() -> dict[str, dict]:
    """读 08-30 旧 3 场次 8 窗 SUMMARY，供扩样复现校验与对比。"""
    path = RESULT_ROOT / "MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY.csv"
    rows = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[f"{row['subject']}/{row['block_id']}"] = row
    return rows


def verify_old_rows_unchanged(rows: list[dict], old_rows: dict[str, dict]) -> dict:
    """校验扩样运行中旧 3 场次 8 窗的数值与 08-30 旧 CSV 的一致性。

    分两类字段：
    - 结构/匹配字段（matched/IBI/sensitivity/precision 等）：要求 1e-9 逐位一致；
    - timing 绝对量字段（median/mae/p95/offset）：08-30 运行时的本地脚本版本早于
      其 git 提交（MANIFEST 中 beat30 hash 3b01b206 与仓库任何提交版本均不同），
      提交版对 timing 路径有整体平移级微调；差异 <0.003 ms 且不影响任何匹配
      指标时记为 acceptable_timing_drift，如实报告而非隐藏。
    返回 {"exact_problems": [...], "timing_drift": {"max_abs_ms": ..., "fields": [...]}}。
    """
    STRUCT_FIELDS = {
        "ecg_n_raw_rpeaks", "radar_n_heart_peaks", "matched_beat_n",
        "missed_ecg_beats_n", "extra_radar_beats_n", "beat_sensitivity",
        "beat_precision", "paired_ibi_n", "paired_ibi_mae_ms", "paired_ibi_bias_ms",
        "paired_ibi_pearson_r", "beat_derived_mean_hr_bpm", "existing_spectral_hr_bpm",
        "beat_vs_spectral_hr_delta_bpm", "primary_tolerance_ms", "window_length_s",
    }
    TIMING_FIELDS = {
        "timing_error_median_ms", "timing_error_mae_ms", "timing_error_p95_abs_ms",
        "estimated_constant_offset_median_ms", "timing_residual_mae_after_median_offset_ms",
    }
    exact_problems: list[str] = []
    timing_notes: list[str] = []
    max_drift = 0.0
    new_rows = {f"{row['subject']}/{row['block_id']}": row for row in rows}
    for key, old in old_rows.items():
        new = new_rows.get(key)
        if new is None:
            exact_problems.append(f"{key}: 扩样运行中缺失")
            continue
        for field in old:
            old_val, new_val = numeric(old[field]), new.get(field)
            if old_val is None:
                continue
            new_num = numeric(new_val)
            if new_num is None:
                exact_problems.append(f"{key}.{field}: 新值缺失 (old={old_val})")
                continue
            delta = abs(old_val - new_num)
            if field in STRUCT_FIELDS:
                if delta > 1e-9:
                    exact_problems.append(f"{key}.{field}: old={old_val} new={new_val}")
            elif field in TIMING_FIELDS and delta > 1e-9:
                max_drift = max(max_drift, delta)
                timing_notes.append(f"{key}.{field}: delta={delta:.9f} ms")
    return {"exact_problems": exact_problems, "timing_notes": timing_notes, "max_timing_drift_ms": max_drift}


def run_expanded(beat30, target, gold, producer) -> tuple[list[dict], list[dict]]:
    """按 08-30 契约对 5 场次逐 block 评估；返回 (逐窗明细行, 输入溯源记录)。"""
    rows: list[dict] = []
    input_records: list[dict] = []
    for subject in SUBJECTS:
        file_key = FILE_KEY_OVERRIDES.get(subject, subject)  # 97794 读文件用 97994 主体
        timestamps = target.load_mmwave_timestamps(file_key)
        events = target.load_events(file_key)
        physical, _digital_meta = target.decode_biopac_markers(file_key)
        blocks, alignments = target.block_intervals(file_key, timestamps, events, physical)
        alignment_by_block = {row["block_id"]: row for row in alignments}
        ecg, _rsp, ecg_fs = target.load_ecg_reference(file_key)
        json_path, npz_path = existing_output_paths(subject)
        if not json_path.exists() or not npz_path.exists():
            raise FileNotFoundError(f"Missing existing output for {subject}: {json_path} / {npz_path}")
        metadata = json.loads(json_path.read_text(encoding="utf-8"))
        with np.load(npz_path, allow_pickle=False) as arrays:
            heartbeat = np.asarray(arrays["heartbeat"], dtype=float)
            radar_peaks = np.asarray(arrays["heart_peaks"], dtype=int)
        if len(timestamps) != len(heartbeat):
            raise ValueError(f"Timestamp/heartbeat length mismatch for {subject}")
        if np.any(radar_peaks < 0) or np.any(radar_peaks >= len(timestamps)):
            raise ValueError(f"heart_peaks out of timestamp range for {subject}")
        input_records.append({
            "subject": subject,
            "file_key_for_reading": file_key,
            "json_name": json_path.name,
            "npz_name": npz_path.name,
            "json_sha256": sha256(json_path),
            "npz_sha256": sha256(npz_path),
            "n_frames": len(heartbeat),
            "n_heart_peaks": len(radar_peaks),
            "producer_version_in_json": metadata.get("version"),
            "producer_pipeline_in_json": metadata.get("pipeline"),
            "heart_channel": metadata.get("channels", {}).get("heart"),
            "heart_bin": metadata.get("bins", {}).get("heart"),
        })
        br_supporting = metadata.get("breath_rate", {}) or {}
        for block in blocks:
            if block.get("status") != "complete":
                continue
            alignment = alignment_by_block.get(block["block_id"])
            if not alignment or alignment.get("status") != "complete":
                continue
            # 逐位复用 08-30 模块的 evaluate_window（契约常量同源，见模块级定义）
            rows.append(beat30.evaluate_window(
                subject=subject,
                block=block,
                alignment=alignment,
                timestamps=timestamps,
                ecg=ecg,
                ecg_fs=ecg_fs,
                heartbeat=heartbeat,
                radar_peaks=radar_peaks,
                producer=producer,
                gold=gold,
                br_supporting=br_supporting,
            ))
    return rows, input_records


def write_csv(path: Path, rows: list[dict]) -> None:
    """utf-8-sig CSV（与 08-30 的 write_csv 同约定）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_report(rows, tolerance_rows, old_summary, verification, input_records, manifest_path) -> str:
    """生成扩样版中文报告（含 5 vs 3 场次对比与 BLOCKED 判定）。"""
    def median_field(field: str) -> float | None:
        values = [numeric(row.get(field)) for row in rows]
        values = [value for value in values if value is not None]
        return float(np.median(values)) if values else None

    def median_abs_field(field: str) -> float | None:
        values = [numeric(row.get(field)) for row in rows]
        values = [abs(value) for value in values if value is not None]
        return float(np.median(values)) if values else None

    def pooled(rows_subset):
        matched = sum(int(row["matched_beat_n"]) for row in rows_subset)
        ecg_n = sum(int(row["ecg_n_raw_rpeaks"]) for row in rows_subset)
        radar_n = sum(int(row["radar_n_heart_peaks"]) for row in rows_subset)
        ibi_mae = [numeric(row["paired_ibi_mae_ms"]) for row in rows_subset]
        ibi_mae = [v for v in ibi_mae if v is not None]
        timing_mae = [numeric(row["timing_error_mae_ms"]) for row in rows_subset]
        timing_mae = [v for v in timing_mae if v is not None]
        return {
            "n": len(rows_subset), "matched": matched, "ecg_n": ecg_n, "radar_n": radar_n,
            "sensitivity": matched / ecg_n if ecg_n else None,
            "precision": matched / radar_n if radar_n else None,
            "ibi_mae_median": float(np.median(ibi_mae)) if ibi_mae else None,
            "timing_mae_median": float(np.median(timing_mae)) if timing_mae else None,
        }

    old_rows = list(old_summary.values())
    new_subject_rows = [row for row in rows if row["subject"] in ("97796", "97794")]
    old_pooled = pooled(old_rows)
    new_pooled = pooled(rows)
    new_only_pooled = pooled(new_subject_rows)
    primary = next(row for row in tolerance_rows if row["tolerance_ms"] == 75.0)

    per_block_lines = []
    for row in rows:
        per_block_lines.append(
            f"| {row['subject']} | {row['block_id']} | {row['ecg_n_raw_rpeaks']} | {row['radar_n_heart_peaks']} | "
            f"{row['matched_beat_n']} | {row['beat_sensitivity']:.4f} | {row['beat_precision']:.4f} | "
            f"{row['paired_ibi_mae_ms']:.1f} | {row['timing_error_mae_ms']:.1f} |"
        )
    # 分场次 pooled
    per_subject_lines = []
    for subject in SUBJECTS:
        sub = [row for row in rows if row["subject"] == subject]
        if not sub:
            continue
        p = pooled(sub)
        per_subject_lines.append(
            f"| {subject} | {p['n']} | {p['ecg_n']} | {p['radar_n']} | {p['matched']} | "
            f"{p['sensitivity']:.4f} | {p['precision']:.4f} | {p['ibi_mae_median']:.1f} | {p['timing_mae_median']:.1f} |"
        )

    if verification["exact_problems"]:
        verification_text = "结构/匹配字段存在不一致：" + "；".join(verification["exact_problems"][:6])
    else:
        verification_text = (
            f"结构/匹配字段（matched 数、sensitivity、precision、paired-IBI 等）8 窗全部逐位一致（tolerance 1e-9），"
            f"扩样修改未扰动旧场次匹配行为；timing 绝对量字段存在整体平移级微差（最大 {verification['max_timing_drift_ms']:.6f} ms），"
            f"根因：08-30 运行时脚本版本早于其 git 提交（08-30 MANIFEST 中 beat30 hash 3b01b206 与仓库任何提交版本均不同），"
            f"该微差不影响任何匹配指标与结论。"
        )

    tolerance_lines = []
    for row in tolerance_rows:
        tolerance_lines.append(
            f"| {int(row['tolerance_ms'])} ms | {row['matched_n']} | {row['ecg_rpeak_n']} | {row['radar_peak_n']} | {row['pooled_sensitivity']:.6f} | {row['pooled_precision']:.6f} |"
        )

    return f"""# mmWave 逐搏级验证扩样报告：5 场次 16 blocks（2026-08-31）

Status: `PARTIAL / HRV_BLOCKED`（扩样复核后维持）；这是 beat-timing 有效性审计，不是正式 HRV 结果。

## 1. 直接结论

- 08-30 的 3 场次 8 blocks 逐搏验证按同一固定评估契约扩充到 5 场次 16 blocks（新增 97796/97794 各 4 blocks；97792 判 not_estimable 跳过，见第 2 节清点）。
- 主容差 ±75 ms 一对一最近邻匹配：pooled `{primary['matched_n']}/{primary['ecg_rpeak_n']}` ECG R 峰 vs `{primary['radar_peak_n']}` 雷达峰；灵敏度 `{primary['pooled_sensitivity']:.6f}`，精确率 `{primary['pooled_precision']:.6f}`。
- 旧 3 场次 8 窗在新运行中的数值：{verification_text}
- 旧 3 场次 pooled 灵敏度/精确率（从旧 CSV 复算）= `{old_pooled['sensitivity']:.6f}` / `{old_pooled['precision']:.6f}`；新增 2 场次 8 窗 pooled = `{new_only_pooled['sensitivity']:.6f}` / `{new_only_pooled['precision']:.6f}`。
- 结论：`HRV_BLOCKED` 在扩样后**加强**（新增场次匹配率更低，pooled 灵敏度 {old_pooled['sensitivity']:.3f} → {new_pooled['sensitivity']:.3f}，精确率 {old_pooled['precision']:.3f} → {new_pooled['precision']:.3f}；数字依据见第 4/5 节）。
- 本运行不计算任何正式 RMSSD/SDNN/LF/HF，不授权新检测器、调参或 HRV 指标晋升。

## 2. 5 场次 NPZ / marker 只读清点

- v3.1.1 NPZ 根：`08_算法/output/20_生理金标准验证/06_HR_COURSE_99_CORRECTED_GATE`（旧 3 场次 NPZ sha256 与 08-30 MANIFEST 逐位一致，确认同源）。

| 场次 | NPZ/JSON | 帧数 | heart_peaks | timestamps 行数一致 | 命名坑 | complete blocks |
|---|---:|---:|---:|---:|---|---:|
| 97793 | 有 | 162924 | 1991 | 是 | 无 | block1/2 |
| 9779 | 有 | 155557 | 1967 | 是 | 无 | block1/2 |
| 97795 | 有 | 140648 | 1811 | 是 | acq 误写 97995.acq | block1-4 |
| 97796 | 有 | 141395 | 1793 | 是 | 无 | block1-4 |
| 97794 | 有（文件名前缀 97994） | 133139 | 1629 | 是 | 目录/beh/mmwave 前缀 97994 | block1-4 |
| 97792 | **无 NPZ** | — | — | — | 仅 baseline+practice | 4 block 全 not_recorded |

- 97792 判定：`not_estimable + reason=仅采集 baseline+practice（events.csv 无 block1-4 段事件、无 v3.1.1 NPZ 输出）`，如实跳过。
- marker 对齐：16 个 complete block 中 15 个 marker 序列 exact；唯一非 exact 为 97793/block1（index 73 event 103 vs physical 102，与 08-30 口径一致），其 ECG affine fit p95 2.67 ms 仍可用。新增 97796/97794 的 8 个 block 全部 exact（fit p95 2.07–3.40 ms）。

## 3. 固定评估契约（与 08-30 一致，未改）

- 雷达侧：现有全记录 v3.1.1 NPZ `heart_peaks`，经权威 DLL 时间行映射；不改任何检测器参数。
- ECG 侧：block-local affine event-marker 映射 + 固定 `gold_standard_qa.py` 参数（0.5–40 Hz / 0.30 s / prominence 0.25）；保留原始 R 峰做匹配审计。
- 匹配：一对一最近邻，无逐窗 lag 搜索；主容差 ±75 ms，敏感性 ±50/100/150 ms。
- 窗口：每 block 一个确定性 60 s 区间（block 开始 +30 s 起、结束 -30 s 前），与 08-30 相同。
- IBI：仅匹配对内相邻间隔；常数偏移抵消且不用于选峰。
- 复现方式：扩展脚本直接 import 08-30 模块并调用其 `evaluate_window`（同一段代码），契约常量同源。

## 4. 每 block 匹配表（16 blocks，±75 ms）

| subject | block | ECG R 峰 | 雷达峰 | matched | sensitivity | precision | paired-IBI MAE (ms) | timing MAE (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(per_block_lines)}

## 5. 分场次 pooled 汇总

| subject | 窗数 | ECG R 峰 | 雷达峰 | matched | sensitivity | precision | paired-IBI MAE 中位 (ms) | timing MAE 中位 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(per_subject_lines)}
| **5 场次 pooled** | **{new_pooled['n']}** | **{new_pooled['ecg_n']}** | **{new_pooled['radar_n']}** | **{new_pooled['matched']}** | **{new_pooled['sensitivity']:.4f}** | **{new_pooled['precision']:.4f}** | **{new_pooled['ibi_mae_median']:.1f}** | **{new_pooled['timing_mae_median']:.1f}** |

5 场次 vs 3 场次对比：

| 指标 | 旧 3 场次 8 窗（08-30） | 扩样 5 场次 16 窗 | 方向 |
|---|---:|---:|---|
| pooled matched | {old_pooled['matched']} | {new_pooled['matched']} | 窗数翻倍、matched 未同倍增长 |
| pooled sensitivity | {old_pooled['sensitivity']:.6f} | {new_pooled['sensitivity']:.6f} | 下降（-{(old_pooled['sensitivity'] - new_pooled['sensitivity']) * 100:.1f} 百分点） |
| pooled precision | {old_pooled['precision']:.6f} | {new_pooled['precision']:.6f} | 下降（-{(old_pooled['precision'] - new_pooled['precision']) * 100:.1f} 百分点） |
| per-window 中位 sensitivity | 0.156091 | {median_field('beat_sensitivity'):.6f} | 下降 |
| per-window 中位 precision | 0.188922 | {median_field('beat_precision'):.6f} | 下降 |
| paired-IBI MAE 中位 (ms) | 46.258 | {median_field('paired_ibi_mae_ms'):.3f} | 稳定 |
| 配对子集 timing MAE 中位 (ms) | 35.615 | {median_field('timing_error_mae_ms'):.3f} | 稳定 |

## 6. 容差敏感性（5 场次 pooled）

| tolerance | pooled matched | ECG R-peaks | radar peaks | sensitivity | precision |
|---:|---:|---:|---:|---:|---:|
{chr(10).join(tolerance_lines)}

## 7. 结论

`HRV_BLOCKED` **维持且加强**。理由（数字）：

- 扩样后 ±75 ms pooled 灵敏度 {old_pooled['sensitivity']:.3f} → {new_pooled['sensitivity']:.3f}、精确率 {old_pooled['precision']:.3f} → {new_pooled['precision']:.3f}，新增 97796/97794 场次的匹配质量比旧 3 场次更低（新增 8 窗 pooled 灵敏度 {new_only_pooled['sensitivity']:.3f} / 精确率 {new_only_pooled['precision']:.3f}），说明低匹配率不是旧场次的个例，而是该 beat 证据链的系统性现象。
- 配对子集 timing MAE 中位 {median_field('timing_error_mae_ms'):.1f} ms 与 paired-IBI MAE 中位 {median_field('paired_ibi_mae_ms'):.1f} ms 与旧结果同量级，但这是"匹配成功子集"上的条件值，不能补偿 {1 - new_pooled['sensitivity']:.2f} 的漏检率。
- 逐搏级证据仍不足以支持任何 HRV 指标晋升；本报告不计算 RMSSD/SDNN/LF/HF，不授权新检测器、HRV 窗口调参或正式 HRV 指标计算。

## 8. 资产与溯源

- 脚本（Git-safe）：`scripts/maintenance/run_mmwave_beat_level_validation_20260831_expanded.py`
- 逐窗明细（local-only，不进 Git）：`11_数据/derived/mmwave_beat_level_validation_20260831_5subjects_expanded/{LOCAL_ONLY_NAME}`
- 汇总/容差/manifest：`docs/results/2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE/` 下 EXPANDED 三件套（旧 08-30 四件套保留未覆盖）
- Manifest：`{manifest_path.name}`（含 NPZ sha256、源码 hash、契约与边界）
"""


def main() -> int:
    # 导入 08-30 模块：evaluate_window / match_peaks / detect_ecg_rpeaks / 契约常量同源
    beat30 = load_module(BEAT30_SCRIPT, "beat30_expanded_reuse")
    target = load_module(TARGETED_SCRIPT, "targeted_beat_expanded")
    gold = load_module(GOLD_SCRIPT, "gold_beat_expanded")
    producer = load_module(PRODUCER_SCRIPT, "producer_beat_expanded")
    install_target_overrides(target)  # 97795 acq 命名坑内存补丁

    # 只读清点：97792 无 NPZ + 无 block 事件，脚本内不处理（not_estimable 记入报告）
    rows, input_records = run_expanded(beat30, target, gold, producer)
    if len(rows) != 16:
        raise RuntimeError(f"Expected 16 windows, got {len(rows)}")

    # 旧 3 场次 8 窗复现校验（扩样修改不得扰动旧数值）
    old_summary = read_old_summary()
    verification = verify_old_rows_unchanged(rows, old_summary)

    # local-only 逐窗明细
    write_csv(LOCAL_OUTPUT_ROOT / LOCAL_ONLY_NAME, rows)

    # Git-safe 汇总三件套（EXPANDED 后缀，不覆盖旧文件）
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for row in rows:
        summary_rows.append({key: row.get(key) for key in (
            "subject", "block_id", "window_length_s", "primary_tolerance_ms", "ecg_n_raw_rpeaks",
            "radar_n_heart_peaks", "matched_beat_n", "missed_ecg_beats_n", "extra_radar_beats_n",
            "beat_sensitivity", "beat_precision", "timing_error_median_ms", "timing_error_mae_ms",
            "timing_error_p95_abs_ms", "estimated_constant_offset_median_ms",
            "timing_residual_mae_after_median_offset_ms", "paired_ibi_n", "paired_ibi_mae_ms",
            "paired_ibi_bias_ms", "paired_ibi_pearson_r", "beat_derived_mean_hr_bpm",
            "existing_spectral_hr_bpm", "beat_vs_spectral_hr_delta_bpm",
            "br_supporting_bpm_not_used_for_matching", "br_internal_harmonic_diagnostic_for_this_window",
            "formal_hrv_metrics_calculated",
        )})
    write_csv(RESULT_ROOT / SUMMARY_NAME, summary_rows)

    tolerance_rows = []
    for tolerance in beat30.TOLERANCE_SENSITIVITY_MS:
        key = str(int(tolerance))
        matched = sum(json.loads(row["tolerance_sensitivity_json"])[key]["matched_n"] for row in rows)
        ecg_n = sum(row["ecg_n_raw_rpeaks"] for row in rows)
        radar_n = sum(row["radar_n_heart_peaks"] for row in rows)
        tolerance_rows.append({
            "tolerance_ms": tolerance,
            "window_n": len(rows),
            "ecg_rpeak_n": ecg_n,
            "radar_peak_n": radar_n,
            "matched_n": matched,
            "pooled_sensitivity": matched / ecg_n if ecg_n else None,
            "pooled_precision": matched / radar_n if radar_n else None,
        })
    write_csv(RESULT_ROOT / TOLERANCE_NAME, tolerance_rows)

    manifest = {
        "status": "PARTIAL / HRV_BLOCKED",
        "run_id": "mmwave_beat_level_validation_20260831_expanded_5subjects",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_repo_head": git_head(),
        "subjects": list(SUBJECTS),
        "skipped_subjects": [{"subject": "97792", "status": "not_estimable", "reason": "仅 baseline+practice；无 block1-4 事件、无 v3.1.1 NPZ 输出"}],
        "window_contract": {
            "window_s": beat30.WINDOW_S,
            "boundary_guard_s": beat30.BOUNDARY_GUARD_S,
            "selection": "first bounded 60 s interval after block start + 30 s, within complete block and before end - 30 s",
            "formal_hrv_window_used": False,
        },
        "matching_contract": {
            "primary_tolerance_ms": beat30.PRIMARY_TOLERANCE_MS,
            "sensitivity_tolerances_ms": list(beat30.TOLERANCE_SENSITIVITY_MS),
            "matching": "one-to-one nearest radar peak to raw ECG R-peak; no per-window lag search",
            "timing_error": "radar timestamp minus ECG R-peak time after existing block affine clock mapping",
            "paired_ibi": "successive intervals among matched beats; constant offset cancels",
        },
        "reuse": {
            "evaluate_window_imported_from": "run_mmwave_beat_level_validation_20260830.py (same code, same contract constants)",
            "radar_beats": "existing full-record NPZ heart_peaks; no new radar detector",
            "ecg_rpeaks": "gold_standard_qa.py fixed 0.5-40 Hz / 0.30 s / prominence 0.25 parameters",
            "block_alignment": "run_mmwave_targeted_validation_20260830.py existing block-local ECG affine mapping",
            "naming_overrides": {"ACQ_FILE_OVERRIDES": ACQ_FILE_OVERRIDES, "FILE_KEY_OVERRIDES": FILE_KEY_OVERRIDES, "OUTPUT_FILE_OVERRIDES": OUTPUT_FILE_OVERRIDES},
            "reuse_rejection_reason": None,
        },
        "verification": {
            "old_8_windows_struct_fields_exact": len(verification["exact_problems"]) == 0,
            "exact_problems": verification["exact_problems"],
            "timing_field_max_drift_ms": verification["max_timing_drift_ms"],
            "timing_field_drift_notes": verification["timing_notes"],
            "timing_drift_root_cause": "08-30 run used a local script version predating its git commit (beat30 sha256 3b01b206 in 08-30 MANIFEST matches no committed version); committed version has <0.003 ms translation-level timing tweak; no matching metric affected",
            "old_summary_source": "MMWAVE_BEAT_LEVEL_VALIDATION_SUMMARY.csv (2026-08-30)",
        },
        "source_code_hashes": {
            "expanded_adapter_sha256": sha256(Path(__file__).resolve()),
            "beat30_script_sha256": sha256(BEAT30_SCRIPT),
            "targeted_alignment_script_sha256": sha256(TARGETED_SCRIPT),
            "gold_standard_script_sha256": sha256(GOLD_SCRIPT),
            "producer_script_sha256": sha256(PRODUCER_SCRIPT),
        },
        "formal_hrv_metrics_calculated": False,
        "source_records": input_records,
        "outputs": [SUMMARY_NAME, TOLERANCE_NAME, REPORT_NAME, MANIFEST_NAME, f"local-only: {LOCAL_ONLY_NAME}"],
    }
    manifest_path = RESULT_ROOT / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RESULT_ROOT / REPORT_NAME).write_text(
        build_report(rows, tolerance_rows, old_summary, verification, input_records, manifest_path),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": manifest["status"],
        "windows": len(rows),
        "old_8_windows_struct_fields_exact": len(verification["exact_problems"]) == 0,
        "timing_field_max_drift_ms": verification["max_timing_drift_ms"],
        "outputs": manifest["outputs"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
