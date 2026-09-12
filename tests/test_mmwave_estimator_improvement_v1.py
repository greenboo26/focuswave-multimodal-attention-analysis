import importlib.util
import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_estimator_improvement_v1_20260912.py"
REPO = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO / "docs" / "results" / "2026-09-12_MMWAVE_ESTIMATOR_IMPROVEMENT_V1"
SPEC = importlib.util.spec_from_file_location("improvement", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(**overrides):
    base = {
        "hr_30s_fused_bpm": "60",
        "hr_30s_time_bpm": "80",
        "hr_30s_spectral_bpm": "60",
        "hr_confidence": "0.05",
        "br_bpm": "20",
        "ecg_hr_bpm": "10",
        "rsp_br_bpm": "99",
    }
    base.update(overrides)
    return base


def test_h1_uses_time_on_existing_warning_threshold():
    value, switched, _ = MODULE.candidate_value(row(), "H1_WARNING_TIME_GATE")
    assert switched is True
    assert value == 80.0


def test_candidate_is_invariant_to_ecg_and_rsp_reference_values():
    original = [MODULE.candidate_value(row(), item["id"]) for item in MODULE.HYPOTHESES]
    changed = [MODULE.candidate_value(row(ecg_hr_bpm="180", rsp_br_bpm="2"), item["id"]) for item in MODULE.HYPOTHESES]
    assert original == changed


def test_harmonic_rule_uses_mmwave_br_not_reference_rsp():
    value, switched, reason = MODULE.candidate_value(row(br_bpm="20", rsp_br_bpm="5"), "H2_HARMONIC_CONFLICT_TIME_GATE")
    assert switched is True
    assert value == 80.0
    assert reason == "mmwave_br_harmonic_conflict"


def test_acceptance_rejects_single_session_gain():
    control = {"mae_bpm": 10, "median_ae_bpm": 8, "p90_ae_bpm": 20, "max_ae_bpm": 40}
    candidate = {"mae_bpm": 9, "median_ae_bpm": 7, "p90_ae_bpm": 19, "max_ae_bpm": 40}
    accepted, failed = MODULE.acceptance(candidate, control, [-5, 0.1, 0.2, 0.3, 0.4], {"improve": 60, "worsen": 40}, [2, 3], [1, 2])
    assert accepted is False
    assert "at_least_3_of_5_sessions_improve" in failed


def test_acceptance_rejects_new_catastrophic_probe_failure():
    control = {"mae_bpm": 10, "median_ae_bpm": 8, "p90_ae_bpm": 20, "max_ae_bpm": 40}
    candidate = {"mae_bpm": 9, "median_ae_bpm": 7, "p90_ae_bpm": 19, "max_ae_bpm": 40}
    accepted, failed = MODULE.acceptance(candidate, control, [-1, -1, -1, 0, 0], {"improve": 60, "worsen": 1}, [0.5, 20], [11.5, 10])
    assert accepted is False
    assert "no_control_correct_to_gt10_transition" in failed
    assert "no_probe_worsens_gt5_bpm" in failed


def test_manifest_declares_no_snapshot_v1_change_and_cloud_handoff_files():
    """交付 manifest 必须可解析、声明未改 snapshot v1，并列出待上传文件清单。"""
    manifest = json.loads((RESULT_DIR / "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["snapshot_v1_modified"] is False
    assert manifest["formal_producer_modified"] is False
    assert manifest["ecg_used_for_production_rule"] is False
    assert manifest["status"] == "NO_STABLE_IMPROVEMENT"
    assert manifest["best_candidate"] is None
    cloud = manifest["cloud_handoff"]
    names = [item["name"] for item in cloud["upload_files"]]
    # 任务正文第 14 节要求的最小上传集合必须全部在清单中
    for required in [
        "HANDOFF.md",
        "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_REPORT.md",
        "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json",
        "REFERENCE_QC_LINEAGE_REPORT.md",
        "REFERENCE_QC_ELIGIBILITY_SUMMARY.csv",
        "CONTROL_VS_CANDIDATES_SUMMARY.csv",
        "PER_SESSION_COMPARISON.csv",
        "FAILURE_CLASS_DELTA.csv",
        "CANDIDATE_DECISION_LOG.md",
        "ERROR_LOG.json",
    ]:
        assert required in names, f"missing upload entry: {required}"
    assert cloud["status"] in {"BLOCKED", "UPLOADED_AND_VERIFIED"}
    # 已上传状态下，清单里每个带具体哈希的文件都必须与磁盘当前内容一致；
    # manifest 自身与最后上传的验证报告是自指文件，其摘要记录在 HANDOFF 与 GitHub issue。
    self_referential = {
        "MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json",
        "CLOUD_HANDOFF_VERIFICATION.json",
    }
    if cloud["status"] == "UPLOADED_AND_VERIFIED":
        import hashlib

        for item in cloud["upload_files"]:
            digest = item["sha256"]
            if item["name"] in self_referential or "\n" in digest:
                continue
            target = REPO / item["repo_path"]
            actual = hashlib.sha256(target.read_bytes()).hexdigest().upper()
            assert actual == digest, f"stale hash recorded for {item['name']}"
