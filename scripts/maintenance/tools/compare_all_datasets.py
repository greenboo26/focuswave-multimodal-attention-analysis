"""
compare_all_datasets.py — 跨数据集信号质量统一对比
========================================================
目的: 回答"预实验信号差是不是算法/门控问题"。对全部历史
      数据集(旧 SART 有电脑遮挡、3min/深呼吸无遮挡、今日预实验
      新环境)用同一套无门控诊断, 对比:
        - 距离-幅度轮廓(人体反射在哪、多强)
        - 相位频谱(呼吸带/心跳带峰, 判断是否含生理信号)
        - 场景活跃度(多少 bin 在动)

用法:
  python compare_all_datasets.py

依赖: numpy, scipy
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

FS = 99.0  # 采样率近似(各数据集 97.8-99.5, 频谱带边界对结论不敏感)
CHUNK = 1000

# (标签, mmwave 目录)
DATASETS = [
    ("旧SART-001(有电脑)", r"E:\sub-001_\mmwave"),
    ("旧SART-007(有电脑)", r"E:\sub-007_\mmwave"),
    ("旧SART-008(有电脑)", r"E:\sub-008_\mmwave"),
    ("SXQ-47min", r"E:\sub-sxq_\mmwave"),
    ("REST-3min(无遮挡)", r"D:\Project\厚粲杯\11_数据\sub-rest_3min_\mmwave"),
    ("DEEP-BREATH(无遮挡)", r"D:\Project\厚粲杯\11_数据\sub-deep-breath\ses-DB\mmwave"),
    ("预实验-001(新环境)", r"E:\预实验\sub-001_\mmwave"),
    ("预实验-002(新环境)", r"E:\预实验\sub-002_\mmwave"),
]


def load_window(mm_dir: Path):
    """加载数据集中间 60s 窗。

    返回 (iq (n,256,8) complex64, meta dict) 或 (None, meta)。
    """
    meta_paths = list(mm_dir.glob("*.meta.json"))
    if not meta_paths:
        return None, None
    meta = json.loads(meta_paths[0].read_text(encoding="utf-8"))
    ts_paths = list(mm_dir.glob("*timestamps.csv"))
    if not ts_paths:
        return None, meta
    frame_idx, rad_ms = [], []
    with open(ts_paths[0]) as f:
        for ln in f:
            p = ln.strip().split(",")
            if len(p) >= 2 and p[0].strip().isdigit():
                frame_idx.append(int(p[0]))
                rad_ms.append(int(p[1]))
    frame_idx, rad_ms = np.array(frame_idx), np.array(rad_ms, dtype=np.int64)
    if len(frame_idx) < CHUNK:
        return None, meta

    # 中间 60s 窗
    t_mid = int((rad_ms[0] + rad_ms[-1]) / 2)
    t0, t1 = t_mid - 30_000, t_mid + 30_000
    fa = max(int(np.searchsorted(rad_ms, t0)), 0)
    fb = min(int(np.searchsorted(rad_ms, t1)), len(frame_idx) - 1)
    fa = min(fa, fb - 1)

    # 按帧号加载分片
    first = int(frame_idx[0])
    parts = sorted(mm_dir.glob("*part*.npz"))
    main_npz = mm_dir.glob("*datacube.npz")
    main_file = [p for p in main_npz if "part" not in p.name]
    all_files = list(parts)
    if main_file:
        all_files.insert(0, main_file[0])
    if not all_files:
        return None, meta

    def frames_for(fa_f, fb_f):
        i_start = (fa_f - first) // CHUNK
        i_end = (fb_f - first + CHUNK - 1) // CHUNK
        chunks = []
        for i in range(i_start, min(i_end, len(all_files))):
            d = np.load(all_files[i])
            keys = sorted([k for k in d.files if k.startswith("tx")])
            if not keys:
                d.close()
                continue
            chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
            d.close()
            chunks.append(chunk)
        if not chunks:
            return None
        iq = np.concatenate(chunks)
        off = first + i_start * CHUNK
        return iq[fa_f - off : fb_f - off]

    iq = frames_for(int(frame_idx[fa]), int(frame_idx[fb]))
    return iq, meta


def diagnose(mm_dir, label):
    iq, meta = load_window(Path(mm_dir))
    if iq is None:
        print(f"[{label}] 无法加载")
        return
    n = iq.shape[0]
    print(f"===== {label} ({n} 帧 ≈ {n / 99.0:.0f}s) =====")

    power = np.mean(np.abs(iq) ** 2, axis=0)  # (256, 8)
    # 1. 距离轮廓: 最强 bin 与峰宽
    b_peak, ch_peak = np.unravel_index(np.argmax(power), power.shape)
    p_max = power[b_peak, ch_peak]
    # 峰宽: 该通道中功率 > 峰值一半的连续 bin 范围
    prof = power[:, ch_peak]
    half = prof > p_max * 0.5
    idxs = np.where(half)[0]
    width = (idxs.max() - idxs.min() + 1) if len(idxs) else 1
    print(f"  距离轮廓: 最强 bin={b_peak} ch={ch_peak} 功率={p_max:.3e} 峰宽={width}bin")

    # 2. 场景活跃度 + 最活跃 bin 频谱
    n_active = 0
    best_phys = None  # (得分, bin, ch, 呼吸峰, 心跳峰)
    best_var = None   # (方差, bin, ch, 频谱)
    for ch in range(8):
        for b in range(256):
            phi = np.unwrap(np.angle(iq[:, b, ch]))
            v = np.var(phi)
            if v < 0.001:
                continue
            n_active += 1
            phi_det = signal.detrend(phi)
            f, pxx = signal.periodogram(phi_det, fs=FS, window="hann")
            brm = (f >= 0.1) & (f <= 0.5)
            hm = (f >= 0.8) & (f <= 2.5)
            br_pk = pxx[brm].max()
            hr_pk = pxx[hm].max()
            # 人体特征得分: 呼吸峰强 + 心跳峰强 + 呼吸峰占主导
            total = pxx[(f >= 0.1) & (f <= 2.5)].max() + 1e-30
            score = (br_pk + hr_pk) * (br_pk / total)
            if best_phys is None or score > best_phys[0]:
                best_phys = (score, b, ch, br_pk, hr_pk, f, pxx)
            if best_var is None or v > best_var[0]:
                best_var = (v, b, ch, f, pxx)
    frac = n_active / (256 * 8) * 100
    print(f"  场景活跃: {n_active}/2048 bin 有相位变化 ({frac:.0f}%)")

    # 3. 最优生理特征 bin
    score, b, ch, br_pk, hr_pk, f, pxx = best_phys
    brm = (f >= 0.1) & (f <= 0.5)
    hm = (f >= 0.8) & (f <= 2.5)
    bf = f[brm][np.argmax(pxx[brm])]
    hf = f[hm][np.argmax(pxx[hm])]
    mag = np.abs(iq[:, b, ch])
    cv = np.std(mag) / (np.mean(mag) + 1e-12)
    phi = np.unwrap(np.angle(iq[:, b, ch]))
    print(f"  最优生理bin: bin={b} ch={ch} 幅度={mag.mean():.4f} CV={cv:.2f} "
          f"呼吸峰={bf:.2f}Hz({br_pk:.1e}) 心跳峰={hf:.2f}Hz({hr_pk:.1e})")
    # 心跳带峰的信噪比(相对全带)
    total_pk = pxx[(f >= 0.1) & (f <= 2.5)].max()
    print(f"  心跳带峰占全带峰值比: {hr_pk / total_pk:.3f}")
    print()


def main():
    for label, d in DATASETS:
        diagnose(d, label)


if __name__ == "__main__":
    main()


