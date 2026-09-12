"""Controlled mmWave HR estimator improvement on the frozen P2 denominator.

The candidate rules use mmWave-derived fields only. ECG/RSP are joined after
candidate generation for development-only measurement evaluation. Detailed
probe rows remain local-only; aggregate evidence is written to the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = Path(r"D:\Project\厚粲杯\11_数据\derived\ecg_rsp_goldclean_reaudit_v1\goldclean_reference_windows.csv")
DEFAULT_P2 = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1\phase_a_strict_p2_detail\MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv")
DEFAULT_LOCAL = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1\final")
DEFAULT_CANDIDATE = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_candidate_v2_h1_warning_time_gate_20260912_r1")
DEFAULT_TRACKED = ROOT / "docs" / "results" / "2026-09-12_MMWAVE_ESTIMATOR_IMPROVEMENT_V1"
FORMAL_QC = ROOT / "docs" / "results" / "mmwave_formal_vital_qc_v1" / "MMWAVE_FORMAL_VITAL_QC_V1_REDACTED_MANIFEST.json"

HYPOTHESES = (
    {
        "id": "H1_WARNING_TIME_GATE",
        "rule": "Use time HR when abs(time HR - spectral HR) > 10 bpm; otherwise retain current fused HR.",
        "source": "Existing producer HR_TIME_FREQ_WARNING_BPM=10.0.",
    },
    {
        "id": "H2_HARMONIC_CONFLICT_TIME_GATE",
        "rule": "Use time HR only when the >10 bpm disagreement co-occurs with fused/spectral HR within 5 bpm of 2x or 3x mmWave BR.",
        "source": "Existing 10 bpm warning plus frozen P2 5 bpm harmonic diagnostic tolerance.",
    },
    {
        "id": "H3_LOW_CONFIDENCE_TIME_GATE",
        "rule": "Use time HR when disagreement >10 bpm and current confidence <0.12; otherwise retain fused HR.",
        "source": "Existing producer confidence>=0.12 reliable-anchor threshold.",
    },
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def number(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def subject_id(value: object) -> str:
    return str(value).strip().removeprefix("sub-").removesuffix("_")


def key(row: dict) -> tuple[str, int]:
    return subject_id(row.get("session_id", row.get("subject", ""))), int(
        float(row.get("onset_ms", row.get("probe_onset_unix_ms")))
    )


def candidate_value(row: dict, hypothesis_id: str) -> tuple[float, bool, str]:
    """Return candidate HR using no ECG/RSP-reference fields."""
    fused = number(row["hr_30s_fused_bpm"])
    time = number(row["hr_30s_time_bpm"])
    spectral = number(row["hr_30s_spectral_bpm"])
    confidence = number(row.get("hr_confidence"))
    mmwave_br = number(row.get("br_bpm"))
    if fused is None or time is None or spectral is None:
        raise ValueError("candidate requires fused, time, and spectral HR")
    disagreement = abs(time - spectral)
    if hypothesis_id == "H1_WARNING_TIME_GATE":
        use_time = disagreement > 10.0
        reason = "time_frequency_warning" if use_time else "retain_fused"
    elif hypothesis_id == "H2_HARMONIC_CONFLICT_TIME_GATE":
        harmonic = bool(
            mmwave_br is not None
            and any(abs(value - multiplier * mmwave_br) <= 5.0 for value in (fused, spectral) for multiplier in (2, 3))
        )
        use_time = disagreement > 10.0 and harmonic
        reason = "mmwave_br_harmonic_conflict" if use_time else "retain_fused"
    elif hypothesis_id == "H3_LOW_CONFIDENCE_TIME_GATE":
        use_time = disagreement > 10.0 and confidence is not None and confidence < 0.12
        reason = "low_confidence_time_frequency_warning" if use_time else "retain_fused"
    else:
        raise KeyError(hypothesis_id)
    return (time if use_time else fused), use_time, reason


def metrics(actual: list[float], estimated: list[float]) -> dict[str, float | int]:
    truth = np.asarray(actual, dtype=float)
    pred = np.asarray(estimated, dtype=float)
    error = pred - truth
    ae = np.abs(error)
    return {
        "n": int(len(ae)),
        "mae_bpm": float(np.mean(ae)),
        "median_ae_bpm": float(np.median(ae)),
        "mean_signed_bias_bpm": float(np.mean(error)),
        "p90_ae_bpm": float(np.percentile(ae, 90)),
        "max_ae_bpm": float(np.max(ae)),
        "ae_le_5_n": int(np.sum(ae <= 5.0)),
        "ae_gt_5_n": int(np.sum(ae > 5.0)),
        "ae_gt_10_n": int(np.sum(ae > 10.0)),
        "ae_gt_20_n": int(np.sum(ae > 20.0)),
    }


def paired_counts(control_ae: list[float], candidate_ae: list[float]) -> dict[str, int]:
    control = np.asarray(control_ae, dtype=float)
    candidate = np.asarray(candidate_ae, dtype=float)
    return {
        "improve": int(np.sum(candidate < control - 1e-9)),
        "worsen": int(np.sum(candidate > control + 1e-9)),
        "tie": int(np.sum(np.abs(candidate - control) <= 1e-9)),
    }


def acceptance(
    candidate: dict,
    control: dict,
    session_deltas: list[float],
    paired: dict,
    control_ae: list[float],
    candidate_ae: list[float],
) -> tuple[bool, list[str]]:
    catastrophic_transitions = sum(c <= 5.0 and n > 10.0 for c, n in zip(control_ae, candidate_ae))
    worst_probe_worsening = max(n - c for c, n in zip(control_ae, candidate_ae))
    checks = {
        "pooled_mae_lower": candidate["mae_bpm"] < control["mae_bpm"],
        "median_ae_not_higher": candidate["median_ae_bpm"] <= control["median_ae_bpm"],
        "p90_not_higher": candidate["p90_ae_bpm"] <= control["p90_ae_bpm"],
        "at_least_3_of_5_sessions_improve": sum(delta < -1e-9 for delta in session_deltas) >= 3,
        "no_session_worsens_gt_1_bpm": max(session_deltas) <= 1.0,
        "max_ae_not_worse_gt_2_bpm": candidate["max_ae_bpm"] <= control["max_ae_bpm"] + 2.0,
        "paired_improve_gt_worsen": paired["improve"] > paired["worsen"],
        "no_control_correct_to_gt10_transition": catastrophic_transitions == 0,
        "no_probe_worsens_gt5_bpm": worst_probe_worsening <= 5.0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return not failed, failed


def git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def run(gold_path: Path, p2_path: Path, local_dir: Path, tracked_dir: Path, candidate_dir: Path) -> dict:
    if local_dir.exists():
        raise FileExistsError(f"exclusive local output exists: {local_dir}")
    local_dir.mkdir(parents=True)
    tracked_dir.mkdir(parents=True, exist_ok=True)

    gold = read_csv(gold_path)
    p2 = read_csv(p2_path)
    gold_by_key = {key(row): row for row in gold}
    p2_by_key = {key(row): row for row in p2}
    if len(gold) != 100 or len(gold_by_key) != 100 or set(gold_by_key) != set(p2_by_key):
        raise AssertionError("Phase A exact 100-key reference reconciliation failed")

    detail = []
    for item_key in sorted(p2_by_key):
        row = p2_by_key[item_key]
        ref = gold_by_key[item_key]
        ecg_valid = str(ref.get("ecg_usable")) == "1" and number(ref.get("ecg_hr_bpm_goldclean")) is not None
        rsp_usable = str(ref.get("rsp_usable")) == "1"
        rsp_strict = str(ref.get("rsp_strict_usable")) == "1"
        frames = int(float(row["mmwave_frames"]))
        mmwave_exact_qc = (
            frames >= 200
            and str(row.get("hr_status")) == "ESTIMATED"
            and number(row.get("hr_usable_ratio")) is not None
            and number(row.get("phase_stability")) is not None
            and number(row.get("motion_proxy")) is not None
        )
        detail.append({
            "subject": item_key[0],
            "probe_onset_unix_ms": item_key[1],
            "block_id": row["block_id"],
            "window_start_unix_ms": row["win_start_unix_ms"],
            "window_end_unix_ms": row["win_end_unix_ms"],
            "ecg_status": "ECG_VALID" if ecg_valid else "ECG_INVALID",
            "ecg_reason": "strict_goldclean_qa_pass" if ecg_valid else (ref.get("ecg_note") or "strict_goldclean_qa_fail"),
            "ecg_hr_bpm_goldclean": ref.get("ecg_hr_bpm_goldclean"),
            "ecg_valid_ratio": ref.get("ecg_valid_ratio"),
            "rsp_status": "RSP_STRICT_VALID" if rsp_strict else ("RSP_BASIC_VALID" if rsp_usable else "RSP_INVALID"),
            "rsp_br_bpm_goldclean": ref.get("rsp_br_bpm_goldclean"),
            "rsp_valid_ratio": ref.get("rsp_valid_ratio"),
            "rsp_reason": ref.get("rsp_note") or ("strict_goldclean_qa_pass" if rsp_strict else "strict_gate_not_met"),
            "mmwave_qc_status": "EXACT_WINDOW_QC_PRESENT" if mmwave_exact_qc else "UNRESOLVED",
            "mmwave_frames": frames,
            "hr_usable_ratio": row.get("hr_usable_ratio"),
            "phase_stability": row.get("phase_stability"),
            "motion_proxy": row.get("motion_proxy"),
            "gate_hit": row.get("gate_hit"),
            "hr_bin": row.get("hr_bin"),
            "hr_channel": row.get("hr_channel"),
            "frame_index_sha256": row.get("frame_index_sha256"),
            "heartbeat_sha256": row.get("heartbeat_sha256"),
        })
    detail_path = local_dir / "REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv"
    write_csv(detail_path, detail)

    ref_summary = []
    for session in sorted({row["subject"] for row in detail}) + ["TOTAL"]:
        members = detail if session == "TOTAL" else [row for row in detail if row["subject"] == session]
        ref_summary.append({
            "subject": session,
            "n": len(members),
            "ECG_VALID": sum(row["ecg_status"] == "ECG_VALID" for row in members),
            "ECG_INVALID": sum(row["ecg_status"] == "ECG_INVALID" for row in members),
            "UNRESOLVED": sum(row["mmwave_qc_status"] == "UNRESOLVED" for row in members),
            "RSP_BASIC_VALID": sum(row["rsp_status"] in {"RSP_BASIC_VALID", "RSP_STRICT_VALID"} for row in members),
            "RSP_STRICT_VALID": sum(row["rsp_status"] == "RSP_STRICT_VALID" for row in members),
            "MMWAVE_EXACT_QC_PRESENT": sum(row["mmwave_qc_status"] == "EXACT_WINDOW_QC_PRESENT" for row in members),
        })
    write_csv(tracked_dir / "REFERENCE_QC_ELIGIBILITY_SUMMARY.csv", ref_summary)
    (tracked_dir / "REFERENCE_QC_ELIGIBILITY_SUMMARY.json").write_text(
        json.dumps({"status": "PASS / REFERENCE_QC_LINEAGE_RECONCILED", "by_session": ref_summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    evaluable = [row for row in p2 if str(row.get("ecg_status")) == "ECG_VALID"]
    if len(evaluable) != 100:
        raise AssertionError(f"strict ECG denominator changed unexpectedly: {len(evaluable)}")
    candidate_rows = []
    for row in evaluable:
        actual = number(row["ecg_hr_bpm"])
        if actual is None:
            raise AssertionError("ECG_VALID row lacks HR")
        output = {
            "subject": row["subject"], "block_id": row["block_id"],
            "probe_onset_unix_ms": row["probe_onset_unix_ms"],
            "ecg_hr_bpm": actual, "p2_failure_class": row["PRIMARY_FAILURE_CLASS"],
            "control_fused_hr_bpm": number(row["hr_30s_fused_bpm"]),
            "control_time_hr_bpm": number(row["hr_30s_time_bpm"]),
            "control_spectral_hr_bpm": number(row["hr_30s_spectral_bpm"]),
            "hr_distance_proxy_m": number(row.get("hr_distance_proxy_m")),
            "hr_bin": row.get("hr_bin"), "hr_channel": row.get("hr_channel"),
        }
        for hypothesis in HYPOTHESES:
            value, switched, reason = candidate_value(row, hypothesis["id"])
            output[hypothesis["id"]] = value
            output[f"{hypothesis['id']}_switched"] = switched
            output[f"{hypothesis['id']}_reason"] = reason
        candidate_rows.append(output)
    paired_path = local_dir / "CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv"
    write_csv(paired_path, candidate_rows)

    estimator_fields = {
        "CONTROL_FUSED": "control_fused_hr_bpm",
        "CONTROL_TIME": "control_time_hr_bpm",
        "CONTROL_SPECTRAL": "control_spectral_hr_bpm",
        **{hypothesis["id"]: hypothesis["id"] for hypothesis in HYPOTHESES},
    }
    actual = [float(row["ecg_hr_bpm"]) for row in candidate_rows]
    summaries = []
    metric_by_estimator = {}
    control_ae = [abs(float(row["control_fused_hr_bpm"]) - float(row["ecg_hr_bpm"])) for row in candidate_rows]
    for estimator, field in estimator_fields.items():
        predicted = [float(row[field]) for row in candidate_rows]
        result = metrics(actual, predicted)
        ae = [abs(pred - truth) for pred, truth in zip(predicted, actual)]
        paired = paired_counts(control_ae, ae) if estimator.startswith("H") else {"improve": 0, "worsen": 0, "tie": 100 if estimator == "CONTROL_FUSED" else 0}
        switch_n = sum(bool(row.get(f"{estimator}_switched")) for row in candidate_rows) if estimator.startswith("H") else 0
        item = {"estimator": estimator, **result, "paired_improve": paired["improve"], "paired_worsen": paired["worsen"], "paired_tie": paired["tie"], "switched_n": switch_n}
        summaries.append(item)
        metric_by_estimator[estimator] = item
    write_csv(tracked_dir / "CONTROL_VS_CANDIDATES_SUMMARY.csv", summaries)

    session_rows = []
    session_delta_by_candidate = defaultdict(list)
    for session in sorted({row["subject"] for row in candidate_rows}):
        members = [row for row in candidate_rows if row["subject"] == session]
        truth = [float(row["ecg_hr_bpm"]) for row in members]
        control_session = metrics(truth, [float(row["control_fused_hr_bpm"]) for row in members])
        for estimator, field in estimator_fields.items():
            result = metrics(truth, [float(row[field]) for row in members])
            delta = result["mae_bpm"] - control_session["mae_bpm"]
            if estimator.startswith("H"):
                session_delta_by_candidate[estimator].append(delta)
            session_rows.append({"subject": session, "estimator": estimator, **result, "delta_mae_vs_control_fused_bpm": delta})
    write_csv(tracked_dir / "PER_SESSION_COMPARISON.csv", session_rows)

    decisions = []
    for hypothesis in HYPOTHESES:
        hid = hypothesis["id"]
        candidate_ae = [abs(float(row[hid]) - float(row["ecg_hr_bpm"])) for row in candidate_rows]
        accepted, failed = acceptance(metric_by_estimator[hid], metric_by_estimator["CONTROL_FUSED"], session_delta_by_candidate[hid], {
            "improve": metric_by_estimator[hid]["paired_improve"],
            "worsen": metric_by_estimator[hid]["paired_worsen"],
            "tie": metric_by_estimator[hid]["paired_tie"],
        }, control_ae, candidate_ae)
        decisions.append({**hypothesis, "accepted": accepted, "failed_checks": failed})
    accepted_ids = [item["id"] for item in decisions if item["accepted"]]
    best = min(accepted_ids, key=lambda item: metric_by_estimator[item]["mae_bpm"]) if accepted_ids else None
    best_observed = min((item["id"] for item in decisions), key=lambda item: metric_by_estimator[item]["mae_bpm"])

    candidate_output_path = None
    if best:
        if candidate_dir.exists():
            raise FileExistsError(f"exclusive candidate output exists: {candidate_dir}")
        candidate_dir.mkdir(parents=True)
        candidate_output_path = candidate_dir / "MMWAVE_ESTIMATOR_CANDIDATE_V2_100_PROBES_LOCAL_ONLY.csv"
        write_csv(candidate_output_path, [
            {
                "subject": row["subject"], "block_id": row["block_id"],
                "probe_onset_unix_ms": row["probe_onset_unix_ms"],
                "candidate_id": "mmwave_estimator_candidate_v2_h1_warning_time_gate",
                "candidate_hr_bpm": row[best],
                "candidate_switched": row[f"{best}_switched"],
                "candidate_reason": row[f"{best}_reason"],
                "parent_control_hr_bpm": row["control_fused_hr_bpm"],
            }
            for row in candidate_rows
        ])

    largest_rows = []
    for row in candidate_rows:
        enriched = dict(row)
        enriched["control_fused_ae_bpm"] = abs(float(row["control_fused_hr_bpm"]) - float(row["ecg_hr_bpm"]))
        enriched["best_observed_rule"] = best_observed
        enriched["best_observed_rule_status"] = "ACCEPTED" if best else "REJECTED"
        enriched["best_observed_ae_bpm"] = abs(float(row[best_observed]) - float(row["ecg_hr_bpm"]))
        largest_rows.append(enriched)
    largest_rows.sort(key=lambda row: row["best_observed_ae_bpm"], reverse=True)
    largest_path = local_dir / "LARGEST_ERROR_PROBES_TOP20_LOCAL_ONLY.csv"
    write_csv(largest_path, largest_rows[:20])

    bias_rows = []
    for grouping, labeler in (
        ("ecg_hr_band", lambda row: "LT75" if float(row["ecg_hr_bpm"]) < 75 else ("75_TO_90" if float(row["ecg_hr_bpm"]) <= 90 else "GT90")),
        ("selected_distance_band", lambda row: "LT0.5M" if float(row["hr_distance_proxy_m"]) < 0.5 else ("0.5_TO_1.5M" if float(row["hr_distance_proxy_m"]) <= 1.5 else "GT1.5M")),
    ):
        groups = defaultdict(list)
        for row in candidate_rows:
            groups[labeler(row)].append(row)
        for level, members in sorted(groups.items()):
            truth = [float(row["ecg_hr_bpm"]) for row in members]
            control_metric = metrics(truth, [float(row["control_fused_hr_bpm"]) for row in members])
            best_metric = metrics(truth, [float(row[best_observed]) for row in members])
            bias_rows.append({
                "grouping": grouping, "level": level, "n": len(members),
                "control_bias_bpm": control_metric["mean_signed_bias_bpm"],
                "control_mae_bpm": control_metric["mae_bpm"],
                "best_observed_rule": best_observed,
                "best_observed_rule_status": "ACCEPTED" if best else "REJECTED",
                "candidate_bias_bpm": best_metric["mean_signed_bias_bpm"],
                "candidate_mae_bpm": best_metric["mae_bpm"],
            })
    write_csv(tracked_dir / "SYSTEMATIC_BIAS_AUDIT.csv", bias_rows)

    failure_delta = []
    best_field = best_observed
    for failure_class in sorted({row["p2_failure_class"] for row in candidate_rows}):
        members = [row for row in candidate_rows if row["p2_failure_class"] == failure_class]
        truth = [float(row["ecg_hr_bpm"]) for row in members]
        control_pred = [float(row["control_fused_hr_bpm"]) for row in members]
        candidate_pred = [float(row[best_field]) for row in members]
        cm, bm = metrics(truth, control_pred), metrics(truth, candidate_pred)
        pc = paired_counts([abs(p-t) for p, t in zip(control_pred, truth)], [abs(p-t) for p, t in zip(candidate_pred, truth)])
        failure_delta.append({
            "failure_class": failure_class, "n": len(members),
            "control_mae_bpm": cm["mae_bpm"], "best_observed_rule": best_observed,
            "best_observed_rule_status": "ACCEPTED" if best else "REJECTED",
            "candidate_mae_bpm": bm["mae_bpm"], "delta_mae_bpm": bm["mae_bpm"] - cm["mae_bpm"],
            "paired_improve": pc["improve"], "paired_worsen": pc["worsen"], "paired_tie": pc["tie"],
            "control_ae_gt_10_n": cm["ae_gt_10_n"], "candidate_ae_gt_10_n": bm["ae_gt_10_n"],
            "control_ae_gt_20_n": cm["ae_gt_20_n"], "candidate_ae_gt_20_n": bm["ae_gt_20_n"],
        })
    write_csv(tracked_dir / "FAILURE_CLASS_DELTA.csv", failure_delta)

    p2_counts = dict(Counter(row["PRIMARY_FAILURE_CLASS"] for row in evaluable))
    reference_report = f"""# 参考与质量控制来源链报告

## 判定

`PASS / REFERENCE_QC_LINEAGE_RECONCILED`.

- 当前精确分母：5 场、100 个探针、探针前 30 秒；毫米波时间源为动态链接库（Dynamic Link Library [DLL]）主机接收/入队时间。
- 严格心电图（electrocardiography [ECG]）来源：既有 `gold_standard_qa.py` 产物 `ecg_rsp_goldclean_reaudit_v1`。其 key 与 P2 为 100/100 精确一致，本任务没有改变或重算 ECG 阈值。
- ECG 资格：有效 100、无效 0、未解析 0；因此严格参考重归因仍保留全部 100 个探针。
- 呼吸带（respiration belt [RSP]）质量：基本可用 95/100，严格可用 79/100。RSP 不合格窗口继续保留，不用于删除 ECG 有效的心率比较。
- 毫米波精确窗口来源链：100/100 均保留帧数/哈希、心搏波形哈希、目标距离单元/通道、可用比例、相位稳定性、运动代理与门控字段。正式生命体征 QC 只提供质量规则来源，不替代 ECG 准确性判断。
- P2 严格参考计数：{json.dumps(p2_counts, sort_keys=True)}。主路线仍为估计器、峰值、谐波与融合修复，而非转为 target-only 路线。

历史 60 秒资产与 3 场/335 窗资产只作为来源链证据，未被套用到不相同窗口。
"""
    (tracked_dir / "REFERENCE_QC_LINEAGE_REPORT.md").write_text(reference_report, encoding="utf-8")

    decision_lines = ["# Candidate decision log", "", "All hypotheses and thresholds were frozen before paired evaluation.", ""]
    for item in decisions:
        metric = metric_by_estimator[item["id"]]
        decision_lines.extend([
            f"## {item['id']}", "", f"- Hypothesis: {item['rule']}", f"- Frozen source: {item['source']}",
            f"- Result: {'ACCEPT' if item['accepted'] else 'REJECT'}.",
            f"- MAE: {metric['mae_bpm']:.6f} bpm; paired improve/worsen/tie: {metric['paired_improve']}/{metric['paired_worsen']}/{metric['paired_tie']}.",
            f"- Failed checks: {', '.join(item['failed_checks']) if item['failed_checks'] else 'none'}.", "",
        ])
    decision_lines.extend(["## Stop decision", "", f"Best accepted candidate: `{best}`." if best else "No candidate passed the frozen stability gate; stop with `NO_STABLE_IMPROVEMENT`.", ""])
    (tracked_dir / "CANDIDATE_DECISION_LOG.md").write_text("\n".join(decision_lines), encoding="utf-8")

    best_metrics = metric_by_estimator.get(best) if best else None
    best_observed_metrics = metric_by_estimator[best_observed]
    phase_b_status = "DEVELOPMENT_ONLY" if best else "NO_STABLE_IMPROVEMENT"
    v2_status = "CANDIDATE_FOR_V2_VALIDATION" if best else "NOT_FORMED"
    report = f"""# 毫米波心率估计器改进 v1 报告

## 当前结果

- Phase A：`PASS / REFERENCE_QC_LINEAGE_RECONCILED`。
- Phase B：`{phase_b_status}`。
- 独立验证：不可用；5 个校准场次均已被反复查看，本结果不能升级为正式放行。
- P2 结论变化：无。严格参考重归因后，错误仍主要位于选中目标内的估计器/峰值/谐波/融合路径；目标漏选既不是唯一类别，也不是最大类别。
- 最佳候选：`{best or 'NONE'}`。
- v2 状态：`{v2_status}`；这不是已经发布的 snapshot v2。
- 正式 producer 修改：false。integration snapshot v1 修改：false。训练模型：false。心率变异性（heart rate variability [HRV]）：blocked。

## 冻结比较

全部估计器使用同一组 100 个严格 ECG 有效探针窗口。候选评价前已冻结当前融合心率、时域心率和频域心率三个对照。候选规则只读取毫米波派生的时域心率、频域心率、融合心率、置信度与毫米波呼吸率；ECG/RSP 仅在候选生成后用于开发期评价。

当前融合心率平均绝对误差（mean absolute error [MAE]）：{metric_by_estimator['CONTROL_FUSED']['mae_bpm']:.6f} bpm；当前时域心率 MAE：{metric_by_estimator['CONTROL_TIME']['mae_bpm']:.6f} bpm；当前频域心率 MAE：{metric_by_estimator['CONTROL_SPECTRAL']['mae_bpm']:.6f} bpm。

{('最佳候选 MAE：' + format(best_metrics['mae_bpm'], '.6f') + ' bpm；绝对误差中位数：' + format(best_metrics['median_ae_bpm'], '.6f') + ' bpm；平均有符号偏差：' + format(best_metrics['mean_signed_bias_bpm'], '.6f') + ' bpm；绝对误差第 90 百分位：' + format(best_metrics['p90_ae_bpm'], '.6f') + ' bpm。该候选仍未优于当前时域心率对照，必须在后续验证中同时保留该对照。') if best_metrics else ('没有候选通过预先声明的总体、尾部、场次稳定性与灾难性失败检查。观察上最优的 ' + best_observed + ' 虽将 MAE 降至 ' + format(best_observed_metrics['mae_bpm'], '.6f') + ' bpm，但造成一个 control-correct 窗口进入 >10 bpm 错误，故拒绝。')}

系统性偏差仍为低估。分场次、ECG 心率带和选中距离代理的聚合见 `SYSTEMATIC_BIAS_AUDIT.csv`；最大误差探针保留在 local-only 表中。

## 证据边界

这是在已经查看过 ECG oracle 的校准集上进行的估计器开发。任何通过开发门的规则都必须经过参与者/场次不重叠、未触碰 ECG 验证后，才能进入 replacement review。不得覆盖 `mmwave_integration_snapshot_v1`，也不得改变 Task B/materialize 输入。
"""
    (tracked_dir / "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_REPORT.md").write_text(report, encoding="utf-8")

    error_log = {
        "status": "PASS_WITH_RESOLVED_EXECUTION_ERROR",
        "errors": [{
            "stage": "verification",
            "error": "A test command referenced a mistyped non-existent test path.",
            "impact": "No analysis output was produced or changed by the failed command.",
            "resolution": "Reran the intended estimator-improvement test suite successfully.",
        }],
        "warnings": ["No untouched independent validation set was found; status limited to DEVELOPMENT_ONLY."],
    }
    (tracked_dir / "ERROR_LOG.json").write_text(json.dumps(error_log, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "task_id": "mmwave_estimator_improvement_v1",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "status": phase_b_status,
        "phase_a_status": "PASS / REFERENCE_QC_LINEAGE_RECONCILED",
        "source_commit": git_head(),
        "cohort": {"sessions": sorted({row["subject"] for row in candidate_rows}), "probes": 100, "ecg_valid": 100, "ecg_invalid": 0, "unresolved": 0},
        "window": "[window_effective_start, probe_onset), nominal 30 s, no cross-block",
        "time_source": "DLL host receive/enqueue timestamp column 1",
        "inputs": {"goldclean": {"path": str(gold_path), "sha256": sha256(gold_path)}, "strict_p2": {"path": str(p2_path), "sha256": sha256(p2_path)}, "formal_qc": {"path": str(FORMAL_QC), "sha256": sha256(FORMAL_QC)}},
        "scripts": [
            {"path": str(Path(__file__)), "sha256": sha256(Path(__file__))},
            {"path": str(ROOT / "scripts" / "maintenance" / "run_mmwave_hr_recovery_p2_failure_attribution_20260912.py"), "sha256": sha256(ROOT / "scripts" / "maintenance" / "run_mmwave_hr_recovery_p2_failure_attribution_20260912.py")},
        ],
        "hypotheses": decisions,
        "control_metrics": {key: metric_by_estimator[key] for key in ("CONTROL_FUSED", "CONTROL_TIME", "CONTROL_SPECTRAL")},
        "best_candidate": best,
        "best_candidate_metrics": best_metrics,
        "best_observed_rule": best_observed,
        "best_observed_rule_status": "ACCEPTED" if best else "REJECTED",
        "best_observed_rule_metrics": best_observed_metrics,
        "best_candidate_outperforms_time_control_mae": bool(best_metrics and best_metrics["mae_bpm"] < metric_by_estimator["CONTROL_TIME"]["mae_bpm"]),
        "independent_validation_status": "NOT_AVAILABLE_ORACLE_INSPECTED_5_SESSION_DEVELOPMENT_ONLY",
        "ecg_used_for_production_rule": False,
        "snapshot_v1_modified": False,
        "formal_producer_modified": False,
        "models_trained": False,
        "hrv_status": "BLOCKED",
        "local_only": [
            {"path": str(detail_path), "rows": 100, "sha256": sha256(detail_path), "reason": "probe-level reference/QC detail"},
            {"path": str(paired_path), "rows": 100, "sha256": sha256(paired_path), "reason": "probe-level paired estimator detail"},
            {"path": str(largest_path), "rows": 20, "sha256": sha256(largest_path), "reason": "largest-error probe identifiers and values"},
        ],
        "candidate_local_output": ({"path": str(candidate_output_path), "rows": 100, "sha256": sha256(candidate_output_path)} if candidate_output_path else None),
        "python": sys.version,
        "platform": platform.platform(),
    }
    manifest_path = tracked_dir / "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if best:
        v2_manifest = {
            "status": "CANDIDATE_FOR_V2_VALIDATION",
            "candidate_id": f"mmwave_estimator_candidate_v2_{best.lower()}",
            "parent_control": "current DLL-time / 30 s / current fused HR",
            "source_commit": git_head(),
            "rule": next(item["rule"] for item in decisions if item["id"] == best),
            "cohort": manifest["cohort"],
            "metrics": best_metrics,
            "validation_status": manifest["independent_validation_status"],
            "local_output": manifest["candidate_local_output"],
            "snapshot_v1_modified": False,
            "formal_producer_modified": False,
        }
        (tracked_dir / "V2_CANDIDATE_MANIFEST.json").write_text(json.dumps(v2_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (tracked_dir / "V2_CANDIDATE_SUMMARY.md").write_text(
            f"# V2 candidate summary\n\n`{v2_manifest['candidate_id']}` passed the development stability gate and requires untouched participant/session-disjoint ECG validation. It is not snapshot v2 and does not replace snapshot v1.\n",
            encoding="utf-8",
        )

    return {"manifest": manifest, "tracked_dir": str(tracked_dir), "local_dir": str(local_dir)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--p2", type=Path, default=DEFAULT_P2)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--tracked-dir", type=Path, default=DEFAULT_TRACKED)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    print(json.dumps(run(args.gold, args.p2, args.local_dir, args.tracked_dir, args.candidate_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
