from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
PIPELINE_VERSION = "focuswave_canonical_v1"
REGISTRY_PATH = REPO / "configs/canonical/local_analysis_registry_v1.json"
PIPELINE_PATH = REPO / "configs/canonical/competition_pipeline_v1.json"
LAUNCHER = REPO / "scripts/canonical/run_local_analysis.py"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(path)
    return data


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def add_dependencies(stage: str, cfg: dict[str, Any], out: list[str], seen: set[str]) -> None:
    if stage in seen:
        return
    for dep in cfg["stages"][stage].get("depends_on", []):
        add_dependencies(dep, cfg, out, seen)
    seen.add(stage)
    out.append(stage)


def selected_stages(args, cfg: dict[str, Any]) -> list[str]:
    requested = [args.stage] if args.stage else list(cfg["profiles"][args.profile])
    ordered: list[str] = []
    seen: set[str] = set()
    for stage in requested:
        add_dependencies(stage, cfg, ordered, seen)
    return ordered


def stage_dir(final_root: Path, machine_id: str, analysis_id: str) -> Path:
    return final_root / PIPELINE_VERSION / machine_id / analysis_id


def build_stage_config(base: dict[str, Any], analysis_id: str, stage_output: Path,
                       final_root: Path, machine_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    resolved = json.loads(json.dumps(base))
    resolved.setdefault("analysis_output_overrides", {})
    resolved.setdefault("analysis_input_overrides", {})
    resolved["analysis_output_overrides"][analysis_id] = str(stage_output)
    stage_cfg = cfg["stages"][analysis_id]
    for role, source in stage_cfg.get("dependency_inputs", {}).items():
        dep, rel = source
        dep_output = stage_dir(final_root, machine_id, dep) / "producer_output"
        candidate = dep_output if rel == "." else dep_output / rel
        if candidate.exists():
            resolved["analysis_input_overrides"].setdefault(analysis_id, {})[role] = str(candidate)
    return resolved


def copy_artifacts(producer_output: Path, target_root: Path,
                   rels: list[str]) -> list[dict[str, Any]]:
    records = []
    for rel in rels:
        src = producer_output / rel
        if not src.is_file():
            continue
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows = None
        if src.suffix.lower() == ".csv":
            try:
                import pandas as pd
                rows = int(len(pd.read_csv(src)))
            except Exception:
                rows = None
        records.append({
            "relative_path": rel,
            "sha256": sha256(dst),
            "size_bytes": dst.stat().st_size,
            "rows": rows,
        })
    return records


def write_stage_manifest(stage_root: Path, analysis_id: str, machine_id: str,
                         site: str, registry: dict[str, Any],
                         aggregate: list[dict[str, Any]],
                         merge_ready: list[dict[str, Any]]) -> None:
    spec = registry["analyses"][analysis_id]
    manifest = {
        "schema_version": "focuswave-stage-package-v1",
        "pipeline_version": PIPELINE_VERSION,
        "analysis_id": analysis_id,
        "machine_id": machine_id,
        "site": site,
        "status": "complete",
        "science_change": False,
        "producer": spec["producer"],
        "source_ref": spec["source_ref"],
        "role": spec["role"],
        "frozen": spec["frozen"],
        "result_unit": spec.get("result_unit"),
        "merge_key": spec.get("merge_key", []),
        "aggregate_artifacts": aggregate,
        "merge_ready_artifacts": merge_ready,
        "merge_ready_policy": "secure_transfer_only_not_git" if merge_ready else "aggregate_only",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (stage_root / "stage_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_stage(analysis_id: str, base_config: dict[str, Any], final_root: Path,
              machine_id: str, site: str, registry: dict[str, Any],
              cfg: dict[str, Any], dry_run: bool, force: bool) -> None:
    root = stage_dir(final_root, machine_id, analysis_id)
    producer_output = root / "producer_output"
    manifest = root / "stage_manifest.json"
    if manifest.exists() and not force and not dry_run:
        print(f"SKIP\t{analysis_id}\t{manifest}")
        return

    root.mkdir(parents=True, exist_ok=True)
    resolved = build_stage_config(base_config, analysis_id, producer_output,
                                  final_root, machine_id, cfg)
    resolved_path = root / "resolved_paths.local.json"
    resolved_path.write_text(json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [sys.executable, str(LAUNCHER), analysis_id, "--paths", str(resolved_path)]
    if dry_run:
        cmd.append("--dry-run")
    if force:
        cmd.append("--force")
    print("RUN\t" + "\t".join(cmd))
    subprocess.run(cmd, cwd=REPO, check=True)
    if dry_run:
        return

    spec = registry["analyses"][analysis_id]
    aggregate = copy_artifacts(producer_output, root / "aggregate",
                               spec.get("aggregate_outputs", []))
    merge_ready = copy_artifacts(producer_output, root / "merge_ready",
                                 spec.get("merge_ready_outputs", []))
    write_stage_manifest(root, analysis_id, machine_id, site,
                         registry, aggregate, merge_ready)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the standardized FocusWave competition pipeline.")
    ap.add_argument("--paths", type=Path, required=True)
    ap.add_argument("--profile", default="competition_core")
    ap.add_argument("--stage")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--machine-id")
    ap.add_argument("--site")
    args = ap.parse_args()

    cfg = load_json(PIPELINE_PATH)
    registry = load_json(REGISTRY_PATH)
    if args.list:
        print(json.dumps({"profiles": cfg["profiles"], "stages": cfg["stages"]},
                         ensure_ascii=False, indent=2))
        return
    if args.profile not in cfg["profiles"] and not args.stage:
        ap.error(f"unknown profile: {args.profile}")
    if args.stage and args.stage not in cfg["stages"]:
        ap.error(f"unknown stage: {args.stage}")

    base = load_json(args.paths)
    paths = base.get("paths", {})
    final_value = paths.get("final_output_root")
    if not final_value:
        raise KeyError("paths.final_output_root is required")
    final_root = Path(final_value).expanduser().resolve()
    machine = base.get("machine", {})
    machine_id = args.machine_id or machine.get("machine_id")
    site = args.site or machine.get("site")
    if not machine_id or not site:
        raise KeyError("machine.machine_id and machine.site are required")

    stages = selected_stages(args, cfg)
    print(json.dumps({
        "pipeline_version": PIPELINE_VERSION,
        "machine_id": machine_id,
        "site": site,
        "stages": stages,
        "final_root": str(final_root),
        "dry_run": args.dry_run,
    }, ensure_ascii=False, indent=2))

    for analysis_id in stages:
        run_stage(analysis_id, base, final_root, machine_id, site,
                  registry, cfg, args.dry_run, args.force)

    if not args.dry_run:
        machine_root = final_root / PIPELINE_VERSION / machine_id
        machine_root.mkdir(parents=True, exist_ok=True)
        (machine_root / "machine_package_manifest.json").write_text(
            json.dumps({
                "schema_version": "focuswave-machine-package-v1",
                "pipeline_version": PIPELINE_VERSION,
                "machine_id": machine_id,
                "site": site,
                "profile": args.profile if not args.stage else None,
                "requested_stage": args.stage,
                "stages": stages,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "teammate_transfer_rule": "transfer this machine directory outside Git; merge_ready may contain pseudonymous row-level derived data",
            }, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
