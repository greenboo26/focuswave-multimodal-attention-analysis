"""C3A: reuse formal NIR frame-level outputs for dynamic probe features.

No NIR video is opened. Existing fullclass ROI/QC CSVs are read in selected
columns, joined to frozen Beijing canonical probes by absolute Unix ms, and
evaluated with a predeclared L2 logistic incremental model.
"""
from __future__ import annotations
import hashlib, json, shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(r"D:\Project\厚粲杯"); DERIVED=ROOT/"11_数据"/"derived"
FORMAL=ROOT/"11_数据"/"01_Attention-Analysis_nvidia-cuda_formal_NIR"
OUT=DERIVED/"c3_multimodal_readiness_v1"; REPO=Path(__file__).resolve().parents[1]
SAFE=REPO/"docs"/"results"/"c3_multimodal_readiness_v1"
SEED=20260826; BOOTSTRAP=2000; MIN_PARTICIPANTS=10
C=["block_num","block_probe_fraction","onset_rel_s"]
B=["b_trial_count","b_rt_mean","b_rt_median","b_rt_sd","b_rt_mad","b_rt_cv","b_rt_slope","b_accuracy","b_error_count","b_error_rate","b_omission_count","b_omission_rate"]
N=["nir_ratio_median","nir_ratio_iqr","nir_ratio_slope_per_s","nir_aperture_median","nir_confidence_median","nir_ratio_first_last_delta"]
READ=["unix_ms","eye","status","roi_clipped","fullclass_normalization_valid","fullclass_pupil_fit_valid","fullclass_pupil_to_iris_diameter_ratio","fullclass_ocular_aperture_ratio_median","pupil_confidence"]

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''): h.update(x)
 return h.hexdigest()
def weight(g):
 c=Counter(g.astype(str)); return np.array([1/c[str(x)] for x in g],float)
def clf(seed): return make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),LogisticRegression(C=1.,class_weight='balanced',max_iter=3000,random_state=seed))
def auc(y,s): return float(roc_auc_score(y,s)) if len(np.unique(y))==2 else np.nan
def oof(d,features,name):
 out=[]
 for fold,(tr,te) in enumerate(LeaveOneGroupOut().split(d,d.target,d.repeat_participant_id)):
  train,test=d.iloc[tr],d.iloc[te]
  if train.target.nunique()<2: raise RuntimeError(f'one-class training fold {fold}')
  m=clf(SEED+fold); m.fit(train[features],train.target,logisticregression__sample_weight=weight(train.repeat_participant_id))
  p=test[['subject','probe_seq','repeat_participant_id','target']].copy(); p['model']=name;p['fold']=fold;p['score']=m.predict_proba(test[features])[:,1];out.append(p)
 return pd.concat(out,ignore_index=True)
def boot(new,base):
 z=new.merge(base[['subject','probe_seq','score']],on=['subject','probe_seq'],suffixes=('_new','_base'),validate='one_to_one')
 gs=z.repeat_participant_id.unique(); pos={g:np.flatnonzero(z.repeat_participant_id.to_numpy()==g) for g in gs}; rng=np.random.default_rng(SEED); vals=[]
 for _ in range(BOOTSTRAP):
  ix=np.concatenate([pos[g] for g in rng.choice(gs,len(gs),replace=True)]); y=z.target.to_numpy()[ix]
  if len(np.unique(y))==2: vals.append(auc(y,z.score_new.to_numpy()[ix])-auc(y,z.score_base.to_numpy()[ix]))
 return auc(z.target,z.score_new)-auc(z.target,z.score_base),*np.quantile(vals,[.025,.975]).tolist(),len(vals)
def dynamic_for_subject(subject,events):
 runs=sorted(FORMAL.glob(f'sub-{subject}_formal_v3.1.3_yolo8_b16_fp32'))
 if len(runs)!=1: return [],{'subject':subject,'asset_status':'missing_or_ambiguous_formal_run','n_probes':len(events)}
 files=list(runs[0].glob('*ritnet_fullclass_v1-2-fast-qc.csv'))
 if len(files)!=1: return [],{'subject':subject,'asset_status':'no_fullclass_dynamic_csv','n_probes':len(events)}
 lo,hi=int(events.probe_onset_ms.min()-60000),int(events.probe_onset_ms.max())
 chunks=[]
 for q in pd.read_csv(files[0],usecols=READ,chunksize=200000,low_memory=False):
  q=q[(q.unix_ms>=lo)&(q.unix_ms<hi)]
  if not q.empty: chunks.append(q)
 if not chunks: return [],{'subject':subject,'asset_status':'fullclass_csv_no_probe_time_overlap','n_probes':len(events)}
 q=pd.concat(chunks,ignore_index=True)
 for c in ['roi_clipped','fullclass_normalization_valid','fullclass_pupil_fit_valid']:
  q[c]=q[c].astype(str).str.lower().eq('true')
 q['valid']=(~q.roi_clipped)&q.fullclass_normalization_valid&q.fullclass_pupil_fit_valid&q.fullclass_pupil_to_iris_diameter_ratio.notna()
 v=q[q.valid].groupby('unix_ms',as_index=False).agg(ratio=('fullclass_pupil_to_iris_diameter_ratio','median'),aperture=('fullclass_ocular_aperture_ratio_median','median'),confidence=('pupil_confidence','median'))
 total=q.groupby('unix_ms').size().index.to_numpy(); rows=[]
 for e in events.itertuples():
  start=e.probe_onset_ms-e.window_s*1000; alln=((total>=start)&(total<e.probe_onset_ms)).sum(); x=v[(v.unix_ms>=start)&(v.unix_ms<e.probe_onset_ms)].copy(); rate=len(x)/alln if alln else 0.
  r={'subject':subject,'probe_onset_ms':e.probe_onset_ms,'window_s':e.window_s,'nir_total_frame_n':int(alln),'nir_valid_frame_n':int(len(x)),'nir_valid_frame_rate':rate,'nir_asset':'formal_fullclass_roi_dynamic'}
  if len(x)>=2:
   ratio=x.ratio.to_numpy(float); t=(x.unix_ms.to_numpy(float)-e.probe_onset_ms)/1000
   r.update({'nir_ratio_median':float(np.median(ratio)),'nir_ratio_iqr':float(np.subtract(*np.quantile(ratio,[.75,.25]))),'nir_ratio_slope_per_s':float(np.polyfit(t,ratio,1)[0]),'nir_aperture_median':float(np.nanmedian(x.aperture)),'nir_confidence_median':float(np.nanmedian(x.confidence)),'nir_ratio_first_last_delta':float(np.nanmean(x.loc[t>=-min(5,e.window_s/2),'ratio'])-np.nanmean(x.loc[t<-max(e.window_s-5,e.window_s/2),'ratio']))})
  rows.append(r)
 return rows,{'subject':subject,'asset_status':'formal_fullclass_dynamic_read','n_probes':len(events),'fullclass_file_mb':round(files[0].stat().st_size/1048576,2)}
def main():
 if OUT.exists() or SAFE.exists(): raise RuntimeError('output target already exists; refuse overwrite')
 OUT.mkdir(parents=True); SAFE.mkdir(parents=True)
 canonical=DERIVED/'c2b_v2_canonical_baselines_20260826'; ids=pd.read_csv(DERIVED/'c3_identity_coverage_crosswalk_v1'/'identity_crosswalk.csv',dtype={'single_experiment_id':str})
 ids.single_experiment_id=ids.single_experiment_id.str.zfill(3); ids=ids[['single_experiment_id','repeat_participant_id','identity_status']].drop_duplicates(); all_base=[]
 for w in (10,30,60):
  x=pd.read_csv(canonical/f'window_{w}s'/'canonical_feature_matrix_local.csv',dtype={'subject':str});x.subject=x.subject.str.zfill(3);x['window_s']=w;x['target']=(x.label!=1).astype(int);all_base.append(x)
 base=pd.concat(all_base,ignore_index=True).merge(ids,left_on='subject',right_on='single_experiment_id',how='left',validate='many_to_one')
 base=base[(base.identity_status.eq('resolved_metadata_crosswalk'))&base.repeat_participant_id.notna()&base.subject.ne('070')].copy(); assets=[];dynamic=[]
 for subject,e in base.groupby('subject',sort=True):
  r,a=dynamic_for_subject(subject,e[['probe_onset_ms','window_s']].drop_duplicates());dynamic.extend(r);assets.append(a)
 dyn=pd.DataFrame(dynamic)
 if dyn.empty: raise RuntimeError('no existing formal dynamic NIR probe rows')
 x=base.merge(dyn,on=['subject','probe_onset_ms','window_s'],how='left',validate='one_to_one');x['nir_primary_ok']=x.nir_valid_frame_rate.ge(.80)&x[N].notna().all(axis=1);cov=[];result=[];preds=[]
 for w in (10,30,60):
  d=x[x.window_s.eq(w)].copy(); nd=d[d.nir_primary_ok].dropna(subset=C+B+N).copy()
  cov.append({'window_s':w,'canonical_identity_resolved_probe':len(d),'formal_fullclass_exact_onset_probe':int(d.nir_asset.eq('formal_fullclass_roi_dynamic').sum()),'primary_qc_probe':len(nd),'participant_n':nd.repeat_participant_id.nunique(),'median_valid_frame_rate':float(nd.nir_valid_frame_rate.median()) if len(nd) else np.nan})
  if nd.repeat_participant_id.nunique()<MIN_PARTICIPANTS or nd.target.nunique()<2:
   for name in ['C+B','C+B+NIR_dynamic']: result.append({'window_s':w,'model':name,'status':'not_modelled_insufficient_common_participants_or_class','n_probe':len(nd),'n_participant':nd.repeat_participant_id.nunique()})
   continue
  for name,f in [('C+B',C+B),('C+B+NIR_dynamic',C+B+N)]:
   p=oof(nd,f,name);p['window_s']=w;preds.append(p);result.append({'window_s':w,'model':name,'status':'eligible','n_probe':len(p),'n_participant':p.repeat_participant_id.nunique(),'positive_n':int(p.target.sum()),'oof_auc':auc(p.target,p.score),'balanced_accuracy_0_5':float(balanced_accuracy_score(p.target,p.score>=.5))})
 pred=pd.concat(preds,ignore_index=True);inc=[]
 for w in (10,30,60):
  a=pred[(pred.window_s==w)&(pred.model=='C+B+NIR_dynamic')];b=pred[(pred.window_s==w)&(pred.model=='C+B')]
  if not a.empty:
   point,lo,hi,n=boot(a,b);inc.append({'window_s':w,'comparison':'C+B+NIR_dynamic minus C+B','n_probe':len(a),'n_participant':a.repeat_participant_id.nunique(),'delta_auc':point,'ci95_low':lo,'ci95_high':hi,'valid_bootstraps':n})
 coverage=pd.DataFrame(cov);results=pd.DataFrame(result);increments=pd.DataFrame(inc);asset=pd.DataFrame(assets)
 x.to_csv(OUT/'c3a_row_level_dynamic_nir_matrix_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig');pred.to_csv(OUT/'c3a_oof_predictions_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig');asset.to_csv(OUT/'c3a_formal_asset_inventory_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig');coverage.to_csv(OUT/'c3a_coverage_qc_deidentified.csv',index=False,encoding='utf-8-sig');results.to_csv(OUT/'c3a_aggregate_model_results.csv',index=False,encoding='utf-8-sig');increments.to_csv(OUT/'c3a_paired_participant_bootstrap.csv',index=False,encoding='utf-8-sig')
 schema=pd.DataFrame([*({'feature_set':'C+B','feature':z,'family':'context' if z in C else 'behavior'} for z in C+B),*({'feature_set':'NIR_dynamic','feature':z,'family':'formal_NIR_fullclass_ROI'} for z in N)]);schema.to_csv(OUT/'c3a_feature_schema.csv',index=False,encoding='utf-8-sig')
 manifest={'run_id':'C3A_FORMAL_NIR_DYNAMIC_INCREMENT_20260826','handoff_commit_declared_by_user':'6e2eda0af827c7a6bff8056ec7d1e79bef955336','handoff_commit_local_availability':'not present in local object database at run time','formal_root':str(FORMAL),'no_raw_video_read':True,'windows_s':[10,30,60],'target':'label 1 versus labels 2/3/4','model':'fixed L2 logistic C=1.0; train-fold median imputation and scaling; outer repeat-participant-disjoint LOGO; equal participant training weights','qc':'predeclared fullclass valid un-clipped ROI plus >=0.80 valid-frame rate','bootstrap':'paired repeat-participant bootstrap, 2000 replicates','inputs':{str(p):sha(p) for p in [DERIVED/'c3_nir_qc_integration_v1'/'nir_probe_aligned.csv',DERIVED/'c3_identity_coverage_crosswalk_v1'/'identity_crosswalk.csv',DERIVED/'beijing_sensor_increment_v1'/'common_probe_incremental_models.csv',DERIVED/'nir_directionality_audit_v1'/'report.md',canonical/'c2b_v2_base_probe_manifest.csv']},'created_at_utc':datetime.now(timezone.utc).isoformat()};(OUT/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 for p in [OUT/'c3a_coverage_qc_deidentified.csv',OUT/'c3a_aggregate_model_results.csv',OUT/'c3a_paired_participant_bootstrap.csv',OUT/'c3a_feature_schema.csv']: shutil.copy2(p,SAFE/p.name)
 import matplotlib.pyplot as plt
 ax=coverage.set_index('window_s')[['canonical_identity_resolved_probe','formal_fullclass_exact_onset_probe','primary_qc_probe']].plot(kind='bar',figsize=(7,3.8),color=['#0072B2','#E69F00','#009E73'],edgecolor='black',linewidth=.35);ax.set_ylabel('Probe count');ax.set_xlabel('Pre-probe window (s)');ax.set_title('C3A formal NIR dynamic-feature coverage');ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False);ax.figure.tight_layout();ax.figure.savefig(OUT/'C3A_Fig1_coverage_v1.png',dpi=300);ax.figure.savefig(SAFE/'C3A_Fig1_coverage_v1.png',dpi=300);plt.close(ax.figure)
 report=['# C3A formal NIR dynamic increment','', '## Formal-asset inventory','',f"The formal NIR directory was read without opening raw video. Fullclass ROI/QC dynamic CSVs were available for {int((asset.asset_status=='formal_fullclass_dynamic_read').sum())} identity-eligible formal sessions; each supplies per-frame Unix ms, eye/ROI clipping state, pupil fit and normalization validity, pupil-to-iris ratio, ocular aperture ratio, and pupil confidence. The requested GitHub handoff commit was not in this local clone object database, so its user-provided hash is recorded but not represented as locally verified.",'','## Coverage and fixed QC','',coverage.to_markdown(index=False),'', 'Primary QC was frozen before modelling: at least 80% valid (un-clipped, normalized, fitted) frames over the exact probe-before window. 10/30/60 s are fixed windows; 30 s is the primary window, while 10/60 s are sensitivity analyses.','', '## Incremental models','',results.to_markdown(index=False),'','## Paired repeat-participant bootstrap','',increments.to_markdown(index=False) if not increments.empty else 'No eligible paired comparison.','', '## Scope boundary','', 'No raw NIR video was read or rerun. HbO/HbR time series are not present in the formal asset schema, so no haemodynamic claim is made. Row-level values, identities, session keys and OOF predictions remain only in the local derived output. RGB/C3B is not started.']
 (OUT/'C3A_FORMAL_NIR_DYNAMIC_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8');shutil.copy2(OUT/'C3A_FORMAL_NIR_DYNAMIC_REPORT.md',SAFE/'C3A_FORMAL_NIR_DYNAMIC_REPORT.md');print(json.dumps({'output':str(OUT),'eligible_models':int((results.status=='eligible').sum()),'dynamic_rows':len(dyn)},ensure_ascii=False))
if __name__=='__main__': main()
