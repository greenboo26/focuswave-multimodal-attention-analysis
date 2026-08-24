# -*- coding: utf-8 -*-
"""导出各被试 RSP 呼吸带全段呼吸率 (Biopac .acq -> gold_standard_qa.rsp_qa)。
输出 CSV: output/A2_rsp_gate/rsp_rates.csv
这是 approach ① / A2 接线中 ext_br_bpm 的取值依据。"""
import sys, csv
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_registry import load_paths

PATHS = load_paths()
ROOT = Path(PATHS["calibration_root"])
OUT = Path(PATHS["algorithm_root"]) / "output" / "A2_rsp_gate"
OUT.mkdir(parents=True, exist_ok=True)
import bioread
from gold_standard_qa import rsp_qa

rows = []
for d in sorted(ROOT.glob("sub-*_")):
    acqs = list(d.glob("*.acq"))
    if not acqs:
        continue
    try:
        da = bioread.read_file(str(acqs[0]))
    except Exception as e:
        rows.append((d.name, "", "READ_FAIL", str(e)[:40], "", ""))
        continue
    sr = da.samples_per_second
    rsp_idx = next((i for i, c in enumerate(da.channels) if "RSP" in str(c.name).upper()), None)
    if rsp_idx is None:
        rows.append((d.name, sr, "NO_RSP_CHANNEL", "", "", ""))
        continue
    rsp = np.asarray(da.channels[rsp_idx].data).astype(float)
    br, rep = rsp_qa(rsp, sr, 0, len(rsp))
    rows.append((d.name, round(sr, 1), round(br, 2) if br else "",
                 rep.get("usable"), round(rep.get("valid_ratio", 0), 3), len(rsp)))

csv_path = OUT / "rsp_rates.csv"
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["subject", "sample_rate_hz", "rsp_br_bpm", "rsp_usable", "rsp_valid_ratio", "rsp_N_samples"])
    w.writerows(rows)
print(f"[saved] {csv_path}")
for r in rows:
    print(r)
