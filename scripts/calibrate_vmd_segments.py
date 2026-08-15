# -*- coding: utf-8 -*-
"""
calibrate_vmd_segments.py — 毫米波×ECG 分段校准（v3.1.1 vmd_heart 主线）
========================================================================
对每个校准场次的每个段，用 v3.1.1 主线的 vmd_heart 方法提取毫米波心率，
与 ECG 金标准心率对比，验证呼吸引导 VMD 能否修好单 bin 方法的锁错问题。

流程（每场每段）:
  1. 读 events.csv → 段边界 unix_ms
  2. 读 timestamps.csv → unix_ms 映射到全局帧索引
  3. 调 v3_1_1.analyze_long_record(method='vmd_heart', frame_start/end)
  4. 读 .acq → 段内 ECG 心率（R 峰 prominence 检测）
  5. 输出对比表

用法:
  python calibrate_vmd_segments.py --subject sub3

依赖: numpy, scipy, bioread, vmdpy, process_vital_signs_v3_1_1
"""
import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import process_vital_signs_v3_1_1 as algo

DATA_ROOT = Path(r"D:\acq_mmwave_results")
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\校准\vmd_segments")

SUBJECTS = {
    'sub2': {'acq': 'sub-2_/sub2.acq', 'dir': 'sub-2_/mmwave',
             'events': 'sub-2_/cal/events.csv', 'prefix': 'sub-2_mmwave'},
    'sub3': {'acq': 'sub-3_/sub3.acq', 'dir': 'sub-3_/mmwave',
             'events': 'sub-3_/cal/events.csv', 'prefix': 'sub-3_mmwave'},
    'sub4': {'acq': 'sub-4_/sub4.acq', 'dir': 'sub-4_/mmwave',
             'events': 'sub-4_/cal/events.csv', 'prefix': 'sub-4_mmwave'},
}

# 段首尾裁剪（秒）：去掉段开头进入状态的过渡 + 抬手伪迹，结尾的松懈。
# ECG 与毫米波同步裁剪同一窗口，保证对比公平。呼吸段(deep_breath)开头
# 被试需几秒跟上节奏、静息段开头有抬手动作，故首裁剪 15s；尾裁剪 5s。
HEAD_TRIM_S = 15.0
TAIL_TRIM_S = 5.0


def read_segments(events_path):
    """读 events.csv，返回 [(段名, start_unix, end_unix)]，按时间排序。"""
    segs = {}
    with open(events_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['event'] == 'segment_start':
                segs.setdefault(row['segment'], {})['start'] = int(row['unix_ms'])
            elif row['event'] == 'segment_end':
                segs.setdefault(row['segment'], {})['end'] = int(row['unix_ms'])
    out = []
    for name, b in segs.items():
        if 'start' in b and 'end' in b:
            out.append((name, b['start'], b['end']))
    return sorted(out, key=lambda x: x[1])


def read_timestamps(mm_dir, prefix):
    ts = np.loadtxt(mm_dir / f'{prefix}_timestamps.csv', delimiter=',')
    return ts[:, 2]  # 第3列 Python unix_ms


def ecg_hr_segment(acq_path, sr, t0_unix, t1_unix, align_offset, align_k):
    """ECG 段内心率（prominence R 峰检测）。align: unix = offset + k*idx"""
    import bioread
    d = bioread.read_file(acq_path)
    # 找 ECG 通道（名字含 ECG）
    ecg_idx = next(i for i, c in enumerate(d.channels) if 'ECG' in str(c.name).upper())
    ecg = np.asarray(d.channels[ecg_idx].data).astype(float)
    i0 = int((t0_unix - align_offset) / align_k)
    i1 = int((t1_unix - align_offset) / align_k)
    seg = ecg[i0:i1] - np.median(ecg[i0:i1])
    peaks, _ = find_peaks(seg, distance=int(0.3 * sr), prominence=0.25)
    if len(peaks) < 5:
        return None
    ibi = np.diff(peaks) / sr * 1000
    ibi = ibi[(ibi >= 400) & (ibi <= 2000)]
    return round(60000 / np.median(ibi), 1) if len(ibi) >= 3 else None


def ecg_align(acq_path, events_path):
    """用段边界 marker 对齐 acq 数字通道和 events unix_ms，返回 (offset, k)。"""
    import bioread
    d = bioread.read_file(acq_path)
    sr = d.samples_per_second
    # 数字通道（STP Input 0~7）
    stp = []
    for i, c in enumerate(d.channels):
        n = str(c.name)
        if 'STP Input' in n:
            stp.append((int(n.split('STP Input ')[1].split(')')[0]), i))
    stp.sort()
    bits = [(np.asarray(d.channels[i].data) > 2.5).astype(int) for _, i in stp[:8]]
    val = sum(bits[b] * (1 << b) for b in range(8))
    val = np.asarray(val)
    rising = np.where((val[1:] != 0) & (val[:-1] == 0))[0] + 1
    ecg_bounds = [(int(val[r]), int(r)) for r in rising if val[r] < 100]

    with open(events_path, encoding='utf-8-sig') as f:
        bounds = [(int(row['marker']), int(row['unix_ms']))
                  for row in csv.DictReader(f)
                  if row['marker'].strip() and int(row['marker']) < 100]
    a_vals = [m for m, _ in bounds]
    e_vals = [v for v, _ in ecg_bounds]
    # 允许 acq 只含 events 序列的后缀（append 段起点可能晚于 calibration_start，
    # 导致开头的 marker 1 缺失）。找 events 序列里能完整对上的最长后缀。
    best = None   # (后缀长度, events起始j, ecg起始i)
    for j in range(len(a_vals)):
        suffix = a_vals[j:]
        for i in range(len(e_vals) - len(suffix) + 1):
            if e_vals[i:i + len(suffix)] == suffix:
                if best is None or len(suffix) > best[0]:
                    best = (len(suffix), j, i)
    if best is None or best[0] < 2:
        raise ValueError(f"marker 值序列未匹配 (acq={e_vals}, events={a_vals})")
    _, j0, i0 = best
    pairs = [(ecg_bounds[i0 + k][1], bounds[j0 + k][1])
             for k in range(best[0])]
    idx = np.array([p[0] for p in pairs], float)
    unix = np.array([p[1] for p in pairs], float)
    k, offset = np.polyfit(idx, unix, 1)
    resid = np.max(np.abs(unix - (offset + k * idx)))
    print(f"[align] 用 {len(pairs)} 个 marker 对齐，残差 max={resid:.2f}ms")
    return offset, k, sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subject', default='sub3', choices=list(SUBJECTS))
    args = ap.parse_args()
    cfg = SUBJECTS[args.subject]

    acq_path = DATA_ROOT / cfg['acq']
    mm_dir = DATA_ROOT / cfg['dir']
    events_path = DATA_ROOT / cfg['events']

    segs = read_segments(events_path)
    offset, k, sr = ecg_align(acq_path, events_path)
    unix = read_timestamps(mm_dir, cfg['prefix'])
    print(f"[{args.subject}] 对齐 offset={offset:.0f}ms, k={k:.6f}, 段数={len(segs)}")

    results = []
    for name, t0, t1 in segs:
        # 跳过运动段（毫米波运动伪影下无法测心率，已从协议移除）
        if name == 'exercise':
            print(f"\n[{name}] 跳过（运动段，不作校准）")
            continue
        # 段首尾裁剪：ECG 和毫米波都用 [t0+HEAD, t1-TAIL]
        tc0 = t0 + HEAD_TRIM_S * 1000
        tc1 = t1 - TAIL_TRIM_S * 1000
        if tc1 - tc0 < 30 * 1000:  # 裁剪后不足 30s 的段（如屏息 45s）减少裁剪
            tc0 = t0 + 5 * 1000
            tc1 = t1 - 3 * 1000
        # ECG 心率
        ecg_hr = ecg_hr_segment(acq_path, sr, tc0, tc1, offset, k)
        # 毫米波帧区间
        f0 = int(np.searchsorted(unix, tc0))
        f1 = int(np.searchsorted(unix, tc1)) - 1
        print(f"\n[{name}] 帧 {f0}~{f1} (裁剪后 {(tc1-tc0)/1000:.0f}s), ECG={ecg_hr}bpm")

        out_dir = OUT_ROOT / args.subject / name
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            result, _ = algo.analyze_long_record(
                parts_dir=mm_dir, output_dir=out_dir,
                session=f'{args.subject}_{name}', method='vmd_heart',
                pattern=f'{cfg["prefix"]}_datacube_part*.npz',
                frame_start=f0, frame_end=f1,
                min_range_m=0.3, max_range_m=1.5)
            hr = result['heart_rate']
            mm_freq = hr.get('freq_bpm')
            mm_time = hr.get('time_bpm')
            mm_fused = hr.get('fused_bpm')
            gate = hr.get('self_check', {}).get('signal_quality', {}).get('hard_gate_passed')
            gap = hr.get('self_check', {}).get('time_frequency_gap_bpm')
            print(f"  mmWave freq={mm_freq} time={mm_time} fused={mm_fused} gate={gate} 时频差={gap}")
            results.append({'segment': name, 'ecg_hr': ecg_hr,
                            'mm_freq': mm_freq, 'mm_time': mm_time, 'mm_fused': mm_fused,
                            'gate_passed': gate, 'gap_bpm': gap})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({'segment': name, 'ecg_hr': ecg_hr, 'error': str(e)})

    print("\n===== 汇总 =====")
    for r in results:
        if 'error' in r:
            print(f"{r['segment']}: ECG={r['ecg_hr']}  ERROR={r['error']}")
        else:
            err = abs(r['mm_fused'] - r['ecg_hr']) if r['mm_fused'] and r['ecg_hr'] else None
            print(f"{r['segment']}: ECG={r['ecg_hr']}bpm  mm={r['mm_fused']}bpm  "
                  f"误差={round(err,1) if err else 'NA'}bpm  gate={r['gate_passed']}")


if __name__ == '__main__':
    main()
