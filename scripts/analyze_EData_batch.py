# -*- coding: utf-8 -*-
"""E:\\Data 批次毫米波快速生理可用性分析。

每个被试取中段 30 s，复用项目现有窗级自适应心肺分离管线，
输出 HR/BR/HRV、信号质量门控和每被试诊断图。
"""
from __future__ import annotations

import csv, json, sys
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

SCRIPT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT))
import analyze_mmwave_hrv as rhrv
import process_vital_signs_v3_1_1 as algo

DATA_ROOT = Path(r"E:\Data")
OUT = Path(r"D:\Project\厚粲杯\08_算法\output\E_Data_20260821")
FS_DEFAULT = 98.7
WIN_S = 30.0

def get_meta(mm, sid):
    p = mm / f"sub-{sid}_mmwave.meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def get_timestamps(mm, sid):
    p = mm / f"sub-{sid}_mmwave_timestamps.csv"
    if not p.exists():
        return None, None
    frame, ms = [], []
    with p.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 3:
                try:
                    frame.append(int(row[0])); ms.append(int(row[2]))
                except ValueError:
                    pass
    return np.asarray(frame), np.asarray(ms, dtype=np.int64)

def load_mid_window(mm, sid, frame, ms, meta):
    parts = algo.collect_npz_parts(mm, pattern=f"sub-{sid}_mmwave_datacube_part*.npz")
    if not parts or len(frame) < 100:
        return None, None
    fs = float(meta.get("fps") or ((len(ms)-1) / ((ms[-1]-ms[0])/1000)) if len(ms)>1 else FS_DEFAULT)
    fs = fs if np.isfinite(fs) and fs > 5 else FS_DEFAULT
    center = len(frame) // 2
    half = int(WIN_S * fs / 2)
    lo, hi = max(0, center-half), min(len(frame), center+half)
    fa, fb = int(frame[lo]), int(frame[hi-1]) + 1
    chunks = []
    first = int(frame[0])
    i0 = max(0, (fa-first)//1000)
    i1 = min(len(parts), (fb-first+999)//1000)
    for p in parts[i0:i1]:
        d = np.load(p)
        keys = sorted([k for k in d.files if k.startswith("tx")])
        chunks.append(np.stack([d[k] for k in keys], axis=-1).astype(np.complex64))
        d.close()
    if not chunks:
        return None, fs
    iq = np.concatenate(chunks, axis=0)
    offset = first + i0*1000
    a, b = fa-offset, fb-offset
    return iq[max(0,a):min(len(iq),b)], fs

def quality_label(res, fs):
    if res is None:
        return "不可用"
    x, info, brinfo = res
    hr, br = x.get("hr_time_bpm"), x.get("br_freq_bpm")
    hrv = x.get("hrv") or {}
    ibi = np.asarray(hrv.get("ibi_ms") or [], dtype=float)
    ok_hr = hr is not None and 40 <= hr <= 120
    ok_br = br is not None and 6 <= br <= 35
    ok_ibi = len(ibi) >= 15 and np.all((ibi >= 300) & (ibi <= 2000))
    if ok_hr and ok_br and ok_ibi:
        return "可计算"
    if ok_br:
        return "仅呼吸可计算"
    return "不可解释"

def band_snr_db(iq, fs, ch, b, lo, hi):
    """带内峰值相对带外稳健噪声底的功率比，作为可比性质量代理，不是仪器校准 SNR。"""
    if iq is None or ch is None or b is None or len(iq) < 100:
        return None
    phi=np.unwrap(np.angle(iq[:, int(b), int(ch)]))
    f,p=signal.periodogram(signal.detrend(phi),fs=fs,window='hann')
    band=(f>=lo)&(f<=hi); allband=(f>=.05)&(f<=3.0)&~band
    if not band.any() or not allband.any(): return None
    return round(float(10*np.log10((np.max(p[band])+1e-15)/(np.median(p[allband])+1e-15))),2)

def make_plot(sid, iq, fs, res, path):
    fig, ax = plt.subplots(3, 1, figsize=(12, 8), constrained_layout=True)
    if iq is not None and len(iq):
        # 取最佳通道的主峰距离单元，画相位和功率谱
        ch = 0
        ph = np.unwrap(np.angle(iq[:, :, ch]), axis=0)
        b = int(np.argmax(np.nanmedian(np.abs(iq)**2, axis=(0,2))))
        raw = signal.detrend(ph[:, b])
        t = np.arange(len(raw))/fs
        ax[0].plot(t, raw, lw=.5, color="#245b8a")
        ax[0].set_ylabel("相位 (rad)"); ax[0].set_title(f"sub-{sid} 中段 {WIN_S:.0f}s 原始相位, bin={b}")
        f, p = signal.periodogram(raw, fs=fs)
        ax[1].plot(f, 10*np.log10(p+1e-12), color="#8a3d62")
        ax[1].set_xlim(0, 3); ax[1].set_ylabel("PSD (dB)"); ax[1].set_xlabel("Hz")
        ax[1].axvspan(.1,.5,color="green",alpha=.12); ax[1].axvspan(.8,2.0,color="red",alpha=.10)
    else:
        ax[0].text(.5,.5,"无可用窗口",ha="center",va="center")
    labels, vals = [], []
    if res is not None:
        x = res[0]; h = x.get("hrv") or {}
        for k in ["hr_time_bpm","br_freq_bpm"]:
            if x.get(k) is not None: labels.append(k.replace("_bpm","")); vals.append(float(x[k]))
        for k in ["SDNN_ms","RMSSD_ms"]:
            if h.get(k) is not None: labels.append(k.replace("_ms","")); vals.append(float(h[k]))
    if vals: ax[2].bar(labels, vals, color=["#c95050","#5a9d68","#5276a8","#b38a42"][:len(vals)])
    ax[2].set_title("估计指标（HR/BR 为 bpm，HRV 为 ms）"); ax[2].grid(axis="y",alpha=.25)
    fig.savefig(path, dpi=150); plt.close(fig)

def main():
    OUT.mkdir(parents=True, exist_ok=True); (OUT/"plots").mkdir(exist_ok=True)
    rows=[]
    subs=sorted([p.name[4:-1] for p in DATA_ROOT.glob("sub-*_") if p.is_dir()])
    for sid in subs:
        mm=DATA_ROOT/f"sub-{sid}_"/"mmwave"; meta=get_meta(mm,sid); frame,ms=get_timestamps(mm,sid)
        row={"subject":sid,"meta_fps":meta.get("fps"),"frame_count":meta.get("frame_count"),"duration_s":meta.get("duration_s")}
        try:
            iq,fs=load_mid_window(mm,sid,frame,ms,meta); rhrv.FS=fs; rhrv.BIN_OFFSET=0
            res=rhrv.analyze_window_auto(iq, method="vmd_heart") if iq is not None else None
            row["analysis_fs"]=round(fs,3) if fs else None; row["quality"]=quality_label(res,fs)
            if res is not None:
                x,info,brinfo=res; h=x.get("hrv") or {}
                row.update({"hr_bpm":x.get("hr_time_bpm"),"br_bpm":x.get("br_freq_bpm"),"heart_ch":info.get("ch"),"heart_bin":info.get("bin"),"resp_ch":brinfo.get("ch"),"resp_bin":brinfo.get("bin"),"sdnn_ms":h.get("SDNN_ms"),"rmssd_ms":h.get("RMSSD_ms"),"n_ibi":len(h.get("ibi_ms") or [])})
                row["hr_snr_proxy_db"] = band_snr_db(iq,fs,info.get("ch"),info.get("bin"),.8,2.0)
                row["br_snr_proxy_db"] = band_snr_db(iq,fs,brinfo.get("ch"),brinfo.get("bin"),.1,.5)
            make_plot(sid,iq,fs,res,OUT/"plots"/f"sub-{sid}_mid30s.png")
        except Exception as e:
            row["quality"]="ERROR"; row["error"]=repr(e)
        rows.append(row); print(sid, row.get("quality"), row.get("hr_bpm"), row.get("br_bpm"), row.get("rmssd_ms"), flush=True)
    import pandas as pd
    df=pd.DataFrame(rows); df.to_csv(OUT/"E_Data_mid30s_metrics.csv",index=False,encoding="utf-8-sig")
    df.to_json(OUT/"E_Data_mid30s_metrics.json",orient="records",force_ascii=False,indent=2)
    print("saved", OUT)

if __name__ == "__main__": main()
