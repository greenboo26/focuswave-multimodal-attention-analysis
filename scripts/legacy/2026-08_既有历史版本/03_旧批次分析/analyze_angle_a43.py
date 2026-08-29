"""
analyze_angle_a43.py — A43 几何角度复刻（基于 RS6240 固件源码）
================================================================
固件源码 mmw_alg_doa.c 的官方角度实现（2026-08-07 源码恢复后提取）:
  1. 校准: ant_aligned[i] = fft_out[i] × ant_calib_data[i]
     （出厂默认校准值, complex16_reim: 低16位实部/高16位虚部）
  2. A43 干涉测量（方位）: ant5×conj(ant4) + ant4×conj(ant1) + ant1×conj(ant0)
     A43 干涉测量（俯仰）: ant1×conj(ant2) + ant2×conj(ant3) + ant5×conj(ant6) + ant6×conj(ant7)
  3. 角度: 硬件 MDSP 查表（arcsin 型）, 系数 ANGLE_CORRECT_FACTOR=2608,
     角度单位 = 度×128。软件复刻用 atan2 取干涉相位特征。

目的: 验证"人 vs 墙反射"在方位相位特征上是否可分（008 空场景 vs 真人）。

用法:
  cd 08_算法/scripts
  python analyze_angle_a43.py

依赖: numpy
"""

import sys
import os
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR.parent))  # scripts/ 父目录（含生产管线）

import analyze_mmwave_hrv as rhrv

# ============================================================
# RS6240 出厂默认校准数据（固件 mmw_alg_ant_calibration.c,
# complex16_reim: 低16位=real(int16), 高16位=imag(int16)）
# ============================================================

CALIB_RS6240_U32 = [
    0x0000540C, 0xDDFB5915, 0x1DD38101, 0xE4C356D9,
    0xFFE65413, 0xDF145A2F, 0x1C6382A3, 0xE4C556BC,
]


def calib_complex(u32):
    """解码 complex16_reim uint32 → 复数（int16 有符号）。"""
    def s16(v):
        return v - 65536 if v > 32767 else v
    real = s16(u32 & 0xFFFF)
    imag = s16((u32 >> 16) & 0xFFFF)
    return complex(real, imag)


CALIB = [calib_complex(v) for v in CALIB_RS6240_U32]

# A43 干涉天线对（固件 mmw_angle_azim/elev_phase_a43）
AZIM_PAIRS = [(5, 4), (4, 1), (1, 0)]
ELEV_PAIRS = [(1, 2), (2, 3), (5, 6), (6, 7)]


# ============================================================
# A43 角度复刻
# ============================================================

def apply_calib(iq, bin_idx):
    """应用出厂校准: ant_aligned[i] = iq[:,bin,ch] × calib[i]。

    参数:
        iq: (n, 256, 8) complex64
        bin_idx: 目标距离门
    返回:
        (n, 8) complex128 校准后天线数据
    """
    ant = iq[:, bin_idx, :].astype(np.complex128)
    return ant * np.array(CALIB, dtype=np.complex128)


def azim_phase_angle(ant):
    """A43 方位干涉相位 → 角度特征（atan2, 单位: 弧度）。

    干涉和 = Σ ant[a]×conj(ant[b])（与固件相位和一致, 相位角即方位指示）。
    """
    s = np.zeros(ant.shape[0], dtype=np.complex128)
    for a, b in AZIM_PAIRS:
        s += ant[:, a] * np.conj(ant[:, b])
    return np.angle(s)


def elev_phase_angle(ant):
    """A43 俯仰干涉相位（同方位逻辑）。"""
    s = np.zeros(ant.shape[0], dtype=np.complex128)
    for a, b in ELEV_PAIRS:
        s += ant[:, a] * np.conj(ant[:, b])
    return np.angle(s)


def angle_spectrum_calib(iq, bin_idx):
    """校准后 8 通道沿天线维 FFT 的角度谱（DBF 近似, 与固件 mmw_angle_fft 类似）。"""
    ant = apply_calib(iq, bin_idx)
    spec = np.mean(np.abs(np.fft.fft(ant, axis=1)), axis=0)
    return spec


# ============================================================
# 主流程: 008 空场景 vs 真人 判别测试
# ============================================================

def main():
    subj = "008"
    rhrv.SUBJECT = subj
    rhrv.MMWAVE_DIR = rhrv.Path(rf"F:\sub-{subj}_\mmwave")
    rhrv.BEH_TIMELINE = rhrv.Path(rf"F:\sub-{subj}_\beh\master_timeline.csv")
    frame_idx, py_ms = rhrv.load_timestamps()
    rhrv.FIRST_FRAME = int(frame_idx[0])
    rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK
    segs = rhrv.parse_rest_segments()

    print("=" * 60)
    print("  A43 角度复刻: 空场景(墙) vs 真人 方位相位判别")
    print("=" * 60)

    def features(iq):
        """对窗内最强 bin 计算方位/俯仰相位角度。"""
        power = np.mean(np.abs(iq) ** 2, axis=0)
        b = int(np.argmax(power))
        ant = apply_calib(iq, b)
        az = azim_phase_angle(ant)
        el = elev_phase_angle(ant)
        # 相位角统计（圆形均值）
        def circ_mean(phi):
            return np.angle(np.mean(np.exp(1j * phi)))
        return {
            "bin": b,
            "azim_mean_deg": np.degrees(circ_mean(az)),
            "azim_std_deg": np.degrees(np.std(az)),
            "elev_mean_deg": np.degrees(circ_mean(el)),
            "elev_std_deg": np.degrees(np.std(el)),
        }

    # 空场景（休息段, 被试不在）
    rest_feats = []
    for s in segs:
        t0 = s["t0_ms"] + 30000
        t1 = t0 + 30000
        fa = max(int(np.searchsorted(py_ms, t0)), 0)
        fb = min(int(np.searchsorted(py_ms, t1)), len(frame_idx) - 1)
        iq = rhrv.load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
        rest_feats.append(features(iq))

    # 真人（任务段, 各休息段前 90s）
    task_feats = []
    for s in segs:
        t0 = s["t0_ms"] - 90000
        t1 = t0 + 30000
        fa = max(int(np.searchsorted(py_ms, t0)), 0)
        fb = min(int(np.searchsorted(py_ms, t1)), len(frame_idx) - 1)
        iq = rhrv.load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
        task_feats.append(features(iq))

    print(f"\n{'场景':<8} {'方位角(°)':>14} {'方位σ(°)':>10} {'俯仰角(°)':>12} {'俯仰σ(°)':>10}")
    for name, feats in [("空场景(墙)", rest_feats), ("真人", task_feats)]:
        for f in feats:
            print(f"{name:<8} {f['azim_mean_deg']:>10.1f} {f['azim_std_deg']:>10.1f} "
                  f"{f['elev_mean_deg']:>10.1f} {f['elev_std_deg']:>10.1f} (bin{f['bin']})")

    az_rest = np.array([f["azim_mean_deg"] for f in rest_feats])
    az_task = np.array([f["azim_mean_deg"] for f in task_feats])
    el_rest = np.array([f["elev_mean_deg"] for f in rest_feats])
    el_task = np.array([f["elev_mean_deg"] for f in task_feats])
    print(f"\n方位角: 空场景 {az_rest.mean():.1f}±{az_rest.std():.1f}° vs 真人 {az_task.mean():.1f}±{az_task.std():.1f}°")
    print(f"俯仰角: 空场景 {el_rest.mean():.1f}±{el_rest.std():.1f}° vs 真人 {el_task.mean():.1f}±{el_task.std():.1f}°")
    # 判别: 两组均值差 vs 组内变异
    sep_az = abs(az_rest.mean() - az_task.mean()) / max(az_rest.std() + az_task.std(), 1e-9)
    sep_el = abs(el_rest.mean() - el_task.mean()) / max(el_rest.std() + el_task.std(), 1e-9)
    print(f"\n分离度(均值差/联合σ): 方位={sep_az:.2f}, 俯仰={sep_el:.2f} (>1 视为可分)")


if __name__ == '__main__':
    main()


