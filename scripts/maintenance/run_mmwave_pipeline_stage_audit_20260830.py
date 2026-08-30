"""Join existing mmWave lineage/replay outputs into a fixed stage audit.

This is a downstream evidence adapter only.  It does not change the producer,
target selector, windows, ECG labels, or any estimator parameter.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION"
TARGET_ROOT = ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
LOCAL_REPLAY = Path(
    r"D:\Project\厚粲杯\11_数据\derived\mmwave_selector_path_reconciliation_20260830"
)

REPLAY = LOCAL_REPLAY / "MMWAVE_SELECTOR_PATH_REPLAY_335_WINDOWS_LOCAL_ONLY.csv"
COVERAGE = TARGET_ROOT / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT.csv"
TARGET_ABLATION = TARGET_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
ESTIMATOR_COMPARISON = TARGET_ROOT / "MMWAVE_HR_ESTIMATOR_SAME_WINDOW_COMPARISON.csv"
LINEAGE = TARGET_ROOT / "MMWAVE_HR_ESTIMATOR_LINEAGE.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: object) -> float | None:
    if value is None or str(value).strip() in {"", "NA", "nan", "None"}:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    return sum(x * y for x, y in zip(dx, dy)) / denom if denom else None


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        value = (index + 1 + end) / 2.0
        for position in order[index:end]:
            ranks[position] = value
        index = end
    return ranks


def fmt(value: object, digits: int = 6) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, digits)
    return value


def portable_manifest_path(path: Path) -> str:
    """Use repository-relative paths for tracked assets, absolute for local-only inputs."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def metrics(rows: list[dict[str, str]], method: str, estimate_field: str) -> dict[str, object]:
    paired: list[tuple[float, float]] = []
    for row in rows:
        truth = as_float(row.get("ecg_hr_bpm_oracle"))
        estimate = as_float(row.get(estimate_field))
        if truth is not None and estimate is not None:
            paired.append((truth, estimate))
    truth = [item[0] for item in paired]
    estimate = [item[1] for item in paired]
    errors = [b - a for a, b in paired]
    absolute = [abs(value) for value in errors]
    return {
        "method": method,
        "fixed_control_n": len(rows),
        "valid_n": len(paired),
        "coverage_pct_of_fixed_control": fmt(100 * len(paired) / len(rows)) if rows else "",
        "mae_bpm": fmt(statistics.fmean(absolute)) if absolute else "",
        "median_ae_bpm": fmt(statistics.median(absolute)) if absolute else "",
        "bias_estimator_minus_ecg_bpm": fmt(statistics.fmean(errors)) if errors else "",
        "rmse_bpm": fmt(math.sqrt(statistics.fmean([value * value for value in errors]))) if errors else "",
        "pearson_r": fmt(pearson(truth, estimate)),
        "spearman_r": fmt(pearson(rank(truth), rank(estimate))),
    }


def paired_delta(rows: list[dict[str, str]], label_a: str, field_a: str, label_b: str, field_b: str) -> dict[str, object]:
    paired: list[tuple[float, float, float]] = []
    for row in rows:
        truth = as_float(row.get("ecg_hr_bpm_oracle"))
        a = as_float(row.get(field_a))
        b = as_float(row.get(field_b))
        if truth is not None and a is not None and b is not None:
            paired.append((truth, a, b))
    ae_a = [abs(a - truth) for truth, a, _ in paired]
    ae_b = [abs(b - truth) for truth, _, b in paired]
    return {
        "method_a": label_a,
        "method_b": label_b,
        "common_valid_n": len(paired),
        "mae_method_a_bpm": fmt(statistics.fmean(ae_a)) if ae_a else "",
        "mae_method_b_bpm": fmt(statistics.fmean(ae_b)) if ae_b else "",
        "mean_ae_delta_a_minus_b_bpm": fmt(statistics.fmean([a - b for a, b in zip(ae_a, ae_b)])) if ae_a else "",
        "median_ae_delta_a_minus_b_bpm": fmt(statistics.median([a - b for a, b in zip(ae_a, ae_b)])) if ae_a else "",
        "method_a_better_n": sum(a < b for a, b in zip(ae_a, ae_b)),
        "method_b_better_n": sum(b < a for a, b in zip(ae_a, ae_b)),
        "tie_n": sum(a == b for a, b in zip(ae_a, ae_b)),
    }


def stage_rows() -> list[dict[str, object]]:
    return [
        {"stage_id": "S01", "stage": "8-channel complex range-domain input", "code_location": "scripts/process_vital_signs_v3_1_1.py:1099-1112; scripts/maintenance/run_mmwave_targeted_validation_20260830.py:227-280", "input": "NPZ tx arrays; [frame, range-bin, channel]", "operation": "sort tx keys, stack channels, cast complex64; no second range FFT", "output": "complex range-domain cube", "why": "preserve channelized range samples and avoid double-transform", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "YES", "direct_effect_evidence": "Output shape/packing audit; NONE for isolated MAE effect", "canonical_reference": "Project audit/U1-U4; L1-L3", "decision": "KEEP"},
        {"stage_id": "S02", "stage": "range profile and target candidate generation", "code_location": "scripts/process_vital_signs_v3_1_1.py:1146-1172,1194-1233", "input": "complex cube", "operation": "mean abs(z)^2 profile; per-channel >1% max candidates; phase variance, detrended FFT, SNR and stability scores", "output": "candidate bins/channels and scores", "why": "rank signal-like range/channel candidates", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "YES", "direct_effect_evidence": "ARM0/ARM1/ARM2 and same-window replay; target is material but not isolated from all downstream stages", "canonical_reference": "L3 target-range selection; project audit", "decision": "RESTORE_EXISTING"},
        {"stage_id": "S03", "stage": "gross range ROI/gate", "code_location": "scripts/process_vital_signs_v3_1_1.py:2500-2517,2803-2900; historical run lineage", "input": "bin candidates and bin spacing", "operation": "historical 0.30-1.50 m = bins 9-40; current independent selector has no physical gate", "output": "gated candidate set or unrestricted set", "why": "constrain implausible target range", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "NO in independent selection", "direct_effect_evidence": "Existing ablation: ARM1 MAE < ARM0 on prior 335-row output; not ECG-tuned and not physical-truth proof", "canonical_reference": "L3 plus protocol prior; exact placement receipt absent", "decision": "RESTORE_EXISTING"},
        {"stage_id": "S04", "stage": "DC/static/clutter handling before selection", "code_location": "scripts/process_vital_signs_v3_1_1.py:1146-1172,1502-1557,1597-1636; audit fields/matrix", "input": "complex cube/profile", "operation": "no downstream DC/IQ/MTI/background subtraction before target selection; plot subtraction is display-only", "output": "raw profile remains selector input", "why": "must distinguish actual target processing from diagnostic visualization", "historical_path_use": "NO", "current_formal_use": "NO", "targeted_path_use": "NO", "direct_effect_evidence": "NONE; no project A/B isolates suppression", "canonical_reference": "L1, L4-L6 support the need/risk, not this implementation", "decision": "UNPROVEN"},
        {"stage_id": "S05", "stage": "phase extraction and displacement", "code_location": "scripts/process_vital_signs_v3_1_1.py:268-270,1415-1439", "input": "selected complex bin/channel", "operation": "unwrap(angle(iq)); wavelength_mm * phase/(4*pi)", "output": "unwrapped displacement time series", "why": "recover chest micro-motion phase", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "YES", "direct_effect_evidence": "Shared across historical/current replay; NONE for isolated stage effect", "canonical_reference": "L1-L2, L4-L5; project-parameter variant", "decision": "KEEP"},
        {"stage_id": "S06", "stage": "BR/HR bandpass", "code_location": "scripts/process_vital_signs_v3_1_1.py:273-275,305-394,642-679", "input": "displacement", "operation": "4th-order SOS; BR 0.1-0.5 Hz branch; HR bp_heart 0.8-2.0 Hz; optional VMD K=3", "output": "filtered BR/HR signals", "why": "isolate physiological bands", "historical_path_use": "YES bp_heart", "current_formal_use": "YES", "targeted_path_use": "YES bandpass; NO VMD/full branch", "direct_effect_evidence": "Historical full-chain 20s adaptation outperforms current block-local on same 323 control rows; VMD has no safe current-20s A/B seam. REUSE_REJECTION_REASON: persisted replay has no VMD branch output and current targeted path does not invoke it", "canonical_reference": "L1-L2, L4-L6; parameters are project-specific", "decision": "KEEP bandpass / UNPROVEN VMD"},
        {"stage_id": "S07", "stage": "window and segment construction", "code_location": "scripts/process_vital_signs_v3_1_1.py:857-1072,1947-2239; targeted wrapper:369-381", "input": "filtered displacement", "operation": "historical internal 25s/5s course and segment correction/consensus; targeted fixed windows 20s", "output": "segment/course estimates", "why": "stabilize short-window spectral estimates", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "PARTIAL", "direct_effect_evidence": "Historical 20s adaptation vs current paths; #25 20s/60s remains confounded", "canonical_reference": "L2; project validation only for exact parameters", "decision": "RESTORE_EXISTING"},
        {"stage_id": "S08", "stage": "periodogram/FFT and candidate generation", "code_location": "scripts/process_vital_signs_v3_1_1.py:727-775,1236-1241; targeted wrapper:309-335", "input": "filtered HR signal", "operation": "Hann periodogram, nfft padding, peak candidates, prominence/IBI candidates", "output": "frequency/time candidates", "why": "produce HR hypotheses", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "YES", "direct_effect_evidence": "Fixed-path vs sequential selector replay; selector exact recovery is supporting path evidence, not HR validity", "canonical_reference": "L1-L2; project heuristic", "decision": "KEEP"},
        {"stage_id": "S09", "stage": "harmonic half/double folding", "code_location": "scripts/process_vital_signs_v3_1_1.py:713-724,1800-1944", "input": "time/frequency candidates and optional anchor", "operation": "existing half/double/triple heuristic; external RSP guard only when acq_path is supplied", "output": "folded candidates", "why": "reduce respiration harmonic/HR octave ambiguity", "historical_path_use": "YES internal; external RSP inactive", "current_formal_use": "YES internal; external inactive in formal runner", "targeted_path_use": "PARTIAL internal selector replay; NO external RSP", "direct_effect_evidence": "No isolated effect. REUSE_REJECTION_REASON: persisted 335-row replay stores folded selector outputs but not pre-fold candidate lists; old targeted path did not call the internal guard and formal runner lacks external RSP input", "canonical_reference": "L6 supports harmonic risk; exact folding is project heuristic", "decision": "UNPROVEN"},
        {"stage_id": "S10", "stage": "previous/reference BPM continuity", "code_location": "scripts/process_vital_signs_v3_1_1.py:727-775,857-1072; selector replay script", "input": "candidate list plus previous BPM", "operation": "score penalty/anchor, reset per complete block; reference BPM=None in replay", "output": "anchored spectral BPM and next previous value", "why": "avoid implausible frame-to-frame jumps", "historical_path_use": "YES course continuity", "current_formal_use": "YES", "targeted_path_use": "RESTORED in selector replay; absent from old targeted estimator", "direct_effect_evidence": "No-anchor descriptive comparison; 37/102 wrong and 17/182 nearby exact recovery", "canonical_reference": "L2; project selector contract", "decision": "RESTORE_EXISTING"},
        {"stage_id": "S11", "stage": "segment correction and consensus", "code_location": "scripts/process_vital_signs_v3_1_1.py:1947-2239", "input": "segment HR candidates", "operation": "correction, ±6 bpm clusters, median/fusion/time-course consensus", "output": "consensus HR", "why": "suppress isolated segment errors", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "NO in old targeted estimator", "direct_effect_evidence": "Historical full-chain 20s adaptation vs current block-local is a bundled comparison. REUSE_REJECTION_REASON: no persisted segment-level intermediate output or safe correction-only toggle for the same 323 rows", "canonical_reference": "Project method; no canonical parameter-level external support", "decision": "RESTORE_EXISTING (bundle only)"},
        {"stage_id": "S12", "stage": "final selector/output and signal gate", "code_location": "scripts/process_vital_signs_v3_1_1.py:2092-2313,2379-2497", "input": "candidate/consensus results", "operation": "quality gate, time/frequency fusion, final score and output; missing remains missing", "output": "HR/BR result plus QC/status", "why": "emit only quality-qualified estimates", "historical_path_use": "YES", "current_formal_use": "YES", "targeted_path_use": "NO/partial", "direct_effect_evidence": "Current formal runner uses full downstream chain; targeted old path stops at raw periodogram/peak. REUSE_REJECTION_REASON: persisted replay does not expose pre-QC estimates under the same output contract, so QC-only effect is not separable", "canonical_reference": "L1-L2; project QC heuristic", "decision": "RESTORE_EXISTING (bundle only)"},
        {"stage_id": "S13", "stage": "ECG reference", "code_location": "#24 ECG eligibility outputs; replay manifest", "input": "ECG only after mmWave output", "operation": "oracle-only eligibility/reference; never passed to selector", "output": "fixed ECG_VALID denominator", "why": "predeclare evaluation cohort without tuning estimator", "historical_path_use": "REFERENCE ONLY", "current_formal_use": "VALIDATION ONLY", "targeted_path_use": "VALIDATION ONLY", "direct_effect_evidence": "323 COMPLETE ∩ ECG_VALID control windows", "canonical_reference": "Project #24 contract", "decision": "KEEP"},
    ]


def main() -> None:
    replay = read_csv(REPLAY)
    coverage = read_csv(COVERAGE)
    target = read_csv(TARGET_ABLATION)
    estimator = read_csv(ESTIMATOR_COMPARISON)

    coverage_by_window = {row["window_id"]: row for row in coverage}
    target_by_window = {row["window_id"]: row for row in target}
    estimator_by_window = {row["window_id"]: row for row in estimator}
    joined: list[dict[str, str]] = []
    for row in replay:
        coverage_row = coverage_by_window.get(row["window_id"], {})
        target_row = target_by_window.get(row["window_id"], {})
        estimator_row = estimator_by_window.get(row["window_id"], {})
        combined = dict(row)
        combined["coverage_class"] = coverage_row.get("coverage_class", "")
        combined["coverage_end_gap_ms"] = coverage_row.get("end_coverage_gap_ms", "")
        for key, value in target_row.items():
            if key not in {"subject", "window_id"}:
                combined[f"target_{key}"] = value
        for key, value in estimator_row.items():
            if key not in {"subject", "window_id"}:
                combined[f"estimator_{key}"] = value
        joined.append(combined)

    complete = [row for row in joined if row.get("coverage_class") == "COMPLETE"]
    control = [row for row in complete if row.get("ecg_eligibility") == "ECG_VALID"]

    method_fields = [
        ("fixed_target_periodogram", "fixed_path_bpm"),
        ("existing_selector_previous_anchor", "selector_bpm"),
        ("existing_selector_fused_previous_anchor", "selector_fused_bpm"),
        ("existing_selector_no_anchor", "no_anchor_selector_bpm"),
        ("existing_selector_fused_no_anchor", "no_anchor_selector_fused_bpm"),
        ("old_targeted_current_block_local", "target_arm0_hr_bpm"),
        ("old_targeted_historical_gate", "target_arm1_gate_only_hr_bpm"),
        ("old_targeted_historical_fixed_target", "target_arm2_historical_target_hr_bpm"),
        ("current_independent_estimator_audit", "estimator_current_independent_hr_bpm"),
        ("current_block_local_estimator_audit", "estimator_current_block_local_hr_bpm"),
        ("historical_full_chain_20s_adaptation", "estimator_historical_20s_adapt_hr_bpm"),
    ]
    metric_rows = [metrics(control, label, field) for label, field in method_fields]

    pairwise_specs = [
        ("existing_selector_previous_anchor", "selector_bpm", "fixed_target_periodogram", "fixed_path_bpm"),
        ("existing_selector_fused_previous_anchor", "selector_fused_bpm", "existing_selector_previous_anchor", "selector_bpm"),
        ("old_targeted_historical_gate", "target_arm1_gate_only_hr_bpm", "old_targeted_current_block_local", "target_arm0_hr_bpm"),
        ("old_targeted_historical_fixed_target", "target_arm2_historical_target_hr_bpm", "old_targeted_current_block_local", "target_arm0_hr_bpm"),
        ("historical_full_chain_20s_adaptation", "estimator_historical_20s_adapt_hr_bpm", "current_block_local_estimator_audit", "estimator_current_block_local_hr_bpm"),
    ]
    pairwise_rows = [paired_delta(control, *spec) for spec in pairwise_specs]

    stage_path = RESULT_ROOT / "MMWAVE_PIPELINE_STAGE_EVIDENCE_2026-08-30.csv"
    stage_data = stage_rows()
    stage_fields = list(stage_data[0])
    write_csv(stage_path, stage_data, stage_fields)

    metric_path = RESULT_ROOT / "MMWAVE_PIPELINE_STAGE_ABLATION_METRICS_2026-08-30.csv"
    metric_fields = list(metric_rows[0])
    write_csv(metric_path, metric_rows, metric_fields)
    pairwise_path = RESULT_ROOT / "MMWAVE_PIPELINE_STAGE_ABLATION_PAIRWISE_2026-08-30.csv"
    write_csv(pairwise_path, pairwise_rows, list(pairwise_rows[0]))

    failure_rows = [
        {
            "truth_subset": "wrong_selection",
            "fixed_path_n": 102,
            "existing_selector_exact_n": 37,
            "existing_selector_nearby_n": 10,
            "existing_selector_not_recovered_n": 55,
            "target_path_subtype_counts": "not applicable: fixed-target replay",
            "residual_locus": "candidate ranking/continuity remains; target/bin/channel is not tested by fixed-target replay",
            "evidence_boundary": "supporting path replay only; no physical target truth",
        },
        {
            "truth_subset": "nearby_target_bin_channel",
            "fixed_path_n": 182,
            "existing_selector_exact_n": 17,
            "existing_selector_nearby_n": 45,
            "existing_selector_not_recovered_n": 120,
            "target_path_subtype_counts": "neighbor-bin=6; neighbor-channel=11; target/channel-switch=164; no-alternative=1",
            "residual_locus": "target/bin/channel and candidate ranking/continuity cannot be separated from existing aligned outputs",
            "evidence_boundary": "path-level subtype only; 15-row continuity diagnostic is not aligned; no physical target truth",
        },
        {
            "truth_subset": "absent_or_weak",
            "fixed_path_n": 17,
            "existing_selector_exact_n": "not applicable",
            "existing_selector_nearby_n": "not applicable",
            "existing_selector_not_recovered_n": "not applicable",
            "target_path_subtype_counts": "not available",
            "residual_locus": "signal absent/weak; do not force selector recovery",
            "evidence_boundary": "retained truth class from #27 audit",
        },
    ]
    failure_path = RESULT_ROOT / "MMWAVE_FAILURE_LOCUS_SUMMARY_2026-08-30.csv"
    write_csv(failure_path, failure_rows, list(failure_rows[0]))

    lineage_rows = [
        {
            "historical_result": "HR MAE 3.7772146 bpm",
            "producer_lineage": "scripts/maintenance/run_hr_course_99_corrected.py -> scripts/process_vital_signs_v3_1_1.py",
            "producer_commit": "64634159d226ee1ed892d53e56fcf3697fbff9b8",
            "input": "8-channel complex range-domain DataCube NPZ; 100 Hz; first 6000-frame target selection",
            "target_contract": "0.037 m/bin; 0.30-1.50 m = bins 9-40; fixed heart target for full record",
            "estimator_contract": "bp_heart 0.8-2.0 Hz; periodogram/peak; phase unwrap; segment correction/consensus/time course",
            "window_contract": "60 s historical probe; 5 sessions; 99 valid windows",
            "output_provenance": "D:\\Project\\厚粲杯\\08_算法\\work\\mmwave_targeted_validation_20260830_rerun",
            "source_lineage_file": portable_manifest_path(LINEAGE),
        }
    ]
    lineage_path = RESULT_ROOT / "MMWAVE_HISTORICAL_PRODUCER_LINEAGE_2026-08-30.csv"
    write_csv(lineage_path, lineage_rows, list(lineage_rows[0]))

    map_path = RESULT_ROOT / "MMWAVE_PIPELINE_STEP_BY_STEP_MAP_2026-08-30.md"
    map_path.write_text(
        "# mmWave producer lineage and step-by-step map (2026-08-30)\n\n"
        "## 固定事实\n\n"
        "- 历史最佳 HR≈3.7772146 bpm 的完整 lineage：`run_hr_course_99_corrected.py` → `process_vital_signs_v3_1_1.py`，commit `64634159d226ee1ed892d53e56fcf3697fbff9b8`。\n"
        "- 输入是 8-channel complex range-domain DataCube，不是 raw ADC；历史 target 先在前 6000 frames 选择，再固定到完整记录。\n"
        "- 历史物理 gate 为 `0.30–1.50 m = bins 9–40`（按 0.037 m/bin）；current targeted independent selector 没有使用该 gate。\n"
        "- 历史、current formal、targeted 三条路径都没有被证实在 target selection 前执行 DC/static/clutter suppression；绘图中的减均值仅是 display diagnostic。\n"
        "- 本轮控制口径固定为 coverage `COMPLETE` 且 ECG `ECG_VALID`，即 323 windows；`97795/block4/w027,w028` 排除，不 padding/backfill/reconstruct，24,809 ms tail 只保留 provenance。\n\n"
        "## 顺序图\n\n"
        "`complex range cube` → `raw range-power profile/candidates` → `[historical gate only: bins 9–40]` → `bin/channel target` → `phase angle → unwrap → displacement` → `BR/HR bandpass` → `periodogram/FFT + time peaks` → `harmonic fold` → `previous-BPM continuity` → `segment correction/consensus` → `time/frequency fusion + signal gate` → `HR/BR output` → `ECG oracle evaluation only`\n\n"
        "## 路径差异\n\n"
        "1. **历史 producer**：6000-frame fixed target + historical gate + `bp_heart` + full v3.1.1 downstream chain + 60 s historical probe.\n"
        "2. **current formal producer**：调用同一 `process_vital_signs_v3_1_1.py` full path，caller gate 作用于 BR/HR candidate set；默认 runner 未传 external RSP acquisition input。\n"
        "3. **old targeted path**：per-window raw target selection/local ±3-bin continuity + bandpass/periodogram/peak；没有接入 existing `_select_spectral_bpm`、VMD/full historical segment correction/consensus/time-course chain。\n"
        "4. **本轮 restored replay**：固定已有 target，接回 existing spectral selector、previous-BPM state、harmonic folding and time/frequency fusion；这是 supporting replay，不是新 selector，也不把 ECG 传入选择。\n\n"
        "## 可验证决策\n\n"
        "- **KEEP**：complex input semantics、phase extraction、bandpass、periodogram/peak、ECG oracle-only denominator。\n"
        "- **RESTORE_EXISTING**：historical physical gate/target contract、previous-BPM selector continuity、segment correction/consensus、final signal/QC output chain。previous anchor 与 time/frequency fusion 已在同一 323 窗直接重放；其余链段只有 bundled comparison，不能宣称单阶段因果贡献。\n"
        "- **UNPROVEN**：near-field peak 已被 static/clutter suppression 去除；DC/static stage 的独立收益；VMD、harmonic guard、segment correction/consensus、final QC 的独立收益；candidate persistence。\n"
        "- **DROP**：new selector/new algorithm、ECG-informed gate tuning、tail repair、按 20 s vs 60 s MAE 直接推广窗口。#25 保持 `WAIT_ON_SELECTOR_VALIDITY`。\n\n"
        "## 逐步人话解释\n\n"
        "| 步骤 | 代码做什么 | 为什么 | 项目内效果 | 参考/依据 | 当前决策 |\n"
        "|---|---|---|---|---|---|\n"
        "| S01 输入 | 把 NPZ 的 8 个复数通道按 range bin 叠成数据立方体，不做第二次 Range FFT | 保留设备已经输出的距离域信息 | 形状/打包审计通过；没有单独 MAE 归因 | `process_vital_signs_v3_1_1.py:1099-1112` | KEEP |\n"
        "| S02 候选 | 用平均功率、相位稳定性和频带分数列出可能的 bin/channel | 先回答哪里有可用动态信号 | target 会改变下游结果，但与后续步骤 bundled | `process_vital_signs_v3_1_1.py:1146-1233` | RESTORE_EXISTING |\n"
        "| S03 距离门 | 历史链将 0.30–1.50 m 固定为 bins 9–40；当前 targeted 独立选择未使用它 | 排除物理上不合理的候选 | 既有 gate/target ablation 保留同一控制口径 | 0.037 m/bin 历史 lineage；既有 gate ablation | RESTORE_EXISTING |\n"
        "| S04 静态项 | 审计确认选 bin 前仍使用 raw mean-power；绘图减均值不回写选择 | 区分真实去杂波和仅用于显示的处理 | 没有可复用的 pre-selection A/B | `process_vital_signs_v3_1_1.py:1146-1172` 与审计矩阵 | UNPROVEN |\n"
        "| S05 相位 | 对选中复数样本取 angle、unwrap，再换算位移 | 从微小相位变化得到运动信号 | 为三条路径共享；无独立归因 | `process_vital_signs_v3_1_1.py:268-270,1415-1439` | KEEP |\n"
        "| S06 带通 | 用既有 SOS 带通分开 BR/HR；VMD 是另一个已有分支 | 去掉带外成分 | bandpass 共享；VMD 没有当前 20 s 可切换输出 | `process_vital_signs_v3_1_1.py:273-394,1296-1369` | KEEP bandpass / UNPROVEN VMD |\n"
        "| S07 窗口 | 历史链有 course/segment 结构，targeted 固定为 20 s | 让短窗估计有上下文 | historical 20 s adaptation 优于 block-local，但与窗口定义纠缠 | 既有 same-window estimator audit | RESTORE_EXISTING（bundle） |\n"
        "| S08 频谱 | 做 Hann periodogram、峰候选和时域峰候选 | 产生 HR 假设 | fixed periodogram→selector 可直接比较 | `process_vital_signs_v3_1_1.py:727-775,1236-1241` | KEEP |\n"
        "| S09 折叠 | 按已有 half/double/triple 规则处理谐波关系 | 避免倍频/半频误锁 | replay 没有折叠前候选列表，不能安全做一开关 A/B | `process_vital_signs_v3_1_1.py:713-724,1800-1944`；REUSE_REJECTION_REASON | UNPROVEN |\n"
        "| S10 连续性 | 用上一窗 BPM 给候选打锚点并跨窗传递 | 限制不合理跳变 | MAE 24.902438→13.276285；同窗 245/323 更好 | `_select_spectral_bpm()` 与 selector replay | RESTORE_EXISTING |\n"
        "| S11 段校正/共识 | 对 segment 结果做校正、聚类、中位数/融合 | 抑制孤立 segment 错误 | 只观察到 full-chain bundled gain；没有 correction-only 中间表 | `process_vital_signs_v3_1_1.py:1947-2239`；REUSE_REJECTION_REASON | RESTORE_EXISTING（bundle） |\n"
        "| S12 最终门控 | 合并时域/频域、计算质量分并输出 QC；缺失保持缺失 | 控制最终输出可信度边界 | targeted old path 未暴露同契约门控前值，不能拆 QC-only delta | `process_vital_signs_v3_1_1.py:2092-2313,2379-2497`；REUSE_REJECTION_REASON | RESTORE_EXISTING（bundle） |\n"
        "| S13 ECG | 只在 mmWave 输出之后读取 ECG eligibility/HR 作 oracle | 固定评估分母而不调参 | COMPLETE∩ECG_VALID=323；ECG 未进入选择 | #24 contract | KEEP |\n\n"
        "## 证据文件\n\n"
        "- `MMWAVE_PIPELINE_STAGE_EVIDENCE_2026-08-30.csv`：逐阶段代码位置、输入输出、用途、三路径是否使用、直接效果证据、文献支持与决策。\n"
        "- `MMWAVE_PIPELINE_STAGE_ABLATION_METRICS_2026-08-30.csv`：323-window fixed control 的 MAE/median AE/bias/RMSE/Pearson/Spearman/valid n。\n"
        "- `MMWAVE_PIPELINE_STAGE_ABLATION_PAIRWISE_2026-08-30.csv`：同窗 paired delta。\n"
        "- `MMWAVE_FAILURE_LOCUS_SUMMARY_2026-08-30.csv`：102 wrong / 182 nearby 的恢复数与剩余定位边界。\n"
        "- `MMWAVE_HISTORICAL_PRODUCER_LINEAGE_2026-08-30.csv`：3.777 lineage、commit、参数、输入、输出绑定。\n",
        encoding="utf-8",
    )

    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    manifest = {
        "run_id": "MMWAVE_PIPELINE_STAGE_AUDIT_20260830",
        "status": "PARTIAL / CONTROLLED_STAGE_AUDIT_COMPLETE_SELECTOR_VALIDITY_SUPPORTING_ONLY",
        "scope": "Downstream join/metrics/evidence only; no producer or estimator change",
        "canonical_main_head_at_run": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "denominators": {
            "all_replay_rows": len(joined),
            "complete_rows": len(complete),
            "complete_ecg_valid_control_rows": len(control),
            "excluded_severely_incomplete": ["97795/block4_w027", "97795/block4_w028"],
        },
        "coverage_contract": "existing timestamp-only contract; COMPLETE=333, SEVERELY_INCOMPLETE=2; no padding/backfill/reconstruct",
        "ecg_contract": "existing ECG_VALID oracle-only labels; no ECG-informed selection/tuning",
        "reused_assets": [
            {"path": portable_manifest_path(REPLAY), "sha256": sha256(REPLAY)},
            {"path": portable_manifest_path(COVERAGE), "sha256": sha256(COVERAGE)},
            {"path": portable_manifest_path(TARGET_ABLATION), "sha256": sha256(TARGET_ABLATION)},
            {"path": portable_manifest_path(ESTIMATOR_COMPARISON), "sha256": sha256(ESTIMATOR_COMPARISON)},
            {"path": portable_manifest_path(LINEAGE), "sha256": sha256(LINEAGE)},
        ],
        "reuse_rejection_reason": "Existing replay, target-ablation, same-window estimator, lineage, and coverage outputs were separate; this adapter only joins them under the requested COMPLETE ∩ ECG_VALID denominator and records step-level evidence. No new selector or algorithm.",
        "stage_replay_contract": [
            {"stage": "previous_anchor", "status": "EXECUTED", "switch": "existing selector with previous BPM vs same selector with previous BPM reset per window", "evidence": "MAE 24.902438 -> 13.276285 bpm on common n=323"},
            {"stage": "time_frequency_fusion", "status": "EXECUTED", "switch": "existing selector output vs existing time/frequency fused output", "evidence": "MAE 13.276285 -> 8.319342 bpm on common n=323"},
            {"stage": "historical_gate_target", "status": "EXECUTED_BOUNDED", "switch": "existing 0.037 m/bin and bins 9-40 gate/6000-frame target arms", "evidence": "historical fixed-target arm MAE 19.427297; gate-only arm valid n=287, not ECG-tuned"},
            {"stage": "harmonic_folding", "status": "NOT_APPLICABLE_UNPROVEN", "switch": "no safe persisted pre-fold candidate toggle", "evidence": "REUSE_REJECTION_REASON: replay lacks pre-fold candidate lists; external RSP input inactive"},
            {"stage": "vmd", "status": "NOT_APPLICABLE_UNPROVEN", "switch": "no safe persisted VMD branch toggle for current 20 s contract", "evidence": "REUSE_REJECTION_REASON: current targeted replay is bandpass-only and has no VMD intermediate output"},
            {"stage": "segment_correction_consensus", "status": "BUNDLED_ONLY", "switch": "no correction-only toggle in persisted 335-row output", "evidence": "REUSE_REJECTION_REASON: only historical full-chain 20 s adaptation is available"},
            {"stage": "final_qc_output", "status": "BUNDLED_ONLY", "switch": "no pre-QC value under the same output contract", "evidence": "REUSE_REJECTION_REASON: QC-only delta is not separable"}
        ],
        "near_field_conclusion": "UNPROVEN: raw mean-power target selection is used; no pre-selection DC/static/clutter suppression is present in the audited downstream producer; plot subtraction is display-only. Do not claim the near-field peak was removed.",
        "decision_summary": {"KEEP": 5, "RESTORE_EXISTING": 6, "UNPROVEN": 2, "DROP": 4},
        "outputs": {
            "stage_evidence": portable_manifest_path(stage_path),
            "metrics": portable_manifest_path(metric_path),
            "pairwise": portable_manifest_path(pairwise_path),
            "failure_locus": portable_manifest_path(failure_path),
            "lineage": portable_manifest_path(lineage_path),
            "step_by_step_map": portable_manifest_path(map_path),
        },
    }
    manifest_path = RESULT_ROOT / "MMWAVE_PIPELINE_STAGE_AUDIT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"complete": len(complete), "control": len(control), "metrics": str(metric_path), "manifest": str(manifest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
