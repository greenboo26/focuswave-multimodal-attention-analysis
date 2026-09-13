"""E-drive mmWave formal probe adapter under the shared M1 producer contract.

The E batch reuses the J adapter's estimator and frame-selection implementation;
only identity/timeline materialization differs. This guarantees J/E share the same
DLL-time, effective-start, right-open slicing contract.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

ALGO_ROOT = Path(__file__).resolve().parents[2]
J_ADAPTER = (
    ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_20260831.py"
)
PROBE_SOURCE = Path(
    r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\Behavior\formal_v3\probe_primary_30s.csv"
)
BACKGROUND = Path(
    r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mapping\background_subject_manifest.csv"
)
MAPPING = Path(
    r"C:\Users\550ACW\Documents\Codex\2026-08-30\files-pasted-by-the-user-focuswave"
    r"\outputs\FocusWave_formal_multimodal_v2_2026-08-30\session_id_mapping.csv"
)
OUT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave")
DATA_ROOTS = (Path(r"E:\正式实验"),)
PRE_WINDOW_MS = 30_000
RUN_ID = "mmwave_probe_merge_ready_E_contract_m1_20260913"
J_SESSIONS = None


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_j_sessions(j) -> set[str]:
    global J_SESSIONS
    if J_SESSIONS is None:
        J_SESSIONS = {
            row["session_id"]
            for row in csv.DictReader(j.TIMELINE.open(encoding="utf-8-sig"))
        }
    return J_SESSIONS


def _maybe_int(row: dict, key: str) -> int | None:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def to_canonical(bg: dict, mp: dict, row: dict) -> dict | None:
    session = row["session_id"]
    raw = bg.get(session)
    if not raw:
        return None
    eid = str(int(raw))
    mapping = mp.get(eid)
    if (
        not mapping
        or not mapping.get("repeat_participant_id")
        or mapping.get("site") != "北京"
    ):
        return None

    probe_onset = (
        _maybe_int(row, "probe_onset_unix_ms")
        or _maybe_int(row, "probe_time_ms")
    )
    if probe_onset is None:
        raise ValueError(f"{session}: missing probe onset")

    declared_end = _maybe_int(row, "window_end_unix_ms") or probe_onset
    nominal_start = (
        _maybe_int(row, "window_start_unix_ms")
        or _maybe_int(row, "window_nominal_start_unix_ms")
        or probe_onset - PRE_WINDOW_MS
    )
    effective_start = _maybe_int(row, "window_effective_start_unix_ms")
    if effective_start is None:
        if _truthy(row.get("window_crosses_block", "")):
            raise ValueError(
                f"{session}: block-truncated Behavior row lacks "
                "window_effective_start_unix_ms; refusing nominal-start fallback"
            )
        effective_start = nominal_start

    block_id = {"B1": "block-1", "B2": "block-2"}.get(
        row["block_id"], row["block_id"]
    )
    probe_index = int(row["probe_order_in_block"])
    canonical = {
        "repeat_participant_id": mapping["repeat_participant_id"],
        "participant_group_id": row.get(
            "participant_group_id", mapping["repeat_participant_id"]
        ),
        "session_id": session,
        "single_experiment_id": eid,
        "site": "北京",
        "block_id": block_id,
        "legacy_block_num": str(
            {"block-1": "1", "block-2": "2"}.get(block_id, "")
        ),
        "probe_id": f"probe-{probe_index:02d}",
        "probe_index_in_block": str(probe_index),
        "probe_index_global": row.get("probe_index_global", ""),
        "legacy_probe_index": "",
        "window_name": row.get("window_name") or "pre_30s",
        "window_start_unix_ms": str(nominal_start),
        "window_end_unix_ms": str(declared_end),
        "window_effective_start_unix_ms": str(effective_start),
        "probe_onset_unix_ms": str(probe_onset),
        "block_start_unix_ms": row.get("block_start_unix_ms", ""),
        "block_end_unix_ms": row.get("block_end_unix_ms", ""),
        "window_truncated_by_block_start": row.get("window_crosses_block", ""),
        "window_boundary_source": "probe_primary_30s",
        "condition": row.get("condition", ""),
        "label_probe_vigilance": row.get("q2_ordinal_4level", ""),
        "label_probe_response": row.get("q1_nominal_4class", ""),
        "label_probe_rt_ms": "",
        "behavior_available": "True",
        "behavior_source_path": "",
        "behavior_trial_count_pre30s": "",
        "behavior_valid_rt_count_pre30s": "",
        "behavior_rt_median_ms_pre30s": row.get(
            "go_correct_rt_median_ms", ""
        ),
        "behavior_rt_mean_ms_pre30s": row.get("go_correct_rt_mean_ms", ""),
        "behavior_error_rate_pre30s": "",
        "behavior_commission_rate_pre30s": row.get("commission_rate", ""),
        "behavior_omission_rate_pre30s": row.get("omission_rate", ""),
        "behavior_qc_status": "",
    }
    if int(canonical["window_end_unix_ms"]) != int(
        canonical["probe_onset_unix_ms"]
    ):
        raise ValueError(
            f"{session}: window_end_unix_ms must equal probe_onset_unix_ms"
        )
    return canonical


def build_base(
    bg: dict,
    mp: dict,
    row: dict,
    state: str,
    observed: bool,
    reason: str,
) -> dict:
    canonical = to_canonical(bg, mp, row)
    base = canonical or {}
    base.update(
        {
            "mmwave_state": state,
            "mmwave_observed": observed,
            "mmwave_missing_reason": reason,
            "mmwave_loadable": False,
        }
    )
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", nargs="*", default=None)
    parser.add_argument("--probe-source", type=Path, default=PROBE_SOURCE)
    parser.add_argument("--output-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    j = load_module(J_ADAPTER, "j_adapter_for_E_m1")
    contract = j.load_contract_module()
    algo = j.load_module(j.PRODUCER, "producer_merge_ready_E_m1")

    bg = {
        row["session_id"]: row["source_subject_raw"]
        for row in csv.DictReader(BACKGROUND.open(encoding="utf-8-sig"))
    }
    mp = {
        row["single_experiment_id"]: row
        for row in csv.DictReader(MAPPING.open(encoding="utf-8-sig"))
    }

    j_sessions = load_j_sessions(j)
    probe_rows = list(
        csv.DictReader(args.probe_source.open(encoding="utf-8-sig"))
    )
    e_rows = [
        row
        for row in probe_rows
        if row["session_id"] not in j_sessions and row["session_id"] in bg
    ]
    sessions = sorted({row["session_id"] for row in e_rows})
    if args.sessions:
        sessions = [session for session in sessions if session in args.sessions]

    print(
        f"E 盘批次: {len(sessions)} sessions / {len(e_rows)} probe 窗口"
        f"（排除 J 盘已跑的 {len(j_sessions)} 场）"
    )

    out_rows: list[dict] = []
    frame_audit_rows: list[dict] = []
    skipped_invalid = 0

    for session in sessions:
        mmw_root = None
        for data_root in DATA_ROOTS:
            candidate = data_root / f"{session}_" / "mmwave"
            if candidate.is_dir():
                mmw_root = candidate
                break
        session_rows = [row for row in e_rows if row["session_id"] == session]
        previous_by_block: dict[str, float | None] = {}

        if mmw_root is None:
            for row in session_rows:
                canonical = to_canonical(bg, mp, row)
                if canonical is None:
                    skipped_invalid += 1
                    continue
                out_rows.append(
                    build_base(
                        bg,
                        mp,
                        row,
                        "STRUCTURAL_MISSING",
                        False,
                        "no_mmwave_directory",
                    )
                )
                frame_audit_rows.append(
                    contract.frame_audit_stub(
                        canonical, "SOURCE_UNAVAILABLE", "no_mmwave_directory"
                    )
                )
            continue

        try:
            timestamps = j.load_timestamps(mmw_root)
            files = j.load_npz_files(mmw_root, session)
        except Exception as exc:
            for row in session_rows:
                canonical = to_canonical(bg, mp, row)
                if canonical is None:
                    skipped_invalid += 1
                    continue
                out_rows.append(
                    build_base(
                        bg,
                        mp,
                        row,
                        "STRUCTURAL_MISSING",
                        False,
                        f"load_failed:{type(exc).__name__}",
                    )
                )
                frame_audit_rows.append(
                    contract.frame_audit_stub(
                        canonical,
                        "SOURCE_MALFORMED",
                        f"load_failed:{type(exc).__name__}",
                    )
                )
            continue

        valid = 0
        for row in session_rows:
            canonical = to_canonical(bg, mp, row)
            if canonical is None:
                skipped_invalid += 1
                continue
            out_rows.append(
                j.process_probe(
                    algo,
                    canonical,
                    files,
                    timestamps,
                    previous_by_block,
                    frame_audit_rows=frame_audit_rows,
                    contract=contract,
                )
            )
            valid += 1
        print(f"{session}: 完成 {valid} 窗口")

    args.output_root.mkdir(parents=True, exist_ok=True)
    provenance = j.git_provenance()
    for row in out_rows:
        row["mmwave_source_run_id"] = RUN_ID
        row["mmwave_source_commit"] = provenance["source_commit"]

    fields = j.build_output_fields()
    out_csv = args.output_root / "mmwave_probe_merge_ready_E.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)

    frame_audit = (
        args.output_root / "mmwave_probe_frame_membership_audit_E.csv"
    )
    j.write_rows(frame_audit, frame_audit_rows)

    state_counts: dict[str, int] = {}
    for row in out_rows:
        state = str(row.get("mmwave_state", "?"))
        state_counts[state] = state_counts.get(state, 0) + 1

    source_files = {
        "e_adapter": Path(__file__).resolve(),
        "j_adapter": J_ADAPTER,
        "contract": j.CONTRACT_PATH,
        "producer": j.PRODUCER,
    }
    manifest = {
        "schema": "mmwave_probe_merge_ready_v1",
        "batch": "E_drive",
        "run_id": RUN_ID,
        "rows": len(out_rows),
        "sessions": len(sessions),
        "state_counts": state_counts,
        "skipped_invalid_identity_rows": skipped_invalid,
        "repeat_participant_id_scheme": "R_format_from_session_id_mapping",
        "probe_source": str(args.probe_source),
        "science_clock_source": contract.SCIENCE_CLOCK_SOURCE,
        "science_timestamp_column_index": contract.SCIENCE_TIMESTAMP_COL,
        "qc_timestamp_column_index": contract.QC_TIMESTAMP_COL,
        "window_contract": contract.WINDOW_CONTRACT,
        "right_endpoint_exclusive": True,
        "effective_start_used_for_slicing": True,
        "hr_usable_window_fraction_semantics": (
            "producer estimate_hr_time_course signal_quality.usable_ratio"
        ),
        "frame_membership_audit": str(frame_audit),
        **provenance,
        "source_hashes_sha256": {
            name: j.sha256(path) for name, path in source_files.items()
        },
        "models_trained": False,
        "q1_q2_used_for_acceptance": False,
        "snapshot_v2_formed": False,
    }
    manifest_path = (
        args.output_root / "mmwave_probe_merge_ready_E_manifest.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"输出: {out_csv}")
    print(f"frame audit: {frame_audit}")
    print(f"manifest: {manifest_path}")
    print(f"状态分布: {state_counts}")


if __name__ == "__main__":
    main()
