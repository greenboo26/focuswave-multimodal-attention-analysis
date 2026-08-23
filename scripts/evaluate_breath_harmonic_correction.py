"""Evaluate a conservative low-frequency respiratory half-rate correction."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt


ROOT = Path(r"D:\Project\厚粲杯\08_算法")
REF = ROOT / "output" / "ACQ_reference_20260821" / "breath_method_comparison_current.json"


def spectrum(npz: Path, end_s: float) -> dict:
    d = np.load(npz, allow_pickle=True)
    t = np.asarray(d["t"], float)
    mask = (t > end_s - 60.0) & (t <= end_s)
    y = np.asarray(d.get("breath", []), float)
    if len(y) != len(t) or mask.sum() < 300:
        return {"raw_bpm": np.nan, "double_bpm": np.nan, "second_harmonic_ratio": np.nan}
    fs = 1.0 / float(np.median(np.diff(t[mask])))
    f, p = signal.periodogram(signal.detrend(y[mask]), fs=fs, window="hann")
    band = (f >= 0.1) & (f <= 0.5) & np.isfinite(p)
    if not np.any(band):
        return {"raw_bpm": np.nan, "double_bpm": np.nan, "second_harmonic_ratio": np.nan}
    fb, pb = f[band], p[band]
    raw_hz = float(fb[int(np.argmax(pb))])
    double_hz = raw_hz * 2.0
    if double_hz > 0.5:
        ratio = np.nan
    else:
        near = np.abs(fb - double_hz) <= max(1.5 * float(np.median(np.diff(fb))), 0.01)
        ratio = float(np.max(pb[near]) / max(np.max(pb), 1e-12)) if np.any(near) else 0.0
    corrected = double_hz * 60.0 if raw_hz * 60.0 < 12.0 and double_hz <= 0.5 else raw_hz * 60.0
    return {"raw_bpm": raw_hz * 60.0, "double_bpm": corrected, "second_harmonic_ratio": ratio}


def main() -> None:
    ref = json.loads(REF.read_text(encoding="utf-8"))
    rows = []
    for row in ref["rows"]:
        p = Path(row["npz"])
        s = spectrum(p, float(row["window_end_mm_s"]))
        if np.isfinite(s["raw_bpm"]) and row.get("br_rsp_bpm") is not None:
            ref_bpm = float(row["br_rsp_bpm"])
            rows.append({**row, **s, "raw_error_bpm": abs(s["raw_bpm"] - ref_bpm), "corrected_error_bpm": abs(s["double_bpm"] - ref_bpm)})
    def mae(key): return float(np.mean([r[key] for r in rows])) if rows else None
    result = {
        "n_windows": len(rows),
        "raw_mae_bpm": mae("raw_error_bpm"),
        "corrected_mae_bpm": mae("corrected_error_bpm"),
        "raw_within_5": sum(r["raw_error_bpm"] <= 5 for r in rows),
        "corrected_within_5": sum(r["corrected_error_bpm"] <= 5 for r in rows),
        "correction_rule": "double the spectral rate only when raw spectral rate < 12 bpm and doubled frequency remains in the 0.1-0.5 Hz band",
        "rows": rows,
    }
    by_subject = {}
    for subject in sorted({r["subject"] for r in rows}):
        sub = [r for r in rows if r["subject"] == subject]
        by_subject[subject] = {
            "n": len(sub),
            "raw_mae_bpm": float(np.mean([r["raw_error_bpm"] for r in sub])),
            "corrected_mae_bpm": float(np.mean([r["corrected_error_bpm"] for r in sub])),
            "raw_within_5": int(sum(r["raw_error_bpm"] <= 5 for r in sub)),
            "corrected_within_5": int(sum(r["corrected_error_bpm"] <= 5 for r in sub)),
        }
    result["by_subject"] = by_subject
    out = ROOT / "output" / "ACQ_reference_20260821" / "breath_harmonic_correction_evaluation.json"
    fig_path = ROOT / "output" / "ACQ_reference_20260821" / "breath_harmonic_correction_scatter.png"
    x = np.asarray([float(r["br_rsp_bpm"]) for r in rows], float)
    raw = np.asarray([float(r["raw_bpm"]) for r in rows], float)
    corrected = np.asarray([float(r["double_bpm"]) for r in rows], float)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, y, title in ((axes[0], raw, "Raw spectral peak"), (axes[1], corrected, "Half-frequency corrected")):
        ax.scatter(x, y, s=22, alpha=0.7)
        lo, hi = min(float(np.min(x)), float(np.min(y))) - 1, max(float(np.max(x)), float(np.max(y))) + 1
        ax.plot([lo, hi], [lo, hi], "k--", linewidth=1)
        ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel="RSP reference (bpm)", ylabel="mmWave estimate (bpm)", title=title)
        ax.grid(alpha=0.2)
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    result["figure"] = str(fig_path)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in result if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
