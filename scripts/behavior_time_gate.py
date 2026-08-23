"""按行为时间轴为毫米波分析生成基线与正式 block 的帧裁剪范围。

本模块只读取 ``master_timeline.csv`` 和毫米波时间戳 CSV；不会读取 npz 原始波形。
正式任务层由每个 ``block_start`` 到 ``block_stop`` 的独立区间组成，不能拼接后
作为连续信号处理，以免跨休息段产生伪造的 IBI/HRV 连续性。
"""

from __future__ import annotations

import bisect
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


INVALID_RECORDS = {
    ("E_Data", "067"),
    ("Formal_mmwave", "036"),
    ("Formal_mmwave", "038"),
    ("Formal_mmwave", "040"),
    ("Formal_mmwave", "041"),
    ("Formal_mmwave", "047"),
}
REVIEW_RECORDS = {("E_Data", "099")}

EXCLUSION_REASONS = [
    "experiment_start 至 baseline_start：设备启动、调试与进入基线前阶段",
    "baseline_stop 至首个 block_start：cover、instructions 与 practice",
    "正式 block 之间：休息与页面切换",
    "最后 block_stop 之后：结算、起身与设备停止尾段",
]


@dataclass(frozen=True)
class FrameSegment:
    layer: str
    label: str
    start_ms: float
    end_ms: float
    frame_start: int
    frame_end: int
    frame_count: int
    retained_duration_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def subject_id_from_dir(subject_dir: Path) -> str | None:
    stem = subject_dir.name.lower()
    if not stem.startswith("sub-"):
        return None
    digits = "".join(ch for ch in stem[4:] if ch.isdigit())
    return digits.zfill(3) if digits else None


def source_tag(root: Path) -> str:
    name = root.name
    if name == "Data":
        return "E_Data"
    if name == "正式实验":
        return "Formal_mmwave"
    return name


def find_timestamp_path(subject_dir: Path, subject_id: str) -> Path:
    candidates = sorted(subject_dir.rglob("*mmwave_timestamps*.csv"))
    if not candidates:
        raise FileNotFoundError(f"未找到毫米波时间戳 CSV：{subject_dir}")
    exact = [path for path in candidates if subject_id in path.name]
    return exact[0] if exact else candidates[0]


def find_mmwave_dir(subject_dir: Path) -> Path:
    candidates = sorted(path for path in subject_dir.glob("mmwave") if path.is_dir())
    if not candidates:
        raise FileNotFoundError(f"未找到毫米波分片目录：{subject_dir}")
    return candidates[0]


def find_timeline_path(subject_dir: Path) -> Path:
    candidates = sorted(subject_dir.glob("beh/master_timeline.csv"))
    if not candidates:
        raise FileNotFoundError(f"未找到 beh/master_timeline.csv：{subject_dir}")
    return candidates[0]


def load_radar_timestamps_ms(path: Path) -> list[float]:
    timestamps: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            try:
                # 与 process_vital_signs_v3_1_1.load_radar_timestamps 保持同一跨模态列口径。
                timestamps.append(float(row[2] if len(row) >= 3 else row[1]))
            except ValueError:
                continue
    if not timestamps:
        raise ValueError(f"没有可用的毫米波时间戳：{path}")
    if any(b < a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError(f"毫米波时间戳非单调递增：{path}")
    return timestamps


def load_timeline_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                unix_ms = float(row["unix_ms"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append({
                "marker": str(row.get("marker") or row.get("event", "")).strip().lower(),
                "detail": str(row.get("detail", "")).strip(),
                "unix_ms": unix_ms,
            })
    return sorted(rows, key=lambda item: item["unix_ms"])


def _marker_times(rows: Iterable[dict], marker: str) -> list[float]:
    return [row["unix_ms"] for row in rows if row["marker"] == marker]


def _make_segment(layer: str, label: str, start_ms: float, end_ms: float, timestamps: list[float]) -> FrameSegment:
    if end_ms <= start_ms:
        raise ValueError(f"{label} 的结束时间不晚于开始时间")
    frame_start = bisect.bisect_left(timestamps, start_ms)
    frame_end = bisect.bisect_left(timestamps, end_ms)
    if frame_end <= frame_start:
        raise ValueError(f"{label} 映射后没有保留帧（{frame_start}:{frame_end}）")
    return FrameSegment(
        layer=layer,
        label=label,
        start_ms=start_ms,
        end_ms=end_ms,
        frame_start=frame_start,
        frame_end=frame_end,
        frame_count=frame_end - frame_start,
        retained_duration_s=round((timestamps[frame_end - 1] - timestamps[frame_start]) / 1000.0, 3),
    )


def build_segments(timeline_path: Path, timestamp_path: Path) -> tuple[FrameSegment, list[FrameSegment], list[float]]:
    rows = load_timeline_rows(timeline_path)
    timestamps = load_radar_timestamps_ms(timestamp_path)
    baseline_starts = _marker_times(rows, "baseline_start")
    baseline_stops = _marker_times(rows, "baseline_stop")
    block_starts = _marker_times(rows, "block_start")
    block_stops = _marker_times(rows, "block_stop")
    if len(baseline_starts) != 1 or len(baseline_stops) != 1:
        raise ValueError("应恰有一个 baseline_start 与一个 baseline_stop")
    if len(block_starts) != len(block_stops) or not block_starts:
        raise ValueError("block_start/block_stop 数量不一致或缺失")
    baseline = _make_segment("baseline", "baseline", baseline_starts[0], baseline_stops[0], timestamps)
    blocks = [
        _make_segment("task", f"block_{index}", start, stop, timestamps)
        for index, (start, stop) in enumerate(zip(block_starts, block_stops), start=1)
    ]
    if any(block.start_ms < baseline.end_ms for block in blocks):
        raise ValueError("正式 block 与 baseline 时间重叠")
    return baseline, blocks, timestamps


def build_record(root: Path, subject_dir: Path) -> dict:
    subject_id = subject_id_from_dir(subject_dir)
    if subject_id is None:
        raise ValueError(f"无法解析被试编号：{subject_dir}")
    tag = source_tag(root)
    record: dict = {
        "source_tag": tag,
        "source_root": str(root),
        "subject": f"sub-{subject_id}",
        "subject_id": subject_id,
        "subject_dir": str(subject_dir),
        "status": "included",
        "exclusion_reasons": EXCLUSION_REASONS,
    }
    if (tag, subject_id) in INVALID_RECORDS:
        record.update(status="excluded_invalid", exclusion_note="既有审计确认毫米波文件缺失或空文件")
        return record
    if (tag, subject_id) in REVIEW_RECORDS:
        record.update(status="excluded_review", exclusion_note="sub-099 缺少 meta，保持待复核，不进入主队列")
        return record
    try:
        timeline_path = find_timeline_path(subject_dir)
        timestamp_path = find_timestamp_path(subject_dir, subject_id)
        mmwave_dir = find_mmwave_dir(subject_dir)
        baseline, blocks, timestamps = build_segments(timeline_path, timestamp_path)
    except (FileNotFoundError, ValueError) as exc:
        record.update(status="excluded_invalid", exclusion_note=str(exc))
        return record
    total_duration_s = round((timestamps[-1] - timestamps[0]) / 1000.0, 3)
    task_frames = sum(item.frame_count for item in blocks)
    task_duration_s = round(sum(item.retained_duration_s for item in blocks), 3)
    retained_frames = baseline.frame_count + task_frames
    retained_duration_s = round(baseline.retained_duration_s + task_duration_s, 3)
    record.update(
        timeline_path=str(timeline_path),
        timestamp_path=str(timestamp_path),
        mmwave_dir=str(mmwave_dir),
        crop_start_ms=min(item.start_ms for item in blocks),
        crop_end_ms=max(item.end_ms for item in blocks),
        total_frames=len(timestamps),
        total_duration_s=total_duration_s,
        baseline=baseline.as_dict(),
        blocks=[item.as_dict() for item in blocks],
        task_block_count=len(blocks),
        task_retained_frames=task_frames,
        task_retained_duration_s=task_duration_s,
        baseline_retained_frames=baseline.frame_count,
        baseline_retained_duration_s=baseline.retained_duration_s,
        retained_frames=retained_frames,
        retained_duration_s=retained_duration_s,
        excluded_frames=len(timestamps) - retained_frames,
        excluded_duration_s=round(max(0.0, total_duration_s - retained_duration_s), 3),
    )
    return record


def discover_records(roots: Iterable[Path]) -> list[dict]:
    records: list[dict] = []
    for root in roots:
        for subject_dir in sorted(path for path in root.glob("sub-*") if path.is_dir()):
            records.append(build_record(root, subject_dir))
    return records
