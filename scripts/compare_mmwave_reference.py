# -*- coding: utf-8 -*-
"""将 ACQ ECG/RSP 参考窗口与毫米波 NPZ 的同一探针窗口配对。"""
from __future__ import annotations
import csv, json, os, argparse
from pathlib import Path
import numpy as np

REF_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821")
MM_ROOT = Path(os.environ.get("ACQ_MMWAVE_ROOT", r"D:\Project\厚粲杯\08_算法\output\ACQ_mmwave_BP"))
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821")


def peaks_s(peaks, t):
    p = np.asarray(peaks, float)
    if p.size == 0: return p
    return t[np.clip(p.astype(int), 0, len(t)-1)] if np.nanmax(p) > np.nanmax(t) + 1 else p


def metric_window(pk, a, b):
    p = pk[(pk > a) & (pk <= b)]
    ibi = np.diff(p); ibi = ibi[np.isfinite(ibi) & (ibi >= .3) & (ibi <= 2.)]
    return (float(60/np.median(ibi)) if len(ibi)>=3 else None,
            float(np.sqrt(np.mean(np.diff(ibi)**2))*1000) if len(ibi)>=3 else None,
            float(np.std(ibi,ddof=1)*1000) if len(ibi)>=3 else None,
            int(len(ibi)))


def rate_window(pk, a, b, lo, hi):
    p = pk[(pk > a) & (pk <= b)]
    d = np.diff(p); d = d[np.isfinite(d) & (d >= lo) & (d <= hi)]
    return float(60 / np.median(d)) if len(d) >= 2 else None


def main():
    ap = argparse.ArgumentParser(description="Compare mmWave vital signs with ACQ ECG/RSP reference.")
    ap.add_argument("--window-s", type=float, default=60.0,
                    help="comparison window ending at the behavior event (30 or 60 s)")
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    refs = json.loads((REF_ROOT/'reference_metrics.json').read_text(encoding='utf-8'))
    refmap = {x['subject']: x for x in refs}
    rows=[]
    for sub, s in refmap.items():
        npz = MM_ROOT/sub/f"{sub.rstrip('_')}_ses-SART_mmwave_vital_signs.npz"
        if not npz.exists(): continue
        d=np.load(npz,allow_pickle=True); t=np.asarray(d['t'],float)
        pk=peaks_s(d.get('heart_peaks',[]),t)
        bpk=peaks_s(d.get('breath_peaks',[]),t)
        hr_t=np.asarray(d.get('hr_course_time_s',[]),float)
        hr_c=np.asarray(d.get('hr_course_fused_bpm',[]),float)
        for r in s.get('probes',[]):
            tp=(r['onset_ms']-s['mmwave_start_ms'])/1000
            ws = float(args.window_s)
            hr,rm,sd,n=metric_window(pk,tp-ws,tp)
            br=rate_window(bpk,tp-ws,tp,2.0,10.0)
            hm=hr_c[(hr_t > tp-ws) & (hr_t <= tp) & np.isfinite(hr_c)]
            hr_ref_key = 'hr_ecg_bpm_30s' if ws <= 30.0 else 'hr_ecg_bpm'
            rm_ref_key = 'rmssd_ecg_ms_30s' if ws <= 30.0 else 'rmssd_ecg_ms'
            sd_ref_key = 'sdnn_ecg_ms_30s' if ws <= 30.0 else 'sdnn_ecg_ms'
            br_ref_key = 'br_rsp_bpm_30s' if ws <= 30.0 else 'br_rsp_bpm'
            hr_course=float(np.median(hm)) if len(hm) else None
            rows.append({'subject':sub,'onset_ms':r['onset_ms'],'attention':r['attention'],
                         'window_s': ws, 'hr_ecg_bpm':r.get(hr_ref_key),'rmssd_ecg_ms':r.get(rm_ref_key),
                         'sdnn_ecg_ms':r.get(sd_ref_key),'hr_mm_bpm':hr,
                         'rmssd_mm_ms':rm,'sdnn_mm_ms':sd,'n_ibi_mm':n,
                         'br_rsp_bpm':r.get(br_ref_key),'br_mm_bpm':br,
                         'hr_course_mm_bpm':hr_course,
                         'hr_error_bpm':hr-float(r['hr_ecg_bpm']) if hr is not None else None,
                         'hr_course_error_bpm':hr_course-float(r['hr_ecg_bpm']) if hr_course is not None else None,
                         'br_error_bpm':br-float(r['br_rsp_bpm']) if br is not None and r.get('br_rsp_bpm') is not None else None,
                         'rmssd_error_ms':rm-float(r['rmssd_ecg_ms']) if rm is not None else None})
    OUT_ROOT.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else ['subject']
    output = args.output or (OUT_ROOT / f'mmwave_vs_reference_probes_{int(args.window_s)}s.csv')
    with open(output,'w',newline='',encoding='utf-8-sig') as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows(rows)
    print('paired_windows',len(rows),'subjects',len(set(r['subject'] for r in rows)), 'window_s', args.window_s, 'output', output)
    if rows:
        for k in ('hr_error_bpm','hr_course_error_bpm','br_error_bpm','rmssd_error_ms'):
            x=np.array([r[k] for r in rows if r[k] is not None],float)
            print(k,'n',len(x),'MAE',float(np.mean(np.abs(x))),'bias',float(np.mean(x)),'median',float(np.median(x)))


if __name__=='__main__': main()
