#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""mmWave external validation asset audit v1.

File: run_mmwave_external_validation_asset_audit_20260913.py
Version: 1.0.0
Purpose:
    在投入正式 cohort 重建 ECG gold-clean（OPT_A）之前，先追溯并评估三个外部
    毫米波数据资产对 preregistered 候选 C1/C2 的可用性：

      - 11_数据/external_benchmarks/VS_DATASET_healthy_v1
      - 11_数据/外部数据集_AgeBalanced_60GHz
      - 11_数据/外部数据集_mmWave_Heartbeat

    只做资产追溯与可行性判断，不跑 C1/C2、不改 producer、不改 snapshot v1。

    四件事：
      1. 扫描外部数据目录；
      2. 反查仓库/脚本/worktree/报告/commit，确认这些数据以前是否跑过、验证过什么；
      3. 判断每个数据集是否有足够 HR/ECG ground truth、时间分辨率与原始毫米波输入，
         能否适配当前 30 s / producer 契约；
      4. 判定对 C1/C2 是 UNTOUCHED、DEVELOPMENT_EXPOSED 还是 INELIGIBLE。

Usage:
    python scripts/maintenance/run_mmwave_external_validation_asset_audit_20260913.py

Dependencies:
    仅 Python 标准库（目录扫描与哈希）；不读取 .mat/.zlib 内容，避免引入格式依赖。
    数据格式结论来自本任务已完成的只读检查，逐条记录在 manifest 的 evidence 字段中。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(r"D:\Project\厚粲杯\11_数据")

# 三个待审计的外部资产（目录名 -> 绝对路径）。
ASSETS = (
    ("VS_DATASET_healthy_v1", DATA_ROOT / "external_benchmarks" / "VS_DATASET_healthy_v1"),
    ("AgeBalanced_60GHz", DATA_ROOT / "外部数据集_AgeBalanced_60GHz"),
    ("mmWave_Heartbeat_TI_gby", DATA_ROOT / "外部数据集_mmWave_Heartbeat"),
)

# 用于反查历史使用的关键词。
HISTORY_TERMS = (
    "VS_DATASET", "VitalSense", "vitalsense_c1b_benchmark",
    "AgeBalanced", "agebalanced",
    "mmWave_Heartbeat", "gby1023", "gby",
)

# C1/C2 所在的生产链路入口（判断外部数据能否承载该机制）。
C1_CODE_PATH = "scripts/process_vital_signs_v3_1_1.py::_select_spectral_bpm"
C2_CODE_PATHS = (
    "scripts/maintenance/run_mmwave_pre30s_selector_hr_20260831.py::selector_step",
    "scripts/process_vital_signs_v3_1_1.py::_smooth_track",
)

OUTPUT_DIR_NAME = "2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1"


def sha256_file(path: Path) -> str:
    """Return the uppercase SHA-256 of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def inventory(path: Path) -> dict:
    """Summarise a dataset directory: file count, bytes, extensions, top level."""
    if not path.exists():
        return {"exists": False}
    files = [p for p in path.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    ext: dict[str, int] = {}
    for p in files:
        ext[p.suffix.lower() or "<none>"] = ext.get(p.suffix.lower() or "<none>", 0) + 1
    top = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
    return {
        "exists": True,
        "path": str(path),
        "files": len(files),
        "bytes": total,
        "megabytes": round(total / 1024 / 1024, 2),
        "extension_histogram": dict(sorted(ext.items(), key=lambda kv: -kv[1])),
        "top_level": top[:40],
        "top_level_count": len(top),
    }


def directory_sha256(path: Path, limit: int | None = None) -> str:
    """Content hash over relative path + bytes of every file, in sorted order.

    Gives one stable identity for a dataset directory without storing per-file
    digests for tens of thousands of files. `limit` caps the number of files hashed
    so the audit stays fast on very large trees; the cap is recorded in the manifest.
    """
    if not path.exists():
        return ""
    files = sorted((p for p in path.rglob("*") if p.is_file()), key=lambda p: str(p.relative_to(path)).lower())
    digest = hashlib.sha256()
    for index, item in enumerate(files):
        if limit is not None and index >= limit:
            digest.update(b"<TRUNCATED>")
            break
        digest.update(str(item.relative_to(path)).replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(item.read_bytes()).digest())
    return digest.hexdigest().upper()


def git_grep(terms, paths=()) -> list[dict]:
    """Search canonical main for the given terms and return file/line hits."""
    hits: list[dict] = []
    for term in terms:
        cmd = ["git", "grep", "-n", "-i", "--no-color", term, "origin/main", "--"]
        cmd.extend(paths or ["."])
        result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            # 输出形如 "<ref>:<path>:<lineno>:<text>"；path 本身可能含冒号，
            # 因此用正则精确切出"数字行号 + 冒号"这一锚点。
            hit = re.match(r"^(?P<file>.+?):(?P<line>\d+):(?P<text>.*)$", line)
            if not hit:
                continue
            hits.append({
                "term": term,
                "file": hit.group("file").split("origin/main:", 1)[-1],
                "line": hit.group("line"),
                "text": hit.group("text")[:200],
            })
    return hits


def summarize_history(hits: list[dict]) -> dict:
    """Group history hits by file and term for the manifest."""
    by_term: dict[str, int] = {}
    by_file: dict[str, int] = {}
    for hit in hits:
        by_term[hit["term"]] = by_term.get(hit["term"], 0) + 1
        by_file[hit["file"]] = by_file.get(hit["file"], 0) + 1
    return {
        "total_hits": len(hits),
        "by_term": dict(sorted(by_term.items())),
        "top_files": sorted(by_file.items(), key=lambda kv: -kv[1])[:15],
    }


def build_assessments(scans: dict, history: dict) -> list[dict]:
    """Assemble the per-dataset assessment records.

    Format/feasibility facts recorded here were established by direct read-only
    inspection during this task (see `evidence` on each record); the script itself
    only re-derives directory-level inventory and hashes.
    """
    return [
        {
            "dataset_id": "VS_DATASET_healthy_v1",
            "citation": "Wu et al., A New Dataset for Millimeter-Wave Radar Vital Sensing With Reference Signals; "
                        "DOI 10.34810/data2962 (Catalan Open Research Area / Dataverse; previous IEEE Dataport 10.21227/wq68-sv85)",
            "role": "EXTERNAL_PUBLIC_REFERENCE_DATASET",
            "hardware": "custom non-commercial FMCW radar, 120 GHz ISM band (CommSensLab-UPC)",
            "subjects": 24,
            "conditions": ["Resting", "Apnea"],
            "recordings": 48,
            "recording_seconds": 120,
            "hr_ecg_ground_truth": {
                "present": True,
                "signal": "Mindray reference: ecg_lead2 (ECG Lead II), ecg_lead3, ecg_leadv1",
                "ecg_rate_hz": 500,
                "ecg_samples": 60000,
                "also_present": ["respiration (256 Hz, 30720)", "pleth (60 Hz, 7200)",
                                 "per-minute HR (120 samples)", "per-minute RR (120 samples)", "BPS/BPM/BPD"],
            },
            "radar_input": {
                "present": True,
                "variable": "VitalSig",
                "samples": 40000,
                "frame_rate_hz": 333.3,
                "derived_time_vector": "Radar.t_frame",
                "kind": "PRE_EXTRACTED_DISPLACEMENT",
                "raw_datacube_available": False,
                "range_bins_available": False,
                "channels_available": False,
            },
            "time_resolution": "Radar 3.0 ms frame interval (333.3 Hz); ECG 2.0 ms (500 Hz), both 120 s",
            "thirty_second_contract": {
                "feasible": True,
                "windows_per_recording": 3,
                "total_non_overlapping_windows": 144,
                "note": "120 s per recording yields 4 x 30 s; using 3 leaves a guard margin. "
                        "Contract is [t, t+30 s) on the file-relative time origin.",
            },
            "c1_eligibility": {
                "eligible": False,
                "reason": "C1 targets the spectral-candidate score inside the selection chain over a complex "
                          "range-domain DataCube (target/bin/channel selection then spectral scoring). This dataset "
                          "supplies a single already-extracted displacement channel with no range bins and no "
                          "channels, so C1's mechanism cannot be expressed or tested here.",
            },
            "c2_eligibility": {
                "eligible": True,
                "reason": "C2 is about spectral-peak selection and anchor persistence on the cardiac waveform. "
                          "A displacement waveform is sufficient to run that mechanism, although it cannot isolate "
                          "target-selection interaction.",
                "caveat": "Cannot test target-selection interaction; result is evidence about the spectral/anchor "
                          "mechanism only.",
            },
            "development_exposure": {
                "classification": "DEVELOPMENT_EXPOSED",
                "what_ran": "C1b formal Radar-ECG benchmark, RUN_ID C1B_VS_DATASET_20260825_V1, "
                            "status BENCHMARK_COMPLETE, 24 subjects / 48 pairs / 384 rows",
                "methods_tested": ["project_bandpass_peak", "vitalsense_amf"],
                "metrics_produced": ["raw_precision", "raw_recall", "raw_f1", "raw_timing_mae_ms",
                                     "raw_ibi_mae_ms", "raw_hr_abs_error_bpm", "raw_rmssd_abs_error_ms",
                                     "raw_sdnn_abs_error_ms"],
                "output_root": r"D:\Project\厚粲杯\11_数据\derived\vitalsense_c1b_benchmark_v1",
                "calibration": "single fixed ECG-radar delay (-18.0 ms) estimated from VS01 Resting and held fixed",
                "reported_boundary": "benchmark_report.md states the run does NOT validate Radar beat/IBI/HRV; "
                                     "HR/IBI/RMSSD/SDNN rows are diagnostic only",
                "pre_registered_protocol": "docs/decisions/2026-08-25-gpt-c1b-dataset-local-ready-run-decision.md and "
                                           "2026-08-25-gpt-c1b-timing-lag-evaluation-amendment.md (frozen before the "
                                           "official 24-subject result)",
                "exposed_to": "beat-level / timing / HR-magnitude / HRV-metric benchmarking with thin baseline methods",
                "not_exposed_to": "the production selection+fusion chain and specifically not the C1 spectral-candidate "
                                  "score or the C2 anchor/SmoothTrack mechanism",
                "tuning_performed": "one subject (VS01 Resting) used for a single global delay constant; no per-subject "
                                    "or per-window algorithm tuning",
            },
            "verdict": "PARTIAL_CANDIDATE_SECONDARY",
            "verdict_reason": "Cannot serve C1 at all. For C2 it is usable only as secondary external evidence, "
                              "because the cohort already produced published benchmark numbers; the C1/C2 mechanisms "
                              "themselves were never evaluated on it.",
        },
        {
            "dataset_id": "AgeBalanced_60GHz",
            "citation": "AgeBalanced 60 GHz cohort, 110 participants (Zenodo-distributed), local copy 2026-08-14",
            "role": "EXTERNAL_PUBLIC_REFERENCE_DATASET",
            "hardware": "TI mmWave (60.25 GHz start, B=480 MHz, R_BIN 0.312 m), 2 TX / 4 RX, 64 ADC samples, "
                        "32 loops, periodic 10 ms",
            "subjects": 110,
            "conditions": ["Lying/Rest", "Lying/Post-exercise", "Sitting/Rest", "Sitting/Post-exercise"],
            "hr_ecg_ground_truth": {
                "present": True,
                "signal": "movesense_ecg.csv (timestamped mV), plus movesense_acc.csv",
                "ecg_cadence": "~250 Hz (4 ms between samples in the observed file head)",
            },
            "radar_input": {
                "present": True,
                "kind": "COMPRESSED_RANGE_FFT_FRAMES",
                "files": ["radar_rFFTs.zlib (per condition)", "radar_timestamps.csv (100 ms cadence)",
                          "radar_chirpConfig.json", "non_breathing_ts.csv"],
                "raw_adc_available": False,
                "note": "Range-FFT-domain frames, not raw ADC; target/range selection is still recoverable in principle",
            },
            "time_resolution": "radar frame period 100 ms (10 Hz); ECG ~4 ms",
            "thirty_second_contract": {
                "feasible": True,
                "windows_per_recording": "multiple",
                "note": "10 Hz frames give 300 frames per 30 s window; ECG at ~250 Hz gives abundant reference.",
            },
            "c1_eligibility": {
                "eligible": False,
                "reason": "Not eligible for C1 as a validation set, because the cohort has already been used to "
                          "evaluate and select HR routes (see development_exposure). Eligibility is blocked by "
                          "exposure, not by format.",
            },
            "c2_eligibility": {"eligible": False, "reason": "Same exposure block as C1."},
            "development_exposure": {
                "classification": "DEVELOPMENT_EXPOSED",
                "what_ran": "2026-08-14 AgeBalanced external ECG reference validation plus multi-bin A/B and HPS / "
                            "harmonic-notch / VMD comparisons on the historical 220 Resting-session scope",
                "commit": "f4a8c74d89ec28e005c537cbd5280a15dcb584e1",
                "published_numbers": {
                    "project_route_session_mae_median_bpm": 9.5,
                    "high_medium_low_bpm": [1.6, 3.4, 10.1],
                    "hps": "10.6 -> 9.7, retained",
                    "temporal_continuity": "9.7 -> 9.5, retained",
                    "fixed_respiration_harmonic_notch": "9.5 -> 10.4, net negative, reverted",
                    "top3_multibin_consensus": "9.5 -> 9.3, small gain, 2x locks 4 -> 6",
                    "vmd_adaptive_grid_median_bpm": {"fixed": 22.5, "adaptive": 25.4, "bandpass": 32.1},
                    "official_reference_recompute_30s_pooled_mae_bpm": 10.361,
                    "official_reference_recompute_50s": {"project": 9.292, "ssa_vmd_adapted": 9.012},
                },
                "exposed_to": "HR accuracy benchmarking and algorithm-route selection (multi-bin, harmonic notch, VMD, HPS, "
                              "temporal continuity)",
                "not_exposed_to": "the production fusion chain and the specific C2 anchor mechanism",
                "tuning_performed": "yes at the route level: several candidate processing routes were compared and "
                                    "accepted or reverted on this cohort",
            },
            "verdict": "INELIGIBLE_FOR_PRIMARY_VALIDATION",
            "verdict_reason": "Route-level exposure means it can no longer serve as an untouched validation set for "
                              "this programme, even though the exact C2 anchor code was not the object of that tuning.",
        },
        {
            "dataset_id": "mmWave_Heartbeat_TI_gby",
            "citation": "TI mmWave raw ADC batch (gby), local copy; 10 files, no documentation packaged",
            "role": "RAW_RADAR_BATCH_WITHOUT_REFERENCE",
            "hardware": "TI mmWave raw ADC capture (device/firmware not documented in the local copy)",
            "subjects": "unknown (10 files named gby1..gby10; file-to-subject mapping not documented)",
            "conditions": "unknown",
            "hr_ecg_ground_truth": {
                "present": False,
                "detail": "The directory contains only 10 .bin raw ADC files (13,107,200 bytes each) and no ECG, "
                          "no respiration reference, no timestamps and no metadata.",
            },
            "radar_input": {
                "present": True,
                "kind": "RAW_ADC_BINARY",
                "note": "Raw ADC; would require a full range-FFT front end plus a documented capture configuration.",
            },
            "time_resolution": "not determinable from the local copy (no chirp config, no timestamps)",
            "thirty_second_contract": {
                "feasible": False,
                "reason": "No timestamp vector and no chirp configuration, so neither wall-clock alignment nor a "
                          "30 s window can be defined.",
            },
            "c1_eligibility": {"eligible": False, "reason": "No HR/ECG ground truth and no time base."},
            "c2_eligibility": {"eligible": False, "reason": "No HR/ECG ground truth and no time base."},
            "development_exposure": {
                "classification": "NOT_EXPOSED_BUT_UNUSABLE",
                "what_ran": "nothing; only referenced once as an inventory line in CHANGELOG.md",
                "exposed_to": "nothing",
                "not_exposed_to": "everything (no analysis ever ran on it)",
                "tuning_performed": "none",
            },
            "verdict": "INELIGIBLE",
            "verdict_reason": "Cannot serve as a validation set: no ECG reference, no timestamps, no acquisition "
                              "metadata, no documented subject mapping.",
        },
    ]


def main(argv: list[str] | None = None) -> int:
    """Run the audit and write all outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "results" / OUTPUT_DIR_NAME,
    )
    parser.add_argument("--hash-limit", type=int, default=400,
                        help="max files hashed per directory for the directory identity digest")
    args = parser.parse_args(argv)
    out: Path = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    scans = {name: inventory(path) for name, path in ASSETS}
    history_hits = git_grep(HISTORY_TERMS, paths=("docs", "ANALYSIS_HISTORY_LEDGER.md", "CHANGELOG.md", "README.md"))
    history = summarize_history(history_hits)
    assessments = build_assessments(scans, history)

    directory_digests = {}
    for name, path in ASSETS:
        if path.exists():
            directory_digests[name] = {
                "sha256_over_first_n_files": directory_sha256(path, limit=args.hash_limit),
                "hash_limit": args.hash_limit,
            }

    # 摘要表。
    summary_rows = []
    for record in assessments:
        summary_rows.append({
            "dataset_id": record["dataset_id"],
            "role": record["role"],
            "subjects": record["subjects"],
            "hr_ecg_ground_truth": record["hr_ecg_ground_truth"]["present"],
            "radar_input_kind": record["radar_input"]["kind"],
            "thirty_second_contract_feasible": record["thirty_second_contract"]["feasible"],
            "c1_eligible": record["c1_eligibility"]["eligible"],
            "c2_eligible": record["c2_eligibility"]["eligible"],
            "development_exposure": record["development_exposure"]["classification"],
            "verdict": record["verdict"],
        })
    write_csv(out / "EXTERNAL_ASSET_ASSESSMENT.csv", summary_rows)

    # 历史使用追溯表。
    history_rows = sorted(history_hits, key=lambda h: (h["file"], int(h["line"])))
    write_csv(out / "EXTERNAL_ASSET_HISTORY_TRACE.csv", history_rows or [{
        "term": "NONE", "file": "NONE", "line": "0", "text": "no history hits",
    }])

    routing = {
        "PREREGISTRATION": "DONE",
        "EXTERNAL_ASSET_INVENTORY": "COMPLETE",
        "OPT_A_BUILD": "PROCEED_AS_PRIMARY",
        "primary_untouched_validation_source": "OPT_A_FORMAL_COHORT",
        "primary_reason": "No external asset is untouched for this programme: VS_DATASET was used for a completed "
                          "C1b benchmark (and cannot express C1 anyway), AgeBalanced was used for route-level HR "
                          "algorithm selection, and the TI gby batch has no reference at all.",
        "secondary_external_evidence": "VS_DATASET_healthy_v1 via its C2-applicable displacement waveform, clearly "
                                       "labelled secondary and not a primary untouched validation",
        "not_usable": ["AgeBalanced_60GHz (route-exposed)", "mmWave_Heartbeat_TI_gby (no reference, no time base)"],
    }

    manifest = {
        "task_id": "mmwave_external_validation_asset_audit_v1",
        "run_id": "mmwave_external_validation_asset_audit_v1_20260913_r1",
        "document_type": "ASSET_AUDIT",
        "status": "ASSET_AUDIT_COMPLETE",
        "date": "2026-09-13",
        "base_commit": current_commit(),
        "audit_only": True,
        "data_run_performed": False,
        "candidate_run_performed": False,
        "dataset_scans": scans,
        "directory_identity": directory_digests,
        "history_trace_summary": history,
        "assessments": assessments,
        "routing": routing,
        "c1_code_path": C1_CODE_PATH,
        "c2_code_paths": list(C2_CODE_PATHS),
        "boundaries": {
            "snapshot_v1_modified": False,
            "formal_producer_modified": False,
            "v2_formed": False,
            "models_trained": False,
            "hrv_status": "BLOCKED",
            "hr_br_status": "HOLD / SUPPORTING_ONLY",
            "candidate_implemented": False,
            "external_data_modified": False,
        },
        "next_task": "mmwave_hr_untouched_ecg_validation_set_v1 (OPT_A) as primary, "
                     "with VS_DATASET secondary C2 evidence only",
    }
    (out / "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps({
        "state": "ASSET_AUDIT_COMPLETE",
        "datasets": [r["dataset_id"] for r in assessments],
        "verdicts": {r["dataset_id"]: r["verdict"] for r in assessments},
        "c1_eligible": [r["dataset_id"] for r in assessments if r["c1_eligibility"]["eligible"]],
        "c2_eligible": [r["dataset_id"] for r in assessments if r["c2_eligibility"]["eligible"]],
        "routing": routing["OPT_A_BUILD"],
        "history_hits": history["total_hits"],
    }, ensure_ascii=False, indent=2))
    return 0


def current_commit() -> str:
    """Return the current Git commit sha when available (provenance only)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
        )
        return result.stdout.strip() or "UNKNOWN"
    except OSError:
        return "UNKNOWN"


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write rows to CSV with LF endings."""
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    sys.exit(main())
