# -*- coding: utf-8 -*-
"""临时验证：毫米波 rest1 段能否提取合理心跳 IBI。"""
import sys, os, glob
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from process_vital_signs_v2 import FS, N_CH
from analyze_rest_3min import select_bins_from_profile, analyze_displacement

DATA_DIR = r"E:\FocusWave_3.0.15\03-data\sub-cal01_\mmwave"
idx = np.load(os.path.join(SCRIPT_DIR, '_rest1_idx.npy'))   # rest1 全局帧索引
i0, i1 = int(idx[0]), int(idx[-1])
print(f"rest1 全局帧索引 {i0}~{i1}，共 {len(idx)} 帧")

# 读涉及的分块 part002~part032（全局索引 2000~32999）
chunk_start = (i0 // 1000) * 1000
chunk_end = (i1 // 1000 + 1) * 1000
chunks = []
n_frames_global = 0
base = chunk_start
for g in range(chunk_start, chunk_end, 1000):
    if g == 0:
        f = os.path.join(DATA_DIR, 'sub-cal01_mmwave_datacube.npz')
    else:
        f = os.path.join(DATA_DIR, f'sub-cal01_mmwave_datacube_part{g//1000:03d}.npz')
    d = np.load(f)
    keys = sorted([k for k in d.keys() if k.startswith('tx')])
    iq = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
    chunks.append(iq)
    d.close()
iq_full = np.concatenate(chunks, axis=0)   # (chunk_end-chunk_start, 256, 8)
print(f"读入 {iq_full.shape}，切 rest1 段")
iq = iq_full[i0 - base: i1 - base + 1]     # rest1 段 (29729, 256, 8)
del iq_full, chunks

# 选 bin
bin_power_acc = np.mean(np.abs(iq) ** 2, axis=0)          # (256, 8)
best_ch = int(np.argmax(np.mean(bin_power_acc, axis=0)))
print(f"best_ch={best_ch}，开始选 bin（可能需几十秒）...")
br_ch, br_bin, hr_ch, hr_bin, candidates = select_bins_from_profile(
    bin_power_acc, best_ch, iq, len(iq))
print(f"呼吸 bin: ch{br_ch}/bin{br_bin}  心跳 bin: ch{hr_ch}/bin{hr_bin}")
print(f"候选 bin 数: {len(candidates)}")

# 提取位移
disp_br = np.unwrap(np.angle(iq[:, br_bin, br_ch]))
disp_hr = np.unwrap(np.angle(iq[:, hr_bin, hr_ch]))
del iq

# 分析（先用 bp 带通方法，避免 vmdpy 依赖）
result, (t, breath, heartbeat, hp, bp) = analyze_displacement(
    disp_br, disp_hr, len(disp_hr), method='bp')
print("\n=== rest1 段毫米波提取结果 ===")
print(f"HR(freq)={result['heart_rate']['freq_bpm']} bpm, "
      f"HR(time)={result['heart_rate']['time_bpm']} bpm, "
      f"n_peaks={result['heart_rate']['n_peaks']}")
print(f"BR={result['breath_rate']['freq_bpm']} bpm")
if result['hrv']:
    h = result['hrv']
    print(f"HRV: mean_IBI={h.get('mean_nni', h.get('mean_ibi', '?'))}, "
          f"SDNN={h.get('sdnn', '?')}")
# 直接算 IBI
ibi = np.diff(hp) / FS * 1000
ibi_clean = ibi[(ibi >= 300) & (ibi <= 2000)]
print(f"毫米波 IBI: 均值={np.mean(ibi_clean):.1f}ms, 标准差={np.std(ibi_clean):.1f}ms, "
      f"n={len(ibi_clean)}")
print(f"前20个 IBI: {np.round(ibi_clean[:20]).astype(int).tolist()}")


