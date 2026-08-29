# -*- coding: utf-8 -*-
"""C1d Radar-Beat/RF-Heartbeat-style backend-only pilot.

Input is the persisted C1c waveform only. No raw ADC, range selection, FFT,
phase extraction, VMD or ECG-informed parameter fitting occurs here.
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, r"D:\Project\厚粲杯\08_算法\scripts")
import run_c1c_mmhrv_pilot as c1c

OUT = c1c.OUT_ROOT
SUBJECTS = ["97793", "9779", "97795"]

CONFIG = {
    "template_window_rule": "median local-peak interval; symmetric one-cycle windows",
    "template_generation": "median of robustly normalized local-peak-centered cycles",
    "similarity": "sliding normalized cross-correlation",
    "dp_interval_rule": "estimated mean interval +/- 3 sample SD, clipped to 0.30-2.00 s",
    "dp_objective": "similarity at beat centers minus quadratic interval penalty",
    "template_and_dp_use_ecg": False,
    "parameters_fitted_to_ecg": False,
    "source_scope": "Radar-Beat 2023 / RF-Heartbeat published backend concept; unspecified numerical details frozen here",
}

def zscore(x):
    x=np.asarray(x,float); return (x-np.mean(x))/(np.std(x)+1e-12)

def make_template(x, peaks, fs):
    p=np.asarray(peaks,int); p=p[(p>0)&(p<len(x))]
    if len(p)<5: raise ValueError("fewer than 5 local peaks for template")
    r0=int(round(np.median(np.diff(p))))
    half=max(10,r0//2); segs=[]
    for q in p:
        if q-half>=0 and q+half<len(x): segs.append(zscore(x[q-half:q+half+1]))
    if len(segs)<5: raise ValueError("fewer than 5 complete template cycles")
    a=np.vstack(segs); return np.median(a,axis=0), r0, float(np.std(np.diff(p)))

def similarity(x, template):
    n=len(x); m=len(template); half=m//2; s=np.full(n,np.nan)
    t=zscore(template)
    for i in range(half,n-half): s[i]=float(np.dot(zscore(x[i-half:i+half+1]),t)/len(t))
    return s

def global_dp(sim, r0, sd):
    n=len(sim); sd=max(float(sd),2.0); lo=max(30,int(round(r0-3*sd))); hi=min(200,int(round(r0+3*sd)))
    dp=np.full(n,-np.inf); prev=np.full(n,-1,int)
    start=max(1,lo); dp[start:]=sim[start:]
    lam=0.25/(sd*sd)
    for t in range(start+1,n):
        if not np.isfinite(sim[t]): continue
        a=max(start,t-hi); b=min(t-lo,n-1)
        if b<a: continue
        cand=np.arange(a,b+1); vals=dp[cand]+sim[t]-lam*(cand-(t-r0))**2
        j=int(np.argmax(vals))
        if np.isfinite(vals[j]): dp[t]=vals[j]; prev[t]=cand[j]
    end=int(np.nanargmax(dp))
    path=[]
    while end>=0 and np.isfinite(dp[end]):
        path.append(end); end=int(prev[end])
        if end<0: break
    return np.asarray(path[::-1],int), {"r0_samples":r0,"sd_samples":sd,"allowed_interval_samples":[lo,hi],"n_centers":len(path)}

def plot_diag(path, x, sim, local, dp, fs, subject):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    t=np.arange(len(x))/fs; fig,ax=plt.subplots(3,1,figsize=(15,8),sharex=True)
    ax[0].plot(t,x,lw=.4); ax[0].set_title(f"{subject} fixed C1c waveform")
    ax[1].plot(t,sim,lw=.5); ax[1].set_title("template similarity")
    ax[2].plot(t,x,lw=.4,label="waveform")
    ax[2].plot(local/fs,x[local],"rx",ms=3,label="local peaks")
    ax[2].plot(dp/fs,x[dp],"go",ms=3,label="global DP")
    ax[2].legend(); ax[2].grid(alpha=.2); fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)

def main():
    rows=[]; diagnostics=[]
    for s in SUBJECTS:
        p=OUT/s/"c1c_waveforms_replayed.npz"
        if not p.exists(): raise FileNotFoundError(p)
        with np.load(p) as d:
            fs=float(d["sampling_rate_hz"]); x=np.asarray(d["normalized_heartbeat"],float); local_t=np.asarray(d["local_peak_times_s"],float); ref=np.asarray(d["ecg_peak_times_s"],float)
        local_all=np.asarray(np.round(local_t*fs),int)
        local=local_all[(local_all >= 0) & (local_all < len(x))]
        templ,r0,sd=make_template(x,local,fs); sim=similarity(x,templ); dp,dpq=global_dp(sim,r0,sd); dp_t=dp/fs
        for method,est in [("c1c_local_peak",local_t),("c1d_radarbeat_global_dp",dp_t)]:
            for tol in c1c.TOLERANCES_MS:
                m=c1c.metrics(ref,est,tol,c1c.FIXED_DELAY_MS); m.update({"subject":s,"method":method,"tolerance_ms":tol,"fixed_delay_ms":c1c.FIXED_DELAY_MS}); rows.append(m)
        out=OUT/s
        np.savez_compressed(out/"c1d_similarity_dp_assets.npz",template=templ,similarity=sim,local_peak_times_s=local_t,dp_peak_times_s=dp_t)
        (out/"c1d_diagnostics.json").write_text(json.dumps({"subject":s,"config":CONFIG,"dp":dpq,"template_samples":len(templ)},indent=2),encoding="utf-8")
        plot_diag(out/"c1d_template_similarity_dp.png",x,sim,local,dp,fs,s); diagnostics.append({"subject":s,**dpq,"n_local_all":len(local_all),"n_local_in_waveform":len(local)})
    fields=sorted({k for r in rows for k in r})
    with (OUT/"c1d_metrics_long.csv").open("w",newline="",encoding="utf-8-sig") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    primary=[r for r in rows if r["tolerance_ms"]==c1c.PRIMARY_TOLERANCE_MS]
    with (OUT/"c1d_metrics_primary.csv").open("w",newline="",encoding="utf-8-sig") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(primary)
    # Frozen success rule: mean F1 +0.10 and >=2/3 session F1 directionally improved; IBI MAE not worsened.
    l=[r for r in primary if r["method"]=="c1c_local_peak"]; g=[r for r in primary if r["method"]=="c1d_radarbeat_global_dp"]
    lm={r["subject"]:r for r in l}; gm={r["subject"]:r for r in g}
    diffs=[float(gm[s]["f1"])-float(lm[s]["f1"]) for s in SUBJECTS]
    ibi_diffs=[float(gm[s]["ibi_mae_ms"])-float(lm[s]["ibi_mae_ms"]) for s in SUBJECTS]
    mean_gain=float(np.mean(diffs)); improved=sum(x>0 for x in diffs)
    success=bool(mean_gain>=0.10 and improved>=2 and all(x<=0 for x in ibi_diffs))
    status="C1D_PASS_CONTINUE_REVIEW" if success else "C1D_NO_MATERIAL_IMPROVEMENT_STOP_HRV"
    (OUT/"c1d_decision.json").write_text(json.dumps({"status":status,"subjects":SUBJECTS,"scope":"C1c waveform only; same-session baseline waveform unavailable","mean_f1_gain":mean_gain,"sessions_f1_improved":improved,"f1_differences":dict(zip(SUBJECTS,diffs)),"ibi_mae_differences_ms":dict(zip(SUBJECTS,ibi_diffs)),"success_rule":{"mean_f1_gain_min":0.10,"sessions_improved_min":2,"ibi_mae_not_worse":True},"config":CONFIG},indent=2),encoding="utf-8")
if __name__=="__main__": main()


