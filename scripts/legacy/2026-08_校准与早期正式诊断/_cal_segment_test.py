# -*- coding: utf-8 -*-
"""临时：分段调用 v3.1.1 算法，验证 sub3 各段心率能否锁对 ECG。"""
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import process_vital_signs_v3_1_1 as algo

PARTS = Path(r'E:/FocusWave_3.0.15/03-data/sub-3_/mmwave')
OUT = Path(r'D:/Project/厚粲杯/08_算法/output/20_生理金标准验证/90_历史校准结果/sub3_seg_vmd')
OUT.mkdir(parents=True, exist_ok=True)

# 各段 (帧起点, 帧终点, ECG 真实心率)
SEGS = {
    'rest1':       (397,   29999, 106),
    'deep_breath': (30451, 42327, 111),
    'breath_hold': (42767, 47034, 114),
    'rest2':       (47671, 77306, 106),
}

for seg, (f0, f1, true_hr) in SEGS.items():
    print(f"\n===== {seg} 帧 {f0}~{f1} 真实 {true_hr}bpm =====")
    out_dir = OUT / seg
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        result, waveforms = algo.analyze_long_record(
            parts_dir=PARTS,
            output_dir=out_dir,
            session=f'sub3_{seg}',
            method='vmd_heart',
            pattern='sub-3_mmwave_datacube_part*.npz',
            frame_start=f0,
            frame_end=f1,
            min_range_m=0.3,
            max_range_m=1.5,
        )
        hr = result['heart_rate']
        print(f"  [bins] heart_ch={result['channels'].get('heart')}, heart_bin={result['bins'].get('heart')}")
        print(f"  freq_bpm={hr.get('freq_bpm')}, time_bpm={hr.get('time_bpm')}, fused={hr.get('fused_bpm')}")
        print(f"  信号门控通过={hr.get('self_check',{}).get('signal_quality',{}).get('hard_gate_passed')}")
        print(f"  时频差={hr.get('self_check',{}).get('time_frequency_gap_bpm')}")
    except Exception as e:
        print(f"  [ERROR] {e}")


