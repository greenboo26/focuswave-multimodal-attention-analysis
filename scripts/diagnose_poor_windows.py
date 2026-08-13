"""
休息段 poor 窗细分诊断
======================
对 9 名被试 rest 分析中被拒的 32 个 poor 窗, 重放判定流程并逐级记录卡点:

  第1关 动作帧占比 > 30% → 整窗拒
  第2关 候选 bin 收集为空 → 拒
  第3关 逐候选心跳评估 (峰值数/IBI 数/HR 范围/CV/频域一致性)
  第4关 段参考修正重检

用法:
    cd 08_算法/scripts
    python diagnose_poor_windows.py

输出: output/预实验/03_跨被试/09_预实验-restHRV变化/poor_window_diagnosis.csv
"""

import csv
import json
from pathlib import Path

import numpy as np

import analyze_mmwave_hrv as rhrv

# ============================================================
# 配置
# ============================================================
DATA_ROOT = Path("J:/预实验")
SUBJECTS = ["000", "003", "004", "005", "006", "007", "008", "009", "010"]
REST_DIR = Path(__file__).resolve().parent.parent / "output" / "预实验" / "02_全程窗"
OUT_CSV = (Path(__file__).resolve().parent.parent / "output" / "预实验"
           / "03_跨被试" / "09_预实验-restHRV变化" / "poor_window_diagnosis.csv")

# 心跳评估各步阈值 (与 analyze_mmwave_hrv 一致)
MIN_PEAKS = 5               # 窄带峰值最少个数
MIN_PEAKS_WIN = 15          # 60s 窗最少合格 IBI 数 (max(15, 窗长×0.5))
HR_MIN, HR_MAX = 40.0, 100.0
IBI_CV_MAX = 0.12
FREQ_CONSIST_BPM = 5        # 逐拍 HR 与主频差 (bpm)


def diagnose_evaluate(iq, ch, b) -> dict:
    """逐步重放 evaluate_heart_bin 并记录每一步。

    参数:
        iq: (n, 256, 8) 窗数据
        ch: 通道索引
        b: 距离 bin
    返回:
        dict: {hp_n, ibi_raw_n, ibi_clean_n, hr, cv, freq_hr, freq_diff,
               fail_step} fail_step 为空=合格
    """
    out = {}
    phi = np.unwrap(np.angle(iq[:, b, ch]))
    br_freq_here = rhrv.estimate_freq_periodogram(
        rhrv._sos_bandpass(phi, 0.1, 0.5), 0.1, 0.5)
    phi = rhrv.suppress_harmonics(phi, br_freq_here)
    heart_bp = rhrv._sos_bandpass(phi, 0.8, 2.5)
    hr_freq = rhrv.estimate_freq_periodogram(heart_bp, 0.8, 2.5)
    out["freq_hr"] = round(hr_freq * 60, 1) if hr_freq else None
    hp = rhrv.detect_heart_peaks_narrowband(heart_bp, hr_freq)
    out["hp_n"] = int(len(hp))
    if len(hp) < MIN_PEAKS:
        out["fail_step"] = "峰值<5"
        return out
    ibi_ms = np.diff(hp) / rhrv.FS * 1000
    ibi_clean = ibi_ms[(ibi_ms >= 300) & (ibi_ms <= 2000)]
    out["ibi_raw_n"] = int(len(ibi_ms))
    out["ibi_clean_n"] = int(len(ibi_clean))
    min_peaks = max(MIN_PEAKS_WIN, int(iq.shape[0] / rhrv.FS * rhrv.MIN_PEAKS_RATE))
    if len(ibi_clean) < min_peaks:
        out["fail_step"] = f"合格IBI<{min_peaks}"
        return out
    hr = 60000 / np.mean(ibi_clean)
    cv = np.std(ibi_clean) / np.mean(ibi_clean)
    out["hr"] = round(hr, 1)
    out["cv"] = round(cv, 3)
    if not (HR_MIN <= hr <= HR_MAX):
        out["fail_step"] = f"HR出范围({hr:.0f})"
        return out
    if cv >= IBI_CV_MAX:
        out["fail_step"] = f"CV≥0.12({cv:.3f})"
        return out
    if hr_freq is not None and abs(hr - hr_freq * 60) > FREQ_CONSIST_BPM:
        out["fail_step"] = f"频域不一致({hr:.0f}vs{hr_freq*60:.0f})"
        return out
    out["fail_step"] = ""
    return out


def diagnose_window(iq, med_hr_hint) -> dict:
    """重放 analyze_window_auto 判定链, 记录失败关卡。

    参数:
        iq: 窗数据
        med_hr_hint: 段参考心率 (bpm) 或 None
    返回:
        dict: 诊断明细
    """
    # 第1关: 动作帧占比
    _, motion_ratio = rhrv.detect_motion_frames(iq)
    if motion_ratio > rhrv.MOTION_RATIO_MAX:
        return {"gate": "动作帧>30%", "motion_ratio": round(motion_ratio, 3)}

    # 第2关: 候选收集
    cands = rhrv.collect_candidates(iq)
    if not cands:
        return {"gate": "无候选bin", "motion_ratio": round(motion_ratio, 3)}

    # 第3关: 逐候选评估 (记录每个候选的失败步骤)
    cand_details = []
    evals = []
    for ch, b in cands:
        dg = diagnose_evaluate(iq, ch, b)
        dg["ch"] = ch
        dg["bin"] = b
        cand_details.append(dg)
        if not dg["fail_step"]:
            # 合格: 还原评估值
            phi = np.unwrap(np.angle(iq[:, b, ch]))
            br_f = rhrv.estimate_freq_periodogram(
                rhrv._sos_bandpass(phi, 0.1, 0.5), 0.1, 0.5)
            phi2 = rhrv.suppress_harmonics(phi, br_f)
            hb = rhrv._sos_bandpass(phi2, 0.8, 2.5)
            hf = rhrv.estimate_freq_periodogram(hb, 0.8, 2.5)
            hp = rhrv.detect_heart_peaks_narrowband(hb, hf)
            ibi = np.diff(hp) / rhrv.FS * 1000
            ibi = ibi[(ibi >= 300) & (ibi <= 2000)]
            evals.append(({"hr": 60000 / np.mean(ibi),
                           "cv": np.std(ibi) / np.mean(ibi)}, ch, b))

    if not evals:
        # 第4关: 段参考修正重检
        if med_hr_hint is not None:
            retry_details = []
            for ch, b in cands:
                # 简化: 记录主频锁错情况
                phi = np.unwrap(np.angle(iq[:, b, ch]))
                br_f = rhrv.estimate_freq_periodogram(
                    rhrv._sos_bandpass(phi, 0.1, 0.5), 0.1, 0.5)
                phi2 = rhrv.suppress_harmonics(phi, br_f)
                hb = rhrv._sos_bandpass(phi2, 0.8, 2.5)
                hf = rhrv.estimate_freq_periodogram(hb, 0.8, 2.5)
                retry_details.append(
                    f"ch{ch}b{b}:主频{hf*60:.0f}bpm" if hf else f"ch{ch}b{b}:无主频")
            return {"gate": "候选全部不合格(重检也失败)",
                    "motion_ratio": round(motion_ratio, 3),
                    "n_cands": len(cands),
                    "cand_details": cand_details,
                    "retry": retry_details,
                    "hint": med_hr_hint}
        return {"gate": "候选全部不合格(无段参考)",
                "motion_ratio": round(motion_ratio, 3),
                "n_cands": len(cands),
                "cand_details": cand_details}
    return {"gate": "合格(对照用)", "motion_ratio": round(motion_ratio, 3)}


def main() -> None:
    """对 9 人 32 个 poor 窗逐一诊断并保存 CSV。"""
    rows = []
    for sub in SUBJECTS:
        # 设置模块全局 (load_frames 依赖)
        rhrv.SUBJECT = sub
        rhrv.DATA_ROOT = DATA_ROOT
        rhrv.MMWAVE_DIR = DATA_ROOT / f"sub-{sub}_" / "mmwave"
        rhrv.BEH_TIMELINE = DATA_ROOT / f"sub-{sub}_" / "beh" / "master_timeline.csv"
        frame_idx, py_ms = rhrv.load_timestamps()
        rhrv.FIRST_FRAME = int(frame_idx[0])
        rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK
        segments = rhrv.parse_rest_segments()

        # 读该被试 rest JSON, 取 poor 窗
        jpath = REST_DIR / f"09_预实验-SUB{sub}-REST-HRV" / f"sub{sub}_rest_hrv_windows.json"
        d = json.load(open(jpath, encoding="utf-8"))
        poor = [r for r in d.get("rows", []) if r.get("quality") != "ok"]

        for r in poor:
            seg_idx = int(r["segment"].replace("rest", "")) - 1
            if seg_idx >= len(segments):
                continue
            seg = segments[seg_idx]
            w0 = seg["t0_ms"] + r["t_start_s"] * 1000
            w1 = seg["t0_ms"] + r["t_end_s"] * 1000
            # 时间 → 行索引 → 帧号 (searchsorted 返回行索引, 必须经 frame_idx 转帧号)
            fa = int(np.searchsorted(py_ms, w0))
            fb = int(np.searchsorted(py_ms, w1))
            if fb - fa < int(0.5 * 60 * rhrv.FS):
                rows.append({"subject": sub, "segment": r["segment"],
                             "window": r["window"], "gate": "窗长不足"})
                continue
            try:
                iq = rhrv.load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
            except ValueError:
                rows.append({"subject": sub, "segment": r["segment"],
                             "window": r["window"], "gate": "数据缺失(npz边界)"})
                continue
            # 段参考: 同段 ok 窗 HR 中位数
            ok_hrs = [x.get("hr_time_bpm") for x in d.get("rows", [])
                      if x.get("quality") == "ok" and x.get("segment") == r["segment"]
                      and x.get("hr_time_bpm")]
            hint = float(np.median(ok_hrs)) if ok_hrs else None
            dg = diagnose_window(iq, hint)
            dg.update({"subject": sub, "segment": r["segment"], "window": r["window"]})
            # cand_details 压缩为字符串
            if "cand_details" in dg:
                dg["cand_summary"] = "; ".join(
                    f"ch{x['ch']}b{x['bin']}:{x['fail_step'] or 'OK'}"
                    f"(hp{x.get('hp_n')},ibi{x.get('ibi_clean_n')},"
                    f"hr{x.get('hr')},cv{x.get('cv')})" for x in dg["cand_details"])
                del dg["cand_details"]
            if "retry" in dg:
                dg["retry"] = "; ".join(dg["retry"])
            rows.append(dg)
            print(f"{sub} {r['segment']}-w{r['window']}: {dg['gate']} "
                  f"(motion={dg.get('motion_ratio')})")

    # 保存 CSV
    fieldnames = ["subject", "segment", "window", "gate", "motion_ratio",
                  "n_cands", "cand_summary", "retry", "hint"]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    # 汇总
    from collections import Counter
    gates = Counter(r["gate"].split("(")[0] for r in rows)
    print(f"\n共诊断 {len(rows)} 窗, 卡点分布:")
    for k, v in gates.most_common():
        print(f"  {k}: {v}")
    print(f"输出: {OUT_CSV}")


if __name__ == "__main__":
    main()
