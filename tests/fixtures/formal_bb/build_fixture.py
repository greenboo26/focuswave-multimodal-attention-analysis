"""Build a tiny synthetic BB cohort; it contains no real participant data."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    base_ms = 1_800_000_000_000
    manifest_rows = []
    identity_rows = []
    groups = {"syn-001": "grp-a", "syn-002": "grp-a", "syn-003": "grp-b", "syn-004": "grp-c"}
    for session_index, (session, group) in enumerate(groups.items(), start=1):
        rows = []
        for trial in range(1, 13):
            is_nogo = int(trial in {3, 6, 9, 12})
            commission = int(trial == 6)
            omission = int(trial == 7)
            correct = int(not commission and not omission)
            response = "space" if (not is_nogo and not omission) or commission else ""
            rt = 300 + session_index * 10 + trial * 3 if response else ""
            is_probe = int(trial == 10)
            onset = base_ms + session_index * 100_000 + trial * 1_000
            rows.append({
                "subject_id": session,
                "block_num": 1,
                "trial_num": trial,
                "cycle_num": 1 if trial <= 6 else 2,
                "is_no_go": is_nogo,
                "response": response,
                "rt": rt,
                "correct": correct,
                "commission": commission,
                "omission": omission,
                "is_probe": is_probe,
                "probe_response": (session_index - 1) % 4 + 1 if is_probe else "",
                "probe_vigilance": session_index if is_probe else "",
                "absolute_onset_time": onset,
                "probe_onset_time": onset if is_probe else "",
            })
        behavior = root / f"{session}_B1.csv"
        pd.DataFrame(rows).to_csv(behavior, index=False, encoding="utf-8-sig")
        manifest_rows.append({
            "session_id": session,
            "block_id": "B1",
            "behavior_path": behavior.name,
            "include": "true",
            "exclusion_reason": "",
            "source_contract": "focuswave_raw_behavior_bb_v1",
        })
        identity_rows.append({
            "session_id": session,
            "anonymous_participant_group_id": group,
            "identity_status": "synthetic_fixture",
        })
    manifest_rows.append({
        "session_id": "sub-9504",
        "block_id": "B1",
        "behavior_path": "not_required_for_excluded_row.csv",
        "include": "true",
        "exclusion_reason": "pilot_session",
        "source_contract": "focuswave_raw_behavior_bb_v1",
    })
    identity_rows.append({
        "session_id": "sub-9504",
        "anonymous_participant_group_id": "grp-pilot",
        "identity_status": "synthetic_fixture",
    })
    manifest = root / "session_manifest.csv"
    identity = root / "anonymous_identity_map.csv"
    config = root / "config.json"
    pd.DataFrame(manifest_rows).to_csv(manifest, index=False, encoding="utf-8-sig")
    pd.DataFrame(identity_rows).to_csv(identity, index=False, encoding="utf-8-sig")
    config.write_text(json.dumps({
        "schema_version": "focuswave-formal-bb-behavior-v1",
        "accepted_source_contracts": ["focuswave_raw_behavior_bb_v1"],
        "explicit_excluded_session_ids": ["sub-9504"],
        "rt_valid_min_ms": 150,
        "rt_valid_max_ms": 2000,
        "rt_min_count_summary": 1,
        "rt_min_count_dispersion": 3,
        "rt_min_count_slope": 4,
        "sdt_min_go_opportunities": 4,
        "sdt_min_nogo_opportunities": 2,
        "probe_window_seconds": [5],
        "fixed_window_seconds": [5],
        "error_trajectory_trial_offsets": [-1, 0, 1],
    }, indent=2), encoding="utf-8")
    return manifest, identity, config


if __name__ == "__main__":
    build(Path(__file__).resolve().parent / "generated")
