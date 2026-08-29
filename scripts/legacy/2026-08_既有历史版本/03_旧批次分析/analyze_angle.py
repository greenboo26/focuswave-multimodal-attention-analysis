"""
1D-DataCube 测角分析脚本
========================
用 sub-1d-test 数据 + 出厂校准数据 (ant_calib.json) 验证 RS6240 2T4R 测角:

  1. 目标 bin 检测 (0.3-1.5m 先验窗内距离谱峰值)
  2. 天线校准 (各通道 × 校准系数, 官方 mmw_cube_ant_align_2t4r 同款复数乘法)
  3. 相位一致性验证 (校准前后通道间相位差 std, 决定测角可行性)
  4. 测角:
     - 方位角: TX0 的 4 RX 子阵 (λ/2 均匀线阵) 相邻相位差法
     - 俯仰角: TX0 vs TX1 相位差 (垂直基线)
  5. 输出角度时间序列与统计

用法:
    cd 08_算法/scripts
    python analyze_angle.py                          # 默认 sub-1d-test
    python analyze_angle.py --data-root X --subject Y --session Z

依赖: numpy (校准数据从 11_数据/calib_data/ant_calib.json 加载)
数据: 11_数据/sub-1d-test/ses-0812/mmwave/ (1000 帧 × 8 通道 × 256 bin)
"""

import os
import sys
import json
import argparse

import numpy as np

# ============================================================
# 硬编码参数
# ============================================================
DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), '11_数据')  # 数据根目录
SUBJECT_ID = '1d-test'      # 被试编号 (sub-1d-test)
SESSION = '0812'            # 会话标签
CALIB_FILE = os.path.join(DATA_ROOT, 'calib_data', 'ant_calib.json')
CHANNELS = ['tx0_rx0', 'tx0_rx1', 'tx0_rx2', 'tx0_rx3',
            'tx1_rx0', 'tx1_rx1', 'tx1_rx2', 'tx1_rx3']  # 8 通道
MIN_BIN = 8                 # 目标搜索下界 (0.3m, 避开近场泄漏 bin 2-3)
MAX_BIN = 45                # 目标搜索上界 (1.7m, 避开 bin146 伪影等)
RANGE_RESOL_MM = 37         # 距离分辨率 (新固件带宽 4.05GHz)
WAVELENGTH_MM = 5.0         # 60GHz 波长
RX_SPACING_MM = 2.45        # RX 间距 (λ/2)
N_FRAMES_MAX = 1000         # 分析帧数上限


def load_frames(save_root: str, subject: str, session: str) -> dict:
    """加载 npz 分块数据并拼接为 8 通道数组。

    Parameters
    ----------
    save_root : str
        数据根目录 (11_数据)。
    subject : str
        被试编号。
    session : str
        会话标签。

    Returns
    -------
    dict
        {通道名: (n_frames, 256) complex 数组}。
    """
    mmwave_dir = os.path.join(save_root, f'sub-{subject}', f'ses-{session}', 'mmwave')
    if not os.path.isdir(mmwave_dir):
        raise FileNotFoundError(f'未找到数据目录: {mmwave_dir}')

    npz_files = sorted(
        f for f in os.listdir(mmwave_dir)
        if f.endswith('.npz') and f'{subject}_ses-{session}_' in f
    )
    if not npz_files:
        raise FileNotFoundError(f'{mmwave_dir} 下无 npz 文件')

    chunks = {ch: [] for ch in CHANNELS}
    for fn in npz_files:
        data = np.load(os.path.join(mmwave_dir, fn))
        for ch in CHANNELS:
            if ch in data:
                chunks[ch].append(data[ch])

    result = {}
    for ch in CHANNELS:
        if chunks[ch]:
            arr = np.concatenate(chunks[ch], axis=0)
            result[ch] = arr[:N_FRAMES_MAX]
    return result


def load_calib(calib_file: str) -> tuple:
    """加载出厂校准数据。

    Parameters
    ----------
    calib_file : str
        ant_calib.json 路径。

    Returns
    -------
    tuple
        (dec_fcw: int, ant_calib: complex[8])。
    """
    with open(calib_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ant_calib = np.array([complex(re, im) for re, im in data['ant_calib_data']])
    return data['dec_fcw'], ant_calib


def detect_target_bin(frames: dict, min_bin: int, max_bin: int) -> int:
    """距离谱峰值检测 (0.3-1.5m 先验窗)。

    Parameters
    ----------
    frames : dict
        {通道名: (n_frames, 256) complex 数组}。
    min_bin, max_bin : int
        搜索窗口。

    Returns
    -------
    int
        目标距离 bin。
    """
    amp = np.abs(frames['tx0_rx0']).mean(axis=0)
    window = amp[min_bin:max_bin]
    peak = int(np.argmax(window)) + min_bin
    return peak


def extract_target_phase(frames: dict, target_bin: int) -> np.ndarray:
    """提取目标 bin 的 8 通道复数值 (n_frames, 8)。

    Parameters
    ----------
    frames : dict
        {通道名: (n_frames, 256) complex 数组}。
    target_bin : int
        目标距离 bin。

    Returns
    -------
    np.ndarray
        (n_frames, 8) complex。
    """
    n = len(frames[CHANNELS[0]])
    data = np.empty((n, 8), dtype=complex)
    for i, ch in enumerate(CHANNELS):
        data[:, i] = frames[ch][:, target_bin]
    return data


def phase_stats(ant: np.ndarray) -> dict:
    """通道间相位差统计 (以通道 0 为参考)。

    Parameters
    ----------
    ant : np.ndarray
        (n_frames, 8) complex 校准后数据。

    Returns
    -------
    dict
        {mean_diff: (7,) 平均相位差, std_diff: (7,) 相位差 std}。
    """
    ref = ant[:, 0]
    diffs = np.angle(ant[:, 1:] * np.conj(ref[:, None]))
    return {'mean_diff': np.mean(diffs, axis=0),
            'std_diff': np.std(diffs, axis=0)}


def azimuth_from_rx_subarray(ant: np.ndarray, tx: int) -> np.ndarray:
    """TX0/TX1 的 4 RX 子阵方位角 (相邻相位差平均法)。

    Parameters
    ----------
    ant : np.ndarray
        (n_frames, 8) complex 校准后数据。
    tx : int
        0 或 1 (选择哪组 TX 的 4 个 RX)。

    Returns
    -------
    np.ndarray
        (n_frames,) 方位角 (弧度)。
    """
    ch = ant[:, tx * 4:(tx + 1) * 4]
    # 相邻 RX 相位差: 3 对 (rx1-rx0, rx2-rx1, rx3-rx2)
    pairs = []
    for i in range(3):
        pairs.append(np.angle(ch[:, i + 1] * np.conj(ch[:, i])))
    dphi = np.mean(pairs, axis=0)  # 平均相邻相位差
    # λ/2 间距: sin(θ) = Δφ·λ/(2π·d) = Δφ/π
    theta = np.arcsin(np.clip(dphi / np.pi, -1, 1))
    return theta


def elevation_from_tx_pair(ant: np.ndarray) -> np.ndarray:
    """TX0 vs TX1 俯仰角 (垂直基线相位差)。

    垂直基线 d = 未知 (TX 间距), 输出为相位差 (弧度), 角度需已知基线。
    TX 间距参考: RS6240 2D MIMO, 俯仰基线约 λ/2 (需规格书确认)。

    Parameters
    ----------
    ant : np.ndarray
        (n_frames, 8) complex 校准后数据。

    Returns
    -------
    np.ndarray
        (n_frames,) TX0-TX1 平均相位差 (弧度)。
    """
    tx0 = ant[:, 0:4]
    tx1 = ant[:, 4:8]
    # 对应 RX 对的相位差平均 (4 对)
    dphi = np.mean(np.angle(tx1 * np.conj(tx0)), axis=1)
    return dphi


def main() -> None:
    """执行测角分析并打印报告。"""
    parser = argparse.ArgumentParser(description='1D-DataCube 测角分析')
    parser.add_argument('--data-root', default=DATA_ROOT, help='数据根目录')
    parser.add_argument('--subject', default=SUBJECT_ID, help='被试编号')
    parser.add_argument('--session', default=SESSION, help='会话标签')
    args = parser.parse_args()

    frames = load_frames(args.data_root, args.subject, args.session)
    if not frames:
        print('无数据, 分析中止')
        sys.exit(1)

    dec_fcw, ant_calib = load_calib(CALIB_FILE)

    print('=' * 60)
    print(f'1D-DataCube 测角分析 | sub-{args.subject} | ses-{args.session}')
    print(f'校准: dec_fcw={dec_fcw}, ant_calib[0]={ant_calib[0]:.0f}{ant_calib[0].imag:+.0f}j')
    print('=' * 60)

    # ① 目标检测
    target_bin = detect_target_bin(frames, MIN_BIN, MAX_BIN)
    print(f'\n[1] 目标检测: bin {target_bin} = {target_bin * RANGE_RESOL_MM / 1000:.2f} m')

    # ② 提取目标复数值
    ant_raw = extract_target_phase(frames, target_bin)

    # ③ 校准前相位一致性 (可行性基线)
    raw_stats = phase_stats(ant_raw)
    print(f'\n[2] 校准前通道相位差 (vs 通道0, std<0.5rad=稳定):')
    for i in range(7):
        print(f'    通道{i + 1}: mean={raw_stats["mean_diff"][i]:+.3f} rad, '
              f'std={raw_stats["std_diff"][i]:.3f} rad '
              f'{"✅" if raw_stats["std_diff"][i] < 0.5 else "❌ 不稳定"}')

    # ④ 天线校准 (复数乘法, 官方同款)
    ant_cal = ant_raw * ant_calib[None, :]

    cal_stats = phase_stats(ant_cal)
    print(f'\n[3] 校准后通道相位差 (std<0.5rad=测角可行):')
    for i in range(7):
        print(f'    通道{i + 1}: mean={cal_stats["mean_diff"][i]:+.3f} rad, '
              f'std={cal_stats["std_diff"][i]:.3f} rad '
              f'{"✅" if cal_stats["std_diff"][i] < 0.5 else "❌ 不稳定"}')

    # ⑤ 测角 (若校准后相位稳定)
    print(f'\n[4] 测角结果 (TX0 4RX 子阵方位角):')
    azi_tx0 = azimuth_from_rx_subarray(ant_cal, tx=0)
    azi_tx1 = azimuth_from_rx_subarray(ant_cal, tx=1)
    elev = elevation_from_tx_pair(ant_cal)
    for name, arr in [('方位角 TX0', azi_tx0), ('方位角 TX1', azi_tx1)]:
        deg = np.degrees(arr)
        print(f'    {name}: mean={np.mean(deg):+.1f}°, std={np.std(deg):.1f}°, '
              f'范围 [{np.min(deg):+.1f}, {np.max(deg):+.1f}]')
    print(f'    TX0-TX1 相位差: mean={np.mean(elev):+.3f} rad, '
          f'std={np.std(elev):.3f} rad')

    # ⑥ 结论
    cal_stable = np.all(cal_stats['std_diff'] < 0.5)
    print(f'\n[5] 结论: {"✅ 校准后通道相位稳定, 测角可行" if cal_stable
          else "❌ 校准后相位仍不稳定, 测角受硬件限制"}')
    print('=' * 60)


if __name__ == '__main__':
    main()


