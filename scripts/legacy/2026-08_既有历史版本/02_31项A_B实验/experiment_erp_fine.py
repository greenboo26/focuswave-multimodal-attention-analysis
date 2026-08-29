"""
experiment_erp_fine.py — 事件相关细粒度版: 5s HR 窗 + 按键动作对照
====================================================================
版本: v1.0 (2026-08-11)
功能: 在粗粒度事件相关（30s 窗）基础上细化:
      1) 5s 分辨率 HR 时间序列（窄带逐拍, 每窗 5-8 拍）
      2) 错误事件（commission）vs 匹配的正确按键事件对照
         ——控制"按键动作本身"的生理伪影
      3) 事件锁定响应曲线: 事件前 10s → 事件后 10s（5s 步进）
依据: Corcoran 2025（10s 探针窗）; 之前的粗粒度发现（错误窗 BR 升高）需排除按键动作。

数据: F:/预实验/sub-007_（错误事件最多的质量被试）
输出: output/预实验/03_跨被试/09_预实验-优化实验/ERP-FINE/
        erp_fine_summary.json + erp_fine_curves.png
用法:
  cd 08_算法/scripts
  python experiment_erp_fine.py --subject 007 --data-root F:/预实验
依赖: numpy, scipy
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import signal

import assess_preexp_quality as apq

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "ERP-FINE"
FINE_WIN = 5.0        # 细窗长（秒）
RESP_RANGE = 10.0     # 事件前后范围（秒）


def hr_in_window(iq) -> float | None:
    """5s 窗 HR 估计: 最优候选 bin 窄带逐拍 → 均值 IBI → HR。"""
    n_frames = iq.shape[0]
    power = np.mean(np.abs(iq) ** 2, axis=0)
    best_ch = int(np.argmax(np.mean(power, axis=0)))
    bin_power = power[:, best_ch]
    zone = slice(apq.MIN_TARGET_BIN, apq.MAX_TARGET_BIN + 1)
    zp = bin_power[zone]
    cands = [zone.start + int(i) for i in np.argsort(zp)[::-1][:apq.MAX_CAND_BINS]]
    best = None
    for b in cands:
        if apq._phase_modulation(iq, best_ch, b, n_frames) < apq.PHASE_MOD_RAD:
            continue
        phi = signal.detrend(np.unwrap(np.angle(iq[:, b, best_ch])))
        heart_bp = apq._bandpass(phi, *apq.HR_BAND)
        f, pxx = signal.periodogram(heart_bp, fs=apq.FS, window="hann")
        m = (f >= apq.HR_BAND[0]) & (f <= apq.HR_BAND[1])
        if not np.any(m):
            continue
        hf = float(f[m][np.argmax(pxx[m])])
        if not (apq.HR_MIN / 60 <= hf <= apq.HR_MAX / 60):
            continue
        lo, hi = max(hf - 0.05, 0.5), hf + 0.05
        xn = apq._bandpass(heart_bp, lo, hi)
        ref = 1.0 / hf
        peaks = []
        i = 0
        while i < len(xn):
            li, ri = int(i + 0.75 * ref * apq.FS), min(int(i + 1.35 * ref * apq.FS), len(xn))
            if li >= len(xn) or ri <= li:
                break
            p = li + int(np.argmax(xn[li:ri]))
            peaks.append(p)
            i = p + 1
        if len(peaks) >= 3:
            ibi = np.diff(peaks) / apq.FS * 1000
            valid = (ibi >= 300) & (ibi <= 2000)
            if np.mean(valid) >= 0.6 and len(ibi[valid]) >= 2:
                hr = 60000.0 / np.mean(ibi[valid])
                if apq.HR_MIN <= hr <= apq.HR_MAX:
                    return float(hr)
    return None


def load_events(data_root: Path, subject: str):
    """commission 与正确按键事件（相对 mmwave 时间, 秒）。"""
    tl = data_root / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    mm_start = None
    with open(tl, encoding="utf-8", newline="") as f:
        for parts in csv.reader(f):
            if len(parts) >= 3 and parts[0] == "mmwave_start":
                mm_start = int(parts[2])
                break
    comm, correct = [], []
    for fpath in sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv")):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    onset = int(float(r["absolute_onset_time"]))
                except (ValueError, KeyError):
                    continue
                rel = (onset - mm_start) / 1000.0
                if rel < 10:
                    continue
                if r["is_no_go"] == "1" and r["response"] == "1":
                    comm.append(rel)
                elif r["is_no_go"] == "0" and r["response"] == "1":
                    correct.append(rel)
    return comm, correct


def extract_curve(data_root: Path, subject: str, event_times: list[float], label: str):
    """事件锁定 HR 曲线: [-10,-5), [-5,0), [0,5), [5,10) 四窗。"""
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    frame_idx, py_ms = apq.load_timestamps(mm_dir, subject)
    t0 = int(py_ms[0])
    curves = [[] for _ in range(4)]
    for et in event_times:
        for k in range(4):
            w0 = et - RESP_RANGE + k * FINE_WIN
            fa = int(np.searchsorted(py_ms, t0 + w0 * 1000))
            fb = int(np.searchsorted(py_ms, t0 + (w0 + FINE_WIN) * 1000))
            fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
            if fb - fa < int(0.6 * FINE_WIN * apq.FS):
                continue
            iq = apq.load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
            hr = hr_in_window(iq)
            if hr is not None:
                curves[k].append(hr)
    out = {}
    for k, name in enumerate(["pre10", "pre5", "post0", "post5"]):
        arr = np.asarray(curves[k], float)
        out[name] = {"n": int(len(arr)),
                     "mean": round(float(np.mean(arr)), 2) if len(arr) else None,
                     "se": round(float(np.std(arr, ddof=1) / np.sqrt(len(arr))), 2) if len(arr) > 1 else None}
    return out


def main():
    parser = argparse.ArgumentParser(description="事件相关细粒度（5s HR + 按键对照）")
    parser.add_argument("--subject", type=str, default="007")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    subject = args.subject.zfill(3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    comm, correct = load_events(data_root, subject)
    print(f"{subject}: commission {len(comm)}, 正确按键 {len(correct)}")
    # 正确按键抽样到与错误同数量（避免事件数不对称）
    rng = np.random.default_rng(42)
    correct_s = sorted(rng.choice(correct, size=min(len(comm), len(correct)), replace=False))
    print("提取错误事件曲线...")
    comm_curve = extract_curve(data_root, subject, comm, "comm")
    print("提取正确按键曲线（对照）...")
    corr_curve = extract_curve(data_root, subject, correct_s, "correct")

    result = {"subject": subject, "comm": comm_curve, "correct": corr_curve}
    with open(OUT_DIR / "erp_fine_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 打印
    for name in ["pre10", "pre5", "post0", "post5"]:
        c, k = comm_curve[name], corr_curve[name]
        print(f"  {name}: 错误 {c['mean']}(±{c['se']}, n={c['n']}) vs "
              f"正确 {k['mean']}(±{k['se']}, n={k['n']})")
    print(f"[json] {OUT_DIR / 'erp_fine_summary.json'}")

    # 图
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    xs = np.array([-7.5, -2.5, 2.5, 7.5])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key, color, lab in [("comm", "#c0392b", "错误按键(commission)"),
                            ("correct", "#2e86c1", "正确按键(对照)")]:
        means = [result[key][n]["mean"] for n in ["pre10", "pre5", "post0", "post5"]]
        ses = [result[key][n]["se"] for n in ["pre10", "pre5", "post0", "post5"]]
        ax.errorbar(xs, means, yerr=ses, fmt="o-", capsize=3, color=color, label=lab)
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(["前 10s", "前 5s", "后 5s", "后 10s"])
    ax.set_ylabel("HR (bpm)")
    ax.set_title(f"sub-{subject} 按键事件锁定 HR 响应（5s 窗, 错误 vs 正确对照）")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    png = OUT_DIR / "erp_fine_curves.png"
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"[png] {png}")


if __name__ == "__main__":
    main()


