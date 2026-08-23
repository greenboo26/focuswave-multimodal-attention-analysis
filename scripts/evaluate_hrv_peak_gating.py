# -*- coding: utf-8 -*-
"""评估带 HR 先验的毫米波逐搏峰质量门控，不改主算法。"""
from __future__ import annotations
import csv,json
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks

REF=Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821\reference_metrics.json")
ROWS=Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821\mmwave_vs_reference_probes.csv")
ROOT=Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_mmwave_FAST")
OUT=Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821\hrv_gating_evaluation.json")
FS=100.0

def to_s(p,t):
 p=np.asarray(p,float); return t[np.clip(p.astype(int),0,len(t)-1)] if len(p) and np.nanmax(p)>np.nanmax(t)+1 else p

def calc(pk, expected):
 d=np.diff(pk)/FS; ref=60.0/expected
 # 先剔除半周期倍频和明显漏峰造成的双周期，再计算短窗 HRV。
 d=d[(d>=max(.30,.65*ref))&(d<=min(2.0,1.45*ref))]
 if len(d)<3:return None
 return {'hr':60/np.median(d),'rmssd':np.sqrt(np.mean(np.diff(d)**2))*1000,'sdnn':np.std(d,ddof=1)*1000,'n':len(d)}

def main():
 refs={s['subject']:s for s in json.loads(REF.read_text(encoding='utf-8'))}
 rows=list(csv.DictReader(open(ROWS,encoding='utf-8-sig'))); cache={}; configs=[(m,p) for m in (.55,.65,.75,.85) for p in (.05,.1,.15,.2)]; allres={str(c):[] for c in configs}
 for r in rows:
  sub=r['subject']; s=refs[sub]; p=ROOT/sub/f"{sub.rstrip('_')}_ses-SART_mmwave_vital_signs.npz"
  if not p.exists() or s.get('mmwave_start_ms') is None:continue
  if sub not in cache:
   d=np.load(p,allow_pickle=True); t=np.asarray(d['t'],float); hb=np.asarray(d['heartbeat'],float); ht=np.asarray(d.get('hr_course_time_s',[]),float); hc=np.asarray(d.get('hr_course_fused_bpm',[]),float); cache[sub]=(t,hb,ht,hc)
  t,hb,ht,hc=cache[sub]; tp=(int(r['onset_ms'])-s['mmwave_start_ms'])/1000; a=max(0,int((tp-60)*FS)); b=min(len(hb),int(tp*FS)); x=hb[a:b]; expected=np.nanmedian(hc[(ht>tp-60)&(ht<=tp)]) if len(ht) else np.nanmedian(hc)
  if not np.isfinite(expected) or expected<=0:continue
  sig=(x-np.median(x))/(np.std(x)+1e-9); period=FS*60/expected
  for mult,prom in configs:
   pk,_=find_peaks(sig,distance=int(mult*period),prominence=prom)
   m=calc(pk,expected)
   if m:
    m.update({'hr_ref':float(r['hr_ecg_bpm']),'rmssd_ref':float(r['rmssd_ecg_ms']),'subject':sub,'attention':int(r['attention'])})
    allres[str((mult,prom))].append(m)
 summary={}
 for k,vals in allres.items():
  if not vals:continue
  summary[k]={'n':len(vals),'hr_mae':float(np.mean([abs(v['hr']-v['hr_ref']) for v in vals])),'rmssd_mae':float(np.mean([abs(v['rmssd']-v['rmssd_ref']) for v in vals])),'median_n_ibi':float(np.median([v['n'] for v in vals]))}
 OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
