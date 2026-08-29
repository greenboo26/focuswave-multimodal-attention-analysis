"""Read-only frontend audit figure for one RS6240 CAL session; not a production analysis."""
from pathlib import Path
import json
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SOURCE = Path(r"D:\acq_mmwave_data\sub-2_\mmwave\sub-2_mmwave_datacube_part001.npz")
OUT = Path(__file__).parent
FS, SPACING, MIN_R, MAX_R = 100.0, 0.08, 0.30, 1.50
HR_LO, HR_HI, BR_LO, BR_HI = 0.8, 2.0, 0.1, 0.5

with np.load(SOURCE) as z:
    keys = sorted(k for k in z.files if k.startswith("tx"))
    cube = np.stack([z[k] for k in keys], axis=-1).astype(np.complex64)
dist = np.arange(cube.shape[1]) * SPACING
power = np.mean(np.abs(cube) ** 2, axis=0)  # range x channel, as accumulate_range_profile
ch_power = np.mean(np.abs(cube) ** 2, axis=(0, 1))
best_ch_auto = int(np.argmax(ch_power))
gate = (dist >= MIN_R) & (dist <= MAX_R)

def phase_stability(phi):
    pd = signal.detrend(phi, type="linear")
    osc = float(np.std(pd))
    if osc < 1e-8: return 0.0
    d = np.diff(pd)
    return 1.0 / (1.0 + .9 * float(np.std(d) / osc) + .35 * float(np.percentile(np.abs(d), 95) / osc))

freqs = np.fft.rfftfreq(cube.shape[0], d=1/FS)
summaries=[]
for ch in range(cube.shape[2]):
    bp = power[:,ch].copy(); bp[~gate] = 0
    thresh=float(bp.max())*.01; candidates=[]
    for b in range(len(bp)):
        if bp[b] < thresh: continue
        phi=np.unwrap(np.angle(cube[:,b,ch])); var=float(np.var(phi))
        if not (.1 < var < 50): continue
        pxx=np.abs(np.fft.rfft(signal.detrend(phi, type="linear")))**2
        noise=max(float(np.mean(pxx[(freqs>=2.5)&(freqs<=5.0)])),1e-10)
        hrs=float(np.mean(pxx[(freqs>=HR_LO)&(freqs<=HR_HI)])/noise)
        brs=float(np.mean(pxx[(freqs>=BR_LO)&(freqs<=BR_HI)])/noise)
        st=phase_stability(phi); candidates.append((b,hrs,brs,brs*st,np.log1p(max(hrs,0))*st**2))
    if not candidates: continue
    bestbr=max(candidates,key=lambda x:x[3]); besthr=max(candidates,key=lambda x:x[4])
    summaries.append(dict(channel=ch,breath_bin=bestbr[0],heart_bin=besthr[0],breath_score=bestbr[3],heart_score=besthr[4],n_candidates=len(candidates)))
br=max(summaries,key=lambda x:x['breath_score']); hr=max(summaries,key=lambda x:x['heart_score'])

raw_amp=np.abs(cube[:,:,br['channel']]); centered=np.abs(cube[:,:,br['channel']]-cube[:,:,br['channel']].mean(axis=0,keepdims=True))
fig,ax=plt.subplots(2,2,figsize=(15,9),constrained_layout=True)
im=ax[0,0].imshow(20*np.log10(raw_amp.T+1e-8),aspect='auto',origin='lower',extent=[0,cube.shape[0]/FS,dist[0],dist[-1]],cmap='viridis')
ax[0,0].set(title=f"Raw range-time magnitude, selected breath ch={br['channel']} (stored NPZ)",xlabel='time (s)',ylabel='range coordinate (m)');fig.colorbar(im,ax=ax[0,0],label='magnitude (dB rel. 1)')
im=ax[0,1].imshow(20*np.log10(centered.T+1e-8),aspect='auto',origin='lower',extent=[0,cube.shape[0]/FS,dist[0],dist[-1]],cmap='viridis')
ax[0,1].set(title='Audit-only temporal-mean subtraction (NOT pipeline preprocessing)',xlabel='time (s)',ylabel='range coordinate (m)');fig.colorbar(im,ax=ax[0,1],label='magnitude (dB rel. 1)')
ax[1,0].plot(dist,10*np.log10(power[:,br['channel']]+1e-14),label=f'ch {br["channel"]} raw mean power')
ax[1,0].axvspan(MIN_R,MAX_R,color='tab:green',alpha=.16,label='current 0.30–1.50 m gate')
ax[1,0].axvline(dist[br['breath_bin']],color='tab:orange',ls='--',label=f"breath bin {br['breath_bin']} ({dist[br['breath_bin']]:.2f} m)")
ax[1,0].axvline(dist[hr['heart_bin']],color='tab:red',ls=':',label=f"heart bin {hr['heart_bin']} ({dist[hr['heart_bin']]:.2f} m)")
ax[1,0].set(xlim=(0,3),title='Profile and current distance gate',xlabel='range coordinate (m)',ylabel='mean power (dB rel. 1)');ax[1,0].legend(fontsize=8);ax[1,0].grid(alpha=.25)
ax[1,1].bar(np.arange(len(ch_power)),10*np.log10(ch_power+1e-14));ax[1,1].axvline(best_ch_auto,color='tab:red',ls='--',label=f'ungated max-power ch {best_ch_auto}')
ax[1,1].set(title='Per-channel mean power (all ranges)',xlabel='stored antenna channel index',ylabel='mean power (dB rel. 1)');ax[1,1].legend(fontsize=8);ax[1,1].grid(axis='y',alpha=.25)
fig.suptitle('RS6240 frontend audit: CAL sub-2, part001, 1,000 stored frames / 10 s',fontsize=14)
fig.savefig(OUT/'cal_sub2_part001_frontend_audit.png',dpi=180);plt.close(fig)
summary=dict(source=str(SOURCE),keys=keys,shape=list(cube.shape),sampling_hz=FS,range_coordinate_formula='bin * 0.08 m; no bias',distance_gate_m=[MIN_R,MAX_R],auto_best_channel=best_ch_auto,selected_breath=br,selected_heart=hr,all_channel_summaries=summaries,notes=['Stored NPZ is already SDK DatacubeConversion output; this script does not run classification or alter raw files.','Temporal-mean subtraction panel is deliberately labeled audit-only because production selection does not apply it.'])
(OUT/'cal_sub2_part001_frontend_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


