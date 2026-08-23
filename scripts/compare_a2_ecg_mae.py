# -*- coding: utf-8 -*-
"""compare_a2_ecg_mae.py — 量化 A2 呼吸带门控的真实收益
============================================================================
用 ECG 金标准（Biopac .acq）做逐窗 HR 对照，比较：
  - gate-ON  (corrected_bpm, A2 接入 RSP 先验后的逐窗 HR)
  - gate-OFF (raw_freq_bpm, 等价于 ext_br_bpm=None 的对照，A2 未介入)
二者来自同一份 gate-ON 产物 JSON：A2 仅在谐波剔除分支作用，
raw_freq_bpm 在门控关时即等于 corrected_bpm，故可用作精确对照。

对齐：复用 validate_gold_anchor.load_align 的 marker 对齐 (offset,k) 把
毫米波窗时间(start_s/end_s) → mmwave 时间戳(unix_ms) → ECG 帧，
再用 gold_standard_qa.ecg_qa 求每窗 ECG HR。

输出: output/A2_rsp_gate/sub-{sub}/a2_ecg_mae.csv + 终端汇总
"""
import sys
import json
import csv
from pathlib import Path
import numpy as np

SCRIPT_DIR = Path(r"D:\Project\厚粲杯\08_算法\scripts")
sys.path.insert(0, str(SCRIPT_DIR))
import validate_gold_anchor as vga          # 提供 load_align / read_segments
import gold_standard_qa as gold_qa

SUB = "97795"
ACQ_ROOT = vga.ACQ_ROOT
OUT_ROOT = Path(r"D:\Project\厚粲杯\08_算法\output\A2_rsp_gate")

data_dir = ACQ_ROOT / f"sub-{SUB}_"
acq_path = list(data_dir.glob("*.acq"))[0]
events_path = data_dir / "beh" / "events.csv"
mm_dir = data_dir / "mmwave"
prefix = f"sub-{SUB}_mmwave"

# 1) ECG 对齐
offset, k, sr, ecg, rsp = vga.load_align(acq_path, events_path)
print(f"[align] offset={offset:.1f}ms k={k:.6f} sr={sr} ecg_len={len(ecg)}")

# 2) mmwave 时间戳 (列2=unix_ms, 行号=part-frame)
ts = np.loadtxt(mm_dir / f"{prefix}_timestamps.csv", delimiter=",")[:, 2]

# 3) gate-ON 产物 JSON
session = f"sub-{SUB}_ses-SART"
json_path = OUT_ROOT / f"sub-{SUB}" / f"{session}_mmwave_vital_signs.json"
d = json.load(open(json_path, encoding="utf-8"))
FS = d["frame_rate_hz"]
windows = d["heart_rate"]["segment_reference_correction"]["windows"]
print(f"[json] FS={FS} n_windows={len(windows)} external_respiration_bpm={d.get('external_respiration_bpm')}")

# 4) 逐窗 ECG HR + 对照
rows = []
for w in windows:
    s0, s1 = w["start_s"], w["end_s"]
    f0, f1 = int(round(s0 * FS)), int(round(s1 * FS))
    if f0 < 0 or f1 >= len(ts):
        continue
    u0, u1 = ts[f0], ts[f1]
    ei0, ei1 = int((u0 - offset) / k), int((u1 - offset) / k)
    if ei0 < 0 or ei1 >= len(ecg) or ei1 <= ei0:
        continue
    hr, rep = gold_qa.ecg_qa(ecg, sr, ei0, ei1)
    if not rep.get("usable") or hr is None:
        continue
    if not (40.0 <= hr <= 180.0):
        continue
    gate_off = w.get("raw_freq_bpm")      # A2 关 (等价于 ext_br_bpm=None)
    gate_on = w.get("corrected_bpm")      # A2 开 (已做谐波剔除回退)
    if gate_off is None or gate_on is None:
        continue
    rows.append({
        "start_s": round(s0, 1), "end_s": round(s1, 1),
        "ecg_hr": round(hr, 1),
        "gate_off_hr": round(gate_off, 1),
        "gate_on_hr": round(gate_on, 1),
        "resp_reject": bool(w.get("resp_harmonic_reject")),
        "resp_k": w.get("resp_harmonic_k"),
        "ecg_valid_ratio": round(rep.get("valid_ratio", 0.0), 3),
    })

print(f"[aligned] {len(rows)} 窗成功对齐 ECG 金标准")

ecg = np.array([r["ecg_hr"] for r in rows])
go = np.array([r["gate_off_hr"] for r in rows])
gn = np.array([r["gate_on_hr"] for r in rows])

mae_off = float(np.mean(np.abs(go - ecg)))
mae_on = float(np.mean(np.abs(gn - ecg)))
rmse_off = float(np.sqrt(np.mean((go - ecg) ** 2)))
rmse_on = float(np.sqrt(np.mean((gn - ecg) ** 2)))

print("\n================ A2 逐窗 ECG MAE ================")
print(f"对齐窗数            : {len(rows)}")
print(f"ECG HR 均值         : {ecg.mean():.1f} bpm")
print(f"mmWave gate-OFF MAE : {mae_off:.2f} bpm  (RMSE {rmse_off:.2f})")
print(f"mmWave gate-ON  MAE : {mae_on:.2f} bpm  (RMSE {rmse_on:.2f})")
print(f"ΔMAE (OFF-ON)       : {mae_off - mae_on:+.2f} bpm  -> A2 真实收益")

# 被拒窗专项
rej = [r for r in rows if r["resp_reject"]]
if rej:
    re = np.array([r["ecg_hr"] for r in rej])
    rgo = np.array([r["gate_off_hr"] for r in rej])
    rgn = np.array([r["gate_on_hr"] for r in rej])
    print(f"\n-- 被 RSP 门控标记的 {len(rej)} 窗 --")
    print(f"   gate-OFF MAE : {np.mean(np.abs(rgo - re)):.2f}")
    print(f"   gate-ON  MAE : {np.mean(np.abs(rgn - re)):.2f}")

# 值被真正修正的窗 (corrected != raw)
fixed = [r for r in rows if abs(r["gate_on_hr"] - r["gate_off_hr"]) > 0.05]
print(f"\n被 A2 真正修正值的窗 : {len(fixed)} / {len(rej)} 被标记")
for r in fixed:
    print(f"   {r['start_s']:.0f}s  {r['gate_off_hr']:.1f} -> {r['gate_on_hr']:.1f}  (ECG {r['ecg_hr']:.1f})")

# 5) 保存
out_csv = OUT_ROOT / f"sub-{SUB}" / "a2_ecg_mae.csv"
with open(out_csv, "w", encoding="utf-8", newline="") as f:
    wtr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    wtr.writeheader()
    wtr.writerows(rows)
print(f"\n[out] {out_csv}")
