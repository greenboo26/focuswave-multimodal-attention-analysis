"""
truncate_preexp_data.py — 预实验毫米波数据截断工具
====================================================================
版本: v2.0 (2026-08-10)
功能: 按行为实验结束（Block6 停止）或自定义时刻截断某被试 mmwave 数据,
      用于"被试离开但忘记停止采集"场景的尾部数据清理。
      截断同步处理: npz 分片（保留 + 边界片裁剪 + 移出备份）、
      timestamps.csv、datacube.bin、meta.json。

方法:
  1. 截断点 = master_timeline 中最后一个 block_stop 时刻（--mode block6）
     或距首帧毫秒数（--mode ms --cut-ms N）
  2. 时间戳精确到帧（searchsorted）; 默认精确到帧并裁剪边界片,
     --align-part 可改为整片对齐（丢弃边界片余量, 不重写 npz）
  3. 被移除的分片与 timestamps/meta 快照移入 mmwave_truncated_backup/（不直接删除）

用法:
  python truncate_preexp_data.py --subject 004 --data-root F:/预实验
  python truncate_preexp_data.py --subject 005 --mode ms --cut-ms 3560000

依赖: numpy
"""

import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np

BIN_HEADER = 32   # bin 文件头部字节数（PSIC 魔数 + 元数据, 由 bin 实际大小与帧数校验）


def detect_bin_frame_bytes(bin_path: Path, frame_count: int) -> int:
    """自动探测 bin 每帧字节数（从 bin 总大小与 meta 帧数反推）。

    参数:
        bin_path: datacube.bin 路径
        frame_count: meta.json 中的帧数
    返回:
        每帧字节数（扣除 32 字节头部）
    """
    size = bin_path.stat().st_size
    return int((size - BIN_HEADER) // frame_count)


def load_py_ms(mm_dir: Path, subject: str) -> np.ndarray:
    """读取 timestamps.csv 的 Python 时间戳列。"""
    ts_path = mm_dir / f"sub-{subject}_mmwave_timestamps.csv"
    return np.loadtxt(ts_path, delimiter=",", usecols=(2,), dtype=np.int64)


def block6_stop_ms(beh_dir: Path) -> int:
    """读取 master_timeline.csv 最后一个 block_stop 时刻（行为实验结束）。

    参数:
        beh_dir: beh 目录
    返回:
        block_stop 的 unix_ms 时间戳
    """
    tl = beh_dir / "master_timeline.csv"
    last_stop = None
    with open(tl, encoding="utf-8", newline="") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 3 and parts[0] == "block_stop":
                last_stop = int(parts[2])
    if last_stop is None:
        raise ValueError("master_timeline 中未找到 block_stop 事件")
    return last_stop


def main():
    parser = argparse.ArgumentParser(description="预实验毫米波数据截断工具")
    parser.add_argument("--subject", type=str, default="004", help="被试编号（3 位）")
    parser.add_argument("--data-root", type=str, default="F:/预实验",
                        help="数据根目录, 含 sub-XXX_/ 子目录")
    parser.add_argument("--mode", choices=["block6", "ms"], default="block6",
                        help="截断模式: block6=按行为实验结束(默认), ms=自定义毫秒")
    parser.add_argument("--cut-ms", type=int, default=None,
                        help="mode=ms 时距首帧的截断毫秒数")
    parser.add_argument("--align-part", action="store_true",
                        help="整片对齐（不重写边界片, 丢弃边界余量, 默认精确裁剪）")
    args = parser.parse_args()

    subject = args.subject.zfill(3)
    data_root = Path(args.data_root)
    mm_dir = data_root / f"sub-{subject}_" / "mmwave"
    beh_dir = data_root / f"sub-{subject}_" / "beh"
    backup = mm_dir / "mmwave_truncated_backup"
    backup.mkdir(parents=True, exist_ok=True)

    # ── 1. 截断点 ──
    py_ms = load_py_ms(mm_dir, subject)
    if args.mode == "block6":
        t_cut_abs = block6_stop_ms(beh_dir)
        print(f"[1/5] 截断点: 行为实验结束 block_stop = 距首帧 "
              f"{round((t_cut_abs - py_ms[0]) / 1000, 2)}s")
    else:
        t_cut_abs = int(py_ms[0]) + args.cut_ms
        print(f"[1/5] 截断点: 距首帧 {args.cut_ms}ms")

    n_keep = int(np.searchsorted(py_ms, t_cut_abs, side="right"))
    boundary_part = n_keep // 1000
    boundary_frames = n_keep % 1000
    if args.align_part and boundary_frames:
        print(f"      整片对齐: 丢弃边界片 {boundary_frames} 帧余量")
        n_keep -= boundary_frames
        boundary_frames = 0
    print(f"      保留 {n_keep} 帧 = 片 0-{n_keep // 1000 - (1 if boundary_frames == 0 else 0)} "
          f"完整 + 边界片 {boundary_frames} 帧")

    # ── 2. 边界片裁剪（重写 npz, 保留前 boundary_frames 帧） ──
    if boundary_frames:
        bpath = mm_dir / f"sub-{subject}_mmwave_datacube_part{boundary_part:03d}.npz"
        with np.load(bpath) as d:
            keys = sorted(k for k in d.keys() if k.startswith("tx"))
            chunk = {k: d[k][:boundary_frames] for k in keys}
        np.savez(bpath, **chunk)
        print(f"[2/5] 边界片 part{boundary_part:03d} 裁剪为前 {boundary_frames} 帧")
    else:
        print("[2/5] 无边界片需裁剪（恰好整片对齐）")

    # ── 3. 移除后续分片到备份目录 ──
    first_del = boundary_part + (1 if boundary_frames else 0)
    moved = 0
    for fn in sorted(mm_dir.glob(f"sub-{subject}_mmwave_datacube_part*.npz")):
        num = int(fn.stem.rsplit("part", 1)[-1])
        if num >= first_del:
            shutil.move(str(fn), backup / fn.name)
            moved += 1
    print(f"[3/5] 移动 {moved} 片（part{first_del:03d} 起）到 {backup}")

    # ── 4. 截断 timestamps.csv ──
    ts_path = mm_dir / f"sub-{subject}_mmwave_timestamps.csv"
    with open(ts_path, encoding="utf-8") as f:
        lines = f.readlines()
    with open(ts_path, "w", encoding="utf-8") as f:
        f.writelines(lines[:n_keep])
    print(f"[4/5] timestamps.csv: {len(lines)} → {n_keep} 行")

    # ── 5. 截断 bin + 更新 meta.json ──
    bin_path = mm_dir / f"sub-{subject}_mmwave.datacube.bin"
    meta_path = mm_dir / f"sub-{subject}_mmwave.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    frame_bytes = detect_bin_frame_bytes(bin_path, int(meta["frame_count"]))
    target = BIN_HEADER + n_keep * frame_bytes
    with open(bin_path, "r+b") as f:
        f.truncate(target)
    meta["frame_count"] = n_keep
    meta["duration_s"] = round(float((py_ms[n_keep - 1] - py_ms[0]) / 1000), 2)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"[5/5] bin 截断到 {target:,} 字节（{n_keep} 帧 × {frame_bytes} 字节）; "
          f"meta.json frame_count={n_keep} duration_s={meta['duration_s']}")
    print("完成")


if __name__ == "__main__":
    main()
