"""临时: 同一数据 (sub-rest_3min) 对比不同 (ch,bin) 的时域心率（用完即删）"""
import os, sys, glob
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from process_vital_signs_v2 import FS
from analyze_rest_3min import detect_peaks_heart_lo

DATA_DIR = Path(r"D:\Project\厚粲杯\11_数据\sub-rest_3min_\mmwave")
npz_files = sorted(glob.glob(str(DATA_DIR / "*_datacube_part*.npz")))
print(f"npz 分片: {len(npz_files)}")

# 加载全部: channels → (帧, bin)
chans = {}
for f in npz_files:
    d = np.load(f)
    for k in d.keys():
        chans.setdefault(k, []).append(d[k])
ch_keys = sorted(chans.keys())
iq = {k: np.concatenate(v, axis=0) for k, v in chans.items()}
n_frames = iq[ch_keys[0]].shape[0]
print(f"通道数: {len(ch_keys)}, 总帧: {n_frames} ({n_frames/FS:.0f}s)")

def extract_disp(ch_key, b):
    x = iq[ch_key][:, b]
    phase = np.unwrap(np.angle(x))
    return phase - phase.mean()

def time_hr(disp):
    peaks = detect_peaks_heart_lo(disp, lo_bpm=40, hi_bpm=150)
    n = len(peaks)
    bpm = n / (len(disp) / FS) * 60 if n > 0 else None
    return bpm, n

# 8/6 自动选: 心跳带 (40-150bpm → 0.67-2.5Hz → 距离 bin 功率) 简化用 bin 功率
iq_fd_pow = {k: np.mean(np.abs(np.fft.fft(iq[k], axis=-2))**2, axis=0) for k in ch_keys}
best = None
for k in ch_keys:
    for b in range(256):
        if best is None or iq_fd_pow[k][b] > best[0]:
            best = (iq_fd_pow[k][b], k, b)
_, auto_ch, auto_bin = best
print(f"功率最高: ch={auto_ch} bin={auto_bin}")

cases = [("功率最高(自动)", auto_ch, auto_bin),
         ("一敏 v24 (ch3,bin33)", "tx0_rx2", 33),
         ("一敏 v2_3 gate (ch5,bin16)", "tx1_rx1", 16)]
for label, k, b in cases:
    if k not in iq:
        print(f"{label}: ch key {k} 不存在, 跳过")
        continue
    disp = extract_disp(k, b)
    bpm, n = time_hr(disp)
    print(f"{label}: bin={b} → 时域 HR={bpm:.1f} bpm, 峰数={n}")


