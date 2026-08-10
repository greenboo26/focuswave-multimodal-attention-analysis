"""
experiment_cfar.py — 优化实验 4: CFAR 自适应阈值定位
====================================================================
版本: v1.0 (2026-08-11)
功能: A/B 对照定位候选筛选策略:
      原版 = 距离门控内功率 ≥ 全局最强 30% 且 ≥ 5%（固定比例）;
      CFAR 版 = 1D 单元平均 CFAR（CA-CFAR）: 候选 bin 功率须超过
      参考单元均值 × α（参考单元自适应噪声底）。
      依据: mmHRV 论文（2D CFAR 在距离-方位平面自适应阈值检测目标）。
评估: 质量评估 ok 比例 + 原因分布。

数据: F:/预实验/sub-XXX_（30s 窗 × 15s 步进, 复用 assess_preexp_quality）
输出: output/预实验/03_跨被试/09_预实验-优化实验/CFAR/
        cfar_ab_summary.json
用法:
  cd 08_算法/scripts
  python experiment_cfar.py --subjects 003,006,007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import json
from pathlib import Path

import numpy as np

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "CFAR"
CFAR_GUARD = 2    # 保护单元数（目标旁瓣保护）
CFAR_REF = 8      # 单侧参考单元数
CFAR_ALPHA = 8.0  # 阈值因子（可扫描）


def cfar_threshold(power, b, guard=CFAR_GUARD, ref=CFAR_REF, alpha=CFAR_ALPHA):
    """1D CA-CFAR 阈值: α × 参考单元均值（排除保护单元）。"""
    lo = max(0, b - guard - ref)
    hi = min(len(power), b + guard + ref + 1)
    ref_cells = np.concatenate([power[lo:b - guard], power[b + guard + 1:hi]])
    if len(ref_cells) == 0:
        return None
    return alpha * np.mean(ref_cells)


def cfar_candidates(bin_power):
    """CFAR 候选 bin: 门控内功率超过局部 CFAR 阈值的 bin。"""
    cands = []
    for b in range(apq.MIN_TARGET_BIN, apq.MAX_TARGET_BIN + 1):
        thr = cfar_threshold(bin_power, b)
        if thr is not None and bin_power[b] > thr:
            cands.append(b)
    return cands


def assess_window_cfar(iq, hr_hint=None, alpha=CFAR_ALPHA):
    """CFAR 定位版单窗评估（候选筛选换成 CFAR）。"""
    n_frames = iq.shape[0]
    result = {"ok": False, "reason": "unknown", "snr_db": None,
              "hr_bpm": None, "ibi_ratio": None, "heart_bin": None,
              "drift_bin": None, "phase_mod_rad": None}

    power = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(power, axis=0)))
    bin_power = power[:, best_ch]
    peak_power = float(bin_power.max())

    cand_bins = cfar_candidates(bin_power)
    if not cand_bins:
        gb = int(np.argmax(bin_power))
        ph_mod_g = apq._phase_modulation(iq, best_ch, gb, n_frames)
        result["phase_mod_rad"] = round(ph_mod_g, 4)
        result["reason"] = "static_target" if ph_mod_g < apq.PHASE_MOD_RAD else "no_target"
        return result
    # 若 CFAR 候选过多（杂波多）, 按功率取 top 6
    if len(cand_bins) > apq.MAX_CAND_BINS:
        cand_bins = sorted(cand_bins, key=lambda b: bin_power[b], reverse=True)[:apq.MAX_CAND_BINS]

    best = None
    for b in cand_bins:
        ph_mod = apq._phase_modulation(iq, best_ch, b, n_frames)
        if ph_mod < apq.PHASE_MOD_RAD:
            continue
        phi = np.unwrap(np.angle(iq[:, b, best_ch]))
        phi_det = apq._detrend(phi) if hasattr(apq, "_detrend") else _detrend(phi)
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


def _detrend(x):
    from scipy import signal
    return signal.detrend(x)


def run_subject(subject, data_root, alpha):
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, subject)
    parts = list(apq.iter_part_files(mm_dir, subject))
    if not parts:
        return {"error": "no_parts"}
    t0, t1 = int(py_ms[0]), int(py_ms[-1])
    n_win = max(1, int((t1 - t0 - apq.WINDOW_SEC * 1000) / (apq.STEP_SEC * 1000)) + 1)
    n_eval = b_ok = c_ok = 0
    b_reasons, c_reasons = {}, {}
    for k in range(n_win):
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        rb = apq.assess_window(iq)
        rc = assess_window_cfar(iq, alpha=alpha)
        n_eval += 1
        b_ok += rb["ok"]
        c_ok += rc["ok"]
        b_reasons[rb["reason"]] = b_reasons.get(rb["reason"], 0) + 1
        c_reasons[rc["reason"]] = c_reasons.get(rc["reason"], 0) + 1
    return {"n_windows": n_eval, "alpha": alpha,
            "base_ok": round(b_ok / n_eval, 3) if n_eval else 0,
            "cfar_ok": round(c_ok / n_eval, 3) if n_eval else 0,
            "base_reasons": b_reasons, "cfar_reasons": c_reasons}


def main():
    parser = argparse.ArgumentParser(description="CFAR 定位 A/B 实验")
    parser.add_argument("--subjects", type=str, default="003,006,007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    parser.add_argument("--alphas", type=str, default="5,8,12",
                        help="逗号分隔阈值因子扫描值")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    for sub in args.subjects.split(","):
        sub = sub.strip().zfill(3)
        for a in args.alphas.split(","):
            a = float(a.strip())
            print(f"[sub-{sub} α={a}] ...")
            r = run_subject(sub, data_root, a)
            key = f"sub-{sub}_alpha{a}"
            result[key] = r
            if "error" not in r:
                print(f"  原版 ok: {r['base_ok']:.0%} | CFAR ok: {r['cfar_ok']:.0%} | Δ={r['cfar_ok'] - r['base_ok']:+.1%}")
    with open(OUT_DIR / "cfar_ab_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / 'cfar_ab_summary.json'}")


if __name__ == "__main__":
    main()
