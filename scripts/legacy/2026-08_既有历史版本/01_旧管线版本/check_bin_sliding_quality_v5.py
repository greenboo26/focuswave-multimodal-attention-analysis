"""
Sliding-window quality check on a full mmWave datacube.bin recording.

This script avoids loading the full bin file into memory at once.
It reads frame windows directly from the bin file, runs the current v5 pipeline,
and writes a CSV/Markdown summary for 30s / 60s style analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from process_vital_signs_v2 import FS
from process_vital_signs_v5 import analyze_iq, plot


HEADER_SIZE = 32
FRAME_SIZE = 8196
SAMPLES_PER_FRAME = 256
CHANNELS = 8
UINT32_PER_FRAME = SAMPLES_PER_FRAME * CHANNELS
META_SUFFIX = ".meta.json"


def load_meta(bin_path: Path) -> Dict:
    meta_path = bin_path.with_suffix("").with_suffix(".meta.json")
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    fallback = bin_path.parent / (bin_path.stem.replace(".datacube", "") + META_SUFFIX)
    if fallback.exists():
        return json.loads(fallback.read_text(encoding="utf-8"))
    return {}


def iter_bin_windows(bin_path: Path, window_frames: int, step_frames: int):
    file_size = bin_path.stat().st_size
    n_frames = (file_size - HEADER_SIZE) // FRAME_SIZE

    with bin_path.open("rb") as f:
        for start_frame in range(0, max(1, n_frames - window_frames + 1), step_frames):
            f.seek(HEADER_SIZE + start_frame * FRAME_SIZE)
            raw = f.read(window_frames * FRAME_SIZE)
            if len(raw) < window_frames * FRAME_SIZE:
                break
            yield start_frame, parse_window_bytes(raw)


def parse_window_bytes(raw: bytes) -> np.ndarray:
    frame_bytes = np.frombuffer(raw, dtype=np.uint8).reshape(-1, FRAME_SIZE)
    adc_bytes = frame_bytes[:, 4:]
    packed = adc_bytes.reshape(-1).view(np.uint32).reshape(-1, UINT32_PER_FRAME)

    imag = (packed & 0xFFFF).astype(np.int32)
    imag[imag >= 0x8000] -= 0x10000
    real = ((packed >> 16) & 0xFFFF).astype(np.int32)
    real[real >= 0x8000] -= 0x10000

    iq = (real + 1j * imag).astype(np.complex64)
    return iq.reshape(-1, SAMPLES_PER_FRAME, CHANNELS)


def _fmt_num(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def evaluate_result(window_label: str, start_s: float, result: Dict, plot_path: Path | None) -> Dict:
    hr = result["heart_rate"]
    br = result["breath_rate"]
    duration_s = result["duration_s"]
    hr_freq = hr["freq_bpm"]
    hr_time = hr["time_bpm"]
    br_freq = br["freq_bpm"]
    br_time = br["time_bpm"]
    hr_diff = abs(hr_freq - hr_time) if hr_freq is not None and hr_time is not None else None
    br_diff = abs(br_freq - br_time) if br_freq is not None and br_time is not None else None

    issues: List[str] = []
    strengths: List[str] = []

    if duration_s < 20:
        issues.append("时长仍然偏短")
    elif duration_s >= 30:
        strengths.append("时长达到长窗分析要求")

    if hr_freq is None or hr_time is None:
        issues.append("心率结果不完整")
    else:
        if 40 <= hr_time <= 120:
            strengths.append("心率时域值在常见静息范围内")
        else:
            issues.append("心率时域值偏离常见静息范围")
        if hr_diff <= 6:
            strengths.append("心率频域和时域较一致")
        elif hr_diff <= 12:
            issues.append("心率频域和时域有一定偏差")
        else:
            issues.append("心率频域和时域偏差较大")

    if br_freq is None or br_time is None:
        issues.append("呼吸结果不完整")
    else:
        if 6 <= br_time <= 30:
            strengths.append("呼吸时域值在合理范围内")
        else:
            issues.append("呼吸时域值超出合理范围")
        if br_diff <= 2:
            strengths.append("呼吸频域和时域较一致")
        elif br_diff <= 4:
            issues.append("呼吸频域和时域有一定偏差")
        else:
            issues.append("呼吸频域和时域偏差较大")

    min_hr_peaks = max(15, int(duration_s * 0.55))
    min_br_peaks = max(3, int(duration_s / 12))
    if hr["n_peaks"] < min_hr_peaks:
        issues.append("心跳峰数偏少，长窗 IBI/HRV 稳定性不足")
    else:
        strengths.append("心跳峰数基本够用")

    if br["n_peaks"] < min_br_peaks:
        issues.append("呼吸峰数偏少，时域呼吸率不稳")
    else:
        strengths.append("呼吸峰数基本够用")

    if result["displacement_mm"]["heart_std"] < 0.01:
        issues.append("心跳波形幅度过小")
    if result["displacement_mm"]["breath_std"] < 0.02:
        issues.append("呼吸波形幅度过小")

    if not issues:
        status = "可用"
    elif len(issues) <= 2:
        status = "需复核"
    else:
        status = "可疑"

    return {
        "window": window_label,
        "start_s": round(start_s, 1),
        "duration_s": duration_s,
        "method": result["method"],
        "best_channel": result["best_channel"],
        "breath_bin": result["bins"]["breath"],
        "heart_bin": result["bins"]["heart"],
        "hr_freq_bpm": hr_freq,
        "hr_time_bpm": hr_time,
        "hr_diff_bpm": hr_diff,
        "hr_peaks": hr["n_peaks"],
        "br_freq_bpm": br_freq,
        "br_time_bpm": br_time,
        "br_diff_bpm": br_diff,
        "br_peaks": br["n_peaks"],
        "breath_std_mm": result["displacement_mm"]["breath_std"],
        "heart_std_mm": result["displacement_mm"]["heart_std"],
        "status": status,
        "strengths": "；".join(strengths),
        "issues": "；".join(issues),
        "plot_path": str(plot_path) if plot_path is not None else "",
    }


def build_failure_row(window_label: str, start_s: float, duration_s: float, error: Exception) -> Dict:
    return {
        "window": window_label,
        "start_s": round(start_s, 1),
        "duration_s": round(duration_s, 1),
        "method": "",
        "best_channel": "",
        "breath_bin": "",
        "heart_bin": "",
        "hr_freq_bpm": "",
        "hr_time_bpm": "",
        "hr_diff_bpm": "",
        "hr_peaks": "",
        "br_freq_bpm": "",
        "br_time_bpm": "",
        "br_diff_bpm": "",
        "br_peaks": "",
        "breath_std_mm": "",
        "heart_std_mm": "",
        "status": "失败",
        "strengths": "",
        "issues": f"窗口处理失败：{type(error).__name__}: {error}",
        "plot_path": "",
    }


def write_csv(rows: List[Dict], out_path: Path) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: List[Dict], out_path: Path, bin_path: Path, window_s: int, step_s: int) -> None:
    lines = [
        "# 毫米波 bin 长窗质量检查结果",
        "",
        f"- 数据：`{bin_path}`",
        f"- 窗口长度：`{window_s}s`",
        f"- 滑动步长：`{step_s}s`",
        "- 说明：这是基于整段 bin 文件切长窗后的自动初筛结果",
        "",
        "## 总览",
        "",
        "| window | 起始时间(s) | 状态 | HR 频域/时域 | BR 频域/时域 | 主要问题 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        hr_text = f"{_fmt_num(row['hr_freq_bpm'])} / {_fmt_num(row['hr_time_bpm'])}"
        br_text = f"{_fmt_num(row['br_freq_bpm'])} / {_fmt_num(row['br_time_bpm'])}"
        issues = row["issues"] or "无明显异常"
        lines.append(
            f"| {row['window']} | {row['start_s']} | {row['status']} | {hr_text} | {br_text} | {issues} |"
        )

    lines.extend(["", "## 逐窗说明", ""])

    for row in rows:
        lines.extend(
            [
                f"### {row['window']}",
                "",
                f"- 起始时间：`{row['start_s']} s`",
                f"- 时长：`{_fmt_num(row['duration_s'])} s`",
                f"- 状态：`{row['status']}`",
                f"- bin 选择：呼吸 `bin {row['breath_bin']}`，心跳 `bin {row['heart_bin']}`，通道 `ch {row['best_channel']}`",
                f"- 心率：频域 `{_fmt_num(row['hr_freq_bpm'])} BPM`，时域 `{_fmt_num(row['hr_time_bpm'])} BPM`，差值 `{_fmt_num(row['hr_diff_bpm'])} BPM`，峰数 `{row['hr_peaks']}`",
                f"- 呼吸：频域 `{_fmt_num(row['br_freq_bpm'])} BPM`，时域 `{_fmt_num(row['br_time_bpm'])} BPM`，差值 `{_fmt_num(row['br_diff_bpm'])} BPM`，峰数 `{row['br_peaks']}`",
                f"- 波形强度：呼吸 std `{_fmt_num(row['breath_std_mm'])} mm`，心跳 std `{_fmt_num(row['heart_std_mm'])} mm`",
                f"- 优点：{row['strengths'] or '无'}",
                f"- 问题：{row['issues'] or '无'}",
                f"- 图像：`{row['plot_path'] or '未保存'}`",
                "",
            ]
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="从整段 datacube.bin 按长窗滑动读取并做质量检查")
    parser.add_argument("bin_path", help="datacube.bin 路径")
    parser.add_argument("--window-s", type=int, default=30, help="窗口长度，默认 30 秒")
    parser.add_argument("--step-s", type=int, default=30, help="滑动步长，默认 30 秒")
    parser.add_argument("--method", choices=["bp", "vmd_heart"], default="vmd_heart")
    parser.add_argument("--output-dir", default=None, help="输出目录")
    parser.add_argument("--save-plots", action="store_true", help="是否为每个窗口保存图像")
    args = parser.parse_args()

    bin_path = Path(args.bin_path)
    window_frames = int(round(args.window_s * FS))
    step_frames = int(round(args.step_s * FS))

    root_out = Path(args.output_dir) if args.output_dir else (
        bin_path.parent.parent / "08_算法" / "results_v5" / "bin_windows"
        if bin_path.parent.name == "mmwave"
        else bin_path.parent / "bin_windows"
    )
    run_out = root_out / f"{bin_path.stem}_{args.window_s}s_step{args.step_s}s_{args.method}"
    run_out.mkdir(parents=True, exist_ok=True)

    meta = load_meta(bin_path)
    meta_out = run_out / "source_meta.json"
    meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    rows: List[Dict] = []
    for idx, (start_frame, iq_td) in enumerate(iter_bin_windows(bin_path, window_frames, step_frames), start=1):
        start_s = start_frame / FS
        end_s = start_s + iq_td.shape[0] / FS
        session = f"{bin_path.stem}_win{idx:03d}_{int(start_s):04d}s_{int(end_s):04d}s"
        win_out = run_out / session
        win_out.mkdir(parents=True, exist_ok=True)

        try:
            result, waveforms = analyze_iq(iq_td, session=session, method=args.method, output_dir=win_out)
            plot_path = plot(result, waveforms, win_out, result["session"]) if args.save_plots else None
            row = evaluate_result(session, start_s, result, plot_path)
            print(
                f"[{session}] {row['status']} | "
                f"HR {row['hr_freq_bpm']}/{row['hr_time_bpm']} BPM | "
                f"BR {row['br_freq_bpm']}/{row['br_time_bpm']} BPM"
            )
        except Exception as exc:
            row = build_failure_row(session, start_s, iq_td.shape[0] / FS, exc)
            print(f"[{session}] 失败 | {type(exc).__name__}: {exc}")

        rows.append(row)

    csv_path = run_out / "bin_window_quality.csv"
    md_path = run_out / "bin_window_quality.md"
    write_csv(rows, csv_path)
    write_markdown(rows, md_path, bin_path, args.window_s, args.step_s)

    print(f"csv: {csv_path}")
    print(f"md: {md_path}")


if __name__ == "__main__":
    main()


