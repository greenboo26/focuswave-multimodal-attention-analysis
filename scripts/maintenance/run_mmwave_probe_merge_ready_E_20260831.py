"""mmWave probe merge-ready adapter（E 盘批次）。

从 Behavior formal_v3 的 probe_primary_30s.csv 提取 E 盘 session 的 probe，
映射到 canonical 五键（R 格式 repeat_participant_id），复用 J 盘版 adapter 的
完整 selector 链与字段填充逻辑。输出与 J 盘版列结构一致，可拼接。

用法：
    .venv_t0/Scripts/python.exe scripts/maintenance/run_mmwave_probe_merge_ready_E_20260831.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np

ALGO_ROOT = Path(__file__).resolve().parents[2]
J_ADAPTER = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_20260831.py"
PROBE_SOURCE = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\Behavior\formal_v3\probe_primary_30s.csv")
BACKGROUND = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mapping\background_subject_manifest.csv")
MAPPING = Path(
    r"C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave"
    r"\outputs\FocusWave_formal_multimodal_v2_2026-08-30\session_id_mapping.csv"
)
OUT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave")
DATA_ROOTS = (Path(r"E:\正式实验"),)
PRE_WINDOW_MS = 30_000
J_SESSIONS = None  # 延迟加载


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_j_sessions() -> set[str]:
    global J_SESSIONS
    if J_SESSIONS is None:
        timeline = J_ADAPTER and load_module(J_ADAPTER, "j_adapter_for_E")
        J_SESSIONS = {r["session_id"] for r in csv.DictReader(timeline.TIMELINE.open(encoding="utf-8-sig"))}
    return J_SESSIONS


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", nargs="*", default=None, help="只处理指定 session（默认全部 E 盘）")
    args = parser.parse_args()

    j = load_module(J_ADAPTER, "j_adapter_for_E")
    algo = j.load_module(j.PRODUCER, "producer_merge_ready_E")

    # R 格式映射：source_subject_raw -> single_experiment_id -> repeat_participant_id
    bg = {r["session_id"]: r["source_subject_raw"] for r in csv.DictReader(BACKGROUND.open(encoding="utf-8-sig"))}
    mp = {r["single_experiment_id"]: r for r in csv.DictReader(MAPPING.open(encoding="utf-8-sig"))}

    j_sessions = load_j_sessions()
    probe_rows = list(csv.DictReader(PROBE_SOURCE.open(encoding="utf-8-sig")))
    e_rows = [r for r in probe_rows if r["session_id"] not in j_sessions and r["session_id"] in bg]
    sessions = sorted({r["session_id"] for r in e_rows})
    if args.sessions:
        sessions = [s for s in sessions if s in args.sessions]
    print(f"E 盘批次: {len(sessions)} sessions / {len(e_rows)} probe 窗口（排除 J 盘已跑的 {len(j_sessions)} 场）")

    out_rows: list[dict] = []
    skipped_invalid = 0
    for session in sessions:
        mmw_root = None
        for root in DATA_ROOTS:
            d = root / f"{session}_" / "mmwave"
            if d.is_dir():
                mmw_root = d
                break
        session_rows = [r for r in e_rows if r["session_id"] == session]
        previous_by_block: dict[str, float | None] = {}

        if mmw_root is None:
            for row in session_rows:
                out_rows.append(build_base(j, bg, mp, row, "STRUCTURAL_MISSING", False, "no_mmwave_directory"))
            continue
        try:
            timestamps = j.load_timestamps(mmw_root)
            files = j.load_npz_files(mmw_root, session)
        except Exception as exc:
            for row in session_rows:
                out_rows.append(build_base(j, bg, mp, row, "STRUCTURAL_MISSING", False, f"load_failed:{type(exc).__name__}"))
            print(f"{session}: 加载失败 {type(exc).__name__}")
            continue

        valid = 0
        for row in session_rows:
            canonical = to_canonical(bg, mp, row)
            if canonical is None:
                skipped_invalid += 1
                continue
            out_rows.append(j.process_probe(algo, canonical, files, timestamps, previous_by_block))
            valid += 1
        print(f"{session}: 完成 {valid} 窗口")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    fields = j.build_output_fields()
    out_csv = OUT_ROOT / "mmwave_probe_merge_ready_E.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)

    state_counts: dict[str, int] = {}
    for r in out_rows:
        state_counts[r.get("mmwave_state", "?")] = state_counts.get(r.get("mmwave_state", "?"), 0) + 1
    try:
        source_commit = subprocess.check_output(
            ["git", "-C", str(ALGO_ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        source_commit = None
    for r in out_rows:
        r.setdefault("mmwave_source_run_id", "mmwave_probe_merge_ready_E_20260831")
        r.setdefault("mmwave_source_commit", source_commit)
    manifest = {
        "schema": "mmwave_probe_merge_ready_v1",
        "batch": "E_drive",
        "rows": len(out_rows),
        "sessions": len(sessions),
        "state_counts": state_counts,
        "repeat_participant_id_scheme": "R_format_from_session_id_mapping",
        "probe_source": str(PROBE_SOURCE),
        "run_date": "2026-08-31",
    }
    (OUT_ROOT / "mmwave_probe_merge_ready_E_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n输出: {out_csv}")
    print(f"状态分布: {state_counts}")


def build_base(j, bg, mp, row, state, observed, reason) -> dict:
    canonical = to_canonical(bg, mp, row)
    base = canonical or {}
    base.update({"mmwave_state": state, "mmwave_observed": observed, "mmwave_missing_reason": reason})
    return base


def to_canonical(bg: dict, mp: dict, row: dict) -> dict | None:
    session = row["session_id"]
    raw = bg.get(session)
    if not raw:
        return None
    eid = str(int(raw))
    m = mp.get(eid)
    if not m or not m["repeat_participant_id"] or m["site"] != "北京":
        return None
    probe_time_ms = int(float(row["probe_time_ms"]))
    block_id = {"B1": "block-1", "B2": "block-2"}.get(row["block_id"], row["block_id"])
    probe_index = int(row["probe_order_in_block"])
    return {
        "repeat_participant_id": m["repeat_participant_id"],
        "session_id": session,
        "single_experiment_id": eid,
        "site": "北京",
        "block_id": block_id,
        "legacy_block_num": str({"block-1": "1", "block-2": "2"}.get(block_id, "")),
        "probe_id": f"probe-{probe_index:02d}",
        "probe_index_in_block": str(probe_index),
        "probe_index_global": "",
        "legacy_probe_index": "",
        "window_name": "pre_30s",
        "window_start_unix_ms": str(probe_time_ms - PRE_WINDOW_MS),
        "window_end_unix_ms": str(probe_time_ms),
        "window_effective_start_unix_ms": str(probe_time_ms - PRE_WINDOW_MS),
        "probe_onset_unix_ms": str(probe_time_ms),
        "block_start_unix_ms": "",
        "block_end_unix_ms": "",
        "window_truncated_by_block_start": row.get("window_crosses_block", ""),
        "window_boundary_source": "probe_primary_30s",
        "condition": "",
        "label_probe_vigilance": row.get("q2_ordinal_4level", ""),
        "label_probe_response": row.get("q1_nominal_4class", ""),
        "label_probe_rt_ms": "",
        "behavior_available": "True",
        "behavior_source_path": "",
        "behavior_trial_count_pre30s": "",
        "behavior_valid_rt_count_pre30s": "",
        "behavior_rt_median_ms_pre30s": row.get("go_correct_rt_median_ms", ""),
        "behavior_rt_mean_ms_pre30s": row.get("go_correct_rt_mean_ms", ""),
        "behavior_error_rate_pre30s": "",
        "behavior_commission_rate_pre30s": row.get("commission_rate", ""),
        "behavior_omission_rate_pre30s": row.get("omission_rate", ""),
        "behavior_qc_status": "",
    }


if __name__ == "__main__":
    main()
