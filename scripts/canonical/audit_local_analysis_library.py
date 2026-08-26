"""Read-only local analysis-library inventory and reproducibility preflight.

This command does not read file contents beyond lightweight manifest/schema probes,
does not copy raw data, and does not run scientific analysis. It is intentionally
parameterized so another machine can audit its own mounted roots.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def csv_header(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return ",".join(next(csv.reader(handle), []))
    except (OSError, UnicodeError, StopIteration):
        return "unreadable"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--derived-root", type=Path, required=True)
    parser.add_argument("--formal-nir-root", type=Path)
    parser.add_argument("--rgb-root", type=Path)
    parser.add_argument("--j-data-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    roots = {"repo": args.repo, "derived": args.derived_root}
    for name, value in (("formal_nir", args.formal_nir_root), ("rgb", args.rgb_root), ("j_data", args.j_data_root)):
        if value:
            roots[name] = value
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for root_name, root in roots.items():
        if not root.exists():
            rows.append({"root": root_name, "path": str(root), "exists": False, "files": 0, "bytes": 0})
            continue
        files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
        rows.append({
            "root": root_name,
            "path": str(root),
            "exists": True,
            "files": len(files),
            "bytes": sum(p.stat().st_size for p in files),
        })

    probes = []
    for path in args.derived_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name in {"run_manifest.json", "provenance_manifest.json", "status.json"}:
            item = {"path": str(path), "size": path.stat().st_size, "sha256": sha256(path)}
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                item["status"] = data.get("status", data.get("run_status", ""))
                item["run_id"] = data.get("run_id", data.get("RUN_ID", ""))
            except (OSError, UnicodeError, json.JSONDecodeError):
                item["status"] = "unreadable_json"
            probes.append(item)
        elif path.suffix.lower() == ".csv" and path.stat().st_size < 20 * 1024 * 1024:
            probes.append({"path": str(path), "size": path.stat().st_size, "header": csv_header(path)})

    payload = {
        "audit_time_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": git(args.repo, "rev-parse", "HEAD"),
        "repo_branch": git(args.repo, "branch", "--show-current"),
        "repo_status": git(args.repo, "status", "--short"),
        "roots": rows,
        "lightweight_probes": probes,
        "raw_data_uploaded": False,
        "scientific_analysis_run": False,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "roots": rows, "probe_count": len(probes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
