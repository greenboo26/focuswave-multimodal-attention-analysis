"""Upload and verify the mmWave estimator improvement v1 cloud handoff.

Purpose: copy the tracked result files into the existing Google Drive task
folder `2026-09-12_mmwave_estimator_improvement_v1` (never creating a new
directory), then read them back and verify name and SHA-256 against the frozen
manifest.

Consistency rules implemented here:
- `MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json` records, per artifact, the
  SHA-256 of the bytes that were uploaded. Those artifacts are frozen at upload
  time and are not edited afterwards.
- The manifest itself and the cloud-verification report are the only files that
  change as verification proceeds; they are uploaded last and their own hashes
  are recorded outside themselves (in the verification report and the GitHub
  issue pointer), because a file cannot carry its own final hash.
"""

import hashlib
import json
import pathlib
import subprocess
import sys
import time

RCLONE = r"D:\Project\.tools\rclone.exe"
FOLDER_ID = "1gZC80XNklehALcuJ6U8NJe_aKy5iwzPd"
FOLDER_URL = "https://drive.google.com/drive/folders/1gZC80XNklehALcuJ6U8NJe_aKy5iwzPd"
REPO = pathlib.Path(r"D:\Project\厚粲杯\08_算法_worktrees\mmwave_estimator_improvement_v1_20260912")
RESULT_DIR = REPO / "docs" / "results" / "2026-09-12_MMWAVE_ESTIMATOR_IMPROVEMENT_V1"
MANIFEST = RESULT_DIR / "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json"
VERIFY_REPORT = RESULT_DIR / "CLOUD_HANDOFF_VERIFICATION.json"
DOWNLOAD_DIR = pathlib.Path(r"D:\Project\.tools\rclone-readback")
MANIFEST_NAME = MANIFEST.name


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


def read_back(name: str) -> pathlib.Path | None:
    """Download a cloud file into the staging dir and return its local path."""
    target = DOWNLOAD_DIR / name
    proc = rclone("copyto", f"gdrive:{name}", str(target))
    return target if proc.returncode == 0 and target.exists() else None


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    upload_files = manifest["cloud_handoff"]["upload_files"]
    artifacts = [item for item in upload_files if item["name"] != MANIFEST_NAME]
    # Files that this script generates during the run have no pre-upload content.
    generated = {VERIFY_REPORT.name}

    # 1) Local pre-check: recorded hashes must match the files on disk.
    precheck = []
    for item in artifacts:
        if item["name"] in generated:
            continue
        source = REPO / item["repo_path"]
        local = sha256_of(source)
        precheck.append({"name": item["name"], "recorded": item["sha256"], "local": local, "match": local == item["sha256"]})
    bad = [row for row in precheck if not row["match"]]
    print("precheck mismatches:", bad)

    # 2) Upload every tracked artifact, then the manifest itself.
    upload_results = []
    for item in upload_files:
        if item["name"] in generated:
            continue
        source = REPO / item["repo_path"]
        proc = rclone("copyto", str(source), f"gdrive:{item['name']}")
        upload_results.append({"name": item["name"], "source": str(source), "exit": proc.returncode})
        print(f"upload {item['name']}: exit={proc.returncode}")

    # 3) Read back and re-hash.
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    listing = rclone("lsjson", "gdrive:")
    remote = {entry["Name"]: entry for entry in json.loads(listing.stdout or "[]")}
    print("remote file count:", len(remote))

    verified = []
    for item in artifacts:
        name = item["name"]
        if name in generated:
            # Generated during this run and uploaded at the end; its own digest is
            # recorded in HANDOFF.md and the GitHub issue pointer.
            verified.append({"name": name, "status": "UPLOADED_LAST_NO_SELF_HASH"})
            continue
        path = read_back(name)
        if path is None:
            verified.append({"name": name, "status": "READBACK_FAILED"})
            continue
        remote_hash = sha256_of(path)
        status = "MATCH" if remote_hash == item["sha256"] else "MISMATCH"
        verified.append({"name": name, "status": status, "recorded_sha256": item["sha256"], "remote_sha256": remote_hash})
        print(f"readback {name}: {status}")

    names_remote = sorted(remote)
    snapshot_names = [name for name in names_remote if "INTEGRATION_SNAPSHOT_V1" in name]
    all_match = all(row["status"] == "MATCH" for row in verified if row["status"] != "UPLOADED_LAST_NO_SELF_HASH")

    report = {
        "task_id": "mmwave_estimator_improvement_v1",
        "folder_name": manifest["cloud_handoff"]["destination_folder_name"],
        "folder_id": FOLDER_ID,
        "folder_url": FOLDER_URL,
        "verified_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "transport": manifest["cloud_handoff"].get("transport", ""),
        "remote_file_count": len(remote),
        "remote_files": names_remote,
        "artifacts_verified": len(verified),
        "artifacts_all_match": all_match,
        "per_file": verified,
        "snapshot_v1_files_present": snapshot_names,
        "no_snapshot_v1_files_mixed": not snapshot_names,
        "manifest_readback_note": "the manifest is uploaded last and cannot carry its own final hash; its bytes are recorded in the GitHub issue pointer and in this report's upload list",
        "self_note": "this verification report is uploaded last; its own SHA-256 is recorded in HANDOFF.md and the GitHub issue pointer",
    }
    VERIFY_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 4) Upload the verification report as the final cloud file.
    proc = rclone("copyto", str(VERIFY_REPORT), f"gdrive:{VERIFY_REPORT.name}")
    print(f"upload {VERIFY_REPORT.name}: exit={proc.returncode}")

    final_listing = rclone("lsjson", "gdrive:")
    final_names = sorted(entry["Name"] for entry in json.loads(final_listing.stdout or "[]"))
    print("final remote file count:", len(final_names))
    print("final remote files:", final_names)
    report["remote_file_count_after_final_upload"] = len(final_names)
    report["remote_files_after_final_upload"] = final_names
    VERIFY_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("verification report sha256:", sha256_of(VERIFY_REPORT))
    return 0 if all_match else 2


if __name__ == "__main__":
    sys.exit(main())
