"""Inventory local RS6240/BIOPAC calibration references without scoring signals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import bioread


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_record(root: Path, path: Path, hash_file: bool = True) -> dict[str, Any]:
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path) if hash_file else "MISSING_EVIDENCE_NOT_HASHED_PHASE_2A",
    }


def build(root: Path) -> dict[str, Any]:
    sessions = []
    for subject_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        acq_files = list(subject_dir.glob("*.acq"))
        meta_files = list((subject_dir / "mmwave").glob("*.meta.json"))
        timestamp_files = list((subject_dir / "mmwave").glob("*_timestamps.csv"))
        radar_bin_files = list((subject_dir / "mmwave").glob("*.datacube.bin"))
        npz_files = list((subject_dir / "mmwave").glob("*.npz"))
        if len(acq_files) != 1 or len(meta_files) != 1:
            sessions.append({"subject_directory": subject_dir.name, "status": "MISSING_EVIDENCE", "reason": "expected one ACQ and one radar meta file"})
            continue
        acq_path = acq_files[0]
        meta_path = meta_files[0]
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        acq = bioread.read_file(str(acq_path))
        channels = [
            {"name": str(channel.name), "sampling_rate_hz": float(channel.samples_per_second), "n_samples": len(channel.data)}
            for channel in acq.channels
        ]
        ecg_channels = [channel for channel in channels if "ECG" in channel["name"].upper()]
        rsp_channels = [channel for channel in channels if "RSP" in channel["name"].upper()]
        folder_digits = "".join(character for character in subject_dir.name if character.isdigit())
        acq_digits = "".join(character for character in acq_path.stem if character.isdigit())
        meta_digits = str(meta.get("subject_id", ""))
        sessions.append(
            {
                "subject_directory": subject_dir.name,
                "declared_session": meta.get("session"),
                "identifier_consistency": {
                    "folder": folder_digits,
                    "acq_filename": acq_digits,
                    "radar_meta": meta_digits,
                    "status": "PASS" if len({folder_digits, acq_digits, meta_digits}) == 1 else "MISMATCH_REQUIRES_ADJUDICATION",
                },
                "reference": {
                    "raw_ecg": bool(ecg_channels),
                    "raw_rsp": bool(rsp_channels),
                    "preannotated_r_peaks": False,
                    "channels": channels,
                },
                "radar": {
                    "transport": meta.get("transport"),
                    "frame_count": meta.get("frame_count"),
                    "duration_s": meta.get("duration_s"),
                    "fps": meta.get("fps"),
                    "range_fft": meta.get("range_fft"),
                    "doppler_fft": meta.get("doppler_fft"),
                    "tx_ant": meta.get("tx_ant"),
                    "rx_ant": meta.get("rx_ant"),
                    "npz_file_count": len(npz_files),
                },
                "sources": {
                    "acq": source_record(root, acq_path),
                    "radar_meta": source_record(root, meta_path),
                    "radar_timestamps": source_record(root, timestamp_files[0]) if len(timestamp_files) == 1 else None,
                    "radar_bin": source_record(root, radar_bin_files[0], hash_file=False) if len(radar_bin_files) == 1 else None,
                },
                "status": "PARTIAL_RAW_LINK_PRESENT_DERIVED_MAPPING_NOT_FROZEN",
            }
        )
    return {
        "schema_version": "rs6240-biopac-reference-inventory-v1",
        "status": "PARTIAL",
        "scope": "read-only Phase 2A source/reference inventory; no signal scoring",
        "summary": {
            "session_directories": len(sessions),
            "raw_ecg_sessions": sum(bool(item.get("reference", {}).get("raw_ecg")) for item in sessions),
            "raw_rsp_sessions": sum(bool(item.get("reference", {}).get("raw_rsp")) for item in sessions),
            "identifier_mismatches": sum(item.get("identifier_consistency", {}).get("status") != "PASS" for item in sessions),
        },
        "boundary": "Radar BIN hashes and exact raw-to-derived window mapping remain MISSING_EVIDENCE; sub-2 has ECG but no RSP and cannot score BR.",
        "sessions": sessions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = build(args.data_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
