"""
experiment_hampel.py — 优化实验 2: Hampel 连续异常段替换（IBI 清洗）
====================================================================
版本: v1.0 (2026-08-11)
功能: A/B 对照 IBI 清洗策略:
      原版 = 生理范围过滤 [300, 2000] ms;
      Hampel 版 = 范围过滤后再用 Hampel（滑动中位数 MAD, 连续异常段
      整体替换为周围有效值中位数）。
      依据: Radar_monitor 仓库 _hampel_filter（逐点替换会造成阶梯偏移,
      连续段整体替换更稳）。
评估: HR 时域-频域一致性 |HR_time - HR_freq| < 5 BPM 的窗比例
      （我们的自验证指标; 无 ECG 金标准下的替代）。

数据: F:/预实验/sub-XXX_（30s 窗, 复用 assess_preexp_quality 加载）
输出: output/预实验/03_跨被试/09_预实验-优化实验/HAMPEL/
        hampel_ab_summary.json
用法:
  cd 08_算法/scripts
  python experiment_hampel.py --subjects 003,006,007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "HAMPEL"


def hampel_replace(sig, window=3, threshold=3.0):
    """Hampel 连续异常段整体替换（Radar_monitor 实现）。

    参数:
        sig: 1D 序列
        window: 半窗口（实际窗 2*window+1）
        threshold: MAD 倍数
    返回:
        替换后序列
    """
    sig = np.asarray(sig, float)
    n = len(sig)
    out = sig.copy()
    meds = np.zeros(n)
    mads = np.zeros(n)
    for i in range(n):
        w = sig[max(0, i - window):min(n, i + window + 1)]
        meds[i] = np.median(w)
        mads[i] = np.median(np.abs(w - meds[i]))
    sigma = mads / 0.6745
    sigma[sigma < 1e-12] = 1e-12
    outlier = np.abs(sig - meds) > threshold * sigma
    # 连续异常段整体替换
    i = 0
    while i < n:
        if not outlier[i]:
            i += 1
            continue
        j = i
        while j < n and outlier[j]:
            j += 1
        lo, hi = max(0, i - 1), min(n - 1, j)
        out[i:j] = np.median(sig[lo:hi + 1])
        i = j
    return out


def extract_ibi_and_freq(iq):
    """提取单窗 IBI 序列（生理范围过滤）与频域 HR, 返回 (ibi, hr_freq_bpm)。

    简化版 _heartband_assess: 候选 bin 内相位调制合格者, 取 IBI 有效率最高。
    """
    n_frames = iq.shape[0]
    power = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(power, axis=0)))
    bin_power = power[:, best_ch]
    zone = slice(apq.MIN_TARGET_BIN, apq.MAX_TARGET_BIN + 1)
    zone_power = bin_power[zone]
    cands = [zone.start + int(i) for i in np.argsort(zone_power)[::-1][:apq.MAX_CAND_BINS]]
    best = None
    for b in cands:
        if apq._phase_modulation(iq, best_ch, b, n_frames) < apq.PHASE_MOD_RAD:
            continue
        phi = signal.detrend(np.unwrap(np.angle(iq[:, b, best_ch])))
        breath_bp = apq._bandpass(phi, *apq.BR_BAND)
        br_freq = apq._dominant_freq(breath_bp, *apq.BR_BAND)
        phi_clean = apq._notch_harmonics(phi, br_freq)
        heart_bp = apq._bandpass(phi_clean, *apq.HR_BAND)
        f, pxx = signal.periodogram(heart_bp, fs=apq.FS, window="hann")
        mask = (f >= apq.HR_BAND[0]) & (f <= apq.HR_BAND[1])
        if not np.any(mask):
            continue
        hr_freq = float(f[mask][np.argmax(pxx[mask])])
        if not (apq.HR_MIN / 60 <= hr_freq <= apq.HR_MAX / 60):
            continue
        lo, hi = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
        xn = apq._bandpass(heart_bp, lo, hi)
        ref = 1.0 / hr_freq
        peaks = []
        i = 0
        while i < len(xn):
            lo_i, hi_i = int(i + 0.75 * ref * apq.FS), min(int(i + 1.35 * ref * apq.FS), len(xn))
            if lo_i >= len(xn) or hi_i <= lo_i:
                break
            p = lo_i + int(np.argmax(xn[lo_i:hi_i]))
            peaks.append(p)
            i = p + 1
        if len(peaks) >= 3:
            ibi = np.diff(peaks) / apq.FS * 1000
            ratio = np.mean((ibi >= 300) & (ibi <= 2000))
            score = ratio
            if best is None or score > best[0]:
                best = (score, ibi, hr_freq * 60)
    if best is None:
        return None, None
    return best[1], best[2]


def run_subject(subject, data_root):
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, subject)
    parts = list(apq.iter_part_files(mm_dir, subject))
    if not parts:
        return {"error": "no_parts"}
    t0, t1 = int(py_ms[0]), int(py_ms[-1])
    n_win = max(1, int((t1 - t0 - apq.WINDOW_SEC * 1000) / (apq.STEP_SEC * 1000)) + 1)

    n_eval = n_base_ok = n_hampel_ok = 0
    outlier_ratios, hr_shifts = [], []
    for k in range(n_win):
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        ibi, hr_freq = extract_ibi_and_freq(iq)
        if ibi is None or len(ibi) < 5:
            continue
        n_eval += 1
        hr_time_base = 60000.0 / np.mean(ibi)
        if abs(hr_time_base - hr_freq) < 5:
            n_base_ok += 1
        ibi_h = hampel_replace(ibi)
        hr_time_h = 60000.0 / np.mean(ibi_h)
        if abs(hr_time_h - hr_freq) < 5:
            n_hampel_ok += 1
        # Hampel 实际剔除的异常点比例（与中位数窗比较）
        med = np.median(ibi)
        mad = np.median(np.abs(ibi - med))
        sigma = mad / 0.6745
        if sigma > 1e-9:
            outlier_ratios.append(np.mean(np.abs(ibi - med) > 3 * sigma))
        hr_shifts.append(abs(hr_time_h - hr_time_base))
    return {"n_windows": n_eval,
            "base_consist": round(n_base_ok / n_eval, 3) if n_eval else 0,
            "hampel_consist": round(n_hampel_ok / n_eval, 3) if n_eval else 0,
            "median_outlier_ratio": round(float(np.median(outlier_ratios)), 4) if outlier_ratios else None,
            "median_hr_shift_bpm": round(float(np.median(hr_shifts)), 2) if hr_shifts else None,
            "max_hr_shift_bpm": round(float(np.max(hr_shifts)), 2) if hr_shifts else None}


def main():
    parser = argparse.ArgumentParser(description="Hampel IBI 清洗 A/B 实验")
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
            print(f"  原版时频一致: {r['base_consist']:.0%} | Hampel: {r['hampel_consist']:.0%} "
                  f"| Δ={r['hampel_consist'] - r['base_consist']:+.1%}")
    with open(OUT_DIR / "hampel_ab_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / 'hampel_ab_summary.json'}")


if __name__ == "__main__":
    main()


