"""行为时间门控的毫米波质量批处理入口。

默认只生成裁剪清单，不读取 npz 波形。传入 --run-analysis 后，算法也只会对
baseline 或单个正式 block 的明确帧范围运行，绝不以整段原始记录为输入。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import median

import behavior_time_gate as gate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "08_算法" / "output" / "质量分析_行为裁剪_v1"
DEFAULT_ROOTS = [Path(r"E:\Data"), Path(r"F:\正式实验")]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_manifest(records: list[dict], output_dir: Path) -> dict:
    summary = {
        "policy": {
            "task_scope": "每个正式 block_start 至 block_stop 的并集；每个 block 独立分析，不跨休息段拼接",
            "baseline_scope": "baseline_start 至 baseline_stop，独立层，不混入任务质量",
            "probe_trial_scope": "后续探针/试次分析必须在 block 内继续依据行为 CSV 时间戳切窗",
            "sub_099": "待复核，排除主队列",
        },
        "n_records": len(records),
        "n_included": sum(item["status"] == "included" for item in records),
        "n_excluded_invalid": sum(item["status"] == "excluded_invalid" for item in records),
        "n_excluded_review": sum(item["status"] == "excluded_review" for item in records),
        "task_block_distribution": {},
    }
    for record in records:
        if record["status"] == "included":
            key = str(record["task_block_count"])
            summary["task_block_distribution"][key] = summary["task_block_distribution"].get(key, 0) + 1
    write_json(output_dir / "crop_manifest.json", records)
    write_json(output_dir / "crop_summary.json", summary)
    fields = [
        "source_tag", "subject", "status", "task_block_count", "crop_start_ms", "crop_end_ms",
        "task_retained_frames", "task_retained_duration_s", "baseline_retained_frames",
        "baseline_retained_duration_s", "retained_frames", "retained_duration_s", "excluded_frames",
        "excluded_duration_s", "timeline_path", "timestamp_path", "exclusion_note", "exclusion_reasons", "blocks",
    ]
    with (output_dir / "crop_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["exclusion_reasons"] = "；".join(record.get("exclusion_reasons", []))
            row["blocks"] = json.dumps(record.get("blocks", []), ensure_ascii=False)
            writer.writerow(row)
    return summary


def _segment_output_dir(output_dir: Path, record: dict, segment: dict) -> Path:
    return output_dir / "segments" / record["source_tag"] / record["subject"] / segment["layer"] / segment["label"]


def run_analysis(records: list[dict], output_dir: Path, method: str) -> list[dict]:
    import process_vital_signs_v3_1_1 as algo

    analyses: list[dict] = []
    for record in records:
        if record["status"] != "included":
            continue
        segments = [record["baseline"], *record["blocks"]]
        segment_results: list[dict] = []
        for segment in segments:
            result, _ = algo.analyze_long_record(
                parts_dir=Path(record["mmwave_dir"]),
                output_dir=_segment_output_dir(output_dir, record, segment),
                session=f"{record['subject']}_ses-SART",
                pattern=f"{record['subject']}_mmwave_datacube_part*.npz",
                method=method,
                frame_start=int(segment["frame_start"]),
                frame_end=int(segment["frame_end"]),
            )
            segment_results.append({
                "layer": segment["layer"],
                "label": segment["label"],
                "frame_start": segment["frame_start"],
                "frame_end": segment["frame_end"],
                "frame_count": segment["frame_count"],
                "retained_duration_s": segment["retained_duration_s"],
                "heart_rate": result.get("heart_rate", {}),
                # v3.1.1 formal producer's public result schema is ``breath_rate``.
                # Keep the summary key aligned with that producer key so a runner
                # invocation cannot silently discard the already-produced BR fields.
                "breath_rate": result.get("breath_rate", {}),
                "quality": result.get("quality", {}),
            })
        task_results = [item for item in segment_results if item["layer"] == "task"]
        analyses.append({
            "source_tag": record["source_tag"],
            "subject": record["subject"],
            "segments": segment_results,
            "task_aggregate_rule": "仅汇总 block 级质量；不跨 block 合并 IBI 或 HRV",
            "task_block_count": len(task_results),
        })
    write_json(output_dir / "segment_analysis_summary.json", analyses)
    return analyses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--roots", type=Path, nargs="+", default=DEFAULT_ROOTS)
    parser.add_argument("--subjects", nargs="*", help="仅处理指定编号，例如 056 011")
    parser.add_argument("--run-analysis", action="store_true", help="对清单中的每个独立裁剪段运行算法")
    parser.add_argument("--method", default="vmd_heart", help="生命体征方法；默认 vmd_heart，可用 bp_heart 做环境冒烟")
    args = parser.parse_args()
    records = gate.discover_records(args.roots)
    if args.subjects:
        selected = {item.zfill(3) for item in args.subjects}
        records = [item for item in records if item["subject_id"] in selected]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = write_manifest(records, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.run_analysis:
        analyses = run_analysis(records, args.output_dir, args.method)
        print(f"已完成独立裁剪段分析：{len(analyses)} 名被试")
    else:
        print("仅生成裁剪清单，未读取 npz 原始波形。需要分段分析时显式传入 --run-analysis。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
