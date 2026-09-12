import importlib.util
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_hr_recovery_p2_failure_attribution_20260912.py"
SPEC = importlib.util.spec_from_file_location("p2", PATH)
P2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P2)


def row(fused=80, time=80, spectral=80, ecg=80, usable=1.0, frames=3000, br=15):
    return {"ecg_hr_bpm": ecg, "hr_30s_fused_bpm": fused, "hr_30s_time_bpm": time,
            "hr_30s_spectral_bpm": spectral, "hr_usable_ratio": usable,
            "mmwave_frames": frames, "br_bpm": br}


def evidence(exact=False, nearby=False, prominence=.5):
    return {"exact_available": exact, "nearby_available": nearby, "exact_tol": 1.5,
            "selected_candidate": {"relative_prominence": prominence}}


def test_primary_precedence_and_old_lineage():
    primary, flags, old = P2.classify(row(fused=70, time=69, spectral=55, ecg=82), evidence(True), {"exact_available": True})
    assert primary == "SELECTED_TARGET_WRONG_PEAK"
    assert old == "true_peak_available_selected_target_but_wrong_selection"
    assert "ORACLE_ASSISTED" in flags


def test_target_miss_and_weak_signal():
    primary, _, _ = P2.classify(row(fused=70, time=70, spectral=70, ecg=82), evidence(False, False, .2), {"exact_available": True})
    assert primary == "TARGET_BIN_CHANNEL_MISS"
    primary, _, _ = P2.classify(row(fused=70, time=70, spectral=70, ecg=82), evidence(False, False, .01), {"exact_available": False})
    assert primary == "WEAK_OR_ABSENT_HEART_EVIDENCE"


def test_fusion_and_severity_flags():
    primary, flags, _ = P2.classify(row(fused=75, time=82, spectral=70, ecg=82), evidence(False, True, .2), {"exact_available": False})
    assert primary == "AMBIGUOUS"
    assert "TIME_CORRECT_FUSION_WRONG" in flags
    assert P2.severity(5) == "AE_LE_5"
    assert P2.severity(20.1) == "AE_GT_20"
