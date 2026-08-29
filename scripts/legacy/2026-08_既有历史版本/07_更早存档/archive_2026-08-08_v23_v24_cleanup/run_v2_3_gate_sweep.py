"""
Batch-compare multiple distance gates for the v2.3 long-record pipeline.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from process_vital_signs_v2_3 import analyze_long_record


SCRIPT_DIR = Path(__file__).resolve().parent
ALG_DIR = SCRIPT_DIR.parent
PROJECT_DIR = ALG_DIR.parent

DEFAULT_PARTS_DIR = PROJECT_DIR / "sub-rest_3min_" / "mmwave"
DEFAULT_OUTPUT_DIR = ALG_DIR / "results_v2_3" / "gate_sweep"
DEFAULT_PATTERN = "sub-rest_3min_mmwave_datacube_part*.npz"
DEFAULT_SESSION = "sub-rest_3min_v23_sweep"


def parse_gate_specs(gate_specs: list[str]) -> list[tuple[float, float]]:
    gates: list[tuple[float, float]] = []
    for spec in gate_specs:
        parts = spec.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid gate spec: {spec}. Expected format like 0.3:1.5")
        lo = float(parts[0])
        hi = float(parts[1])
        if hi <= lo:
            raise ValueError(f"Invalid gate spec: {spec}. max must be greater than min.")
        gates.append((lo, hi))
    return gates


def gate_tag(lo: float, hi: float) -> str:
    return f"{lo:.1f}_{hi:.1f}m".replace(".", "p")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch compare multiple distance gates for v2.3")
    parser.add_argument("--parts-dir", type=Path, default=DEFAULT_PARTS_DIR, help="Directory containing part*.npz chunks")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="Filename glob for chunk files")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for sweep outputs")
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Base session name")
    parser.add_argument("--method", choices=["bp", "vmd_heart"], default="vmd_heart", help="Heart extraction branch")
    parser.add_argument("--breath-view-start-s", type=float, default=60.0, help="Breath panel / FFT view start time in seconds")
    parser.add_argument("--bin-spacing-m", type=float, default=0.08, help="Distance per range bin in meters")
    parser.add_argument("--range-bias-m", type=float, default=0.0, help="Distance bias correction in meters")
    parser.add_argument(
        "--gates",
        nargs="+",
        default=["0.3:1.5", "0.3:2.0", "0.3:2.5", "0.4:2.0"],
        help="Distance gates in min:max meter format",
    )
    args = parser.parse_args()

    gates = parse_gate_specs(args.gates)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict] = []
    for lo, hi in gates:
        tag = gate_tag(lo, hi)
        session = f"{args.session}_{tag}"
        out_dir = args.output_dir / tag
        print(f"\n=== gate {lo:.1f}-{hi:.1f} m ===")
        result, _ = analyze_long_record(
            parts_dir=args.parts_dir,
            output_dir=out_dir,
            session=session,
            method=args.method,
            pattern=args.pattern,
            breath_view_start_s=args.breath_view_start_s,
            min_range_m=lo,
            max_range_m=hi,
            bin_spacing_m=args.bin_spacing_m,
            range_bias_m=args.range_bias_m,
        )

        hr_freq = result["heart_rate"].get("freq_bpm")
        hr_time = result["heart_rate"].get("time_bpm")
        br_freq = result["breath_rate"].get("freq_bpm")
        br_time = result["breath_rate"].get("time_bpm")
        hr_gap = None if (hr_freq is None or hr_time is None) else round(abs(hr_freq - hr_time), 1)
        br_gap = None if (br_freq is None or br_time is None) else round(abs(br_freq - br_time), 1)
        channels = result.get("channels", {})
        dist = result.get("distance_axis", {})
        summary_rows.append(
            {
                "gate_min_m": lo,
                "gate_max_m": hi,
                "session": session,
                "hr_freq_bpm": hr_freq,
                "hr_time_bpm": hr_time,
                "hr_gap_bpm": hr_gap,
                "br_freq_bpm": br_freq,
                "br_time_bpm": br_time,
                "br_gap_bpm": br_gap,
                "br_confidence": result["breath_rate"].get("confidence"),
                "breath_ch": channels.get("breath"),
                "heart_ch": channels.get("heart"),
                "breath_bin": result["bins"].get("breath"),
                "heart_bin": result["bins"].get("heart"),
                "breath_distance_m": dist.get("breath_distance_m"),
                "heart_distance_m": dist.get("heart_distance_m"),
                "output_dir": str(out_dir),
            }
        )
        print(
            f"HR freq/time={hr_freq}/{hr_time} BPM, BR freq/time={br_freq}/{br_time} BPM, "
            f"bins br/hr={result['bins'].get('breath')}/{result['bins'].get('heart')}"
        )

    csv_path = args.output_dir / "gate_sweep_summary.csv"
    fieldnames = [
        "gate_min_m",
        "gate_max_m",
        "session",
        "hr_freq_bpm",
        "hr_time_bpm",
        "hr_gap_bpm",
        "br_freq_bpm",
        "br_time_bpm",
        "br_gap_bpm",
        "br_confidence",
        "breath_ch",
        "heart_ch",
        "breath_bin",
        "heart_bin",
        "breath_distance_m",
        "heart_distance_m",
        "output_dir",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\n[summary_csv] {csv_path}")


if __name__ == "__main__":
    main()


