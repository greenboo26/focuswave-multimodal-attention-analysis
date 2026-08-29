# -*- coding: utf-8 -*-
"""对比 baseline vs block1 的呼吸主频 + 心跳带频谱，判断陷波安全性"""
import numpy as np, csv, os, sys
from pathlib import Path
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import process_vital_signs_v3_1_1 as algo
from process_vital_signs_v3_1_1 import FS, HR_LO_HZ, HR_HI_HZ, BR_LO_HZ, BR_HI_HZ

DATA_ROOT = Path(r"D:\acq_mmwave_results\sub-9779_")
EVENTS = DATA_ROOT / "beh" / "events.csv"
MM_DIR = DATA_ROOT / "mmwave"
PREFIX = "sub-9779_mmwave"

# 读段边界
segs = {}
with open(EVENTS, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row['event'] == 'segment_start':
            segs.setdefault(row['segment'], {})['start'] = int(row['unix_ms'])
        elif row['event'] == 'segment_end':
            segs.setdefault(row['segment'], {})['end'] = int(row['unix_ms'])

ts = np.loadtxt(MM_DIR / f'{PREFIX}_timestamps.csv', delimiter=',')[:, 2]
npz_files = algo.collect_npz_parts(MM_DIR, pattern=f'{PREFIX}_datacube_part*.npz')

for segname, gold_hr in [('baseline', 85.1), ('block1', 84.7)]:
    t0, t1 = segs[segname]['start'], segs[segname]['end']
    f0 = int(np.searchsorted(ts, t0)); f1 = int(np.searchsorted(ts, t1)) - 1
    ch_power, bin_power_acc, _ = algo.accumulate_range_profile(npz_files, frame_start=f0, frame_end=f1)
    iq_sample = next(algo._iter_selected_chunks(npz_files, frame_start=f0, frame_end=f1))
    iq_fd = algo._as_range_cube(iq_sample)
    gate = algo._distance_gate_to_bin_mask(bin_power_acc.shape[0], 0.3, 1.5, 0.08, 0.0)
    bpa = np.array(bin_power_acc, copy=True); bpa[~gate, :] = 0.0
    br_ch, br_bin, hr_ch, hr_bin, _ = algo.select_separate_channels_bins(bpa, iq_fd, iq_sample.shape[0])
    disp_br, disp_hr, n = algo.extract_displacement_separate(npz_files, br_ch, br_bin, hr_ch, hr_bin, frame_start=f0, frame_end=f1)

    br_bp = algo._sos_bandpass(disp_br, BR_LO_HZ, BR_HI_HZ)
    br_freq = algo.estimate_freq_periodogram(br_bp, BR_LO_HZ, BR_HI_HZ)
    freqs = np.fft.rfftfreq(n, d=1/FS)
    disp_dt = signal.detrend(disp_hr, type='linear')
    _, pxx = signal.periodogram(disp_dt, fs=FS, window='hann')
    hm = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    dom = freqs[hm][np.argmax(pxx[hm])]
    # 真实心率处功率
    true_hz = gold_hr/60
    near = (freqs >= true_hz-0.1) & (freqs <= true_hz+0.1)
    true_power = np.max(pxx[near])

    print(f"\n=== {segname} (真实HR {gold_hr}bpm={true_hz:.3f}Hz) ===")
    print(f"  呼吸主频 {br_freq:.3f}Hz = {br_freq*60:.1f}次/分" if br_freq else "  呼吸无主频")
    if br_freq:
        # 真实心率是第几次谐波附近
        for h in range(1, 16):
            fh = br_freq * h
            if 0.7 <= fh <= 2.6:
                mark = " <== 真实心率附近!" if abs(fh - true_hz) < 0.06 else ""
                print(f"    呼吸第{h:2d}次谐波 = {fh:.3f}Hz = {fh*60:.1f}bpm{mark}")
    print(f"  心跳带主频 {dom*60:.1f}bpm, 真实心率处功率={true_power:.2f}, 主频功率={np.max(pxx[hm]):.2f}")


