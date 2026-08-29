# -*- coding: utf-8 -*-
"""Deterministic C1c replay: fixed channel/bin, save missing waveforms."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.signal import find_peaks

SCRIPT = Path(r"D:\Project\厚粲杯\08_算法\scripts")
sys.path.insert(0, str(SCRIPT))
import run_c1c_mmhrv_pilot as c1c

FIXED = {"97793": (0,15), "9779": (4,12), "97795": (3,24)}

def replay(subject):
    root=c1c.RAW_ROOT/f"sub-{subject}_"; mm=root/"mmwave"; prefix=f"sub-{subject}_mmwave"
    raw=c1c.load_raw(mm,prefix); ts=c1c.load_ts(mm,prefix)
    n=min(len(raw),len(ts),c1c.PILOT_FRAMES); raw=raw[:n]; ts=ts[:n]
    rfft=c1c.range_fft(raw); ch,b=FIXED[subject]
    phase=np.unwrap(np.angle(rfft[:,b,ch]))
    h,vmd,norm=c1c.c1c_peaks(phase); h=np.asarray(vmd.pop("heartbeat_component"));
    acq=root/f"{subject}.acq"
    if not acq.exists(): acq=next(root.glob("*.acq"))
    ref,_=c1c.ecg_peaks_for_session(acq,root/"beh"/"events.csv",ts[0],ts[-1])
    t=(ts-ts[0])/1000.0
    est=t[c1c.peaks(norm)]
    ref_s=(ref-ts[0])/1000.0
    rows=[]
    for tol in c1c.TOLERANCES_MS:
        m=c1c.metrics(ref_s,est,tol,c1c.FIXED_DELAY_MS); m.update({"subject":subject,"method":"c1c_mmhrv_adaptive_vmd","tolerance_ms":tol,"fixed_delay_ms":c1c.FIXED_DELAY_MS}); rows.append(m)
    out=c1c.OUT_ROOT/subject; out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/"c1c_waveforms_replayed.npz",time_s=t,sampling_rate_hz=c1c.FS_RADAR,selected_channel=ch,selected_bin=b,selected_complex_slow_time=rfft[:,b,ch],unwrapped_phase=phase,heartbeat_component=h,normalized_heartbeat=norm,local_peak_times_s=est,ecg_peak_times_s=ref_s)
    (out/"replay_manifest.json").write_text(json.dumps({"status":"C1C_REPLAY_COMPLETE","subject":subject,"selected_channel":ch,"selected_bin":b,"raw_frames":n,"sampling_rate_hz":c1c.FS_RADAR,"reuse":"fixed diagnostics.json channel/bin and frozen C1c parameters; no re-selection"},indent=2),encoding="utf-8")
    return rows

def main():
    rows=[]
    for s in ["97793","9779","97795"]: rows.extend(replay(s))
    fields=sorted({k for r in rows for k in r})
    with (c1c.OUT_ROOT/"c1c_replay_metrics_long.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
if __name__=="__main__": main()


