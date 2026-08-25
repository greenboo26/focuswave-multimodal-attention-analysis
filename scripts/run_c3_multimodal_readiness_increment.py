"""C3A v2: read all existing formal NIR results; never open/rerun video."""
from __future__ import annotations
import hashlib,json,shutil
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score,roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(r"D:\Project\厚粲杯"); DER=ROOT/"11_数据"/"derived"; FORMAL=ROOT/"11_数据"/"01_Attention-Analysis_nvidia-cuda_formal_NIR"
OUT=DER/"c3a_formal_nir_full_available_results_v2"; REPO=Path(__file__).resolve().parents[1]; SAFE=REPO/"docs"/"results"/"c3a_formal_nir_full_available_results_v2"
CAN=DER/"c2b_v2_canonical_baselines_20260826"; MASTER=DER/"analysis_tables_v2"/"subject_session_master_v2.csv"; SEED=20260826; BOOT=2000; MINP=10
C=["block_num","block_probe_fraction","onset_rel_s"]; B=["b_trial_count","b_rt_mean","b_rt_median","b_rt_sd","b_rt_mad","b_rt_cv","b_rt_slope","b_accuracy","b_error_count","b_error_rate","b_omission_count","b_omission_rate"]
N=["nir_ratio_median","nir_ratio_iqr","nir_ratio_slope_per_s","nir_aperture_median","nir_confidence_median","nir_ratio_first_last_delta"]
READ=["unix_ms","eye","status","roi_clipped","fullclass_normalization_valid","fullclass_pupil_fit_valid","fullclass_pupil_to_iris_diameter_ratio","fullclass_ocular_aperture_ratio_median","pupil_confidence"]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def yes(s):return s.astype(str).str.strip().str.lower().isin(['true','1','yes'])
def getjson(p):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except (OSError,UnicodeDecodeError,json.JSONDecodeError):return {}
def inv():
 rows=[]
 for d in sorted(FORMAL.glob('sub-*_formal*')):
  sid=d.name.split('_')[0].replace('sub-','').zfill(3); fs={x.name for x in d.iterdir() if x.is_file()}; full=[x for x in d.glob('*ritnet_fullclass_v1-2-fast-qc.csv') if not x.name.endswith('_qc_index.csv')]; comp=getjson(d/'completion.json'); fcomp=getjson(next(iter(d.glob('*fast-qc_completion.json')),d/'__missing__.json'))
  rows.append({'formal_subject':sid,'formal_run_dir':d.name,'run_variant':'yolo8' if 'yolo8' in d.name else 'legacy_yolo','has_completion_json':'completion.json' in fs,'has_eyes_csv':'eyes.csv' in fs,'has_frames_csv':'frames.csv' in fs,'has_summary_json':'summary.json' in fs,'has_phase_windows_json':'phase_windows.json' in fs,'has_fullclass_dynamic_csv':len(full)==1,'has_fullclass_qc_index':any(x.endswith('_qc_index.csv') for x in fs),'has_fullclass_completion':bool(fcomp),'formal_completion_status':comp.get('status',comp.get('run_status','not_recorded')),'fullclass_completion_status':fcomp.get('status',fcomp.get('run_status','not_recorded')),'fullclass_csv_mb':round(full[0].stat().st_size/1048576,2) if len(full)==1 else np.nan,'fullclass_csv_name':full[0].name if len(full)==1 else pd.NA})
 return pd.DataFrame(rows)
def base():
 a=[]
 for w in (10,30,60):
  x=pd.read_csv(CAN/f'window_{w}s'/'canonical_feature_matrix_local.csv',dtype={'subject':str});x.subject=x.subject.str.zfill(3);x['window_s']=w;x['target']=(pd.to_numeric(x.label,errors='coerce')!=1).astype(int);a.append(x)
 return pd.concat(a,ignore_index=True)
def linkage(i,b):
 m=pd.read_csv(MASTER,dtype={'single_experiment_id':str,'repeat_participant_id':str});m.single_experiment_id=m.single_experiment_id.str.zfill(3)
 if m.single_experiment_id.duplicated().any():raise RuntimeError('non-unique master session key')
 m['identity_link_status']=np.where(m.repeat_participant_id.notna()&m.record_status.eq('retained_as_session_record')&m.participant_slot_status.eq('real_person'),'linked_retained_real_person','not_eligible_identity_or_session_record')
 cols=['single_experiment_id','repeat_participant_id','site','record_status','participant_slot_status','questionnaire_match_status','questionnaire_validity','identity_link_status'];a=i.merge(m[cols],left_on='formal_subject',right_on='single_experiment_id',how='left',validate='many_to_one')
 p=b.groupby('subject',as_index=False).agg(canonical_probe_rows=('probe_seq','size'),canonical_windows=('window_s','nunique'));a=a.merge(p,left_on='formal_subject',right_on='subject',how='left',validate='many_to_one');a['canonical_session_status']=np.where(a.canonical_windows.eq(3),'canonical_10_30_60s_available','no_complete_canonical_probe_timeline')
 a['formal_session_link_status']=np.select([a.identity_link_status.eq('linked_retained_real_person')&a.canonical_session_status.eq('canonical_10_30_60s_available'),a.single_experiment_id.isna()],['linked_to_formal_experiment_session','no_master_session_key'],default='identity_not_eligible');return a
def dyn(sid,events,i):
 r=i[(i.formal_subject==sid)&i.has_fullclass_dynamic_csv]
 if len(r)!=1:return [],{'formal_subject':sid,'dynamic_asset_status':'no_unique_fullclass_dynamic_asset','requested_probe_rows':len(events)}
 r=r.iloc[0];p=FORMAL/r.formal_run_dir/r.fullclass_csv_name;lo,hi=int(events.probe_onset_ms.min()-60000),int(events.probe_onset_ms.max());cs=[]
 for q in pd.read_csv(p,usecols=READ,chunksize=200000,low_memory=False):
  q=q[(q.unix_ms>=lo)&(q.unix_ms<hi)]
  if not q.empty:cs.append(q)
 if not cs:return [],{'formal_subject':sid,'dynamic_asset_status':'fullclass_no_canonical_time_overlap','requested_probe_rows':len(events),'fullclass_file_mb':r.fullclass_csv_mb}
 q=pd.concat(cs,ignore_index=True);q['valid']=(~yes(q.roi_clipped))&yes(q.fullclass_normalization_valid)&yes(q.fullclass_pupil_fit_valid)&q.fullclass_pupil_to_iris_diameter_ratio.notna();v=q[q.valid].groupby('unix_ms',as_index=False).agg(ratio=('fullclass_pupil_to_iris_diameter_ratio','median'),aperture=('fullclass_ocular_aperture_ratio_median','median'),confidence=('pupil_confidence','median'));times=q.groupby('unix_ms').size().index.to_numpy();rows=[]
 for e in events.itertuples():
  st=e.probe_onset_ms-e.window_s*1000;n=int(((times>=st)&(times<e.probe_onset_ms)).sum());z=v[(v.unix_ms>=st)&(v.unix_ms<e.probe_onset_ms)].copy();rate=len(z)/n if n else 0.;ztime=(z.unix_ms.to_numpy(float)-e.probe_onset_ms)/1000
  x={'subject':sid,'probe_onset_ms':e.probe_onset_ms,'window_s':e.window_s,'nir_total_frame_n':n,'nir_valid_frame_n':len(z),'nir_valid_frame_rate':rate,'nir_dynamic_asset':'formal_fullclass_roi_dynamic'}
  if len(z)>=2:
   a=z.ratio.to_numpy(float);early=z.loc[ztime<-max(e.window_s-5,e.window_s/2),'ratio'];late=z.loc[ztime>=-min(5,e.window_s/2),'ratio'];x.update({'nir_ratio_median':float(np.nanmedian(a)),'nir_ratio_iqr':float(np.subtract(*np.nanquantile(a,[.75,.25]))),'nir_ratio_slope_per_s':float(np.polyfit(ztime,a,1)[0]),'nir_aperture_median':float(np.nanmedian(z.aperture)),'nir_confidence_median':float(np.nanmedian(z.confidence)),'nir_ratio_first_last_delta':float(np.nanmean(late)-np.nanmean(early))})
  rows.append(x)
 return rows,{'formal_subject':sid,'dynamic_asset_status':'fullclass_dynamic_read','requested_probe_rows':len(events),'fullclass_file_mb':r.fullclass_csv_mb}
def wt(g):
 c=Counter(g.astype(str));return np.array([1/c[str(x)] for x in g],float)
def auc(y,s):return float(roc_auc_score(y,s)) if len(np.unique(y))==2 else np.nan
def oof(d,fs,name):
 z=[]
 for f,(tr,te) in enumerate(LeaveOneGroupOut().split(d,d.target,d.repeat_participant_id)):
  m=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),LogisticRegression(C=1.,class_weight='balanced',max_iter=3000,random_state=SEED+f));train,test=d.iloc[tr],d.iloc[te];m.fit(train[fs],train.target,logisticregression__sample_weight=wt(train.repeat_participant_id));p=test[['subject','probe_seq','repeat_participant_id','target']].copy();p['model']=name;p['fold']=f;p['score']=m.predict_proba(test[fs])[:,1];z.append(p)
 return pd.concat(z,ignore_index=True)
def boot(n,b):
 z=n.merge(b[['subject','probe_seq','score']],on=['subject','probe_seq'],suffixes=('_new','_base'),validate='one_to_one');gs=z.repeat_participant_id.unique();pos={g:np.flatnonzero(z.repeat_participant_id.to_numpy()==g) for g in gs};rng=np.random.default_rng(SEED);v=[]
 for _ in range(BOOT):
  ix=np.concatenate([pos[g] for g in rng.choice(gs,len(gs),replace=True)]);y=z.target.to_numpy()[ix]
  if len(np.unique(y))==2:v.append(auc(y,z.score_new.to_numpy()[ix])-auc(y,z.score_base.to_numpy()[ix]))
 return auc(z.target,z.score_new)-auc(z.target,z.score_base),*np.quantile(v,[.025,.975]),len(v)
def main():
 if OUT.exists() or SAFE.exists():raise RuntimeError(f'refuse overwrite: {OUT}')
 OUT.mkdir(parents=True);SAFE.mkdir(parents=True);i,b=inv(),base();l=linkage(i,b);linked=l[l.formal_session_link_status.eq('linked_to_formal_experiment_session')];mb=b[b.subject.isin(set(linked.formal_subject))].merge(linked[['formal_subject','repeat_participant_id']].drop_duplicates(),left_on='subject',right_on='formal_subject',how='inner',validate='many_to_one');fr=[];aa=[]
 for sid,e in mb.groupby('subject',sort=True):
  x,a=dyn(sid,e[['probe_onset_ms','window_s']].drop_duplicates(),i);fr+=x;aa.append(a)
 features,asset=pd.DataFrame(fr),pd.DataFrame(aa);x=mb.merge(features,on=['subject','probe_onset_ms','window_s'],how='left',validate='one_to_one');x['nir_primary_ok']=x.nir_valid_frame_rate.ge(.80)&x[N].notna().all(axis=1);cov=[];res=[];preds=[]
 for w in (10,30,60):
  d=x[x.window_s.eq(w)].copy();md=d[d.nir_primary_ok].dropna(subset=C+B+N).copy();cov.append({'window_s':w,'linked_canonical_probe':len(d),'dynamic_exact_onset_probe':int(d.nir_dynamic_asset.eq('formal_fullclass_roi_dynamic').sum()),'primary_qc_probe':len(md),'repeat_participant_n':md.repeat_participant_id.nunique(),'median_valid_frame_rate':float(md.nir_valid_frame_rate.median()) if len(md) else np.nan})
  if md.repeat_participant_id.nunique()<MINP or md.target.nunique()<2:
   for name in ['C+B','C+B+NIR_dynamic']:res.append({'window_s':w,'model':name,'status':'not_modelled_insufficient_common_participants_or_class','n_probe':len(md),'n_participant':md.repeat_participant_id.nunique()})
  else:
   for name,fs in [('C+B',C+B),('C+B+NIR_dynamic',C+B+N)]:
    p=oof(md,fs,name);p['window_s']=w;preds.append(p);res.append({'window_s':w,'model':name,'status':'eligible','n_probe':len(p),'n_participant':p.repeat_participant_id.nunique(),'positive_n':int(p.target.sum()),'oof_auc':auc(p.target,p.score),'balanced_accuracy_0_5':float(balanced_accuracy_score(p.target,p.score>=.5))})
 cov,res=pd.DataFrame(cov),pd.DataFrame(res);pred=pd.concat(preds,ignore_index=True) if preds else pd.DataFrame();inc=[]
 for w in (10,30,60):
  n=pred[(pred.window_s==w)&(pred.model=='C+B+NIR_dynamic')];old=pred[(pred.window_s==w)&(pred.model=='C+B')]
  if not n.empty:
   point,lo,hi,k=boot(n,old);inc.append({'window_s':w,'comparison':'C+B+NIR_dynamic minus C+B','n_probe':len(n),'n_participant':n.repeat_participant_id.nunique(),'delta_auc':point,'ci95_low':lo,'ci95_high':hi,'valid_bootstraps':k})
 inc=pd.DataFrame(inc)
 for d,name in [(i,'session_inventory_LOCAL_ONLY.csv'),(l,'identity_linkage_audit_LOCAL_ONLY.csv'),(asset,'dynamic_asset_audit_LOCAL_ONLY.csv'),(x,'probe_features_LOCAL_ONLY.csv'),(pred,'oof_predictions_LOCAL_ONLY.csv'),(cov,'coverage_qc_deidentified.csv'),(res,'aggregate_model_results.csv'),(inc,'paired_participant_bootstrap.csv')]:d.to_csv(OUT/name,index=False,encoding='utf-8-sig')
 schema=pd.DataFrame([*({'feature_set':'C+B','feature':f,'family':'context' if f in C else 'behavior'} for f in C+B),*({'feature_set':'NIR_dynamic','feature':f,'family':'formal_NIR_fullclass_ROI'} for f in N)]);schema.to_csv(OUT/'feature_schema.csv',index=False,encoding='utf-8-sig')
 summary={'formal_run_directories':len(i),'formal_unique_subjects':i.formal_subject.nunique(),'formal_yolo8_completed_session_results':int((i.has_completion_json&i.has_eyes_csv&i.has_frames_csv&i.has_summary_json&i.run_variant.eq('yolo8')).sum()),'formal_fullclass_dynamic_assets':int(i.has_fullclass_dynamic_csv.sum()),'linked_formal_experiment_sessions':int(linked.formal_subject.nunique()),'beijing_current_accessible_sessions':int(l.loc[l.canonical_session_status.eq('canonical_10_30_60s_available'),'formal_subject'].nunique()),'identity_unlinked_or_not_real_person':int(l.loc[~l.formal_session_link_status.eq('linked_to_formal_experiment_session'),'formal_subject'].nunique()),'missing_timestamp_or_probe_alignment_sessions':int((asset.dynamic_asset_status!='fullclass_dynamic_read').sum()),'qc30_probe':int(cov.loc[cov.window_s.eq(30),'primary_qc_probe'].iloc[0]),'final_repeat_participant_n_30s':int(cov.loc[cov.window_s.eq(30),'repeat_participant_n'].iloc[0]),'final_probe_n_30s':int(cov.loc[cov.window_s.eq(30),'primary_qc_probe'].iloc[0])}
 manifest={'run_id':'C3A_FORMAL_NIR_FULL_AVAILABLE_RESULTS_V2','created_at_utc':datetime.now(timezone.utc).isoformat(),'formal_root':str(FORMAL),'entrypoint':'all formal result directories; old crosswalk not coverage authority','no_raw_video_read_or_rerun':True,'windows_s':[10,30,60],'primary_window_s':30,'label':'label 1 versus labels 2/3/4','model':'fixed L2 logistic C=1.0; train-fold median imputation/scaling; repeat-participant-disjoint LOGO; equal participant training weights','qc':'existing fullclass: un-clipped ROI + normalization-valid + pupil-fit-valid + >=0.80 valid-frame rate','bootstrap':'paired repeat-participant bootstrap, 2000 replicates','inputs_sha256':{str(p):sha(p) for p in [MASTER,CAN/'c2b_v2_base_probe_manifest.csv']},'summary':summary};(OUT/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 for p in [OUT/'coverage_qc_deidentified.csv',OUT/'aggregate_model_results.csv',OUT/'paired_participant_bootstrap.csv',OUT/'feature_schema.csv']:shutil.copy2(p,SAFE/p.name)
 fig,ax=plt.subplots(figsize=(7.5,3.8));cov.set_index('window_s')[['linked_canonical_probe','dynamic_exact_onset_probe','primary_qc_probe']].plot(kind='bar',ax=ax,color=['#4169a1','#d8903d','#4e9c7a'],edgecolor='black',linewidth=.3);ax.set(xlabel='Pre-probe window (s)',ylabel='Probe count',title='C3A v2: formal NIR availability and frozen QC');ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'C3A_V2_Fig1_coverage.png',dpi=300);fig.savefig(SAFE/'C3A_V2_Fig1_coverage.png',dpi=300);plt.close(fig)
 fig,ax=plt.subplots(figsize=(6.6,3.8));
 if not inc.empty:ax.errorbar(inc.window_s,inc.delta_auc,yerr=[inc.delta_auc-inc.ci95_low,inc.ci95_high-inc.delta_auc],fmt='o',color='#4169a1',capsize=4)
 ax.axhline(0,color='black',linewidth=.8);ax.set(xlabel='Pre-probe window (s)',ylabel='Paired ΔAUC',title='C3A v2: NIR dynamic increment (95% bootstrap CI)');ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'C3A_V2_Fig2_delta_auc.png',dpi=300);fig.savefig(SAFE/'C3A_V2_Fig2_delta_auc.png',dpi=300);plt.close(fig)
 report=['# C3A_FORMAL_NIR_FULL_AVAILABLE_RESULTS_V2','','## Outcome','',f"The formal directory is the authoritative entry point. It contains {summary['formal_run_directories']} run directories for {summary['formal_unique_subjects']} unique formal subjects; {summary['formal_yolo8_completed_session_results']} have completed yolo8 session-level eyes/frames/summary results, while only {summary['formal_fullclass_dynamic_assets']} currently include the pre-existing fullclass per-frame ROI/QC dynamic asset required by the frozen C3A QC rule.",'','## Coverage and linkage','',f"{summary['linked_formal_experiment_sessions']} sessions deterministically link to a retained real-person formal experiment session and canonical timeline. {summary['beijing_current_accessible_sessions']} formal directories have a complete current 10/30/60 s canonical probe timeline. {summary['identity_unlinked_or_not_real_person']} fail the real-person identity/session gate. Among linked sessions, {summary['missing_timestamp_or_probe_alignment_sessions']} lack an existing fullclass dynamic asset or cannot be aligned; this is an asset-availability limit, not a video review result.",'',cov.to_markdown(index=False),'','## Fixed model results','',res.to_markdown(index=False),'','## Paired participant bootstrap','',inc.to_markdown(index=False) if not inc.empty else 'No eligible paired comparison.','','## Why v1 was a subset','','The v1 C3A script entered through `c3_identity_coverage_crosswalk_v1`, a 17-session legacy crosswalk, then required a pre-existing fullclass dynamic CSV and therefore analysed 15 sessions / 12 repeat participants after its additional eligibility gates. That crosswalk is retained as OLD_SUBSET/preliminary evidence and is not used as the v2 coverage authority. V2 inventories all formal result directories first, uses `subject_session_master_v2.csv` plus the current canonical probe timeline for deterministic linkage, and separately reports session-level availability versus fullclass-dynamic model eligibility.','','## Limits','','No raw NIR video was opened or rerun. `eyes.csv/frames.csv/summary.json` establish completed session-level processing but cannot satisfy the frozen fullclass normalization/pupil-fit QC rule by themselves; those sessions are counted in availability but excluded from the C3A dynamic model until an already-authorized upstream fullclass result exists. All identity keys, run directories, probe timestamps, row-level features and OOF predictions remain local only. NIR is a visual physiological reference signal, not attention ground truth.']
 (OUT/'C3A_FORMAL_NIR_FULL_AVAILABLE_RESULTS_V2_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8');shutil.copy2(OUT/'C3A_FORMAL_NIR_FULL_AVAILABLE_RESULTS_V2_REPORT.md',SAFE/'C3A_FORMAL_NIR_FULL_AVAILABLE_RESULTS_V2_REPORT.md');print(json.dumps({'output':str(OUT),**summary,'eligible_model_rows':int(res.status.eq('eligible').sum())},ensure_ascii=False))
if __name__=='__main__':main()
