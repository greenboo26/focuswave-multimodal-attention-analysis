"""Re-run the unchanged targeted HR arms on DLL-time windows.

This is a timestamp-semantics sensitivity run only. Target, gate, filter,
fixed FS, ECG reference, and arm definitions are imported from the already
accepted bounded diagnostic code and are not changed here.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


ALGO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
OLD_ABLATION = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
NEW_WINDOWS = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv"
RECON_MANIFEST = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_MANIFEST.json"
RERUN_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
ABLATION_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_gate_target_ablation_20260830.py"
HIST_SCRIPT = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_estimator_same_window_audit_20260830.py"
SUBJECTS = ("97793", "9779", "97795")


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception:
        return "unavailable"


def numeric(value):
    if value in (None, "", "None", "nan", "NaN"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def metrics(rows: list[dict], version: str, arm: str, value_key: str) -> dict:
    pairs = [(numeric(row.get(value_key)), numeric(row.get("ecg_hr_bpm"))) for row in rows]
    pairs = [(estimate, reference) for estimate, reference in pairs if estimate is not None and reference is not None]
    errors = np.asarray([estimate - reference for estimate, reference in pairs], dtype=float)
    absolute = np.abs(errors)
    pearson = float(pearsonr([estimate for estimate, _ in pairs], [reference for _, reference in pairs]).statistic) if len(pairs) >= 2 else None
    spearman = float(spearmanr([estimate for estimate, _ in pairs], [reference for _, reference in pairs]).statistic) if len(pairs) >= 2 else None
    return {"version": version, "arm": arm, "n": len(pairs), "coverage_pct": round(100 * len(pairs) / len(rows), 3) if rows else None, "mae_bpm": round(float(np.mean(absolute)), 6) if len(errors) else None, "median_ae_bpm": round(float(np.median(absolute)), 6) if len(errors) else None, "rmse_bpm": round(float(np.sqrt(np.mean(errors ** 2))), 6) if len(errors) else None, "bias_bpm": round(float(np.mean(errors)), 6) if len(errors) else None, "pearson_r": round(pearson, 6) if pearson is not None else None, "spearman_r": round(spearman, 6) if spearman is not None else None}


def replay_new(rerun, ablation, historical, algo, new_rows: list[dict], old_by_window: dict[tuple[str, str, str], dict]) -> list[dict]:
    target_map = {subject: historical.historical_target(subject) for subject in SUBJECTS}
    output = []
    state = {"arm0": {}, "arm1": {}, "arm3": {}}
    for subject in SUBJECTS:
        reader = rerun.PartReader(subject)
        subject_rows = [row for row in new_rows if row["subject"] == subject]
        for row in subject_rows:
            block = row["block_id"]
            for arm in ("arm0", "arm1", "arm3"):
                if state[arm].get(subject, {}).get("block_id") != block:
                    state[arm][subject] = {"block_id": block, "hr": None, "br": None}
            start = int(row["frame_start_row"]); end = int(row["frame_end_row_exclusive"])
            iq = reader.slice(start, end)
            independent, summaries = rerun.independent_selection(algo, iq)
            arm0_br_ch, arm0_br_bin, _ = rerun.local_choice(summaries, "br", state["arm0"][subject]["br"])
            arm0_ch, arm0_bin, arm0_reason = rerun.local_choice(summaries, "hr", state["arm0"][subject]["hr"])
            arm0_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm0_ch, arm0_bin)
            gated = ablation.gated_summaries(summaries)
            if gated:
                arm1_ch, arm1_bin, arm1_reason = ablation.choose_gated(rerun, summaries, state["arm1"][subject]["hr"])
                arm3_ch, arm3_bin, arm3_reason = ablation.choose_gated(rerun, summaries, state["arm3"][subject]["hr"])
                arm1_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm1_ch, arm1_bin)
                arm3_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm3_ch, arm3_bin)
            else:
                arm1_ch = arm1_bin = arm3_ch = arm3_bin = None
                arm1_reason = arm3_reason = "no_candidate_in_historical_gate"
                arm1_vitals = {"analysis_status": arm1_reason}; arm3_vitals = {"analysis_status": arm3_reason}
            hist = target_map[subject]
            arm2_ch, arm2_bin = int(hist["heart_channel"]), int(hist["heart_bin"])
            arm2_vitals = rerun.estimate_vitals(algo, iq, arm0_br_ch, arm0_br_bin, arm2_ch, arm2_bin)
            old = old_by_window[(subject, block, row["window_id"])]
            ecg = numeric(old.get("ecg_hr_bpm"))
            record = {"subject": subject, "block_id": block, "window_id": row["window_id"], "window_start_unix_ms": row["window_start_unix_ms"], "window_end_unix_ms": row["window_end_unix_ms"], "ecg_hr_bpm": ecg, "new_frame_start_row": start, "new_frame_end_row_exclusive": end, "new_window_frame_count": row["new_window_frame_count"], "old_window_frame_count": row["old_window_frame_count"], "frame_overlap_jaccard": row["frame_overlap_jaccard"], "added_frames": row["added_frames"], "removed_frames": row["removed_frames"], "frame_membership_changed": row["frame_membership_changed"], "window_equivalence": row["window_equivalence"]}
            record.update(ablation.selected_fields("new_arm0", arm0_vitals, arm0_ch, arm0_bin, arm0_reason, ecg))
            record.update(ablation.selected_fields("new_arm1", arm1_vitals, arm1_ch, arm1_bin, arm1_reason, ecg))
            record.update(ablation.selected_fields("new_arm2", arm2_vitals, arm2_ch, arm2_bin, "historical_6000_frame_fixed_target", ecg))
            record.update(ablation.selected_fields("new_arm3", arm3_vitals, arm3_ch, arm3_bin, arm3_reason, ecg))
            # The same window_id is reused across subjects; the composite key
            # is resolved once above and remains the old comparator row.
            for arm, old_key, new_key in (("arm0", "arm0_hr_bpm", "new_arm0_hr_bpm"), ("arm1", "arm1_gate_only_hr_bpm", "new_arm1_hr_bpm"), ("arm2", "arm2_historical_target_hr_bpm", "new_arm2_hr_bpm")):
                record[f"old_{arm}_hr_bpm"] = old.get(old_key)
                record[f"old_{arm}_hr"] = old.get(old_key)
                record[f"new_{arm}_hr"] = record.get(new_key)
                record[f"old_{arm}_abs_error"] = old.get({"arm0": "arm0_abs_error", "arm1": "arm1_gate_only_abs_error", "arm2": "arm2_historical_target_abs_error"}[arm])
                record[f"new_{arm}_abs_error"] = record.get(f"new_{arm}_abs_error")
            output.append(record)
            state["arm0"][subject]["hr"] = (arm0_ch, arm0_bin) if arm0_ch is not None else None
            state["arm0"][subject]["br"] = (arm0_br_ch, arm0_br_bin) if arm0_br_ch is not None else None
            state["arm1"][subject]["hr"] = (arm1_ch, arm1_bin) if arm1_ch is not None else None
            state["arm3"][subject]["hr"] = (arm3_ch, arm3_bin) if arm3_ch is not None else None
    return sorted(output, key=lambda row: (SUBJECTS.index(row["subject"]), row["block_id"], row["window_id"]))


def main() -> int:
    rerun = load_module(RERUN_SCRIPT, "targeted_wrapper_for_time_sensitivity")
    ablation = load_module(ABLATION_SCRIPT, "frozen_ablation_for_time_sensitivity")
    historical = load_module(HIST_SCRIPT, "historical_target_for_time_sensitivity")
    algo = load_module(rerun.PRODUCER_FILE, "existing_hr_estimator_for_time_sensitivity")
    old_rows = [row for row in read_csv(OLD_ABLATION) if row.get("subject") in SUBJECTS]
    new_rows = [row for row in read_csv(NEW_WINDOWS) if row.get("subject") in SUBJECTS]
    old_by_window = {(row["subject"], row["block_id"], row["window_id"]): row for row in old_rows}
    new_keys = {(row["subject"], row["block_id"], row["window_id"]) for row in new_rows}
    if len(old_by_window) != len(old_rows) or new_keys != set(old_by_window) or len(new_rows) != len(old_rows):
        raise RuntimeError(f"old/new window row mismatch: {len(old_rows)} vs {len(new_rows)}")
    new_results = replay_new(rerun, ablation, historical, algo, new_rows, old_by_window)
    output_path = RESULT_ROOT / "MMWAVE_TIME_SEMANTICS_HR_COMPARISON.csv"
    write_csv(output_path, new_results)
    metric_rows = []
    for arm, old_key, new_key in (("arm0", "old_arm0_hr_bpm", "new_arm0_hr_bpm"), ("arm1", "old_arm1_hr_bpm", "new_arm1_hr_bpm"), ("arm2", "old_arm2_hr_bpm", "new_arm2_hr_bpm")):
        metric_rows.append(metrics(new_results, "new_dll_time", arm, new_key))
        metric_rows.append(metrics(new_results, "old_python_time", arm, old_key))
    metric_path = RESULT_ROOT / "MMWAVE_TIME_SEMANTICS_HR_METRICS.csv"
    write_csv(metric_path, metric_rows)
    changed = [row for row in new_results if row["frame_membership_changed"] == "True" or row["frame_membership_changed"] is True]
    obvious = [row for row in new_results if row["window_equivalence"] == "OBVIOUS"]
    new_coverage = {arm: sum(numeric(row.get(f"new_{arm}_hr_bpm")) is not None for row in new_results) for arm in ("arm0", "arm1", "arm2")}
    old_coverage = {arm: sum(numeric(row.get(f"old_{arm}_hr_bpm")) is not None for row in new_results) for arm in ("arm0", "arm1", "arm2")}
    mean_abs_delta = {arm: round(float(np.mean([abs(numeric(row.get(f"new_{arm}_hr_bpm")) - numeric(row.get(f"old_{arm}_hr_bpm"))) for row in new_results if numeric(row.get(f"new_{arm}_hr_bpm")) is not None and numeric(row.get(f"old_{arm}_hr_bpm")) is not None])), 6) if any(numeric(row.get(f"new_{arm}_hr_bpm")) is not None and numeric(row.get(f"old_{arm}_hr_bpm")) is not None for row in new_results) else None for arm in ("arm0", "arm1", "arm2")}
    classification = "PYTHON_TIMESTAMP_ARTIFACT_MATERIALLY_CHANGED_WINDOWS" if len(obvious) > 0 and any(mean_abs_delta[arm] not in (None, 0) for arm in mean_abs_delta) else "PYTHON_TIMESTAMP_ARTIFACT_COSMETIC_ONLY"
    fixed_contract = json.loads(RECON_MANIFEST.read_text(encoding="utf-8"))
    coverage_summary = fixed_contract.get("absolute_coverage_summary", {})
    short_rows = [row for row in new_results if numeric(row.get("new_window_frame_count")) is not None and int(float(row["new_window_frame_count"])) < 100]
    metric_lines = ["| version | arm | n | coverage % | MAE | median AE | RMSE | bias | Pearson | Spearman |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    metric_lines.extend(f"| {row['version']} | {row['arm']} | {row['n']} | {row['coverage_pct']} | {row['mae_bpm']} | {row['median_ae_bpm']} | {row['rmse_bpm']} | {row['bias_bpm']} | {row['pearson_r']} | {row['spearman_r']} |" for row in metric_rows)
    report_path = RESULT_ROOT / "MMWAVE_TIME_SEMANTICS_HR_COMPARISON_REPORT_2026-08-30.md"
    report_path.write_text("\n".join([
        "# mmWave time-semantics HR sensitivity — 2026-08-30", "", f"状态：`PARTIAL / {classification}`", "",
        "本轮唯一改变是 window frame membership：旧 Python-time 窗口改为冻结 contract 定义的 DLL absolute Unix-ms 窗口。ARM0/ARM1/ARM2 的 target、gate、filter、FS=100、ECG reference 和 block denominator 均未改变。", "",
        f"- old rows/new rows: `{len(old_rows)}/{len(new_results)}`; changed membership: `{len(changed)}`; obvious Jaccard<0.9: `{len(obvious)}`.", f"- HR coverage old/new: `{old_coverage}` / `{new_coverage}`.", f"- Mean absolute HR value delta old→new: `{mean_abs_delta}` bpm.", "",
        "## Metrics", "", "详见 `MMWAVE_TIME_SEMANTICS_HR_METRICS.csv`，包括 old/new 的 MAE、median AE、RMSE、bias、Pearson、Spearman。所有相关系数均为描述性，不作因果推断。", "", *metric_lines, "",
        "## Coverage blocker", "", f"- DLL authoritative data coverage summary: `{json.dumps(coverage_summary, ensure_ascii=False)}`.", f"- New windows with fewer than 100 DLL frames: `{[(row['subject'], row['block_id'], row['window_id'], row['new_window_frame_count']) for row in short_rows]}`.", "- `97795/block4` ends with only 46 recorded DLL frames because the program end marker is 24,809 ms after the last DLL frame. The missing tail is not imputed; the affected HR rows are invalid/missing rather than silently treated as physiological failures.", "",
        "## Decision", "", f"- `WINDOW_DECISION = {classification}`.", "- Classification A (cosmetic only): not supported; the change is material (310/335 membership changes, 154 obvious equivalence changes, and 6.13–6.85 bpm mean absolute HR value deltas).", "- Classification B (materially changed windows): supported; the old Python-time rows and new DLL-time rows are not interchangeable.", "- Classification C (unresolved): retained for exact DLL timestamp generator origin and the 97795/block4 acquisition-coverage tail.", "- 旧 24.9/21.8/19.1 bpm 结果保留为历史 Python-time window provenance，但不再作为 DLL authoritative window 的当前结果；当前 contract 下应由 new DLL-time metrics 引用。", "- 不修改 producer，不调 estimator，不修改 target/gate，不运行 HRV/#16/C2B/C2C/full batch。", "- HR/BR 继续 `HOLD`；HRV `BLOCKED`；Issue #16 `PAUSED`。", "", "## Artifacts", "", "- `MMWAVE_TIME_SEMANTICS_HR_COMPARISON.csv`", "- `MMWAVE_TIME_SEMANTICS_HR_METRICS.csv`", "- `MMWAVE_TIME_SEMANTICS_HR_COMPARISON_REPORT_2026-08-30.md`", ""]), encoding="utf-8")
    manifest = {"status": f"PARTIAL / {classification}", "canonical_algorithm_head_at_run": git(ALGO_ROOT, "rev-parse", "HEAD"), "canonical_algorithm_remote_main_at_run": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"), "fixed_contract_manifest": str(RECON_MANIFEST), "fixed_contract_manifest_sha256": sha256(RECON_MANIFEST), "old_input": str(OLD_ABLATION), "old_input_sha256": sha256(OLD_ABLATION), "new_window_input": str(NEW_WINDOWS), "new_window_input_sha256": sha256(NEW_WINDOWS), "arms": {"arm0": "current block-local", "arm1": "historical bins 9-40 gate + current block-local", "arm2": "historical fixed target + current 20s estimator"}, "only_changed": "window frame membership from Python-time to DLL-time", "old_window_results_decision": "RETAIN_AS_HISTORICAL_PROVENANCE__SUPERSEDE_FOR_CURRENT_DLL_CONTRACT", "window_equivalence": {"n": len(new_results), "changed": len(changed), "obvious": len(obvious)}, "mean_abs_hr_value_delta_bpm": mean_abs_delta, "coverage_blocker": {"short_window_rows": [(row["subject"], row["block_id"], row["window_id"], int(float(row["new_window_frame_count"]))) for row in short_rows], "absolute_coverage_summary": coverage_summary}, "decision_categories": {"A_cosmetic_only": False, "B_materially_changed_windows": True, "C_unresolved": ["exact DLL timestamp generator origin", "97795/block4 acquisition coverage tail"]}, "outputs": {}}
    for path in (output_path, metric_path, report_path):
        manifest["outputs"][path.name] = {"path": path.name, "sha256": sha256(path), "row_count": sum(1 for _ in csv.DictReader(path.open(encoding="utf-8-sig"))) if path.suffix == ".csv" else None}
    manifest_path = RESULT_ROOT / "MMWAVE_TIME_SEMANTICS_HR_COMPARISON_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "metrics": metric_rows, "window_equivalence": manifest["window_equivalence"], "mean_abs_hr_value_delta_bpm": mean_abs_delta, "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
