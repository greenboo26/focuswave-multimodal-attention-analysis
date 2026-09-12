"""Read-only audit of the frozen FocusWave 180 s mmWave resting baseline.

This script does not modify the formal producer and does not implement a
baseline-personalized selector.  It describes availability, clock/frame QC,
and the behavior of the current selector in six audit-only 30 s slices.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def read_sessions(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    sessions = sorted({row["session_id"] for row in rows})
    keys = {(r["repeat_participant_id"], r["session_id"], r["block_id"], r["probe_id"], r["window_name"]) for r in rows}
    if len(keys) != len(rows):
        raise ValueError(f"non-unique frozen keys: {path}")
    return sessions


def baseline_markers(path: Path) -> tuple[int, int, float]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    starts = [r for r in rows if r.get("event") == "baseline_start"]
    stops = [r for r in rows if r.get("event") == "baseline_stop"]
    if len(starts) != 1 or len(stops) != 1:
        raise ValueError(f"baseline_marker_count:{len(starts)}/{len(stops)}")
    match = re.search(r"duration=([0-9.]+)s", stops[0].get("detail", ""))
    if not match:
        raise ValueError("baseline_stop_duration_missing")
    return int(starts[0]["unix_ms"]), int(stops[0]["unix_ms"]), float(match.group(1))


class IndexedCube:
    """Index chunk headers once and decompress only requested frame ranges."""

    def __init__(self, files: list[Path], timestamp_count: int):
        self.entries = []
        self._cache_key = None
        self._cache_value = None
        cursor = 0
        expected_keys = None
        for path in files:
            shapes = {}
            with zipfile.ZipFile(path) as z:
                for name in sorted(z.namelist()):
                    if not name.startswith("tx") or not name.endswith(".npy"):
                        continue
                    with z.open(name) as f:
                        version = np.lib.format.read_magic(f)
                        if version == (1, 0):
                            shape, _, _ = np.lib.format.read_array_header_1_0(f)
                        elif version == (2, 0):
                            shape, _, _ = np.lib.format.read_array_header_2_0(f)
                        else:
                            raise ValueError(f"unsupported_npy_header:{version}")
                    shapes[name[:-4]] = shape
            keys = tuple(shapes)
            if not keys or (expected_keys is not None and keys != expected_keys):
                raise ValueError("inconsistent_cube_channels")
            expected_keys = keys
            n = int(shapes[keys[0]][0])
            if any(shape != shapes[keys[0]] for shape in shapes.values()):
                raise ValueError("channel_shape_mismatch")
            self.entries.append((path, cursor, cursor + n, keys))
            cursor += n
        if cursor != timestamp_count:
            raise ValueError(f"npz_timestamp_count_mismatch:{cursor}/{timestamp_count}")

    def slice(self, start: int, end: int) -> np.ndarray:
        key = (int(start), int(end))
        if key == self._cache_key:
            return self._cache_value
        chunks = []
        for path, lo, hi, keys in self.entries:
            if hi <= start:
                continue
            if lo >= end:
                break
            with np.load(path) as data:
                chunks.append(np.stack([data[k][max(0, start-lo):min(hi-lo, end-lo)] for k in keys], axis=-1).astype(np.complex64))
        if not chunks:
            raise ValueError("empty_cube_slice")
        value = np.concatenate(chunks)
        if len(value) != end - start:
            raise ValueError(f"incomplete_cube_slice:{len(value)}/{end-start}")
        self._cache_key, self._cache_value = key, value
        return value


def finite(value):
    if value is None:
        return None
    x = float(value)
    return x if np.isfinite(x) else None


def selector_diagnostics(algo, iq: np.ndarray) -> dict:
    iq_fd = algo._as_range_cube(iq)
    power = np.mean(np.abs(iq_fd) ** 2, axis=0)
    br_ch, br_bin, hr_ch, hr_bin, summaries = algo.select_separate_channels_bins(power, iq_fd, len(iq_fd))
    all_hr = []
    all_br = []
    for ch in range(power.shape[1]):
        _, _, candidates = algo.select_bins_from_profile(power, ch, iq_fd, len(iq_fd))
        all_hr.extend((float(item[5]), ch, int(item[0]), float(item[1]), float(item[4])) for item in candidates)
        all_br.extend((float(item[3]), ch, int(item[0]), float(item[2]), float(item[4])) for item in candidates)
    all_hr.sort(reverse=True)
    all_br.sort(reverse=True)
    best_hr = all_hr[0]
    best_br = all_br[0]
    if (best_hr[1], best_hr[2]) != (hr_ch, hr_bin) or (best_br[1], best_br[2]) != (br_ch, br_bin):
        raise RuntimeError("selector_diagnostic_identity_mismatch")
    hr_margin = best_hr[0] - all_hr[1][0] if len(all_hr) > 1 else None
    br_margin = best_br[0] - all_br[1][0] if len(all_br) > 1 else None
    target_power = float(power[hr_bin, hr_ch])
    positive = power[:, hr_ch][power[:, hr_ch] > 0]
    power_contrast_db = 10.0 * np.log10(target_power / float(np.median(positive))) if len(positive) and target_power > 0 else None
    return {
        "hr_selected_channel": hr_ch,
        "hr_selected_bin": hr_bin,
        "br_selected_channel": br_ch,
        "br_selected_bin": br_bin,
        "hr_selection_score": best_hr[0],
        "hr_selection_margin": hr_margin,
        "hr_selector_snr": best_hr[3],
        "hr_phase_stability": best_hr[4],
        "br_selection_score": best_br[0],
        "br_selection_margin": br_margin,
        "br_selector_snr": best_br[3],
        "br_phase_stability": best_br[4],
        "hr_target_power_mean": target_power,
        "hr_target_power_contrast_db": power_contrast_db,
        "selector_channel_summaries": len(summaries),
    }


def session_stability(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["window_status"] == "OBSERVED"]
    if not valid:
        return {}
    pairs = [(int(r["hr_selected_channel"]), int(r["hr_selected_bin"])) for r in valid]
    bins = [p[1] for p in pairs]
    channels = [p[0] for p in pairs]
    pair_mode, pair_n = Counter(pairs).most_common(1)[0]
    bin_mode, bin_n = Counter(bins).most_common(1)[0]
    ch_mode, ch_n = Counter(channels).most_common(1)[0]
    longest = run = 0
    for pair in pairs:
        run = run + 1 if pair == pair_mode else 0
        longest = max(longest, run)
    return {
        "audit_windows_observed": len(valid),
        "hr_modal_channel": ch_mode,
        "hr_modal_bin": bin_mode,
        "hr_modal_pair_channel": pair_mode[0],
        "hr_modal_pair_bin": pair_mode[1],
        "hr_channel_persistence": ch_n / len(valid),
        "hr_bin_persistence": bin_n / len(valid),
        "hr_pair_persistence": pair_n / len(valid),
        "hr_unique_pairs": len(set(pairs)),
        "hr_median_abs_bin_deviation_from_mode": float(np.median(np.abs(np.asarray(bins) - bin_mode))),
        "hr_longest_modal_pair_run": longest,
    }


def write_csv(path: Path, rows: list[dict]):
    fields = sorted({k for row in rows for k in row})
    with path.open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--j-table", type=Path, required=True)
    parser.add_argument("--e-table", type=Path, required=True)
    parser.add_argument("--j-root", type=Path, required=True)
    parser.add_argument("--e-root", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--acquisition-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sessions", nargs="*")
    args = parser.parse_args()

    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    expected = {"J": (args.j_table, args.j_root, 72), "E": (args.e_table, args.e_root, 44)}
    selected = set(args.sessions or [])
    cohort = []
    for batch, (table, root, count) in expected.items():
        sessions = read_sessions(table)
        if len(sessions) != count:
            raise ValueError(f"{batch}_frozen_session_count:{len(sessions)}/{count}")
        cohort.extend((batch, session, root) for session in sessions if not selected or session in selected)
    if selected - {s for _, s, _ in cohort}:
        raise ValueError("requested_session_outside_frozen_cohort")

    adapter = load_module(args.adapter, "baseline_audit_adapter")
    algo = load_module(args.producer, "baseline_audit_producer")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    per_session, per_window, source_inputs = [], [], []
    original_slice = adapter.slice_iq
    for batch, session, root in cohort:
        item = {"batch": batch, "session_id": session}
        session_root = root / f"{session}_"
        timeline = session_root / "beh" / "master_timeline.csv"
        mmwave = session_root / "mmwave"
        item.update(timeline_path=str(timeline), mmwave_path=str(mmwave))
        try:
            marker_start, marker_stop, logged_duration_s = baseline_markers(timeline)
            inferred_start = int(round(marker_stop - logged_duration_s * 1000.0))
            item.update(
                timeline_available=True,
                marker_start_unix_ms=marker_start,
                marker_stop_unix_ms=marker_stop,
                marker_envelope_ms=marker_stop-marker_start,
                marker_envelope_excess_over_logged_ms=marker_stop-marker_start-logged_duration_s*1000.0,
                logged_rest_duration_s=logged_duration_s,
                inferred_rest_start_unix_ms=inferred_start,
                rest_start_semantics="INFERRED_FROM_BASELINE_STOP_MINUS_ROUNDED_LOGGED_DURATION",
            )
            source_inputs.append({"path": str(timeline), "sha256": sha256(timeline)})
        except Exception as exc:
            item.update(timeline_available=False, session_status="STRUCTURAL_MISSING", failure_reason=f"timeline:{type(exc).__name__}:{exc}")
            per_session.append(item)
            print(f"{batch} {session}: {item['failure_reason']}", flush=True)
            continue
        try:
            timestamps = adapter.load_timestamps(mmwave)
            alignment = adapter.alignment_timestamps(timestamps)
            if len(alignment) < 2 or np.any(np.diff(alignment) < 0) or np.any(np.diff(timestamps[:, 0]) <= 0):
                raise ValueError("nonmonotonic_timestamp_or_frame_id")
            files = adapter.load_npz_files(mmwave, session)
            cube = IndexedCube(files, len(timestamps))
            ts_path = next(mmwave.glob("*_mmwave_timestamps.csv"))
            source_inputs.append({"path": str(ts_path), "sha256": sha256(ts_path)})
            item.update(timestamp_path=str(ts_path), timestamp_rows=len(timestamps), npz_parts=len(files))
        except Exception as exc:
            item.update(session_status="STRUCTURAL_MISSING", failure_reason=f"mmwave:{type(exc).__name__}:{exc}")
            per_session.append(item)
            print(f"{batch} {session}: {item['failure_reason']}", flush=True)
            continue

        lo = int(np.searchsorted(alignment, inferred_start, side="left"))
        hi = int(np.searchsorted(alignment, marker_stop, side="left"))
        selected_ts = alignment[lo:hi]
        intervals = np.diff(selected_ts)
        frame_ids = timestamps[lo:hi, 0]
        item.update(
            inferred_rest_frame_count=len(selected_ts),
            inferred_rest_first_frame_unix_ms=int(selected_ts[0]) if len(selected_ts) else None,
            inferred_rest_last_frame_unix_ms=int(selected_ts[-1]) if len(selected_ts) else None,
            inferred_rest_median_interval_ms=finite(np.median(intervals)) if len(intervals) else None,
            inferred_rest_p95_interval_ms=finite(np.percentile(intervals, 95)) if len(intervals) else None,
            inferred_rest_gap_gt20ms=int(np.count_nonzero(intervals > 20)),
            inferred_rest_gap_gt50ms=int(np.count_nonzero(intervals > 50)),
            inferred_rest_gap_gt100ms=int(np.count_nonzero(intervals > 100)),
            inferred_rest_frame_id_gap_count=int(np.count_nonzero(np.diff(frame_ids) != 1)) if len(frame_ids) > 1 else 0,
            inferred_rest_timestamp_span_ms=int(selected_ts[-1]-selected_ts[0]) if len(selected_ts) > 1 else 0,
            inferred_rest_nominal_coverage_fraction=min(1.0, len(selected_ts) / (180000.0 / np.median(intervals))) if len(intervals) and np.median(intervals) > 0 else None,
            timestamp_covers_inferred_rest=bool(len(alignment) and alignment[0] <= inferred_start and alignment[-1] >= marker_stop),
        )

        adapter.slice_iq = lambda files_arg, start, end, c=cube: c.slice(start, end)
        session_windows = []
        for window_index in range(6):
            start = inferred_start + window_index * 30000
            end = min(inferred_start + (window_index + 1) * 30000, marker_stop)
            row = {
                "session_id": session,
                "block_id": "baseline_audit",
                "window_start_unix_ms": str(start),
                "window_effective_start_unix_ms": str(start),
                "window_end_unix_ms": str(end),
            }
            out = {"batch": batch, "session_id": session, "audit_window_index": window_index + 1, "audit_window_start_unix_ms": start, "audit_window_end_unix_ms": end}
            try:
                produced = adapter.process_probe(algo, row, files, timestamps, {})
                out["window_status"] = produced.get("mmwave_state")
                out["window_failure_reason"] = produced.get("mmwave_missing_reason")
                for source, target in {
                    "mmwave_timestamp_coverage_fraction": "timestamp_coverage_fraction",
                    "mmwave_hr_freq_bpm_median": "hr_freq_bpm_median",
                    "mmwave_hr_time_bpm_median": "hr_time_bpm_median",
                    "mmwave_hr_fused_bpm_median": "hr_fused_bpm_median",
                    "mmwave_breath_rate_breaths_per_min_median": "breath_rate_bpm_median",
                    "mmwave_hr_usable_window_fraction": "hr_usable_window_fraction",
                    "mmwave_hr_mean_confidence": "hr_mean_confidence",
                    "mmwave_motion_proxy_median": "motion_proxy",
                }.items():
                    out[target] = produced.get(source)
                i0 = int(np.searchsorted(alignment, start, side="left"))
                i1 = int(np.searchsorted(alignment, end, side="left"))
                if out["window_status"] == "OBSERVED":
                    out.update(selector_diagnostics(algo, cube.slice(i0, i1)))
            except Exception as exc:
                out.update(window_status="QC_FAIL", window_failure_reason=f"{type(exc).__name__}:{exc}")
            per_window.append(out)
            session_windows.append(out)
        item.update(session_stability(session_windows))
        item["session_status"] = "OBSERVED" if item.get("audit_windows_observed") == 6 else "QC_FAIL"
        item["failure_reason"] = None if item["session_status"] == "OBSERVED" else "one_or_more_audit_windows_not_observed"
        per_session.append(item)
        print(f"{batch} {session}: {item['session_status']} windows={item.get('audit_windows_observed', 0)}/6", flush=True)

    adapter.slice_iq = original_slice
    write_csv(args.output_dir / "baseline_session_audit.csv", per_session)
    write_csv(args.output_dir / "baseline_window_diagnostics_30s_audit_only.csv", per_window)
    state_counts = dict(Counter(row["session_status"] for row in per_session))
    batch_counts = {batch: dict(Counter(r["session_status"] for r in per_session if r["batch"] == batch)) for batch in ("J", "E")}
    manifest = {
        "schema": "focuswave_mmwave_baseline_personalization_asset_audit_v1",
        "task_id": "mmwave_baseline_personalization_audit",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "audit_only_no_formal_producer_change_no_final_baseline_selector",
        "models_trained": False,
        "formal_hr_producer_modified": False,
        "final_baseline_selector_implemented": False,
        "ecg_used": False,
        "attention_labels_used": False,
        "cohort": {"sessions": len(per_session), "expected_full_sessions": 116, "batches": {"J": 72, "E": 44}},
        "state_counts": state_counts,
        "batch_state_counts": batch_counts,
        "audit_window": {"duration_s": 30, "count_per_session": 6, "role": "descriptive_partition_only_not_final_window_choice"},
        "timestamp": {"alignment_column_zero_based": 1, "semantics": "DLL host receive/enqueue Unix ms; not radar hardware frame-start time", "rest_start": "inferred from baseline_stop minus duration logged to 0.1 s because baseline_start precedes posture-confirmation input"},
        "source_commits": {
            "producer_repo_head": git_value(args.producer.parents[1], "rev-parse", "HEAD"),
            "acquisition_formaltest_head": git_value(args.acquisition_repo, "rev-parse", "HEAD"),
        },
        "source_hashes": {
            "j_frozen_table": sha256(args.j_table),
            "e_frozen_table": sha256(args.e_table),
            "producer": sha256(args.producer),
            "adapter": sha256(args.adapter),
        },
        "outputs": {},
        "input_files_hashed": source_inputs,
        "python": sys.version,
        "numpy": np.__version__,
    }
    for name in ("baseline_session_audit.csv", "baseline_window_diagnostics_30s_audit_only.csv"):
        path = args.output_dir / name
        manifest["outputs"][name] = {"sha256": sha256(path), "rows": len(per_session) if "session" in name else len(per_window)}
    manifest_path = args.output_dir / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
