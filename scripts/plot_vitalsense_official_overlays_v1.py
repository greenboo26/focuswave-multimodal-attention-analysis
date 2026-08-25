from pathlib import Path
import argparse
import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser(); p.add_argument('--data-dir',type=Path,required=True); p.add_argument('--official-dir',type=Path,required=True); p.add_argument('--out-dir',type=Path,required=True); a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    for s in ['VS02','VS12','VS24']:
        for c in ['Resting','Apnea']:
            r=loadmat(a.data_dir/f'{s}_{c}.mat',squeeze_me=True,struct_as_record=False); m=loadmat(a.data_dir/f'{s}_{c}_Mindray.mat',squeeze_me=True,struct_as_record=False)
            vital=np.asarray(r['VitalSig'],float).squeeze(); fs=float(np.asarray(r['Radar'].fs).squeeze()); t=np.asarray(r['Radar'].t_frame,float).squeeze(); t=t-t[0]
            ecg=np.asarray(m['ecg_lead2'],float).squeeze(); fse=float(np.asarray(m['Fs_ecg']).squeeze()); te=np.arange(len(ecg))/fse
            b,a0=butter(4,[5/(fse/2),25/(fse/2)],btype='band'); ecgf=filtfilt(b,a0,(ecg-np.median(ecg))/(np.std(ecg)+1e-12));
            from scipy.signal import find_peaks
            ep,_=find_peaks(ecgf,distance=round(.3*fse),prominence=.35)
            beats=np.loadtxt(a.official_dir/'official_beats'/f'{s}_{c}_official_beats.csv',delimiter=',',ndmin=1)
            card=vital-filtfilt(*butter(4,.3/(fs/2),btype='low'),vital)
            fig,ax=plt.subplots(figsize=(12,3.8)); ax.plot(t,card/(np.std(card)+1e-12),color='#1f77b4',lw=.6,label='Radar cardiac residual'); ax.vlines(beats,-3,3,color='#d62728',lw=.7,alpha=.7,label='Official RWAMF beats');
            ax2=ax.twinx(); ax2.plot(te,ecgf,color='#222222',lw=.35,alpha=.45,label='ECG Lead II filtered'); ax2.scatter(te[ep],ecgf[ep],s=8,color='#2ca02c',label='ECG R peaks'); ax.set_xlim(0,t[-1]); ax.set_xlabel('Time (s)'); ax.set_title(f'{s} {c}: official VitalSense beat overlay');
            h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); ax.legend(h1+h2,l1+l2,loc='upper right',fontsize=8); fig.tight_layout(); fig.savefig(a.out_dir/f'{s}_{c}_official_overlay.png',dpi=150); plt.close(fig)
if __name__=='__main__': main()
