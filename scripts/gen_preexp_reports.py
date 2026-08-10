"""
gen_preexp_reports.py — 预实验标准化预处理报告生成
====================================================================
版本: v1.0 (2026-08-11)
功能: 对预实验被试生成标准化预处理报告（对齐 NeuroKit pipeline 报告
      理念）: 信号质量（SNR/IBI/原因分布）+ 全程窗可用率 + 生理特征
      汇总 + 行为表现 + 错误事件 + 探针标签分布。每被试一份 md,
      附一张汇总对比表。

数据: quality: output/预实验/09_预实验-SUB{XXX}-QUALITY/sub{XXX}_quality_detail.csv
      windows: output/预实验/09_预实验-SUB{XXX}-FULL/sub{XXX}_full_windows.json
      行为:    F:/预实验/sub-XXX_/beh/（Block csv + master_timeline）
输出: output/预实验/09_预实验-预处理报告/
        sub{XXX}_prep_report.md  ← 每被试报告
        preexp_all_report.md     ← 汇总对比表
用法:
  cd 08_算法/scripts
  python gen_preexp_reports.py --data-root F:/预实验
依赖: numpy
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent / "output" / "预实验"
OUT_DIR = OUT_ROOT / "09_预实验-预处理报告"
SUBJECTS = ["000", "001", "002", "003", "004", "005", "006", "007"]


def load_quality(subject: str) -> dict:
    """读质量评估 detail.csv, 汇总 SNR/IBI/原因分布。"""
    p = OUT_ROOT / f"09_预实验-SUB{subject}-QUALITY" / f"sub{subject}_quality_detail.csv"
    if not p.exists():
        return None
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    n = len(rows)
    ok = [r for r in rows if r["ok"] == "True"]
    snrs = [float(r["snr_db"]) for r in ok if r["snr_db"]]
    ibis = [float(r["ibi_ratio"]) for r in ok if r["ibi_ratio"]]
    reasons = {}
    for r in rows:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    return {"n_windows": n, "n_ok": len(ok), "ok_ratio": len(ok) / n if n else 0,
            "snr_median": np.median(snrs) if snrs else None,
            "ibi_median": np.median(ibis) if ibis else None,
            "reasons": reasons}


def load_full(subject: str) -> dict:
    """读 full_windows.json, 汇总生理与行为特征。"""
    p = OUT_ROOT / f"09_预实验-SUB{subject}-FULL" / f"sub{subject}_full_windows.json"
    if not p.exists():
        return None
    d = json.load(open(p, encoding="utf-8"))
    ok = [w for w in d["windows"] if w.get("quality") == "ok"]
    out = {"n_total": len(d["windows"]), "n_ok": len(ok),
           "ok_ratio": len(ok) / len(d["windows"]) if d["windows"] else 0}
    for m in ["hr_bpm", "br_bpm", "sdnn_ms", "rmssd_ms", "sampen", "dfa_alpha1"]:
        vals = [w[m] for w in ok if w.get(m) is not None and w[m] == w[m]]
        out[m] = {"median": float(np.median(vals)), "q1": float(np.percentile(vals, 25)),
                  "q3": float(np.percentile(vals, 75))} if vals else None
    rts = [w["rt_mean"] for w in ok if w.get("rt_mean") is not None]
    out["rt_median"] = float(np.median(rts)) if rts else None
    probes = d.get("probes", [])
    labels = {}
    for pr in probes:
        lab = pr.get("label_name", "未知")
        labels[lab] = labels.get(lab, 0) + 1
    out["probes"] = {"n": len(probes), "labels": labels,
                     "n_ok": sum(1 for pr in probes if pr.get("quality") == "ok")}
    return out


def load_behavior(data_root: Path, subject: str) -> dict:
    """读行为 CSV, 统计错误事件与 RT。"""
    comm = omis = n_go = n_nogo = 0
    rts = []
    for fpath in sorted((data_root / f"sub-{subject}_" / "beh").glob(f"sub-{subject}_Block*_beh.csv")):
        with open(fpath, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["is_no_go"] == "1":
                    n_nogo += 1
                    if r["response"] == "1":
                        comm += 1
                else:
                    n_go += 1
                    if r["response"] == "0":
                        omis += 1
                if r.get("rt") and r["response"] == "1" and r["is_no_go"] == "0":
                    rts.append(float(r["rt"]))
    return {"n_go": n_go, "n_nogo": n_nogo, "comm": comm, "omis": omis,
            "comm_rate": comm / n_nogo if n_nogo else None,
            "omis_rate": omis / n_go if n_go else None,
            "rt_median": float(np.median(rts)) if rts else None}


def fmt(v, nd=1):
    return f"{v:.{nd}f}" if v is not None and v == v else "-"


def main():
    parser = argparse.ArgumentParser(description="预实验标准化预处理报告")
    parser.add_argument("--data-root", type=str, default="F:/预实验")
    args = parser.parse_args()
    data_root = Path(args.data_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for sub in SUBJECTS:
        q = load_quality(sub)
        f = load_full(sub)
        b = load_behavior(data_root, sub)
        if q is None and f is None:
            continue
        verdict = "不可信" if (q and q["ok_ratio"] < 0.3) else (
            "部分可信" if q and q["ok_ratio"] < 0.7 else ("可信" if q else "—"))
        rows.append({"sub": sub, "q": q, "f": f, "b": b, "verdict": verdict})

    # 汇总表
    all_lines = ["# 预实验预处理报告汇总（2026-08-11）", "",
                 "| 被试 | 质量评估 | SNR(dB) | 全程窗可用率 | HR | BR | SDNN | RMSSD | SampEn | DFAα1 | RT(ms) | 误按率 | 漏按率 | 探针(专注/总) |",
                 "|------|---------|---------|-------------|-----|-----|------|-------|--------|--------|--------|--------|--------|--------------|"]
    for r in rows:
        q, f, b = r["q"], r["f"], r["b"]
        probes = f"{f['probes']['labels'].get('专注', 0)}/{f['probes']['n']}" if f and f["probes"]["n"] else "-"
        all_lines.append(
            f"| {r['sub']} | {r['verdict']} | {fmt(q['snr_median']) if q else '-'} | "
            f"{fmt(f['ok_ratio']*100) if f else '-'}% | {fmt(f['hr_bpm']['median']) if f and f['hr_bpm'] else '-'} | "
            f"{fmt(f['br_bpm']['median']) if f and f['br_bpm'] else '-'} | "
            f"{fmt(f['sdnn_ms']['median']) if f and f['sdnn_ms'] else '-'} | "
            f"{fmt(f['rmssd_ms']['median']) if f and f['rmssd_ms'] else '-'} | "
            f"{fmt(f['sampen']['median'], 2) if f and f['sampen'] else '-'} | "
            f"{fmt(f['dfa_alpha1']['median'], 2) if f and f['dfa_alpha1'] else '-'} | "
            f"{fmt(b['rt_median']) if b else '-'} | "
            f"{fmt(b['comm_rate']*100) if b and b['comm_rate'] is not None else '-'}% | "
            f"{fmt(b['omis_rate']*100) if b and b['omis_rate'] is not None else '-'}% | {probes} |")
    all_lines += ["", "质量评估口径: SNR≥3dB 且 IBI 有效率≥0.8 → 窗可信。",
                  "被试级: ≥70% 可信 / 30-70% 部分可信 / <30% 不可信。",
                  "SampEn/DFA 为 v1.4 新增非线性特征（IBI 序列复杂度, 走神文献关注维度）。"]
    (OUT_DIR / "preexp_all_report.md").write_text("\n".join(all_lines), encoding="utf-8")

    # 每被试报告
    for r in rows:
        sub, q, f, b = r["sub"], r["q"], r["f"], r["b"]
        lines = [f"# sub-{sub} 预处理报告", "", f"生成: 2026-08-11 | 判定: **{r['verdict']}**", "",
                 "## 信号质量（assess_preexp_quality 口径）"]
        if q:
            lines += [f"- 质量评估窗: {q['n_ok']}/{q['n_windows']} ({q['ok_ratio']:.0%})",
                      f"- SNR 中位: {fmt(q['snr_median'], 1)} dB | IBI 有效率中位: {fmt(q['ibi_median'], 2)}",
                      f"- 原因分布: {q['reasons']}"]
        else:
            lines += ["- 未做质量评估"]
        lines += ["", "## 全程窗生理特征（可信窗）"]
        if f:
            for m, lab in [("hr_bpm", "HR"), ("br_bpm", "BR"), ("sdnn_ms", "SDNN"),
                           ("rmssd_ms", "RMSSD"), ("sampen", "SampEn"), ("dfa_alpha1", "DFAα1")]:
                v = f.get(m)
                lines.append(f"- {lab}: 中位 {fmt(v['median'] if v else None, 2)} "
                             f"(IQR {fmt(v['q1'] if v else None, 2)}-{fmt(v['q3'] if v else None, 2)})" if v else f"- {lab}: 无")
            lines += [f"- 全程窗可用率: {f['n_ok']}/{f['n_total']} ({f['ok_ratio']:.0%})"]
        lines += ["", "## 行为表现"]
        if b:
            lines += [f"- go 试次: {b['n_go']} | no-go 试次: {b['n_nogo']}",
                      f"- commission: {b['comm']} ({fmt(b['comm_rate']*100)}%) | omission: {b['omis']} ({fmt(b['omis_rate']*100)}%)",
                      f"- RT 中位: {fmt(b['rt_median'])} ms"]
        lines += ["", "## 探针标签"]
        if f and f["probes"]["n"]:
            lines += [f"- 探针: {f['probes']['n']} 个（可信 {f['probes']['n_ok']}）, 标签分布: {f['probes']['labels']}"]
        else:
            lines += ["- 无探针数据"]
        (OUT_DIR / f"sub{sub}_prep_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"[md] {OUT_DIR}/preexp_all_report.md + 每被试报告")
    print("\n".join(all_lines[:12]))


if __name__ == "__main__":
    main()
