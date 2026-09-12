#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Write CLOUD_HANDOFF_VERIFICATION.json for the external-asset-audit Drive handoff.

File: finalize_external_audit_cloud_handoff_20260913.py
Version: 1.0.0
Purpose:
    上传并逐文件回读校验后，生成云端交接验证记录。所有 digest 都从本地文件与回读
    目录重新计算，不手抄。不打印、读取或写入任何 rclone 凭据。

Usage:
    python scripts/maintenance/finalize_external_audit_cloud_handoff_20260913.py \
        --readback-dir <local staging dir>

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULT_DIR = REPO / "docs" / "results" / "2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1"

CLOUD_FOLDER_NAME = "2026-09-13_mmwave_external_validation_asset_audit_v1"
CLOUD_FOLDER_PARENT = "_AI_HANDOFF"
CLOUD_FOLDER_PARENT_ID = "1wZ6fHAyz4JMBwQ7LxL2fYZ9DdhO4XAfL"
CLOUD_REMOTE_PATH = f"gdrive:{CLOUD_FOLDER_NAME}"

# 自指文件：本验证记录无法收录自己的最终 digest；其摘要记录在 HANDOFF 与 issue pointer。
SELF_REFERENTIAL = {"CLOUD_HANDOFF_VERIFICATION.json"}


def sha256(path: Path) -> str:
    """Return the uppercase SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main(argv: list[str] | None = None) -> int:
    """Build and write the cloud handoff verification record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readback-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=RESULT_DIR)
    args = parser.parse_args(argv)

    out: Path = args.out_dir
    readback: Path = args.readback_dir
    if not readback.exists():
        raise SystemExit(f"readback directory missing: {readback}")

    per_file = []
    matched = 0
    for path in sorted(p for p in out.iterdir() if p.is_file()):
        name = path.name
        if name in SELF_REFERENTIAL:
            continue
        local_digest = sha256(path)
        cloud_path = readback / name
        if not cloud_path.exists():
            per_file.append({"name": name, "status": "MISSING_ON_CLOUD", "local_sha256": local_digest})
            continue
        cloud_digest = sha256(cloud_path)
        status = "MATCH" if cloud_digest == local_digest else "MISMATCH"
        if status == "MATCH":
            matched += 1
        per_file.append({
            "name": name,
            "status": status,
            "local_sha256": local_digest,
            "cloud_sha256": cloud_digest,
        })

    names = [entry["name"] for entry in per_file]
    forbidden = [n for n in names if "INTEGRATION_SNAPSHOT" in n or "ESTIMATOR_IMPROVEMENT" in n
                 or "LOW_BIAS_MECHANISM" in n]

    record = {
        "task_id": "mmwave_external_validation_asset_audit_v1",
        "run_id": "mmwave_external_validation_asset_audit_v1_20260913_r1",
        "folder_name": CLOUD_FOLDER_NAME,
        "folder_parent": CLOUD_FOLDER_PARENT,
        "folder_parent_id": CLOUD_FOLDER_PARENT_ID,
        "remote_path": CLOUD_REMOTE_PATH,
        "access_pattern": "--drive-root-folder-id " + CLOUD_FOLDER_PARENT_ID,
        "transport": "rclone 1.75.1 (portable, D:\\Project\\.tools\\rclone.exe), Google Drive remote 'gdrive'; "
                     "credentials live only in the machine-local rclone config and were never printed, logged or committed.",
        "cloud_file_count": matched,
        "cloud_files": names,
        "verified_by_readback": True,
        "readback_dir": str(readback),
        "per_file": per_file,
        "frozen_artifacts_all_match": matched == len(per_file),
        "frozen_artifacts_checked": matched,
        "no_prior_bundle_files_mixed": not forbidden,
        "external_datasets_not_uploaded": True,
        "external_datasets_note": "The three audited external datasets stay local-only and were not uploaded; this "
                                  "bundle carries only the Git-safe audit report, manifest, assessment/history tables, "
                                  "error log and handoff.",
        "self_referential_files": sorted(SELF_REFERENTIAL),
        "note": "CLOUD_HANDOFF_VERIFICATION.json is written last and cannot carry its own final digest; that digest "
                "is recorded in HANDOFF.md and the GitHub issue pointer.",
    }
    target = out / "CLOUD_HANDOFF_VERIFICATION.json"
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({
        "state": "CLOUD_VERIFICATION_WRITTEN",
        "cloud_file_count": record["cloud_file_count"],
        "frozen_artifacts_all_match": record["frozen_artifacts_all_match"],
        "no_prior_bundle_files_mixed": record["no_prior_bundle_files_mixed"],
        "verification_sha256": sha256(target),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
