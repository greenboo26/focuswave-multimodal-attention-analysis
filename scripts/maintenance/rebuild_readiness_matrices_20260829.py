from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"D:\Project\厚粲杯\11_数据")
OUT = ROOT / "docs" / "results" / "final_merge_readiness_20260829"
ANCHOR = DATA / "derived" / "focuswave_canonical_v1_rerun_20260826" / "focuswave_canonical_v1" / "beijing-nvidia-main" / "report_cohort_v1" / "merge_ready" / "report_analysis_cohort.csv"
MMWAVE = DATA / "derived" / "focuswave_canonical_v1_rerun_20260826" / "focuswave_canonical_v1" / "beijing-nvidia-main" / "mmwave_m1_v1" / "merge_ready" / "m1_q0_probe_matrix.csv"
RGB = DATA / "04_Attention-Analysis_nvidia-cuda_RGB" / "cohort_status.csv"
NIR = DATA / "derived" / "nir_69session_final_probe_analysis_v1" / "nir_session_qc_summary.csv"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    anchor = read(ANCHOR)
    mmwave = read(MMWAVE)
    rgb = {row["subject"]: row for row in read(RGB)}
    nir = {row["subject"]: row for row in read(NIR)}
    mmwave_by_key = {
        f"{row['subject'].zfill(3)}|{row['probe_id']}": row for row in mmwave
    }
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in anchor:
        grouped[row["session_id"]].append(row)

    session_fields = [
        "subject", "session", "repeat_participant_id", "behavior_available", "probe_available",
        "mmwave_available", "mmwave_qc_class", "rgb_available", "rgb_qc_class", "nir_available",
        "nir_qc_class", "usable_behavior_baseline", "usable_behavior_rgb", "usable_behavior_mmwave",
        "usable_behavior_rgb_mmwave", "usable_full_multimodal", "exclusion_reason",
    ]
    probe_fields = [
        "subject", "session", "repeat_participant_id", "probe_id", "behavior_available", "probe_available",
        "mmwave_available", "mmwave_qc_class", "rgb_available", "rgb_qc_class", "nir_available",
        "nir_qc_class", "usable_behavior_baseline", "usable_behavior_rgb", "usable_behavior_mmwave",
        "usable_behavior_rgb_mmwave", "usable_full_multimodal", "exclusion_reason",
    ]
    sessions: list[dict[str, str]] = []
    probes: list[dict[str, str]] = []
    for session_id in sorted(grouped, key=lambda value: int(value.rsplit("-", 1)[-1])):
        group = grouped[session_id]
        first = group[0]
        subject = f"sub-{first['subject_id'].zfill(3)}"
        mm_rows = [row for row in mmwave if row["subject"].zfill(3) == first["subject_id"].zfill(3)]
        ok_rows = [row for row in mm_rows if row.get("quality") == "ok" and row.get("q_extraction_ok") == "1.0"]
        rgb_ok = subject in rgb and rgb[subject].get("status") in {"complete", "skipped_complete"}
        nir_ok = subject in nir
        session_mmwave = "yes" if mm_rows else "no"
        session_qc = "preliminary_screening_only" if ok_rows else "no_preliminary_screening_flag"
        session_row = {
            "subject": subject,
            "session": session_id,
            "repeat_participant_id": first["repeat_participant_id"],
            "behavior_available": "yes",
            "probe_available": "yes",
            "mmwave_available": session_mmwave,
            "mmwave_qc_class": session_qc,
            "rgb_available": "yes" if rgb_ok else "no",
            "rgb_qc_class": "engineering_complete_formal_analysis_not_authorized" if rgb_ok else "missing",
            "nir_available": "yes" if nir_ok else "no",
            "nir_qc_class": "completion_present_probe_alignment_not_recomputed" if nir_ok else "not_completion_in_canonical_cohort",
            "usable_behavior_baseline": "yes",
            "usable_behavior_rgb": "yes" if rgb_ok else "no",
            "usable_behavior_mmwave": "preliminary_screening_only" if ok_rows else "no_preliminary_screening_flag",
            "usable_behavior_rgb_mmwave": "preliminary_screening_only" if rgb_ok and ok_rows else "no_preliminary_screening_flag",
            "usable_full_multimodal": "yes" if rgb_ok and ok_rows and nir_ok else "no",
            "exclusion_reason": "" if rgb_ok and ok_rows and nir_ok else "modality_missing_or_not_formally_authorized",
        }
        sessions.append(session_row)
        for item in group:
            key = f"{first['subject_id'].zfill(3)}|{item['session_probe_index']}"
            source = mmwave_by_key.get(key)
            passed = source is not None and source.get("quality") == "ok" and source.get("q_extraction_ok") == "1.0"
            probe_row = {
                "subject": subject,
                "session": session_id,
                "repeat_participant_id": first["repeat_participant_id"],
                "probe_id": item["session_probe_index"],
                "behavior_available": "yes",
                "probe_available": "yes",
                "mmwave_available": "yes" if source is not None else "no",
                "mmwave_qc_class": "preliminary_screening_only" if passed else "no_preliminary_screening_flag",
                "rgb_available": "yes" if rgb_ok else "no",
                "rgb_qc_class": "engineering_complete_formal_analysis_not_authorized" if rgb_ok else "missing",
                "nir_available": "yes" if nir_ok else "no",
                "nir_qc_class": "completion_present_probe_alignment_not_recomputed" if nir_ok else "not_completion_in_canonical_cohort",
                "usable_behavior_baseline": "yes",
                "usable_behavior_rgb": "yes" if rgb_ok else "no",
                "usable_behavior_mmwave": "preliminary_screening_only" if passed else "no_preliminary_screening_flag",
                "usable_behavior_rgb_mmwave": "preliminary_screening_only" if rgb_ok and passed else "no_preliminary_screening_flag",
                "usable_full_multimodal": "yes" if rgb_ok and passed and nir_ok else "no",
                "exclusion_reason": "" if rgb_ok and passed and nir_ok else "modality_missing_or_not_formally_authorized",
            }
            probes.append(probe_row)

    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "merge_session_availability_matrix.csv", sorted(sessions, key=lambda row: row["subject"]), session_fields)
    write(OUT / "merge_probe_level_availability_matrix.csv", sorted(probes, key=lambda row: (row["subject"], int(row["probe_id"]))), probe_fields)
    print(f"rebuilt sessions={len(sessions)} probes={len(probes)}")


if __name__ == "__main__":
    main()


