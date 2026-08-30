"""pre_30s 对齐窗口 + 完整 selector 链 HR 重跑试跑（sub-97793）。

复用 producer 的完整 selector 链（自动选 bin/channel + spectral + 谐波折叠 +
time/frequency fusion）和 targeted_validation 的 block-local ECG affine 对齐。
两个估计器时长：30s 全程 + 25s 末尾段。仅下游 audit，不写 producer 输出、不
用 ECG 选 target。

用法：
    .venv_t0/Scripts/python.exe scripts/maintenance/run_mmwave_pre30s_selector_hr_20260831.py
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import numpy as np

ALGO_ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ALGO_ROOT / "scripts" / "process_vital_signs_v3_1_1.py"
TARGETED = ALGO_ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py"
DATA_ROOT = Path(r"D:\acq_mmwave_data")
SUBJECTS = ("97793", "9779", "97795")
FS = 100.0
PRE_WINDOW_MS = 30_000
COURSE_S = 25.0


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    return {
        "selector_bpm": selected,
        "selector_time_bpm": time_bpm,
        "selector_time_harmonic_folded": time_folded,
        "selector_fused_bpm": fused,
        "selector_confidence": confidence,
        "selector_next_previous_bpm": next_previous,
        "selector_n_peaks": int(len(peaks)),
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


def run_subject(algo, target, subject: str) -> list[dict]:
    timestamps = target.load_mmwave_timestamps(subject)
    events = target.load_events(subject)
    physical, _ = target.decode_biopac_markers(subject)
    blocks, alignment = target.block_intervals(subject, timestamps, events, physical)
    reader = target.PartReader(subject)
    ecg, rsp, ecg_fs = target.load_ecg_reference(subject)

    block_map = {b["block_id"]: b for b in blocks}
    align_map = {r["block_id"]: r for r in alignment}

    probes = load_probe_onsets(subject)
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
        i0 = int(np.searchsorted(timestamps[:, 2], win_start, side="left"))
        i1 = int(np.searchsorted(timestamps[:, 2], win_end, side="right"))
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
        step30 = selector_step(algo, heartbeat, previous)
        n25 = int(COURSE_S * FS)
        step25 = selector_step(algo, heartbeat[-n25:], previous) if len(heartbeat) >= n25 else None

        phi_br = np.unwrap(np.angle(iq_fd[:, br_bin, br_ch]))
        disp_br = algo.WAVELENGTH_MM * phi_br / (4 * np.pi)
        _, br_freq, _, _ = algo._select_breath_candidate(disp_br)
        br_bpm = br_freq * 60.0 if br_freq is not None else None

        ref = target.ecg_rsp_window(ecg, rsp, ecg_fs, ecg_i0, ecg_i1) if ecg_i0 is not None else {}
        ecg_hr = ref.get("ecg_hr_bpm")

        rows.append({
            "subject": subject,
            "block_id": block_id,
            "probe_onset_unix_ms": onset,
            "win_start_unix_ms": win_start,
            "win_end_unix_ms": win_end,
            "win_s": round((win_end - win_start) / 1000.0, 3),
            "mmwave_frames": i1 - i0,
            "hr_bin": hr_bin,
            "hr_channel": hr_ch,
            "ecg_hr_bpm": ecg_hr,
            "hr_30s_fused_bpm": step30["selector_fused_bpm"],
            "hr_25s_fused_bpm": step25["selector_fused_bpm"] if step25 else None,
            "hr_30s_spectral_bpm": step30["selector_bpm"],
            "hr_25s_spectral_bpm": step25["selector_bpm"] if step25 else None,
            "time_harmonic_folded_30s": step30["selector_time_harmonic_folded"],
            "time_harmonic_folded_25s": step25["selector_time_harmonic_folded"] if step25 else None,
            "br_bpm": round(br_bpm, 3) if br_bpm is not None else None,
            "rsp_br_bpm": ref.get("rsp_br_bpm"),
            "ecg_status": ref.get("ecg_status"),
        })
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
    algo = load_module(PRODUCER, "producer_pre30s")
    target = load_module(TARGETED, "targeted_pre30s")

    out = Path(r"D:\Project\厚粲杯\11_数据\derived\mmwave_pre30s_selector_hr_20260831")
    out.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    for subject in SUBJECTS:
        rows = run_subject(algo, target, subject)
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
