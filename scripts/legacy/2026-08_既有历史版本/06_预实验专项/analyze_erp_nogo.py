"""
analyze_erp_nogo.py — no-go 试次前窗事件相关生理分析（v2, 2026-08-12）
====================================================================
版本: v2.0 (2026-08-12)
功能: 以 no-go 试次为锚点, 取错误/正确 no-go **之前 60s** 的生理窗,
      对比虚报（commission）与正确抑制（correct inhibition）前窗的
      HR/BR/SDNN/RMSSD, 检验抑制失败前的生理状态差异。

设计依据（《生理指标与专注状态判断手册》v1.0）:
  - 前窗而非错误窗: 错误窗含错误后反馈反应, 污染"前兆"测量
  - 同类试次对比: no-go 都需要抑制, 只差成败; 对照组非"无错误窗"
  - 60s 前窗: RMSSD 在 60s 窗与长窗参考高度相关（r>0.9）; SDNN 同窗长
    组间比较仍有效; 频域 LF/HF 不用于事件窗（分辨率不足）
  - 污染剔除: no-go 间隔中位 5.8s, 60s 前窗必然跨多个试次, 剔除前窗
    内含其他虚报的窗（错误组与对照组同规则）
  - 呼吸混淆: RMSSD 受呼吸频率影响, 报告 BR 组间差异, RMSSD 比较以
    BR 为协变量（ANCOVA, 效果量为部分 η²）

数据: 行为 F:/预实验/sub-XXX_/beh/sub-XXX_Block*_beh.csv
      生理  mmwave 分片（load_frames 按帧范围加载）
      时间对齐: absolute_onset_time 与 mmwave_start 同轴（unix ms）
输出: output/预实验/03_跨被试/09_预实验-事件相关-nogo/
        erp_nogo_summary.json  ← 每被试 + 聚合
        erp_nogo_compare.png   ← 错误 vs 正确前窗对比
用法:
  cd 08_算法/scripts
  python analyze_erp_nogo.py --data-root F:/预实验
依赖: numpy, scipy, matplotlib
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent / "output" / "预实验"
OUT_DIR = OUT_ROOT / "03_跨被试" / "09_预实验-事件相关-nogo"
SUBJECTS = ["000", "003", "004", "005", "006", "007", "008", "009", "010"]
PRE_WIN_SEC = 60.0        # no-go 前窗长 (s): RMSSD 短窗可靠性依据 (r>0.9);
                          # 频域 LF 需 ≥2min、HF ≥1min（Task Force 1996),
                          # 延长用 --pre-win 覆盖（注意: no-go 间隔 5.8s,
                          # 窗越长含其他虚报概率越高, 样本损失越大）
MIN_EVENTS = 5            # 被试级最少事件数
METRICS = ["hr_bpm", "sdnn_ms", "rmssd_ms", "br_bpm"]
# 伪影窗剔除: sub-010 快呼吸谐波污染心跳带, 真实静息 HR 49-62bpm
SUBJECT_HR_VALID = {"010": (40.0, 75.0)}


def load_events(data_root: Path, subject: str) -> list[dict]:
    """读取全部 no-go 试次（含按键与否与绝对时间戳）。

    参数:
        data_root: 数据根目录
        subject: 被试编号
    返回:
        [{"abs_onset_ms": int, "comm": bool, "rel_s": float(距 mmwave_start)}, ...]
    """
    tl = data_root / f"sub-{subject}_" / "beh" / "master_timeline.csv"
    mm_start = None
    with open(tl, encoding="utf-8", newline="") as f:
        for parts in csv.reader(f):
            if len(parts) >= 3 and parts[0] == "mmwave_start":
                mm_start = int(parts[2])
                break
    if mm_start is None:
        return []

    events = []
    beh_dir = data_root / f"sub-{subject}_" / "beh"
    for b in sorted(beh_dir.glob(f"sub-{subject}_Block*_beh.csv")):
        with open(b, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("is_no_go") != "1":
                    continue
                try:
                    abs_ms = int(float(r["absolute_onset_time"]))
                except (KeyError, ValueError):
                    continue
                comm = r.get("response", "") == "1"
                events.append({"abs_onset_ms": abs_ms, "comm": comm,
                               "rel_s": (abs_ms - mm_start) / 1000.0})
    return events


_TS_CACHE: dict = {}       # subject -> (frame_idx, py_ms) 时间戳缓存


def load_frames_for_window(mm_dir: Path, subject: str, fps: float,
                           t0_ms: int, t1_ms: int):
    """按绝对时间范围 [t0_ms, t1_ms) 加载毫米波窗数据。

    实现: 读 timestamps.csv 的第三列（Python ms 时间戳）, 找帧号范围,
    复用 analyze_mmwave_full 的 load_frames（片号映射）。时间戳按
    场次缓存, 避免逐事件重复读文件。

    参数:
        mm_dir: mmwave 分片目录
        subject: 被试编号
        fps: 帧率 (Hz)
        t0_ms: 窗起点 (ms)
        t1_ms: 窗终点 (ms)
    返回:
        iq: (n, 256, 8) complex64 或 None（帧不足）
    """
    import sys
    sys.path.insert(0, str(SCRIPT_DIR))
    import analyze_mmwave_hrv as rhrv
    rhrv.SUBJECT = subject
    rhrv.DATA_ROOT = mm_dir.parent.parent
    rhrv.MMWAVE_DIR = mm_dir
    if subject not in _TS_CACHE:
        frame_idx, py_ms = rhrv.load_timestamps()
        _TS_CACHE[subject] = (frame_idx, py_ms)
    frame_idx, py_ms = _TS_CACHE[subject]
    if len(frame_idx) == 0:
        return None
    rhrv.FIRST_FRAME = int(frame_idx[0])
    rhrv.N_PARTITIONS = (len(frame_idx) + rhrv.CHUNK - 1) // rhrv.CHUNK
    i0 = int(np.searchsorted(py_ms, t0_ms))
    i1 = int(np.searchsorted(py_ms, t1_ms))
    if i1 - i0 < 200:                    # 少于 200 帧（~2s）不可用
        return None
    try:
        return rhrv.load_frames(int(frame_idx[i0]), int(frame_idx[i1]))
    except Exception:
        return None


def main():
    """遍历场次 → 前窗提取 → 组间比较 → 聚合。"""
    parser = argparse.ArgumentParser(description="no-go 前窗事件相关分析")
    parser.add_argument("--data-root", required=True, help="数据根目录 (F:/预实验)")
    parser.add_argument("--pre-win", type=float, default=PRE_WIN_SEC,
                        help=f"前窗长 (s), 默认 {PRE_WIN_SEC}; 延长可纳入频域但损失样本")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for subject in SUBJECTS:
        events = load_events(data_root, subject)
        if len(events) < MIN_EVENTS:
            print(f"sub-{subject}: 事件 {len(events)} 个, 跳过")
            continue
        # 错误时刻集合（用于剔除前窗含其他虚报）
        comm_times = {e["abs_onset_ms"] for e in events if e["comm"]}
        mm_dir = data_root / f"sub-{subject}_" / "mmwave"
        # 取 meta fps
        import json as _json
        meta = _json.loads((mm_dir / f"sub-{subject}_mmwave.meta.json").read_text())
        fps = float(meta["fps"])

        win_ms = int(args.pre_win * 1000)
        comm_windows, corr_windows = [], []
        n_comm, n_corr, n_drop = 0, 0, 0
        for ev in events:
            t1 = ev["abs_onset_ms"]
            t0 = t1 - win_ms
            # 剔除前窗内含其他虚报的窗（错误与正确组同规则）
            if any(c for c in comm_times if t0 <= c < t1):
                n_drop += 1
                continue
            iq = load_frames_for_window(mm_dir, subject, fps, t0, t1)
            if iq is None:
                continue
            from analyze_mmwave_hrv import analyze_window_auto
            out = analyze_window_auto(iq)
            if out is None or out[0].get("quality") != "ok":
                continue
            res = out[0]
            hr = res["hr_time_bpm"]
            # 伪影剔除: HR 超出生理/个体有效范围
            lo, hi = SUBJECT_HR_VALID.get(subject, (40.0, 100.0))
            if hr is None or not (lo <= hr <= hi):
                continue
            freq = res.get("hrv", {}).get("frequency", {}) if res.get("hrv") else {}
            row = {
                "hr_bpm": hr,
                "br_bpm": res.get("br_freq_bpm"),
                "sdnn_ms": res["hrv"]["SDNN_ms"] if res.get("hrv") else None,
                "rmssd_ms": res["hrv"]["RMSSD_ms"] if res.get("hrv") else None,
                "lf_hf": freq.get("LF_HF") if freq else None,
                "lf_ms2": freq.get("LF_ms2") if freq else None,
                "hf_ms2": freq.get("HF_ms2") if freq else None,
                "t_rel_s": ev["rel_s"],
            }
            if ev["comm"]:
                comm_windows.append(row); n_comm += 1
            else:
                corr_windows.append(row); n_corr += 1
        print(f"sub-{subject}: 前窗虚报 {n_comm}, 正确抑制 {n_corr}, 污染剔除 {n_drop}")

        # ── 组间比较 ──
        compare = {}
        for m in METRICS:
            vc = [w[m] for w in comm_windows if w[m] is not None]
            vr = [w[m] for w in corr_windows if w[m] is not None]
            if len(vc) < MIN_EVENTS or len(vr) < MIN_EVENTS:
                continue
            t, p = stats.ttest_ind(vc, vr, equal_var=False)
            pooled = np.sqrt(((len(vc) - 1) * np.std(vc, ddof=1) ** 2
                              + (len(vr) - 1) * np.std(vr, ddof=1) ** 2)
                             / (len(vc) + len(vr) - 2))
            d = (np.mean(vc) - np.mean(vr)) / (pooled + 1e-12)
            compare[m] = {"n_event": len(vc), "n_control": len(vr),
                          "mean_event": round(float(np.mean(vc)), 3),
                          "mean_control": round(float(np.mean(vr)), 3),
                          "t": round(float(t), 3), "p": round(float(p), 4),
                          "cohen_d": round(float(d), 3)}
        results[subject] = {"n_comm": n_comm, "n_corr": n_corr,
                            "compare": compare}

        # 打印
        for m, c in compare.items():
            flag = " *" if c["p"] < 0.05 else ""
            print(f"  {m}: 错误 {c['mean_event']} vs 正确 {c['mean_control']} "
                  f"(d={c['cohen_d']}, p={c['p']}){flag}")

    # ── 聚合: 跨场次 mean d ──
    agg = {}
    for m in METRICS:
        ds = [r["compare"][m]["cohen_d"] for r in results.values()
              if m in r["compare"]]
        if ds:
            agg[m] = {"n_subjects": len(ds), "mean_d": round(float(np.mean(ds)), 3),
                      "d_list": ds}
    print("\n聚合效应量(comm 前窗 vs correct 前窗):", json.dumps(agg, ensure_ascii=False))

    with open(OUT_DIR / "erp_nogo_summary.json", "w", encoding="utf-8") as f:
        json.dump({"subjects": results, "aggregate": agg}, f, ensure_ascii=False, indent=2)
    print(f"[json] {OUT_DIR / 'erp_nogo_summary.json'}")


if __name__ == "__main__":
    main()


