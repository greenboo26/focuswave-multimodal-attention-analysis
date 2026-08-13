# -*- coding: utf-8 -*-
"""
validate_external_gold_0814.py — 外部金标准数据集验证（60GHz AgeBalanced）
======================================================================
文件名：validate_external_gold_0814.py
版本：v1.0（2026-08-14）
功能：用本项目处理链路（静态杂波去除 + 带内功率选门 + SOS 窄带滤波 +
      窗口化时频融合）处理外部公开数据集（Zenodo 10.5281/zenodo.16760683，
      110 被试 60GHz 雷达 + Movesense ECG 金标准），逐窗口输出：
      - freq_bpm / time_bpm / fused_bpm：频域、时域与融合心率
      - time_freq_gap_bpm：时频差（置信度基础）
      - quality：high / med / low（时频一致 + 峰规则性门控）
      并与同窗 ECG 金标准心率对比，统计 MAE/RMSE 与可用窗口占比。

      数据格式（helper_fns.py / 论文）：
      - radar_rFFTs.zlib：zlib+pickle，(n_frames, 8通道, 64距离门) 复数
      - 帧率 10Hz（PERIODICITY=100ms），距离门 31.2cm（R_BIN）
      - movesense_ecg.csv：Timestamp,mV，约 250Hz
      - non_breathing_ts.csv：屏气段 begin/end（可选）

用法示例：
    python validate_external_gold_0814.py --folder P001/Lying/Rest
    python validate_external_gold_0814.py --all   # 全部 440 会话批量

依赖：numpy、pandas、matplotlib、scipy
"""

import argparse
import json
import pickle
import zlib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, find_peaks, sosfiltfilt

# 中文字体（Windows SimHei，避免中文显示为方框）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 参数集中声明
# ============================================================
DATA_DIR = Path(r'D:\Project\厚粲杯\11_数据\外部数据集_AgeBalanced_60GHz')
FS_RADAR = 10.0                       # 雷达帧率 Hz（PERIODICITY=100ms）
FS_ECG = 250.0                        # ECG 采样率 Hz（Movesense 实测约 250）
BREATH_BAND = (0.1, 0.5)              # 呼吸带通 Hz
HEART_BAND = (0.8, 2.5)               # 心跳带通 Hz（运动后可 >2Hz）
FILT_ORDER = 4                        # SOS 带通阶数
WIN_S, STEP_S = 25.0, 5.0             # 窗口时长与步长（对齐一敏 v3.1）
RANGE_BIN_MIN, RANGE_BIN_MAX = 1, 10  # 选门范围（bin 1-10 = 31.7cm-3.2m）
AMP_TH_RATIO = 0.2                    # 选门幅度阈值（相对最大）
N_BINS = 3                            # 多 bin 交叉验证候选数（带内功率 top N）
BIN_AGREE_BPM = 6.0                   # 多 bin 共识阈值（BPM，组内两两差 ≤ 此值）
GAP_HIGH, GAP_MED = 6.0, 12.0         # 时频差门控阈值（BPM）
MIN_PEAKS = 3                         # 时域峰最少数量（少于则 low）
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'output' / '外部数据集' / '02_gold_validation'


def load_radar(folder: Path):
    """加载雷达距离谱、时间戳与 chirp 配置。

    Args:
        folder: 会话目录（含 radar_rFFTs.zlib 等）

    Returns:
        (rffts, ts)：复数距离谱 (n_frames, 8, 64) 与时间戳序列
    """
    with open(folder / 'radar_rFFTs.zlib', 'rb') as f:
        rffts, _ = pickle.loads(zlib.decompress(f.read()))
    ts = pd.read_csv(folder / 'radar_timestamps.csv', header=None).squeeze().tolist()
    return np.asarray(rffts), ts


def load_ecg(folder: Path):
    """加载 ECG 金标准（时间戳 + mV）。

    Returns:
        (t_sec, mv)：相对秒与电压
    """
    ecg = pd.read_csv(folder / 'movesense_ecg.csv', parse_dates=['Timestamp'])
    t0 = ecg['Timestamp'].iloc[0]
    t_sec = (ecg['Timestamp'] - t0).dt.total_seconds().to_numpy()
    return t_sec, ecg['mV'].to_numpy()


def ecg_hr_bpm(t_sec, mv, win_t0, win_t1):
    """计算指定时间窗内的 ECG 金标准心率（R 峰检测 + T 波剔除）。

    T 波误检会导致金标准心率翻倍（实测 26% 的 R-R <0.4s 为 T 波），
    剔除规则：间隔 <0.4s 的相邻峰保留幅度更高者（R 峰远高于 T 波）。

    Args:
        t_sec, mv: ECG 时间与电压
        win_t0, win_t1: 窗口起止（秒）

    Returns:
        hr_bpm 或 None（窗口内峰不足）
    """
    m = (t_sec >= win_t0) & (t_sec < win_t1)
    if m.sum() < FS_ECG * 5:                    # 少于 5 秒数据
        return None
    seg = mv[m] - np.median(mv[m])
    sos = butter(2, [5, 15], btype='band', fs=FS_ECG, output='sos')
    f = sosfiltfilt(sos, seg)
    peaks, _ = find_peaks(f, distance=int(0.25 * FS_ECG),
                          prominence=0.2 * np.std(f))
    if len(peaks) < 3:
        return None
    # T 波剔除：近间隔峰保留高者
    t_peak = t_sec[m][peaks]
    h_peak = f[peaks]
    keep = np.ones(len(peaks), dtype=bool)
    i = 1
    while i < len(peaks):
        if t_peak[i] - t_peak[i - 1] < 0.4:
            if h_peak[i] > h_peak[i - 1]:
                keep[i - 1] = False
            else:
                keep[i] = False
        i += 1
    peaks = peaks[keep]
    if len(peaks) < 3:
        return None
    rr = np.diff(t_sec[m][peaks])
    rr = rr[(rr > 0.25) & (rr < 2.0)]           # 生理范围 30-240 BPM
    if len(rr) < 2:
        return None
    return 60.0 / np.median(rr)


def hps_fundamental(seg, f_lo=0.7, f_hi=2.3):
    """谐波乘积谱（Harmonic Product Spectrum）基频估计。

    频谱 S(f) 与 S(2f)、S(3f) 逐点相乘：真基频处各级谐波同时有能量，
    乘积最大；锁定在 2 倍谐波处时基频位置乘积小，天然免疫 2 倍频
    锁定（文献主流基频判决方法）。频率上限受奈奎斯特约束：
    f > fs/6 时只用 2 级乘积。

    Args:
        seg: 窗口内相位差信号
        f_lo, f_hi: 基频候选范围（Hz，默认 42-138 BPM）

    Returns:
        best_hz 或 None（无候选）
    """
    spec = np.abs(np.fft.rfft(seg))
    freq = np.fft.rfftfreq(len(seg), d=1 / FS_RADAR)
    best_hz, best_p = None, -1.0
    for f in freq[(freq >= f_lo) & (freq <= f_hi)]:
        p = spec[np.argmin(np.abs(freq - f))]
        for k in (2, 3):
            if k * f > freq.max():
                break                    # 谐波超出奈奎斯特，降级乘积
            p *= spec[np.argmin(np.abs(freq - k * f))]
        if p > best_p:
            best_p, best_hz = p, f
    return best_hz


def notch_respiration_harmonics(phi_s, breath_hz):
    """在呼吸谐波（3/4 倍基频）处陷波，防止其污染心跳频段。

    呼吸 3 倍谐波（0.45-1.5Hz）与 4 倍谐波（0.6-2.0Hz）常落入心跳
    带，是心率估计的主要干扰源。用窄带带阻（中心 ±3%）在谐波处
    开槽；谐波超出心跳带时跳过。

    Args:
        phi_s: 平滑相位差信号
        breath_hz: 呼吸基频（Hz）

    Returns:
        陷波后信号
    """
    if breath_hz is None:
        return phi_s
    out = phi_s.copy()
    for k in (3, 4):
        fh = k * breath_hz
        if not (HEART_BAND[0] <= fh <= HEART_BAND[1]):
            continue                      # 谐波在心跳带外，无需陷波
        sos = butter(2, [2 * fh * 0.97 / FS_RADAR, 2 * fh * 1.03 / FS_RADAR],
                     btype='bandstop', output='sos')
        out = sosfiltfilt(sos, out)
    return out


def refine_harmonic(seg, f0_hz):
    """2 倍频谐波判别：候选 f0 与半频 f0/2 比较时域峰规则性，选更可信者。

    心跳信号的二次谐波（回声）能量可能强于基频，导致频谱峰锁定在
    2 倍频。判别方法：对两个候选频率分别做窄带滤波 + 峰检测，评分 =
    1/(IBI 变异系数 + 峰高变异系数)，规则性高的候选是真基频。

    Args:
        seg: 窗口内相位差信号
        f0_hz: 频域初选频率（Hz）

    Returns:
        (best_hz, corrected)：修正后频率与是否修正
    """
    if f0_hz is None or f0_hz / 2 < 0.45:
        return f0_hz, False               # 半频低于 27 BPM 生理下限，不检查
    cands = [f0_hz, f0_hz / 2]
    best_hz, best_score = f0_hz, -1.0
    for fc in cands:
        # 窄带滤波（±15% 中心频率），峰距离限半周期
        sos = butter(FILT_ORDER, [2 * fc * 0.85 / FS_RADAR,
                                  2 * fc * 1.15 / FS_RADAR],
                     btype='bandpass', output='sos')
        s = sosfiltfilt(sos, seg)
        peaks, _ = find_peaks(s, distance=int(0.5 / fc * FS_RADAR),
                              prominence=0.2 * np.std(s))
        if len(peaks) < MIN_PEAKS:
            continue
        ibi = np.diff(peaks) / FS_RADAR
        ibi = ibi[(ibi > 0.25) & (ibi < 2.0)]
        if len(ibi) < 2:
            continue
        reg = ibi.std() / ibi.mean()       # IBI 变异系数
        h = s[peaks]
        hcv = h.std() / (h.mean() + 1e-12)  # 峰高变异系数
        score = 1.0 / (reg + hcv + 1e-6)
        if score > best_score:
            best_score, best_hz = score, fc
    return best_hz, abs(best_hz - f0_hz) > 1e-6


def window_vitals(phi_s):
    """对相位差信号做窗口化时频心率估计（25s 窗 5s 步长 + 谐波修正）。

    Args:
        phi_s: 平滑后的相位差信号（帧率 10Hz）

    Returns:
        list of dict：每窗口 freq_bpm/time_bpm/gap/quality/n_peaks
    """
    win_frames = int(WIN_S * FS_RADAR)
    step_frames = int(STEP_S * FS_RADAR)
    rows = []
    for i0 in range(0, len(phi_s) - win_frames + 1, step_frames):
        seg = phi_s[i0: i0 + win_frames]
        seg = seg - seg.mean()
        # 频域心率：谐波乘积谱基频估计（0.7-2.3Hz，天然抗 2 倍锁定）
        f0 = hps_fundamental(seg)
        # 2 倍频谐波判别（HPS 后二次保险）
        f1, corrected = refine_harmonic(seg, f0)
        freq_bpm = f1 * 60 if f1 else None
        # 时域心率（心跳带通后峰间隔）
        sos = butter(FILT_ORDER, [2 * HEART_BAND[0] / FS_RADAR,
                                  2 * HEART_BAND[1] / FS_RADAR],
                     btype='bandpass', output='sos')
        heart = sosfiltfilt(sos, seg)
        peaks, _ = find_peaks(heart, distance=int(0.25 * FS_RADAR),
                              prominence=0.3 * np.std(heart))
        if len(peaks) >= MIN_PEAKS:
            ibi = np.diff(peaks) / FS_RADAR
            ibi = ibi[(ibi > 0.25) & (ibi < 2.0)]
            time_bpm = 60.0 / np.median(ibi) if len(ibi) >= 2 else None
            regularity = ibi.std() / ibi.mean() if len(ibi) >= 2 else 1.0
        else:
            time_bpm, regularity = None, 1.0
        # 时频融合与质量门控
        if freq_bpm and time_bpm:
            gap = abs(freq_bpm - time_bpm)
            fused = (freq_bpm + time_bpm) / 2
        else:
            gap, fused = None, (freq_bpm or time_bpm)
        if gap is None or time_bpm is None:
            quality = 'low'
        elif gap <= GAP_HIGH and regularity < 0.25:
            quality = 'high'
        elif gap <= GAP_MED:
            quality = 'med'
        else:
            quality = 'low'
        rows.append({'win_start_s': i0 / FS_RADAR,
                     'freq_bpm': round(freq_bpm, 1) if freq_bpm else None,
                     'time_bpm': round(time_bpm, 1) if time_bpm else None,
                     'fused_bpm': round(fused, 1) if fused else None,
                     'time_freq_gap_bpm': round(gap, 1) if gap else None,
                     'regularity': round(regularity, 3) if regularity < 1 else None,
                     'n_peaks': len(peaks),
                     'harmonic_corrected': corrected,
                     'quality': quality})
    return rows


def select_top_bins(prof):
    """多 bin 交叉验证候选选择：幅度达标的门中按带内功率取 top N。

    Args:
        prof: 复数距离谱 (n_frames, 64)

    Returns:
        list of int：候选 bin 索引（按带内功率降序，最多 N_BINS 个）
    """
    amp = np.abs(prof).mean(axis=0)
    amp_th = AMP_TH_RATIO * amp[RANGE_BIN_MIN: RANGE_BIN_MAX + 1].max()
    dphi_all = np.diff(np.angle(prof), axis=0)
    freq = np.fft.rfftfreq(dphi_all.shape[0], d=1 / FS_RADAR)
    band = (freq >= 0.15) & (freq <= 2.5)
    scored = []
    for g in range(RANGE_BIN_MIN, RANGE_BIN_MAX + 1):
        if amp[g] < amp_th:
            continue                          # 噪声门排除
        dphi = dphi_all[:, g] - dphi_all[:, g].mean()
        power = np.abs(np.fft.rfft(dphi))[band] ** 2
        scored.append((power.sum(), g))
    scored.sort(reverse=True)
    return [g for _, g in scored[: N_BINS]]


def bin_phase_signal(prof, g):
    """单个 bin 的相位链路：unwrap → 差分 → 0.25s 滑动平均。

    Args:
        prof: 复数距离谱
        g: bin 索引

    Returns:
        phi_s: 平滑相位差信号
    """
    phi = np.angle(prof[:, g])
    dphi = np.diff(np.unwrap(phi))
    win = int(0.25 * FS_RADAR)
    return np.convolve(dphi, np.ones(win) / win, mode='same')


def vote_bins(per_bin_rows):
    """多 bin 投票融合：每窗取各 bin fused 值，找最大共识组取中位。

    共识组 = 两两差 ≤ BIN_AGREE_BPM 的最大子集。组大小 ≥2 视为
    交叉验证通过（多个独立距离门算出一致心率）；组大小 1 标记低置信。

    Args:
        per_bin_rows: list of list，每个 bin 的 window_vitals 输出

    Returns:
        list of dict：投票后的窗口记录（含 vote_bins 共识组大小）
    """
    n_win = len(per_bin_rows[0])
    merged = []
    for wi in range(n_win):
        vals = [b[wi]['fused_bpm'] for b in per_bin_rows
                if b[wi]['fused_bpm'] is not None]
        base = per_bin_rows[0][wi]
        if not vals:
            base['vote_bins'] = 0
            merged.append(base)
            continue
        # 贪心找最大共识组
        vals_s = sorted(vals)
        best_group = [vals_s[0]]
        for v in vals_s[1:]:
            if v - best_group[0] <= BIN_AGREE_BPM:
                best_group.append(v)
        # 重新扫描起点找全局最大组（简化：排序后滑动窗口）
        best_start, best_len = 0, 0
        for i in range(len(vals_s)):
            j = i
            while j < len(vals_s) and vals_s[j] - vals_s[i] <= BIN_AGREE_BPM:
                j += 1
            if j - i > best_len:
                best_len, best_start = j - i, i
        group = vals_s[best_start: best_start + best_len]
        vote = float(np.median(group))
        base['fused_bpm'] = round(vote, 1)
        base['vote_bins'] = len(group)
        base['n_bin_estimates'] = len(vals)
        # 共识组 ≥2 且时频一致 → 升置信；否则降 low
        if len(group) >= 2:
            if base.get('time_freq_gap_bpm') is not None \
                    and base['time_freq_gap_bpm'] <= GAP_MED:
                base['quality'] = 'high' if base['time_freq_gap_bpm'] <= GAP_HIGH \
                    else 'med'
        else:
            base['quality'] = 'low'
        merged.append(base)
    return merged


def process_session(folder: Path):
    """处理单个会话：多 bin 选门 → 逐 bin 窗口估计 → 投票融合 → 金标准对比。

    Args:
        folder: 会话目录路径

    Returns:
        dict：会话级结果（含逐窗口记录）
    """
    rffts, ts = load_radar(folder)
    t_ecg, mv = load_ecg(folder)
    # 通道平均（8 通道相干性未知，先平均幅度最大的通道？直接平均相位不可靠，
    # 这里对复数距离谱先按通道平均再取相位，等效于非相干平均后取主通道）
    prof = np.mean(rffts, axis=1)              # (n_frames, 64) 通道平均
    prof_dyn = prof - prof.mean(axis=0, keepdims=True)   # 静态杂波去除

    # 多 bin 候选选择（带内功率 top N，幅度达标）
    cand_bins = select_top_bins(prof)
    if not cand_bins:
        return {'folder': str(folder), 'n_frames': len(rffts),
                'selected_bin': None, 'windows': [], 'mae_bpm': None}

    # 呼吸率（用主 bin 相位，全长 SOS 带通 + 谱峰）
    phi_s0 = bin_phase_signal(prof, cand_bins[0])
    sos_b = butter(FILT_ORDER, [2 * BREATH_BAND[0] / FS_RADAR,
                                2 * BREATH_BAND[1] / FS_RADAR],
                   btype='bandpass', output='sos')
    breath = sosfiltfilt(sos_b, phi_s0)
    sb = np.abs(np.fft.rfft(breath))
    fb = np.fft.rfftfreq(len(breath), d=1 / FS_RADAR)
    mb = (fb >= 0.15) & (fb <= 0.45)
    breath_bpm = fb[mb][np.argmax(sb[mb])] * 60 if mb.any() else None

    # 注：呼吸谐波陷波（notch_respiration_harmonics）实测净负收益
    # （MAE 9.5→10.4，4 倍谐波与低心率基频重叠时误伤），已停用。
    # 若后续引入金标准引导的谐波-心跳距离保护条件可重新启用。

    # 逐 bin 窗口化估计
    per_bin_rows = [window_vitals(bin_phase_signal(prof, g))
                    for g in cand_bins]

    # 多 bin 投票融合
    rows = vote_bins(per_bin_rows)

    # 时间轨迹连续性修正：与相邻可用窗口中位差 >12 BPM 的孤立跳变
    # 用相邻中位替换（参考一敏 v3.1 置信度加权双向连续轨迹的简化版）
    traj = [r['fused_bpm'] for r in rows]
    for i in range(len(rows)):
        if traj[i] is None:
            continue
        neigh = [traj[j] for j in (i - 1, i + 1)
                 if 0 <= j < len(traj) and traj[j] is not None]
        if neigh and abs(traj[i] - np.median(neigh)) > 12:
            rows[i]['traj_bpm'] = round(float(np.median(neigh)), 1)
        else:
            rows[i]['traj_bpm'] = rows[i]['fused_bpm']
    errs = []
    for r in rows:
        gold = ecg_hr_bpm(t_ecg, mv, r['win_start_s'], r['win_start_s'] + WIN_S)
        r['gold_bpm'] = round(gold, 1) if gold else None
        if gold and r['traj_bpm']:
            errs.append(r['traj_bpm'] - gold)
    errs = np.array(errs)
    return {
        'folder': str(folder),
        'n_frames': len(rffts),
        'selected_bins': cand_bins,
        'selected_range_m': [round(g * 0.3123, 2) for g in cand_bins],
        'breath_bpm': round(breath_bpm, 1) if breath_bpm else None,
        'windows': rows,
        'n_pairs': len(errs),
        'mae_bpm': round(float(np.abs(errs).mean()), 2) if len(errs) else None,
        'rmse_bpm': round(float(np.sqrt((errs ** 2).mean())), 2) if len(errs) else None,
    }


def main():
    """主流程：单会话或 --all 批量，输出 JSON 汇总与图。"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', default='P001/Lying/Rest', help='会话目录（相对数据根）')
    parser.add_argument('--all', action='store_true', help='批量处理全部会话')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.all:
        folders = sorted(p for p in DATA_DIR.glob('P*/**/R*')
                         if p.is_dir() and (p / 'radar_rFFTs.zlib').exists())
    else:
        folders = [DATA_DIR / args.folder]

    summary = []
    for folder in folders:
        try:
            res = process_session(folder)
            summary.append(res)
            qual = [w['quality'] for w in res['windows']]
            n_hi = qual.count('high') + qual.count('med')
            bins = ','.join(str(b) for b in res.get('selected_bins', []))
            print(f"{res['folder']}: 门[{bins}] 呼吸{res['breath_bpm']}"
                  f" 窗口{len(qual)} 可用{n_hi} "
                  f"MAE {res['mae_bpm']} RMSE {res['rmse_bpm']}")
        except Exception as e:
            print(f'[SKIP] {folder}: {type(e).__name__} {str(e)[:100]}')

    out_json = OUTPUT_DIR / ('gold_validation_all.json' if args.all
                             else f'gold_validation_{Path(args.folder).name}.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print(f'[OK] 结果: {out_json}')

    # 汇总图：每会话 MAE（按 quality 分层）
    if len(summary) > 1:
        fig, ax = plt.subplots(figsize=(12, 5))
        mae_all = [s['mae_bpm'] for s in summary if s['mae_bpm'] is not None]
        ax.hist(mae_all, bins=20, edgecolor='k')
        ax.set_xlabel('MAE (BPM)')
        ax.set_ylabel('会话数')
        ax.set_title(f'金标准心率 MAE 分布（{len(mae_all)} 会话，'
                     f'中位 {np.median(mae_all):.1f} BPM）')
        fig.tight_layout()
        out_png = OUTPUT_DIR / 'gold_validation_mae_hist.png'
        fig.savefig(out_png, dpi=150)
        plt.close(fig)
        print(f'[OK] 分布图: {out_png}')


if __name__ == '__main__':
    main()
