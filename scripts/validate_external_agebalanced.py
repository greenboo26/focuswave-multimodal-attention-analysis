"""Independent radar-vs-ECG heart-rate audit for the AgeBalanced 60 GHz dataset."""
from __future__ import annotations

import argparse
import csv
import json
import pickle
import zlib
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, periodogram

ROOT = Path(r"D:\Project\厚粲杯\11_数据\外部数据集_AgeBalanced_60GHz")
OUT = Path(r"D:\Project\厚粲杯\08_算法\output\External_AgeBalanced")


def read_csv(path, value_key):
    ts=[]; y=[]
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try: ts.append(r["Timestamp"]); y.append(float(r[value_key]))
            except (KeyError, ValueError): pass
    return ts, np.asarray(y, float)


def load_radar(path):
    with path.open("rb") as f: rfft, rbins = pickle.loads(zlib.decompress(f.read()))
    return np.asarray(rfft), np.asarray(rbins)


def ecg_hr(y, fs=250.0):
    y = y[np.isfinite(y)]
    if len(y) < fs * 10: return np.nan
    b,a=butter(3,[5/(fs/2),25/(fs/2)],btype="band")
    z=filtfilt(b,a,y); z=(z-np.median(z))/(np.std(z)+1e-9)
    peaks,_=find_peaks(z,distance=int(.35*fs),prominence=.5)
    ibi=np.diff(peaks)/fs; ibi=ibi[(ibi>=.3)&(ibi<=2.0)]
    return float(60/np.median(ibi)) if len(ibi)>=3 else np.nan


def radar_hr(rfft, rbins, fs=10.0):
    # Average chirps, unwrap the phase at each range bin, and choose the strongest cardiac band.
    x=np.mean(rfft,axis=1)
    best=(np.nan,np.nan,np.nan)
    candidate_bins = [k for k, r in enumerate(rbins) if 0.3 <= float(r) <= 2.0]
    for k in candidate_bins:
        ph=np.unwrap(np.angle(x[:,k])); ph=ph-np.polyval(np.polyfit(np.arange(len(ph)),ph,1),np.arange(len(ph)))
        f,p=periodogram(ph,fs=fs,detrend="linear")
        q=(f>=.8)&(f<=2.5)
        if not np.any(q): continue
        i=np.flatnonzero(q)[np.argmax(p[q])]; score=float(p[i]/(np.sum(p[(f>=.5)&(f<=3.0)])+1e-12))
        if np.isnan(best[2]) or score>best[2]: best=(float(f[i]*60),int(k),score)
    return best


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--max-sessions",type=int,default=0); args=ap.parse_args()
    sessions=sorted(ROOT.glob("P*/*/*/radar_rFFTs.zlib"))
    if args.max_sessions: sessions=sessions[:args.max_sessions]
    rows=[]
    for rp in sessions:
        folder=rp.parent; ecg_path=folder/"movesense_ecg.csv"
        if not ecg_path.exists(): continue
        _, ecg=read_csv(ecg_path,"mV"); rfft,rbins=load_radar(rp)
        rh,bin_idx,score=radar_hr(rfft, rbins); eh=ecg_hr(ecg)
        rows.append({"participant":rp.parts[-4],"posture":rp.parts[-3],"condition":rp.parts[-2],"radar_hr_bpm":rh,"ecg_hr_bpm":eh,"mae_bpm":abs(rh-eh) if np.isfinite(rh) and np.isfinite(eh) else None,"selected_range_bin":bin_idx,"cardiac_band_score":score})
        if len(rows)%25==0: print(f"processed {len(rows)}",flush=True)
    valid=[r for r in rows if r["mae_bpm"] is not None]
    summary={"n_sessions":len(rows),"n_valid_pairs":len(valid),"n_participants":len(set(r["participant"] for r in rows)),"radar_ecg_mae_bpm":float(np.mean([r["mae_bpm"] for r in valid])) if valid else None,"radar_ecg_bias_bpm":float(np.mean([r["radar_hr_bpm"]-r["ecg_hr_bpm"] for r in valid])) if valid else None,"note":"External physiology audit only; no FocusWave attention labels and no classifier training."}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    with (OUT/"sessions.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["participant"]); w.writeheader(); w.writerows(rows)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
