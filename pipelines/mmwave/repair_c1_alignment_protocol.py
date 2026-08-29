# -*- coding: utf-8 -*-
"""C1 alignment protocol repair (diagnostic only).

This script does not re-extract radar signals and does not change C1c/C1d
detectors.  It audits independent marker-based clock provenance, performs a
fixed lag-invariant IBI sequence audit, and evaluates pre-declared held-out
constant lags.  Oracle lags are diagnostic upper bounds only.
"""
from __future__ import annotations

import csv, json, sys
from pathlib import Path
import numpy as np

ALGO = Path(r"D:\Project\厚粲杯\08_算法\scripts")
sys.path.insert(0, str(ALGO))
from calibrate_ecg_mmwave import read_ecg_and_markers, read_events, align_clocks
from run_c1c_mmhrv_pilot import greedy, metrics

RAW_ROOT = Path(r"D:\acq_mmwave_data")
ASSET_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1")
OUT_ROOT = Path(r"D:\Project\厚粲杯\11_数据\derived\c1_alignment_protocol_repair_v1")
SUBJECTS = ("97793", "9779", "97795")
FIXED_DELAY_MS = -18.0
TOLS_MS = (50.0, 75.0, 100.0, 150.0)
PRIMARY_TOL_MS = 75.0
LAG_GRID_MS = np.arange(-250.0, 250.0 + 0.1, 5.0)
IBI_MATCH_MAX_DIFF_MS = 250.0
IBI_GAP_PENALTY_MS = 250.0


def read_ts(path: Path):
    a = np.loadtxt(path, delimiter=",", ndmin=2)
    return a[:, 2].astype(float)


def timestamp_audit(path: Path):
    ts = read_ts(path)
    dt = np.diff(ts)
    med = float(np.median(dt)) if len(dt) else None
    mad = float(np.median(np.abs(dt - med))) if len(dt) else None
    threshold = max(2.0 * (1000.0 / 99.0), 2.5 * med) if med else None
    gaps = dt[dt > threshold] if threshold is not None else np.array([])
    return {
        "path": str(path), "n_frames": int(len(ts)),
        "first_unix_ms": float(ts[0]) if len(ts) else None,
        "last_unix_ms": float(ts[-1]) if len(ts) else None,
        "median_dt_ms": med, "mad_dt_ms": mad,
        "max_dt_ms": float(np.max(dt)) if len(dt) else None,
        "gap_threshold_ms": threshold, "n_large_gaps": int(len(gaps)),
        "max_large_gap_ms": float(np.max(gaps)) if len(gaps) else None,
        "timestamp_precision_ms": float(np.min(np.abs(dt - med))) if len(dt) else None,
    }, ts


def event_audit(path: Path):
    ev = read_events(str(path))
    vals = [x[0] for x in ev]; times = [x[1] for x in ev]
    return {
        "path": str(path), "n_events": len(ev),
        "n_boundary_events_lt100": sum(v < 100 for v in vals),
        "unique_markers": sorted(set(vals)),
        "first_unix_ms": min(times) if times else None,
        "last_unix_ms": max(times) if times else None,
        "marker_timestamp_precision_ms": min(
            (abs(float(times[i+1]) - float(times[i])) for i in range(len(times)-1)),
            default=None),
    }, ev


def marker_clock_audit(acq: Path, events, sr_hint=None):
    result = {"acq_path": str(acq), "marker_fit_available": False}
    try:
        ecg, sr, pulses = read_ecg_and_markers(str(acq))
        result.update({"ecg_samples": int(len(ecg)), "ecg_sampling_rate_hz": float(sr),
                       "ecg_marker_pulses": len(pulses),
                       "ecg_marker_values": sorted(set(v for v, _ in pulses))})
        fit = align_clocks(pulses, events, sr)
        if fit is None:
            result["device_clock_offset_status"] = "device_clock_offset_not_identifiable"
            return result
        off, ms_per_sample = fit
        bounds = [(m, u) for m, u, _, _ in events if m < 100]
        ecg_bounds = [(v, idx) for v, idx in pulses if v < 100]
        # Reconstruct the same marker-pair logic only for an independent fit QC.
        pairs = []
        for m, u in bounds:
            cands = [idx for v, idx in ecg_bounds if v == m]
            if cands:
                if not pairs:
                    pairs.append((cands[0], u))
                else:
                    pred = pairs[-1][0] + (u - pairs[-1][1]) / ms_per_sample
                    pairs.append((min(cands, key=lambda z: abs(z-pred)), u))
        if len(pairs) >= 2:
            idx = np.asarray([p[0] for p in pairs], float)
            unix = np.asarray([p[1] for p in pairs], float)
            resid = unix - (off + ms_per_sample * idx)
            result.update({"marker_fit_available": True,
                           "device_clock_offset_status": "identifiable_via_independent_marker_fit",
                           "clock_fit_intercept_ms": float(off),
                           "clock_fit_ms_per_ecg_sample": float(ms_per_sample),
                           "marker_fit_pairs": len(pairs),
                           "marker_fit_rmse_ms": float(np.sqrt(np.mean(resid**2))),
                           "marker_fit_max_abs_residual_ms": float(np.max(np.abs(resid)))})
        else:
            result["device_clock_offset_status"] = "device_clock_offset_not_identifiable"
    except Exception as exc:
        result.update({"device_clock_offset_status": "audit_error", "error": repr(exc)})
    return result


def load_beats(subject: str, method: str):
    p = ASSET_ROOT / subject
    if method == "c1c_local":
        with np.load(p / "c1c_waveforms_replayed.npz") as d:
            return np.asarray(d["ecg_peak_times_s"], float), np.asarray(d["local_peak_times_s"], float)
    with np.load(p / "c1d_similarity_dp_assets.npz") as d:
        # C1d assets contain the DP sequence but not always the ECG copy;
        # the ECG timestamps are the same frozen C1c reference for this session.
        est = np.asarray(d["dp_peak_times_s"], float)
    with np.load(p / "c1c_waveforms_replayed.npz") as d:
        ref = np.asarray(d["ecg_peak_times_s"], float)
    return ref, est


def lag_metrics(ref, est, delay):
    return metrics(ref, est, PRIMARY_TOL_MS, float(delay))


def oracle(ref, est):
    vals = [(float(l), lag_metrics(ref, est, l)) for l in LAG_GRID_MS]
    return max(vals, key=lambda x: (x[1]["f1"] or -1.0))


def heldout(ref, est):
    mid = 0.5 * max(float(ref[-1]) if len(ref) else 0.0,
                    float(est[-1]) if len(est) else 0.0)
    results = []
    for name, cal, eva in (("first_to_second", (ref < mid), (ref >= mid)),
                           ("second_to_first", (ref >= mid), (ref < mid))):
        rcal, rtest = ref[cal], ref[eva]
        ecal, etest = est[cal if False else (est < mid)], est[est >= mid]
        if name == "second_to_first":
            ecal, etest = est[est >= mid], est[est < mid]
        if len(rcal) < 2 or len(ecal) < 2 or len(rtest) < 2 or len(etest) < 2:
            results.append({"direction": name, "status": "insufficient_beats"})
            continue
        cal_oracle_lag, cal_m = oracle(rcal, ecal)
        ev_m = lag_metrics(rtest, etest, cal_oracle_lag)
        results.append({"direction": name, "status": "ok",
                        "calibration_optimal_delay_ms": cal_oracle_lag,
                        "calibration_f1": cal_m["f1"],
                        "evaluation_f1": ev_m["f1"],
                        "evaluation_precision": ev_m["precision"],
                        "evaluation_recall": ev_m["recall"],
                        "evaluation_timing_mae_ms": ev_m["timing_mae_ms"],
                        "oracle_full_delay_ms": oracle(ref, est)[0],
                        "oracle_full_f1": oracle(ref, est)[1]["f1"]})
    return results


def align_ibi(a, b):
    """Fixed monotone interval alignment, not DTW and not lag-dependent."""
    n, m = len(a), len(b)
    dp = np.full((n+1, m+1), np.inf); ptr = np.zeros((n+1, m+1), np.int8)
    dp[:, 0] = np.arange(n + 1) * IBI_GAP_PENALTY_MS
    dp[0, :] = np.arange(m + 1) * IBI_GAP_PENALTY_MS
    for i in range(1, n+1):
        for j in range(1, m+1):
            diff = abs(a[i-1]-b[j-1])
            match_cost = diff if diff <= IBI_MATCH_MAX_DIFF_MS else (2 * IBI_GAP_PENALTY_MS + 1.0)
            vals = (dp[i-1,j-1] + match_cost,
                    dp[i-1,j] + IBI_GAP_PENALTY_MS,
                    dp[i,j-1] + IBI_GAP_PENALTY_MS)
            k = int(np.argmin(vals)); dp[i,j] = vals[k]; ptr[i,j] = k
    i, j = n, m; pairs=[]; gaps_a=gaps_b=0
    while i or j:
        k = ptr[i,j] if i and j else (1 if i else 2)
        if k == 0: pairs.append((i-1,j-1)); i-=1; j-=1
        elif k == 1: gaps_a += 1; i-=1
        else: gaps_b += 1; j-=1
    return pairs[::-1], gaps_a, gaps_b


def ibi_audit(ref, est):
    r = np.diff(ref)*1000.0; e = np.diff(est)*1000.0
    pairs, miss, extra = align_ibi(r, e)
    rv = np.asarray([r[i] for i,j in pairs], float); ev = np.asarray([e[j] for i,j in pairs], float)
    if len(rv):
        err = ev-rv
        corr = float(np.corrcoef(rv, ev)[0,1]) if len(rv)>1 and np.std(rv)>0 and np.std(ev)>0 else None
        mae = float(np.mean(np.abs(err))); medae = float(np.median(np.abs(err)))
        diff_q = [float(x) for x in np.quantile(err, [0,.25,.5,.75,1])]
    else: corr=mae=medae=None; diff_q=[]
    def rv_stats(x):
        return (float(np.sqrt(np.mean(np.diff(x)**2))), float(np.std(x,ddof=1))) if len(x)>2 else (None,None)
    rr, rs = rv_stats(rv); er, es = rv_stats(ev)
    return {"ecg_ibi_count": len(r), "radar_ibi_count": len(e), "aligned_ibi_pairs": len(pairs),
            "missed_ibi_count": miss, "extra_ibi_count": extra,
            "missed_rate": miss/max(len(r),1), "extra_rate": extra/max(len(e),1),
            "aligned_ibi_mae_ms": mae, "aligned_ibi_median_ae_ms": medae,
            "aligned_ibi_correlation": corr, "ibi_difference_quantiles_ms": diff_q,
            "rmssd_diagnostic_error_ms": abs(er-rr) if er is not None and rr is not None else None,
            "sdnn_diagnostic_error_ms": abs(es-rs) if es is not None and rs is not None else None}


def residual_summary(ref, est):
    pairs = greedy(ref, est - FIXED_DELAY_MS/1000.0, PRIMARY_TOL_MS/1000.0)
    x = np.asarray([d*1000.0 for _,_,d in pairs])
    return {"n_fixed_pairs": len(x), "median_residual_ms": float(np.median(x)) if len(x) else None,
            "mean_residual_ms": float(np.mean(x)) if len(x) else None,
            "sd_residual_ms": float(np.std(x, ddof=1)) if len(x)>1 else None,
            "residual_q_ms": [float(v) for v in np.quantile(x,[.1,.5,.9])] if len(x) else []}


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    sync_rows=[]; metric_rows=[]; ibi_rows=[]; held_rows=[]; residual_rows=[]
    methods=("c1c_local", "c1d_dp")
    for s in SUBJECTS:
        root=RAW_ROOT/f"sub-{s}_"; mm=root/"mmwave"; beh=root/"beh"
        ts_path=mm/f"sub-{s}_mmwave_timestamps.csv"; events_path=beh/"events.csv"
        acqs=list(root.glob("*.acq"))
        ta, ts = timestamp_audit(ts_path)
        ea, events = event_audit(events_path)
        ca = marker_clock_audit(acqs[0], events) if len(acqs)==1 else {"device_clock_offset_status":"acq_ambiguous", "acq_paths":[str(x) for x in acqs]}
        sync_rows.append({"subject":s, "radar_time_source":"frame timestamp CSV, Unix ms",
                          "ecg_time_source":"Biopac .acq sample index mapped to Unix ms using common digital markers",
                          "same_native_clock":False, "device_clock_offset_concept":"marker-derived clock mapping, not heartbeat lag",
                          "timestamp_audit":ta, "event_audit":ea, "marker_clock_audit":ca,
                          "acq_path":str(acqs[0]) if len(acqs)==1 else None,
                          "events_path":str(events_path)})
        for method in methods:
            ref, est = load_beats(s, method)
            o_lag, o_m = oracle(ref, est)
            fixed=lag_metrics(ref,est,FIXED_DELAY_MS)
            metric_rows.append({"subject":s,"method":method,"fixed_delay_ms":FIXED_DELAY_MS,
                                "fixed_f1":fixed["f1"],"fixed_precision":fixed["precision"],"fixed_recall":fixed["recall"],
                                "oracle_lag_upper_bound_ms":o_lag,"oracle_f1":o_m["f1"],
                                "oracle_recall":o_m["recall"],"oracle_precision":o_m["precision"]})
            ibi_rows.append({"subject":s,"method":method,**ibi_audit(ref,est)})
            for h in heldout(ref,est): held_rows.append({"subject":s,"method":method,**h})
            residual_rows.append({"subject":s,"method":method,**residual_summary(ref,est)})
    def write_csv(path, rows):
        if not rows: return
        keys=sorted({k for r in rows for k in r})
        with path.open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=keys); w.writeheader()
            for r in rows: w.writerow({k: json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    write_csv(OUT_ROOT/'c1_alignment_holdout_metrics.csv', held_rows)
    write_csv(OUT_ROOT/'c1_alignment_fixed_vs_oracle.csv', metric_rows)
    write_csv(OUT_ROOT/'c1_alignment_lag_invariant_ibi.csv', ibi_rows)
    write_csv(OUT_ROOT/'c1_detector_landmark_residuals.csv', residual_rows)
    (OUT_ROOT/'c1_device_sync_audit.json').write_text(json.dumps(sync_rows,ensure_ascii=False,indent=2),encoding='utf-8')
    fixed=np.mean([r['fixed_f1'] for r in metric_rows]); oracle_f=np.mean([r['oracle_f1'] for r in metric_rows])
    held_ok=[r['evaluation_f1'] for r in held_rows if r.get('status')=='ok']
    ibi_ok=[r['aligned_ibi_mae_ms'] for r in ibi_rows if r.get('aligned_ibi_mae_ms') is not None]
    sync_ident=all(x['marker_clock_audit'].get('marker_fit_available') for x in sync_rows)
    # Conservative final status: marker mapping may be identifiable, but held-out and
    # lag-invariant diagnostics do not by themselves validate HRV.
    session_held = {}
    for r in held_rows:
        if r.get('status') == 'ok':
            session_held.setdefault(r['subject'], []).append(r['evaluation_f1'])
    held_session_mean = {s: float(np.mean(v)) for s, v in session_held.items()}
    fixed_session_mean = {}
    for r in metric_rows:
        fixed_session_mean.setdefault(r['subject'], []).append(r['fixed_f1'])
    fixed_session_mean = {s: float(np.mean(v)) for s, v in fixed_session_mean.items()}
    stable_recovery_sessions = sum(
        held_session_mean.get(s, -1) - fixed_session_mean.get(s, 0) >= 0.10
        for s in held_session_mean)
    status = 'C1_ALIGNMENT_PARTIAL_ISSUE_HRV_STILL_UNVALIDATED'
    if sync_ident and (float(np.mean(held_ok)) - float(fixed) < 0.10 or stable_recovery_sessions < 2):
        status = 'C1_ALIGNMENT_NOT_PRIMARY_CAUSE_STOP_HRV_CONFIRMED'
    summary={"status":status,"no_new_heartbeat_algorithm":True,
             "fixed_delay_ms":FIXED_DELAY_MS,"primary_tolerance_ms":PRIMARY_TOL_MS,
             "lag_grid_ms":[-250,250,5],"mean_fixed_f1":float(fixed),"mean_oracle_f1":float(oracle_f),
             "mean_heldout_f1":float(np.mean(held_ok)) if held_ok else None,
             "heldout_session_mean_f1":held_session_mean,
             "fixed_session_mean_f1":fixed_session_mean,
             "stable_recovery_sessions_ge_0_10":int(stable_recovery_sessions),
             "lag_invariant_ibi_mae_mean_ms":float(np.mean(ibi_ok)) if ibi_ok else None,
             "device_sync_all_marker_fit_available":sync_ident,
             "interpretation":"Oracle lag is an upper bound only; it is not a formal performance result. IBI audit is independent of constant timestamp shift.",
             "inputs":[str(ASSET_ROOT),str(RAW_ROOT)]}
    (OUT_ROOT/'c1_alignment_protocol_repair_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    report = f'''# C1 Alignment Protocol Repair\n\n状态：`{status}`\n\n本轮只修复验证协议，不重新提取 raw ADC，不修改 C1c/C1d detector、VMD、range/bin、waveform 或 ECG R 峰检测。\n\n## 关键结论\n\n- 固定 `{FIXED_DELAY_MS:.0f} ms` 与全段 oracle lag 分开报告；oracle 只是后验上界。\n- 设备同步只通过 `.acq` 数字 marker、`events.csv` 和雷达帧 Unix ms 审计，不用心搏 F1 定义 device offset。\n- IBI 使用固定单调序列对齐，允许 missed/extra beat，不做任意时间伸缩；因此不依赖常数 lag。\n- 半段 held-out 评估把 lag 选择与评价分离。\n\n汇总：mean fixed F1 = `{fixed:.3f}`，mean oracle F1 = `{oracle_f:.3f}`，mean held-out F1 = `{float(np.mean(held_ok)) if held_ok else float('nan'):.3f}`；lag-invariant aligned IBI MAE mean = `{float(np.mean(ibi_ok)) if ibi_ok else float('nan'):.1f} ms`。这些结果不足以称为 HRV 已验证。\n\n## 概念分离\n\n`device_clock_offset` 仅指独立 marker 映射；`electromechanical_delay` 指 ECG 电活动到机械事件的生理延迟；`detector_landmark_offset` 指局部峰或 DP 选取的机械形态点差异；`beat_matching_residual` 指固定评价规则下剩余的逐搏时间误差。它们不再合并称为 ECG–radar delay。\n\n## 证据文件\n\n- `c1_device_sync_audit.json`\n- `c1_alignment_fixed_vs_oracle.csv`\n- `c1_alignment_holdout_metrics.csv`\n- `c1_alignment_lag_invariant_ibi.csv`\n- `c1_detector_landmark_residuals.csv`\n\n正式结论边界：本轮没有证明 RS6240 无法测 HRV；仅表明当前比赛周期内，逐搏 IBI/HRV 仍未获得可靠验证依据。\n'''
    (OUT_ROOT/'C1_ALIGNMENT_PROTOCOL_REPAIR.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()


