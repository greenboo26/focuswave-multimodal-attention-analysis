"""Enrich block-stop metadata without recomputing unchanged signal slices."""
import argparse
import csv
import json
from pathlib import Path
from mmwave_frozen_cohort import block_starts, canonical_row, sha, validate_rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--raw-root',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--run-id',required=True)
    args=p.parse_args()
    manifest_path=args.input.with_name(args.input.stem+'_manifest.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if sha(args.input) != manifest['output_sha256']:
        raise ValueError('Parent output hash mismatch')
    inputs={r['path']:r['sha256'] for r in manifest['inputs']}
    with args.input.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
    validate_rows(rows)
    markers={}
    changed=0
    for row in rows:
        session=row['session_id']
        timeline=args.raw_root/(session+'_')/'beh/master_timeline.csv'
        if session not in markers:
            if timeline.exists():
                if inputs.get(str(timeline)) != sha(timeline):
                    raise ValueError('Timeline differs from feature run')
                markers[session]=(block_starts(timeline),block_starts(timeline,'block_stop'))
            else:
                markers[session]=({}, {})
        starts,ends=markers[session]
        base,known=canonical_row(row,starts,ends)
        if known:
            if base['window_effective_start_unix_ms'] != row['window_effective_start_unix_ms']:
                raise ValueError('Slice change requires feature replay')
            changed += row.get('block_end_unix_ms') != base['block_end_unix_ms']
            row['block_end_unix_ms']=base['block_end_unix_ms']
        elif row['mmwave_state']=='OBSERVED':
            raise ValueError('Observed row without validated block bounds')
        row['mmwave_source_run_id']=args.run_id
    args.output_dir.mkdir(parents=True,exist_ok=False)
    out=args.output_dir/args.input.name
    with out.open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    audit=json.loads((args.input.parent/'probe_audit.json').read_text(encoding='utf-8'))
    (args.output_dir/'probe_audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False),encoding='utf-8')
    manifest.update(run_id=args.run_id, output_sha256=sha(out), metadata_only=True, block_stop_updated_rows=changed,
                    feature_source_run_id=manifest['run_id'],feature_source_manifest_sha256=sha(manifest_path),
                    feature_source_csv_sha256=sha(args.input),feature_source_path=str(args.input),
                    metadata_script_sha256=sha(__file__),metadata_helpers_sha256=sha(Path(__file__).with_name('mmwave_frozen_cohort.py')),
                    slice_equivalence_verified=True, numerical_features_unchanged=True)
    out.with_name(out.stem+'_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),block_stop_updated_rows=changed,numerical_features_unchanged=True)))


if __name__=='__main__':
    main()
