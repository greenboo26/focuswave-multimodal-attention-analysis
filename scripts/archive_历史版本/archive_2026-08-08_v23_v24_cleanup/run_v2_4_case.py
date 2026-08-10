"""
Launcher for the v2.4 long-record mmWave pipeline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from process_vital_signs_v2_4 import analyze_long_record


SCRIPT_DIR = Path(__file__).resolve().parent
ALG_DIR = SCRIPT_DIR.parent
PROJECT_DIR = ALG_DIR.parent

DEFAULT_PARTS_DIR = PROJECT_DIR / "mmwave"
DEFAULT_OUTPUT_DIR = ALG_DIR / "results_v2_4" / "sxq_47min" / "v2.4"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v2.4 chunked long-record pipeline")
    parser.add_argument("--parts-dir", type=Path, default=DEFAULT_PARTS_DIR, help="Directory containing part*.npz chunks")
    parser.add_argument("--pattern", default="sub-SXQ_mmwave_datacube_part*.npz", help="Filename glob for chunk files")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for json/npz/png outputs")
    parser.add_argument("--session", default="sub-sxq_ses-SART", help="Session name written into the outputs")
    parser.add_argument("--method", choices=["bp", "vmd_heart"], default="vmd_heart", help="Heart extraction branch")
    parser.add_argument("--breath-view-start-s", type=float, default=None, help="Breath panel / FFT view start time in seconds")
    parser.add_argument("--channel-override", type=int, default=None, help="Force one virtual channel index (0-7)")
    parser.add_argument("--min-range-m", type=float, default=0.3, help="Minimum distance gate in meters")
    parser.add_argument("--max-range-m", type=float, default=1.5, help="Maximum distance gate in meters")
    parser.add_argument("--bin-spacing-m", type=float, default=0.08, help="Distance per range bin in meters")
    parser.add_argument("--range-bias-m", type=float, default=0.0, help="Distance bias correction in meters")
    args = parser.parse_args()

    result, _ = analyze_long_record(
        parts_dir=args.parts_dir,
        output_dir=args.output_dir,
        session=args.session,
        method=args.method,
        pattern=args.pattern,
        breath_view_start_s=args.breath_view_start_s,
        channel_override=args.channel_override,
        min_range_m=args.min_range_m,
        max_range_m=args.max_range_m,
        bin_spacing_m=args.bin_spacing_m,
        range_bias_m=args.range_bias_m,
    )

    print(f"session: {result['session']}")
    print(f"version: {result['version']}")
    print(f"method: {result['method']}")
    print(f"duration_s: {result['duration_s']}")
    print(f"HR freq/time: {result['heart_rate']['freq_bpm']} / {result['heart_rate']['time_bpm']} BPM")
    print(f"BR freq/time: {result['breath_rate']['freq_bpm']} / {result['breath_rate']['time_bpm']} BPM")
    print(f"BR confidence: {result['breath_rate'].get('confidence')}")
    print(f"BR quality: {result.get('breath_quality', {}).get('label')} / {result.get('breath_quality', {}).get('score')}")
    channels = result.get("channels", {})
    dist = result.get("distance_axis", {})
    fusion = result.get("breath_fusion", {})
    print(
        f"bins/channels: br_ch={channels.get('breath', result['best_channel'])}, "
        f"hr_ch={channels.get('heart', result['best_channel'])}, "
        f"auto_ch={result.get('auto_best_channel')}, "
        f"br_bin={result['bins']['breath']}, hr_bin={result['bins']['heart']}"
    )
    print(
        f"distance: br={dist.get('breath_distance_m')} m, "
        f"hr={dist.get('heart_distance_m')} m, "
        f"gate=[{dist.get('min_range_m')}, {dist.get('max_range_m')}] m, "
        f"bin_spacing={dist.get('bin_spacing_m')} m"
    )
    print(f"fusion bins: {fusion.get('candidate_bins')}")


if __name__ == "__main__":
    main()
