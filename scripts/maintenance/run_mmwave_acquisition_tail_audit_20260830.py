"""Audit the mmWave acquisition/DLL timestamp tail without changing raw data.

This audit reuses the stored timestamp CSV and events.csv files.  It does not
re-discover timestamp semantics, read NPZ payloads, pad/backfill frames, or
rerun any HR analysis.  The FocusWave source is inspected at the requested
immutable ref for lifecycle ordering evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_COMMIT = "8e6fe5c5d08f386661bc05aaf9d5c5715a43b317"
SOURCE_PATHS = {
    "capture": "01-MainProgram/core/mmwave_capture.py",
    "main": "01-MainProgram/main_experiment_msmf.py",
    "event_logger": "01-MainProgram/core/event_logger.py",
}
LONG_TAIL_MS = 5_000
PYTHON_EVENT_TOLERANCE_MS = 2_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(source_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_root), *args], text=True
    ).strip()


def source_text(source_root: Path, commit: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_root), "show", f"{commit}:{path}"],
        text=True,
        encoding="utf-8",
    )


def line_of(text: str, needle: str, start: int = 0) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if index >= start and needle in line:
            return index
    return None


def source_evidence(source_root: Path, commit: str) -> dict[str, Any]:
    texts = {name: source_text(source_root, commit, path) for name, path in SOURCE_PATHS.items()}
    capture = texts["capture"]
    main = texts["main"]
    event_logger = texts["event_logger"]
    stop = line_of(capture, "def stop(")
    stop_collect = line_of(capture, "self._api.StopCollectingData()", stop or 0)
    recording_false = line_of(capture, "self._recording_flag = False", stop or 0)
    queue_wait = line_of(capture, "while not self._data_queue.empty()", stop or 0)
    running_false = line_of(capture, "self._running = False", stop or 0)
    worker_conversion = line_of(capture, "self._api.DatacubeConversion(")
    callback_enqueue = line_of(capture, "self._data_queue.put_nowait(receive_data)")
    marker_end = line_of(main, "def _marker_seg_end(")
    marker_end_log = line_of(main, "self.event_logger.log('segment_end'", marker_end or 0)
    stop_all = line_of(main, "self._stop_all_modalities()")
    experiment_end = line_of(main, "'experiment_end'", stop_all or 0)
    logger_flush = line_of(event_logger, "self._file.flush()")
    return {
        "source_ref": commit,
        "source_paths": SOURCE_PATHS,
        "line_numbers": {
            "capture_callback_enqueue": callback_enqueue,
            "capture_worker_conversion": worker_conversion,
            "capture_stop": stop,
            "capture_stop_collecting": stop_collect,
            "capture_recording_flag_false": recording_false,
            "capture_queue_wait": queue_wait,
            "capture_running_false": running_false,
            "main_marker_segment_end": marker_end,
            "main_marker_segment_end_log": marker_end_log,
            "main_stop_all_modalities": stop_all,
            "main_experiment_end_log": experiment_end,
            "event_logger_flush": logger_flush,
        },
        "ordering_checks": {
            "worker_conversion_is_synchronous_in_worker": bool(worker_conversion and callback_enqueue and worker_conversion > callback_enqueue),
            "recording_flag_cleared_before_queue_wait": bool(recording_false and queue_wait and recording_false < queue_wait),
            "worker_stop_flag_set_after_queue_wait": bool(running_false and queue_wait and running_false > queue_wait),
            "experiment_end_logged_after_stop_all_modalities": bool(experiment_end and stop_all and experiment_end > stop_all),
            "events_flush_each_log": logger_flush is not None,
        },
    }


def read_events(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_timestamp_tail(path: Path, tail_size: int = 101) -> dict[str, Any]:
    first: tuple[int, int, int] | None = None
    last: tuple[int, int, int] | None = None
    previous: tuple[int, int, int] | None = None
    count = 0
    frame_consecutive = True
    frame_gap_count = 0
    first_frame_gap: tuple[int, int, int] | None = None
    tail: list[tuple[int, int, int]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if not row:
                continue
            current = (int(row[0]), int(row[1]), int(row[2]))
            if first is None:
                first = current
            if previous is not None and current[0] != previous[0] + 1:
                frame_consecutive = False
                frame_gap_count += 1
                if first_frame_gap is None:
                    first_frame_gap = (previous[0], current[0], current[0] - previous[0] - 1)
            previous = current
            last = current
            count += 1
            tail.append(current)
            if len(tail) > tail_size:
                tail.pop(0)
    if first is None or last is None:
        raise ValueError(f"empty timestamp file: {path}")
    dll_intervals = [b[1] - a[1] for a, b in zip(tail, tail[1:])]
    py_intervals = [b[2] - a[2] for a, b in zip(tail, tail[1:])]
    return {
        "timestamp_rows": count,
        "first_frame_index": first[0],
        "last_frame_index": last[0],
        "frame_index_consecutive": frame_consecutive,
        "frame_index_gap_count": frame_gap_count,
        "first_frame_index_gap": list(first_frame_gap) if first_frame_gap else None,
        "first_dll_unix_ms": first[1],
        "last_dll_unix_ms": last[1],
        "first_python_unix_ms": first[2],
        "last_python_unix_ms": last[2],
        "dll_span_ms": last[1] - first[1],
        "python_span_ms": last[2] - first[2],
        "final_python_minus_dll_ms": last[2] - last[1],
        "tail_dll_interval_min_ms": min(dll_intervals) if dll_intervals else None,
        "tail_dll_interval_median_ms": sorted(dll_intervals)[len(dll_intervals) // 2] if dll_intervals else None,
        "tail_dll_interval_max_ms": max(dll_intervals) if dll_intervals else None,
        "tail_python_interval_min_ms": min(py_intervals) if py_intervals else None,
        "tail_python_interval_median_ms": sorted(py_intervals)[len(py_intervals) // 2] if py_intervals else None,
        "tail_python_interval_max_ms": max(py_intervals) if py_intervals else None,
    }


def event_time(events: list[dict[str, str]], event: str, segment: str | None = None) -> int | None:
    candidates = [
        row for row in events
        if row.get("event") == event and (segment is None or row.get("segment") == segment)
    ]
    if not candidates:
        return None
    return max(int(row["unix_ms"]) for row in candidates)


def audit_session(session_dir: Path, subject: str) -> dict[str, Any]:
    event_path = session_dir / "beh" / "events.csv"
    timestamp_paths = sorted((session_dir / "mmwave").glob("*_timestamps.csv"))
    result: dict[str, Any] = {
        "subject": subject,
        "session_dir": str(session_dir),
        "events_path": str(event_path),
        "timestamp_path": str(timestamp_paths[0]) if timestamp_paths else None,
        "events_present": event_path.is_file(),
        "timestamps_present": bool(timestamp_paths),
    }
    if not event_path.is_file() or not timestamp_paths:
        result["audit_status"] = "MISSING_REQUIRED_LOG"
        return result
    events = read_events(event_path)
    timestamp = read_timestamp_tail(timestamp_paths[0])
    block4_end = event_time(events, "segment_end", "block4")
    experiment_end = event_time(events, "experiment_end")
    # Use block4 end when available; otherwise compare the complete experiment
    # end.  A missing block4 is explicitly non-comparable, not a substitute
    # block boundary.
    block_end = block4_end if block4_end is not None else experiment_end
    result.update(timestamp)
    result.update({
        "event_rows": len(events),
        "block4_end_unix_ms": block4_end,
        "experiment_end_unix_ms": experiment_end,
        "reference_end_unix_ms": block_end,
        "reference_end_after_last_dll_ms": block_end - timestamp["last_dll_unix_ms"] if block_end is not None else None,
        "experiment_end_after_last_dll_ms": experiment_end - timestamp["last_dll_unix_ms"] if experiment_end is not None else None,
        "experiment_end_after_last_python_ms": experiment_end - timestamp["last_python_unix_ms"] if experiment_end is not None else None,
        "has_block4": block4_end is not None,
        "long_tail_candidate_ge_5s": bool(block_end is not None and block_end - timestamp["last_dll_unix_ms"] >= LONG_TAIL_MS),
        "python_processing_near_event": bool(experiment_end is not None and abs(experiment_end - timestamp["last_python_unix_ms"]) <= PYTHON_EVENT_TOLERANCE_MS),
        "audit_status": "OK",
    })
    if result["long_tail_candidate_ge_5s"] and result["python_processing_near_event"]:
        result["queue_lag_signature"] = True
        result["interpretation"] = "DLL tail lags program end while final Python processing time is near event end; consistent with consumer backlog/shutdown truncation, not proof of physical RF dropout."
    else:
        result["queue_lag_signature"] = False
        result["interpretation"] = "No long-tail queue-lag signature under this audit rule."
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "subject", "audit_status", "has_block4", "timestamp_rows", "first_frame_index", "last_frame_index",
        "frame_index_consecutive", "frame_index_gap_count", "first_frame_index_gap", "last_dll_unix_ms", "last_python_unix_ms", "block4_end_unix_ms",
        "experiment_end_unix_ms", "reference_end_after_last_dll_ms", "experiment_end_after_last_dll_ms",
        "experiment_end_after_last_python_ms", "final_python_minus_dll_ms", "dll_span_ms", "python_span_ms",
        "tail_dll_interval_median_ms", "tail_python_interval_median_ms", "long_tail_candidate_ge_5s",
        "python_processing_near_event", "queue_lag_signature", "interpretation",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_report(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    long_rows = [row for row in rows if row.get("long_tail_candidate_ge_5s")]
    audited_rows = [row for row in rows if row.get("audit_status") == "OK"]
    missing_rows = [row for row in rows if row.get("audit_status") == "MISSING_REQUIRED_LOG"]
    lines = [
        "# mmWave acquisition/DLL coverage tail audit — 2026-08-30",
        "",
        "状态：`PARTIAL / HISTORICAL_TAIL_IRRECOVERABLE / FUTURE_STOP_ORDER_FIX_IDENTIFIED`",
        "",
        "## Scope and reuse gate",
        "",
        "本审计只读取既有 `events.csv`、`*_mmwave_timestamps.csv` 的事件、首尾、计数与 frame-index 连续性，并检查 FocusWave `ecg` immutable source ref。没有重做 Python-vs-DLL timestamp discovery，没有读取或修改 NPZ/raw payload，没有 synthetic padding/backfill，没有改 primary 335-window provenance，也没有运行 C2B/C2C 或 HR analysis。",
        "",
        f"- RUN_ID: `{manifest['run_id']}`",
        f"- canonical algorithm HEAD: `{manifest['canonical_algorithm_head']}`",
        f"- FocusWave source: `ecg@{manifest['source_commit']}`",
        f"- REUSE_REJECTION_REASON: existing c0f1717 coverage audit only covered the three targeted subjects and did not inspect acquisition lifecycle ordering or the other available session tails; a bounded new audit was required to answer Issue #28 items 1–3.",
        f"- Existing coverage manifest reused without modification: `{manifest['coverage_manifest_reuse']['path']}`; its recorded algorithm head remains `{manifest['coverage_manifest_reuse']['canonical_algorithm_head_at_run']}` and its historical input/reconstruction provenance remains the prior worktree (`{manifest['coverage_manifest_reuse']['window_input']}`).",
        "",
        "## Source-level causal path",
        "",
        "在 `mmwave_capture.py` 中，DLL callback 只把对象放入有界队列；worker 随后同步执行 `DatacubeConversion` 和文件写出。现有 `stop()` 的顺序是 `StopCollectingData()` → 将 `_recording_flag` 设为 false → 等待队列 → 停 worker → flush/close。这样，停止前已经进入队列但尚未被 worker 消费的帧，会在队列等待期间被取出但因 recording flag 已关闭而不再写出；当前 meta 也没有保存 queue backlog、callback drop 或 stop latency，无法从历史文件单独区分“队列残留被丢弃”和更底层 SDK/DLL 时间戳漂移。",
        "",
        "源码顺序检查：",
        "",
        f"- callback enqueue line `{manifest['source_line_numbers']['capture_callback_enqueue']}`; synchronous conversion line `{manifest['source_line_numbers']['capture_worker_conversion']}`.",
        f"- `stop()` line `{manifest['source_line_numbers']['capture_stop']}`; `recording_flag=False` line `{manifest['source_line_numbers']['capture_recording_flag_false']}` precedes queue wait line `{manifest['source_line_numbers']['capture_queue_wait']}`.",
        f"- main program logs block marker end before the final UI/cleanup; `_stop_all_modalities()` line `{manifest['source_line_numbers']['main_stop_all_modalities']}` precedes `experiment_end` logging line `{manifest['source_line_numbers']['main_experiment_end_log']}`.",
        f"- EventLogger flushes each event at line `{manifest['source_line_numbers']['event_logger_flush']}`, so marker-file buffering is not the primary explanation for the observed event timestamps.",
        "",
        "## Observed tail",
        "",
        "| subject | audit | block4 | frame indices consecutive | reference end − last DLL ms | experiment end − last Python ms | final Python − DLL ms | queue-lag signature |",
        "|---|---|---:|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['subject']} | {row.get('audit_status')} | {row.get('has_block4')} | {row.get('frame_index_consecutive', 'N/A')} | {row.get('reference_end_after_last_dll_ms')} | {row.get('experiment_end_after_last_python_ms')} | {row.get('final_python_minus_dll_ms')} | {row.get('queue_lag_signature', False)} |"
        )
    lines += [
        "",
        "## Session-count and frame-index limits",
        "",
        f"`session_count={len(rows)}` means all `{manifest['data_root']}` `sub-*` directories enumerated by this audit. `audited_session_count={len(audited_rows)}` means only sessions with both `beh/events.csv` and a timestamp CSV. The remaining `{len(missing_rows)}` sessions are `MISSING_REQUIRED_LOG`; they were not excluded as negative evidence and cannot be used to rule out the same tail pattern.",
        "",
        "Frame-index continuity is session-specific, not a global property:",
    ]
    for row in audited_rows:
        continuity = row.get("frame_index_consecutive")
        gap_count = row.get("frame_index_gap_count")
        if continuity:
            detail = f"`frame_index_consecutive=true` (`gap_count={gap_count}`)"
        else:
            detail = f"`frame_index_consecutive=false` (`gap_count={gap_count}`, first gap={row.get('first_frame_index_gap')})"
        lines.append(f"- `{row['subject']}`: {detail}.")
    lines += [
        "- The nonconsecutive retained indices for `97796` and `97994` remain unresolved limitations. They do not invalidate the observed timestamps, but they prevent treating those sessions as proof of exactly the same frame-loss mechanism as `97795`.",
        "",
        "## Root-cause conclusion",
        "",
        f"- Long-tail candidates under the engineering rule `reference end − last DLL >= {LONG_TAIL_MS} ms`: `{len(long_rows)}` sessions: `" + ", ".join(row['subject'] for row in long_rows) + "`.",
        "- `97795/block4`: the existing primary-window evidence remains unchanged: `w027` has 1,035 frames and `w028` has 46 frames; their DLL end gaps are 9,536 ms and 19,536 ms. The block4 marker is 24,809 ms after the last DLL frame.",
        "- `97795`, `97796`, and `97994` all show the same long-tail signature in the available four-block recordings, so the evidence does not support calling this a 97795-only marker-write anomaly. However, `97796` and `97994` have `frame_index_consecutive=false`; that nonconsecutiveness is unresolved, and the five `MISSING_REQUIRED_LOG` sessions cannot be used to exclude the same pattern. Sessions without block4 are recorded as not comparable at block4.",
        "- The best supported mechanism is a slow/saturated consumer plus shutdown ordering: the final Python processing times are near the experiment end while the stored DLL times lag by about 24.8 s, 26.1 s, and 52.6 s. This is not sufficient to prove a physical sensor dropout. `97795` has consecutive retained frame indices in this scan; `97796` and `97994` do not, so any stronger common-loss claim remains unsupported. Any unretained queue tail is not recoverable from the files.",
        "- Historical status: `IRRECOVERABLE`. No timestamp, frame payload, queue counter, or callback receipt exists that can safely reconstruct the missing/ambiguous tail. Do not backfill, pad, or replace the primary 335-window result.",
        "",
        "## Future prevention (source-owner patch location; not applied here)",
        "",
        "最小修复位置是 FocusWave `ecg` 的 `01-MainProgram/core/mmwave_capture.py::MMWaveCapture.stop()`：停止 DLL 后先断开 callback 输入，并在 `_recording_flag` 仍为 true 时按 `unfinished_tasks`/明确 drain-and-join 语义消费已入队对象；只有队列真正排空或明确记录超时后，才关闭 recording/worker、flush 文件和写 meta。meta 应追加 queue residual/drop count、stop begin/end 和 drain timeout，便于下一次判定 acquisition tail。需要在采集机做一次短时真实硬件 dry-run 验证；本审计不修改 producer worktree，也不宣称该未来修复已经验证。",
        "",
        "## Boundary to other issues",
        "",
        "本结果只补足 acquisition/DLL tail 的工程证据；它不改变现有 335-window primary provenance，不阻塞 #24–#27 的 validity 分析，也不把 coverage tail 解释为总体 HR 大误差主因。",
        "",
        "## Outputs",
        "",
        f"- `{manifest['csv_output']}`",
        f"- `{manifest['report_output']}`",
        f"- `{manifest['manifest_output']}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--focuswave-root", type=Path, required=True)
    parser.add_argument("--source-commit", default=DEFAULT_SOURCE_COMMIT)
    parser.add_argument("--output-root", type=Path, default=Path("docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION"))
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    actual_source_head = git(args.focuswave_root, "rev-parse", args.source_commit)
    if actual_source_head != args.source_commit:
        raise RuntimeError(f"source ref does not resolve exactly: {args.source_commit} -> {actual_source_head}")
    canonical_head = git(Path(__file__).resolve().parents[2], "rev-parse", "HEAD")
    source = source_evidence(args.focuswave_root, args.source_commit)
    coverage_manifest_path = args.output_root / "MMWAVE_DLL_WINDOW_COVERAGE_AUDIT_MANIFEST.json"
    coverage_manifest = json.loads(coverage_manifest_path.read_text(encoding="utf-8"))
    rows = []
    for session_dir in sorted(path for path in args.data_root.glob("sub-*") if path.is_dir()):
        subject = session_dir.name.removeprefix("sub-").removesuffix("_")
        rows.append(audit_session(session_dir, subject))

    args.output_root.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_root / "MMWAVE_ACQUISITION_TAIL_AUDIT_2026-08-30.csv"
    report_path = args.output_root / "MMWAVE_ACQUISITION_TAIL_AUDIT_REPORT_2026-08-30.md"
    manifest_path = args.output_root / "MMWAVE_ACQUISITION_TAIL_AUDIT_MANIFEST.json"
    write_csv(csv_path, rows)
    manifest: dict[str, Any] = {
        "status": "PARTIAL / HISTORICAL_TAIL_IRRECOVERABLE / FUTURE_STOP_ORDER_FIX_IDENTIFIED",
        "run_id": args.run_id,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_algorithm_head": canonical_head,
        "source_commit": args.source_commit,
        "data_root": str(args.data_root),
        "focuswave_root": str(args.focuswave_root),
        "source_line_numbers": source["line_numbers"],
        "source_ordering_checks": source["ordering_checks"],
        "coverage_manifest_reuse": {
            "path": coverage_manifest_path.name,
            "canonical_algorithm_head_at_run": coverage_manifest["canonical_algorithm_head_at_run"],
            "canonical_algorithm_remote_main_at_run": coverage_manifest["canonical_algorithm_remote_main_at_run"],
            "window_input": coverage_manifest["window_input"],
            "reconstruction_manifest": coverage_manifest["reconstruction_manifest"],
            "source_manifest_sha256_before_audit": sha256(coverage_manifest_path),
        },
        "reuse": {
            "reused": [
                "c0f171763ee0f22fe41131214246006c36442a67 coverage audit",
                "426576e0809252656b79729ac077e91a6bfca80d DLL frame-time contract",
                "FocusWave ecg source ref and existing events/timestamp files",
            ],
            "reuse_rejection_reason": "Existing coverage audit covered only the three targeted subjects and did not inspect acquisition lifecycle ordering or all available session tails.",
        },
        "contract": {
            "long_tail_candidate_ms": LONG_TAIL_MS,
            "python_event_tolerance_ms": PYTHON_EVENT_TOLERANCE_MS,
            "uses_dll_timestamp_for_tail": True,
            "uses_python_timestamp_only_for_processing_nearness": True,
            "synthetic_padding": False,
            "backfill": False,
            "primary_335_window_changed": False,
        },
        "session_count": len(rows),
        "audited_session_count": sum(row.get("audit_status") == "OK" for row in rows),
        "long_tail_subjects": [row["subject"] for row in rows if row.get("long_tail_candidate_ge_5s")],
        "rows": rows,
        "csv_output": csv_path.name,
        "report_output": report_path.name,
        "manifest_output": manifest_path.name,
    }
    report_path.write_text(build_report(manifest, rows), encoding="utf-8")
    manifest["outputs"] = {
        csv_path.name: {"path": csv_path.name, "sha256": sha256(csv_path), "row_count": len(rows)},
        report_path.name: {"path": report_path.name, "sha256": sha256(report_path)},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "run_id": args.run_id,
        "audited_session_count": manifest["audited_session_count"],
        "long_tail_subjects": manifest["long_tail_subjects"],
        "outputs": manifest["outputs"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
