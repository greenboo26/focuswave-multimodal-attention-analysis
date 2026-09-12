import importlib.util
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_estimator_improvement_v1_20260912.py"
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
