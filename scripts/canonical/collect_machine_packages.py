from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PIPELINE_VERSION = "focuswave_canonical_v1"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(path)
    return data


def find_stage_manifests(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob(f"{PIPELINE_VERSION}/*/*/stage_manifest.json"))


def collect_package(root: Path) -> list[dict[str, Any]]:
    rows = []
    for manifest_path in find_stage_manifests(root):
        manifest = load_json(manifest_path)
        stage_root = manifest_path.parent
        for artifact in manifest.get("merge_ready_artifacts", []):
            rel = artifact["relative_path"]
            path = stage_root / "merge_ready" / rel
            if path.is_file():
                rows.append({
                    "analysis_id": manifest["analysis_id"],
                    "machine_id": manifest["machine_id"],
                    "site": manifest["site"],
                    "merge_key": manifest.get("merge_key", []),
                    "scientific_signature": scientific_signature(manifest),
                    "relative_path": rel,
                    "path": path,
                })
    return rows


def scientific_signature(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the minimum semantic contract used for fail-closed merging."""
    return {
        "pipeline_version": manifest.get("pipeline_version"),
        "producer": manifest.get("producer"),
        "source_ref": manifest.get("source_ref"),
        "frozen": manifest.get("frozen", {}),
        "result_unit": manifest.get("result_unit"),
        "merge_key": manifest.get("merge_key", []),
    }


def merge_group(items: list[dict[str, Any]], output: Path) -> dict[str, Any]:
    frames = []
    columns = None
    signature = None
    for item in items:
        if signature is None:
            signature = item["scientific_signature"]
        elif item["scientific_signature"] != signature:
            raise RuntimeError(
                f"scientific signature mismatch for {item['analysis_id']} / {item['relative_path']} "
                f"from machine {item['machine_id']}: expected {signature}, got {item['scientific_signature']}"
            )
        frame = pd.read_csv(item["path"])
        if columns is None:
            columns = list(frame.columns)
        elif list(frame.columns) != columns:
            raise RuntimeError(
                f"schema mismatch for {item['analysis_id']} / {item['relative_path']} "
                f"from machine {item['machine_id']}"
            )
        frame.insert(0, "_source_site", item["site"])
        frame.insert(0, "_source_machine_id", item["machine_id"])
        frames.append(frame)

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output, index=False, encoding="utf-8-sig")
    return {
        "output": str(output),
        "rows": int(len(merged)),
        "machines": sorted({x["machine_id"] for x in items}),
        "sites": sorted({x["site"] for x in items}),
        "merge_key": items[0].get("merge_key", []) if items else [],
        "scientific_signature": signature or {},
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Collect local and teammate FocusWave machine packages into one schema-checked combined input root."
    )
    ap.add_argument("--paths", type=Path, required=True)
    ap.add_argument("--local-root", type=Path)
    ap.add_argument("--teammate-root", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    config = load_json(args.paths)
    paths = config.get("paths", {})
    local_root = (args.local_root or Path(paths["final_output_root"])).expanduser().resolve()
    teammate_root = (args.teammate_root or Path(paths["teammate_input_root"])).expanduser().resolve()
    output_root = (args.output or Path(paths["combined_input_root"])).expanduser().resolve()

    items = collect_package(local_root) + collect_package(teammate_root)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault((item["analysis_id"], item["relative_path"]), []).append(item)

    results = {}
    for (analysis_id, rel), group in sorted(grouped.items()):
        name = Path(rel).name
        out = output_root / "focuswave_combined_v1" / analysis_id / name
        results[f"{analysis_id}:{rel}"] = merge_group(group, out)

    manifest_path = output_root / "focuswave_combined_v1" / "combined_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "focuswave-combined-input-v1",
        "local_root": str(local_root),
        "teammate_root": str(teammate_root),
        "groups": results,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
