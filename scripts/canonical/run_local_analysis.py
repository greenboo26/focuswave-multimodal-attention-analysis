#!/usr/bin/env python
"""Canonical launcher for FocusWave analyses already completed locally.

This launcher does not define new science. It binds frozen producer scripts to a
small machine-local path configuration, performs a read-only preflight, refuses
implicit overwrite, and writes a provenance manifest after a successful run.

Machine-specific paths belong in an untracked JSON file. Scientific constants
remain inside the frozen producer and its method card / archive provenance.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]

ANALYSES: dict[str, dict[str, Any]] = {
    "behavior_baseline_v2": {
        "producer": "pipelines/behavior/run_final_report_cohort_baseline_v2.py",
        "source_ref": "archive/20260826/final-report-cohort-baseline-v2",
        "mode": "cli",
        "required": ["raw_data_root", "derived_root"],
        "output": "final_report_cohort_baseline_v2",
    },
    "behavior_longitudinal_v1": {
        "producer": "pipelines/behavior/run_beijing_longitudinal_event_analysis_v1.py",
        "source_ref": "archive/20260826/c1-alignment-protocol-repair",
        "mode": "globals",
        "required": ["raw_data_root", "derived_root"],
        "output": "beijing_c2_identity_reuse_event_analysis_v2/formal_behavior_longitudinal_v1",
    },
    "behavior_preprobe_v1": {
        "producer": "pipelines/behavior/run_beijing_preprobe_state_comparison_v1.py",
        "source_ref": "archive/20260826/c1-alignment-protocol-repair",
        "mode": "globals",
        "required": ["derived_root"],
        "output": "beijing_c2_identity_reuse_event_analysis_v2/formal_behavior_longitudinal_v1",
        "shares_upstream_output": True,
    },
    "questionnaire_q1_v1": {
        "producer": "pipelines/questionnaire/run_q1_questionnaire_criterion_validity.py",
        "source_ref": "archive/20260826/q1-questionnaire-criterion-validity",
        "mode": "globals_cli",
        "required": ["derived_root"],
        "output": "questionnaire_criterion_validity_v1",
    },
    "mmwave_c1_alignment_v1": {
        "producer": "pipelines/mmwave/audit_c1_alignment_robustness.py",
        "source_ref": "archive/20260826/c1-alignment-protocol-repair",
        "mode": "globals",
        "required": ["derived_root"],
        "output": "c1_alignment_robustness_audit_v1",
    },
    "mmwave_m1_v1": {
        "producer": "pipelines/mmwave/build_evaluate_j_mmwave_m1_loso.py",
        "source_ref": "archive/20260826/m1-mmwave-person-effect-audit",
        "mode": "cli",
        "required": ["raw_data_root", "derived_root", "legacy_output_root"],
        "output": "j_m1_q0_71_rerun_v1",
    },
    "mmwave_c2b_v2": {
        "producer": "pipelines/mmwave/run_c2b_v2_canonical_reconstruction.py",
        "source_ref": "archive/20260826/c2b-v2-canonical",
        "mode": "globals_cli",
        "required": ["raw_data_root", "derived_root", "legacy_output_root"],
        "output": "c2b_v2_canonical_baselines_20260826",
    },
    "mmwave_c2c_v1": {
        "producer": "pipelines/mmwave/run_c2c_personalized_mmwave_calibration.py",
        "source_ref": "archive/20260826/c2c-within-subject-normalization",
        "mode": "globals_cli",
        "required": ["raw_data_root", "derived_root"],
        "output": "c2c_within_subject_normalization_v1",
    },
    "beijing_sensor_increment_v1": {
        "producer": "pipelines/mmwave/run_beijing_sensor_increment_v1.py",
        "source_ref": "archive/20260826/c1-alignment-protocol-repair",
        "mode": "globals",
        "required": ["derived_root"],
        "output": "beijing_sensor_increment_v1",
    },
}

PACKAGE_NAMES = [
    "numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "matplotlib",
    "vmdpy", "bioread",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    aliases = config.get("paths", config)
    if not isinstance(aliases, dict):
        raise ValueError("paths config must contain an object named 'paths'")
    return {str(k): Path(os.path.expandvars(os.path.expanduser(str(v)))).resolve() for k, v in aliases.items() if v}


def output_dir(analysis_id: str, spec: dict[str, Any], paths: dict[str, Path], config: dict[str, Any]) -> Path:
    overrides = config.get("analysis_output_overrides", {})
    if analysis_id in overrides:
        return Path(os.path.expandvars(os.path.expanduser(str(overrides[analysis_id])))).resolve()
    return paths["derived_root"] / spec["output"]


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in PACKAGE_NAMES:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = None
    return out


def import_module(path: Path):
    name = "focuswave_canonical_" + hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def argv(values: list[str]):
    old = sys.argv[:]
    sys.argv = values
    try:
        yield
    finally:
        sys.argv = old


def input_map(analysis_id: str, paths: dict[str, Path]) -> dict[str, Path]:
    d = paths.get("derived_root")
    raw = paths.get("raw_data_root")
    legacy = paths.get("legacy_output_root")
    maps: dict[str, dict[str, Path]] = {
        "behavior_baseline_v2": {
            "cohort": d / "report_cohort_label_vigilance_v1/report_analysis_cohort.csv",
            "raw_data_root": raw,
        },
        "behavior_longitudinal_v1": {
            "join": d / "beijing_c2_identity_reuse_event_analysis_v2/deterministic_join.csv",
            "raw_data_root": raw,
        },
        "behavior_preprobe_v1": {
            "probe_event_level": d / "beijing_c2_identity_reuse_event_analysis_v2/formal_behavior_longitudinal_v1/probe_event_level_behavior.csv",
        },
        "questionnaire_q1_v1": {
            "audit_dir": d / "questionnaire_measurement_audit_v1",
            "bridge": d / "questionnaire_non_nir_session_bridge_v1/questionnaire_non_nir_session_bridge.csv",
        },
        "mmwave_c1_alignment_v1": {
            "c1_root": d / "c1c_mmhrv_pilot_v1",
        },
        "mmwave_m1_v1": {
            "current": legacy / "J_Data_GROUP_SUMMARY/probe_summary.csv",
            "raw_data_root": raw,
            "legacy_output_root": legacy,
        },
        "mmwave_c2b_v2": {
            "c2a_root": legacy / "40_正式实验/04_C2a_标签与样本单元审计/derived_20260826",
            "old_matrix": d / "j_m1_q0_71_rerun_v1/m1_q0_probe_matrix.csv",
            "raw_data_root": raw,
            "legacy_output_root": legacy,
        },
        "mmwave_c2c_v1": {
            "c2b_root": d / "c2b_v2_canonical_baselines_20260826",
            "raw_data_root": raw,
        },
        "beijing_sensor_increment_v1": {
            "behavior": d / "beijing_c2_identity_reuse_event_analysis_v2/formal_behavior_longitudinal_v1/probe_event_level_behavior.csv",
            "nir": d / "current_j_nir_mmwave_analysis_input_v2/current_j_nir_mmwave_analysis_input.csv",
            "crosswalk": d / "c3_identity_coverage_crosswalk_v1/identity_crosswalk.csv",
            "mmwave": d / "non_nir_window_analysis_input_v1/non_nir_window_analysis_input.csv",
        },
    }
    return maps[analysis_id]


def preflight(analysis_id: str, spec: dict[str, Any], paths: dict[str, Path], config: dict[str, Any]) -> dict[str, Any]:
    missing_aliases = [k for k in spec["required"] if k not in paths]
    if missing_aliases:
        raise KeyError(f"missing path aliases: {', '.join(missing_aliases)}")
    producer = REPO / spec["producer"]
    if not producer.is_file():
        raise FileNotFoundError(producer)
    inputs = input_map(analysis_id, paths)
    checks = {}
    for role, p in inputs.items():
        exists = p.exists()
        checks[role] = {"path": str(p), "exists": exists, "kind": "dir" if p.is_dir() else "file" if p.is_file() else "missing"}
    out = output_dir(analysis_id, spec, paths, config)
    return {"analysis_id": analysis_id, "producer": str(producer.relative_to(REPO)), "source_ref": spec["source_ref"], "inputs": checks, "output": str(out)}


def ensure_output_safe(out: Path, force: bool, shares_upstream_output: bool = False) -> None:
    if not out.exists():
        return
    entries = list(out.iterdir()) if out.is_dir() else [out]
    if entries and not force:
        reason = "output package already contains upstream products" if shares_upstream_output else "output is not empty"
        raise FileExistsError(f"{reason}: {out}; choose analysis_output_overrides or pass --force explicitly")


def run_analysis(analysis_id: str, spec: dict[str, Any], paths: dict[str, Path], config: dict[str, Any], force: bool) -> Path:
    producer = REPO / spec["producer"]
    out = output_dir(analysis_id, spec, paths, config)
    ensure_output_safe(out, force, bool(spec.get("shares_upstream_output")))
    out.mkdir(parents=True, exist_ok=True)
    inp = input_map(analysis_id, paths)

    if analysis_id == "behavior_baseline_v2":
        cmd = [sys.executable, str(producer), "--cohort", str(inp["cohort"]), "--data-root", str(inp["raw_data_root"]), "--output", str(out)]
        subprocess.run(cmd, cwd=REPO, check=True)
    elif analysis_id == "behavior_longitudinal_v1":
        m = import_module(producer); m.JOIN = inp["join"]; m.DATA_ROOT = inp["raw_data_root"]; m.OUT = out; m.main()
    elif analysis_id == "behavior_preprobe_v1":
        m = import_module(producer); m.OUT = out; m.INPUT = inp["probe_event_level"]; m.main()
    elif analysis_id == "questionnaire_q1_v1":
        m = import_module(producer); m.AUDIT_DIR = inp["audit_dir"]; m.BRIDGE = inp["bridge"]; m.DEFAULT_OUT = out
        with argv([str(producer), "--out", str(out), "--bootstrap-draws", "5000"]): m.main()
    elif analysis_id == "mmwave_c1_alignment_v1":
        m = import_module(producer); m.C1 = inp["c1_root"]; m.OUT = out
        frozen = import_module(REPO / "pipelines/mmwave/frozen_c1_metrics.py")
        m.load_c1 = lambda: frozen
        m.main()
    elif analysis_id == "mmwave_m1_v1":
        cmd = [sys.executable, str(producer), "--current", str(inp["current"]), "--data-root", str(inp["raw_data_root"]), "--full-root", str(inp["legacy_output_root"]), "--output", str(out)]
        subprocess.run(cmd, cwd=REPO, check=True)
    elif analysis_id == "mmwave_c2b_v2":
        m = import_module(producer)
        m.DATA = inp["raw_data_root"]; m.C2A = inp["c2a_root"]; m.OUT = out; m.FULL_ROOT = inp["legacy_output_root"]
        m.OLD = REPO / "pipelines/mmwave/build_evaluate_j_mmwave_m1_loso.py"
        with argv([str(producer), "--windows", "10", "30", "60", "--data-root", str(inp["raw_data_root"]), "--output", str(out), "--old-matrix", str(inp["old_matrix"]), "--extract", "--evaluate"]): m.main()
    elif analysis_id == "mmwave_c2c_v1":
        m = import_module(producer); m.DATA = inp["raw_data_root"]; m.C2B = inp["c2b_root"]; m.OUT = out
        with argv([str(producer), "--output", str(out), "--bootstrap", "5000", "--windows", "10", "30", "60"]): m.main()
    elif analysis_id == "beijing_sensor_increment_v1":
        m = import_module(producer); m.DERIVED = paths["derived_root"]; m.BEHAVIOR = inp["behavior"]; m.NIR = inp["nir"]; m.CROSSWALK = inp["crosswalk"]; m.MMWAVE = inp["mmwave"]; m.OUT = out; m.main()
    else:
        raise KeyError(analysis_id)
    return out


def write_provenance(out: Path, analysis_id: str, spec: dict[str, Any], config_path: Path, paths: dict[str, Path]) -> None:
    producer = REPO / spec["producer"]
    inp = input_map(analysis_id, paths)
    input_evidence = {}
    for role, p in inp.items():
        rec: dict[str, Any] = {"exists": p.exists(), "kind": "dir" if p.is_dir() else "file" if p.is_file() else "missing"}
        if p.is_file():
            rec["sha256"] = sha256_file(p)
            rec["size_bytes"] = p.stat().st_size
        input_evidence[role] = rec
    manifest = {
        "schema_version": "focuswave-canonical-run-v1",
        "analysis_id": analysis_id,
        "science_change": False,
        "producer": str(producer.relative_to(REPO)),
        "producer_sha256": sha256_file(producer),
        "source_archive_ref": spec["source_ref"],
        "central_git_commit": git_head(),
        "path_config_sha256": sha256_file(config_path),
        "input_evidence": input_evidence,
        "python": sys.version,
        "platform": platform.platform(),
        "packages": package_versions(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out / "canonical_run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("analysis", nargs="?", choices=sorted(ANALYSES))
    ap.add_argument("--paths", type=Path, help="untracked local paths JSON")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="explicitly allow producer outputs to replace files in an existing output package")
    args = ap.parse_args()
    if args.list:
        for key in sorted(ANALYSES):
            print(f"{key}\t{ANALYSES[key]['producer']}\t{ANALYSES[key]['source_ref']}")
        return
    if not args.analysis or not args.paths:
        ap.error("analysis and --paths are required unless --list is used")
    config = load_json(args.paths)
    paths = resolve_paths(config)
    spec = ANALYSES[args.analysis]
    check = preflight(args.analysis, spec, paths, config)
    print(json.dumps(check, ensure_ascii=False, indent=2))
    missing = [name for name, rec in check["inputs"].items() if not rec["exists"]]
    if missing:
        raise FileNotFoundError("preflight failed; missing inputs: " + ", ".join(missing))
    if args.dry_run:
        return
    out = run_analysis(args.analysis, spec, paths, config, args.force)
    write_provenance(out, args.analysis, spec, args.paths.resolve(), paths)
    print(json.dumps({"status": "complete", "analysis_id": args.analysis, "output": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
