#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the mmWave external validation asset audit v1.

File: test_mmwave_external_validation_asset_audit.py
Version: 1.0.0
Purpose:
    锁定外部资产审计的结论与边界：
      - 三个外部数据集都被评估，且分类明确（没有 C1 可用资产）；
      - VS_DATASET 的 C1 不可用与 C2 可用、以及它的 C1b 暴露历史都被记录；
      - AgeBalanced 与 TI gby 的被排除理由被记录；
      - 路由为 OPT_A 作 primary + VS_DATASET 作 secondary；
      - 本任务不得运行候选、不得修改 producer / snapshot v1 / 外部数据；
      - preregistration 的验证集计划必须已同步外部路由结论。

Usage:
    python -m pytest tests/test_mmwave_external_validation_asset_audit.py -q

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

AUDIT_DIR = REPO / "docs" / "results" / "2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1"
REPORT = AUDIT_DIR / "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_REPORT.md"
MANIFEST = AUDIT_DIR / "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_MANIFEST.json"
ASSESSMENT = AUDIT_DIR / "EXTERNAL_ASSET_ASSESSMENT.csv"
HISTORY = AUDIT_DIR / "EXTERNAL_ASSET_HISTORY_TRACE.csv"
ERROR_LOG = AUDIT_DIR / "ERROR_LOG.json"
HANDOFF = AUDIT_DIR / "HANDOFF.md"
SCRIPT = REPO / "scripts" / "maintenance" / "run_mmwave_external_validation_asset_audit_20260913.py"

VS_PLAN = REPO / "docs" / "canonical" / "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md"
PRODUCER = REPO / "scripts" / "process_vital_signs_v3_1_1.py"
SNAPSHOT_V1 = REPO / "docs" / "results" / "2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1"

EXPECTED_DATASETS = {"VS_DATASET_healthy_v1", "AgeBalanced_60GHz", "mmWave_Heartbeat_TI_gby"}

FORBIDDEN_VERDICT_TOKENS = ("VALIDATED", "FORMAL_HR_READY", "SNAPSHOT_V2_READY", "PASS_VALIDATION")


def load_manifest() -> dict:
    """Load the audit manifest."""
    if not MANIFEST.exists():
        pytest.skip(f"audit manifest not present: {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict]:
    """Read a CSV produced by the audit."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_deliverables_exist():
    """All declared audit deliverables must exist and be non-empty."""
    for path in (REPORT, MANIFEST, ASSESSMENT, HISTORY, ERROR_LOG, HANDOFF, SCRIPT):
        assert path.exists(), f"missing deliverable: {path.name}"
        assert path.stat().st_size > 0, f"empty deliverable: {path.name}"
    assert REPORT.stat().st_size > 4000, "audit report is too thin"


def test_all_three_datasets_assessed():
    """Every external asset must appear in the manifest and the summary table."""
    manifest = load_manifest()
    assessed = {record["dataset_id"] for record in manifest["assessments"]}
    assert assessed == EXPECTED_DATASETS
    rows = read_csv_rows(ASSESSMENT)
    assert {row["dataset_id"] for row in rows} == EXPECTED_DATASETS


def test_each_assessment_answers_the_four_required_questions():
    """Each dataset must carry ground-truth, resolution, contract and exposure fields."""
    manifest = load_manifest()
    for record in manifest["assessments"]:
        assert "hr_ecg_ground_truth" in record and "present" in record["hr_ecg_ground_truth"]
        assert "radar_input" in record and "kind" in record["radar_input"]
        assert "time_resolution" in record
        assert "thirty_second_contract" in record and "feasible" in record["thirty_second_contract"]
        assert "development_exposure" in record and "classification" in record["development_exposure"]
        assert "c1_eligibility" in record and "eligible" in record["c1_eligibility"]
        assert "c2_eligibility" in record and "eligible" in record["c2_eligibility"]
        assert record.get("verdict"), f"missing verdict for {record['dataset_id']}"


def test_no_external_asset_is_c1_eligible():
    """C1 must have zero external candidates."""
    manifest = load_manifest()
    c1 = [r["dataset_id"] for r in manifest["assessments"] if r["c1_eligibility"]["eligible"]]
    assert c1 == [], f"C1 unexpectedly has external candidates: {c1}"


def test_only_vs_dataset_is_c2_eligible_and_is_secondary():
    """VS_DATASET must be the sole C2 option and must be labelled secondary."""
    manifest = load_manifest()
    c2 = [r["dataset_id"] for r in manifest["assessments"] if r["c2_eligibility"]["eligible"]]
    assert c2 == ["VS_DATASET_healthy_v1"], f"unexpected C2 candidates: {c2}"
    vs = next(r for r in manifest["assessments"] if r["dataset_id"] == "VS_DATASET_healthy_v1")
    assert vs["verdict"] == "PARTIAL_CANDIDATE_SECONDARY"
    assert vs["radar_input"]["raw_datacube_available"] is False


def test_vs_dataset_exposure_history_is_recorded():
    """The existing C1b benchmark must be recorded as prior exposure."""
    manifest = load_manifest()
    vs = next(r for r in manifest["assessments"] if r["dataset_id"] == "VS_DATASET_healthy_v1")
    exposure = vs["development_exposure"]
    assert exposure["classification"] == "DEVELOPMENT_EXPOSED"
    assert "C1B_VS_DATASET_20260825_V1" in exposure["what_ran"]
    assert "BENCHMARK_COMPLETE" in exposure["what_ran"]
    assert "raw_hr_abs_error_bpm" in exposure["metrics_produced"]
    assert "C1 spectral-candidate" in exposure["not_exposed_to"] or "C1 spectral-candidate score" in exposure["not_exposed_to"]


def test_agebalanced_and_ti_gby_exclusions_are_recorded():
    """The two excluded datasets must carry explicit reasons."""
    manifest = load_manifest()
    age = next(r for r in manifest["assessments"] if r["dataset_id"] == "AgeBalanced_60GHz")
    assert age["development_exposure"]["classification"] == "DEVELOPMENT_EXPOSED"
    assert age["development_exposure"]["commit"] == "f4a8c74d89ec28e005c537cbd5280a15dcb584e1"
    assert age["verdict"] == "INELIGIBLE_FOR_PRIMARY_VALIDATION"

    ti = next(r for r in manifest["assessments"] if r["dataset_id"] == "mmWave_Heartbeat_TI_gby")
    assert ti["hr_ecg_ground_truth"]["present"] is False
    assert ti["thirty_second_contract"]["feasible"] is False
    assert ti["verdict"] == "INELIGIBLE"


def test_routing_decision():
    """Routing must keep OPT_A as primary and VS_DATASET as secondary only."""
    manifest = load_manifest()
    routing = manifest["routing"]
    assert routing["PREREGISTRATION"] == "DONE"
    assert routing["EXTERNAL_ASSET_INVENTORY"] == "COMPLETE"
    assert "PROCEED_AS_PRIMARY" in routing["OPT_A_BUILD"]
    assert routing["primary_untouched_validation_source"] == "OPT_A_FORMAL_COHORT"
    assert "VS_DATASET" in routing["secondary_external_evidence"]
    assert any("AgeBalanced" in item for item in routing["not_usable"])
    assert any("mmWave_Heartbeat" in item for item in routing["not_usable"])


def test_boundaries_all_false_and_hrv_blocked():
    """The audit must not have touched anything it is forbidden to touch."""
    manifest = load_manifest()
    boundaries = manifest["boundaries"]
    for flag in (
        "snapshot_v1_modified",
        "formal_producer_modified",
        "v2_formed",
        "models_trained",
        "candidate_implemented",
        "external_data_modified",
    ):
        assert boundaries[flag] is False, f"boundary violated: {flag}"
    assert boundaries["hrv_status"] == "BLOCKED"
    assert boundaries["hr_br_status"] == "HOLD / SUPPORTING_ONLY"
    assert manifest["audit_only"] is True
    assert manifest["data_run_performed"] is False
    assert manifest["candidate_run_performed"] is False


def test_no_forbidden_verdict_tokens():
    """The audit must not claim any validation or readiness status."""
    for path in (REPORT, HANDOFF, MANIFEST):
        blob = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_VERDICT_TOKENS:
            assert token not in blob, f"{path.name} contains forbidden token: {token}"


def test_history_trace_records_real_references():
    """The history trace must contain real git hits, not a placeholder."""
    manifest = load_manifest()
    assert manifest["history_trace_summary"]["total_hits"] > 0
    rows = read_csv_rows(HISTORY)
    assert len(rows) > 0
    assert not (len(rows) == 1 and rows[0]["term"] == "NONE")
    files = {row["file"] for row in rows}
    assert any("ANALYSIS_HISTORY_LEDGER" in f for f in files), "history trace misses the ledger"
    terms = {row["term"] for row in rows}
    assert "AgeBalanced" in terms


def test_validation_set_plan_reflects_external_routing():
    """The preregistration validation-set plan must carry the external audit result."""
    if not VS_PLAN.exists():
        pytest.skip("validation-set plan not present")
    text = VS_PLAN.read_text(encoding="utf-8")
    assert "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1" in text
    assert "VS_DATASET" in text
    assert "secondary" in text.lower()


def test_producer_and_snapshot_untouched():
    """The formal producer and snapshot v1 must be unchanged by this task."""
    if PRODUCER.exists():
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--", "scripts/process_vital_signs_v3_1_1.py"],
            cwd=str(REPO), capture_output=True, text=True, check=False,
        )
        if out.returncode == 0:
            assert out.stdout.strip() == "", f"formal producer modified: {out.stdout}"
    if SNAPSHOT_V1.exists():
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--",
             "docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/"],
            cwd=str(REPO), capture_output=True, text=True, check=False,
        )
        if out.returncode == 0:
            assert out.stdout.strip() == "", f"snapshot v1 modified: {out.stdout}"
