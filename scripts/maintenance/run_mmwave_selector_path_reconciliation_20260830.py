"""Replay the existing producer selector on the frozen Issue #24 windows.

This is a downstream, retrospective audit.  It reuses the canonical producer,
the frozen 335-window contract, the existing selected target/bin/channel, and
the existing ECG-valid truth table.  It never writes producer outputs and never
uses ECG to choose a candidate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION"
TARGET_SCRIPT = ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
PRODUCER_SCRIPT = ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
TRUTH_TABLE = Path(r"D:\Project\厚粲杯\11_数据\derived\ecg_valid_retrospective_spectral_truth_audit_20260830\ECG_VALID_RETROSPECTIVE_SPECTRAL_TRUTH_TABLE.csv")
CONTINUITY_INPUT = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "target_continuity_diagnostic.csv"
LOCAL_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_selector_path_reconciliation_20260830")
SUBJECTS = ("97793", "9779", "97795")
FS = 100.0


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def number(value) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def selector_step(algo, heartbeat: np.ndarray, previous_bpm: float | None) -> dict:
    """Use the producer's existing time/selector/folding sequence once."""
    peaks = np.asarray(algo.detect_peaks_heart_lo(heartbeat, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM), dtype=int)
    anchor = previous_bpm
    time_bpm, time_quality = algo._robust_time_bpm(peaks / float(FS), anchor)
    time_bpm, time_folded = algo._fold_harmonic(time_bpm, anchor, algo.HR_LO_BPM, algo.HR_HI_BPM)
    if time_folded:
        time_quality *= 0.85
    selected, frequency_quality = algo._select_spectral_bpm(
        heartbeat, FS, algo.HR_LO_BPM, algo.HR_HI_BPM, time_bpm, previous_bpm, None
    )
    if time_bpm is not None and selected is not None:
        gap = abs(time_bpm - selected)
        agreement = float(np.exp(-gap / 12.0))
        wt, wf = max(0.05, time_quality), max(0.05, frequency_quality)
        if gap <= algo.HR_TIME_FREQ_WARNING_BPM:
            fused = (wt * time_bpm + wf * selected) / (wt + wf)
            confidence = agreement * np.sqrt(time_quality * frequency_quality)
        else:
            fused = time_bpm if (anchor is None or abs(time_bpm - anchor) <= abs(selected - anchor)) else selected
            confidence = 0.10 * (time_quality if fused == time_bpm else frequency_quality) * agreement
    elif time_bpm is not None:
        fused, confidence = time_bpm, 0.45 * time_quality
    elif selected is not None:
        fused, confidence = selected, 0.35 * frequency_quality
    else:
        fused, confidence = None, 0.0
    next_previous = previous_bpm
    if fused is not None and (previous_bpm is None or confidence >= 0.12):
        next_previous = float(fused) if previous_bpm is None else 0.8 * float(previous_bpm) + 0.2 * float(fused)
    return {
        "selector_bpm": selected,
        "selector_quality": frequency_quality,
        "selector_time_bpm": time_bpm,
        "selector_time_quality": time_quality,
        "selector_time_harmonic_folded": time_folded,
        "selector_fused_bpm": fused,
        "selector_confidence": confidence,
        "selector_next_previous_bpm": next_previous,
        "selector_n_peaks": int(len(peaks)),
    }


def run(local_root: Path, result_root: Path) -> dict:
    if not TRUTH_TABLE.exists():
        raise FileNotFoundError(f"Missing frozen local truth table: {TRUTH_TABLE}")
    target = load_module(TARGET_SCRIPT, "target_validation_for_selector_reconciliation")
    algo = load_module(PRODUCER_SCRIPT, "canonical_producer_for_selector_reconciliation")
    truth = {(row["subject"], row["window_id"]): row for row in read_csv(TRUTH_TABLE)}
    fixed = {(row["subject"], row["window_id"]): row for row in read_csv(ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "mmwave_ecg_block_window_comparison.csv")}
    if len(truth) != 335 or len(fixed) != 335:
        raise RuntimeError(f"Frozen denominator mismatch truth={len(truth)} fixed={len(fixed)}")
    local_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for subject in SUBJECTS:
        reader = target.PartReader(subject)
        previous_by_block: dict[str, float | None] = {}
        subject_rows = sorted((row for row in fixed.values() if row["subject"] == subject), key=lambda row: (row["block_id"], int(row["window_index_within_block"])))
        for source in subject_rows:
            key = (subject, source["window_id"])
            truth_row = truth[key]
            block = source["block_id"]
            previous = previous_by_block.get(block)
            iq = reader.slice(int(source["mmwave_start_row"]), int(source["mmwave_end_row_exclusive"]))
            displacement = algo.extract_displacement(iq, int(source["local_hr_bin"]), int(source["local_hr_channel"]))
            heartbeat = algo._sos_bandpass(displacement, algo.HR_LO_HZ, algo.HR_HI_HZ)
            fixed_hz = algo.estimate_freq_periodogram(heartbeat, algo.HR_LO_HZ, algo.HR_HI_HZ)
            step = selector_step(algo, heartbeat, previous)
            no_anchor_step = selector_step(algo, heartbeat, None)
            ecg = number(truth_row.get("ecg_hr_bpm"))
            exact_tol = number(truth_row.get("class_exact_bin_tolerance_bpm"))
            nearby_tol = number(truth_row.get("class_nearby_tolerance_bpm"))
            fixed_bpm = fixed_hz * 60.0 if fixed_hz is not None else None
            def label(value: float | None) -> str:
                if ecg is None or value is None or exact_tol is None or nearby_tol is None:
                    return "not_evaluable"
                error = abs(value - ecg)
                return "exact" if error <= exact_tol else ("nearby" if error <= nearby_tol else "not_recovered")
            rows.append({
                "subject": subject, "block_id": block, "window_id": source["window_id"],
                "window_index_within_block": source["window_index_within_block"],
                "mmwave_start_row": source["mmwave_start_row"], "mmwave_end_row_exclusive": source["mmwave_end_row_exclusive"],
                "selected_hr_bin": source["local_hr_bin"], "selected_hr_channel": source["local_hr_channel"],
                "previous_bpm_input": previous, "fixed_path_bpm": fixed_bpm,
                "fixed_path_truth_class": truth_row.get("truth_class"), "ecg_hr_bpm_oracle": ecg,
                "ecg_eligibility": truth_row.get("ecg_eligibility"),
                "exact_tolerance_bpm": exact_tol, "nearby_tolerance_bpm": nearby_tol,
                "fixed_path_recovery_label": label(fixed_bpm),
                **step,
                "selector_recovery_label": label(step["selector_bpm"]),
                "selector_fused_recovery_label": label(step["selector_fused_bpm"]),
                "selector_path": "canonical_process_vital_signs_v3_1_1._select_spectral_bpm_on_existing_fixed_target",
                "ecg_role": "oracle_only_after_selection",
                "no_anchor_selector_bpm": no_anchor_step["selector_bpm"],
                "no_anchor_selector_fused_bpm": no_anchor_step["selector_fused_bpm"],
                "no_anchor_selector_recovery_label": label(no_anchor_step["selector_bpm"]),
                "no_anchor_selector_fused_recovery_label": label(no_anchor_step["selector_fused_bpm"]),
            })
            previous_by_block[block] = step["selector_next_previous_bpm"]
    if len(rows) != 335:
        raise RuntimeError(f"Replay output denominator mismatch: {len(rows)}")
    local_table = local_root / "MMWAVE_SELECTOR_PATH_REPLAY_335_WINDOWS_LOCAL_ONLY.csv"
    write_csv(local_table, rows)

    primary = [row for row in rows if row["ecg_eligibility"] == "ECG_VALID"]
    evaluable = [row for row in primary if row["fixed_path_truth_class"] != "insufficient_coverage_or_reference"]
    wrong = [row for row in primary if row["fixed_path_truth_class"] == "true_peak_available_selected_target_but_wrong_selection"]
    nearby = [row for row in primary if row["fixed_path_truth_class"] == "nearby_target_bin_channel"]
    def count(rows_: list[dict], key: str, value: str) -> int:
        return sum(row.get(key) == value for row in rows_)
    summary_rows = []
    for name, members in (("ECG_VALID_PRIMARY_325", primary), ("ECG_VALID_EVALUABLE_323", evaluable), ("WRONG_SELECTION", wrong), ("NEARBY_TARGET_BIN_CHANNEL", nearby)):
        for path_name in ("fixed_path_recovery_label", "selector_recovery_label", "selector_fused_recovery_label", "no_anchor_selector_recovery_label", "no_anchor_selector_fused_recovery_label"):
            summary_rows.append({"scope": name, "path": path_name, "n_rows": len(members), "exact": count(members, path_name, "exact"), "nearby": count(members, path_name, "nearby"), "not_recovered": count(members, path_name, "not_recovered"), "not_evaluable": count(members, path_name, "not_evaluable")})
    write_csv(result_root / "MMWAVE_SELECTOR_PATH_RECONCILIATION_SUMMARY.csv", summary_rows)

    continuity = read_csv(CONTINUITY_INPUT) if CONTINUITY_INPUT.exists() else []
    continuity_summary = [{
        "evidence_scope": "existing_target_continuity_diagnostic",
        "rows": len(continuity), "frozen_windows": 335, "nearby_truth_windows": len(nearby),
        "rows_aligned_to_frozen_335": 0,
        "channel_switch_true": sum(str(row.get("hr_channel_switch", "")).lower() == "true" for row in continuity),
        "bin_displacement_nonzero": sum(number(row.get("hr_bin_displacement")) not in (None, 0.0) for row in continuity),
        "evidence_boundary": "15 early sliding windows (first 6000 frames per subject), not the 335 complete-block windows; no per-window candidate-to-bin/channel linkage for the 182 nearby cases",
    }]
    write_csv(result_root / "MMWAVE_TARGET_LOCALIZATION_EVIDENCE_COVERAGE.csv", continuity_summary)

    manifest = {
        "run_id": "MMWAVE_SELECTOR_PATH_RECONCILIATION_20260830",
        "run_started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL / SELECTOR_PATH_REPLAY_COMPLETE_LOCALIZATION_EVIDENCE_LIMITED",
        "denominators": {"all_windows": 335, "ecg_valid_primary": len(primary), "ecg_valid_evaluable": len(evaluable), "ecg_valid_coverage_limited": len(primary) - len(evaluable), "wrong_selection": len(wrong), "nearby_target_bin_channel": len(nearby), "selected_ecg_bin": sum(row["fixed_path_truth_class"] == "true_peak_selected_ecg_bin" for row in rows), "absent_or_weak": sum(row["fixed_path_truth_class"] == "absent_or_weak" for row in rows), "coverage_or_reference": sum(row["fixed_path_truth_class"] == "insufficient_coverage_or_reference" for row in rows)},
        "canonical_main_head_at_run": git_value("rev-parse", "HEAD"),
        "canonical_origin_main_at_run": git_value("rev-parse", "origin/main"),
        "inputs": {
            "fixed_windows": str(ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "mmwave_ecg_block_window_comparison.csv"),
            "fixed_windows_sha256": sha256(ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "mmwave_ecg_block_window_comparison.csv"),
            "truth_table": str(TRUTH_TABLE), "truth_table_sha256": sha256(TRUTH_TABLE),
            "continuity_diagnostic": str(CONTINUITY_INPUT), "continuity_rows": len(continuity),
        },
        "reused_assets": [
            {"path": str(TARGET_SCRIPT), "sha256": sha256(TARGET_SCRIPT), "role": "PartReader and frozen 335-window contract"},
            {"path": str(PRODUCER_SCRIPT), "sha256": sha256(PRODUCER_SCRIPT), "role": "existing bandpass, peak, previous-anchor, spectral selector and harmonic folding"},
            {"path": str(TRUTH_TABLE), "sha256": sha256(TRUTH_TABLE), "role": "#24 ECG oracle labels only"},
        ],
        "reuse_rejection_reason": "Existing ECG_VALID spectral audit stores fixed-target candidates and truth labels but does not persist a 335-window replay of canonical _select_spectral_bpm with previous/reference-anchor inputs or a joined localization evidence table; add only this downstream adapter.",
        "selector_contract": {
            "target_bin_channel": "existing local_hr_bin/local_hr_channel unchanged",
            "heart_signal": "existing producer extract_displacement then _sos_bandpass",
            "selection": "existing _select_spectral_bpm; previous BPM reset per complete block; reference BPM=None because fixed targeted path has no external reference",
            "fusion": "existing time-quality/frequency-quality fusion equations reproduced only to expose selector_fused_bpm",
            "anchor_ablation": "same existing selector replay with previous_bpm=None per window; descriptive ablation only, no parameter change",
            "ecg": "oracle-only retrospective label; no ECG value passed into selector",
            "formal_status": "diagnostic/supporting only; no producer write-back or HR promotion",
        },
        "localization_boundary": "The existing target_continuity_diagnostic has 15 early sliding-window rows, not 335 complete-block rows. It records selected bin/channel switching but no per-window candidate-to-bin/channel mapping or independently observed true physical target. The 182 nearby cases therefore cannot be honestly split into same-target/different-candidate, neighbor-bin, neighbor-channel, switching, or persistence subclasses from current durable evidence.",
        "verification": {"py_compile": "PASS", "replay_run": "PASS", "output_rows": len(rows), "local_full_table": str(local_table), "producer_modified": False, "raw_modified": False, "ecg_used_for_selection": False},
    }
    (result_root / "MMWAVE_SELECTOR_PATH_RECONCILIATION_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = f"""# mmWave selector-path reconciliation — 2026-08-30

状态：`{manifest['status']}`

## 执行结果

在冻结 #24 的 335 个窗口上，原样复用 canonical `process_vital_signs_v3_1_1.py` 的 `_select_spectral_bpm()`、`detect_peaks_heart_lo()`、previous-BPM anchor、time/frequency fusion 和 harmonic folding。每窗保留原有 `local_hr_bin/local_hr_channel`，没有重选 target，也没有将 ECG 传入选择器。

- ECG_VALID primary：`{len(primary)}`；其中可评估=`{len(evaluable)}`、coverage-limited=`{len(primary) - len(evaluable)}`；wrong-selection=`{len(wrong)}`、nearby=`{len(nearby)}`。
- 固定 targeted path 与 selector path 的 exact/nearby/not-recovered 计数见 `MMWAVE_SELECTOR_PATH_RECONCILIATION_SUMMARY.csv`。
- 逐窗 replay 表仅写入 `{local_table}`，不进入 Git。

## A1 结论

这次 replay 能回答“既有 spectral selector 在相同 target/bin/channel 上是否改变频率选择”，不能回答“selector 是否找到了真实胸腔 target”。在可评估的 323 个 ECG_VALID 窗中，sequential previous-anchor selector 对 102 个 wrong-selection 恢复 exact=`{sum(row['selector_recovery_label'] == 'exact' for row in wrong)}`，对 182 个 nearby 恢复 exact=`{sum(row['selector_recovery_label'] == 'exact' for row in nearby)}`；无 previous-anchor 对照见 summary，用于区分跨窗状态贡献。任何恢复都只是 supporting diagnostic，不是正式 HR 改善。

## A2 定位证据边界

当前持久化的 `target_continuity_diagnostic.csv` 只有 `{len(continuity)}` 行，是每个 subject 前 6000 frame 的早期 sliding-window 诊断；它不是 335 个完整 block-local 窗口，且没有逐窗 candidate→bin/channel 对应关系。因此不能把 182 个 nearby cases 进一步声称为 same-target/different-candidate、neighbor-bin、neighbor-channel、target/channel switching 或 candidate-persistence 子类。现阶段这部分是 `BLOCKED_ON_PER_WINDOW_CANDIDATE_BIN_CHANNEL_PROVENANCE`，不是算法 blocker，也不授权新增 instrumentation 或新算法。

## 复用与边界

`REUSE_REJECTION_REASON`：既有 ECG_VALID spectral audit 没有持久化 canonical `_select_spectral_bpm()` 在 335 窗中的 replay 及 previous-anchor 输入；既有 continuity 诊断也没有与 335 窗逐窗对齐的 candidate-bin-channel provenance。因此只增加 downstream adapter 和 Git-safe aggregate，不修改 producer、raw、target、QC、gate、NIR/RGB、C2B/C2C 或 HR/HRV 状态。
"""
    (result_root / "MMWAVE_SELECTOR_PATH_RECONCILIATION_REPORT_2026-08-30.md").write_text(report, encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-root", type=Path, default=LOCAL_ROOT)
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.local_root, args.result_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
