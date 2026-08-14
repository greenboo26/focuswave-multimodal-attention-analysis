#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: audit_signal_quality_0814.py
版本: v1.0 (2026-08-14)
功能: 外部金标准数据集信号质量审计——回答"low 窗口是数据差还是算法差"。
      对每个窗口计算四个与算法无关的信号质量指标，与主验证的 quality
      标签及估计误差对比：
      · heart_snr: 心跳带(0.8-2.5Hz)功率 / 噪声带(3-5Hz)功率（dB）
      · breath_ratio: 呼吸带(0.1-0.5Hz)功率 / 心跳带功率
      · motion_std: 窗口内加速度合成幅度标准差（被试运动量）
      · bin_amp: 所选距离门平均幅度（反射强度）
      判据：
      · low 窗口若 SNR 显著低于 high → 数据差主导
      · low 窗口若 SNR 与 high 相当 → 算法差主导
      · 半频锁定窗口若 SNR 不低 → 半频锁定是算法缺陷实锤
用法: python scripts/audit_signal_quality_0814.py
依赖: numpy, pandas, scipy, matplotlib
数据: 11_数据/外部数据集_AgeBalanced_60GHz + gold_validation_all.json
输出: output/外部数据集/02_gold_validation/signal_quality_audit.json / .png
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
from scipy.signal import butter, sosfiltfilt

# ============ 集中参数声明 ============
DATA_DIR = Path(r'D:\Project\厚粲杯\11_数据\外部数据集_AgeBalanced_60GHz')
JSON_VAL = Path(r'D:\Project\厚粲杯\08_算法\output\外部数据集\02_gold_validation\gold_validation_all.json')
OUT_JSON = Path(r'D:\Project\厚粲杯\08_算法\output\外部数据集\02_gold_validation\signal_quality_audit.json')
OUT_PNG = Path(r'D:\Project\厚粲杯\08_算法\output\外部数据集\02_gold_validation\signal_quality_audit.png')
FS_RADAR = 10.0                 # 雷达帧率 Hz
WIN_S = 25.0                    # 窗口时长 s（与主验证一致）
STEP_S = 5.0                    # 窗口步长 s（与主验证一致）
HEART_BAND = (0.8, 2.5)         # 心跳频段 Hz
BREATH_BAND = (0.1, 0.5)        # 呼吸频段 Hz
NOISE_BAND = (3.0, 5.0)         # 噪声频段 Hz（Nyquist 5Hz）
RANGE_BIN_MIN, RANGE_BIN_MAX = 10, 50   # 距离门搜索范围（与主验证一致）
N_BINS = 3                      # 审计用 bin 数（与主验证一致）
AMP_TH_RATIO = 0.5              # 噪声门幅度比例（与主验证一致）
DPI = 150
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def load_radar(folder):
    """读取雷达距离谱与时间戳（与主验证脚本一致）。"""
    with open(folder / 'radar_rFFTs.zlib', 'rb') as f:
        rffts, _ = pickle.loads(zlib.decompress(f.read()))
    return np.asarray(rffts)


def load_acc(folder):
    """读取加速度计，转相对秒与三轴合成幅度。"""
    acc = pd.read_csv(folder / 'movesense_acc.csv', parse_dates=['Timestamp'])
    t = (acc['Timestamp'] - acc['Timestamp'].iloc[0]).dt.total_seconds().to_numpy()
    mag = np.sqrt((acc[['X: (m/s^2)', 'Y: (m/s^2)', 'Z: (m/s^2)']] ** 2).sum(axis=1)).to_numpy()
    return t, mag


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


def bin_phase(prof, g):
    """单 bin 相位链路：unwrap → 差分 → 0.25s 滑动平均（与主验证一致）。"""
    phi = np.angle(prof[:, g])
    dphi = np.diff(np.unwrap(phi))
    win = int(0.25 * FS_RADAR)
    return np.convolve(dphi, np.ones(win) / win, mode='same')


def band_power(seg, band):
    """计算信号在指定频段的功率（去除均值与线性趋势后 FFT）。"""
    seg = seg - seg.mean()
    seg = seg - np.polyval(np.polyfit(np.arange(len(seg)), seg, 1), np.arange(len(seg)))
    freq = np.fft.rfftfreq(len(seg), d=1 / FS_RADAR)
    spec = np.abs(np.fft.rfft(seg)) ** 2
    m = (freq >= band[0]) & (freq <= band[1])
    return spec[m].sum()


def window_metrics(phi_s, acc_t, acc_mag, prof_amp, bins):
    """逐窗口计算四项信号质量指标。

    Args:
        phi_s: 相位信号列表（每 bin 一个，与主验证同长度）
        acc_t, acc_mag: 加速度相对秒与合成幅度
        prof_amp: 距离谱平均幅度 (64,)
        bins: 选中的距离门索引

    Returns:
        list of dict: 每窗口 heart_snr/breath_ratio/motion_std/bin_amp
    """
    win_frames = int(WIN_S * FS_RADAR)
    step_frames = int(STEP_S * FS_RADAR)
    rows = []
    for i0 in range(0, len(phi_s[0]) - win_frames + 1, step_frames):
        t0, t1 = i0 / FS_RADAR, (i0 + win_frames) / FS_RADAR
        snrs, breaths = [], []
        for ps in phi_s:
            seg = ps[i0:i0 + win_frames]
            p_heart = band_power(seg, HEART_BAND)
            p_noise = band_power(seg, NOISE_BAND)
            p_breath = band_power(seg, BREATH_BAND)
            # 三 bin 取中位，避免单 bin 异常
            snrs.append(10 * np.log10(p_heart / max(p_noise, 1e-20)))
            breaths.append(p_breath / max(p_heart, 1e-20))
        # 窗口内运动量（加速度合成幅度标准差，去重力常数不影响 std）
        m = (acc_t >= t0) & (acc_t < t1)
        motion = float(np.std(acc_mag[m])) if m.sum() > 10 else float('nan')
        rows.append({'win_start_s': i0 / FS_RADAR,
                     'heart_snr_db': float(np.median(snrs)),
                     'breath_ratio': float(np.median(breaths)),
                     'motion_std': motion,
                     'bin_amp': float(np.median(prof_amp[bins]))})
    return rows


def audit_session(folder):
    """对单个会话做审计，返回与主验证窗口对齐的指标行。"""
    rffts = load_radar(folder)
    # 与主验证一致: 8 天线通道平均 + 静态杂波去除
    prof = np.mean(rffts, axis=1)                      # (n_frames, 64)
    prof = prof - prof.mean(axis=0, keepdims=True)     # 静态杂波去除
    bins = select_top_bins(prof)
    phi_s = [bin_phase(prof, g) for g in bins]
    acc_t, acc_mag = load_acc(folder)
    prof_amp = np.abs(prof).mean(axis=0)
    return window_metrics(phi_s, acc_t, acc_mag, prof_amp, bins)


def main():
    """主流程: 220 会话审计 → join 主验证标签 → 统计与出图。"""
    val = json.load(open(JSON_VAL, encoding='utf-8'))
    # 会话路径列表
    sessions = [(s['folder'], Path(DATA_DIR) / s['folder']) for s in val]
    print(f'审计会话数: {len(sessions)}')

    # 逐会话审计，与主验证窗口 join
    joined = []
    for folder_str, path in sessions:
        try:
            rows = audit_session(path)
        except Exception as e:
            print(f'[跳过] {folder_str}: {e}')
            continue
        s = next(x for x in val if x['folder'] == folder_str)
        by_start = {r['win_start_s']: r for r in rows}
        for w in s['windows']:
            r = by_start.get(w['win_start_s'])
            if r is None:
                continue
            r = dict(r)
            r['quality'] = w['quality']
            r['freq_bpm'] = w.get('freq_bpm')
            r['gold_bpm'] = w.get('gold_bpm')
            r['folder'] = folder_str
            joined.append(r)
    print(f'join 成功窗口: {len(joined)}')

    # 分组统计
    groups = {}
    for q in ['high', 'med', 'low']:
        rows = [r for r in joined if r['quality'] == q]
        groups[q] = rows
    # 半频锁定窗口（频域估计约为金标准一半）
    half = [r for r in joined if r.get('freq_bpm') and r.get('gold_bpm')
            and 0.4 < r['freq_bpm'] / r['gold_bpm'] < 0.6]
    # 低质量但非半频的窗口（残余原因组）
    low_other = [r for r in groups['low']
                 if not (r.get('freq_bpm') and r.get('gold_bpm')
                         and 0.4 < r['freq_bpm'] / r['gold_bpm'] < 0.6)]

    def med(rows, key):
        vals = [r[key] for r in rows if not np.isnan(r[key])]
        return float(np.median(vals)) if vals else float('nan')

    summary = {
        'n_windows': {q: len(groups[q]) for q in groups},
        'n_half_locked': len(half),
        'n_low_other': len(low_other),
        'heart_snr_db': {
            'high': med(groups['high'], 'heart_snr_db'),
            'med': med(groups['med'], 'heart_snr_db'),
            'low': med(groups['low'], 'heart_snr_db'),
            'low_half': med(half, 'heart_snr_db'),
            'low_other': med(low_other, 'heart_snr_db'),
        },
        'breath_ratio': {
            'high': med(groups['high'], 'breath_ratio'),
            'med': med(groups['med'], 'breath_ratio'),
            'low': med(groups['low'], 'breath_ratio'),
            'low_half': med(half, 'breath_ratio'),
            'low_other': med(low_other, 'breath_ratio'),
        },
        'motion_std': {
            'high': med(groups['high'], 'motion_std'),
            'med': med(groups['med'], 'motion_std'),
            'low': med(groups['low'], 'motion_std'),
            'low_half': med(half, 'motion_std'),
            'low_other': med(low_other, 'motion_std'),
        },
        'bin_amp': {
            'high': med(groups['high'], 'bin_amp'),
            'med': med(groups['med'], 'bin_amp'),
            'low': med(groups['low'], 'bin_amp'),
            'low_half': med(half, 'bin_amp'),
            'low_other': med(low_other, 'bin_amp'),
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print('审计汇总:', json.dumps(summary, ensure_ascii=False, indent=2))

    # 出图: 四指标 × 五组箱线图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    group_names = ['high', 'med', 'low\n(非半频)', 'low\n(半频)', 'low\n(全部)']
    group_rows = [groups['high'], groups['med'], low_other, half, groups['low']]
    for ax, key, title in [
        (axes[0, 0], 'heart_snr_db', '心跳带信噪比 (dB)'),
        (axes[0, 1], 'breath_ratio', '呼吸/心跳功率比'),
        (axes[1, 0], 'motion_std', '窗口内运动量 std (m/s²)'),
        (axes[1, 1], 'bin_amp', '距离门反射幅度'),
    ]:
        data = [[r[key] for r in rows if not np.isnan(r[key])] for rows in group_rows]
        bp = ax.boxplot(data, tick_labels=group_names, patch_artist=True,
                        showfliers=False)
        for patch in bp['boxes']:
            patch.set_facecolor('#8ab4d8')
            patch.set_alpha(0.7)
        for i, dd in enumerate(data):
            if dd:
                ax.text(i + 1, np.median(dd), f'{np.median(dd):.2f}',
                        ha='center', va='bottom', fontsize=9)
        ax.set_title(title)
        ax.set_ylabel(title)
    fig.suptitle('信号质量审计: high / med / low(非半频) / low(半频) 对比', fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_PNG, dpi=DPI)
    print(f'[OK] 审计图: {OUT_PNG}')


if __name__ == '__main__':
    main()
