#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the mmWave untouched ECG validation set v1 (blocked package).

File: test_mmwave_hr_untouched_ecg_validation_set.py
Version: 1.0.0
Purpose:
    锁定本轮前提核查的结论与边界：
      - 任务状态必须是 BLOCKED，且没有伪造验证集；
      - 阻断项必须是 VS_4/VS_5/VS_6/VS_7；
      - 全机 ECG 覆盖事实（仅 11 个 .acq，全在 D:\acq_mmwave_data）必须被记录；
      - 必须显式记录"前两轮 OPT_A 建议是错的"并说明根因；
      - 不得改 producer / snapshot v1 / 原始数据，不得实现候选；
      - HRV 保持 BLOCKED，HR/BR 保持 HOLD。

Usage:
    python -m pytest tests/test_mmwave_hr_untouched_ecg_validation_set.py -q

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DIR = REPO / "docs" / "results" / "2026-09-13_MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1"

REPORT = DIR / "MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1_REPORT.md"
MANIFEST = DIR / "MMWAVE_HR_UNTOUCHED_ECG_VALIDATION_SET_V1_MANIFEST.json"
SCAN = DIR / "ECG_SOURCE_FEASIBILITY_SCAN.csv"
PRECONDITIONS = DIR / "VALIDATION_SET_CONTRACT_PRECONDITIONS.csv"
ERROR_LOG = DIR / "ERROR_LOG.json"
HANDOFF = DIR / "HANDOFF.md"
SCRIPT = REPO / "scripts" / "maintenance" / "run_mmwave_untouched_ecg_validation_feasibility_20260913.py"

PRODUCER = REPO / "scripts" / "process_vital_signs_v3_1_1.py"
SNAPSHOT_V1 = REPO / "docs" / "results" / "2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1"

EXPECTED_BLOCKING = {"VS_4_INDEPENDENT_ECG_REFERENCE", "VS_5_WINDOW_CONTRACT",
                     "VS_6_ECG_ELIGIBILITY", "VS_7_DENOMINATOR_FROZEN"}


def load_manifest() -> dict:
    """Load the feasibility manifest."""
    if not MANIFEST.exists():
        pytest.skip(f"manifest not present: {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list:
    """Read a CSV from the package."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_deliverables_exist():
    """All package deliverables must exist and be non-empty."""
    for path in (REPORT, MANIFEST, SCAN, PRECONDITIONS, ERROR_LOG, HANDOFF, SCRIPT):
        assert path.exists(), f"missing deliverable: {path.name}"
        assert path.stat().st_size > 0, f"empty deliverable: {path.name}"
    assert REPORT.stat().st_size > 4000


def test_state_is_blocked_and_no_validation_set_was_built():
    """The task must report BLOCKED and must not have fabricated a validation set."""
    manifest = load_manifest()
    assert manifest["state"] == "BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE"
    assert manifest["validation_set_built"] is False
    assert manifest["candidate_run_performed"] is False
    assert manifest["c1_c2_run_permitted"] is False


def test_blocking_contract_items_are_the_scientific_ones():
    """Exactly VS_4/VS_5/VS_6/VS_7 must block, and the procedural items must pass."""
    manifest = load_manifest()
    assert set(manifest["blocking_contract_items"]) == EXPECTED_BLOCKING
    assert manifest["contract_preconditions_met"] == 6
    assert manifest["contract_preconditions_total"] == 10

    rows = {r["contract_item"]: r for r in read_rows(PRECONDITIONS)}
    assert set(rows) >= EXPECTED_BLOCKING | {"VS_1_SESSION_DISJOINT", "VS_8_NO_REUSE"}
    for item in EXPECTED_BLOCKING:
        assert rows[item]["precondition_met"].strip().lower() == "false", f"{item} should be blocking"
    for item in ("VS_1_SESSION_DISJOINT", "VS_2_PARTICIPANT_DISJOINT", "VS_3_UNTOUCHED",
                 "VS_8_NO_REUSE", "VS_9_NO_DEVELOPMENT_LEAKAGE", "VS_10_NO_SNAPSHOT_V2"):
        assert rows[item]["precondition_met"].strip().lower() == "true", f"{item} should be satisfiable"


def test_ecg_coverage_facts_are_recorded():
    """The authoritative ECG coverage inventory must be in the manifest."""
    manifest = load_manifest()
    coverage = manifest["ecg_coverage_authoritative"]
    assert coverage["total_ecg_bearing_sessions"] == 11
    roots = coverage["roots"]
    assert roots["D:\\acq_mmwave_data"]["acq"] == 11
    assert any(v["acq"] == 0 for k, v in roots.items() if "preexperiment" in k.lower())
    assert any(v["acq"] == 0 for k, v in roots.items() if k.startswith("J:"))
    classes = coverage["session_classes"]
    assert len(classes["calibration_sessions_no_probe_windows"]) == 5
    assert len(classes["already_consumed_development_sessions"]) == 5
    assert classes["not_estimable_no_probe_events"] == ["sub-97792_"]


def test_scan_table_covers_all_four_roots():
    """The scan table must cover every physiology-capable root."""
    rows = read_rows(SCAN)
    labels = {r["source_label"] for r in rows}
    assert {"formal_data_root_J", "preexperiment_root_I", "calibration_root_D"} <= labels


def test_previous_recommendation_retraction_is_recorded():
    """The earlier OPT_A recommendation must be explicitly retracted with its root cause."""
    manifest = load_manifest()
    retraction = manifest["previous_opt_a_recommendation_was_wrong"]
    assert "engineering" in retraction["why_wrong"] or "missing input" in retraction["why_wrong"]
    assert retraction["corrected_by"]

    blob = REPORT.read_text(encoding="utf-8")
    assert "我在此之前给出的 OPT_A 建议是错的" in blob
    assert "没有核对" in blob or "从未核对" in blob


def test_remediation_options_are_recorded_and_calibration_is_not_recommended():
    """All four options must be present, with REM_3 explicitly not recommended."""
    manifest = load_manifest()
    options = {o["id"]: o for o in manifest["remediation_options"]}
    assert set(options) == {"REM_1_LOCATE_FORMAL_ECG", "REM_2_NEW_ACQUISITION",
                            "REM_3_CALIBRATION_WINDOW_CONTRACT", "REM_4_ACCEPT_ABSENCE"}
    assert "NOT RECOMMENDED" in options["REM_3_CALIBRATION_WINDOW_CONTRACT"]["note"]
    assert "REM_1" in manifest["next_dependency"]


def test_vs_dataset_role_is_secondary_only():
    """The frozen VS_DATASET decision must be preserved verbatim in substance."""
    role = load_manifest()["vs_dataset_role"]
    assert role["role"] == "SECONDARY_EXTERNAL_CORROBORATION_ONLY"
    assert role["untouched"] is False
    assert role["primary_gate_eligible"] is False
    assert role["c1_evidence"] == "NOT_PERMITTED"
    assert role["c2_evidence"] == "PERMITTED_SECONDARY_ONLY"
    assert role["can_authorize_v2"] is False


def test_boundaries_untouched():
    """The task must not have modified protected assets."""
    boundaries = load_manifest()["boundaries"]
    for flag in ("snapshot_v1_modified", "formal_producer_modified", "v2_formed",
                 "models_trained", "candidate_implemented", "source_data_modified"):
        assert boundaries[flag] is False, f"boundary violated: {flag}"
    assert boundaries["hrv_status"] == "BLOCKED"
    assert boundaries["hr_br_status"] == "HOLD / SUPPORTING_ONLY"

    for path in ("scripts/process_vital_signs_v3_1_1.py", "docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/"):
        target = REPO / path
        if not target.exists():
            continue
        out = subprocess.run(["git", "diff", "--name-only", "origin/main", "--", path],
                             cwd=str(REPO), capture_output=True, text=True, check=False)
        if out.returncode == 0:
            assert out.stdout.strip() == "", f"protected path modified: {path}"


def test_error_log_records_the_blocker_and_the_retraction():
    """The error log must carry the blocker and the retraction warning."""
    log = json.loads(ERROR_LOG.read_text(encoding="utf-8"))
    assert log["state"] == "BLOCKED_ECG_REFERENCE_SOURCE_UNAVAILABLE"
    ids = {e["id"] for e in log["errors"]} | {w["id"] for w in log["warnings"]}
    assert "BLOCKER_ECG_REFERENCE_SOURCE_UNAVAILABLE" in ids
    assert "PRIOR_OPT_A_RECOMMENDATION_RETRACTED" in ids