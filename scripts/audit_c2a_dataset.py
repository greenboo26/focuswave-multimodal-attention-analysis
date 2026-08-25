"""Build compact C2a audit summaries from the existing read-only audit manifest.

This script does not read raw videos, raw ADC, or questionnaire workbooks. It
only normalizes the already generated C2a manifest and the existing subject
session master into local audit summaries. Row-level outputs stay local.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


AUDIT = Path(r"D:\Project\厚粲杯\08_算法\output\40_正式实验\04_C2a_标签与样本单元审计\derived_20260826")
MASTER = Path(r"D:\Project\厚粲杯\11_数据\derived\analysis_tables_v2\subject_session_master_v2.csv")
OUT = AUDIT


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def truth(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main():
    probes = read_csv(AUDIT / "c2a_sample_manifest.csv")
    master = read_csv(MASTER)
    probe_key = lambda r: (r["subject_id"], r.get("block_num", ""), r["probe_id"], r.get("probe_onset_time", ""))
    base_probes = {}
    for row in probes:
        base_probes.setdefault(probe_key(row), row)
    base = list(base_probes.values())
    subject_ids = sorted({r["subject_id"] for r in base})

    by_subject = {}
    for row in master:
        sid = str(row.get("single_experiment_id", "")).zfill(3)
        if sid in subject_ids and sid not in by_subject:
            by_subject[sid] = row

    group_rows = []
    for sid in subject_ids:
        row = by_subject.get(sid, {})
        group = row.get("repeat_participant_id", "")
        status = "deterministic_existing_crosswalk" if group else "unresolved"
        group_rows.append({
            "subject_id": sid,
            "group_subject_id": group,
            "mapping_status": status,
            "source": "analysis_tables_v2/subject_session_master_v2.csv" if group else "no_matching_master_row",
        })
    write_csv(OUT / "c2a_subject_group_map.csv", group_rows[0].keys(), group_rows)

    labels = Counter(str(r.get("probe_response", "")).strip() for r in base)
    total = sum(labels.values())
    label_rows = []
    for value in sorted(labels, key=lambda x: (x == "", x)):
        label_rows.append({
            "label_field": "probe_response",
            "raw_value": value,
            "n_probe": labels[value],
            "proportion": round(labels[value] / total, 8) if total else 0,
            "semantic_status": "raw_code_not_preassigned_to_psychological_construct",
        })
    write_csv(OUT / "c2a_label_summary.csv", label_rows[0].keys(), label_rows)

    unique_subjects = {r["subject_id"] for r in base}
    modality_rows = [
        {"modality": "behavior", "n_probe": len(base), "n_subject": len(unique_subjects), "n_session": len(unique_subjects), "coverage_definition": "probe manifest present", "quality_status": "audit_only"},
        {"modality": "mmwave_raw_or_timestamp", "n_probe": len({probe_key(r) for r in base if truth(r.get('mmwave_raw_present')) or truth(r.get('mmwave_timestamp_present'))}), "n_subject": len({r['subject_id'] for r in base if truth(r.get('mmwave_raw_present')) or truth(r.get('mmwave_timestamp_present'))}), "n_session": len({r['subject_id'] for r in base if truth(r.get('mmwave_raw_present')) or truth(r.get('mmwave_timestamp_present'))}), "coverage_definition": "raw/timestamp presence in C2a manifest", "quality_status": "not physiological validity"},
        {"modality": "RGB", "n_probe": "not_per_probe", "n_subject": sum(truth(by_subject.get(s, {}).get('j_raw_rgb_video_present', '')) for s in subject_ids), "n_session": sum(truth(by_subject.get(s, {}).get('j_raw_rgb_video_present', '')) for s in subject_ids), "coverage_definition": "existing subject master raw RGB video flag", "quality_status": "session_level_only"},
        {"modality": "NIR", "n_probe": "see_prior_c3", "n_subject": "see_prior_c3", "n_session": "see_prior_c3", "coverage_definition": "prior C3 aligned asset; not recomputed in C2a", "quality_status": "identity/quality must be joined explicitly"},
    ]
    write_csv(OUT / "c2a_modality_coverage.csv", modality_rows[0].keys(), modality_rows)

    summary = {
        "status": "C2A_DATASET_AUDIT_COMPLETE",
        "subject_count": len(unique_subjects),
        "group_subject_count_deterministically_mapped": len({r["group_subject_id"] for r in group_rows if r["group_subject_id"]}),
        "session_count": len(unique_subjects),
        "probe_count": len(base),
        "manifest_rows": len(probes),
        "candidate_windows_s": [10, 30, 60],
        "window_complete_counts": {str(w): sum(truth(r.get("timestamp_full")) for r in probes if str(r.get("window_s")) == str(w)) for w in (10, 30, 60)},
        "label_field": "probe_response",
        "label_values": dict(labels),
        "do_not_train": True,
        "do_not_enter_hrv": True,
        "blockers": [
            "probe_response semantic mapping is not independently validated in this audit",
            "questionnaire-to-current-J-subject mapping is not deterministic for all records",
            "timestamp coverage is not signal-quality validation",
            "rest usability has temporal boundary evidence but no independent signal-quality validation",
        ],
    }
    (OUT / "c2a_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
