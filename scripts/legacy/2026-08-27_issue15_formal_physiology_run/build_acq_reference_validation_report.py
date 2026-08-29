# -*- coding: utf-8 -*-
"""Build a strict ACQ ECG/RSP versus mmWave validation report.

The report is deliberately separate from the attention classifier results:
ACQ is an independent physiological reference set, while the SART behavior
timestamps define which windows are eligible.  No ECG/RSP value is used as a
feature or label in the attention model.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
INPUT = ROOT / "output" / "20_生理金标准验证" / "01_历史严格参照_v20260821"
OUT = ROOT / "work" / "issue15_formal_physiology_run_2026-08-27" / "output" / "acq_reference_validation"
REF_CSV = INPUT / "mmwave_vs_reference_probes_60s.csv"
BR_JSON = INPUT / "breath_method_comparison_current.json"
REF_METRICS = INPUT / "reference_metrics.json"
REPORT = OUT / "ACQ_reference_validation_20260827.md"


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def finite(rows: list[dict], key: str) -> np.ndarray:
    vals = []
    for r in rows:
        try:
            v = float(r.get(key, ""))
        except (TypeError, ValueError):
            continue
        if np.isfinite(v):
            vals.append(v)
    return np.asarray(vals, dtype=float)


def mae(rows: list[dict], pred: str, ref: str) -> tuple[int, float, float]:
    pairs = []
    for r in rows:
        try:
            a, b = float(r[pred]), float(r[ref])
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(a) and np.isfinite(b):
            pairs.append((a, b))
    if not pairs:
        return 0, float("nan"), float("nan")
    x = np.asarray(pairs, float)
    err = x[:, 0] - x[:, 1]
    return len(err), float(np.mean(np.abs(err))), float(np.mean(err))


def plot_validation(rows: list[dict], br: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    panels = [
        (rows, "hr_ecg_bpm", "hr_course_mm_bpm", "ECG HR (bpm)", "mmWave HR course (bpm)", "Heart-rate course"),
        (br.get("rows", []), "br_rsp_bpm", "br_mm_spectral_bpm", "Respiratory-belt BR (bpm)", "mmWave spectral BR (bpm)", "Respiration"),
        (rows, "rmssd_ecg_ms", "rmssd_mm_ms", "ECG RMSSD (ms)", "mmWave RMSSD (ms)", "Short-window HRV"),
    ]
    for ax, (source_rows, ref, pred, xlabel, ylabel, title) in zip(axes, panels):
        x, y = [], []
        for r in source_rows:
            try:
                a, b = float(r[ref]), float(r[pred])
            except (KeyError, TypeError, ValueError):
                continue
            if np.isfinite(a) and np.isfinite(b):
                x.append(a); y.append(b)
        if x:
            ax.scatter(x, y, s=22, alpha=.65, edgecolor="none")
            lo, hi = min(x + y), max(x + y)
            ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="identity")
            ax.legend(frameon=False, fontsize=8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(alpha=.25)
    fig.suptitle("Independent ACQ reference validation, strict behavior-gated windows")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_csv(REF_CSV)
    br = json.loads(BR_JSON.read_text(encoding="utf-8"))
    ref_metrics = json.loads(REF_METRICS.read_text(encoding="utf-8"))
    subject_counts = {s["subject"]: len(s.get("probes", [])) for s in ref_metrics if s.get("probes")}

    n_hr, hr_mae, hr_bias = mae(rows, "hr_course_mm_bpm", "hr_ecg_bpm")
    n_hr_peak, hr_peak_mae, hr_peak_bias = mae(rows, "hr_mm_bpm", "hr_ecg_bpm")
    n_rm, rm_mae, rm_bias = mae(rows, "rmssd_mm_ms", "rmssd_ecg_ms")
    n_sd, sd_mae, sd_bias = mae(rows, "sdnn_mm_ms", "sdnn_ecg_ms")
    n_br, br_mae, br_bias = mae(rows, "br_mm_bpm", "br_rsp_bpm")
    br_summary = br.get("summary", {})
    n_br_spec = int(br_summary.get("n_windows", 0) or 0)
    br_spec_mae = float(br_summary.get("spectral_mae_bpm")) if br_summary.get("spectral_mae_bpm") is not None else float("nan")
    br_spec_bias = float("nan")

    summary = {
        "reference": "BIOPAC ECG/RSP .acq",
        "strict_behavior_gate": True,
        "subjects_with_sart_reference_windows": len(subject_counts),
        "paired_windows": len(rows),
        "subject_window_counts": subject_counts,
        "heart_rate_course": {"n": n_hr, "mae_bpm": hr_mae, "bias_bpm": hr_bias,
                               "within_5_bpm": int(sum(abs(float(r["hr_course_error_bpm"])) <= 5 for r in rows if r.get("hr_course_error_bpm") not in (None, "")))},
        "heart_rate_peak": {"n": n_hr_peak, "mae_bpm": hr_peak_mae, "bias_bpm": hr_peak_bias},
        "respiration_peak": {"n": n_br, "mae_bpm": br_mae, "bias_bpm": br_bias},
        "respiration_spectral": {"n": n_br_spec, "mae_bpm": br_spec_mae, "bias_bpm": None,
                                  "within_5_bpm": br.get("summary", {}).get("spectral_within_5_bpm")},
        "hrv_rmssd": {"n": n_rm, "mae_ms": rm_mae, "bias_ms": rm_bias, "status": "not_reliable_for_current_pipeline"},
        "hrv_sdnn": {"n": n_sd, "mae_ms": sd_mae, "bias_ms": sd_bias, "status": "not_reliable_for_current_pipeline"},
    }
    (OUT / "acq_reference_validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    plot_validation(rows, br, OUT / "acq_reference_validation_scatter.png")

    REPORT.write_text(f"""# ACQ 独立生理参照验证报告（2026-08-22）

## 结论

这批 BIOPAC（ECG，心电图；RSP，呼吸带）与毫米波同步数据用于独立生理效标验证，不作为专注分类的输入。行为时间戳定义有效窗口，实验前基线、练习、休息和实验结束后的记录不进入配对分析。

当前形成 {len(subject_counts)} 名有 SART 参照窗口的被试、{len(rows)} 个严格门控探针窗口。

| 指标 | 毫米波估计 | 与参照的结果 | 当前判定 |
|---|---|---:|---|
| 心率，课程估计 | 滑动 HR | MAE={hr_mae:.2f} bpm，n={n_hr} | 可用于研究级趋势，仍需继续校准 |
| 心率，逐峰估计 | 峰间期 | MAE={hr_peak_mae:.2f} bpm，n={n_hr_peak} | 倍频/谐波错误仍明显 |
| 呼吸率，时间峰值 | 呼吸峰间期 | MAE={br_mae:.2f} 次/分，n={n_br} | 不可作为当前默认输出 |
| 呼吸率，频谱 | 主频 + 低频半频候选修正 | MAE={br_spec_mae:.2f} 次/分，n={n_br_spec} | 研究性候选，需独立队列复核 |
| RMSSD，短窗 HRV | 心跳间期变异 | MAE={rm_mae:.2f} ms，n={n_rm} | 不可靠，不用于临床或正式状态判定 |
| SDNN，短窗 HRV | 心跳间期变异 | MAE={sd_mae:.2f} ms，n={n_sd} | 不可靠，不用于临床或正式状态判定 |

## 解释边界

成人静息心率通常参考 60–100 bpm，静息呼吸率约 12–18 次/分；这些是一般健康成人参考范围，不是专注状态标签的正常值。任务中的 HR/BR 应优先做被试内基线变化和与行为效标的关联分析，不能用单个数值诊断健康或注意障碍。

短时 HRV 需要严格的正常搏动间期清洗和足够记录长度。当前毫米波逐搏间期误差尚未达到可以支持 RMSSD/SDNN 状态解释的程度，因此申请书中“毫米波可提取 HRV”目前只能作为待验证研究目标，不能写成已实现指标。

## 对系统路线的影响

1. 保留毫米波心率课程估计作为质量门控后的辅助生理趋势。
2. 呼吸率必须输出质量等级；检测到频谱半频或与呼吸带偏差过大时输出“不可用”，不能强行给出数值。
3. HRV 暂不进入默认专注分类模型。后续需用 ECG 对齐的原始 IBI 逐搏校准，并至少采用 5 分钟短时标准窗口，另行验证修正率和误差。
4. 专注识别仍以行为探针、SART 行为表现和跨模态一致性为效标；ECG/RSP 只用于独立验证，不产生标签泄漏。

图表：`acq_reference_validation_scatter.png`

数据明细：`mmwave_vs_reference_probes_60s.csv`、`breath_method_comparison_current.json`、`acq_reference_validation_summary.json`
""", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


