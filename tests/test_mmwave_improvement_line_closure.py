#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the mmWave improvement line closure v1.

File: test_mmwave_improvement_line_closure.py
Version: 1.0.0
Purpose:
    锁定毫米波改进线收口的裁决与边界，防止它被重新打开成"继续找验证集"：
      - 收口文件必须存在并记录权威裁决；
      - OPT_A 必须标为无效，REM_1 必须标为不执行；
      - 错误必须记为 corrected planning error，而不是待解的数据位置问题；
      - C1/C2 必须是 PAUSED_PENDING_NEW_COLLECTION；
      - snapshot v1 / producer / HRV 边界不变，不形成 v2；
      - VS_DATASET 仅作 C2 secondary，AgeBalanced 为历史 benchmark；
      - 验证集计划与外部资产审计中的 OPT_A 路由必须已被标记作废。

Usage:
    python -m pytest tests/test_mmwave_improvement_line_closure.py -q

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

CLOSURE = REPO / "docs" / "canonical" / "MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1.md"
PLAN = REPO / "docs" / "canonical" / "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md"
EXTERNAL_REPORT = (REPO / "docs" / "results" / "2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1"
                   / "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_REPORT.md")
PREREG_MANIFEST = REPO / "docs" / "canonical" / "MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1_MANIFEST.json"
STATUS = REPO / "PROJECT_STATUS.md"
LEDGER = REPO / "ANALYSIS_HISTORY_LEDGER.md"
AI_PROJECT = REPO / "AI_PROJECT.md"

PRODUCER = REPO / "scripts" / "process_vital_signs_v3_1_1.py"
SNAPSHOT_V1 = REPO / "docs" / "results" / "2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1"


def test_closure_document_exists_and_states_the_ruling():
    """The closure record must exist and carry the authoritative decisions."""
    assert CLOSURE.exists(), "closure document missing"
    text = CLOSURE.read_text(encoding="utf-8")
    assert "MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1" in text
    assert "OPT_A" in text and "无效" in text
    assert "REM_1" in text and "不执行" in text
    assert "corrected planning error" in text
    assert "PAUSED_PENDING_NEW_COLLECTION" in text
    assert "LINE_PAUSED" in text


def test_closure_states_the_three_status_tokens():
    """The three closure status tokens must be recorded."""
    text = CLOSURE.read_text(encoding="utf-8")
    for token in ("MMWAVE_IMPROVEMENT_LINE = PAUSED", "MMWAVE_INTEGRATION      = READY",
                  "MAIN_ANALYSIS           = PROCEED"):
        assert token in text, f"missing closure status token: {token}"


def test_opt_a_routing_is_voided_in_the_plan():
    """The plan must explicitly void the OPT_A routing and keep the old text as provenance."""
    assert PLAN.exists(), "validation-set plan missing"
    text = PLAN.read_text(encoding="utf-8")
    assert "ROUTING VOID" in text
    assert "is invalid" in text
    # 旧文本保留为 provenance，不得删除历史。
    assert "to be built next" in text


def test_recommendation_is_retracted_in_the_plan():
    """The OPT_A recommendation must be marked retracted."""
    text = PLAN.read_text(encoding="utf-8")
    assert "RETRACTED RECOMMENDATION" in text
    assert "data-engineering task" in text


def test_external_audit_routing_is_voided():
    """The external audit report must void its own PROCEED_AS_PRIMARY routing."""
    if not EXTERNAL_REPORT.exists():
        pytest.skip("external audit report not present")
    text = EXTERNAL_REPORT.read_text(encoding="utf-8")
    assert "路由作废" in text
    assert "PAUSED_PENDING_NEW_COLLECTION" in text


def test_governance_documents_carry_the_closure():
    """Current-state documents must point at the closure record."""
    markers = ("MMWAVE_IMPROVEMENT_LINE_CLOSURE_V1", "mmWave improvement line CLOSURE v1",
               "mmwave_line_closure")
    for path in (STATUS, LEDGER, AI_PROJECT):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        assert any(m in text for m in markers), f"{path.name} does not carry the closure"


def test_preregistration_digests_still_consistent():
    """Refreshing the plan must have kept the preregistration digests current."""
    import hashlib
    import json

    if not PREREG_MANIFEST.exists():
        pytest.skip("preregistration manifest not present")
    manifest = json.loads(PREREG_MANIFEST.read_text(encoding="utf-8"))
    for rel, digest in manifest["document_digests_lf_normalised"].items():
        actual = hashlib.sha256((REPO / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()
        assert actual == digest, f"stale digest for {rel}"


def test_boundaries_unchanged():
    """The closure must not have modified snapshot v1 or the producer."""
    import subprocess

    for path in ("scripts/process_vital_signs_v3_1_1.py",
                 "docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/"):
        if not (REPO / path).exists():
            continue
        out = subprocess.run(["git", "diff", "--name-only", "origin/main", "--", path],
                             cwd=str(REPO), capture_output=True, text=True, check=False)
        if out.returncode == 0:
            assert out.stdout.strip() == "", f"protected path modified: {path}"