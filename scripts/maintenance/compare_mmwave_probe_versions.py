"""Exact-key old/new comparison, including missing transitions and finite deltas."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from mmwave_frozen_cohort import KEYS, validate_rows


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    validate_rows(rows)
    return {tuple(r[k] for k in KEYS):r for r in rows}


def number(value):
    try:
        result = float(value)
        return result if np.isfinite(result) else None
    except (ValueError,TypeError):
        return None


def normalized(value):
    if value in ('',None,'None','nan','NaN'):
        return None
    numeric = number(value)
    return numeric if numeric is not None else value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old', nargs=2, required=True, type=Path)
    p.add_argument('--new', nargs=2, required=True, type=Path)
    p.add_argument('--output-dir', required=True, type=Path)
    args = p.parse_args()
    old, new, audits = {}, {}, {}
    for old_path, new_path in zip(args.old,args.new):
        for target, path in ((old,old_path),(new,new_path)):
            data = read(path)
            if target.keys() & data.keys():
                raise ValueError('Duplicate keys across batches')
            target.update(data)
        for row in json.loads((new_path.parent/'probe_audit.json').read_text(encoding='utf-8')):
            audits[tuple(row[k] for k in KEYS)] = row
    if old.keys() != new.keys():
        raise ValueError('Old/new key mismatch')
    fields = [k for k in next(iter(old.values())) if k.startswith('mmwave_') and k not in ('mmwave_source_commit','mmwave_source_run_id')]
    summary, detail = {}, []
    changed_keys = set()
    for field in fields:
        changes = []; deltas = []; missing_to_value = value_to_missing = 0
        for key in sorted(old):
            a,b = old[key].get(field),new[key].get(field)
            if normalized(a) != normalized(b):
                changes.append(key)
                changed_keys.add(key)
                detail.append(dict(zip(KEYS,key), field=field, old=a, new=b, absolute_difference=abs(number(b)-number(a)) if number(a) is not None and number(b) is not None else None))
            na,nb = number(a),number(b)
            if na is not None and nb is not None:
                deltas.append(abs(nb-na))
            missing_to_value += normalized(a) is None and normalized(b) is not None
            value_to_missing += normalized(a) is not None and normalized(b) is None
        summary[field] = dict(changed_rows=len(changes), finite_pairs=len(deltas), missing_to_value=missing_to_value, value_to_missing=value_to_missing,
                              median_absolute_difference=float(np.median(deltas)) if deltas else None,
                              p90_absolute_difference=float(np.percentile(deltas,90)) if deltas else None,
                              max_absolute_difference=float(max(deltas)) if deltas else None)
    boundary = {k for k,v in audits.items() if v['old_endpoint_hit']}
    result = dict(rows=len(old), sessions=len({r['session_id'] for r in old.values()}), one_to_one=True,
                  any_mmwave_field_changed=len(changed_keys), old_endpoint_hits=len(boundary),
                  endpoint_hit_rows_changed=len(boundary & changed_keys),
                  actual_block_truncations=sum(r['truncated'] for r in audits.values()),
                  boundary_unknown_rows=sum(not r['boundary_known'] for r in audits.values()),
                  frame_gap_rows=sum(r.get('frame_index_gap_count',0)>0 for r in audits.values()),
                  old_states=dict(Counter(r['mmwave_state'] for r in old.values())),
                  new_states=dict(Counter(r['mmwave_state'] for r in new.values())), fields=summary,
                  new_usable_fraction=dict(Counter(r.get('mmwave_hr_usable_window_fraction','') for r in new.values())),
                  formal_physiological_predictor_admission='NOT_PASSED', models_trained=False,
                  admission_reason='Existing supporting/hold contract remains; quality metrics are not predictors. Python frame-time and fixed-FS gap qualifications remain unresolved.',
                  sources=[dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in args.old+args.new])
    args.output_dir.mkdir(parents=True,exist_ok=False)
    with (args.output_dir/'old_vs_new_summary.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    with (args.output_dir/'old_vs_new_per_probe.csv').open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=[*KEYS,'field','old','new','absolute_difference'])
        writer.writeheader();writer.writerows(detail)
    print(json.dumps({k:v for k,v in result.items() if k not in ('fields','sources','new_usable_fraction')},ensure_ascii=False))


if __name__ == '__main__':
    main()
