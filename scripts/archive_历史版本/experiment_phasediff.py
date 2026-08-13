"""
experiment_phasediff.py — 优化实验 3: 相位差分替代 detrend
====================================================================
版本: v1.0 (2026-08-11)
功能: A/B 对照相位预处理策略:
      原版 = unwrap + 线性 detrend（静态杂波对消）;
      差分版 = unwrap + 一阶差分 + Savitzky-Golay 平滑
      （倪杰2024: 相位差分增强心跳、抑制相位漂移）。
评估: 质量评估 ok 比例（SNR≥3dB 且 IBI 有效率≥0.8）+ 原因分布。

数据: F:/预实验/sub-XXX_（30s 窗 × 15s 步进, 复用 assess_preexp_quality）
输出: output/预实验/03_跨被试/09_预实验-优化实验/PHASEDiff/
        phasediff_ab_summary.json
用法:
  cd 08_算法/scripts
  python experiment_phasediff.py --subjects 003,006,007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "PHASEDiff"
SG_WINDOW = 11    # SG 平滑窗（差分后噪声放大, 需平滑）
SG_POLY = 2       # SG 多项式阶


def assess_window_phasediff(iq, hr_hint=None):
    """差分版单窗评估（替换 detrend 为 diff+SG）。"""
    n_frames = iq.shape[0]
    result = {"ok": False, "reason": "unknown", "snr_db": None,
              "hr_bpm": None, "ibi_ratio": None, "heart_bin": None,
              "drift_bin": None, "phase_mod_rad": None}

    power = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(power, axis=0)))
    bin_power = power[:, best_ch]
    peak_power = float(bin_power.max())
    zone = slice(apq.MIN_TARGET_BIN, apq.MAX_TARGET_BIN + 1)
    if zone.start >= len(bin_power):
        result["reason"] = "no_target"
        return result
    zone_power = bin_power[zone]
    zone_max = float(zone_power.max())
    if zone_max < peak_power * apq.POWER_RATIO_TARGET or zone_max < peak_power * 0.05:
        gb = int(np.argmax(bin_power))
        ph_mod_g = apq._phase_modulation(iq, best_ch, gb, n_frames)
        result["phase_mod_rad"] = round(ph_mod_g, 4)
        result["reason"] = "static_target" if ph_mod_g < apq.PHASE_MOD_RAD else "no_target"
        return result
    cand_bins = [zone.start + int(idx) for idx in
                 np.argsort(zone_power)[::-1][:apq.MAX_CAND_BINS]]

    best = None
    for b in cand_bins:
        ph_mod = apq._phase_modulation(iq, best_ch, b, n_frames)
        if ph_mod < apq.PHASE_MOD_RAD:
            continue
        phi = np.unwrap(np.angle(iq[:, b, best_ch]))
        # 差分版相位预处理
        phi_diff = np.diff(phi)
        if len(phi_diff) >= SG_WINDOW:
            phi_det = signal.savgol_filter(phi_diff, SG_WINDOW, SG_POLY)
        else:
            phi_det = phi_diff
        snr_db, hr_bpm, ibi_ratio, _ = apq._heartband_assess(phi_det, hr_hint)
        if snr_db is None:
            continue
        score = (ibi_ratio >= apq.IBI_OK_RATIO, snr_db >= apq.SNR_OK_DB, ibi_ratio, snr_db)
        if best is None or score > best[0]:
            best = (score, {"heart_bin": int(b), "snr_db": round(float(snr_db), 2),
                            "hr_bpm": round(float(hr_bpm), 1) if hr_bpm else None,
                            "ibi_ratio": round(float(ibi_ratio), 3),
                            "phase_mod_rad": round(ph_mod, 4)})
    if best is None:
        result["phase_mod_rad"] = round(
            apq._phase_modulation(iq, best_ch, cand_bins[0], n_frames), 4)
        result["reason"] = "static_target"
        return result
    result.update(best[1])

    half = n_frames // 2
    if half >= 100:
        p1 = np.mean(np.abs(iq[:half]) ** 2, axis=0)
        p2 = np.mean(np.abs(iq[half:]) ** 2, axis=0)
        result["drift_bin"] = int(abs(int(np.argmax(p1[:, best_ch])) -
                                      int(np.argmax(p2[:, best_ch]))))
    else:
        result["drift_bin"] = 0

    if result["snr_db"] >= apq.SNR_OK_DB and result["ibi_ratio"] >= apq.IBI_OK_RATIO:
        result["ok"] = True
        result["reason"] = "ok"
    elif result["snr_db"] < apq.SNR_OK_DB:
        result["reason"] = "low_snr"
    else:
        result["reason"] = "low_ibi"
    return result


def run_subject(subject, data_root):
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, subject)
    parts = list(apq.iter_part_files(mm_dir, subject))
    if not parts:
        return {"error": "no_parts"}
    t0, t1 = int(py_ms[0]), int(py_ms[-1])
    n_win = max(1, int((t1 - t0 - apq.WINDOW_SEC * 1000) / (apq.STEP_SEC * 1000)) + 1)
    n_eval = b_ok = d_ok = 0
    b_reasons, d_reasons = {}, {}
    for k in range(n_win):
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        rb = apq.assess_window(iq)
        rd = assess_window_phasediff(iq)
        n_eval += 1
        b_ok += rb["ok"]
        d_ok += rd["ok"]
        b_reasons[rb["reason"]] = b_reasons.get(rb["reason"], 0) + 1
        d_reasons[rd["reason"]] = d_reasons.get(rd["reason"], 0) + 1
    return {"n_windows": n_eval,
            "base_ok": round(b_ok / n_eval, 3) if n_eval else 0,
            "diff_ok": round(d_ok / n_eval, 3) if n_eval else 0,
            "base_reasons": b_reasons, "diff_reasons": d_reasons}


def main():
    parser = argparse.ArgumentParser(description="相位差分 A/B 实验")
    parser.add_argument("--subjects", type=str, default="003,006,007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    for sub in args.subjects.split(","):
        sub = sub.strip().zfill(3)
        print(f"[sub-{sub}] ...")
        r = run_subject(sub, data_root)
        result[sub] = r
        if "error" not in r:
            print(f"  原版 ok: {r['base_ok']:.0%} | 差分版 ok: {r['diff_ok']:.0%} | Δ={r['diff_ok'] - r['base_ok']:+.1%}")
    with open(OUT_DIR / "phasediff_ab_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / 'phasediff_ab_summary.json'}")


if __name__ == "__main__":
    main()
