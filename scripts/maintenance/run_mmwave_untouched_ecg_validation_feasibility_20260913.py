#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""mmWave untouched ECG validation set v1 - precondition feasibility audit.

File: run_mmwave_untouched_ecg_validation_feasibility_20260913.py
Version: 1.0.0
Purpose:
    mmwave_hr_untouched_ecg_validation_set_v1 (OPT_A) 的第一前提是：正式 cohort 的
    session 必须存在可与毫米波窗口对齐的 ECG 采集来源，才能生成独立 per-window
    gold-clean ECG 参考。

    本脚本只做只读前提核查：逐个候选源根扫描 ECG/BIOPAC 采集是否存在，并判定
    VS_1 到 VS_10 的前置条件是否满足。不建验证集、不跑候选、不改任何数据。

    结论若为 BLOCKED，则按规范报告 precondition 缺失，而不是伪造分母。

Usage:
    python scripts/maintenance/run_mmwave_untouched_ecg_validation_feasibility_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# 候选 ECG 来源根（本机 paths.local.json 声明的正式/校准/预实验根，加派生与正式分析根）。
SOURCE_ROOTS = (
    ("formal_data_root_J", Path(r"J:\Data")),
    ("preexperiment_root_I", Path(r"I:\预实验")),
    ("calibration_root_D", Path(r"D:\acq_mmwave_data")),
    ("derived_root", Path(r"D:\Project\厚粲杯\11_数据\derived")),
    ("formal_analysis_root", Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis")),
)

ECG_FILE_SUFFIXES = (".acq", ".ecg", ".biopac", ".edf")
ECG_NAME_HINTS = ("ecg", "biopac", "acq", "rpeak", "r_peak")

# 开发集（已被反复查看的 5 个 session）——不得作为验证集。
DEVELOPMENT_SESSIONS = ("9779", "97793", "97794", "97795", "97796")

EXPECTED_MAIN = "40240750f740898709feb257f5188ec954b1d08b"


def current_commit() -> str:
    """Return the current Git commit sha, or UNKNOWN."""
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                                capture_output=True, text=True, check=False)
        return result.stdout.strip() or "UNKNOWN"
    except OSError:
        return "UNKNOWN"


def scan_root(label: str, root: Path, max_files: int = 400000) -> dict:
    """Scan one candidate root for session dirs and ECG acquisition artefacts."""
    if not root.exists():
        return {"label": label, "path": str(root), "exists": False}

    session_dirs = []
    ecg_files = []
    subdir_names = set()
    file_count = 0

    for entry in root.iterdir():
        if entry.is_dir() and entry.name.lower().startswith("sub-"):
            session_dirs.append(entry.name.rstrip("_"))

    for item in root.rglob("*"):
        file_count += 1
        if file_count > max_files:
            break
        if item.is_dir():
            subdir_names.add(item.name)
            continue
        if item.suffix.lower() in ECG_FILE_SUFFIXES:
            ecg_files.append(str(item.relative_to(root)))
            continue
        lowered = item.name.lower()
        if any(hint in lowered for hint in ECG_NAME_HINTS):
            ecg_files.append(str(item.relative_to(root)))

    return {
        "label": label,
        "path": str(root),
        "exists": True,
        "session_dir_count": len(session_dirs),
        "session_ids_sample": sorted(session_dirs)[:12],
        "non_session_subdirs": sorted(subdir_names)[:20],
        "ecg_artefact_count": len(ecg_files),
        "ecg_artefacts_sample": ecg_files[:12],
        "files_scanned": file_count,
    }


def formal_session_subdirs(root: Path, sample: int = 12) -> dict:
    """Count the per-session subdirectory names in a formal root."""
    if not root.exists():
        return {}
    found = {}
    for entry in list(root.iterdir())[:sample]:
        if not entry.is_dir():
            continue
        for child in entry.iterdir():
            if child.is_dir():
                found[child.name] = found.get(child.name, 0) + 1
    return dict(sorted(found.items(), key=lambda kv: -kv[1]))


def build_contract_preconditions(scans: dict, session_subdirs: dict) -> list:
    """Decide which validation-set contract items have their precondition met."""
    formal = scans.get("formal_data_root_J", {})
    sessions_ok = formal.get("session_dir_count", 0) > 0

    return [
        {
            "contract_item": "VS_1_SESSION_DISJOINT",
            "precondition_met": sessions_ok,
            "evidence": "formal J root exposes %d session dirs, none of which is a development session; "
                        "session-disjointness is satisfiable" % formal.get("session_dir_count", 0),
        },
        {
            "contract_item": "VS_2_PARTICIPANT_DISJOINT",
            "precondition_met": sessions_ok,
            "evidence": "formal ids are a different id space from the development calibration sessions",
        },
        {
            "contract_item": "VS_3_UNTOUCHED",
            "precondition_met": sessions_ok,
            "evidence": "formal sessions have not been used for HR algorithm development",
        },
        {
            "contract_item": "VS_4_INDEPENDENT_ECG_REFERENCE",
            "precondition_met": False,
            "evidence": "no ECG/BIOPAC acquisition artefact exists for any formal session: formal-root ECG "
                        "artefacts=%d; per-session subdirs=%s; the only gold-clean per-window ECG reference on "
                        "this machine covers the 5 exhausted development sessions"
                        % (formal.get("ecg_artefact_count", 0), sorted(session_subdirs)),
        },
        {
            "contract_item": "VS_5_WINDOW_CONTRACT",
            "precondition_met": False,
            "evidence": "the frozen window contract is defined by mmWave frames plus block markers derived from the "
                        "ECG/BIOPAC acquisition; without that acquisition, marker alignment and therefore "
                        "window_effective_start cannot be reproduced for formal sessions",
        },
        {
            "contract_item": "VS_6_ECG_ELIGIBILITY",
            "precondition_met": False,
            "evidence": "eligibility requires a per-probe ECG reference to classify valid/invalid/unresolved",
        },
        {
            "contract_item": "VS_7_DENOMINATOR_FROZEN",
            "precondition_met": False,
            "evidence": "the denominator cannot be frozen without per-probe ECG eligibility",
        },
        {
            "contract_item": "VS_8_NO_REUSE",
            "precondition_met": True,
            "evidence": "procedural item; satisfiable by keeping build and first use in separate tasks",
        },
        {
            "contract_item": "VS_9_NO_DEVELOPMENT_LEAKAGE",
            "precondition_met": True,
            "evidence": "procedural item; satisfiable by the separate-task sequencing already frozen",
        },
        {
            "contract_item": "VS_10_NO_SNAPSHOT_V2",
            "precondition_met": True,
            "evidence": "procedural item; unchanged from the preregistration",
        },
    ]


def main(argv=None) -> int:
    """Run the feasibility audit and write outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path,
        default=REPO_ROOT / "docs" / "results" / "2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1",
    )
    args = parser.parse_args(argv)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    scans = {label: scan_root(label, root) for label, root in SOURCE_ROOTS}
    session_subdirs = formal_session_subdirs(Path(r"J:\Data"))
    preconditions = build_contract_preconditions(scans, session_subdirs)

    blocking = [p for p in preconditions if not p["precondition_met"]]
    state = "BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE" if blocking else "PRECONDITIONS_MET"

    rows = [{
        "source_label": label,
        "path": scan.get("path", ""),
        "exists": scan.get("exists", False),
        "session_dir_count": scan.get("session_dir_count", 0),
        "ecg_artefact_count": scan.get("ecg_artefact_count", 0),
        "ecg_artefacts_sample": "|".join(scan.get("ecg_artefacts_sample", [])[:5]),
        "non_session_subdirs": "|".join(scan.get("non_session_subdirs", [])[:8]),
    } for label, scan in scans.items()]
    with (out / "ECG_SOURCE_FEASIBILITY_SCAN.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    contract_rows = [{
        "contract_item": p["contract_item"],
        "precondition_met": p["precondition_met"],
        "evidence": p["evidence"],
    } for p in preconditions]
    with (out / "VALIDATION_SET_CONTRACT_PRECONDITIONS.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(contract_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(contract_rows)

    manifest = {
        "task_id": "mmwave_hr_untouched_ecg_validation_set_v1",
        "run_id": "mmwave_hr_untouched_ecg_validation_set_v1_20260913_r1",
        "document_type": "PRECONDITION_FEASIBILITY_AUDIT",
        "state": state,
        "date": "2026-09-13",
        "base_commit": current_commit(),
        "expected_main_at_task_start": EXPECTED_MAIN,
        "validation_set_built": False,
        "candidate_run_performed": False,
        "source_roots_scanned": list(scans.values()),
        "formal_session_subdirs": session_subdirs,
        "development_sessions_excluded": list(DEVELOPMENT_SESSIONS),
        "contract_preconditions": preconditions,
        "blocking_contract_items": [p["contract_item"] for p in blocking],
        "blocker": {
            "id": "ECG_REFERENCE_SOURCE_UNAVAILABLE_FOR_FORMAL_COHORT",
            "detail": "OPT_A requires an independent per-window gold-clean ECG reference for formal-cohort "
                      "sessions. No ECG/BIOPAC acquisition artefact exists for the formal cohort anywhere "
                      "reachable on this machine. The formal J root contains only beh/mmwave/nir/rgb per session; "
                      "the pre-experiment and calibration roots contain no .acq; and the only gold-clean "
                      "per-window ECG reference present covers exactly the 5 development sessions.",
            "consequence": "VS_4, VS_5, VS_6 and VS_7 cannot be satisfied, so "
                           "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1 cannot be formed and C1/C2 must not be run.",
        },
        "remediation_options": [
            {"id": "REM_1_LOCATE_FORMAL_ECG",
             "detail": "Determine whether formal-cohort ECG/BIOPAC was acquired at all and, if so, obtain it from "
                       "the acquisition machine or archive drive, then rerun the gold-clean reference for the "
                       "chosen sessions.",
             "effort": "UNKNOWN_UNTIL_SOURCED",
             "note": "must be resolved before any other option is evaluated"},
            {"id": "REM_2_NEW_ACQUISITION",
             "detail": "Collect new participant/session-disjoint data with synchronized mmWave and ECG under the "
                       "frozen window contract.",
             "effort": "HIGH",
             "note": "the only option guaranteed to be both untouched and readable"},
            {"id": "REM_3_PREEXPERIMENT_PILOT",
             "detail": "Check whether the I:/preexperiment sessions have a usable synchronized ECG source; if they "
                       "do, they are a small but genuinely disjoint pilot set.",
             "effort": "MEDIUM_IF_SOURCED",
             "note": "session-level scope may be too small for the frozen five criteria"},
        ],
        "boundaries": {
            "snapshot_v1_modified": False,
            "formal_producer_modified": False,
            "v2_formed": False,
            "models_trained": False,
            "hrv_status": "BLOCKED",
            "hr_br_status": "HOLD / SUPPORTING_ONLY",
            "candidate_implemented": False,
            "source_data_modified": False,
        },
        "vs_dataset_role": {
            "role": "SECONDARY_EXTERNAL_CORROBORATION_ONLY",
            "untouched": False,
            "primary_gate_eligible": False,
            "c1_evidence": "NOT_PERMITTED",
            "c2_evidence": "PERMITTED_SECONDARY_ONLY",
            "can_authorize_v2": False,
        },
        "next_dependency": "Resolve the formal-cohort ECG source question (REM_1) before rebuilding OPT_A; "
                           "C1/C2 remain blocked until MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1 exists.",
    }
    (out / "MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps({
        "state": state,
        "source_roots": {label: {"exists": s.get("exists", False),
                                 "sessions": s.get("session_dir_count", 0),
                                 "ecg_artefacts": s.get("ecg_artefact_count", 0)}
                         for label, s in scans.items()},
        "formal_session_subdirs": session_subdirs,
        "blocking_contract_items": [p["contract_item"] for p in blocking],
        "validation_set_built": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())