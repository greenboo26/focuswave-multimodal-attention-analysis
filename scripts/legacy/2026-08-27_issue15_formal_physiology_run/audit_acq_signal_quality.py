"""Aggregate ACQ mmWave signal-quality proxies for the strict SART/reference cohort."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import median


ROOT = Path(r"D:\Project\厚粲杯\08_算法")
MMWAVE_ROOT = ROOT / "output" / "20_生理金标准验证" / "05_毫米波参照_FAST"
OUT_DIR = ROOT / "work" / "issue15_formal_physiology_run_2026-08-27" / "output" / "acq_signal_quality"
SUBJECTS = ["97793", "97794", "97795", "97796", "9779"]


def finite(values):
    return [float(v) for v in values if v is not None and math.isfinite(float(v))]


def pct(values, threshold):
    vals = finite(values)
    return 100.0 * sum(v >= threshold for v in vals) / len(vals) if vals else None


def read_subject(subject):
    path = MMWAVE_ROOT / f"sub-{subject}_" / f"sub-{subject}_ses-SART_mmwave_vital_signs.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    hr = data["heart_rate"]
    br = data["breath_rate"]
    hrv = data["hrv"]
    signal = hr["self_check"]["signal_quality"]
    course = hr["time_course"]
    points = course.get("points", [])
    point_quality = [p.get("quality") for p in points]
    gaps = [p.get("time_freq_gap_bpm") for p in points]
    confidences = [p.get("confidence") for p in points]
    return {
        "subject": subject,
        "duration_s": data.get("duration_s"),
        "heart_ptp_mm": data["displacement_mm"].get("heart_ptp"),
        "heart_std_mm": data["displacement_mm"].get("heart_std"),
        "breath_ptp_mm": data["displacement_mm"].get("breath_ptp"),
        "breath_std_mm": data["displacement_mm"].get("breath_std"),
        "heart_signal_usable_ratio_pct": 100.0 * signal.get("usable_ratio", 0.0),
        "heart_signal_min_std_mm": signal.get("min_observed_std_mm"),
        "heart_high_quality_pct": 100.0 * sum(q == "high" for q in point_quality) / len(point_quality) if point_quality else None,
        "heart_usable_quality_pct": 100.0 * sum(q in {"high", "medium"} for q in point_quality) / len(point_quality) if point_quality else None,
        "heart_median_confidence": median(finite(confidences)) if finite(confidences) else None,
        "heart_gap_median_bpm": median(finite(gaps)) if finite(gaps) else None,
        "heart_gap_gt10_pct": pct(gaps, 10.0),
        "heart_ptp_to_std_ratio": (float(data["displacement_mm"].get("heart_ptp")) / float(data["displacement_mm"].get("heart_std"))) if data["displacement_mm"].get("heart_std") else None,
        "breath_ptp_to_std_ratio": (float(data["displacement_mm"].get("breath_ptp")) / float(data["displacement_mm"].get("breath_std"))) if data["displacement_mm"].get("breath_std") else None,
        "hr_freq_bpm": hr.get("freq_bpm"),
        "hr_time_bpm": hr.get("time_bpm"),
        "br_freq_bpm": br.get("freq_bpm"),
        "br_time_bpm": br.get("time_bpm"),
        "br_confidence": br.get("confidence"),
        "rmssd_ms": hrv.get("RMSSD_ms"),
        "sdnn_ms": hrv.get("SDNN_ms"),
    }


def summarize(rows):
    keys = [
        "heart_ptp_mm", "heart_std_mm", "heart_signal_usable_ratio_pct",
        "heart_high_quality_pct", "heart_usable_quality_pct", "heart_median_confidence",
        "heart_gap_median_bpm", "heart_gap_gt10_pct", "heart_ptp_to_std_ratio",
        "breath_ptp_mm", "breath_std_mm", "breath_ptp_to_std_ratio",
    ]
    result = {key: {"median": median(finite(r.get(key) for r in rows))} for key in keys}
    confidence = [r.get("br_confidence") for r in rows]
    result["br_confidence"] = {
        "counts": {label: confidence.count(label) for label in sorted(set(confidence))},
        "high_or_medium_pct": 100.0 * sum(v in {"high", "medium"} for v in confidence) / len(confidence),
    }
    return result


def main():
    rows = [read_subject(subject) for subject in SUBJECTS]
    result = {
        "strict_sart_reference_subjects": SUBJECTS,
        "n_subjects": len(rows),
        "snr_interpretation": "These are algorithmic signal-quality and amplitude/noise proxies, not calibrated sensor SNR in dB.",
        "subjects": rows,
        "median_summary": summarize(rows),
        "interpretation": {
            "heart": "Waveform is present and passes the current hard gate for this cohort, but time-frequency disagreement and medium/low confidence require window-level QC.",
            "breath": "Breath waveform is present, but the rate estimator requires independent reference validation because a half-frequency failure is observed.",
            "hrv": "HRV values are not accepted as valid physiological estimates until the independent ECG comparison is corrected.",
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "acq_signal_quality_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# ACQ 严格行为时间窗毫米波质量审计",
        "",
        f"对象：{len(rows)} 名具有 ECG/RSP 与毫米波配对数据的 SART 被试。所有结果使用行为有效区间，排除开始前、结束后及无效练习/清理记录。",
        "",
        "这里的‘SNR’仅指算法质量字段和振幅/噪声代理，不是经过传感器标定的 dB 信噪比。",
        "",
        "## 关键中位数",
        "",
        f"- 心动位移峰峰值：{result['median_summary']['heart_ptp_mm']['median']:.2f} mm；10 秒信号硬门控可用比例：{result['median_summary']['heart_signal_usable_ratio_pct']['median']:.1f}%。",
        f"- 心率高质量点比例：{result['median_summary']['heart_high_quality_pct']['median']:.1f}%；高/中质量点比例：{result['median_summary']['heart_usable_quality_pct']['median']:.1f}%。",
        f"- 心率时频差中位数：{result['median_summary']['heart_gap_median_bpm']['median']:.2f} bpm；超过 10 bpm 的点比例：{result['median_summary']['heart_gap_gt10_pct']['median']:.1f}%。",
        f"- 呼吸位移峰峰值：{result['median_summary']['breath_ptp_mm']['median']:.2f} mm；五名被试的呼吸率置信度标签均为：{result['median_summary']['br_confidence']['counts']}。",
        "",
        "## 结论",
        "",
        "心动波形在当前五名严格配对被试上是可检测的，但‘有波形’不等于‘每个窗口都可用于生理估计’，应保留时频一致性和置信度门控。呼吸波形同样存在，但呼吸率已经出现系统性半频偏差。HRV 的振幅/噪声代理不能替代 ECG 参照，因此当前不进入专注判定。",
    ]
    (OUT_DIR / "ACQ_signal_quality_audit_20260822.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["median_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


