"""
experiment_ceemdan.py — 优化实验 7: CEEMDAN 预分组 + VMD 精细分离（抽样）
====================================================================
版本: v1.0 (2026-08-11)
功能: 抽样验证 CEEMDAN 呼吸/心跳分离 vs 现有谐波陷波:
      对原版 ok 窗的选定 bin, CEEMDAN 分解 → 按中心频率分组
      （0.8-2.5Hz 心跳带）→ 重构心跳 → 心跳评估（SNR/IBI）。
      目标: 谐波陷波是否已覆盖 CEEMDAN 的作用（呼吸污染心跳带）。
依据: Radar_monitor extract_resp_heart（CEEMDAN → 中心频率分组）。
评估: ok 窗判定一致性 + SNR/IBI 变化。

数据: F:/预实验/sub-003_（抽样前 30 个 ok 窗, CEEMDAN 计算量大）
输出: output/预实验/03_跨被试/09_预实验-优化实验/CEEMDAN/
        ceemdan_sample_summary.json
用法:
  cd 08_算法/scripts
  python experiment_ceemdan.py --data-root F:/预实验 --n-windows 30
依赖: numpy, scipy, PyEMD
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal
from PyEMD import CEEMDAN

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "CEEMDAN"


def ceemdan_heart(phi_det):
    """CEEMDAN 分解 → 心跳带中心频率分量重构。"""
    try:
        ceemdan = CEEMDAN(trials=5)
        imfs = ceemdan(phi_det)
    except Exception:
        return None
    heart = None
    for imf in imfs:
        f, pxx = signal.periodogram(imf, fs=apq.FS, window="hann")
        mask = (f >= apq.HR_BAND[0]) & (f <= apq.HR_BAND[1])
        if not np.any(mask):
            continue
        # 心跳带能量占比
        band_energy = np.sum(pxx[mask])
        total = np.sum(pxx) + 1e-12
        if band_energy / total > 0.5:
            heart = imf if heart is None else heart + imf
    return heart


def assess_heart_signal(heart):
    """对重构心跳信号做 SNR/IBI 评估（复用 _heartband_assess 逻辑）。"""
    f, pxx = signal.periodogram(heart, fs=apq.FS, window="hann")
    mask = (f >= apq.HR_BAND[0]) & (f <= apq.HR_BAND[1])
    if not np.any(mask):
        return None
    hr_freq_hz = float(f[mask][np.argmax(pxx[mask])])
    snr_db = 10 * np.log10(pxx[mask].max() / (np.median(pxx[mask]) + 1e-12))
    lo, hi = max(hr_freq_hz - 0.05, 0.5), hr_freq_hz + 0.05
    xn = apq._bandpass(heart, lo, hi)
    ref = 1.0 / hr_freq_hz
    peaks = []
    i = 0
    while i < len(xn):
        lo_i, hi_i = int(i + 0.75 * ref * apq.FS), min(int(i + 1.35 * ref * apq.FS), len(xn))
        if lo_i >= len(xn) or hi_i <= lo_i:
            break
        p = lo_i + int(np.argmax(xn[lo_i:hi_i]))
        peaks.append(p)
        i = p + 1
    ibi_ratio = 0.0
    if len(peaks) >= 3:
        ibi = np.diff(peaks) / apq.FS * 1000
        ibi_ratio = float(np.mean((ibi >= apq.IBI_MIN) & (ibi <= apq.IBI_MAX)))
    return {"snr_db": round(float(snr_db), 2), "ibi_ratio": round(float(ibi_ratio), 3),
            "ok": snr_db >= apq.SNR_OK_DB and ibi_ratio >= apq.IBI_OK_RATIO}


def main():
    parser = argparse.ArgumentParser(description="CEEMDAN 预分组抽样验证")
    parser.add_argument("--subject", type=str, default="003")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    parser.add_argument("--n-windows", type=int, default=30)
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sub = args.subject.zfill(3)

    mm_dir = data_root / f"sub-{sub}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, sub)
    t0 = int(py_ms[0])
    n_win = max(1, int((int(py_ms[-1]) - t0 - apq.WINDOW_SEC * 1000) / (apq.STEP_SEC * 1000)) + 1)

    rows = []
    n_tested = 0
    for k in range(min(n_win, args.n_windows * 3)):  # 需要 30 个 ok 窗, 多扫
        if n_tested >= args.n_windows:
            break
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, sub, frame_idx, fa, fb)
        base = apq.assess_window(iq)
        if not base["ok"] or base.get("heart_bin") is None:
            continue
        n_tested += 1
        power = np.mean(np.abs(iq) ** 2, axis=0)
        best_ch = int(np.argmax(np.mean(power, axis=0)))
        phi = np.unwrap(np.angle(iq[:, base["heart_bin"], best_ch]))
        phi_det = signal.detrend(phi)
        heart = ceemdan_heart(phi_det)
        if heart is None:
            rows.append({"win": k, "base_ok": True, "ceemdan_ok": None, "note": "decompose_fail"})
            continue
        r = assess_heart_signal(heart)
        rows.append({"win": k, "base_ok": True,
                     "base_snr": base["snr_db"], "base_ibi": base["ibi_ratio"],
                     "ceemdan_ok": r["ok"] if r else None,
                     "ceemdan_snr": r["snr_db"] if r else None,
                     "ceemdan_ibi": r["ibi_ratio"] if r else None})
        print(f"  win{k}: 原版 ok(SNR {base['snr_db']} IBI {base['ibi_ratio']}) | "
              f"CEEMDAN {'ok' if r and r['ok'] else 'FAIL'}(SNR {r['snr_db'] if r else '-'} IBI {r['ibi_ratio'] if r else '-'})")

    ok_agree = sum(1 for x in rows if x.get("ceemdan_ok") is True)
    ok_fail = sum(1 for x in rows if x.get("ceemdan_ok") is False)
    fail = sum(1 for x in rows if x.get("ceemdan_ok") is None)
    summary = {"n_ok_windows": len(rows), "ceemdan_agree_ok": ok_agree,
               "ceemdan_fail": ok_fail, "decompose_fail": fail,
               "agree_ratio": round(ok_agree / len(rows), 3) if rows else 0}
    with open(OUT_DIR / "ceemdan_sample_summary.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"\n汇总: 原版 ok 窗 {len(rows)} 个, CEEMDAN 也 ok {ok_agree} 个, "
          f"CEEMDAN 失败 {ok_fail} 个, 分解失败 {fail} 个")
    print(f"[json] {OUT_DIR / 'ceemdan_sample_summary.json'}")


if __name__ == "__main__":
    main()


