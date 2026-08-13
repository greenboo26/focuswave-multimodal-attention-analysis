"""
experiment_spc.py — 优化实验 1: SPC 相邻单元相位相干性定位评分
====================================================================
版本: v1.0 (2026-08-11)
功能: A/B 对照 assess_preexp_quality 的定位策略:
      原版 = 距离门控内按功率排序取候选 bin;
      SPC 版 = 功率门控筛选后, 候选 bin 按其相位差分与相邻 ±2 bin
      的皮尔逊相关（取最大 |r|）重新排序, 优先评估 SPC 高的 bin。
      依据: Radar_monitor 仓库（胸腔反射覆盖相邻距离单元, 真实体征
      单元的相位与邻居相干; 噪声单元相位随机）。

数据: F:/预实验/sub-XXX_（同 assess_preexp_quality 口径, 30s 窗 × 15s 步进）
输出: output/预实验/03_跨被试/09_预实验-优化实验/SPC/
        spc_ab_summary.json   ← 每被试 A/B ok 比例对比
用法:
  cd 08_算法/scripts
  python experiment_spc.py --subjects 003 006 007 --data-root F:/预实验
依赖: numpy, scipy（复用 assess_preexp_quality 的加载/评估函数）
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "SPC"
SPC_RADIUS = 2     # 相邻 bin 半径（±2 bin ≈ ±7.5cm）


def assess_window_spc(iq, hr_hint=None):
    """SPC 版单窗评估: 功率门控后按 SPC 排序候选。

    参数:
        iq: (n, 256, 8) complex64 窗数据
        hr_hint: 参考心率
    返回:
        dict（同 assess_window 结构, 附 spc_best 字段）
    """
    n_frames = iq.shape[0]
    result = {"ok": False, "reason": "unknown", "snr_db": None,
              "hr_bpm": None, "ibi_ratio": None, "heart_bin": None,
              "drift_bin": None, "phase_mod_rad": None}

    power = np.mean(np.abs(iq) ** 2, axis=0)
    ch_power = np.mean(power, axis=0)
    best_ch = int(np.argmax(ch_power))
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
    # 功率候选扩到 12 个, 再按 SPC 重排取 MAX_CAND_BINS
    cand_bins = [zone.start + int(idx) for idx in
                 np.argsort(zone_power)[::-1][:12]]

    # SPC 评分: 相位差分与相邻 ±SPC_RADIUS bin 的最大 |r|
    spc = {}
    for b in cand_bins:
        phi = np.unwrap(np.angle(iq[:, b, best_ch]))
        pd = np.diff(phi)
        rs = []
        for nb in range(max(0, b - SPC_RADIUS), min(256, b + SPC_RADIUS + 1)):
            if nb == b:
                continue
            pd2 = np.diff(np.unwrap(np.angle(iq[:, nb, best_ch])))
            r = stats.pearsonr(pd, pd2)[0]
            rs.append(abs(r) if r == r else 0.0)
        spc[b] = max(rs) if rs else 0.0
    cand_bins.sort(key=lambda b: spc[b], reverse=True)
    cand_bins = cand_bins[:apq.MAX_CAND_BINS]
    result["spc_best"] = round(float(spc[cand_bins[0]]), 3) if cand_bins else None

    best = None
    for b in cand_bins:
        ph_mod = apq._phase_modulation(iq, best_ch, b, n_frames)
        if ph_mod < apq.PHASE_MOD_RAD:
            continue
        phi = np.unwrap(np.angle(iq[:, b, best_ch]))
        phi_det = signal_detrend(phi)
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
        b1 = int(np.argmax(p1[:, best_ch]))
        b2 = int(np.argmax(p2[:, best_ch]))
        result["drift_bin"] = int(abs(b1 - b2))
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


def signal_detrend(x):
    from scipy import signal
    return signal.detrend(x)


def run_subject(subject: str, data_root: Path) -> dict:
    """对单个被试跑 A/B 全窗评估。"""
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, subject)
    parts = list(apq.iter_part_files(mm_dir, subject))
    if not parts:
        return {"error": "no_parts"}
    t0, t1 = int(py_ms[0]), int(py_ms[-1])
    n_win = max(1, int((t1 - t0 - apq.WINDOW_SEC * 1000) / (apq.STEP_SEC * 1000)) + 1)

    base_ok = spc_ok = 0
    base_reasons, spc_reasons = {}, {}
    n_eval = 0
    for k in range(n_win):
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        r_base = apq.assess_window(iq)
        r_spc = assess_window_spc(iq)
        n_eval += 1
        if r_base["ok"]:
            base_ok += 1
        if r_spc["ok"]:
            spc_ok += 1
        base_reasons[r_base["reason"]] = base_reasons.get(r_base["reason"], 0) + 1
        spc_reasons[r_spc["reason"]] = spc_reasons.get(r_spc["reason"], 0) + 1
    return {"n_windows": n_eval,
            "base_ok_ratio": round(base_ok / n_eval, 3) if n_eval else 0,
            "spc_ok_ratio": round(spc_ok / n_eval, 3) if n_eval else 0,
            "base_reasons": base_reasons, "spc_reasons": spc_reasons}


def main():
    parser = argparse.ArgumentParser(description="SPC 定位 A/B 实验")
    parser.add_argument("--subjects", type=str, default="003,006,007",
                        help="逗号分隔被试编号")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    result = {}
    for sub in args.subjects.split(","):
        sub = sub.strip().zfill(3)
        print(f"[sub-{sub}] 全窗 A/B 评估...")
        r = run_subject(sub, data_root)
        result[sub] = r
        if "error" in r:
            print(f"  {r['error']}")
            continue
        print(f"  原版 ok: {r['base_ok_ratio']:.0%} | SPC 版 ok: {r['spc_ok_ratio']:.0%} "
              f"| Δ={r['spc_ok_ratio'] - r['base_ok_ratio']:+.1%}")
    json_path = OUT_DIR / "spc_ab_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {json_path}")


if __name__ == "__main__":
    main()
