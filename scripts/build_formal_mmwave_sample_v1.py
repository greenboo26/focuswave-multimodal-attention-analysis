"""Build a small de-identified formal mmWave structure sample.

The source directory is supplied at runtime and is never copied wholesale.
Only selected frame rows and relative timestamps are exported.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


KEYS = [
    "tx0_rx0", "tx0_rx1", "tx0_rx2", "tx0_rx3",
    "tx1_rx0", "tx1_rx1", "tx1_rx2", "tx1_rx3",
]
FRAME_PAYLOAD_BYTES = 8 * 256 * 4
FRAME_RECORD_BYTES = 12 + FRAME_PAYLOAD_BYTES


def read_timestamps(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter=",", dtype=np.int64)


def load_frame_slice(source: Path, start: int, stop: int) -> dict[str, np.ndarray]:
    files = sorted(source.glob("*_datacube_part*.npz"))
    if not files:
        raise FileNotFoundError(f"No part NPZ files under {source}")
    out = {key: [] for key in KEYS}
    cursor = 0
    for path in files:
        with np.load(path, allow_pickle=False) as z:
            n = z[KEYS[0]].shape[0]
            left = max(start - cursor, 0)
            right = min(stop - cursor, n)
            if left < right:
                for key in KEYS:
                    out[key].append(np.asarray(z[key][left:right]))
            cursor += n
            if cursor >= stop:
                break
    if any(not parts for parts in out.values()):
        raise RuntimeError(f"Could not extract [{start}, {stop}) from {source}")
    return {key: np.concatenate(parts, axis=0) for key, parts in out.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-frame", type=int, required=True)
    parser.add_argument("--stop-frame", type=int, required=True)
    parser.add_argument("--sample-alias", default="formal_qc_subject_a")
    args = parser.parse_args()

    src = args.source_dir
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    ts_path = next(src.glob("*_timestamps.csv"))
    timestamps = read_timestamps(ts_path)
    if not (0 <= args.start_frame < args.stop_frame <= len(timestamps)):
        raise ValueError("requested frame range is outside the timestamp table")

    arrays = load_frame_slice(src, args.start_frame, args.stop_frame)
    for i, (left, right) in enumerate([(0, 5940), (5940, 11880), (11880, args.stop_frame - args.start_frame)], 1):
        if right <= left:
            continue
        chunk = {key: value[left:right] for key, value in arrays.items()}
        np.savez_compressed(out / f"mmwave_part_{i:03d}_60s.npz", **chunk)

    selected_ts = timestamps[args.start_frame:args.stop_frame].copy()
    relative = selected_ts.copy()
    relative[:, 0] -= relative[0, 0]
    relative[:, 1:] -= relative[0, 1:]
    with (out / "timestamps_relative.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame_index_relative", "timestamp_column_1_relative_ms", "timestamp_column_2_relative_ms"])
        writer.writerows(relative.tolist())

    meta_path = next(src.glob("*.meta.json"), None)
    source_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path else {}
    sanitized_meta = {
        "sample_alias": args.sample_alias,
        "source_subject_id_removed": True,
        "selected_frame_count": int(args.stop_frame - args.start_frame),
        "frame_range_in_source_removed": True,
        "fps": source_meta.get("fps"),
        "tx_ant": source_meta.get("tx_ant", 2),
        "rx_ant": source_meta.get("rx_ant", 4),
        "range_fft": source_meta.get("range_fft", 256),
        "doppler_fft": source_meta.get("doppler_fft", 32),
        "npz_keys": KEYS,
        "npz_dtype": "complex128",
        "npz_shape_per_chunk": "(frames, 256)",
        "timestamp_semantics": "three source columns retained only as relative values; source column names were absent",
        "absolute_timestamps_removed": True,
    }
    (out / "metadata_sanitized.json").write_text(json.dumps(sanitized_meta, indent=2), encoding="utf-8")

    bin_path = next(src.glob("*.datacube.bin"), None)
    if bin_path:
        with bin_path.open("rb") as handle:
            handle.seek(32 + args.start_frame * FRAME_RECORD_BYTES)
            raw = handle.read(32 + 2 * FRAME_RECORD_BYTES)
        (out / "raw_frame_sample.bin").write_bytes(raw)

    manifest = {
        "sample_alias": args.sample_alias,
        "selected_duration_approx_s": round((args.stop_frame - args.start_frame) / float(source_meta.get("fps", 99.0)), 3),
        "chunks": 3,
        "source_path_not_recorded": True,
        "source_subject_id_not_recorded": True,
        "source_absolute_timestamps_not_recorded": True,
        "purpose": "public structure-reading sample only; not a formal analysis result",
    }
    (out / "sample_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
