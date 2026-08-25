"""Evaluate official MATLAB VitalSense beats with the frozen C1b evaluator."""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
import numpy as np
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_vitalsense_c1b_benchmark_v1 import (  # noqa: E402
    arr, scalar, get_field, ecg_rpeaks, project_bandpass_peak,
    vitalsense_amf, metrics, greedy_match, TOLERANCES_MS, PRIMARY_TOLERANCE_MS,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--official-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--primary-delay-ms", type=float, default=-18.000000000000682)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    subjects = [f"VS{i:02d}" for i in range(1,25)]
    conditions = ["Resting", "Apnea"]
    all_rows=[]
    official_primary_delay=None
    for s in subjects:
        for c in conditions:
            r=loadmat(args.data_dir/f"{s}_{c}.mat",squeeze_me=True,struct_as_record=False)
            m=loadmat(args.data_dir/f"{s}_{c}_Mindray.mat",squeeze_me=True,struct_as_record=False)
            vital=arr(r["VitalSig"]); fs=scalar(get_field(r["Radar"],"fs")); t=arr(get_field(r["Radar"],"t_frame")); t=t-t[0]
            ecg=arr(m["ecg_lead2"]); fs_e=scalar(m["Fs_ecg"]); ref_t=np.arange(len(ecg))/fs_e; ref_t=ref_t[ecg_rpeaks(ecg,fs_e)]
            official_file=args.official_dir/"official_beats"/f"{s}_{c}_official_beats.csv"
            official_t=np.atleast_1d(np.loadtxt(official_file,delimiter=",",ndmin=1)) if official_file.stat().st_size else np.array([])
            methods={"project_bandpass_peak":t[project_bandpass_peak(vital,fs)],"python_vitalsense_amf":t[vitalsense_amf(vital,fs)],"official_matlab_vitalsense_rw_amf":official_t}
            if s=="VS01" and c=="Resting":
                pp=greedy_match(ref_t,official_t,PRIMARY_TOLERANCE_MS/1000)
                official_primary_delay=float(np.median([d for _,_,d in pp])) if pp else None
            for method,est_t in methods.items():
                for tol in TOLERANCES_MS:
                    raw=metrics(ref_t,est_t,tol,0.0); primary=metrics(ref_t,est_t,tol,args.primary_delay_ms/1000.0)
                    diagnostic_delay=(official_primary_delay if official_primary_delay is not None else args.primary_delay_ms/1000.0) if method=="official_matlab_vitalsense_rw_amf" else args.primary_delay_ms/1000.0
                    diagnostic=metrics(ref_t,est_t,tol,diagnostic_delay)
                    row={"subject":s,"condition":c,"method":method,"delay_mode":"official_delay_not_estimable" if method=="official_matlab_vitalsense_rw_amf" and official_primary_delay is None else "primary_fixed_c1b","official_delay_diagnostic_ms":None if official_primary_delay is None else official_primary_delay*1000.0,"primary_delay_ms":args.primary_delay_ms,"tolerance_ms":tol}
                    row.update({f"raw_{k}":v for k,v in raw.items()}); row.update({f"primary_{k}":v for k,v in primary.items()}); row.update({f"diagnostic_{k}":v for k,v in diagnostic.items()}); all_rows.append(row)
    # Primary/long outputs
    fields=sorted({k for x in all_rows for k in x})
    with (args.out_dir/"official_beat_metrics_long.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(all_rows)
    primary=[x for x in all_rows if x["tolerance_ms"]==PRIMARY_TOLERANCE_MS]
    with (args.out_dir/"official_beat_metrics_primary.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(primary)
    # Compact three-method summary (means and medians by condition).
    wanted=["primary_precision","primary_recall","primary_f1","primary_ecg_beats","primary_radar_beats","primary_matched_beats","primary_ibi_mae_ms","primary_hr_abs_error_bpm","primary_rmssd_abs_error_ms","primary_sdnn_abs_error_ms"]
    summary=[]
    for method in sorted({x["method"] for x in primary}):
        for condition in conditions+['Overall']:
            ss=[x for x in primary if x["method"]==method and (condition=='Overall' or x["condition"]==condition)]
            for metric in wanted:
                vals=np.array([float(x[metric]) for x in ss if x.get(metric) not in (None,'') and str(x[metric])!='nan'])
                if len(vals): summary.append({"method":method,"condition":condition,"metric":metric,"n":len(vals),"mean":float(vals.mean()),"median":float(np.median(vals)),"q25":float(np.quantile(vals,.25)),"q75":float(np.quantile(vals,.75))})
    with (args.out_dir/"three_method_comparison.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["method","condition","metric","n","mean","median","q25","q75"]);w.writeheader();w.writerows(summary)
    cfg={"status":"OFFICIAL_REPRO_COMPLETE","official_delay_diagnostic_ms":None if official_primary_delay is None else official_primary_delay*1000.0,"official_delay_status":"not_estimable_from_VS01_Resting_at_primary_tolerance" if official_primary_delay is None else "estimated_once_from_VS01_Resting","primary_delay_ms":args.primary_delay_ms,"primary_tolerance_ms":PRIMARY_TOLERANCE_MS,"sensitivity_tolerances_ms":list(TOLERANCES_MS),"sessions":48,"methods":sorted({x['method'] for x in primary})}
    (args.out_dir/"official_evaluation_run_manifest.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")


if __name__=="__main__": main()
