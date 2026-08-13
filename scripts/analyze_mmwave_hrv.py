"""
analyze_rest_hrv.py — 正式实验休息段 HRV 分段分析（多被试）
================================================================
目的: 验证 SART 实验中 3 分钟休息时间内 HRV 的变化轨迹，
      判断休息时长 3 分钟是否必要（HRV 是否在更短时间窗内已稳定）。

数据: F:/sub-XXX_/mmwave/（npz 分片 × 1000 帧，首帧号从 timestamps 动态读取）
时间线: F:/sub-XXX_/beh/master_timeline.csv（休息段 = block_stop → rest_stop）

设计:
  5 个休息段（实测 183.5-189.2s）× 3 个 60s 窗（0-60 / 60-120 / 120-180s）
  每窗独立提取心跳/呼吸 → HRV 时域（SDNN/RMSSD）+ 频域（LF/HF/LF-HF）
  跨段聚合（均值 ± SE）→ 轨迹图 → 稳定点判断

v1.1 (2026-08-07):
  窗级自适应选 bin —— 原段级固定 bin 在部分窗口信号质量差,
  峰值检测锁倍频/谐波 (HR 出现 51→104→51 跳变)。改为每窗在
  幅度稳定的候选 (ch, bin) 中, 按 "HR 落在 40-100 bpm 生理范围 +
  IBI CV < 0.12 + 峰值数 ≥ 30" 评分取最优, 无合格 bin 的窗标记
  为不可信并排除出聚合。

方法: 复用 analyze_rest_3min 主线（vmd_heart + bp + 窄带逐拍检测），
      窗长为 60s 保证频域分辨率（f_res≈0.017Hz，可分辨 LF 带）。

用法:
  cd 08_算法/scripts
  python analyze_rest_hrv.py --subject 001
  python analyze_rest_hrv.py --subject 007

输出:
  output/旧实验/08_旧批次-SUB{XXX}-REST-HRV/
    sub{XXX}_rest_hrv_windows.json   ← 每段每窗指标 + 聚合统计
    sub{XXX}_rest_hrv_trajectory.png ← 3 窗轨迹图（个体线 + 均值±SE）

依赖: numpy, scipy, matplotlib, vmdpy
"""

import os
import sys
import csv
import json
import glob
import time as time_mod
from pathlib import Path

import numpy as np
from scipy import signal, stats

# ── 复用已有管线的函数（analyze_rest_3min.py 为纯函数模块, 无副作用）──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from process_vital_signs_v2 import FS, N_CH, _sos_bandpass
from process_vital_signs_v3 import separate_vmd_heart_only
from process_vital_signs_v9 import suppress_harmonics  # v9 谐波陷波模块
from analyze_rest_3min import (
    accumulate_range_profile,
    select_bins_from_profile,
    estimate_freq_periodogram,
    compute_hrv_time,
    compute_hrv_frequency,
)


# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

# 数据路径（subject 由命令行 --subject 传入, 根目录由 --data-root 覆盖）
SUBJECT = "001"
DATA_ROOT = Path("E:")  # 数据根目录（原 F: 盘数据已迁移至 E: 根目录）,
                        # 预实验数据传 E:\预实验（--data-root 覆盖）
MMWAVE_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "mmwave"
BEH_TIMELINE = DATA_ROOT / f"sub-{SUBJECT}_" / "beh" / "master_timeline.csv"
OUTPUT_DIR = Path(rf"D:\Project\厚粲杯\08_算法\output\08_旧批次-SUB{SUBJECT}-REST-HRV")

# 分析参数
WINDOW_SEC = 30            # 每窗时长（秒）。2026-08-13: 60s→30s, 与全程窗管线一致;
                           # 60s 长窗下候选收集的相位方差/幅度 CV 条件失效（呼吸累积
                           # 漂移+坐姿微调累积）致 46% 窗被误拒, 30s 窗同段 86% 可信
N_WINDOWS = 6              # 每休息段最多切窗数（30s×6=180s, 段尾不足 30s 自动跳过）
METHOD = "vmd_heart"       # 分离方法（当前主线: 心跳 VMD, 呼吸 bp）
CHUNK = 1000               # 每 npz 片帧数（与采集写入一致）
HRV_RS_FS = 4.0            # HRV 频域重采样率 (Hz), Task Force 1996 建议 2-4 Hz

FIRST_FRAME = None         # 首帧号（雷达上电即发帧, 各被试不同, 从 timestamps 首行读取）
N_PARTITIONS = None        # npz 有效片数（= frame_count // CHUNK, 各被试不同）
BIN_OFFSET = 0             # npz 距离裁剪偏移（新采集数据 bin_offset=8, 旧数据=0,
                           # 由 load_frames 读取 npz 内 bin_offset 字段自动更新）

# 窗级 bin 评分门限（生理合理性 + 检测稳定性）
HR_MIN, HR_MAX = 40.0, 100.0   # 静息心率生理范围（bpm），超出视为锁倍频/伪影
IBI_CV_MAX = 0.12              # IBI 变异系数上限，过大说明峰值检测不可靠
MIN_PEAKS_RATE = 0.5           # 每窗最少峰值 = 窗长(秒)×0.5（30s→15 拍起,
                               # 下限 15）。原固定 30 拍对 30s 窗过严: 任务态
                               # 检测效率 75-85%, 25-29 拍窗被误拒（实测
                               # 探针窗可用率 29%→71%）
MAX_CANDIDATES = 24            # 候选 (ch, bin) 上限，控制评分耗时
MOTION_RATIO_MAX = 0.30        # 窗内动作帧占比上限，超过判不可信（动作帧由
                               # 帧间幅度差分 + MAD 稳健阈值检测）
MIN_TARGET_BIN = 0             # 距离下界已取消。2026-08-12 实测: 下限 0 与 2 无
                               # 差异（000/003/rest_3min 质量一致, 无窗误选 DC
                               # bin), 近场底噪与 DC bin 由相位方差/幅度 CV/
                               # 心跳合理性门控过滤。人体主瓣可落在近场带
                               # （000/004 型实测主瓣 bin 6）, 原下界 bin 8 会
                               # 把这类主瓣排除导致 no_target 误判
MAX_TARGET_BIN = 45            # 人体目标距离上界 (bin ≈ 1.69m)。远距 bin 是
                               # 环境反射（风扇/空调/窗外/墙）, 实测 007/008
                               # 曾选到 bin253(≈9.4m) 误判为心跳, 必须排除


# ============================================================
# 数据加载
# ============================================================

def parse_rest_segments():
    """解析 master_timeline.csv, 提取休息段起止时间。

    休息段 = block_stop → rest_stop（rest_stop 是程序记录的休息结束打点,
    事件 detail 带实测休息时长）。Block6 后无休息段。

    Returns:
        list[dict]: [{"label": "rest1", "t0_ms": int, "t1_ms": int}]
    """
    segments = []
    pending_stop = None  # 上一个 block_stop 时刻
    rest_idx = 0
    with open(BEH_TIMELINE, encoding="utf-8", newline="") as f:
        # 用 csv 模块解析: detail 字段含逗号（如被试信息）, split(",") 会拆错
        for parts in csv.reader(f):
            if len(parts) < 3 or not parts[2].strip().isdigit():
                continue
            event, detail, ts = parts[0], parts[1], int(parts[2])
            if event == "block_stop":
                pending_stop = ts
            elif event == "rest_stop" and pending_stop is not None:
                rest_idx += 1
                segments.append({
                    "label": f"rest{rest_idx}",
                    "t0_ms": pending_stop,
                    "t1_ms": ts,
                    "rest_s": float(detail.replace("rest=", "").replace("s", "")),
                })
                pending_stop = None
    return segments


def load_behavior_span(subject_dir=None):
    """读 master_timeline.csv 取任务数据起止时间 (unix_ms)。

    严格按行为时间轴截断: 任务数据 = sart_start → 最后 block_stop,
    排除实验开始前 (cover/instructions/practice) 与结束后 (结束界面停留)
    的雷达数据。找不到时间轴返回 (None, None) (调用方全量+警告)。

    参数:
        subject_dir: sub-XXX_ 目录 (含 beh/master_timeline.csv);
                     None 时用模块全局 DATA_ROOT 推导
    返回:
        (sart_start_ms, last_block_stop_ms), 缺失项为 None
    """
    if subject_dir is None:
        subject_dir = BEH_TIMELINE.parent.parent if hasattr(BEH_TIMELINE, "parent") else None
    tl = subject_dir / "beh" / "master_timeline.csv"
    if tl is None or not tl.exists():
        return None, None
    sart_start = None
    last_block_stop = None
    with open(tl, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("event") == "sart_start":
                sart_start = int(row["unix_ms"])
            elif row.get("event") == "block_stop":
                last_block_stop = int(row["unix_ms"])
    return sart_start, last_block_stop


def load_timestamps():
    """读取帧号与 Python 时间戳（与 timeline 同源, 跨设备对齐最可靠）。

    Returns:
        frame_idx: (n,) int 数组, 帧号
        py_ms: (n,) int64 数组, 采集电脑 Python 时间戳 (ms)
    """
    frame_idx, py_ms = [], []
    with open(MMWAVE_DIR / f"sub-{SUBJECT}_mmwave_timestamps.csv") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            frame_idx.append(int(parts[0]))
            py_ms.append(int(parts[2]))
    return np.array(frame_idx), np.array(py_ms, dtype=np.int64)


def load_frames(fa, fb):
    """按帧范围 [fa, fb) 加载复数距离域数据。

    帧号 → npz 片: 片 i 覆盖帧 [FIRST_FRAME + i*CHUNK, FIRST_FRAME + (i+1)*CHUNK)。
    片 0 是主文件, 片 1+ 是 partNNN；尾部空片（<100KB）跳过。

    Returns:
        iq_fd: (fb-fa, 256, 8) complex64, 通道序 tx0_rx0..tx3_rx3
    """
    i_start = (fa - FIRST_FRAME) // CHUNK
    i_end = (fb - FIRST_FRAME + CHUNK - 1) // CHUNK
    chunks = []
    offset0 = FIRST_FRAME + i_start * CHUNK
    for i in range(i_start, min(i_end, N_PARTITIONS)):
        fpath = MMWAVE_DIR / (f"sub-{SUBJECT}_mmwave_datacube.npz" if i == 0
                              else f"sub-{SUBJECT}_mmwave_datacube_part{i:03d}.npz")
        if not fpath.exists() or fpath.stat().st_size < 100_000:
            continue  # 尾部空片（崩溃重试残留）
        d = np.load(fpath)
        # 距离裁剪偏移: 新采集数据 npz 只含近距离 bin（bin_offset=8）,
        # 旧数据无此字段 → 保持 0（完整 256 bin）
        if 'bin_offset' in d:
            global BIN_OFFSET
            BIN_OFFSET = int(d['bin_offset'])
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        d.close()
        chunks.append(chunk)
    iq = np.concatenate(chunks)
    lo = fa - offset0
    hi = lo + (fb - fa)
    return iq[lo:hi]


# ============================================================
# 窗级自适应 bin 选择（v1.1）
# ============================================================

def detect_motion_frames(iq, mad_k=5.0):
    """逐帧动作检测: 帧间幅度变化率超过稳健阈值（median+k×MAD）的帧。

    呼吸/心跳微动几乎不改变回波幅度, 而大幅度动作（起身/挥手/转头等）
    突变反射几何 → 帧间幅度差分大。用 MAD（中位数绝对偏差）稳健统计
    定阈值, 不依赖绝对幅度（不同被试/距离的幅度绝对值差异大）。

    参数:
        iq: (n, 256, 8) complex64 窗数据
        mad_k: 阈值系数（倍数中位数）, 默认 5
    返回:
        motion: (n-1,) bool, True=动作帧
        ratio: 动作帧占比
    """
    mag = np.mean(np.abs(iq), axis=(1, 2))  # 每帧全场景平均幅度
    d = np.abs(np.diff(mag))
    med = np.median(d)
    mad = 1.4826 * np.median(np.abs(d - med))
    thresh = med + mad_k * mad
    motion = d > thresh
    return motion, float(np.mean(motion))


def spc_score(iq, ch, b, radius=2):
    """相邻距离单元相位相干性（SPC, 空间相位相干）。

    文献判据（UESTC Optimizing SNR 等）: 胸腔反射覆盖相邻 bin,
    生命体征单元与邻居的相位差分相关高; 纯噪声 bin 相邻相位不相关。
    与距离/SNR 解耦, 替代固定相位方差阈值（后者随距离失效）。

    参数:
        iq: (n, 256, 8) 窗数据
        ch: 通道索引
        b: 候选 bin
        radius: 相邻半径（bin）
    返回:
        SPC 评分（与 ±radius bin 相位差分的最大 |r|, 0-1）
    """
    pd = np.diff(np.unwrap(np.angle(iq[:, b, ch])))
    rs = []
    for nb in range(max(0, b - radius), min(iq.shape[1], b + radius + 1)):
        if nb == b:
            continue
        pd2 = np.diff(np.unwrap(np.angle(iq[:, nb, ch])))
        r = stats.pearsonr(pd, pd2)[0]
        rs.append(abs(r) if r == r else 0.0)
    return max(rs) if rs else 0.0


def collect_candidates(iq, max_candidates=MAX_CANDIDATES):
    """窗内收集候选 (ch, bin), 按 SPC 空间相位相干排序。

    过滤规则（2026-08-13 修订, 文献依据）: 功率高于峰值 1%、
    距离门控、幅度 CV < 30%（闪烁伪影）; 弃用固定相位方差阈值
    （phi_var 随距离/SNR 剧烈变化, 人体 bin 实测 70 会超 50 上限误拒）,
    改用 SPC 排序取前 max_candidates。

    Returns:
        list[tuple]: [(ch, bin), ...]，按 SPC 降序
    """
    power = np.mean(np.abs(iq) ** 2, axis=0)  # (256, 8)
    raw = []
    for ch in range(N_CH):
        bin_power = power[:, ch]
        thresh = np.max(bin_power) * 0.01
        for b in range(len(bin_power)):
            if bin_power[b] < thresh:
                continue
            # 距离门控: 排除人体距离范围外的 bin（环境反射误判心跳）
            global_bin = b + BIN_OFFSET
            if not (MIN_TARGET_BIN <= global_bin <= MAX_TARGET_BIN):
                continue
            mag = np.abs(iq[:, b, ch])
            if np.std(mag) / (np.mean(mag) + 1e-12) >= 0.30:
                continue
            raw.append((int(ch), int(b)))
    # SPC 排序取 top N（文献判据, 与距离解耦）
    scored = sorted(raw, key=lambda cb: spc_score(iq, cb[0], cb[1]), reverse=True)
    return scored[:max_candidates]


def evaluate_heart_bin(iq, ch, b):
    """对单个候选 bin 做快速心跳评估（bp 窄带逐拍, 不做 VMD）。

    返回 None（不合格）或 {"hr", "cv", "n"}。生理合理性门控:
    HR ∈ [HR_MIN, HR_MAX]（排除锁倍频/运动伪影）、IBI CV < IBI_CV_MAX、
    峰值数 ≥ MIN_PEAKS。
    """
    phi = np.unwrap(np.angle(iq[:, b, ch]))
    # 呼吸谐波陷波（v9 模块）: 呼吸波形非正弦, 谐波落入心跳带污染检测。
    # 先估呼吸主频, 再对 1/2/3 次谐波陷波, 干净后再做心跳检测
    br_freq_here = estimate_freq_periodogram(
        _sos_bandpass(phi, 0.1, 0.5), 0.1, 0.5)
    phi = suppress_harmonics(phi, br_freq_here)
    heart_bp = _sos_bandpass(phi, 0.8, 2.5)
    hr_freq = estimate_freq_periodogram(heart_bp, 0.8, 2.5)
    hp = detect_heart_peaks_narrowband(heart_bp, hr_freq)
    if len(hp) < 5:
        return None
    ibi_ms = np.diff(hp) / FS * 1000
    ibi_clean = ibi_ms[(ibi_ms >= 300) & (ibi_ms <= 2000)]
    # 最少峰值数按窗长自适应（短窗任务态检测效率 75-85%, 固定 30 拍过严）
    min_peaks = max(15, int(iq.shape[0] / FS * MIN_PEAKS_RATE))
    if len(ibi_clean) < min_peaks:
        return None
    hr = 60000 / np.mean(ibi_clean)
    cv = np.std(ibi_clean) / np.mean(ibi_clean)
    if not (HR_MIN <= hr <= HR_MAX) or cv >= IBI_CV_MAX:
        return None
    # 频域一致性: 逐拍 HR 与 periodogram 主频差 > 5 bpm 视为伪影
    #（窄带以主频为中心, 逐拍 HR 应落在主频 ±0.05Hz ≈ ±3bpm 内）
    if hr_freq is not None and abs(hr - hr_freq * 60) > 5:
        return None
    return {"hr": hr, "cv": cv, "n": int(len(ibi_clean))}


def breath_power_ratio(phi):
    """呼吸带 (0.1-0.5 Hz) 功率占比, 用于挑选呼吸信号最强的 bin。"""
    x = signal.detrend(phi)  # 去线性漂移, 避免 periodogram 直流泄漏
    f, pxx = signal.periodogram(x, fs=FS, window="hann")
    mask_all = (f >= 0.05) & (f <= 3.0)
    mask_br = (f >= 0.1) & (f <= 0.5)
    return np.sum(pxx[mask_br]) / (np.sum(pxx[mask_all]) + 1e-12)


def evaluate_heart_bin_at(iq, ch, b, hr_freq_hz):
    """用指定频率窄带检测候选 bin（段参考修正倍频锁定用, v1.3）。

    正常评估（evaluate_heart_bin）锁定 periodogram 主频, 倍频伪影时
    主频本身锁错（HR≈2×真实值）。此函数绕过主频, 直接用参考频率
    窄带逐拍检测, 并要求结果接近参考（±10bpm）。

    返回 None（不合格）或 {"hr", "cv", "n"}。
    """
    phi = np.unwrap(np.angle(iq[:, b, ch]))
    br_freq_here = estimate_freq_periodogram(
        _sos_bandpass(phi, 0.1, 0.5), 0.1, 0.5)
    phi = suppress_harmonics(phi, br_freq_here)
    heart_bp = _sos_bandpass(phi, 0.8, 2.5)
    hp = detect_heart_peaks_narrowband(heart_bp, hr_freq_hz)
    if len(hp) < 5:
        return None
    ibi_ms = np.diff(hp) / FS * 1000
    ibi_clean = ibi_ms[(ibi_ms >= 300) & (ibi_ms <= 2000)]
    min_peaks = max(15, int(iq.shape[0] / FS * MIN_PEAKS_RATE))
    if len(ibi_clean) < min_peaks:
        return None
    hr = 60000 / np.mean(ibi_clean)
    cv = np.std(ibi_clean) / np.mean(ibi_clean)
    if not (HR_MIN <= hr <= HR_MAX) or cv >= IBI_CV_MAX:
        return None
    if abs(hr - hr_freq_hz * 60) > 10:
        return None  # 必须接近参考频率（否则不是倍频而是真信号差）
    return {"hr": hr, "cv": cv, "n": int(len(ibi_clean))}


def analyze_window_auto(iq, method="vmd_heart", med_hr_hint=None):
    """窗级自适应选 bin + 完整体征分析。

    步骤: 收集候选 → 呼吸 bin（呼吸带功率占比最高）→ 心跳 bin
    （多 bin 交叉验证: 同段多个候选 bin 应观测同一心率, 取与中位数
    一致且 IBI CV 最小的 bin, 排除单个 bin 锁错主频的伪影）→
    选定 bin 上做完整分析。

    v1.3 (2026-08-07): med_hr_hint 段参考修正。单强反射场景（如 001,
    候选 bin 少）倍频锁定无冗余可纠正, 所有候选主频锁错 → 用段内
    其他窗的 HR 中位数重检（生理约束: 心率不会瞬间翻倍）。

    参数:
        iq: (n, 256, 8) complex64 窗数据
        method: 心跳分离方法 bp | vmd_heart
        med_hr_hint: 段参考心率 (bpm), None=不启用
    返回:
        (result, heart_bin, breath_bin) 或 None（无合格心跳 bin）
    """
    # 动作帧占比过高 → 整窗不可信（大幅度动作破坏相位解调）
    _, motion_ratio = detect_motion_frames(iq)
    if motion_ratio > MOTION_RATIO_MAX:
        return None

    cands = collect_candidates(iq)
    if not cands:
        return None

    # 呼吸 bin: 呼吸带功率占比最高的候选（呼吸幅度大, 占比显著）
    br_cb = max(cands, key=lambda cb: breath_power_ratio(
        np.unwrap(np.angle(iq[:, cb[1], cb[0]]))))

    # 多 bin 交叉验证（v1.2）: 收集全部合格候选
    evals = []
    for ch, b in cands:
        ev = evaluate_heart_bin(iq, ch, b)
        if ev is not None:
            evals.append((ev, ch, b))

    hint_used = None
    if not evals and med_hr_hint is not None:
        # v1.3 段参考修正: 所有候选主频锁错（常见倍频）→ 用段中位 HR 重检
        evals = []
        for ch, b in cands:
            ev = evaluate_heart_bin_at(iq, ch, b, med_hr_hint / 60.0)
            if ev is not None:
                evals.append((ev, ch, b))
        if evals:
            hint_used = med_hr_hint
    if not evals:
        return None  # 所有候选都不合格 → 该窗不可信

    if hint_used is not None:
        # 段参考修正成功: 直接选 CV 最小, 跳过窗内中位数剔除
        best_ev, hr_ch, hr_bin = min(evals, key=lambda e: e[0]["cv"])
        med_hr = hint_used
        sel = evals
    else:
        # 同段多 bin 应观测同一心率: 剔除偏离中位数 >10bpm 的 bin
        hrs = np.array([e[0]["hr"] for e in evals])
        med_hr = float(np.median(hrs))
        sel = [e for e in evals if abs(e[0]["hr"] - med_hr) <= 10]
        if not sel:
            sel = evals  # 全部偏离（数据整体差）→ 退回全部, 选 CV 最小
        # 心跳 bin: 与中位数一致者中 IBI CV 最小
        best_ev, hr_ch, hr_bin = min(sel, key=lambda e: (e[0]["cv"], abs(e[0]["hr"] - med_hr)))
    br_ch, br_bin = br_cb

    # 选定 bin 上做完整分析（VMD 分离 + 窄带逐拍 + HRV）
    # 频率锚定 bp 评估值（Hz）, 防止 VMD 后主频漂移到倍频/谐波
    disp_br = np.unwrap(np.angle(iq[:, br_bin, br_ch]))
    disp_hr = np.unwrap(np.angle(iq[:, hr_bin, hr_ch]))
    res = analyze_window(disp_br, disp_hr, method=method,
                         hr_freq_hint=med_hr / 60.0)
    res["quality"] = "ok"
    res["n_consistent_bins"] = len(sel)
    res["motion_ratio"] = round(motion_ratio, 3)
    res["harmonics_corrected"] = hint_used is not None
    # 报告用全局 bin 索引（npz 内相对索引 + 裁剪偏移）
    return res, {"ch": hr_ch, "bin": hr_bin + BIN_OFFSET,
                 "cv": round(best_ev["cv"], 3)}, \
        {"ch": br_ch, "bin": br_bin + BIN_OFFSET}


# ============================================================
# 单窗体征分析（复用主线方法, 60s 窗独立计算）
# ============================================================

def detect_heart_peaks_narrowband(heartbeat, hr_freq):
    """窄带逐拍心跳峰值检测（v1.4 主线方法, 混入呼吸谐波/噪声峰）。

    频域主峰 ±0.05Hz 窄带带通后逐拍取局部最大, 与 3min 脚本一致。
    """
    hp = np.array([], dtype=int)
    if hr_freq is None:
        return hp
    lo_nb, hi_nb = max(hr_freq - 0.05, 0.5), hr_freq + 0.05
    sos_hp = signal.butter(4, [lo_nb, hi_nb], btype='band', fs=FS, output='sos')
    xn = signal.sosfiltfilt(sos_hp, heartbeat)
    ref = 1.0 / hr_freq
    n_pts = len(xn)
    peaks_list = []
    i = 0
    while i < n_pts:
        lo_i, hi_i = int(i + 0.75 * ref * FS), min(int(i + 1.35 * ref * FS), n_pts)
        if lo_i >= n_pts or hi_i <= lo_i:
            break
        p = lo_i + np.argmax(xn[lo_i:hi_i])
        peaks_list.append(p)
        i = p + 1
    return np.array(peaks_list, dtype=int)


def _ibi_continuity_filter(ibi_ms, max_jump_ms=250):
    """相邻 IBI 生理连续性过滤（文献标准做法: 心率不会瞬间跳变）。

    迭代剔除与前后相邻 IBI 差都超过 max_jump_ms 的孤立异常
    （漏检/误检峰导致）。参考 R-peak 检测后处理的常规生理约束。

    参数:
        ibi_ms: IBI 序列 (ms)
        max_jump_ms: 相邻跳变上限 (ms), 静息心率 50-100bpm 对应
                     IBI 600-1200ms, 250ms 跳变 ≈ 40-50% 瞬时变化
    返回:
        np.ndarray: 过滤后的 IBI 序列
    """
    ibi = np.asarray(ibi_ms, dtype=float)
    if len(ibi) < 3:
        return ibi
    for _ in range(3):
        if len(ibi) < 3:
            break
        prev_diff = np.abs(np.diff(ibi, prepend=ibi[0]))
        next_diff = np.abs(np.diff(ibi, append=ibi[-1]))
        bad = (prev_diff > max_jump_ms) & (next_diff > max_jump_ms)
        if not bad.any():
            break
        ibi = ibi[~bad]
    return ibi


def analyze_window(disp_br, disp_hr, method="vmd_heart", hr_freq_hint=None):
    """对单窗位移信号做分离、峰值检测、体征估计（含 HRV 时域+频域）。

    参数:
        disp_br: (n,) 呼吸 bin 的相位位移序列
        disp_hr: (n,) 心跳 bin 的相位位移序列
        method: 心跳分离方法 bp | vmd_heart
        hr_freq_hint: 外部评估的心跳频率 (Hz), 锚定窄带中心防止 VMD
                      主频漂移到倍频/谐波（实测 VMD 后 HR 51→135 假跳变）
    返回:
        dict: 单窗指标（HR/BR/HRV/峰值数）
    """
    # 呼吸: bp 带通 0.1-0.5 Hz
    breath = _sos_bandpass(disp_br, 0.1, 0.5)
    br_freq = estimate_freq_periodogram(breath, 0.1, 0.5)

    # 呼吸谐波陷波（v9 模块）: 用呼吸 bin 的主频（呼吸信号最干净处）
    # 对心跳 bin 的 1/2/3 次谐波陷波, 消除谐波对心跳带污染
    disp_hr = suppress_harmonics(disp_hr, br_freq)

    # 心跳: bp 带通 0.8-2.5 Hz
    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)
    hr_freq_bp = estimate_freq_periodogram(heart_bp, 0.8, 2.5)

    # 频率锚定: 外部 hint 优先（可靠）
    if hr_freq_hint is not None and 0.5 <= hr_freq_hint <= 2.0:
        hr_freq = hr_freq_hint
        # 自动模式直接走 bp 波形: 60s 窗窄带（±0.05Hz）已排除谐波,
        # VMD 波形质量在短窗上不稳定, 实测导致漏检拍 → RMSSD>SDNN 异常
        heartbeat = heart_bp
    else:
        if method == "vmd_heart" and hr_freq_bp is not None:
            heartbeat, _ = separate_vmd_heart_only(disp_hr, hr_freq_hint=hr_freq_bp)
            hr_freq = estimate_freq_periodogram(heartbeat, 0.8, 2.5)
            # 倍频保护: VMD 主频超出生理范围时退回 bp 结果
            if hr_freq is None or not (0.5 <= hr_freq <= 2.0):
                heartbeat = heart_bp
                hr_freq = hr_freq_bp
        else:
            heartbeat = heart_bp
            hr_freq = hr_freq_bp

    # 窄带逐拍检测
    hp = detect_heart_peaks_narrowband(heartbeat, hr_freq)

    # HRV: 时域 + 频域
    hrv = {}
    if len(hp) >= 5:
        ibi_ms = np.diff(hp) / FS * 1000
        ibi_clean = ibi_ms[(ibi_ms >= 300) & (ibi_ms <= 2000)]
        # 生理连续性过滤（文献标准做法）: 相邻 IBI 跳变 >250ms 的孤立异常剔除
        # （心率不会瞬间跳变, 此类 IBI 为漏检/误检峰导致）
        ibi_clean = _ibi_continuity_filter(ibi_clean, max_jump_ms=250)
        if len(ibi_clean) >= 5:
            hrv = compute_hrv_time(ibi_clean)
            # 频域仅长窗计算（LF 0.04-0.15Hz 需 ≥120s 窗才有分辨率）
            if len(disp_hr) / FS >= 120:
                hrv["frequency"] = compute_hrv_frequency(ibi_clean)
            # 非线性特征挂 IBI 序列（供窗级 SampEn/DFA 扩展, v1.4+）
            hrv["ibi_ms"] = ibi_clean.tolist()

    return {
        "hr_freq_bpm": round(float(hr_freq * 60), 1) if hr_freq else None,
        "hr_time_bpm": round(float(60 * FS / np.mean(np.diff(hp))), 1) if len(hp) >= 2 else None,
        "br_freq_bpm": round(float(br_freq * 60), 1) if br_freq else None,
        "n_heart_peaks": int(len(hp)),
        "hrv": hrv,
    }


# ============================================================
# 主流程
# ============================================================

def main():
    global SUBJECT, DATA_ROOT, MMWAVE_DIR, BEH_TIMELINE, OUTPUT_DIR, FIRST_FRAME, N_PARTITIONS
    import argparse
    parser = argparse.ArgumentParser(description="SART 休息段 HRV 分段分析")
    parser.add_argument("--subject", type=str, default="001",
                        help="被试编号（如 001/007），对应 <data-root>/sub-XXX_/")
    parser.add_argument("--data-root", type=str, default=str(DATA_ROOT),
                        help="数据根目录, 默认 E:（旧数据 E:\\sub-XXX_）; 预实验传 E:\\预实验")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="输出目录名（相对 output/）, 默认 08_旧批次-SUB{SUBJECT}-REST-HRV; "
                             "预实验传 09_预实验-SUB{SUBJECT}-REST-HRV 避免覆盖旧分析")
    args = parser.parse_args()

    SUBJECT = args.subject.zfill(3)
    DATA_ROOT = Path(args.data_root)
    MMWAVE_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "mmwave"
    BEH_TIMELINE = DATA_ROOT / f"sub-{SUBJECT}_" / "beh" / "master_timeline.csv"
    out_name = args.output_dir or f"旧实验/08_旧批次-SUB{SUBJECT}-REST-HRV"
    OUTPUT_DIR = Path(rf"D:\Project\厚粲杯\08_算法\output\{out_name}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    t_all = time_mod.time()
    print("=" * 60)
    print(f"  sub-{SUBJECT} 休息段 HRV 分段分析（验证 3 分钟休息必要性）")
    print("=" * 60)

    # ── 1. 解析休息段 ──
    segments = parse_rest_segments()
    print(f"\n[1/5] 休息段: {len(segments)} 个")
    for s in segments:
        print(f"  {s['label']}: {s['t0_ms']} → {s['t1_ms']} ({s['rest_s']}s)")

    # ── 2. 加载时间戳, 建立帧↔时间映射 ──
    frame_idx, py_ms = load_timestamps()
    FIRST_FRAME = int(frame_idx[0])
    N_PARTITIONS = (len(frame_idx) + CHUNK - 1) // CHUNK  # 向上取整, 含尾片
    print(f"[2/5] 时间戳帧范围: {frame_idx[0]}-{frame_idx[-1]}, "
          f"共 {len(frame_idx)} 帧 ({N_PARTITIONS} 片)")

    # ── 3. 逐段逐窗分析 ──
    print(f"[3/5] 分段分析（{N_WINDOWS} × {WINDOW_SEC}s 窗, 窗级自适应选 bin）...")
    all_rows = []   # 每行 = 一个窗的指标（含段标签）
    for si, seg in enumerate(segments):
        t_seg = time_mod.time()
        # 时间 → 行索引 → 帧号（searchsorted 返回行索引, 必须经 frame_idx 转帧号）
        fa = int(np.searchsorted(py_ms, seg["t0_ms"]))
        fb = int(np.searchsorted(py_ms, seg["t1_ms"]))
        fa = max(fa, 0)
        fb = min(fb, len(frame_idx) - 1)
        frame_fa = int(frame_idx[fa])
        frame_fb = int(frame_idx[fb])
        # 窗切分: 30s 窗 × 15s 步进（与全程窗管线完全一致, 重叠窗增加覆盖）
        step_frames = int(15 * FS)
        win_frames = int(WINDOW_SEC * FS)
        n_win_max = max(1, int((frame_fb - frame_fa - win_frames) / step_frames) + 1)
        n_use = frame_fb - frame_fa
        print(f"\n  {seg['label']}: 帧 {frame_fa}-{frame_fb} "
              f"({n_use / FS:.0f}s / {seg['rest_s']}s 可用, 最多 {n_win_max} 窗)")

        # 逐窗分析（第一遍正常检测）
        seg_rows = []
        for k in range(n_win_max):
            f0k = frame_fa + k * step_frames
            f1k = f0k + win_frames
            if f1k > frame_fb:  # 窗超出段尾则跳过
                break
            if f1k - f0k < 15 * FS:  # 窗太短（<15s）则跳过
                continue
            iq = load_frames(f0k, f1k)
            win_res = analyze_window_auto(iq, method=METHOD)
            row = {"segment": seg["label"], "window": k + 1,
                   "t_start_s": round((f0k - frame_fa) / FS),
                   "t_end_s": round((f1k - frame_fa) / FS)}
            if win_res is None:
                row["quality"] = "poor"
                row["reason"] = "无合格心跳 bin（运动伪影或信号差）"
                seg_rows.append(row)
                continue
            res, hr_bin, br_bin = win_res
            row.update(res)
            row["heart_bin"] = hr_bin
            row["breath_bin"] = br_bin
            seg_rows.append(row)

        # 段参考修正（与全程窗一致）: ok 窗 HR 中位 → poor 窗重检
        ref_hrs = [r.get("hr_time_bpm") for r in seg_rows
                   if r.get("quality") == "ok" and r.get("hr_time_bpm")]
        med_hr_seg = float(np.median(ref_hrs)) if ref_hrs else None
        n_corrected = 0
        if med_hr_seg is not None:
            for k, r in enumerate(seg_rows):
                if r.get("quality") == "ok":
                    continue
                f0k = frame_fa + k * step_frames
                f1k = f0k + win_frames
                if f1k > frame_fb:
                    continue
                iq = load_frames(f0k, f1k)
                win_res = analyze_window_auto(iq, method=METHOD, med_hr_hint=med_hr_seg)
                if win_res is not None:
                    res, hr_bin, br_bin = win_res
                    r.update(res)
                    r["heart_bin"] = hr_bin
                    r["breath_bin"] = br_bin
                    r["harmonics_corrected"] = True
                    n_corrected += 1

        for row in seg_rows:
            all_rows.append(row)
            if row.get("quality") == "poor":
                print(f"      win{row['window']} ({row['t_start_s']}-{row['t_end_s']}s): "
                      f"[不可信] {row.get('reason')}")
            else:
                hrv = row.get("hrv", {})
                hrv_s = f"SDNN={hrv.get('SDNN_ms')}ms RMSSD={hrv.get('RMSSD_ms')}ms"
                if "frequency" in hrv and hrv["frequency"]:
                    hrv_s += (f" LF={hrv['frequency']['LF_ms2']} "
                              f"HF={hrv['frequency']['HF_ms2']} LF/HF={hrv['frequency']['LF_HF']}")
                print(f"      win{row['window']} ({row['t_start_s']}-{row['t_end_s']}s): "
                      f"HR={row.get('hr_time_bpm')}bpm {hrv_s}")
        print(f"      [段参考修正救回 {n_corrected} 窗, 耗时 {time_mod.time() - t_seg:.0f}s]")

    # ── 4. 聚合统计: 可信窗的每窗均值 ± SE ──
    print("\n[4/5] 跨段聚合（均值 ± SE, 仅 quality=ok 窗）...")
    ok_rows = [r for r in all_rows if r.get("quality") == "ok"]
    print(f"  可信窗: {len(ok_rows)}/{len(all_rows)}")
    metrics = ["hr_time_bpm", "SDNN_ms", "RMSSD_ms", "LF_ms2", "HF_ms2", "LF_HF"]
    agg = {"windows": [], "metrics": {}}
    for k in range(N_WINDOWS):
        rows_k = [r for r in ok_rows if r["window"] == k + 1]
        if not rows_k:
            continue
        agg["windows"].append({
            "window": k + 1,
            "n_segments": len(rows_k),
            "t_range_s": [rows_k[0]["t_start_s"], rows_k[0]["t_end_s"]],
        })
        line = f"  win{k+1} (n={len(rows_k)}): "
        for m in metrics:
            vals = []
            for r in rows_k:
                if m in ("LF_ms2", "HF_ms2", "LF_HF"):
                    v = r["hrv"].get("frequency", {}).get(m)
                elif m in ("SDNN_ms", "RMSSD_ms"):
                    v = r["hrv"].get(m)
                else:
                    v = r.get(m)
                if v is not None and isinstance(v, (int, float)):
                    vals.append(float(v))
            if vals:
                mean = np.mean(vals)
                # n=1 时无法估 SE, 记为 0（个体线仍展示）
                se = np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0.0
                agg["metrics"].setdefault(m, []).append(
                    {"window": k + 1, "mean": round(mean, 2), "se": round(se, 2)})
                line += f"{m}={mean:.1f}±{se:.1f} "
        print(line)

    # ── 配对检验: 相邻窗差异 (Wilcoxon, 小样本) ──
    print("\n  相邻窗配对检验 (Wilcoxon):")
    for m in ["SDNN_ms", "RMSSD_ms", "HF_ms2", "LF_HF"]:
        per_seg = {}
        for r in ok_rows:
            v = r["hrv"].get(m) if m in ("SDNN_ms", "RMSSD_ms") else r["hrv"].get("frequency", {}).get(m)
            if v is not None and isinstance(v, (int, float)):
                per_seg.setdefault(r["segment"], {})[r["window"]] = float(v)
        # 只统计 3 窗齐全的段
        segs = [s for s in per_seg if all(k in per_seg[s] for k in (1, 2, 3))]
        if len(segs) >= 3:
            for wa, wb, name in [(1, 2, "w1→w2"), (2, 3, "w2→w3")]:
                a = [per_seg[s][wa] for s in segs]
                b = [per_seg[s][wb] for s in segs]
                d = np.array(b) - np.array(a)
                if np.all(d == 0):
                    stat_res = "无变化"
                else:
                    w, p = stats.wilcoxon(a, b)
                    stat_res = f"W={w:.0f}, p={p:.3f}"
                print(f"    {m} {name}: {stat_res} (Δmean={np.mean(d):+.1f}, n={len(segs)})")
    print(f"\n[5/5] 耗时 {time_mod.time() - t_all:.0f}s")

    # ── 保存 JSON ──
    json_path = OUTPUT_DIR / f"sub{SUBJECT}_rest_hrv_windows.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"rows": all_rows, "aggregate": agg}, f, ensure_ascii=False, indent=2)
    print(f"  [json] {json_path}")

    # ── 绘图 ──
    plot_trajectory(ok_rows, agg, OUTPUT_DIR / f"sub{SUBJECT}_rest_hrv_trajectory.png")


def plot_trajectory(rows, agg, png_path):
    """6 面板轨迹图: 每窗均值 ± SE 误差棒 + 个体线（仅可信窗）。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    panels = [
        ("hr_time_bpm", "HR (bpm)", "心率"),
        ("SDNN_ms", "SDNN (ms)", "时域"),
        ("RMSSD_ms", "RMSSD (ms)", "时域"),
        ("LF_ms2", "LF (ms²)", "频域"),
        ("HF_ms2", "HF (ms²)", "频域"),
        ("LF_HF", "LF/HF", "频域"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    xs = [r["window"] for r in agg["windows"]]
    for ax, (m, ylabel, kind) in zip(axes.flat, panels):
        # 个体线
        per_seg = {}
        for r in rows:
            if m in ("LF_ms2", "HF_ms2", "LF_HF"):
                v = r["hrv"].get("frequency", {}).get(m)
            elif m in ("SDNN_ms", "RMSSD_ms"):
                v = r["hrv"].get(m)
            else:
                v = r.get(m)
            if v is not None and isinstance(v, (int, float)):
                per_seg.setdefault(r["segment"], {})[r["window"]] = float(v)
        for seg, d in per_seg.items():
            if len(d) >= 2:
                w = sorted(d)
                ax.plot(w, [d[k] for k in w], "o-", alpha=0.25, markersize=3, linewidth=0.8)
        # 聚合均值 ± SE
        pts = agg["metrics"].get(m, [])
        if pts:
            ax.errorbar([p["window"] for p in pts], [p["mean"] for p in pts],
                        yerr=[p["se"] for p in pts], fmt="D-", color="red",
                        capsize=4, markersize=6, linewidth=1.5)
        ax.set_xticks(xs)
        ax.set_xlabel("休息时间窗 (60s/窗)")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{m} [{kind}]")
        ax.grid(True, alpha=0.3)
    fig.suptitle(f"sub-{SUBJECT} 休息段 HRV 轨迹（可信窗个体线 + 红点均值±SE）", fontsize=14)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  [png] {png_path}")


if __name__ == '__main__':
    main()
