"""pre_30s 对齐窗口 + 完整 selector 链 HR 重跑（6 场次扩样，08-31）。

复用 producer 的完整 selector 链（自动选 bin/channel + spectral + 谐波折叠 +
time/frequency fusion）和 targeted_validation 的 block-local ECG affine 对齐。
两个估计器时长：30s 全程 + 25s 末尾段。仅下游 audit，不写 producer 输出、不
用 ECG 选 target。

场次：97793 / 9779 / 97795（原 3 场次）+ 97792 / 97796 / 97794（扩样）。
命名坑：97795 的 acq 误写 97995.acq、97794 目录及目录内文件前缀误用 97994，
映射见 ACQ_FILE_OVERRIDES / FILE_KEY_OVERRIDES。97792 无正式 block 行为数据
（仅 baseline+practice），判 not_estimable 跳过。

用法：
    .venv_t0/Scripts/python.exe scripts/maintenance/run_mmwave_pre30s_selector_hr_20260831.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ALGO_ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
TARGETED = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
DATA_ROOT = Path(r"D:\acq_mmwave_data")
SUBJECTS = ("97793", "9779", "97795", "97792", "97796", "97794")
FS = 100.0
PRE_WINDOW_MS = 30_000
COURSE_S = 25.0
ALIGNMENT_TIMESTAMP_SOURCE = "dll_host_receive"
ALIGNMENT_TIMESTAMP_COLUMN = 1
PYTHON_PROCESS_TIMESTAMP_COLUMN = 2

# ---- 场次命名坑映射（08-16 现场日志口径，08-31 扩样只读复核确认） ----
# 97795：目录 sub-97795_ 正确，acq 文件名误写 97995.acq（目录内唯一 acq，glob 本可命中，显式映射更稳）。
# 97794：目录 sub-97994_ 及目录内 beh/mmwave 文件名前缀均为 97994（acq 文件名 97794.acq 正确）。
#        口径统一为场次 97794；调用 target 模块读文件时用文件主体 97994，输出行的 subject 写回 97794。
ACQ_FILE_OVERRIDES = {"97795": "97995.acq"}
FILE_KEY_OVERRIDES = {"97794": "97994"}


def install_target_overrides(target) -> None:
    """给 targeted 模块装命名坑映射（仅内存 patch，不改任何文件）。

    target 模块的 session_dir/PartReader 等按 f"sub-{subject}_" 拼路径，
    对 97794 需改用文件主体 97994（由调用点翻译，见 run_subject）；本函数
    只 patch acq_path：97795 显式取 97995.acq，其余保持 glob 原逻辑。
    """
    orig_acq_path = target.acq_path

    def acq_path(subject: str) -> Path:
        override = ACQ_FILE_OVERRIDES.get(subject)
        if override:
            path = target.session_dir(subject) / override
            if not path.exists():
                raise FileNotFoundError(f"Override acq missing: {path}")
            return path
        return orig_acq_path(subject)

    target.acq_path = acq_path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def alignment_timestamps(timestamps: np.ndarray) -> np.ndarray:
    """Return the formal DLL host-receive clock; never fall back to Python time."""
    values = np.asarray(timestamps)
    if values.ndim != 2 or values.shape[1] <= ALIGNMENT_TIMESTAMP_COLUMN:
        raise ValueError("DLL host receive timestamp column is required")
    result = values[:, ALIGNMENT_TIMESTAMP_COLUMN].astype(np.int64)
    if len(result) == 0 or np.any(result <= 0) or np.any(np.diff(result) < 0):
        raise ValueError("DLL host receive timestamps are invalid or nonmonotonic")
    return result


def selector_step(algo, heartbeat: np.ndarray, previous_bpm: float | None) -> dict:
    """完整 selector 链：time + harmonic fold + spectral + fusion（复用 producer 现有方法）。"""
    peaks = np.asarray(algo.detect_peaks_heart_lo(heartbeat, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM), dtype=int)
    anchor = previous_bpm
    time_bpm, time_quality = algo._robust_time_bpm(peaks / float(FS), anchor)
    time_bpm, time_folded = algo._fold_harmonic(time_bpm, anchor, algo.HR_LO_BPM, algo.HR_HI_BPM)
    if time_folded:
        time_quality *= 0.85
    selected, frequency_quality = algo._select_spectral_bpm(
        heartbeat, FS, algo.HR_LO_BPM, algo.HR_HI_BPM, time_bpm, previous_bpm, None
    )
    if time_bpm is not None and selected is not None:
        gap = abs(time_bpm - selected)
        agreement = float(np.exp(-gap / 12.0))
        wt, wf = max(0.05, time_quality), max(0.05, frequency_quality)
        if gap <= algo.HR_TIME_FREQ_WARNING_BPM:
            fused = (wt * time_bpm + wf * selected) / (wt + wf)
            confidence = agreement * np.sqrt(time_quality * frequency_quality)
        else:
            fused = time_bpm if (anchor is None or abs(time_bpm - anchor) <= abs(selected - anchor)) else selected
            confidence = 0.10 * (time_quality if fused == time_bpm else frequency_quality) * agreement
    elif time_bpm is not None:
        fused, confidence = time_bpm, 0.45 * time_quality
    elif selected is not None:
        fused, confidence = selected, 0.35 * frequency_quality
    else:
        fused, confidence = None, 0.0
    next_previous = previous_bpm
    if fused is not None and (previous_bpm is None or confidence >= 0.12):
        next_previous = float(fused) if previous_bpm is None else 0.8 * float(previous_bpm) + 0.2 * float(fused)
    # Audit the current producer course QC without changing the frozen B2 HR outputs.
    course = algo.estimate_hr_time_course(
        heartbeat=heartbeat,
        peaks=peaks,
        fs=FS,
        reference_bpm=None,
        window_s=COURSE_S,
        step_s=5.0,
    )
    course_confidence = [float(point.get("confidence", 0.0)) for point in course.get("points", [])]
    return {
        "selector_bpm": selected,
        "selector_time_bpm": time_bpm,
        "selector_time_harmonic_folded": time_folded,
        "selector_fused_bpm": fused,
        "selector_confidence": confidence,
        "selector_next_previous_bpm": next_previous,
        "selector_n_peaks": int(len(peaks)),
        "course_mean_confidence": float(np.mean(course_confidence)) if course_confidence else None,
        "course_usable_ratio": course.get("signal_quality", {}).get("usable_ratio"),
        "course_json": course,
    }


def restoration_step(algo, heartbeat: np.ndarray) -> dict:
    """Run only the P0-approved existing downstream restoration bundle."""
    peaks = np.asarray(
        algo.detect_peaks_heart_lo(heartbeat, lo_bpm=algo.HR_LO_BPM, hi_bpm=algo.HR_HI_BPM),
        dtype=int,
    )
    base_freq_hz = algo.estimate_freq_periodogram(heartbeat, algo.HR_LO_HZ, algo.HR_HI_HZ)
    base_freq_bpm = round(float(base_freq_hz * 60.0), 1) if base_freq_hz is not None else None
    global_time_bpm = round(float(60.0 * FS / np.mean(np.diff(peaks))), 1) if len(peaks) >= 2 else None

    segment = algo._heart_segment_reference_correction(
        heartbeat=heartbeat,
        hp=peaks,
        base_freq_bpm=base_freq_bpm,
        ext_br_bpm=None,
    )
    periodogram_bpm = segment.get("corrected_freq_bpm", base_freq_bpm)
    consensus_bpm, consensus_time_bpm, consensus = algo._heart_window_consensus_bpm(
        seg_corr=segment,
        hr_freq_bpm_periodogram=periodogram_bpm,
        hr_time_bpm_global=global_time_bpm,
    )
    course = algo.estimate_hr_time_course(
        heartbeat=heartbeat,
        peaks=peaks,
        fs=FS,
        reference_bpm=consensus_bpm,
        window_s=COURSE_S,
        step_s=5.0,
    )
    quality = course.get("signal_quality", {})
    gate_passed = bool(quality.get("hard_gate_passed", False))
    pre_gate = {
        "spectral_bpm": course.get("freq_median_bpm"),
        "time_bpm": course.get("time_median_bpm"),
        "fused_bpm": course.get("fused_median_bpm"),
    }
    confidence = [float(point.get("confidence", 0.0)) for point in course.get("points", [])]
    return {
        **{key: value if gate_passed else None for key, value in pre_gate.items()},
        "pre_gate": pre_gate,
        "confidence": float(np.mean(confidence)) if confidence else None,
        "usable_ratio": quality.get("usable_ratio"),
        "gate_hit": not gate_passed,
        "gate_reason": None if gate_passed else "usable_ratio_below_0.50",
        "status": "ESTIMATED" if gate_passed else "QC_FAIL_SIGNAL_QUALITY",
        "reference_bpm": consensus_bpm,
        "consensus_time_bpm": consensus_time_bpm,
        "base_freq_bpm": base_freq_bpm,
        "global_time_bpm": global_time_bpm,
        "segment": segment,
        "consensus": consensus,
        "course": course,
        "n_peaks": int(len(peaks)),
    }


def load_probe_onsets(subject: str) -> list[dict]:
    probes: list[dict] = []
    beh_dir = DATA_ROOT / f"sub-{subject}_" / "beh"
    for block_num in (1, 2, 3, 4):
        candidates = sorted(beh_dir.glob(f"sub-{subject}_Block{block_num}_*_beh.csv"))
        if not candidates:
            continue
        path = candidates[0]
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("is_probe", "")).strip().lower() in ("1", "true"):
                    onset = row.get("probe_onset_time")
                    if onset:
                        probes.append({"block_id": f"block{block_num}", "probe_onset_unix_ms": int(float(onset))})
    return probes


def run_subject(algo, target, subject: str, arm: str) -> list[dict]:
    # 97794 的目录/文件前缀误用 97994，读文件时用文件主体 key；输出行 subject 保持 97794
    file_key = FILE_KEY_OVERRIDES.get(subject, subject)
    probes = load_probe_onsets(file_key)
    if not probes:
        # not_estimable：无 probe 窗口（97792 仅 baseline+practice，beh 无 Block CSV 且
        # events.csv 无 block1-4 段事件）。不读 acq、不切 mmWave 帧，直接跳过。
        print(f"[NOT_ESTIMABLE] {subject}: 无 probe 窗口（beh Block CSV 或 events.csv 正式 block 缺失），跳过")
        return []
    timestamps = target.load_mmwave_timestamps(file_key)
    events = target.load_events(file_key)
    physical, _ = target.decode_biopac_markers(file_key)
    blocks, alignment = target.block_intervals(file_key, timestamps, events, physical)
    reader = target.PartReader(file_key)
    ecg, rsp, ecg_fs = target.load_ecg_reference(file_key)

    block_map = {b["block_id"]: b for b in blocks}
    align_map = {r["block_id"]: r for r in alignment}

    previous_by_block: dict[str, float | None] = {}
    rows: list[dict] = []

    for probe in probes:
        block_id = probe["block_id"]
        block = block_map.get(block_id)
        if block is None or block["status"] != "complete":
            continue
        onset = probe["probe_onset_unix_ms"]
        win_start = max(onset - PRE_WINDOW_MS, int(block["start_event_unix_ms"]))
        win_end = onset
        if win_end - win_start < int(10 * 1000):
            continue
        # Formal cutover: select radar frames by DLL host receive time in the
        # right-open physiological interval [win_start, probe_onset).  The
        # Python processing timestamp remains available only for QC elsewhere.
        frame_time = alignment_timestamps(timestamps)
        i0 = int(np.searchsorted(frame_time, win_start, side="left"))
        i1 = int(np.searchsorted(frame_time, win_end, side="left"))
        if i1 - i0 < 200:
            continue

        align = align_map.get(block_id, {})
        slope = align.get("ecg_fit_slope_samples_per_ms")
        intercept = align.get("ecg_fit_intercept_sample")
        ecg_i0 = int(round(slope * win_start + intercept)) if slope is not None else None
        ecg_i1 = int(round(slope * win_end + intercept)) if slope is not None else None

        iq = reader.slice(i0, i1)
        iq_fd = algo._as_range_cube(iq)
        bin_power_acc = np.mean(np.abs(iq_fd) ** 2, axis=0)
        br_ch, br_bin, hr_ch, hr_bin, _ = algo.select_separate_channels_bins(bin_power_acc, iq_fd, iq_fd.shape[0])
        disp = algo.extract_displacement(iq_fd, hr_bin, hr_ch)
        heartbeat = algo._sos_bandpass(disp, algo.HR_LO_HZ, algo.HR_HI_HZ)

        previous = previous_by_block.get(block_id)
        step30 = selector_step(algo, heartbeat, previous) if arm == "control" else restoration_step(algo, heartbeat)
        n25 = int(COURSE_S * FS)
        step25 = selector_step(algo, heartbeat[-n25:], previous) if arm == "control" and len(heartbeat) >= n25 else None

        phi_br = np.unwrap(np.angle(iq_fd[:, br_bin, br_ch]))
        disp_br = algo.WAVELENGTH_MM * phi_br / (4 * np.pi)
        _, br_freq, _, _ = algo._select_breath_candidate(disp_br)
        br_bpm = br_freq * 60.0 if br_freq is not None else None

        phi_hr = np.unwrap(np.angle(iq_fd[:, hr_bin, hr_ch]))
        phase_stability, _ = algo._phase_stability_score(phi_hr)
        motion_proxy = float(np.std(np.diff(disp))) if len(disp) > 1 else None
        frame_ids = np.asarray(timestamps[i0:i1, 0], dtype="<i8")
        frame_index_sha256 = hashlib.sha256(frame_ids.tobytes()).hexdigest().upper()
        heartbeat_sha256 = hashlib.sha256(np.asarray(heartbeat, dtype="<f8").tobytes()).hexdigest().upper()

        ref = target.ecg_rsp_window(ecg, rsp, ecg_fs, ecg_i0, ecg_i1) if ecg_i0 is not None else {}
        ecg_hr = ref.get("ecg_hr_bpm")

        rows.append({
            "arm": arm,
            "subject": subject,
            "block_id": block_id,
            "probe_onset_unix_ms": onset,
            "win_start_unix_ms": win_start,
            "win_end_unix_ms": win_end,
            "win_s": round((win_end - win_start) / 1000.0, 3),
            "mmwave_frames": i1 - i0,
            "frame_i0": i0,
            "frame_i1_exclusive": i1,
            "frame_index_sha256": frame_index_sha256,
            "heartbeat_sha256": heartbeat_sha256,
            "alignment_timestamp_source": ALIGNMENT_TIMESTAMP_SOURCE,
            "alignment_timestamp_column": ALIGNMENT_TIMESTAMP_COLUMN,
            "hr_bin": hr_bin,
            "hr_channel": hr_ch,
            "hr_distance_proxy_m": round(float(hr_bin) * 0.037, 3),
            "br_bin": br_bin,
            "br_channel": br_ch,
            "ecg_hr_bpm": ecg_hr,
            "hr_30s_fused_bpm": step30["selector_fused_bpm"] if arm == "control" else step30["fused_bpm"],
            "hr_25s_fused_bpm": step25["selector_fused_bpm"] if step25 else None,
            "hr_30s_spectral_bpm": step30["selector_bpm"] if arm == "control" else step30["spectral_bpm"],
            "hr_25s_spectral_bpm": step25["selector_bpm"] if step25 else None,
            "hr_30s_time_bpm": step30["selector_time_bpm"] if arm == "control" else step30["time_bpm"],
            "hr_25s_time_bpm": step25["selector_time_bpm"] if step25 else None,
            "time_harmonic_folded_30s": step30["selector_time_harmonic_folded"] if arm == "control" else None,
            "time_harmonic_folded_25s": step25["selector_time_harmonic_folded"] if step25 else None,
            "hr_spectral_bpm_pre_gate": (
                step30["selector_bpm"] if arm == "control" else step30["pre_gate"]["spectral_bpm"]
            ),
            "hr_time_bpm_pre_gate": (
                step30["selector_time_bpm"] if arm == "control" else step30["pre_gate"]["time_bpm"]
            ),
            "hr_fused_bpm_pre_gate": (
                step30["selector_fused_bpm"] if arm == "control" else step30["pre_gate"]["fused_bpm"]
            ),
            "hr_confidence": step30["course_mean_confidence"] if arm == "control" else step30["confidence"],
            "hr_usable_ratio": (
                step30["course_usable_ratio"] if arm == "control" else step30["usable_ratio"]
            ),
            "gate_hit": False if arm == "control" else step30["gate_hit"],
            "gate_reason": None if arm == "control" else step30["gate_reason"],
            "hr_status": "ESTIMATED" if arm == "control" else step30["status"],
            "restoration_reference_bpm": None if arm == "control" else step30["reference_bpm"],
            "restoration_consensus_time_bpm": None if arm == "control" else step30["consensus_time_bpm"],
            "restoration_base_freq_bpm": None if arm == "control" else step30["base_freq_bpm"],
            "restoration_global_time_bpm": None if arm == "control" else step30["global_time_bpm"],
            "restoration_n_peaks": step30["selector_n_peaks"] if arm == "control" else step30["n_peaks"],
            "restoration_segment_json": None if arm == "control" else json.dumps(step30["segment"], ensure_ascii=False, sort_keys=True),
            "restoration_consensus_json": None if arm == "control" else json.dumps(step30["consensus"], ensure_ascii=False, sort_keys=True),
            "restoration_course_json": None if arm == "control" else json.dumps(step30["course"], ensure_ascii=False, sort_keys=True),
            "control_course_json": json.dumps(step30["course_json"], ensure_ascii=False, sort_keys=True) if arm == "control" else None,
            "br_bpm": round(br_bpm, 3) if br_bpm is not None else None,
            "phase_stability": round(phase_stability, 8) if phase_stability is not None else None,
            "motion_proxy": round(motion_proxy, 10) if motion_proxy is not None else None,
            "rsp_br_bpm": ref.get("rsp_br_bpm"),
            "ecg_status": ref.get("ecg_status"),
        })
        if arm == "control":
            previous_by_block[block_id] = step30["selector_next_previous_bpm"]

    return rows


def summarize(subject: str | None, rows: list[dict]) -> None:
    valid = [r for r in rows if r["ecg_hr_bpm"] is not None]
    label = f"sub-{subject}" if subject else "全部 subject"
    print(f"\n=== {label} pre_30s + 完整 selector 链 ===")
    print(f"总 probe 窗口: {len(rows)} | ECG 有效: {len(valid)}")
    for est_label, key in (("30s fused", "hr_30s_fused_bpm"), ("25s fused", "hr_25s_fused_bpm"), ("30s spectral", "hr_30s_spectral_bpm"), ("25s spectral", "hr_25s_spectral_bpm")):
        pairs = [(r["ecg_hr_bpm"], r[key]) for r in valid if r[key] is not None]
        if not pairs:
            print(f"{est_label}: 无可评估窗口")
            continue
        err = [abs(e - h) for e, h in pairs]
        ratio = [h / e for e, h in pairs if e > 0]
        half_locked = sum(1 for r in ratio if 0.42 <= r <= 0.58)
        bias = [h - e for e, h in pairs]
        print(f"{est_label}: n={len(pairs)} MAE={np.mean(err):.2f} medianAE={np.median(err):.2f} bias={np.mean(bias):+.2f} 锁半频={half_locked}/{len(pairs)} ({half_locked/len(pairs)*100:.0f}%)")
    br_pairs = [(r["rsp_br_bpm"], r["br_bpm"]) for r in valid if r.get("rsp_br_bpm") is not None and r.get("br_bpm") is not None]
    if br_pairs:
        br_err = [abs(e - b) for e, b in br_pairs]
        br_ratio = [b / e for e, b in br_pairs if e > 0]
        br_half = sum(1 for r in br_ratio if 0.42 <= r <= 0.58)
        print(f"BR: n={len(br_pairs)} MAE={np.mean(br_err):.2f} medianAE={np.median(br_err):.2f} 锁半频={br_half}/{len(br_pairs)} ({br_half/len(br_pairs)*100:.0f}%)")
    else:
        print("BR: 无可评估窗口")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New, task-specific directory; existing directories are protected.")
    parser.add_argument("--arm", choices=("control", "restoration"), default="control")
    args = parser.parse_args()
    algo = load_module(PRODUCER, "producer_pre30s")
    target = load_module(TARGETED, "targeted_pre30s")
    install_target_overrides(target)

    # Every clock rerun is isolated from the historical Python-time baseline.
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=False)

    all_rows: list[dict] = []
    for subject in SUBJECTS:
        rows = run_subject(algo, target, subject, args.arm)
        if not rows:
            continue  # not_estimable 场次已在 run_subject 打印原因，不写空 CSV
        summarize(subject, rows)
        all_rows.extend(rows)
        fields = sorted({k for r in rows for k in r})
        with (out / f"sub-{subject}_pre30s_selector_hr.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    summarize(None, all_rows)
    fields = sorted({k for r in all_rows for k in r})
    with (out / "all_subjects_pre30s_selector_hr.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n结果已写: {out}")


if __name__ == "__main__":
    main()
