"""
Compare the first 10-second window parsed from datacube.bin
against sub-SXQ_mmwave_datacube_part001.npz.

Run this inside the user's working conda environment, for example:
python debug_bin_vs_part001.py
"""

from pathlib import Path

import numpy as np

from check_bin_sliding_quality_v5 import HEADER_SIZE, FRAME_SIZE, parse_window_bytes
from process_vital_signs_v2 import load_data, range_fft, select_bins


BASE = Path(r"D:\北师珠学杂\课外项目\厚粲")
BIN_PATH = BASE / "mmwave" / "sub-SXQ_mmwave.datacube.bin"
PART_PATH = BASE / "mmwave" / "sub-SXQ_mmwave_datacube_part001.npz"
OUT_PATH = BASE / "08_算法" / "results_v5" / "bin_windows" / "debug_bin_vs_part001.txt"


def summarize_iq(name: str, iq: np.ndarray):
    lines = []
    lines.append(f"[{name}]")
    lines.append(f"shape: {iq.shape}")
    lines.append(f"dtype: {iq.dtype}")
    lines.append(f"abs mean: {float(np.abs(iq).mean()):.6f}")
    lines.append(f"abs std : {float(np.abs(iq).std()):.6f}")
    lines.append(f"first sample ch0: {iq[0, 0, 0]}")
    lines.append("")
    return lines


def main():
    part_iq = load_data(PART_PATH)

    with BIN_PATH.open("rb") as f:
        f.seek(HEADER_SIZE)
        raw = f.read(FRAME_SIZE * 1000)
    bin_iq = parse_window_bytes(raw)

    lines = []
    lines.extend(summarize_iq("part001 npz", part_iq))
    lines.extend(summarize_iq("bin first 1000 frames", bin_iq))

    same_shape = part_iq.shape == bin_iq.shape
    lines.append(f"same shape: {same_shape}")

    if same_shape:
        diff = np.abs(part_iq - bin_iq)
        lines.append(f"allclose exact: {np.allclose(part_iq, bin_iq)}")
        lines.append(f"mean abs diff: {float(diff.mean()):.6f}")
        lines.append(f"max abs diff : {float(diff.max()):.6f}")
        lines.append(f"first 5x5x2 allclose: {np.allclose(part_iq[:5, :5, :2], bin_iq[:5, :5, :2])}")
        lines.append("")

    try:
        part_fd = range_fft(part_iq)
        part_bins = select_bins(part_fd, part_fd.shape[0])
        lines.append(f"part001 bins: best_ch={part_bins[0]}, br_bin={part_bins[1]}, hr_bin={part_bins[2]}")
    except Exception as exc:
        lines.append(f"part001 bins failed: {type(exc).__name__}: {exc}")

    try:
        bin_fd = range_fft(bin_iq)
        bin_bins = select_bins(bin_fd, bin_fd.shape[0])
        lines.append(f"bin first-1000 bins: best_ch={bin_bins[0]}, br_bin={bin_bins[1]}, hr_bin={bin_bins[2]}")
    except Exception as exc:
        lines.append(f"bin first-1000 bins failed: {type(exc).__name__}: {exc}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT_PATH}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
