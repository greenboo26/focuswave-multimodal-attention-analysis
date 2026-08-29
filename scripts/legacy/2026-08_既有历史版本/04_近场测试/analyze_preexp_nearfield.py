"""
analyze_preexp_nearfield.py — 预实验全部场次人体距离与近场杂波强度统计
=====================================================================
版本: v1.0 (2026-08-12)
功能: 对预实验全部场次（000-007 等）逐 30s 窗口统计:
        1. 人体主峰距离 bin (bin 8-45, 0.3-1.69 m)
        2. 严格近场峰强度 (bin 2-6, 0.075-0.225 m)
        3. 近场峰/人体峰强度比
      用于检验"人体距离过近导致人体旁瓣侵入近场带"假设,
      以及固定摆位（人距 35-40 cm）下近场杂波的普遍强度。

输入: --data-root 下的 sub-XXX/mmwave/sub-XXX_mmwave_datacube*.npz
      流式处理, 不一次性加载长 session 全量数据。

用法:
  cd 08_算法/scripts
  python analyze_preexp_nearfield.py --data-root F:/预实验 --out 0812preexp_range
  python analyze_preexp_nearfield.py --data-root F:/0812test --out 0812test_range

输出:
  output/<out>/preexp_range_summary.csv  ← 每被试每窗口一行
  output/<out>/preexp_range_stats.md     ← 汇总统计
  output/<out>/range_scatter.png         ← 近场/人体比 vs 人体距离散点

依赖: numpy, scipy, matplotlib
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

BIN_RES_M = 0.0375        # 距离分辨率 (m/bin), 3.75 cm
NEAR_BINS = slice(2, 7)   # 严格近场 bin 2-6 (0.075-0.225 m)
BODY_BINS = slice(2, 46)  # 人体定位 bin 2-45 (0.075-1.69 m), 取全局峰值:
                          # 人体主瓣可能落在近场带内（坐得太近时）, 仅从
                          # bin 8 起定位会把主瓣误判为近场杂波
WINDOW_SEC = 30.0         # 统计窗口长 (s), 与质量评估一致
MIN_SIZE_BYTE = 100_000   # 有效 npz 分片最小体积
MAX_PARTS = 1_000_000     # 上限保护: 防止意外扫描过多分片

# 输出目录（相对 08_算法/output/）
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"


# ============================================================
# 数据加载（流式）
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
        if i > MAX_PARTS:
            break


def frames_to_power(chunk: np.ndarray) -> np.ndarray:
    """单片 (n, 256, 8) 复数 → 逐帧跨通道功率平均幅度 (n, 256)。

    参数:
        chunk: 单片复数距离域数据
    返回:
        amp: (n, 256) float32 逐帧幅度轮廓
    """
    return np.sqrt(np.mean(np.abs(chunk) ** 2, axis=2)).astype(np.float32)


# ============================================================
# 窗口统计
# ============================================================

def win_stats(amp: np.ndarray, fps: float, t0_sec: float) -> dict:
    """单窗口统计: 近场峰、人体峰及其距离、比值。

    参数:
        amp: (n, 256) 逐帧幅度轮廓
        fps: 帧率 (Hz)
        t0_sec: 窗口起始时间 (s)
    返回:
        dict: 窗口级指标
    """
    profile = np.mean(amp, axis=0)            # 窗口平均轮廓
    nf_peak = float(np.max(profile[NEAR_BINS]))
    body_peak = float(np.max(profile[BODY_BINS]))
    body_bin = int(BODY_BINS.start + np.argmax(profile[BODY_BINS]))
    return {
        "t0_sec": round(t0_sec, 1),
        "nf_peak": nf_peak,
        "body_peak": body_peak,
        "nf_body_ratio": nf_peak / (body_peak + 1e-12),
        "body_bin": body_bin,
        "body_m": round(body_bin * BIN_RES_M, 2),
    }


def analyze_subject(mmwave_dir: Path, subject: str, fps: float,
                    win_sec: float = WINDOW_SEC) -> list[dict]:
    """流式分析单个场次, 输出全部窗口统计。

    参数:
        mmwave_dir: mmwave 分片目录
        subject: 被试编号
        fps: 帧率 (Hz)
        win_sec: 窗口长 (s)
    返回:
        list[dict]: 每窗口一条统计
    """
    win_len = max(int(win_sec * fps), 1)
    rows, buf, t0 = [], [], 0.0
    for _, fpath in iter_part_files(mmwave_dir, subject):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        d.close()
        buf.append(frames_to_power(chunk))
        # 攒够一个窗口即统计并清空
        while sum(b.shape[0] for b in buf) >= win_len:
            n_take = win_len
            frames, new_buf = [], []
            for b in buf:
                if n_take == 0:
                    new_buf.append(b)
                elif len(b) <= n_take:
                    frames.append(b)
                    n_take -= len(b)
                else:
                    frames.append(b[:n_take])
                    new_buf.append(b[n_take:])
                    n_take = 0
            amp = np.concatenate(frames, axis=0)
            rows.append(win_stats(amp, fps, t0))
            t0 += win_sec
            buf = new_buf
        del chunk
    # 尾部不足一个窗口的帧: 至少 1s 才纳入
    if buf and sum(b.shape[0] for b in buf) >= fps:
        amp = np.concatenate(buf, axis=0)
        rows.append(win_stats(amp, fps, t0))
    return rows


# ============================================================
# 主流程
# ============================================================

def main():
    """遍历全部场次 → 窗口统计 → 汇总表 + 散点图。"""
    parser = argparse.ArgumentParser(description="预实验人体距离与近场强度统计")
    parser.add_argument("--data-root", required=True, help="数据根目录 (F:/预实验)")
    parser.add_argument("--out", default="preexp_range", help="输出目录 (相对 08_算法/output/)")
    parser.add_argument("--fps", type=float, default=98.5, help="帧率 (Hz), 默认 98.5")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    output_dir = OUTPUT_ROOT / args.out
    output_dir.mkdir(parents=True, exist_ok=True)

    sub_dirs = sorted([d for d in data_root.iterdir()
                       if d.is_dir() and d.name.startswith("sub-")])
    all_rows = []
    for sd in sub_dirs:
        subject = sd.name.removeprefix("sub-").split("_")[0]
        mmwave_dir = sd / "mmwave"
        if not (mmwave_dir / f"sub-{subject}_mmwave_datacube.npz").exists():
            continue
        rows = analyze_subject(mmwave_dir, subject, args.fps)
        print(f"sub-{subject}: {len(rows)} 窗")
        for r in rows:
            all_rows.append({"subject": subject, **r})

    # ── 汇总统计 ──
    import csv
    with open(output_dir / "preexp_range_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "t0_sec", "nf_peak", "body_peak",
                    "nf_body_ratio", "body_bin", "body_m"])
        for r in all_rows:
            w.writerow([r["subject"], r["t0_sec"], r["nf_peak"], r["body_peak"],
                        r["nf_body_ratio"], r["body_bin"], r["body_m"]])

    lines = ["# 预实验人体距离与近场强度汇总\n"]
    lines.append("| 场次 | 窗数 | 人体距离中位 (m) | 人体距离 IQR (m) | 近场峰中位 | 近场/人体中位 |")
    lines.append("|------|------|-----------------|-----------------|-----------|-------------|")
    stats = {}
    for sub in sorted({r["subject"] for r in all_rows}):
        rows = [r for r in all_rows if r["subject"] == sub]
        dm = np.median([r["body_m"] for r in rows])
        dq = np.percentile([r["body_m"] for r in rows], [25, 75])
        nf = np.median([r["nf_peak"] for r in rows])
        ratio = np.median([r["nf_body_ratio"] for r in rows])
        stats[sub] = {"dm": dm, "d_lo": dq[0], "d_hi": dq[1], "nf": nf, "ratio": ratio}
        lines.append(f"| {sub} | {len(rows)} | {dm:.2f} | {dq[0]:.2f}-{dq[1]:.2f} "
                     f"| {nf:.3f} | {ratio:.2f} |")
    (output_dir / "preexp_range_stats.md").write_text("\n".join(lines), encoding="utf-8")

    # ── 散点图: 近场/人体比 vs 人体距离 ──
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = plt.cm.tab20(np.linspace(0, 1, len(stats)))
    for (sub, c) in zip(stats, colors):
        rows = [r for r in all_rows if r["subject"] == sub]
        ax.scatter([r["body_m"] for r in rows], [r["nf_body_ratio"] for r in rows],
                   s=12, alpha=0.6, color=c, label=f"sub-{sub}")
    ax.axhline(1.0, color="gray", ls="--", lw=0.8, label="近场=人体")
    ax.set_xlabel("人体距离 (m)")
    ax.set_ylabel("近场峰/人体峰比")
    ax.set_title("预实验各场次: 近场杂波强度 vs 人体距离 (30s 窗)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "range_scatter.png", dpi=120)
    plt.close(fig)

    print()
    for line in lines:
        print(line)
    print(f"\n输出目录: {output_dir}")


if __name__ == "__main__":
    main()


