"""Aggregate existing mmWave distance/error and physical-gate evidence.

This is a read-only audit of already-produced estimator outputs.  It does not
open raw DataCube files, reselect targets, rerun an estimator, or choose a
distance threshold from the observed errors.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median


SCRIPT_NAME = "run_mmwave_distance_error_physical_gate_audit_20260830.py"
BANDS = (
    ("<0.20", None, 0.20),
    ("0.20-0.30", 0.20, 0.30),
    ("0.30-0.60", 0.30, 0.60),
    ("0.60-1.00", 0.60, 1.00),
    (">1.00", 1.00, None),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def union_fieldnames(rows: list[dict[str, object]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for name in row:
            if name not in names:
                names.append(name)
    return names


def finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def number(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if not finite(value):
        raise ValueError(f"non-numeric {key!r}: {value!r}")
    return float(value)


def session_id(value: str) -> str:
    value = str(value).strip()
    value = value.removeprefix("sub-").removesuffix("_")
    return value.zfill(3) if value.isdigit() else value


def distance_band(distance: float) -> str:
    for label, lower, upper in BANDS:
        if lower is None and distance < upper:  # type: ignore[operator]
            return label
        if upper is None and distance > lower:  # type: ignore[operator]
            return label
        if lower is not None and upper is not None and lower <= distance < upper:
            return label
    # Exact 1.00 m is retained in the lower closed interval by contract.
    if math.isclose(distance, 1.00, abs_tol=1e-12):
        return "0.60-1.00"
    raise ValueError(f"distance did not map to a predefined band: {distance}")


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        rank = (index + 1 + end) / 2.0
        for position in order[index:end]:
            result[position] = rank
        index = end
    return result


def correlation(xs: list[float], ys: list[float]) -> tuple[float | None, float | None]:
    if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None, None
    x_bar = mean(xs)
    y_bar = mean(ys)
    denominator = math.sqrt(sum((x - x_bar) ** 2 for x in xs) * sum((y - y_bar) ** 2 for y in ys))
    pearson = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / denominator
    rx, ry = ranks(xs), ranks(ys)
    rx_bar, ry_bar = mean(rx), mean(ry)
    rank_denominator = math.sqrt(sum((x - rx_bar) ** 2 for x in rx) * sum((y - ry_bar) ** 2 for y in ry))
    spearman = sum((x - rx_bar) * (y - ry_bar) for x, y in zip(rx, ry)) / rank_denominator
    return pearson, spearman


def ols_slope(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(set(xs)) < 2:
        return None
    x_bar, y_bar = mean(xs), mean(ys)
    denominator = sum((x - x_bar) ** 2 for x in xs)
    return sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / denominator


def metric_row(metric: str, cohort: str, rows: list[dict[str, object]]) -> dict[str, object]:
    distances = [float(row["distance_m"]) for row in rows]
    errors = [float(row["abs_error"]) for row in rows]
    signed = [float(row["signed_error"]) for row in rows]
    pearson, spearman = correlation(distances, errors)
    sessions = {str(row["session"]) for row in rows}
    return {
        "metric": metric,
        "cohort": cohort,
        "n_windows": len(rows),
        "n_sessions": len(sessions),
        "n_participants": len(sessions),
        "distance_mean_m": round(mean(distances), 6),
        "distance_median_m": round(median(distances), 6),
        "abs_error_mean": round(mean(errors), 6),
        "abs_error_median": round(median(errors), 6),
        "bias_mean_estimate_minus_reference": round(mean(signed), 6),
        "rmse": round(math.sqrt(mean(value * value for value in signed)), 6),
        "within_5_fraction": round(sum(value <= 5 for value in errors) / len(errors), 6),
        "within_10_fraction": round(sum(value <= 10 for value in errors) / len(errors), 6),
        "pearson_distance_abs_error": None if pearson is None else round(pearson, 6),
        "spearman_distance_abs_error": None if spearman is None else round(spearman, 6),
        "ols_abs_error_per_m": None if ols_slope(distances, errors) is None else round(ols_slope(distances, errors), 6),
        "analysis_role": "descriptive; repeated windows within participant; not a threshold-selection test",
    }


def normalize_hr(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], int]:
    normalized: list[dict[str, object]] = []
    rejected = 0
    for row in rows:
        required = ("session", "window_key", "new_distance_37mm", "new_HR_course", "ECG_HR", "new_heart_bin", "new_channel")
        if not all(finite(row.get(key, "")) for key in required[2:]):
            rejected += 1
            continue
        estimate = number(row, "new_HR_course")
        reference = number(row, "ECG_HR")
        normalized.append(
            {
                "metric": "HR",
                "session": session_id(row["session"]),
                "window_key": row["window_key"],
                "distance_m": number(row, "new_distance_37mm"),
                "estimate": estimate,
                "reference": reference,
                "abs_error": abs(estimate - reference),
                "signed_error": estimate - reference,
                "target": int(float(row["new_heart_bin"])),
                "channel": int(float(row["new_channel"])),
                "order": number(row, "onset_ms") if finite(row.get("onset_ms", "")) else len(normalized),
            }
        )
    return normalized, rejected


def normalize_br(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], int]:
    normalized: list[dict[str, object]] = []
    rejected = 0
    for row in rows:
        required = ("session", "window_key", "new_distance_m", "new_br_mm_spectral_bpm", "br_rsp_bpm", "new_breath_bin", "new_best_channel")
        if not all(finite(row.get(key, "")) for key in required[2:]):
            rejected += 1
            continue
        estimate = number(row, "new_br_mm_spectral_bpm")
        reference = number(row, "br_rsp_bpm")
        normalized.append(
            {
                "metric": "BR",
                "session": session_id(row["session"]),
                "window_key": row["window_key"],
                "distance_m": number(row, "new_distance_m"),
                "estimate": estimate,
                "reference": reference,
                "abs_error": abs(estimate - reference),
                "signed_error": estimate - reference,
                "target": int(float(row["new_breath_bin"])),
                "channel": int(float(row["new_best_channel"])),
                "order": number(row, "onset_acq_s") if finite(row.get("onset_acq_s", "")) else len(normalized),
            }
        )
    return normalized, rejected


def stability_summary(metric: str, rows: list[dict[str, object]]) -> dict[str, object]:
    by_session: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_session[str(row["session"])].append(row)
    session_stats: list[dict[str, float]] = []
    for session, session_rows in by_session.items():
        ordered = sorted(session_rows, key=lambda row: (float(row["order"]), str(row["window_key"])))
        target_switches = sum(a["target"] != b["target"] for a, b in zip(ordered, ordered[1:]))
        channel_switches = sum(a["channel"] != b["channel"] for a, b in zip(ordered, ordered[1:]))
        transitions = max(len(ordered) - 1, 0)
        session_stats.append(
            {
                "windows": float(len(ordered)),
                "unique_targets": float(len({row["target"] for row in ordered})),
                "target_switches": float(target_switches),
                "channel_switches": float(channel_switches),
                "target_stability_fraction": (1.0 - target_switches / transitions) if transitions else 1.0,
                "channel_stability_fraction": (1.0 - channel_switches / transitions) if transitions else 1.0,
            }
        )
    transitions = sum(max(int(stat["windows"]) - 1, 0) for stat in session_stats)
    target_switches = sum(int(stat["target_switches"]) for stat in session_stats)
    channel_switches = sum(int(stat["channel_switches"]) for stat in session_stats)
    target_stability = [stat["target_stability_fraction"] for stat in session_stats]
    channel_stability = [stat["channel_stability_fraction"] for stat in session_stats]
    return {
        "metric": metric,
        "n_windows": len(rows),
        "n_sessions": len(session_stats),
        "n_participants": len(session_stats),
        "windows_min": int(min(stat["windows"] for stat in session_stats)),
        "windows_median": round(median(stat["windows"] for stat in session_stats), 6),
        "windows_max": int(max(stat["windows"] for stat in session_stats)),
        "unique_targets_median_per_session": round(median(stat["unique_targets"] for stat in session_stats), 6),
        "target_switches": target_switches,
        "target_switch_rate_over_transitions": round(target_switches / transitions, 6) if transitions else None,
        "target_stability_fraction_session_median": round(median(target_stability), 6),
        "target_stability_fraction_session_min": round(min(target_stability), 6),
        "target_stability_fraction_session_max": round(max(target_stability), 6),
        "sessions_target_stable_100pct": sum(value == 1.0 for value in target_stability),
        "channel_switches": channel_switches,
        "channel_switch_rate_over_transitions": round(channel_switches / transitions, 6) if transitions else None,
        "channel_stability_fraction_session_median": round(median(channel_stability), 6),
        "analysis_role": "existing estimator target/channel sequence; stability is not chest-lock confirmation",
    }


def band_rows(metric: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for label, _, _ in BANDS:
        subset = [row for row in rows if distance_band(float(row["distance_m"])) == label]
        if not subset:
            output.append({"metric": metric, "cohort": "ECG_VALID" if metric == "HR" else "RSP_VALID", "distance_band": label, "n_windows": 0})
            continue
        summary = metric_row(metric, "ECG_VALID" if metric == "HR" else "RSP_VALID", subset)
        summary["distance_band"] = label
        output.append(summary)
    return output


def extract_b2_evidence(report: Path) -> list[dict[str, object]]:
    text = report.read_text(encoding="utf-8")
    required = ("持续亮带", "RISK_NOT_SUPPORTED", "AMBIGUOUS")
    missing = [token for token in required if token not in text]
    if missing:
        raise ValueError(f"B2 report missing required evidence tokens: {missing}")
    evidence: list[dict[str, object]] = [
        {
            "scope": "formal_B2",
            "evidence": "persistent_near_side_bright_structure",
            "classification": "OBSERVED",
            "evidence_level": "SUPPORTING",
            "n_sessions": 43,
            "detail": "Existing locked 16 near + 18 far + 9 reference front-end audit reports persistent near-side bright structure across groups; cause remains unresolved.",
        },
        {
            "scope": "formal_B2",
            "evidence": "near_field_direct_leakage_or_fixed_reflection_cause",
            "classification": "UNRESOLVED",
            "evidence_level": "SUPPORTING",
            "n_sessions": 43,
            "detail": "Existing conservative B2 conclusion is RISK_NOT_SUPPORTED; no new exclusion gate is authorized.",
        },
    ]
    patterns = {
        "NEAR_LT_0.30": r"NEAR_LT_0\.30 \(n=(\d+)\): heart — (.*?); breath — (.*?)\.",
        "FAR_GT_1.50": r"FAR_GT_1\.50 \(n=(\d+)\): heart — (.*?); breath — (.*?)\.",
        "REFERENCE_0.30_0.60": r"REFERENCE_0\.30_0\.60 \(n=(\d+)\): heart — (.*?); breath — (.*?)\.",
    }
    label_counts: Counter[str] = Counter()
    for group, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            for label in ("AMBIGUOUS", "LIKELY_HUMAN", "LIKELY_NEAR_FIELD_OR_DIRECT_LEAKAGE", "LIKELY_FIXED_ENVIRONMENT_REFLECTION"):
                label_counts[label] += sum(int(value) for value in re.findall(rf"{re.escape(label)}=(\d+)", match.group(0)))
            evidence.append(
                {
                    "scope": "formal_B2",
                    "evidence": f"target_classification_{group}",
                    "classification": "REUSED_EXISTING_LABELS",
                    "evidence_level": "SUPPORTING",
                    "n_sessions": int(match.group(1)),
                    "detail": f"heart={match.group(2)}; breath={match.group(3)}; labels are not physical truth.",
                }
            )
    evidence.extend(
        [
            {
                "scope": "formal_B2",
                "evidence": "target_classification_LIKELY_HUMAN",
                "classification": "LIKELY_HUMAN",
                "evidence_level": "SUPPORTING__CANDIDATE_ONLY",
                "n_sessions": f"{label_counts['LIKELY_HUMAN']} target labels",
                "detail": "Existing B2 visible-shape label only; it does not replace placement ground truth or prove chest lock.",
            },
            {
                "scope": "formal_B2",
                "evidence": "target_classification_AMBIGUOUS",
                "classification": "AMBIGUOUS",
                "evidence_level": "SUPPORTING__CONSERVATIVE_DEFAULT",
                "n_sessions": f"{label_counts['AMBIGUOUS']} target labels",
                "detail": "Existing B2 retained ambiguous when the conservative profile/heatmap criteria were not met.",
            },
            {
                "scope": "formal_B2",
                "evidence": "target_classification_LIKELY_NEAR_FIELD_OR_DIRECT_LEAKAGE",
                "classification": "LIKELY_NEAR_FIELD_OR_DIRECT_LEAKAGE",
                "evidence_level": "NOT_OBSERVED__UNRESOLVED_CAUSE",
                "n_sessions": "0 target labels",
                "detail": "No batch-level target evidence met the existing conservative condition; this is not evidence that the mechanism is absent.",
            },
            {
                "scope": "formal_B2",
                "evidence": "target_classification_LIKELY_FIXED_ENVIRONMENT_REFLECTION",
                "classification": "LIKELY_FIXED_ENVIRONMENT_REFLECTION",
                "evidence_level": "NOT_OBSERVED__UNRESOLVED_CAUSE",
                "n_sessions": "0 target labels",
                "detail": "No batch-level target evidence met the existing conservative condition; this is not evidence that the mechanism is absent.",
            },
        ]
    )
    return evidence


def extract_formal_stability_evidence(report: Path) -> list[dict[str, object]]:
    """Parse the existing B2 diagnostic table without recomputing it."""
    output: list[dict[str, object]] = []
    groups = {"NEAR_LT_0.30", "FAR_GT_1.50", "REFERENCE_0.30_0.60"}
    for line in report.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 13 or cells[0] not in groups:
            continue
        output.append(
            {
                "group": cells[0],
                "n_sessions": int(cells[1]),
                "range_peak_mode_fraction_median": float(cells[6]),
                "range_peak_bin_std_median_bins": float(cells[7]),
                "channel_amplitude_cv_median": float(cells[8]),
                "usable_ratio_median": float(cells[9]),
                "below_threshold_ratio_median": float(cells[10]),
                "existing_hr_quality": cells[11],
                "existing_br_quality": cells[12],
                "analysis_role": "existing B2 diagnostic proxy; not target-lock confirmation or a new QC gate",
            }
        )
    if len(output) != 3:
        raise ValueError(f"expected three B2 diagnostic groups, got {len(output)}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-distance-qc", type=Path, required=True)
    parser.add_argument("--hr-paired", type=Path, required=True)
    parser.add_argument("--br-paired", type=Path, required=True)
    parser.add_argument("--b2-report", type=Path, required=True)
    parser.add_argument("--early-profile-figure", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.formal_distance_qc, args.hr_paired, args.br_paired, args.b2_report, args.early_profile_figure):
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    formal = read_csv(args.formal_distance_qc)
    hr, hr_rejected = normalize_hr(read_csv(args.hr_paired))
    br, br_rejected = normalize_br(read_csv(args.br_paired))
    if len(formal) != 71:
        raise ValueError(f"formal distance input expected 71 rows, got {len(formal)}")
    if len(hr) != 99:
        raise ValueError(f"ECG_VALID input expected 99 rows, got {len(hr)}")
    if len(br) != 99:
        raise ValueError(f"RSP_VALID input expected 99 rows, got {len(br)}")

    summary_rows: list[dict[str, object]] = []
    summary_rows.extend([metric_row("HR", "ECG_VALID", hr), metric_row("BR", "RSP_VALID", br)])
    for metric, rows, cohort in (("HR", hr, "ECG_VALID"), ("BR", br, "RSP_VALID")):
        historical = [row for row in rows if 0.30 <= float(row["distance_m"]) <= 1.50]
        row = metric_row(metric, "HISTORICAL_GATE_SENSITIVITY", historical)
        row["gate_label"] = "HISTORICAL_GATE_SENSITIVITY"
        summary_rows.append(row)
    write_csv(
        args.output_dir / "MMWAVE_DISTANCE_ERROR_SUMMARY.csv",
        summary_rows,
        union_fieldnames(summary_rows),
    )

    by_band = band_rows("HR", hr) + band_rows("BR", br)
    write_csv(args.output_dir / "MMWAVE_DISTANCE_ERROR_BY_BAND.csv", by_band, union_fieldnames(by_band))

    stability = [stability_summary("HR", hr), stability_summary("BR", br)]
    write_csv(args.output_dir / "MMWAVE_TARGET_STABILITY_COVERAGE_SUMMARY.csv", stability, list(stability[0].keys()))

    formal_rows: list[dict[str, object]] = []
    for label, _, _ in BANDS:
        subset = [row for row in formal if distance_band(number(row, "corrected_distance_0.037_m")) == label]
        formal_rows.append(
            {
                "distance_band": label,
                "n_sessions": len(subset),
                "n_participants": len({session_id(row["session"]) for row in subset}),
                "identity_note": "formal session id used as participant key; no second participant mapping inferred",
            }
        )
    qc_counts = Counter(row["corrected_distance_qc"] for row in formal)
    transition_counts = Counter(row["qc_change_type"] for row in formal)
    for label, count in sorted(qc_counts.items()):
        formal_rows.append({"distance_band": f"corrected_qc={label}", "n_sessions": count, "n_participants": count, "identity_note": "existing QC label; not ECG/RSP validity"})
    for label, count in sorted(transition_counts.items()):
        formal_rows.append({"distance_band": f"transition={label}", "n_sessions": count, "n_participants": count, "identity_note": "existing old-vs-corrected distance QC transition"})
    write_csv(args.output_dir / "MMWAVE_FORMAL_DISTANCE_DISTRIBUTION.csv", formal_rows, ["distance_band", "n_sessions", "n_participants", "identity_note"])

    physical_evidence = extract_b2_evidence(args.b2_report)
    formal_stability = extract_formal_stability_evidence(args.b2_report)
    write_csv(
        args.output_dir / "MMWAVE_FORMAL_TARGET_STABILITY_EVIDENCE.csv",
        formal_stability,
        list(formal_stability[0].keys()),
    )
    physical_evidence.append(
        {
            "scope": "early_BIOPAC_representative",
            "evidence": "existing_range_profile_figure",
            "classification": "OBSERVED_STRUCTURE_ONLY",
            "evidence_level": "ENGINEERING_REFERENCE",
            "n_sessions": "1 representative",
            "detail": "Existing representative range-profile figure is retained as visual context; it does not establish human placement, cause, or a gate.",
        }
    )
    write_csv(args.output_dir / "MMWAVE_PHYSICAL_EVIDENCE.csv", physical_evidence, ["scope", "evidence", "classification", "evidence_level", "n_sessions", "detail"])

    run_id = "MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_paths = {
        "formal_distance_qc": args.formal_distance_qc,
        "hr_paired_existing_estimator": args.hr_paired,
        "br_paired_existing_estimator": args.br_paired,
        "formal_B2_report": args.b2_report,
        "early_profile_figure": args.early_profile_figure,
    }
    source_meta = {
        role: {"basename": path.name, "sha256": sha256(path)} for role, path in source_paths.items()
    }
    output_names = [
        "MMWAVE_DISTANCE_ERROR_SUMMARY.csv",
        "MMWAVE_DISTANCE_ERROR_BY_BAND.csv",
        "MMWAVE_TARGET_STABILITY_COVERAGE_SUMMARY.csv",
        "MMWAVE_FORMAL_DISTANCE_DISTRIBUTION.csv",
        "MMWAVE_FORMAL_TARGET_STABILITY_EVIDENCE.csv",
        "MMWAVE_PHYSICAL_EVIDENCE.csv",
        "MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_REPORT_2026-08-30.md",
        "MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_MANIFEST.json",
    ]
    manifest = {
        "run_id": run_id,
        "status": "PASS / DESCRIPTIVE_DISTANCE_ERROR_COMPLETE__PHYSICAL_GATE_UNRESOLVED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "script": SCRIPT_NAME,
        "script_sha256": sha256(Path(__file__).resolve()),
        "analysis_set": {
            "formal_distance": {"sessions": 71, "participants": 71, "estimator_rerun": False},
            "ecg_valid_hr": {"windows": len(hr), "sessions": len({row['session'] for row in hr}), "participants": len({row['session'] for row in hr}), "rejected_by_source_validity": hr_rejected},
            "rsp_valid_br": {"windows": len(br), "sessions": len({row['session'] for row in br}), "participants": len({row['session'] for row in br}), "rejected_by_source_validity": br_rejected},
        },
        "distance_semantics": "corrected_distance_m = selected_bin * 0.037; selected bin reused from existing outputs; not human ground-truth distance",
        "predefined_bands_m": ["<0.20", "0.20-0.30", "0.30-0.60", "0.60-1.00", ">1.00"],
        "historical_gate_role": "HISTORICAL_GATE_SENSITIVITY_ONLY",
        "physical_gate_decision": "UNRESOLVED",
        "near_field_decision": "OBSERVED_NEAR_SIDE_STRUCTURE__CAUSE_UNRESOLVED__EXCLUSION_NOT_AUTHORIZED",
        "reuse_rejection_reason": "Existing B2 structural audit and separate HR/BR corrected paired tables did not provide one aggregate with continuous distance-vs-absolute-error, predeclared bands, source-valid coverage, and target-stability distributions; add only this downstream aggregation layer.",
        "estimator": "existing corrected-gate paired outputs; no producer, target rule, estimator, or QC threshold change",
        "source_files": source_meta,
        "outputs": output_names,
        "row_level_outputs": "none; only aggregate CSVs are written",
        "prohibitions_checked": ["no raw data change", "no C2B/C2C", "no new HR algorithm family", "no MAE-based threshold tuning", "no NIR/RGB producer change"],
    }
    (args.output_dir / "MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def fmt(value: object) -> str:
        return "NA" if value is None else str(value)

    hr_all = summary_rows[0]
    br_all = summary_rows[1]
    report = f"""# mmWave distance-error and physical-gate audit — 2026-08-30

Status: **PASS / descriptive distance-error complete; physical gate UNRESOLVED**
RUN_ID: `{run_id}`

## Decision

The existing corrected estimator outputs were aggregated on the pre-existing `ECG_VALID` and `RSP_VALID` reference rows. The analysis does not select a new distance threshold. Historical `0.30–1.50 m` is reported only as `HISTORICAL_GATE_SENSITIVITY`.

The formal front-end evidence remains: a near-side bright structure is observed in the locked B2 audit, but its cause is unresolved. It is not established as human chest, near-field/direct leakage, or fixed-environment reflection; a near-field exclusion gate is not authorized.

`REUSE_REJECTION_REASON`: the existing B2 structural audit and separate corrected HR/BR paired tables did not provide one aggregate with continuous distance-versus-absolute-error, predeclared bands, source-valid coverage, and target-stability distributions. This package therefore adds only a downstream aggregation layer.

## Denominators and reuse

| layer | windows/sessions | participants | role |
|---|---:|---:|---|
| formal corrected distance | 71 sessions | 71 session keys | distance/QC distribution only; no formal ECG/RSP truth |
| ECG_VALID HR | {len(hr)} windows | {len({row['session'] for row in hr})} | existing 99-window corrected HR-course output |
| RSP_VALID BR | {len(br)} windows | {len({row['session'] for row in br})} | existing 99-row valid RSP comparison output |

The five-participant reference layer must not be generalized to the formal 71-session cohort.

The separate #24 targeted ECG-QC layer is intentionally not merged into this package; this deliverable preserves the formal 71-session descriptive layer and the early 5-participant/99-window reference layer.

## Continuous distance versus absolute error

Correlations and slopes are descriptive because windows repeat within participant; no inferential p-value is used for gate selection.

| metric | N | MAE | median AE | bias | Pearson r(distance, AE) | Spearman rho(distance, AE) | slope AE/m |
|---|---:|---:|---:|---:|---:|---:|---:|
| HR / ECG_VALID | {hr_all['n_windows']} | {hr_all['abs_error_mean']} | {hr_all['abs_error_median']} | {hr_all['bias_mean_estimate_minus_reference']} | {fmt(hr_all['pearson_distance_abs_error'])} | {fmt(hr_all['spearman_distance_abs_error'])} | {fmt(hr_all['ols_abs_error_per_m'])} |
| BR / RSP_VALID | {br_all['n_windows']} | {br_all['abs_error_mean']} | {br_all['abs_error_median']} | {br_all['bias_mean_estimate_minus_reference']} | {fmt(br_all['pearson_distance_abs_error'])} | {fmt(br_all['spearman_distance_abs_error'])} | {fmt(br_all['ols_abs_error_per_m'])} |

These values quantify association in the existing outputs; they do not prove a causal distance effect or justify a gate.

## Predefined distance bands

`MMWAVE_DISTANCE_ERROR_BY_BAND.csv` reports N, session/participant counts, error summaries, and the same descriptive association fields for `<0.20`, `0.20–0.30`, `0.30–0.60`, `0.60–1.00`, and `>1.00 m`. Empty bands remain explicit rather than being dropped.

## Coverage and target stability

`MMWAVE_TARGET_STABILITY_COVERAGE_SUMMARY.csv` reports source-valid window coverage, session/participant counts, target-bin switch rate, channel switch rate, and session-level stability distributions. Stability means repeated existing target/channel values across ordered reference windows; it is not independent chest-lock evidence. `MMWAVE_FORMAL_TARGET_STABILITY_EVIDENCE.csv` separately retains the existing B2 formal diagnostic proxies (range-peak mode fraction/dispersion and channel-amplitude CV) for near, far, and reference groups; these are not new thresholds.

Formal corrected-distance session distribution is in `MMWAVE_FORMAL_DISTANCE_DISTRIBUTION.csv`. The corrected QC and old→corrected transition counts are retained as existing QC metadata, not physiology validity.

## Physical evidence classification

`MMWAVE_PHYSICAL_EVIDENCE.csv` reuses the B2 locked front-end audit and the existing early representative range-profile figure. Formal structure is **OBSERVED / SUPPORTING**; mechanism is **UNRESOLVED**; early visual context is **ENGINEERING_REFERENCE**. No target label is upgraded and no exclusion gate is introduced.

## Provenance and limits

- Distance semantics: selected bin × `0.037 m`; selected bins and estimator outputs are reused, not reselected.
- ECG/RSP validity: existing paired tables define the available valid rows; this audit adds no new ECG/RSP artifact rule.
- No raw, NPZ, participant-level, or row-level output is written by this script.
- Full input hashes and aggregate output list are in `MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_MANIFEST.json`.
"""
    (args.output_dir / "MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_REPORT_2026-08-30.md").write_text(report, encoding="utf-8")
    print(json.dumps({"run_id": run_id, "status": manifest["status"], "output_dir": str(args.output_dir), "hr_valid": len(hr), "br_valid": len(br)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
