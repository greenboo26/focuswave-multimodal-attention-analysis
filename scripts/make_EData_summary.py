# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(r'D:\Project\厚粲杯\08_算法\output\E_Data_20260821')
d=pd.read_csv(OUT/'E_Data_mid30s_metrics.csv')
plt.rcParams['axes.unicode_minus']=False
fig,ax=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
spec=[('hr_bpm','HR (bpm)',(40,100)),('br_bpm','BR (breaths/min)',(0,35)),('sdnn_ms','SDNN (ms)',(0,None)),('rmssd_ms','RMSSD (ms)',(0,None))]
for a,(k,lab,ylim) in zip(ax.flat,spec):
    a.hist(d[k].dropna(),bins=14,color='#5276a8',alpha=.85,edgecolor='white')
    a.set_xlabel(lab); a.set_ylabel('被试数'); a.set_title(lab)
    if ylim[0] is not None: a.set_xlim(*ylim)
fig.savefig(OUT/'E_Data_metric_distributions.png',dpi=180); plt.close(fig)

fig,ax=plt.subplots(figsize=(12,5),constrained_layout=True)
cols=['hr_bpm','br_bpm','sdnn_ms','rmssd_ms']
z=(d[cols]-d[cols].mean())/d[cols].std()
im=ax.imshow(z.T.values,aspect='auto',cmap='coolwarm',vmin=-2.5,vmax=2.5)
ax.set_xticks(range(len(d))); ax.set_xticklabels(d.subject.tolist(),rotation=90,fontsize=7)
ax.set_yticks(range(4)); ax.set_yticklabels(['HR','BR','SDNN','RMSSD'])
fig.colorbar(im,ax=ax,label='z')
ax.set_xlabel('被试'); ax.set_ylabel('指标'); ax.set_title('E:Data 中段30秒指标标准化热图')
fig.savefig(OUT/'E_Data_metric_heatmap.png',dpi=180); plt.close(fig)

summary={
 'n_subjects':int(len(d)), 'n_calculable':int((d.quality=='可计算').sum()),
 'n_unavailable':int((d.quality!='可计算').sum()),
 'hr_median':float(d.hr_bpm.median()), 'br_median':float(d.br_bpm.median()),
 'sdnn_median':float(d.sdnn_ms.median()), 'rmssd_median':float(d.rmssd_ms.median()),
 'br_12_25_ratio':float(((d.br_bpm>=12)&(d.br_bpm<=25)).mean()),
 'hr_40_100_ratio':float(((d.hr_bpm>=40)&(d.hr_bpm<=100)).mean()),
}
(OUT/'summary_stats.txt').write_text('\n'.join(f'{k}={v}' for k,v in summary.items()),encoding='utf-8')
print(summary)
