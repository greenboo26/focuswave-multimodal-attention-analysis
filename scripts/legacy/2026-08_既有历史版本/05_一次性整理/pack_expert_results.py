"""
专家审查包结果打包脚本
======================
把每名被试的质量评估 + 全程窗生理指标合并为单个汇总文档,
连同质量时间线图复制到专家审查包 03_结果示例/。

用法:
    cd 08_算法/scripts
    python pack_expert_results.py

依赖: numpy (结果 JSON/CSV 均来自截断版 v5 输出)
"""

import csv
import json
import shutil
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR.parent / "output"
PACK_DIR = SCRIPT_DIR.parent / "docs" / "交付" / "给专家审查包" / "03_结果示例"

# 可用被试 (001/002 摆位失误排除) → 匿名标签
SUBJECTS = [("000", "A"), ("003", "B"), ("004", "C"), ("005", "D"),
            ("006", "E"), ("007", "F"), ("008", "G"), ("009", "H"),
            ("010", "I")]


def load_quality(sub: str) -> dict:
    """读质量评估 CSV, 返回汇总统计。

    参数:
        sub: 被试编号
    返回:
        dict: {n_win, n_ok, ok_ratio, hr_median, snr_median, n_artifact}
    """
    path = (OUTPUT_ROOT / "预实验" / "01_质量评估"
            / f"09_预实验-SUB{sub}-QUALITY-v5" / f"sub{sub}_quality_detail.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    ok = [r for r in rows if r["ok"] == "True"]
    hrs = sorted(float(r["hr_bpm"]) for r in ok if r["hr_bpm"])
    snrs = sorted(float(r["snr_db"]) for r in ok if r["snr_db"])
    n_art = sum(1 for r in rows if r["reason"] == "hr_out_of_range")
    return {
        "n_win": len(rows), "n_ok": len(ok),
        "ok_ratio": len(ok) / len(rows) if rows else 0,
        "hr_median": hrs[len(hrs) // 2] if hrs else None,
        "snr_median": snrs[len(snrs) // 2] if snrs else None,
        "n_artifact": n_art,
    }


def load_physio(sub: str) -> dict:
    """读全程窗 JSON, 返回可信窗生理指标均值±标准差。

    参数:
        sub: 被试编号
    返回:
        dict: {n_win, hr, br, sdnn, rmssd} 各为 (mean, std)
    """
    path = (OUTPUT_ROOT / "预实验" / "02_全程窗"
            / f"09_预实验-SUB{sub}-FULL-v5" / f"sub{sub}_full_windows.json")
    d = json.load(open(path, encoding="utf-8"))
    ws = [w for w in d["windows"] if w.get("quality") == "ok"]

    def stat(key):
        vals = [w[key] for w in ws if w.get(key) is not None]
        return (float(np.mean(vals)), float(np.std(vals)), len(vals)) if vals else (None, None, 0)

    return {"n_win": len(ws), "hr": stat("hr_bpm"), "br": stat("br_bpm"),
            "sdnn": stat("sdnn_ms"), "rmssd": stat("rmssd_ms")}


def build_md(tag: str, q: dict, p: dict) -> str:
    """生成单被试合并汇总文档。

    参数:
        tag: 匿名标签 (A-I)
        q: 质量评估统计
        p: 生理指标统计
    返回:
        str: Markdown 文档内容
    """
    verdict = "可信" if q["ok_ratio"] >= 0.7 else "部分可信"
    lines = [
        f"# 被试 {tag} 结果汇总",
        "",
        "## 质量评估（30s 窗 × 15s 步进, 按行为时间轴截断）",
        "",
        f"- 判定: **{verdict}**",
        f"- 可信窗: {q['n_ok']}/{q['n_win']} ({q['ok_ratio']:.0%})",
        f"- HR 中位数: {q['hr_median']:.1f} bpm" if q["hr_median"] else "- HR: 无",
        f"- SNR 中位数: {q['snr_median']:.1f} dB" if q["snr_median"] else "- SNR: 无",
    ]
    if q["n_artifact"]:
        lines.append(f"- 呼吸谐波伪影窗（HR 超生理范围剔除）: {q['n_artifact']} 窗")
    lines += [
        "",
        "窗级判定: SNR ≥ 3dB 且 IBI 有效率 ≥ 0.8 → 可信。",
        "",
        "## 生理指标（全程可信窗均值 ± 标准差）",
        "",
    ]
    for name, (mean, std, n) in [("HR (bpm)", p["hr"]), ("呼吸率 (次/分)", p["br"]),
                                  ("SDNN (ms)", p["sdnn"]), ("RMSSD (ms)", p["rmssd"])]:
        lines.append(f"- {name}: {mean:.1f} ± {std:.1f}（n={n}）" if mean is not None
                     else f"- {name}: 无")
    return "\n".join(lines) + "\n"


def main() -> None:
    """打包 9 名被试结果到专家审查包。"""
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    for sub, tag in SUBJECTS:
        q = load_quality(sub)
        p = load_physio(sub)
        md = build_md(tag, q, p)
        (PACK_DIR / f"被试{tag}_结果汇总.md").write_text(md, encoding="utf-8")
        # 质量时间线图
        src_png = (OUTPUT_ROOT / "预实验" / "01_质量评估"
                   / f"09_预实验-SUB{sub}-QUALITY-v5" / f"sub{sub}_quality_timeline.png")
        if src_png.exists():
            shutil.copy(src_png, PACK_DIR / f"被试{tag}_质量时间线.png")
        print(f"被试{tag}: {q['n_ok']}/{q['n_win']} ({q['ok_ratio']:.0%}), "
              f"HR 中位 {q['hr_median']:.0f}, 生理窗 {p['n_win']}")
    # 清理旧的拆分文档
    for old in PACK_DIR.glob("被试*_质量评估汇总.md"):
        old.unlink()
    for old in PACK_DIR.glob("被试*_生理指标汇总.md"):
        old.unlink()
    print("打包完成")


if __name__ == "__main__":
    main()


