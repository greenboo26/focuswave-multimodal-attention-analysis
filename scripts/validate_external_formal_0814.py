#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: validate_external_formal_0814.py
版本: v1.0 (2026-08-14)
功能: 把正式实验管线（analyze_mmwave_hrv.py 的窗级心跳评估）移植到
      外部金标准数据集上验证，回答"正式管线在外部数据上表现如何"。
      正式管线核心: 呼吸谐波陷波(v9 suppress_harmonics) → 心跳带
      periodogram 主频 → 主频±0.05Hz 窄带逐拍 → IBI 清洗 → 门控
      （HR 生理范围 + IBI CV + 时频一致性 ≤5 BPM）。
      适配差异（与正式管线）:
      · 帧率 100Hz→10Hz（外部数据），所有滤波/峰值参数按 fs=10 显式传入
      · 窗口 30s→25s（与主验证 validate_external_gold_0814 对齐以便对比）
      · bin 选择: 正式管线用 SPC+IQ 候选收集，外部数据为距离谱，
        改用主验证的带内功率 top3（bin 选择差异见 README 说明）
用法: python scripts/validate_external_formal_0814.py
依赖: numpy, pandas, scipy, matplotlib
输出: output/外部数据集/02_gold_validation/formal_validation_all.json
      output/外部数据集/02_gold_validation/formal_vs_hps_compare.png
"""

import json
import pickle
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal

# ============ 集中参数声明 ============
DATA_DIR = Path(r'D:\Project\厚粲杯\11_数据\外部数据集_AgeBalanced_60GHz')
JSON_HPS = Path(r'D:\Project\厚粲杯\08_算法\output\外部数据集\02_gold_validation\gold_validation_all.json')
OUT_JSON = Path(r'D:\Project\厚粲杯\08_算法\output\外部数据集\02_gold_validation\formal_validation_all.json')
OUT_PNG = Path(r'D:\Project\厚粲杯\08_算法\output\外部数据集\02_gold_validation\formal_vs_hps_compare.png')
FS_RADAR = 10.0                 # 外部数据帧率 Hz（正式管线为 100Hz，移植时显式传入）
FS_ECG = 256.0                  # ECG 采样率 Hz
WIN_S = 25.0                    # 窗口时长 s（与主验证对齐；正式管线为 30s）
STEP_S = 5.0                    # 窗口步长 s
# 正式管线门控参数（analyze_mmwave_hrv.py 头部声明，原样移植）
HR_MIN, HR_MAX = 40.0, 100.0    # 静息心率生理范围（bpm）
IBI_CV_MAX = 0.12               # IBI 变异系数上限
MIN_PEAKS_RATE = 0.5            # 每窗最少峰值 = 窗长(秒)×0.5
GAP_BPM = 5.0                   # 时频一致性门控（|逐拍HR - 主频×60| ≤ 5，同事所指"差5bpm"）
IBI_MIN_MS, IBI_MAX_MS = 300, 2000   # IBI 生理清洗范围（ms）
BREATH_BAND = (0.1, 0.5)        # 呼吸带 Hz
HEART_BAND = (0.8, 2.5)         # 心跳带 Hz
NOTCH_Q, NOTCH_Q_H3 = 30, 40    # v9 陷波 Q 值（3 次谐波更窄）
# 多 bin 选择（主验证一致，保证对比公平）
RANGE_BIN_MIN, RANGE_BIN_MAX = 10, 50
N_BINS = 3
AMP_TH_RATIO = 0.5
DPI = 150
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def load_radar(folder):
    """读取雷达距离谱（与主验证一致）。"""
    with open(folder / 'radar_rFFTs.zlib', 'rb') as f:
        rffts, _ = pickle.loads(zlib.decompress(f.read()))
    return np.asarray(rffts)


def load_ecg(folder):
    """读取 ECG 金标准（相对秒 + mV）。"""
    ecg = pd.read_csv(folder / 'movesense_ecg.csv', parse_dates=['Timestamp'])
    t0 = ecg['Timestamp'].iloc[0]
    t_sec = (ecg['Timestamp'] - t0).dt.total_seconds().to_numpy()
    return t_sec, ecg['mV'].to_numpy()


def ecg_hr_bpm(t_sec, mv, win_t0, win_t1):
    """窗口内 ECG 金标准心率（R 峰 + T 波剔除，与主验证一致）。"""
    m = (t_sec >= win_t0) & (t_sec < win_t1)
    if m.sum() < FS_ECG * 5:
        return None
    seg = mv[m] - np.median(mv[m])
    sos = signal.butter(2, [5, 15], btype='band', fs=FS_ECG, output='sos')
    f = signal.sosfiltfilt(sos, seg)
    peaks, _ = signal.find_peaks(f, distance=int(0.25 * FS_ECG),
                                 prominence=0.2 * np.std(f))
    if len(peaks) < 3:
        return None
    # T 波剔除：间隔 <0.4s 的相邻峰保留幅度更高者
    t_peak = t_sec[m][peaks]
    h_peak = f[peaks]
    keep = np.ones(len(peaks), dtype=bool)
    for i in range(1, len(peaks)):
        if t_peak[i] - t_peak[i - 1] < 0.4:
            if h_peak[i] > h_peak[i - 1]:
                keep[i - 1] = False
            else:
                keep[i] = False
    peaks = peaks[keep]
    if len(peaks) < 3:
        return None
    rr = np.diff(t_sec[m][peaks])
    rr = rr[(rr > 0.25) & (rr < 2.0)]
    if len(rr) < 2:
        return None
    return 60.0 / np.median(rr)


def select_top_bins(prof):
    """多 bin 选择：幅度达标门中按带内功率取 top N（与主验证一致）。"""
    amp = np.abs(prof).mean(axis=0)
    amp_th = AMP_TH_RATIO * amp[RANGE_BIN_MIN:RANGE_BIN_MAX + 1].max()
    dphi_all = np.diff(np.angle(prof), axis=0)
    freq = np.fft.rfftfreq(dphi_all.shape[0], d=1 / FS_RADAR)
    band = (freq >= 0.15) & (freq <= 2.5)
    scored = []
    for g in range(RANGE_BIN_MIN, RANGE_BIN_MAX + 1):
        if amp[g] < amp_th:
            continue
        dphi = dphi_all[:, g] - dphi_all[:, g].mean()
        power = np.abs(np.fft.rfft(dphi))[band] ** 2
        scored.append((power.sum(), g))
    scored.sort(reverse=True)
    return [g for _, g in scored[:N_BINS]]


def sos_bandpass(x, lo_hz, hi_hz):
    """SOS 带通（正式管线 _sos_bandpass 的 fs=10 移植版）。"""
    sos = signal.butter(4, [lo_hz, hi_hz], btype='band', fs=FS_RADAR, output='sos')
    return signal.sosfiltfilt(sos, x)


def estimate_freq_periodogram(x, lo_hz, hi_hz):
    """周期图主频（analyze_rest_3min 移植版，fs=10）。"""
    f, pxx = signal.periodogram(x, fs=FS_RADAR, window='hann')
    mask = (f >= lo_hz) & (f <= hi_hz)
    if not np.any(mask):
        return None
    return float(f[mask][np.argmax(pxx[mask])])


def suppress_harmonics(x, br_freq_hz):
    """呼吸谐波陷波（process_vital_signs_v9 移植版，fs=10）。

    对呼吸主频 1/2/3 次谐波 iirnotch 陷波，3 次谐波离心跳主频近
    用更窄 Q=40。
    """
    if br_freq_hz is None:
        return x
    y = x.copy()
    for h in range(1, 4):
        f0 = br_freq_hz * h
        if f0 > 3.0:
            break
        q = NOTCH_Q_H3 if h == 3 else NOTCH_Q
        b, a = signal.iirnotch(f0, q, FS_RADAR)
        y = signal.sosfiltfilt(signal.tf2sos(b, a), y)
    return y


def detect_heart_peaks_narrowband(heartbeat, hr_freq):
    """窄带逐拍峰检测（process_vital_signs_v9 移植版，fs=10）。

    主频 ±0.05Hz 窄带带通后，按参考周期 [0.75, 1.35]×ref 窗口
    滑动取局部最大。
    """
    if hr_freq is None:
        return np.array([], dtype=int)
    lo_nb, hi_nb = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
    sos_hp = signal.butter(4, [lo_nb, hi_nb], btype='band', fs=FS_RADAR, output='sos')
    xn = signal.sosfiltfilt(sos_hp, heartbeat)
    ref = 1.0 / hr_freq
    n_pts = len(xn)
    peaks_list = []
    i = 0
    while i < n_pts:
        lo_i = int(i + 0.75 * ref * FS_RADAR)
        hi_i = min(int(i + 1.35 * ref * FS_RADAR), n_pts)
        if lo_i >= n_pts or hi_i <= lo_i:
            break
        p = lo_i + np.argmax(xn[lo_i:hi_i])
        peaks_list.append(p)
        i = p + 1
    return np.array(peaks_list, dtype=int)


def formal_heart_assess(phi):
    """正式管线窗级心跳评估（evaluate_heart_bin 核心移植，fs=10）。

    Args:
        phi: 窗口内相位序列（去均值/去趋势后）

    Returns:
        dict: hr_bpm / hr_freq_bpm / n_peaks / cv / rejected(拒绝原因)
              hr_bpm 为 None 表示该窗口被正式管线门控拒绝
    """
    # 1. 呼吸主频（陷波输入）
    breath_bp = sos_bandpass(phi, *BREATH_BAND)
    br_freq = estimate_freq_periodogram(breath_bp, *BREATH_BAND)
    # 2. 呼吸谐波陷波 → 心跳带通
    phi_clean = suppress_harmonics(phi, br_freq)
    heart_bp = sos_bandpass(phi_clean, *HEART_BAND)
    # 3. periodogram 主频
    hr_freq = estimate_freq_periodogram(heart_bp, *HEART_BAND)
    # 4. 窄带逐拍
    hp = detect_heart_peaks_narrowband(heart_bp, hr_freq)
    if len(hp) < 5:
        return {'hr_bpm': None, 'hr_freq_bpm': None, 'n_peaks': len(hp),
                'rejected': 'few_peaks'}
    # 5. IBI 清洗 + 最少拍数门控
    ibi_ms = np.diff(hp) / FS_RADAR * 1000
    ibi_clean = ibi_ms[(ibi_ms >= IBI_MIN_MS) & (ibi_ms <= IBI_MAX_MS)]
    min_peaks = max(15, int(WIN_S * MIN_PEAKS_RATE))
    if len(ibi_clean) < min_peaks:
        return {'hr_bpm': None, 'hr_freq_bpm': None, 'n_peaks': len(hp),
                'rejected': 'few_valid_ibi'}
    # 6. 生理范围 + IBI CV 门控
    hr = 60000.0 / np.mean(ibi_clean)
    cv = np.std(ibi_clean) / np.mean(ibi_clean)
    if not (HR_MIN <= hr <= HR_MAX):
        return {'hr_bpm': None, 'hr_freq_bpm': hr_freq * 60 if hr_freq else None,
                'n_peaks': len(hp), 'rejected': 'hr_range'}
    if cv >= IBI_CV_MAX:
        return {'hr_bpm': None, 'hr_freq_bpm': hr_freq * 60 if hr_freq else None,
                'n_peaks': len(hp), 'rejected': 'ibi_cv'}
    # 7. 时频一致性门控（同事所指"时域频域差 5bpm"）
    if hr_freq is not None and abs(hr - hr_freq * 60) > GAP_BPM:
        return {'hr_bpm': None, 'hr_freq_bpm': hr_freq * 60,
                'n_peaks': len(hp), 'rejected': 'time_freq_gap'}
    return {'hr_bpm': hr, 'hr_freq_bpm': hr_freq * 60 if hr_freq else None,
            'n_peaks': len(hp), 'cv': cv, 'rejected': None}


def process_session(folder):
    """单会话: 通道平均 → 静态杂波去除 → 选 bin → 逐窗口正式管线评估。

    Returns:
        list[dict]: 窗口记录（win_start_s / bin_hrs / hr_bpm / gold_bpm）
    """
    rffts = load_radar(folder)
    t_ecg, mv = load_ecg(folder)
    # 通道平均 + 静态杂波去除（与主验证一致）
    prof = np.mean(rffts, axis=1)
    prof = prof - prof.mean(axis=0, keepdims=True)
    bins = select_top_bins(prof)

    win_frames = int(WIN_S * FS_RADAR)
    step_frames = int(STEP_S * FS_RADAR)
    rows = []
    for i0 in range(0, prof.shape[0] - win_frames + 1, step_frames):
        t0 = i0 / FS_RADAR
        bin_results = []
        for g in bins:
            # 相位序列（与正式管线一致: unwrap 后不做额外平滑）
            phi = np.unwrap(np.angle(prof[:, g]))
            seg = phi[i0:i0 + win_frames]
            seg = signal.detrend(seg)
            r = formal_heart_assess(seg)
            r['bin'] = g
            bin_results.append(r)
        # 多 bin 共识: 通过门控的 bin 取中位（类比主验证 vote_bins）
        passed = [r['hr_bpm'] for r in bin_results if r['hr_bpm'] is not None]
        hr_final = float(np.median(passed)) if passed else None
        gold = ecg_hr_bpm(t_ecg, mv, t0, t0 + WIN_S)
        rows.append({
            'win_start_s': t0,
            'bin_results': bin_results,
            'hr_bpm': round(hr_final, 1) if hr_final else None,
            'gold_bpm': round(gold, 1) if gold else None,
        })
    return rows


def main():
    """主流程: 220 会话 → 正式管线评估 → 汇总统计 → 与 HPS 版对比出图。"""
    hps = json.load(open(JSON_HPS, encoding='utf-8'))
    sessions = [(s['folder'], Path(DATA_DIR) / s['folder']) for s in hps]
    print(f'会话数: {len(sessions)}')

    # 逐会话跑正式管线
    all_rows = []
    rejects = {}
    for folder_str, path in sessions:
        try:
            rows = process_session(path)
        except Exception as e:
            print(f'[跳过] {folder_str}: {e}')
            continue
        for r in rows:
            r['folder'] = folder_str
            all_rows.append(r)
            for b in r['bin_results']:
                if b['rejected']:
                    rejects[b['rejected']] = rejects.get(b['rejected'], 0) + 1

    n_win = len(all_rows)
    n_gold = sum(1 for r in all_rows if r['gold_bpm'] is not None)
    n_pass = sum(1 for r in all_rows if r['hr_bpm'] is not None and r['gold_bpm'] is not None)
    errs = [abs(r['hr_bpm'] - r['gold_bpm']) for r in all_rows
            if r['hr_bpm'] is not None and r['gold_bpm'] is not None]
    errs = np.array(errs)
    summary = {
        'n_sessions': len(sessions),
        'n_windows': n_win,
        'n_with_gold': n_gold,
        'n_passed_gate': n_pass,
        'gate_pass_rate': round(n_pass / max(n_gold, 1), 3),
        'mae_median_bpm': round(float(np.median(errs)), 2) if len(errs) else None,
        'mae_mean_bpm': round(float(errs.mean()), 2) if len(errs) else None,
        'rmse_bpm': round(float(np.sqrt((errs ** 2).mean())), 2) if len(errs) else None,
        'pct_lt5': round(float((errs < 5).mean()), 3) if len(errs) else None,
        'pct_lt10': round(float((errs < 10).mean()), 3) if len(errs) else None,
        'reject_reasons': rejects,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print('正式管线验证汇总:', json.dumps(summary, ensure_ascii=False, indent=2))

    # 会话级对比: 正式管线 vs HPS 版（主验证）
    formal_sess, hps_sess = {}, {}
    for r in all_rows:
        if r['hr_bpm'] is not None and r['gold_bpm'] is not None:
            formal_sess.setdefault(r['folder'], []).append(abs(r['hr_bpm'] - r['gold_bpm']))
    for s in hps:
        if s['mae_bpm'] is not None:
            hps_sess[s['folder']] = s['mae_bpm']
    formal_mae = {k: np.median(v) for k, v in formal_sess.items()}
    common = sorted(set(formal_mae) & set(hps_sess))
    f_vals = [formal_mae[k] for k in common]
    h_vals = [hps_sess[k] for k in common]
    print(f'会话级对比（共同 {len(common)} 会话）:')
    print(f'  正式管线 MAE 中位: {np.median(f_vals):.2f} BPM')
    print(f'  HPS 版   MAE 中位: {np.median(h_vals):.2f} BPM')

    # 对比图: 左-正式管线可用窗口误差直方, 右-会话级正式vs HPS 散点
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    ax = axes[0]
    if len(errs):
        ax.hist(errs, bins=25, edgecolor='k', color='#2ca25f', alpha=0.8)
        ax.axvline(np.median(errs), color='r', ls='--',
                   label=f'中位 {np.median(errs):.1f} BPM')
        ax.legend()
    ax.set_xlabel('窗口级 |正式管线 HR - ECG 金标准| (BPM)')
    ax.set_ylabel('窗口数')
    ax.set_title(f'正式管线可用窗口误差（门控通过率 {summary["gate_pass_rate"]*100:.0f}%）')
    ax = axes[1]
    ax.scatter(h_vals, f_vals, s=15, alpha=0.5, c='#4a90d9')
    lim = [0, max(max(h_vals), max(f_vals)) + 2]
    ax.plot(lim, lim, 'k--', lw=1, label='两者相等')
    ax.set_xlabel('HPS 版会话级 MAE (BPM)')
    ax.set_ylabel('正式管线会话级 MAE (BPM)')
    ax.set_title('会话级对比: 正式管线 vs HPS 版')
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=DPI)
    print(f'[OK] 对比图: {OUT_PNG}')


if __name__ == '__main__':
    main()
