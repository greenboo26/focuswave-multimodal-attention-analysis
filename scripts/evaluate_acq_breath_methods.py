"""Compare stored mmWave breath peak/frequency estimates with respiratory belt."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import signal


def rate_from_npz(npz_path: Path, end_s: float) -> dict:
    d = np.load(npz_path, allow_pickle=True)
    t = np.asarray(d["t"], float); start = end_s - 60.0
    bp = np.asarray(d.get("breath_peaks", []), float).ravel()
    if len(bp) and np.nanmax(bp) > np.nanmax(t) + 1:
        bp = t[np.clip(bp.astype(int), 0, len(t) - 1)]
    bpw = bp[(bp > start) & (bp <= end_s)]
    time_bpm = float(60.0 / np.mean(np.diff(bpw))) if len(bpw) >= 2 else np.nan
    b = np.asarray(d.get("breath", []), float)
    mask = (t > start) & (t <= end_s)
    y = b[mask] if len(b) == len(t) else np.asarray([])
    spectral_raw_bpm = np.nan
    if len(y) >= 300:
        fs = 1.0 / float(np.median(np.diff(t[mask])))
        f, p = signal.periodogram(signal.detrend(y), fs=fs, window="hann")
        m = (f >= .1) & (f <= .5) & np.isfinite(p)
        if np.any(m): spectral_raw_bpm = float(f[m][np.argmax(p[m])] * 60.0)
    spectral_bpm = spectral_raw_bpm
    harmonic_correction = False
    if np.isfinite(spectral_raw_bpm) and spectral_raw_bpm < 12.0 and spectral_raw_bpm * 2.0 <= 30.0:
        spectral_bpm = spectral_raw_bpm * 2.0
        harmonic_correction = True
    return {"br_mm_time_bpm": time_bpm, "br_mm_spectral_raw_bpm": spectral_raw_bpm,
            "br_mm_spectral_bpm": spectral_bpm, "br_harmonic_correction": harmonic_correction,
            "n_breath_peaks": int(len(bpw))}


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--reference",type=Path,required=True); ap.add_argument("--npz-root",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    metrics=json.loads(args.reference.read_text(encoding="utf-8")); rows=[]
    for s in metrics:
        if not s.get("probes") or not s.get("offset_mmwave_from_acq_s"): continue
        npz=args.npz_root / s["subject"] / f"{s['subject']}ses-SART_mmwave_vital_signs.npz"
        # stored directory names include a trailing underscore; retain exact folder/file fallback
        if not npz.exists():
            matches=list((args.npz_root / s["subject"]).glob("*_vital_signs.npz")) if (args.npz_root / s["subject"]).exists() else []
            if not matches: continue
            npz=matches[0]
        for p in s["probes"]:
            end_s=float(p["onset_acq_s"])-float(s["offset_mmwave_from_acq_s"])
            if end_s < 60: continue
            row={"subject":s["subject"],"onset_acq_s":p["onset_acq_s"],"br_rsp_bpm":p.get("br_rsp_bpm"),"window_end_mm_s":end_s,"npz":str(npz)}
            row.update(rate_from_npz(npz,end_s)); rows.append(row)
    for r in rows:
        for k in ("br_rsp_bpm","br_mm_time_bpm","br_mm_spectral_bpm"):
            r[k]=float(r[k]) if r.get(k) is not None else np.nan
        r["time_error_bpm"]=abs(r["br_mm_time_bpm"]-r["br_rsp_bpm"]) if np.isfinite(r["br_mm_time_bpm"]) and np.isfinite(r["br_rsp_bpm"]) else np.nan
        r["spectral_error_bpm"]=abs(r["br_mm_spectral_bpm"]-r["br_rsp_bpm"]) if np.isfinite(r["br_mm_spectral_bpm"]) and np.isfinite(r["br_rsp_bpm"]) else np.nan
    summary={"n_windows":len(rows),"n_subjects":len({r["subject"] for r in rows}),"time_mae_bpm":float(np.nanmean([r["time_error_bpm"] for r in rows])) if rows else None,"spectral_mae_bpm":float(np.nanmean([r["spectral_error_bpm"] for r in rows])) if rows else None,"time_within_5_bpm":int(sum(np.isfinite(r["time_error_bpm"]) and r["time_error_bpm"]<=5 for r in rows)),"spectral_within_5_bpm":int(sum(np.isfinite(r["spectral_error_bpm"]) and r["spectral_error_bpm"]<=5 for r in rows))}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps({"summary":summary,"rows":rows},ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
