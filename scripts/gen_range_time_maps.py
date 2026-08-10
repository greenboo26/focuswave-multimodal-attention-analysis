"""
gen_range_time_maps.py — 全程距离-时间热图生成（多被试对比）
============================================================
版本: v2.0 (2026-08-10)
功能: 对预实验被试（000/001/002/003）流式读取毫米波 npz 分片,
      生成全程距离-时间热图（时间 × 距离 的幅度图）, 直观呈现
      全程人体目标位置、信号强弱、休息段/运动伪影。

样式（对齐旧版 range_time_map_全程对比.png）:
  - 每列 = 10s（时间聚合粒度, 与旧图一致）
  - Y 轴距离 (m), 范围 0-1.75 m（bin 0-46, 3.75cm/bin）
  - 无 colorbar, 用颜色梯度直接传递幅度
  - 标题格式: "预实验 sub-000 (43min) — 全程距离-时间热图(每列=10s, 幅度)"
  - 2×2 对比图 + 每被试单独图, 四被试统一 dB 归一化

方法:
  逐片读取 → 每 10s（1000 帧）取幅度最大值（时间聚合）→ 距离 bin
  保留 0-46（0-1.75m）→ 通道取 max（任一通道可见的反射都显示）→
  dB 刻度, 按四被试统一百分位裁剪动态范围。

用法:
  cd 08_算法/scripts
  python gen_range_time_maps.py --data-root F:/预实验

输出:
  output/09_PREEXP-SUBJECTS-COMPARE/
    range_time_map_全程对比_000-003.png  ← 2×2 对比
    range_time_map_sub-000_全程.png       ← 单被试图 ×4
    range_time_maps_data.json             ← 数据摘要（供复核）

依赖: numpy, matplotlib
"""

from __future__ import annotations

import argparse
import json
import time as time_mod
from pathlib import Path

import numpy as np

# ============================================================
# 配置（硬编码参数集中声明）
# ============================================================

SUBJECTS = ["000", "001", "002", "003"]   # 参与对比的被试
CHUNK = 1000                              # 每 npz 片帧数
FS = 100.0                                # 采样率 (Hz)
AGG_SEC = 10.0                            # 时间聚合粒度 (s)：每 10s 一列（与旧图一致）
BIN_CM = 3.75                             # 距离 bin 分辨率 (cm)，8GHz 带宽 → 3.75cm
Y_MAX_M = 1.75                            # 显示距离上限 (m)，bin 0-46（环境反射远距 bin 排除）
DB_LO_PCT, DB_HI_PCT = 5.0, 99.5          # dB 动态范围裁剪百分位（四被试统一）
COLORMAP = "jet"                          # 配色（旧图同款: 深蓝→浅蓝→黄→红）
FIG_SIZE = (14, 11)                       # 2×2 对比图尺寸
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "output" / "09_PREEXP-SUBJECTS-COMPARE"


# ============================================================
# 数据加载（流式: 逐片读入, 时间聚合降采样）
# ============================================================

def iter_part_files(mm_dir: Path, subject: str):
    """遍历所有有效 npz 分片（主文件 + partNNN, 跳过 <100KB 尾片）。"""
    main_npz = mm_dir / f"sub-{subject}_mmwave_datacube.npz"
    if main_npz.exists() and main_npz.stat().st_size >= 100_000:
        yield main_npz
    i = 1
    while True:
        fpath = mm_dir / f"sub-{subject}_mmwave_datacube_part{i:03d}.npz"
        if not fpath.exists():
            break
        if fpath.stat().st_size >= 100_000:
            yield fpath
        i += 1


def build_range_time_map(mm_dir: Path, subject: str) -> np.ndarray:
    """流式构建距离-时间幅度矩阵。

    每片 1000 帧 = 10s, 恰好一列: 取全场景幅度最大值 (256, 8) →
    通道 max → (1, 256) 行。总列数 = 分片数（≈ 时长/10s）。

    参数:
        mm_dir: mmwave 分片目录
        subject: 被试编号
    返回:
        rt_map: (n_t, 256) float32, 幅度（线性刻度, 后续转 dB）
    """
    rows = []
    for fpath in iter_part_files(mm_dir, subject):
        d = np.load(fpath)
        keys = sorted([k for k in d.keys() if k.startswith('tx')])
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.float32)
        d.close()
        mag = np.abs(chunk)                          # (1000, 256, 8)
        rows.append(mag.max(axis=(0, 2)))            # 时间聚合 + 通道 max → (256,)
    return np.stack(rows)                            # (n_t, 256)


def to_db(rt_map: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """幅度 → dB, 并按统一范围裁剪。"""
    return np.clip(20 * np.log10(rt_map + 1e-9), vmin, vmax)


# ============================================================
# 绘图（样式对齐旧版: 无 colorbar, Y 轴距离 m, 标题带时长）
# ============================================================

def plot_single(ax, rt_map_db: np.ndarray, vmin: float, vmax: float,
                subject: str, duration_min: float):
    """单被试热图绘制（无 colorbar, 与旧图样式一致）。

    参数:
        ax: matplotlib 坐标轴
        rt_map_db: (n_t, 256) dB 矩阵
        vmin/vmax: 统一 dB 裁剪范围
        subject: 被试编号
        duration_min: 数据时长（分钟, 用于标题）
    """
    n_bin = int(Y_MAX_M * 100 / BIN_CM) + 1          # 显示 bin 数（0-1.75m）
    data = rt_map_db[:, :n_bin].T                    # (n_bin, n_t), 转置后每列=10s
    im = ax.imshow(data, aspect="auto", origin="lower", cmap=COLORMAP,
                   vmin=vmin, vmax=vmax,
                   extent=[0, rt_map_db.shape[0] * AGG_SEC / 60,
                           0, Y_MAX_M])
    ax.set_xlabel("时间 (min)")
    ax.set_ylabel("距离 (m)")
    ax.set_title(f"预实验 sub-{subject} ({duration_min:.0f}min) — "
                 f"全程距离-时间热图(每列={AGG_SEC:.0f}s, 幅度)")
    return im


def main():
    parser = argparse.ArgumentParser(description="全程距离-时间热图生成")
    parser.add_argument("--data-root", type=str, default="F:/预实验",
                        help="数据根目录, 含 sub-XXX_/ 子目录")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR),
                        help="输出目录")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t_all = time_mod.time()
    print("=" * 60)
    print("  全程距离-时间热图（000/001/002/003, 样式对齐旧版）")
    print("=" * 60)

    # ── 1. 逐被试构建矩阵 ──
    maps = {}
    for subject in SUBJECTS:
        mm_dir = data_root / f"sub-{subject}_" / "mmwave"
        print(f"[{subject}] 流式构建 ({time_mod.time() - t_all:.0f}s)...")
        maps[subject] = build_range_time_map(mm_dir, subject)
        print(f"  → {maps[subject].shape} ({maps[subject].shape[0] * AGG_SEC / 60:.1f} min)")

    # ── 2. 统一 dB 动态范围（四被试聚合百分位） ──
    all_db = np.concatenate([20 * np.log10(m + 1e-9).ravel() for m in maps.values()])
    vmin, vmax = np.percentile(all_db, [DB_LO_PCT, DB_HI_PCT])
    del all_db
    print(f"统一 dB 范围: [{vmin:.1f}, {vmax:.1f}]")

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    # ── 3. 单被试图（无 colorbar） ──
    for subject, m in maps.items():
        db = to_db(m, vmin, vmax)
        duration_min = m.shape[0] * AGG_SEC / 60
        fig, ax = plt.subplots(figsize=(12, 5))
        plot_single(ax, db, vmin, vmax, subject, duration_min)
        png = out_dir / f"range_time_map_sub-{subject}_全程.png"
        fig.tight_layout()
        fig.savefig(png, dpi=150)
        plt.close(fig)
        print(f"  [png] {png}")

    # ── 4. 2×2 对比图（无 colorbar） ──
    fig, axes = plt.subplots(2, 2, figsize=FIG_SIZE)
    for ax, subject in zip(axes.flat, SUBJECTS):
        db = to_db(maps[subject], vmin, vmax)
        duration_min = maps[subject].shape[0] * AGG_SEC / 60
        plot_single(ax, db, vmin, vmax, subject, duration_min)
    fig.suptitle("预实验全程距离-时间热图对比（统一 dB 范围）", fontsize=15)
    png = out_dir / "range_time_map_全程对比_000-003.png"
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(png, dpi=150)
    plt.close(fig)
    print(f"  [png] {png}")

    # ── 5. 摘要 JSON ──
    json_path = out_dir / "range_time_maps_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "subjects": {s: {"n_t": int(m.shape[0]),
                             "duration_min": round(m.shape[0] * AGG_SEC / 60, 1)}
                         for s, m in maps.items()},
            "agg_sec": AGG_SEC, "bin_cm": BIN_CM, "y_max_m": Y_MAX_M,
            "db_range": [round(float(vmin), 1), round(float(vmax), 1)],
        }, f, ensure_ascii=False, indent=2)
    print(f"  [json] {json_path}")
    print(f"  总耗时 {time_mod.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()
