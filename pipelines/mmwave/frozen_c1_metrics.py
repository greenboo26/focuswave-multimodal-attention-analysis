"""Frozen C1 beat-matching evaluator extracted verbatim from the accepted C1c producer.

Source provenance:
archive/20260826/c1-alignment-protocol-repair
scripts/run_c1c_mmhrv_pilot.py@6b3df47b9e082a6b3f3b3515f748dc0352cafc81

Only the evaluator functions required by audit_c1_alignment_robustness.py are
packaged here. This does not change C1 science or restart HRV development.
"""
from __future__ import annotations

import numpy as np


def greedy(ref, est, tol_s):
    i = j = 0
    pairs = []
    while i < len(ref) and j < len(est):
        d = est[j] - ref[i]
        if abs(d) <= tol_s:
            pairs.append((i, j, d))
            i += 1
            j += 1
        elif est[j] < ref[i] - tol_s:
            j += 1
        else:
            i += 1
    return pairs


def hrv(ibi):
    if len(ibi) < 2:
        return None, None
    return float(np.sqrt(np.mean(np.diff(ibi) ** 2))), float(np.std(ibi, ddof=1))


def metrics(ref, est, tol_ms, delay_ms):
    pairs = greedy(ref, est - delay_ms / 1000, tol_ms / 1000)
    ri = np.array([a for a, _, _ in pairs], int)
    ei = np.array([b for _, b, _ in pairs], int)
    ribi = np.diff(ref[ri]) * 1000 if len(ri) > 1 else np.array([])
    eibi = np.diff(est[ei]) * 1000 if len(ei) > 1 else np.array([])
    rr, rs = hrv(ribi)
    er, es = hrv(eibi)
    return {
        "ecg_beats": len(ref),
        "radar_beats": len(est),
        "matched_beats": len(pairs),
        "precision": len(pairs) / len(est) if len(est) else None,
        "recall": len(pairs) / len(ref) if len(ref) else None,
        "f1": 2 * len(pairs) / (len(ref) + len(est)) if len(ref) + len(est) else None,
        "timing_mae_ms": float(np.mean(np.abs([d for _, _, d in pairs])) * 1000) if pairs else None,
        "ibi_mae_ms": float(np.mean(np.abs(eibi - ribi))) if len(ribi) else None,
        "hr_ecg_bpm": float(60000 / np.median(ribi)) if len(ribi) else None,
        "hr_radar_bpm": float(60000 / np.median(eibi)) if len(eibi) else None,
        "hr_abs_error_bpm": float(abs(60000 / np.median(eibi) - 60000 / np.median(ribi))) if len(ribi) and len(eibi) else None,
        "rmssd_abs_error_ms": abs(er - rr) if er is not None and rr is not None else None,
        "sdnn_abs_error_ms": abs(es - rs) if es is not None and rs is not None else None,
    }
