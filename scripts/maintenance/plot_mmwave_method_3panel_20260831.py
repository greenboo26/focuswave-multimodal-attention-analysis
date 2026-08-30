"""毫米波信号处理方法 3 面板图（方法部分 4.5.4 用）。

A 距离谱与选中单元；B 胸壁位移与呼吸/心搏成分分离；C 心搏频段频谱与峰值。
数据取 sub-97793 第一个 pre_30s 窗口（targeted 被试）。

数据输入：D:\acq_mmwave_data\sub-97793_（NPZ + timestamps）
输出文件：docs/results/2026-08-31_MMWAVE_PRE30S_SELECTOR_HR/MMWAVE_METHOD_3PANEL_2026-08-31.png（+svg）
项目：厚粲杯 FocusWave | 分析脚本 v1 | 创建日期：2026-08-31
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

ALGO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_20260831.py"
OUT_DIR = ALGO_ROOT / "docs" / "results" / "2026-08-31_MMWAVE_PRE30S_SELECTOR_HR"

COLOR_MMWAVE = "#0E7C7B"
COLOR_BR = "#4A7BA6"
COLOR_HR = "#C2543D"
COLOR_RAW = "#8A8A8A"
BIN_SPACING_M = 0.037

for name in ("SimSun", "Microsoft YaHei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [name, "Arial"]
        break
plt.rcParams["axes.unicode_minus"] = False


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    adapter = load_module(ADAPTER, "adapter_for_method_plot")
    algo = load_module(adapter.PRODUCER, "producer_for_method_plot")

    subject = "sub-97793"
    mmw_root = Path(r"D:\acq_mmwave_data\sub-97793_\mmwave")
    timestamps = adapter.load_timestamps(mmw_root)
    files = adapter.load_npz_files(mmw_root, subject)

    import csv as _csv

    rows = list(_csv.DictReader(Path(
        r"D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831"
        r"\sub-97793_pre30s_selector_hr.csv"
    ).open(encoding="utf-8-sig")))
    row = rows[0]
    win_start = int(row["win_start_unix_ms"])
    win_end = int(row["win_end_unix_ms"])
    i0 = int(np.searchsorted(timestamps[:, 2], win_start, side="left"))
    i1 = int(np.searchsorted(timestamps[:, 2], win_end, side="right"))
    iq = adapter.slice_iq(files, i0, i1)
    iq_fd = algo._as_range_cube(iq)

    bin_power_acc = np.mean(np.abs(iq_fd) ** 2, axis=0)
    br_ch, br_bin, hr_ch, hr_bin, _ = algo.select_separate_channels_bins(bin_power_acc, iq_fd, iq_fd.shape[0])
    disp = algo.extract_displacement(iq_fd, hr_bin, hr_ch)
    disp_br = algo._sos_bandpass(disp, algo.BR_LO_HZ, algo.BR_HI_HZ)
    disp_hr = algo._sos_bandpass(disp, algo.HR_LO_HZ, algo.HR_HI_HZ)

    freqs, pxx = signal_periodogram(disp_hr)
    hr_peak = freqs[np.argmax(pxx[(freqs >= algo.HR_LO_HZ) & (freqs <= algo.HR_HI_HZ)])] if np.any((freqs >= algo.HR_LO_HZ) & (freqs <= algo.HR_HI_HZ)) else None

    fig, axes = plt.subplots(3, 1, figsize=(6.8, 7.2), dpi=300, sharex=False)

    # A：距离谱（取功率最高的通道）
    ax = axes[0]
    ch_power = bin_power_acc[:, hr_ch]
    dist = np.arange(len(ch_power)) * BIN_SPACING_M
    ax.plot(dist, ch_power, color=COLOR_MMWAVE, linewidth=0.9)
    ax.axvline(hr_bin * BIN_SPACING_M, color=COLOR_HR, linestyle="--", linewidth=1.0)
    ax.set_xlabel("距离（m）", fontsize=9.5)
    ax.set_ylabel("平均功率", fontsize=9.5)
    ax.set_title("A 距离谱与选中胸部单元", fontsize=10.5, loc="left")
    ax.tick_params(labelsize=8.5)

    # B：位移分离（取 20 s 段显示）
    ax = axes[1]
    t = np.arange(len(disp)) / algo.FS
    show = slice(0, int(20 * algo.FS))
    ax.plot(t[show], disp[show], color=COLOR_RAW, linewidth=0.6, label="胸壁相对位移")
    ax.plot(t[show], disp_br[show] + 0.6, color=COLOR_BR, linewidth=0.9, label="呼吸成分（0.10-0.50 Hz，偏移显示）")
    ax.plot(t[show], disp_hr[show] - 0.6, color=COLOR_HR, linewidth=0.9, label="心搏成分（0.8-2.0 Hz，偏移显示）")
    ax.set_xlabel("时间（s）", fontsize=9.5)
    ax.set_ylabel("位移（mm）", fontsize=9.5)
    ax.set_title("B 胸壁位移与心肺成分分离", fontsize=10.5, loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper right")
    ax.tick_params(labelsize=8.5)

    # C：心搏频段频谱
    ax = axes[2]
    ax.plot(freqs, 10 * np.log10(pxx + 1e-12), color=COLOR_MMWAVE, linewidth=0.9)
    if hr_peak is not None:
        ax.axvline(hr_peak, color=COLOR_HR, linestyle="--", linewidth=1.0)
        ax.text(hr_peak + 0.05, 12, f"{hr_peak * 60:.0f} bpm", fontsize=8.5, color=COLOR_HR)
    ax.axvspan(algo.HR_LO_HZ, algo.HR_HI_HZ, color="#0E7C7B", alpha=0.08)
    ax.set_xlim(0, 3)
    ax.set_xlabel("频率（Hz）", fontsize=9.5)
    ax.set_ylabel("功率谱密度（dB）", fontsize=9.5)
    ax.set_title("C 心搏频段频谱与峰值检测", fontsize=10.5, loc="left")
    ax.tick_params(labelsize=8.5)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = OUT_DIR / f"MMWAVE_METHOD_3PANEL_2026-08-31.{ext}"
        fig.savefig(out, bbox_inches="tight", facecolor="white")
        print(out)
    plt.close(fig)


def signal_periodogram(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    freqs, pxx = plt.mlab.psd(x, NFFT=4096, Fs=100.0, detrend="linear", window=np.hanning(4096), noverlap=2048, sides="onesided")
    return freqs, pxx


if __name__ == "__main__":
    main()
