# -*- coding: utf-8 -*-
"""
validate_gold_anchor.py — 通用金标准验证 + baseline anchor 法（ECG + RSP 双通道）
============================================================================
对任意正式实验被试（有 Biopac ECG + RSP 呼吸通道 + 毫米波 + events.csv），
一次性输出：
  1. 金标准对照（每段毫米波 HR/BR vs ECG/RSP，全局主频，无锚）
  2. baseline anchor 法（用静息段毫米波自测 HR 做锚，任务段只在锚±margin 内找心跳峰）

这是 validate_9779_gold.py 与 validate_9779_anchor.py 的参数化合并版，
可对 9779 / 97792 / 97793 / 后续任意被试复用。

用法: python validate_gold_anchor.py --subject 97793 [--anchor-margin 15]
输出: output/校准/sub{subject}_gold/gold_validation.csv + anchor_validation.json
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.signal import find_peaks

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import process_vital_signs_v3_1_1 as algo
from process_vital_signs_v3_1_1 import FS, HR_LO_HZ, HR_HI_HZ, BR_LO_HZ, BR_HI_HZ
import gold_standard_qa as gold_qa

ACQ_ROOT = Path(r"D:\acq_mmwave_results")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\校准")

# 呼吸峰值检测参数
RSP_MIN_DIST_S = 0.5          # 呼吸峰最小间距（秒）
RSP_PROMINENCE = 0.2          # 呼吸峰显著度


def read_segments(events_path):
    """读 events.csv，返回 [(段名, start_unix, end_unix)]，按时间排序。
    block3 等「只有 start 无 end」的中断段自动过滤（end=None 不纳入）。"""
    segs = {}
    with open(events_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['event'] == 'segment_start':
                segs.setdefault(row['segment'], []).append(
                    {'start': int(row['unix_ms']), 'end': None})
            elif row['event'] == 'segment_end':
                for s in reversed(segs.get(row['segment'], [])):
                    if s['end'] is None:
                        s['end'] = int(row['unix_ms'])
                        break
    out = []
    for name, lst in segs.items():
        for s in lst:
            if s['start'] is not None and s['end'] is not None:
                out.append((name, s['start'], s['end']))
    return sorted(out, key=lambda x: x[1])


def load_align(acq_path, events_path):
    """marker 对齐，返回 (offset, k, sr, ecg, rsp)。"""
    import bioread
    d = bioread.read_file(str(acq_path))
    sr = d.samples_per_second
    ecg_idx = next(i for i, c in enumerate(d.channels) if 'ECG' in str(c.name).upper())
    rsp_idx = next(i for i, c in enumerate(d.channels) if 'RSP' in str(c.name).upper())
    ecg = np.asarray(d.channels[ecg_idx].data).astype(float)
    rsp = np.asarray(d.channels[rsp_idx].data).astype(float)

    stp = []
    for i, ch in enumerate(d.channels):
        n = str(ch.name)
        if 'STP Input' in n:
            stp.append((int(n.split('STP Input ')[1].split(')')[0]), i))
    stp.sort()
    bits = [(np.asarray(d.channels[i].data) > 2.5).astype(int) for num, i in stp[:8]]
    val = sum(bits[b] * (1 << b) for b in range(8))
    val = np.asarray(val)
    rising = np.where((val[1:] != 0) & (val[:-1] == 0))[0] + 1
    ecg_bounds = [(int(val[r]), int(r)) for r in rising if int(val[r]) < 100]

    with open(events_path, encoding='utf-8-sig') as f:
        bounds = [(int(row['marker']), int(row['unix_ms']))
                  for row in csv.DictReader(f)
                  if row['marker'].strip() and int(row['marker']) < 100]
    a_vals = [m for m, _ in bounds]
    e_vals = [v for v, _ in ecg_bounds]
    best = None
    for j in range(len(a_vals)):
        suffix = a_vals[j:]
        for i in range(len(e_vals) - len(suffix) + 1):
            if e_vals[i:i + len(suffix)] == suffix and (best is None or len(suffix) > best[0]):
                best = (len(suffix), j, i)
    _, j0, i0 = best
    pairs = [(ecg_bounds[i0 + t][1], bounds[j0 + t][1]) for t in range(best[0])]
    idx = np.array([p[0] for p in pairs], float)
    unix = np.array([p[1] for p in pairs], float)
    k, offset = np.polyfit(idx, unix, 1)
    resid = np.max(np.abs(unix - (offset + k * idx)))
    print(f"[align] {len(pairs)} 个 marker, k={k:.6f}, 残差 max={resid:.2f}ms")
    return offset, k, sr, ecg, rsp


def ecg_hr_segment(ecg, sr, t0_unix, t1_unix, offset, k):
    """ECG 段内心率，接入质量检测 + 伪迹排除。返回 (hr, report)。"""
    i0 = int((t0_unix - offset) / k)
    i1 = int((t1_unix - offset) / k)
    return gold_qa.ecg_qa(ecg, sr, i0, i1)


def rsp_br_segment(rsp, sr, t0_unix, t1_unix, offset, k):
    """RSP 段内呼吸率，接入质量检测 + 伪迹排除。返回 (br, report)。"""
    i0 = int((t0_unix - offset) / k)
    i1 = int((t1_unix - offset) / k)
    return gold_qa.rsp_qa(rsp, sr, i0, i1)


def load_mm_segment(mm_dir, prefix, f0, f1):
    """加载毫米波段数据：选 bin + 提取呼吸/心跳位移。

    返回 (disp_br, disp_hr, n, qa) 或 None。
    qa 含选 bin 的质量指标（hr_snr / phase_stability / 幅度 CV），供毫米波质量门控用。
    """
    npz_files = algo.collect_npz_parts(mm_dir, pattern=f'{prefix}_datacube_part*.npz')
    ch_power, bin_power_acc, _ = algo.accumulate_range_profile(
        npz_files, frame_start=f0, frame_end=f1)
    iq_sample = next(algo._iter_selected_chunks(npz_files, frame_start=f0, frame_end=f1), None)
    if iq_sample is None:
        return None
    iq_fd = algo._as_range_cube(iq_sample)
    gate = algo._distance_gate_to_bin_mask(bin_power_acc.shape[0], 0.3, 1.5, 0.08, 0.0)
    bpa = np.array(bin_power_acc, copy=True)
    bpa[~gate, :] = 0.0
    br_ch, br_bin, hr_ch, hr_bin, summaries = algo.select_separate_channels_bins(
        bpa, iq_fd, iq_sample.shape[0])
    # 取选中心跳 bin 的质量指标
    hr_summary = max(summaries, key=lambda s: s["best_hr_selection_score"])
    qa = {
        'hr_ch': hr_ch, 'hr_bin': hr_bin,
        'hr_snr': hr_summary.get('best_hr_snr'),
        'hr_phase_stability': hr_summary.get('best_hr_phase_stability'),
    }
    disp_br, disp_hr, n = algo.extract_displacement_separate(
        npz_files, br_ch, br_bin, hr_ch, hr_bin, frame_start=f0, frame_end=f1)
    if n < FS * 10:
        return None
    return disp_br, disp_hr, n, qa


def hr_from_disp(disp_hr, anchor_bpm=None, margin=15.0):
    """从心跳位移序列提取 HR（可选 anchor 窄带）。

    返回 (hr_bpm, qa_dict)。qa_dict 含时频一致性、主峰 SNR、峰值数，
    供毫米波质量门控用（与金标准清洗对称）。
    """
    qa = {'hr_freq_bpm': None, 'hr_time_bpm': None, 'n_peaks': 0,
          'time_freq_gap_bpm': None, 'heart_band_snr_db': None}

    hr_bp = algo._sos_bandpass(disp_hr, HR_LO_HZ, HR_HI_HZ)
    freqs = np.fft.rfftfreq(len(hr_bp), d=1 / FS)
    _, pxx = signal.periodogram(hr_bp, fs=FS, window='hann')

    # 心跳带 SNR：主峰功率 / 心跳带内噪声底（文献 3dB 门控）
    hr_mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    pxx_hr = pxx[hr_mask]
    if len(pxx_hr) > 0 and np.median(pxx_hr) > 0:
        qa['heart_band_snr_db'] = round(float(10 * np.log10(
            np.max(pxx_hr) / np.median(pxx_hr))), 2)

    if anchor_bpm is not None:
        lo_hz = max(HR_LO_HZ, (anchor_bpm - margin) / 60.0)
        hi_hz = min(HR_HI_HZ, (anchor_bpm + margin) / 60.0)
    else:
        lo_hz, hi_hz = HR_LO_HZ, HR_HI_HZ
    mask = (freqs >= lo_hz) & (freqs <= hi_hz)
    if not np.any(mask):
        return None, qa
    hr_freq = freqs[mask][np.argmax(pxx[mask])]
    qa['hr_freq_bpm'] = round(float(hr_freq * 60), 1)

    # 窄带逐拍
    lo, hi = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
    sos = signal.butter(4, [lo, hi], btype='band', fs=FS, output='sos')
    xn = signal.sosfiltfilt(sos, hr_bp)
    ref = 1.0 / hr_freq
    peaks = []
    i = 0
    while i < len(xn):
        lo_i, hi_i = int(i + 0.75 * ref * FS), min(int(i + 1.35 * ref * FS), len(xn))
        if lo_i >= len(xn) or hi_i <= lo_i:
            break
        p = lo_i + np.argmax(xn[lo_i:hi_i])
        peaks.append(p)
        i = p + 1
    qa['n_peaks'] = len(peaks)

    if len(peaks) < 5:
        hr = hr_freq * 60
    else:
        ibi = np.diff(peaks) / FS * 1000
        ibi = ibi[(ibi >= 300) & (ibi <= 2000)]
        hr = (60000 / np.median(ibi)) if len(ibi) >= 3 else (hr_freq * 60)
    qa['hr_time_bpm'] = round(float(hr), 1)
    # 时频一致性：逐拍 HR 与 periodogram 主频差
    if qa['hr_time_bpm'] is not None and qa['hr_freq_bpm'] is not None:
        qa['time_freq_gap_bpm'] = round(abs(qa['hr_time_bpm'] - qa['hr_freq_bpm']), 1)
    return hr, qa


def extract_hr_br(disp_br, disp_hr, anchor_bpm=None, margin=15.0):
    """从已加载的位移序列提取 (HR, BR)。HR 可选 anchor 窄带，BR 用呼吸主频。"""
    br_bp = algo._sos_bandpass(disp_br, BR_LO_HZ, BR_HI_HZ)
    br_freq = algo.estimate_freq_periodogram(br_bp, BR_LO_HZ, BR_HI_HZ)
    br = br_freq * 60 if br_freq else None
    hr, qa = hr_from_disp(disp_hr, anchor_bpm=anchor_bpm, margin=margin)
    return hr, br, qa


# ── 毫米波质量门控阈值（文献标准）───────────────────────────
MM_SNR_MIN_DB = 3.0             # 心跳带主峰 SNR 下限（专利 US20220175314A1，约 3dB）
MM_PHASE_STABILITY_MIN = 0.5    # 相位稳定性下限（主线选 bin 打分，粗糙判据）
MM_TIME_FREQ_GAP_MAX = 10.0     # 时频一致性上限（专家建议：差 >10 bpm 判不可信）


def mm_hr_usable(qa_bin, qa_hr):
    """毫米波心率质量门控判定，返回 (usable, 拒绝原因)。

    依据（文献/主线）:
    - 心跳带 SNR < 3dB → 信号太弱，不可信（专利 US20220175314A1）
    - 相位稳定性 < 0.5 → 选 bin 粗糙，不可信（主线选 bin 打分）
    - 时频差 > 10 bpm → 时频不一致，不可信（专家 08-15 建议）
    """
    reasons = []
    if qa_bin.get('hr_snr') is not None and qa_bin['hr_snr'] < 1.0:
        # hr_snr 是线性比值，3dB ≈ 2 倍；这里用 <1 即主峰不比噪声中位数强
        reasons.append('hr_snr_low')
    if qa_bin.get('hr_phase_stability') is not None and \
            qa_bin['hr_phase_stability'] < MM_PHASE_STABILITY_MIN:
        reasons.append('phase_stability_low')
    if qa_hr.get('heart_band_snr_db') is not None and \
            qa_hr['heart_band_snr_db'] < MM_SNR_MIN_DB:
        reasons.append('heart_band_snr_low')
    if qa_hr.get('time_freq_gap_bpm') is not None and \
            qa_hr['time_freq_gap_bpm'] > MM_TIME_FREQ_GAP_MAX:
        reasons.append('time_freq_mismatch')
    return (len(reasons) == 0, reasons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subject', default='97793')
    ap.add_argument('--anchor-margin', type=float, default=15.0)
    args = ap.parse_args()
    sub = args.subject

    data_root = ACQ_ROOT / f'sub-{sub}_'
    # acq 文件名不总等于目录编号（如 sub-97994_ 下是 97794.acq），glob 查找而非硬拼
    acq_files = list(data_root.glob('*.acq'))
    if not acq_files:
        print(f"[ERROR] 找不到 acq 文件: {data_root}")
        return
    acq_path = acq_files[0]
    events_path = data_root / 'beh' / 'events.csv'
    mm_dir = data_root / 'mmwave'
    prefix = f'sub-{sub}_mmwave'
    out_dir = OUT_ROOT / f'sub{sub}_gold'
    out_dir.mkdir(parents=True, exist_ok=True)

    offset, k, sr, ecg, rsp = load_align(acq_path, events_path)
    seg_list = read_segments(events_path)
    ts = np.loadtxt(mm_dir / f'{prefix}_timestamps.csv', delimiter=',')[:, 2]
    print(f"[seg] {len(seg_list)} 个完整段")

    # baseline 段锚
    baseline = next(s for s in seg_list if s[0] == 'baseline')
    t0, t1 = baseline[1], baseline[2]
    f0 = int(np.searchsorted(ts, t0)); f1 = int(np.searchsorted(ts, t1)) - 1
    b_disp = load_mm_segment(mm_dir, prefix, f0, f1)
    baseline_hr, baseline_hr_qa = hr_from_disp(b_disp[1], anchor_bpm=None) if b_disp else (None, {})
    baseline_usable, baseline_reasons = mm_hr_usable(b_disp[3], baseline_hr_qa) if b_disp else (False, ['no_disp'])
    baseline_gold, baseline_gold_rep = ecg_hr_segment(ecg, sr, t0, t1, offset, k)
    _, baseline_rsp_rep = rsp_br_segment(rsp, sr, t0, t1, offset, k)
    anchor = baseline_hr if baseline_hr else baseline_gold
    print(f"[baseline] 毫米波自测 {baseline_hr:.1f} bpm, ECG {baseline_gold:.1f} bpm")
    print(f"[baseline毫米波质量] 可用={baseline_usable}, SNR={baseline_hr_qa.get('heart_band_snr_db')}dB, "
          f"相位稳定={b_disp[3]['hr_phase_stability'] if b_disp else 'NA'}, "
          f"时频差={baseline_hr_qa.get('time_freq_gap_bpm')}bpm, 拒绝={baseline_reasons}")
    print(f"[baseline质量] ECG可用={baseline_gold_rep['usable']}(正常RR比例{baseline_gold_rep['valid_ratio']:.0%}, 拒{baseline_gold_rep['n_ibi_range_rejected']}+{baseline_gold_rep['n_pc_rejected']}), "
          f"RSP可用={baseline_rsp_rep['usable']}(正常周期比例{baseline_rsp_rep['valid_ratio']:.0%}, 幅度{baseline_rsp_rep['amp']})")
    print(f"[anchor] {anchor:.1f} bpm (margin ±{args.anchor_margin})\n")

    print(f"{'段':12s} {'ECG':>7s} {'RSP':>7s} {'mm无锚':>7s} {'mm有锚':>7s} "
          f"{'HR误差':>7s} {'mmBR':>7s} {'BR误差':>7s} {'ECG用':>5s} {'RSP用':>5s} {'mm用':>5s} {'mm拒':>8s}")
    rows = []
    for name, t0, t1 in seg_list:
        if name == 'baseline':
            continue
        f0 = int(np.searchsorted(ts, t0)); f1 = int(np.searchsorted(ts, t1)) - 1
        gold_hr, ecg_rep = ecg_hr_segment(ecg, sr, t0, t1, offset, k)
        gold_br, rsp_rep = rsp_br_segment(rsp, sr, t0, t1, offset, k)
        d = load_mm_segment(mm_dir, prefix, f0, f1)
        if d is None:
            hr_no = hr_an = br = None
            mm_usable = False
            mm_reasons = ['no_disp']
        else:
            hr_no, br, qa_no = extract_hr_br(d[0], d[1], anchor_bpm=None)
            hr_an, _, qa_an = extract_hr_br(d[0], d[1], anchor_bpm=anchor, margin=args.anchor_margin)
            mm_usable, mm_reasons = mm_hr_usable(d[3], qa_an)
        hr_err = (hr_an - gold_hr) if (hr_an and gold_hr) else None
        br_err = (br - gold_br) if (br and gold_br) else None
        print(f"{name:12s} {gold_hr if gold_hr else 0:7.1f} "
              f"{gold_br if gold_br else 0:7.1f} "
              f"{hr_no if hr_no else 0:7.1f} {hr_an if hr_an else 0:7.1f} "
              f"{hr_err if hr_err is not None else 0:7.1f} "
              f"{br if br else 0:7.1f} "
              f"{br_err if br_err is not None else 0:7.1f} "
              f"{str(ecg_rep['usable']):>5s} {str(rsp_rep['usable']):>5s} "
              f"{str(mm_usable):>5s} {str(mm_reasons if mm_reasons else ''):>8s}")
        rows.append({'segment': name, 'ecg_hr': round(gold_hr, 1) if gold_hr else None,
                     'rsp_br': round(gold_br, 2) if gold_br else None,
                     'mm_hr_noanchor': round(hr_no, 1) if hr_no else None,
                     'mm_hr_anchor': round(hr_an, 1) if hr_an else None,
                     'mm_br': round(br, 2) if br else None,
                     'hr_err_anchor': round(hr_err, 1) if hr_err else None,
                     'br_err': round(br_err, 1) if br_err else None,
                     'ecg_usable': ecg_rep['usable'],
                     'ecg_valid_ratio': round(ecg_rep['valid_ratio'], 3),
                     'rsp_usable': rsp_rep['usable'],
                     'rsp_valid_ratio': round(rsp_rep['valid_ratio'], 3),
                     'mm_usable': mm_usable,
                     'mm_reject_reasons': mm_reasons})

    json_path = out_dir / 'gold_anchor_validation.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'subject': sub, 'baseline_anchor_bpm': round(anchor, 1),
                   'margin': args.anchor_margin, 'segments': rows},
                  f, ensure_ascii=False, indent=2)
    print(f"\n[out] {json_path}")


if __name__ == '__main__':
    main()
