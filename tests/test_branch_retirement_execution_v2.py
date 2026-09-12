#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the branch retirement execution ledger v2 (2026-09-13).

File: test_branch_retirement_execution_v2.py
Version: 1.0.0
Purpose:
    锁定 2026-09-13 分支清理的授权边界与证据，防止它被后继智能体扩大解释：
      - 只允许 3 个已合入 main 的分支被授权删除，不得多删；
      - 这 3 个分支必须以精确 40 位 SHA 记录，且分类为 MERGED_INTO_MAIN；
      - 其余 10 个分支必须逐一记录保留理由；
      - 必须记录对 V1 矩阵与 V1 执行账本的更正；
      - 必须记录 master 回滚点与 legacy tag 未被动过；
      - 必须记录主工作区与嵌套仓库的风险，避免被当成已完成清理。

Usage:
    python -m pytest tests/test_branch_retirement_execution_v2.py -q

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

MATRIX = REPO / "docs" / "repository" / "BRANCH_RETIREMENT_MATRIX_V2.csv"
LEDGER = REPO / "docs" / "repository" / "BRANCH_RETIREMENT_EXECUTION_V2.md"
MATRIX_V1 = REPO / "docs" / "repository" / "BRANCH_RETIREMENT_MATRIX_V1.csv"
LEDGER_V1 = REPO / "docs" / "repository" / "BRANCH_RETIREMENT_EXECUTION_V1.md"

BASELINE_MAIN_SHA = "7b68efec5dc545ad832571c5be7db3de347c937c"
MASTER_SHA = "96525b19422b34291e4d87747fef214d1fec60d7"
LEGACY_TAG = "legacy/mmwave-hrv-master-pre-focuswave-20260826"

AUTHORIZED_DELETIONS = {
    "codex/mmwave-estimator-improvement-v1-20260912":
        "da84260c87ac581d2a806b06878a33472e0160fc",
    "codex/mmwave-pre30s-selector-hr-20260831":
        "2f606cb9332c319993264789061731dd67be064b",
    "codex/t0-vmd-fix":
        "018d6f79ec410552ee6f59d6f9f5fb6e8151ce42",
}

RETAINED_BRANCHES = [
    "codex/behavior-formal-v3-rejected-baseline-fix",
    "codex/behavior-science-v3-baseline",
    "codex/formal-bb-behavior-v1",
    "codex/formal-bb-probe-window-fix",
    "codex/mmwave-formal-reanalysis-v2",
    "codex/mmwave-production-contract-hardening",
    "codex/project-state-map-20260829",
    "codex/q1-questionnaire-criterion-validity-20260826",
    "fix/issue33-probe-contract",
    "master",
]


def _read_matrix() -> list[dict[str, str]]:
    """读取 V2 矩阵并返回行字典列表；文件缺失时直接失败。"""
    assert MATRIX.exists(), f"missing matrix: {MATRIX}"
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _ledger_text() -> str:
    """读取 V2 执行账本文本；文件缺失时直接失败。"""
    assert LEDGER.exists(), f"missing ledger: {LEDGER}"
    return LEDGER.read_text(encoding="utf-8")


def test_matrix_covers_the_full_branch_surface():
    """矩阵必须覆盖当前全部 13 个非 main 远端分支，每行字段完整。"""
    rows = _read_matrix()
    names = [row["branch_name"] for row in rows]
    assert len(rows) == 13, f"expected 13 non-main branches, got {len(rows)}"
    assert len(set(names)) == 13, "branch_name must be unique"
    assert "main" not in names, "main is the default branch and must not be a retirement row"
    for row in rows:
        assert None not in row, f"extra unquoted comma in row: {row['branch_name']}"
        assert row["head_sha"], f"missing head_sha for {row['branch_name']}"
        assert re.fullmatch(r"[0-9a-f]{40}", row["head_sha"]), row["head_sha"]
        assert row["classification"], f"missing classification for {row['branch_name']}"
        assert row["recommended_final_action"], f"missing action for {row['branch_name']}"


def test_only_three_branches_are_authorized_for_deletion():
    """授权删除集必须恰好是 3 个已合入 main 的分支，防止清理范围被扩大。"""
    rows = _read_matrix()
    authorized = {
        row["branch_name"]: row["head_sha"]
        for row in rows
        if row["recommended_final_action"] == "delete"
    }
    assert authorized == AUTHORIZED_DELETIONS, authorized


def test_authorized_deletions_are_ancestors_of_main():
    """被删除的分支必须分类为 MERGED_INTO_MAIN，即其全部提交仍可从 main 到达。"""
    rows = {row["branch_name"]: row for row in _read_matrix()}
    for name, sha in AUTHORIZED_DELETIONS.items():
        row = rows[name]
        assert row["head_sha"] == sha, name
        assert row["classification"] == "MERGED_INTO_MAIN", name
        assert row["canonical_successor"] == "main", name


def test_retained_branches_are_all_recorded_with_a_reason():
    """10 个保留分支必须逐一出现在矩阵与账本中。"""
    rows = {row["branch_name"]: row for row in _read_matrix()}
    text = _ledger_text()
    for name in RETAINED_BRANCHES:
        assert name in rows, f"{name} missing from matrix"
        assert name in text, f"{name} missing from ledger"
        assert rows[name]["classification"] != "MERGED_INTO_MAIN", name
    # 保留分支不得被写成可删除
    for name in RETAINED_BRANCHES:
        assert rows[name]["recommended_final_action"] != "delete", name


def test_ledger_records_the_q1_tag_gap_and_report_mirror():
    """q1 分支必须记为活跃报告线，并记录 tag 未覆盖尾部 28 个提交。"""
    text = _ledger_text()
    assert "no common ancestor" in text
    assert "d8a2870766b011da3d62b85d33dd10652d2db4b4" in text
    assert "ba7a2c652bea82c3fa58ad5858a7460ed933fb47" in text
    assert "28 commits past" in text
    assert "docs/交付/0827报告v1_填充版_20260831.docx" in text
    assert "10d56a656d1f7cec3de65a6f1ae3e6214691a211" in text


def test_ledger_corrects_the_earlier_records():
    """必须显式更正 V1 矩阵与 V1 执行账本中关于 q1 的陈述。"""
    text = _ledger_text()
    assert MATRIX_V1.exists() and LEDGER_V1.exists()
    assert "BRANCH_RETIREMENT_MATRIX_V1.csv" in text
    assert "BRANCH_RETIREMENT_EXECUTION_V1.md" in text
    assert "is stale" in text
    assert "does not hold for this row" in text


def test_ledger_preserves_rollback_anchors():
    """基线、master、legacy tag 与默认分支必须原样记录，且声明未建/未删 tag。"""
    text = _ledger_text()
    assert BASELINE_MAIN_SHA in text
    assert MASTER_SHA in text
    assert LEGACY_TAG in text
    assert "Default branch remains `main`" in text
    assert "No archive, legacy, or stage tag was created, deleted, or force-moved" in text


def test_ledger_records_open_risks_and_execution_status():
    """必须记录工作区/嵌套仓库风险，并给出机器可判定的执行状态。"""
    text = _ledger_text()
    assert "codex/q1-questionnaire-criterion-validity-20260826`, not on `main`" in text
    assert "git clean -fdx" in text
    assert "FocusWave-Formal-Analysis" in text
    assert "Attention-Analysis" in text
    statuses = {"DELETION_AUTHORIZED_PENDING", "DELETED_AND_VERIFIED"}
    found = {token for token in statuses if token in text}
    assert len(found) == 1, f"ledger must carry exactly one execution status, found {found}"


def test_held_superseded_branches_have_no_archive_tag_yet():
    """3 个已取代分支必须记为尚无 tag，并要求先打 tag 再删。"""
    rows = {row["branch_name"]: row for row in _read_matrix()}
    for name in (
        "codex/mmwave-formal-reanalysis-v2",
        "codex/mmwave-production-contract-hardening",
        "codex/project-state-map-20260829",
    ):
        assert rows[name]["classification"] in {
            "SUPERSEDED_NO_ARCHIVE_TAG",
            "SUPERSEDED_BY_MAIN",
        }, name
        assert rows[name]["recommended_final_action"] != "delete", name
    text = _ledger_text()
    assert "archive/20260913/" in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
