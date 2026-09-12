#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the mmWave low-bias mechanism audit v1.

File: test_mmwave_low_bias_mechanism_audit.py
Version: 1.0.0
Purpose:
    锁定机制审计的边界与结果一致性：
      - 输入三份 CSV 的 SHA-256 必须与冻结值一致；
      - 100/100 keys exact，5 sessions；
      - 冻结 control 指标可复现；
      - 不产生任何 candidate / production 规则输出；
      - 不改 producer、不改 snapshot v1、不训练模型、HRV 保持 BLOCKED；
      - 输出 schema 与 manifest 一致；
      - local-only probe 表不入 Git，且 manifest 记录的 digest 与磁盘一致。

Usage:
    python -m pytest tests/test_mmwave_low_bias_mechanism_audit.py -q

Dependencies:
    仅 Python 标准库（与审计脚本一致，避免受本机 numpy/pandas 版本影响）。
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "maintenance" / "run_mmwave_low_bias_mechanism_audit_20260913.py"
RENDER = REPO / "scripts" / "maintenance" / "render_mmwave_mechanism_audit_docs_20260913.py"
RESULT_DIR = REPO / "docs" / "results" / "2026-09-13_MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1"
MANIFEST = RESULT_DIR / "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_MANIFEST.json"
SNAPSHOT_V1 = REPO / "docs" / "results" / "2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1"
PRODUCER = REPO / "scripts" / "process_vital_signs_v3_1_1.py"

DERIVED = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1")
INPUTS = {
    "CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv":
        (DERIVED / "final_r6" / "CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv",
         "B4251445B1938DF61F07EFECE9ECBA4DD29FEFFCEED699E0B5B5226D0571A76D"),
    "REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv":
        (DERIVED / "final_r6" / "REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv",
         "EA9DB07FB37A2027569714B3193FC49AAFECA7C59690750BFFAF523C7188F479"),
    "MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv":
        (DERIVED / "phase_a_strict_p2_detail" / "MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv",
         "FFED63DDE2E30F5A7B216E5996CB136012286CE4832CA82E6541A66E556C81B1"),
}

EXPECTED_CLASS_COUNTS = {
    "CORRECT_OR_NEAR_CORRECT": 39,
    "SELECTED_TARGET_WRONG_PEAK": 27,
    "HARMONIC_OR_HALF_DOUBLE_LOCK": 18,
    "TARGET_BIN_CHANNEL_MISS": 16,
}
EXPECTED_FUSED_BIAS = -9.033105841645153
EXPECTED_FUSED_MAE = 10.457079173363644

ALLOWED_MECHANISM_STATUS = {
    "MECHANISM_SUPPORTED",
    "MULTIFACTOR_MECHANISM_SUPPORTED",
    "MECHANISM_PARTIALLY_RESOLVED",
    "MECHANISM_NOT_RESOLVED",
}
FORBIDDEN_STATUS = {"IMPROVED", "FORMAL_HR_READY", "SNAPSHOT_V2_READY"}

REQUIRED_OUTPUTS = (
    "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_REPORT.md",
    "MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_MANIFEST.json",
    "FUSION_PATH_AUDIT.md",
    "FUSION_LOW_BIAS_DECOMPOSITION.csv",
    "DISTANCE_SESSION_STRATIFIED.csv",
    "DISTANCE_FAILURE_CLASS_MATRIX.csv",
    "FAILURE_CLASS_BIAS_DECOMPOSITION.csv",
    "ECG_HR_BAND_DECOMPOSITION.csv",
    "QC_BIAS_DECOMPOSITION.csv",
    "MECHANISM_EVIDENCE_MATRIX.csv",
    "ERROR_LOG.json",
    "HANDOFF.md",
)


def sha256(path: Path) -> str:
    """Return the uppercase SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_manifest() -> dict:
    """Load the audit manifest, skipping when inputs are unavailable."""
    if not MANIFEST.exists():
        pytest.skip(f"audit manifest not present: {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def read_rows(name: str) -> list[dict]:
    """Read a produced CSV from the result directory."""
    with (RESULT_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_input_identity_is_frozen():
    """The three inputs must match the frozen SHA-256 values exactly."""
    for name, (path, expected) in INPUTS.items():
        if not path.exists():
            pytest.skip(f"input unavailable on this machine: {path}")
        assert sha256(path) == expected, f"input identity drifted: {name}"


def test_control_reproduction_via_verify_only():
    """Re-running the audit in verify-only mode must reproduce the frozen control."""
    if not all(path.exists() for path, _ in INPUTS.values()):
        pytest.skip("frozen inputs unavailable")
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify-only"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, f"verify-only failed: {out.stderr[-2000:]}"
    payload = json.loads(out.stdout.strip().splitlines()[-1])
    assert payload["state"] == "VERIFY_ONLY_PASS"
    assert payload["n_probes"] == 100
    assert payload["fused_bias"] == pytest.approx(EXPECTED_FUSED_BIAS, abs=1e-9)


def test_denominator_and_frozen_control_in_manifest():
    """Manifest must record 5 sessions / 100 probes and the reproduced control."""
    manifest = load_manifest()
    assert manifest["denominator"]["n_probes"] == 100
    assert manifest["denominator"]["n_sessions"] == 5
    assert manifest["denominator"]["session_counts"] == {
        "9779": 20, "97793": 20, "97794": 20, "97795": 20, "97796": 20
    }
    assert manifest["denominator"]["failure_class_counts"] == EXPECTED_CLASS_COUNTS
    reproduced = manifest["frozen_control_reproduced"]
    assert reproduced["fused"]["bias"] == pytest.approx(EXPECTED_FUSED_BIAS, abs=1e-8)
    assert reproduced["fused"]["mae"] == pytest.approx(EXPECTED_FUSED_MAE, abs=1e-8)


def test_probe_level_keys_are_exactly_100():
    """The fusion decomposition must contain exactly the 100 frozen keys, once each."""
    rows = read_rows("FUSION_LOW_BIAS_DECOMPOSITION.csv")
    assert len(rows) == 100
    keys = [(r["subject"], r["block_id"], r["probe_onset_unix_ms"]) for r in rows]
    assert len(set(keys)) == 100
    assert {k[0] for k in keys} == {"9779", "97793", "97794", "97795", "97796"}
    per_session = {s: sum(1 for k in keys if k[0] == s) for s in {k[0] for k in keys}}
    assert per_session == {"9779": 20, "97793": 20, "97794": 20, "97795": 20, "97796": 20}


def test_required_outputs_exist_and_are_nonempty():
    """Every required Git-safe deliverable must exist and be non-empty."""
    for name in REQUIRED_OUTPUTS:
        path = RESULT_DIR / name
        assert path.exists(), f"missing deliverable: {name}"
        assert path.stat().st_size > 0, f"empty deliverable: {name}"


def test_output_schema_is_stable():
    """Key columns of each produced table must exist and be populated."""
    fusion = read_rows("FUSION_LOW_BIAS_DECOMPOSITION.csv")
    for column in (
        "signed_error_fused_bpm", "signed_error_time_bpm", "signed_error_spectral_bpm",
        "absolute_error_fused_bpm", "absolute_error_time_bpm", "absolute_error_spectral_bpm",
        "fusion_penalty_vs_time_bpm", "fusion_signed_shift_vs_time_bpm",
        "spectral_signed_shift_vs_time_bpm", "spectral_below_time", "fused_below_time",
        "spectral_pulled_fused_down", "time_ae_le5_and_fused_ae_gt5",
        "time_ae_le5_and_fused_ae_gt10",
    ):
        assert column in fusion[0], f"fusion table missing column: {column}"

    for name in (
        "FAILURE_CLASS_BIAS_DECOMPOSITION.csv",
        "DISTANCE_FAILURE_CLASS_MATRIX.csv",
    ):
        rows = read_rows(name)
        for column in ("n", "fused_bias_bpm", "fused_mae_bpm", "time_bias_bpm", "spectral_bias_bpm"):
            assert column in rows[0], f"{name} missing column: {column}"

    bands = read_rows("ECG_HR_BAND_DECOMPOSITION.csv")
    assert {r["ecg_hr_band"] for r in bands} == {"LT75", "75_TO_90", "GT90"}
    assert {"POOLED", "SESSION_9779"} <= {r["scope"] for r in bands}

    qc = read_rows("QC_BIAS_DECOMPOSITION.csv")
    qc_fields = {r["qc_field"] for r in qc}
    assert {"hr_usable_ratio", "phase_stability", "motion_proxy"} <= qc_fields

    matrix = read_rows("MECHANISM_EVIDENCE_MATRIX.csv")
    for column in (
        "MECHANISM_CANDIDATE", "EVIDENCE_FOR", "EVIDENCE_AGAINST",
        "SESSION_CONSISTENCY", "FAILURE_CLASS_LINK", "CONFIDENCE", "NEXT_TEST",
    ):
        assert column in matrix[0], f"mechanism matrix missing column: {column}"
    assert len(matrix) >= 7
    for row in matrix:
        assert row["EVIDENCE_FOR"].strip(), "mechanism row without evidence_for"
        assert row["EVIDENCE_AGAINST"].strip(), "mechanism row without evidence_against"
        assert row["NEXT_TEST"].strip(), "mechanism row without next_test"


def test_bias_attribution_is_additive_across_classes():
    """Per-class bias contributions must sum to the pooled fused bias."""
    rows = read_rows("BIAS_ATTRIBUTION_DECOMPOSITION.csv")
    per_class = [r for r in rows if r["failure_class"] != "ALL_PROBES"]
    pooled = [r for r in rows if r["failure_class"] == "ALL_PROBES"]
    assert len(pooled) == 1
    total = sum(float(r["bias_contribution_to_pooled_bpm"]) for r in per_class)
    assert total == pytest.approx(float(pooled[0]["bias_contribution_to_pooled_bpm"]), abs=1e-6)
    assert sum(int(r["n"]) for r in per_class) == 100


def test_mechanism_status_is_in_allowed_vocabulary():
    """The final status must use only the allowed mechanism vocabulary."""
    manifest = load_manifest()
    status = manifest["mechanism_status"]
    assert status in ALLOWED_MECHANISM_STATUS, f"unexpected mechanism status: {status}"
    assert status not in FORBIDDEN_STATUS


def test_no_candidate_or_production_promotion():
    """The audit must not declare any candidate, improvement or v2 formation."""
    manifest = load_manifest()
    boundaries = manifest["boundaries"]
    assert boundaries["no_new_gating_rule"] is True
    assert boundaries["no_new_threshold"] is True
    assert boundaries["no_production_candidate"] is True
    assert boundaries["snapshot_v1_modified"] is False
    assert boundaries["formal_producer_modified"] is False
    assert boundaries["models_trained"] is False
    assert boundaries["hrv_status"] == "BLOCKED"

    blob = MANIFEST.read_text(encoding="utf-8")
    for forbidden in ("SNAPSHOT_V2_READY", "FORMAL_HR_READY", '"IMPROVED"'):
        assert forbidden not in blob, f"forbidden status token present: {forbidden}"


def test_producer_and_snapshot_v1_untouched():
    """The formal producer and snapshot v1 must not be modified by this task."""
    if PRODUCER.exists():
        # 生产脚本必须与 canonical main 完全一致（本任务未改 producer）。
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--",
             "scripts/process_vital_signs_v3_1_1.py"],
            cwd=str(REPO), capture_output=True, text=True, check=False,
        )
        if out.returncode == 0:
            assert out.stdout.strip() == "", f"formal producer modified: {out.stdout}"
    if SNAPSHOT_V1.exists():
        # 任务分支必须包含与 canonical main 相同的 snapshot v1 文件。
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--",
             "docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/"],
            cwd=str(REPO), capture_output=True, text=True, check=False,
        )
        if out.returncode == 0:
            assert out.stdout.strip() == "", f"snapshot v1 modified: {out.stdout}"


def test_manifest_matches_disk_for_local_only_probe_table():
    """The local-only probe table must exist outside Git and match its digest."""
    manifest = load_manifest()
    local = manifest["local_only_outputs"]
    assert len(local) == 1
    entry = local[0]
    path = Path(entry["path"])
    if not path.exists():
        pytest.skip("local-only probe table unavailable on this machine")
    assert entry["rows"] == 100
    assert sha256(path) == entry["sha256"]

    # local-only 表不能进入 Git。
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", entry["name"]],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert out.returncode != 0, "local-only probe table must not be tracked by Git"


def test_markdown_deliverables_recorded_in_manifest():
    """Rendered Markdown deliverables must be present and digest-recorded."""
    manifest = load_manifest()
    recorded = manifest["markdown_deliverables"]
    assert set(recorded) >= {"MMWAVE_LOW_BIAS_MECHANISM_AUDIT_V1_REPORT.md", "FUSION_PATH_AUDIT.md"}
    for name, info in recorded.items():
        path = RESULT_DIR / name
        assert path.exists(), f"recorded deliverable missing: {name}"
        assert info["sha256"] == sha256(path), f"stale digest recorded for {name}"


def test_render_script_is_importable():
    """The render helper must load cleanly (syntax/import smoke check)."""
    spec = importlib.util.spec_from_file_location("mechanism_render", RENDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main")
