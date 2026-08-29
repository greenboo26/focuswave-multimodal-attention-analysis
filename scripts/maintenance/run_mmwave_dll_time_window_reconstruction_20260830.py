"""Freeze DLL frame-time semantics and reconstruct targeted windows.

This is a bounded, read-only timestamp/window diagnostic. It does not alter
the acquisition producer, raw data, HR estimator, target/gate rules, ECG
reference, or any formal batch. The row-level frame mapping is intentionally
written to the local derived-data area rather than committed to Git.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np


ALGO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(r"D:\acq_mmwave_data")
FOCUSWAVE_ROOT = Path(r"D:\Project\厚粲杯\05_实验\FocusWave")
RESULT_ROOT = ALGO_ROOT / "docs" / "results" / "2026-08-30_MMWAVE_TARGETED_VALIDATION"
FIXED_WINDOWS = RESULT_ROOT / "MMWAVE_HR_GATE_TARGET_ABLATION_2026-08-30.csv"
ALIGNMENT_AUDIT = RESULT_ROOT / "ecg_alignment_audit.csv"
LOCAL_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_timestamp_semantics_repair_20260830")
MAPPING_PATH = LOCAL_ROOT / "MMWAVE_FRAME_TIME_MAPPING_AUDIT.csv"
WRAPPER = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
SUBJECTS = ("97793", "9779", "97795")
WINDOW_S = 20_000
STEP_S = 10_000
BOUNDARY_GUARD_S = 5_000
BLOCK_MARKERS = {"block1": (12, 22), "block2": (13, 23), "block3": (14, 24), "block4": (16, 26)}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception:
        return "unavailable"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def session_dir(subject: str) -> Path:
    return DATA_ROOT / f"sub-{subject}_"


def load_events(subject: str) -> list[dict]:
    rows = read_csv(session_dir(subject) / "beh" / "events.csv")
    for row in rows:
        row["unix_ms_int"] = int(float(row.get("unix_ms", 0) or 0))
        marker = str(row.get("marker", "")).strip()
        row["marker_int"] = int(marker) if marker.isdigit() else None
    return rows


def nearest_index(values: np.ndarray, target: int) -> int:
    position = int(np.searchsorted(values, target, side="left"))
    candidates = [idx for idx in (position - 1, position) if 0 <= idx < len(values)]
    return min(candidates, key=lambda idx: abs(int(values[idx]) - target))


def block_event_rows(events: list[dict], block_id: str) -> tuple[dict | None, dict | None]:
    start_marker, end_marker = BLOCK_MARKERS[block_id]
    starts = [row for row in events if row.get("event") == "segment_start" and row.get("segment") == block_id and row.get("marker_int") == start_marker]
    start = starts[0] if starts else None
    ends = [row for row in events if row.get("event") == "segment_end" and row.get("segment") == block_id and row.get("marker_int") == end_marker and start and row["unix_ms_int"] > start["unix_ms_int"]]
    return start, (ends[0] if ends else None)


def audit_mapping(rerun, subject: str, writer: csv.DictWriter) -> dict:
    timestamps = rerun.load_mmwave_timestamps(subject)
    reader = rerun.PartReader(subject)
    frame_ids = timestamps[:, 0].astype(np.int64)
    python_ts = timestamps[:, 2].astype(np.int64)
    dll_ts = timestamps[:, 1].astype(np.int64)
    npz_keys_consistent = True
    npz_file_metadata = []
    for index, path in enumerate(reader.files):
        with np.load(path) as data:
            keys = sorted(key for key in data.files if key.startswith("tx"))
            shapes = {key: int(data[key].shape[0]) for key in keys}
            npz_keys_consistent = npz_keys_consistent and bool(keys) and len(set(shapes.values())) == 1 and shapes[keys[0]] == int(reader.lengths[index])
            npz_file_metadata.append({"file": path.name, "frame_count": int(reader.lengths[index]), "tx_keys": keys, "channel_lengths_consistent": len(set(shapes.values())) == 1})
    frame_diff = np.diff(frame_ids)
    mapping_ok = len(timestamps) == reader.total_frames and len(np.unique(frame_ids)) == len(frame_ids) and bool(np.all(frame_diff == 1)) and npz_keys_consistent
    for global_idx in range(len(timestamps)):
        part = int(np.searchsorted(reader.starts, global_idx, side="right") - 1)
        frame_in_file = global_idx - int(reader.starts[part])
        writer.writerow({
            "subject": subject,
            "global_frame_idx": global_idx,
            "npz_file": reader.files[part].name,
            "frame_idx_in_file": frame_in_file,
            "python_unix_ms": int(python_ts[global_idx]),
            "dll_timestamp": int(dll_ts[global_idx]),
            "mapping_status": "OK" if mapping_ok else "MAPPING_CHECK_FAILED",
        })
    return {
        "timestamp_rows": int(len(timestamps)),
        "npz_frames": int(reader.total_frames),
        "row_count_equal": bool(len(timestamps) == reader.total_frames),
        "frame_index_first": int(frame_ids[0]),
        "frame_index_last": int(frame_ids[-1]),
        "frame_index_unique": int(len(np.unique(frame_ids))),
        "frame_index_diff_unique": sorted({int(value) for value in np.unique(frame_diff)}),
        "missing_or_duplicate_or_reordered": bool(not np.all(frame_diff == 1)),
        "npz_keys_and_channel_lengths_consistent": bool(npz_keys_consistent),
        "npz_file_count": len(reader.files),
        "npz_chunk_size_set": sorted({int(value) for value in reader.lengths}),
        "mapping_status": "OK" if mapping_ok else "MAPPING_CHECK_FAILED",
        "npz_files": npz_file_metadata,
        "python_first_ms": int(python_ts[0]),
        "python_last_ms": int(python_ts[-1]),
        "dll_first_unix_ms": int(dll_ts[0]),
        "dll_last_unix_ms": int(dll_ts[-1]),
        "dll_monotonic": bool(np.all(np.diff(dll_ts) >= 0)),
        "dll_negative_steps": int(np.sum(np.diff(dll_ts) < 0)),
        "dll_interval_distribution_ms": {key: round(float(value), 3) for key, value in zip(("min", "p10", "median", "p90", "p95", "max"), np.percentile(np.diff(dll_ts), [0, 10, 50, 90, 95, 100]))},
    }


def marker_anchor_audit(subject: str, dll_ts: np.ndarray, events: list[dict], alignment_rows: list[dict]) -> dict:
    marker_rows = []
    for row in events:
        marker = row.get("marker_int")
        if marker in {11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26}:
            idx = nearest_index(dll_ts, row["unix_ms_int"])
            marker_rows.append({"event": row.get("event"), "segment": row.get("segment"), "marker": marker, "event_unix_ms": row["unix_ms_int"], "nearest_dll_unix_ms": int(dll_ts[idx]), "delta_ms": int(dll_ts[idx] - row["unix_ms_int"])})
    tick_rows = []
    for row in events:
        marker = row.get("marker_int")
        if row.get("event") == "tick" and marker is not None and 101 <= marker <= 110:
            idx = nearest_index(dll_ts, row["unix_ms_int"])
            tick_rows.append(int(dll_ts[idx] - row["unix_ms_int"]))
    alignment_subject = [row for row in alignment_rows if row.get("subject") == subject]
    return {
        "program_marker_n": len(marker_rows),
        "program_marker_abs_delta_ms": {key: round(float(value), 3) for key, value in zip(("min", "median", "p95_abs", "max_abs"), (np.min(np.abs([row["delta_ms"] for row in marker_rows])), np.median([row["delta_ms"] for row in marker_rows]), np.percentile(np.abs([row["delta_ms"] for row in marker_rows]), 95), np.max(np.abs([row["delta_ms"] for row in marker_rows]))))} if marker_rows else {},
        "tick_n": len(tick_rows),
        "tick_abs_delta_p95_ms": round(float(np.percentile(np.abs(tick_rows), 95)), 3) if tick_rows else None,
        "tick_abs_delta_max_ms": round(float(np.max(np.abs(tick_rows))), 3) if tick_rows else None,
        "first_dll_unix_ms": int(dll_ts[0]),
        "last_dll_unix_ms": int(dll_ts[-1]),
        "last_program_event_unix_ms": int(max(row["unix_ms_int"] for row in events)) if events else None,
        "last_program_event_after_last_dll_ms": int(max(row["unix_ms_int"] for row in events) - dll_ts[-1]) if events else None,
        "biopac_alignment_rows": alignment_subject,
    }


def reconstruct_windows(rerun, subject: str, old_rows: list[dict], alignment_rows: list[dict]) -> tuple[list[dict], dict]:
    timestamps = rerun.load_mmwave_timestamps(subject)
    py_ts = timestamps[:, 2].astype(np.int64)
    dll_ts = timestamps[:, 1].astype(np.int64)
    events = load_events(subject)
    output = []
    blocks = {}
    for block_id, (start_marker, end_marker) in BLOCK_MARKERS.items():
        start_row, end_row = block_event_rows(events, block_id)
        alignment = next((row for row in alignment_rows if row.get("subject") == subject and row.get("block_id") == block_id), {})
        complete = bool(start_row and end_row and alignment.get("status") == "complete")
        blocks[block_id] = {"start_unix_ms": start_row["unix_ms_int"] if start_row else None, "end_unix_ms": end_row["unix_ms_int"] if end_row else None, "start_marker": start_marker, "end_marker": end_marker, "complete": complete, "alignment_status": alignment.get("status", "missing")}
        if not complete:
            continue
        old_block = [row for row in old_rows if row.get("subject") == subject and row.get("block_id") == block_id]
        start = blocks[block_id]["start_unix_ms"] + BOUNDARY_GUARD_S
        block_end = blocks[block_id]["end_unix_ms"] - BOUNDARY_GUARD_S
        index = 1
        while start + WINDOW_S <= block_end:
            stop = start + WINDOW_S
            new_start = int(np.searchsorted(dll_ts, start, side="left"))
            new_end = int(np.searchsorted(dll_ts, stop, side="right"))
            old = next((row for row in old_block if row.get("window_id") == f"{block_id}_w{index:03d}"), None)
            if old is None:
                raise RuntimeError(f"Missing frozen old window {subject}/{block_id}/w{index:03d}")
            old_start = int(old["mmwave_start_row"]); old_end = int(old["mmwave_end_row_exclusive"])
            old_set = set(range(old_start, old_end)); new_set = set(range(new_start, new_end))
            intersection = len(old_set & new_set); union = len(old_set | new_set)
            jaccard = intersection / union if union else None
            if jaccard == 1.0:
                equivalence = "EXACT"
            elif jaccard is not None and jaccard >= 0.9:
                equivalence = "PARTIAL"
            else:
                equivalence = "OBVIOUS"
            output.append({
                "subject": subject, "block_id": block_id, "window_id": f"{block_id}_w{index:03d}",
                "window_start_unix_ms": start, "window_end_unix_ms": stop,
                "frame_start_idx": int(timestamps[new_start, 0]) if new_end > new_start else None,
                "frame_end_idx": int(timestamps[new_end - 1, 0]) if new_end > new_start else None,
                "frame_start_row": new_start, "frame_end_row_exclusive": new_end,
                "frame_count": new_end - new_start,
                "dll_time_span_ms": int(dll_ts[new_end - 1] - dll_ts[new_start]) if new_end > new_start else None,
                "python_time_span_ms": int(py_ts[new_end - 1] - py_ts[new_start]) if new_end > new_start else None,
                "old_window_frame_count": old_end - old_start, "new_window_frame_count": new_end - new_start,
                "frame_membership_changed": bool(old_set != new_set), "frame_overlap_n": intersection,
                "frame_overlap_jaccard": round(float(jaccard), 6) if jaccard is not None else None,
                "added_frames": len(new_set - old_set), "removed_frames": len(old_set - new_set),
                "frame_count_delta": (new_end - new_start) - (old_end - old_start), "window_equivalence": equivalence,
                "alignment_status": alignment.get("status"), "marker_sequence_exact": alignment.get("marker_sequence_exact"),
            })
            start += STEP_S
            index += 1
    return output, blocks


def write_contract(path: Path, mapping_summary: dict, block_summary: dict, window_summary: dict, source_commit: str, coverage_summary: dict) -> None:
    compact_mapping = {
        subject: {key: value for key, value in summary.items() if key != "npz_files"}
        for subject, summary in mapping_summary.items()
    }
    path.write_text(f"""# mmWave frame-time contract — 2026-08-30

Status: `FROZEN_FOR_TARGETED_RECONSTRUCTION / ABSOLUTE_DLL_UNIX_MS_WITH_SOURCE_LIMITATION`

## Authoritative frame clock

The authoritative per-frame clock for this targeted analysis is the second timestamp column in the acquisition timestamp CSV: `receive_data.timeStamp`, converted by `MMWaveCapture._dotnet_ts_to_unix_ms()` to integer Unix milliseconds. The Python `time.time()` column is provenance only and is not used to define physiological windows.

Acquisition source: `kyandi233-dev/FocusWave@ecg`, commit `{source_commit}`, `01-MainProgram/core/mmwave_capture.py`.

- `_on_data()` receives the SDK/DLL `receive_data` object and queues it.
- `_process_datacube()` reads `receive_data.timeStamp` and `receive_data.frameIndex`.
- `_dotnet_ts_to_unix_ms()` accepts a .NET `DateTime` or the documented string format `YYYY-MM-DD-HH:MM:SS.sss`, constructs a local naive `datetime`, and calls `datetime.timestamp()*1000`.
- The source therefore establishes the stored field as a DLL-provided DateTime converted to Unix ms. The repository does not independently document whether the underlying DateTime is generated by the radar device, firmware, SDK, or host-side DLL callback; that origin remains a source limitation.

## Absolute anchor and conversion

For a valid sample, `dll_unix_ms = local_datetime(receive_data.timeStamp).timestamp()*1000`, with the acquisition host's local timezone (Beijing/UTC+8 in the source comment). The data-level checks show monotonic DLL timestamps and program-marker nearest-frame deltas of only a few milliseconds, supporting direct absolute use for this dataset. No additional global offset is fitted.

## Frame mapping

Python timestamp rows, NPZ frames, and DLL timestamp rows are mapped by their shared concatenation order. The audit verifies row counts, frame index sequence, NPZ file order, within-file offsets, channel lengths, duplicate/missing/reorder checks. Summary: `{json.dumps(compact_mapping, ensure_ascii=False)}`.

## Block mapping and window rule

Block boundaries remain the existing program `events.csv` markers and BIOPAC audit: block1 `12/22`, block2 `13/23`, block3 `14/24`, block4 `16/26` when used; 101–110 ticks are retained for local alignment verification. Only blocks marked complete by the existing BIOPAC/alignment audit enter reconstruction. Each block uses start + 5 s guard, 20 s windows, 10 s step, and end - 5 s guard. No transition crosses rest, posture adjustment, or block boundary.

Window reconstruction summary: `{json.dumps(window_summary, ensure_ascii=False)}`.

Absolute coverage audit: `{json.dumps(coverage_summary, ensure_ascii=False)}`. A positive `complete_block_end_after_last_dll_ms` means the program/BIOPAC end marker extends beyond the last recorded DLL frame; those tail intervals are not imputed or backfilled.

## Precision and limitations

- Stored precision is integer milliseconds; frame-to-frame DLL intervals are approximately 10 ms and are not forced to a synthetic grid.
- The Python timestamp remains in the mapping audit for provenance but cannot define frame gaps or physiology windows.
- The exact hardware-vs-SDK origin of `receive_data.timeStamp` is not exposed in this repository; absolute validity is supported by code conversion and marker alignment, not by an SDK specification.
- Existing HR/BR/HRV boundaries are unchanged. This contract authorizes window equivalence audit first; HR rerun is a separate, unchanged-estimator sensitivity step only after this contract is accepted.
""", encoding="utf-8")


def main() -> int:
    rerun = load_module(WRAPPER, "targeted_wrapper_for_dll_time")
    alignment_rows = read_csv(ALIGNMENT_AUDIT)
    old_rows = [row for row in read_csv(FIXED_WINDOWS) if row.get("subject") in SUBJECTS]
    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    mapping_summaries = {}
    with MAPPING_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["subject", "global_frame_idx", "npz_file", "frame_idx_in_file", "python_unix_ms", "dll_timestamp", "mapping_status"])
        writer.writeheader()
        for subject in SUBJECTS:
            mapping_summaries[subject] = audit_mapping(rerun, subject, writer)
    window_rows = []
    block_summaries = {}
    anchor_summaries = {}
    for subject in SUBJECTS:
        timestamps = rerun.load_mmwave_timestamps(subject)
        events = load_events(subject)
        anchor_summaries[subject] = marker_anchor_audit(subject, timestamps[:, 1].astype(np.int64), events, alignment_rows)
        rows, blocks = reconstruct_windows(rerun, subject, old_rows, alignment_rows)
        window_rows.extend(rows)
        block_summaries[subject] = blocks
    window_rows.sort(key=lambda row: (SUBJECTS.index(row["subject"]), row["block_id"], row["window_id"]))
    window_path = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv"
    write_csv(window_path, window_rows)
    exact = sum(row["window_equivalence"] == "EXACT" for row in window_rows)
    partial = sum(row["window_equivalence"] == "PARTIAL" for row in window_rows)
    obvious = sum(row["window_equivalence"] == "OBVIOUS" for row in window_rows)
    window_summary = {"n": len(window_rows), "exact": exact, "partial": partial, "obvious": obvious, "changed": sum(bool(row["frame_membership_changed"]) for row in window_rows), "mean_jaccard": round(float(np.mean([row["frame_overlap_jaccard"] for row in window_rows])), 6) if window_rows else None, "median_jaccard": round(float(np.median([row["frame_overlap_jaccard"] for row in window_rows])), 6) if window_rows else None, "min_jaccard": round(float(np.min([row["frame_overlap_jaccard"] for row in window_rows])), 6) if window_rows else None, "mean_frame_count_delta": round(float(np.mean([row["frame_count_delta"] for row in window_rows])), 6) if window_rows else None, "min_new_frame_count": min(row["new_window_frame_count"] for row in window_rows) if window_rows else None, "max_new_frame_count": max(row["new_window_frame_count"] for row in window_rows) if window_rows else None}
    coverage_summary = {}
    for subject in SUBJECTS:
        complete_ends = [block["end_unix_ms"] for block in block_summaries[subject].values() if block["complete"] and block["end_unix_ms"] is not None]
        last_dll = anchor_summaries[subject]["last_dll_unix_ms"]
        complete_end = max(complete_ends) if complete_ends else None
        coverage_summary[subject] = {
            "last_dll_unix_ms": last_dll,
            "complete_block_end_unix_ms": complete_end,
            "complete_block_end_after_last_dll_ms": (complete_end - last_dll) if complete_end is not None else None,
        }
    source_commit = git(FOCUSWAVE_ROOT, "rev-parse", "ecg")
    contract_path = ALGO_ROOT / "docs" / "research" / "MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md"
    write_contract(contract_path, mapping_summaries, block_summaries, window_summary, source_commit, coverage_summary)
    report_lines = [
        "# mmWave DLL frame-time reconstruction and window equivalence audit — 2026-08-30", "",
        "状态：`WINDOW_CONTRACT_RECONSTRUCTED / HR_NOT_YET_RERUN`", "",
        f"- Canonical algorithm baseline at run: `{git(ALGO_ROOT, 'rev-parse', 'HEAD')}`.",
        f"- FocusWave acquisition source: `ecg` `{source_commit}`.",
        "- This run only freezes frame-time semantics, audits mapping, and compares old/new window membership. It does not run HR, change target/gate, change ECG, or modify producer/raw/firmware/portable V2.", "",
        "## DLL timestamp meaning", "",
        "`receive_data.timeStamp` is a DLL-provided .NET DateTime/string field converted by `_dotnet_ts_to_unix_ms()` into Unix ms. Its exact device-vs-SDK generation origin is not documented in the repository, so the contract records that limitation. In the data, it is monotonic and aligns to program marker Unix times within millisecond-scale deltas.", "",
        "## Python/NPZ/DLL mapping", "",
        f"Mapping audit: `{MAPPING_PATH}` (local-only row-level output), SHA-256 `{sha256(MAPPING_PATH)}`.", "",
        "| subject | timestamp rows | NPZ frames | frame diff | mapping | DLL monotonic | negative DLL steps | DLL interval median/max ms |",
        "|---|---:|---:|---|---|---|---:|---|",
    ]
    for subject in SUBJECTS:
        item = mapping_summaries[subject]
        report_lines.append(f"| {subject} | {item['timestamp_rows']} | {item['npz_frames']} | {item['frame_index_diff_unique']} | {item['mapping_status']} | {item['dll_monotonic']} | {item['dll_negative_steps']} | {item['dll_interval_distribution_ms']['median']}/{item['dll_interval_distribution_ms']['max']} |")
    short_windows = [row for row in window_rows if row["new_window_frame_count"] < 100]
    report_lines += ["", "## Marker and BIOPAC anchor audit", "", "Existing `ecg_alignment_audit.csv` remains the BIOPAC/program marker audit: block-local mappings, 101–110 ticks, and complete-block status are reused. The reconstruction does not create a new ECG reference. Anchor details are in the manifest.", "", "## Absolute coverage limitation", "", f"- Complete-block end minus last recorded DLL frame: `{json.dumps(coverage_summary, ensure_ascii=False)}`.", f"- Short reconstructed windows (`new_window_frame_count < 100`): `{len(short_windows)}`; the observed case is `{[(row['subject'], row['block_id'], row['window_id'], row['new_window_frame_count']) for row in short_windows]}`.", "- The 97795/block4 program end marker is 24,809 ms after the last DLL frame; the final guarded window therefore contains only 46 recorded DLL frames. No synthetic timestamps, frame padding, or Python-time backfill is applied.", "", "## Old versus new windows", "", f"- New DLL-time windows: `{len(window_rows)}`; exact `{exact}`, partial (Jaccard ≥ 0.9) `{partial}`, obvious (Jaccard < 0.9) `{obvious}`.", f"- Changed membership: `{window_summary['changed']}/{len(window_rows)}`; Jaccard mean/median/min: `{window_summary['mean_jaccard']}/{window_summary['median_jaccard']}/{window_summary['min_jaccard']}`.", f"- New frame count range: `{window_summary['min_new_frame_count']}–{window_summary['max_new_frame_count']}`; mean frame-count delta versus old: `{window_summary['mean_frame_count_delta']}`.", "- The old Python-time windows are not automatically deleted or superseded by this audit; the HR decision is deferred until the unchanged estimator is rerun on the new membership if the equivalence gate is materially changed.", "", "## Final decision gate", "", "- `DLL_TIME_RECONSTRUCTION`: supported for this dataset as absolute DLL Unix ms, with the source-origin limitation recorded.", "- `WINDOW_EQUIVALENCE`: see exact/partial/obvious counts above.", "- `HR_RERUN`: not performed in this first stage.", "- HR remains `HOLD`; BR remains `HOLD`; HRV remains `BLOCKED`; Issue #16 remains `PAUSED`.", "", "## Artifacts", "", "- `MMWAVE_FRAME_TIME_MAPPING_AUDIT.csv` — local-only row-level mapping audit", "- `MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md`", "- `MMWAVE_DLL_TIME_WINDOWS_2026-08-30.csv`", "- `MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_MANIFEST.json`", "- `MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_REPORT_2026-08-30.md`", ""]
    report_path = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_REPORT_2026-08-30.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    manifest = {
        "status": "WINDOW_CONTRACT_RECONSTRUCTED / HR_NOT_YET_RERUN",
        "canonical_algorithm_head_at_run": git(ALGO_ROOT, "rev-parse", "HEAD"),
        "canonical_algorithm_remote_main_at_run": git(ALGO_ROOT, "ls-remote", "origin", "refs/heads/main"),
        "focuswave_repository": "kyandi233-dev/FocusWave", "focuswave_branch": "ecg", "focuswave_commit": source_commit,
        "source_file": "01-MainProgram/core/mmwave_capture.py", "source_function_fields": ["_on_data", "_dotnet_ts_to_unix_ms", "_process_datacube", "_flush_npz_chunk"],
        "authoritative_frame_clock": "DLL receive_data.timeStamp converted to absolute Unix milliseconds",
        "python_timestamp_role": "provenance_only_not_window_clock",
        "mapping_output_local_only": str(MAPPING_PATH), "mapping_sha256": sha256(MAPPING_PATH),
        "mapping_summary": {subject: {key: value for key, value in summary.items() if key != "npz_files"} for subject, summary in mapping_summaries.items()}, "anchor_summary": anchor_summaries, "block_summary": block_summaries, "absolute_coverage_summary": coverage_summary,
        "fixed_old_window_input": str(FIXED_WINDOWS), "fixed_old_window_input_sha256": sha256(FIXED_WINDOWS),
        "alignment_audit": {"path": ALIGNMENT_AUDIT.name, "sha256": sha256(ALIGNMENT_AUDIT), "row_count": len(alignment_rows)},
        "window_summary": window_summary,
        "window_contract": {"window_s": 20, "step_s": 10, "boundary_guard_s": 5, "complete_blocks_only": True, "cross_rest_or_block_transitions": False},
        "old_20s_results_decision": "DEFER_UNTIL_UNCHANGED_ESTIMATOR_RERUN_ON_DLL_TIME_MEMBERSHIP",
        "hr_rerun": "NOT_RUN_IN_STAGE_1",
        "exclusions": ["HR estimator tuning", "target/gate changes", "ECG changes", "new HRV", "Issue #16", "C2B", "C2C", "full batch", "producer/raw/firmware", "portable V2", "window deletion"],
        "outputs": {},
    }
    for path in (window_path, contract_path, report_path):
        manifest["outputs"][path.name] = {"path": path.name, "sha256": sha256(path), "row_count": sum(1 for _ in csv.DictReader(path.open(encoding="utf-8-sig"))) if path.suffix == ".csv" else None}
    manifest_path = RESULT_ROOT / "MMWAVE_DLL_TIME_WINDOW_RECONSTRUCTION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "mapping": mapping_summaries, "window_summary": window_summary, "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
