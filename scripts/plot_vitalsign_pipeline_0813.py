# -*- coding: utf-8 -*-
"""
plot_vitalsign_pipeline_0813.py — 生命体征信号处理全流程逐步图
============================================================
文件名：plot_vitalsign_pipeline_0813.py
版本：v1.0（2026-08-13）
功能：复现博客（cnblogs.com/fangrx/p/18327174，TI IWR6843 生命体征
      提取流程）的每一步信号处理图，数据源为预实验毫米波 npz：

      步骤 1  距离维 FFT（固件 256 门 IQ 幅度，距离-时间热图）
      步骤 2  相位提取（0.3-1.5m 范围能量最大距离门，未展开相位）
      步骤 3  相位解缠绕（unwrap）
      步骤 4  相位差分（相邻帧相位差 → 位移信号）
      步骤 5  脉冲噪声去除（滑动平均，窗口 0.25s）
      步骤 6  相位差信号 FFT（呼吸/心跳分频段观察）
      步骤 7  呼吸信号分离（0.1-0.5Hz 巴特沃斯带通 + FFT 谱峰 → 呼吸率）
      步骤 8  心跳信号分离（0.8-2.0Hz 巴特沃斯带通 + FFT 谱峰 → 心率）

      与博客的差异：博客为 TI 原始 ADC 1024 点 FFT、帧率 20Hz；
      本数据为固件端 256 门 FFT 结果、帧率约 98.5Hz，滤波器
      按实际帧率设计，生理频段一致（呼吸 0.1-0.5Hz、心跳 0.8-2Hz）。

用法示例：
    python plot_vitalsign_pipeline_0813.py --subject 004 --seconds 60

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
# 参数集中声明
# ============================================================
DATA_DIR = Path(r'J:\预实验')              # 数据根目录（可改）
RANGE_BINS = 256                           # 距离门数（固件 256 点 FFT）
RANGE_RES_M = 0.037                        # 距离分辨率 37mm/门（新固件校准值）
FS = 98.5                                  # 帧率 Hz（meta.json fps 实测均值，仅用于帧数换算）
UNIFORM_FS = 100.0                         # 时间戳重采样均匀网格 Hz（频谱分析用）
CHANNEL = 'tx0_rx0'                        # 展示通道（8 通道任选 tx*_rx*）
RANGE_MIN_M, RANGE_MAX_M = 0.3, 1.5        # 目标检测范围（博客同款 0.3-1.5m）
SMOOTH_WIN_S = 0.25                        # 滑动平均窗口时长（博客 0.25s）
BREATH_BAND = (0.1, 0.5)                   # 呼吸带通频段 Hz（博客 0.1-0.5Hz）
BREATH_ORDER = 4                           # 呼吸滤波器阶数（博客 4 阶）
HEART_BAND = (0.8, 2.0)                    # 心跳带通频段 Hz（博客 0.8-2Hz）
HEART_ORDER = 8                            # 心跳滤波器阶数（博客 8 阶）
DB_LO_PCT, DB_HI_PCT = 5.0, 99.0           # 距离热图 dB 裁剪百分位
FIG_SIZE = (18, 16)                        # 总图尺寸（2 列 × 4 行）
SCRIPT_DIR = Path(__file__).resolve().parent
# 输出按规范：output/预实验/03_跨被试/ 下编号命名（与其他 09_ 分析产物并列）
OUTPUT_DIR = (SCRIPT_DIR.parent / 'output' / '预实验' / '03_跨被试'
              / '09_预实验-生命体征mesh')


def load_iq(subject: str, seconds: float, offset_s: float = 0):
    """跨 npz 分片读取指定时长与起点的 IQ 数据。

    Args:
        subject: 被试编号（如 '004'）
        seconds: 读取时长（秒）
        offset_s: 起点偏移（秒，相对 mmWave 开始采集）

    Returns:
        iq: 复数 IQ (n_frames, 256)
        t_unix: 各帧 DLL 时间戳（第 2 列，固件逐帧打的硬件接收时刻，
                实测间隔中位 10.0ms、std 1.28ms，帧率干净稳定）
    """
    n_frames = int(round(seconds * FS))
    i0 = int(round(offset_s * FS))          # 起点帧号
    per_part = 1000                         # 每片固定 1000 帧
    p_start = i0 // per_part + 1
    p_end = (i0 + n_frames - 1) // per_part + 1
    parts = []
    for p in range(p_start, p_end + 1):
        fpath = (DATA_DIR / f'sub-{subject}_' / 'mmwave'
                 / f'sub-{subject}_mmwave_datacube_part{p:03d}.npz')
        data = np.load(fpath)
        parts.append(data[CHANNEL])
    iq = np.concatenate(parts, axis=0)[i0 % per_part: i0 % per_part + n_frames]
    # 时间戳 CSV 三列：帧号, DLL 时间戳, Python 时间戳。用第 2 列（DLL 硬件时戳）
    ts_path = DATA_DIR / f'sub-{subject}_' / 'mmwave' / f'sub-{subject}_mmwave_timestamps.csv'
    ts = np.genfromtxt(ts_path, delimiter=',')
    t_unix = ts[i0: i0 + n_frames, 1]
    return iq, t_unix


def find_rest_offset_s(subject: str, rest_index: int, seconds: float):
    """从 master_timeline 自动定位第 N 段休息的末尾前 seconds 秒。

    取休息段最后 seconds 秒（呼吸稳定期），用于生命体征验证。

    Args:
        subject: 被试编号
        rest_index: 第几段休息（1 起，通常共 5 段）
        seconds: 需要时长（秒）

    Returns:
        offset_s: 相对 mmWave 开始采集的偏移（秒）
    """
    import pandas as pd
    tl_path = DATA_DIR / f'sub-{subject}_' / 'beh' / 'master_timeline.csv'
    tl = pd.read_csv(tl_path, encoding='utf-8-sig')
    rest_rows = tl[tl['event'] == 'rest_stop']
    if rest_index > len(rest_rows):
        raise ValueError(f'sub-{subject} 只有 {len(rest_rows)} 段休息，'
                         f'请求第 {rest_index} 段')
    row = rest_rows.iloc[rest_index - 1]
    rest_end_ms = float(row['unix_ms'])                     # 休息结束时刻
    rest_s = float(row['detail'].split('=')[1].replace('s', ''))  # 实际休息时长
    target_start_ms = rest_end_ms - seconds * 1000          # 休息末尾前 seconds 秒
    ts_path = DATA_DIR / f'sub-{subject}_' / 'mmwave' / f'sub-{subject}_mmwave_timestamps.csv'
    ts = np.genfromtxt(ts_path, delimiter=',')
    mm_start_ms = ts[0, 2]                                  # mmWave 首帧时刻
    offset_s = (target_start_ms - mm_start_ms) / 1000.0
    print(f'[REST] 第{rest_index}段休息: 结束于 '
          f'{pd.to_datetime(rest_end_ms, unit="ms").strftime("%H:%M:%S")}, '
          f'时长 {rest_s:.1f}s, 取末尾 {seconds}s')
    return max(0.0, offset_s)


def bandpass_filter(x, band, order, fs):
    """零相位巴特沃斯带通滤波（SOS 形式，低频窄带数值稳定）。

    呼吸/心跳带通截止频率低至 0.1Hz（归一化频率 ~0.002），
    传统 b/a 形式的 filtfilt 极点贴单位圆，长信号（数千帧）
    数值误差累积导致输出爆炸（实测 std 达 1e15）。SOS 级联
    分解 + sosfiltfilt 数值稳定。

    Args:
        x: 输入信号
        band: (low, high) 截止频率 Hz
        order: 滤波器阶数
        fs: 采样率 Hz

    Returns:
        滤波后信号（与输入同形状）
    """
    sos = butter(order, [2 * band[0] / fs, 2 * band[1] / fs],
                 btype='bandpass', output='sos')
    return sosfiltfilt(sos, x)


def resample_uniform(x, t_unix, fs_out=100.0):
    """按时间戳把非均匀采样信号线性插值到均匀网格（备用）。

    时间戳说明：CSV 第 2 列（DLL 固件逐帧时戳）间隔中位 10.0ms、
    std 1.28ms，干净稳定；第 3 列（Python 回调时刻）抖动大
    （std 96ms，含 3 秒级跳变），仅用于跨模态对齐（与行为数据
    同源时钟）。帧内频谱分析用等间隔 FFT 或本函数的 DLL 时戳插值，
    两者结果一致。

    Args:
        x: 非均匀采样信号
        t_unix: 各样本 Unix 毫秒时间戳（与 x 等长）
        fs_out: 输出均匀采样率 Hz

    Returns:
        (x_u, t_u)：均匀网格信号与时间轴（秒）
    """
    t = (t_unix - t_unix[0]) / 1000.0       # 相对秒
    # 去重保证时间严格递增（时间戳抖动可能产生重复/回退）
    order = np.argsort(t, kind='stable')
    t_s, x_s = t[order], x[order]
    keep = np.concatenate([[True], np.diff(t_s) > 0])
    t_s, x_s = t_s[keep], x_s[keep]
    # 均匀网格（截取原信号完整覆盖范围）
    t_u = np.arange(0, t_s[-1], 1 / fs_out)
    x_u = np.interp(t_u, t_s, x_s)
    return x_u, t_u


def step1_mesh(ax, iq, n_show=300, r_max=0.8):
    """步骤 1：距离维 FFT 结果 3D mesh 图（与博客 mesh 图同款）。

    静态杂波去除（复域减帧平均）后取线性幅度画曲面：
    X=距离、Y=帧（chirp 序号）、Z=幅度。仅显示前 n_show 帧
    （mesh 过密会糊）与 0-r_max 距离范围，突出人体动态峰。

    Args:
        ax: 3D 子图
        iq: 复数 IQ (n_frames, 256)
        n_show: 展示帧数（约 100fps，300 帧 ≈ 3 秒）
        r_max: 距离轴上限（米）
    """
    iq_dyn = iq - iq.mean(axis=0, keepdims=True)   # 复域减帧平均（静态杂波去除）
    mag = np.abs(iq_dyn[: n_show])                 # 线性幅度（博客 abs 同款）
    t_axis = np.arange(n_show) / FS                # 时间轴（秒）
    r_axis = RANGE_RES_M * np.arange(RANGE_BINS)
    keep = r_axis <= r_max
    x, y = np.meshgrid(r_axis[keep], t_axis)
    z = mag[:, keep]
    ax.plot_surface(x, y, z, cmap='jet', rstride=2, cstride=2,
                    linewidth=0, antialiased=True)
    ax.view_init(elev=30, azim=-60)                # 与博客视角接近
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('时间 (s)')
    ax.set_zlabel('幅度')
    ax.set_title(f'步骤1 距离维FFT结果（静态杂波去除后，前 {n_show} 帧 ≈ {n_show / FS:.1f}s）')


def step2_extract_phase(ax, iq):
    """步骤 2：生命体征频段功率最大距离门 + 未展开相位。

    博客按全频段能量最大选门，但实测能量最大门（近场静态杂波）
    相位差后生理信号弱，且单门选择在不同休息段间不稳定（门号
    漂移导致呼吸率 10-20 次/分波动）。改为：
    1) 相对幅度阈值（≥0.2×最大幅度）排除纯噪声门；
    2) 在达标门中选 0.15-2Hz 带内相位差功率最大的门为主门；
    帧率用等间隔 FFT（DLL 时戳实测间隔中位 10.0ms、std 1.28ms）。

    Args:
        ax: 子图
        iq: 复数 IQ (n_frames, 256)

    Returns:
        (angle_target, idx)：相位序列与主门索引
    """
    min_idx = int(RANGE_MIN_M / RANGE_RES_M)
    max_idx = int(RANGE_MAX_M / RANGE_RES_M)
    amp_mean = np.abs(iq).mean(axis=0)         # 各门平均幅度
    dphi_all = np.diff(np.angle(iq), axis=0)   # 全体门差分相位
    freq = np.fft.rfftfreq(dphi_all.shape[0], d=1 / FS)
    band = (freq >= 0.15) & (freq <= 2.0)      # 呼吸+心跳频段掩码
    # 噪声门（无目标反射，幅度≈0）相位差为纯随机跳变（std 可达 2 rad+），
    # 带内功率虚高。先用相对幅度阈值排除噪声门，再选带内功率最大者。
    amp_th = 0.2 * amp_mean[min_idx: max_idx + 1].max()
    best_power, idx = -1.0, min_idx
    for g in range(min_idx, max_idx + 1):
        if amp_mean[g] < amp_th:
            continue                           # 噪声门排除
        dphi = dphi_all[:, g]
        dphi = dphi - dphi.mean()              # 去直流（静态分量）
        power = np.abs(np.fft.rfft(dphi))[band] ** 2
        power = power.sum()                    # 带内总功率
        if power > best_power:
            best_power, idx = power, g
    angle_target = np.angle(iq[:, idx])        # 主门相位序列
    ax.plot(angle_target[: 300], 'b-', lw=0.8)
    ax.set_xlabel('帧数')
    ax.set_ylabel('相位 (rad)')
    ax.set_title(f'步骤2 未展开相位信号（主门 {idx} = {idx * RANGE_RES_M * 100:.1f}cm，'
                 f'0.15-2Hz带内功率选门）')
    return angle_target, idx


def step3_unwrap(ax, phi):
    """步骤 3：相位解缠绕。"""
    phi_u = np.unwrap(phi)
    ax.plot(phi_u, 'g-', lw=0.8)
    ax.set_xlabel('帧数')
    ax.set_ylabel('相位 (rad)')
    ax.set_title('步骤3 解缠后的相位')
    return phi_u


def step4_diff(ax, phi_u):
    """步骤 4：相位差分（相邻帧相位差 → 位移信号）。"""
    dphi = np.diff(phi_u)
    ax.plot(dphi, 'r-', lw=0.8)
    ax.set_xlabel('帧数')
    ax.set_ylabel('相位差 (rad)')
    ax.set_title('步骤4 相位差分后信号')
    return dphi


def step5_smooth(ax, dphi):
    """步骤 5：脉冲噪声去除（滑动平均，窗口 0.25s）。"""
    win = max(1, int(round(SMOOTH_WIN_S * FS)))
    phi_s = np.convolve(dphi, np.ones(win) / win, mode='same')
    ax.plot(phi_s, 'm-', lw=0.8)
    ax.set_xlabel('帧数')
    ax.set_ylabel('相位差 (rad)')
    ax.set_title(f'步骤5 滑动平均滤波相位信号（窗口 {win} 帧 = {SMOOTH_WIN_S}s）')
    return phi_s


def step6_spectrum(ax, phi_s, fs):
    """步骤 6：相位差信号 FFT（0-5Hz 放大观察呼吸/心跳分频段）。"""
    n = len(phi_s)
    spec = np.abs(np.fft.fft(phi_s))
    freq = np.fft.fftfreq(n, d=1 / fs)
    pos = freq >= 0
    ax.plot(freq[pos], spec[pos], 'k-', lw=0.8)
    ax.set_xlim(0, 5)
    ax.set_xlabel('频率 (Hz)')
    ax.set_ylabel('幅度')
    ax.set_title('步骤6 相位信号FFT（呼吸<0.5Hz / 心跳0.8-2Hz）')
    ax.axvspan(*BREATH_BAND, color='b', alpha=0.15, label='呼吸带')
    ax.axvspan(*HEART_BAND, color='r', alpha=0.15, label='心跳带')
    ax.legend(fontsize=9)
    return spec, freq


def step7_breath(ax_t, ax_f, phi_s, fs):
    """步骤 7：呼吸信号分离（带通滤波 + 频谱峰值 → 呼吸率）。

    Args:
        ax_t, ax_f: 时域与频域子图
        phi_s: 均匀重采样后的相位差信号
        fs: 均匀采样率 Hz

    Returns:
        breath_bpm: 呼吸率（次/分钟）
    """
    breath = bandpass_filter(phi_s, BREATH_BAND, BREATH_ORDER, fs)
    t_axis = np.arange(len(breath)) / fs
    ax_t.plot(t_axis, breath, 'b-', lw=0.8)
    ax_t.set_xlabel('时间 (s)')
    ax_t.set_ylabel('幅度')
    ax_t.set_title('步骤7 呼吸时域波形（0.1-0.5Hz带通）')
    spec = np.abs(np.fft.fft(breath))
    freq = np.fft.fftfreq(len(breath), d=1 / fs)
    pos = (freq >= 0) & (freq <= 1.0)
    ax_f.plot(freq[pos], spec[pos], 'b-', lw=0.8)
    # 谱峰搜索（避开滤波边界：0.15-0.45Hz，边界外为滤波器滚降伪峰）
    band = (freq >= 0.15) & (freq <= 0.45)
    peak_hz = freq[band][np.argmax(spec[band])] if band.any() else 0
    breath_bpm = peak_hz * 60
    ax_f.axvline(peak_hz, color='b', ls='--', lw=1)
    ax_f.set_xlabel('频率 (Hz)')
    ax_f.set_ylabel('幅度')
    ax_f.set_title(f'步骤7 呼吸信号FFT（峰值 {peak_hz:.3f}Hz → {breath_bpm:.1f} 次/分钟）')
    return breath_bpm


def step8_heart(ax_t, ax_f, phi_s, fs):
    """步骤 8：心跳信号分离（带通滤波 + 频谱峰值 → 心率）。

    Args:
        ax_t, ax_f: 时域与频域子图
        phi_s: 均匀重采样后的相位差信号
        fs: 均匀采样率 Hz

    Returns:
        heart_bpm: 心率（次/分钟）
    """
    heart = bandpass_filter(phi_s, HEART_BAND, HEART_ORDER, fs)
    t_axis = np.arange(len(heart)) / fs
    ax_t.plot(t_axis, heart, 'r-', lw=0.8)
    ax_t.set_xlabel('时间 (s)')
    ax_t.set_ylabel('幅度')
    ax_t.set_title('步骤8 心跳时域波形（0.8-2Hz带通）')
    spec = np.abs(np.fft.fft(heart))
    freq = np.fft.fftfreq(len(heart), d=1 / fs)
    pos = (freq >= 0) & (freq <= 3.0)
    ax_f.plot(freq[pos], spec[pos], 'r-', lw=0.8)
    # 谱峰搜索（避开滤波边界：0.9-1.9Hz，边界外为滤波器滚降伪峰）
    band = (freq >= 0.9) & (freq <= 1.9)
    peak_hz = freq[band][np.argmax(spec[band])] if band.any() else 0
    heart_bpm = peak_hz * 60
    ax_f.axvline(peak_hz, color='r', ls='--', lw=1)
    ax_f.set_xlabel('频率 (Hz)')
    ax_f.set_ylabel('幅度')
    ax_f.set_title(f'步骤8 心跳信号FFT（峰值 {peak_hz:.3f}Hz → {heart_bpm:.1f} 次/分钟）')
    return heart_bpm


def save_mesh_figure(subject, iq, out_dir):
    """保存单个被试的步骤 1 3D mesh 单图。

    Args:
        subject: 被试编号（如 '004'）
        iq: 复数 IQ (n_frames, 256)
        out_dir: 输出目录 Path
    """
    fig_m = plt.figure(figsize=(12, 7))
    ax_m = fig_m.add_subplot(111, projection='3d')
    step1_mesh(ax_m, iq)
    fig_m.suptitle(f'毫米波距离维FFT 3D mesh — sub-{subject} '
                   f'({CHANNEL}, 静态杂波去除后)', fontsize=14)
    fig_m.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_m = out_dir / f'vitalsign_mesh_sub-{subject}_300fr.png'
    fig_m.savefig(out_m, dpi=150)
    plt.close(fig_m)
    print(f'[OK] mesh 单图已保存: {out_m}')


def main():
    """主流程：默认绘制全流程面板总图；--mesh-only 时仅输出步骤 1 的 3D mesh 单图。"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', default='004', help='被试编号')
    parser.add_argument('--seconds', type=float, default=60,
                        help='分析时长（秒），建议 ≥30s 以分辨呼吸峰')
    parser.add_argument('--offset', type=float, default=None,
                        help='起点偏移秒（相对 mmWave 开始）；不填则用 --rest')
    parser.add_argument('--rest', type=int, default=1,
                        help='取第几段休息末尾（自动对齐 master_timeline，默认第 1 段）')
    parser.add_argument('--mesh-only', action='store_true',
                        help='仅输出步骤 1 的 3D mesh 单图（不含后续步骤）')
    parser.add_argument('--all', action='store_true',
                        help='批量生成 J 盘所有被试的 mesh 单图')
    args = parser.parse_args()

    # 起点确定：显式 offset 优先，否则自动定位休息段
    if args.offset is not None:
        offset_s = args.offset
    else:
        offset_s = find_rest_offset_s(args.subject, args.rest, args.seconds)

    iq, t_unix = load_iq(args.subject, args.seconds, offset_s)
    print(f'[LOAD] sub-{args.subject}: {len(iq)} 帧 '
          f'({len(iq) / FS:.1f}s, fs={FS}Hz, {CHANNEL}, offset={offset_s:.0f}s)')

    # ---- 单独输出步骤 1 mesh 图 ----
    if args.mesh_only:
        save_mesh_figure(args.subject, iq, OUTPUT_DIR)
        return

    # ---- 批量：所有被试 mesh 单图 ----
    if args.all:
        subjects = sorted(p.name.replace('sub-', '').replace('_', '')
                          for p in DATA_DIR.glob('sub-*_'))
        for sid in subjects:
            try:
                off = find_rest_offset_s(sid, args.rest, args.seconds)
                iq_s, _ = load_iq(sid, args.seconds, off)
                save_mesh_figure(sid, iq_s, OUTPUT_DIR)
            except Exception as e:
                print(f'[SKIP] sub-{sid}: {e}')
        return

    fig = plt.figure(figsize=FIG_SIZE)
    # 面板布局（GridSpec 4 行 × 3 列）：
    # 行1: 3D mesh 距离FFT（占整行 3 列）
    # 行2: 未展开相位 | 解缠相位 | 相位差分
    # 行3: 平滑相位 | 相位FFT | 呼吸时域
    # 行4: 呼吸FFT | 心跳时域 | 心跳FFT
    gs = fig.add_gridspec(4, 3)
    ax_mesh = fig.add_subplot(gs[0, :], projection='3d')
    axes = [[fig.add_subplot(gs[r, c]) for c in range(3)]
            for r in range(1, 4)]

    # ---- 步骤 1：距离维 FFT 3D mesh（静态杂波去除后） ----
    step1_mesh(ax_mesh, iq)

    # ---- 步骤 2-6：相位链路 ----
    phi, idx = step2_extract_phase(axes[0][0], iq)
    phi_u = step3_unwrap(axes[0][1], phi)
    dphi = step4_diff(axes[0][2], phi_u)
    phi_s = step5_smooth(axes[1][0], dphi)
    step6_spectrum(axes[1][1], phi_s, FS)

    # ---- 步骤 7-8：呼吸/心跳分离 ----
    breath_bpm = step7_breath(axes[1][2], axes[2][0], phi_s, FS)
    heart_bpm = step8_heart(axes[2][1], axes[2][2], phi_s, FS)

    fig.suptitle(f'毫米波生命体征信号处理流程 — sub-{args.subject} '
                 f'({CHANNEL}, {len(iq)} 帧 {len(iq) / FS:.1f}s, '
                 f'fs={FS}Hz, 目标距离门 {idx * RANGE_RES_M * 100:.1f}cm)',
                 fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUTPUT_DIR / f'vitalsign_pipeline_sub-{args.subject}_{int(args.seconds)}s.png'
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f'[OK] 全流程图已保存: {out_png}')
    print(f'[RESULT] 呼吸率: {breath_bpm:.1f} 次/分钟 | '
          f'心率: {heart_bpm:.1f} 次/分钟')


if __name__ == '__main__':
    main()
