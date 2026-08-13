"""
analyze_nearfield_test.py — 近场杂波来源测试分析（0812test 简化版）
====================================================================
版本: v1.0 (2026-08-12)
功能: 分析 0812test 两段对比（正常按键 vs 手不动）的近场峰行为，
      按《近场杂波来源测试方案》指标输出：
        1. 近场峰强度: 平均距离-幅度轮廓近场带（bin 2-8, 0.075-0.3m）峰值
        2. 相位调制指数: 10s 滑窗内相位变化 >1 rad 的窗占比（0-100%）
        3. 人体带对照: bin 8-16（0.3-0.6m）峰值
      用于判定近场动态调制来源是手部动作（H3）还是设备固有（H1）。

输入（每场景一个子目录）:
  sub-XXXX/beh/master_timeline.csv   ← 起止时间戳（裁剪参考）
  sub-XXXX/mmwave/sub-XXXX_mmwave_datacube*.npz  ← 分片复数距离域数据

用法:
  cd 08_算法/scripts
  python analyze_nearfield_test.py --data-root F:/0812test \
      --out output/0812test

输出:
  output/0812test/nearfield_metrics.csv   ← 每场景指标表
  output/0812test/range_time_nearfield.png ← 近场区距离-时间图（裁剪后）
  output/0812test/nearfield_profiles.png   ← 7 场景近场轮廓叠图（裁剪后）

依赖: numpy, scipy, matplotlib
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# matplotlib 中文字体（Windows 环境）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

BIN_RES_M = 0.0375        # 距离分辨率 (m/bin), 与方案一致 (3.75 cm)
NEAR_BINS = slice(2, 9)   # 近场带 bin 2-8 (0.075-0.3 m), 含 8 因与人体带衔接
NEAR_STRICT = slice(2, 7) # 严格近场 bin 2-6 (0.075-0.225 m), 排除人体主峰翼
NEAR_EDGE = slice(7, 9)   # 近场-人体交界 bin 7-8 (0.2625-0.3 m), 可能含人体翼
BODY_BINS = slice(8, 17)  # 人体带 bin 8-16 (0.3-0.6 m), 含 8 重叠便于对照
SLIDING_SEC = 10.0        # 相位调制滑窗长 (s), 与方案一致
SLIDING_STEP_SEC = 5.0    # 滑窗步进 (s), 50% 重叠
PHASE_MOD_RAD = 1.0       # 动态判定阈值: 窗内相位变化 >1 rad
CROP_START_SEC = 10.0     # 默认裁剪开头 (s), 去掉姿势调整/cover 段
CROP_END_SEC = 10.0       # 默认裁剪结尾 (s), 去掉退出前动作段
MIN_SIZE_BYTE = 100_000   # 有效 npz 分片最小体积 (尾片不足视为无效)

# 输出目录（相对 08_算法/output/）
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"


# ============================================================
# 数据加载
# ============================================================

def iter_part_files(mmwave_dir: Path, subject: str):
    """遍历 mmwave 目录下所有有效 npz 分片。

    参数:
        mmwave_dir: mmwave 分片所在目录
        subject: 被试编号
    生成:
        (片索引, npz 文件路径)
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


def load_all_frames(mmwave_dir: Path, subject: str, fps: float):
    """流式读入全部帧并拼接为 (n, n_bins, n_ch) 复数距离域数据。

    保留全部 8 通道复数（2TX×4RX）: 幅度谱用功率非相干合成,
    相位分析需在单通道上做（跨通道平均会抹平相位）。

    参数:
        mmwave_dir: mmwave 分片所在目录
        subject: 被试编号
        fps: 帧率 (Hz), 用于裁剪
    返回:
        (iq, t_sec): iq (n, 256, 8) complex64 距离域复数数据,
                     t_sec (n,) float 帧时间轴（秒）
    """
    parts = []
    for _, fpath in iter_part_files(mmwave_dir, subject):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        d.close()
        parts.append(chunk)
        del chunk
    iq = np.concatenate(parts, axis=0)
    t_sec = np.arange(iq.shape[0]) / fps
    return iq, t_sec


def power_profile(iq: np.ndarray) -> np.ndarray:
    """跨通道功率平均的距离-幅度轮廓（幅度量纲）。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域数据
    返回:
        profile: (n_bins,) float 平均幅度轮廓
    """
    return np.sqrt(np.mean(np.abs(iq) ** 2, axis=(0, 2)))


# ============================================================
# 指标计算
# ============================================================

def nearfield_peak(iq: np.ndarray, bins: slice) -> float:
    """平均距离-幅度轮廓的近场带峰值（相对值）。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域数据
        bins: 分析带 (bin 切片)
    返回:
        peak: 时间平均幅度轮廓在带内的峰值
    """
    profile = power_profile(iq)
    return float(np.max(profile[bins]))


def body_peak(iq: np.ndarray, bins: slice) -> float:
    """人体带峰值（与近场峰同量纲, 作相对对照）。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域数据
        bins: 人体带 (bin 切片)
    返回:
        peak: 时间平均幅度轮廓在带内的峰值
    """
    return nearfield_peak(iq, bins)


def phase_mod_index(iq: np.ndarray, t_sec: np.ndarray, fps: float,
                    bin_idx: int) -> float:
    """单 bin 相位调制指数: 10s 滑窗内相位变化 >1 rad 的窗占比。

    实现: 在指定 bin 上选功率最强通道提取相位（单通道相位才保有
    生理/动作调制信息, 跨通道平均会抹平）; unwrap 后滑窗统计
    max(phi)-min(phi) 超过阈值的比例。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域数据
        t_sec: 帧时间轴 (s)
        fps: 帧率 (Hz)
        bin_idx: 待测 bin 索引
    返回:
        ratio: 动态窗占比 (0-100%)
    """
    ch_power = np.mean(np.abs(iq[:, bin_idx, :]) ** 2, axis=0)
    best_ch = int(np.argmax(ch_power))
    phi = np.unwrap(np.angle(iq[:, bin_idx, best_ch]))
    win_len = max(int(SLIDING_SEC * fps), 1)
    step = max(int(SLIDING_STEP_SEC * fps), 1)
    n_win = (len(phi) - win_len) // step + 1
    if n_win < 1:
        return float("nan")
    n_dyn = 0
    for i in range(n_win):
        seg = phi[i * step: i * step + win_len]
        if np.ptp(seg) > PHASE_MOD_RAD:
            n_dyn += 1
    return 100.0 * n_dyn / n_win


def phase_mod_per_bin(iq: np.ndarray, t_sec: np.ndarray, fps: float,
                      bins: slice) -> dict[int, float]:
    """近场带逐 bin 相位调制指数（区分真实近场杂波与人体翼）。

    近场带中靠近人体边缘的 bin（如 bin 7-8）可能只是人体主峰的
    翼, 其动态来自人体生理/动作调制而非近场杂波本身; 逐 bin 输出
    可定位动态调制究竟发生在哪个距离单元。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域数据
        t_sec: 帧时间轴 (s)
        fps: 帧率 (Hz)
        bins: 分析带 (bin 切片)
    返回:
        dict: {bin 索引: 相位调制指数 %}, 键按 bin 升序
    """
    return {b: phase_mod_index(iq, t_sec, fps, b)
            for b in range(bins.start, bins.stop)}


def nearfield_peak_bin(iq: np.ndarray) -> int:
    """返回近场带内时间平均功率峰值 bin 索引（供相位分析定位）。

    参数:
        iq: (n, n_bins, n_ch) 复数距离域数据
    返回:
        bin 索引
    """
    profile = power_profile(iq)
    return int(NEAR_BINS.start + np.argmax(profile[NEAR_BINS]))


# ============================================================
# 裁剪与场景汇总
# ============================================================

def crop(iq: np.ndarray, t_sec: np.ndarray, fps: float,
         start_sec: float, end_sec: float):
    """按秒数裁剪首尾帧（去掉姿势调整/cover/退出段）。

    参数:
        iq: (n, n_bins) 复数距离域数据
        t_sec: 帧时间轴 (s)
        fps: 帧率 (Hz)
        start_sec: 开头裁剪秒数
        end_sec: 结尾裁剪秒数
    返回:
        (iq_c, t_c, crop_info): 裁剪后数据、时间轴、裁剪说明
    """
    i0 = int(start_sec * fps)
    i1 = len(t_sec) - int(end_sec * fps)
    if i1 <= i0:
        raise ValueError("裁剪后无剩余帧, 请减小裁剪秒数")
    info = (f"裁剪首 {start_sec:.0f}s + 尾 {end_sec:.0f}s, "
            f"保留 {i1 - i0} 帧 ({t_sec[i1 - 1] - t_sec[i0]:.1f}s)")
    return iq[i0:i1], t_sec[i0:i1] - t_sec[i0], info


def analyze_subject(data_root: Path, sub_dir: Path, fps: float,
                    crop_start: float, crop_end: float) -> dict:
    """分析单个场景, 返回指标字典与图数据。

    参数:
        data_root: 数据根目录
        sub_dir: 场景子目录
        fps: 帧率 (Hz)
        crop_start: 开头裁剪秒数
        crop_end: 结尾裁剪秒数
    返回:
        dict: 场景指标 + 图数据（profile 与 range-time 小图）
    """
    subject = sub_dir.name.split("_")[0].removeprefix("sub-")   # sub-08121_正常按键 → 08121
    label = sub_dir.name.replace(f"sub-{subject}", "").lstrip("_")
    mmwave_dir = sub_dir / "mmwave"

    iq_full, t_full = load_all_frames(mmwave_dir, subject, fps)
    iq, t_sec, crop_info = crop(iq_full, t_full, fps, crop_start, crop_end)

    profile = power_profile(iq)                    # 平均距离-幅度轮廓
    nf_peak = nearfield_peak(iq, NEAR_BINS)
    nf_peak_strict = nearfield_peak(iq, NEAR_STRICT)
    nf_peak_edge = nearfield_peak(iq, NEAR_EDGE)
    body_peak_val = body_peak(iq, BODY_BINS)
    nf_bin = nearfield_peak_bin(iq)
    # 逐 bin 相位调制（区分真实近场杂波 bin 2-6 与人体翼 bin 7-8）
    pm_all = phase_mod_per_bin(iq, t_sec, fps, NEAR_BINS)
    pm_strict = max(v for b, v in pm_all.items()
                    if NEAR_STRICT.start <= b < NEAR_STRICT.stop)
    pm_edge = max(v for b, v in pm_all.items()
                  if NEAR_EDGE.start <= b < NEAR_EDGE.stop)

    # range-time 小图（近场区 bin 0-16 zoom, 跨通道功率合成）
    fig, ax = plt.subplots(figsize=(10, 4))
    rt = np.sqrt(np.mean(np.abs(iq[:, :17, :]) ** 2, axis=2)).T
    im = ax.imshow(rt, aspect="auto", origin="lower",
                   extent=[0, t_sec[-1], 0, 17 * BIN_RES_M],
                   cmap="viridis")
    ax.axhline(0.3, color="w", ls="--", lw=0.8, label="0.3 m (近场/人体带界)")
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("距离 (m)")
    ax.set_title(f"{label} (sub-{subject}) 近场区距离-时间 | {crop_info}")
    plt.colorbar(im, ax=ax, label="幅度")
    ax.legend()
    fig.tight_layout()
    fig.savefig(rt_fig := str(output_dir / f"sub-{subject}_range_time.png"), dpi=120)
    plt.close(fig)

    return {
        "subject": subject,
        "label": label,
        "n_frames": len(iq),
        "duration_sec": round(t_sec[-1], 1),
        "nf_peak": nf_peak,
        "nf_peak_strict": nf_peak_strict,
        "nf_peak_edge": nf_peak_edge,
        "body_peak": body_peak_val,
        "nf_body_ratio": nf_peak / (body_peak_val + 1e-12),
        "nf_peak_bin": nf_bin,
        "nf_peak_m": round(nf_bin * BIN_RES_M, 2),
        "pm_strict": round(pm_strict, 1),
        "pm_edge": round(pm_edge, 1),
        "pm_all": pm_all,
        "crop_note": crop_info,
        "profile": profile,
        "rt_fig": rt_fig,
    }


def main():
    """主流程: 遍历场景 → 指标 → 汇总表 + 叠图。"""
    parser = argparse.ArgumentParser(description="近场杂波来源测试分析 (0812test)")
    parser.add_argument("--data-root", required=True, help="数据根目录 (F:/0812test)")
    parser.add_argument("--out", default="output/0812test", help="输出目录 (相对 08_算法/)")
    parser.add_argument("--fps", type=float, default=98.0, help="帧率 (Hz), 默认 98")
    parser.add_argument("--crop-start", type=float, default=CROP_START_SEC,
                        help=f"开头裁剪秒数 (默认 {CROP_START_SEC})")
    parser.add_argument("--crop-end", type=float, default=CROP_END_SEC,
                        help=f"结尾裁剪秒数 (默认 {CROP_END_SEC})")
    args = parser.parse_args()

    global output_dir
    data_root = Path(args.data_root)
    output_dir = OUTPUT_ROOT / args.out
    output_dir.mkdir(parents=True, exist_ok=True)

    sub_dirs = sorted([d for d in data_root.iterdir() if d.is_dir()])
    results, profiles = [], {}
    for sd in sub_dirs:
        res = analyze_subject(data_root, sd, args.fps, args.crop_start, args.crop_end)
        results.append(res)
        profiles[res["label"]] = res["profile"]

    # ── 指标汇总表 ──
    print(f"\n{'场景':<12}{'时长s':>7}{'近场峰':>9}{'近场严格':>9}{'交界bin7-8':>9}"
          f"{'人体峰':>9}{'相位调制%':>9}{'交界调制%':>9}")
    print("   (近场峰 = 带内峰值; 近场严格 = bin 2-6; 交界 = bin 7-8 人体翼区)")
    print("-" * 88)
    for r in results:
        print(f"{r['label']:<12}{r['duration_sec']:>7.1f}{r['nf_peak']:>9.2f}"
              f"{r['nf_peak_strict']:>9.2f}{r['nf_peak_edge']:>9.2f}"
              f"{r['body_peak']:>9.2f}{r['pm_strict']:>9.1f}{r['pm_edge']:>9.1f}")
        print(f"    {r['crop_note']}")
        pm_desc = ", ".join(f"bin{b}:{v:.0f}%" for b, v in r["pm_all"].items())
        print(f"    逐bin调制: {pm_desc}")

    # ── 近场轮廓叠图（bin 0-20 zoom） ──
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, profile in profiles.items():
        ax.plot(np.arange(21) * BIN_RES_M, profile[:21], marker=".", label=label)
    ax.axvspan(NEAR_BINS.start * BIN_RES_M, (NEAR_BINS.stop - 1) * BIN_RES_M,
               color="orange", alpha=0.12, label="近场带 0.075-0.3 m")
    ax.axvspan(BODY_BINS.start * BIN_RES_M, (BODY_BINS.stop - 1) * BIN_RES_M,
               color="blue", alpha=0.08, label="人体带 0.3-0.6 m")
    ax.set_xlabel("距离 (m)")
    ax.set_ylabel("平均幅度")
    ax.set_title("近场杂波来源测试: 距离-幅度轮廓对比 (0-0.8 m)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "nearfield_profiles.png", dpi=120)
    plt.close(fig)

    # ── 指标表存 csv ──
    import csv
    with open(output_dir / "nearfield_metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "label", "duration_sec", "nf_peak", "nf_peak_strict",
                    "nf_peak_edge", "body_peak", "nf_body_ratio",
                    "nf_peak_bin", "nf_peak_m", "pm_strict", "pm_edge", "crop_note"])
        for r in results:
            w.writerow([r["subject"], r["label"], r["duration_sec"], r["nf_peak"],
                        r["nf_peak_strict"], r["nf_peak_edge"], r["body_peak"],
                        r["nf_body_ratio"], r["nf_peak_bin"], r["nf_peak_m"],
                        r["pm_strict"], r["pm_edge"], r["crop_note"]])
    # 逐 bin 相位调制细节表
    with open(output_dir / "nearfield_pm_perbin.csv", "w", newline="") as f:
        w = csv.writer(f)
        bins = list(range(NEAR_BINS.start, NEAR_BINS.stop))
        w.writerow(["subject", "label"] + [f"bin{b}_{b*BIN_RES_M:.2f}m" for b in bins])
        for r in results:
            w.writerow([r["subject"], r["label"]]
                       + [r["pm_all"][b] for b in bins])

    print(f"\n输出目录: {output_dir}")
    print("叠图: nearfield_profiles.png | 指标表: nearfield_metrics.csv")


if __name__ == "__main__":
    main()
