"""Release-level consistency checks for the mmWave attention research system."""
from __future__ import annotations

import json
import py_compile
import csv
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def main():
    errors = []
    source_dirs = sorted(Path(r"E:\Data").glob("sub-*_"))
    result_dirs = sorted(OUT.glob("sub-*_"))
    jsons = [d / f"{d.name.rstrip('_')}_ses-SART_mmwave_vital_signs.json" for d in result_dirs]
    npzs = [d / f"{d.name.rstrip('_')}_ses-SART_mmwave_vital_signs.npz" for d in result_dirs]
    if len(source_dirs) < len(result_dirs): errors.append("processed directory count exceeds source directory count")
    if len(result_dirs) == 0: errors.append("no processed directories found")
    if not all(p.exists() for p in jsons): errors.append("one or more vital-sign JSON outputs are missing")
    if not all(p.exists() for p in npzs): errors.append("one or more vital-sign NPZ outputs are missing")
    required = [
        OUT / "final_summary.json", OUT / "focus_discrimination.csv", OUT / "focus_lopo.json", OUT / "focus_discrimination_augmented.csv", OUT / "augmented_vitals_lopo.json",
        OUT / "runtime_focus_system_eval.json", OUT / "rich_focus_features_lopo.json",
        OUT / "behavior_gated_runtime_all.json", OUT / "behavior_gated_runtime_all.csv",
        OUT / "within_subject_focus_lopo.json", OUT / "personalized_temporal_lopo.json",
        OUT / "label_coverage_audit.json", OUT / "final_hr_br_distribution.png",
        OUT / "target_100_audit.json", OUT / "target_100_audit.csv",
        OUT / "project_completion_audit.json",
        OUT / "behavior_outcome_audit.json", OUT / "behavior_subject_summary.csv", OUT / "behavior_probe_windows.csv", OUT / "behavior_supervised_lopo.json",
        OUT / "mmwave_behavior_criterion.json", OUT / "mmwave_behavior_criterion_windows.csv",
        OUT / "mmwave_behavior_fusion_lopo.json",
        OUT / "crossmodal_time_gate.json", OUT / "crossmodal_time_gate.csv",
        OUT / "crossmodal_features_all.csv", OUT / "crossmodal_fusion_lopo.json", OUT / "crossmodal_temporal_lopo.json", OUT / "crossmodal_within_subject_lopo.json", OUT / "personalized_temporal_runtime.json", OUT / "personalized_temporal_runtime_expanded.json",
        OUT / "personalized_temporal_runtime_behavior.json",
        OUT / "system_mode_policy.json",
        OUT / "source_inventory_final.json",
        ROOT / "output" / "External_AgeBalanced" / "summary.json",
        ROOT / "output" / "External_AgeBalanced" / "sessions.csv",
        ROOT / "output" / "ACQ_reference_20260821" / "breath_method_comparison.json",
        ROOT / "output" / "ACQ_reference_20260821" / "breath_method_comparison_current.json",
        ROOT / "output" / "ACQ_reference_20260821" / "acq_reference_validation_summary.json",
        ROOT / "output" / "ACQ_reference_20260821" / "ACQ_reference_validation_20260822.md",
        ROOT / "output" / "ACQ_reference_20260821" / "acq_reference_validation_scatter.png",
        ROOT / "output" / "ACQ_reference_20260821" / "mmwave_vs_reference_probes_60s.csv",
        ROOT / "output" / "ACQ_reference_20260821" / "acq_signal_quality_audit.json",
        ROOT / "output" / "ACQ_reference_20260821" / "ACQ_signal_quality_audit_20260822.md",
        ROOT / "output" / "ACQ_reference_20260821" / "breath_harmonic_correction_evaluation.json",
        ROOT / "output" / "ACQ_reference_20260821" / "breath_harmonic_correction_scatter.png",
        ROOT / "output" / "E_Data_FAST" / "personalized_scores_validated_behavior.json",
        ROOT / "output" / "E_Data_FAST" / "personalized_scores_mmwave.json",
        ROOT / "output" / "E_Data_FAST" / "personalized_scores_mmwave_rgb_nir.json",
        ROOT / "output" / "E_Data_FAST" / "personalized_scores_validated_behavior.csv",
        ROOT / "output" / "E_Data_FAST" / "source_evidence_audit.json",
        ROOT / "docs" / "毫米波专注系统_运行手册.md",
        ROOT / "docs" / "最终交付审计报告_100人目标.md",
        ROOT / "docs" / "系统模式结果对照表.md",
        ROOT / "数据采集与验收清单_100人目标.md",
        ROOT / "需求-证据追踪矩阵.md",
        ROOT / "output" / "系统验证报告_20260821.md", ROOT / "README_毫米波专注系统.md",
    ]
    errors.extend(f"missing artifact: {p}" for p in required if not p.exists())
    if errors:
        status = "failed"
    else:
        summary = json.loads((OUT / "final_summary.json").read_text(encoding="utf-8"))
        runtime = json.loads((OUT / "runtime_focus_system_eval.json").read_text(encoding="utf-8"))["summary"]
        temporal = json.loads((OUT / "personalized_temporal_lopo.json").read_text(encoding="utf-8"))["analyses"]
        csv_windows = sum(1 for _ in csv.DictReader((OUT / "focus_discrimination.csv").open(encoding="utf-8-sig")))
        checks = {
            "complete_subjects_matches_directories": summary["complete_subjects"] == len(result_dirs),
            "probe_windows_matches_csv": summary["probe_windows"] == csv_windows,
            "runtime_windows_matches_csv": runtime["n_input_windows"] == csv_windows,
            "behavior_gated_runtime_windows_match_csv": json.loads((OUT / "behavior_gated_runtime_all.json").read_text(encoding="utf-8"))["n_windows"] == csv_windows,
            "behavior_gated_runtime_subjects_match_summary": json.loads((OUT / "behavior_gated_runtime_all.json").read_text(encoding="utf-8"))["n_records"] == summary["complete_subjects"],
            "temporal_focus_all_auc_present": temporal["focus_vs_all_nonfocus"]["auc"] is not None,
            "temporal_focus_mw_auc_present": temporal["focus_vs_mind_wandering"]["auc"] is not None,
        }
        errors.extend(k for k, v in checks.items() if not v)
        for p in [ROOT / "scripts" / "mmwave_focus_system.py", ROOT / "scripts" / "run_focus_runtime_batch.py", ROOT / "scripts" / "fit_personalized_calibration.py", ROOT / "scripts" / "personalized_temporal_runtime.py", ROOT / "scripts" / "score_personalized_models.py", ROOT / "scripts" / "augment_window_vital_features.py", ROOT / "scripts" / "evaluate_augmented_vitals_lopo.py", ROOT / "scripts" / "evaluate_acq_breath_methods.py", ROOT / "scripts" / "evaluate_breath_harmonic_correction.py", ROOT / "scripts" / "compare_mmwave_reference.py", ROOT / "scripts" / "analyze_acq_reference.py", ROOT / "scripts" / "build_acq_reference_validation_report.py", ROOT / "scripts" / "audit_acq_signal_quality.py", ROOT / "scripts" / "evaluate_personalized_temporal.py", ROOT / "scripts" / "evaluate_raw_motion_features.py", ROOT / "scripts" / "audit_behavior_outcomes.py", ROOT / "scripts" / "evaluate_mmwave_behavior_criterion.py", ROOT / "scripts" / "evaluate_mmwave_behavior_fusion.py", ROOT / "scripts" / "evaluate_behavior_supervised_lopo.py", ROOT / "scripts" / "audit_crossmodal_time_gate.py", ROOT / "scripts" / "extract_crossmodal_features.py", ROOT / "scripts" / "batch_extract_crossmodal.py", ROOT / "scripts" / "evaluate_crossmodal_fusion.py", ROOT / "scripts" / "evaluate_crossmodal_temporal.py", ROOT / "scripts" / "evaluate_crossmodal_within_subject.py", ROOT / "scripts" / "audit_project_completion.py", ROOT / "scripts" / "update_focuswave_pipeline.py", ROOT / "scripts" / "audit_source_inventory.py", ROOT / "scripts" / "audit_source_evidence.py", ROOT / "scripts" / "audit_100_subject_target.py"]:
            try: py_compile.compile(str(p), doraise=True)
            except Exception as e: errors.append(f"compile failed: {p}: {e}")
        status = "passed" if not errors else "failed"
    optional = [OUT / "raw_motion_features_lopo.json", OUT / "raw_motion_features.csv"]
    result = {"status": status, "errors": errors, "source_directories": len(source_dirs), "processed_directories": len(result_dirs), "checked_artifacts": len(required), "optional_raw_motion_artifacts_present": all(p.exists() for p in optional)}
    (OUT / "release_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors: raise SystemExit(1)


if __name__ == "__main__": main()
