import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts/maintenance'
sys.path.insert(0, str(SCRIPTS))
import mmwave_frozen_cohort as runner
import run_mmwave_probe_merge_ready_20260831 as adapter


def row():
    return dict(repeat_participant_id='R1', session_id='sub-1', block_id='block-1',
                probe_id='probe-01', window_name='pre_30s', window_start_unix_ms='0',
                window_effective_start_unix_ms='0', window_end_unix_ms='30000', probe_onset_unix_ms='30000')


def test_block_clip_and_identity():
    source = dict(row(), mmwave_hr_fused_bpm_median='999')
    result, known = runner.canonical_row(source, {'block-1':1000})
    assert known and result['window_effective_start_unix_ms'] == '1000'
    assert result['window_truncated_by_block_start'] == 'True'
    assert 'mmwave_hr_fused_bpm_median' not in result
    assert all(result[k] == source[k] for k in runner.KEYS)
    assert runner.canonical_row(source, {})[1] is False


def test_keys_fail_closed():
    with pytest.raises(ValueError):
        runner.validate_rows([row(), row()])
    with pytest.raises(ValueError):
        runner.validate_rows([dict(row(), repeat_participant_id='')])


def test_block_stop_is_exported_and_required():
    result, known = runner.canonical_row(row(), {'block-1':1000}, {'block-1':31000})
    assert known and result['block_end_unix_ms'] == '31000'
    assert runner.canonical_row(row(), {'block-1':1000}, {})[1] is False
    assert runner.canonical_row(row(), {'block-1':1000}, {'block-1':29000})[1] is False


def test_block_stop_from_real_event_schema(tmp_path):
    path=tmp_path/'timeline.csv'
    path.write_text('event,detail,unix_ms\nblock_start,Block1_B,1000\nblock_stop,Block1_B,31000\n',encoding='utf-8')
    assert runner.block_starts(path) == {'block-1':1000}
    assert runner.block_starts(path,'block_stop') == {'block-1':31000}


def test_exclusive_end_effective_start_and_producer_summaries(monkeypatch):
    timestamps = np.column_stack([np.arange(3002)]*2 + [np.arange(3002)*10])
    captured = {}
    def sliced(files, lo, hi):
        captured['slice'] = (lo, hi)
        return np.ones((hi-lo,2,1), dtype=complex)
    monkeypatch.setattr(adapter, 'slice_iq', sliced)
    def course(*args, **kwargs):
        captured['length'] = len(args[0])
        return dict(freq_median_bpm=71.0, time_median_bpm=72.0, fused_median_bpm=73.0,
                    points=[dict(confidence=.2),dict(confidence=.6)], signal_quality=dict(usable_ratio=.5))
    algo = SimpleNamespace(_as_range_cube=lambda x:x,
        select_separate_channels_bins=lambda *a:(0,0,0,0,None),
        extract_displacement=lambda x,*a:np.arange(len(x),dtype=float),
        _sos_bandpass=lambda x,*a:x, HR_LO_HZ=.8, HR_HI_HZ=2., HR_LO_BPM=48, HR_HI_BPM=120,
        detect_peaks_heart_lo=lambda *a,**k:np.array([],dtype=int), estimate_hr_time_course=course,
        WAVELENGTH_MM=4., _select_breath_candidate=lambda x:(None,.2,None,None),
        _phase_stability_score=lambda x:(.9,None))
    result = adapter.process_probe(algo, dict(row(), window_effective_start_unix_ms='1000'), [], timestamps, {})
    assert captured == {'slice':(100,3000), 'length':2900}
    assert result['mmwave_hr_fused_bpm_median'] == 73.
    assert result['mmwave_hr_usable_window_fraction'] == .5
    assert result['mmwave_hr_mean_confidence'] == .4
    assert result['mmwave_rmssd_ms'] is None


def test_npz_mapping_and_slice(tmp_path):
    path = tmp_path/'cube.npz'
    np.savez(path, tx0=np.ones((10,2)), tx1=np.zeros((10,2)))
    cube = runner.IndexedCube([path], 10)
    assert cube.slice(2,5).shape == (3,2,2)
    assert cube.last_slice_hash
    with pytest.raises(ValueError):
        runner.IndexedCube([path], 9)
