"""
跨数据集对比图生成脚本
  生成 output/quality_check.png 和 output/vmd_comparison.png
  （历史数据集 SART_30s / TZTEST / SART_50min 的质量与方法对比图）

2026-08-07 修复:
  - 数据路径迁移: 04_硬件/.../radar_collector → 11_数据/radar_collector
  - 移除二次 range_fft: npz 已是距离域 (0xC2 = Interval0 RFFT),
    二次 FFT 破坏相位结构（8/6 管线 bug 修正, 此处同步）

用法：python gen_comparison_plots.py
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent))  # scripts/ 父目录（含 process_vital_signs_v2）

from process_vital_signs_v2 import (
    FS, load_data, range_fft, select_bins,
    extract_displacement, _sos_bandpass, detect_peaks_heart,
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

RADAR_DATA = Path("D:/Project/厚粲杯/11_数据/radar_collector")
OUTPUT_DIR = SCRIPT_DIR.parent.parent / "output" / "figures"  # 08_算法/output/figures

DATASETS = {
    "SART_30s":   RADAR_DATA / "data_v2/sub-001/ses-SART/mmwave/sub-001_ses-SART_mmwave_datacube.npz",
    "TZTEST_10s": RADAR_DATA / "data_v3/sub-000/ses-fix/mmwave/sub-fix_ses-TZTEST_mmwave_datacube.npz",
    "SART_50min": RADAR_DATA / "data_v3/sub-002/ses-50min/mmwave/sub-test_ses-SART_mmwave_datacube.npz",
}
for name in list(DATASETS):
    if not DATASETS[name].exists():
        print(f"SKIP {name}: {DATASETS[name]} not found")
        del DATASETS[name]


# ── VMD heart-only ──

def vmd_heart_only(disp_hr, hr_freq_hint=None, K=4, alpha=1000):
    from vmdpy import VMD
    try:
        u, u_hat, omega = VMD(disp_hr.astype(np.float64), alpha, 0.0, K, 0, 1, 1e-7)
    except Exception:
        return None
    best_k, best_dist = 0, np.inf
    hr_low, hr_high = 0.8, 2.5
    for k in range(K):
        f_peak = float(np.mean(omega[k])) / (2 * np.pi) * FS
        if hr_low <= f_peak <= hr_high:
            dist = abs(f_peak - hr_freq_hint) if hr_freq_hint else 0
            if dist < best_dist:
                best_dist, best_k = dist, k
    if best_dist == np.inf:
        for k in range(K):
            f_peak = float(np.mean(omega[k])) / (2 * np.pi) * FS
            dist = abs(f_peak - (hr_freq_hint or 1.5))
            if dist < best_dist:
                best_dist, best_k = dist, k
    return u[best_k, :]


def analyze(npz_path, method="bp"):
    iq_fd = load_data(npz_path)
    # npz 已是距离域 (0xC2 = Interval0 RFFT), 不做二次 range_fft
    n_frames = iq_fd.shape[0]
    best_ch, br_bin, hr_bin = select_bins(iq_fd, n_frames)
    disp_br = extract_displacement(iq_fd, br_bin, best_ch)
    disp_hr = extract_displacement(iq_fd, hr_bin, best_ch)
    breath = _sos_bandpass(disp_br, 0.1, 0.5)
    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)

    f, pxx_h = signal.periodogram(heart_bp, fs=FS, window="hann")
    hr_mask = (f >= 0.8) & (f <= 2.5)
    hr_freq = f[hr_mask][np.argmax(pxx_h[hr_mask])] if hr_mask.any() else None

    if method == "vmd":
        heart_vmd = vmd_heart_only(disp_hr, hr_freq_hint=hr_freq)
        heart = heart_vmd if heart_vmd is not None else heart_bp
    else:
        heart = heart_bp

    hp = detect_peaks_heart(heart)
    return {"breath": breath, "heart": heart, "hp": hp, "n_frames": n_frames, "iq_fd": iq_fd}


def gen_quality_check():
    fig, axes = plt.subplots(len(DATASETS), 2, figsize=(16, 4 * len(DATASETS)))
    if len(DATASETS) == 1:
        axes = axes.reshape(1, -1)
    fig.suptitle("Data Quality Overview", fontsize=14)

    for row, (name, npz_path) in enumerate(DATASETS.items()):
        r = analyze(npz_path, method="bp")
        n_frames = r["n_frames"]
        best_ch = int(np.argmax(np.mean(np.abs(r["iq_fd"]), axis=(0, 1))))
        ax = axes[row, 0]
        rp = np.mean(np.abs(r["iq_fd"]) ** 2, axis=(0, 2))
        ax.plot(rp)
        ax.set_xlim(0, 128)
        ax.set_xlabel("range bin"); ax.set_ylabel("power")
        ax.set_title(f"{name} — Range Profile ({n_frames / FS:.1f}s)")

        ax = axes[row, 1]
        disp = extract_displacement(r["iq_fd"], 20, best_ch)
        t = np.arange(len(disp)) / FS
        ax.plot(t, disp, alpha=0.7)
        ax.set_xlim(0, min(10, len(disp) / FS))
        ax.set_xlabel("time (s)"); ax.set_ylabel("mm")
        ax.set_title(f"{name} — Displacement (ch {best_ch})")

    plt.tight_layout()
    out = OUTPUT_DIR / "quality_check.png"
    plt.savefig(out, dpi=150); plt.close()
    print(f"quality_check.png → {out}")


def gen_vmd_comparison():
    fig, axes = plt.subplots(len(DATASETS), 2, figsize=(16, 5 * len(DATASETS)))
    if len(DATASETS) == 1:
        axes = axes.reshape(1, -1)
    fig.suptitle("bp vs vmd_heart Comparison", fontsize=14)

    for row, (name, npz_path) in enumerate(DATASETS.items()):
        bp_r = analyze(npz_path, method="bp")
        vmd_r = analyze(npz_path, method="vmd")
        duration = bp_r["n_frames"] / FS
        t = np.arange(bp_r["n_frames"]) / FS

        ax = axes[row, 0]
        x_start = max(0, duration - 10)
        mask = t >= x_start
        ax.plot(t[mask], bp_r["heart"][mask], "gray", alpha=0.5, label="bp")
        ax.plot(t[mask], vmd_r["heart"][mask], "r-", alpha=0.8, label="vmd_heart")
        hp = vmd_r["hp"]
        if len(hp) > 0:
            hm = (t[hp] >= x_start)
            ax.plot(t[hp][hm], vmd_r["heart"][hp][hm], "ro", markersize=4)
        hr_bp = 60 * FS / np.mean(np.diff(bp_r["hp"])) if len(bp_r["hp"]) >= 2 else 0
        hr_vmd = 60 * FS / np.mean(np.diff(vmd_r["hp"])) if len(vmd_r["hp"]) >= 2 else 0
        ax.set_title(f"{name} — Heart: bp={hr_bp:.1f} vs vmd={hr_vmd:.1f} BPM")
        ax.set_xlabel("time (s)"); ax.set_ylabel("mm")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

        ax = axes[row, 1]
        x = np.arange(2); w = 0.3
        ax.bar(x - w/2, [hr_bp, hr_vmd], w, label="HR (BPM)", color="red", alpha=0.7)
        ax.set_xticks(x); ax.set_xticklabels(["bp", "vmd"])
        ax.set_ylabel("BPM")
        ax.set_title(f"{name} — HR Summary")
        ax.legend(fontsize=8)

    plt.tight_layout()
    out = OUTPUT_DIR / "vmd_comparison.png"
    plt.savefig(out, dpi=150); plt.close()
    print(f"vmd_comparison.png → {out}")


if __name__ == "__main__":
    gen_quality_check()
    gen_vmd_comparison()


