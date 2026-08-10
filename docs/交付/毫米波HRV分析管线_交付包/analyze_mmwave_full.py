"""
analyze_mmwave_full.py — sub-001 全程毫米波 × 行为联合分析
================================================================
目的: 全程（含 practice + 6 block + 5 rest）时间线上毫米波特征
      （HR/BR/HRV）与行为表现（反应时/错误率）的对应关系；
      探针前 30s 窗口的特征 × 探针标签（专注/干扰/走神/空白），
      为"毫米波专注状态系统"的特征筛选提供探索性证据。

数据: F:/sub-001_/（mmwave npz 分片 + beh CSV + master_timeline）
方法: 复用 analyze_rest_hrv 的窗级自适应选 bin（v1.2 多 bin 交叉验证）,
      30s 无重叠窗覆盖 mmwave 全程。

用法:
  cd 08_算法/scripts
  python analyze_mmwave_full.py --subject 001

输出:
  output/08_SUB{XXX}-FULL/
    sub{XXX}_full_windows.json    ← 全程窗特征 + 行为
    sub{XXX}_probe_features.json  ← 探针前 30s 特征
    sub{XXX}_full_timeline.png    ← 时间线图（毫米波 × 行为）
    sub{XXX}_probe_compare.png    ← 探针标签特征对比

依赖: numpy, scipy, matplotlib, vmdpy
"""

import os
import sys
import csv
import json
import glob
import time as time_mod
from pathlib import Path

import numpy as np
from scipy import signal, stats

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from analyze_mmwave_hrv import (
    FS, N_CH, load_timestamps, load_frames, analyze_window_auto,
    parse_rest_segments, analyze_window, _sos_bandpass,
    estimate_freq_periodogram, HR_MIN, HR_MAX, detect_motion_frames,
)
from analyze_rest_3min import select_bins_from_profile
import analyze_mmwave_hrv as rhrv  # 用于设置模块级 FIRST_FRAME/N_PARTITIONS

# ============================================================
# 配置
# ============================================================

SUBJECT = "001"
DATA_ROOT = Path("E:")  # 数据根目录（原 F: 盘数据已迁移至 E: 根目录）,
                        # 预实验数据传 E:\预实验（--data-root 覆盖）
MMWAVE_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "mmwave"
BEH_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "beh"
OUTPUT_DIR = Path(rf"output\08_SUB{SUBJECT}-FULL")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SEC = 30        # 全程时间线窗长（秒），30s 保证 HR/BR 稳定, HRV 仅报告时域
PROBE_BEFORE_MS = 30_000   # 探针前特征窗（毫秒）
PROBE_RT_N = 5             # 探针前最近 N 个 go 试次的行为特征
PROBE_LABELS = {"1": "专注", "2": "任务相关干扰", "3": "走神", "4": "大脑空白"}


# ============================================================
# 行为数据加载
# ============================================================

def load_beh_trials():
    """合并 6 个 block 行为 CSV 为试次列表。

    Returns:
        list[dict]: 每试次含 onset_ms / rt / correct / is_probe /
                    probe_response / probe_onset_ms
    """
    trials = []
    for fpath in sorted(BEH_DIR.glob(f"sub-{SUBJECT}_Block*_beh.csv")):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                t = {
                    "onset_ms": int(float(row["absolute_onset_time"])),
                    "rt": float(row["rt"]) if row["rt"] else None,
                    "correct": int(row["correct"]),
                    "is_probe": row["is_probe"] == "1",
                }
                if t["is_probe"] and row["probe_response"]:
                    t["probe_response"] = row["probe_response"]
                    t["probe_onset_ms"] = int(float(row["probe_onset_time"]))
                trials.append(t)
    return trials


def select_bins_full_session(frame_idx, py_ms, t_start_ms, t_end_ms, n_win, excluded):
    """全程选 bin（REST-3min 式: 长数据全谱, SNR 高, 选最干净路径）。

    均匀抽样 ~18 段 × 20s 拼接为样本（避免加载全程 27 万帧），
    累积功率 + 窄带一致性校验全谱找最优呼吸/心跳 (ch, bin)。
    不受距离门控限制（含墙反射多径路径, 与 REST-3min 一致）。

    Returns:
        (br_ch, br_bin, hr_ch, hr_bin) 或 None（无合格候选）
    """
    sample_chunks = []
    for k in range(0, n_win, 5):
        t0 = t_start_ms + k * WINDOW_SEC * 1000
        t1 = t0 + 20_000
        if any(t0 < e1 and t1 > e0 for e0, e1 in excluded):
            continue
        fa = max(int(np.searchsorted(py_ms, t0)), 0)
        fb = min(int(np.searchsorted(py_ms, t1)), len(frame_idx) - 1)
        if fb - fa < 500:
            continue
        try:
            sample_chunks.append(load_frames(int(frame_idx[fa]), int(frame_idx[fb])))
        except IndexError:
            continue
    if not sample_chunks:
        return None
    iq_sample = np.concatenate(sample_chunks)
    bin_power_acc = np.mean(np.abs(iq_sample) ** 2, axis=0)  # (256, 8) 平均功率
    best_ch = int(np.argmax(np.mean(bin_power_acc, axis=0)))
    try:
        br_ch, br_bin, hr_ch, hr_bin, _ = select_bins_from_profile(
            bin_power_acc, best_ch, iq_sample, iq_sample.shape[0])
    except RuntimeError:
        return None
    return br_ch, br_bin, hr_ch, hr_bin


def analyze_fixed_bin(iq, hr_ch, hr_bin, br_ch, br_bin, method="vmd_heart"):
    """用全程选定的固定 bin 分析单窗（不再每窗重新选 bin）。

    窗内 bp 主频作锚定（防 VMD 倍频漂移），主频或逐拍 HR 不在
    生理范围则返回 None（该窗不可信）。附加动作帧检测。
    """
    # 动作帧占比过高 → 不可信
    _, motion_ratio = detect_motion_frames(iq)
    if motion_ratio > rhrv.MOTION_RATIO_MAX:
        return None
    disp_br = np.unwrap(np.angle(iq[:, br_bin, br_ch]))
    disp_hr = np.unwrap(np.angle(iq[:, hr_bin, hr_ch]))
    heart_bp = _sos_bandpass(disp_hr, 0.8, 2.5)
    hr_freq = estimate_freq_periodogram(heart_bp, 0.8, 2.5)
    if hr_freq is None or not (0.5 <= hr_freq <= 2.0):
        return None
    res = analyze_window(disp_br, disp_hr, method=method, hr_freq_hint=hr_freq)
    hr_t = res.get("hr_time_bpm")
    if hr_t is None or not (HR_MIN <= hr_t <= HR_MAX):
        return None
    res["quality"] = "ok"
    res["motion_ratio"] = round(motion_ratio, 3)
    return res


def window_behavior(trials, t0_ms, t1_ms):
    """聚合落在 [t0_ms, t1_ms) 内试次的行为指标。

    返回 dict: n_trials / n_err / rt_mean / rt_sd；无试次时 rt 为 None。
    """
    in_win = [t for t in trials if t0_ms <= t["onset_ms"] < t1_ms]
    if not in_win:
        return {"n_trials": 0, "n_err": 0, "rt_mean": None, "rt_sd": None}
    rts = [t["rt"] for t in in_win if t["rt"] is not None]
    return {
        "n_trials": len(in_win),
        "n_err": sum(1 for t in in_win if not t["correct"]),
        "rt_mean": round(float(np.mean(rts)), 1) if rts else None,
        "rt_sd": round(float(np.std(rts)), 1) if len(rts) > 1 else None,
    }


# ============================================================
# 主流程
# ============================================================

def main():
    global SUBJECT, DATA_ROOT, MMWAVE_DIR, BEH_DIR, OUTPUT_DIR
    import argparse
    parser = argparse.ArgumentParser(description="全程毫米波×行为联合分析")
    parser.add_argument("--subject", type=str, default="001")
    parser.add_argument("--exclude-rest", action="store_true",
                        help="排除休息段（被试休息时不在座位, 数据为空场景）")
    parser.add_argument("--data-root", type=str, default=str(DATA_ROOT),
                        help="数据根目录, 默认 E:（旧数据 E:\\sub-XXX_）; 预实验传 E:\\预实验")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="输出目录名（相对 output/）, 默认 08_SUB{SUBJECT}-FULL; "
                             "预实验传 09_PREEXP-SUB{SUBJECT}-FULL 避免覆盖旧分析")
    args = parser.parse_args()

    SUBJECT = args.subject.zfill(3)
    DATA_ROOT = Path(args.data_root)
    MMWAVE_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "mmwave"
    BEH_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "beh"
    out_name = args.output_dir or f"08_SUB{SUBJECT}-FULL"
    OUTPUT_DIR = Path(rf"output\{out_name}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    t_all = time_mod.time()
    print("=" * 60)
    print(f"  sub-{SUBJECT} 全程毫米波 × 行为联合分析")
    print("=" * 60)

    # ── 1. 加载时间戳与行为 ──
    # 同步被导入模块的数据路径（load_timestamps/load_frames 在 rhrv 模块内执行）
    rhrv.SUBJECT = SUBJECT
    rhrv.DATA_ROOT = DATA_ROOT
    rhrv.MMWAVE_DIR = DATA_ROOT / f"sub-{SUBJECT}_" / "mmwave"
    rhrv.BEH_TIMELINE = DATA_ROOT / f"sub-{SUBJECT}_" / "beh" / "master_timeline.csv"
    frame_idx, py_ms = load_timestamps()
    # 设置被导入模块的全局量（load_frames 依赖首帧号与片数）
    rhrv.FIRST_FRAME = int(frame_idx[0])
    rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK  # 向上取整, 含尾片
    trials = load_beh_trials()
    n_probe = sum(1 for t in trials if t.get("probe_response"))
    print(f"[1/5] 帧 {frame_idx[0]}-{frame_idx[-1]} ({len(frame_idx)} 帧), "
          f"试次 {len(trials)}, 探针 {n_probe}")

    # 全程时间范围（mmwave 数据覆盖范围）
    t_start_ms = int(py_ms[0])
    t_end_ms = int(py_ms[-1])
    n_win = int((t_end_ms - t_start_ms) / (WINDOW_SEC * 1000))

    # 排除休息段时间范围（被试不在座位, 空场景数据无效）
    excluded = []
    if args.exclude_rest:
        for seg in parse_rest_segments():
            excluded.append((seg["t0_ms"], seg["t1_ms"]))
        rest_labels = [seg["label"] for seg in parse_rest_segments()]
        print(f"  排除休息段 {len(excluded)} 段: {rest_labels}")

    # ── 2. 全程 30s 窗特征（窗级自适应 + 段参考, 与探针窗一致） ──
    # v1.3: 废弃"全程选 bin 固定检测"（select_bins_from_profile 无距离门控,
    # SXQ 实测选到 bin253=9.4m 环境反射）; 统一用窗级自适应（含距离门控）
    print(f"[2/5] 全程 {WINDOW_SEC}s 窗 × {n_win} 窗（第一遍正常检测）...")
    windows = []
    n_excluded = 0
    for k in range(n_win):
        t0 = t_start_ms + k * WINDOW_SEC * 1000
        t1 = t0 + WINDOW_SEC * 1000
        # 与休息段重叠 → 跳过
        if any(t0 < e1 and t1 > e0 for e0, e1 in excluded):
            n_excluded += 1
            continue
        fa = int(np.searchsorted(py_ms, t0))
        fb = int(np.searchsorted(py_ms, t1))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        iq = load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
        win_res = analyze_window_auto(iq, method="vmd_heart")
        beh = window_behavior(trials, t0, t1)
        row = {"t_start_s": round((t0 - t_start_ms) / 1000),
               "t_end_s": round((t1 - t_start_ms) / 1000)}
        if win_res is None:
            row["quality"] = "poor"
        else:
            row["quality"] = "ok"
            row["hr_bpm"] = win_res[0].get("hr_time_bpm")
            row["br_bpm"] = win_res[0].get("br_freq_bpm")
            hrv = win_res[0].get("hrv", {})
            row["sdnn_ms"] = hrv.get("SDNN_ms")
            row["rmssd_ms"] = hrv.get("RMSSD_ms")
            row["heart_bin"] = win_res[1]["bin"]
        row.update(beh)
        windows.append(row)

    # 段参考修正: 全程窗统一用被试级 HR 中位数纠正倍频锁定（与探针窗一致）
    ref_hrs_w = [w["hr_bpm"] for w in windows
                 if w["quality"] == "ok" and w.get("hr_bpm")]
    med_hr_w = float(np.median(ref_hrs_w)) if ref_hrs_w else None
    n_w_corrected = 0
    for k in range(len(windows)):
        w = windows[k]
        if w["quality"] == "ok" or med_hr_w is None:
            continue
        t0 = t_start_ms + w["t_start_s"] * 1000
        t1 = t0 + WINDOW_SEC * 1000
        fa = int(np.searchsorted(py_ms, t0))
        fb = int(np.searchsorted(py_ms, t1))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        iq = load_frames(int(frame_idx[fa]), int(frame_idx[fb]))
        res = analyze_window_auto(iq, method="vmd_heart", med_hr_hint=med_hr_w)
        if res is not None:
            w["quality"] = "ok"
            w["hr_bpm"] = res[0].get("hr_time_bpm")
            w["br_bpm"] = res[0].get("br_freq_bpm")
            hrv = res[0].get("hrv", {})
            w["sdnn_ms"] = hrv.get("SDNN_ms")
            w["rmssd_ms"] = hrv.get("RMSSD_ms")
            w["heart_bin"] = res[1]["bin"]
            w["harmonics_corrected"] = True
            n_w_corrected += 1
    print(f"  可信窗: {sum(1 for w in windows if w['quality'] == 'ok')}/{len(windows)}"
          f"（段参考修正救回 {n_w_corrected} 窗）")

    # ── 4. 探针前 30s 特征（窗级自适应 + 段参考修正） ──
    print(f"[4/5] 探针前 {PROBE_BEFORE_MS // 1000}s 窗特征（两遍: 正常 → 段参考修正）...")

    def load_probe_window(t):
        p0 = t["probe_onset_ms"] - PROBE_BEFORE_MS
        p1 = t["probe_onset_ms"]
        fa = int(np.searchsorted(py_ms, p0))
        fb = int(np.searchsorted(py_ms, p1))
        fa, fb = min(max(fa, 0), len(frame_idx) - 1), min(fb, len(frame_idx) - 1)
        if fb - fa < 1000:  # 少于 ~10s 数据则跳过
            return None
        return load_frames(int(frame_idx[fa]), int(frame_idx[fb]))

    probes = [t for t in trials if t.get("probe_response")]
    # 第一遍: 正常检测, 收集可信 HR 作被试级参考
    pass1 = []
    for t in probes:
        iq = load_probe_window(t)
        if iq is None:
            pass1.append(None)
            continue
        res = analyze_window_auto(iq, method="vmd_heart")
        pass1.append(res)
    ref_hrs = [r[0].get("hr_time_bpm") for r in pass1
               if r is not None and r[0].get("hr_time_bpm")]
    med_hr = float(np.median(ref_hrs)) if ref_hrs else None
    print(f"  被试参考 HR 中位数: {med_hr} bpm (n={len(ref_hrs)})")

    # 第二遍: poor 窗用段参考重试（倍频锁定修正, 生理约束: 心率不瞬间翻倍）
    probe_rows = []
    n_corrected = 0
    for t, r1 in zip(probes, pass1):
        iq = load_probe_window(t)
        row = {"probe_id": len(probe_rows) + 1,
               "label": t["probe_response"],
               "label_name": PROBE_LABELS.get(t["probe_response"], "?")}
        prior_go = [x for x in trials
                    if x["onset_ms"] < t["probe_onset_ms"] and x["rt"] is not None and not x["is_probe"]][-PROBE_RT_N:]
        row["prior_rt_mean"] = round(float(np.mean([x["rt"] for x in prior_go])), 1) if prior_go else None
        row["prior_n_err"] = sum(1 for x in prior_go if not x["correct"])
        if iq is None:
            row["quality"] = "poor"
        else:
            win_res = r1
            if win_res is None and med_hr is not None:
                win_res = analyze_window_auto(iq, method="vmd_heart",
                                              med_hr_hint=med_hr)
                if win_res is not None:
                    n_corrected += 1
            if win_res is None:
                row["quality"] = "poor"
            else:
                row["quality"] = "ok"
                row["hr_bpm"] = win_res[0].get("hr_time_bpm")
                row["br_bpm"] = win_res[0].get("br_freq_bpm")
                hrv = win_res[0].get("hrv", {})
                row["sdnn_ms"] = hrv.get("SDNN_ms")
                row["rmssd_ms"] = hrv.get("RMSSD_ms")
                row["lf_hf"] = hrv.get("frequency", {}).get("LF_HF") if hrv else None
                row["harmonics_corrected"] = win_res[0].get("harmonics_corrected", False)
        probe_rows.append(row)
    print(f"  段参考修正救回: {n_corrected} 窗")

    n_pok = sum(1 for p in probe_rows if p["quality"] == "ok")
    print(f"  可信探针窗: {n_pok}/{len(probe_rows)}")

    # ── 4. 行为 × 毫米波相关（全程窗） ──
    print(f"[4/5] 行为 × 毫米波相关（可信窗）...")
    ok_w = [w for w in windows if w["quality"] == "ok" and w["rt_mean"] is not None]
    corrs = {}
    for m1, m2 in [("hr_bpm", "rt_mean"), ("hr_bpm", "rt_sd"),
                   ("sdnn_ms", "rt_mean"), ("rmssd_ms", "rt_mean"),
                   ("br_bpm", "rt_mean"), ("sdnn_ms", "n_err")]:
        pairs = [(w[m1], w[m2]) for w in ok_w
                 if w.get(m1) is not None and w.get(m2) is not None]
        if len(pairs) >= 10:
            r, p = stats.pearsonr([p[0] for p in pairs], [p[1] for p in pairs])
            corrs[f"{m1}~{m2}"] = {"r": round(r, 3), "p": round(p, 4), "n": len(pairs)}
    for k, v in corrs.items():
        print(f"  {k}: r={v['r']}, p={v['p']}, n={v['n']}")

    # ── 5. 保存 + 绘图 ──
    json.dump({"windows": windows, "probes": probe_rows, "correlations": corrs},
              open(OUTPUT_DIR / f"sub{SUBJECT}_full_windows.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"[5/5] 保存完成, 耗时 {time_mod.time() - t_all:.0f}s")

    plot_timeline(windows, OUTPUT_DIR / f"sub{SUBJECT}_full_timeline.png")
    plot_probe_compare(probe_rows, OUTPUT_DIR / f"sub{SUBJECT}_probe_compare.png")


# ============================================================
# 绘图
# ============================================================

def plot_timeline(windows, png_path):
    """4 面板全程时间线: HR / BR / HRV / 行为（RT 与错误）。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    ok = [w for w in windows if w["quality"] == "ok"]
    ts = [(w["t_start_s"] + w["t_end_s"]) / 2 / 60 for w in ok]  # 分钟
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

    for ax, key, ylab, color, title in [
        (axes[0], "hr_bpm", "HR (bpm)", "red", "心率"),
        (axes[1], "br_bpm", "BR (bpm)", "green", "呼吸率"),
        (axes[2], "sdnn_ms", "SDNN (ms)", "blue", "HRV 时域"),
    ]:
        vals = [w[key] for w in ok if w.get(key) is not None]
        t_valid = [t for t, w in zip(ts, ok) if w.get(key) is not None]
        ax.plot(t_valid, vals, ".-", color=color, alpha=0.7, markersize=3)
        ax.set_ylabel(ylab)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

    # 行为: RT 均值 + 错误
    ax = axes[3]
    rt_ok = [(t, w["rt_mean"]) for t, w in zip(ts, ok) if w.get("rt_mean") is not None]
    if rt_ok:
        ax.plot([t for t, _ in rt_ok], [r for _, r in rt_ok], ".-", color="purple",
                alpha=0.7, markersize=3, label="RT 均值 (ms)")
    ax.set_xlabel("时间 (分钟)")
    ax.set_ylabel("RT (ms)")
    ax.set_title("行为: 反应时")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.suptitle(f"sub-{SUBJECT} 全程毫米波 × 行为时间线（30s 窗）", fontsize=14)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  [png] {png_path}")


def plot_probe_compare(probe_rows, png_path):
    """探针 4 类标签下的特征对比（HR / RT），样本少, 仅作描述。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
    plt.rcParams["axes.unicode_minus"] = False

    ok = [p for p in probe_rows if p["quality"] == "ok"]
    if not ok:
        return
    labels = sorted({p["label"] for p in ok}, key=lambda x: int(x))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    for ax, key, ylab in [
        (axes[0], "hr_bpm", "HR (bpm)"),
        (axes[1], "prior_rt_mean", "探针前 RT 均值 (ms)"),
    ]:
        for lab in labels:
            vals = [p[key] for p in ok if p["label"] == lab and p.get(key) is not None]
            if vals:
                ax.scatter([PROBE_LABELS[lab]] * len(vals), vals, alpha=0.6, s=40)
                ax.plot([PROBE_LABELS[lab]], [np.mean(vals)], "D", color="red", markersize=7)
        ax.set_ylabel(ylab)
        ax.set_title(ylab)
        ax.grid(True, alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=15)

    fig.suptitle(f"sub-{SUBJECT} 探针标签 × 特征（可信窗 n={len(ok)}）", fontsize=13)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  [png] {png_path}")


if __name__ == '__main__':
    main()
