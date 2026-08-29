"""Audit historical ECG reference lineage and replay fixed mmWave windows.

This is a read-only scientific audit around the existing block-local targeted
validation output.  It changes neither the producer, raw acquisition files,
portable V2, nor the formal analysis repository.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_MM_FILE = RESULT_ROOT / "mmwave_ecg_block_window_comparison.csv"
SUBJECTS = ("97793", "9779", "97795")
CANONICAL_HEAD = "472735b6b6af5f98e92ab7815718e81863cb6098"
CANONICAL_MASTER = "96525b19422b34291e4d87747fef214d1fec60d7"
CANONICAL_REANALYSIS = "d87229afe071f23450728a6d617ec82317e6c9df"
FOCUSWAVE_ECG = "8e6fe5c5d08f386661bc05aaf9d5c5715a43b317"
ATTENTION_HEAD = "df6a06a74c1505ff3e22f651aed5dbc4f874483c"
FOCUSWAVE_ROOT = Path(r"D:\Project\厚粲杯\05_实验\FocusWave")
ATTENTION_ROOT = Path(r"D:\Project\厚粲杯\08_算法\01_Attention-Analysis_nvidia-cuda")
DATA_ROOT = Path(r"D:\acq_mmwave_data")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(repo: Path, *args: str, text: bool = True):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=text, stderr=subprocess.DEVNULL).strip()


def source_record(repo: Path, repo_name: str, ref: str, path: str, **fields) -> dict:
    row = {"repo": repo_name, "branch_or_ref": ref, "commit": ref, "local_path": str(repo), "script_path": path}
    row.update(fields)
    try:
        content = subprocess.check_output(["git", "-C", str(repo), "show", f"{ref}:{path}"], stderr=subprocess.DEVNULL)
        row["commit"] = git(repo, "rev-parse", ref)
        row["commit_time"] = git(repo, "show", "-s", "--format=%cI", ref)
        row["source_sha256"] = sha256_bytes(content)
        row["reproducibility"] = "source_present_at_ref"
    except Exception:
        row["reproducibility"] = "source_not_present_at_ref"
    return row


def import_rerun_module():
    path = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
    spec = importlib.util.spec_from_file_location("mmwave_targeted_rerun", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_float(value):
    try:
        return float(value) if value not in (None, "", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def metrics(rows: list[dict], prefix: str) -> dict:
    pairs = [(safe_float(row.get(f"{prefix}_ecg_hr_bpm")), safe_float(row.get("mmwave_hr_bpm"))) for row in rows]
    pairs = [(a, m) for a, m in pairs if a is not None and m is not None]
    errors = [abs(m - a) for a, m in pairs]
    signed = [m - a for a, m in pairs]
    return {
        "pipeline": prefix,
        "n": len(pairs),
        "mae_bpm": round(float(np.mean(errors)), 6) if errors else None,
        "median_abs_error_bpm": round(float(np.median(errors)), 6) if errors else None,
        "bias_mmwave_minus_ecg_bpm": round(float(np.mean(signed)), 6) if signed else None,
    }


def comparison_diagnostics(rows: list[dict]) -> dict:
    pairs = [(safe_float(row.get("historical_ecg_hr_bpm")), safe_float(row.get("current_ecg_hr_bpm"))) for row in rows]
    pairs = [(old, new) for old, new in pairs if old is not None and new is not None]
    deltas = [new - old for old, new in pairs]
    changed = [value for value in deltas if abs(value) > 1e-9]
    by_subject = {}
    for subject in sorted({row["subject"] for row in rows}):
        values = [new - old for row in rows if row["subject"] == subject for old, new in [(safe_float(row.get("historical_ecg_hr_bpm")), safe_float(row.get("current_ecg_hr_bpm")))] if old is not None and new is not None]
        by_subject[subject] = {
            "n": len(values),
            "changed_n": sum(abs(value) > 1e-9 for value in values),
            "mean_delta_current_minus_old_bpm": round(float(np.mean(values)), 6) if values else None,
            "median_abs_delta_bpm": round(float(np.median(np.abs(values))), 6) if values else None,
            "max_abs_delta_bpm": round(float(np.max(np.abs(values))), 6) if values else None,
        }
    return {
        "n": len(deltas),
        "changed_n": len(changed),
        "unchanged_n": len(deltas) - len(changed),
        "mean_delta_current_minus_old_bpm": round(float(np.mean(deltas)), 6) if deltas else None,
        "median_abs_delta_bpm": round(float(np.median(np.abs(deltas))), 6) if deltas else None,
        "max_abs_delta_bpm": round(float(np.max(np.abs(deltas))), 6) if deltas else None,
        "by_subject": by_subject,
    }


def replay_fixed_windows(rerun) -> tuple[list[dict], list[dict], dict]:
    fixed = [row for row in read_csv(FIXED_MM_FILE) if row.get("subject") in SUBJECTS]
    output, alignment_rows = [], []
    for subject in SUBJECTS:
        events = rerun.load_events(subject)
        timestamps = rerun.load_mmwave_timestamps(subject)
        physical, digital_meta = rerun.decode_biopac_markers(subject)
        blocks, audits = rerun.block_intervals(subject, timestamps, events, physical)
        block_by_id = {row["block_id"]: row for row in blocks}
        audit_by_id = {row["block_id"]: row for row in audits}
        ecg, _rsp, fs = rerun.load_ecg_reference(subject)
        acq_start_ms = int(digital_meta["acq_start_ms_metadata"])
        acq_path = Path(digital_meta["acq_path"])
        file_verdict = "directory_subject_matches_basename_typo" if subject == "97795" and acq_path.name == "97995.acq" else "subject_basename_match"
        for row in fixed:
            if row.get("subject") != subject:
                continue
            block_id = row["block_id"]
            block = block_by_id[block_id]
            audit = audit_by_id[block_id]
            if block["status"] != "complete" or audit.get("ecg_fit_slope_samples_per_ms") is None:
                continue
            # Use the exact mmWave value already produced by the block-local
            # targeted run.  No mmWave selection or estimator is recomputed.
            mmwave_hr = safe_float(row.get("local_hr_freq_bpm"))
            start_ms = int(row["window_start_unix_ms"])
            end_ms = int(row["window_end_unix_ms"])
            old_i0 = int(round((start_ms - acq_start_ms) * fs / 1000.0))
            old_i1 = int(round((end_ms - acq_start_ms) * fs / 1000.0))
            slope = float(block["ecg_fit_slope"])
            intercept = float(block["ecg_fit_intercept"])
            current_i0 = int(round(slope * start_ms + intercept))
            current_i1 = int(round(slope * end_ms + intercept))
            old = rerun.ecg_rsp_window(ecg, _rsp, fs, old_i0, old_i1)
            current = rerun.ecg_rsp_window(ecg, _rsp, fs, current_i0, current_i1)
            # Minimal-difference arm: current detector with the historical
            # metadata-zero alignment.  It isolates alignment from detector.
            minimal = rerun.ecg_rsp_window(ecg, _rsp, fs, old_i0, old_i1)
            output.append({
                "subject": subject,
                "block_id": block_id,
                "window_id": row["window_id"],
                "window_index_within_block": row["window_index_within_block"],
                "window_start_unix_ms": start_ms,
                "window_end_unix_ms": end_ms,
                "window_start_s_from_block": row["window_start_s_from_block"],
                "window_end_s_from_block": row["window_end_s_from_block"],
                "mmwave_hr_bpm": mmwave_hr,
                "mmwave_hr_source": "existing_fixed_local_hr_freq_bpm_from_block_targeted_rerun",
                "historical_ecg_hr_bpm": old.get("ecg_hr_bpm"),
                "current_ecg_hr_bpm": current.get("ecg_hr_bpm"),
                "minimal_difference_ecg_hr_bpm": minimal.get("ecg_hr_bpm"),
                "historical_ecg_abs_error_bpm": abs(mmwave_hr - float(old["ecg_hr_bpm"])) if mmwave_hr is not None and old.get("ecg_hr_bpm") is not None else None,
                "current_ecg_abs_error_bpm": abs(mmwave_hr - float(current["ecg_hr_bpm"])) if mmwave_hr is not None and current.get("ecg_hr_bpm") is not None else None,
                "minimal_difference_abs_error_bpm": abs(mmwave_hr - float(minimal["ecg_hr_bpm"])) if mmwave_hr is not None and minimal.get("ecg_hr_bpm") is not None else None,
                "historical_ecg_n_rpeaks": old.get("ecg_n_rpeaks"),
                "current_ecg_n_rpeaks": current.get("ecg_n_rpeaks"),
                "historical_ecg_status": old.get("ecg_status"),
                "current_ecg_status": current.get("ecg_status"),
                "old_alignment": "acq_earliest_marker_created_at_metadata_zero",
                "current_alignment": "per_block_event_marker_to_physical_digital_pulse_affine_fit",
                "old_ecg_start_sample": old_i0,
                "old_ecg_end_sample": old_i1,
                "current_ecg_start_sample": current_i0,
                "current_ecg_end_sample": current_i1,
                "acq_file": str(acq_path),
                "acq_filename_verdict": file_verdict,
                "acq_fs_hz": fs,
                "ecg_channel": "ECG, X, RSPEC-R",
                "marker_channel": "Digital (STP Input 0..7)",
            })
        alignment_rows.append({
            "subject": subject,
            "acq_file": str(acq_path),
            "acq_filename_verdict": file_verdict,
            "acq_start_ms_metadata": acq_start_ms,
            "acq_fs_hz": fs,
            "acq_samples": digital_meta["acq_samples"],
            "ecg_channel": "ECG, X, RSPEC-R",
            "marker_channel": "Digital (STP Input 0..7)",
            "block_count_complete": sum(block["status"] == "complete" for block in blocks),
            "ecg_fit_p95_ms_max": max((safe_float(a.get("ecg_fit_residual_p95_ms")) or 0.0 for a in audits), default=None),
            "mmwave_tick_gap_n_abs_over_100ms": sum(int(a.get("mmwave_tick_gap_n_abs_over_100ms") or 0) for a in audits),
        })
    summary = [metrics(output, "historical"), metrics(output, "current"), metrics(output, "minimal_difference")]
    return output, summary, {"subjects": alignment_rows, "fixed_mmwave_rows": len(fixed)}


def lineage() -> list[dict]:
    rows = []
    common_old = {
        "created_or_modified": "commit timestamp",
        "acq_rule": "bioread first *.acq in subject directory",
        "ecg_channel": "first channel name containing ECG",
        "fs_hz": "datafile sample rate; formal files 2000",
        "marker_channel": "eight Digital (STP Input) lines when used",
        "block_split": "behavior/event block timestamps; varies by script",
        "hr": "median valid IBI, 0.30-2.00 s",
        "windows": "script-specific; historical 60 s probe windows unless caller-defined",
        "mmwave_comparison": "paired existing mmWave output; not ECG feature extraction",
    }
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_MASTER, "scripts/analyze_acq_reference.py", role="historical low-error ECG reference", **common_old, timestamp_offset="acq_start_ms = earliest_marker_created_at; Unix behavior onset converted to acquisition seconds", rpeak="4th-order SOS 5-35 Hz; adaptive MAD/std prominence; distance 0.45 s", outputs="output/20_生理金标准验证/01_历史严格参照_v20260821", historical_result="HR reference used in old 4.590 and corrected-gate 3.777 audit chain", reproducibility="pending artifact-to-commit binding; source verified"))
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_HEAD, "scripts/analyze_acq_reference.py", role="current canonical copy of historical reference script", **common_old, timestamp_offset="same metadata acq zero; not the current targeted marker-affine window mapping", rpeak="same as historical copy", outputs="source only; no new run", historical_result="not independently rerun here", reproducibility="source verified"))
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_MASTER, "scripts/gold_standard_qa.py", role="alternate ECG QA chain", **common_old, timestamp_offset="sample indices supplied by caller; validate_gold_anchor uses marker affine", rpeak="3rd-order SOS 0.5-40 Hz; fixed prominence .25; distance 0.30 s; optional 20% IBI rejection", outputs="gold-anchor QA / validation artifacts", historical_result="not the provenance-confirmed source of 3.777 HR-course value", reproducibility="source verified"))
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_MASTER, "scripts/validate_gold_anchor.py", role="marker-aligned gold-anchor comparison", **common_old, timestamp_offset="longest common suffix of event markers and physical digital pulses; affine fit", rpeak="delegates gold_standard_qa", outputs="gold-anchor validation outputs", historical_result="historical alignment route; no direct 3-session replay result", reproducibility="source verified"))
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_MASTER, "docs/交付/毫米波ECG金标准验证_0816/脚本/calibrate_ecg_mmwave.py", role="older calibration script", **common_old, timestamp_offset="event Unix to physical digital marker affine fit", rpeak="fixed prominence .25; min distance .30 s; 2000 Hz", outputs="calibration reports / old mmWave-ECG probes", historical_result="calibration-era results; not the confirmed source of current 3.777 table", reproducibility="source verified"))
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_REANALYSIS, "pipelines/mmwave/ecg_reference_v1.py", role="frozen radar-blind formal reanalysis reference", **common_old, timestamp_offset="caller-provided mapping; not used for this .acq replay", rpeak="3rd-order .5-40 Hz; positive/negative polarity selection; prominence .25; distance .30 s", outputs="formal reanalysis pipeline module", historical_result="no direct evidence it produced 3.777", reproducibility="source verified"))
    rows.append(source_record(ALGO_ROOT, "greenboo26/focuswave-multimodal-attention-analysis", CANONICAL_HEAD, "scripts/maintenance/run_mmwave_targeted_validation_20260830.py", role="current targeted rerun", **common_old, timestamp_offset="per-block event marker to physical Biopac digital pulse affine fit", rpeak="4th-order SOS 5-35 Hz; adaptive MAD/std prominence; distance .45 s", window_rule="20 s, 10 s step, 5 s boundary guard within complete block", outputs="2026-08-30_MMWAVE_TARGETED_VALIDATION/mmwave_ecg_block_window_comparison.csv", historical_result="current block-local HR MAE 24.885 bpm using local HR output; qualified/provisional pending this audit", reproducibility="source verified"))
    focus_common = {"created_or_modified": "FocusWave commit timestamp", "acq_rule": "experiment writes session-local events.csv", "ecg_channel": "not selected by acquisition program", "fs_hz": "Biopac-side acquisition, observed 2000", "marker_channel": "8-bit parallel marker pulse", "block_split": "segment start/end markers; rest then posture/NIR alignment before next block", "timestamp_offset": "events.csv Unix ms; physical marker pulse in BIOPAC", "rpeak": "not in acquisition program", "hr": "not in acquisition program", "windows": "program block timing", "mmwave_comparison": "provides alignment contract only", "outputs": "events.csv / marker pulses", "historical_result": "acquisition provenance, not a result", "reproducibility": "source verified"}
    for path, role in [("01-MainProgram/core/event_logger.py", "event and tick marker writer"), ("01-MainProgram/core/parallel_marker.py", "physical 8-bit marker pulse writer"), ("01-MainProgram/main_experiment_msmf.py", "block/rest/posture sequencing")]:
        rows.append(source_record(FOCUSWAVE_ROOT, "kyandi233-dev/FocusWave", "ecg", path, role=role, **focus_common))
    rows.append({"repo": "kyandi233-dev/Attention-Analysis", "branch_or_ref": "nvidia-cuda", "commit": ATTENTION_HEAD, "local_path": str(ATTENTION_ROOT), "script_path": "NO_RELEVANT_ECG_MM WAVE_REFERENCE_SCRIPT_FOUND", "role": "inventory result", "created_or_modified": "checked current local branch and available refs", "historical_result": "no relevant ECG/BIOPAC/mmWave reference chain located", "reproducibility": "inventory_only"})
    return rows


def historical_results() -> list[dict]:
    return [
        {"result_id": "historical_old_gate", "artifact": r"D:\Project\厚粲杯\08_算法\output\20_生理金标准验证\01_历史严格参照_v20260821", "cohort": "5 sessions: 97793,97794,97795,97796,9779", "windows": "100 rows / 99 valid HR-course", "window_rule": "60 s behavior-gated probe window", "ecg_reference": "analyze_acq_reference.py; metadata acq zero; 4th-order 5-35 Hz adaptive peaks", "mmwave_side": "05_毫米波参照_FAST; bp_heart; 0.08 m/bin", "hr_mae_bpm": 4.5901917738, "status": "historical reproduced", "comparability_to_current": "not comparable: cohort/window/mmWave gate differ"},
        {"result_id": "historical_corrected_gate", "artifact": r"D:\Project\厚粲杯\08_算法\output\20_生理金标准验证\07_HR_COURSE_99_CORRECTED_GATE_AUDIT", "cohort": "same 5 sessions", "windows": "same 100 rows / 99 valid HR-course", "window_rule": "same 60 s probe keys", "ecg_reference": "same historical ECG reference chain", "mmwave_side": "06_HR_COURSE_99_CORRECTED_GATE; bp_heart; 0.037 m/bin physical gate 0.30-1.50 m", "hr_mae_bpm": 3.7772146, "status": "corrected-gate historical estimate", "comparability_to_current": "not comparable: mmWave target/gate and cohort/window differ"},
        {"result_id": "goldclean_reaudit", "artifact": r"D:\Project\厚粲杯\11_数据\derived\ecg_rsp_goldclean_pairing_v1", "cohort": "source 5-session pairing", "windows": "100 exact source windows", "window_rule": "re-paired existing source windows", "ecg_reference": "re-cleaned ECG/RSP; no mmWave rerun", "mmwave_side": "existing strict output", "hr_mae_bpm": 5.023715, "status": "historical re-pairing", "comparability_to_current": "not comparable: 60 s source windows"},
        {"result_id": "current_targeted_block_local", "artifact": str(RESULT_ROOT), "cohort": "97793,9779,97795", "windows": "335 windows / 327 within-block transitions", "window_rule": "20 s, 10 s step, 5 s guard, complete formal blocks only", "ecg_reference": "current rerun detector with per-block marker-affine mapping", "mmwave_side": "existing producer estimator; block-local target selection", "hr_mae_bpm": 24.885, "status": "provisional pending historical ECG audit; remains qualified after audit", "comparability_to_current": "same targeted run; not comparable to 99-window calibration"},
    ]


def build_report(replay_summary: list[dict], replay_meta: dict, diagnostics: dict) -> str:
    lines = [
        "# Historical ECG reference-chain audit — 2026-08-30",
        "",
        "状态：`PARTIAL / HISTORICAL_ECG_CHAIN_AUDITED_CURRENT_MMWAVE_COMPARISON_QUALIFIED`",
        "",
        "本审计只替换 ECG/BIOPAC 参考链，毫米波端固定读取既有 block-local targeted rerun 的 `local_hr_freq_bpm`；没有重新选择 bin/channel，也没有运行正式全量批处理。原始 `.acq`、NPZ、实验程序、producer、portable V2 与 `Attention-Analysis@codex/formal-analysis-v2-portable` 均未修改。",
        "",
        "## 1. 结论",
        "",
        "- 已确认历史最佳 HR 数值是 5-session/99-valid-window 的 corrected-distance calibration：MAE `3.7772146 bpm`；其 ECG 参考链可追溯到 `scripts/analyze_acq_reference.py`，但毫米波端同时使用了旧/更正距离门，不能当作本轮 3-session、20-s block 结果。",
        "- 历史 `4.5901918 bpm` 是同一 5-session/99-window 链的旧 `0.08 m/bin` gate；该历史表可重现。`3.7772146 bpm` 是只改变毫米波 `0.037 m/bin` gate 后的 corrected-gate estimate，不是 ECG detector 单独带来的改善。",
        "- 三场固定窗口重放使用同一 `local_hr_freq_bpm` 毫米波值。历史 metadata-zero ECG、当前 per-block marker-affine ECG、以及 minimal-difference arm 的 HR reference 结果均已逐窗写入 `ECG_REFERENCE_PIPELINE_COMPARISON.csv`。",
        "- 因历史与当前 detector 的核心 ECG 参数相同（4th-order 5–35 Hz、adaptive prominence、0.45-s minimum distance、0.30–2.00-s IBI），本次差异主要来自 alignment/window/cohort/mmWave-side，而不是已发现的 R-peak detector 改写。",
        "- 最终状态保持 `PARTIAL`：历史链已解释到可复现的脚本和结果层，但当前 `.acq` 文件的 `97795` 目录内文件名为 `97995.acq`，只能确认目录/通道/marker/采样长度的一致性，不能从文件名本身证明被试 ID；同时 mmWave timestamp gaps 和历史/当前毫米波估计器不同，不能宣称一个统一的 cross-era MAE。",
        "",
        "## 2. Fixed replay summary",
        "",
        "| ECG arm | n | MAE vs fixed mmWave HR (bpm) | median absolute error | bias (mmWave−ECG) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in replay_summary:
        lines.append(f"| {row['pipeline']} | {row['n']} | {row['mae_bpm']} | {row['median_abs_error_bpm']} | {row['bias_mmwave_minus_ecg_bpm']} |")
    lines += [
        "",
        "重放表中的 `historical` 与 `minimal_difference` 在本实现中使用同一 metadata-zero sample mapping；这是有意的 isolation arm，显示当前 ECG detector 相对历史 `analyze_acq_reference` detector 没有产生另一个独立结果。`current` 才使用本轮每个 block 的 physical-marker affine mapping。",
        f"逐窗比较显示 old→current ECG HR 在 {diagnostics['changed_n']}/{diagnostics['n']} 窗发生数值变化，变化的中位绝对值为 {diagnostics['median_abs_delta_bpm']} bpm、最大绝对值为 {diagnostics['max_abs_delta_bpm']} bpm；current−old 的平均变化为 {diagnostics['mean_delta_current_minus_old_bpm']} bpm。reference alignment 有可测但很小的逐窗影响，不能解释约 24.9 bpm 级别的毫米波误差。",
        "",
        "## 3. Alignment audit",
        "",
        "- OLD_ALIGNMENT：`(event_unix_ms − earliest_marker_created_at) × fs/1000`，对应历史 `analyze_acq_reference.py` 的 acquisition-zero 规则。",
        "- CURRENT_ALIGNMENT：每个 block 单独用 `events.csv` 的 program marker 与 BIOPAC 8-bit digital pulse 做 affine fit；不跨 rest、坐姿调整或 block boundary 借用 mapping。",
        f"- 本次固定重放读取 {replay_meta['fixed_mmwave_rows']} 个已有 mmWave comparison rows；每个 block 重新查找对应 `.acq` ECG 和 block mapping。",
        "- 三场均为 2000 Hz，ECG 通道为 `ECG, X, RSPEC-R`，marker 通道为 `Digital (STP Input 0..7)`。",
        "- `97795` 使用 `D:\\acq_mmwave_data\\sub-97795_\\97995.acq`；没有重命名或复制它。审计分类为 `directory_subject_matches_basename_typo`，不是把文件名错误升级为生理数据错配。",
        "- mmWave tick gap 统计和 ECG marker mismatch 仍保留在既有 `ecg_alignment_audit.csv`；它们限制双机时间轴的最终闭合，但不改变本次 ECG reference replay 的 block-local reset 规则。",
        "",
        "## 4. Historical result lineage and decision",
        "",
        "`ECG_SCRIPT_LINEAGE.csv` 区分了 canonical `master` 历史脚本、当前 `main` 同名副本、alternate `gold_standard_qa`/`validate_gold_anchor`、formal reanalysis reference、FocusWave acquisition marker source，以及 Attention-Analysis 的无相关脚本盘点。",
        "",
        "历史 `3.777` 应保留为：`corrected-distance calibration result, ECG reference chain reproducible, not transferable to current block-local run`。历史 `4.590` 应保留为：`old-distance-gate historical reproduction`。当前 `24.885` 应保留为：`current 20-s block-local diagnostic MAE, qualified/provisional, not formal HR validity`。",
        "",
        "## 5. Scope and next gate",
        "",
        "HR/BR 继续 `HOLD`，HRV 继续 `BLOCKED`；没有运行 #16、C2B/C2C、HRV 新算法或全量 formal batch。下一步若要闭合，需要在同一冻结毫米波输出和同一 block/window contract 下，取得可证明等价的历史/当前 reference mapping，或明确重新定义一套只用于当前 block 的 reference benchmark；本审计不擅自选择其中之一。",
        "",
        "## 6. Files",
        "",
        "- `ECG_SCRIPT_LINEAGE.csv` — script/branch/commit and parameter lineage",
        "- `ECG_HISTORICAL_RESULT_PROVENANCE.csv` — historical MAE denominator and comparability",
        "- `ECG_REFERENCE_PIPELINE_COMPARISON.csv` — fixed mmWave, old/current/minimal ECG per-window replay",
        "- `ECG_REFERENCE_PIPELINE_SUMMARY.csv` — descriptive replay metrics",
        "- `ECG_REFERENCE_ALIGNMENT_AUDIT.csv` — OLD_ALIGNMENT vs CURRENT_ALIGNMENT and `.acq` mapping audit",
        "- `ECG_REFERENCE_AUDIT_MANIFEST.json` — inputs, exclusions, hashes and status",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    rerun = import_rerun_module()
    replay, replay_summary, replay_meta = replay_fixed_windows(rerun)
    diagnostics = comparison_diagnostics(replay)
    write_csv(RESULT_ROOT / "ECG_REFERENCE_PIPELINE_COMPARISON.csv", replay)
    write_csv(RESULT_ROOT / "ECG_REFERENCE_PIPELINE_SUMMARY.csv", replay_summary)
    write_csv(RESULT_ROOT / "ECG_REFERENCE_ALIGNMENT_AUDIT.csv", replay_meta["subjects"])
    write_csv(RESULT_ROOT / "ECG_SCRIPT_LINEAGE.csv", lineage())
    write_csv(RESULT_ROOT / "ECG_HISTORICAL_RESULT_PROVENANCE.csv", historical_results())
    report_path = RESULT_ROOT / "ECG_REFERENCE_AUDIT_REPORT_2026-08-30.md"
    report_path.write_text(build_report(replay_summary, replay_meta, diagnostics), encoding="utf-8")
    outputs = [
        "ECG_SCRIPT_LINEAGE.csv",
        "ECG_HISTORICAL_RESULT_PROVENANCE.csv",
        "ECG_REFERENCE_PIPELINE_COMPARISON.csv",
        "ECG_REFERENCE_PIPELINE_SUMMARY.csv",
        "ECG_REFERENCE_ALIGNMENT_AUDIT.csv",
        "ECG_REFERENCE_AUDIT_REPORT_2026-08-30.md",
    ]
    manifest = {
        "status": "PARTIAL / HISTORICAL_ECG_CHAIN_AUDITED_CURRENT_MMWAVE_COMPARISON_QUALIFIED",
        "canonical_main_commit_verified": CANONICAL_HEAD,
        "acquisition_repo": "kyandi233-dev/FocusWave",
        "acquisition_branch": "ecg",
        "acquisition_commit": FOCUSWAVE_ECG,
        "analysis_set": list(SUBJECTS),
        "fixed_mmwave_input": str(FIXED_MM_FILE),
        "fixed_mmwave_input_sha256": sha256_bytes(FIXED_MM_FILE.read_bytes()),
        "fixed_mmwave_field": "local_hr_freq_bpm",
        "replay_rows": len(replay),
        "replay_summary": replay_summary,
        "comparison_diagnostics": diagnostics,
        "old_alignment": "acq earliest_marker_created_at metadata zero",
        "current_alignment": "per-block events.csv marker to physical BIOPAC digital pulse affine fit",
        "excluded": ["Issue #16", "C2B", "C2C", "new HRV algorithm", "full formal batch", "producer modification", "portable V2 modification", "Attention-Analysis codex/formal-analysis-v2-portable modification", "raw data modification"],
        "historical_result_provenance": historical_results(),
        "outputs": [{"path": name, "sha256": sha256_bytes((RESULT_ROOT / name).read_bytes())} for name in outputs],
    }
    (RESULT_ROOT / "ECG_REFERENCE_AUDIT_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "replay_rows": len(replay), "summary": replay_summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
