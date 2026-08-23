"""Refresh the complete FocusWave mmWave analysis after adding data."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
DATA = Path(r"E:\Data")
OUT = ROOT / "output" / "E_Data_FAST"


def run(cmd, env):
    print("[pipeline]", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, env=env, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-extraction", action="store_true", help="reuse existing vital-sign outputs")
    ap.add_argument("--skip-rich", action="store_true", help="skip the slower rich-feature audit")
    ap.add_argument("--skip-external", action="store_true", help="reuse the external AgeBalanced physiology audit")
    ap.add_argument("--skip-formal", action="store_true", help="reuse existing formal-experiment summaries")
    ap.add_argument("--raw-motion", action="store_true", help="run the slow raw phase/motion audit")
    args = ap.parse_args()
    env = os.environ.copy(); env["E_DATA_ROOT"] = str(DATA); env["E_DATA_OUT_ROOT"] = str(OUT); env["E_DATA_METHOD"] = "bp_heart"; env["PYTHONIOENCODING"] = "utf-8"
    py = Path(sys.executable)
    subs = sorted(d.name.replace("sub-", "").rstrip("_") for d in DATA.glob("sub-*_"))
    if not args.skip_extraction:
        run([py, ROOT / "scripts" / "run_e_data_batch_fast.py", *subs], env)
    completed = sorted(d.name.replace("sub-", "").rstrip("_") for d in OUT.glob("sub-*_" ) if list(d.glob("*_vital_signs.npz")))
    run([py, ROOT / "output" / "06_正式实验" / "E_Data" / "analyze_e_data_focus.py", "--subjects", *completed], env)
    augmented = OUT / "focus_discrimination_augmented.csv"
    run([py, ROOT / "scripts" / "augment_window_vital_features.py",
         "--csv", OUT / "focus_discrimination.csv",
         "--output", augmented,
         "--npz-root", OUT], env)
    run([py, ROOT / "scripts" / "evaluate_focus_csv_lopo.py", OUT / "focus_discrimination.csv", OUT / "focus_lopo.json"], env)
    run([py, ROOT / "scripts" / "summarize_e_final.py"], env)
    run([py, ROOT / "scripts" / "evaluate_runtime_focus_system.py"], env)
    run([py, ROOT / "scripts" / "run_focus_runtime_batch.py",
         OUT,
         OUT / "behavior_gated_runtime_all",
         "--windows-csv", OUT / "focus_discrimination.csv"], env)
    if not args.skip_rich:
        run([py, ROOT / "scripts" / "evaluate_rich_focus_features.py"], env)
        run([py, ROOT / "scripts" / "evaluate_within_subject_focus.py"], env)
        run([py, ROOT / "scripts" / "evaluate_personalized_temporal.py"], env)
    run([py, ROOT / "scripts" / "audit_label_coverage.py"], env)
    run([py, ROOT / "scripts" / "audit_behavior_outcomes.py"], env)
    augmented_cmd = [py, ROOT / "scripts" / "evaluate_augmented_vitals_lopo.py",
                     "--vitals", augmented,
                     "--behavior", OUT / "behavior_probe_windows.csv",
                     "--output", OUT / "augmented_vitals_lopo.json"]
    if (OUT / "crossmodal_features_all.csv").exists():
        augmented_cmd.extend(["--crossmodal", OUT / "crossmodal_features_all.csv"])
    run(augmented_cmd, env)
    run([py, ROOT / "scripts" / "evaluate_behavior_supervised_lopo.py",
         "--mmwave", OUT / "focus_discrimination.csv",
         "--behavior", OUT / "behavior_probe_windows.csv",
         "--crossmodal", OUT / "crossmodal_features_all.csv",
         "--output", OUT / "behavior_supervised_lopo.json"], env)
    run([py, ROOT / "scripts" / "evaluate_mmwave_behavior_criterion.py"], env)
    run([py, ROOT / "scripts" / "evaluate_mmwave_behavior_fusion.py"], env)
    run([py, ROOT / "scripts" / "audit_crossmodal_time_gate.py"], env)
    crossmodal_csv = OUT / "crossmodal_features_all.csv"
    if crossmodal_csv.exists():
        model_dir = OUT / "personalized_models_validated"
        run([py, ROOT / "scripts" / "evaluate_crossmodal_fusion.py",
             "--mmwave", OUT / "focus_discrimination.csv",
             "--crossmodal", crossmodal_csv,
             "--output", OUT / "crossmodal_fusion_lopo.json"], env)
        run([py, ROOT / "scripts" / "evaluate_crossmodal_temporal.py",
             "--mmwave", OUT / "focus_discrimination.csv",
             "--crossmodal", crossmodal_csv,
             "--output", OUT / "crossmodal_temporal_lopo.json"], env)
        run([py, ROOT / "scripts" / "evaluate_crossmodal_within_subject.py",
             "--mmwave", OUT / "focus_discrimination.csv",
             "--crossmodal", crossmodal_csv,
             "--output", OUT / "crossmodal_within_subject_lopo.json"], env)
        run([py, ROOT / "scripts" / "personalized_temporal_runtime.py",
             "--mmwave", augmented,
             "--crossmodal", crossmodal_csv,
             "--output", OUT / "personalized_temporal_runtime.json"], env)
        run([py, ROOT / "scripts" / "personalized_temporal_runtime.py",
             "--mmwave", augmented,
             "--crossmodal", crossmodal_csv,
             "--expanded-vitals",
             "--output", OUT / "personalized_temporal_runtime_expanded.json"], env)
        run([py, ROOT / "scripts" / "personalized_temporal_runtime.py",
             "--mmwave", augmented,
             "--crossmodal", crossmodal_csv,
             "--behavior", OUT / "behavior_probe_windows.csv",
             "--behavior-assisted", "--expanded-vitals",
             "--model-dir", model_dir,
             "--output", OUT / "personalized_temporal_runtime_behavior.json"], env)
        run([py, ROOT / "scripts" / "score_personalized_models.py",
             "--features", augmented,
             "--crossmodal", crossmodal_csv,
             "--behavior", OUT / "behavior_probe_windows.csv",
             "--models", model_dir,
             "--mode", "mmwave_rgb_nir_behavior",
             "--output", OUT / "personalized_scores_validated_behavior.json"], env)
        # Also score models that do not receive behavior features.  These are
        # the relevant research modes for a future online mmWave/RGB/NIR
        # runtime; behavior-assisted results remain an upper-bound audit.
        run([py, ROOT / "scripts" / "score_personalized_models.py",
             "--features", augmented,
             "--crossmodal", crossmodal_csv,
             "--models", model_dir,
             "--mode", "mmwave",
             "--output", OUT / "personalized_scores_mmwave.json"], env)
        run([py, ROOT / "scripts" / "score_personalized_models.py",
             "--features", augmented,
             "--crossmodal", crossmodal_csv,
             "--models", model_dir,
             "--mode", "mmwave_rgb_nir",
             "--output", OUT / "personalized_scores_mmwave_rgb_nir.json"], env)
    if not args.skip_formal:
        # Formal experiment is a separate protocol layer.  It contributes
        # behavior and exploratory physiology summaries, but is not pooled
        # into the main E_Data training cohort.
        run([py, ROOT / "scripts" / "analyze_formal_behavior.py"], env)
        run([py, ROOT / "scripts" / "analyze_formal_cross_subject.py"], env)
        run([py, ROOT / "scripts" / "analyze_formal_probe_centric.py"], env)
    run([py, ROOT / "scripts" / "audit_100_subject_target.py"], env)
    run([py, ROOT / "scripts" / "audit_source_inventory.py"], env)
    run([py, ROOT / "scripts" / "audit_source_evidence.py"], env)
    run([py, ROOT / "scripts" / "build_system_mode_policy.py"], env)
    if not args.skip_external:
        run([py, ROOT / "scripts" / "validate_external_agebalanced.py"], env)
    # Refresh the independent BIOPAC ECG/RSP reference layer before the
    # project audit.  Its windows are behavior-timestamp gated and never
    # become attention-model inputs.
    run([py, ROOT / "scripts" / "analyze_acq_reference.py"], env)
    env["ACQ_MMWAVE_ROOT"] = str(ROOT / "output" / "ACQ_mmwave_FAST")
    run([py, ROOT / "scripts" / "compare_mmwave_reference.py",
         "--window-s", "60",
         "--output", ROOT / "output" / "ACQ_reference_20260821" / "mmwave_vs_reference_probes_60s.csv"], env)
    run([py, ROOT / "scripts" / "evaluate_acq_breath_methods.py",
         "--reference", ROOT / "output" / "ACQ_reference_20260821" / "reference_metrics.json",
         "--npz-root", ROOT / "output" / "ACQ_mmwave_FAST",
         "--output", ROOT / "output" / "ACQ_reference_20260821" / "breath_method_comparison_current.json"], env)
    run([py, ROOT / "scripts" / "evaluate_breath_harmonic_correction.py"], env)
    # Keep the historical filename for downstream consumers while the report
    # is built from the current strict comparison output.
    run([py, ROOT / "scripts" / "build_acq_reference_validation_report.py"], env)
    run([py, ROOT / "scripts" / "audit_acq_signal_quality.py"], env)
    if args.raw_motion:
        run([py, ROOT / "scripts" / "evaluate_raw_motion_features.py"], env)
    run([py, ROOT / "scripts" / "audit_project_completion.py"], env)
    run([py, ROOT / "scripts" / "verify_system_release.py"], env)
    print(f"[pipeline] complete: {len(completed)} processed subjects", flush=True)


if __name__ == "__main__": main()
