# -*- coding: utf-8 -*-
"""
analyze_external_heartbeat_0814.py — 外部数据集跨设备验证
======================================================
文件名：analyze_external_heartbeat_0814.py
版本：v1.0（2026-08-13）
功能：用本项目处理思路（静态杂波去除 + SOS 窄带滤波 + 带内功率选门）
      处理外部公开数据集（phish-tech mmWave-Heartbeat，TI IWR6843 原始
      ADC bin），验证处理链路的跨设备泛化性。

      数据格式（依据该仓库 preprocessing.m 参数）：
      - 200 ADC 采样/chirp，4 RX，I/Q 交错 int16
      - 每帧 2 chirp（取第 1 个），帧周期 50ms → 慢时间 20Hz
      - Fs_adc=4MHz，slope=77.006e12 Hz/s，起始频率 60GHz

用法示例：
    python analyze_external_heartbeat_0814.py --file adc_1023gby1_Raw_0.bin

依赖：numpy、matplotlib、scipy
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfiltfilt

# 中文字体（Windows SimHei，避免中文显示为方框）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 参数集中声明（来自 preprocessing.m 的雷达配置）
# ============================================================
DATA_DIR = Path(r'D:\Project\厚粲杯\11_数据\外部数据集_mmWave_Heartbeat')  # 数据根目录
N_ADC = 200                                # 每 chirp ADC 采样数
N_RX = 4                                   # 接收天线数
N_TX = 1                                   # 发射天线数
IS_REAL = 0                                # 0=复采样（I/Q 交错）
FS_ADC = 4e6                               # ADC 采样率 Hz
SLOPE = 77.006e12                          # 调频斜率 Hz/s
START_FREQ = 60e9                          # 起始频率 Hz
C = 3e8                                    # 光速 m/s
FRAME_PERIOD = 0.05                        # 帧周期 50ms
FS_VITAL = 1 / FRAME_PERIOD                # 慢时间采样率 20Hz
N_FFT_RANGE = 256                          # 距离 FFT 点数（补零）
RANGE_MIN_M, RANGE_MAX_M = 0.3, 2.5        # 选门检测范围
BREATH_BAND = (0.1, 0.5)                   # 呼吸带通 Hz
HEART_BAND = (0.8, 2.0)                    # 心跳带通 Hz
FILT_ORDER = 4                             # 滤波器阶数（SOS 数值稳定）
AMP_TH_RATIO = 0.2                         # 选门幅度阈值（相对最大幅度）
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'output' / '外部数据集' / '01_phish_heartbeat'


def parse_bin(fpath):
    """解析 TI 原始 ADC bin：I/Q 交错 int16 → (n_chirps, n_rx, n_adc) 复数。

    Args:
        fpath: bin 文件路径

    Returns:
        adc: 复数数组 (n_chirps, n_rx, n_adc)
    """
    raw = np.fromfile(fpath, dtype=np.int16)
    samples_per_chirp = 2 * N_ADC * N_RX      # I/Q × 采样 × RX
    n_chirps = len(raw) // samples_per_chirp
    raw = raw[: n_chirps * samples_per_chirp]
    lvds = raw.reshape(n_chirps, N_RX, N_ADC, 2)   # (chirp, rx, adc, I/Q)
    adc = lvds[:, :, :, 0] + 1j * lvds[:, :, :, 1]
    return adc


def range_fft(adc, rx=0):
    """距离维 FFT（取每帧第 1 个 chirp，单 RX）。

    Args:
        adc: (n_chirps, n_rx, n_adc) 复数
        rx: 接收通道号（默认 0）

    Returns:
        range_profile: (n_frames, n_fft) 距离谱
    """
    chirps = adc[::2, rx, :]                   # 每帧第 1 个 chirp
    window = np.hanning(N_ADC)
    prof = np.fft.fft(chirps * window, N_FFT_RANGE, axis=1)
    return prof


def main():
    """主流程：解析 → 距离 FFT → 去杂波 → 选门 → 相位链路 → 呼吸/心率。"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default='adc_1023gby1_Raw_0.bin',
                        help='bin 文件名（相对数据根目录的子目录）')
    args = parser.parse_args()

    fpath = list(DATA_DIR.rglob(args.file))[0]
    print(f'[LOAD] {fpath}')
    adc = parse_bin(fpath)
    n_frames = adc.shape[0] // 2
    print(f'[INFO] {n_frames} 帧 ({n_frames * FRAME_PERIOD:.0f}s, '
          f'fs={FS_VITAL}Hz)')

    # ---- 距离 FFT ----
    prof = range_fft(adc)                      # (n_frames, 256)
    prof_dyn = prof - prof.mean(axis=0, keepdims=True)   # 静态杂波去除

    # ---- 距离轴与选门 ----
    range_res = FS_ADC * C / (2 * SLOPE * N_FFT_RANGE)   # 补零后距离分辨率
    range_axis = range_res * np.arange(N_FFT_RANGE)
    amp = np.abs(prof).mean(axis=0)            # 各门平均幅度
    i_min = int(RANGE_MIN_M / range_res)
    i_max = int(RANGE_MAX_M / range_res)
    amp_th = AMP_TH_RATIO * amp[i_min: i_max + 1].max()
    # 带内功率选门（呼吸+心跳 0.15-2Hz，SOS 前用 FFT 直接算）
    dphi_all = np.diff(np.angle(prof), axis=0)
    freq = np.fft.rfftfreq(dphi_all.shape[0], d=FRAME_PERIOD)
    band = (freq >= 0.15) & (freq <= 2.0)
    best_power, idx = -1.0, i_min
    for g in range(i_min, i_max + 1):
        if amp[g] < amp_th:
            continue
        dphi = dphi_all[:, g] - dphi_all[:, g].mean()
        power = np.abs(np.fft.rfft(dphi))[band] ** 2
        if power.sum() > best_power:
            best_power, idx = power.sum(), g
    print(f'[BIN] 选中距离门 {idx} = {idx * range_res * 100:.1f}cm')

    # ---- 相位链路 ----
    phi = np.angle(prof[:, idx])
    phi_u = np.unwrap(phi)
    dphi = np.diff(phi_u)
    win = max(1, int(round(0.25 * FS_VITAL)))  # 0.25s 滑动平均
    phi_s = np.convolve(dphi, np.ones(win) / win, mode='same')

    # ---- 呼吸/心跳分离（SOS 滤波） ----
    def bp(x, band):
        sos = butter(FILT_ORDER, [2 * band[0] / FS_VITAL, 2 * band[1] / FS_VITAL],
                     btype='bandpass', output='sos')
        return sosfiltfilt(sos, x)

    breath = bp(phi_s, BREATH_BAND)
    heart = bp(phi_s, HEART_BAND)
    f_breath = np.fft.rfftfreq(len(breath), d=FRAME_PERIOD)
    s_breath = np.abs(np.fft.rfft(breath))
    m = (f_breath >= 0.15) & (f_breath <= 0.45)
    breath_hz = f_breath[m][np.argmax(s_breath[m])] if m.any() else 0
    f_heart = np.fft.rfftfreq(len(heart), d=FRAME_PERIOD)
    s_heart = np.abs(np.fft.rfft(heart))
    m2 = (f_heart >= 0.9) & (f_heart <= 1.9)
    heart_hz = f_heart[m2][np.argmax(s_heart[m2])] if m2.any() else 0
    print(f'[RESULT] 呼吸 {breath_hz * 60:.1f} 次/分 ({breath_hz:.3f}Hz) | '
          f'心率 {heart_hz * 60:.1f} 次/分 ({heart_hz:.3f}Hz)')

    # ---- 汇总图（4 面板：距离能量 + 呼吸 + 心跳 + 频谱） ----
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    t_axis = np.arange(n_frames) * FRAME_PERIOD
    ax = axes[0, 0]
    ax.plot(range_axis, amp, 'k-')
    ax.axvspan(RANGE_MIN_M, RANGE_MAX_M, color='g', alpha=0.1)
    ax.axvline(idx * range_res, color='r', ls='--', label=f'选中 {idx * range_res * 100:.0f}cm')
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('平均幅度')
    ax.set_title('距离能量分布与选门')
    ax.legend()
    ax = axes[0, 1]
    ax.plot(t_axis[: 400], breath[: 400], 'b-', lw=0.8)
    ax.set_xlabel('时间 (s)')
    ax.set_title(f'呼吸波形（{breath_hz * 60:.1f} 次/分）')
    ax = axes[1, 0]
    ax.plot(t_axis[: 400], heart[: 400], 'r-', lw=0.8)
    ax.set_xlabel('时间 (s)')
    ax.set_title(f'心跳波形（{heart_hz * 60:.1f} 次/分）')
    ax = axes[1, 1]
    ax.plot(f_breath[f_breath <= 1], s_breath[f_breath <= 1], 'b-', lw=0.8,
            label='呼吸')
    ax.plot(f_heart[f_heart <= 3], s_heart[f_heart <= 3], 'r-', lw=0.8,
            label='心跳')
    ax.set_xlabel('频率 (Hz)')
    ax.set_ylabel('幅度')
    ax.set_title('呼吸/心跳频谱')
    ax.legend()
    fig.suptitle(f'外部数据集跨设备验证 — {args.file}', fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_png = OUTPUT_DIR / f'{Path(args.file).stem}_vitalsigns.png'
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f'[OK] 汇总图: {out_png}')


if __name__ == '__main__':
    main()
