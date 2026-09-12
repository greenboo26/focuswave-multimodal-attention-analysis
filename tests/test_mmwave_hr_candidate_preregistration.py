#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the mmWave HR candidate preregistration v1.

File: test_mmwave_hr_candidate_preregistration.py
Version: 1.0.0
Purpose:
    锁定这份预注册的边界，防止它被悄悄改成一个"事后调参"授权：
      - 预注册文档、验证集计划与判据登记必须存在且非空；
      - 两个候选必须存在，且每个都写明允许改什么、禁止改什么；
      - 成功判据必须是完整且冻结的五条（MAE 改善 >= 1.0 bpm、paired improve>worsen、
        单 session 恶化 <= 1.0 bpm、AE>10 不增加、0 个 correct->catastrophic 转换）；
      - 本任务不得包含任何候选实现代码，不得修改 producer / snapshot v1 / 窗口 / 阈值；
      - 不得授权 snapshot v2，不得解锁 HRV；
      - 开发集必须被明确标记为"不可作为验证集"，且验证集必须标记为尚未建立；
      - 验证集 contract 检查项必须齐全。

Usage:
    python -m pytest tests/test_mmwave_hr_candidate_preregistration.py -q

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

PREREG = REPO / "docs" / "canonical" / "MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md"
VS_PLAN = REPO / "docs" / "canonical" / "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md"
CRITERIA = REPO / "docs" / "canonical" / "CANDIDATE_SUCCESS_CRITERIA_V1.csv"
MANIFEST = REPO / "docs" / "canonical" / "MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_MANIFEST.json"
PRODUCER = REPO / "scripts" / "process_vital_signs_v3_1_1.py"
SNAPSHOT_V1 = REPO / "docs" / "results" / "2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1"

CANDIDATES = ("C1_SPECTRAL_SCORING_NEUTRALITY", "C2_ANCHOR_PERSISTENCE")
DEVELOPMENT_SESSIONS = ("9779", "97793", "97794", "97795", "97796")
VS_CHECKS = (
    "VS_1_SESSION_DISJOINT",
    "VS_2_PARTICIPANT_DISJOINT",
    "VS_3_UNTOUCHED",
    "VS_4_INDEPENDENT_ECG_REFERENCE",
    "VS_5_WINDOW_CONTRACT",
    "VS_6_ECG_ELIGIBILITY",
    "VS_7_DENOMINATOR_FROZEN",
    "VS_8_NO_REUSE",
    "VS_9_NO_DEVELOPMENT_LEAKAGE",
    "VS_10_NO_SNAPSHOT_V2",
)
SUCCESS_CRITERIA_IDS = tuple(f"C1_SUCCESS_{i}" for i in range(1, 6))
FAILURE_CRITERIA_IDS = tuple(f"C1_FAIL_{i}" for i in range(1, 5))

FORBIDDEN_STATUS_TOKENS = ("IMPROVED", "FORMAL_HR_READY", "SNAPSHOT_V2_READY")


def load_manifest() -> dict:
    """Load the preregistration manifest."""
    if not MANIFEST.exists():
        pytest.skip(f"preregistration manifest not present: {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def read_criteria() -> list[dict]:
    """Read the criteria register."""
    with CRITERIA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_preregistration_documents_exist_and_are_substantive():
    """The preregistration, validation-set plan and criteria register must exist."""
    for path in (PREREG, VS_PLAN, CRITERIA, MANIFEST):
        assert path.exists(), f"missing deliverable: {path.name}"
        assert path.stat().st_size > 0, f"empty deliverable: {path.name}"
    assert PREREG.stat().st_size > 5000, "preregistration document is too thin to be a freeze"
    assert VS_PLAN.stat().st_size > 3000, "validation-set plan is too thin"


def test_both_candidates_are_frozen_with_explicit_permissions():
    """Each candidate must appear with allowed and forbidden change sections."""
    text = PREREG.read_text(encoding="utf-8")
    for candidate in CANDIDATES:
        assert candidate in text, f"candidate not frozen: {candidate}"
    # 每个候选都必须在预注册中同时出现"允许改什么"和"禁止改什么"。
    assert text.count("**允许改什么**") >= 2
    assert text.count("**禁止改什么**") >= 2
    assert "**什么算成功（C1 成功判据）**" in text
    assert "**什么算失败（C1 失败判据）**" in text


def test_success_criteria_are_the_frozen_five():
    """The five shared success criteria must be present verbatim in both artifacts."""
    text = PREREG.read_text(encoding="utf-8")
    for marker in (
        "C1_SUCCESS_1", "C1_SUCCESS_2", "C1_SUCCESS_3", "C1_SUCCESS_4", "C1_SUCCESS_5",
        "1.0 bpm",
        "paired improve > paired worsen",
    ):
        assert marker in text, f"missing success criterion marker: {marker}"

    rows = read_criteria()
    ids = {row["criterion_id"] for row in rows}
    for criterion in SUCCESS_CRITERIA_IDS + FAILURE_CRITERIA_IDS:
        assert criterion in ids, f"criteria register missing {criterion}"
    for check in VS_CHECKS:
        assert check in ids, f"criteria register missing {check}"
    # 两个候选必须共用同一套判据。
    for row in rows:
        if row["criterion_id"].startswith("C2_SUCCESS_"):
            sibling = "C1_" + row["criterion_id"].split("_", 1)[1]
            assert sibling in ids, f"C2 criteria not mirrored from C1: {row['criterion_id']}"


def test_manifest_declares_preregistration_only():
    """The manifest must prove that nothing was implemented or run."""
    manifest = load_manifest()
    assert manifest["document_type"] == "PREREGISTRATION"
    assert manifest["preregistration_only"] is True
    assert manifest["data_run_performed"] is False
    assert len(manifest["candidates_frozen"]) == 2
    assert {c["candidate_id"] for c in manifest["candidates_frozen"]} == set(CANDIDATES)
    for candidate in manifest["candidates_frozen"]:
        assert candidate["implemented"] is False, f"{candidate['candidate_id']} must not be implemented"


def test_boundaries_are_all_false_and_hrv_blocked():
    """Every scope boundary must remain unviolated and HRV must stay BLOCKED."""
    manifest = load_manifest()
    boundaries = manifest["boundaries"]
    for flag in (
        "snapshot_v1_modified",
        "formal_producer_modified",
        "v2_formed",
        "models_trained",
        "candidate_implemented",
        "production_candidate",
        "threshold_changed",
        "distance_gate_created",
        "global_bias_correction_applied",
    ):
        assert boundaries[flag] is False, f"boundary violated: {flag}"
    assert boundaries["hrv_status"] == "BLOCKED"
    assert boundaries["hr_br_status"] == "HOLD / SUPPORTING_ONLY"


def test_development_set_is_marked_unusable_as_validation():
    """The exposed 5-session set must be explicitly barred from validation duty."""
    manifest = load_manifest()
    development = manifest["development_set_frozen"]
    assert tuple(development["sessions"]) == DEVELOPMENT_SESSIONS
    assert development["usable_as_validation"] is False
    assert development["participant_disjoint"] is False

    text = PREREG.read_text(encoding="utf-8")
    assert "single_person_repeated_measurement" in text
    assert "不得再作为验证集" in text


def test_validation_set_not_yet_formed_and_run_gated():
    """The validation set must be absent and candidate runs must remain gated off."""
    manifest = load_manifest()
    gate = manifest["validation_gate"]
    assert gate["formed"] is False
    assert gate["run_permitted"] is False
    assert tuple(gate["contract_checks"]) == VS_CHECKS

    text = VS_PLAN.read_text(encoding="utf-8")
    assert "NO_CANDIDATE_RUN_PERMITTED" in text
    assert "SET_NOT_YET_FORMED" in text
    for check in VS_CHECKS:
        assert check in text, f"validation-set plan missing {check}"


def test_development_reference_covers_only_development_sessions():
    """The only gold-clean reference on this machine covers the development sessions."""
    manifest = load_manifest()
    reference = manifest["validation_set_inventory"]["development_gold_clean_reference"]
    assert reference["sessions"] == 5
    assert reference["ecg_usable_windows"] == 100
    assert reference["covers_only_development_sessions"] is True


def test_formal_cohort_is_recorded_as_disjoint():
    """The formal cohort must be recorded as having zero session overlap."""
    manifest = load_manifest()
    cohort = manifest["validation_set_inventory"]["formal_cohort"]
    assert cohort["sessions"] == 116
    assert cohort["participant_groups"] == 61
    assert cohort["probes"] == 2320
    assert cohort["session_overlap_with_development"] == 0
    assert cohort["per_window_gold_clean_ecg_reference_exists"] is False
    assert manifest["validation_set_inventory"]["recommended_option"] == "OPT_A"


def test_no_forbidden_status_tokens():
    """The forbidden result labels must not appear anywhere in the deliverables."""
    for path in (PREREG, VS_PLAN, MANIFEST):
        blob = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_STATUS_TOKENS:
            # 允许出现在"明确不允许的结果表述"这类否定语境中，但不得被当作结论宣称。
            assert f"→ {token}" not in blob, f"{path.name} claims forbidden status: {token}"
            assert f"= {token}" not in blob, f"{path.name} claims forbidden status: {token}"


def test_no_candidate_implementation_was_added():
    """This task must not add candidate implementation code."""
    assert not (REPO / "scripts" / "maintenance" / "run_mmwave_hr_candidate_c1_20260913.py").exists()
    assert not (REPO / "scripts" / "maintenance" / "run_mmwave_hr_candidate_c2_20260913.py").exists()

    out = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    if out.returncode == 0:
        changed = [line for line in out.stdout.splitlines() if line.strip()]
        for path in changed:
            assert "process_vital_signs_v3_1_1.py" not in path, "formal producer must not change"
            assert "MMWAVE_INTEGRATION_SNAPSHOT_V1" not in path, "snapshot v1 must not change"


def test_frozen_producer_constants_are_quoted_correctly():
    """The preregistration must quote the real producer constants for both candidates."""
    text = PREREG.read_text(encoding="utf-8")
    for constant in ("0.035", "0.025", "0.8*previous_bpm + 0.2*fused", "0.20", "0.30", "7.0"):
        assert constant in text, f"preregistration does not quote constant: {constant}"

    if PRODUCER.exists():
        source = PRODUCER.read_text(encoding="utf-8")
        for constant in ("0.035", "0.025"):
            assert constant in source, f"producer no longer contains {constant}; preregistration is stale"
        assert re.search(r"HR_TIME_FREQ_WARNING_BPM\s*=\s*10\.0", source)
        assert re.search(r"HR_LO_BPM\s*=\s*HR_LO_HZ\s*\*\s*60\.0", source)


def test_governance_documents_point_to_preregistration():
    """Current-state documents must reference the preregistration."""
    for rel in (
        "AI_PROJECT.md",
        "PROJECT_STATUS.md",
        "docs/canonical/RESULT_INDEX_V1.md",
        "ANALYSIS_HISTORY_LEDGER.md",
    ):
        path = REPO / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1" in text or "mmwave_hr_candidate_preregistration" in text, (
            f"{rel} does not point to the preregistration"
        )


def test_deliverables_are_recorded_in_manifest():
    """Every declared deliverable must exist."""
    manifest = load_manifest()
    for rel in manifest["deliverables"]:
        assert (REPO / rel).exists(), f"declared deliverable missing: {rel}"


def test_manifest_digests_match_disk_for_documents():
    """Record the documents' LF-normalised digests and confirm the manifest is current."""
    manifest = load_manifest()
    recorded = manifest.get("document_digests_lf_normalised", {})
    if not recorded:
        pytest.skip("manifest does not record document digests")
    for rel, digest in recorded.items():
        path = REPO / rel
        actual = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()
        assert actual == digest, f"stale digest for {rel}"
