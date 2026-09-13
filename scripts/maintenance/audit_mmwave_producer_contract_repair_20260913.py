"""Old-vs-new audit for the mmWave producer M1 contract repair.

The producer HR selector is stateful within each session/block: each probe consumes
an incoming previous_bpm anchor that is updated from prior probe HR output.
Therefore two determinism contracts are audited separately:

1) stateless derived fields: same frame membership => identical output;
2) stateful HR fields: same frame membership AND same incoming reconstructed
   previous_bpm anchor => identical output.

When local membership is unchanged but the incoming anchor has already diverged
because an earlier probe legitimately changed frame membership, HR differences are
reported as explained state propagation rather than contract failures.

This script does not train models and does not use Q1/Q2 for acceptance.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

KEYS = [
    "repeat_participant_id",
    "session_id",
    "block_id",
    "probe_id",
    "window_name",
]

STATELESS_DETERMINISTIC_IF_MEMBERSHIP_SAME = [
    "mmwave_state",
    "mmwave_observed",
    "mmwave_missing_reason",
    "mmwave_loadable",
    "mmwave_breath_rate_breaths_per_min_median",
    "mmwave_selected_bin_mode",
    "mmwave_selected_channel_mode",
    "mmwave_selected_bin_distance_proxy_m",
    "mmwave_phase_stability_median",
    "mmwave_motion_proxy_median",
]

STATEFUL_HR_FIELDS = [
    "mmwave_hr_freq_bpm_median",
    "mmwave_hr_time_bpm_median",
    "mmwave_hr_fused_bpm_median",
    "mmwave_hr_mean_confidence",
]

INTENTIONALLY_REDEFINED_QC = [
    "mmwave_timestamp_coverage_fraction",
    "mmwave_hr_usable_window_fraction",
]

HR_ANCHOR_UPDATE_CONFIDENCE = 0.12


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def canonical_key(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(key, "")).strip() for key in KEYS)


def combine(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.extend(read_csv(path))
    return rows


def unique_map(rows: list[dict[str, Any]], label: str) -> dict[tuple[str, ...], dict]:
    out: dict[tuple[str, ...], dict] = {}
    for row in rows:
        key = canonical_key(row)
        if key in out:
            raise ValueError(f"{label}: duplicate canonical key {key}")
        out[key] = row
    return out


def norm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return None
    if text.lower() in {"true", "false"}:
        return text.lower()
    try:
        numeric_value = float(text)
    except ValueError:
        return text
    if not math.isfinite(numeric_value):
        return text
    return f"{numeric_value:.12g}"


def numeric(value: Any) -> float | None:
    normalized = norm(value)
    if normalized is None:
        return None
    try:
        result = float(normalized)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def changed(a: Any, b: Any) -> bool:
    return norm(a) != norm(b)


def parse_bool(value: Any) -> bool | None:
    text = norm(value)
    if text is None:
        return None
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    return None


def state_label(row: dict[str, Any]) -> str:
    state = norm(row.get("mmwave_state")) or "MISSING"
    reason = norm(row.get("mmwave_missing_reason"))
    return f"{state}:{reason}" if reason else state


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def probe_order(row: dict[str, Any]) -> int:
    direct = numeric(row.get("probe_index_in_block"))
    if direct is not None:
        return int(direct)
    match = re.search(r"(\d+)$", str(row.get("probe_id", "")))
    if match:
        return int(match.group(1))
    raise ValueError(f"cannot determine probe order for {canonical_key(row)}")


def _anchor_close(a: float | None, b: float | None, atol: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=0.0, abs_tol=atol)


def reconstruct_incoming_anchor(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, ...], float | None]:
    """Reconstruct persisted previous_bpm state from emitted HR/confidence.

    The producer updates state after each probe:
      - first finite fused HR seeds previous_bpm regardless of confidence;
      - later finite fused HR updates only when confidence >= 0.12;
      - otherwise previous_bpm is retained.

    Exported fused HR/confidence are rounded, so this is audit-lineage evidence,
    not a byte-identical copy of internal floating-point state. It is sufficient
    to determine whether old/new emitted state histories were identical before a
    probe: identical histories reconstruct identically.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(
            (str(row.get("session_id", "")), str(row.get("block_id", ""))), []
        ).append(row)

    incoming: dict[tuple[str, ...], float | None] = {}
    for group_rows in groups.values():
        group_rows.sort(key=probe_order)
        previous: float | None = None
        for row in group_rows:
            incoming[canonical_key(row)] = previous
            fused = numeric(row.get("mmwave_hr_fused_bpm_median"))
            confidence = numeric(row.get("mmwave_hr_mean_confidence"))
            if fused is not None and (
                previous is None
                or (
                    confidence is not None
                    and confidence >= HR_ANCHOR_UPDATE_CONFIDENCE
                )
            ):
                previous = (
                    fused if previous is None else 0.8 * previous + 0.2 * fused
                )
    return incoming


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-j", type=Path, required=True)
    parser.add_argument("--old-e", type=Path, required=True)
    parser.add_argument("--new-j", type=Path, required=True)
    parser.add_argument("--new-e", type=Path, required=True)
    parser.add_argument("--frame-j", type=Path, required=True)
    parser.add_argument("--frame-e", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-probes", type=int, default=2320)
    args = parser.parse_args()

    old_rows = combine([args.old_j, args.old_e])
    new_rows = combine([args.new_j, args.new_e])
    frame_rows = combine([args.frame_j, args.frame_e])

    old_map = unique_map(old_rows, "old")
    new_map = unique_map(new_rows, "new")
    frame_map = unique_map(frame_rows, "frame_audit")
    old_anchor = reconstruct_incoming_anchor(old_rows)
    new_anchor = reconstruct_incoming_anchor(new_rows)

    old_keys = set(old_map)
    new_keys = set(new_map)
    frame_keys = set(frame_map)
    only_old = sorted(old_keys - new_keys)
    only_new = sorted(new_keys - old_keys)
    missing_frame = sorted(new_keys - frame_keys)
    extra_frame = sorted(frame_keys - new_keys)

    all_keys = sorted(old_keys | new_keys)
    detail: list[dict[str, Any]] = []
    membership_changed_n = 0
    strict_frame_violations = 0
    stateless_violations = 0
    stateful_unexplained_violations = 0
    stateful_explained_by_anchor = 0
    raw_same_membership_hr_difference_n = 0
    state_transition_counts: Counter[str] = Counter()
    hr_changed_n = 0
    br_changed_n = 0
    usable_fraction_changed_n = 0

    for key in all_keys:
        old = old_map.get(key, {})
        new = new_map.get(key, {})
        frame = frame_map.get(key, {})
        membership_changed = parse_bool(frame.get("membership_changed"))
        if membership_changed is True:
            membership_changed_n += 1

        strict_before = parse_bool(frame.get("new_all_selected_before_probe"))
        audit_status = norm(frame.get("audit_status"))
        if audit_status == "SELECTED" and strict_before is not True:
            strict_frame_violations += 1

        old_incoming = old_anchor.get(key)
        new_incoming = new_anchor.get(key)
        incoming_anchor_same = _anchor_close(old_incoming, new_incoming)

        row: dict[str, Any] = {name: value for name, value in zip(KEYS, key)}
        row.update(
            {
                "frame_audit_status": frame.get("audit_status"),
                "frame_audit_reason": frame.get("audit_reason"),
                "legacy_n_frames": frame.get("legacy_n_frames"),
                "new_n_frames": frame.get("new_n_frames"),
                "legacy_membership_digest_sha256": frame.get(
                    "legacy_membership_digest_sha256"
                ),
                "new_membership_digest_sha256": frame.get(
                    "new_membership_digest_sha256"
                ),
                "membership_changed": membership_changed,
                "new_all_selected_before_probe": strict_before,
                "old_incoming_previous_bpm_reconstructed": old_incoming,
                "new_incoming_previous_bpm_reconstructed": new_incoming,
                "incoming_previous_bpm_same": incoming_anchor_same,
                "old_state": state_label(old),
                "new_state": state_label(new),
            }
        )

        transition = f"{state_label(old)} -> {state_label(new)}"
        state_transition_counts[transition] += 1

        stateless_changes: list[str] = []
        for field in STATELESS_DETERMINISTIC_IF_MEMBERSHIP_SAME:
            is_changed = changed(old.get(field), new.get(field))
            row[f"{field}__changed"] = is_changed
            if is_changed:
                stateless_changes.append(field)

        stateful_hr_changes: list[str] = []
        for field in STATEFUL_HR_FIELDS:
            is_changed = changed(old.get(field), new.get(field))
            row[f"{field}__changed"] = is_changed
            if is_changed:
                stateful_hr_changes.append(field)

        same_membership_selected = (
            audit_status == "SELECTED" and membership_changed is False
        )

        stateless_violation = bool(
            same_membership_selected and stateless_changes
        )
        if stateless_violation:
            stateless_violations += 1

        raw_same_membership_hr_difference = bool(
            same_membership_selected and stateful_hr_changes
        )
        if raw_same_membership_hr_difference:
            raw_same_membership_hr_difference_n += 1

        explained_stateful = bool(
            raw_same_membership_hr_difference and not incoming_anchor_same
        )
        unexplained_stateful = bool(
            raw_same_membership_hr_difference and incoming_anchor_same
        )
        if explained_stateful:
            stateful_explained_by_anchor += 1
        if unexplained_stateful:
            stateful_unexplained_violations += 1

        row["stateless_deterministic_violation_when_membership_same"] = (
            stateless_violation
        )
        row["stateless_changed_fields"] = ";".join(stateless_changes)
        row["raw_stateful_hr_difference_when_membership_same"] = (
            raw_same_membership_hr_difference
        )
        row["stateful_hr_difference_explained_by_anchor_divergence"] = (
            explained_stateful
        )
        row[
            "stateful_hr_violation_when_membership_and_anchor_same"
        ] = unexplained_stateful
        row["stateful_hr_changed_fields"] = ";".join(stateful_hr_changes)

        old_hr = numeric(old.get("mmwave_hr_fused_bpm_median"))
        new_hr = numeric(new.get("mmwave_hr_fused_bpm_median"))
        old_br = numeric(old.get("mmwave_breath_rate_breaths_per_min_median"))
        new_br = numeric(new.get("mmwave_breath_rate_breaths_per_min_median"))
        row["hr_fused_delta_bpm"] = (
            new_hr - old_hr if old_hr is not None and new_hr is not None else None
        )
        row["br_delta_breaths_per_min"] = (
            new_br - old_br if old_br is not None and new_br is not None else None
        )
        if changed(
            old.get("mmwave_hr_fused_bpm_median"),
            new.get("mmwave_hr_fused_bpm_median"),
        ):
            hr_changed_n += 1
        if changed(
            old.get("mmwave_breath_rate_breaths_per_min_median"),
            new.get("mmwave_breath_rate_breaths_per_min_median"),
        ):
            br_changed_n += 1
        if changed(
            old.get("mmwave_hr_usable_window_fraction"),
            new.get("mmwave_hr_usable_window_fraction"),
        ):
            usable_fraction_changed_n += 1

        for field in INTENTIONALLY_REDEFINED_QC:
            row[f"old_{field}"] = old.get(field)
            row[f"new_{field}"] = new.get(field)

        detail.append(row)

    pass_contract = (
        len(old_rows) == args.expected_probes
        and len(new_rows) == args.expected_probes
        and not only_old
        and not only_new
        and not missing_frame
        and not extra_frame
        and strict_frame_violations == 0
        and stateless_violations == 0
        and stateful_unexplained_violations == 0
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "mmwave_contract_old_vs_new_audit.csv"
    write_csv(detail_path, detail)
    summary = {
        "status": "PASS" if pass_contract else "FAIL",
        "expected_probe_n": args.expected_probes,
        "old_probe_n": len(old_rows),
        "new_probe_n": len(new_rows),
        "frame_audit_probe_n": len(frame_rows),
        "only_in_old_n": len(only_old),
        "only_in_new_n": len(only_new),
        "missing_frame_audit_n": len(missing_frame),
        "extra_frame_audit_n": len(extra_frame),
        "membership_changed_n": membership_changed_n,
        "strict_new_frame_membership_violation_n": strict_frame_violations,
        "stateless_deterministic_violation_when_membership_same_n": stateless_violations,
        "raw_stateful_hr_difference_when_membership_same_n": raw_same_membership_hr_difference_n,
        "stateful_hr_difference_explained_by_anchor_divergence_n": stateful_explained_by_anchor,
        "stateful_hr_violation_when_membership_and_anchor_same_n": stateful_unexplained_violations,
        "hr_fused_changed_n": hr_changed_n,
        "br_changed_n": br_changed_n,
        "usable_fraction_changed_n": usable_fraction_changed_n,
        "state_transitions": dict(sorted(state_transition_counts.items())),
        "acceptance_uses_q1_q2": False,
        "determinism_contract": {
            "stateless_fields": (
                "same frame membership requires identical outputs"
            ),
            "stateful_hr_fields": (
                "same frame membership plus same incoming previous_bpm anchor "
                "requires identical HR outputs"
            ),
            "anchor_update_rule": (
                "first finite fused HR seeds state; subsequent finite fused HR "
                "updates at confidence >= 0.12 using 0.8*previous + 0.2*fused"
            ),
        },
        "scientific_scope": (
            "producer contract/provenance audit only; not physiology validation"
        ),
    }
    summary_path = args.output_dir / "mmwave_contract_old_vs_new_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not pass_contract:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
