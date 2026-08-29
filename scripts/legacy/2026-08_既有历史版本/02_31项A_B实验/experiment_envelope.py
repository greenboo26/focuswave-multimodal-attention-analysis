"""
experiment_envelope.py — 优化实验 6: 包络归一化再找峰
====================================================================
版本: v1.0 (2026-08-11)
功能: A/B 对照峰值检测前的预处理:
      原版 = 窄带带通信号直接找局部最大;
      包络版 = 移动平均包络（abs 信号）估计 → 信号/包络比值归一化
      → 再找峰（对抗幅度慢漂移, 降低伪峰）。
      依据: mmHRV 论文（峰值检测前移动平均包络归一化）。
评估: 对原版 best bin 重评估, 对比 ok 比例/IBI 有效率/HR 稳定性。

数据: F:/预实验/sub-XXX_（30s 窗 × 15s 步进, 复用 assess_preexp_quality）
输出: output/预实验/03_跨被试/09_预实验-优化实验/ENVELOPE/
        envelope_ab_summary.json
用法:
  cd 08_算法/scripts
  python experiment_envelope.py --subjects 003,006,007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "ENVELOPE"
ENV_WINDOW_S = 2.0  # 包络移动平均窗（秒）


def assess_with_envelope(iq, hr_hint=None):
    """包络归一化版评估（对原版 best bin 重评估）。"""
    base = apq.assess_window(iq, hr_hint)
    if not base["ok"] or base.get("heart_bin") is None:
        return base
    n_frames = iq.shape[0]
    power = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(power, axis=0)))
    b = base["heart_bin"]
    phi = np.unwrap(np.angle(iq[:, b, best_ch]))
    phi_det = signal.detrend(phi)

    # 同 _heartband_assess 到窄带检测前
    breath_bp = apq._bandpass(phi_det, *apq.BR_BAND)
    br_freq = apq._dominant_freq(breath_bp, *apq.BR_BAND)
    phi_clean = apq._notch_harmonics(phi_det, br_freq)
    heart_bp = apq._bandpass(phi_clean, *apq.HR_BAND)
    f, pxx = signal.periodogram(heart_bp, fs=apq.FS, window="hann")
    mask_hb = (f >= apq.HR_BAND[0]) & (f <= apq.HR_BAND[1])
    hr_freq_hz = float(f[mask_hb][np.argmax(pxx[mask_hb])])
    noise_floor = np.median(pxx[mask_hb])
    snr_db = 10 * np.log10(pxx[mask_hb].max() / (noise_floor + 1e-12))
    if not (apq.HR_MIN / 60 <= hr_freq_hz <= apq.HR_MAX / 60) and hr_hint is not None:
        hr_freq_hz = hr_hint / 60.0

    # 包络归一化
    lo_nb, hi_nb = max(hr_freq_hz - 0.05, 0.5), hr_freq_hz + 0.05
    xn = apq._bandpass(heart_bp, lo_nb, hi_nb)
    win = max(int(ENV_WINDOW_S * apq.FS), 5)
    env = np.convolve(np.abs(xn), np.ones(win) / win, mode="same")
    env[env < 1e-9] = 1e-9
    xn_norm = xn / env

    # 窄带逐拍（与 _detect_peaks_narrowband 同逻辑）
    ref = 1.0 / hr_freq_hz
    n_pts = len(xn_norm)
    peaks = []
    i = 0
    while i < n_pts:
        lo_i, hi_i = int(i + 0.75 * ref * apq.FS), min(int(i + 1.35 * ref * apq.FS), n_pts)
        if lo_i >= n_pts or hi_i <= lo_i:
            break
        p = lo_i + int(np.argmax(xn_norm[lo_i:hi_i]))
        peaks.append(p)
        i = p + 1

    ibi_ratio, hr_bpm = 0.0, None
    if len(peaks) >= 3:
        ibi_ms = np.diff(peaks) / apq.FS * 1000
        valid = (ibi_ms >= apq.IBI_MIN) & (ibi_ms <= apq.IBI_MAX)
        ibi_ratio = float(np.mean(valid))
        ibi_clean = ibi_ms[valid]
        if len(ibi_clean) >= 3:
            hr_bpm = 60000.0 / np.mean(ibi_clean)

    out = dict(base)
    out["snr_db"] = round(float(snr_db), 2)
    out["hr_bpm"] = round(float(hr_bpm), 1) if hr_bpm else None
    out["ibi_ratio"] = round(float(ibi_ratio), 3)
    if snr_db >= apq.SNR_OK_DB and ibi_ratio >= apq.IBI_OK_RATIO:
        out["ok"] = True
        out["reason"] = "ok"
    elif snr_db < apq.SNR_OK_DB:
        out["ok"] = False
        out["reason"] = "low_snr"
    else:
        out["ok"] = False
        out["reason"] = "low_ibi"
    return out


def run_subject(subject, data_root):
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, subject)
    parts = list(apq.iter_part_files(mm_dir, subject))
    if not parts:
        return {"error": "no_parts"}
    t0, t1 = int(py_ms[0]), int(py_ms[-1])
    n_win = max(1, int((t1 - t0 - apq.WINDOW_SEC * 1000) / (apq.STEP_SEC * 1000)) + 1)
    n_eval = b_ok = e_ok = 0
    hr_diff = []
    for k in range(n_win):
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        rb = apq.assess_window(iq)
        re_ = assess_with_envelope(iq)
        n_eval += 1
        b_ok += rb["ok"]
        e_ok += re_["ok"]
        if rb.get("hr_bpm") and re_.get("hr_bpm"):
            hr_diff.append(abs(rb["hr_bpm"] - re_["hr_bpm"]))
    return {"n_windows": n_eval,
            "base_ok": round(b_ok / n_eval, 3) if n_eval else 0,
            "env_ok": round(e_ok / n_eval, 3) if n_eval else 0,
            "median_hr_diff": round(float(np.median(hr_diff)), 2) if hr_diff else None,
            "max_hr_diff": round(float(np.max(hr_diff)), 2) if hr_diff else None}


def main():
    parser = argparse.ArgumentParser(description="包络归一化 A/B 实验")
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
            print(f"  原版 ok: {r['base_ok']:.0%} | 包络版 ok: {r['env_ok']:.0%} | Δ={r['env_ok'] - r['base_ok']:+.1%}"
                  f" | HR差异中位 {r['median_hr_diff']}bpm")
    with open(OUT_DIR / "envelope_ab_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / 'envelope_ab_summary.json'}")


if __name__ == "__main__":
    main()


