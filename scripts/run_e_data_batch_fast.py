# -*- coding: utf-8 -*-
"""快速批处理：60 秒定位通道/距离，随后固定候选做全程提取。

该脚本用于大批量工程处理；完整多候选管线仍保留作抽查基线。
"""
from __future__ import annotations
import csv, json, os, sys, time
from pathlib import Path

SCRIPT_DIR = Path(r"D:\Project\厚粲杯\08_算法\scripts")
RUNNER = Path(r"D:\Project\厚粲杯\08_算法\output\06_正式实验\E_Data\run_e_data_batch.py")
sys.path.insert(0, str(RUNNER.parent))
import run_e_data_batch as base

algo = base.algo
DATA_ROOT = Path(os.environ.get("E_DATA_ROOT", r"E:\Data"))
OUT_ROOT = Path(os.environ.get("E_DATA_OUT_ROOT", r"D:\Project\厚粲杯\08_算法\output\FAST_mmwave"))
METHOD = os.environ.get("E_DATA_METHOD", "bp_heart")
FS = 100.0


def read_json(out_dir, session):
    p = out_dir / f"{session}_mmwave_vital_signs.json"
    if not p.exists():
        return None
    # The producer closes the JSON just after the NPZ/figures are written on
    # Windows. Retry briefly so a transient sharing violation does not discard
    # an otherwise valid subject from the batch summary.
    for attempt in range(8):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.5 * (attempt + 1))
    return None


def run_one(s):
    mm_dir = DATA_ROOT / f"sub-{s}_" / "mmwave"
    session = f"sub-{s}_ses-SART"
    pattern = f"sub-{s}_mmwave_datacube_part*.npz"
    out = OUT_ROOT / f"sub-{s}_"
    final = read_json(out, session)
    if final:
        return base._row_from_result(s, final, 0.0)
    select_dir = out / "_selection_60s"
    sel = read_json(select_dir, session)
    if not sel:
        algo.analyze_long_record(
            parts_dir=mm_dir, output_dir=select_dir, session=session,
            method=METHOD, pattern=pattern, frame_start=0, frame_end=int(60 * FS),
            min_range_m=0.3, max_range_m=1.5, bin_spacing_m=0.08, range_bias_m=0.0,
        )
        sel = read_json(select_dir, session)
    bins = sel.get("bins", {})
    hch = sel.get("best_channel")
    hbin = bins.get("heart")
    if hch is None or hbin is None:
        raise RuntimeError(f"60s selection failed: best_channel={hch}, bins={bins}")
    t0 = time.time()
    algo.analyze_long_record(
        parts_dir=mm_dir, output_dir=out, session=session,
        method=METHOD, pattern=pattern,
        forced_heart_ch=int(hch), forced_heart_bin=int(hbin),
        min_range_m=0.3, max_range_m=1.5, bin_spacing_m=0.08, range_bias_m=0.0,
    )
    final = read_json(out, session)
    if not final:
        raise RuntimeError("fast full extraction did not write JSON")
    row = base._row_from_result(s, final, time.time() - t0)
    row["selection_window_s"] = 60.0
    row["selection_channel"] = int(hch)
    row["selection_heart_bin"] = int(hbin)
    row["fast_mode"] = True
    return row


def main():
    subs = sys.argv[1:] or sorted(d.name.replace("sub-", "").rstrip("_") for d in DATA_ROOT.glob("sub-*_"))
    rows=[]
    for s in subs:
        print(f"[fast] sub-{s}", flush=True)
        try:
            row=run_one(s); rows.append(row)
            print(f"  HR={row.get('hr_freq_bpm')}/{row.get('hr_time_bpm')} RR={row.get('br_freq_bpm')} elapsed={row.get('elapsed_s')}", flush=True)
        except Exception as e:
            row={"subject":s,"error":f"{type(e).__name__}: {e}"}; rows.append(row); print("  ERROR",row["error"],flush=True)
    OUT_ROOT.mkdir(parents=True,exist_ok=True)
    (OUT_ROOT/"summary.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(OUT_ROOT/"summary.csv","w",newline="",encoding="utf-8-sig") as fh:
        w=csv.DictWriter(fh,fieldnames=keys,extrasaction="ignore");w.writeheader();w.writerows(rows)


if __name__ == "__main__": main()
