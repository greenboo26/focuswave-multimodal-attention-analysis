"""Parameterized, exclusive-output replay of a frozen merge-ready cohort.

The old table supplies keys/timeline only, never feature values. No identity is
inferred and no raw directory outside the frozen session list is included.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import run_mmwave_probe_merge_ready_20260831 as adapter

KEYS = ('repeat_participant_id', 'session_id', 'block_id', 'probe_id', 'window_name')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_rows(rows):
    keys = [tuple(r.get(k, '') for k in KEYS) for r in rows]
    if not keys or any(not all(k) for k in keys) or len(set(keys)) != len(keys):
        raise ValueError('Empty/duplicate frozen cohort keys')
    for row in rows:
        if row['window_name'] != 'pre_30s' or int(row['window_end_unix_ms']) != int(row['probe_onset_unix_ms']):
            raise ValueError('Unsupported window contract')


def block_starts(path, event='block_start'):
    result = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if row['event'] != event:
                continue
            match = re.fullmatch(r'Block(\d+)_B', row['detail'])
            if match:
                key = 'block-' + match[1]
                if key in result:
                    raise ValueError('Duplicate block marker')
                result[key] = int(row['unix_ms'])
    return result


def canonical_row(row, starts, ends=None):
    # Frozen identity and non-mmWave columns are retained, including missing rows.
    out = {k: v for k, v in row.items() if not k.startswith('mmwave_')}
    start = int(row['window_start_unix_ms'])
    end = int(row['window_end_unix_ms'])
    if end - start != 30000:
        raise ValueError('Nominal window is not pre_30s')
    block = starts.get(row['block_id'])
    if block is None:
        return out, False
    effective = max(start, block)
    if effective >= end:
        raise ValueError('Probe precedes block start')
    if ends is not None:
        stop = ends.get(row['block_id'])
        if stop is None or end > stop:
            return out, False
        out['block_end_unix_ms'] = str(stop)
    out.update(block_start_unix_ms=str(block), window_effective_start_unix_ms=str(effective),
               window_truncated_by_block_start=str(effective > start),
               window_boundary_source='beh/master_timeline.csv:block_start')
    return out, True


class IndexedCube:
    """Read headers once and decompress only files intersecting a probe."""
    def __init__(self, files, timestamp_count):
        self.entries = []
        self.last_slice_hash = None
        cursor = 0
        expected_keys = None
        for path in files:
            shapes = {}
            with zipfile.ZipFile(path) as z:
                for name in sorted(z.namelist()):
                    if not name.startswith('tx') or not name.endswith('.npy'):
                        continue
                    with z.open(name) as f:
                        version = np.lib.format.read_magic(f)
                        if version == (1, 0):
                            shape, _, _ = np.lib.format.read_array_header_1_0(f)
                        elif version == (2, 0):
                            shape, _, _ = np.lib.format.read_array_header_2_0(f)
                        else:
                            raise ValueError(f'Unsupported NPY header {version}')
                    shapes[name[:-4]] = shape
            keys = tuple(shapes)
            if not keys or (expected_keys is not None and expected_keys != keys):
                raise ValueError('Inconsistent cube channels')
            expected_keys = keys
            n = shapes[keys[0]][0]
            if any(shape != shapes[keys[0]] for shape in shapes.values()):
                raise ValueError('Channel shape mismatch')
            self.entries.append((path, cursor, cursor+n, keys))
            cursor += n
        if cursor != timestamp_count:
            raise ValueError(f'NPZ/timestamp count mismatch: {cursor}/{timestamp_count}')

    def slice(self, start, end):
        chunks = []
        for path, lo, hi, keys in self.entries:
            if hi <= start:
                continue
            if lo >= end:
                break
            with np.load(path) as z:
                chunks.append(np.stack([z[k][max(0,start-lo):min(hi-lo,end-lo)] for k in keys], axis=-1).astype(np.complex64))
        result = np.concatenate(chunks)
        if len(result) != end-start:
            raise ValueError('Incomplete cube slice')
        self.last_slice_hash = hashlib.sha256(result.tobytes()).hexdigest()
        return result


def missing(row, state, reason, observed=False):
    return dict(row, mmwave_state=state, mmwave_observed=observed,
                mmwave_loadable=False, mmwave_missing_reason=reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--raw-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--sessions', nargs='+', help='Explicit smoke subset only; never rewrites full run')
    args = parser.parse_args()
    freeze = json.loads(args.freeze.read_text(encoding='utf-8'))
    old_hash = sha(args.baseline)
    if not any(Path(r['path']).resolve() == args.baseline.resolve() and r['sha256'] == old_hash for r in freeze['baseline']):
        raise ValueError('Baseline differs from frozen source')
    with args.baseline.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    validate_rows(rows)
    if args.sessions:
        if not set(args.sessions) <= {r['session_id'] for r in rows}:
            raise ValueError('Smoke session outside frozen cohort')
        rows = [r for r in rows if r['session_id'] in args.sessions]
    if args.output_dir.exists():
        raise FileExistsError('Existing run directory protected')
    source_files = [Path(__file__), Path(adapter.__file__), adapter.PRODUCER]
    source_hashes = {str(p.relative_to(adapter.ALGO_ROOT)): sha(p) for p in source_files}
    commit = subprocess.check_output(['git','-C',str(adapter.ALGO_ROOT),'rev-parse','HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git','-C',str(adapter.ALGO_ROOT),'status','--porcelain'], text=True)
    algo = adapter.load_module(adapter.PRODUCER, 'frozen_probe_producer')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    out_rows, audit, source_inputs = [], [], []
    original_slice = adapter.slice_iq
    for session in sorted({r['session_id'] for r in rows}):
        session_rows = [r for r in rows if r['session_id'] == session]
        root = args.raw_root / (session+'_')
        timeline = root/'beh/master_timeline.csv'
        starts = block_starts(timeline) if timeline.exists() else {}
        ends = block_starts(timeline, 'block_stop') if timeline.exists() else {}
        if timeline.exists():
            source_inputs.append(dict(path=str(timeline), sha256=sha(timeline)))
        timestamps = cube = None
        reason = None
        try:
            timestamps = adapter.load_timestamps(root/'mmwave')
            if np.any(np.diff(timestamps[:,2]) < 0) or np.any(np.diff(timestamps[:,0]) <= 0):
                raise ValueError('Nonmonotonic time or duplicate/reordered frame index')
            files = adapter.load_npz_files(root/'mmwave', session)
            cube = IndexedCube(files, len(timestamps))
            ts_path = next((root/'mmwave').glob('*_mmwave_timestamps.csv'))
            source_inputs.append(dict(path=str(ts_path), sha256=sha(ts_path)))
            adapter.slice_iq = lambda files, lo, hi: cube.slice(lo, hi)
        except (FileNotFoundError, ValueError) as exc:
            reason = f'{type(exc).__name__}:{exc}'
        for row in session_rows:
            base, boundary_known = canonical_row(row, starts, ends)
            item = {k:row[k] for k in KEYS}
            item.update(boundary_known=boundary_known, truncated=boundary_known and int(base['window_effective_start_unix_ms']) > int(base['window_start_unix_ms']),
                        old_endpoint_hit=bool(timestamps is not None and np.any(timestamps[:,2] == int(row['window_end_unix_ms']))))
            if timestamps is not None and boundary_known:
                lo, hi = np.searchsorted(timestamps[:,2], [int(base['window_effective_start_unix_ms']),int(base['window_end_unix_ms'])], side='left')
                item['frame_index_gap_count'] = int(np.count_nonzero(np.diff(timestamps[lo:hi,0]) != 1))
            if reason:
                out = missing(base, 'STRUCTURAL_MISSING' if timestamps is None else 'QC_FAIL', reason, timestamps is not None)
            elif not boundary_known:
                out = missing(base, 'UNRESOLVED', 'block_boundary_unverified', False)
            else:
                cube.last_slice_hash = None
                out = adapter.process_probe(algo, base, files, timestamps, {})
                item['input_slice_sha256'] = cube.last_slice_hash
            out.update(mmwave_source_run_id=args.run_id, mmwave_source_commit=commit)
            out_rows.append(out)
            audit.append(item)
        print(f'{session}: {len(session_rows)} probes; {reason or "processed"}', flush=True)
    adapter.slice_iq = original_slice
    validate_rows(out_rows)
    if {tuple(r[k] for k in KEYS) for r in out_rows} != {tuple(r[k] for k in KEYS) for r in rows}:
        raise ValueError('Cohort changed')
    out_csv = args.output_dir / args.baseline.name
    with out_csv.open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        writer.writeheader()
        writer.writerows(out_rows)
    with (args.output_dir/'probe_audit.json').open('x', encoding='utf-8') as f:
        json.dump(audit, f, indent=2, allow_nan=False)
    if any(sha(adapter.ALGO_ROOT/p) != value for p,value in source_hashes.items()) or sha(args.baseline) != old_hash:
        raise RuntimeError('Source changed during run')
    manifest = dict(schema='mmwave_probe_merge_ready_v1', pipeline_version='issue33-v2', run_id=args.run_id,
                    source_commit=commit, source_tree_dirty=dirty, source_hashes=source_hashes,
                    baseline_sha256=old_hash, output_sha256=sha(out_csv), inputs=source_inputs,
                    rows=len(out_rows), sessions=len({r['session_id'] for r in out_rows}),
                    state_counts=dict(Counter(r['mmwave_state'] for r in out_rows)),
                    run_utc=datetime.now(timezone.utc).isoformat(), python=sys.version, numpy=np.__version__,
                    parameters=dict(fs=adapter.FS, course_s=adapter.COURSE_S, step_s=5.0, timestamp_column=2, end_exclusive=True),
                    physiology_role='SUPPORTING_HOLD / NOT_PRIMARY', hrv_fields='EXCLUDE / null',
                    scientific_admission='NOT_PROMOTED', models_trained=False,
                    timestamp_limitation='Python write-time retained for controlled issue33 replay; DLL-time transfer to formal cohort is not yet validated.')
    with out_csv.with_name(out_csv.stem+'_manifest.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
