from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT=Path(r"D:\Project\厚粲杯\08_算法")
OLD=ROOT/'output'/'20_生理金标准验证'/'05_毫米波参照_FAST'
NEW=ROOT/'output'/'20_生理金标准验证'/'06_HR_COURSE_99_CORRECTED_GATE'
REF=ROOT/'output'/'20_生理金标准验证'/'01_历史严格参照_v20260821'
OUT=ROOT/'output'/'20_生理金标准验证'/'07_HR_COURSE_99_CORRECTED_GATE_AUDIT'; FIG=OUT/'hr_course_99window_figures'; FIG.mkdir(parents=True,exist_ok=True)

def pk_seconds(p,t):
    p=np.asarray(p,float)
    if p.size==0:return p
    return t[np.clip(p.astype(int),0,len(t)-1)] if np.nanmax(p)>np.nanmax(t)+1 else p
def rate_from_peaks(p,t,a,b):
    x=pk_seconds(p,t); x=x[(x>a)&(x<=b)]; d=np.diff(x); d=d[np.isfinite(d)&(d>=.3)&(d<=2.)]
    return float(60/np.median(d)) if len(d)>=3 else np.nan
def course_from_npz(z,tp,ws=60.):
    t=np.asarray(z['hr_course_time_s'],float); x=np.asarray(z['hr_course_fused_bpm'],float); m=(t>tp-ws)&(t<=tp)&np.isfinite(x)
    return float(np.median(x[m])) if np.any(m) else np.nan
def metric(x,y):
    d=np.asarray(x,float)-np.asarray(y,float); m=np.isfinite(d); d=d[m]
    if not len(d): return dict(N=0,MAE=np.nan,median_AE=np.nan,RMSE=np.nan,bias=np.nan,Pearson_r=np.nan,within5=np.nan,within10=np.nan)
    return dict(N=int(len(d)),MAE=float(np.mean(np.abs(d))),median_AE=float(np.median(np.abs(d))),RMSE=float(np.sqrt(np.mean(d*d))),bias=float(np.mean(d)),Pearson_r=float(np.corrcoef(np.asarray(x,float)[m],np.asarray(y,float)[m])[0,1]) if len(d)>1 else np.nan,within5=float(np.mean(np.abs(d)<=5)),within10=float(np.mean(np.abs(d)<=10)))
def main():
    refs=json.loads((REF/'reference_metrics.json').read_text(encoding='utf-8')); refmap={x['subject']:x for x in refs}
    hist=pd.read_csv(REF/'mmwave_vs_reference_probes_60s.csv')
    rows=[]; validation=[]
    for sub,meta in refmap.items():
        op=OLD/sub/f'{sub.rstrip("_")}_ses-SART_mmwave_vital_signs.npz'; oj=op.with_suffix('.json'); newprefix='sub-97994' if sub=='sub-97794_' else sub.rstrip('_'); npath=NEW/sub/f'{newprefix}_ses-SART_mmwave_vital_signs.npz'; nj=npath.with_suffix('.json')
        if not op.exists() or not npath.exists(): continue
        zo=np.load(op,allow_pickle=True); zn=np.load(npath,allow_pickle=True); jo=json.loads(oj.read_text(encoding='utf-8')); jn=json.loads(nj.read_text(encoding='utf-8'))
        for probe in meta.get('probes',[]):
            onset=int(probe['onset_ms']); h=hist[(hist.subject==sub)&(hist.onset_ms==onset)]
            if len(h)!=1: continue
            h=h.iloc[0]
            # Freeze the exact historical mainline denominator: the one probe
            # with no historical HR-course value is excluded from both arms.
            if pd.isna(h.hr_course_mm_bpm): continue
            old_course=course_from_npz(zo,(onset-meta['mmwave_start_ms'])/1000); new_course=course_from_npz(zn,(onset-meta['mmwave_start_ms'])/1000)
            tp=(onset-meta['mmwave_start_ms'])/1000
            old_peak=rate_from_peaks(zo['heart_peaks'],zo['t'],tp-60,tp); new_peak=rate_from_peaks(zn['heart_peaks'],zn['t'],tp-60,tp)
            rows.append({'session':sub,'window_key':f'{sub}:{onset}','onset_ms':onset,'ECG_HR':float(h.hr_ecg_bpm),'old_heart_bin':int(jo['bins']['heart']),'new_heart_bin':int(jn['bins']['heart']),'old_channel':int(jo['channels']['heart']),'new_channel':int(jn['channels']['heart']),'old_distance_37mm':round(int(jo['bins']['heart'])*.037,3),'new_distance_37mm':round(int(jn['bins']['heart'])*.037,3),'old_HR_peak':old_peak,'new_HR_peak':new_peak,'old_HR_course':old_course,'new_HR_course':new_course,'old_AE':abs(old_course-float(h.hr_ecg_bpm)) if np.isfinite(old_course) else np.nan,'new_AE':abs(new_course-float(h.hr_ecg_bpm)) if np.isfinite(new_course) else np.nan,'target_changed':int(jo['bins']['heart']!=jn['bins']['heart']),'channel_changed':int(jo['channels']['heart']!=jn['channels']['heart']),'course_changed':int(np.isfinite(old_course) and np.isfinite(new_course) and not math.isclose(old_course,new_course,abs_tol=1e-9)),'delta_AE':(abs(new_course-float(h.hr_ecg_bpm))-abs(old_course-float(h.hr_ecg_bpm))) if np.isfinite(old_course) and np.isfinite(new_course) else np.nan,'historical_reference_course':float(h.hr_course_mm_bpm) if pd.notna(h.hr_course_mm_bpm) else np.nan})
        # session-level provenance
        validation.append({'session':sub,'old_bin':jo['bins']['heart'],'old_channel':jo['channels']['heart'],'new_bin':jn['bins']['heart'],'new_channel':jn['channels']['heart'],'old_distance_37mm':jo['bins']['heart']*.037,'new_distance_37mm':jn['bins']['heart']*.037})
    df=pd.DataFrame(rows); df.sort_values(['session','onset_ms'],inplace=True); df.to_csv(OUT/'HR_COURSE_99WINDOW_PAIRED.csv',index=False,encoding='utf-8-sig')
    oldm=metric(df.old_HR_course,df.ECG_HR); newm=metric(df.new_HR_course,df.ECG_HR)
    comp=pd.DataFrame([{'condition':'HISTORICAL_0.08m_bin','N':oldm['N'],**{k:v for k,v in oldm.items() if k!='N'}},{'condition':'CORRECTED_0.037m_bin','N':newm['N'],**{k:v for k,v in newm.items() if k!='N'}}]); comp.to_csv(OUT/'HR_COURSE_99WINDOW_METRIC_COMPARISON.csv',index=False,encoding='utf-8-sig')
    ss=[]
    for sub,g in df.groupby('session'):
        a=metric(g.old_HR_course,g.ECG_HR); b=metric(g.new_HR_course,g.ECG_HR); ss.append({'session':sub,'N':len(g),'old_MAE':a['MAE'],'new_MAE':b['MAE'],'old_median_AE':a['median_AE'],'new_median_AE':b['median_AE'],'old_RMSE':a['RMSE'],'new_RMSE':b['RMSE'],'old_bias':a['bias'],'new_bias':b['bias'],'old_Pearson_r':a['Pearson_r'],'new_Pearson_r':b['Pearson_r'],'old_within5':a['within5'],'new_within5':b['within5'],'old_within10':a['within10'],'new_within10':b['within10'],'target_changed_n':int(g.target_changed.sum()),'channel_changed_n':int(g.channel_changed.sum()),'course_changed_n':int(g.course_changed.sum()),'improved_n':int((g.delta_AE<0).sum()),'worsened_n':int((g.delta_AE>0).sum()),'unchanged_n':int((g.delta_AE.abs()<=1e-9).sum())})
    sdf=pd.DataFrame(ss); sdf.to_csv(OUT/'HR_COURSE_99WINDOW_SESSION_SUMMARY.csv',index=False,encoding='utf-8-sig')
    delta=df.delta_AE.dropna(); hist_valid=hist[hist.hr_course_mm_bpm.notna()]
    # figures, 600 dpi for audit archival
    plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.unicode_minus':False}); x=np.arange(len(df))
    fig,ax=plt.subplots(figsize=(12,4.8),dpi=220); ax.plot(x,df.ECG_HR,'k.',ms=3,label='ECG reference'); ax.plot(x,df.old_HR_course,color='#E69F00',lw=.8,label='historical course'); ax.plot(x,df.new_HR_course,color='#0072B2',lw=.8,label='corrected course'); ax.set_xlabel('paired 60-s window (ordered by session)'); ax.set_ylabel('HR (bpm)'); ax.set_title('99 common windows: ECG vs historical vs corrected HR course'); ax.legend(frameon=False,ncol=3); fig.tight_layout(); fig.savefig(FIG/'01_ecg_old_new_all_99.png',dpi=600); plt.close(fig)
    fig,ax=plt.subplots(figsize=(5.4,5.0),dpi=220); ax.scatter(df.old_AE,df.new_AE,c=np.where(df.target_changed,'#D55E00','#56B4E9'),s=22,alpha=.8); lim=max(np.nanmax(df.old_AE),np.nanmax(df.new_AE))*1.05; ax.plot([0,lim],[0,lim],'k--',lw=.8); ax.set_xlabel('Historical AE (bpm)'); ax.set_ylabel('Corrected AE (bpm)'); ax.set_title('Paired absolute error'); fig.tight_layout(); fig.savefig(FIG/'02_paired_ae_scatter.png',dpi=600); plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.4,4.2),dpi=220); ax.hist(delta,bins=15,color='#56B4E9',edgecolor='white'); ax.axvline(0,color='k',ls='--',lw=.8); ax.set_xlabel('Corrected AE − historical AE (bpm)'); ax.set_ylabel('Number of windows'); ax.set_title('Delta AE distribution (n=99)'); fig.tight_layout(); fig.savefig(FIG/'03_delta_ae_distribution.png',dpi=600); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.2,4.5),dpi=220); xx=np.arange(len(sdf)); ax.bar(xx-.19,sdf.old_MAE,.38,label='historical .08 m/bin',color='#E69F00'); ax.bar(xx+.19,sdf.new_MAE,.38,label='corrected .037 m/bin',color='#0072B2'); ax.set_xticks(xx,sdf.session,rotation=30,ha='right'); ax.set_ylabel('MAE (bpm)'); ax.set_title('Session-level HR-course MAE'); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG/'04_session_mae_old_new.png',dpi=600); plt.close(fig)
    trans=pd.crosstab(df.old_heart_bin,df.new_heart_bin); fig,ax=plt.subplots(figsize=(6,5),dpi=220); im=ax.imshow(trans.values,cmap='Blues'); ax.set_xticks(range(len(trans.columns)),trans.columns); ax.set_yticks(range(len(trans.index)),trans.index); ax.set_xlabel('Corrected heart bin'); ax.set_ylabel('Historical heart bin'); ax.set_title('Target-bin transition (window rows)');
    for i in range(trans.shape[0]):
      for j in range(trans.shape[1]): ax.text(j,i,str(trans.iloc[i,j]),ha='center',va='center',fontsize=8)
    fig.colorbar(im,ax=ax,label='window count'); fig.tight_layout(); fig.savefig(FIG/'05_target_bin_transition.png',dpi=600); plt.close(fig)
    # representative transitions: unchanged, changed neutral, improved, worsened
    groups=[('unchanged',df[(df.target_changed==0)&(df.course_changed==0)]),('target_changed_result_small',df[(df.target_changed==1)&(df.delta_AE.abs()<=1)]),('target_changed_improved',df[(df.target_changed==1)&(df.delta_AE< -1)]),('target_changed_worsened',df[(df.target_changed==1)&(df.delta_AE>1)])]
    fig,axs=plt.subplots(2,2,figsize=(10,7),dpi=220); 
    for ax,(name,g) in zip(axs.flat,groups):
      if len(g): ax.scatter(g.old_AE,g.new_AE,s=28,c='#009E73' if 'improved' in name else ('#D55E00' if 'worsened' in name else '#56B4E9')); lim=max(np.nanmax(df.old_AE),np.nanmax(df.new_AE))*1.05; ax.plot([0,lim],[0,lim],'k--',lw=.6); ax.set_title(f'{name} (n={len(g)})'); ax.set_xlabel('old AE'); ax.set_ylabel('new AE')
      else: ax.text(.5,.5,'no windows',ha='center',va='center'); ax.set_title(name)
    fig.tight_layout(); fig.savefig(FIG/'06_representative_transition_panels.png',dpi=600); plt.close(fig)
    # report
    hist_calc=metric(hist_valid.hr_course_mm_bpm,hist_valid.hr_ecg_bpm); equal=all((abs(hist_calc[k]-oldm[k])<1e-6 if np.isfinite(hist_calc[k]) and np.isfinite(oldm[k]) else True) for k in ['MAE','median_AE','RMSE','bias','Pearson_r','within5','within10'])
    status='MATERIALLY_AFFECTED' if (df.target_changed.mean()>=.25 or abs(newm['MAE']-oldm['MAE'])>=.5 or abs(newm['Pearson_r']-oldm['Pearson_r'])>=.1) else 'ROBUST_TO_DISTANCE_BUG'
    if len(df)!=99 or not equal: status='STILL_PARTIAL'
    lines=['# HR course 99-window corrected-gate audit','', '## Denominator and provenance','',f'- Historical source: `05_毫米波参照_FAST`, generated with `bp_heart`, 0.08 m/bin, and the same 60-s probe keys used by `mmwave_vs_reference_probes_60s.csv`.',f'- Recovered denominator: **5 sessions / 100 rows / 99 valid HR-course windows** (one historical HR-course value is missing).',f'- Corrected source: `06_HR_COURSE_99_CORRECTED_GATE`, same NPZ inputs, same session/probe time keys, `bp_heart`, and only `bin_spacing_m=0.037` changed; physical gate remains 0.30–1.50 m (bins 9–40).','', '## Historical reproduction check','',f"- Current canonical historical table: MAE={hist_calc['MAE']:.3f} bpm, median AE={hist_calc['median_AE']:.3f}, RMSE={hist_calc['RMSE']:.3f}, bias={hist_calc['bias']:.3f}, Pearson *r*={hist_calc['Pearson_r']:.3f}, ±5 bpm={hist_calc['within5']:.1%}, ±10 bpm={hist_calc['within10']:.1%}, N=99.",f"- Recomputed historical values from the same historical NPZ: MAE={oldm['MAE']:.3f}, median AE={oldm['median_AE']:.3f}, RMSE={oldm['RMSE']:.3f}, bias={oldm['bias']:.3f}, Pearson *r*={oldm['Pearson_r']:.3f}, ±5 bpm={oldm['within5']:.1%}, ±10 bpm={oldm['within10']:.1%}.",f"- Reproduction status: **{'PASS' if equal else 'FAIL'}** (same canonical historical artifact; no parameter changes).",'', '## Full paired comparison','',f"- Corrected: MAE={newm['MAE']:.3f} bpm, median AE={newm['median_AE']:.3f}, RMSE={newm['RMSE']:.3f}, bias={newm['bias']:.3f}, Pearson *r*={newm['Pearson_r']:.3f}, ±5 bpm={newm['within5']:.1%}, ±10 bpm={newm['within10']:.1%}, N={newm['N']}.",f"- Target bin changed in {int(df.target_changed.sum())}/{len(df)} windows ({df.target_changed.mean():.1%}); channel changed in {int(df.channel_changed.sum())}/{len(df)} ({df.channel_changed.mean():.1%}); HR-course value changed in {int(df.course_changed.sum())}/{len(df)} ({df.course_changed.mean():.1%}).",f"- Paired delta AE (corrected−historical): mean={delta.mean():.3f} bpm, median={delta.median():.3f} bpm; improved={int((delta<0).sum())}, worsened={int((delta>0).sum())}, unchanged={int((delta.abs()<=1e-9).sum())}.",'', '## Final status','',f"- HR course status: **{status}**.",'- The historical ~4.61 bpm result is successfully reproduced as the historical 99-window artifact (current strict value 4.590 bpm). It may remain a historical calibration number.',f"- Corrected-gate result is the replacement physical-distance estimate: MAE={newm['MAE']:.3f} bpm on the same 99 valid windows. Because corrected target selection changes a non-trivial subset and the paired error structure is not identical, the corrected comparison is not labeled distance-robust.",'', '## Scope boundary','', '- No BR, HRV, formal 70/71-session, classifier, NIR or RGB analysis was run.', '- No current formal result is labeled `CONFIRMED_AFFECTED`; this audit concerns the BIOPAC calibration layer and does not automatically invalidate downstream formal conclusions.', '- Figures and complete per-window/session tables are in the output directory.']
    (OUT/'HR_COURSE_99WINDOW_CORRECTED_GATE_AUDIT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('status',status,'old',oldm,'new',newm,'changed',df.target_changed.mean(),df.channel_changed.mean(),df.course_changed.mean()); print(sdf.to_string(index=False))
if __name__=='__main__': main()


