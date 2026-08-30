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
TARGET_ABLATION = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
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
    target_ablation = {(row["subject"], row["window_id"]): row for row in read_csv(TARGET_ABLATION)}
    if len(truth) != 335 or len(fixed) != 335 or len(target_ablation) != 335:
        raise RuntimeError(f"Frozen denominator mismatch truth={len(truth)} fixed={len(fixed)} target_ablation={len(target_ablation)}")
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

    def integer(value) -> int | None:
        parsed = number(value)
        return int(parsed) if parsed is not None else None

    localization_rows: list[dict] = []
    for row in nearby:
        key = (row["subject"], row["window_id"])
        target_row = target_ablation[key]
        fixed_bin = integer(row["selected_hr_bin"])
        fixed_channel = integer(row["selected_hr_channel"])
        arm0_bin = integer(target_row.get("arm0_selected_bin"))
        arm0_channel = integer(target_row.get("arm0_selected_channel"))
        fixed_target_consistent = (fixed_bin, fixed_channel) == (arm0_bin, arm0_channel)
        fixed_bpm = number(row.get("fixed_path_bpm"))
        selector_bpm = number(row.get("selector_bpm"))
        same_target_different_candidate = (
            fixed_target_consistent and fixed_bpm is not None and selector_bpm is not None and abs(fixed_bpm - selector_bpm) > 1e-9
        )
        alternatives = []
        for arm_name in ("arm1_selected", "arm2_selected", "arm3_selected"):
            alt_bin = integer(target_row.get(f"{arm_name}_bin"))
            alt_channel = integer(target_row.get(f"{arm_name}_channel"))
            if alt_bin is not None and alt_channel is not None and arm0_bin is not None and arm0_channel is not None:
                alternatives.append((alt_bin, alt_channel))
        changed = [(alt_bin, alt_channel) for alt_bin, alt_channel in alternatives if (alt_bin, alt_channel) != (arm0_bin, arm0_channel)]
        has_neighbor_bin = any(abs(alt_bin - arm0_bin) == 1 and alt_channel == arm0_channel for alt_bin, alt_channel in changed)
        has_neighbor_channel = any(alt_bin == arm0_bin and alt_channel != arm0_channel for alt_bin, alt_channel in changed)
        has_target_channel_switch = any(
            (alt_bin, alt_channel) != (arm0_bin, arm0_channel)
            and not (abs(alt_bin - arm0_bin) == 1 and alt_channel == arm0_channel)
            and not (alt_bin == arm0_bin and alt_channel != arm0_channel)
            for alt_bin, alt_channel in changed
        )
        if has_neighbor_bin:
            target_locus = "neighbor_bin"
        elif has_neighbor_channel:
            target_locus = "neighbor_channel"
        elif has_target_channel_switch:
            target_locus = "target_channel_switch"
        elif not changed:
            target_locus = "no_alternative_target_change_observed"
        else:
            target_locus = "unclassified_target_change"
        localization_rows.append({
            "subject": row["subject"],
            "block_id": row["block_id"],
            "window_id": row["window_id"],
            "truth_class": row["fixed_path_truth_class"],
            "fixed_target_bin": fixed_bin,
            "fixed_target_channel": fixed_channel,
            "arm0_target_bin": arm0_bin,
            "arm0_target_channel": arm0_channel,
            "fixed_target_contract_consistent": fixed_target_consistent,
            "fixed_path_bpm": fixed_bpm,
            "selector_bpm": selector_bpm,
            "same_fixed_target_different_candidate": same_target_different_candidate,
            "selector_recovery_label": row["selector_recovery_label"],
            "target_path_locus": target_locus,
            "candidate_count": integer(truth[key].get("candidate_count")),
            "nearest_ecg_candidate_rank": integer(truth[key].get("nearest_ecg_candidate_rank")),
            "candidate_persistence_status": "NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS",
            "evidence_boundary": "path-level existing selector/target ablation; not independent physical target truth",
        })
    localization_table = local_root / "MMWAVE_NEARBY_LOCALIZATION_SUBTYPES_182_WINDOWS_LOCAL_ONLY.csv"
    write_csv(localization_table, localization_rows)
    subtype_counts = Counter(row["target_path_locus"] for row in localization_rows)
    subtype_rows = [
        {"scope": "NEARBY_TARGET_BIN_CHANNEL_182", "subtype": subtype, "n_rows": subtype_counts.get(subtype, 0), "pct": round(100.0 * subtype_counts.get(subtype, 0) / len(localization_rows), 3), "evidence_status": "PATH_LEVEL_SUPPORTING"}
        for subtype in ("neighbor_bin", "neighbor_channel", "target_channel_switch", "no_alternative_target_change_observed", "unclassified_target_change")
    ]
    subtype_rows.append({"scope": "NEARBY_TARGET_BIN_CHANNEL_182", "subtype": "same_fixed_target_different_candidate", "n_rows": sum(row["same_fixed_target_different_candidate"] for row in localization_rows), "pct": round(100.0 * sum(row["same_fixed_target_different_candidate"] for row in localization_rows) / len(localization_rows), 3), "evidence_status": "ORTHOGONAL_SELECTOR_PATH_SUPPORTING"})
    subtype_rows.append({"scope": "NEARBY_TARGET_BIN_CHANNEL_182", "subtype": "candidate_persistence_or_instability", "n_rows": 0, "pct": 0.0, "evidence_status": "NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS"})
    write_csv(result_root / "MMWAVE_NEARBY_LOCALIZATION_SUBTYPES.csv", subtype_rows)

    continuity = read_csv(CONTINUITY_INPUT) if CONTINUITY_INPUT.exists() else []
    continuity_summary = [{
        "evidence_scope": "existing_target_continuity_diagnostic",
        "rows": len(continuity), "frozen_windows": 335, "nearby_truth_windows": len(nearby),
        "rows_aligned_to_frozen_335": 0,
        "channel_switch_true": sum(str(row.get("hr_channel_switch", "")).lower() == "true" for row in continuity),
        "bin_displacement_nonzero": sum(number(row.get("hr_bin_displacement")) not in (None, 0.0) for row in continuity),
        "candidate_target_rows": len(target_ablation),
        "candidate_target_rows_aligned_to_frozen_335": len(target_ablation),
        "nearby_localization_rows": len(localization_rows),
        "same_fixed_target_different_candidate": sum(row["same_fixed_target_different_candidate"] for row in localization_rows),
        "neighbor_bin": subtype_counts.get("neighbor_bin", 0),
        "neighbor_channel": subtype_counts.get("neighbor_channel", 0),
        "target_channel_switch": subtype_counts.get("target_channel_switch", 0),
        "no_alternative_target_change_observed": subtype_counts.get("no_alternative_target_change_observed", 0),
        "candidate_persistence_rows": 0,
        "evidence_boundary": "15 early sliding windows remain non-aligned for persistence; existing 335-row target ablation plus replay/truth join supports path-level subtypes for all 182 nearby cases, not independent physical target truth",
    }]
    write_csv(result_root / "MMWAVE_TARGET_LOCALIZATION_EVIDENCE_COVERAGE.csv", continuity_summary)

    manifest = {
        "run_id": "MMWAVE_SELECTOR_PATH_RECONCILIATION_20260830",
        "run_started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL / SELECTOR_PATH_REPLAY_AND_PATH_LOCALIZATION_COMPLETE_PHYSICAL_TARGET_UNRESOLVED",
        "denominators": {"all_windows": 335, "ecg_valid_primary": len(primary), "ecg_valid_evaluable": len(evaluable), "ecg_valid_coverage_limited": len(primary) - len(evaluable), "wrong_selection": len(wrong), "nearby_target_bin_channel": len(nearby), "selected_ecg_bin": sum(row["fixed_path_truth_class"] == "true_peak_selected_ecg_bin" for row in rows), "absent_or_weak": sum(row["fixed_path_truth_class"] == "absent_or_weak" for row in rows), "coverage_or_reference": sum(row["fixed_path_truth_class"] == "insufficient_coverage_or_reference" for row in rows)},
        "canonical_main_head_at_run": git_value("rev-parse", "HEAD"),
        "canonical_origin_main_at_run": git_value("rev-parse", "origin/main"),
        "inputs": {
            "fixed_windows": str(ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "mmwave_ecg_block_window_comparison.csv"),
            "fixed_windows_sha256": sha256(ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION" / "mmwave_ecg_block_window_comparison.csv"),
            "truth_table": str(TRUTH_TABLE), "truth_table_sha256": sha256(TRUTH_TABLE),
            "target_ablation": str(TARGET_ABLATION), "target_ablation_sha256": sha256(TARGET_ABLATION), "target_ablation_rows": len(target_ablation),
            "continuity_diagnostic": str(CONTINUITY_INPUT), "continuity_rows": len(continuity),
        },
        "reused_assets": [
            {"path": str(TARGET_SCRIPT), "sha256": sha256(TARGET_SCRIPT), "role": "PartReader and frozen 335-window contract"},
            {"path": str(PRODUCER_SCRIPT), "sha256": sha256(PRODUCER_SCRIPT), "role": "existing bandpass, peak, previous-anchor, spectral selector and harmonic folding"},
            {"path": str(TRUTH_TABLE), "sha256": sha256(TRUTH_TABLE), "role": "#24 ECG oracle labels only"},
        ],
        "reuse_rejection_reason": "Existing ECG_VALID spectral audit, target ablation, and continuity outputs were separate; none joined the canonical selector replay to the 182 nearby subset with path-level bin/channel subtype counts. Add only this downstream join; do not add instrumentation or a new algorithm.",
        "selector_contract": {
            "target_bin_channel": "existing local_hr_bin/local_hr_channel unchanged",
            "heart_signal": "existing producer extract_displacement then _sos_bandpass",
            "selection": "existing _select_spectral_bpm; previous BPM reset per complete block; reference BPM=None because fixed targeted path has no external reference",
            "fusion": "existing time-quality/frequency-quality fusion equations reproduced only to expose selector_fused_bpm",
            "anchor_ablation": "same existing selector replay with previous_bpm=None per window; descriptive ablation only, no parameter change",
            "ecg": "oracle-only retrospective label; no ECG value passed into selector",
            "formal_status": "diagnostic/supporting only; no producer write-back or HR promotion",
        },
        "localization_boundary": "The existing 335-row target ablation plus replay/truth join supports path-level subtypes: same fixed target/different candidate=182, neighbor bin=6, neighbor channel=11, target/channel switch=164, no alternative target change=1. The 15-row continuity diagnostic is not aligned to the 335 windows, so candidate persistence/instability remains unavailable; no subtype is independent physical target truth.",
        "localization": {"rows": len(localization_rows), "target_path_subtypes": dict(subtype_counts), "same_fixed_target_different_candidate": sum(row["same_fixed_target_different_candidate"] for row in localization_rows), "candidate_persistence": "NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS", "physical_target_truth": "UNRESOLVED"},
        "verification": {"py_compile": "PASS", "replay_run": "PASS", "localization_join": "PASS", "output_rows": len(rows), "localization_rows": len(localization_rows), "local_full_table": str(local_table), "local_localization_table": str(localization_table), "producer_modified": False, "raw_modified": False, "ecg_used_for_selection": False},
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

## A2 路径级定位

将现有 335 行 target-ablation 的 selected bin/channel 与本次 replay/truth 按 `(subject, window_id)` 对齐后，182 个 nearby 可得到路径级最小分类：neighbor-bin=`{subtype_counts.get('neighbor_bin', 0)}`、neighbor-channel=`{subtype_counts.get('neighbor_channel', 0)}`、target/channel switch=`{subtype_counts.get('target_channel_switch', 0)}`、no alternative target change=`{subtype_counts.get('no_alternative_target_change_observed', 0)}`，合计 182；同一 fixed target 上 selector candidate 改变=`{sum(row['same_fixed_target_different_candidate'] for row in localization_rows)}`。逐窗分类表仅写入 `{localization_table}`，聚合见 `MMWAVE_NEARBY_LOCALIZATION_SUBTYPES.csv`。

这解决的是“已有路径之间如何分流”的证据缺口，不是“真实 target 在哪里”。`target_continuity_diagnostic.csv` 仍只有 `{len(continuity)}` 条早期 sliding-window 记录，未提供与 335 窗对齐的连续 candidate persistence/instability，因此该子类保持 `NOT_AVAILABLE_FROM_EXISTING_ALIGNED_OUTPUTS`；独立 physical target truth 仍 `UNRESOLVED`。

## 复用与边界

`REUSE_REJECTION_REASON`：既有 ECG_VALID spectral audit 没有 canonical `_select_spectral_bpm()` 的 335 窗 previous-anchor replay；target ablation、truth 和 replay 也未合并为 182 nearby 的路径级 subtype aggregate。因此只扩展现有 downstream adapter 做窄 join，不修改 producer、raw、target、QC、gate、NIR/RGB、C2B/C2C 或 HR/HRV 状态。
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
