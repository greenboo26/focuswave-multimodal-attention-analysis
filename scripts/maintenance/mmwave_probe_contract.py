"""Shared formal mmWave probe-window contract.

Science alignment is frozen to timestamp CSV zero-based column 1
(DLL host receive/enqueue time). Column 2 is Python worker processing time
and is retained only for QC. Formal windows are strictly right-open:
[window_effective_start_unix_ms, probe_onset_unix_ms).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Any

import numpy as np

SCIENCE_TIMESTAMP_COL = 1
QC_TIMESTAMP_COL = 2
SCIENCE_CLOCK_SOURCE = "dll_host_receive_enqueue"
WINDOW_CONTRACT = "[window_effective_start_unix_ms,probe_onset_unix_ms)"
LEGACY_CONTRACT = "python_processing_time + nominal_start + right_inclusive_end"


@dataclass(frozen=True)
class FrameWindow:
    i0: int
    i1_exclusive: int
    n_frames: int
    first_science_timestamp_ms: int | None
    last_science_timestamp_ms: int | None
    membership_digest_sha256: str
    all_selected_before_probe: bool
    all_selected_at_or_after_effective_start: bool
    effective_start_unix_ms: int
    probe_onset_unix_ms: int


def _as_int(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"missing required time field: {key}")
    return int(float(value))


def _validate_timestamp_matrix(timestamps: np.ndarray) -> np.ndarray:
    values = np.asarray(timestamps)
    if values.ndim != 2 or values.shape[1] <= QC_TIMESTAMP_COL:
        raise ValueError("timestamp matrix must contain frame, DLL-time, and Python-time columns")
    science = values[:, SCIENCE_TIMESTAMP_COL].astype(np.int64)
    if science.size > 1 and np.any(np.diff(science) < 0):
        raise ValueError("DLL science timestamp column is not monotonic")
    return science


def _membership_digest(i0: int, selected_science_ts: np.ndarray) -> str:
    payload = "\n".join(
        f"{idx},{int(ts)}"
        for idx, ts in zip(range(i0, i0 + len(selected_science_ts)), selected_science_ts)
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def select_frame_window(row: Mapping[str, Any], timestamps: np.ndarray) -> FrameWindow:
    """Select the frozen formal science window and fail closed on contract mismatch."""
    science = _validate_timestamp_matrix(timestamps)
    effective_start = _as_int(row, "window_effective_start_unix_ms")
    probe_onset = _as_int(row, "probe_onset_unix_ms")
    declared_end = _as_int(row, "window_end_unix_ms")
    if declared_end != probe_onset:
        raise ValueError("declared window_end_unix_ms must equal probe_onset_unix_ms exactly")
    if effective_start >= probe_onset:
        raise ValueError("effective window start must be strictly before probe onset")

    i0 = int(np.searchsorted(science, effective_start, side="left"))
    i1 = int(np.searchsorted(science, probe_onset, side="left"))
    selected = science[i0:i1]

    at_or_after_start = bool(np.all(selected >= effective_start)) if selected.size else True
    before_probe = bool(np.all(selected < probe_onset)) if selected.size else True
    if not at_or_after_start or not before_probe:
        raise AssertionError("selected frame membership violates the frozen time contract")

    return FrameWindow(
        i0=i0,
        i1_exclusive=i1,
        n_frames=i1 - i0,
        first_science_timestamp_ms=int(selected[0]) if selected.size else None,
        last_science_timestamp_ms=int(selected[-1]) if selected.size else None,
        membership_digest_sha256=_membership_digest(i0, selected),
        all_selected_before_probe=before_probe,
        all_selected_at_or_after_effective_start=at_or_after_start,
        effective_start_unix_ms=effective_start,
        probe_onset_unix_ms=probe_onset,
    )


def select_legacy_frame_window(row: Mapping[str, Any], timestamps: np.ndarray) -> dict[str, Any]:
    """Reconstruct current-main legacy membership for old-vs-new audit only."""
    values = np.asarray(timestamps)
    if values.ndim != 2 or values.shape[1] <= QC_TIMESTAMP_COL:
        raise ValueError("timestamp matrix must contain three columns")
    legacy_clock = values[:, QC_TIMESTAMP_COL].astype(np.int64)
    if legacy_clock.size > 1 and np.any(np.diff(legacy_clock) < 0):
        raise ValueError("legacy Python timestamp column is not monotonic")
    start = _as_int(row, "window_start_unix_ms")
    end = _as_int(row, "window_end_unix_ms")
    i0 = int(np.searchsorted(legacy_clock, start, side="left"))
    i1 = int(np.searchsorted(legacy_clock, end, side="right"))
    selected = legacy_clock[i0:i1]
    probe_onset = _as_int(row, "probe_onset_unix_ms")
    return {
        "legacy_i0": i0,
        "legacy_i1_exclusive": i1,
        "legacy_n_frames": i1 - i0,
        "legacy_first_timestamp_ms": int(selected[0]) if selected.size else None,
        "legacy_last_timestamp_ms": int(selected[-1]) if selected.size else None,
        "legacy_membership_digest_sha256": _membership_digest(i0, selected),
        "legacy_all_selected_before_probe": bool(np.all(selected < probe_onset)) if selected.size else True,
    }


def frame_audit_row(row: Mapping[str, Any], formal: FrameWindow, legacy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    keys = {key: row.get(key) for key in ("repeat_participant_id", "participant_group_id", "session_id", "block_id", "probe_id", "probe_index_in_block", "window_name") if key in row}
    out: dict[str, Any] = {
        **keys,
        "science_timestamp_column_index": SCIENCE_TIMESTAMP_COL,
        "science_clock_source": SCIENCE_CLOCK_SOURCE,
        "window_contract": WINDOW_CONTRACT,
        "window_effective_start_unix_ms": formal.effective_start_unix_ms,
        "probe_onset_unix_ms": formal.probe_onset_unix_ms,
        "new_i0": formal.i0,
        "new_i1_exclusive": formal.i1_exclusive,
        "new_n_frames": formal.n_frames,
        "new_first_science_timestamp_ms": formal.first_science_timestamp_ms,
        "new_last_science_timestamp_ms": formal.last_science_timestamp_ms,
        "new_membership_digest_sha256": formal.membership_digest_sha256,
        "new_all_selected_before_probe": formal.all_selected_before_probe,
        "new_all_selected_at_or_after_effective_start": formal.all_selected_at_or_after_effective_start,
        "audit_status": "SELECTED",
        "audit_reason": "",
    }
    if legacy is not None:
        out.update(legacy)
        out["membership_changed"] = legacy.get("legacy_membership_digest_sha256") != formal.membership_digest_sha256
    return out


def frame_audit_stub(row: Mapping[str, Any], status: str, reason: str) -> dict[str, Any]:
    keys = {key: row.get(key) for key in ("repeat_participant_id", "participant_group_id", "session_id", "block_id", "probe_id", "probe_index_in_block", "window_name") if key in row}
    return {
        **keys,
        "science_timestamp_column_index": SCIENCE_TIMESTAMP_COL,
        "science_clock_source": SCIENCE_CLOCK_SOURCE,
        "window_contract": WINDOW_CONTRACT,
        "audit_status": status,
        "audit_reason": reason,
        "new_all_selected_before_probe": None,
        "new_all_selected_at_or_after_effective_start": None,
        "membership_changed": None,
    }
