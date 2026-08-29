# -*- coding: utf-8 -*-
"""
experiment_vmd_params_0814.py — VMD 参数自适应 A/B 实验（外部金标准数据集）
========================================================================
文件名：experiment_vmd_params_0814.py
版本：v1.0（2026-08-14）
功能：在外部金标准数据集上验证「VMD 参数网格自适应」是否优于固定参数
      （K=4, alpha=1000，项目现用值）。自适应准则：对每个参数组合做
      VMD 分解 → 选中心频率落在心跳带的 IMF 重建心跳 → 时域峰规则性
      评分（IBI 变异系数倒数）→ 取评分最优组合的心率估计。
      与固定参数及基线（带通滤波 + HPS）三路对比金标准。

      参考：Gu 2025 (arXiv:2502.11042) VMD+NRBO 自适应调参思路，
      本实验用网格搜索替代 NRBO 验证「自适应是否有收益」，有效再
      考虑移植优化器。

用法示例：
    python experiment_vmd_params_0814.py --folders 40 --seed 1   # 抽样 40 会话

依赖：numpy、scipy、vmdpy
"""

import argparse
import json
import pickle
import random
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, find_peaks, sosfiltfilt
from vmdpy import VMD

# ============================================================
# 参数集中声明
# ============================================================
DATA_DIR = Path(r'D:\Project\厚粲杯\11_数据\外部数据集_AgeBalanced_60GHz')
FS_RADAR = 10.0                       # 雷达帧率 Hz
WIN_S = 25.0                          # 窗口时长（与主验证一致）
K_GRID = [3, 4, 5]                    # VMD 分量数候选
ALPHA_GRID = [500, 1000, 2000]        # VMD 惩罚因子候选
K_FIXED, ALPHA_FIXED = 4, 1000        # 项目现用固定参数
HEART_BAND = (0.8, 2.5)               # 心跳频段 Hz
FILT_ORDER = 4                        # SOS 带通阶数
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'output' / '外部数据集' / '03_vmd_params'


def load_session(folder):
    """加载会话雷达距离谱（通道平均 + 静态杂波去除）。

    Args:
        folder: 会话目录

    Returns:
        prof: 复数距离谱 (n_frames, 64)
    """
    with open(folder / 'radar_rFFTs.zlib', 'rb') as f:
        rffts, _ = pickle.loads(zlib.decompress(f.read()))
    prof = np.mean(np.asarray(rffts), axis=1)
    return prof - prof.mean(axis=0, keepdims=True)


def select_bin(prof):
    """带内功率选主 bin（与主验证脚本同口径）。

    Returns:
        bin 索引
    """
    amp = np.abs(prof).mean(axis=0)
    amp_th = 0.2 * amp[1: 11].max()
    dphi_all = np.diff(np.angle(prof), axis=0)
    freq = np.fft.rfftfreq(dphi_all.shape[0], d=1 / FS_RADAR)
    band = (freq >= 0.15) & (freq <= 2.5)
    best_power, idx = -1.0, 1
    for g in range(1, 11):
        if amp[g] < amp_th:
            continue
        dphi = dphi_all[:, g] - dphi_all[:, g].mean()
        power = np.abs(np.fft.rfft(dphi))[band] ** 2
        if power.sum() > best_power:
            best_power, idx = power.sum(), g
    return idx


def peak_regularity_score(sig):
    """时域峰规则性评分：1/(IBI 变异系数 + 峰高变异系数)。

    Args:
        sig: 心跳候选信号

    Returns:
        (score, bpm)：评分与峰间隔心率；无有效峰返回 (-inf, None)
    """
    peaks, _ = find_peaks(sig, distance=int(0.25 * FS_RADAR),
                          prominence=0.2 * np.std(sig))
    if len(peaks) < 3:
        return -np.inf, None
    ibi = np.diff(peaks) / FS_RADAR
    ibi = ibi[(ibi > 0.25) & (ibi < 2.0)]
    if len(ibi) < 2:
        return -np.inf, None
    reg = ibi.std() / ibi.mean()
    h = sig[peaks]
    hcv = h.std() / (h.mean() + 1e-12)
    score = 1.0 / (reg + hcv + 1e-6)
    return score, 60.0 / np.median(ibi)


def vmd_heart_estimate(seg, k, alpha):
    """指定 VMD 参数的心跳估计：选心跳带内 IMF，取峰规则性最优者。

    Args:
        seg: 窗口信号（去均值）
        k, alpha: VMD 参数

    Returns:
        (score, bpm)：最优 IMF 的评分与心率
    """
    try:
        u, _, omega = VMD(seg, alpha=alpha, tau=0, K=k, DC=False,
                          init=1, tol=1e-6)
    except Exception:
        return -np.inf, None
    best_score, best_bpm = -np.inf, None
    for mode in u:
        dom = np.abs(np.fft.rfft(mode))
        freqs = np.fft.rfftfreq(len(mode), d=1 / FS_RADAR)
        band = (freqs >= HEART_BAND[0]) & (freqs <= HEART_BAND[1])
        if not band.any():
            continue
        center = freqs[band][np.argmax(dom[band])]
        if not (0.9 <= center <= 2.3):
            continue                      # 心跳带内但贴近边界的不算
        sc, bpm = peak_regularity_score(mode)
        if sc > best_score:
            best_score, best_bpm = sc, bpm
    return best_score, best_bpm


def baseline_estimate(seg):
    """基线：带通滤波 + 时域峰（不含 HPS，便于单独对比 VMD 贡献）。

    Returns:
        (score, bpm)
    """
    sos = butter(FILT_ORDER, [2 * HEART_BAND[0] / FS_RADAR,
                              2 * HEART_BAND[1] / FS_RADAR],
                 btype='bandpass', output='sos')
    heart = sosfiltfilt(sos, seg)
    return peak_regularity_score(heart)


def main():
    """主流程：抽样会话 → 三路估计（固定/自适应/基线）→ 金标准对比。"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--folders', type=int, default=40,
                        help='抽样会话数（默认 40，全部 220 较慢）')
    parser.add_argument('--seed', type=int, default=1, help='抽样随机种子')
    args = parser.parse_args()

    folders = sorted(p for p in DATA_DIR.glob('P*/**/R*')
                     if p.is_dir() and (p / 'radar_rFFTs.zlib').exists())
    random.seed(args.seed)
    folders = random.sample(folders, min(args.folders, len(folders)))

    # 三路误差收集
    err_fixed, err_adapt, err_base = [], [], []
    n_win = 0
    for folder in folders:
        try:
            prof = load_session(folder)
            g = select_bin(prof)
            phi = np.angle(prof[:, g])
            dphi = np.diff(np.unwrap(phi))
            win = int(0.25 * FS_RADAR)
            phi_s = np.convolve(dphi, np.ones(win) / win, mode='same')
            ecg = pd.read_csv(folder / 'movesense_ecg.csv',
                              parse_dates=['Timestamp'])
            t_ecg = (ecg['Timestamp'] - ecg['Timestamp'].iloc[0]
                     ).dt.total_seconds().to_numpy()
            mv = ecg['mV'].to_numpy()
        except Exception as e:
            print(f'[SKIP] {folder.name}: {type(e).__name__}')
            continue

        win_frames = int(WIN_S * FS_RADAR)
        for i0 in range(0, len(phi_s) - win_frames + 1, int(5 * FS_RADAR)):
            seg = phi_s[i0: i0 + win_frames]
            seg = seg - seg.mean()
            t0, t1 = i0 / FS_RADAR, (i0 + win_frames) / FS_RADAR
            # ECG 金标准（T 波剔除同主脚本）
            m = (t_ecg >= t0) & (t_ecg < t1)
            if m.sum() < FS_RADAR * 5:
                continue
            s = mv[m] - np.median(mv[m])
            sos = butter(2, [5, 15], btype='band', fs=250, output='sos')
            fe = sosfiltfilt(sos, s)
            peaks, _ = find_peaks(fe, distance=62, prominence=0.2 * np.std(fe))
            if len(peaks) < 3:
                continue
            t_p = t_ecg[m][peaks]; h_p = fe[peaks]
            keep = np.ones(len(peaks), bool)
            i = 1
            while i < len(peaks):
                if t_p[i] - t_p[i - 1] < 0.4:
                    if h_p[i] > h_p[i - 1]:
                        keep[i - 1] = False
                    else:
                        keep[i] = False
                i += 1
            peaks = peaks[keep]
            if len(peaks) < 3:
                continue
            rr = np.diff(t_ecg[m][peaks])
            rr = rr[(rr > 0.25) & (rr < 2.0)]
            if len(rr) < 2:
                continue
            gold = 60.0 / np.median(rr)

            # 三路估计
            _, b_fixed = vmd_heart_estimate(seg, K_FIXED, ALPHA_FIXED)
            best_par, best_sc = (K_FIXED, ALPHA_FIXED), -np.inf
            best_b = None
            for k in K_GRID:
                for a in ALPHA_GRID:
                    sc, b = vmd_heart_estimate(seg, k, a)
                    if sc > best_sc:
                        best_sc, best_par, best_b = sc, (k, a), b
            _, b_base = baseline_estimate(seg)
            n_win += 1
            if b_fixed:
                err_fixed.append(abs(b_fixed - gold))
            if best_b:
                err_adapt.append(abs(best_b - gold))
            if b_base:
                err_base.append(abs(b_base - gold))

    print(f'窗口数: {n_win}')
    print(f'固定 VMD (K=4, a=1000): MAE 中位 {np.median(err_fixed):.1f}, '
          f'均值 {np.mean(err_fixed):.1f} ({len(err_fixed)} 窗)')
    print(f'网格自适应 VMD:        MAE 中位 {np.median(err_adapt):.1f}, '
          f'均值 {np.mean(err_adapt):.1f} ({len(err_adapt)} 窗)')
    print(f'基线 (带通+峰检测):    MAE 中位 {np.median(err_base):.1f}, '
          f'均值 {np.mean(err_base):.1f} ({len(err_base)} 窗)')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / 'vmd_params_result.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'n_win': n_win,
                   'fixed': {'median': float(np.median(err_fixed)),
                             'mean': float(np.mean(err_fixed)),
                             'n': len(err_fixed)},
                   'adaptive': {'median': float(np.median(err_adapt)),
                                'mean': float(np.mean(err_adapt)),
                                'n': len(err_adapt)},
                   'baseline': {'median': float(np.median(err_base)),
                                'mean': float(np.mean(err_base)),
                                'n': len(err_base)}},
                  f, ensure_ascii=False, indent=2)
    print(f'[OK] 结果: {out}')


if __name__ == '__main__':
    main()


