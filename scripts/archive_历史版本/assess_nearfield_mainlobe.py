"""
assess_nearfield_mainlobe.py — 近场主瓣心跳可提取性验证
========================================================
版本: v1.0 (2026-08-12)
功能: 对近场杂波强的场次（人体主瓣落在近场带 bin 2-6 内）验证:
      把心跳提取直接放在近场带内人体主瓣 bin 上, 是否仍能提取
      生理信号。回答"近场干扰能否靠算法处理"：
        - 若主瓣 bin 提取质量好 → 管线只是定位范围问题, 扩展
          定位到近场带即可救回
        - 若质量仍差 → 近场带内信号被泄漏底噪污染, 只能摆位

方法: 30s 窗, 对候选 bin (近场带内全局峰 + bin 8 对照) 分别:
      相位 unwrap → 去趋势 → 呼吸带主频 → iirnotch 谐波陷波
      → 心跳带 (0.8-2.5 Hz) 主频/SNR → 窄带逐拍 IBI 有效率
      判定: SNR ≥ 3 dB 且 IBI 有效率 ≥ 0.8 → ok

用法:
  cd 08_算法/scripts
  python assess_nearfield_mainlobe.py --data-root F:/预实验 --subject 001

输出: 控制台窗级对比表 (主瓣 bin vs bin 8)

依赖: numpy, scipy
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import signal

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

CHUNK = 1000            # 每 npz 片帧数
WINDOW_SEC = 30.0       # 窗长 (s), 与质量评估一致
STEP_SEC = 15.0         # 窗步进 (s)
FS = 99.0               # 采样率 (Hz) 近似
BR_BAND = (0.1, 0.5)    # 呼吸带 (Hz)
HR_BAND = (0.8, 2.5)    # 心跳带 (Hz)
IBI_MIN, IBI_MAX = 300.0, 2000.0  # IBI 有效范围 (ms)
SNR_OK_DB = 3.0         # 可信 SNR 下界 (dB)
IBI_OK_RATIO = 0.8      # 可信 IBI 有效率下界
NEAR_BINS = slice(2, 7) # 近场带 bin 2-6 (0.075-0.225 m)
MIN_SIZE_BYTE = 100_000 # 有效 npz 分片最小体积


# ============================================================
# 数据与信号处理
# ============================================================

def iter_part_files(mmwave_dir: Path, subject: str):
    """遍历有效 npz 分片（与主管线一致）。

    参数:
        mmwave_dir: mmwave 分片目录
        subject: 被试编号
    生成:
        (片索引, 文件路径)
    """
    main_npz = mmwave_dir / f"sub-{subject}_mmwave_datacube.npz"
    if main_npz.exists() and main_npz.stat().st_size >= MIN_SIZE_BYTE:
        yield 0, main_npz
    i = 1
    while True:
        fpath = mmwave_dir / f"sub-{subject}_mmwave_datacube_part{i:03d}.npz"
        if not fpath.exists():
            break
        if fpath.stat().st_size >= MIN_SIZE_BYTE:
            yield i, fpath
        i += 1


def assess_bin(iq: np.ndarray, b: int, fps: float) -> tuple:
    """单 bin 心跳提取质量（呼吸谐波陷波 → 心跳带 → IBI）。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域窗数据
        b: bin 索引
        fps: 帧率
    返回:
        (snr_db, hr_bpm, ibi_ratio) 或 (None, None, None)
    """
    ch_power = np.mean(np.abs(iq[:, b, :]) ** 2, axis=0)
    best_ch = int(np.argmax(ch_power))
    phi = np.unwrap(np.angle(iq[:, b, best_ch]))
    phi_det = signal.detrend(phi)

    breath_bp = _bandpass(phi_det, *BR_BAND, fps)
    f, pxx = signal.periodogram(breath_bp, fs=fps, window="hann")
    m = (f >= BR_BAND[0]) & (f <= BR_BAND[1])
    br_freq = float(f[m][np.argmax(pxx[m])])
    phi_clean = _notch_harmonics(phi_det, br_freq, fps)

    heart_bp = _bandpass(phi_clean, *HR_BAND, fps)
    f, pxx = signal.periodogram(heart_bp, fs=fps, window="hann")
    m = (f >= HR_BAND[0]) & (f <= HR_BAND[1])
    if not np.any(m):
        return None, None, None
    p_hb = pxx[m]
    hr_freq = float(f[m][np.argmax(p_hb)])
    snr_db = 10 * np.log10(p_hb.max() / (np.median(p_hb) + 1e-12))
    if not (40 / 60 <= hr_freq <= 100 / 60):
        return snr_db, None, 0.0
    hp = _detect_peaks_narrowband(heart_bp, hr_freq, fps)
    ibi_ratio, hr_bpm = 0.0, None
    if len(hp) >= 3:
        ibi_ms = np.diff(hp) / fps * 1000
        valid = (ibi_ms >= IBI_MIN) & (ibi_ms <= IBI_MAX)
        ibi_ratio = float(np.mean(valid))
        clean = ibi_ms[valid]
        if len(clean) >= 3:
            hr_bpm = 60000.0 / np.mean(clean)
    return snr_db, hr_bpm, ibi_ratio


def _bandpass(x: np.ndarray, lo: float, hi: float, fps: float) -> np.ndarray:
    """巴特沃斯带通滤波（2 阶）。"""
    b, a = signal.butter(2, [lo / (fps / 2), hi / (fps / 2)], btype="band")
    return signal.filtfilt(b, a, x)


def _notch_harmonics(x: np.ndarray, f0: float, fps: float) -> np.ndarray:
    """陷波呼吸基频及一次谐波（iirnotch 级联）。

    参数:
        x: 输入相位序列
        f0: 呼吸主频 (Hz)
        fps: 采样率
    返回:
        陷波后序列
    """
    y = x.copy()
    for mult in (1, 2):
        f = f0 * mult
        if f > 0.1 and f < fps / 2 - 1:
            w0 = f / (fps / 2)
            b, a = signal.iirnotch(w0, Q=20)
            y = signal.filtfilt(b, a, y)
    return y


def _detect_peaks_narrowband(x: np.ndarray, f0: float, fps: float) -> np.ndarray:
    """以主频 f0 为参考的窄带逐拍检测（峰值间隔接近 1/f0）。

    参数:
        x: 心跳带滤波序列
        f0: 心跳主频 (Hz)
        fps: 采样率
    返回:
        峰索引数组
    """
    if f0 <= 0:
        return np.array([], dtype=int)
    min_dist = max(int((1.0 / f0) * 0.5 * fps), 1)
    return signal.find_peaks(x, distance=min_dist,
                             height=np.std(x) * 0.5)[0]


def main():
    """流式逐窗评估主瓣 bin vs bin 8, 输出对比表。"""
    parser = argparse.ArgumentParser(description="近场主瓣心跳可提取性验证")
    parser.add_argument("--data-root", required=True, help="数据根目录")
    parser.add_argument("--subject", required=True, help="被试编号 (如 001)")
    args = parser.parse_args()

    mmwave_dir = Path(args.data_root) / f"sub-{args.subject}_" / "mmwave"
    win_len = int(WINDOW_SEC * FS)
    step = int(STEP_SEC * FS)

    buf, rows = [], []
    for _, fpath in iter_part_files(mmwave_dir, args.subject):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        d.close()
        buf.append(chunk)
        while sum(b.shape[0] for b in buf) >= win_len:
            frames, new_buf = [], []
            n_take = win_len
            for b in buf:
                if n_take == 0:
                    new_buf.append(b)
                elif len(b) <= n_take:
                    frames.append(b); n_take -= len(b)
                else:
                    frames.append(b[:n_take])
                    new_buf.append(b[n_take:]); n_take = 0
            iq = np.concatenate(frames, axis=0)
            rows.append(iq)
            buf = new_buf

    print(f"\nsub-{args.subject} 主瓣 bin 心跳提取对比 (30s 窗, 步进 {STEP_SEC}s)")
    print(f"{'窗':>3} {'主瓣bin':>7} {'主瓣SNR':>8} {'主瓣HR':>7} {'主瓣IBI%':>7}"
          f" {'bin8':>5} {'bin8SNR':>7} {'bin8HR':>7} {'bin8IBI%':>8}")
    print("-" * 78)
    n_ok_main, n_ok_b8, n_win = 0, 0, 0
    for i, iq in enumerate(rows):
        prof = np.sqrt(np.mean(np.abs(iq) ** 2, axis=(0, 2)))
        main_bin = int(NEAR_BINS.start + np.argmax(prof[NEAR_BINS]))
        s_main, hr_main, ibi_main = assess_bin(iq, main_bin, FS)
        s_b8, hr_b8, ibi_b8 = assess_bin(iq, 8, FS)
        ok_main = (s_main is not None and s_main >= SNR_OK_DB
                   and (ibi_main or 0) >= IBI_OK_RATIO)
        ok_b8 = (s_b8 is not None and s_b8 >= SNR_OK_DB
                 and (ibi_b8 or 0) >= IBI_OK_RATIO)
        n_ok_main += ok_main; n_ok_b8 += ok_b8; n_win += 1
        print(f"{i:>3} {main_bin:>7} {s_main if s_main is None else round(s_main,1):>8}"
              f" {str(hr_main):>7} {str(ibi_main):>7}"
              f" {8:>5} {s_b8 if s_b8 is None else round(s_b8,1):>7}"
              f" {str(hr_b8):>7} {str(ibi_b8):>8}")
    print("-" * 78)
    print(f"主瓣 bin 可信窗: {n_ok_main}/{n_win} ({100*n_ok_main/max(n_win,1):.0f}%) | "
          f"bin 8 可信窗: {n_ok_b8}/{n_win} ({100*n_ok_b8/max(n_win,1):.0f}%)")


if __name__ == "__main__":
    main()
