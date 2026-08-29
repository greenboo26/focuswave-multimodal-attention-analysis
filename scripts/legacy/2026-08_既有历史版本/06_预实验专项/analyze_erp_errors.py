"""
analyze_erp_errors.py — 行为错误事件相关生理分析（Event-Related, 粗粒度版）
====================================================================
版本: v1.0 (2026-08-11)
功能: 以行为错误（commission: no-go 上错误按键 / omission: go 上漏按）
      为事件锚点, 将事件映射到 30s 生理窗, 对比"错误窗 vs 非错误窗"
      与"错误前窗 → 错误窗 → 错误后窗"的 HR/BR/HRV 变化模式。
      不依赖探针标签, 样本量为探针的数十倍（预实验 183 commission）。

数据: 行为事件: F:/预实验/sub-XXX_/beh/sub-XXX_Block*_beh.csv
      生理窗:   output/预实验/09_预实验-SUB{XXX}-FULL/sub{XXX}_full_windows.json
      时间对齐: beh/ 下 master_timeline.csv 的 mmwave_start
输出: output/预实验/03_跨被试/09_预实验-事件相关/
        erp_summary.json        ← 每被试 + 聚合统计
        erp_window_compare.png  ← 错误窗 vs 非错误窗对比
        erp_response_curve.png  ← 错误前/错误/错误后窗变化曲线
用法:
  cd 08_算法/scripts
  python analyze_erp_errors.py --data-root F:/预实验
依赖: numpy, scipy, matplotlib
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent / "output" / "预实验"
OUT_DIR = OUT_ROOT / "03_跨被试" / "09_预实验-事件相关"
SUBJECTS = ["000", "003", "004", "005", "006", "007", "008", "009", "010"]
WINDOW_SEC = 30.0          # 生理窗长（与 analyze_mmwave_full 一致）
MIN_EVENTS = 5             # 被试级分析最少事件数
METRICS = ["hr_bpm", "sdnn_ms", "rmssd_ms", "br_bpm"]
# 伪影窗剔除: sub-010 快呼吸时呼吸 4-5 次谐波与环境中第二心跳源泄漏,
# 产生 75-106bpm 假 HR 窗（2026-08-11 频谱验证）。真实静息 HR 49-62bpm。
SUBJECT_HR_VALID = {"010": (40.0, 75.0)}


def load_events(data_root: Path, subject: str) -> list[dict]:
    """读取该被试全部 commission/omission 事件（含相对 mmwave 时间）。

    参数:
        data_root: 数据根目录
        subject: 被试编号
    返回:
        [{"type": comm|omis, "rel_s": 距 mmwave_start 秒}, ...]
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
    for fpath in sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv")):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    onset = int(float(r["absolute_onset_time"]))
                except (ValueError, KeyError):
                    continue
                rel_s = (onset - mm_start) / 1000.0
                if rel_s < 0:
                    continue
                if r["is_no_go"] == "1" and r["response"] == "1":
                    events.append({"type": "comm", "rel_s": rel_s})
                elif r["is_no_go"] == "0" and r["response"] == "0":
                    events.append({"type": "omis", "rel_s": rel_s})
    return events


def load_windows(subject: str) -> list[dict]:
    """读取可信窗（quality=ok, 含生理指标）。"""
    p = OUT_ROOT / "02_全程窗" / f"09_预实验-SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    if not p.exists():
        return []
    d = json.load(open(p, encoding="utf-8"))
    ws = [w for w in d["windows"] if w.get("quality") == "ok" and w.get("hr_bpm")]
    if subject in SUBJECT_HR_VALID:
        lo, hi = SUBJECT_HR_VALID[subject]
        ws = [w for w in ws if lo <= w["hr_bpm"] <= hi]
    return ws


def classify_windows(windows: list[dict], events: list[dict]) -> tuple[dict, dict]:
    """事件 → 窗归属: 错误窗 / 非错误窗 / 错误前窗 / 错误后窗。

    窗 i 覆盖 [t_start, t_start+30); 事件落在窗内中间 20s
    [t_start+5, t_start+25) 视为该窗的事件（避开边界归属歧义）。

    参数:
        windows: 可信窗列表
        events: 事件列表
    返回:
        (event_windows, context): event_windows = {type: [窗索引...]},
                                  context = {type: {"prev": [...], "post": [...]}}
    """
    idx = {w["t_start_s"]: i for i, w in enumerate(windows)}
    starts = sorted(idx)
    event_windows = {"comm": [], "omis": []}
    context = {"comm": {"prev": [], "post": []}, "omis": {"prev": [], "post": []}}
    for ev in events:
        t = ev["rel_s"]
        # 事件所属窗: 窗起点 <= t-5 且 t+5 < 窗起点+30
        for s in starts:
            if s <= t - 5 and t + 5 < s + WINDOW_SEC:
                i = idx[s]
                event_windows[ev["type"]].append(i)
                # 前窗/后窗（存在才记录）
                j = starts.index(s)
                if j > 0:
                    context[ev["type"]]["prev"].append(idx[starts[j - 1]])
                if j < len(starts) - 1:
                    context[ev["type"]]["post"].append(idx[starts[j + 1]])
                break
    return event_windows, context


def window_compare(windows: list[dict], ev_idx: list[int], metric: str):
    """错误窗 vs 非错误窗（该指标）的 t 检验与效应量。

    参数:
        windows: 可信窗列表
        ev_idx: 错误窗索引集合
        metric: 指标名
    返回:
        dict: n_event/n_control/mean_event/mean_control/t/p/d 或 None
    """
    ev = set(ev_idx)
    x = [windows[i][metric] for i in ev if windows[i].get(metric) is not None]
    y = [w[metric] for i, w in enumerate(windows)
         if i not in ev and w.get(metric) is not None]
    if len(x) < MIN_EVENTS or len(y) < 10:
        return None
    x, y = np.asarray(x, float), np.asarray(y, float)
    t, p = stats.ttest_ind(x, y)
    sp = np.sqrt(((len(x) - 1) * x.var(ddof=1) + (len(y) - 1) * y.var(ddof=1)) /
                 (len(x) + len(y) - 2))
    d = (x.mean() - y.mean()) / sp if sp > 0 else 0.0
    return {"n_event": int(len(x)), "n_control": int(len(y)),
            "mean_event": round(float(x.mean()), 3), "mean_control": round(float(y.mean()), 3),
            "t": round(float(t), 3), "p": round(float(p), 4), "cohen_d": round(float(d), 3)}


def response_curve(windows: list[dict], ev_idx: list[int], context: dict, metric: str):
    """错误前窗 → 错误窗 → 错误后窗 的均值变化（配对）。

    参数:
        windows: 可信窗列表
        ev_idx: 错误窗索引
        context: prev/post 窗索引
        metric: 指标名
    返回:
        dict: {"prev": [值...], "event": [...], "post": [...]}（三列配对可用）或 None
    """
    # prev/event/post 三列按事件一一对应（context 与 ev_idx 同序构建）
    pairs = {"prev": [], "event": [], "post": []}
    n = min(len(context["prev"]), len(ev_idx), len(context["post"]))
    if n < MIN_EVENTS:
        return None
    for k in range(n):
        i_ev = ev_idx[k]
        i_pre, i_post = context["prev"][k], context["post"][k]
        for key, i in (("prev", i_pre), ("event", i_ev), ("post", i_post)):
            v = windows[i].get(metric)
            if v is not None:
                pairs[key].append(v)
    out = {"n": int(n)}
    for key in ("prev", "event", "post"):
        arr = np.asarray(pairs[key], float)
        out[key] = {"mean": round(float(arr.mean()), 3),
                    "se": round(float(arr.std(ddof=1) / np.sqrt(len(arr))), 3),
                    "n": int(len(arr))} if len(arr) else None
    return out


def main():
    parser = argparse.ArgumentParser(description="行为错误事件相关生理分析")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    result = {}
    print("=" * 60)
    print("  行为错误事件相关分析（commission/omission 锚点, 不依赖探针）")
    print("=" * 60)
    for sub in SUBJECTS:
        events = load_events(data_root, sub)
        windows = load_windows(sub)
        if not windows:
            print(f"sub-{sub}: 无可信窗, 跳过")
            continue
        ev_idx, context = classify_windows(windows, events)
        # 按唯一窗计数（同窗多事件去重, 与 window_compare 内部一致）
        n_comm, n_omis = len(set(ev_idx["comm"])), len(set(ev_idx["omis"]))
        print(f"sub-{sub}: 可信窗 {len(windows)}, commission {n_comm}, omission {n_omis}")
        sub_res = {"n_windows": len(windows), "n_comm": n_comm, "n_omis": n_omis,
                   "compare": {}, "response": {}}
        for typ, n in (("comm", n_comm), ("omis", n_omis)):
            if n < MIN_EVENTS:
                continue
            for m in METRICS:
                cmp = window_compare(windows, ev_idx[typ], m)
                if cmp:
                    sub_res["compare"][f"{typ}_{m}"] = cmp
                resp = response_curve(windows, ev_idx[typ], context[typ], m)
                if resp:
                    sub_res["response"][f"{typ}_{m}"] = resp
        result[sub] = sub_res

    # 聚合: 跨被试合并 comm 错误窗 vs 非错误窗（按被试内 z 不适用, 先合并原始值）
    agg = {}
    for m in METRICS:
        all_ev, all_ct = [], []
        for sub, r in result.items():
            key = f"comm_{m}"
            if key in r["compare"]:
                # 需要原始值才能合并: 从窗口重算
                pass
        agg[m] = None
    # 聚合改为: 对每个被试 compare 的 cohen_d 取均值（效应量方向合并）
    agg_d = {m: [] for m in METRICS}
    for sub, r in result.items():
        for m in METRICS:
            if f"comm_{m}" in r["compare"]:
                agg_d[m].append(r["compare"][f"comm_{m}"]["cohen_d"])
    agg = {m: {"n_subjects": len(v), "mean_d": round(float(np.mean(v)), 3),
               "d_list": v} for m, v in agg_d.items() if v}
    result["_aggregate"] = {"n_subjects_analyzed": sum(1 for s in SUBJECTS if s in result),
                            "mean_cohen_d_comm": agg}

    json_path = OUT_DIR / "erp_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[json] {json_path}")

    # 打印关键结果
    print("\n===== commission 错误窗 vs 非错误窗（被试级）=====")
    for sub, r in result.items():
        if sub == "_aggregate":
            continue
        for m in METRICS:
            key = f"comm_{m}"
            if key in r["compare"]:
                c = r["compare"][key]
                sig = " *" if c["p"] < 0.05 else ""
                print(f"  {sub} {m}: 错误 {c['mean_event']} vs 非错误 {c['mean_control']} "
                      f"(d={c['cohen_d']}, p={c['p']}){sig}")
    _plot_compare(result, OUT_DIR)
    _plot_response(result, OUT_DIR)
    print(f"  聚合效应量(comm): {agg}")


def _plot_compare(result: dict, out_dir: Path):
    """错误窗 vs 非错误窗对比图（cohen d 森林图风格）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    subs = [s for s in SUBJECTS if s in result]
    fig, axes = plt.subplots(1, len(METRICS), figsize=(16, 4), sharey=True)
    for ax, m in zip(axes, METRICS):
        labels, ds = [], []
        for sub in subs:
            key = f"comm_{m}"
            if key in result[sub].get("compare", {}):
                labels.append(sub)
                ds.append(result[sub]["compare"][key]["cohen_d"])
        if ds:
            ax.barh(labels, ds, color=["#2e86c1" if abs(d) < 0.2 else ("#c0392b" if d > 0 else "#8e44ad") for d in ds])
            ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(f"{m}\n(错误窗−非错误窗, Cohen's d)")
        ax.grid(True, alpha=0.3, axis="x")
    fig.suptitle("commission 错误窗 vs 非错误窗 生理差异（正=错误窗更高）", fontsize=13)
    plt.tight_layout()
    png = out_dir / "erp_window_compare.png"
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"[png] {png}")


def _plot_response(result: dict, out_dir: Path):
    """错误前窗 → 错误窗 → 错误后窗 响应曲线（跨被试聚合均值）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, len(METRICS), figsize=(16, 4))
    x = np.array([-1, 0, 1])
    for ax, m in zip(axes, METRICS):
        curves = []
        for sub, r in result.items():
            if sub == "_aggregate":
                continue
            key = f"comm_{m}"
            if key in r["response"]:
                resp = r["response"][key]
                means = [resp[k]["mean"] if resp[k] else np.nan for k in ("prev", "event", "post")]
                if not any(np.isnan(means)):
                    curves.append(means)
        if curves:
            arr = np.asarray(curves, float)
            mu, se = arr.mean(axis=0), arr.std(axis=0, ddof=1) / np.sqrt(len(arr))
            ax.errorbar(x, mu, yerr=se, fmt="o-", capsize=3, color="#2e86c1")
            ax.set_xticks(x)
            ax.set_xticklabels(["错误前窗", "错误窗", "错误后窗"])
            ax.axhline(mu[0], color="gray", linestyle="--", linewidth=0.8)
        ax.set_title(f"{m}（n={len(curves)} 被试）")
        ax.grid(True, alpha=0.3)
    fig.suptitle("commission 错误前后 30s 窗生理响应曲线（跨被试均值±SE）", fontsize=13)
    plt.tight_layout()
    png = out_dir / "erp_response_curve.png"
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"[png] {png}")


if __name__ == "__main__":
    main()


