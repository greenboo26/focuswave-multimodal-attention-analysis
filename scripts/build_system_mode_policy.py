"""Build an evidence-bound mode policy for the FocusWave runtime."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def main() -> None:
    summary = json.loads((OUT / "final_summary.json").read_text(encoding="utf-8"))
    base = json.loads((OUT / "personalized_temporal_runtime_expanded.json").read_text(encoding="utf-8"))
    behavior = json.loads((OUT / "personalized_temporal_runtime_behavior.json").read_text(encoding="utf-8"))
    visual = json.loads((OUT / "augmented_vitals_enhanced_visual_lopo.json").read_text(encoding="utf-8"))
    policy = {
        "system": "FocusWave mmWave attention research system",
        "status": "research_prototype_not_deployment_validated",
        "time_gate": {
            "required": True,
            "rule": "Only behavior-defined windows fully inside valid SART blocks are eligible; pre/post, practice and rest are excluded.",
        },
        "modes": [
            {
                "id": "physiology_quality_only",
                "default": True,
                "inputs": ["mmWave NPZ", "behavior-gated window timestamps"],
                "outputs": ["heart rate", "breath rate raw/corrected with quality and harmonic-correction flag", "exploratory HRV with quality"],
                "attention_decision": "indeterminate unless explicitly using research scoring",
                "evidence": "output/E_Data_FAST/final_summary.json",
            },
            {
                "id": "personalized_mmwave",
                "default": False,
                "inputs": ["mmWave features", "first-half subject labels for calibration"],
                "protocol": "first half calibration, second half independent scoring",
                "coverage": base["mmwave_rgb_nir"]["n_scored_subjects"],
                "attention_auc_focus_vs_mw": base["mmwave_rgb_nir"]["evaluations"]["focus_vs_mind_wandering"]["auc"],
                "warning": "Exploratory and limited to subjects with sufficient calibration labels.",
                "evidence": "output/E_Data_FAST/personalized_temporal_runtime_expanded.json",
            },
            {
                "id": "behavior_assisted_multimodal",
                "default": False,
                "inputs": ["mmWave features", "RGB/NIR proxies", "SART features from prior 60 seconds"],
                "protocol": "first half calibration, second half independent scoring",
                "coverage": behavior["mmwave_rgb_nir_behavior"]["n_scored_subjects"],
                "attention_auc_focus_vs_mw": behavior["mmwave_rgb_nir_behavior"]["evaluations"]["focus_vs_mind_wandering"]["auc"],
                "subject_bootstrap_auc_95_ci": [behavior["mmwave_rgb_nir_behavior"]["evaluations"]["focus_vs_mind_wandering"]["subject_bootstrap"]["auc_2.5_50_97.5"][0], behavior["mmwave_rgb_nir_behavior"]["evaluations"]["focus_vs_mind_wandering"]["subject_bootstrap"]["auc_2.5_50_97.5"][2]],
                "warning": "This is behavior-assisted multimodal performance, not pure mmWave performance.",
                "evidence": "output/E_Data_FAST/personalized_temporal_runtime_behavior.json",
            },
            {
                "id": "visual_geometry_exploration",
                "default": False,
                "inputs": ["RGB face geometry proxy", "NIR pupil geometry proxy"],
                "attention_auc_focus_vs_mw": visual["analyses"]["focus_vs_mw"]["enhanced_visual"]["auc"],
                "warning": "Not enabled by default because it did not improve the current cross-subject result.",
                "evidence": "output/E_Data_FAST/augmented_vitals_enhanced_visual_lopo.json",
            },
        ],
        "current_data": {
            "complete_subjects": summary["complete_subjects"],
            "probe_windows": summary["probe_windows"],
            "heart_rate_extractable_subjects": summary["quality"]["hr_n"],
            "breath_rate_in_exploratory_range_subjects": summary["quality"]["br_12_25"],
        },
        "scientific_boundary": "A generalizable cross-subject mmWave attention classifier is not established by the current data.",
    }
    path = OUT / "system_mode_policy.json"
    path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(path), "modes": len(policy["modes"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
