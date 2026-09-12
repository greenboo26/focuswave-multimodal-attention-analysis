"""Finalize the cloud handoff records after the verified upload.

Purpose: the upload run froze the result artifacts and produced
`CLOUD_HANDOFF_VERIFICATION.json`. Two coordination files (HANDOFF.md and the
manifest) changed afterwards to point at that verification report, so this script
re-uploads exactly those two, re-verifies all 13 cloud files by read-back and
recomputes hashes, and then re-runs the verification report so its per-file
records reflect the final cloud state.

Consistency rule: the frozen result artifacts are never edited here; only the two
coordination files and the regenerated verification report change.
"""

import hashlib
import json
import pathlib
import subprocess
import sys
import time

RCLONE = r"D:\Project\.tools\rclone.exe"
FOLDER_ID = "1gZC80XNklehALcuJ6U8NJe_aKy5iwzPd"
REPO = pathlib.Path(r"D:\Project\厚粲杯\08_算法_worktrees\mmwave_estimator_improvement_v1_20260912")
RESULT_DIR = REPO / "docs" / "results" / "2026-09-12_MMWAVE_ESTIMATOR_IMPROVEMENT_V1"
MANIFEST = RESULT_DIR / "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json"
VERIFY_REPORT = RESULT_DIR / "CLOUD_HANDOFF_VERIFICATION.json"
DOWNLOAD_DIR = pathlib.Path(r"D:\Project\.tools\rclone-readback")
MANIFEST_NAME = MANIFEST.name

# Files whose recorded hash is the authority and which must not change now.
FROZEN_EXCLUDE = {MANIFEST_NAME, "CLOUD_HANDOFF_VERIFICATION.json"}
# Files that legitimately change while the handoff records are finalized; they are
# re-uploaded here and compared against the current local text, not a frozen hash.
COORDINATION = ["HANDOFF.md", MANIFEST_NAME]


def sha256_of(path: pathlib.Path) -> str:
    """Return the uppercase SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rclone(*args: str) -> subprocess.CompletedProcess:
    """Run rclone against the task folder and return the completed process."""
    return subprocess.run(
        [RCLONE, *args, "--drive-root-folder-id", FOLDER_ID],
        capture_output=True,
        text=True,
        timeout=900,
    )


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    upload_files = manifest["cloud_handoff"]["upload_files"]

    # 1) Re-upload coordination files so the cloud matches the final local text.
    for name in COORDINATION:
        source = RESULT_DIR / name
        proc = rclone("copyto", str(source), f"gdrive:{name}")
        print(f"re-upload {name}: exit={proc.returncode} hash={sha256_of(source)}")

    # 2) Read back every cloud file and compute the authoritative hash table.
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    listing = rclone("lsjson", "gdrive:")
    remote_names = sorted(entry["Name"] for entry in json.loads(listing.stdout or "[]"))
    print("cloud file count:", len(remote_names))

    per_file = []
    for name in remote_names:
        if name == VERIFY_REPORT.name:
            # A file cannot verify itself: this report is regenerated and uploaded
            # after the loop, and its digest is recorded in HANDOFF.md and the
            # GitHub issue pointer.
            continue
        target = DOWNLOAD_DIR / name
        proc = rclone("copyto", f"gdrive:{name}", str(target))
        if proc.returncode != 0 or not target.exists():
            per_file.append({"name": name, "status": "READBACK_FAILED"})
            continue
        digest = sha256_of(target)
        recorded = next((item["sha256"] for item in upload_files if item["name"] == name), None)
        if name in COORDINATION:
            # Coordination files change during finalization; compare against the
            # current local text instead of the frozen manifest hash.
            local = sha256_of(RESULT_DIR / name)
            status = "MATCH_LOCAL" if digest == local else "MISMATCH"
            per_file.append({"name": name, "status": status, "local_sha256": local, "cloud_sha256": digest})
            print(f"readback {name}: {status}")
            continue
        match = recorded is not None and recorded == digest
        per_file.append(
            {
                "name": name,
                "status": "MATCH" if match else ("NO_RECORDED_HASH" if recorded is None else "MISMATCH"),
                "recorded_sha256": recorded,
                "cloud_sha256": digest,
            }
        )
        print(f"readback {name}: {per_file[-1]['status']}")

    snapshot_names = [name for name in remote_names if "INTEGRATION_SNAPSHOT_V1" in name]
    frozen_bad = [
        row
        for row in per_file
        if row["name"] not in FROZEN_EXCLUDE
        and row["name"] not in COORDINATION
        and row["status"] != "MATCH"
    ]
    verification = {
        "task_id": "mmwave_estimator_improvement_v1",
        "folder_name": manifest["cloud_handoff"]["destination_folder_name"],
        "folder_id": FOLDER_ID,
        "folder_url": manifest["cloud_handoff"]["destination_folder_url"],
        # No wall-clock field on purpose: the report must be byte-stable so that a
        # re-run reproduces the same digest.
        "transport": manifest["cloud_handoff"].get("transport", ""),
        "cloud_file_count": len(remote_names),
        "cloud_files": remote_names,
        "frozen_artifacts_all_match": not frozen_bad,
        "frozen_artifacts_checked": len([row for row in per_file if row["name"] not in FROZEN_EXCLUDE]),
        "snapshot_v1_files_present": snapshot_names,
        "no_snapshot_v1_files_mixed": not snapshot_names,
        "per_file": per_file,
        "note": "the manifest and this verification report are the only files allowed to change during verification; their own digests are recorded in HANDOFF.md and the GitHub issue pointer",
    }
    VERIFY_REPORT.write_text(json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 3) Upload the regenerated verification report as the final cloud file.
    proc = rclone("copyto", str(VERIFY_REPORT), f"gdrive:{VERIFY_REPORT.name}")
    print(f"upload {VERIFY_REPORT.name}: exit={proc.returncode}")
    print("verification report sha256:", sha256_of(VERIFY_REPORT))

    final_listing = rclone("lsjson", "gdrive:")
    print("final cloud file count:", len(json.loads(final_listing.stdout or "[]")))
    print("handoff sha256:", sha256_of(RESULT_DIR / "HANDOFF.md"))
    print("manifest sha256:", sha256_of(MANIFEST))
    return 0 if not frozen_bad else 2


if __name__ == "__main__":
    sys.exit(main())
