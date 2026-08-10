"""
experiment_ssa.py — 优化实验 5: SSA 奇异谱分析降噪
====================================================================
版本: v1.0 (2026-08-11)
功能: A/B 对照心跳评估前的相位信号降噪:
      原版 = detrend + 呼吸谐波陷波 + 心跳带带通;
      SSA 版 = 在上述之前先做 SSA 降噪重构（Hankel 矩阵 SVD,
      累积能量 95% 截断重构; 窗口 L=min(10s 帧数, N//2)）。
      依据: 倪杰2024（SSA 优于低通/PCA, 窗 10s, 95% 能量）;
            Radar_monitor CSSA（级联两阶段）。
评估: 质量评估 ok 比例 + 原因分布。

数据: F:/预实验/sub-XXX_（30s 窗 × 15s 步进, 复用 assess_preexp_quality）
输出: output/预实验/03_跨被试/09_预实验-优化实验/SSA/
        ssa_ab_summary.json
用法:
  cd 08_算法/scripts
  python experiment_ssa.py --subjects 003,006,007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "SSA"
SSA_ENERGY = 0.95  # 累积能量截断比例
SSA_MAX_WIN_S = 10.0  # SSA 窗口上限（秒）


def ssa_denoise(x, energy=SSA_ENERGY):
    """SSA 降噪重构: Hankel SVD → 前 k 个奇异值重构（k 由累积能量决定）。

    参数:
        x: 1D 信号
        energy: 累积能量比例（0-1）
    返回:
        重构信号（长度与原信号一致）
    """
    x = np.asarray(x, float)
    n = len(x)
    L = int(min(SSA_MAX_WIN_S * apq.FS, n // 2))
    L = max(3, L)
    K = n - L + 1
    H = np.zeros((L, K))
    for i in range(L):
        H[i, :] = x[i:i + K]
    U, s, Vt = np.linalg.svd(H, full_matrices=False)
    total = np.sum(s ** 2)
    cum = 0.0
    k = 0
    for i in range(len(s)):
        cum += s[i] ** 2
        k = i + 1
        if cum / total >= energy:
            break
    H_rec = (U[:, :k] * s[:k]) @ Vt[:k, :]
    # 对角平均（Hankel 化）
    out = np.zeros(n)
    cnt = np.zeros(n)
    for i in range(L):
        for j in range(K):
            out[i + j] += H_rec[i, j]
            cnt[i + j] += 1
    return out / cnt


def assess_window_ssa(iq, hr_hint=None):
    """SSA 降噪版单窗评估（仅对原版选定 bin 做 SSA 重评估, 每窗 1 次 SVD）。"""
    # 先取原版结果（含选定 bin）
    base = apq.assess_window(iq, hr_hint)
    if not base["ok"] or base.get("heart_bin") is None:
        return base
    n_frames = iq.shape[0]
    power = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(power, axis=0)))
    b = base["heart_bin"]
    phi = np.unwrap(np.angle(iq[:, b, best_ch]))
    phi_det = signal.detrend(phi)
    phi_ssa = ssa_denoise(phi_det)
    snr_db, hr_bpm, ibi_ratio, _ = apq._heartband_assess(phi_ssa, hr_hint)
    out = dict(base)
    if snr_db is None:
        out["ok"] = False
        out["reason"] = "low_snr"
        return out
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
    n_eval = b_ok = s_ok = 0
    b_reasons, s_reasons = {}, {}
    for k in range(n_win):
        w0 = t0 + k * apq.STEP_SEC * 1000
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w0 + apq.WINDOW_SEC * 1000))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * apq.WINDOW_SEC * apq.FS):
            continue
        iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        rb = apq.assess_window(iq)
        rs = assess_window_ssa(iq)
        n_eval += 1
        b_ok += rb["ok"]
        s_ok += rs["ok"]
        b_reasons[rb["reason"]] = b_reasons.get(rb["reason"], 0) + 1
        s_reasons[rs["reason"]] = s_reasons.get(rs["reason"], 0) + 1
    return {"n_windows": n_eval,
            "base_ok": round(b_ok / n_eval, 3) if n_eval else 0,
            "ssa_ok": round(s_ok / n_eval, 3) if n_eval else 0,
            "base_reasons": b_reasons, "ssa_reasons": s_reasons}


def main():
    parser = argparse.ArgumentParser(description="SSA 降噪 A/B 实验")
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
            print(f"  原版 ok: {r['base_ok']:.0%} | SSA ok: {r['ssa_ok']:.0%} | Δ={r['ssa_ok'] - r['base_ok']:+.1%}")
    with open(OUT_DIR / "ssa_ab_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / 'ssa_ab_summary.json'}")


if __name__ == "__main__":
    main()
