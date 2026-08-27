"""Freeze a Git-safe provenance manifest for the AgeBalanced 60 GHz dataset.

The output contains hashes, file counts, session identities, sampling metadata,
and reference availability. It never copies signal values or local absolute
paths into the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "agebalanced-60ghz-provenance-v1"
SPLIT_SCHEMA_VERSION = "focuswave-mmwave-agebalanced-split-v1"
SEED = 20260827
SPLIT_SALT = "focuswave-mmwave-v2"
EXPECTED_SESSION_LAYOUT = (
    ("Lying", "Rest"),
    ("Lying", "Post-exercise"),
    ("Sitting", "Rest"),
    ("Sitting", "Post-exercise"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_timestamp(value: str) -> float:
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def csv_time_summary(path: Path, timestamp_field: str | None = "Timestamp") -> dict[str, Any]:
    row_count = 0
    previous: float | None = None
    positive_deltas: list[float] = []
    nonmonotonic = 0
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        if timestamp_field is None:
            rows = (row[0] for row in csv.reader(stream) if row)
        else:
            reader = csv.DictReader(stream)
            if timestamp_field not in (reader.fieldnames or []):
                raise ValueError(f"{path}: missing {timestamp_field!r} column")
            rows = (row[timestamp_field] for row in reader)
        for raw in rows:
            if first_timestamp is None:
                first_timestamp = raw
            last_timestamp = raw
            current = parse_timestamp(raw)
            if previous is not None:
                delta = current - previous
                if delta > 0:
                    positive_deltas.append(delta)
                else:
                    nonmonotonic += 1
            previous = current
            row_count += 1
    median_delta = statistics.median(positive_deltas) if positive_deltas else None
    return {
        "rows": row_count,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "median_delta_s": median_delta,
        "estimated_sampling_rate_hz": (1.0 / median_delta) if median_delta else None,
        "nonmonotonic_intervals": nonmonotonic,
    }


def canonical_digest(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda item: item["relative_path"]):
        line = f'{record["relative_path"]}|{record["size_bytes"]}|{record["sha256"]}\n'
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def split_rank(subject_id: str) -> str:
    material = f"{SPLIT_SALT}|{SEED}|{subject_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def file_record(root: Path, path: Path) -> dict[str, Any]:
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_manifest(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    participants = sorted(path for path in root.glob("P[0-9][0-9][0-9]") if path.is_dir())
    sessions: list[dict[str, Any]] = []
    file_records = [file_record(root, path) for path in root.rglob("*") if path.is_file()]
    missing: list[str] = []

    for participant in participants:
        for posture, condition in EXPECTED_SESSION_LAYOUT:
            session_dir = participant / posture / condition
            session_id = f"{participant.name}_{posture.lower()}_{condition.lower().replace('-', '_')}"
            expected_files = [
                "movesense_acc.csv",
                "movesense_ecg.csv",
                "radar_chirpConfig.json",
                "radar_rFFTs.zlib",
                "radar_timestamps.csv",
            ]
            if condition == "Rest":
                expected_files.append("non_breathing_ts.csv")
            missing_here = [name for name in expected_files if not (session_dir / name).is_file()]
            missing.extend(f"{session_id}/{name}" for name in missing_here)
            if missing_here:
                sessions.append({"session_id": session_id, "missing_files": missing_here})
                continue

            ecg_summary = csv_time_summary(session_dir / "movesense_ecg.csv")
            radar_summary = csv_time_summary(session_dir / "radar_timestamps.csv", timestamp_field=None)
            with (session_dir / "radar_chirpConfig.json").open("r", encoding="utf-8") as stream:
                chirp = json.load(stream)
            periodicity_ms = float(chirp["PERIODICITY"])
            sessions.append(
                {
                    "subject_id": participant.name,
                    "session_id": session_id,
                    "posture": posture,
                    "condition": condition,
                    "historical_220_scope": condition == "Rest",
                    "relative_directory": session_dir.relative_to(root).as_posix(),
                    "files": {name: (session_dir / name).relative_to(root).as_posix() for name in expected_files},
                    "radar": {
                        "representation": "complex range FFT frames serialized with zlib/pickle",
                        "configured_frame_rate_hz": 1000.0 / periodicity_ms,
                        "timestamp_summary": radar_summary,
                        "chirp_config": chirp,
                    },
                    "reference": {
                        "raw_ecg": True,
                        "ecg_fields": ["Timestamp", "mV"],
                        "ecg_summary": ecg_summary,
                        "preannotated_r_peaks": False,
                        "raw_rsp": False,
                        "rsp_fields": [],
                        "chest_accelerometer": True,
                        "accelerometer_is_rsp": False,
                        "breath_hold_marker": condition == "Rest",
                    },
                }
            )

    ranked = sorted((split_rank(path.name), path.name) for path in participants)
    development = sorted(subject_id for _, subject_id in ranked[:30])
    held_out = sorted(subject_id for _, subject_id in ranked[30:])
    split = {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "status": "FROZEN_BEFORE_HELDOUT_SCORING",
        "seed": SEED,
        "algorithm": "sort SHA256('focuswave-mmwave-v2|20260827|subject_id'); first 30 development, remaining held_out",
        "participant_unit": "all sessions for a participant remain in one split",
        "development_participants": development,
        "held_out_participants": held_out,
        "counts": {"development": len(development), "held_out": len(held_out)},
    }

    ecg_rates = [
        session["reference"]["ecg_summary"]["estimated_sampling_rate_hz"]
        for session in sessions
        if "reference" in session
    ]
    radar_rates = [
        session["radar"]["configured_frame_rate_hz"] for session in sessions if "radar" in session
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not missing and len(participants) == 110 and len(sessions) == 440 else "PARTIAL",
        "dataset": {
            "id": "agebalanced_60ghz_ecg",
            "doi": "10.5281/zenodo.16760683",
            "paper_doi": "10.1038/s41597-026-07172-9",
            "license": "MISSING_EVIDENCE",
            "license_note": "No license file was found in the extracted package or db_records.zip; record-specific Zenodo metadata was not recoverable during Phase 2A.",
        },
        "scope": {
            "participants": len(participants),
            "sessions_total": len(sessions),
            "historical_sessions": sum(bool(session.get("historical_220_scope")) for session in sessions),
            "historical_definition": "all directories matched by P*/**/Rest in validate_external_gold_0814.py; two Rest sessions per participant",
            "post_exercise_sessions": sum(session.get("condition") == "Post-exercise" for session in sessions),
        },
        "sampling_summary": {
            "radar_configured_hz_unique": sorted(set(radar_rates)),
            "ecg_estimated_hz_min": min(ecg_rates),
            "ecg_estimated_hz_median": statistics.median(ecg_rates),
            "ecg_estimated_hz_max": max(ecg_rates),
        },
        "reference_boundary": {
            "hr": "raw ECG is available; ECG QC and frozen R-peak detection are required before scoring",
            "br": "BLOCKED_NO_RSP; chest accelerometer and breath-hold markers are not RSP",
            "hrv": "BLOCKED; no preannotated beats and V2 hrv_authorized=false",
        },
        "missing_expected_files": missing,
        "source_package": {
            "file_count": len(file_records),
            "total_bytes": sum(item["size_bytes"] for item in file_records),
            "canonical_file_manifest_sha256": canonical_digest(file_records),
            "files": file_records,
        },
        "sessions": sessions,
    }
    return manifest, split


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split-output", required=True, type=Path)
    args = parser.parse_args()
    root = args.data_root.resolve()
    manifest, split = build_manifest(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.split_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.split_output.write_text(json.dumps(split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
