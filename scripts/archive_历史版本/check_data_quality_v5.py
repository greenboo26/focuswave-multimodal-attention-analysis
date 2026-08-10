"""
基于 v5 pipeline 的毫米波生命体征批量质量检查脚本。

支持两种模式：
1. 运行 run_v5_case.py 里已经登记的 case
2. 扫描某个目录下所有 part*.npz 分片文件并批量检查
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from process_vital_signs_v5 import analyze, plot
from run_v5_case import CASES


SCRIPT_DIR = Path(__file__).resolve().parent
ALG_DIR = SCRIPT_DIR.parent
OUTPUT_ROOT = ALG_DIR / "results_v5" / "quality_check"


def _fmt_num(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _sanitize_name(name: str) -> str:
    safe = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_"):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe)


def _iter_part_files(parts_dir: Path) -> List[Path]:
    files = sorted(parts_dir.glob("*part*.npz"))
    if not files:
        raise FileNotFoundError(f"在目录中没有找到 part*.npz 文件：{parts_dir}")
    return files


def _build_targets(args) -> List[Tuple[str, Path]]:
    targets: List[Tuple[str, Path]] = []

    if args.parts_dir:
        parts_dir = Path(args.parts_dir)
        for path in _iter_part_files(parts_dir):
            targets.append((path.stem, path))
        return targets

    for case_name in args.cases:
        targets.append((case_name, CASES[case_name]))
    return targets


def evaluate_result(case_name: str, data_path: Path, result: Dict, plot_path: Path) -> Dict:
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

    if duration_s < 30:
        issues.append("时长偏短")
    elif duration_s >= 60:
        strengths.append("时长较充足")

    if hr_freq is None or hr_time is None:
        issues.append("心率结果不完整")
    else:
        if 40 <= hr_time <= 120:
            strengths.append("心率时域值在常见静息范围内")
        else:
            issues.append("心率时域值偏离常见静息范围")
        if hr_diff <= 8:
            strengths.append("心率频域和时域较一致")
        elif hr_diff <= 15:
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
        if br_diff <= 3:
            strengths.append("呼吸频域和时域较一致")
        elif br_diff <= 6:
            issues.append("呼吸频域和时域有一定偏差")
        else:
            issues.append("呼吸频域和时域偏差较大")

    if hr["n_peaks"] < 15:
        issues.append("心跳峰数偏少，IBI/HRV 稳定性不足")
    else:
        strengths.append("心跳峰数基本够用")

    if br["n_peaks"] < 4:
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
        "case": case_name,
        "method": result["method"],
        "data_path": str(data_path),
        "duration_s": duration_s,
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
        "plot_path": str(plot_path),
        "json_path": str((plot_path.parent / f"{plot_path.stem}.json").resolve()),
    }


def write_csv(rows: List[Dict], out_path: Path) -> None:
    fieldnames = [
        "case",
        "method",
        "data_path",
        "duration_s",
        "best_channel",
        "breath_bin",
        "heart_bin",
        "hr_freq_bpm",
        "hr_time_bpm",
        "hr_diff_bpm",
        "hr_peaks",
        "br_freq_bpm",
        "br_time_bpm",
        "br_diff_bpm",
        "br_peaks",
        "breath_std_mm",
        "heart_std_mm",
        "status",
        "strengths",
        "issues",
        "plot_path",
        "json_path",
    ]
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: List[Dict], out_path: Path, method: str, source_label: str) -> None:
    lines = [
        "# 毫米波生命体征数据质量检查结果",
        "",
        "- 生成日期：2026-08-01",
        f"- 方法：`{method}`",
        f"- 数据来源：`{source_label}`",
        "- 性质：自动初筛结果，不等于真值验证",
        "",
        "## 总览",
        "",
        "| case | 状态 | HR 频域/时域 | BR 频域/时域 | 主要问题 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        hr_text = f"{_fmt_num(row['hr_freq_bpm'])} / {_fmt_num(row['hr_time_bpm'])}"
        br_text = f"{_fmt_num(row['br_freq_bpm'])} / {_fmt_num(row['br_time_bpm'])}"
        issues = row["issues"] or "无明显异常"
        lines.append(f"| {row['case']} | {row['status']} | {hr_text} | {br_text} | {issues} |")

    lines.extend(["", "## 逐项说明", ""])

    for row in rows:
        lines.extend(
            [
                f"### {row['case']}",
                "",
                f"- 数据：`{row['data_path']}`",
                f"- 状态：`{row['status']}`",
                f"- 时长：`{_fmt_num(row['duration_s'])} s`",
                f"- bin 选择：呼吸 `bin {row['breath_bin']}`，心跳 `bin {row['heart_bin']}`，通道 `ch {row['best_channel']}`",
                f"- 心率：频域 `{_fmt_num(row['hr_freq_bpm'])} BPM`，时域 `{_fmt_num(row['hr_time_bpm'])} BPM`，差值 `{_fmt_num(row['hr_diff_bpm'])} BPM`，峰数 `{row['hr_peaks']}`",
                f"- 呼吸：频域 `{_fmt_num(row['br_freq_bpm'])} BPM`，时域 `{_fmt_num(row['br_time_bpm'])} BPM`，差值 `{_fmt_num(row['br_diff_bpm'])} BPM`，峰数 `{row['br_peaks']}`",
                f"- 波形强度：呼吸 std `{_fmt_num(row['breath_std_mm'])} mm`，心跳 std `{_fmt_num(row['heart_std_mm'])} mm`",
                f"- 优点：{row['strengths'] or '无'}",
                f"- 问题：{row['issues'] or '无'}",
                f"- 图像：`{row['plot_path']}`",
                "",
            ]
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def run_targets(targets: Iterable[Tuple[str, Path]], method: str, out_dir: Path) -> List[Dict]:
    rows: List[Dict] = []
    for case_name, data_path in targets:
        case_out = out_dir / _sanitize_name(case_name) / method
        case_out.mkdir(parents=True, exist_ok=True)

        result, waveforms = analyze(data_path, method=method, output_dir=case_out)
        plot_path = plot(result, waveforms, case_out, result["session"])
        row = evaluate_result(case_name, data_path, result, plot_path)
        rows.append(row)
        print(
            f"[{case_name}] {row['status']} | "
            f"HR {row['hr_freq_bpm']}/{row['hr_time_bpm']} BPM | "
            f"BR {row['br_freq_bpm']}/{row['br_time_bpm']} BPM"
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description="v5 毫米波数据批量质量检查")
    parser.add_argument(
        "--cases",
        nargs="*",
        default=sorted(CASES.keys()),
        choices=sorted(CASES.keys()),
        help="run_v5_case.py 里登记过的 case；使用 --parts-dir 时忽略。",
    )
    parser.add_argument(
        "--parts-dir",
        default=None,
        help="包含 part*.npz 分片文件的目录。",
    )
    parser.add_argument(
        "--method",
        choices=["bp", "vmd_heart"],
        default="vmd_heart",
        help="默认推荐使用 vmd_heart。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_ROOT),
        help="质量检查输出目录。",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = _build_targets(args)
    source_label = args.parts_dir if args.parts_dir else "脚本内置 case"
    if args.parts_dir:
        source_name = _sanitize_name(Path(args.parts_dir).name or "parts")
        out_dir = out_dir / f"parts_{source_name}"
        out_dir.mkdir(parents=True, exist_ok=True)

    rows = run_targets(targets, args.method, out_dir)

    stem = f"quality_check_{args.method}"
    csv_path = out_dir / f"{stem}.csv"
    md_path = out_dir / f"{stem}.md"
    write_csv(rows, csv_path)
    write_markdown(rows, md_path, args.method, source_label)

    print(f"csv: {csv_path}")
    print(f"md: {md_path}")


if __name__ == "__main__":
    main()
