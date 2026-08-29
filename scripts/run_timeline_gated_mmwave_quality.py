"""行为时间门控的毫米波质量批处理入口。

默认只生成裁剪清单，不读取 npz 波形。传入 --run-analysis 后，算法也只会对
baseline 或单个正式 block 的明确帧范围运行，绝不以整段原始记录为输入。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path

import behavior_time_gate as gate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "08_算法" / "output" / "质量分析_行为裁剪_v1"
DEFAULT_ROOTS = [Path(r"E:\Data"), Path(r"F:\正式实验")]
SCHEMA_VERSION = "mmwave_segment_analysis_v1"
PIPELINE_VERSION = "v3.1.1-contract.1"
SUPPORTED_METHODS = ("vmd_heart", "bp_heart")
VMDPY_VERSION = "0.2"


class MethodPreflightError(RuntimeError):
    pass


def _strict_json_value(value):
    if isinstance(value, dict):
        return {str(key): _strict_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strict_json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return [_strict_json_value(item) for item in value.tolist()]
        if isinstance(value, np.generic):
            return _strict_json_value(value.item())
    except ImportError:
        pass
    return value


def strict_json_dumps(payload: object, **kwargs) -> str:
    return json.dumps(_strict_json_value(payload), allow_nan=False, **kwargs)


def prepare_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"OUTPUT_DIRECTORY_NOT_EMPTY: {path}")
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_state(name: str, required_version: str | None = None) -> dict:
    installed = importlib.util.find_spec(name) is not None
    version = None
    if installed:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
    return {"package": name, "installed": installed, "version": version,
            "required_version": required_version,
            "version_ok": installed and (required_version is None or version == required_version)}


def method_preflight(method: str) -> dict:
    if method not in SUPPORTED_METHODS:
        return {"status": "blocked", "requested_method": method, "selected_method": None,
                "fallback_used": False, "failure_reason": "UNSUPPORTED_METHOD", "dependencies": []}
    dependencies = [_package_state("numpy"), _package_state("scipy")]
    failure_reason = None
    backend = "scipy_bandpass"
    if method == "vmd_heart":
        backend = "vmdpy"
        vmdpy = _package_state("vmdpy", VMDPY_VERSION)
        dependencies.append(vmdpy)
        if not vmdpy["installed"]:
            failure_reason = "MISSING_VMDPY_DEPENDENCY"
        elif not vmdpy["version_ok"]:
            failure_reason = "VMDPY_VERSION_MISMATCH"
        else:
            try:
                if not callable(getattr(importlib.import_module("vmdpy"), "VMD", None)):
                    failure_reason = "VMDPY_VMD_SYMBOL_UNAVAILABLE"
            except Exception as exc:
                failure_reason = f"VMDPY_IMPORT_FAILED:{type(exc).__name__}"
    elif not all(item["installed"] for item in dependencies):
        failure_reason = "MISSING_BP_HEART_DEPENDENCY"
    return {"status": "pass" if failure_reason is None else "blocked",
            "requested_method": method, "selected_method": method if failure_reason is None else None,
            "backend": backend, "fallback_used": False, "failure_reason": failure_reason,
            "dependencies": dependencies,
            "python": {"executable": sys.executable, "version": platform.python_version()}}


def load_input_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"INPUT_MANIFEST_NOT_FOUND: {path}")
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = [dict(row) for row in csv.DictReader(handle)]
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("sessions") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("INPUT_MANIFEST_HAS_NO_SESSIONS")
    seen = set()
    normalized = []
    for raw in rows:
        session_id = str(raw.get("session_id") or raw.get("subject") or "").strip().lower()
        if session_id and not session_id.startswith("sub-"):
            session_id = f"sub-{session_id.zfill(3)}"
        group_id = str(raw.get("anonymous_participant_group_id") or "").strip()
        if not session_id:
            raise ValueError("INPUT_MANIFEST_MISSING_SESSION_ID")
        if not group_id:
            raise ValueError(f"INPUT_MANIFEST_MISSING_ANONYMOUS_GROUP:{session_id}")
        if session_id in seen:
            raise ValueError(f"INPUT_MANIFEST_DUPLICATE_SESSION:{session_id}")
        seen.add(session_id)
        row = dict(raw)
        row.update(session_id=session_id, anonymous_participant_group_id=group_id)
        normalized.append(row)
    return normalized


def apply_input_manifest(discovered: list[dict], rows: list[dict]) -> list[dict]:
    by_session = {}
    for record in discovered:
        by_session.setdefault(record["subject"].lower(), []).append(record)
    records = []
    for row in rows:
        matches = by_session.get(row["session_id"], [])
        requested_tag = str(row.get("source_tag") or "").strip()
        if requested_tag:
            matches = [item for item in matches if item["source_tag"] == requested_tag]
        if len(matches) > 1:
            raise ValueError(f"INPUT_MANIFEST_AMBIGUOUS_SESSION:{row['session_id']}")
        record = dict(matches[0]) if matches else {
            "source_tag": requested_tag or "manifest", "subject": row["session_id"],
            "subject_id": row["session_id"].removeprefix("sub-"), "status": "excluded_invalid",
            "exclusion_note": "MANIFEST_SESSION_NOT_DISCOVERED"}
        record.update(session_id=row["session_id"], site=row.get("site"),
                      anonymous_participant_group_id=row["anonymous_participant_group_id"],
                      repeat_participant_id=row.get("repeat_participant_id"),
                      identity_status=row.get("identity_status"), manifest_source_ref=row.get("source_ref"))
        records.append(record)
    return records


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(strict_json_dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_manifest(records: list[dict], output_dir: Path, input_manifest: dict | None = None) -> dict:
    if not records:
        raise ValueError("EMPTY_RECORD_SET_REFUSES_OUTPUT")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "input_manifest": input_manifest,
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
        "source_tag", "site", "session_id", "subject", "anonymous_participant_group_id",
        "repeat_participant_id", "identity_status", "status", "task_block_count", "crop_start_ms", "crop_end_ms",
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
            row["blocks"] = strict_json_dumps(record.get("blocks", []), ensure_ascii=False)
            writer.writerow(row)
    return summary


def _segment_output_dir(output_dir: Path, record: dict, segment: dict) -> Path:
    return output_dir / "segments" / record["source_tag"] / record["subject"] / segment["layer"] / segment["label"]


def _status_layers(result: dict, quality_valid: bool) -> dict:
    heart = result.get("heart_rate") or {}
    breath = result.get("breath_rate") or {}
    hrv = result.get("hrv") or {}
    signal_pass = bool((heart.get("time_course") or {}).get("signal_quality", {}).get("hard_gate_passed", False))
    hr_computed = any(heart.get(key) is not None for key in ("freq_bpm", "time_bpm", "fused_bpm"))
    br_computed = any(breath.get(key) is not None for key in ("freq_bpm", "time_bpm"))
    hrv_computed = any(hrv.get(key) is not None for key in ("mean_IBI_ms", "SDNN_ms", "RMSSD_ms"))
    common = {"external_validation_status": "not_available",
              "behavior_link_status": "blocked_pending_formal_release", "formal_report_status": "blocked"}
    return {
        "hr": {"computed": hr_computed,
               "engineering_status": "signal_gate_passed" if hr_computed and signal_pass and quality_valid else "rejected", **common},
        "rr_br": {"computed": br_computed,
                  "engineering_status": "computed_pending_engineering_gate" if br_computed and quality_valid else "rejected", **common},
        "ibi_hrv": {"computed": hrv_computed,
                    "engineering_status": "candidate_only" if hrv_computed and quality_valid else "rejected",
                    "external_validation_status": "not_available", "behavior_link_status": "blocked",
                    "formal_report_status": "blocked"},
    }


def _segment_result(record: dict, segment: dict, result: dict, method: str, analysis_id: str) -> dict:
    heart = result.get("heart_rate") or {}
    course = heart.get("time_course") or {}
    quality_valid = bool(result.get("quality_valid", True))
    return {
        "schema_version": SCHEMA_VERSION, "pipeline_version": PIPELINE_VERSION, "analysis_id": analysis_id,
        "site": record.get("site"), "session_id": record.get("session_id", record["subject"]),
        "subject": record["subject"],
        "anonymous_participant_group_id": record.get("anonymous_participant_group_id"),
        "repeat_participant_id": record.get("repeat_participant_id"),
        "identity_status": record.get("identity_status"),
        "layer": segment["layer"], "label": segment["label"],
        "frame_start": segment["frame_start"], "frame_end": segment["frame_end"],
        "frame_count": segment["frame_count"], "retained_duration_s": segment["retained_duration_s"],
        "method": method, "algorithm_returned": bool(result.get("algorithm_returned", True)),
        "quality_valid": quality_valid, "selection_status": result.get("selection_status", "selected"),
        "failure_reason": result.get("failure_reason"),
        "heart_rate": heart, "breath_rate": result.get("breath_rate") or {}, "hrv": result.get("hrv") or {},
        "quality": {"signal_quality": course.get("signal_quality") or {}, "metrics": course.get("metrics") or {}},
        "channel_selection": result.get("channel_selection") or {},
        "status_layers": _status_layers(result, quality_valid),
    }


def _failed_segment(record: dict, segment: dict, method: str, analysis_id: str, exc: Exception) -> dict:
    reason = getattr(exc, "reason", None) or f"{type(exc).__name__}:{exc}"
    item = _segment_result(record, segment, {}, method, analysis_id)
    item.update(algorithm_returned=False, quality_valid=False, selection_status="rejected", failure_reason=reason,
                channel_selection={"candidates": getattr(exc, "summaries", [])})
    return item


def _flat_row(item: dict) -> dict:
    heart, breath, hrv = item["heart_rate"], item["breath_rate"], item["hrv"]
    status = item["status_layers"]
    return {
        "schema_version": item["schema_version"], "pipeline_version": item["pipeline_version"],
        "analysis_id": item["analysis_id"], "site": item.get("site"), "session_id": item["session_id"],
        "subject": item["subject"], "anonymous_participant_group_id": item.get("anonymous_participant_group_id"),
        "repeat_participant_id": item.get("repeat_participant_id"), "segment_label": item["label"],
        "segment_layer": item["layer"], "frame_start": item["frame_start"], "frame_end": item["frame_end"],
        "frame_count": item["frame_count"], "duration_s": item["retained_duration_s"], "method": item["method"],
        "algorithm_returned": item["algorithm_returned"], "quality_valid": item["quality_valid"],
        "selection_status": item["selection_status"], "failure_reason": item.get("failure_reason"),
        "hr_freq_bpm": heart.get("freq_bpm"), "hr_time_bpm": heart.get("time_bpm"),
        "hr_fused_bpm": heart.get("fused_bpm"), "br_freq_bpm": breath.get("freq_bpm"),
        "br_time_bpm": breath.get("time_bpm"), "br_n_peaks": breath.get("n_peaks"),
        "ibi_mean_ms": hrv.get("mean_IBI_ms"), "hrv_sdnn_ms": hrv.get("SDNN_ms"),
        "hrv_rmssd_ms": hrv.get("RMSSD_ms"), "hr_engineering_status": status["hr"]["engineering_status"],
        "br_engineering_status": status["rr_br"]["engineering_status"],
        "ibi_hrv_engineering_status": status["ibi_hrv"]["engineering_status"],
        "external_validation_status": status["hr"]["external_validation_status"],
        "behavior_link_status": status["hr"]["behavior_link_status"],
        "formal_report_status": status["hr"]["formal_report_status"],
    }


def run_analysis(records: list[dict], output_dir: Path, method: str, analysis_id: str,
                 input_manifest: dict, preflight: dict) -> dict:
    import process_vital_signs_v3_1_1 as algo

    included = [record for record in records if record["status"] == "included"]
    if not included:
        raise ValueError("NO_INCLUDED_SESSION_RECORDS")
    analyses: list[dict] = []
    rows = []
    succeeded = failed = 0
    for record in included:
        segments = [record["baseline"], *record["blocks"]]
        segment_results: list[dict] = []
        for segment in segments:
            try:
                result, _ = algo.analyze_long_record(
                    parts_dir=Path(record["mmwave_dir"]), output_dir=_segment_output_dir(output_dir, record, segment),
                    session=f"{record['subject']}_ses-SART", pattern=f"{record['subject']}_mmwave_datacube_part*.npz",
                    method=method, frame_start=int(segment["frame_start"]), frame_end=int(segment["frame_end"]))
                item = _segment_result(record, segment, result, method, analysis_id)
                succeeded += 1
            except Exception as exc:
                item = _failed_segment(record, segment, method, analysis_id, exc)
                failed += 1
            segment_results.append(item)
            rows.append(_flat_row(item))
        task_results = [item for item in segment_results if item["layer"] == "task"]
        analyses.append({
            "source_tag": record["source_tag"], "session_id": record.get("session_id", record["subject"]),
            "subject": record["subject"], "anonymous_participant_group_id": record.get("anonymous_participant_group_id"),
            "repeat_participant_id": record.get("repeat_participant_id"),
            "segments": segment_results,
            "task_aggregate_rule": "仅汇总 block 级质量；不跨 block 合并 IBI 或 HRV",
            "task_block_count": len(task_results),
        })
    payload = {"schema_version": SCHEMA_VERSION, "pipeline_version": PIPELINE_VERSION,
               "analysis_id": analysis_id, "status": "completed" if failed == 0 else "completed_with_failures",
               "method": method, "input_manifest": input_manifest, "preflight": preflight,
               "n_sessions": len(analyses), "n_segments_succeeded": succeeded, "n_segments_failed": failed,
               "records": analyses,
               "scientific_status": {"computability": "reported_per_metric", "engineering_qc": "reported_per_metric",
                                     "external_physiology_validation": "not_available",
                                     "behavior_association": "blocked_pending_formal_release", "formal_report": "blocked"}}
    write_json(output_dir / "segment_analysis_summary.json", payload)
    fields = list(rows[0])
    with (output_dir / "segment_analysis_rows.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--roots", type=Path, nargs="+", default=DEFAULT_ROOTS)
    parser.add_argument("--input-manifest", type=Path, help="冻结的场次和匿名参与者组清单（JSON/CSV）")
    parser.add_argument("--subjects", nargs="*", help="仅限旧版裁剪冒烟；正式运行使用输入 manifest")
    parser.add_argument("--run-analysis", action="store_true", help="对清单中的每个独立裁剪段运行算法")
    parser.add_argument("--preflight-only", action="store_true", help="只检查方法与依赖，不读取本地数据")
    parser.add_argument("--method", choices=SUPPORTED_METHODS, default="vmd_heart")
    parser.add_argument("--analysis-id", default="mmwave_timeline_gated_v1")
    args = parser.parse_args()

    preflight = method_preflight(args.method)
    if args.preflight_only:
        print(strict_json_dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if preflight["status"] == "pass" else 2
    if args.output_dir is None:
        parser.error("--output-dir is required unless --preflight-only is used")
    if args.run_analysis and args.input_manifest is None:
        parser.error("--run-analysis requires --input-manifest")

    discovered = gate.discover_records(args.roots)
    if args.input_manifest is not None:
        rows = load_input_manifest(args.input_manifest)
        records = apply_input_manifest(discovered, rows)
        manifest_meta = {"path": str(args.input_manifest), "sha256": sha256_file(args.input_manifest),
                         "n_sessions": len(rows)}
    else:
        records = discovered
        manifest_meta = {"path": None, "sha256": None, "n_sessions": len(records),
                         "status": "legacy_crop_only"}
    if args.subjects and args.input_manifest is None:
        selected = {item.zfill(3) for item in args.subjects}
        records = [item for item in records if item["subject_id"] in selected]
    if not records:
        raise ValueError("EMPTY_RECORD_SET_REFUSES_OUTPUT")
    if args.run_analysis and not any(record["status"] == "included" for record in records):
        raise ValueError("NO_INCLUDED_SESSION_RECORDS")
    if args.run_analysis and preflight["status"] != "pass":
        raise MethodPreflightError(strict_json_dumps(preflight, ensure_ascii=False))

    prepare_output_dir(args.output_dir)
    summary = write_manifest(records, args.output_dir, manifest_meta)
    print(strict_json_dumps(summary, ensure_ascii=False, indent=2))
    if args.run_analysis:
        analysis = run_analysis(records, args.output_dir, args.method, args.analysis_id, manifest_meta, preflight)
        print(f"已完成独立裁剪段分析：{analysis['n_sessions']} 个场次；失败段={analysis['n_segments_failed']}")
    else:
        print("仅生成裁剪清单，未读取 npz 原始波形。需要分段分析时显式传入 --run-analysis。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
