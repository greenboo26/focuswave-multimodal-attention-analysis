"""
assess_preexp_quality.py — 预实验毫米波心跳质量独立评估（文献标准流程）
====================================================================
版本: v1.0 (2026-08-10)
功能: 对预实验被试（000-007 等）的毫米波 npz 分片数据做
      窗口级心跳可测性评估，判定"有人且心跳可提取"的窗口比例，
      作为全程 HR/HRV 与探针窗分析的前置质量门。

方法（独立管线, 与 0810test 评估一致, 不沿用工作区旧管线）:
  距离功率谱定位 → 相位方差人体判别（真实目标相位受呼吸/心跳
  调制, 静态杂波相位静止）→ 相位 unwrap + 去趋势（静态杂波对消）
  → 呼吸主频估计 → 呼吸谐波 iirnotch 陷波 → 心跳带 (0.8-2.5 Hz)
  主频 + 窄带逐拍 → 窗级指标。

指标:
  SNR(dB)    = 心跳带主峰功率 / 带内噪声底（中位数功率）
  频谱锐度   = 主峰 3dB 宽度内功率占比
  IBI有效率  = IBI ∈ [300, 2000] ms 的间隔占比
  定位漂移   = 前半窗与后半窗距离峰 bin 之差
  相位调制   = 10s 相位角度变化（判别真实目标 vs 静态杂波）

判定:
  窗级: SNR ≥ 3 dB 且 IBI 有效率 ≥ 0.8 → ok（可信）
  被试级: ok 比例 ≥ 70% 可信；≥ 30% 部分可信；< 30% 不可信

用法:
  cd 08_算法/scripts
  python assess_preexp_quality.py --subject 000 --data-root F:/预实验
  python assess_preexp_quality.py --subject 003 --data-root F:/预实验

输出:
  output/09_预实验-SUB{XXX}-QUALITY/
    sub{XXX}_quality_detail.csv   ← 窗级结果
    sub{XXX}_quality_summary.md   ← 汇总报告
    sub{XXX}_quality_timeline.png ← 质量时间线图

依赖: numpy, scipy, matplotlib
"""

from __future__ import annotations

import argparse
import json
import time as time_mod
from pathlib import Path

import numpy as np
from scipy import signal

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

CHUNK = 1000            # 每 npz 片帧数（与采集写入一致）
WINDOW_SEC = 30         # 质量评估窗长（秒），与全程分析窗一致
STEP_SEC = 15           # 窗起始步进（秒），半重叠提升覆盖
FS = 100.0              # 采样率（Hz）
HR_MIN, HR_MAX = 40.0, 100.0   # 静息心率生理范围（bpm）
BR_BAND = (0.1, 0.5)    # 呼吸带 (Hz)
HR_BAND = (0.8, 2.5)    # 心跳带 (Hz)
IBI_MIN, IBI_MAX = 300.0, 2000.0  # IBI 有效范围 (ms)
SNR_OK_DB = 3.0         # 窗级可信 SNR 下界 (dB)
IBI_OK_RATIO = 0.8      # 窗级可信 IBI 有效率下界
PHASE_MOD_RAD = 0.01    # 10s 相位角度变化阈值 (rad)：低于此判静态目标
POWER_RATIO_TARGET = 0.30  # 目标 bin 功率须 ≥ 最强 bin 的该比例（定位竞争判别）
MAX_CAND_BINS = 6         # 每窗最多评估的候选 bin 数（多候选定位, 取 IBI 最优）
MIN_TARGET_BIN = 8        # 人体目标距离下界 (bin ≈ 30cm)
MAX_TARGET_BIN = 45       # 人体目标距离上界 (bin ≈ 1.69m)，超出视为环境反射

# 输出目录（相对 08_算法/output/）
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"


# ============================================================
# 数据加载（流式, 逐片读入 + 缓冲拼窗, 支持长数据）
# ============================================================

def load_timestamps(mmwave_dir: Path, subject: str):
    """读取帧号与 Python 时间戳。

    参数:
        mmwave_dir: mmwave 分片所在目录
        subject: 被试编号（如 000）
    返回:
        frame_idx: (n,) int 数组, 帧号
        py_ms: (n,) int64 数组, 采集电脑 Python 时间戳 (ms)
    """
    frame_idx, py_ms = [], []
    with open(mmwave_dir / f"sub-{subject}_mmwave_timestamps.csv") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            frame_idx.append(int(parts[0]))
            py_ms.append(int(parts[2]))
    return np.array(frame_idx), np.array(py_ms, dtype=np.int64)


def iter_part_files(mmwave_dir: Path, subject: str):
    """遍历所有有效 npz 分片（主文件 + partNNN, 跳过 <100KB 尾片）。

    参数:
        mmwave_dir: mmwave 分片所在目录
        subject: 被试编号
    生成:
        (片索引, npz 文件路径)
    """
    main_npz = mmwave_dir / f"sub-{subject}_mmwave_datacube.npz"
    if main_npz.exists() and main_npz.stat().st_size >= 100_000:
        yield 0, main_npz
    i = 1
    while True:
        fpath = mmwave_dir / f"sub-{subject}_mmwave_datacube_part{i:03d}.npz"
        if not fpath.exists():
            break
        if fpath.stat().st_size >= 100_000:
            yield i, fpath
        i += 1


def load_part(fpath: Path):
    """读取单片 npz 为复数距离域数据 (n, 256, 8)。

    参数:
        fpath: npz 文件路径
    返回:
        iq_fd: (n, 256, 8) complex64, 通道序 tx0_rx0..tx3_rx3
    """
    d = np.load(fpath)
    keys = sorted([k for k in d.keys() if k.startswith('tx')])
    chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
    d.close()
    return chunk


# ============================================================
# 单窗质量评估
# ============================================================

def _phase_modulation(iq: np.ndarray, ch: int, b: int, n_frames: int) -> float:
    """计算 bin 相位在 10s 内的角度变化（判别真实目标 vs 静态杂波）。

    真实人体目标相位受呼吸/心跳调制, 10s 内变化显著; 静态杂波
    仅含噪声级起伏, 变化极小。

    参数:
        iq: 窗数据
        ch: 通道索引
        b: bin 索引
        n_frames: 帧数
    返回:
        phase_mod: 10s 相位变化 (rad)
    """
    phi = np.unwrap(np.angle(iq[:, b, ch]))
    phi_det = signal.detrend(phi)
    seg_len = max(int(10.0 * FS), 1)
    if n_frames >= seg_len:
        return float(np.abs(phi_det[seg_len] - phi_det[0]))
    return float(np.abs(phi_det[-1] - phi_det[0]))


def _heartband_assess(phi_det: np.ndarray, hr_hint: float | None):
    """对去趋势相位做心跳带评估: 呼吸谐波陷波 → 主频/SNR → 逐拍/IBI。

    参数:
        phi_det: 去趋势相位序列
        hr_hint: 被试参考心率 (bpm), 倍频窗重检用
    返回:
        (snr_db, hr_bpm, ibi_ratio, hr_freq_hz) 或 (None, None, None, None)
    """
    breath_bp = _bandpass(phi_det, *BR_BAND)
    br_freq = _dominant_freq(breath_bp, *BR_BAND)
    phi_clean = _notch_harmonics(phi_det, br_freq)

    heart_bp = _bandpass(phi_clean, *HR_BAND)
    f, pxx = signal.periodogram(heart_bp, fs=FS, window="hann")
    mask_hb = (f >= HR_BAND[0]) & (f <= HR_BAND[1])
    if not np.any(mask_hb):
        return None, None, None, None
    p_hb = pxx[mask_hb]
    hr_freq_hz = float(f[mask_hb][np.argmax(p_hb)])
    noise_floor = np.median(p_hb)
    snr_db = 10 * np.log10(p_hb.max() / (noise_floor + 1e-12))
    # 倍频保护: 主频超出生理范围时用参考心率重检窄带
    if not (HR_MIN / 60 <= hr_freq_hz <= HR_MAX / 60) and hr_hint is not None:
        hr_freq_hz = hr_hint / 60.0
    hp = _detect_peaks_narrowband(heart_bp, hr_freq_hz)
    ibi_ratio, hr_bpm = 0.0, None
    if len(hp) >= 3:
        ibi_ms = np.diff(hp) / FS * 1000
        valid = (ibi_ms >= IBI_MIN) & (ibi_ms <= IBI_MAX)
        ibi_ratio = float(np.mean(valid))
        ibi_clean = ibi_ms[valid]
        if len(ibi_clean) >= 3:
            hr_bpm = 60000.0 / np.mean(ibi_clean)
    return snr_db, hr_bpm, ibi_ratio, hr_freq_hz


def assess_window(iq: np.ndarray, hr_hint: float | None = None) -> dict:
    """对单窗做心跳质量评估（文献标准流程 + 多候选 bin）。

    流程: 距离功率谱 → 距离门控内多候选 bin（应对近距杂波定位竞争）
    → 相位调制判别（静态杂波 vs 真实目标）→ 逐候选心跳评估（呼吸
    谐波 iirnotch → 心跳带主频/SNR → 窄带逐拍/IBI）→ 取最优候选。

    参数:
        iq: (n, 256, 8) complex64 窗数据
        hr_hint: 被试参考心率 (bpm), 用于倍频窗的窄带重检
    返回:
        dict: 窗级指标与判定
    """
    n_frames = iq.shape[0]
    result = {"ok": False, "reason": "unknown", "snr_db": None,
              "hr_bpm": None, "ibi_ratio": None, "heart_bin": None,
              "drift_bin": None, "phase_mod_rad": None}

    # ── 1. 距离-通道功率谱 ──
    power = np.mean(np.abs(iq) ** 2, axis=0)          # (256, 8)
    ch_power = np.mean(power, axis=0)                  # 每通道总功率
    best_ch = int(np.argmax(ch_power))
    bin_power = power[:, best_ch]                      # 最优通道的距离谱
    peak_power = float(bin_power.max())

    # ── 2. 多候选 bin（距离门控内功率 top N, 应对近距杂波竞争） ──
    zone = slice(MIN_TARGET_BIN, MAX_TARGET_BIN + 1)
    if zone.start >= len(bin_power):
        result["reason"] = "no_target"
        return result
    zone_power = bin_power[zone]
    zone_max = float(zone_power.max())
    # 门控内必须有可分辨目标: 功率 ≥ 全局最强 30% 且 ≥ 全局最强 5%
    # （30%: 定位竞争下人体目标应与杂波相当; 5%: 保证不是纯噪声 bin）
    if zone_max < peak_power * POWER_RATIO_TARGET or zone_max < peak_power * 0.05:
        # 门控内无目标 → 看全局最强 bin 是否静态（区分"无人"与"雷达没照到"）
        gb = int(np.argmax(bin_power))
        ph_mod_g = _phase_modulation(iq, best_ch, gb, n_frames)
        result["phase_mod_rad"] = round(ph_mod_g, 4)
        result["reason"] = "static_target" if ph_mod_g < PHASE_MOD_RAD else "no_target"
        return result
    cand_bins = [zone.start + int(idx) for idx in
                 np.argsort(zone_power)[::-1][:MAX_CAND_BINS]]

    # ── 3. 逐候选评估, 取 IBI 有效率最高者 ──
    best = None
    for b in cand_bins:
        ph_mod = _phase_modulation(iq, best_ch, b, n_frames)
        if ph_mod < PHASE_MOD_RAD:                     # 静态杂波 bin
            continue
        phi = np.unwrap(np.angle(iq[:, b, best_ch]))
        phi_det = signal.detrend(phi)
        snr_db, hr_bpm, ibi_ratio, _ = _heartband_assess(phi_det, hr_hint)
        if snr_db is None:
            continue
        score = (ibi_ratio >= IBI_OK_RATIO, snr_db >= SNR_OK_DB, ibi_ratio, snr_db)
        if best is None or score > best[0]:
            best = (score, {"heart_bin": int(b), "snr_db": round(float(snr_db), 2),
                            "hr_bpm": round(float(hr_bpm), 1) if hr_bpm else None,
                            "ibi_ratio": round(float(ibi_ratio), 3),
                            "phase_mod_rad": round(ph_mod, 4)})
    if best is None:
        # 有目标但所有候选相位调制不足（无人体微动）
        result["phase_mod_rad"] = round(_phase_modulation(iq, best_ch, cand_bins[0], n_frames), 4)
        result["reason"] = "static_target"
        return result
    result.update(best[1])

    # ── 4. 定位漂移（前半窗 vs 后半窗距离峰之差） ──
    half = n_frames // 2
    if half >= 100:                                    # 少于 1s 不做漂移估计
        p1 = np.mean(np.abs(iq[:half]) ** 2, axis=0)
        p2 = np.mean(np.abs(iq[half:]) ** 2, axis=0)
        b1 = int(np.argmax(p1[:, best_ch]))
        b2 = int(np.argmax(p2[:, best_ch]))
        result["drift_bin"] = int(abs(b1 - b2))
    else:
        result["drift_bin"] = 0

    # ── 5. 判定: SNR ≥ 3dB 且 IBI 有效率 ≥ 0.8 ──
    if result["snr_db"] >= SNR_OK_DB and result["ibi_ratio"] >= IBI_OK_RATIO:
        result["ok"] = True
        result["reason"] = "ok"
    elif result["snr_db"] < SNR_OK_DB:
        result["reason"] = "low_snr"
    else:
        result["reason"] = "low_ibi"
    return result


def _bandpass(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """零相位 butter 带通滤波。"""
    sos = signal.butter(4, [lo, hi], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)


def _dominant_freq(x: np.ndarray, lo: float, hi: float) -> float | None:
    """带内周期图主频 (Hz), 无有效峰返回 None。"""
    f, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask = (f >= lo) & (f <= hi)
    if not np.any(mask):
        return None
    return float(f[mask][np.argmax(pxx[mask])])


def _notch_harmonics(phi: np.ndarray, br_freq: float | None,
                     n_harm: int = 3, q: float = 30.0) -> np.ndarray:
    """对呼吸基频 1..n_harm 次谐波做 iirnotch 陷波。

    呼吸波形非正弦, 谐波落入心跳带 (0.8-2.5 Hz) 污染峰值检测;
    陷波系数按文献标准流程取 Q=30（带宽 ≈ 主频/30）。

    参数:
        phi: 相位位移序列
        br_freq: 呼吸主频 (Hz), None 则跳过
        n_harm: 陷波谐波数
        q: 陷波品质因数
    返回:
        陷波后的相位序列
    """
    if br_freq is None:
        return phi
    y = phi.copy()
    for k in range(1, n_harm + 1):
        fk = br_freq * k
        if fk >= HR_BAND[1]:                           # 超出心跳带无需陷波
            continue
        b, a = signal.iirnotch(fk, q, FS)
        y = signal.filtfilt(b, a, y)
    return y


def _detect_peaks_narrowband(heartbeat: np.ndarray, hr_freq: float) -> np.ndarray:
    """窄带逐拍峰值检测（主频 ±0.05Hz 带通后逐拍取局部最大）。

    参数:
        heartbeat: 心跳带相位序列
        hr_freq: 心跳主频 (Hz)
    返回:
        peaks: (m,) int 峰值帧索引
    """
    if hr_freq is None:
        return np.array([], dtype=int)
    lo_nb, hi_nb = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
    xn = _bandpass(heartbeat, lo_nb, hi_nb)
    ref = 1.0 / hr_freq
    n_pts = len(xn)
    peaks_list = []
    i = 0
    while i < n_pts:
        lo_i, hi_i = int(i + 0.75 * ref * FS), min(int(i + 1.35 * ref * FS), n_pts)
        if lo_i >= n_pts or hi_i <= lo_i:
            break
        p = lo_i + int(np.argmax(xn[lo_i:hi_i]))
        peaks_list.append(p)
        i = p + 1
    return np.array(peaks_list, dtype=int)


# ============================================================
# 按帧号加载（流式: 每窗只读覆盖的 2-4 片, 避免全量入内存）
# ============================================================

def load_frames_by_time(mm_dir: Path, subject: str, frame_idx: np.ndarray,
                        fa_row: int, fb_row: int) -> np.ndarray:
    """按帧行索引 [fa_row, fb_row) 加载复数距离域数据。

    片 i 覆盖帧 [FIRST_FRAME + i*CHUNK, FIRST_FRAME + (i+1)*CHUNK)。
    30s 窗 ≈ 3 片, 相邻窗重叠片由 OS 缓存命中, 无需全局缓冲。

    参数:
        mm_dir: mmwave 分片所在目录
        subject: 被试编号
        frame_idx: 帧号数组（与 timestamps.csv 对齐）
        fa_row: 起始帧的行索引
        fb_row: 结束帧的行索引（不含）
    返回:
        iq_fd: (fb_row-fa_row, 256, 8) complex64
    """
    first_frame = int(frame_idx[0])
    i_start = (int(frame_idx[fa_row]) - first_frame) // CHUNK
    i_end = (int(frame_idx[fb_row - 1]) - first_frame) // CHUNK
    chunks = []
    for i in range(i_start, i_end + 1):
        fpath = mm_dir / (f"sub-{subject}_mmwave_datacube.npz" if i == 0
                          else f"sub-{subject}_mmwave_datacube_part{i:03d}.npz")
        if not fpath.exists():
            continue
        chunks.append(load_part(fpath))
    iq = np.concatenate(chunks)
    base_frame = first_frame + i_start * CHUNK
    lo = int(frame_idx[fa_row]) - base_frame
    hi = lo + (fb_row - fa_row)
    return iq[lo:hi]


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="预实验毫米波心跳质量独立评估")
    parser.add_argument("--subject", type=str, default="000", help="被试编号（如 000）")
    parser.add_argument("--data-root", type=str, default="F:/预实验",
                        help="数据根目录, 含 sub-XXX_/ 子目录")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="输出目录名（相对 output/）")
    args = parser.parse_args()

    subject = args.subject.zfill(3)
    data_root = Path(args.data_root)
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    out_name = args.output_dir or f"09_预实验-SUB{subject}-QUALITY"
    out_dir = OUTPUT_ROOT / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    t_all = time_mod.time()
    print("=" * 60)
    print(f"  sub-{subject} 心跳质量独立评估（文献标准流程）")
    print(f"  数据: {mm_dir}")
    print("=" * 60)

    # ── 1. 时间戳 + 分片清单 ──
    frame_idx, py_ms = load_timestamps(mm_dir, subject)
    parts = list(iter_part_files(mm_dir, subject))
    print(f"[1/4] 帧 {frame_idx[0]}-{frame_idx[-1]} ({len(frame_idx)} 帧), "
          f"{len(parts)} 片, 覆盖 {(py_ms[-1] - py_ms[0]) / 1000:.0f}s")

    t_start_ms, t_end_ms = int(py_ms[0]), int(py_ms[-1])
    win_ms = WINDOW_SEC * 1000
    step_ms = STEP_SEC * 1000
    n_win = max(1, int((t_end_ms - t_start_ms - win_ms) / step_ms) + 1)

    # ── 2. 窗级扫描（按帧号加载, 30s 窗 × 15s 步进） ──
    print(f"[2/4] {WINDOW_SEC}s 窗 × {STEP_SEC}s 步进, 共 {n_win} 窗...")
    rows = []
    for k in range(n_win):
        w0 = t_start_ms + k * step_ms
        w1 = w0 + win_ms
        # 时间 → 帧行索引（searchsorted 返回行索引, 须经 frame_idx 转帧号）
        fa = int(np.searchsorted(py_ms, w0))
        fb = int(np.searchsorted(py_ms, w1))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < int(0.8 * WINDOW_SEC * FS):
            rows.append({"t_start_s": round((w0 - t_start_ms) / 1000),
                         "ok": False, "reason": "short_data"})
            continue
        iq = load_frames_by_time(mm_dir, subject, frame_idx, fa, fb)
        res = assess_window(iq)
        row = {"t_start_s": round((w0 - t_start_ms) / 1000)}
        row.update(res)
        rows.append(row)
        if k % 20 == 0 or res["ok"]:
            print(f"  win{k+1}/{n_win} @{row['t_start_s']}s: "
                  f"{'OK' if res['ok'] else res['reason']} "
                  f"SNR={res['snr_db']}dB HR={res['hr_bpm']}bpm "
                  f"IBI={res['ibi_ratio']}")

    # ── 3. 汇总 ──
    print("[3/4] 汇总...")
    ok_rows = [r for r in rows if r["ok"]]
    ratio = len(ok_rows) / len(rows) if rows else 0.0
    hrs = [r["hr_bpm"] for r in ok_rows if r.get("hr_bpm")]
    snrs = [r["snr_db"] for r in ok_rows if r.get("snr_db") is not None]
    drifts = [r["drift_bin"] for r in ok_rows if r.get("drift_bin") is not None]
    verdict = "可信" if ratio >= 0.70 else ("部分可信" if ratio >= 0.30 else "不可信")
    summary = {
        "subject": subject,
        "n_windows": len(rows),
        "n_ok": len(ok_rows),
        "ok_ratio": round(ratio, 3),
        "hr_median_bpm": round(float(np.median(hrs)), 1) if hrs else None,
        "snr_median_db": round(float(np.median(snrs)), 2) if snrs else None,
        "drift_median_bin": round(float(np.median(drifts)), 1) if drifts else None,
        "verdict": verdict,
        "reasons": {},
    }
    for r in rows:
        summary["reasons"][r["reason"]] = summary["reasons"].get(r["reason"], 0) + 1
    print(f"  可信窗: {len(ok_rows)}/{len(rows)} ({ratio:.0%}) → {verdict}")
    print(f"  HR 中位数: {summary['hr_median_bpm']} bpm, "
          f"SNR 中位数: {summary['snr_median_db']} dB")
    print(f"  原因分布: {summary['reasons']}")

    # ── 4. 保存 CSV + 汇总 MD + 时间线图 ──
    csv_path = out_dir / f"sub{subject}_quality_detail.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=[
            "subject", "t_start", "ok", "reason", "snr_db",
            "hr_bpm", "ibi_ratio", "heart_bin", "drift_bin", "phase_mod_rad"])
        writer.writeheader()
        for r in rows:
            writer.writerow({"subject": f"sub-{subject}_", "t_start": r["t_start_s"],
                             "ok": r["ok"], "reason": r["reason"],
                             "snr_db": r["snr_db"], "hr_bpm": r["hr_bpm"],
                             "ibi_ratio": r["ibi_ratio"], "heart_bin": r["heart_bin"],
                             "drift_bin": r["drift_bin"],
                             "phase_mod_rad": r["phase_mod_rad"]})
    print(f"  [csv] {csv_path}")

    md_path = out_dir / f"sub{subject}_quality_summary.md"
    md_lines = [
        f"# sub-{subject} 心跳质量评估汇总",
        "",
        f"- 生成时间: {time_mod.strftime('%Y-%m-%d %H:%M')}",
        f"- 数据: {mm_dir}",
        f"- 窗: {WINDOW_SEC}s × {STEP_SEC}s 步进, {len(rows)} 窗",
        "",
        f"## 判定: **{verdict}**",
        "",
        f"- 可信窗: {len(ok_rows)}/{len(rows)} ({ratio:.0%})",
        f"- HR 中位数: {summary['hr_median_bpm']} bpm",
        f"- SNR 中位数: {summary['snr_median_db']} dB",
        f"- 定位漂移中位数: {summary['drift_median_bin']} bin",
        f"- 原因分布: {summary['reasons']}",
        "",
        "窗级判定: SNR ≥ 3dB 且 IBI 有效率 ≥ 0.8 → 可信。",
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  [md] {md_path}")

    _plot_timeline(rows, out_dir / f"sub{subject}_quality_timeline.png", subject)
    print(f"  耗时 {time_mod.time() - t_all:.0f}s")


def _plot_timeline(rows, png_path, subject):
    """质量时间线图: 上=SNR, 下=HR（可信窗）, 背景标质量。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    ts = [r["t_start_s"] / 60 for r in rows]           # 分钟
    fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    colors = ["#c0392b" if r["ok"] else "#95a5a6" for r in rows]
    ax = axes[0]
    ax.bar(ts, [r["snr_db"] if r["snr_db"] is not None else 0 for r in rows],
           width=0.2, color=colors, alpha=0.8)
    ax.axhline(SNR_OK_DB, color="red", linestyle="--", linewidth=1, label=f"SNR 阈值 {SNR_OK_DB}dB")
    ax.set_ylabel("SNR (dB)")
    ax.set_title(f"sub-{subject} 心跳质量时间线（可信窗={sum(1 for r in rows if r['ok'])}）")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ok_ts = [r["t_start_s"] / 60 for r in rows if r["ok"] and r.get("hr_bpm")]
    ok_hr = [r["hr_bpm"] for r in rows if r["ok"] and r.get("hr_bpm")]
    if ok_ts:
        ax.plot(ok_ts, ok_hr, "o-", color="#2e86c1", markersize=3)
    ax.set_xlabel("时间 (分钟)")
    ax.set_ylabel("HR (bpm)")
    ax.set_title("心率（仅可信窗）")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  [png] {png_path}")


if __name__ == "__main__":
    main()
