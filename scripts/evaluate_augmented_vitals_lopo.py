"""Evaluate expanded window-level physiological/quality features with LOPO."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


BASE = ["rmssd_ms", "sdnn_ms", "hr_med_bpm", "z_rmssd", "n_peaks"]
EXTRA = ["breath_rate_bpm", "breath_rate_spectral_bpm", "breath_rate_time_freq_gap_bpm", "hr_time_freq_gap_bpm", "hr_confidence", "hr_signal_std_10s_mm"]
VISION = ["rgb_motion", "rgb_luminance", "nir_pupil_dark_fraction", "nir_eye_contrast"]
VISION_GEOMETRY = ["rgb_face_detected", "rgb_face_area_frac", "rgb_face_center_offset", "rgb_face_luminance", "nir_pupil_detected", "nir_pupil_radius_px", "nir_pupil_center_x", "nir_pupil_center_y"]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))


def merge(vital_path: Path, cm_path: Path | None) -> list[dict]:
    rows = load(vital_path); cmap = {}
    if cm_path:
        cmap = {(str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)): r for r in load(cm_path)}
    out = []
    for r in rows:
        key = (str(r["subject"]).zfill(3), round(float(r["onset_rel_s"]), 1)); x = dict(r)
        if key in cmap: x.update({k: v for k, v in cmap[key].items() if k not in {"subject", "onset_rel_s", "attention"}})
        x["subject"] = key[0]; x["attention"] = int(r["attention"]); out.append(x)
    return out


def lopo(rows: list[dict], features: list[str], target: str = "attention") -> dict:
    usable = []
    for r in rows:
        try:
            x = np.asarray([float(r[f]) for f in features], float)
            if not np.all(np.isfinite(x)): continue
            y = int(r[target]) if target == "attention" else int(float(r[target]) < .95)
            if target == "attention": y = int(r["attention"] == 1)
            usable.append((r["subject"], x, y, int(r["attention"])))
        except (KeyError, TypeError, ValueError): continue
    y_true=[]; score=[]; pred=[]; subs=[]
    for s in sorted({r[0] for r in usable}):
        tr=[r for r in usable if r[0]!=s]; te=[r for r in usable if r[0]==s]
        if not te or len({r[2] for r in tr})<2: continue
        model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,class_weight="balanced")); model.fit(np.asarray([r[1] for r in tr]),np.asarray([r[2] for r in tr])); p=model.predict_proba(np.asarray([r[1] for r in te]))[:,1]
        y_true += [r[2] for r in te]; score += p.tolist(); pred += (p>=.5).astype(int).tolist(); subs += [s]*len(te)
    return {"n":len(y_true),"subjects":len(set(subs)),"auc":float(roc_auc_score(y_true,score)) if len(set(y_true))==2 else None,"balanced_accuracy":float(balanced_accuracy_score(y_true,pred)) if y_true else None,"features":features}


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--vitals",type=Path,required=True); ap.add_argument("--crossmodal",type=Path); ap.add_argument("--enhanced-crossmodal",type=Path); ap.add_argument("--behavior",type=Path); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    rows=merge(args.vitals,args.crossmodal); result={"n_rows":len(rows),"n_subjects":len({r["subject"] for r in rows}),"analyses":{}}
    if args.enhanced_crossmodal:
        enhanced = merge(args.vitals, args.enhanced_crossmodal)
        geo = {(r["subject"], round(float(r["onset_rel_s"]), 1)): r for r in enhanced}
        for r in rows:
            e = geo.get((r["subject"], round(float(r["onset_rel_s"]), 1)), {})
            for k in VISION_GEOMETRY:
                r[k] = e.get(k)
    for name, filt in (("focus_vs_all",None),("focus_vs_mw",{1,3})):
        rs=[r for r in rows if filt is None or r["attention"] in filt]
        result["analyses"][name]={"base":lopo(rs,BASE),"expanded":lopo(rs,BASE+EXTRA),"expanded_visual":lopo(rs,BASE+EXTRA+VISION) if args.crossmodal else None,"enhanced_visual":lopo(rs,BASE+EXTRA+VISION+VISION_GEOMETRY) if args.enhanced_crossmodal else None}
    if args.behavior:
        bmap={(str(r["subject"]).zfill(3),round(float(r["onset_rel_s"]),1)):r for r in load(args.behavior)}
        for r in rows:
            b=bmap.get((r["subject"],round(float(r["onset_rel_s"]),1))); r["accuracy"]=b.get("accuracy") if b else None
        result["behavior_target_accuracy_below_95"]={"expanded":lopo(rows,BASE+EXTRA,"accuracy"),"expanded_visual":lopo(rows,BASE+EXTRA+VISION,"accuracy") if args.crossmodal else None,"enhanced_visual":lopo(rows,BASE+EXTRA+VISION+VISION_GEOMETRY,"accuracy") if args.enhanced_crossmodal else None}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
