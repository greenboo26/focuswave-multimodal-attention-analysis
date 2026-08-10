"""
check_preexp_data.py — 预实验数据完整性快检
====================================================
目的: 对新采集被试（E:\\预实验\\sub-XXX_）做采集端到端的
      完整性检查（毫米波分片/时间戳/行为文件），在跑分析管线
      前确认数据无缺帧、缺片、时间戳断裂。

用法:
  python check_preexp_data.py --subject 001
  python check_preexp_data.py --subject 002

输出:
  标准输出逐项报告 + 问题标记

依赖: numpy（仅时间戳间隔统计）
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CHUNK = 1000  # 每 npz 片帧数（与采集写入一致）
MIN_PART_BYTES = 100_000  # 尾部空片判定（<100KB 视为崩溃残留）


def check_subject(data_root: Path, subject: str) -> int:
    n_issues = 0
    subdir = data_root / f"sub-{subject}_"
    mm_dir = subdir / "mmwave"
    beh_dir = subdir / "beh"

    def issue(msg):
        nonlocal n_issues
        n_issues += 1
        print(f"  [问题] {msg}")

    def ok(msg):
        print(f"  [OK] {msg}")

    print(f"=== sub-{subject} ===")

    # ── 1. 毫米波 meta 与文件 ──
    meta_path = mm_dir / f"sub-{subject}_mmwave.meta.json"
    if not meta_path.exists():
        issue(f"meta.json 缺失: {meta_path}")
        return n_issues
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    frame_count = int(meta["frame_count"])
    ok(f"meta: {frame_count} 帧, {meta['duration_s']}s, {meta['fps']}fps, "
       f"{meta['range_fft']}×{meta['doppler_fft']} FFT, {meta['tx_ant']}TX/{meta['rx_ant']}RX")

    # ── 2. npz 分片连续性 ──
    parts = sorted(mm_dir.glob(f"sub-{subject}_mmwave_datacube_part*.npz"))
    main_npz = mm_dir / f"sub-{subject}_mmwave_datacube.npz"
    n_expected_parts = (frame_count + CHUNK - 1) // CHUNK - 1  # 主文件算片 0
    if not main_npz.exists():
        issue(f"主 npz 缺失: {main_npz.name}")
    # 尾部小文件（<100KB）是崩溃残留, 管线 load_frames 会跳过, 单独报告
    small = [p for p in parts if p.stat().st_size < MIN_PART_BYTES]
    good_parts = [p for p in parts if p.stat().st_size >= MIN_PART_BYTES]
    if small:
        print(f"  [提示] {len(small)} 片 <100KB（崩溃残留, 管线自动跳过）: "
              f"{[p.name for p in small[:5]]}")
    if len(good_parts) != n_expected_parts:
        issue(f"有效分片 {len(good_parts)} ≠ 期望 {n_expected_parts}（frame_count={frame_count}）")
    else:
        ok(f"有效分片齐全: {len(good_parts)} 片（含主文件共 {len(good_parts) + 1} 片）")
    # 编号连续性（part001 起, 无跳号）
    numbers = []
    for p in good_parts:
        try:
            numbers.append(int(p.stem.split("part")[-1]))
        except ValueError:
            issue(f"无法解析片号: {p.name}")
    if numbers:
        missing = [i for i in range(1, max(numbers) + 1) if i not in set(numbers)]
        if missing:
            issue(f"分片缺号: {missing[:10]}{'…' if len(missing) > 10 else ''}")

    # ── 3. 时间戳连续性与 meta 一致性 ──
    ts_path = mm_dir / f"sub-{subject}_mmwave_timestamps.csv"
    if not ts_path.exists():
        issue(f"timestamps.csv 缺失: {ts_path.name}")
    else:
        with open(ts_path) as f:
            rows = [ln.strip().split(",") for ln in f if ln.strip()]
        n_ts = len(rows)
        if n_ts != frame_count:
            issue(f"时间戳行数 {n_ts} ≠ meta frame_count {frame_count}")
        else:
            ok(f"时间戳行数 = frame_count = {n_ts}")
        try:
            rad_ms = np.array([int(r[1]) for r in rows], dtype=np.int64)  # 雷达硬件时钟
            py_ms = np.array([int(r[2]) for r in rows], dtype=np.int64)   # Python 时钟
        except (IndexError, ValueError):
            issue("时间戳格式异常（应为 frame_idx,rad_ms,py_ms 3 列）")
            return n_issues
        gaps = np.diff(rad_ms)  # 主时钟用雷达时间戳（硬件时钟, 无 Python 侧抖动）
        med_gap = float(np.median(gaps))
        max_gap = int(gaps.max())
        n_big = int((gaps > 50).sum())  # >50ms 视为丢帧间隙（正常 10ms 级）
        py_med = float(np.median(np.diff(py_ms)))
        ok(f"雷达时钟: 中位间隔 {med_gap:.1f}ms, 最大间隔 {max_gap}ms, "
           f">50ms 间隙 {n_big} 处")
        if max_gap > 1000:
            issue(f"雷达时钟存在 >1s 断裂（最大 {max_gap}ms）, 该处数据将缺帧")
        if n_big > 10:
            issue(f"雷达时钟 >50ms 间隙 {n_big} 处偏多, 建议核对是否影响窗分析")
        if py_med < 5 or py_med > 20:
            print(f"  [提示] Python 时钟中位间隔 {py_med:.1f}ms（与雷达时钟不同属正常, "
                  f"仅用于事件对齐, 不做帧计数）")

    # ── 4. 行为文件 ──
    blocks = sorted(beh_dir.glob(f"sub-{subject}_Block*_beh.csv"))
    if len(blocks) != 6:
        issue(f"Block 行为文件 {len(blocks)} 个 ≠ 6")
    else:
        ok(f"6 个 Block 文件齐全")
    summary = beh_dir / "subject_summary.csv"
    if summary.exists():
        with open(summary, encoding="utf-8-sig") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if len(lines) >= 2:
            header, row = lines[0], lines[1]
            print(f"  [OK] 行为总结: {row}")
        else:
            issue("subject_summary.csv 无数据行")
    else:
        issue("subject_summary.csv 缺失")
    timeline = beh_dir / "master_timeline.csv"
    if not timeline.exists():
        issue("master_timeline.csv 缺失")
    else:
        n_evt = sum(1 for ln in timeline.open(encoding="utf-8") if ln.strip())
        ok(f"master_timeline: {n_evt - 1} 个事件")

    print()
    return n_issues


def main():
    parser = argparse.ArgumentParser(description="预实验数据完整性快检")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--data-root", type=str, default=r"E:\预实验")
    args = parser.parse_args()

    total = 0
    for s in args.subject.split(","):
        total += check_subject(Path(args.data_root), s.strip().zfill(3))
    print(f"共 {total} 个问题" if total else "全部通过")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
