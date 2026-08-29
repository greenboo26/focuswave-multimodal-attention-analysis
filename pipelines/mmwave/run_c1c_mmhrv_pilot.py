# -*- coding: utf-8 -*-
"""C1c mmHRV single-target pilot on formal RS6240 raw ADC.

This adapter is deliberately narrow. It reads the existing formal NPZ ADC
chunks, performs the already audited 256-point range FFT, selects one
single-target channel/bin without MIMO beamforming, extracts complex phase,
and compares a conservative mmHRV-style VMD+envelope-normalisation route
against three fixed local baselines under one evaluator.

The Wang et al. mmHRV paper does not provide enough reproducible numerical
parameters in the local evidence for K/alpha/peak thresholds. The values in
PILOT_CONFIG are therefore adapter parameters, not claims about the paper's
original hidden settings; they are frozen for this pilot and never fitted to
ECG.
"""
from __future__ import annotations

import argparse, csv, json, sys
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.signal import find_peaks

ALGO = Path(r"D:\Project\厚粲杯\08_算法\scripts")
sys.path.insert(0, str(ALGO))
import process_vital_signs_v3_1_1 as v311
from calibrate_ecg_mmwave import read_ecg_and_markers, read_events, align_clocks

RAW_ROOT = Path(r"D:\acq_mmwave_data")
OUT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1")
SUBJECTS = ["97793", "97794", "97795"]
FS_RADAR = 100.0
PILOT_FRAMES = 6000  # fixed first 60 s, matching the existing block-1 pilot scope
TOLERANCES_MS = (50.0, 75.0, 100.0, 150.0)
PRIMARY_TOLERANCE_MS = 75.0
FIXED_DELAY_MS = -18.000000000000682

PILOT_CONFIG = {
    "range_fft_points": 256,
    "human_bin_range": [3, 30],
    "selection": "single-channel single-bin maximum periodicity/phase-stability; no beamforming",
    "vmd_backend": "sktime.libs.vmdpy then vmdpy",
    "vmd_alpha": 1000,
    "vmd_K": 3,
    "vmd_tau": 0,
    "vmd_DC": False,
    "vmd_init": 1,
    "vmd_tol": 1e-6,
    "heartbeat_band_hz": [0.8, 2.0],
    "normalization_envelope_window_s": 2.0,
    "peak_detector": "existing process_vital_signs_v3_1_1.detect_peaks_heart_lo",
    "paper_parameter_status": "K/alpha and peak thresholds not uniquely recoverable from local paper note; frozen conservative adapter values above",
}

def load_raw(parts_dir: Path, prefix: str) -> np.ndarray:
    files = sorted(parts_dir.glob(f"{prefix}_datacube_part*.npz"))
    base = parts_dir / f"{prefix}_datacube.npz"
    if base.exists(): files = [base] + files
    if not files: raise FileNotFoundError(f"no NPZ chunks under {parts_dir}")
    rows = []
    for p in files:
        with np.load(p) as d:
            keys = sorted(k for k in d.files if k.startswith("tx"))
            if len(keys) != 8: raise ValueError(f"{p}: expected 8 tx/rx keys, got {len(keys)}")
            # (frames, fast_time, channel), raw complex ADC according to SDK audit.
            a = np.stack([np.asarray(d[k]) for k in keys], axis=-1)
            if a.ndim != 3 or a.shape[1] != 256: raise ValueError(f"{p}: shape {a.shape}")
            rows.append(a.astype(np.complex64))
    return np.concatenate(rows, axis=0)

def load_ts(mm_dir: Path, prefix: str) -> np.ndarray:
    p = mm_dir / f"{prefix}_timestamps.csv"
    a = np.loadtxt(p, delimiter=",", ndmin=2)
    return a[:, 2].astype(float)

def range_fft(raw: np.ndarray) -> np.ndarray:
    x = raw - np.mean(raw, axis=1, keepdims=True)
    return np.fft.fft(x, n=256, axis=1).astype(np.complex64)

def phase_score(phi: np.ndarray) -> tuple[float, dict]:
    p = np.unwrap(np.angle(phi))
    p = signal.detrend(p)
    f, px = signal.periodogram(p, fs=FS_RADAR, window="hann")
    band = (f >= 0.8) & (f <= 2.0)
    noise = np.median(px[(f >= 2.5) & (f <= 5.0)]) + 1e-12
    # FFT autocorrelation; the direct O(n^2) correlate is prohibitively slow
    # for a full formal session and is mathematically equivalent here.
    q = p - np.mean(p)
    nfft = 1 << int(np.ceil(np.log2(max(2, 2 * len(q) - 1))))
    fq = np.fft.rfft(q, n=nfft)
    ac = np.fft.irfft(np.abs(fq) ** 2, n=nfft)[:len(q)]
    ac = ac / (ac[0] + 1e-12)
    lags = np.arange(len(ac)) / FS_RADAR
    lagmask = (lags >= 0.42) & (lags <= 1.25)
    ac_peak = float(np.max(ac[lagmask])) if np.any(lagmask) else 0.0
    band_snr = float(np.max(px[band]) / noise) if np.any(band) else 0.0
    rough = float(np.std(np.diff(p)) / (np.std(p) + 1e-12))
    score = float(max(ac_peak, 0.0) * np.log1p(max(band_snr, 0.0)) / (1.0 + rough))
    return score, {"autocorr_peak": ac_peak, "band_snr_linear": band_snr, "roughness": rough}

def select_channel_bin(rfft: np.ndarray) -> tuple[int, int, list[dict]]:
    n, _, c = rfft.shape
    candidates = []
    for ch in range(c):
        for b in range(3, min(30, rfft.shape[1]-1)+1):
            score, q = phase_score(rfft[:, b, ch])
            candidates.append({"channel": ch, "bin": b, "score": score, **q})
    best = max(candidates, key=lambda z: z["score"])
    return int(best["channel"]), int(best["bin"]), sorted(candidates, key=lambda z: z["score"], reverse=True)[:20]

def vmd_heartbeat(x: np.ndarray) -> tuple[np.ndarray, dict]:
    VMD, backend = v311._load_vmd()
    y = signal.detrend(np.asarray(x, float))
    u, _, omega = VMD(y, alpha=1000, tau=0, K=3, DC=False, init=1, tol=1e-6)
    freqs = np.fft.rfftfreq(len(y), 1/FS_RADAR)
    mask = (freqs >= 0.8) & (freqs <= 2.0)
    summaries = []
    best = None; best_score = -np.inf
    for k, mode in enumerate(u):
        _, px = signal.periodogram(mode, fs=FS_RADAR, window="hann")
        dom = float(freqs[mask][np.argmax(px[mask])]) if np.any(mask) else np.nan
        score = float(np.sum(px[mask]) * np.std(mode)) if np.any(mask) else -np.inf
        summaries.append({"mode": k, "dominant_hz": dom, "score": score,
                          "center_hz": float(omega[-1, k] * FS_RADAR)})
        if score > best_score: best_score, best = score, k
    if best is None or not np.isfinite(best_score):
        return v311._sos_bandpass(y, 0.8, 2.0), {"backend": backend, "fallback": True, "modes": summaries}
    return np.asarray(u[best], float), {"backend": backend, "selected_mode": int(best), "modes": summaries, "fallback": False}

def normalize_heartbeat(x: np.ndarray) -> np.ndarray:
    env = np.convolve(np.abs(x), np.ones(int(2*FS_RADAR))/int(2*FS_RADAR), mode="same")
    return x / (env + 1e-8)

def peaks(x: np.ndarray) -> np.ndarray:
    return np.asarray(v311.detect_peaks_heart_lo(x, lo_bpm=48.0, hi_bpm=120.0), dtype=int)

def baseline_peaks(phase: np.ndarray, method: str) -> np.ndarray:
    if method == "c1b_project_bandpass":
        return peaks(v311._sos_bandpass(signal.detrend(phase), 0.8, 2.0))
    if method == "c1b_python_amf":
        x = v311._sos_bandpass(signal.detrend(phase), 0.8, 2.0)
        f, px = signal.periodogram(x, fs=FS_RADAR, window="hann")
        m = (f >= 0.667) & (f <= 3.333)
        f0 = float(f[m][np.argmax(px[m])])
        period = max(3, int(round(FS_RADAR/f0)))
        t = np.sin(np.arange(period)/period*2*np.pi); t -= t.mean(); t /= np.linalg.norm(t)+1e-12
        z = np.convolve((x-np.median(x))/(np.std(x)+1e-12), t[::-1], mode="same")
        return find_peaks(z, distance=int(0.70*period), prominence=max(0.05, 0.20*np.std(z)))[0].astype(int)
    if method == "c1b_v311_vmd":
        h, _ = v311.separate_vmd_heart_only(signal.detrend(phase))
        return peaks(h)
    raise ValueError(method)

def c1c_peaks(phase: np.ndarray) -> tuple[np.ndarray, dict, np.ndarray]:
    h, vmd = vmd_heartbeat(phase)
    z = normalize_heartbeat(h)
    vmd["heartbeat_component"] = h
    return peaks(z), vmd, z

def greedy(ref, est, tol_s):
    i=j=0; pairs=[]
    while i < len(ref) and j < len(est):
        d = est[j]-ref[i]
        if abs(d) <= tol_s: pairs.append((i,j,d)); i+=1; j+=1
        elif est[j] < ref[i]-tol_s: j+=1
        else: i+=1
    return pairs

def hrv(ibi):
    if len(ibi) < 2: return None, None
    return float(np.sqrt(np.mean(np.diff(ibi)**2))), float(np.std(ibi, ddof=1))

def metrics(ref, est, tol_ms, delay_ms):
    pairs = greedy(ref, est - delay_ms/1000, tol_ms/1000)
    ri=np.array([a for a,_,_ in pairs], int); ei=np.array([b for _,b,_ in pairs], int)
    ribi=np.diff(ref[ri])*1000 if len(ri)>1 else np.array([]); eibi=np.diff(est[ei])*1000 if len(ei)>1 else np.array([])
    rr, rs = hrv(ribi); er, es = hrv(eibi)
    return {"ecg_beats":len(ref),"radar_beats":len(est),"matched_beats":len(pairs),
            "precision":len(pairs)/len(est) if len(est) else None,"recall":len(pairs)/len(ref) if len(ref) else None,
            "f1":2*len(pairs)/(len(ref)+len(est)) if len(ref)+len(est) else None,
            "timing_mae_ms":float(np.mean(np.abs([d for _,_,d in pairs]))*1000) if pairs else None,
            "ibi_mae_ms":float(np.mean(np.abs(eibi-ribi))) if len(ribi) else None,
            "hr_ecg_bpm":float(60000/np.median(ribi)) if len(ribi) else None,
            "hr_radar_bpm":float(60000/np.median(eibi)) if len(eibi) else None,
            "hr_abs_error_bpm":float(abs(60000/np.median(eibi)-60000/np.median(ribi))) if len(ribi) and len(eibi) else None,
            "rmssd_abs_error_ms":abs(er-rr) if er is not None and rr is not None else None,
            "sdnn_abs_error_ms":abs(es-rs) if es is not None and rs is not None else None}

def ecg_peaks_for_session(acq: Path, events: Path, t0: float, t1: float):
    ecg, sr, pulses = read_ecg_and_markers(str(acq)); ev = read_events(str(events)); off,k=align_clocks(pulses, ev, sr)
    i0=max(0,int((t0-off)/k)); i1=min(len(ecg),int((t1-off)/k)); x=ecg[i0:i1]
    x=signal.sosfiltfilt(signal.butter(4,[5,35],btype="band",fs=sr,output="sos"), x)
    p,_=find_peaks(x, distance=int(.30*sr), prominence=max(np.std(x)*.25,1e-6))
    return off+k*(p+i0), sr

def save_diag(path: Path, t, phase, heart, norm, ref, methods, session):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax=plt.subplots(4,1,figsize=(15,10),sharex=False)
    ax[0].plot(t, phase, lw=.35); ax[0].set_title(f"{session} selected complex phase");
    ax[1].plot(t, heart, lw=.35); ax[1].set_title("VMD heartbeat component")
    ax[2].plot(t, norm, lw=.35); ax[2].set_title("normalised heartbeat waveform")
    ax[3].plot(t, norm, lw=.35); ax[3].vlines(ref-ref[0], np.nanmin(norm), np.nanmax(norm), color="r", alpha=.25); ax[3].set_title("ECG reference timing overlay (relative)")
    for a in ax: a.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)

def run_one(subject: str):
    root=RAW_ROOT/f"sub-{subject}_"; mm=root/"mmwave"; prefix=f"sub-{subject}_mmwave"
    raw=load_raw(mm,prefix); ts=load_ts(mm,prefix); n=min(len(raw),len(ts),PILOT_FRAMES); raw=raw[:n]; ts=ts[:n]
    rfft=range_fft(raw); ch,b,cands=select_channel_bin(rfft); phase=np.unwrap(np.angle(rfft[:,b,ch]));
    # Use complete radar duration and matched ECG time span; no ECG-informed frontend tuning.
    acq = root / f"{subject}.acq"
    if not acq.exists():
        # Existing ledger records this known directory/file naming mismatch
        # for sub-97795 (folder is 97795, Biopac file is 97995.acq).
        matches = sorted(root.glob("*.acq"))
        if len(matches) != 1:
            raise FileNotFoundError(f"ECG .acq is not uniquely resolvable for {subject}: {matches}")
        acq = matches[0]
    ref, _ = ecg_peaks_for_session(acq, root/"beh"/"events.csv", ts[0], ts[-1])
    t=(ts-ts[0])/1000
    methods={}
    for name in ["c1b_project_bandpass","c1b_python_amf","c1b_v311_vmd"]: methods[name]=t[baseline_peaks(phase,name)]
    cpk,vmd,norm=c1c_peaks(phase); heartbeat=np.asarray(vmd.pop("heartbeat_component")); methods["c1c_mmhrv_adaptive_vmd"]=t[cpk]
    rows=[]
    for method,est in methods.items():
        for tol in TOLERANCES_MS:
            m=metrics((ref-ts[0])/1000,est,tol,FIXED_DELAY_MS); m.update({"subject":subject,"method":method,"tolerance_ms":tol,"fixed_delay_ms":FIXED_DELAY_MS})
            rows.append(m)
    out=OUT_ROOT/subject; out.mkdir(parents=True,exist_ok=True)
    (out/"diagnostics.json").write_text(json.dumps({"subject":subject,"raw_shape":list(raw.shape),"fft_shape":list(rfft.shape),"selected_channel":ch,"selected_bin":b,"candidates":cands,"vmd":vmd,"config":PILOT_CONFIG},indent=2),encoding="utf-8")
    save_diag(out/"c1c_diagnostic.png",t,phase, heartbeat, norm, (ref-ts[0])/1000, methods,subject)
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--subjects",nargs="*",default=SUBJECTS); a=ap.parse_args(); OUT_ROOT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for s in a.subjects: rows.extend(run_one(s))
    fields=sorted({k for r in rows for k in r});
    with (OUT_ROOT/"c1c_metrics_long.csv").open("w",newline="",encoding="utf-8-sig") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    primary=[r for r in rows if r["tolerance_ms"] == PRIMARY_TOLERANCE_MS]
    with (OUT_ROOT/"c1c_metrics_primary.csv").open("w",newline="",encoding="utf-8-sig") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(primary)
    manifest={"status":"C1C_PILOT_COMPLETE","subjects":a.subjects,"input":"formal RS6240 raw ADC NPZ + Biopac ECG","pilot_scope":"first 60 s / 6000 frames per session","no_beamforming":True,"fixed_delay_ms":FIXED_DELAY_MS,"primary_tolerance_ms":75.0,"tolerances_ms":list(TOLERANCES_MS),"baseline_scope":"same selected phase, local C1b-compatible implementations; official MATLAB VS baseline is not applicable to formal RS6240 raw ADC"}
    (OUT_ROOT/"run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
if __name__ == "__main__": main()


