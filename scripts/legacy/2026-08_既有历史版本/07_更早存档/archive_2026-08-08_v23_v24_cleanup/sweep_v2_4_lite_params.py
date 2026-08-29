from __future__ import annotations

import csv
from pathlib import Path

from process_vital_signs_v2_4_lite import analyze_long_record


SCRIPT_DIR = Path(__file__).resolve().parent
ALG_DIR = SCRIPT_DIR.parent
PROJECT_DIR = ALG_DIR.parent

PARTS_DIR = PROJECT_DIR / "sub-rest_3min_" / "mmwave"
PATTERN = "sub-rest_3min_mmwave_datacube_part*.npz"
BASE_OUTPUT_DIR = ALG_DIR / "results_v2_4" / "sweep_v24_lite_rest3min"

HP_VALUES = [0.02, 0.025, 0.03]
STEP_VALUES = [10.0, 12.0, 15.0]


def main() -> None:
    BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for hp in HP_VALUES:
        for step_z in STEP_VALUES:
            tag = f"hp{str(hp).replace('.', 'p')}_step{str(step_z).replace('.', 'p')}"
            output_dir = BASE_OUTPUT_DIR / tag
            session = f"sub-rest_3min_{tag}"
            print(f"[run] {tag}")

            result, _ = analyze_long_record(
                parts_dir=PARTS_DIR,
                output_dir=output_dir,
                session=session,
                method="vmd_heart",
                pattern=PATTERN,
                breath_view_start_s=60.0,
                hp_cutoff_hz=hp,
                step_z_threshold=step_z,
            )

            breath_rate = result.get("breath_rate", {})
            breath_quality = result.get("breath_quality", {})
            fusion = result.get("breath_fusion", {})
            windows = result.get("breath_windows", {})
            gap = None
            if breath_rate.get("freq_bpm") is not None and breath_rate.get("time_bpm") is not None:
                gap = abs(float(breath_rate["freq_bpm"]) - float(breath_rate["time_bpm"]))

            rows.append(
                {
                    "tag": tag,
                    "hp_cutoff_hz": hp,
                    "step_z_threshold": step_z,
                    "br_freq_bpm": breath_rate.get("freq_bpm"),
                    "br_time_bpm": breath_rate.get("time_bpm"),
                    "br_gap_bpm": round(gap, 3) if gap is not None else None,
                    "br_confidence": breath_rate.get("confidence"),
                    "quality_label": breath_quality.get("label"),
                    "quality_score": breath_quality.get("score"),
                    "usable_window_ratio": breath_quality.get("usable_window_ratio"),
                    "neighbor_freq_std_bpm": breath_quality.get("neighbor_freq_std_bpm"),
                    "sliding_br_std_bpm": breath_quality.get("sliding_br_std_bpm"),
                    "center_freq_bpm": fusion.get("center_freq_bpm"),
                    "n_usable_windows": windows.get("n_usable_windows"),
                    "output_dir": str(output_dir),
                }
            )

    summary_path = BASE_OUTPUT_DIR / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"[summary] {summary_path}")


if __name__ == "__main__":
    main()


