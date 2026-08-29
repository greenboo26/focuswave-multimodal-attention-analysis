"""
compare_range_profiles.py — 对比多批次毫米波数据的距离-信号强度轮廓
=====================================================================
用途: 排查"预实验信号弱/雷达坏了"假设。对每批 npz 分片数据计算
      距离轮廓(各 bin 平均幅度, 8 天线平均), 叠加绘图 + 输出
      关键距离幅度表, 对比预实验与全部历史数据集。

用法:
    python compare_range_profiles.py
    批次列表在下方 BATCHES 中编辑。

输出:
    <OUT_DIR>/compare_range_profile.png  + 终端打印幅度表

依赖: numpy, matplotlib
"""

import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BIN_TO_CM = 3.75          # 距离分辨率(cm/bin), 与 04b 一致
SAMPLE_PER_PART = 30      # 每个 npz 分片取前 N 帧(长实验均匀覆盖全程)
MAX_PARTS = 500           # 最多扫描分片数
OUT_DIR = Path(r"D:/Project/厚粲杯/08_算法/output")

BATCHES = [
    # (显示名, mmwave 目录)
    ("预实验 sub-001 (43min)", r"F:/预实验/sub-001_/mmwave"),
    ("预实验 sub-002 (43min)", r"F:/预实验/sub-002_/mmwave"),
    ("旧SART sub-001 (46min, 有电脑遮挡)", r"F:/sub-001_/mmwave"),
    ("旧SART sub-007 (48min, 无遮挡)", r"F:/sub-007_/mmwave"),
    ("旧SART sub-008 (74min, 无遮挡)", r"F:/sub-008_/mmwave"),
    ("旧SART sub-sxq (47min, 无电脑遮挡)", r"F:/sub-sxq_/mmwave"),
    ("REST-3min (无遮挡)", r"D:/Project/厚粲杯/11_数据/sub-rest_3min_/mmwave"),
    ("DEEP-BREATH (无遮挡)", r"D:/Project/厚粲杯/11_数据/sub-deep-breath/ses-DB/mmwave"),
    ("04b验证 0.8m (能分析)", r"D:/Project/厚粲杯/05_实验/FocusWave/03-data/sub-verify_/mmwave"),
]


def load_profile(mm_dir: Path, max_frames: int = 5000):
    """加载 mm_dir 的分片, 每分片取前 SAMPLE_PER_PART 帧, 计算距离轮廓。

    Returns:
        np.ndarray: 每 bin 的平均幅度 (256,), 失败返回 None
    """
    parts = sorted(mm_dir.glob("*part*.npz"))
    main_npz = [p for p in mm_dir.glob("*datacube.npz") if "part" not in p.name]
    files = list(parts)[:MAX_PARTS]
    if main_npz:
        files.insert(0, main_npz[0])
    if not files:
        return None

    chunks = []
    got = 0
    for p in files:
        d = np.load(p)
        keys = sorted([k for k in d.files if k.startswith("tx")])
        if not keys:
            d.close()
            continue
        chunk = np.stack([d[k] for k in keys], axis=-1).astype(np.complex64)
        d.close()
        take = min(SAMPLE_PER_PART, chunk.shape[0], max_frames - got)
        chunks.append(chunk[:take])
        got += take
        if got >= max_frames:
            break
    if not chunks:
        return None
    iq = np.concatenate(chunks)
    return np.abs(iq).mean(axis=(0, 2))   # 平均幅度 per bin, 8 天线平均


def main():
    results = {}
    print("=" * 64)
    print("各批次距离-信号强度(平均|IQ|) 计算")
    print("=" * 64)
    for name, path in BATCHES:
        mm_dir = Path(path)
        if not mm_dir.is_dir():
            print(f"[跳过] {name}: 目录不存在")
            continue
        try:
            prof = load_profile(mm_dir)
        except Exception as e:
            print(f"[错误] {name}: {e}")
            continue
        if prof is None:
            print(f"[无数据] {name}")
            continue
        results[name] = prof
        peak_bin = int(np.argmax(prof))
        print(f"[OK]   {name}")
        print(f"       峰值 bin={peak_bin} ({peak_bin * BIN_TO_CM / 100:.2f}m) "
              f"幅度={prof[peak_bin]:.4f}")

    if not results:
        print("无任何批次可分析")
        return

    # ── 幅度表: 关键距离位置 ──
    key_m = [0.2, 0.5, 0.8, 1.0, 1.5, 2.0]
    key_bin = [round(m / (BIN_TO_CM / 100)) for m in key_m]
    print()
    print("=" * 64)
    print("关键距离幅度表 (平均|IQ|)")
    print("=" * 64)
    header = f"{'批次':<28}" + "".join(f"{m:>8.1f}m" for m in key_m)
    print(header)
    for name, prof in results.items():
        cells = "".join(f"{prof[b]:>10.4f}" for b in key_bin)
        print(f"{name:<28}{cells}")

    # ── 叠加图(对数坐标: 近场泄漏与人体信号跨 3 个数量级) ──
    fig, ax = plt.subplots(figsize=(12, 7))
    for name, prof in results.items():
        x_m = np.arange(256) * BIN_TO_CM / 100
        ax.plot(x_m, prof, lw=1.3, label=name)
    ax.set_yscale("log")
    ax.axvline(0.8, color="gray", ls="--", lw=0.8)
    ax.text(0.82, ax.get_ylim()[0] * 3, "0.8m 预期人体位置",
            color="gray", fontsize=8, rotation=90, va="bottom")
    ax.set_xlim(0, 2.5)
    ax.set_ylim(1e-4, 1.0)
    ax.set_xlabel("距离 (m)")
    ax.set_ylabel("平均幅度 |IQ| (对数)")
    ax.set_title("各批次毫米波距离-信号强度对比（全程均匀采样, 对数坐标）")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3, which="both")

    out_png = OUT_DIR / "compare_range_profile.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print()
    print(f"对比图已保存: {out_png}")


if __name__ == "__main__":
    main()


