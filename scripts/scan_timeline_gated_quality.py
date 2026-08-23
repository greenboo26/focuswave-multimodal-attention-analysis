"""按行为时间轴扫描毫米波信号质量，不读取任何完整实验段。

每次扫描只传入一个 baseline 或一个正式 block 的 ``frame_start/frame_end``。
这里的通过级别仅描述心跳带通位移是否高于既有噪声阈值，不等同于 ECG 准确性
或 HRV 有效性。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import behavior_time_gate as gate
import process_vital_signs_v3_1_1 as algo


PROJECT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "08_算法" / "output" / "质量分析_行为裁剪_v1"
DEFAULT_ROOTS = [Path(r"E:\Data"), Path(r"F:\正式实验")]


def scan_segment(record: dict, segment: dict) -> dict:
    """只扫描一个已映射的帧范围，返回信号存在性质量指标。"""
    mmwave_dir = Path(record["mmwave_dir"])
    pattern = f"{record['subject']}_mmwave_datacube_part*.npz"
    npz_files = algo.collect_npz_parts(mmwave_dir, pattern=pattern)
    frame_start, frame_end = int(segment["frame_start"]), int(segment["frame_end"])
    common = {
        "source_tag": record["source_tag"], "subject": record["subject"],
        "layer": segment["layer"], "segment": segment["label"],
        "frame_start": frame_start, "frame_end": frame_end,
        "frame_count": int(segment["frame_count"]),
        "duration_s": float(segment["retained_duration_s"]),
    }
    if not npz_files:
        return {**common, "status": "error", "error": "no_npz"}
    try:
        channel_power, bin_power_acc, n_frames = algo.accumulate_range_profile(
            npz_files, frame_start=frame_start, frame_end=frame_end)
        sample = next(algo._iter_selected_chunks(
            npz_files, frame_start=frame_start, frame_end=min(frame_end, frame_start + 1000)), None)
        if sample is None or n_frames <= 0:
            return {**common, "status": "error", "error": "empty_cropped_segment"}
        sample_fd = algo._as_range_cube(sample)
        _, _, hr_ch, hr_bin, candidate_summaries = algo.select_separate_channels_bins(
            bin_power_acc, sample_fd, sample.shape[0])
        hr_summary = max(candidate_summaries, key=lambda item: item["best_hr_selection_score"])
        stds: list[float] = []
        for iq in algo._iter_selected_chunks(npz_files, frame_start=frame_start, frame_end=frame_end):
            if len(iq) < 100:
                continue
            displacement_mm = algo.WAVELENGTH_MM * np.unwrap(np.angle(iq[:, hr_bin, hr_ch])) / (4 * np.pi)
            heart_bp = algo._sos_bandpass(signal.detrend(displacement_mm, type="linear"), algo.HR_LO_HZ, algo.HR_HI_HZ)
            value = float(np.std(heart_bp))
            if np.isfinite(value):
                stds.append(value)
        if not stds:
            return {**common, "status": "error", "error": "no_valid_quality_window"}
        values = np.asarray(stds, dtype=float)
        usable_ratio = float(np.mean(values >= algo.MIN_HEART_WINDOW_STD_MM))
        level = "pass" if usable_ratio >= 0.80 else "partial" if usable_ratio >= 0.50 else "fail"
        return {
            **common, "status": "ok", "n_scanned_frames": int(n_frames),
            "best_channel": int(np.argmax(channel_power)), "hr_channel": int(hr_ch), "hr_bin": int(hr_bin),
            "hr_bin_distance_m": round(float(hr_bin * algo.SDK_DEFAULT_BIN_SPACING_M), 3),
            "phase_stability": round(float(hr_summary["best_hr_phase_stability"]), 4),
            "quality_window_count": len(stds),
            "std_mm_median": round(float(np.median(values)), 6),
            "std_mm_p25": round(float(np.percentile(values, 25)), 6),
            "std_mm_p75": round(float(np.percentile(values, 75)), 6),
            "usable_ratio": round(usable_ratio, 4),
            "signal_existence_level": level,
            "quality_rule": "心跳带通位移10秒窗 std >= 0.0005 mm；仅为信号存在性，不验证生理数值准确度",
        }
    except Exception as exc:  # 逐段记录而非中断全批。
        return {**common, "status": "error", "error": f"{type(exc).__name__}: {exc}"}


def write_outputs(rows: list[dict], records: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "segment_quality.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    fieldnames = sorted({key for row in rows for key in row})
    with (output_dir / "segment_quality.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    ok = [row for row in rows if row["status"] == "ok"]
    task = [row for row in ok if row["layer"] == "task"]
    baseline = [row for row in ok if row["layer"] == "baseline"]
    counts = {level: sum(row.get("signal_existence_level") == level for row in task) for level in ("pass", "partial", "fail")}
    summary = {
        "scope": "仅 behavior_time_gate 映射的 baseline 与正式 block；不含练习、说明、休息和收尾",
        "quality_boundary": "此处仅评估毫米波心跳带通位移信号存在性；不构成 ECG 准确性或 HRV 有效性结论",
        "records_included": sum(record["status"] == "included" for record in records),
        "segments_total": len(rows), "segments_ok": len(ok), "segments_error": len(rows) - len(ok),
        "task_segments": len(task), "baseline_segments": len(baseline),
        "task_signal_existence_counts": counts,
        "task_usable_ratio_median": round(float(np.median([row["usable_ratio"] for row in task])), 4) if task else None,
        "baseline_usable_ratio_median": round(float(np.median([row["usable_ratio"] for row in baseline])), 4) if baseline else None,
    }
    (output_dir / "segment_quality_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, nargs="+", default=DEFAULT_ROOTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--subjects", nargs="*", help="可选，被试编号，例如 056 011")
    parser.add_argument("--layers", choices=["all", "task", "baseline"], default="all")
    args = parser.parse_args()
    records = gate.discover_records(args.roots)
    if args.subjects:
        selected = {item.zfill(3) for item in args.subjects}
        records = [record for record in records if record["subject_id"] in selected]
    rows: list[dict] = []
    included = [record for record in records if record["status"] == "included"]
    for index, record in enumerate(included, start=1):
        segments = [record["baseline"], *record["blocks"]]
        if args.layers != "all":
            segments = [segment for segment in segments if segment["layer"] == args.layers]
        print(f"[{index}/{len(included)}] {record['source_tag']} {record['subject']}：{len(segments)} 段", flush=True)
        for segment in segments:
            row = scan_segment(record, segment)
            rows.append(row)
            print(f"  {segment['label']}: {row['status']} {row.get('signal_existence_level', row.get('error'))}", flush=True)
            write_outputs(rows, records, args.output_dir)  # 允许中断后保留已完成段。
    write_outputs(rows, records, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
